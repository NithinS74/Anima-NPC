"""Inspectable English prototype appraisal, without an extra inference call."""

import re

from npc.contracts.context import Persona, PlayerInput, Relationship, SocialAppraisal

QUOTED = re.compile(r'"[^"\n]*"|(?<!\w)\x27[^\x27\n]+\x27(?!\w)|\u201c[^\u201d]*\u201d')
DIRECT_INSULT = re.compile(
    r"\b(?:fuck\s+(?:you|off)|shut\s+(?:up|the fuck up)|"
    r"you(?:'re| are)?\s+(?:(?:a|an|such a|fucking|bloody|damn)\s+)*"
    r"(?:idiot|moron|asshole|bastard|bitch|useless|stupid|pathetic))\b"
)
THREAT = re.compile(r"\b(?:i(?:'ll| will| am going to)|gonna)\s+(?:kill|hurt|stab|shoot|beat)\s+you\b")
SWEAR = re.compile(r"\b(?:fuck(?:ing)?|shit|damn|bastard|asshole|bitch)\b")


def appraise_social(player: PlayerInput, persona: Persona, relationship: Relationship) -> SocialAppraisal:
    text = QUOTED.sub("", player.text.casefold()).strip()
    text = re.sub(r"\b(?:he|she|they|someone|a stranger)\s+(?:said|called|told|shouted)\b[^.!?]*", "", text)
    if player.confidence < 0.6:
        return SocialAppraisal(reasons=("uncertain_input_no_social_penalty",))
    stimulus = "neutral"
    if THREAT.search(text):
        stimulus = "threat"
    elif DIRECT_INSULT.search(text) or re.fullmatch(r"(?:idiot|moron|asshole|bitch)[.! ]*", text):
        friendly = relationship.familiarity >= 60 and relationship.trust >= 40 and relationship.favourability >= 50
        stimulus = "rough_banter" if friendly and re.search(r"\b(?:haha|kidding|joking)\b", text) else "directed_insult"
    elif re.search(r"\b(?:sorry|i apologize|my apologies)\b", text):
        stimulus = "apology"
    elif re.search(r"\b(?:thank you|thanks|appreciate it)\b", text):
        stimulus = "gratitude"
    elif SWEAR.search(text):
        stimulus = "incidental_profanity"
    reasons = [stimulus]
    tone = "guarded" if relationship.trust <= -25 else "warm" if relationship.favourability >= 25 or persona.warmth >= 0.7 else "neutral"
    willingness = "engage" if persona.service_role or relationship.familiarity >= 40 else "brief"
    if willingness == "brief": reasons.append("stranger_no_service_obligation")
    if stimulus == "threat":
        willingness = "withdraw" if persona.assertiveness < 0.5 or relationship.fear >= 60 else "boundary"
        tone = "fearful" if willingness == "withdraw" else "angry"
    elif stimulus == "directed_insult":
        willingness = "disengage" if relationship.irritation >= 80 else "boundary"
        tone = "angry" if persona.patience < 0.5 else "guarded"
    elif stimulus == "rough_banter":
        tone = "sarcastic"; reasons.append("familiar_trusted_banter")
    elif relationship.irritation >= 85:
        willingness = "disengage"; reasons.append("sustained_irritation")
    elif relationship.irritation >= 60 or relationship.favourability <= -40:
        willingness = "brief"; reasons.append("limited_willingness")
    allow_swearing = persona.swearing == "when_provoked" and stimulus in {"directed_insult", "rough_banter"} and persona.assertiveness >= 0.6
    return SocialAppraisal(stimulus=stimulus, willingness=willingness, tone=tone,
                           allow_swearing=allow_swearing, reasons=tuple(reasons))


def relationship_effect(player: PlayerInput, persona: Persona, before: Relationship, *, positive_allowed: bool):
    appraisal = appraise_social(player, persona, before)
    delta = dict.fromkeys(before.model_dump(), 0)
    if appraisal.stimulus == "directed_insult":
        delta.update(favourability=-7, trust=-4, irritation=round(12 + 12 * (1 - persona.patience)))
    elif appraisal.stimulus == "threat":
        delta.update(favourability=-12, trust=-12, fear=20, irritation=15)
    elif appraisal.stimulus == "apology" and positive_allowed:
        delta["irritation"] = -8  # words do not restore trust
    elif appraisal.stimulus == "gratitude" and positive_allowed:
        delta.update(favourability=1, irritation=-2)
    if positive_allowed and player.confidence >= 0.6:
        delta["familiarity"] = 1
    values = {key: max(-100 if key in {"favourability", "trust"} else 0,
                       min(100, value + delta[key])) for key, value in before.model_dump().items()}
    after = Relationship.model_validate(values)
    actual = {key: values[key] - value for key, value in before.model_dump().items()}
    return after, actual, appraisal
