"""Authored/fallback line pools chosen deterministically from the request ID."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

POOL_FILE = Path(__file__).resolve().parents[3] / "fixtures" / "lines" / "line_pools.json"
# Used only when the fixture is missing; one line each, so behaviour degrades to the old fixed lines.
BUILTIN = {"fallback": {"default": ["I cannot say."], "formal": ["I cannot speak to that matter."]}}


@lru_cache(maxsize=1)
def pools(path: Path = POOL_FILE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if isinstance(v, dict)}
    except (OSError, ValueError):
        return BUILTIN


def style_keys(persona, relationship=None) -> tuple[str, ...]:
    keys = []
    if "formal" in {s.casefold() for s in persona.speech_style}:
        keys.append("formal")
    if persona.warmth >= 0.7:
        keys.append("warm")
    if persona.caution >= 0.7 or persona.warmth < 0.3:
        keys.append("guarded")
    return tuple(keys)


def pick_line(intent: str, keys, request_id: str, recent=(), *, table=None) -> str | None:
    """First key present wins, then 'default'. Skips recently used lines; a one-line pool just returns it."""
    pool_set = (table or pools()).get(intent)
    if not pool_set:
        return None
    pool = next((pool_set[k] for k in (*keys, "default") if pool_set.get(k)), None)
    if not pool:
        return None
    start = int(hashlib.sha256(request_id.encode()).hexdigest()[:8], 16) % len(pool)
    used = {line.casefold().strip() for line in recent}
    for step in range(len(pool)):
        line = pool[(start + step) % len(pool)]
        if line.casefold().strip() not in used:
            return line
    return pool[start]


def recent_lines(situation) -> tuple[str, ...]:
    return tuple(m.npc_text for m in situation.recent_dialogue if m.npc_text) + tuple(situation.conversation.replies)
