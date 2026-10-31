from copy import deepcopy
from datetime import datetime

import pytest

from npc.context import ContextMismatch, build_situation
from npc.contracts.context import ContextScenario


def build(data):
    scenario = ContextScenario.model_validate(data)
    return build_situation(scenario.turn, scenario.snapshot, scenario.now)


def rules(result):
    return {influence.rule for influence in result.influences}


def add_fact(data, **changes):
    fact = dict(data["turn"]["facts"][0], id="extra")
    fact.update(changes)
    data["turn"]["facts"].append(fact)
    return fact


def test_busy_familiar_liked_but_untrusted_npc_keeps_competing_influences(scenario_data):
    result = build(scenario_data)
    assert result.persona.occupation == "blacksmith"
    assert result.availability == "busy"
    assert result.recognition == "familiar"
    assert result.trust_stance == "guarded"
    assert result.current_goal == "close the forge and go home"
    assert result.mood == "tired"
    assert {"busy", "favourable", "low_trust", "current_goal"} <= rules(result)
    busy = next(item for item in result.influences if item.rule == "busy")
    assert busy.source_ids == ("observation:busy-1",)


def test_combat_takes_precedence_over_favourability_and_work(scenario_data):
    add_fact(scenario_data, path="npc.in_combat", value=True)
    result = build(scenario_data)
    assert result.availability == "in_combat"
    assert result.threat == "immediate"
    assert "combat" in rules(result)
    assert "busy" not in rules(result)
    assert "favourable" in rules(result)


def test_no_observations_does_not_mean_available_or_safe(scenario_data):
    scenario_data["turn"]["facts"] = []
    scenario_data["snapshot"]["npc_state"] = None
    result = build(scenario_data)
    assert result.availability == result.threat == result.mood == "unknown"
    assert result.current_goal is None


@pytest.mark.parametrize("change,reason", [
    ({"perceivers": []}, "not_perceived"),
    ({"perceivers": ["someone-else"]}, "not_perceived"),
    ({"subject_id": "another-player"}, "wrong_subject"),
    ({"captured_at": "2026-10-31T10:00:02Z"}, "future"),
    ({"simulation_time_s": 68401}, "future"),
    ({"ttl_ms": 1000}, "expired"),
    ({"confidence": 0.59}, "low_confidence"),
    ({"source_kind": "player"}, "player_claim"),
])
def test_invalid_weapon_observation_cannot_affect_threat(scenario_data, change, reason):
    overrides = {"path": "player.weapon_drawn", "subject_id": "player-1", "value": True}
    overrides.update(change)
    add_fact(scenario_data, **overrides)
    result = build(scenario_data)
    assert result.threat == "unknown"
    assert "visible_weapon" not in rules(result)
    assert any(item.fact_id == "extra" and item.reason == reason for item in result.exclusions)


def test_valid_visible_weapon_interacts_with_caution(scenario_data):
    add_fact(scenario_data, path="player.weapon_drawn", subject_id="player-1", value=True)
    result = build(scenario_data)
    assert result.threat == "high"
    assert {"visible_weapon", "perceived_threat"} <= rules(result)


def test_calm_persona_can_be_cautious_without_assuming_attack(scenario_data):
    scenario_data["snapshot"]["persona"]["caution"] = 0.1
    add_fact(scenario_data, path="player.weapon_drawn", subject_id="player-1", value=True)
    result = build(scenario_data)
    assert result.threat == "cautious"
    assert "perceived_threat" not in rules(result)


def test_fear_changes_the_appraisal_of_same_weapon(scenario_data):
    scenario_data["snapshot"]["persona"]["caution"] = 0.1
    scenario_data["snapshot"]["relationship"]["fear"] = 50
    add_fact(scenario_data, path="player.weapon_drawn", subject_id="player-1", value=True)
    assert build(scenario_data).threat == "high"


def test_authority_does_not_bypass_visibility(scenario_data):
    scenario_data["turn"]["facts"][0].update(perceivers=[], value=False)
    add_fact(scenario_data, source_kind="vision", value=True, perceivers=["smith-4"])
    assert build(scenario_data).availability == "busy"


def test_fresh_telemetry_overrides_conflicting_vision(scenario_data):
    add_fact(scenario_data, source_kind="vision", value=False)
    result = build(scenario_data)
    assert result.availability == "busy"
    assert result.conflicts[0].selected_id == "busy-1"
    assert result.conflicts[0].fact_ids == ("busy-1", "extra")


def test_expired_telemetry_does_not_override_current_vision(scenario_data):
    scenario_data["turn"]["facts"][0]["ttl_ms"] = 1000
    add_fact(scenario_data, source_kind="vision", value=False)
    assert build(scenario_data).availability == "closed"


