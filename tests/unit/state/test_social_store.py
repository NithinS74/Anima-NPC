import sqlite3

import pytest

from npc.contracts.context import PlayerInput, Relationship, Scope
from npc.state.social_store import SocialStore, StateConflict, StoreFailure
from tools.npc_lab.service import load_profiles


@pytest.fixture
def state(tmp_path):
    clock = [100.0]
    store = SocialStore(tmp_path / "social.sqlite3", clock=lambda: clock[0])
    p = load_profiles()["mira"]
    key = store.key(Scope(game_id="demo", world_id="village", save_branch_id="a"), "mira", "player-1")
    initial = store.ensure(key, p.relationship, p.mood)
    return store, key, p, initial, clock


def begin(state, request="r-1", text="fuck you", revision=None):
    store, key, p, initial, _ = state
    return store.begin_turn(key, request, PlayerInput(text=text), p.persona, initial["revision"] if revision is None else revision)


def test_restart_and_event_dedup_do_not_repeat_relationship_changes(state):
    store, key, p, _, _ = state
    first, audit, _ = begin(state)
    reopened = SocialStore(store.path)
    assert reopened.load(key)["relationship"] == first["relationship"]
    second, repeated, _ = begin(state)
    assert second["revision"] == first["revision"]
    assert audit == repeated
    with pytest.raises(StateConflict): begin(state, text="different message")


def test_scope_player_and_npc_isolation(state):
    store, key, p, initial, _ = state
    begin(state)
    for world, npc, player in [("elsewhere", "mira", "player-1"), ("village", "elin", "player-1"), ("village", "mira", "player-2")]:
        other = store.key(Scope(game_id="demo", world_id=world, save_branch_id="a"), npc, player)
        assert store.ensure(other, p.relationship, p.mood)["relationship"] == initial["relationship"]


def test_positive_conversation_gains_are_cooldown_limited(state):
    store, key, p, initial, clock = state
    first, _, _ = begin(state, text="thanks")
    second, _, _ = begin(state, "r-2", "thanks", first["revision"])
    assert second["relationship"] == first["relationship"]
    assert second["relationship"].trust == initial["relationship"].trust
    clock[0] += 61
    third, _, _ = begin(state, "r-3", "thanks", second["revision"])
    assert third["relationship"].favourability == first["relationship"].favourability + 1


def test_expected_revision_conflict_and_test_override(state):
    store, key, p, initial, _ = state
    changed, _, _ = begin(state)
    with pytest.raises(StateConflict): begin(state, "r-2")
    with pytest.raises(StateConflict): store.override(key, p.relationship, "calm", initial["revision"])
    override = store.override(key, Relationship(trust=50), "calm", changed["revision"])
    assert override["relationship"].trust == 50


def stage(store, key, request, revision):
    preview = {"result":{"response":{"mode":"speech","text":"A remembered reply."}}}
    store.stage_preview(key, request, preview, revision)
    return preview


def test_only_acknowledged_displayed_response_enters_memory(state):
    store, key, _, _, _ = state
    current, _, _ = begin(state)
    assert not store.load(key)["history"]
    stage(store, key, "r-1", current["revision"])
    assert not store.load(key)["history"]
    store.displayed(key, "r-1")
    memory = store.load(key)["history"]
    assert len(memory) == 1 and memory[0].npc_text == "A remembered reply."
    assert memory[0].player_text == "fuck you"
    store.displayed(key, "r-1")
    assert len(store.load(key)["history"]) == 1


def test_cancelled_unseen_response_cannot_be_acknowledged(state):
    store, key, _, _, _ = state
    current, _, _ = begin(state)
    stage(store, key, "r-1", current["revision"])
    store.cancel(key, "r-1")
    with pytest.raises(StateConflict): store.displayed(key, "r-1")
    assert not store.load(key)["history"]


def test_history_query_is_bounded_and_restart_safe(state):
    store, key, _, current, _ = state
    for index in range(12):
        request = f"r-{index}"
        current, _, _ = begin(state, request, "How is work?", current["revision"])
        stage(store, key, request, current["revision"]); store.displayed(key, request)
    history = SocialStore(store.path).load(key)["history"]
    assert [m.request_id for m in history] == [f"r-{i}" for i in range(4,12)]


def test_capacity_and_unknown_schema_fail_explicitly(tmp_path):
    path = tmp_path / "state.sqlite3"
    store = SocialStore(path)
    with pytest.raises(StoreFailure, match="state_capacity"):
        SocialStore(path, max_bytes=1)
    with sqlite3.connect(path) as db: db.execute("PRAGMA user_version=99")
    with pytest.raises(StoreFailure, match="unsupported_state_version"):
        SocialStore(path)


def test_game_memory_provenance_is_explicit_and_default_lab_is_preserved(state):
    store,key,profile,initial,clock=state
    updated,_,_=begin(state,'provenance','Hello',initial['revision'])
    stage(store,key,'provenance',updated['revision']);store.displayed(key,'provenance')
    assert SocialStore(store.path).load(key)['history'][0].source=='console_display'
    assert SocialStore(store.path,memory_source='game_completed').load(key)['history'][0].source=='game_completed'
    with pytest.raises(ValueError):SocialStore(store.path,memory_source='heard')
