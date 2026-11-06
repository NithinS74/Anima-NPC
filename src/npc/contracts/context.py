"""Initial v0.1 context-boundary schemas. Other pipeline contracts are deferred."""

from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StrictFloat,
    StrictInt,
    StringConstraints,
    model_validator,
)

Identifier = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=128)]
ShortText = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=512)]
SourceReference = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=160)]
Dimension = Literal["engagement", "tone", "length", "disclosure", "knowledge"]
Score = Annotated[StrictInt, Field(ge=-100, le=100)]
Level = Annotated[StrictInt, Field(ge=0, le=100)]
Probability = Annotated[StrictFloat, Field(ge=0, le=1)]
Nonnegative = Annotated[StrictInt, Field(ge=0)]
SimulationTime = Annotated[StrictFloat, Field(ge=0)]
Scalar = StrictBool | StrictInt | StrictFloat | ShortText


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False, validate_default=True)


class Scope(Contract):
    game_id: Identifier
    world_id: Identifier
    save_branch_id: Identifier


Brief = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=140)]


class Persona(Contract):
    name: ShortText
    occupation: ShortText
    social_role: ShortText
    speech_style: Annotated[tuple[ShortText, ...], Field(max_length=8)] = ()
    goals: Annotated[tuple[ShortText, ...], Field(max_length=8)] = ()
    boundaries: Annotated[tuple[ShortText, ...], Field(max_length=8)] = ()
    service_role: StrictBool = False
    warmth: Probability = 0.5
    caution: Probability = 0.5
    patience: Probability = 0.5
    assertiveness: Probability = 0.5
    swearing: Literal["never", "when_provoked"] = "never"
    # Optional authored world grounding. Generic: games supply the content (fixtures/config), never core code.
    location: Brief | None = None
    common_knowledge: Annotated[tuple[Brief, ...], Field(max_length=6)] = ()
    services: Annotated[tuple[Brief, ...], Field(max_length=6)] = ()


class Relationship(Contract):
    favourability: Score = 0
    trust: Score = 0
    familiarity: Level = 0
    fear: Level = 0
    irritation: Level = 0


class NpcState(Contract):
    """Optional transient state with independent freshness, not timeless truth."""

    observed_at: AwareDatetime
    ttl_ms: Annotated[StrictInt, Field(gt=0, le=60000)]
    mood: Literal["neutral", "calm", "angry", "tired", "fearful"] = "neutral"
    current_goal: ShortText | None = None


class DialogueMemory(Contract):
    request_id: Identifier
    player_text: Annotated[str, Field(strict=True, max_length=4000)]
    npc_text: Annotated[str, Field(strict=True, max_length=2000)]
    mode: Literal["speech", "silence", "end"] = "speech"
    source: Literal["console_display", "game_completed"] = "console_display"


class SocialAppraisal(Contract):
    stimulus: Literal["neutral", "incidental_profanity", "directed_insult", "threat", "apology", "gratitude", "rough_banter"] = "neutral"
    willingness: Literal["engage", "brief", "boundary", "disengage", "withdraw"] = "brief"
    tone: Literal["neutral", "warm", "guarded", "sarcastic", "angry", "fearful"] = "neutral"
    allow_swearing: StrictBool = False
    reasons: Annotated[tuple[Identifier, ...], Field(max_length=8)] = ()
    policy_version: Literal["0.1"] = "0.1"


TurnType = Literal["new", "repeat", "rephrase", "follow_up", "push_back", "shared_news", "stall", "answered", "return"]
Move = Literal["answer", "expand", "answer_differently", "challenge", "close_topic", "reconsider", "admit_limit",
               "hold", "react", "follow_through", "recall", "take_initiative", "opening", "farewell"]
Snippet = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=160)]


class TopicRecord(Contract):
    text: Snippet
    asked: Annotated[StrictInt, Field(ge=1, le=99)] = 1
    last_turn: Nonnegative = 0
    exhausted: StrictBool = False


