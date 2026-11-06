"""I24 WP-B: scripted multi-turn conversations with fake models and retrievers. Offline."""

import asyncio
import json
import time

import httpx

from npc.behavior import apply_move, choose_move, choose_plan
from npc.context import build_situation
from npc.context.conversation import read_turn
from npc.contracts.context import ConversationState, PlayerInput, Scope, TopicRecord
from npc.contracts.dialogue import ProviderReply
from npc.contracts.knowledge import Evidence, KnowledgeContext
from npc.generation.prompt import build_prompt
from npc.rag.config import RAGConfig
from npc.rag.http import HTTPRetriever
from npc.runtime.preview import PreviewLimits, PreviewRunner
from npc.state.social_store import SocialStore
from tools.npc_lab.service import LabTurn, load_profiles, make_scenario

QUESTION = "Who is the king of Skyrim?"


def reply(text, evidence=()):
    return json.dumps({"mode": "speech", "text": text, "cue": None, "evidence_ids": list(evidence)})


class Provider:
    def __init__(self, *texts):
        self.texts, self.prompts = list(texts), []

    async def generate(self, prompt, timeout_s):
        self.prompts.append(prompt)
        return ProviderReply(content=self.texts.pop(0), model="fake", finish_reason="stop", input_tokens=1, output_tokens=1)


class Retriever:
    def __init__(self, *ids):
        self.ids, self.calls = ids, 0

    async def retrieve(self, situation, *, timeout_s):
        self.calls += 1
        hits = tuple(Evidence(id=i, text=f"Passage {i} about the king.", source="lore.txt", chunk_index=n, distance=0.1)
                     for n, i in enumerate(self.ids))
        return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status="ok", evidence=hits)


class Rig:
    def __init__(self, tmp_path, provider, retriever=None, persona="elin", limits=None):
        self.store = SocialStore(tmp_path / "s.sqlite3", clock=lambda: 1000.0)
        self.profile = load_profiles()[persona]
        self.key = self.store.key(Scope(game_id="manual-lab", world_id=self.profile.world, save_branch_id="b"), "lab-" + persona, "p")
        self.store.ensure(self.key, self.profile.relationship, self.profile.mood)
        self.runner = PreviewRunner(provider, limits or PreviewLimits(max_input_bytes=8000), retriever=retriever)
        self.n = 0

    def ask(self, text=QUESTION, display=True):
        self.n += 1
        rid = f"t{self.n}"
        state, audit, _ = self.store.begin_turn(self.key, rid, PlayerInput(text=text), self.profile.persona,
                                                self.store.load(self.key)["revision"])
        turn = LabTurn(request_id=rid, persona_id=self.profile.id, text=text, relationship=state["relationship"], mood=state["mood"])
        scenario = make_scenario(self.profile, turn, state["revision"], state["history"], state["conversation"], state["reading"])
        result = asyncio.run(self.runner.run(scenario))
        if result.response:
            self.store.stage_preview(self.key, rid, {"result": result.model_dump(mode="json")}, state["revision"],
                                     evidence_ids=result.response.evidence_ids or result.evidence_used)
            if display:
                self.store.displayed(self.key, rid)
        return result


def test_same_question_four_times_changes_move_prompt_and_reply(tmp_path):
    provider = Provider(reply("Folk say the High King is dead and the Jarls squabble."), reply("Ask me again and I would still point at the Jarls."),
                        reply("Why do you keep pressing about thrones, stranger?"), reply("Enough of crowns; talk of something else."))
    rig = Rig(tmp_path, provider)
    results = [rig.ask() for _ in range(4)]
    assert [r.plan.move for r in results] == ["answer", "answer_differently", "challenge", "close_topic"]
    assert [r.turn_type for r in results] == ["new", "repeat", "repeat", "repeat"]
    systems = [p.messages[0].content for p in provider.prompts]
    users = [p.messages[1].content for p in provider.prompts]
    assert len(set(zip(systems, users))) == 4
    assert systems[1] != systems[2] != systems[3]
    assert "MOVE:" not in systems[0] and "MOVE:" in systems[3]
    assert json.loads(users[3])["conversation_brief"]["asked"] == 3


