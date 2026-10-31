import json

import pytest
from pydantic import ValidationError

from npc.context import build_situation
from npc.contracts.context import ContextScenario, ObservedFact, Relationship, Situation


@pytest.mark.parametrize("field,value", [
    ("trust", -101), ("favourability", 101), ("familiarity", -1),
    ("fear", 101), ("irritation", "40"), ("trust", True),
])
def test_relationship_rejects_invalid_scores(field, value):
    with pytest.raises(ValidationError):
        Relationship(**{field: value})


@pytest.mark.parametrize("path,value", [
    ("npc.busy", "false"), ("player.weapon_drawn", 1), ("shop.open", 0),
    ("world.hour", 24), ("world.hour", -1), ("world.hour", True),
    ("world.location", False),
])
def test_known_fact_paths_enforce_value_types(scenario_data, path, value):
    fact = scenario_data["turn"]["facts"][0]
    fact.update(path=path, value=value)
    with pytest.raises(ValidationError):
        ObservedFact.model_validate(fact)


@pytest.mark.parametrize("change", [
    {"ttl_ms": 0}, {"ttl_ms": 60001}, {"confidence": -0.1},
    {"confidence": float("nan")}, {"subject_id": None},
    {"captured_at": "2026-10-31T10:00:00"},
])
def test_observation_rejects_invalid_metadata(scenario_data, change):
    fact = scenario_data["turn"]["facts"][0]
    fact.update(change)
    with pytest.raises(ValidationError):
        ObservedFact.model_validate(fact)


def test_duplicate_observation_ids_rejected(scenario_data):
    scenario_data["turn"]["facts"].append(scenario_data["turn"]["facts"][0])
    with pytest.raises(ValidationError, match="unique"):
        ContextScenario.model_validate(scenario_data)


@pytest.mark.parametrize("version", ["0.2", "1.0", "", 0.1])
def test_unsupported_schema_version_rejected(scenario_data, version):
    scenario_data["turn"]["schema_version"] = version
    with pytest.raises(ValidationError):
        ContextScenario.model_validate(scenario_data)


def test_unexpected_contract_keys_rejected(scenario_data):
    scenario_data["snapshot"]["relationship"]["grant_secrets"] = True
    with pytest.raises(ValidationError):
        ContextScenario.model_validate(scenario_data)


def test_contract_is_frozen_and_json_roundtrips(scenario):
    with pytest.raises(ValidationError):
        scenario.snapshot.relationship.trust = 100
    restored = ContextScenario.model_validate_json(scenario.model_dump_json())
    assert restored == scenario
    assert json.loads(restored.model_dump_json())["turn"]["facts"][0]["value"] is True


def test_bound_fact_count(scenario_data):
    original = scenario_data["turn"]["facts"][0]
    scenario_data["turn"]["facts"] = [dict(original, id=f"f-{i}") for i in range(101)]
    with pytest.raises(ValidationError):
        ContextScenario.model_validate(scenario_data)


def test_payload_byte_limit_even_when_individual_fields_fit(scenario_data):
    original = scenario_data["turn"]["facts"][0]
    perceivers = [str(i).ljust(128, "a") for i in range(32)]
    scenario_data["turn"]["facts"] = [dict(original, id=f"f-{i}", perceivers=perceivers) for i in range(100)]
    with pytest.raises(ValidationError, match="256 KB"):
        ContextScenario.model_validate(scenario_data)


def test_shop_observation_requires_its_service_owner(scenario_data):
    scenario_data["turn"]["facts"][1].pop("subject_id")
    with pytest.raises(ValidationError, match="subject_id"):
        ContextScenario.model_validate(scenario_data)


@pytest.mark.parametrize("change", ["duplicate_field", "wrong_value", "too_many_sources"])
def test_appraisal_dependency_contract_is_consistent_and_bounded(scenario, change):
    result = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    data = result.model_dump(mode="json")
    if change == "duplicate_field":
        data["dependencies"][1] = data["dependencies"][0]
    elif change == "wrong_value":
        data["dependencies"][0]["value"] = "invented-availability"
    else:
        data["dependencies"][0]["source_ids"] = [f"source-{i}" for i in range(5)]
    with pytest.raises(ValidationError):
        Situation.model_validate(data)
