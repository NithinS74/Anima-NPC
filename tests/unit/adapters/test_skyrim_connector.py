"""Offline connection boundary tests; never open Skyrim, microphone or a provider."""

import asyncio
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import struct
import time
import wave

import httpx
import pytest
from pydantic import ValidationError

from npc.adapters.skyrim.assets import Artifacts, mouth_envelope, png_from_bgra, read_audio, stage_audio, wav_duration
from npc.adapters.skyrim.bridge import Bridge, ConnectionError
from npc.adapters.skyrim.protocol import (
    ActorData, Form, GameEvent, GameSnapshot, PipelineResult, Settings, SpeechInput,
    canonical_scenario, profile_for,
)


def form(identifier="00013478", name="Test NPC", plugin="Skyrim.esm"):
    return Form(form_id=identifier, local_id=identifier, name=name, plugin=plugin)


def event(kind="start", sequence=1, **changes):
    actor = ActorData(reference=form(), base=form("0001347B"), in_combat=False, dead=False,
                      weapon_drawn=False, sees_player=False)
    player = actor.model_copy(update={"reference": form("00000014", "Player"), "weapon_drawn": True})
    snapshot = GameSnapshot(npc=actor, player=player, hour=12.0, game_days=2.0, interior=True,
                            location=form("00016772", "Whiterun"))
    return GameEvent(kind=kind, sequence=sequence, state_revision=1, event_id=f"event-{sequence}",
                     session_id="session-a", game_epoch="load-a", game_pid=123,
                     captured_at_ms=int(time.time() * 1000), snapshot=snapshot if kind in {"start", "snapshot"} else None).model_copy(update=changes)


def speech(**changes):
    return SpeechInput(session_id="session-a", input_id="input-a", text="Hello there.", **changes)


def result(**changes):
    return PipelineResult(session_id="session-a", request_id="input-a", npc_id="ref:00013478",
                           text="Good day.", **changes)


def settings(tmp_path, **changes):
    return Settings(game_directory=str(tmp_path / "game"), output_directory=str(tmp_path / "output"),
                     audio_root=str(tmp_path / "audio"), capture_screenshots=False, **changes)


def wav(seconds=0.2, value=4000):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(16000)
        audio.writeframes(struct.pack("<h", value) * int(16000 * seconds))
    return stream.getvalue()


async def ready(bridge):
    await bridge.game_event(event())
    await bridge.session.context_task


async def pending(bridge):
    await ready(bridge)
    await bridge.player_input(speech())
    await bridge.session.turn_task


def test_mapping_preserves_unknown_knowledge_and_visibility():
    source = event()
    profile = profile_for(source.snapshot, {})
    scenario = canonical_scenario(source, speech(), profile, "world-a", 1)
    assert profile.knowledge_sources == ()
    assert scenario.snapshot.persona.occupation == "unknown"
    assert scenario.turn.scope.save_branch_id == "load-a"
    assert scenario.turn.npc_id != scenario.turn.player_id
    assert "player.weapon_drawn" not in {fact.path for fact in scenario.turn.facts}
    assert "world.weather" not in {fact.path for fact in scenario.turn.facts}
    assert all(fact.captured_at.timestamp() == pytest.approx(source.captured_at_ms / 1000) for fact in scenario.turn.facts)


@pytest.mark.parametrize("url", ["https://example.com/events", "http://user:secret@localhost/events", "http://localhost/events#secret"])
def test_remote_or_credential_endpoints_rejected(url, tmp_path):
    with pytest.raises(ValidationError):
        settings(tmp_path, pipeline_url=url)


def test_wav_checks_and_contained_staging(tmp_path):
    raw = wav()
    assert wav_duration(raw) == pytest.approx(0.2)
    with pytest.raises(ValueError): wav_duration(raw[:-50])
    with pytest.raises(ValueError): wav_duration(b"not audio")
    audio = tmp_path / "audio"; audio.mkdir()
    (audio / "line.wav").write_bytes(raw)
    assert read_audio("line.wav", audio) == raw
    with pytest.raises(ValueError): read_audio("../line.wav", audio)
    relative, duration = stage_audio(raw, tmp_path / "game", "a" * 32)
    assert (tmp_path / "game/Data" / relative).read_bytes() == raw
    with pytest.raises(ValueError): stage_audio(raw, tmp_path, "../../escape")
    assert len(mouth_envelope(raw)) == 4
    assert all(0 < value <= 1 for value in mouth_envelope(raw))


