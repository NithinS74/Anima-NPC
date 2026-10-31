"""Test fixture composition only; generation remains in npc.runtime."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StringConstraints

from npc.context import build_situation
from npc.contracts.context import Contract, ContextScenario, Identifier, Persona, Relationship
from npc.runtime.preview import PreviewLimits, PreviewRunner

ROOT = Path(__file__).resolve().parents[2]
PROFILE_DIR = ROOT / "fixtures/personas/npc_lab"
Mood = Literal["neutral", "calm", "angry", "tired", "fearful"]


class LabProfile(Contract):
    id: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,31}$", strict=True)]
    world: Identifier
    location: Annotated[str, Field(strict=True, min_length=1, max_length=80)]
    tagline: Annotated[str, Field(strict=True, min_length=1, max_length=120)]
    persona: Persona
    relationship: Relationship
    mood: Mood
    current_goal: Annotated[str, Field(strict=True, min_length=1, max_length=100)]
    starters: Annotated[tuple[Annotated[str, Field(strict=True, max_length=160)], ...], Field(min_length=1, max_length=5)]
    testing_notes: Annotated[str, Field(strict=True, min_length=1, max_length=400)]


class LabTurn(Contract):
    request_id: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9-]{1,64}$", strict=True)]
    persona_id: Identifier
    text: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)]
    relationship: Relationship
    mood: Mood
    state: Literal["available", "busy", "closed", "combat"] = "available"
    weapon_drawn: StrictBool = False


class CancelRequest(Contract):
    request_id: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9-]{1,64}$", strict=True)]


def load_profiles(directory: Path = PROFILE_DIR) -> dict[str, LabProfile]:
    paths = sorted(directory.glob("*.json"))
    if not 1 <= len(paths) <= 16:
        raise ValueError("expected 1 to 16 lab profiles")
    profiles = {}
    for path in paths:
        if path.stat().st_size > 16384:
            raise ValueError("profile exceeds 16 KB")
        profile = LabProfile.model_validate_json(path.read_text(encoding="utf-8"))
        if profile.id in profiles or path.stem != profile.id:
            raise ValueError("profile ID must be unique and match its filename")
        profiles[profile.id] = profile
    return profiles


def make_scenario(profile: LabProfile, turn: LabTurn, revision: int) -> ContextScenario:
    now = datetime.now(timezone.utc)
    scope = {"game_id": "manual-lab", "world_id": profile.world, "save_branch_id": "isolated-test"}
    npc = "lab-" + profile.id
    facts = []
    for name, path, value, subject in [
        ("combat", "npc.in_combat", turn.state == "combat", npc),
        ("busy", "npc.busy", turn.state == "busy", npc),
        ("weapon", "player.weapon_drawn", turn.weapon_drawn, "lab-player"),
        ("location", "world.location", profile.location, None),
    ]:
        facts.append(dict(id=name, path=path, value=value, subject_id=subject, source="manual-lab",
                          source_kind="telemetry", captured_at=now, simulation_time_s=0.0,
                          ttl_ms=60000, confidence=1.0, perceivers=[npc]))
    if profile.persona.service_role:
        facts.append(dict(id="service", path="shop.open", value=turn.state != "closed", subject_id=npc,
                          source="manual-lab", source_kind="telemetry", captured_at=now, simulation_time_s=0.0,
                          ttl_ms=60000, confidence=1.0, perceivers=[npc]))
    elif turn.state == "closed":
        raise ValueError("closed applies only to service-role NPCs")
    return ContextScenario.model_validate(dict(now=now, turn=dict(
        scope=scope, request_id=turn.request_id, session_id="manual-console", npc_id=npc, player_id="lab-player",
        sequence=revision, expected_dialogue_revision=revision, captured_at=now, simulation_time_s=0.0,
        player_input={"text": turn.text}, facts=facts,
    ), snapshot=dict(
        scope=scope, npc_id=npc, player_id="lab-player", storage_revision=revision,
        dialogue_revision=revision, turn_epoch=revision, persona=profile.persona.model_dump(),
        relationship=turn.relationship.model_dump(), npc_state=dict(observed_at=now, ttl_ms=60000,
        mood=turn.mood, current_goal=profile.current_goal),
    )))


class LabService:
    def __init__(self, provider, *, live: bool = False, realtime: bool = False, profiles=None):
        self.profiles = profiles if profiles is not None else load_profiles()
        self.live = live
        self.realtime = realtime
        # Lab profiles/controls measured at 2.1 KiB. Keep a declared bound rather
        # than truncating identity/state; core CLI defaults remain unchanged.
        limits = PreviewLimits(max_input_bytes=3072) if realtime else PreviewLimits(
            response_timeout_ms=10000, model_cutoff_ms=9450, max_input_bytes=3072)
        self.runner = PreviewRunner(provider, limits)
        self.active: tuple[str, asyncio.Event] | None = None
        self.revision = 0

    def info(self):
        return dict(mode="live" if self.live else "offline fake", timing_profile="realtime" if self.realtime else "development",
                    deadline_ms=self.runner.limits.response_timeout_ms,
                    input_budget_bytes=self.runner.limits.max_input_bytes,
                    profiles=[p.model_dump(mode="json") for p in self.profiles.values()],
                    memory="Single-turn context. Chat history is display-only; no conversation memory.")

    async def turn(self, turn: LabTurn):
        if self.active is not None:
            return {"error": "lab_busy"}
        if turn.persona_id not in self.profiles:
            raise ValueError("unknown profile")
        self.revision += 1
        scenario = make_scenario(self.profiles[turn.persona_id], turn, self.revision)
        cancellation = asyncio.Event()
        self.active = (turn.request_id, cancellation)
        try:
            situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
            result = await self.runner.run(scenario, cancellation=cancellation)
            return {"result": result.model_dump(mode="json"), "context": situation.model_dump(mode="json")}
        finally:
            self.active = None

    async def cancel(self, request: CancelRequest):
        matched = self.active is not None and self.active[0] == request.request_id
        if matched:
            self.active[1].set()
        return {"cancelled": matched}
