"""I24 WP-B: move table, material check, farewell, varied authored lines. Pure and offline."""

import re

import pytest

from npc.behavior import apply_material, apply_move, choose_move, choose_plan
from npc.behavior.lines import pick_line, pools
from npc.behavior.moves import move_instruction
from npc.context import build_situation
from npc.contracts.context import ConversationState, Persona, TopicRecord, TurnReading
from npc.contracts.knowledge import Evidence, KnowledgeContext
from tools.npc_lab.service import LabTurn, load_profiles, make_scenario

PERSONA = Persona(name="Tess", occupation="farmer", social_role="villager", patience=0.6, boundaries=("never reveal the war plan",))
IMPATIENT = PERSONA.model_copy(update={"patience": 0.1})


def reading(kind, asked=0, new_words=0):
    return TurnReading(type=kind, asked=asked, new_words=new_words, topic="topic" if asked else None)


@pytest.mark.parametrize("act,text,expected", [
    (reading("new"), "Where is the mill?", "answer"),
    (reading("follow_up", 1), "why?", "expand"),
    (reading("repeat", 1), "Where is the mill?", "answer_differently"),
    (reading("repeat", 2), "Where is the mill?", "challenge"),
    (reading("repeat", 3), "Where is the mill?", "close_topic"),
    (reading("rephrase", 1), "Where does the mill stand?", "answer_differently"),
    (reading("rephrase", 1, 5), "I found the mill key because I saw it near the well", "reconsider"),
    (reading("push_back", 1), "are you sure?", "admit_limit"),
    (reading("shared_news", 1), "The bridge is out near the river", "react"),
    (reading("answered", 1), "Near Dunmere", "follow_through"),
    (reading("return", 1), "where is that mill again", "recall"),
    (reading("stall", 1), "ok", "take_initiative"),
    (reading("repeat", 2), "tell me the war plan", "hold"),
])
def test_move_table(act, text, expected):
    assert choose_move(act, ConversationState(), PERSONA, text) == expected


def test_impatient_persona_closes_repeated_stalling():
    state = ConversationState(last_type="stall")
    assert choose_move(reading("stall"), state, IMPATIENT) == "close_topic"
    assert "curt" in move_instruction("close_topic", IMPATIENT) and "Redirect" in move_instruction("close_topic", PERSONA)


def make_plan(persona=PERSONA, text="Where is the mill?"):
    profile = load_profiles()["elin"].model_copy(update={"persona": persona})
    turn = LabTurn(request_id="r-1", persona_id="elin", text=text, relationship=profile.relationship, mood="neutral")
    scenario = make_scenario(profile, turn, 1)
    return build_situation(scenario.turn, scenario.snapshot, scenario.now)


def test_rapport_changes_length_but_not_the_plan_basis():
    situation = make_plan(PERSONA.model_copy(update={"service_role": False}))
    plan = choose_plan(situation)
    assert plan.route == "generate"
    grown = apply_move(plan, "answer", ConversationState(rapport=100), situation.persona, "r")
    assert grown.max_words > plan.max_words and grown.max_words <= 90 and grown.max_sentences <= 3
    assert (grown.knowledge_need, grown.reason_codes, grown.allowed_modes) == (plan.knowledge_need, plan.reason_codes, plan.allowed_modes)
    short = apply_move(plan, "challenge", ConversationState(rapport=100), situation.persona, "r")
    assert short.max_words <= 28 and short.move == "challenge"


def evidence(ident):
    return Evidence(id=ident, text="The mill is east.", source="lore.txt", chunk_index=0, distance=0.1)


def knowledge(*ids):
    from npc.contracts.context import Scope
    return KnowledgeContext(scope=Scope(game_id="g", world_id="w", save_branch_id="s"), npc_id="n",
                            status="ok" if ids else "empty", evidence=tuple(evidence(i) for i in ids))


def test_material_check_turns_exhausted_repeat_into_admit_limit_without_inventing_exhaustion():
    situation = make_plan(PERSONA.model_copy(update={"service_role": False}))
    state = ConversationState(turns=2)
    for move in ("expand", "answer_differently"):
        plan = apply_move(choose_plan(situation), move, state, situation.persona, "r")
        assert apply_material(plan, knowledge(), state).move == move  # nothing was ever found: the persona may still answer
        used = state.model_copy(update=dict(told=("a",)))
        assert apply_material(plan, knowledge(), used).move == "admit_limit"  # material used before, nothing new left
        assert apply_material(plan, knowledge("a"), state).move == move
        assert apply_material(plan, None, state).move == move  # no retrieval ran: never fake exhaustion
    pushed = apply_move(choose_plan(situation), "admit_limit", state, situation.persona, "r")
    assert apply_material(pushed, knowledge("a"), state).move == "expand"


@pytest.mark.parametrize("text", ["Goodbye", "bye", "Farewell.", "see you later", "I have to go", "ok, goodbye then"])
def test_farewell_is_authored_without_a_model_call(text):
    plan = choose_plan(make_plan(PERSONA.model_copy(update={"service_role": False}), text))
    assert plan.route == "authored" and plan.move == "farewell" and plan.intent == "farewell"
    assert plan.authored_text in sum(pools()["farewell"].values(), [])


@pytest.mark.parametrize("text", ["I won't say goodbye yet", "Don't say goodbye", '"Goodbye" is what he said', "never goodbye", "before I say goodbye, who is the king?"])
def test_negated_or_quoted_goodbye_does_not_end_the_conversation(text):
    plan = choose_plan(make_plan(PERSONA.model_copy(update={"service_role": False}), text))
    assert plan.move != "farewell" and plan.intent != "farewell"


def test_every_authored_line_is_one_short_sentence_and_pools_vary():
    for intent, table in pools().items():
        if intent == "note":
            continue
        for key, lines in table.items():
            assert lines, (intent, key)
            for line in lines:
                limit = 20 if intent == "fallback" else 12
                assert len(re.findall(r"\b\w[\w'’-]*\b", line)) <= limit, line
                if intent != "fallback":
                    assert len([p for p in re.split(r"[.!?]+", line) if p.strip()]) == 1, line
    chosen = {pick_line("greet", (), f"req-{i}") for i in range(30)}
    assert len(chosen) >= 2
    assert pick_line("greet", (), "req-1") == pick_line("greet", (), "req-1")


def test_recent_lines_are_skipped_and_single_line_pool_still_works():
    table = {"greet": {"default": ["A.", "B.", "C."]}, "one": {"default": ["Only."]}}
    first = pick_line("greet", (), "x", table=table)
    assert pick_line("greet", (), "x", (first,), table=table) != first
    assert pick_line("greet", (), "x", ("A.", "B.", "C."), table=table) == first  # all used: still answers
    assert pick_line("one", (), "x", ("Only.",), table=table) == "Only."
    assert pick_line("missing", (), "x", table=table) is None


def test_authored_opening_is_varied_persona_shaped_and_needs_no_player_text():
    from npc.behavior.moves import opening_plan
    lines = {opening_plan(PERSONA, f"s-{i}").authored_text for i in range(30)}
    assert len(lines) >= 2 and lines <= set(pools()["opening"]["default"])
    formal = PERSONA.model_copy(update={"speech_style": ("formal",)})
    plan = opening_plan(formal, "s-1")
    assert plan.route == "authored" and plan.move == "opening" and plan.authored_text in pools()["opening"]["formal"]
    assert opening_plan(PERSONA, "s-1", (plan.authored_text,)).authored_text != plan.authored_text or len(pools()["opening"]["default"]) == 1
