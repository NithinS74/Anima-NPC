"""python -m npc.adapters.skyrim --config configs/skyrim/connector.json"""

import argparse
import json
from pathlib import Path

from .bridge import Bridge
from .protocol import Settings, SpeechInput
from .diagnostics import configure, shutdown, event as log_event
from .server import create_app


def build_runner(settings, root):
    """Compose the existing pipeline; never ingest or download during launch."""
    from npc.generation.config import load_provider
    from npc.runtime.preview import PreviewLimits, PreviewRunner
    from npc.rag import load_retriever
    timeout_ms = int(settings.timeout_s * 1000)
    return PreviewRunner(load_provider(root / settings.provider_profile),
                         PreviewLimits(response_timeout_ms=timeout_ms,
                                       model_cutoff_ms=max(50, timeout_ms - 1000),
                                       max_input_bytes=12000),
                         retriever=load_retriever(root / settings.rag_config if settings.rag_config else None))


def send_text(settings, text, *, client=None):
    """Submit only to Anima's active loopback session, never Mantella."""
    import httpx
    import uuid
    def submit(connection):
        health = connection.get("/v1/health")
        health.raise_for_status()
        session = health.json().get("session_id")
        if not session:
            raise ValueError("Open normal NPC dialogue in Skyrim before sending Anima text")
        speech = SpeechInput(session_id=session, input_id=uuid.uuid4().hex, text=text)
        response = connection.post("/v1/player-input", json=speech.model_dump(mode="json"))
        response.raise_for_status()
        log_event("INPUT_SUBMITTED", session=session, request=speech.input_id, text=text,
                  status="accepted_for_processing; not_delivery")
        return response.json()
    if client is not None:
        return submit(client)
    with httpx.Client(base_url=f"http://127.0.0.1:{settings.port}", timeout=5, trust_env=False) as connection:
        return submit(connection)


def main():
    parser = argparse.ArgumentParser(description="Independent Skyrim connection layer")
    parser.add_argument("--config", default="configs/skyrim/connector.json")
    parser.add_argument("--cv-url", help="Loopback CV origin; overrides the local JSON setting")
    parser.add_argument("--rag-config", help="Trusted Skyrim world/NPC/source bindings")
    parser.add_argument("--provider-profile", help="Provider YAML; a live profile can incur API charges")
    parser.add_argument("--attach-visual-reference", action="store_true", help="Attach untrusted camera description to dialogue prompts")
    parser.add_argument("--say", help="Send this text to the running ANIMA bridge; does not start a server")
    parser.add_argument("--log-file", help="Optional rotating Anima dialogue log (1 MiB, two backups)")
    parser.add_argument("--local-speech", action="store_true", help="Enable local Windows voice synthesis and dictation")
    args = parser.parse_args()
    root = Path.cwd()
    path = root / args.config
    if not path.is_file():
        parser.error("create configs/skyrim/connector.json from connector.example.json first")
    raw = json.loads(path.read_bytes())
    for name in ("cv_url", "rag_config", "provider_profile"):
        if (value := getattr(args, name)) is not None:
            raw[name] = value
    if args.attach_visual_reference:
        raw["attach_visual_reference"] = True
    if args.local_speech:
        port = raw.get("port", 8768)
        raw.update(stt_url=f"http://127.0.0.1:{port}/v1/speech/stt", tts_url=f"http://127.0.0.1:{port}/v1/speech/tts")
    settings = Settings.model_validate(raw)
    configure(args.log_file)
    if args.say is not None:
        import httpx
        try:
            send_text(settings, args.say)
        except (ValueError, httpx.HTTPError):
            parser.exit(1, "ANIMA: text was not accepted; check bridge health, open NPC dialogue, and retry.\n")
        finally:
            shutdown()
        return
    log_event("STARTUP", mode=settings.pipeline_mode, provider_profile=Path(settings.provider_profile).name,
              rag=bool(settings.rag_config), stt=bool(settings.stt_url), tts=bool(settings.tts_url),
              port=settings.port, attribution="Anima bridge only; other mods are separate")
    runner = None
    if settings.pipeline_mode == "preview":
        runner = build_runner(settings, root)
    import uvicorn
    bridge = Bridge(settings, root=root, runner=runner)
    app = create_app(bridge)
    if args.local_speech:
        from .speech import WindowsSpeech, create_speech_app
        app.mount("/v1/speech", create_speech_app(WindowsSpeech(root / settings.output_directory / "speech")))
    try:
        uvicorn.run(app, host="127.0.0.1", port=settings.port,
                    access_log=False, limit_concurrency=8, timeout_keep_alive=3)
    finally:
        shutdown()


if __name__ == "__main__":
    main()
