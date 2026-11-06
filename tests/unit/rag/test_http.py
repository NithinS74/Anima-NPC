import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError

from npc.context import build_situation
from npc.contracts.context import DialogueMemory, PlayerInput
from npc.rag.http import HTTPRetriever, RAGConfig, load_retriever


def config(situation, **overrides):
    data = dict(bindings=[dict(game_id=situation.scope.game_id, world_id=situation.scope.world_id,
                              npc_ids=[situation.npc_id], source="lore/dialogue.txt")])
    data.update(overrides)
    return RAGConfig.model_validate(data)


def hit(**changes):
    data = dict(id="chunk-1", text="The healer works at the eastern gate.", source="lore/dialogue.txt",
                page=None, chunk_index=7, distance=0.2, truncated=False)
    data.update(changes)
    return data


def retrieve(situation, response, *, settings=None, status=200):
    calls = []
    def handler(request):
        data = json.loads(request.content)
        calls.append(data)
        payload = dict(query=data["query"], context="DO NOT USE PREPACKED CONTEXT", matches=response)
        return httpx.Response(status, content=json.dumps(payload).encode())
    adapter = HTTPRetriever(settings or config(situation), transport=httpx.MockTransport(handler))
    return asyncio.run(adapter.retrieve(situation, timeout_s=0.5)), calls


