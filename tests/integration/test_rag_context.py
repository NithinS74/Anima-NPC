import asyncio
import json

import httpx
import pytest

from npc.contracts.context import ContextScenario
from npc.contracts.dialogue import ProviderReply
from npc.contracts.knowledge import KnowledgeContext
from npc.rag.http import HTTPRetriever, RAGConfig
from npc.runtime.preview import PreviewLimits, PreviewRunner


class GroundedProvider:
    def __init__(self, repair=False):
        self.calls = []
        self.repair = repair

    async def generate(self, prompt, timeout_s):
        self.calls.append(prompt)
        if self.repair and len(self.calls) == 1:
            return ProviderReply(content="invalid", model="fake", finish_reason="stop")
        evidence = prompt.evidence
        text = "Try the eastern gate." if evidence else "I do not know."
        body = dict(mode="speech", text=text, cue=None, evidence_ids=[json.loads(prompt.messages[1].content)["retrieved_evidence"][0]["id"]] if evidence else [])
        return ProviderReply(content=json.dumps(body), model="fake", finish_reason="stop")


def generating(data):
    data["turn"]["facts"] = []
    data["turn"]["player_input"]["text"] = "Where is the healer?"
    return ContextScenario.model_validate(data)


@pytest.mark.parametrize("game,world,source", [("fantasy", "village", "fantasy.txt"), ("space", "station", "station.txt")])
def test_source_to_context_to_provider_to_validated_citation_in_two_worlds(scenario_data, game, world, source):
    scenario = generating(scenario_data)
    data = scenario.model_dump()
    for part in [data["turn"], data["snapshot"]]:
        part["scope"].update(game_id=game, world_id=world)
    scenario = ContextScenario.model_validate(data)
    config = RAGConfig(bindings=[dict(game_id=game, world_id=world, npc_ids=[scenario.turn.npc_id], source=source)])
    requests = []
    def handler(request):
        data = json.loads(request.content)
        requests.append(data)
        assert data["source"] == source
        return httpx.Response(200, json=dict(query=data["query"], context="", matches=[dict(
            id="source-revision-chunk", text="The healer works by the eastern gate.", source=source,
            page=None, chunk_index=4, distance=0.2, truncated=False)]))
    provider = GroundedProvider(repair=True)
    retriever = HTTPRetriever(config, transport=httpx.MockTransport(handler))
    result = asyncio.run(PreviewRunner(provider, PreviewLimits(max_input_bytes=10000), retriever=retriever).run(scenario))
    assert result.status == "repair_success" and len(requests) == 1 and len(provider.calls) == 2
    assert result.response.evidence_ids == ("source-revision-chunk",)
    assert result.evidence_used == ("source-revision-chunk",)
    assert result.knowledge.evidence[0].source == source
    for prompt in provider.calls:
        data = json.loads(prompt.messages[1].content)
        assert data["retrieved_evidence"][0]["text"] == "The healer works by the eastern gate."
        assert scenario.snapshot.persona.name in prompt.messages[0].content


class CountingRetriever:
    def __init__(self, status="empty"):
        self.calls = 0
        self.status = status

    async def retrieve(self, situation, *, timeout_s):
        self.calls += 1
        return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status=self.status)


def test_authored_and_combat_skip_retrieval(scenario_data):
    retriever, provider = CountingRetriever(), GroundedProvider()
    runner = PreviewRunner(provider, retriever=retriever)
    assert asyncio.run(runner.run(ContextScenario.model_validate(scenario_data))).status == "authored_success"
    scenario_data["turn"]["facts"][0]["path"] = "npc.in_combat"
    assert asyncio.run(runner.run(ContextScenario.model_validate(scenario_data))).status == "policy_silence"
    assert retriever.calls == 0 and not provider.calls


@pytest.mark.parametrize("status", ["empty", "unavailable", "forbidden"])
def test_missing_knowledge_is_explicit_and_unavailable_never_generates(scenario_data, status):
    retriever, provider = CountingRetriever(status), GroundedProvider()
    result = asyncio.run(PreviewRunner(provider, PreviewLimits(max_input_bytes=10000), retriever=retriever).run(generating(scenario_data)))
    assert result.knowledge.status == status
    assert result.status == ("model_success" if status == "empty" else "error_fallback")
    assert len(provider.calls) == (1 if status == "empty" else 0)
    assert not result.evidence_used


def test_stalled_retrieval_is_bounded_and_cancellable(scenario_data):
    async def run(cancel):
        started = asyncio.Event()
        class Stalled:
            async def retrieve(self, situation, *, timeout_s):
                started.set()
                await asyncio.Event().wait()
        provider = GroundedProvider()
        runner = PreviewRunner(provider, PreviewLimits(retrieval_timeout_ms=20), retriever=Stalled())
        cancellation = asyncio.Event()
        task = asyncio.create_task(runner.run(generating(scenario_data), cancellation=cancellation))
        await started.wait()
        if cancel:
            cancellation.set()
        result = await asyncio.wait_for(task, 0.5)
        assert result.status == ("cancelled" if cancel else "error_fallback")
        if not cancel:
            assert result.error_code == "retrieval_timeout"
        assert not provider.calls
    asyncio.run(run(False))
    asyncio.run(run(True))


