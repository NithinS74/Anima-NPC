import asyncio
import io
import json
import struct
import wave
from pathlib import Path

import pytest

from npc.generation.provider import OfflineProvider
from tools.npc_lab.media import LabMedia, MediaFailure, MediaSettings, validate_wav
from tools.npc_lab.service import CancelRequest, LabService, LabTurn, load_profiles
from tools.npc_lab.setup_assets import copy_piper


def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(22050)
        wav.writeframes(b"\x00\x00" * 2205)
    return buffer.getvalue()


def glb_bytes(data=None):
    payload = json.dumps(data or {"asset": {"version": "2.0"}}).encode()
    payload += b" " * (-len(payload) % 4)
    return struct.pack("<4sIIII", b"glTF", 2, 20 + len(payload), len(payload), 0x4E4F534A) + payload


@pytest.fixture
def media(tmp_path):
    settings = MediaSettings(piper_directory="assets/private/npc_lab/piper", voices={"mira": "femaleeventoned"},
                             models={"mira": "assets/private/npc_lab/models/mira.glb"})
    media = LabMedia(tmp_path, settings=settings, timeout_s=0.03)
    models = media.piper / "models/skyrim/low"; models.mkdir(parents=True)
    (media.piper / "piper.exe").write_bytes(b"fake, never executed")
    (models / "femaleeventoned.onnx").write_bytes(b"fake")
    (models / "femaleeventoned.onnx.json").write_text("{}")
    return media


def test_missing_media_is_explicit_and_paths_are_not_exposed(media):
    info = media.describe("mira")
    assert info == {"voice_available": True, "voice": "femaleeventoned", "model_url": None, "appearance_source": None,
                    "scene": "mira", "scene_label": "The forge", "scene_url": "/scenes/mira.svg"}
    assert not media.describe("absent")["voice_available"]
    assert str(media.root) not in json.dumps(info)


def test_scenes_use_fixed_known_roles_and_unknown_ids_fall_back(media):
    assert [media.describe(id)["scene"] for id in ("mira", "elin", "daren", "iona")] == ["mira", "elin", "daren", "iona"]
    assert media.describe("unrecognized")["scene"] == "default"


def test_real_game_scene_is_bounded_and_preferred_to_illustration(media):
    image = b"\xff\xd8\xff\xc0\x00\x0b\x08\x02\x58\x03\x20\x01\x01\x11\x00\xff\xd9"
    folder = media.private / "scenes"; folder.mkdir(parents=True)
    (folder / "mira.jpg").write_bytes(image)
    assert media.scene_bytes("mira") == image
    assert media.describe("mira")["scene_url"] == "/api/scenes/mira.jpg"
    with pytest.raises(MediaFailure): media.scene_bytes("../../.env")
    (folder / "mira.jpg").write_bytes(b"not a screenshot")
    assert media.scene_url("mira") == "/scenes/mira.svg"


def test_optional_game_fonts_are_bounded_and_never_arbitrary_paths(media):
    assert not media.game_fonts_ready()
    folder = media.private / "fonts"; folder.mkdir(parents=True)
    valid = b"\x00\x01\x00\x00" + struct.pack(">H", 1) + b"\x00" * 22
    for name in ("FuturaCondensedLight.ttf", "FuturaCondensed.ttf"):
        (folder / name).write_bytes(valid)
    assert media.game_fonts_ready()
    assert media.font_bytes("dialogue") == valid
    with pytest.raises(MediaFailure): media.font_bytes("../../.env")
    (folder / "FuturaCondensedLight.ttf").write_bytes(b"invalid font")
    assert not media.game_fonts_ready()


def test_configured_media_cannot_escape_private_asset_root(tmp_path):
    settings = MediaSettings(piper_directory=".env", voices={}, models={})
    with pytest.raises(ValueError, match="private"):
        LabMedia(tmp_path, settings=settings)


def test_valid_self_contained_glb_is_served_by_profile_id(media):
    path = media.private / "models/mira.glb"; path.parent.mkdir(); path.write_bytes(glb_bytes())
    assert media.model_path("mira") == path
    assert media.describe("mira")["model_url"] == "/api/models/mira.glb"
    assert media.model_bytes("mira") == path.read_bytes()


@pytest.mark.parametrize("payload", [b"not a model", glb_bytes({"asset":{"version":"2.0"},"images":[{"uri":"https://example.org/private.png"}]}), glb_bytes({"asset":{"version":"1.0"}})])
def test_malformed_or_external_model_is_unavailable(media, payload):
    path = media.private / "models/mira.glb"; path.parent.mkdir(); path.write_bytes(payload)
    assert media.model_path("mira") is None
    with pytest.raises(MediaFailure, match="model_unavailable"):
        media.model_bytes("mira")


def test_oversize_model_fails_without_loading_entire_file(media):
    path = media.private / "models/mira.glb"; path.parent.mkdir()
    with path.open("wb") as file:
        file.write(glb_bytes()); file.truncate(33 * 1024 * 1024)
    assert media.model_path("mira") is None


