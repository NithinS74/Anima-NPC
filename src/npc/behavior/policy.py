"""Initial scenario policy; routing quality remains an evaluation question."""

import re

from npc.contracts.context import Situation
from npc.contracts.dialogue import InteractionPlan


def choose_plan(situation: Situation) -> InteractionPlan:
    formal = "formal" in {style.casefold() for style in situation.persona.speech_style}
    fallback = "I cannot speak to that matter." if formal else "I cannot say."
    affect = "guarded" if situation.trust_stance == "guarded" else situation.mood
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
    if situation.availability == "busy":
        return authored("busy", "I am occupied; please return later." if formal else "I'm occupied; try another time.")
    if any(item.rule == "service_closed" for item in situation.influences):
        return authored("service_closed", "The service is closed for now.")
    # Full-string recognition avoids swallowing 'Hello, where is the ...?'.
    text = situation.player_input.text.casefold().strip(" .!?,")
    if text in {"hi", "hello", "hey", "good morning", "good evening"}:
        return authored("greet", "Welcome; how may I help?" if formal else "What do you need?")
    detail = bool(re.search(r"\b(in detail|explain fully)\b", text)) and situation.availability == "available" and situation.trust_stance != "guarded"
    factual = bool(re.search(r"\b(where|who|when)\b", text))
    return InteractionPlan(route="generate", intent="respond_in_character", knowledge_need="required" if factual else "uncertain",
                           max_words=90 if detail else 40, max_sentences=4 if detail else 2,
                           reason_codes=("novel_input", "no_external_knowledge"), **common)
