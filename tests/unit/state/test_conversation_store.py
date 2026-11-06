"""I24 WP-B: conversation state persistence, migration and the display-only update rule."""

import sqlite3

import pytest

from npc.contracts.context import PlayerInput, Relationship, Scope
from npc.state.social_store import SocialStore, StateConflict, StoreFailure
from tools.npc_lab.service import load_profiles

V1_SCHEMA = """
CREATE TABLE social_state (scope_key TEXT PRIMARY KEY, relationship TEXT NOT NULL, mood TEXT NOT NULL, revision INTEGER NOT NULL, last_gain REAL NOT NULL);
CREATE TABLE social_turn (sequence INTEGER PRIMARY KEY AUTOINCREMENT, scope_key TEXT NOT NULL, request_id TEXT NOT NULL, digest TEXT NOT NULL,
  player_text TEXT NOT NULL, audit TEXT NOT NULL, result TEXT, npc_text TEXT, mode TEXT, displayed INTEGER NOT NULL DEFAULT 0,
  cancelled INTEGER NOT NULL DEFAULT 0, UNIQUE(scope_key, request_id));
CREATE INDEX social_history ON social_turn(scope_key, displayed, sequence DESC);
PRAGMA user_version=1;
"""


@pytest.fixture
def rig(tmp_path):
    store = SocialStore(tmp_path / "s.sqlite3", clock=lambda: 1000.0)
    profile = load_profiles()["elin"]
    key = store.key(Scope(game_id="g", world_id="w", save_branch_id="b"), "elin", "p")
    store.ensure(key, profile.relationship, profile.mood)
    return store, key, profile


def turn(rig, request, text, reply="Aye, it is east of the market.", move="answer", evidence=("e1",), show=True):
    store, key, profile = rig
    state, audit, _ = store.begin_turn(key, request, PlayerInput(text=text), profile.persona, store.load(key)["revision"])
    store.stage_preview(key, request, {"result": {"response": {"mode": "speech", "text": reply, "evidence_ids": []}}}, state["revision"],
                        move=move, evidence_ids=evidence)
    if show:
        store.displayed(key, request)
    return state, audit


def test_version_1_database_opens_migrates_and_keeps_its_data(tmp_path):
    path = tmp_path / "old.sqlite3"
    key = SocialStore.key(Scope(game_id="g", world_id="w", save_branch_id="b"), "elin", "p")
    with sqlite3.connect(path) as db:
        db.executescript(V1_SCHEMA)
        db.execute("INSERT INTO social_state VALUES(?,?,?,?,?)", (key, Relationship(familiarity=33).model_dump_json(), "calm", 5, 0))
        db.execute("INSERT INTO social_turn(scope_key,request_id,digest,player_text,audit,result,npc_text,mode,displayed) VALUES(?,?,?,?,?,?,?,?,1)",
                   (key, "old-1", "d", "Hello", "{}", "{}", "Welcome.", "speech"))
    store = SocialStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
    loaded = store.load(key)
    assert loaded["relationship"].familiarity == 33 and loaded["history"][0].npc_text == "Welcome."
    assert loaded["conversation"].turns == 0
    SocialStore(path)  # reopening a version-2 file is fine
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=3")
    with pytest.raises(StoreFailure):
        SocialStore(path)


def test_only_displayed_turns_update_conversation_state(rig):
    store, key, _ = rig
    turn(rig, "r1", "Where is the mill?", show=False)
    assert store.load(key)["conversation"].turns == 0  # staged, not heard
    store.cancel(key, "r1")  # interrupted
    assert store.load(key)["conversation"].turns == 0
    state, audit = turn(rig, "r2", "Where is the mill?")  # a retried question is not a repeat
    assert audit["turn_type"] == "new" and state["reading"].type == "new"
    conv = store.load(key)["conversation"]
    assert conv.turns == 1 and conv.told == ("e1",) and conv.last_move == "answer" and conv.replies[-1].startswith("Aye")


def test_duplicate_receipt_never_double_counts(rig):
    store, key, _ = rig
    turn(rig, "r1", "Where is the mill?")
    before = store.load(key)["conversation"]
    store.displayed(key, "r1")
    store.displayed(key, "r1")
    assert store.load(key)["conversation"] == before and before.turns == 1
    with pytest.raises(StateConflict):
        store.displayed(key, "never-staged")


def test_repeats_are_recorded_and_cached_begin_turn_returns_the_same_reading(rig):
    store, key, profile = rig
    turn(rig, "r1", "Where is the mill?")
    state, audit = turn(rig, "r2", "Where is the mill?", move="answer_differently", evidence=())
    assert audit["turn_type"] == "repeat"
    again, _, cached = store.begin_turn(key, "r2", PlayerInput(text="Where is the mill?"), profile.persona, store.load(key)["revision"])
    assert cached is not None and again["reading"].type == "repeat"
    conv = store.load(key)["conversation"]
    assert conv.topics[-1].asked == 2 and conv.last_type == "repeat"


def test_repetition_does_not_change_relationship_or_trust(rig):
    store, key, _ = rig
    turn(rig, "r0", "Where is the mill?")
    baseline = store.load(key)["relationship"]
    for i in range(1, 6):
        turn(rig, f"r{i}", "Where is the mill?", move="close_topic")
    after = store.load(key)["relationship"]
    assert (after.trust, after.favourability) == (baseline.trust, baseline.favourability)