def test_png_encoding_and_capture_retention(tmp_path):
    raw = png_from_bgra(1, 1, b"\x00\x00\xff\xff")
    assert raw.startswith(b"\x89PNG")
    with pytest.raises(ValueError): png_from_bgra(0, 1, b"")
    captures = []
    artifacts = Artifacts(tmp_path, max_bytes=10000, max_screenshots=1,
                          capture=lambda pid: captures.append(pid) or raw)
    first = Path(artifacts.screenshot("one", 123))
    second = Path(artifacts.screenshot("two", 123))
    assert not first.exists() and second.exists()
    assert captures == [123, 123]
    with pytest.raises(ValueError):
        artifacts.event("large", {"text": "a" * 20000})


def test_context_ready_precedes_input_and_contains_game_metadata(tmp_path):
    async def run():
        bridge = Bridge(settings(tmp_path), root=tmp_path)
        try:
            await pending(bridge)
            records = [json.loads(path.read_text()) for path in bridge.output.glob("inbox/*.json")]
            assert {record["kind"] for record in records} == {"context_ready", "player_turn"}
            context = next(r for r in records if r["kind"] == "context_ready")
            assert context["knowledge_status"] == "unknown"
            assert context["image_description"] is None
            assert context["game"]["npc"]["base"]["plugin"] == "Skyrim.esm"
            assert (await bridge.player_input(speech()))["status"] == "pending"
            assert len(list(bridge.output.glob("inbox/*.json"))) == 2
        finally: await bridge.close()
    asyncio.run(run())


def test_screenshot_failure_does_not_block_context(tmp_path):
    async def run():
        def broken(_): raise OSError("game minimized")
        config = settings(tmp_path).model_copy(update={"capture_screenshots": True})
        bridge = Bridge(config, root=tmp_path, capture=broken)
        try:
            await ready(bridge)
            assert bridge.session.screenshot["status"] == "unavailable"
            assert len(list(bridge.output.glob("inbox/*.json"))) == 1
        finally: await bridge.close()
    asyncio.run(run())


def test_result_correlation_polling_ack_and_duplicate_are_idempotent(tmp_path):
    async def run():
        bridge = Bridge(settings(tmp_path), root=tmp_path)
        try:
            await pending(bridge)
            with pytest.raises(ConnectionError):
                await bridge.result(result().model_copy(update={"npc_id": "other"}))
            answer = await bridge.result(result())
            command = bridge.command("session-a")
            assert command["text"] == "Good day."
            assert command["snapshot_sequence"] == 1
            assert bridge.command("session-a") == command  # lost HTTP reply does not lose delivery
            assert await bridge.result(result()) == {"delivery_id": answer["delivery_id"], "status": "pending"}
            with pytest.raises(ConnectionError):
                await bridge.player_input(speech().model_copy(update={"input_id": "input-b"}))
            await bridge.game_event(event("delivery", 2, delivery_id=answer["delivery_id"], status="started"))
            assert bridge.command("session-a") == {"kind": "idle"}
            await bridge.game_event(event("delivery", 3, delivery_id=answer["delivery_id"], status="completed"))
            await bridge.game_event(event("delivery", 4, delivery_id=answer["delivery_id"], status="started"))
            assert bridge.session.delivery_status == "completed"
            assert (await bridge.player_input(speech().model_copy(update={"input_id": "input-b"})))["status"] == "pending"
        finally: await bridge.close()
    asyncio.run(run())


def test_heartbeat_keeps_turn_but_relevant_state_cancels_it(tmp_path):
    async def run():
        bridge = Bridge(settings(tmp_path), root=tmp_path)
        try:
            await pending(bridge)
            await bridge.game_event(event("snapshot", 2))
            assert bridge.session.request_id == "input-a"
            await bridge.game_event(event("snapshot", 3, state_revision=2))
            assert bridge.session.request_id is None
            with pytest.raises(ConnectionError): await bridge.result(result())
            assert (await bridge.game_event(event("snapshot", 2)))["status"] == "duplicate"
            with pytest.raises(ConnectionError):
                await bridge.game_event(event("snapshot", 2, event_id="different-stale-event"))
        finally: await bridge.close()
    asyncio.run(run())


