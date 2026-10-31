"""Initial scenario policy; routing quality remains an evaluation question."""

import re

from npc.contracts.context import Situation
from npc.contracts.dialogue import InteractionPlan


def choose_plan(situation: Situation) -> InteractionPlan:
    formal = "formal" in {style.casefold() for style in situation.persona.speech_style}
    fallback = "I cannot speak to that matter." if formal else "I cannot say."
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
        return authored("clarify", "Could you repeat that?")
    if situation.threat == "high":
        return authored("warn", "Keep your distance.")
    if social.willingness in {"disengage", "withdraw"}:
        return InteractionPlan(route="end", intent=social.willingness, affect=social.tone,
                               knowledge_need="none", max_words=0, max_sentences=0,
                               allowed_modes=("end",), reason_codes=social.reasons)
    if social.stimulus == "threat":
        return authored("reject_threat", "Keep back; I won't tolerate threats.")
    if social.stimulus == "directed_insult":
        line = "Watch your damn mouth." if social.allow_swearing and situation.relationship.irritation >= 55 else "Mind your tongue."
        if situation.persona.patience >= 0.6:
            line = "You can be upset without taking it out on me."
        if formal:
            line = "That language is unacceptable; address me respectfully."
        return authored("set_boundary", line)
    if social.stimulus == "rough_banter" and not has_question:
        return authored("familiar_banter", "Still a cheeky bastard, aren't you?" if social.allow_swearing else "You haven't changed, have you?")
    if social.stimulus == "apology" and not has_question:
        return authored("acknowledge_apology", "An apology doesn't settle everything." if situation.relationship.irritation >= 60 else "Apology heard; give me a moment.")
    if situation.availability == "busy":
        if situation.relationship.familiarity >= 40 and situation.relationship.trust >= 40:
            return authored("busy", "Not now, friend; I've got work to finish.")
        return authored("busy", "I am occupied; please return later." if formal else "I'm occupied; try another time.")
    if any(item.rule == "service_closed" for item in situation.influences):
        return authored("service_closed", "The service is closed for now.")
    # Full-string recognition avoids swallowing 'Hello, where is the ...?'.
    text = situation.player_input.text.casefold().strip(" .!?,")
    if text in {"hi", "hello", "hey", "good morning", "good evening"}:
        if situation.relationship.familiarity >= 40 and situation.relationship.favourability >= 25 and situation.relationship.trust >= 40:
            return authored("greet", "Good to see you; what do you need?")
        if situation.persona.warmth >= 0.7 and situation.persona.service_role:
            return authored("greet", "Welcome in; what can I do for you?")
        if social.willingness == "brief" and situation.trust_stance == "guarded":
            return authored("greet", "State your business.")
        return authored("greet", "Welcome; how may I help?" if formal else "What do you need?")
    detail = bool(re.search(r"\b(in detail|explain fully)\b", text)) and situation.availability == "available" and situation.trust_stance != "guarded"
    factual = bool(re.search(r"\b(where|who|when)\b", text))
    brief = social.willingness == "brief"
    return InteractionPlan(route="generate", intent="brief_reply" if brief else "respond_in_character", knowledge_need="required" if factual else "uncertain",
                           max_words=18 if brief else 90 if detail else 40, max_sentences=1 if brief else 4 if detail else 2,
                           reason_codes=("novel_input", "no_external_knowledge"), **common)
