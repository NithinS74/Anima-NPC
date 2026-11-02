"""python -m npc.adapters.skyrim --config configs/skyrim/connector.json"""

import argparse
import json
from pathlib import Path

from .bridge import Bridge
from .protocol import Settings
from .server import create_app


def main():
    parser = argparse.ArgumentParser(description="Independent Skyrim connection layer")
    parser.add_argument("--config", default="configs/skyrim/connector.json")
    args = parser.parse_args()
    root = Path.cwd()
    path = root / args.config
    if not path.is_file():
        parser.error("create configs/skyrim/connector.json from connector.example.json first")
    settings = Settings.model_validate_json(path.read_bytes())
    runner = None
    if settings.pipeline_mode == "preview":
        from npc.generation.config import load_provider
        from npc.runtime.preview import PreviewLimits, PreviewRunner
        runner = PreviewRunner(load_provider(root / settings.provider_profile),
                               PreviewLimits(response_timeout_ms=25000, model_cutoff_ms=22000))
    import uvicorn
    bridge = Bridge(settings, root=root, runner=runner)
    uvicorn.run(create_app(bridge), host="127.0.0.1", port=settings.port,
                access_log=False, limit_concurrency=8, timeout_keep_alive=3)


if __name__ == "__main__":
    main()
