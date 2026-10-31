import pytest

from npc.behavior import choose_plan
from npc.context import build_situation
from npc.contracts.context import ContextScenario


def plan(data):
    scenario = ContextScenario.model_validate(data)
    return choose_plan(build_situation(scenario.turn, scenario.snapshot, scenario.now))


@pytest.mark.parametrize("text", ["hello", "HI!", "good morning"])
def test_exact_greetings_use_authored_path(scenario_data, text):
    scenario_data["turn"]["facts"] = []
    scenario_data["turn"]["player_input"]["text"] = text
    result = plan(scenario_data)
    assert result.route == "authored"
    assert result.intent == "greet"


def test_greeting_plus_question_is_not_consumed_as_greeting(scenario_data):
    scenario_data["turn"]["facts"] = []
    scenario_data["turn"]["player_input"]["text"] = "Hello, where is the market?"
    result = plan(scenario_data)
    assert result.route == "generate"
    assert result.knowledge_need == "required"


def test_busy_closed_smith_does_not_need_a_model(scenario_data):
    assert plan(scenario_data).route == "authored"
    assert plan(scenario_data).intent == "busy"


def test_combat_ends_without_speech(scenario_data):
    scenario_data["turn"]["facts"][0]["path"] = "npc.in_combat"
    result = plan(scenario_data)
    assert result.route == "end"
    assert result.max_words == 0


def test_transcript_uncertainty_gets_clarification(scenario_data):
    scenario_data["turn"]["player_input"].update(source="stt", confidence=0.2)
    assert plan(scenario_data).intent == "clarify"


def test_guarded_npc_does_not_allow_unbounded_detail(scenario_data):
    scenario_data["turn"]["facts"] = []
    scenario_data["turn"]["player_input"]["text"] = "Explain fully in detail."
    assert plan(scenario_data).max_words == 40
