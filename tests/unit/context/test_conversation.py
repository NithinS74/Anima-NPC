"""I24 WP-B: turn reading on a labelled set, similarity injection, and state advance. Offline and deterministic."""

import json
from pathlib import Path

import pytest

from npc.context.conversation import advance, read_turn, token_similarity
from npc.contracts.context import ConversationState, TurnReading

CASES = json.loads((Path(__file__).resolve().parents[3] / "fixtures/evaluation/conversation/turns.json").read_text(encoding="utf-8"))["cases"]


def state_from(history):
    state = ConversationState()
    for player, reply in history:
        state = advance(state, read_turn(player, state), player, reply, None)
    return state


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_labelled_turns(case):
    assert read_turn(case["text"], state_from(case["history"])).type == case["expect"]


def test_repeat_is_not_confused_with_a_real_follow_up():
    state = state_from([["Who is the king?", "A man in a far castle."]])
    assert read_turn("Who is the king?", state).type == "repeat"
    assert read_turn("Why do they say so?", state).type == "follow_up"


def test_precision_and_recall_on_the_labelled_set():
    right = sum(read_turn(c["text"], state_from(c["history"])).type == c["expect"] for c in CASES)
    assert right == len(CASES)


def test_injected_similarity_is_used_and_never_required_to_load_anything():
    state = state_from([["Who is the king?", "x"]])
    always = lambda a, b: 1.0
    assert read_turn("something unrelated entirely", state, always).type == "repeat"
    assert read_turn("something unrelated entirely", state, lambda a, b: 0.0).type in {"new", "shared_news"}
    assert 0 <= token_similarity("a b c", "a b d") <= 1


def test_state_is_bounded_and_rapport_never_leaves_range():
    state = ConversationState()
    for i in range(40):
        text = f"topic number{i} alpha{i}"
        state = advance(state, read_turn(text, state), text, f"reply {i}", "answer", (f"e{i}",))
    assert len(state.topics) <= 16 and len(state.told) <= 8 and len(state.replies) <= 4 and 0 <= state.rapport <= 100


def test_repeat_counts_asks_and_lowers_rapport():
    state = ConversationState()
    for _ in range(3):
        state = advance(state, read_turn("Who is the king?", state), "Who is the king?", "r", None)
    assert state.topics[-1].asked == 3 and state.rapport < 8
