import json
from pathlib import Path

import pytest

from npc.contracts.context import ContextScenario

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"


@pytest.fixture
def scenario_data():
    # Each test receives a fresh mutable input, never a shared model instance.
    return json.loads((FIXTURES / "smith_closing.json").read_text(encoding="utf-8"))


@pytest.fixture
def scenario(scenario_data):
    return ContextScenario.model_validate(scenario_data)
