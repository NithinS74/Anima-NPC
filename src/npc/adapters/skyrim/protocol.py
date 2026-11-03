"""Versioned game/bridge contracts. Raw Skyrim observations stay at this boundary."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import Field, StrictInt, field_validator

from npc.contracts.context import (
    Contract, ContextScenario, Identifier, ObservedFact, Persona, PlayerInput,
    Scope, StateSnapshot, TurnInput, NpcState,
)

Text = Annotated[str, Field(strict=True, max_length=2000)]
HexID = Annotated[str, Field(strict=True, pattern=r"^[0-9A-Fa-f]{8}$")]


class Form(Contract):
    form_id: HexID
    local_id: HexID
    plugin: Annotated[str, Field(strict=True, max_length=128)] = ""
    name: Annotated[str, Field(strict=True, max_length=512)] = ""

    @property
    def definition_key(self):
        return f"{self.plugin.lower()}:{self.local_id.lower()}"


class ActorData(Contract):
    reference: Form
    base: Form
    race: Form | None = None
    voice: Form | None = None
    sex: StrictInt | None = None
    in_combat: bool
    dead: bool
    weapon_drawn: bool
    sees_player: bool | None = None
    hostile_to_player: bool | None = None
    factions: Annotated[tuple[Form, ...], Field(max_length=64)] = ()
    equipment: Annotated[tuple[Form, ...], Field(max_length=2)] = ()


class DialogueOption(Contract):
    topic: Form
    info: Form | None = None
    player_text: Text
    responses: Annotated[tuple[Text, ...], Field(max_length=32)] = ()
    quest: Form | None = None
    quest_stage: StrictInt | None = None
    provenance: Literal["engine_dialogue_menu"] = "engine_dialogue_menu"


class GameSnapshot(Contract):
    npc: ActorData
    player: ActorData
    location: Form | None = None
    cell: Form | None = None
    interior: bool
    hour: float = Field(ge=0, lt=24, allow_inf_nan=False)
    game_days: float = Field(ge=0, allow_inf_nan=False)
    weather: Form | None = None
    weather_label: Annotated[str, Field(strict=True, max_length=128)] | None = None
    dialogue: Annotated[tuple[DialogueOption, ...], Field(max_length=64)] = ()
    dialogue_complete: bool = False


class GameEvent(Contract):
    schema_version: Literal["0.1"] = "0.1"
    event_id: Identifier
    session_id: Identifier
    game_epoch: Identifier
    sequence: Annotated[StrictInt, Field(ge=0)]
    state_revision: Annotated[StrictInt, Field(ge=0)] = 0
    captured_at_ms: Annotated[StrictInt, Field(ge=0)]
    game_pid: Annotated[StrictInt, Field(gt=0)]
    kind: Literal["start", "snapshot", "end", "listen_start", "listen_stop", "delivery", "player_text"]
    snapshot: GameSnapshot | None = None
    text: Annotated[str, Field(strict=True, min_length=1, max_length=4000)] | None = None
    delivery_id: Identifier | None = None
    status: Literal["started", "completed", "interrupted", "failed"] | None = None


class SpeechInput(Contract):
    session_id: Identifier
    input_id: Identifier
    text: Annotated[str, Field(strict=True, min_length=1, max_length=4000)]
    source: Literal["text", "stt"] = "text"
    confidence: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)


class PipelineResult(Contract):
    session_id: Identifier
    request_id: Identifier
    npc_id: Identifier
    mode: Literal["speech", "silence", "end"] = "speech"
    text: Text = ""
    # Trusted local pipeline artifact, constrained to the configured audio root.
    audio_path: Annotated[str, Field(strict=True, max_length=1024)] | None = None


class NpcProfile(Contract):
    persona: Persona
    # Explicitly authored knowledge bindings; game mechanics do not imply knowledge.
    knowledge_sources: Annotated[tuple[Text, ...], Field(max_length=16)] = ()


class Settings(Contract):
    game_directory: str
    output_directory: str = "output/skyrim"
    profiles_file: str | None = None
    world_id: Identifier = "local-skyrim"
    pipeline_mode: Literal["inbox", "http", "preview"] = "inbox"
    pipeline_url: str | None = None
    tts_url: str | None = None
    stt_url: str | None = None
    cv_url: str | None = None
    cv_timeout_s: float = Field(default=8, ge=1, le=15)
    visual_ttl_s: float = Field(default=15, ge=1, le=60)
    attach_visual_reference: bool = False
    rag_config: str | None = None
    provider_profile: str = "configs/providers/offline.yaml"
    audio_root: str = "output/pipeline/audio"
    state_db: str | None = "output/skyrim/social.sqlite3"
    port: int = Field(default=8768, ge=1024, le=65535)
    timeout_s: float = Field(default=30, ge=1, le=60)
    capture_screenshots: bool = True
    max_screenshots: int = Field(default=100, ge=1, le=1000)
    max_output_bytes: int = Field(default=250 * 1024 * 1024, ge=1024, le=2 * 1024**3)

    @field_validator("cv_url")
    @classmethod
    def cv_origin(cls, value):
        from npc.vision.client import validate_cv_url
        return validate_cv_url(value) if value is not None else None

    @field_validator("pipeline_url", "tts_url", "stt_url")
    @classmethod
    def local_endpoint(cls, value):
        if value is None:
            return value
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username or parsed.password or parsed.fragment or parsed.query):
            raise ValueError("connector endpoints must be credential-free loopback HTTP URLs")
        return value


def npc_id(snapshot: GameSnapshot) -> str:
    return "ref:" + snapshot.npc.reference.form_id.lower()


def profile_for(snapshot: GameSnapshot, profiles: dict[str, NpcProfile]) -> NpcProfile:
    profile = profiles.get(snapshot.npc.base.definition_key)
    if profile:
        return profile
    return NpcProfile(persona=Persona(
        name=snapshot.npc.reference.name or snapshot.npc.base.name or "Unknown NPC",
        occupation="unknown", social_role="unknown", speech_style=(),
        boundaries=("Background and private knowledge are unknown unless explicitly supplied.",),
    ))


def canonical_scenario(event: GameEvent, speech: SpeechInput, profile: NpcProfile,
                       world_id: str, revision: int, *, now: datetime | None = None, social_state=None) -> ContextScenario:
    """Small executable core view; full game context travels beside it to the pipeline."""
    data = event.snapshot
    if data is None:
        raise ValueError("snapshot required")
    now = now or datetime.now(timezone.utc)
    npc, player = npc_id(data), "ref:" + data.player.reference.form_id.lower()
    scope = Scope(game_id="skyrim", world_id=world_id, save_branch_id=event.game_epoch)
    facts = []

    observed_at = datetime.fromtimestamp(event.captured_at_ms / 1000, timezone.utc)

    def add(path, value, subject=None):
        facts.append(ObservedFact(
            id=f"{speech.input_id}:{len(facts)}", path=path, value=value, source="anima-skse",
            source_kind="telemetry", subject_id=subject, captured_at=observed_at,
            simulation_time_s=float(data.game_days * 86400), ttl_ms=5000,
            confidence=1.0, perceivers=(npc,),
        ))

    add("npc.in_combat", data.npc.in_combat, npc)
    if data.npc.sees_player:
        add("player.weapon_drawn", data.player.weapon_drawn, player)
    if data.location and data.location.name:
        add("world.location", data.location.name)
    add("world.hour", data.hour)
    if not data.interior and data.weather_label:
        add("world.weather", data.weather_label)
    turn = TurnInput(scope=scope, request_id=speech.input_id, session_id=event.session_id,
                     npc_id=npc, player_id=player, sequence=event.sequence,
                     expected_dialogue_revision=revision, captured_at=now,
                     simulation_time_s=float(data.game_days * 86400),
                     player_input=PlayerInput(text=speech.text, source=speech.source,
                                              confidence=speech.confidence), facts=tuple(facts))
    state = StateSnapshot(scope=scope, npc_id=npc, player_id=player,
                          storage_revision=social_state["revision"] if social_state else revision,
                          dialogue_revision=revision, turn_epoch=revision,
                          persona=profile.persona,
                          **({"relationship": social_state["relationship"], "recent_dialogue": social_state["history"],
                              "npc_state": NpcState(observed_at=now, ttl_ms=60000, mood=social_state["mood"])}
                             if social_state else {}))
    return ContextScenario(now=now, turn=turn, snapshot=state)
