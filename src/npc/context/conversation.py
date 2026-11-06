"""Pure conversation reading: how a player turn relates to the conversation so far.

No I/O and no model call. Similarity is injected; the default is a deterministic token-overlap
measure, replaced by the MiniLM encoder only when the retrieval service has already loaded it.
Nothing here grants knowledge or changes trust.
"""

import math
import re
from collections.abc import Callable
from typing import get_args

from npc.contracts.context import ConversationState, Move, TopicRecord, TurnReading

Similarity = Callable[[str, str], float]

# Calibrated on fixtures/evaluation/conversation/turns.json (token scale). The embedding scale is NOT
# calibrated on a labelled set yet; it uses conventional MiniLM cosine values.
THRESHOLDS = {
    "token": dict(repeat=0.8, rephrase=0.4, recall=0.4),
    "embedding": dict(repeat=0.92, rephrase=0.6, recall=0.5),
}
RETURN_GAP_TURNS = 3  # an older topic counts as a return only after this many turns
NEW_INFO_WORDS = 4  # a rephrase this much longer than the topic, with a cue, is new information
MAX_SNIPPET = 160

STOPWORDS = frozenset("""a an the is are was were be been am do does did to of and or in on at for with about as by it its this that
these those i me my you your we our they them their he she him her his what whats who whom when where why how which can could would
should will shall may might must tell please just so then there here if but not no yes ok okay hello hi hey""".split())
STALL_WORDS = frozenset("ok okay hmm hm mm mhm uh um huh i see right fine alright sure yes no yeah nope aye well oh ah".split())
ANSWER_WORDS = frozenset("yes no yeah nope aye ok okay sure".split())
INTERROGATIVES = frozenset("what who whom when where why how which".split())
# Courtesy, farewell and intention words: a statement made only of these shares no news.
SOCIAL_WORDS = frozenset("""thanks thank thankyou cheers appreciate grateful bye goodbye farewell later soon go going went come coming see
glad sorry understood noted gotcha great good nice fine well will shall now then""".split())
GREETING_WORDS = frozenset("hello hi hey greetings hail".split())

PUSH_BACK = re.compile(r"\b(are you sure|you(?:'re| are) (?:lying|wrong)|that(?:'s| is| can't| cannot| doesn't| isn't|s not)\b.*\b(?:right|true|possible|make sense)|"
                       r"i don't believe|i do not believe|no[, ]+(?:that|you)|come on|really\?|that can't be|that's not true)", re.I)
FOLLOW_UP = re.compile(r"^(?:and |but |so )?(?:why|how so|who told you(?: that)?|what do you mean|tell me more|go on|and then|explain|"
                       r"what about (?:that|it)|since when|says who|what happened|then what)\b", re.I)
NEW_INFO_CUE = re.compile(r"\b(because|i (?:have|found|brought|saw|heard|know)|here(?:'s| is)|proof|my (?:family|brother|sister|father|mother))\b", re.I)
QUESTION = re.compile(r"\?|^(?:what|who|where|when|why|how|which|can|could|would|do|does|did|is|are|will)\b", re.I)


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def tokens(text: str) -> list[str]:
    text = re.sub(r"['’]s\b", "", text.casefold())
    return re.findall(r"[a-z0-9]+", text)


def content(text: str) -> frozenset[str]:
    return frozenset(_stem(w) for w in tokens(text) if w not in STOPWORDS)


def _similarity_content(text: str) -> frozenset[str]:
    # Interrogatives stay: "who is X" and "where is X" are different questions.
    return content(text) | frozenset(w for w in tokens(text) if w in INTERROGATIVES)


def token_similarity(a: str, b: str) -> float:
    left, right = _similarity_content(a), _similarity_content(b)
    if not left or not right:
        return 1.0 if tokens(a) == tokens(b) and tokens(a) else 0.0
    return len(left & right) / len(left | right)


token_similarity.kind = "token"  # type: ignore[attr-defined]

_ENCODER: Callable[[list[str]], list] | None = None
_CACHE: dict[str, list[float]] = {}


def set_encoder(embed: Callable[[list[str]], list] | None) -> None:
    """Register an ALREADY LOADED encoder. This module never loads or downloads a model."""
    global _ENCODER
    _ENCODER = embed
    _CACHE.clear()


def _vector(text: str):
    vec = _CACHE.get(text)
    if vec is None:
        vec = [float(x) for x in _ENCODER([text])[0]]  # type: ignore[misc]
        if len(_CACHE) > 64:
            _CACHE.clear()
        _CACHE[text] = vec
    return vec


def embedding_similarity(a: str, b: str) -> float:
    try:
        x, y = _vector(a), _vector(b)
        norm = math.sqrt(sum(v * v for v in x)) * math.sqrt(sum(v * v for v in y))
        return max(0.0, min(1.0, sum(p * q for p, q in zip(x, y)) / norm)) if norm else 0.0
    except Exception:  # never fail a turn because of the encoder
        return token_similarity(a, b)


embedding_similarity.kind = "embedding"  # type: ignore[attr-defined]


