import argparse
import webbrowser
from pathlib import Path

from npc.generation.config import ConfigurationFailure, load_provider
from npc.generation.provider import OfflineProvider
from tools.npc_lab.server import LabServer
from tools.npc_lab.service import LabService
from tools.npc_lab.media import LabMedia
from tools.npc_lab.service import ROOT
from npc.state.social_store import SocialStore, StoreFailure


def main():
    parser = argparse.ArgumentParser(description="Separate local NPC manual-test lab")
    parser.add_argument("--live", action="store_true", help="Enable API calls using local provider settings")
    parser.add_argument("--offline", action="store_false", dest="live", help="Override the launcher to use the fake provider")
    parser.set_defaults(live=False)
    parser.add_argument("--config", type=Path, default=Path("configs/providers/gemini.yaml"))
    parser.add_argument("--realtime", action="store_true", help="Use the core 3 s deadline instead of development timing")
    parser.add_argument("--development-timeout", type=int, default=30, choices=range(1, 61), metavar="1..60", help="Manual-testing deadline in seconds (default 30; ignored in realtime mode)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-db", type=Path, default=ROOT / "data/npc_lab/state.sqlite3", help="Separate SQLite file for an isolated test history")
    parser.add_argument("--open", action="store_true", help="Open the local browser interface")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be 1..65535")
    try:
        provider = load_provider(args.config) if args.live else OfflineProvider()
        server = LabServer(LabService(provider, live=args.live, realtime=args.realtime, development_timeout_s=args.development_timeout, media=LabMedia(),
                                     state_store=SocialStore(args.state_db)), args.port)
    except ConfigurationFailure as error:
        print(f"Configuration error: {error}. Check the local .env; no keys printed.")
        return 2
    except StoreFailure:
        print("Could not open persistent lab state. Check data/npc_lab/ and available disk space.")
        return 2
    except (OSError, ValueError):
        print("Could not start lab. Check persona files and whether the port is already in use.")
        return 2
    print(f"NPC lab: {server.origin} | {'LIVE API (may incur charges)' if args.live else 'OFFLINE FAKE'}")
    print("Persistent social state and acknowledged conversation history. Ctrl+C stops the lab.")
    if args.open:
        webbrowser.open(server.origin)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