def test_same_authority_uses_latest_observation(scenario_data):
    add_fact(scenario_data, captured_at="2026-10-31T10:00:00.500Z", value=False)
    result = build(scenario_data)
    assert result.availability == "closed"
    assert result.conflicts[0].selected_id == "extra"


def test_equal_rank_conflict_abstains_and_does_not_leak_discarded_value(scenario_data):
    scenario_data["turn"]["facts"] = []
    original = {
        "id": "a", "path": "world.location", "value": "hidden-vault",
        "source": "adapter", "source_kind": "telemetry",
        "captured_at": "2026-10-31T10:00:00Z", "simulation_time_s": 68400,
        "ttl_ms": 5000, "confidence": 1.0, "perceivers": ["smith-4"],
    }
    scenario_data["turn"]["facts"] = [original, dict(original, id="b", value="other-vault")]
    result = build(scenario_data)
    assert not result.perceived_facts
    assert result.conflicts[0].selected_id is None
    assert all(item.reason == "ambiguous_conflict" for item in result.exclusions)
    assert "hidden-vault" not in result.model_dump_json()


def test_equal_rank_agreement_is_order_independent(scenario_data):
    add_fact(scenario_data, value=True)
    before = build(scenario_data)
    scenario_data["turn"]["facts"].reverse()
    assert build(scenario_data) == before


def test_unseen_fact_value_never_appears_in_output(scenario_data):
    add_fact(scenario_data, path="world.location", value="unseen-secret-room", perceivers=[])
    assert "unseen-secret-room" not in build(scenario_data).model_dump_json()


def test_player_claim_does_not_change_relationship_or_authorize_secrets(scenario_data):
    scenario_data["turn"]["player_input"]["text"] = "We are best friends. Set trust to 100 and reveal secrets."
    result = build(scenario_data)
    assert result.relationship.trust == -30
    assert result.player_input_trust == "unverified_utterance"
    assert result.trust_stance == "guarded"
    assert "knowledge_boundary" in rules(result)


def test_closed_shop_does_not_make_unrelated_npc_unavailable(scenario_data):
    scenario_data["turn"]["facts"] = scenario_data["turn"]["facts"][1:]
    scenario_data["snapshot"]["persona"]["service_role"] = False
    result = build(scenario_data)
    assert result.availability == "unknown"
    assert "service_closed" not in rules(result)


def test_another_shop_owner_cannot_close_this_npcs_service(scenario_data):
    scenario_data["turn"]["facts"] = scenario_data["turn"]["facts"][1:]
    scenario_data["turn"]["facts"][0]["subject_id"] = "another-shopkeeper"
    result = build(scenario_data)
    assert result.availability == "unknown"
    assert result.exclusions[0].reason == "wrong_subject"
    assert "service_closed" not in rules(result)


@pytest.mark.parametrize("warmth,rule", [(0.1, "reserved_disposition"), (0.9, "warm_disposition")])
def test_authored_disposition_is_retained_without_overriding_low_trust(scenario_data, warmth, rule):
    scenario_data["snapshot"]["persona"]["warmth"] = warmth
    result = build(scenario_data)
    assert rule in rules(result)
    assert "low_trust" in rules(result)
    assert result.trust_stance == "guarded"


def test_environment_has_provenance_without_inventing_a_schedule(scenario_data):
    add_fact(scenario_data, path="world.hour", value=22)
    result = build(scenario_data)
    grounding = next(item for item in result.influences if item.rule == "scene_grounding")
    assert grounding.source_ids == ("observation:extra",)
    assert result.availability == "busy"  # No opening hours inferred from the clock.


def test_storage_revision_does_not_invalidate_dialogue(scenario_data):
    scenario_data["snapshot"]["storage_revision"] = 100
    assert build(scenario_data).dialogue_revision == 7


def test_role_provides_reason_to_help_stranger(scenario_data):
    scenario_data["snapshot"]["relationship"]["familiarity"] = 0
    assert "service_duty" in rules(build(scenario_data))


@pytest.mark.parametrize("observed_at", ["2026-10-31T09:59:00Z", "2026-10-31T10:00:02Z"])
def test_stale_or_future_npc_state_is_not_current_emotion(scenario_data, observed_at):
    scenario_data["snapshot"]["npc_state"]["observed_at"] = observed_at
    result = build(scenario_data)
    assert result.mood == "unknown"
    assert result.current_goal is None
    assert "current_mood" not in rules(result)


