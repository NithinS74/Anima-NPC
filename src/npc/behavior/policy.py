"""Initial scenario policy; routing quality remains an evaluation question."""

import re

from npc.contracts.context import Situation
from npc.behavior.lines import pick_line, recent_lines, style_keys
from npc.contracts.dialogue import InteractionPlan

FAREWELL = re.compile(
    r"^(?:(?:ok|okay|well|alright|right|thanks|thank you|then)[ ,.!]+)*(?:goodbye|good bye|bye|bye bye|farewell|see you(?: later| around| soon)?|"
    r"good night|take care|until next time|(?:i (?:must|have to|need to|should) (?:go|leave|be going))|(?:i(?:'m| am) (?:off|leaving))|gotta go)"
    r"(?:[ ,.!]+(?:then|now|for now|everyone|friend|stranger|thanks|thank you))*$")
NEGATION = re.compile(r"(?:not|no|never|won't|don't|dont|cannot|can't|without|before|until i)|n't", re.I)


def is_farewell(text: str) -> bool:
    """A plain goodbye only: a negation or a quoted goodbye keeps the conversation going."""
    raw = text.strip()
    if any(q in raw for q in ('"', "“", "”", "‘")) or len(raw.split()) > 7:
        return False
    if NEGATION.search(raw) and not re.match(r"^(?:i (?:must|have to|need to|should) go)", raw, re.I):
        return False
    return bool(FAREWELL.match(raw.casefold().strip(" .!?,")))


def choose_plan(situation: Situation) -> InteractionPlan:
    formal = "formal" in {style.casefold() for style in situation.persona.speech_style}
    keys, recent, rid = style_keys(situation.persona), recent_lines(situation), situation.request_id

    def line(intent, *variant):
        return pick_line(intent, (*variant, *keys), rid, recent)

    fallback = pick_line("fallback", keys, rid, recent) or "I cannot say."
    social = situation.social_appraisal
    has_question = bool(re.search(r"\?|\b(?:where|who|when|what|how|why|can|could|would)\b", situation.player_input.text.casefold()))
    affect = social.tone if social.tone != "neutral" else "guarded" if situation.trust_stance == "guarded" else situation.mood
    common = {"affect": affect, "fallback_text": fallback, "allowed_modes": ("speech",)}

    def authored(intent: str, line: str) -> InteractionPlan:
        return InteractionPlan(route="authored", intent=intent, knowledge_need="none",
                               max_words=12, max_sentences=1, authored_text=line,
                               reason_codes=(intent,), **common)

    if situation.availability == "in_combat":
        return InteractionPlan(route="end", intent="prioritize_safety", affect="urgent",
                               knowledge_need="none", max_words=0, max_sentences=0,
                               allowed_modes=("end",), reason_codes=("combat",))
    if any(item.rule == "uncertain_transcript" for item in situation.influences):
        return authored("clarify", line("clarify"))
    if situation.threat == "high":
        return authored("warn", line("warn"))
    if social.willingness in {"disengage", "withdraw"}:
        return InteractionPlan(route="end", intent=social.willingness, affect=social.tone,
                               knowledge_need="none", max_words=0, max_sentences=0,
                               allowed_modes=("end",), reason_codes=social.reasons)
    if social.stimulus == "threat":
        return authored("reject_threat", line("reject_threat"))
    if social.stimulus == "directed_insult":
        variant = "swear" if social.allow_swearing and situation.relationship.irritation >= 55 else "default"
        if situation.persona.patience >= 0.6:
            variant = "patient"
        if formal:
            variant = "formal"
        return authored("set_boundary", line("set_boundary", variant))
    if social.stimulus == "rough_banter" and not has_question:
        return authored("familiar_banter", line("familiar_banter", "swear" if social.allow_swearing else "default"))
    if social.stimulus == "apology" and not has_question:
        return authored("acknowledge_apology", line("acknowledge_apology", "irritated" if situation.relationship.irritation >= 60 else "default"))
    if situation.availability == "busy":
        if situation.relationship.familiarity >= 40 and situation.relationship.trust >= 40:
            return authored("busy", line("busy", "friend"))
        return authored("busy", line("busy", "formal") if formal else line("busy", "default"))
    if any(item.rule == "service_closed" for item in situation.influences):
        return authored("service_closed", line("service_closed"))
    # Full-string recognition avoids swallowing 'Hello, where is the ...?'.
    text = situation.player_input.text.casefold().strip(" .!?,")
    if is_farewell(situation.player_input.text):
        plan = authored("farewell", line("farewell"))
        return plan.model_copy(update={"move": "farewell"})
    if text in {"hi", "hello", "hey", "good morning", "good evening"}:
        if situation.relationship.familiarity >= 40 and situation.relationship.favourability >= 25 and situation.relationship.trust >= 40:
            return authored("greet", line("greet", "friend"))
        if situation.persona.warmth >= 0.7 and situation.persona.service_role:
            return authored("greet", line("greet", "warm"))
        if social.willingness == "brief" and situation.trust_stance == "guarded":
            return authored("greet", line("greet", "guarded"))
        return authored("greet", line("greet", "formal") if formal else line("greet", "default"))
    detail = bool(re.search(r"\b(in detail|explain fully)\b", text)) and situation.availability == "available" and situation.trust_stance != "guarded"
    factual = bool(re.search(r"\b(where|who|when)\b", text))
    brief = social.willingness == "brief"
    return InteractionPlan(route="generate", intent="brief_reply" if brief else "respond_in_character", knowledge_need="required" if factual else "uncertain",
                           max_words=18 if brief else 90 if detail else 40, max_sentences=1 if brief else 4 if detail else 2,
                           reason_codes=("novel_input", "no_external_knowledge"), **common)
