"""One-player connection lifecycle, independent of model and game implementation."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid
from collections import deque

import httpx

from .assets import Artifacts, MAX_WAV_BYTES, mouth_envelope, read_audio, stage_audio, wav_duration
from .protocol import GameEvent, NpcProfile, PipelineResult, Settings, SpeechInput, canonical_scenario, npc_id, profile_for
from .windows import Microphone, capture_client


class ConnectionError(ValueError):
    pass


@dataclass
class Session:
    event: GameEvent
    revision: int = 0
    last_sequence: int = 0
    request_id: str | None = None
    deadline: float = 0
    delivery: dict | None = None
    delivery_status: str | None = None
    inputs: dict = field(default_factory=dict)
    events: set = field(default_factory=set)
    screenshot: dict | None = None
    context_task: asyncio.Task | None = None
    turn_task: asyncio.Task | None = None


class Bridge:
    def __init__(self, settings: Settings, *, root: Path, capture=capture_client,
                 client: httpx.AsyncClient | None = None, runner=None, microphone=None, clock=time.time):
        self.settings, self.root = settings, root.resolve()
        self.output = self.resolve(settings.output_directory)
        self.game = self.resolve(settings.game_directory)
        self.audio_root = self.resolve(settings.audio_root)
        self.artifacts = Artifacts(self.output, max_bytes=settings.max_output_bytes,
                                   max_screenshots=settings.max_screenshots, capture=capture)
        self.profiles = {}
        if settings.profiles_file:
            path = self.resolve(settings.profiles_file)
            if path.stat().st_size > 128 * 1024:
                raise ValueError("profiles exceed 128 KB")
            raw = json.loads(path.read_text(encoding="utf-8"))
            if len(raw) > 256:
                raise ValueError("too many NPC profiles")
            self.profiles = {key.lower(): NpcProfile.model_validate(value) for key, value in raw.items()}
        if settings.pipeline_mode == "http" and not settings.pipeline_url:
            raise ValueError("pipeline_url is required in HTTP mode")
        self.client = client or httpx.AsyncClient(timeout=settings.timeout_s, trust_env=False,
                                                 limits=httpx.Limits(max_connections=3))
        self.runner = runner
        self.microphone = microphone or Microphone(self.output / "microphone")
        self.session: Session | None = None
        self.ended = deque(maxlen=16)
        self.clock = clock
        self.error: str | None = None
        self._background: set[asyncio.Task] = set()
        self._microphone_task: asyncio.Task | None = None
        self._mic_gate = asyncio.Lock()

    def resolve(self, value):
        path = Path(value)
        return (path if path.is_absolute() else self.root / path).resolve()

    def spawn(self, coroutine):
        if len(self._background) >= 8:
            coroutine.close()
            raise ConnectionError("connector worker admission exhausted")
        task = asyncio.create_task(coroutine)
        self._background.add(task)

        def settled(done):
            self._background.discard(done)
            if not done.cancelled() and done.exception() is not None:
                self.error = type(done.exception()).__name__

        task.add_done_callback(settled)
        return task

    async def close(self):
        for task in tuple(self._background):
            task.cancel()
        await asyncio.gather(*self._background, return_exceptions=True)
        await asyncio.to_thread(self.microphone.discard)
        await self.client.aclose()

    def current(self, session_id):
        if self.session is None or self.session.event.session_id != session_id:
            raise ConnectionError("unknown or ended session")
        return self.session

    def invalidate(self, session):
        if session.turn_task and not session.turn_task.done():
            session.turn_task.cancel()
        if session.request_id:
            session.inputs[session.request_id] = "cancelled"
        session.request_id = None
        if session.delivery and session.delivery_status not in {"completed", "interrupted", "failed"}:
            session.delivery = {**session.delivery, "kind": "stop"}

    async def game_event(self, event: GameEvent):
        if event.session_id in self.ended:
            if event.kind == "end":
                return {"status": "duplicate"}
            raise ConnectionError("session already ended; open a new conversation")
        if event.kind == "start":
            if not event.snapshot:
                raise ConnectionError("start requires snapshot")
            if self.session and self.session.event.session_id == event.session_id:
                if event.event_id in self.session.events:
                    return {"status": "duplicate"}
                raise ConnectionError("session already started")
            if self.session:
                await self.end(self.session)
            session = Session(event=event, revision=event.state_revision, last_sequence=event.sequence)
            session.events.add(event.event_id)
            self.session = session
            session.context_task = self.spawn(self.publish_context(session, "context_ready"))
            return {"status": "ready", "npc_id": npc_id(event.snapshot)}
        session = self.current(event.session_id)
        if event.game_epoch != session.event.game_epoch:
            raise ConnectionError("game epoch mismatch")
        if event.event_id in session.events:
            return {"status": "duplicate"}
        if event.sequence <= session.last_sequence:
            raise ConnectionError("out of order game event")
        if len(session.events) >= 4096:
            raise ConnectionError("session event limit reached; start a new conversation")
        if event.kind == "snapshot":
            if not event.snapshot or npc_id(event.snapshot) != npc_id(session.event.snapshot):
                raise ConnectionError("snapshot actor mismatch")
            if event.state_revision < session.revision:
                raise ConnectionError("out of order state revision")
            changed = event.state_revision != session.revision
            if changed:
                self.invalidate(session)
                session.revision = event.state_revision
            session.event = event
            # Coalesce context notifications while a bounded capture/HTTP operation runs.
            if changed and (not session.context_task or session.context_task.done()):
                session.context_task = self.spawn(self.publish_context(session, "context_updated"))
        elif event.kind == "end":
            await self.end(session)
        elif event.kind == "delivery":
            if not session.delivery or event.delivery_id != session.delivery["delivery_id"] or not event.status:
                raise ConnectionError("unknown delivery")
            if session.delivery_status in {"completed", "interrupted", "failed"}:
                session.events.add(event.event_id)
                session.last_sequence = event.sequence
                return {"status": session.delivery_status}
            session.delivery_status = event.status
            if event.status in {"completed", "interrupted", "failed"}:
                self._remove_staged_audio(session)
            self.spawn(self.publish({"kind": "delivery", "session_id": event.session_id,
                                "delivery_id": event.delivery_id, "request_id": session.delivery["request_id"],
                                "status": event.status, "heard_text": None}))
        elif event.kind == "listen_start":
            if not self.settings.stt_url:
                self.error = "stt_not_configured"
            elif self._microphone_task and not self._microphone_task.done():
                raise ConnectionError("microphone busy")
            else:
                self._microphone_task = self.spawn(self.listen(session))
        elif event.kind == "listen_stop":
            self.spawn(self.finish_listening(session))
        session.events.add(event.event_id)
        session.last_sequence = event.sequence
        return {"status": "accepted"}

    def _remove_staged_audio(self, session):
        if session.delivery and session.delivery.get("audio_file"):
            relative = session.delivery["audio_file"]
            path = self.game / "Data" / relative
            # Only internally generated delivery filenames are ever removed.
            expected = self.game / "Data/Sound/Voice/AnimaConnector" / (session.delivery["delivery_id"] + ".wav")
            if path == expected:
                path.unlink(missing_ok=True)

    async def end(self, session):
        self.invalidate(session)
        if session.context_task and not session.context_task.done():
            session.context_task.cancel()
        if self._microphone_task and not self._microphone_task.done():
            self._microphone_task.cancel()
        await asyncio.to_thread(self.microphone.discard)
        # Native side stops sound before emitting end; no success ack is fabricated.
        self._remove_staged_audio(session)
        if self.session is session:
            self.session = None
        self.ended.append(session.event.session_id)
        self.spawn(self.publish({"kind": "context_closed", "session_id": session.event.session_id}))

    async def publish(self, payload):
        identifier = uuid.uuid4().hex
        envelope = {"schema_version": "0.1", "event_id": identifier,
                    "captured_at": datetime.now(timezone.utc).isoformat(), **payload}
        self.artifacts.event(identifier, envelope)
        if self.settings.pipeline_mode == "http":
            async with self.client.stream("POST", self.settings.pipeline_url, json=envelope) as response:
                response.raise_for_status()
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 256 * 1024:
                        raise ConnectionError("pipeline response too large")
                if response.status_code != 202 and raw and payload["kind"] == "player_turn":
                    result = PipelineResult.model_validate_json(raw)
                    await self.result(result)
        return envelope

    async def publish_context(self, session, kind):
        event = session.event
        if self.settings.capture_screenshots and kind == "context_ready":
            try:
                path = await asyncio.to_thread(self.artifacts.screenshot, uuid.uuid4().hex, event.game_pid)
                session.screenshot = {"path": path, "viewpoint": "player_camera", "status": "saved",
                                      "captured_at": datetime.now(timezone.utc).isoformat(),
                                      "npc_visibility": "unknown", "event_id": event.event_id}
            except (OSError, ValueError):
                session.screenshot = {"status": "unavailable", "viewpoint": "player_camera"}
        if self.session is not session:
            return
        # Use latest coalesced snapshot after capture, while preserving frame provenance.
        event = session.event
        profile = profile_for(event.snapshot, self.profiles)
        await self.publish({"kind": kind, "session_id": event.session_id,
                            "game_epoch": event.game_epoch, "npc_id": npc_id(event.snapshot),
                            "revision": session.revision, "game": event.snapshot.model_dump(mode="json"),
                            "npc_profile": profile.model_dump(mode="json"),
                            "knowledge_status": "authored" if profile.knowledge_sources else "unknown",
                            "screenshot": session.screenshot, "image_description": None})

    async def player_input(self, speech: SpeechInput):
        session = self.current(speech.session_id)
        if speech.input_id in session.inputs:
            return {"request_id": speech.input_id, "status": session.inputs[speech.input_id]}
        if len(session.inputs) >= 128:
            raise ConnectionError("conversation turn limit reached")
        if session.request_id is not None or (session.delivery and session.delivery_status not in {"completed", "interrupted", "failed"}):
            raise ConnectionError("turn or playback busy; interrupt playback before speaking again")
        session.request_id = speech.input_id
        session.deadline = self.clock() + self.settings.timeout_s
        session.inputs[speech.input_id] = "pending"
        session.turn_task = self.spawn(self.run_turn(session, speech))
        return {"request_id": speech.input_id, "status": "pending"}

    async def run_turn(self, session, speech):
        try:
            if session.context_task:
                await asyncio.shield(session.context_task)
            if self.session is not session or session.request_id != speech.input_id:
                return
            profile = profile_for(session.event.snapshot, self.profiles)
            scenario = canonical_scenario(session.event, speech, profile, self.settings.world_id, session.revision)
            payload = {"kind": "player_turn", "session_id": speech.session_id,
                       "request_id": speech.input_id, "npc_id": scenario.turn.npc_id,
                       "revision": session.revision, "expires_at": session.deadline,
                       "player_input": speech.model_dump(mode="json"),
                       "scenario": scenario.model_dump(mode="json"),
                       "game": session.event.snapshot.model_dump(mode="json"),
                       "npc_profile": profile.model_dump(mode="json"),
                       "screenshot": session.screenshot, "image_description": None}
            remaining = session.deadline - self.clock()
            if remaining <= 0:
                raise ConnectionError("turn expired")
            async with asyncio.timeout(remaining):
                await self.publish(payload)
                if self.settings.pipeline_mode == "preview":
                    if self.runner is None:
                        raise ConnectionError("preview runner not configured")
                    preview = await self.runner.run(scenario)
                    if preview.response:
                        await self.result(PipelineResult(session_id=speech.session_id, request_id=speech.input_id,
                                                        npc_id=scenario.turn.npc_id, mode=preview.response.mode,
                                                        text=preview.response.text))
        except asyncio.CancelledError:
            session.inputs[speech.input_id] = "cancelled"
            raise
        except (ValueError, OSError, httpx.HTTPError, TimeoutError):
            session.inputs[speech.input_id] = "failed"
            if session.request_id == speech.input_id:
                session.request_id = None
            self.error = "pipeline_turn_failed"

    async def result(self, result: PipelineResult):
        session = self.current(result.session_id)
        if session.delivery and session.delivery["request_id"] == result.request_id:
            return {"delivery_id": session.delivery["delivery_id"], "status": session.delivery_status}
        if (result.request_id != session.request_id or self.clock() >= session.deadline
                or result.npc_id != npc_id(session.event.snapshot)):
            raise ConnectionError("stale or uncorrelated pipeline result")
        if ((result.mode == "speech" and not result.text.strip())
                or (result.mode == "silence" and (result.text or result.audio_path))):
            raise ConnectionError("invalid mode/text combination")
        # Only one callback may synthesize/stage this turn. Release on failure for explicit retry.
        if session.inputs[result.request_id] == "staging":
            raise ConnectionError("result already staging")
        session.inputs[result.request_id] = "staging"
        revision = session.revision
        raw = None
        try:
            if result.audio_path:
                raw = await asyncio.to_thread(read_audio, result.audio_path, self.audio_root)
            elif result.text and self.settings.tts_url:
                try:
                    # Leave time to deliver a text-only result if synthesis fails.
                    async with asyncio.timeout(max(0.001, session.deadline - self.clock() - 0.5)):
                        async with self.client.stream("POST", self.settings.tts_url, json={
                            "request_id": result.request_id, "text": result.text,
                            "voice": session.event.snapshot.npc.voice.model_dump() if session.event.snapshot.npc.voice else None,
                        }) as response:
                            response.raise_for_status()
                            data = bytearray()
                            async for chunk in response.aiter_bytes():
                                data.extend(chunk)
                                if len(data) > MAX_WAV_BYTES:
                                    raise ConnectionError("TTS audio exceeds limit")
                            raw = bytes(data)
                            wav_duration(raw)
                except (ValueError, httpx.HTTPError, TimeoutError):
                    raw = None
                    self.error = "tts_unavailable_text_only"
            if (self.session is not session or session.request_id != result.request_id
                    or session.revision != revision or self.clock() >= session.deadline):
                raise ConnectionError("result became stale during audio preparation")
            delivery_id = uuid.uuid4().hex
            envelope = await asyncio.to_thread(mouth_envelope, raw) if raw else []
            if (self.session is not session or session.request_id != result.request_id
                    or session.revision != revision or self.clock() >= session.deadline):
                raise ConnectionError("result became stale during audio analysis")
            relative, duration = stage_audio(raw, self.game, delivery_id) if raw else (None, min(15, max(2, len(result.text) / 15)))
            session.delivery = {"kind": "speak", "delivery_id": delivery_id, "session_id": result.session_id,
                                "request_id": result.request_id, "npc_id": result.npc_id,
                                "snapshot_sequence": session.revision, "mode": result.mode,
                                "text": result.text, "audio_file": relative, "duration_s": duration, "mouth": envelope,
                                "expires_at_ms": int(session.deadline * 1000)}
            session.delivery_status = "pending"
            session.inputs[result.request_id] = "staged"
            session.request_id = None
            return {"delivery_id": delivery_id, "status": "pending", "audio": bool(raw)}
        except BaseException:
            if session.request_id == result.request_id:
                session.inputs[result.request_id] = "pending"
            raise

    def command(self, session_id):
        session = self.current(session_id)
        command = session.delivery
        if not command or session.delivery_status in {"completed", "interrupted", "failed"}:
            return {"kind": "idle"}
        if command["kind"] == "stop":
            return command
        if session.delivery_status == "started":
            return {"kind": "idle"}
        if self.clock() * 1000 >= command["expires_at_ms"]:
            # A lost start ack is ambiguous: ask receiver to stop, never assume success.
            session.delivery = {**command, "kind": "stop"}
            return session.delivery
        return command

    async def listen(self, session):
        async with self._mic_gate:
            if self.session is not session:
                return
            # F8 is an explicit interruption: game-side already stops current audio.
            self.invalidate(session)
            await asyncio.to_thread(self.microphone.start)
        await asyncio.sleep(15)
        await self.finish_listening(session)

    async def finish_listening(self, session):
        async with self._mic_gate:
            if not self.microphone.active:
                return
            raw = await asyncio.to_thread(self.microphone.stop)
        if self._microphone_task and self._microphone_task is not asyncio.current_task():
            self._microphone_task.cancel()
        if self.session is not session:
            return
        wav_duration(raw)
        async with self.client.stream("POST", self.settings.stt_url, content=raw,
                                      headers={"Content-Type": "audio/wav"}) as response:
            response.raise_for_status()
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > 16384:
                    raise ConnectionError("STT response too large")
            parsed = json.loads(body)
        await self.player_input(SpeechInput(session_id=session.event.session_id, input_id=uuid.uuid4().hex,
                                            text=parsed["text"], confidence=parsed.get("confidence", 1), source="stt"))
