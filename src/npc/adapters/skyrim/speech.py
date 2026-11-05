"""Local Windows speech adapter. No model download, shell interpolation or game logic."""

import asyncio
import json
import os
from pathlib import Path
import subprocess
import tempfile
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from contextlib import asynccontextmanager

from .assets import MAX_WAV_BYTES, wav_duration
from .diagnostics import event as log_event


class SpeechFailure(ValueError):
    pass


class SynthesisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=600)
    voice: dict | None = None  # Native identity metadata; not a file/process argument.
    npc_base: dict | None = None


class WindowsSpeech:
    stt_engine = "Windows SAPI"

    def __init__(self, directory: Path, *, timeout_s=20, launch=asyncio.create_subprocess_exec):
        self.directory = directory
        self.timeout_s = timeout_s
        self.launch = launch
        self.busy = False

    def worker_command(self, operation, request):
        return ["powershell.exe", "-NoProfile", "-NonInteractive", "-File",
                str(Path(__file__).with_name("speech_worker.ps1")), "-RequestPath", str(request)]

    async def _run(self, operation, *, text=None, audio=None):
        if self.busy:
            raise SpeechFailure("speech_busy")
        self.busy = True
        process = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=self.directory) as work:
                work = Path(work)
                command = {"operation": operation}
                if text is not None:
                    command.update(text=text, output=str(work / "output.wav"))
                if audio is not None:
                    (work / "input.wav").write_bytes(audio)
                    command["input"] = str(work / "input.wav")
                request = work / "request.json"
                request.write_text(json.dumps(command), encoding="utf-8")
                process = await self.launch(
                    *self.worker_command(operation, request),
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                try:
                    stdout, _ = await asyncio.wait_for(process.communicate(), self.timeout_s)
                finally:
                    if process.returncode is None:
                        process.kill()
                        await process.wait()
                if process.returncode != 0 or len(stdout) > 16384:
                    raise SpeechFailure("speech_engine_failed")
                result = json.loads(stdout.decode("utf-8-sig"))
                if operation == "tts":
                    with (work / "output.wav").open("rb") as stream:
                        raw = stream.read(MAX_WAV_BYTES + 1)
                    wav_duration(raw)
                    return raw
                if operation == "stt":
                    text, confidence = result.get("text"), result.get("confidence")
                    if (not isinstance(text, str) or not text.strip() or len(text) > 4000
                            or isinstance(confidence, bool) or not isinstance(confidence, (int, float))
                            or not 0 <= confidence <= 1):
                        raise SpeechFailure("invalid_transcript")
                return result
        except TimeoutError:
            raise SpeechFailure("speech_timeout") from None
        except (OSError, json.JSONDecodeError, UnicodeError):
            raise SpeechFailure("speech_engine_unavailable") from None
        finally:
            # Cancellation/timeout cannot leave a speech process or microphone-file reader alive.
            if process is not None and process.returncode is None:
                process.kill()
                await process.wait()
            self.busy = False

    async def synthesize(self, request):
        if not request.text.strip():
            raise SpeechFailure("empty_speech")
        raw = await self._run("tts", text=request.text)
        log_event("TTS_READY", request=request.request_id, engine="Windows SAPI", bytes=len(raw))
        return raw

    async def transcribe(self, raw):
        if wav_duration(raw) > 16:
            raise SpeechFailure("microphone_audio_limit")
        result = await self._run("stt", audio=raw)
        log_event("STT_READY", text=result["text"], confidence=result["confidence"], engine=self.stt_engine)
        return {"text": result["text"], "confidence": result["confidence"]}


class WhisperSpeech(WindowsSpeech):
    """Reuse bounded worker/cleanup; Windows TTS remains opt-in and unchanged."""

    stt_engine = "Whisper base.en CPU INT8"

    def __init__(self, directory, root, **kwargs):
        super().__init__(directory, **kwargs)
        self.root = root

    def worker_command(self, operation, request):
        if operation == "stt":
            return [sys.executable, "-m", "npc.adapters.skyrim.whisper",
                    "--root", str(self.root), "--request", str(request)]
        return super().worker_command(operation, request)


def create_speech_app(engine, *, tts_enabled=True, turbo=None):
    @asynccontextmanager
    async def lifespan(app):
        if turbo:
            await turbo.start()
        try:
            yield
        finally:
            if turbo:
                await turbo.close()
    app = FastAPI(title="Anima local speech", lifespan=lifespan)

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse({"error": "loopback_only"}, status_code=403)
        limit = 16384 if request.url.path.endswith("/tts") else MAX_WAV_BYTES
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > limit:
                return JSONResponse({"error": "speech_payload_too_large"}, status_code=413)
        request._body = bytes(raw)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def failure(request, error):
        log_event("SPEECH_FAILED", operation=request.url.path, error=type(error).__name__)
        return JSONResponse({"error": "speech_unavailable"}, status_code=503)

    @app.get("/health")
    async def health():
        if turbo:
            ready = getattr(turbo, "ready", turbo.process is not None and turbo.process.returncode is None)
            return {"status": "ready" if ready else "degraded",
                    "stt": engine.stt_engine if engine else "external", "tts": "Chatterbox Turbo"}
        if isinstance(engine, WhisperSpeech):
            from .whisper import model_path
            model_path(engine.root)
            voices = (await engine._run("probe")).get("voices", []) if tts_enabled else []
            return {"status": "ready" if not tts_enabled or voices else "degraded",
                    "stt": engine.stt_engine, "tts": "Windows SAPI" if tts_enabled else "disabled"}
        result = await engine._run("probe")
        return {"status": "ready" if result.get("voices") and result.get("recognizers") else "degraded", **result}

    @app.post("/tts")
    async def tts(request: SynthesisInput, http_request: Request):
        if not tts_enabled:
            return JSONResponse({"error": "tts_not_configured"}, status_code=503)
        if turbo:
            from npc.output.chatterbox import TurboRequest
            def key(form):
                if form and form.get("plugin") and form.get("local_id"):
                    if not isinstance(form["plugin"], str) or not isinstance(form["local_id"], str):
                        raise ValueError("invalid voice identity")
                    return f"{form['plugin'].lower()}:{form['local_id'].lower()}"
                return None
            work = asyncio.create_task(turbo.synthesize(TurboRequest(
                request_id=request.request_id, text=request.text,
                voice_key=key(request.voice), npc_key=key(request.npc_base))))
            try:
                # A disconnected bridge must not leave stale GPU work occupying the slot.
                while not work.done():
                    await asyncio.wait({work}, timeout=.1)
                    if await http_request.is_disconnected():
                        raise asyncio.CancelledError()
                raw = await work
                wav_duration(raw)
                log_event("TTS_READY", request=request.request_id, engine="Chatterbox Turbo", bytes=len(raw))
                return Response(raw, media_type="audio/wav")
            except (OSError, TimeoutError):
                raise ValueError("Turbo worker unavailable") from None
            finally:
                if not work.done():
                    work.cancel()
                await asyncio.gather(work, return_exceptions=True)
        return Response(await engine.synthesize(request), media_type="audio/wav")

    @app.post("/stt")
    async def stt(request: Request):
        if engine is None:
            return JSONResponse({"error": "stt_external"}, status_code=503)
        if request.headers.get("content-type", "").split(";")[0] != "audio/wav":
            return JSONResponse({"error": "audio_wav_required"}, status_code=415)
        return await engine.transcribe(await request.body())

    return app