def test_expired_delivery_stops_instead_of_replaying(tmp_path):
    async def run():
        now = [time.time()]
        bridge = Bridge(settings(tmp_path), root=tmp_path, clock=lambda: now[0])
        try:
            await pending(bridge)
            await bridge.result(result())
            now[0] += 31
            assert bridge.command("session-a")["kind"] == "stop"
            assert bridge.session.delivery_status == "pending"
        finally: await bridge.close()
    asyncio.run(run())


def test_end_rejects_future_callback_and_removes_staged_audio(tmp_path):
    async def run():
        bridge = Bridge(settings(tmp_path), root=tmp_path)
        bridge.audio_root.mkdir()
        (bridge.audio_root / "response.wav").write_bytes(wav())
        try:
            await pending(bridge)
            await bridge.result(result(audio_path="response.wav"))
            command = bridge.command("session-a")
            path = bridge.game / "Data" / command["audio_file"]
            assert path.exists() and command["mouth"]
            await bridge.game_event(event("end", 2))
            assert not path.exists()
            with pytest.raises(ConnectionError): await bridge.result(result())
        finally: await bridge.close()
    asyncio.run(run())


def test_http_pipeline_roundtrip_and_failed_pipeline(tmp_path):
    async def run():
        received = []
        def responder(request):
            payload = json.loads(request.content)
            received.append(payload)
            if payload["kind"] == "player_turn":
                return httpx.Response(200, json=result().model_dump())
            return httpx.Response(202)
        client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
        bridge = Bridge(settings(tmp_path, pipeline_mode="http", pipeline_url="http://localhost/events"), root=tmp_path, client=client)
        try:
            await pending(bridge)
            assert [r["kind"] for r in received] == ["context_ready", "player_turn"]
            assert bridge.command("session-a")["kind"] == "speak"
        finally: await bridge.close()
    asyncio.run(run())


def test_preview_uses_existing_core_without_live_calls(tmp_path):
    from npc.generation.provider import OfflineProvider
    from npc.runtime.preview import PreviewRunner
    async def run():
        bridge = Bridge(settings(tmp_path, pipeline_mode="preview"), root=tmp_path, runner=PreviewRunner(OfflineProvider()))
        try:
            await pending(bridge)
            command = bridge.command("session-a")
            assert command["kind"] == "speak" and command["text"]
        finally: await bridge.close()
    asyncio.run(run())


def test_http_routes_validate_ingress_and_deliver_callback(tmp_path):
    from fastapi.testclient import TestClient
    from npc.adapters.skyrim.server import create_app
    bridge = Bridge(settings(tmp_path), root=tmp_path)
    with TestClient(create_app(bridge)) as client:
        assert client.get("/v1/health").json()["image_descriptor"] == "not_connected"
        assert client.post("/v1/game/event", content="{}", headers={"Content-Type": "text/plain"}).status_code == 415
        assert client.post("/v1/game/event", content=b" " * (256 * 1024 + 1), headers={"Content-Type": "application/json"}).status_code == 413
        assert client.post("/v1/game/event", json={}).status_code == 422
        assert client.post("/v1/game/event", json=event().model_dump(mode="json")).status_code == 200
        assert client.post("/v1/player-input", json=speech().model_dump()).status_code == 202
        response = client.post("/v1/pipeline/result", json=result().model_dump())
        assert response.status_code == 200
        command = client.get("/v1/game/command", params={"session_id": "session-a"}).json()
        assert command["delivery_id"] == response.json()["delivery_id"]
        assert client.post("/v1/game/event", json=event("end", 2).model_dump(mode="json")).status_code == 200
        assert client.post("/v1/pipeline/result", json=result().model_dump()).status_code == 409
        assert client.post("/v1/game/event", json=event().model_dump(mode="json")).status_code == 409


