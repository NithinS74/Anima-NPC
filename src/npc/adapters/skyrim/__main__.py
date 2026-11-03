"""python -m npc.adapters.skyrim --config configs/skyrim/connector.json"""

import argparse
import json
from pathlib import Path

from .bridge import Bridge
from .protocol import Settings
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


def main():
    parser = argparse.ArgumentParser(description="Independent Skyrim connection layer")
    parser.add_argument("--config", default="configs/skyrim/connector.json")
    parser.add_argument("--cv-url", help="Loopback CV origin; overrides the local JSON setting")
    parser.add_argument("--rag-config", help="Trusted Skyrim world/NPC/source bindings")
    parser.add_argument("--provider-profile", help="Provider YAML; a live profile can incur API charges")
    parser.add_argument("--attach-visual-reference", action="store_true", help="Attach untrusted camera description to dialogue prompts")
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
    settings = Settings.model_validate(raw)
    runner = None
    if settings.pipeline_mode == "preview":
        runner = build_runner(settings, root)
    import uvicorn
    bridge = Bridge(settings, root=root, runner=runner)
    uvicorn.run(create_app(bridge), host="127.0.0.1", port=settings.port,
                access_log=False, limit_concurrency=8, timeout_keep_alive=3)


if __name__ == "__main__":
    main()