def test_repeated_reply_is_rejected_then_repaired_within_two_calls(tmp_path):
    same = "The crown sits far from our little village, friend."
    provider = Provider(reply(same), reply(same), reply("Ask the guards; they hear more of the court than I do."))
    rig = Rig(tmp_path, provider)
    assert rig.ask().model_calls == 1
    second = rig.ask()
    assert second.status == "repair_success" and second.model_calls == 2 and "repeated_reply" in second.violations
    assert "repeated_reply" in provider.prompts[2].messages[0].content


def test_two_repeats_in_a_row_use_a_fallback_without_a_third_call(tmp_path):
    same = "The crown sits far from our little village, friend."
    provider = Provider(reply(same), reply(same), reply(same))
    rig = Rig(tmp_path, provider)
    rig.ask()
    third = rig.ask()
    assert third.model_calls == 2 and third.status == "error_fallback" and len(provider.prompts) == 3
    assert third.response.text != same


def test_interrupted_reply_leaves_the_next_turn_new(tmp_path):
    provider = Provider(reply("It is a long story about the crown, traveller."), reply("Different words about the crown entirely."))
    rig = Rig(tmp_path, provider)
    rig.ask(display=False)
    again = rig.ask()
    assert again.turn_type == "new" and again.plan.move == "answer"


def test_told_passages_are_not_offered_again_and_exhaustion_admits_the_limit(tmp_path):
    provider = Provider(reply("The king is spoken of in lore.", ["kb1", "kb2"]), reply("I have nothing more to add on that matter, friend."))
    rig = Rig(tmp_path, provider, Retriever("p1", "p2"))
    first = rig.ask()
    assert first.evidence_used == ("p1", "p2")
    second = rig.ask()
    assert second.evidence_used == () and second.plan.move == "admit_limit"
    assert second.knowledge.status == "empty"
    assert json.loads(provider.prompts[1].messages[1].content)["knowledge_status"] == "empty"
    assert "nothing more" in provider.prompts[1].messages[0].content


def test_repetition_never_unlocks_restricted_knowledge_or_trust(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(500)

    config = RAGConfig.model_validate(dict(bindings=[dict(game_id="manual-lab", world_id="village", npc_ids=["someone-else"], source="lore.txt")]))
    provider = Provider()
    rig = Rig(tmp_path, provider, HTTPRetriever(config, transport=httpx.MockTransport(handler)))
    before = rig.store.load(rig.key)["relationship"]
    results = [rig.ask() for _ in range(6)]
    assert not calls and not provider.prompts  # unbound NPC: no retrieval and no model call, however often it is asked
    assert all(r.knowledge.status == "forbidden" and r.evidence_used == () for r in results)
    after = rig.store.load(rig.key)["relationship"]
    assert (after.trust, after.favourability) == (before.trust, before.favourability)


def test_added_processing_time_stays_under_30ms_per_turn():
    profile = load_profiles()["elin"]
    topics = tuple(TopicRecord(text=f"topic about subject{i} and thing{i}", asked=2, last_turn=i) for i in range(16))
    conv = ConversationState(turns=20, topics=topics, told=("a",), replies=("An earlier reply here.",) * 4,
                             claims=("I came from Dunmere",) * 8, phrases=("well i would say",) * 8, rapport=60)
    turn = LabTurn(request_id="r", persona_id="elin", text=QUESTION, relationship=profile.relationship, mood="neutral")
    total = 0.0
    for _ in range(20):
        began = time.perf_counter()
        reading = read_turn(turn.text, conv)
        scenario = make_scenario(profile, turn, 1, (), conv, reading)
        situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
        plan = apply_move(choose_plan(situation), choose_move(reading, conv, situation.persona, turn.text), conv, situation.persona, "r")
        build_prompt(situation, plan, max_input_bytes=8000)
        total += time.perf_counter() - began
    assert total / 20 < 0.030
