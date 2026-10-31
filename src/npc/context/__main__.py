"""Offline situation preview: python -m npc.context <scenario.json>."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from npc.context import ContextMismatch, build_situation
from npc.contracts.context import ContextScenario


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    args = parser.parse_args()
    try:
        if args.scenario.stat().st_size > 256 * 1024:
            raise ValueError("scenario file exceeds 256 KB")
        scenario = ContextScenario.model_validate_json(args.scenario.read_text(encoding="utf-8"))
        result = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    except (OSError, ValueError, ValidationError, ContextMismatch) as error:
        # Do not echo player/corpus values from Pydantic validation details.
        print(f"Cannot preview scenario: {type(error).__name__}. Check schema, scope and timestamps.", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
