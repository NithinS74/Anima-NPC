"""I24 WP-B: repeated_reply, move_not_made and unsupported_name. Offline."""

import json

import pytest

from npc.behavior import apply_move, choose_plan
from npc.context import build_situation
from npc.contracts.context import ConversationState, DialogueMemory
from npc.contracts.dialogue import CurrentState, ProviderReply
from npc.contracts.knowledge import Evidence
from npc.validation import validate_response
from tools.npc_lab.service import LabTurn, load_profiles, make_scenario


def situation(text="Tell me about the road", conversation=None, memory=()):
    profile = load_profiles()["elin"]
    turn = LabTurn(request_id="r", persona_id="elin", text=text, relationship=profile.relationship, mood="neutral")
    scenario = make_scenario(profile, turn, 1, memory, conversation)
    return build_situation(scenario.turn, scenario.snapshot, scenario.now)


def check(text, sit, move=None, evidence=(), allowlist=()):
    plan = choose_plan(sit)
    assert plan.route == "generate"
    if move:
        plan = apply_move(plan, move, sit.conversation, sit.persona, "r")
    reply = ProviderReply(content=json.dumps({"mode": "speech", "text": text, "cue": None, "evidence_ids": []}), model="m", finish_reason="stop")
    return validate_response(reply, sit, plan.model_copy(update={"max_words": 40, "max_sentences": 3}),
                             CurrentState(dialogue_revision=1, turn_epoch=1), evidence=evidence, name_allowlist=allowlist).violations


def test_repeated_reply_by_similarity_and_by_opening():
    conv = ConversationState(turns=1, replies=("The road east is long and dusty.",))
    sit = situation(conversation=conv)
    assert "repeated_reply" in check("The road east is long and dusty.", sit)
    assert "repeated_reply" in check("The road east is long and wet with rain today.", sit)  # same opening words
    assert "repeated_reply" not in check("Mind the bandits past the old bridge.", sit)


def test_repetition_is_also_checked_against_displayed_history():
    memory = (DialogueMemory(request_id="a", player_text="x", npc_text="Mind the bandits past the old bridge."),)
    assert "repeated_reply" in check("Mind the bandits past the old bridge.", situation(memory=memory))


def test_expand_must_add_something_new():
    conv = ConversationState(turns=1, replies=("Mind the bandits past the old bridge.",))
    sit = situation(conversation=conv)
    assert "move_not_made" in check("Bandits, past the bridge, mind.", sit, move="expand")
    assert "move_not_made" not in check("Wolves hunt near the pines after dusk.", sit, move="expand")
    assert "move_not_made" not in check("Bandits, past the bridge, mind.", sit, move="answer")


@pytest.mark.parametrize("text,player,expect", [
    ("They say Whitehaven is quiet.", "Tell me about the road", True),
    ("They say Dunmere's roads are quiet.", "I come from Dunmere", False),
    ("You mentioned Hjaalmarch roads.", 'I read "Hjaalmarch" somewhere', False),
    ("Well, the road is quiet.", "Tell me about the road", False),
    ("Aye, the Lantern Inn is warm.", "Tell me about the road", False),
    ("Honestly, Stormhelm knows.", "Tell me about the road", True),
])
def test_unsupported_name(text, player, expect):
    assert ("unsupported_name" in check(text, situation(player))) is expect


def test_names_from_evidence_are_allowed():
    hit = Evidence(id="e", text="Captain Brannoch holds the pass.", source="s", chunk_index=0, distance=0.1)
    assert "unsupported_name" not in check("They say Brannoch holds the pass.", situation(), evidence=(hit,))
    assert "unsupported_name" in check("They say Brannoch holds the pass.", situation())


def test_scene_values_and_allowlist_are_accepted_names():
    from npc.contracts.context import SceneItem
    sit = situation("Tell me about the road")
    assert "unsupported_name" in check("They say Brannoch is quiet.", sit)
    with_scene = sit.model_copy(update={"scene": (SceneItem(label="banner", value="Brannoch crest"),)})
    assert "unsupported_name" not in check("They say Brannoch is quiet.", with_scene)
    assert "unsupported_name" in check("Honestly, Zorbland is quiet.", sit)
    assert "unsupported_name" not in check("Honestly, Zorbland is quiet.", sit, allowlist=("Zorbland",))


def test_skyrim_allowlist_comes_from_config_not_core():
    import pathlib
    from npc.adapters.skyrim.__main__ import _name_allowlist
    from types import SimpleNamespace
    terms = _name_allowlist(SimpleNamespace(role_rules_file="configs/skyrim/role_rules.json"), pathlib.Path(__file__).resolve().parents[3])
    assert {"Jarl", "Nord", "Skyrim", "Imperial", "Stormcloak", "Tamriel", "Septims"} <= set(terms)


def test_short_replies_do_not_trip_repeat_checks():
    conv = ConversationState(turns=2, replies=("Not for sale, friend.",))
    sit = situation(conversation=conv)
    assert "repeated_reply" not in check("Not for sale, friend.", sit)
    assert "repeated_reply" not in check("Not for sale, stranger.", sit)


def test_only_last_two_replies_are_compared_and_five_shared_words_are_fine():
    conv = ConversationState(turns=4, replies=("Mind the bandits past the old bridge.", "Wolves hunt near the pines.", "The inn serves stew nightly."))
    sit = situation(conversation=conv)
    assert "repeated_reply" not in check("Mind the bandits past the old bridge.", sit)  # third-oldest is not compared
    conv = ConversationState(turns=2, replies=("The road east is long and dusty.",))
    assert "repeated_reply" not in check("The road east is wet.", situation(conversation=conv))  # five shared words only
