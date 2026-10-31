"""Local-only lab models and Mantella Piper protocol; independent of NPC core."""

import asyncio
import io
import json
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Annotated

from pydantic import Field, StringConstraints

from npc.contracts.context import Contract
from tools.npc_lab.service import ROOT

Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,31}$", strict=True)]
Voice = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]{1,64}$", strict=True)]
MAX_MODEL_BYTES = 32 * 1024 * 1024
MAX_WAV_BYTES = 2 * 1024 * 1024
SCENES = {"mira": "The forge", "elin": "The inn", "daren": "The village gate", "iona": "The registry"}


class MediaSettings(Contract):
    piper_directory: str
    voices: Annotated[dict[Slug, Voice], Field(max_length=16)]
    models: Annotated[dict[Slug, str], Field(max_length=16)]
    appearance_sources: Annotated[dict[Slug, str], Field(max_length=16)] = Field(default_factory=dict)


class MediaFailure(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def validate_glb_header(header: bytes, size: int, json_bytes: bytes):
    if len(header) != 20 or not 20 < size <= MAX_MODEL_BYTES:
        raise ValueError("invalid model")
    magic, version, length, chunk_length, chunk_type = struct.unpack("<4sIIII", header)
    if magic != b"glTF" or version != 2 or length != size or chunk_type != 0x4E4F534A:
        raise ValueError("invalid GLB")
    if not 1 <= chunk_length <= 2 * 1024 * 1024 or chunk_length != len(json_bytes) or 20 + chunk_length > size:
        raise ValueError("invalid JSON chunk")
    data = json.loads(json_bytes)
    # Self-contained GLB only: no external file/network texture or buffer fetches.
    if any("uri" in item for key in ("buffers", "images") for item in data.get(key, [])):
        raise ValueError("external GLB resource")
    if data.get("asset", {}).get("version") != "2.0":
        raise ValueError("invalid glTF version")


def validate_wav(raw: bytes):
    if not 44 < len(raw) <= MAX_WAV_BYTES:
        raise MediaFailure("invalid_audio")
    try:
        with wave.open(io.BytesIO(raw), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            if not 0 < duration <= 30 or audio.getnchannels() not in (1, 2) or audio.getsampwidth() != 2:
                raise MediaFailure("invalid_audio")
            expected = audio.getnframes() * audio.getnchannels() * audio.getsampwidth()
            if len(audio.readframes(audio.getnframes())) != expected:
                raise MediaFailure("invalid_audio")
    except (wave.Error, EOFError, ZeroDivisionError):
        raise MediaFailure("invalid_audio") from None


class LabMedia:
    def __init__(self, root: Path = ROOT, *, timeout_s=10, settings: MediaSettings | None = None):
        self.root = root.resolve()
        self.private = (self.root / "assets/private/npc_lab").resolve()
        if settings is None:
            path = self.root / "configs/npc_lab/media.json"
            if path.stat().st_size > 16384:
                raise ValueError("media config exceeds 16 KB")
            settings = MediaSettings.model_validate_json(path.read_text(encoding="utf-8"))
        self.settings = settings
        self.piper = self._private_path(settings.piper_directory)
        self.timeout_s = timeout_s
        self._voice_lock = asyncio.Lock()
        self.active: tuple[str, asyncio.Task] | None = None

    def _private_path(self, relative: str):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.private):
            raise ValueError("media must remain within the private lab asset directory")
        return path

    def voice_ready(self, persona_id):
        voice = self.settings.voices.get(persona_id)
        return bool(voice and (self.piper / "piper.exe").is_file()
                    and (self.piper / "models/skyrim/low" / f"{voice}.onnx").is_file()
                    and (self.piper / "models/skyrim/low" / f"{voice}.onnx.json").is_file())

    def model_path(self, persona_id):
        try:
            relative = self.settings.models[persona_id]
            path = self._private_path(relative)
            size = path.stat().st_size
            with path.open("rb") as stream:
                header = stream.read(20)
                chunk_length = struct.unpack("<I", header[12:16])[0] if len(header) == 20 else 0
                if not 1 <= chunk_length <= 2 * 1024 * 1024:
                    return None
                validate_glb_header(header, size, stream.read(chunk_length))
            return path
        except (OSError, KeyError, ValueError, TypeError, AttributeError, RecursionError, struct.error):
            return None

    def model_bytes(self, persona_id):
        path = self.model_path(persona_id)
        if path is None:
            raise MediaFailure("model_unavailable")
        with path.open("rb") as stream:
            raw = stream.read(MAX_MODEL_BYTES + 1)
        chunk_length = struct.unpack("<I", raw[12:16])[0]
        validate_glb_header(raw[:20], len(raw), raw[20:20 + chunk_length])
        return raw

    def describe(self, persona_id):
        return dict(voice_available=self.voice_ready(persona_id), voice=self.settings.voices.get(persona_id),
                    model_url=f"/api/models/{persona_id}.glb" if self.model_path(persona_id) else None,
                    appearance_source=self.settings.appearance_sources.get(persona_id),
                    scene=persona_id if persona_id in SCENES else "default", scene_label=SCENES.get(persona_id, "A place between stories"))

    def font_bytes(self, kind):
        filenames = {"dialogue": "FuturaCondensedLight.ttf", "interface": "FuturaCondensed.ttf"}
        if kind not in filenames:
            raise MediaFailure("font_unavailable")
        try:
            path = self._private_path("assets/private/npc_lab/fonts/" + filenames[kind])
            with path.open("rb") as stream:
                raw = stream.read(2 * 1024 * 1024 + 1)
            if not 28 <= len(raw) <= 2 * 1024 * 1024 or raw[:4] not in {b"\x00\x01\x00\x00", b"OTTO"}:
                raise ValueError("invalid font")
            count = struct.unpack(">H", raw[4:6])[0]
            if not 1 <= count <= 128 or 12 + 16 * count > len(raw):
                raise ValueError("invalid font directory")
            return raw
        except (OSError, ValueError):
            raise MediaFailure("font_unavailable") from None

    def game_fonts_ready(self):
        try:
            self.font_bytes("dialogue"); self.font_bytes("interface")
            return True
        except MediaFailure:
            return False

    def background_bytes(self):
        path = self.private / "background/skyrim-stone.png"
        try:
            with path.open("rb") as stream:
                raw = stream.read(8 * 1024 * 1024 + 1)
            if not 24 < len(raw) <= 8 * 1024 * 1024 or raw[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("invalid background")
            width, height = struct.unpack(">II", raw[16:24])
            if not (1 <= width <= 2048 and 1 <= height <= 2048):
                raise ValueError("background dimensions")
            return raw
        except (OSError, ValueError):
            raise MediaFailure("background_unavailable") from None

    def background_url(self):
        try:
            self.background_bytes()
            return "/api/background/skyrim.png"
        except MediaFailure:
            return None

    async def cancel(self, request_id):
        if self.active is not None and self.active[0] == request_id:
            self.active[1].cancel()
            return True
        return False

    async def synthesize(self, request_id: str, persona_id: str, text: str):
        if self._voice_lock.locked():
            raise MediaFailure("voice_busy")
        if not self.voice_ready(persona_id):
            raise MediaFailure("voice_unavailable")
        # The executable has a line-oriented command protocol. Player/model text
        # must never introduce another command line or terminal control bytes.
        text = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        if not text or len(text) > 600:
            raise MediaFailure("speech_text_limit")
        async with self._voice_lock:
            self.active = (request_id, asyncio.current_task())
            try:
                return await self._synthesize(persona_id, text)
            except asyncio.CancelledError:
                raise MediaFailure("speech_cancelled") from None
            finally:
                self.active = None

    async def _synthesize(self, persona_id, text):
        model = self.piper / "models/skyrim/low" / f"{self.settings.voices[persona_id]}.onnx"
        if any(c in str(model) for c in "\r\n\x00"):
            raise MediaFailure("invalid_voice_path")
        work_root = self.root / "output/npc_lab/tts"
        work_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_root) as work:
            process = None
            try:
                process = await asyncio.create_subprocess_exec(
                    str(self.piper / "piper.exe"), cwd=work,
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    env={**os.environ, "OMP_NUM_THREADS": "1"},
                )
                command = f"load_model {model}\nsynthesize {text}\nexit\n".encode("utf-8")
                await asyncio.wait_for(process.communicate(command), timeout=self.timeout_s)
                if process.returncode != 0:
                    raise MediaFailure("voice_process_failed")
                path = Path(work) / "out.wav"
                with path.open("rb") as stream:
                    raw = stream.read(MAX_WAV_BYTES + 1)
                validate_wav(raw)
                return raw
            except TimeoutError:
                raise MediaFailure("voice_timeout") from None
            except (OSError, ValueError):
                raise MediaFailure("voice_process_failed") from None
            finally:
                if process is not None and process.returncode is None:
                    process.kill()
                    await process.wait()