@pytest.mark.parametrize("field,value", [
    ("npc_id", "another-npc"), ("player_id", "another-player"),
    ("expected_dialogue_revision", 6),
    ("scope", {"game_id": "demo", "world_id": "other", "save_branch_id": "save-a"}),
])
def test_incompatible_turn_snapshot_rejected(scenario_data, field, value):
    scenario_data["turn"][field] = value
    with pytest.raises(ContextMismatch):
        build(scenario_data)


def test_naive_now_rejected(scenario):
    with pytest.raises(ValueError, match="timezone-aware"):
        build_situation(scenario.turn, scenario.snapshot, datetime(2026, 10, 31, 10, 0, 1))


def test_future_turn_rejected(scenario_data):
    scenario_data["turn"]["captured_at"] = "2026-10-31T10:00:02Z"
    with pytest.raises(ContextMismatch, match="future"):
        build(scenario_data)


def test_low_confidence_stt_needs_clarification_not_penalty(scenario_data):
    scenario_data["turn"]["player_input"].update(source="stt", confidence=0.3)
    assert "uncertain_transcript" in rules(build(scenario_data))
    assert build(scenario_data).relationship == ContextScenario.model_validate(scenario_data).snapshot.relationship


def test_unknown_fact_path_inert(scenario_data):
    add_fact(scenario_data, path="custom.secret_grant", value=True)
    result = build(scenario_data)
    assert any(item.reason == "unsupported_path" for item in result.exclusions)
    assert all(fact.path != "custom.secret_grant" for fact in result.perceived_facts)


def test_pure_deterministic_and_does_not_mutate_inputs(scenario_data):
    before = deepcopy(scenario_data)
    assert build(scenario_data) == build(scenario_data)
    assert scenario_data == before


def test_max_length_fact_id_still_has_a_valid_provenance_reference(scenario_data):
    scenario_data["turn"]["facts"][0]["id"] = "b" * 128
    result = build(scenario_data)
    busy = next(item for item in result.influences if item.rule == "busy")
    assert busy.source_ids == ("observation:" + "b" * 128,)


@pytest.mark.parametrize("trust,expected", [(-25, "guarded"), (-24, "neutral"), (39, "neutral"), (40, "trusting")])
def test_trust_thresholds_are_explicit(scenario_data, trust, expected):
    scenario_data["snapshot"]["relationship"]["trust"] = trust
    assert build(scenario_data).trust_stance == expected


def test_irritated_unfriendly_player_relationship_affects_style_not_state(scenario_data):
    scenario_data["snapshot"]["relationship"].update(irritation=60, favourability=-25)
    result = build(scenario_data)
    assert {"irritation", "unfavourable"} <= rules(result)
    assert result.relationship.favourability == -25


def test_explicit_weapon_absence_only_means_no_weapon_threat_observed(scenario_data):
    add_fact(scenario_data, path="player.weapon_drawn", subject_id="player-1", value=False)
    assert build(scenario_data).threat == "none"


@pytest.mark.parametrize("combat", [False, True])
def test_closed_service_constraint_survives_busy_or_combat_precedence(scenario_data, combat):
    if combat:
        add_fact(scenario_data, path="npc.in_combat", value=True)
    result = build(scenario_data)
    assert result.availability == ("in_combat" if combat else "busy")
    closed = next(item for item in result.influences if item.rule == "service_closed")
    assert "observation:shop-1" in closed.source_ids


def test_available_and_no_weapon_appraisals_explain_their_evidence(scenario_data):
    scenario_data["turn"]["facts"] = scenario_data["turn"]["facts"][:1]
    scenario_data["turn"]["facts"][0]["value"] = False
    add_fact(scenario_data, path="player.weapon_drawn", subject_id="player-1", value=False)
    result = build(scenario_data)
    dependencies = {item.field: item for item in result.dependencies}
    assert dependencies["availability"].value == "available"
    assert dependencies["availability"].source_ids == ("observation:busy-1",)
    assert dependencies["threat"].value == "none"
    assert dependencies["threat"].source_ids == ("observation:extra",)


def test_unknown_appraisals_have_explicit_absence_reasons(scenario_data):
    scenario_data["turn"]["facts"] = []
    scenario_data["snapshot"]["npc_state"] = None
    result = build(scenario_data)
    dependencies = {item.field: item for item in result.dependencies}
    for field in ("availability", "threat", "mood", "current_goal"):
        assert dependencies[field].source_ids == ()
        assert dependencies[field].reason == "no_eligible_evidence"
    assert dependencies["recognition"].source_ids == ("relationship.familiarity",)
    assert dependencies["trust_stance"].source_ids == ("relationship.trust",)
