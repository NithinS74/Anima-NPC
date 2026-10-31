import json
import subprocess
import sys
from pathlib import Path

import pytest

from npc.context import build_situation
from npc.contracts.context import ContextScenario

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("name,availability,recognition", [
    ("smith_closing", "busy", "familiar"),
    ("station_clerk", "available", "stranger"),
])
def test_public_world_scenarios_use_same_context_builder(name, availability, recognition):
    scenario = ContextScenario.model_validate_json((ROOT / "fixtures/scenarios" / f"{name}.json").read_text())
    result = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    assert result.availability == availability
    assert result.recognition == recognition
    assert result.scope == scenario.turn.scope
    assert result.persona == scenario.snapshot.persona


def test_cli_produces_inspectable_context_without_network():
    result = subprocess.run(
        [sys.executable, "-m", "npc.context", "fixtures/scenarios/smith_closing.json"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10,
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["availability"] == "busy"
    assert output["trust_stance"] == "guarded"
    assert "response_text" not in output  # This slice does not fabricate dialogue.


@pytest.mark.parametrize("payload", ["not JSON", '{"private":"sensitive-player-text"}'])
def test_cli_invalid_input_fails_without_echoing_private_data(tmp_path, payload):
    path = tmp_path / "invalid.json"
    path.write_text(payload)
    result = subprocess.run([sys.executable, "-m", "npc.context", str(path)], cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "sensitive-player-text" not in result.stderr
    assert not result.stdout
