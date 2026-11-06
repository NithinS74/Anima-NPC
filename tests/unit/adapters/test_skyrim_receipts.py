"""Delivery receipt detail (reason/audio) and revision handling. Offline; no game or provider."""

import asyncio
import logging
import time

import pytest
from pydantic import ValidationError

from npc.adapters.skyrim.bridge import Bridge
from npc.adapters.skyrim.protocol import ActorData, Form, GameEvent, GameSnapshot, Settings, SpeechInput


def form(identifier="00013478", name="Test NPC"):
    return Form(form_id=identifier, local_id=identifier, name=name, plugin="Skyrim.esm")


def event(kind="start", sequence=1, revision=1, sees_player=False, **changes):
    actor = ActorData(reference=form(), base=form("0001347B"), in_combat=False, dead=False,
                      weapon_drawn=False, sees_player=sees_player)
    player = actor.model_copy(update={"reference": form("00000014", "Player")})
    snapshot = GameSnapshot(npc=actor, player=player, hour=12.0, game_days=2.0, interior=True,
                            location=form("00016772", "Whiterun"))
    return GameEvent(kind=kind, sequence=sequence, state_revision=revision, event_id=f"event-{sequence}",
                     session_id="session-a", game_epoch="load-a", game_pid=123,
                     captured_at_ms=int(time.time() * 1000),
                     snapshot=snapshot if kind in {"start", "snapshot"} else None).model_copy(update=changes)


def settings(tmp_path):
    return Settings(game_directory=str(tmp_path / "game"), output_directory=str(tmp_path / "output"),
                    audio_root=str(tmp_path / "audio"), capture_screenshots=False, pipeline_mode="preview")


def bridge_for(tmp_path):
    from npc.generation.provider import OfflineProvider
    from npc.runtime.preview import PreviewRunner
    return Bridge(settings(tmp_path), root=tmp_path, runner=PreviewRunner(OfflineProvider()))


async def staged(bridge):
    await bridge.game_event(event())
    await bridge.session.context_task
    await bridge.player_input(SpeechInput(session_id="session-a", input_id="input-a", text="Hello"))
    await bridge.session.turn_task
    return bridge.command("session-a")


def receipt(sequence, command, status, **extra):
    return event("delivery", sequence, delivery_id=command["delivery_id"], status=status, **extra)


def test_new_receipt_fields_are_validated_and_old_receipts_still_parse():
    old = event("delivery", 2, delivery_id="d", status="completed")
    assert old.reason is None and old.audio is None
    new = event("delivery", 2, delivery_id="d", status="completed", reason="end", audio="ended_early")
    assert (new.reason, new.audio) == ("end", "ended_early")
    assert GameEvent.model_validate_json(new.model_dump_json()).audio == "ended_early"
    for bad in ({"audio": "heard"}, {"reason": "Not A Reason"}, {"reason": "x" * 40}):
        with pytest.raises(ValidationError):
            GameEvent.model_validate({**old.model_dump(mode="json"), **bad})


def test_native_ack_logs_reason_and_audio_and_unreported_for_old_plugins(tmp_path, caplog, monkeypatch):
    from npc.adapters.skyrim.diagnostics import LOGGER
    monkeypatch.setattr(LOGGER, "propagate", False)
    monkeypatch.setattr(LOGGER, "handlers", [caplog.handler])
    caplog.set_level(logging.INFO, logger=LOGGER.name)

    async def run():
        bridge = bridge_for(tmp_path)
        try:
            command = await staged(bridge)
            await bridge.game_event(receipt(2, command, "started"))
            await bridge.game_event(receipt(3, command, "completed", reason="end", audio="ended_early"))
        finally:
            await bridge.close()
    asyncio.run(run())
    acks = [r.getMessage() for r in caplog.records if r.getMessage().startswith("NATIVE_ACK")]
    assert 'reason="unreported"' in acks[0] and 'audio="unreported"' in acks[0]
    assert 'status="completed"' in acks[1] and 'reason="end"' in acks[1] and 'audio="ended_early"' in acks[1]
    assert 'memory_committed="True"' in acks[1]


@pytest.mark.parametrize("audio", ["ended_early", "failed", "full", "none"])
def test_completed_receipt_commits_memory_whatever_the_audio_outcome(tmp_path, audio):
    async def run():
        bridge = bridge_for(tmp_path)
        try:
            command = await staged(bridge)
            key = bridge.session.social_key
            assert bridge.state_store.load(key)["history"] == ()
            await bridge.game_event(receipt(2, command, "completed", reason="end", audio=audio))
            history = bridge.state_store.load(key)["history"]
            assert len(history) == 1 and history[0].source == "game_completed"
        finally:
            await bridge.close()
    asyncio.run(run())


@pytest.mark.parametrize("reason", ["barge_in", "menu_closed", "combat", "actor_lost", "state_changed",
                                    "superseded", "bridge_stop"])
def test_interrupted_receipt_never_commits_memory(tmp_path, reason):
    async def run():
        bridge = bridge_for(tmp_path)
        try:
            command = await staged(bridge)
            key = bridge.session.social_key
            await bridge.game_event(receipt(2, command, "interrupted", reason=reason))
            assert bridge.state_store.load(key)["history"] == ()
        finally:
            await bridge.close()
    asyncio.run(run())


def test_failed_receipt_does_not_commit_memory(tmp_path):
    async def run():
        bridge = bridge_for(tmp_path)
        try:
            command = await staged(bridge)
            key = bridge.session.social_key
            await bridge.game_event(receipt(2, command, "failed", reason="audio_failed", audio="failed"))
            assert bridge.state_store.load(key)["history"] == ()
        finally:
            await bridge.close()
    asyncio.run(run())


def test_same_revision_snapshot_updates_event_without_cancelling_turn_or_delivery(tmp_path):
    async def run():
        bridge = bridge_for(tmp_path)
        try:
            await bridge.game_event(event())
            await bridge.session.context_task
            await bridge.player_input(SpeechInput(session_id="session-a", input_id="input-a", text="Hello"))
            heartbeat = event("snapshot", 2, revision=1, sees_player=True)
            await bridge.game_event(heartbeat)
            assert bridge.session.event is heartbeat and bridge.session.event.snapshot.npc.sees_player is True
            assert bridge.session.request_id == "input-a"
            assert not bridge.session.turn_task.cancelled()
            await bridge.session.turn_task
            command = bridge.command("session-a")
            assert command["kind"] == "speak"
            await bridge.game_event(event("snapshot", 3, revision=1, sees_player=False))
            assert bridge.command("session-a") == command
            assert bridge.session.delivery["kind"] == "speak"
        finally:
            await bridge.close()
    asyncio.run(run())


def test_changed_revision_still_cancels_turn_and_stops_staged_delivery(tmp_path):
    async def run():
        bridge = bridge_for(tmp_path)
        try:
            await bridge.game_event(event())
            await bridge.session.context_task
            await bridge.player_input(SpeechInput(session_id="session-a", input_id="input-a", text="Hello"))
            await bridge.game_event(event("snapshot", 2, revision=2))
            assert bridge.session.request_id is None and bridge.session.inputs["input-a"] == "cancelled"
            await asyncio.gather(bridge.session.turn_task, return_exceptions=True)
            await bridge.player_input(SpeechInput(session_id="session-a", input_id="input-b", text="Hello again"))
            await bridge.session.turn_task
            assert bridge.command("session-a")["kind"] == "speak"
            await bridge.game_event(event("snapshot", 3, revision=3))
            assert bridge.command("session-a")["kind"] == "stop"
        finally:
            await bridge.close()
    asyncio.run(run())
