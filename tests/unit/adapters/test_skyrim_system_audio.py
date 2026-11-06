"""System audio output: voice plays through the OS while the plugin shows a subtitle-only delivery."""

import asyncio
import time

from npc.adapters.skyrim.bridge import Bridge, PLAYBACK_PAD_S
from npc.adapters.skyrim.protocol import PipelineResult, SpeechInput
from tests.unit.adapters.test_skyrim_connector import event, pending, result, settings, wav


class FakeAudio:
    def __init__(self, fail=False):
        self.plays, self.stops, self.fail = [], 0, fail

    def play(self, path):
        self.plays.append((path, path.exists()))
        if self.fail:
            raise OSError("no sound device")

    def stop(self):
        self.stops += 1


def receipt(command, status, sequence):
    return event("delivery", sequence, event_id=f"receipt-{sequence}", delivery_id=command["delivery_id"], status=status)


async def staged(tmp_path, audio, **changes):
    bridge = Bridge(settings(tmp_path, **changes), root=tmp_path, audio=audio)
    bridge.audio_root.mkdir()
    (bridge.audio_root / "r.wav").write_bytes(wav(0.2))
    await pending(bridge)
    await bridge.result(result(audio_path="r.wav"))
    return bridge, bridge.command("session-a")


def playback_files(bridge):
    return list((bridge.output / "speech" / "playback").glob("*.wav"))


def test_system_mode_keeps_game_folder_clean_and_sends_subtitle_command(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged(tmp_path, audio)
        try:
            assert command["audio_file"] is None and command["mouth"]
            assert abs(command["duration_s"] - (0.2 + PLAYBACK_PAD_S)) < 1e-6
            assert not bridge.game.exists() or not list(bridge.game.rglob("*.wav"))
            assert [f.name for f in playback_files(bridge)] == [command["delivery_id"] + ".wav"]
            assert audio.plays == []  # nothing audible before the native start receipt
        finally: await bridge.close()
    asyncio.run(run())


def test_plays_once_on_started_even_with_duplicates(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged(tmp_path, audio)
        try:
            await bridge.game_event(receipt(command, "started", 2))
            await bridge.game_event(receipt(command, "started", 3))
            assert len(audio.plays) == 1 and audio.plays[0][1] is True
        finally: await bridge.close()
    asyncio.run(run())


def test_interrupted_and_failed_stop_and_delete(tmp_path):
    async def run():
        for status in ("interrupted", "failed"):
            audio = FakeAudio()
            bridge, command = await staged(tmp_path / status, audio)
            try:
                await bridge.game_event(receipt(command, "started", 2))
                await bridge.game_event(receipt(command, status, 3))
                assert audio.stops == 1 and not playback_files(bridge)
            finally: await bridge.close()
    asyncio.run(run())


def test_completed_lets_sound_finish_then_deletes(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged(tmp_path, audio)
        try:
            await bridge.game_event(receipt(command, "started", 2))
            await bridge.game_event(receipt(command, "completed", 3))
            assert playback_files(bridge) and audio.stops == 0  # tail of the speech is not cut off
            deadline = time.monotonic() + 3
            while playback_files(bridge) and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
            assert not playback_files(bridge)
        finally: await bridge.close()
    asyncio.run(run())


def test_invalidation_session_end_and_close_stop_and_delete(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged(tmp_path, audio)
        await bridge.game_event(receipt(command, "started", 2))
        bridge.invalidate(bridge.session)  # barge-in
        assert audio.stops == 1 and not playback_files(bridge)
        await bridge.game_event(receipt(command, "started", 3))  # late duplicate must stay silent
        assert len(audio.plays) == 1
        await bridge.close()

        audio = FakeAudio()
        bridge, command = await staged(tmp_path / "end", audio)
        await bridge.game_event(receipt(command, "started", 2))
        await bridge.game_event(event("end", 3))
        assert audio.stops == 1 and not playback_files(bridge)
        await bridge.close()

        audio = FakeAudio()
        bridge, command = await staged(tmp_path / "close", audio)
        await bridge.game_event(receipt(command, "started", 2))
        await bridge.close()
        assert audio.stops == 1 and not playback_files(bridge)
    asyncio.run(run())


def test_new_delivery_stops_previous_sound(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, first = await staged(tmp_path, audio)
        try:
            await bridge.game_event(receipt(first, "started", 2))
            await bridge.game_event(receipt(first, "completed", 3))
            await bridge.player_input(SpeechInput(session_id="session-a", input_id="input-b", text="Again."))
            await bridge.session.turn_task
            await bridge.result(PipelineResult(session_id="session-a", request_id="input-b", npc_id="ref:00013478", text="Good day.", audio_path="r.wav"))
            second = bridge.command("session-a")
            assert audio.stops == 1
            assert [f.name for f in playback_files(bridge)] == [second["delivery_id"] + ".wav"]
        finally: await bridge.close()
    asyncio.run(run())


def test_player_error_never_breaks_turn_or_memory_commit(tmp_path):
    async def run():
        audio = FakeAudio(fail=True)
        bridge, command = await staged(tmp_path, audio)
        try:
            assert (await bridge.game_event(receipt(command, "started", 2)))["status"] == "accepted"
            assert (await bridge.game_event(receipt(command, "completed", 3)))["status"] == "accepted"
            assert bridge.session.delivery_status == "completed"
        finally: await bridge.close()
    asyncio.run(run())


def test_engine_mode_unchanged(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged(tmp_path, audio, audio_output="engine")
        try:
            assert (bridge.game / "Data" / command["audio_file"]).exists()
            assert abs(command["duration_s"] - 0.2) < 1e-6
            await bridge.game_event(receipt(command, "started", 2))
            assert audio.plays == [] and not playback_files(bridge)
        finally: await bridge.close()
    asyncio.run(run())
