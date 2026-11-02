"""Loopback-only HTTP surface; model-facing work runs outside the game process."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .bridge import Bridge, ConnectionError
from .protocol import GameEvent, PipelineResult, SpeechInput


def create_app(bridge: Bridge):
    @asynccontextmanager
    async def lifespan(app):
        yield
        await bridge.close()

    app = FastAPI(title="Anima Skyrim connector", lifespan=lifespan)

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        # No CORS and no public bind. Check the actual peer, never forwarded headers.
        if request.client and request.client.host not in {"127.0.0.1", "::1", "testclient"}:
            return JSONResponse({"error": "loopback_only"}, status_code=403)
        if request.method == "POST":
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": "application_json_required"}, status_code=415)
            data = bytearray()
            async for chunk in request.stream():
                data.extend(chunk)
                if len(data) > 256 * 1024:
                    return JSONResponse({"error": "payload_too_large"}, status_code=413)
            request._body = bytes(data)
        return await call_next(request)

    @app.exception_handler(ConnectionError)
    async def conflict(request, error):
        return JSONResponse({"error": str(error)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request, error):
        return JSONResponse({"error": "invalid_connector_operation"}, status_code=400)

    @app.get("/v1/health")
    async def health():
        session = bridge.session
        return {"status": "ready", "pipeline_mode": bridge.settings.pipeline_mode,
                "session_id": session.event.session_id if session else None,
                "last_error": bridge.error, "image_descriptor": "not_connected"}

    @app.post("/v1/game/event")
    async def game_event(event: GameEvent):
        return await bridge.game_event(event)

    @app.get("/v1/game/command")
    async def command(session_id: str):
        return bridge.command(session_id)

    @app.post("/v1/player-input", status_code=202)
    async def speech(speech: SpeechInput):
        return await bridge.player_input(speech)

    @app.post("/v1/pipeline/result")
    async def result(result: PipelineResult):
        return await bridge.result(result)

    return app
