"""Per-character voice table and the optional engine `say` output. Offline: no game, Piper or FaceFX needed."""

import asyncio
from pathlib import Path
import subprocess

from npc.adapters.skyrim import say_output
from npc.adapters.skyrim.bridge import Bridge, PLAYBACK_PAD_S
from npc.adapters.skyrim.say_output import next_topic, stage_say, voice_stem
from npc.adapters.skyrim.speech import PiperSpeech, SynthesisInput
from npc.adapters.skyrim.voice_table import VoiceTable, model_key
from tests.unit.adapters.test_skyrim_connector import event, form, result, settings, speech, wav
from tests.unit.adapters.test_skyrim_system_audio import FakeAudio, receipt

HEADER = "name,voice_model,bio,skyrim_voice_folder,race,gender,ref_id,base_id\r\n"
ROWS = [
    ("Amren", "MaleEvenToned", "013BAA", "01A66A"),
    ("Ulfberth War-Bear", "Male Brute", "013B9F", "0D15B0"),
    ("Whiterun Guard", "", "", ""),
    ("Olava the Feeble", "FemaleOldKindly", "013BAE", "01A699"),
    ("Twin", "MaleGuard", "", ""), ("Twin", "FemaleNord", "", ""),
]


def write_table(path, bom=True):
    lines = HEADER + "".join(f'{n},{m},"bio, with comma",x,Nord,Male,{r},{b}\r\n' for n, m, b, r in ROWS)
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + lines.encode("utf-8"))
    return path


def test_voice_table_reads_bom_and_normalises_model_names(tmp_path):
    for bom in (True, False):
        table = VoiceTable(write_table(tmp_path / f"t{bom}.csv", bom))
        found = table.lookup(ref={"plugin": "Skyrim.esm", "local_id": "0001A66A"}, base=None, name="")
        assert found == [("maleeventoned", "voice_table:ref_id")]
        assert table.lookup(ref=None, base={"plugin": "skyrim.esm", "local_id": "00013B9F"}, name="") == [("malebrute", "voice_table:base_id")]
    assert model_key(" Male Even Toned") == "maleeventoned"


def test_voice_table_order_ref_then_base_then_exact_name(tmp_path):
    table = VoiceTable(write_table(tmp_path / "t.csv"))
    found = table.lookup(ref={"plugin": "Skyrim.esm", "local_id": "0001A699"}, base={"plugin": "Skyrim.esm", "local_id": "00013BAE"},
                         name="Olava the Feeble")
    assert [reason for _, reason in found] == ["voice_table:ref_id", "voice_table:base_id", "voice_table:name"]
    assert table.lookup(ref=None, base=None, name="  amren ") == [("maleeventoned", "voice_table:name")]


def test_voice_table_ignores_unvoiced_rows_ambiguous_names_and_modded_ids(tmp_path):
    table = VoiceTable(write_table(tmp_path / "t.csv"))
    assert table.lookup(ref=None, base=None, name="Whiterun Guard") == []   # empty voice_model
    assert table.lookup(ref=None, base=None, name="Twin") == []             # two different models: ambiguous
    assert table.lookup(ref=None, base={"plugin": "SomeMod.esp", "local_id": "00013BAA"}, name="") == []
    assert table.lookup(ref=None, base=None, name="Nobody Known") == []


def test_voice_table_missing_or_broken_file_is_empty(tmp_path):
    assert VoiceTable(tmp_path / "missing.csv").lookup(ref=None, base=None, name="Amren") == []
    assert VoiceTable(None).lookup(ref=None, base=None, name="Amren") == []
    (tmp_path / "bad.csv").write_bytes(b"\xff\xfe\x00bad")
    assert VoiceTable(tmp_path / "bad.csv").lookup(ref=None, base=None, name="Amren") == []


class Resolver:
    def resolve(self, plugin, local_id):
        return {"00013AE6": "maleguard"}.get(local_id)