def test_existing_api_contract_source_filter_and_followup_context(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    situation = situation.model_copy(update={"player_input": PlayerInput(text="Where can I find them?"), "recent_dialogue": (
        DialogueMemory(request_id="prior", player_text="Who is the healer?", npc_text="PRIVATE_UNSUPPORTED_NPC_HISTORY"),)})
    result, calls = retrieve(situation, [hit()])
    assert result.status == "ok" and result.evidence[0].id == "chunk-1"
    assert result.scope == situation.scope and result.npc_id == situation.npc_id
    assert calls[0]["source"] == "lore/dialogue.txt" and calls[0]["top_k"] == 8  # candidate_k, not top_k
    assert calls[0]["query"] == "Where can I find the healer?"
    assert situation.player_input.text == "Where can I find them?"
    assert "healer" in calls[0]["query"]
    assert "PRIVATE_UNSUPPORTED_NPC_HISTORY" not in calls[0]["query"]
    assert "DO NOT USE" not in result.model_dump_json()


@pytest.mark.parametrize("change", [dict(world_id="another"), dict(game_id="another"), dict(npc_ids=["other-npc"])])
def test_unbound_identity_is_denied_before_network(scenario, change):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    data = config(situation).model_dump()
    data["bindings"][0].update(change)
    result, calls = retrieve(situation, [hit()], settings=RAGConfig.model_validate(data))
    assert result.status == "forbidden" and not result.evidence and not calls


@pytest.mark.parametrize("response,expected", [
    ([], "empty"), ([hit(truncated=True)], "empty"), ([hit(source="secret.txt")], "unavailable"),
    ([hit(distance=float("nan"))], "unavailable"), ([hit(text="")], "unavailable"),
    ([hit(), hit()], "ok"), ([hit()] * 9, "unavailable"),
])
def test_bad_empty_partial_and_duplicate_matches(scenario, response, expected):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    result, _ = retrieve(situation, response)
    assert result.status == expected
    assert len(result.evidence) <= 1


def test_distance_threshold_is_explicit_not_a_confidence_probability(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    result, _ = retrieve(situation, [hit(distance=0.9)], settings=config(situation, max_distance=0.4))
    assert result.status == "empty"


@pytest.mark.parametrize("status", [422, 500, 503])
def test_api_errors_are_typed_unavailable(scenario, status):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    result, _ = retrieve(situation, [], status=status)
    assert result.status == "unavailable"


def test_transport_and_oversized_responses_are_unavailable(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    def disconnected(request):
        raise httpx.ConnectError("offline")
    for handler in [disconnected, lambda r: httpx.Response(200, content=b"x" * 96001)]:
        adapter = HTTPRetriever(config(situation), transport=httpx.MockTransport(handler))
        assert asyncio.run(adapter.retrieve(situation, timeout_s=0.5)).status == "unavailable"


def test_config_rejects_ambiguous_bindings_and_bad_source_paths(scenario, tmp_path):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    data = config(situation).model_dump()
    data["bindings"] *= 2
    with pytest.raises(ValidationError):
        RAGConfig.model_validate(data)
    data = config(situation).model_dump()
    for source in ["../secret", "C:/secret", "/secret", "folder\\secret"]:
        data["bindings"][0]["source"] = source
        with pytest.raises(ValidationError):
            RAGConfig.model_validate(data)
    assert load_retriever(None) is None
    path = tmp_path / "rag.json"
    path.write_text(config(situation).model_dump_json())
    assert load_retriever(path).config == config(situation)


def test_standalone_question_is_not_diluted_by_role_or_scene(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    situation = situation.model_copy(update={"player_input": PlayerInput(text="Who is Mephala?")})
    _, calls = retrieve(situation, [])
    assert calls[0]["query"] == "Who is Mephala?"


def test_dialogue_source_binding_filters_raw_speaker_claims_before_context(scenario):
    from npc.generation.prompt import build_prompt
    from npc.behavior import choose_plan
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    settings = config(situation).model_dump()
    settings["bindings"][0]["source_format"] = "dialogue_export"
    raw = ("FormID: 00000001\tQ\tB\tT\tHELO\t0\tOur friendship ended.\t\t \n"
           "FormID: 00000002\tQ\tB\tT\tHELO\t0\tTaren works the northern forge.\t\t ")
    result, _ = retrieve(situation, [hit(text=raw)], settings=RAGConfig.model_validate(settings))
    assert result.status == "ok" and result.evidence[0].source_kind == "dialogue"
    assert "Our friendship" not in result.evidence[0].text
    prompt = build_prompt(situation, choose_plan(situation), knowledge=result, max_input_bytes=5000)
    assert "Taren works the northern forge." in prompt.messages[1].content
    assert "Our friendship" not in prompt.messages[1].content
    assert result.evidence[0].record_ids == ("00000002:0",)
    assert "00000002" not in prompt.messages[1].content
    entry = json.loads(prompt.messages[1].content)["retrieved_evidence"][0]
    assert entry["speaker"] == "unknown" and entry["conditions"] == "unresolved"
    assert "past NPC claims" in prompt.messages[0].content
    ordinary, _ = retrieve(situation, [hit(text=raw)])
    assert ordinary.evidence[0].text == raw


def test_dialogue_with_no_eligible_reference_is_empty(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    settings = config(situation).model_dump()
    settings["bindings"][0]["source_format"] = "dialogue_export"
    raw = "FormID: 00000001\tQ\tB\tT\tHELO\t0\tHe's my old friend.\t\t "
    result, _ = retrieve(situation, [hit(text=raw)], settings=RAGConfig.model_validate(settings))
    assert result.status == "empty" and not result.evidence


@pytest.mark.parametrize("previous,current,expected", [
    ("tell me about the dragons", "where can i find it", "where can i find the dragons"),
    ("Who is Taren?", "What about him?", "What about Taren?"),
    ("Describe the northern gate.", "Where is that?", "Where is the northern gate?"),
])
def test_followup_retrieval_names_the_topic_without_changing_player_input(scenario, previous, current, expected):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    situation = situation.model_copy(update={"player_input": PlayerInput(text=current), "recent_dialogue": (
        DialogueMemory(request_id="previous", player_text=previous, npc_text="UNVERIFIED_NPC_TEXT"),)})
    _, calls = retrieve(situation, [])
    assert calls[0]["query"] == expected
    assert situation.player_input.text == current
    assert "UNVERIFIED_NPC_TEXT" not in calls[0]["query"]


def test_ambiguous_previous_question_uses_bounded_player_context_without_guessing(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    situation = situation.model_copy(update={"player_input": PlayerInput(text="What about it?"), "recent_dialogue": (
        DialogueMemory(request_id="previous", player_text="Perhaps later.", npc_text="UNVERIFIED_NPC_TEXT"),)})
    _, calls = retrieve(situation, [])
    assert calls[0]["query"] == "What about it?\nPrevious player question: Perhaps later."
