"""Prepare and maintain the NPC-owned local knowledge index."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root (defaults to this NPC checkout)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare", help="Initialize/download the local encoder and sync documents")
    commands.add_parser("sync", help="Explicitly index document additions/edits/deletions")
    commands.add_parser("status", help="Show local corpus/index paths and counts")
    query = commands.add_parser("query", help="Retrieve evidence without a dialogue-model call")
    query.add_argument("text")
    query.add_argument("--source")
    query.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        from npc.rag.backend import RAGService, Settings
        service = RAGService(Settings(root=args.root))
        if args.command in {"prepare", "sync"}:
            if args.command == "prepare":
                print("Preparing local CPU embedding model (first setup may download it)...", flush=True)
                service.warmup()
            print("Synchronizing local knowledge index...", flush=True)
            report = service.sync()
            print(report.model_dump_json(indent=2))
            return 1 if report.errors else 0
        data = service.status() if args.command == "status" else service.retrieve(
            args.text, source=args.source, top_k=args.top_k).model_dump()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(f"Local RAG unavailable: {error}. Run setup; existing documents/index were not reset.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