@pytest.mark.parametrize("raw", [b"", b"x" * 100, wav_bytes()[:-20], b"x" * (2 * 1024 * 1024 + 1)])
def test_invalid_audio_rejected(raw):
    with pytest.raises(MediaFailure, match="invalid_audio"):
        validate_wav(raw)


def test_valid_audio_accepted():
    validate_wav(wav_bytes())


class Process:
    def __init__(self, work, block=None):
        self.work, self.block, self.returncode = Path(work), block, None
        self.commands = None; self.killed = False

    async def communicate(self, commands):
        self.commands = commands
        if self.block:
            await self.block.wait()
        (self.work / "out.wav").write_bytes(wav_bytes())
        self.returncode = 0
        return None, None

    def kill(self):
        self.killed = True; self.returncode = -1

    async def wait(self):
        return self.returncode


def test_voice_uses_no_shell_and_normalizes_command_injection(media, monkeypatch):
    calls = []
    async def create(*args, **kwargs):
        process = Process(kwargs["cwd"]); calls.append((args, kwargs, process)); return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    result = asyncio.run(media.synthesize("r-1", "mira", "Hello\nexit\r\nload_model evil\x00"))
    assert result == wav_bytes()
    args, kwargs, process = calls[0]
    assert args == (str(media.piper / "piper.exe"),)
    lines = process.commands.decode().splitlines()
    assert len(lines) == 3
    assert lines[1] == "synthesize Hello exit load_model evil"
    assert lines[2] == "exit"
    assert kwargs["stdout"] == kwargs["stderr"] == asyncio.subprocess.DEVNULL
    assert not Path(kwargs["cwd"]).exists()


def test_voice_timeout_kills_process_and_cleans_up(media, monkeypatch):
    calls = []
    async def create(*args, **kwargs):
        process = Process(kwargs["cwd"], asyncio.Event()); calls.append(process); return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    with pytest.raises(MediaFailure, match="voice_timeout"):
        asyncio.run(media.synthesize("r-1", "mira", "Hello"))
    assert calls[0].killed
    assert not calls[0].work.exists()
    assert media.active is None


def test_voice_admission_and_cancellation_are_bounded(media, monkeypatch):
    async def run():
        started = asyncio.Event(); calls = []
        async def create(*args, **kwargs):
            process = Process(kwargs["cwd"], asyncio.Event()); calls.append(process); started.set(); return process
        monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
        task = asyncio.create_task(media.synthesize("r-1", "mira", "Hello"))
        await started.wait()
        with pytest.raises(MediaFailure, match="voice_busy"):
            await media.synthesize("r-2", "mira", "Other")
        assert not await media.cancel("wrong")
        assert await media.cancel("r-1")
        with pytest.raises(MediaFailure, match="speech_cancelled"):
            await task
        assert len(calls) == 1 and calls[0].killed
    asyncio.run(run())


def test_missing_voice_and_oversize_text_do_not_start_process(media):
    with pytest.raises(MediaFailure, match="voice_unavailable"):
        asyncio.run(media.synthesize("r", "missing", "Hello"))
    with pytest.raises(MediaFailure, match="speech_text_limit"):
        asyncio.run(media.synthesize("r", "mira", "x" * 601))


def test_only_recorded_validated_text_reaches_voice_and_cache_is_bounded():
    class FakeMedia:
        def __init__(self): self.calls = []
        async def synthesize(self, request_id, persona_id, text): self.calls.append((persona_id, text)); return b"voice"
        async def cancel(self, request_id): return False
    async def run():
        voice = FakeMedia(); service = LabService(OfflineProvider(), media=voice)
        with pytest.raises(ValueError): await service.speech(CancelRequest(request_id="unrecorded"))
        p = load_profiles()["mira"]
        for i in range(10):
            await service.turn(LabTurn(request_id=f"r-{i}", persona_id="mira", text="How is work?", relationship=p.relationship, mood=p.mood))
        assert len(service.speech_records) == 8
        assert await service.speech(CancelRequest(request_id="r-9")) == b"voice"
        assert voice.calls == [("mira", "Work keeps me occupied, as usual.")]
        await service.cancel(CancelRequest(request_id="r-9"))
        with pytest.raises(ValueError): await service.speech(CancelRequest(request_id="r-9"))
    asyncio.run(run())


def test_copy_installed_runtime_retains_license_and_selected_models(media, tmp_path):
    source = media.piper
    (source / "LICENSE.md").write_text("test license")
    (source / "espeak-ng-data").mkdir(); (source / "espeak-ng-data/data").write_text("test")
    target = tmp_path / "copy"
    copy_piper(source, target, ["femaleeventoned"])
    assert (target / "LICENSE.md").read_text() == "test license"
    assert (target / "models/skyrim/low/femaleeventoned.onnx").read_bytes() == b"fake"
    assert (source / "piper.exe").exists()
