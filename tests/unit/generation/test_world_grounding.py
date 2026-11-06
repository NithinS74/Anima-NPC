"""I24 WP-B: common knowledge, location and services reach the prompt, within the byte budget. Offline."""

import json
from pathlib import Path

import pytest

from npc.behavior import apply_move, choose_plan
from npc.context import build_situation
from npc.contracts.context import ConversationState, Persona
from npc.generation.prompt import build_prompt
from tools.npc_lab.service import LabTurn, load_profiles, make_scenario

ROOT = Path(__file__).resolve().parents[3]


def situation_for(persona_id="mira", text="What is Skyrim and where are you?", persona=None):
    profile = load_profiles()[persona_id]
    if persona is not None:  # a compact stand-in with no observations, as a lean connector turn would be
        profile = profile.model_copy(update={"persona": persona, "current_goal": "work"})
    turn = LabTurn(request_id="r-1", persona_id=persona_id, text=text, relationship=profile.relationship, mood="neutral")
    scenario = make_scenario(profile, turn, 1)
    if persona is not None:
        scenario = scenario.model_copy(update={"turn": scenario.turn.model_copy(update={"facts": ()})})
    return build_situation(scenario.turn, scenario.snapshot, scenario.now)


@pytest.mark.parametrize("pid", ["mira", "elin", "daren", "iona"])
def test_lab_personas_give_location_and_common_knowledge_within_3072(pid):
    sit = situation_for(pid)
    plan = choose_plan(sit)
    assert plan.route == "generate"
    prompt = build_prompt(sit, plan, max_input_bytes=3072)
    system, data = prompt.messages[0].content, json.loads(prompt.messages[1].content)
    assert prompt.budget_bytes <= 3072
    assert sit.persona.location in system
    assert data.get("common_knowledge")
    assert "real-world topics" in system and "no external lore" in system


def test_village_personas_know_skyrim_but_iona_answers_for_her_station_only():
    for pid in ("mira", "elin", "daren"):
        assert any("Skyrim" in line for line in load_profiles()[pid].persona.common_knowledge)
    iona = load_profiles()["iona"].persona
    text = " ".join(iona.common_knowledge + (iona.location or "",))
    assert "Skyrim" not in text and "station" in text.casefold()


def test_mira_may_take_work_but_stays_curt():
    mira = load_profiles()["mira"].persona
    assert not any("eager assistance" in b for b in mira.boundaries) and mira.services
    sit = situation_for("mira", "Can you make me a sword?")
    system = build_prompt(sit, choose_plan(sit), max_input_bytes=3072).messages[0].content
    assert "normal business" in system and "cannot hand over items" in system
    assert "forge and repair weapons" in system


def small_persona(common=6, long=True):
    return Persona(name="Tess", occupation="farmer", social_role="villager", location="Tess farm near the hills",
                   services=("sell eggs and barley",),
                   common_knowledge=tuple((f"Common fact number {i} that any local would plainly know." if long else f"Fact {i}.") for i in range(common)))


def test_ordinary_turn_with_world_fields_fits_the_default_2048():
    sit = situation_for("elin", persona=small_persona(2, long=False))
    plan = apply_move(choose_plan(sit), "answer", ConversationState(), sit.persona, "r")
    prompt = build_prompt(sit, plan, max_input_bytes=2048)
    assert prompt.budget_bytes <= 2048 and json.loads(prompt.messages[1].content)["common_knowledge"]
    assert "sell eggs" in prompt.messages[0].content and "Tess farm" in prompt.messages[0].content


def test_common_knowledge_is_trimmed_before_the_move_instruction_and_services_stay():
    sit = situation_for("elin", persona=small_persona(6))
    plan = apply_move(choose_plan(sit), "challenge", ConversationState(turns=3, last_type="repeat"), sit.persona, "r")
    roomy = build_prompt(sit, plan, max_input_bytes=4000)
    tight = build_prompt(sit, plan, max_input_bytes=2300)
    assert len(json.loads(roomy.messages[1].content)["common_knowledge"]) == 6
    kept = json.loads(tight.messages[1].content).get("common_knowledge", [])
    assert len(kept) < 6 and "common_knowledge" in tight.sections_dropped
    assert "MOVE:" in tight.messages[0].content and "sell eggs" in tight.messages[0].content


def test_no_game_specific_strings_in_core_prompt_or_policy_code():
    for name in ("generation/prompt.py", "behavior/moves.py", "behavior/policy.py", "behavior/lines.py", "context/conversation.py"):
        assert "skyrim" not in (ROOT / "src/npc" / name).read_text(encoding="utf-8").casefold(), name


def test_real_world_topics_are_not_supplied_as_knowledge():
    for profile in load_profiles().values():
        text = " ".join(profile.persona.common_knowledge).casefold()
        assert "python" not in text and "france" not in text


def test_conversation_brief_move_and_sections_fit_the_default_2048_without_prompt_too_large():
    from npc.contracts.context import TurnReading
    sit = situation_for("elin", persona=small_persona(0))
    conv = ConversationState(turns=4, rapport=40, replies=("Folk say the Jarls squabble.",), phrases=("folk say the jarls",),
                             claims=("I came from Dunmere",), last_move="answer")
    sit = sit.model_copy(update={"conversation": conv, "reading": TurnReading(type="repeat", topic="Who rules?", asked=2)})
    plan = apply_move(choose_plan(sit), "challenge", conv, sit.persona, "r")
    prompt = build_prompt(sit, plan, max_input_bytes=2048)
    assert prompt.budget_bytes <= 2048
    assert json.loads(prompt.messages[1].content)["conversation_brief"]["type"] == "repeat"
    assert "MOVE:" in prompt.messages[0].content
