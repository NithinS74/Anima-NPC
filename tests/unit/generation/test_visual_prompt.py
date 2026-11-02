import json
from datetime import datetime, timezone

from npc.behavior import choose_plan
from npc.context import build_situation
from npc.contracts.context import ContextScenario
from npc.generation.prompt import build_prompt
from npc.vision import VisualContext


def test_visual_reference_is_untrusted_user_data_not_a_fact(scenario_data):
    scenario_data["turn"]["facts"] = []
    scenario = ContextScenario.model_validate(scenario_data)
    visual = VisualContext(id="cv-scene", captured_at=datetime.now(timezone.utc), environment="A moonlit road", uncertainties=("Identity unknown",))
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now, visual_context=visual)
    prompt = build_prompt(situation, choose_plan(situation), max_input_bytes=3072)
    assert "not NPC perception or game truth" in prompt.messages[0].content
    data = json.loads(prompt.messages[1].content)
    assert data["untrusted_visual_reference"]["environment"] == "A moonlit road"
    assert all(fact.path != "world.location" for fact in situation.perceived_facts)
    assert situation.visual_context == visual