class ConversationState(Contract):
    """Bounded record of what happened in a conversation. Never knowledge, trust or authority."""

    turns: Nonnegative = 0
    topics: Annotated[tuple[TopicRecord, ...], Field(max_length=16)] = ()
    told: Annotated[tuple[Identifier, ...], Field(max_length=8)] = ()  # evidence IDs already given
    replies: Annotated[tuple[Snippet, ...], Field(max_length=4)] = ()  # recent NPC replies
    claims: Annotated[tuple[Snippet, ...], Field(max_length=8)] = ()  # player claims, never facts
    phrases: Annotated[tuple[Annotated[str, StringConstraints(strict=True, min_length=1, max_length=48)], ...], Field(max_length=8)] = ()
    last_type: TurnType | None = None
    last_move: Move | None = None
    open_question: StrictBool = False
    rapport: Level = 0


class TurnReading(Contract):
    """How the current player turn relates to the conversation so far."""

    type: TurnType = "new"
    topic: Snippet | None = None
    asked: Nonnegative = 0
    new_words: Nonnegative = 0
    similarity: Annotated[StrictFloat, Field(ge=0, le=1)] = 0.0


class StateSnapshot(Contract):
    schema_version: Literal["0.1"] = "0.1"
    scope: Scope
    npc_id: Identifier
    player_id: Identifier
    storage_revision: Nonnegative
    dialogue_revision: Nonnegative
    turn_epoch: Nonnegative
    persona: Persona
    relationship: Relationship = Field(default_factory=Relationship)
    npc_state: NpcState | None = None
    recent_dialogue: Annotated[tuple[DialogueMemory, ...], Field(max_length=8)] = ()
    conversation: ConversationState = Field(default_factory=ConversationState)
    reading: TurnReading | None = None


class PlayerInput(Contract):
    text: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)]
    source: Literal["text", "stt"] = "text"
    confidence: Probability = 1.0


class VisualContext(Contract):
    """Bounded CV descriptor available to context assembly, never canonical game truth."""

    id: Identifier
    captured_at: AwareDatetime
    environment: ShortText | None = None
    characters: Annotated[tuple[ShortText, ...], Field(max_length=4)] = ()
    objects: Annotated[tuple[ShortText, ...], Field(max_length=8)] = ()
    uncertainties: Annotated[tuple[ShortText, ...], Field(max_length=4)] = ()
    detector_model: Identifier | None = None
    vlm_model: Identifier | None = None

    def prompt_payload(self) -> dict:
        return {
            "environment": self.environment, "characters": self.characters,
            "objects": self.objects, "uncertainties": self.uncertainties,
            "source": {"detector_model": self.detector_model, "vlm_model": self.vlm_model},
        }


BOOLEAN_PATHS = frozenset({"npc.in_combat", "npc.busy", "shop.open", "player.weapon_drawn"})
TEXT_PATHS = frozenset({"world.location", "world.weather"})
SUPPORTED_PATHS = BOOLEAN_PATHS | TEXT_PATHS | {"world.hour"}


class ObservedFact(Contract):
    id: Identifier
    path: Identifier
    value: Scalar
    source: Identifier
    source_kind: Literal["telemetry", "vision", "player"]
    subject_id: Identifier | None = None
    captured_at: AwareDatetime
    simulation_time_s: SimulationTime
    ttl_ms: Annotated[StrictInt, Field(gt=0, le=60000)]
    confidence: Probability
    perceivers: Annotated[tuple[Identifier, ...], Field(max_length=32)] = ()

    @model_validator(mode="after")
    def check_fact_value(self) -> "ObservedFact":
        if self.path in BOOLEAN_PATHS and type(self.value) is not bool:
            raise ValueError(f"{self.path} requires a boolean, not a coerced number/string")
        if self.path in TEXT_PATHS and not isinstance(self.value, str):
            raise ValueError(f"{self.path} requires text")
        if self.path == "world.hour":
            if type(self.value) not in (int, float) or not 0 <= self.value < 24:
                raise ValueError("world.hour requires a number in [0, 24)")
        if (self.path.startswith(("npc.", "player.")) or self.path == "shop.open") and self.subject_id is None:
            raise ValueError("actor observations require subject_id")
        return self


class SceneItem(Contract):
    """One perceivable detail of the scene (adapter-supplied). Data only: it grants no knowledge and changes no policy."""

    label: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=32)]
    value: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)]


