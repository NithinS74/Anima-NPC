import asyncio
import importlib.util
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "research/cs3235_paper/experiments/orchestration_study.py"
spec = importlib.util.spec_from_file_location("orchestration_study", PATH)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def test_every_case_labels_every_persona_before_running():
    assert {c[0] for c in study.CASES} and len({c[0] for c in study.CASES}) == len(study.CASES)
    for case in study.CASES:
        assert set(case[4]) == set(study.PERSONAS)
        assert set(case[4].values()) <= {"authored", "generate", "end"}


def test_percentile_uses_nearest_rank():
    assert study.percentile(list(range(1, 101)), 0.95) == 95
    assert study.percentile([7], 0.95) == 7


def test_behaviour_flags_a_wrong_route_as_a_failure(monkeypatch):
    wrong = ("x", "Plain greeting, deliberately mislabelled", "Hello", None, study.GEN)
    monkeypatch.setattr(study, "CASES", [wrong])
    result = study.behaviour()
    assert result["passed"] == 0 and len(result["failures"]) == len(study.PERSONAS)


@pytest.mark.parametrize("name", ["malformed_json", "out_of_character", "fake_citation"])
def test_bad_candidates_are_never_delivered(monkeypatch, name):
    monkeypatch.setattr(study, "FAULTS", {name: study.FAULTS[name]})
    [row] = study.faults(repeats=4)
    assert row["passed"] and row["bad_text_delivered"] == 0 and row["max_calls"] == 2


def test_fault_check_catches_a_candidate_that_was_delivered(monkeypatch):
    # A valid reply listed as a fault must be reported as delivered, or the metric proves nothing.
    text = '{"mode":"speech","text":"Hello there.","cue":null,"evidence_ids":[]}'
    monkeypatch.setattr(study, "FAULTS", {"leak": dict(script=[text], expect="error_fallback")})
    [row] = study.faults(repeats=2)
    assert row["passed"] is False


def test_detection_scores_count_both_error_types():
    scores = study.detection_scores([True, False, True, True], [False, True])
    assert scores["true_positive"] == 3 and scores["false_positive"] == 1
    assert scores["precision"] == 0.75 and scores["recall"] == 0.75


def test_detection_scores_report_no_precision_when_nothing_is_flagged():
    assert study.detection_scores([False], [False])["precision"] is None


def test_detection_reports_misses_and_false_alarms():
    result = study.hostility_detection({"hostile": ["You idiot.", "You stink."], "benign": ["Good morning.", "You moron."]})
    assert result["missed"] == ["You stink."] and result["false_alarms"] == ["You moron."]


def test_pressure_labels_do_not_overlap_hostility_labels():
    data = study.load_hostility()
    assert not set(data["hostile"]) & set(data["benign"])
    assert not set(data["pressure"]) & (set(data["hostile"]) | set(data["benign"]))


def test_player_pressure_detects_a_real_state_change():
    # An insult does change trust, so a zero count from the study means something.
    result = study.player_pressure({"pressure": ["You idiot."]})
    assert result["trust_or_favour_changed"] == result["turns"] == len(study.PERSONAS)


def test_native_provider_needs_no_core_change():
    item = study.scenario("elin", "What keeps you busy these days?")
    provider = study.NativeProtocolProvider(lambda body: {"output_text": study.VALID})
    reply = asyncio.run(study.runner(provider).run(item))
    assert reply.status == "model_success" and reply.model == "native-mock"
