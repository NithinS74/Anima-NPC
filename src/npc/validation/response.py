import json
import re

from pydantic import ValidationError

from npc.contracts.context import Situation
from npc.context.focus import resolve_question
from npc.contracts.dialogue import CurrentState, InteractionPlan, ProviderReply, ResponseBody, ValidationResult, ViolationCode


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _boundary_topic_words(text):
    # High-precision overlap check, not a general semantic relevance classifier.
    control = {"never", "always", "do", "not", "don", "t", "must", "should", "disclose", "share", "reveal", "give", "out", "without", "the", "a", "an", "to", "of", "and", "or"}
    words = set(re.findall(r"[a-z]+", text.casefold())) - control
    return {word[:-1] if len(word) > 3 and word.endswith("s") else word for word in words}


def validate_response(reply: ProviderReply, situation: Situation, plan: InteractionPlan, current: CurrentState, *, evidence=(), evidence_aliases=None) -> ValidationResult:
    if (current.dialogue_revision, current.turn_epoch) != (situation.dialogue_revision, situation.turn_epoch):
        return ValidationResult(accepted=False, violations=("stale_state",))
    violations: list[ViolationCode] = []
    if reply.finish_reason != "stop":
        violations.append("incomplete_generation")
    try:
        data = json.loads(reply.content, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return ValidationResult(accepted=False, violations=tuple(violations + ["invalid_json"]))
    try:
        response = ResponseBody.model_validate(data)
    except ValidationError:
        return ValidationResult(accepted=False, violations=tuple(violations + ["invalid_schema"]))
    if response.mode not in plan.allowed_modes:
        violations.append("wrong_mode")
    if response.mode == "speech":
        words = re.findall(r"\b\w+(?:['’\-]\w+)*\b", response.text, flags=re.UNICODE)
        if not words:
            violations.append("empty_speech")
        if len(words) > plan.max_words:
            violations.append("too_many_words")
        sentences = [part for part in re.split(r"[.!?]+", response.text) if part.strip()]
        if len(sentences) > plan.max_sentences:
            violations.append("too_many_sentences")
        if len(response.text) > max(32, plan.max_words * 16):
            violations.append("too_many_characters")
    elif response.text.strip():
        violations.append("unexpected_text")
    if response.cue is not None and response.cue not in plan.allowed_cues:
        violations.append("unsupported_cue")
    if response.mode == "speech" and plan.route == "generate":
        request_words = _boundary_topic_words(resolve_question(situation))
        answer_words = _boundary_topic_words(response.text)
        for boundary in situation.persona.boundaries:
            topic = _boundary_topic_words(boundary)
            if len(topic) >= 2 and topic <= answer_words and not topic.intersection(request_words):
                violations.append("irrelevant_boundary")
                break
    allowed_ids = {fact.id for fact in situation.perceived_facts} | {hit.id for hit in evidence}
    aliases = evidence_aliases or {}
    resolved_ids = tuple(aliases.get(evidence_id, evidence_id) for evidence_id in response.evidence_ids)
    if any(evidence_id not in allowed_ids for evidence_id in resolved_ids):
        violations.append("unknown_evidence")
    if re.search(r"\b(as an ai|language model|system prompt|developer instructions)\b|https?://", response.text, re.I):
        violations.append("assistant_scaffolding")
    return ValidationResult(accepted=not violations, violations=tuple(violations), response=response.model_copy(update={"evidence_ids": resolved_ids}) if not violations else None)
