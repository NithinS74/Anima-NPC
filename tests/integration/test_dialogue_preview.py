import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("fixture,status,calls", [("smith_closing", "authored_success", 0), ("station_clerk", "model_success", 1), ("smith_available", "model_success", 1)])
def test_offline_cli_exercises_full_preview_chain(fixture, status, calls):
    result = subprocess.run([sys.executable, "-m", "npc.runtime", f"fixtures/scenarios/{fixture}.json"],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == status
    assert data["model_calls"] == calls
    assert data["response"] is not None
    if calls:
        assert data["model"] == "offline-demo"


def test_cli_text_override_is_validated_and_can_take_zero_call_greeting_route():
    result = subprocess.run([sys.executable, "-m", "npc.runtime", "fixtures/scenarios/station_clerk.json", "--text", "Hello"],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0
    assert json.loads(result.stdout)["model_calls"] == 0


def test_live_cli_does_not_make_network_call_when_config_missing(tmp_path):
    result = subprocess.run([sys.executable, "-m", "npc.runtime", "fixtures/scenarios/station_clerk.json", "--live", "--config", str(tmp_path/"missing.yaml")],
                            cwd=ROOT, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert "Configuration error" in result.stderr
    assert not result.stdout