def test_lab_uses_same_retrieval_and_exposes_exact_evidence_in_inspector():
    from tools.npc_lab.service import LabService, LabTurn, load_profiles
    profile = load_profiles()["mira"]
    provider, retriever = GroundedProvider(), CountingRetriever()
    service = LabService(provider, retriever=retriever)
    turn = LabTurn(request_id="rag-test", persona_id="mira", text="Where is the healer?",
                   relationship=profile.relationship, mood=profile.mood)
    payload = asyncio.run(service.turn(turn))
    assert payload["result"]["knowledge"]["status"] == "empty"
    assert payload["llm_input"]["calls"][0]["evidence"] == []
    assert payload["llm_input"]["calls"][0]["budget_bytes"] <= 10000
    assert retriever.calls == 1


def test_retrieval_cleanup_retains_admission_until_outstanding_work_settles(scenario_data):
    async def run():
        cleaning, release = asyncio.Event(), asyncio.Event()
        class SlowCleanup:
            async def retrieve(self, situation, *, timeout_s):
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError:
                    cleaning.set()
                    await release.wait()
                    return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status="empty")
        provider = GroundedProvider()
        runner = PreviewRunner(provider, PreviewLimits(retrieval_timeout_ms=20), retriever=SlowCleanup())
        scenario = generating(scenario_data)
        task = asyncio.create_task(runner.run(scenario))
        try:
            await asyncio.wait_for(cleaning.wait(), 0.5)
            result = await asyncio.wait_for(asyncio.shield(task), 0.2)
            assert result.error_code == "retrieval_timeout"
            assert (await runner.run(scenario)).status == "busy"
            assert not provider.calls
        finally:
            release.set()
            await task
            await asyncio.sleep(0)
    asyncio.run(run())


@pytest.mark.parametrize("invalidates", ["state", "deadline"])
def test_retrieval_time_and_state_changes_are_checked_before_generation(scenario_data, invalidates):
    from npc.contracts.dialogue import CurrentState
    clock = [0.0]
    scenario = generating(scenario_data)
    revision = [scenario.snapshot.dialogue_revision]
    class ChangesDuringRetrieval:
        async def retrieve(self, situation, *, timeout_s):
            if invalidates == "state":
                revision[0] += 1
            else:
                clock[0] = 2.6
            return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status="empty")
    provider = GroundedProvider()
    runner = PreviewRunner(provider, retriever=ChangesDuringRetrieval(), clock=lambda: clock[0])
    result = asyncio.run(runner.run(scenario, current_state=lambda: CurrentState(
        dialogue_revision=revision[0], turn_epoch=scenario.snapshot.turn_epoch)))
    assert result.status == ("cancelled" if invalidates == "state" else "error_fallback")
    assert not provider.calls


@pytest.mark.parametrize("corrects", [True, False])
def test_unrelated_boundary_reply_uses_one_repair_without_canned_topic_answers(scenario_data, corrects):
    from npc.contracts.context import DialogueMemory
    scenario = generating(scenario_data)
    data = scenario.model_dump()
    data["snapshot"]["persona"]["boundaries"] = ["never disclose patrol schedules"]
    data["snapshot"]["recent_dialogue"] = [DialogueMemory(request_id="old", player_text="Tell me the patrol schedule.", npc_text="Earlier reply").model_dump()]
    data["turn"]["player_input"]["text"] = "Write me a Python script."
    scenario = ContextScenario.model_validate(data)
    class Replies:
        def __init__(self): self.calls = []
        async def generate(self, prompt, timeout_s):
            self.calls.append(prompt)
            text = "I do not share patrol schedules." if len(self.calls) == 1 or not corrects else "That is beyond what I know."
            return ProviderReply(content=json.dumps(dict(mode="speech", text=text, evidence_ids=[])), model="fake", finish_reason="stop")
    provider = Replies()
    result = asyncio.run(PreviewRunner(provider, PreviewLimits(max_input_bytes=10000), retriever=CountingRetriever()).run(scenario))
    assert result.status == ("repair_success" if corrects else "error_fallback") and result.model_calls == 2
    assert result.response.text == ("That is beyond what I know." if corrects else result.plan.fallback_text)
    assert result.error_code == (None if corrects else "irrelevant_boundary")
    assert "Answer the current topic" in provider.calls[1].messages[0].content
    assert "That is beyond what I know." not in provider.calls[1].messages[0].content