def candidates(tmp_path, **kwargs):
    engine = PiperSpeech(tmp_path / "s", tmp_path, piper_directory=tmp_path / "p", voice_types=Resolver(), **kwargs)
    available = {"maleguard", "maleeventoned", "malebrute", "femalenord", "malenord"}

    def run():
        base = {"plugin": "Skyrim.esm", "local_id": "00013BAA", "form_id": "00013BAA", "name": "Amren"}
        request = SynthesisInput(request_id="r", text="Hi.", voice={"plugin": "Skyrim.esm", "local_id": "00013AE6"},
                                 npc_base=base, npc_ref={"plugin": "Skyrim.esm", "local_id": "0001A66A", "form_id": "0001A66A", "name": "Amren"},
                                 sex=0)
        return asyncio.run(engine.candidates(request, available))
    return run


def test_candidate_order_override_table_voice_type_same_sex(tmp_path):
    table = VoiceTable(write_table(tmp_path / "t.csv"))
    run = candidates(tmp_path, voice_table=table, voice_overrides={"Skyrim.esm:00013BAA": "Male Brute"})
    assert run() == [("malebrute", "override"), ("maleeventoned", "voice_table:ref_id"), ("maleguard", "voice_type"),
                     ("malenord", "same_sex")]
    plain = candidates(tmp_path)
    assert plain() == [("maleguard", "voice_type"), ("malenord", "same_sex")]  # no table: behaviour unchanged
    unknown = candidates(tmp_path, voice_table=VoiceTable(tmp_path / "nope.csv"))
    assert unknown() == plain()
    named = candidates(tmp_path, voice_overrides={"AMREN": "femalenord"})
    assert named()[0] == ("femalenord", "override")


def test_table_model_without_a_piper_file_is_skipped(tmp_path):
    (tmp_path / "t.csv").write_text(HEADER + "Amren,MaleDoesNotExist,b,x,x,x,01A66A,013BAA\n", encoding="utf-8")
    run = candidates(tmp_path, voice_table=VoiceTable(tmp_path / "t.csv"))
    assert run()[0] == ("maleguard", "voice_type")


# ---- say output ----

def test_topic_alternation_follows_mantella():
    seq, last = [], 0
    for _ in range(5):
        last = next_topic(last)
        seq.append(last)
    assert seq == [1, 2, 1, 2, 1]


def test_voice_file_naming(tmp_path):
    assert voice_stem(1) == "AnimaDialo_AnimaSpeechLine_00000805_1"
    assert voice_stem(2) == "AnimaDialo_AnimaSpeechLine_00000807_1"
    path, lip, seconds = stage_say(wav(0.2), tmp_path, "maleguard", 2, "Hello.")
    assert path == tmp_path / "Data/Sound/Voice/Anima.esp/maleguard/AnimaDialo_AnimaSpeechLine_00000807_1.wav"
    assert path.read_bytes() == wav(0.2) and lip is False and abs(seconds - 0.2) < 1e-6


def test_missing_facefx_writes_no_lip_and_removes_a_stale_one(tmp_path):
    folder = tmp_path / "Data/Sound/Voice/Anima.esp/maleguard"
    folder.mkdir(parents=True)
    stale = folder / (voice_stem(1) + ".lip")
    stale.write_bytes(b"old")
    for directory in ("", str(tmp_path / "no-facefx")):
        _, lip, _ = stage_say(wav(), tmp_path, "maleguard", 1, "Hi.", directory)
        assert lip is False and not stale.exists()


