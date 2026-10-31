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


def choose_provider(mode, config):
    if mode == "offline":
        return OfflineProvider(), False
    try:
        provider = load_provider(config)
        return provider, not isinstance(provider, OfflineProvider)
    except ConfigurationFailure:
        if mode == "live":
            raise
        print("No valid live provider configuration. Starting OFFLINE SCRIPTED preview; configure .env for real responses.")
        return OfflineProvider(), False


def main():
    parser = argparse.ArgumentParser(description="Anima local NPC companion application")
    parser.add_argument("--live", action="store_const", dest="mode", const="live", help="Require configured API calls")
    parser.add_argument("--offline", action="store_const", dest="mode", const="offline", help="Use the scripted provider")
    parser.add_argument("--auto", action="store_const", dest="mode", const="auto", help="Use configured API or a labelled offline preview")
    parser.set_defaults(mode="offline")
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
        provider, live = choose_provider(args.mode, args.config)
        server = LabServer(LabService(provider, live=live, realtime=args.realtime, development_timeout_s=args.development_timeout, media=LabMedia(),
                                     state_store=SocialStore(args.state_db)), args.port)
    except ConfigurationFailure as error:
        print(f"Configuration error: {error}. Check the local .env; no keys printed.")
        return 2
    except StoreFailure:
        print("Could not open persistent lab state. Check data/npc_lab/ and available disk space.")
        return 2
    except (OSError, ValueError):
        print("Could not start Anima. Check persona files and whether the port is already in use.")
        return 2
    print(f"Anima: {server.origin} | {'LIVE API (may incur charges)' if live else 'OFFLINE FAKE'}")
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