class TurnInput(Contract):
    schema_version: Literal["0.1"] = "0.1"
    scope: Scope
    request_id: Identifier
    session_id: Identifier
    npc_id: Identifier
    player_id: Identifier
    sequence: Nonnegative
    expected_dialogue_revision: Nonnegative
    captured_at: AwareDatetime
    simulation_time_s: SimulationTime
    player_input: PlayerInput
    facts: Annotated[tuple[ObservedFact, ...], Field(max_length=100)] = ()
    scene: Annotated[tuple[SceneItem, ...], Field(max_length=8)] = ()

    @model_validator(mode="after")
    def check_payload(self) -> "TurnInput":
        ids = [fact.id for fact in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("observation IDs must be unique within a turn")
        if len(self.model_dump_json().encode("utf-8")) > 256 * 1024:
            raise ValueError("turn exceeds the 256 KB canonical payload limit")
        return self


class Exclusion(Contract):
    fact_id: Identifier
    reason: Literal[
        "unsupported_path", "player_claim", "not_perceived", "wrong_subject",
        "future", "expired", "low_confidence", "superseded", "ambiguous_conflict",
    ]


class Conflict(Contract):
    path: Identifier
    fact_ids: tuple[Identifier, ...]
    selected_id: Identifier | None


class Influence(Contract):
    rule: Identifier
    dimension: Dimension
    effect: ShortText
    source_ids: tuple[SourceReference, ...]


class AppraisalDependency(Contract):
    field: Literal["availability", "threat", "recognition", "trust_stance", "mood", "current_goal"]
    value: Scalar | None
    reason: Literal["observed_state", "relationship_threshold", "fresh_npc_state", "no_eligible_evidence"]
    source_ids: Annotated[tuple[SourceReference, ...], Field(max_length=4)]


class Situation(Contract):
    schema_version: Literal["0.1"] = "0.1"
    appraisal_version: Literal["0.1"] = "0.1"
    scope: Scope
    request_id: Identifier
    npc_id: Identifier
    player_id: Identifier
    dialogue_revision: Nonnegative
    turn_epoch: Nonnegative
    persona: Persona
    relationship: Relationship
    player_input: PlayerInput
    player_input_trust: Literal["unverified_utterance"] = "unverified_utterance"
    availability: Literal["unknown", "available", "busy", "closed", "in_combat"]
    threat: Literal["unknown", "none", "cautious", "high", "immediate"]
    recognition: Literal["stranger", "familiar"]
    trust_stance: Literal["guarded", "neutral", "trusting"]
    mood: Literal["unknown", "neutral", "calm", "angry", "tired", "fearful"]
    current_goal: ShortText | None
    perceived_facts: tuple[ObservedFact, ...]
    exclusions: tuple[Exclusion, ...]
    conflicts: tuple[Conflict, ...]
    influences: tuple[Influence, ...]
    dependencies: Annotated[tuple[AppraisalDependency, ...], Field(min_length=6, max_length=6)]
    notes: tuple[ShortText, ...] = ()
    social_appraisal: SocialAppraisal = Field(default_factory=SocialAppraisal)
    visual_context: VisualContext | None = None
    recent_dialogue: Annotated[tuple[DialogueMemory, ...], Field(max_length=8)] = ()
    conversation: ConversationState = Field(default_factory=ConversationState)
    reading: TurnReading | None = None
    scene: Annotated[tuple[SceneItem, ...], Field(max_length=8)] = ()

    @model_validator(mode="after")
    def check_dependencies(self) -> "Situation":
        if len({item.field for item in self.dependencies}) != 6:
            raise ValueError("appraisal dependencies must cover each field exactly once")
        if any(item.value != getattr(self, item.field) for item in self.dependencies):
            raise ValueError("appraisal dependency values must match the situation")
        return self


class AdapterContext(Contract):
    """Opaque adapter observations at pipeline ingress, not authorized NPC knowledge."""

    source: Identifier
    payload: dict[str, JsonValue]

    @model_validator(mode="after")
    def bound_payload(self) -> "AdapterContext":
        if len(self.model_dump_json().encode("utf-8")) > 256 * 1024:
            raise ValueError("adapter context exceeds the 256 KB payload limit")
        return self


class ContextScenario(Contract):
    now: AwareDatetime
    turn: TurnInput
    snapshot: StateSnapshot
    adapter_context: AdapterContext | None = None
