"""Default characters for Skyrim NPCs without an authored profile. All game knowledge lives in the rules file."""

import hashlib
import json
import re
from pathlib import Path

from npc.contracts.context import Persona, SceneItem

MAX_RULES_BYTES = 128 * 1024
SERVICES_MAX = 6


def load_rules(path: Path) -> dict | None:
    """Rules or None when the file is absent/invalid (callers then keep the plain unknown persona)."""
    try:
        if path.stat().st_size > MAX_RULES_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("rules", []), list) else None


def _word(term: str, text: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(term.lower()) + r"(?![a-z0-9])", text) is not None


def _matches(match: dict, names: str, factions: list[str], faction_ids: set[str], gear: str, race: str) -> bool:
    return (any(_word(t, names) for t in match.get("name", ()))
            or any(_word(t, f) for t in match.get("faction", ()) for f in factions)
            or any(i.upper() in faction_ids for i in match.get("faction_id", ()))
            or any(_word(t, gear) for t in match.get("equipment", ()))
            or any(_word(t, race) for t in match.get("race", ())))


def _unit(seed: str, index: int) -> float:
    return hashlib.sha256(f"{seed}:{index}".encode()).digest()[0] / 255


def _place(snapshot) -> str | None:
    for form in (snapshot.location, snapshot.cell):
        if form is not None and form.name:
            return form.name[:140]
    return None


def derive_persona(snapshot, rules: dict) -> Persona:
    npc = snapshot.npc
    name = npc.reference.name or npc.base.name or "Unknown NPC"
    names = " ".join(n for n in (npc.reference.name, npc.base.name) if n).lower()
    factions = [f.name.lower() for f in npc.factions if f.name]
    ids = {f.form_id.upper() for f in npc.factions}
    gear = " ".join(f.name for f in npc.equipment if f.name).lower()
    race = (npc.race.name if npc.race and npc.race.name else "").lower()
    role = dict(rules.get("default", {}))
    for rule in rules.get("rules", ()):
        if _matches(rule.get("match", {}), names, factions, ids, gear, race):
            role = {**role, **rule.get("role", {})}
            break
    seed = npc.reference.form_id.lower()
    spread = float(rules.get("trait_spread", 0.2))
    traits = {}
    for index, key in enumerate(("warmth", "caution", "patience", "assertiveness")):
        base = float(role.get("traits", {}).get(key, 0.5))
        traits[key] = round(min(1.0, max(0.0, base + (_unit(seed, index) - 0.5) * 2 * spread)), 2)
    style = list(role.get("speech_style", ()))
    pool = rules.get("style_pool") or ()
    if pool:
        pick = pool[int(_unit(seed, 9) * 255) % len(pool)]
        if pick not in style:
            style.append(pick)
    # World knowledge first, then the hold's Jarl when the place is known, then what the role adds.
    knowledge = list(rules.get("world_common_knowledge", ()))
    place = _place(snapshot)
    haystack = " ".join(filter(None, [place and place.lower(), snapshot.cell.name.lower() if snapshot.cell and snapshot.cell.name else None, *factions]))
    for hold in rules.get("holds", ()):
        if any(_word(k, haystack) for k in hold.get("keys", ())):
            knowledge.append(hold["line"])
            break
    knowledge += role.get("common_knowledge", ())
    return Persona(
        name=name, occupation=role.get("occupation", "townsperson"), social_role=role.get("social_role", "local resident"),
        speech_style=tuple(style[:8]), goals=tuple(role.get("goals", ()))[:8], boundaries=tuple(role.get("boundaries", ()))[:8],
        service_role=bool(role.get("service_role", False)), location=place,
        common_knowledge=tuple(k[:140] for k in knowledge[:6]), services=tuple(role.get("services", ()))[:SERVICES_MAX], **traits)


def time_of_day(hour: float) -> str:
    return ("night" if hour < 5 or hour >= 21 else "dawn" if hour < 7 else "morning" if hour < 12
            else "afternoon" if hour < 17 else "evening")


def build_scene(snapshot) -> tuple[SceneItem, ...]:
    """What the NPC can perceive right now. No quest, dialogue-list or hidden state."""
    items = []

    def add(label, value):
        if value:
            items.append(SceneItem(label=label, value=value[:80]))

    place = _place(snapshot)
    add("place", f"{place}, {'indoors' if snapshot.interior else 'outdoors'}" if place else ("indoors" if snapshot.interior else "outdoors"))
    add("time", time_of_day(snapshot.hour))
    if not snapshot.interior and snapshot.weather_label:
        add("weather", snapshot.weather_label.replace("_", " "))
    npc = snapshot.npc
    add("your_gear", ", ".join(dict.fromkeys(f.name for f in npc.equipment if f.name)))
    if npc.sees_player:
        player = snapshot.player
        add("player_gear", ", ".join(dict.fromkeys(f.name for f in player.equipment if f.name)))
        add("player_weapon", "drawn" if player.weapon_drawn else "sheathed")
    return tuple(items)
