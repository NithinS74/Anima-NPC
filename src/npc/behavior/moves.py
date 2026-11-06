"""Deterministic choice of what the NPC tries to do this turn. Pure; never touches knowledge or trust.

Existing hard rules in policy.py decide first (combat, threats, insults, availability, greetings,
farewells). Moves only shape the generated replies that policy leaves open.
"""

import re

from npc.behavior.lines import pick_line, style_keys
from npc.context.conversation import content
from npc.contracts.context import ConversationState, Persona, TurnReading
from npc.contracts.dialogue import InteractionPlan
from npc.contracts.knowledge import KnowledgeContext

REPEATED = frozenset({"repeat", "rephrase", "push_back"})
MAX_GROWN_WORDS, MAX_GROWN_SENTENCES = 45, 3
SHORT_MOVES = frozenset({"challenge", "close_topic", "hold", "admit_limit", "take_initiative"})

INSTRUCTIONS = {
    "answer": "",
    "expand": "Add something new on this topic; do not restate.",
    "answer_differently": "Asked before: use new words and one new detail, or ask what they want.",
    "challenge": "They keep asking: react in character, ask why it matters; do not just answer.",
    "close_topic": "Close this topic. {close}",
    "reconsider": "New angle (a claim, not proof): treat it as a real development.",
    "admit_limit": "Say you have nothing more; maybe labelled hearsay/opinion, or who might know.",
    "hold": "Refuse this in new words, in character; you may grow wary.",
    "react": "React to what they told you; it is their unverified claim.",
    "follow_through": "They answered you; use their answer.",
    "recall": "Refer back to the earlier talk and add what fits.",
    "take_initiative": "They say little: raise your own concern or end the talk.",
    "opening": "Greet as talk begins; do not claim they said anything.",
    "farewell": "Say goodbye briefly.",
}


def _boundary_pressure(text: str, persona: Persona) -> bool:
    words = content(text)
    for boundary in persona.boundaries:
        topic = content(boundary) - {"never", "always", "must", "disclose", "share", "reveal", "give", "without"}
        if topic and len(topic & words) >= min(2, len(topic)):
            return True
    return False


def choose_move(act: TurnReading, state: ConversationState, persona: Persona, text: str = "") -> str:
    """The I23 move table. `act` is the turn reading; repetition changes the move, never what is known."""
    kind, asked = act.type, act.asked
    if kind in REPEATED and text and _boundary_pressure(text, persona):
        return "hold"
    if kind in {"repeat", "rephrase"}:
        if kind == "rephrase" and act.new_words >= 4 and re.search(
                r"\b(because|i (?:have|found|brought|saw)|here(?:'s| is)|proof)\b", text, re.I):
            return "reconsider"
        return "answer_differently" if asked <= 1 else "challenge" if asked == 2 else "close_topic"
    return {"new": "answer", "follow_up": "expand", "push_back": "admit_limit", "shared_news": "react",
            "answered": "follow_through", "return": "recall",
            "stall": "close_topic" if state.last_type == "stall" and persona.patience < 0.3 else "take_initiative",
            }.get(kind, "answer")


def apply_move(plan: InteractionPlan, move: str, state: ConversationState, persona: Persona, request_id: str = "") -> InteractionPlan:
    """Attach the move. Length follows move and bounded rapport; rapport never touches trust or knowledge."""
    if plan.route != "generate":
        return plan
    words, sentences = plan.max_words, plan.max_sentences
    if move in SHORT_MOVES:
        words, sentences = min(words, 28), min(sentences, 2)
    else:
        bonus = state.rapport // 25  # 0..4
        words = min(MAX_GROWN_WORDS, max(words, words + 6 * bonus)) if words < MAX_GROWN_WORDS else words
        sentences = min(MAX_GROWN_SENTENCES, sentences + (1 if state.rapport >= 50 and sentences < MAX_GROWN_SENTENCES else 0))
    fallback = pick_line("fallback", (move, *style_keys(persona)), request_id, state.replies) or plan.fallback_text
    return plan.model_copy(update=dict(move=move, max_words=words, max_sentences=sentences, fallback_text=fallback[:200]))


def apply_material(plan: InteractionPlan, knowledge: KnowledgeContext | None, state: ConversationState) -> InteractionPlan:
    """After retrieval: a repeated topic whose earlier material is used up becomes Admit limit (and fresh material revives it).

    Only acts when retrieval ran AND material was used before; a persona that could answer from its own
    profile is not forced to admit a limit just because nothing was ever retrieved.
    """
    if plan.move is None or knowledge is None or knowledge.status not in {"ok", "empty"} or not state.turns:
        return plan
    fresh = knowledge.status == "ok" and bool(knowledge.evidence)
    exhausted = bool(state.told) or bool(state.topics and state.topics[-1].exhausted)  # material was used before
    if plan.move in {"expand", "answer_differently"} and not fresh and exhausted:
        return plan.model_copy(update=dict(move="admit_limit", max_words=min(plan.max_words, 28), max_sentences=min(plan.max_sentences, 2)))
    if plan.move == "admit_limit" and fresh:
        return plan.model_copy(update=dict(move="expand"))
    return plan


def move_instruction(move: str | None, persona: Persona) -> str:
    text = INSTRUCTIONS.get(move or "", "")
    if "{close}" in text:
        text = text.format(close="Redirect politely." if persona.patience >= 0.5 else "Be curt or end the talk.")
    return text


def opening_plan(persona: Persona, request_id: str, recent=()) -> InteractionPlan:
    """Authored session-start line for a stranger or routine greeting: no model call, no player utterance.

    Wiring it to a session start (and the optional model-written opening for known players) is adapter work.
    """
    line = pick_line("opening", style_keys(persona), request_id, recent) or "Yes?"
    return InteractionPlan(route="authored", intent="opening", affect="neutral", knowledge_need="none", max_words=12,
                           max_sentences=1, allowed_modes=("speech",), authored_text=line, reason_codes=("opening",),
                           move="opening")