def test_failed_pipeline_releases_turn_without_fabricating_reply(tmp_path):
    async def run():
        def respond(request):
            return httpx.Response(202 if json.loads(request.content)["kind"] == "context_ready" else 503)
        bridge = Bridge(settings(tmp_path, pipeline_mode="http", pipeline_url="http://localhost/events"),
                         root=tmp_path, client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        try:
            await pending(bridge)
            assert bridge.session.request_id is None
            assert bridge.session.inputs["input-a"] == "failed"
            assert bridge.command("session-a") == {"kind": "idle"}
            assert bridge.error == "pipeline_turn_failed"
        finally: await bridge.close()
    asyncio.run(run())


def test_push_to_talk_transcribes_and_deletes_recording_boundary(tmp_path):
    class FakeMicrophone:
        active = False
        starts = 0
        stops = 0
        def start(self): self.starts += 1; self.active = True
        def stop(self): self.stops += 1; self.active = False; return wav()
        def discard(self):
            if self.active: self.stop()
    async def run():
        received = []
        def transcribe(request):
            received.append(request.content)
            return httpx.Response(200, json={"text": "Good morning.", "confidence": 0.9})
        microphone = FakeMicrophone()
        bridge = Bridge(settings(tmp_path, stt_url="http://localhost/stt"), root=tmp_path,
                         microphone=microphone, client=httpx.AsyncClient(transport=httpx.MockTransport(transcribe)))
        try:
            await ready(bridge)
            await bridge.game_event(event("listen_start", 2))
            # Wait for the fake device's worker boundary, not a real microphone.
            for _ in range(100):
                if microphone.active: break
                await asyncio.sleep(0.001)
            await bridge.finish_listening(bridge.session)
            await bridge.session.turn_task
            assert microphone.starts == microphone.stops == 1
            assert received == [wav()]
            records = [json.loads(path.read_text()) for path in bridge.output.glob("inbox/*.json")]
            turn = next(value for value in records if value["kind"] == "player_turn")
            assert turn["player_input"]["source"] == "stt"
            assert turn["player_input"]["text"] == "Good morning."
        finally: await bridge.close()
    asyncio.run(run())


@pytest.mark.parametrize("status,content", [(503, b"unavailable"), (200, b"bad wav"), (200, wav())])
def test_tts_keeps_validated_text_on_audio_failure(tmp_path, status, content):
    async def run():
        received = []
        def respond(request):
            received.append(json.loads(request.content))
            return httpx.Response(status, content=content)
        bridge = Bridge(settings(tmp_path, tts_url="http://localhost/tts"), root=tmp_path,
                         client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        try:
            await pending(bridge)
            answer = await bridge.result(result())
            command = bridge.command("session-a")
            assert command["text"] == "Good day."
            assert received[0]["text"] == command["text"]
            assert answer["audio"] is (content == wav())
            if not answer["audio"]:
                assert bridge.error == "tts_unavailable_text_only"
        finally: await bridge.close()
    asyncio.run(run())


def test_ptt_without_stt_configuration_keeps_context_and_never_records(tmp_path):
    async def run():
        bridge = Bridge(settings(tmp_path), root=tmp_path)
        try:
            await ready(bridge)
            assert (await bridge.game_event(event("listen_start", 2)))["status"] == "accepted"
            assert bridge.session.event.session_id == "session-a"
            assert not bridge.microphone.active
            assert bridge.error == "stt_not_configured"
        finally: await bridge.close()
    asyncio.run(run())


def test_runner_composes_configured_rag_and_provider(tmp_path):
    from npc.adapters.skyrim.__main__ import build_runner
    from npc.rag.http import HTTPRetriever
    from npc.generation.provider import OfflineProvider
    profile = tmp_path / "offline.yaml"
    profile.write_text("provider: offline\n")
    config = tmp_path / "rag.json"
    config.write_text(json.dumps({"backend": "http", "bindings": [{"game_id": "skyrim",
        "world_id": "local-skyrim", "npc_ids": ["ref:00013478"], "source": "public.txt"}]}))
    runner = build_runner(settings(tmp_path, provider_profile="offline.yaml", rag_config="rag.json"), tmp_path)
    assert isinstance(runner.provider, OfflineProvider)
    assert isinstance(runner.retriever, HTTPRetriever)
    assert runner.retriever.config.bindings[0].npc_ids == ("ref:00013478",)
    assert runner.limits.max_input_bytes == 12000


def test_cli_overrides_enable_connected_path_without_rewriting_config(tmp_path, monkeypatch):
    import sys
    import uvicorn
    from fastapi.testclient import TestClient
    from npc.adapters.skyrim.__main__ import main
    profile = tmp_path / "offline.yaml"; profile.write_text("provider: offline\n")
    config = tmp_path / "connector.json"
    original = settings(tmp_path, pipeline_mode="preview", provider_profile=str(profile)).model_dump_json()
    config.write_text(original)
    monkeypatch.setattr(sys, "argv", ["connector", "--config", str(config), "--cv-url", "http://localhost:8000",
                                      "--attach-visual-reference", "--provider-profile", str(profile)])
    observed = []
    def serve(app, **kwargs):
        assert kwargs["host"] == "127.0.0.1"
        with TestClient(app) as client: observed.append(client.get("/v1/health").json())
    monkeypatch.setattr(uvicorn, "run", serve)
    main()
    assert observed[0]["pipeline_mode"] == "preview"
    assert observed[0]["image_descriptor"] == "configured"
    assert observed[0]["visual_attached"] is True
    assert config.read_text() == original


@pytest.mark.parametrize("failure", ["unavailable", "timeout"])
def test_vision_failure_keeps_text_pipeline_usable(tmp_path, failure):
    from npc.vision import CVFailure
    from npc.generation.provider import OfflineProvider
    from npc.runtime.preview import PreviewRunner
    class BrokenVision:
        async def analyze(self, *args):
            raise CVFailure("cv_unavailable") if failure == "unavailable" else TimeoutError()
    async def run():
        config = settings(tmp_path, pipeline_mode="preview").model_copy(update={"capture_screenshots": True})
        bridge = Bridge(config, root=tmp_path, cv_client=BrokenVision(), capture=lambda _: png_from_bgra(1, 1, b"\0\0\0\xff"),
                        runner=PreviewRunner(OfflineProvider()))
        try:
            await pending(bridge)
            assert bridge.session.visual is None
            assert bridge.session.visual_status == "unavailable"
            assert bridge.command("session-a")["text"]
        finally: await bridge.close()
    asyncio.run(run())


def test_visual_frame_is_bound_to_revision_ttl_and_session(tmp_path):
    from npc.vision import VisualContext
    class Vision:
        def __init__(self): self.started = asyncio.Event(); self.finish = asyncio.Event()
        async def analyze(self, *args):
            self.started.set()
            await self.finish.wait()
            return VisualContext(id="frame-a", captured_at=datetime.now(timezone.utc), environment="Old room")
    async def run():
        vision = Vision()
        now = [time.time()]
        config = settings(tmp_path).model_copy(update={"capture_screenshots": True})
        bridge = Bridge(config, root=tmp_path, cv_client=vision, clock=lambda: now[0],
                        capture=lambda _: png_from_bgra(1, 1, b"\0\0\0\xff"))
        try:
            await bridge.game_event(event())
            await vision.started.wait()
            await bridge.game_event(event("snapshot", 2, state_revision=2))
            vision.finish.set()
            await bridge.session.context_task
            assert bridge.session.visual is None
            assert bridge.session.visual_status == "stale"
            await bridge.publish_context(bridge.session, "context_updated")
            assert bridge.visual_reference(bridge.session).environment == "Old room"
            now[0] += 16
            assert bridge.visual_reference(bridge.session) is None
            await bridge.game_event(event().model_copy(update={"session_id": "session-b", "game_epoch": "load-b"}))
            assert bridge.session.visual is None
            await bridge.session.context_task
            assert bridge.session.visual_revision == 1
        finally: await bridge.close()
    asyncio.run(run())


def test_no_response_releases_pending_turn(tmp_path):
    class EmptyRunner:
        async def run(self, *args, **kwargs):
            from types import SimpleNamespace
            return SimpleNamespace(response=None)
    async def run():
        bridge = Bridge(settings(tmp_path, pipeline_mode="preview"), root=tmp_path, runner=EmptyRunner())
        try:
            await pending(bridge)
            assert bridge.session.request_id is None
            assert bridge.session.inputs["input-a"] == "failed"
            assert bridge.command("session-a") == {"kind": "idle"}
        finally: await bridge.close()
    asyncio.run(run())


@pytest.mark.parametrize("attach", [True, False])
def test_capture_vlm_rag_generation_delivery_roundtrip(tmp_path, attach):
    """Real CV HTTP/schema, VLM client, core and adapter; fake inference/game IO."""
    from fastapi import FastAPI
    from app.api.routes import router
    from app.detection.yolo_detector import NoDetector
    from app.perception.pipeline import PerceptionPipeline
    from app.vision.ollama_vlm import OllamaVLM
    from npc.vision import CVSceneClient
    from npc.contracts.dialogue import ProviderReply
    from npc.rag.config import RAGConfig
    from npc.rag.http import HTTPRetriever
    from npc.runtime.preview import PreviewLimits, PreviewRunner
    from npc.context import build_situation
    prompts, queries, vlm_requests = [], [], []
    class Provider:
        async def generate(self, prompt, timeout_s):
            prompts.append(prompt)
            return ProviderReply(content='{"mode":"speech","text":"The healer works at the eastern gate.","cue":null,"evidence_ids":["kb1"]}',
                                 model="fake", finish_reason="stop", input_tokens=20, output_tokens=10)
    def model(request):
        vlm_requests.append(json.loads(request.content))
        return httpx.Response(200, json={"response": json.dumps({"environment": {"description": "A stone room"},
            "uncertainties": ["NPC visibility unknown"]})})
    def retrieve(request):
        queries.append(json.loads(request.content))
        return httpx.Response(200, json={"query": queries[-1]["query"], "matches": [{"id": "healer-fact",
            "text": "The healer works at the eastern gate.", "source": "public.txt", "chunk_index": 0,
            "distance": 0.1, "truncated": False}]})
    async def run():
        app = FastAPI(); app.include_router(router)
        app.state.pipeline = PerceptionPipeline(NoDetector(), OllamaVLM("http://localhost:11434", "fake-vlm", 2,
            transport=httpx.MockTransport(model)), tmp_path / "cv")
        vision = CVSceneClient("http://localhost:8000", 2, transport=httpx.ASGITransport(app=app))
        retriever = HTTPRetriever(RAGConfig(backend="http", bindings=[{"game_id": "skyrim", "world_id": "local-skyrim",
            "npc_ids": ["ref:00013478"], "source": "public.txt"}]), transport=httpx.MockTransport(retrieve))
        runner = PreviewRunner(Provider(), PreviewLimits(max_input_bytes=12000), retriever=retriever)
        config = settings(tmp_path, pipeline_mode="preview", attach_visual_reference=attach).model_copy(update={"capture_screenshots": True})
        bridge = Bridge(config, root=tmp_path, cv_client=vision, runner=runner,
                        capture=lambda _: png_from_bgra(1, 1, b"\0\0\0\xff"))
        try:
            await ready(bridge)
            question = speech().model_copy(update={"text": "Where can I find the healer?"})
            await bridge.player_input(question)
            await bridge.session.turn_task
            command = bridge.command("session-a")
            assert command["text"] == "The healer works at the eastern gate."
            assert command["audio_file"] is None
            assert len(prompts) == len(queries) == len(vlm_requests) == 1
            data = json.loads(prompts[0].messages[1].content)
            assert ("untrusted_visual_reference" in data) is attach
            if attach: assert data["untrusted_visual_reference"]["environment"] == "A stone room"
            assert data["retrieved_evidence"][0]["text"] == command["text"]
            scenario = canonical_scenario(event(), question, profile_for(event().snapshot, {}), "local-skyrim", 1)
            situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
            assert not any(f.value == "A stone room" for f in situation.perceived_facts)
            await bridge.game_event(event("delivery", 2, delivery_id=command["delivery_id"], status="started"))
            await bridge.game_event(event("delivery", 3, delivery_id=command["delivery_id"], status="completed"))
            assert bridge.command("session-a") == {"kind": "idle"}
            assert bridge.session.delivery_status == "completed"
        finally: await bridge.close()
    asyncio.run(run())
