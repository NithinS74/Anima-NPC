"""Bounded interpretation of short follow-ups, never new world facts."""

import re


def resolve_question(situation):
    query = situation.player_input.text
    if (len(query) < 200 and situation.recent_dialogue
            and re.search(r"\b(it|its|that|those|them|they|there|he|she|him|her)\b", query, re.I)):
        previous = situation.recent_dialogue[-1].player_text[:200]
        topic = re.fullmatch(
            r"(?:please\s+)?(?:tell me about|what can you tell me about|who (?:is|are)|"
            r"what (?:is|are)|describe|explain)\s+(.+?)[.!?]*", previous.strip(), re.I)
        if topic and re.search(r"\b(it|that|those|them|him|her)\b", query, re.I):
            subject = topic.group(1).strip()
            query = re.sub(r"\b(?:it|that|those|them|him|her)\b", lambda _: subject, query, flags=re.I)
        else:
            query += "\nPrevious player question: " + previous
    return query
