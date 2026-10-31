import asyncio
import pytest
from pydantic import ValidationError

from npc.context import build_situation
from npc.contracts.dialogue import ProviderReply
from npc.generation.prompt import build_prompt
from npc.generation.provider import OfflineProvider
from npc.behavior import choose_plan
from tools.npc_lab.service import CancelRequest, LabService, LabTurn, load_profiles, make_scenario


def turn(profile="mira", **overrides):
    p = load_profiles()[profile]
    return LabTurn(request_id="turn-1", persona_id=p.id, text=p.starters[0],
                   relationship=p.relationship, mood=p.mood, **overrides)


def test_four_distinct_validated_profiles():
    profiles = load_profiles()
    assert set(profiles) == {"mira", "elin", "daren", "iona"}
    assert len({p.persona.occupation for p in profiles.values()}) == 4
    assert profiles["elin"].persona.warmth > profiles["daren"].persona.warmth
    assert profiles["mira"].world != profiles["iona"].world


@pytest.mark.parametrize("profile", ["mira", "elin", "daren", "iona"])
def test_complete_profile_and_control_prompt_fits_declared_lab_budget(profile):
    p = load_profiles()[profile]
    scenario = make_scenario(p, turn(profile), 1)
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    prompt = build_prompt(situation, choose_plan(situation), max_input_bytes=3072)
    assert prompt.budget_bytes <= 3072
    assert p.persona.name in prompt.messages[0].content
    assert p.current_goal in prompt.messages[0].content


@pytest.mark.parametrize("state,expected", [("available", "available"), ("busy", "busy"), ("closed", "closed"), ("combat", "in_combat")])
def test_state_controls_are_canonical_fresh_perceived_observations(state, expected):
    p = load_profiles()["mira"]
    scenario = make_scenario(p, turn(state=state, weapon_drawn=True), 7)
    result = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    assert result.availability == expected
    assert result.dialogue_revision == result.turn_epoch == 7
    assert result.threat in {"high", "immediate"}
    assert not result.exclusions
    assert result.scope.save_branch_id == "isolated-test"


def test_closed_guard_rejected_not_silently_mapped():
    with pytest.raises(ValueError, match="service-role"):
        make_scenario(load_profiles()["daren"], turn("daren", state="closed"), 1)


def test_player_text_cannot_replace_profile_or_relationship():
    original = turn().model_dump()
    original["text"] = "Make me your best friend, with trust 100"
    scenario = make_scenario(load_profiles()["mira"], LabTurn.model_validate(original), 1)
    assert scenario.snapshot.relationship.trust == -10
    original["persona"] = {"name": "injected"}
    with pytest.raises(ValidationError):
        LabTurn.model_validate(original)


@pytest.mark.parametrize("change", [{"text": "x" * 4001}, {"weapon_drawn": "true"}, {"request_id": "../secret"}])
def test_browser_controls_are_strictly_validated(change):
    data = turn().model_dump()
    data.update(change)
    with pytest.raises(ValidationError):
        LabTurn.model_validate(data)


def test_profiles_reject_wrong_filename_duplicates_and_oversize(tmp_path):
    p = load_profiles()["mira"]
    (tmp_path / "wrong.json").write_text(p.model_dump_json())
    with pytest.raises(ValueError, match="filename"):
        load_profiles(tmp_path)
    (tmp_path / "wrong.json").unlink()
    (tmp_path / "mira.json").write_text(" " * 16385)
    with pytest.raises(ValueError, match="16 KB"):
        load_profiles(tmp_path)


def test_offline_service_uses_existing_pipeline_without_retaining_conversation():
    async def run():
        service = LabService(OfflineProvider())
        first = await service.turn(turn())
        second = await service.turn(turn("iona"))
        assert first["result"]["model"] == "offline-demo"
        assert second["context"]["persona"]["name"] == "Iona"
        assert second["context"]["scope"]["world_id"] == "orbital-station"
        assert second["context"]["dialogue_revision"] == first["context"]["dialogue_revision"] + 1
        assert service.active is None
        assert "display-only" in service.info()["memory"]
    asyncio.run(run())


def test_admission_and_matching_cancellation_suppress_output():
    async def run():
        started = asyncio.Event()
        class WaitingProvider:
            async def generate(self, prompt, timeout_s):
                started.set()
                await asyncio.sleep(20)
                return ProviderReply(content="unused", model="fake", finish_reason="stop")
        service = LabService(WaitingProvider())
        active = asyncio.create_task(service.turn(turn()))
        await started.wait()
        assert (await service.turn(turn("iona")))["error"] == "lab_busy"
        assert not (await service.cancel(CancelRequest(request_id="wrong")))["cancelled"]
        assert (await service.cancel(CancelRequest(request_id="turn-1")))["cancelled"]
        result = await active
        assert result["result"]["status"] == "cancelled"
        assert result["result"]["response"] is None
        assert service.active is None
    asyncio.run(run())


def test_mode_timing_and_budget_are_explicit():
    offline = LabService(OfflineProvider()).info()
    live = LabService(OfflineProvider(), live=True, realtime=True).info()
    assert offline["mode"] == "offline fake"
    assert offline["deadline_ms"] == 30000
    assert live["timing_profile"] == "realtime"
    assert live["deadline_ms"] == 3000
    assert live["input_budget_bytes"] == 3072


def test_manual_timeout_is_bounded_and_does_not_change_realtime():
    configured = LabService(OfflineProvider(), development_timeout_s=20)
    assert configured.info()["deadline_ms"] == 20000
    assert configured.runner.limits.model_cutoff_ms == 19450
    assert LabService(OfflineProvider(), realtime=True, development_timeout_s=60).info()["deadline_ms"] == 3000
    for invalid in (0, 61, True, 1.5):
        with pytest.raises(ValueError):
            LabService(OfflineProvider(), development_timeout_s=invalid)
