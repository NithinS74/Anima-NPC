"""Test fixture composition only; generation remains in npc.runtime."""

import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal
from time import monotonic

from pydantic import Field, StrictBool, StrictInt, StringConstraints

from npc.context import build_situation
from npc.contracts.context import Contract, ContextScenario, Identifier, Persona, Relationship
from npc.runtime.preview import PreviewLimits, PreviewRunner
from npc.state.social_store import SocialStore

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
    state_revision: Annotated[StrictInt, Field(ge=0)] | None = None


class CancelRequest(Contract):
    request_id: Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9-]{1,64}$", strict=True)]


class LabStateEdit(Contract):
    persona_id: Identifier
    relationship: Relationship
    mood: Mood
    state_revision: Annotated[StrictInt, Field(ge=0)]


class DisplayAck(CancelRequest):
    persona_id: Identifier


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


def make_scenario(profile: LabProfile, turn: LabTurn, revision: int, memory=()) -> ContextScenario:
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
        relationship=turn.relationship.model_dump(), recent_dialogue=[m.model_dump() for m in memory], npc_state=dict(observed_at=now, ttl_ms=60000,
        mood=turn.mood, current_goal=profile.current_goal),
    )))


class LabService:
    def __init__(self, provider, *, live: bool = False, realtime: bool = False, development_timeout_s: int = 30, profiles=None, media=None, state_store: SocialStore | None = None):
        self.profiles = profiles if profiles is not None else load_profiles()
        self.live = live
        self.realtime = realtime
        if type(development_timeout_s) is not int or not 1 <= development_timeout_s <= 60:
            raise ValueError("development timeout must be 1..60 seconds")
        # Lab profiles/controls measured at 2.1 KiB. Keep a declared bound rather
        # than truncating identity/state; core CLI defaults remain unchanged.
        limits = PreviewLimits(max_input_bytes=3072) if realtime else PreviewLimits(
            response_timeout_ms=development_timeout_s * 1000,
            model_cutoff_ms=min(59000, development_timeout_s * 1000 - 550), max_input_bytes=3072)
        self.runner = PreviewRunner(provider, limits)
        self.active: tuple[str, asyncio.Event] | None = None
        self.revision = 0
        self.media = media
        self.speech_records = OrderedDict()
        self.state_store = state_store
        self.active_profile = None
        if state_store:
            for profile in self.profiles.values():
                state_store.ensure(self.state_key(profile.id), profile.relationship, profile.mood)

    def state_key(self, persona_id):
        profile = self.profiles[persona_id]
        from npc.contracts.context import Scope
        return SocialStore.key(Scope(game_id="manual-lab", world_id=profile.world, save_branch_id="isolated-test"),
                               "lab-" + profile.id, "lab-player")

    @staticmethod
    def public_state(state):
        return dict(relationship=state["relationship"].model_dump(), mood=state["mood"], state_revision=state["revision"],
                    history=[m.model_dump(mode="json") for m in state["history"]])

    def profile_info(self, profile):
        data = profile.model_dump(mode="json")
        data["media"] = self.media.describe(profile.id) if self.media else dict(voice_available=False, voice=None, model_url=None)
        if self.state_store:
            data.update(self.public_state(self.state_store.load(self.state_key(profile.id))))
        return data

    def info(self):
        return dict(mode="live" if self.live else "offline fake", timing_profile="realtime" if self.realtime else "development",
                    deadline_ms=self.runner.limits.response_timeout_ms,
                    input_budget_bytes=self.runner.limits.max_input_bytes,
                    background_url=self.media.background_url() if self.media else None,
                    profiles=[self.profile_info(p) for p in self.profiles.values()],
                    persistent_state=self.state_store is not None,
                    memory="Relationships persist; recent displayed dialogue is untrusted memory." if self.state_store else
                    "Single-turn context. Chat history is display-only; no conversation memory.")

    async def turn(self, turn: LabTurn):
        if self.active is not None:
            return {"error": "lab_busy"}
        if turn.persona_id not in self.profiles:
            raise ValueError("unknown profile")
        if turn.state == "closed" and not self.profiles[turn.persona_id].persona.service_role:
            raise ValueError("closed applies only to service-role NPCs")
        self.revision += 1
        state, audit, memory = None, None, ()
        if self.state_store:
            if turn.state_revision is None:
                raise ValueError("state revision required")
            from npc.contracts.context import PlayerInput
            state, audit, cached = self.state_store.begin_turn(self.state_key(turn.persona_id), turn.request_id,
                PlayerInput(text=turn.text), self.profiles[turn.persona_id].persona, turn.state_revision)
            if cached:
                cached["cached"] = True
                cached["saved_state"] = self.public_state(state)
                return cached
            data = turn.model_dump(); data.update(relationship=state["relationship"].model_dump(), mood=state["mood"])
            turn = LabTurn.model_validate(data)
            memory = state["history"]
        scenario = make_scenario(self.profiles[turn.persona_id], turn, state["revision"] if state else self.revision, memory)
        cancellation = asyncio.Event()
        self.active = (turn.request_id, cancellation)
        self.active_profile = turn.persona_id
        try:
            situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
            result = await self.runner.run(scenario, cancellation=cancellation)
            payload = {"result": result.model_dump(mode="json"), "context": situation.model_dump(mode="json")}
            if state:
                payload.update(social_change=audit, saved_state=self.public_state(state))
                if result.status != "cancelled":
                    self.state_store.stage_preview(self.state_key(turn.persona_id), turn.request_id, payload, state["revision"])
            if result.response and result.response.mode == "speech" and result.response.text:
                self.speech_records[turn.request_id] = (turn.persona_id, result.response.text, monotonic())
                while len(self.speech_records) > 8:
                    self.speech_records.popitem(last=False)
            return payload
        finally:
            self.active = None
            self.active_profile = None

    async def cancel(self, request: CancelRequest):
        matched = self.active is not None and self.active[0] == request.request_id
        if matched:
            self.active[1].set()
            if self.state_store:
                self.state_store.cancel(self.state_key(self.active_profile), request.request_id)
        self.speech_records.pop(request.request_id, None)
        voice_cancelled = await self.media.cancel(request.request_id) if self.media else False
        return {"cancelled": matched or voice_cancelled}

    async def speech(self, request: CancelRequest):
        record = self.speech_records.get(request.request_id)
        if self.media is None or record is None or monotonic() - record[2] > 300:
            raise ValueError("validated speech unavailable")
        return await self.media.synthesize(request.request_id, record[0], record[1])

    async def edit_state(self, request: LabStateEdit):
        if self.active:
            return {"error": "lab_busy"}
        if self.state_store is None or request.persona_id not in self.profiles:
            raise ValueError("persistent state unavailable")
        state = self.state_store.override(self.state_key(request.persona_id), request.relationship, request.mood, request.state_revision)
        return self.public_state(state)

    async def displayed(self, request: DisplayAck):
        if self.state_store is None or request.persona_id not in self.profiles:
            raise ValueError("persistent state unavailable")
        state = self.state_store.displayed(self.state_key(request.persona_id), request.request_id)
        return self.public_state(state)
