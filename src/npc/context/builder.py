"""Pure context appraisal; final engagement decisions belong to behavior policy."""

from datetime import datetime

from npc.contracts.context import (
    SUPPORTED_PATHS, AppraisalDependency, Conflict, Dimension, Exclusion, Influence, ObservedFact,
    Situation, StateSnapshot, TurnInput,
)

SOURCE_PRIORITY = {"telemetry": 2, "vision": 1}
MIN_CONFIDENCE = 0.6


class ContextMismatch(ValueError):
    """A turn and snapshot cannot describe the same current interaction."""


def _freshness(captured_at: datetime, ttl_ms: int, now: datetime) -> str | None:
    age_ms = (now - captured_at).total_seconds() * 1000
    if age_ms < 0:
        return "future"
    if age_ms >= ttl_ms:
        return "expired"
    return None


def _resolve(
    turn: TurnInput, now: datetime,
) -> tuple[tuple[ObservedFact, ...], tuple[Exclusion, ...], tuple[Conflict, ...]]:
    groups: dict[str, list[ObservedFact]] = {}
    exclusions: list[Exclusion] = []
    conflicts: list[Conflict] = []
    for fact in turn.facts:
        reason = None
        if fact.path not in SUPPORTED_PATHS:
            reason = "unsupported_path"
        elif fact.source_kind == "player":
            reason = "player_claim"
        elif turn.npc_id not in fact.perceivers:
            reason = "not_perceived"
        elif (
            ((fact.path.startswith("npc.") or fact.path == "shop.open") and fact.subject_id != turn.npc_id)
            or (fact.path.startswith("player.") and fact.subject_id != turn.player_id)
        ):
            reason = "wrong_subject"
        elif fact.simulation_time_s > turn.simulation_time_s:
            reason = "future"
        else:
            reason = _freshness(fact.captured_at, fact.ttl_ms, now)
            if reason is None and fact.confidence < MIN_CONFIDENCE:
                reason = "low_confidence"
        if reason:
            exclusions.append(Exclusion(fact_id=fact.id, reason=reason))
        else:
            groups.setdefault(fact.path, []).append(fact)

    selected = []
    for path, facts in sorted(groups.items()):
        rank = lambda fact: (SOURCE_PRIORITY[fact.source_kind], fact.captured_at)
        best_rank = max(map(rank, facts))
        leaders = [fact for fact in facts if rank(fact) == best_rank]
        ambiguous = any(fact.value != leaders[0].value for fact in leaders)
        winner = None if ambiguous else min(leaders, key=lambda fact: fact.id)
        if any(fact.value != facts[0].value for fact in facts):
            conflicts.append(Conflict(
                path=path, fact_ids=tuple(sorted(fact.id for fact in facts)),
                selected_id=winner.id if winner else None,
            ))
        if winner:
            selected.append(winner)
        for fact in facts:
            if winner is None or fact.id != winner.id:
                exclusions.append(Exclusion(
                    fact_id=fact.id,
                    reason="ambiguous_conflict" if ambiguous else "superseded",
                ))
    return tuple(selected), tuple(sorted(exclusions, key=lambda item: item.fact_id)), tuple(conflicts)