def test_facefx_runs_without_shell_and_writes_lip(tmp_path, monkeypatch):
    tool = tmp_path / "fx"
    tool.mkdir()
    (tool / "FaceFXWrapper.exe").write_bytes(b"x")
    (tool / "FonixData.cdf").write_bytes(b"x")
    calls = []

    def fake(command, **kwargs):
        calls.append((command, kwargs))
        Path(command[6]).write_bytes(b"LIP")
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(say_output.subprocess, "run", fake)
    path, lip, _ = stage_say(wav(), tmp_path, "maleguard", 1, 'Say "no" now', str(tool))
    assert lip and path.with_suffix(".lip").read_bytes() == b"LIP"
    command, kwargs = calls[0]
    assert command[1:3] == ["Skyrim", "USEnglish"] and command[-1] == "Say no now" and not kwargs.get("shell")

    def failing(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(say_output.subprocess, "run", failing)
    _, lip, _ = stage_say(wav(), tmp_path, "maleguard", 1, "Hi.", str(tool))
    assert lip is False and not path.with_suffix(".lip").exists()


def voiced_start():
    source = event()
    npc = source.snapshot.npc.model_copy(update={"voice": form("00013AE6", "Voice")})
    return source.model_copy(update={"snapshot": source.snapshot.model_copy(update={"npc": npc})})


async def staged_say(tmp_path, audio, **changes):
    bridge = Bridge(settings(tmp_path, audio_output="say", **changes), root=tmp_path, audio=audio)
    bridge.voice_types = Resolver()
    bridge.audio_root.mkdir()
    (bridge.audio_root / "r.wav").write_bytes(wav(0.2))
    await bridge.game_event(voiced_start())
    await bridge.session.context_task
    await bridge.player_input(speech())
    await bridge.session.turn_task
    await bridge.result(result(audio_path="r.wav"))
    return bridge, bridge.command("session-a")


def test_say_mode_stages_engine_files_and_a_topic_command(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged_say(tmp_path, audio)
        try:
            assert command["topic_index"] == 1 and command["text"] == "Good day." and command["audio_file"] is None
            assert abs(command["duration_s"] - (0.2 + PLAYBACK_PAD_S)) < 1e-6
            wavs = list((tmp_path / "game/Data/Sound/Voice/Anima.esp/maleguard").glob("*.wav"))
            assert [f.name for f in wavs] == [voice_stem(1) + ".wav"]
            await bridge.game_event(receipt(command, "started", 2))
            assert audio.plays == []  # the engine speaks; system playback stays on standby
        finally:
            await bridge.close()
    asyncio.run(run())


def test_say_unavailable_receipt_falls_back_to_system_audio(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged_say(tmp_path, audio)
        try:
            failed = receipt(command, "failed", 2).model_copy(update={"reason": "say_unavailable"})
            assert (await bridge.game_event(failed))["status"] == "fallback_system"
            again = bridge.command("session-a")
            assert again["kind"] == "speak" and "topic_index" not in again and again["delivery_id"] != command["delivery_id"]
            assert again["text"] == command["text"] and bridge._say_off
            await bridge.game_event(receipt(again, "started", 3))
            assert len(audio.plays) == 1 and audio.plays[0][1] is True
        finally:
            await bridge.close()
    asyncio.run(run())


def test_say_audio_failed_receipt_falls_back_to_system_audio(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge, command = await staged_say(tmp_path, audio)
        try:
            failed = receipt(command, "failed", 2).model_copy(update={"reason": "audio_failed", "audio": "failed"})
            assert (await bridge.game_event(failed))["status"] == "fallback_system"  # the actor never spoke the Say line
            again = bridge.command("session-a")
            assert again["kind"] == "speak" and "topic_index" not in again and bridge._say_off
        finally:
            await bridge.close()
    asyncio.run(run())


def test_say_without_voice_type_uses_system_audio(tmp_path):
    async def run():
        audio = FakeAudio()
        bridge = Bridge(settings(tmp_path, audio_output="say"), root=tmp_path, audio=audio)
        bridge.audio_root.mkdir()
        (bridge.audio_root / "r.wav").write_bytes(wav(0.2))
        await bridge.game_event(event())  # no voice form in the snapshot
        await bridge.session.context_task
        await bridge.player_input(speech())
        await bridge.session.turn_task
        await bridge.result(result(audio_path="r.wav"))
        command = bridge.command("session-a")
        try:
            assert "topic_index" not in command
            await bridge.game_event(receipt(command, "started", 2))
            assert len(audio.plays) == 1 and not (tmp_path / "game/Data/Sound/Voice/Anima.esp").exists()
        finally:
            await bridge.close()
    asyncio.run(run())


def test_topics_alternate_across_turns(tmp_path):
    async def run():
        bridge, command = await staged_say(tmp_path, FakeAudio())
        try:
            first = command["topic_index"]
            await bridge.game_event(receipt(command, "started", 2))
            await bridge.game_event(receipt(command, "completed", 3))
            await bridge.player_input(speech().model_copy(update={"input_id": "input-b"}))
            await bridge.session.turn_task
            await bridge.result(result(audio_path="r.wav").model_copy(update={"request_id": "input-b"}))
            assert [first, bridge.command("session-a")["topic_index"]] == [1, 2]
        finally:
            await bridge.close()
    asyncio.run(run())