def default_similarity() -> Similarity:
    return embedding_similarity if _ENCODER is not None else token_similarity


def snippet(text: str, limit: int = MAX_SNIPPET) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def is_question(text: str) -> bool:
    return bool(QUESTION.search(text.strip()))


def read_turn(text: str, state: ConversationState, similarity: Similarity | None = None) -> TurnReading:
    """Classify the player's turn against the conversation state. Deterministic for a given similarity."""
    similarity = similarity or default_similarity()
    limits = THRESHOLDS.get(getattr(similarity, "kind", "token"), THRESHOLDS["token"])
    words = tokens(text)
    clean = snippet(text)
    last = state.topics[-1] if state.topics else None

    def reading(kind, topic=None, sim=0.0, new_words=0):
        return TurnReading(type=kind, topic=topic.text if isinstance(topic, TopicRecord) else topic,
                           asked=topic.asked if isinstance(topic, TopicRecord) else 0,
                           new_words=new_words, similarity=round(max(0.0, min(1.0, sim)), 3))

    if not words:
        return reading("stall", last)
    question = is_question(text)
    if state.open_question and not question and (words[0] in ANSWER_WORDS or len(content(text)) >= 1):
        best = max((similarity(clean, t.text) for t in state.topics), default=0.0)
        if best < limits["rephrase"]:
            return reading("answered", last)
    if len(words) <= 2 and all(w in STALL_WORDS for w in words):
        return reading("stall", last)
    if len(words) <= 2 and all(w in GREETING_WORDS for w in words):
        return reading("new", None)
    scored = [(similarity(clean, t.text), i) for i, t in enumerate(state.topics)]
    best, index = max(scored, default=(0.0, -1))
    topic = state.topics[index] if index >= 0 else None
    if topic is not None and best >= limits["repeat"]:
        return reading("repeat", topic, best)
    if last is not None and PUSH_BACK.search(text) and len(words) <= 12:
        return reading("push_back", last, best)
    if last is not None and FOLLOW_UP.match(text.strip()) and len(words) <= 8:
        return reading("follow_up", last, best)
    if topic is not None:
        mine, theirs = content(text), content(topic.text)
        recent = state.turns - topic.last_turn < RETURN_GAP_TURNS
        if recent and theirs and theirs < mine and best < limits["repeat"]:  # same words plus more: narrows the topic
            return reading("follow_up", topic, best)
        if best >= limits["rephrase"] and recent:
            return reading("rephrase", topic, best, len(mine - theirs))
        if best >= limits["recall"] and not recent:
            return reading("return", topic, best)
    news = {w for w in content(text) if w not in SOCIAL_WORDS and _stem(w) not in SOCIAL_WORDS}
    if not question and len(news) >= 2:
        return reading("shared_news", last, best)
    if not question and all(w in STALL_WORDS or w in STOPWORDS or w in SOCIAL_WORDS for w in words):
        return reading("stall", last, best)
    return reading("new", None, best)


def _bounded(items, new, size):
    return (tuple(i for i in items if i != new) + (new,))[-size:]


def advance(state: ConversationState, reading: TurnReading | None, player_text: str, reply: str,
            move: str | None, evidence_ids=()) -> ConversationState:
    """State after a COMPLETED (displayed) turn. Rapport changes length and warmth only."""
    kind = reading.type if reading else "new"
    turn = state.turns + 1
    topics = list(state.topics)
    key = reading.topic if reading and reading.topic else snippet(player_text)
    at = next((i for i, t in enumerate(topics) if t.text == key), None)
    if kind in {"new", "return", "repeat", "rephrase"} or (kind in {"follow_up", "push_back"} and at is None):
        if at is None:
            topics.append(TopicRecord(text=key, asked=1, last_turn=turn))
        else:
            old = topics.pop(at)
            topics.append(old.model_copy(update=dict(asked=min(99, old.asked + (kind in {"repeat", "rephrase"})), last_turn=turn)))
    elif at is not None:
        old = topics.pop(at)
        topics.append(old.model_copy(update=dict(last_turn=turn)))
    if move == "admit_limit" and topics:
        topics[-1] = topics[-1].model_copy(update=dict(exhausted=True))
    claims = state.claims
    if kind == "shared_news":
        claims = _bounded(claims, snippet(player_text, 120), 8)
    told = state.told
    for ident in evidence_ids:
        told = _bounded(told, ident, 8)
    replies = _bounded(state.replies, snippet(reply), 4) if reply else state.replies
    phrases = state.phrases
    if reply:
        opening = " ".join(reply.split()[:4]).casefold().strip(" ,.;:!?")[:48]
        if opening:
            phrases = _bounded(phrases, opening, 8)
    gain = {"new": 4, "shared_news": 4, "answered": 4, "follow_up": 3, "return": 2, "stall": 0}.get(kind, -4)
    return ConversationState(
        turns=turn, topics=tuple(topics[-16:]), told=told, replies=replies, claims=claims, phrases=phrases,
        last_type=kind, last_move=move if move in get_args(Move) else None,
        open_question=reply.rstrip().endswith("?"), rapport=max(0, min(100, state.rapport + gain)))