def build_situation(turn: TurnInput, snapshot: StateSnapshot, now: datetime) -> Situation:
    """Appraise validated canonical inputs; never mutate them or grant knowledge.

    Source kinds, perceivers and the snapshot must come from trusted upstream
    connectors/storage, not directly from arbitrary player-provided JSON.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    for field in ("scope", "npc_id", "player_id"):
        if getattr(turn, field) != getattr(snapshot, field):
            raise ContextMismatch(f"turn/snapshot {field} mismatch")
    if turn.expected_dialogue_revision != snapshot.dialogue_revision:
        raise ContextMismatch("stale dialogue revision")
    if turn.captured_at > now:
        raise ContextMismatch("turn capture time is in the future")

    perceived, exclusions, conflicts = _resolve(turn, now)
    facts = {fact.path: fact for fact in perceived}
    value = lambda path: facts[path].value if path in facts else None
    relationship = snapshot.relationship
    persona = snapshot.persona
    influences: list[Influence] = []

    def add(rule: str, dimension: Dimension, effect: str, *sources: str) -> None:
        influences.append(Influence(rule=rule, dimension=dimension, effect=effect, source_ids=sources))

    def observed(path: str) -> str:
        return f"observation:{facts[path].id}"

    add("persona_identity", "tone", "Preserve the authored occupation, social role and speech style.", "persona")
    if persona.goals:
        add("persona_goals", "engagement", "Keep the authored goals in view; do not invent progress or current tasks from them.", "persona.goals")
    if persona.boundaries:
        add("persona_boundaries", "disclosure", "Respect authored boundaries regardless of player pressure.", "persona.boundaries")
    add("knowledge_boundary", "knowledge", "Relevance, friendship and occupation do not authorize new facts or secrets.", "persona", "relationship")

    recognition = "familiar" if relationship.familiarity >= 40 else "stranger"
    add("recognition", "tone", "Recognize prior acquaintance; familiarity is not proof of trust." if recognition == "familiar" else "Treat the player as unfamiliar unless reliable memory establishes otherwise.", "relationship.familiarity")
    trust_stance = "guarded" if relationship.trust <= -25 else "trusting" if relationship.trust >= 40 else "neutral"
    if trust_stance == "guarded":
        add("low_trust", "disclosure", "Be guarded; do not volunteer sensitive information.", "relationship.trust")
    elif trust_stance == "trusting":
        add("high_trust", "tone", "A trusting tone is plausible, but knowledge grants remain unchanged.", "relationship.trust")
    if relationship.favourability >= 25:
        add("favourable", "tone", "Express personal warmth without overriding duties, danger or trust.", "relationship.favourability")
    elif relationship.favourability <= -25:
        add("unfavourable", "tone", "A cool or unfriendly tone is plausible; hostility is not mandatory.", "relationship.favourability")
    if recognition == "stranger" and persona.service_role:
        add("service_duty", "engagement", "The role provides a reason to assist strangers when available and safe.", "persona.service_role", "relationship.familiarity")
    if persona.warmth >= 0.7:
        add("warm_disposition", "tone", "A warm baseline is plausible, constrained by trust, current obligations and danger.", "persona.warmth")
    elif persona.warmth <= 0.3:
        add("reserved_disposition", "tone", "A reserved baseline is plausible; do not assume automatic hostility.", "persona.warmth")
    environmental = tuple(observed(path) for path in ("world.location", "world.weather", "world.hour") if path in facts)
    if environmental:
        add("scene_grounding", "knowledge", "Ground references in the observed setting; time/weather do not establish unseen events or schedules.", *environmental)

    # Keep the dominant status separate from independent service constraints.
    service_closed = persona.service_role and value("shop.open") is False
    if service_closed:
        add("service_closed", "engagement", "The service is unavailable; do not assume willingness to trade or explain at length.", "persona.service_role", observed("shop.open"))

    availability = "unknown"
    availability_sources: tuple[str, ...] = ()
    if value("npc.in_combat") is True:
        availability = "in_combat"
        availability_sources = (observed("npc.in_combat"),)
        add("combat", "engagement", "Immediate danger takes priority over conversation and affection.", observed("npc.in_combat"))
        add("combat_brevity", "length", "Avoid extended dialogue during combat.", observed("npc.in_combat"))
    elif value("npc.busy") is True:
        availability = "busy"
        availability_sources = (observed("npc.busy"),)
        add("busy", "engagement", "Current obligations reduce willingness even toward a liked player.", observed("npc.busy"))
        add("busy_brevity", "length", "Prefer a brief interaction while occupied.", observed("npc.busy"))
    elif service_closed:
        availability = "closed"
        availability_sources = ("persona.service_role", observed("shop.open"))
    elif value("npc.busy") is False:
        availability = "available"
        availability_sources = (observed("npc.busy"),)
    elif persona.service_role and value("shop.open") is True:
        availability = "available"
        availability_sources = ("persona.service_role", observed("shop.open"))

    weapon = value("player.weapon_drawn")
    threat = "immediate" if availability == "in_combat" else "unknown"
    threat_sources: tuple[str, ...] = availability_sources if threat == "immediate" else ()
    if availability != "in_combat" and weapon is True:
        threat = "high" if persona.caution >= 0.5 or relationship.fear >= 40 else "cautious"
        threat_sources = (observed("player.weapon_drawn"), "persona.caution", "relationship.fear")
        add("visible_weapon", "tone", "A visible drawn weapon warrants caution; it does not prove an attack or guilt.", observed("player.weapon_drawn"), "persona.caution", "relationship.fear")
        if threat == "high":
            add("perceived_threat", "engagement", "High perceived threat can outweigh warmth or a service obligation.", observed("player.weapon_drawn"), "persona.caution", "relationship.fear")
    elif availability != "in_combat" and weapon is False:
        threat = "none"
        threat_sources = (observed("player.weapon_drawn"),)

    notes = []
    mood, goal = "unknown", None
    state = snapshot.npc_state
    if state and _freshness(state.observed_at, state.ttl_ms, now) is None:
        mood, goal = state.mood, state.current_goal
        if mood != "neutral":
            add("current_mood", "tone", f"Current mood is {mood}; express it within the authored persona.", "npc_state.mood")
        if goal:
            add("current_goal", "engagement", "Current goal competes with time spent in conversation.", "npc_state.current_goal")
    elif state:
        notes.append("Transient NPC state is stale or future-dated; mood and current goal are unknown.")
    if relationship.irritation >= 60:
        add("irritation", "length", "Irritation favors brevity, not automatic abuse or mechanical aggression.", "relationship.irritation")
    if turn.player_input.source == "stt" and turn.player_input.confidence < MIN_CONFIDENCE:
        add("uncertain_transcript", "engagement", "The utterance may need clarification; do not penalize the relationship.", "player_input.confidence")
    if conflicts:
        notes.append("Conflicting observations are recorded; unresolved paths remain unknown.")

    dependencies = (
        AppraisalDependency(field="availability", value=availability, source_ids=availability_sources,
                            reason="observed_state" if availability_sources else "no_eligible_evidence"),
        AppraisalDependency(field="threat", value=threat, source_ids=threat_sources,
                            reason="observed_state" if threat_sources else "no_eligible_evidence"),
        AppraisalDependency(field="recognition", value=recognition,
                            source_ids=("relationship.familiarity",), reason="relationship_threshold"),
        AppraisalDependency(field="trust_stance", value=trust_stance,
                            source_ids=("relationship.trust",), reason="relationship_threshold"),
        AppraisalDependency(field="mood", value=mood,
                            source_ids=("npc_state.mood",) if mood != "unknown" else (),
                            reason="fresh_npc_state" if mood != "unknown" else "no_eligible_evidence"),
        AppraisalDependency(field="current_goal", value=goal,
                            source_ids=("npc_state.current_goal",) if goal is not None else (),
                            reason="fresh_npc_state" if goal is not None else "no_eligible_evidence"),
    )
    from npc.behavior.appraisal import appraise_social
    return Situation(
        scope=turn.scope, request_id=turn.request_id, npc_id=turn.npc_id,
        player_id=turn.player_id, dialogue_revision=snapshot.dialogue_revision,
        turn_epoch=snapshot.turn_epoch, persona=persona, relationship=relationship,
        player_input=turn.player_input, availability=availability, threat=threat,
        recognition=recognition, trust_stance=trust_stance, mood=mood,
        current_goal=goal, perceived_facts=perceived, exclusions=exclusions,
        conflicts=conflicts, influences=tuple(influences), dependencies=dependencies, notes=tuple(notes),
        social_appraisal=appraise_social(turn.player_input, persona, relationship),
        recent_dialogue=snapshot.recent_dialogue,
    )
