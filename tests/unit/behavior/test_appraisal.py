import pytest

from npc.behavior.appraisal import appraise_social, relationship_effect
from npc.behavior import choose_plan
from npc.context import build_situation
from npc.contracts.context import PlayerInput, Relationship
from tools.npc_lab.service import LabTurn, load_profiles, make_scenario


@pytest.mark.parametrize("text,stimulus", [
    ("You are a fucking idiot", "directed_insult"), ("fuck you", "directed_insult"),
    ("Damn, this weather is terrible", "incidental_profanity"),
    ('He called me "an idiot" today', "neutral"),
    ("Someone said fuck you to me.", "neutral"),
    ("I'll kill you", "threat"), ("Sorry for what I said", "apology"),
    ("Thank you for your time", "gratitude"),
])
def test_context_of_language_matters(text, stimulus):
    p = load_profiles()["mira"]
    assert appraise_social(PlayerInput(text=text), p.persona, p.relationship).stimulus == stimulus


def test_familiar_banter_is_different_from_a_strangers_abuse():
    p = load_profiles()["mira"]
    friend = Relationship(favourability=80, trust=80, familiarity=90)
    utterance = PlayerInput(text="You bastard, haha, just kidding")
    assert appraise_social(utterance, p.persona, friend).stimulus == "rough_banter"
    assert appraise_social(utterance, p.persona, Relationship()).stimulus == "directed_insult"


def test_insult_changes_bounded_scores_but_incidental_profanity_does_not():
    p = load_profiles()["mira"]
    before = Relationship(favourability=-98, trust=-99, irritation=95)
    after, delta, _ = relationship_effect(PlayerInput(text="fuck you"), p.persona, before, positive_allowed=False)
    assert after.favourability == after.trust == -100
    assert after.irritation == 100
    assert delta["irritation"] == 5
    neutral, _, _ = relationship_effect(PlayerInput(text="Damn, rough day"), p.persona, before, positive_allowed=False)
    assert neutral == before


def test_uncertain_transcript_is_not_social_evidence():
    p = load_profiles()["mira"]
    after, delta, appraisal = relationship_effect(PlayerInput(text="fuck you", source="stt", confidence=0.2), p.persona, p.relationship, positive_allowed=True)
    assert after == p.relationship
    assert not any(delta.values())
    assert "uncertain_input_no_social_penalty" in appraisal.reasons


def plan(profile, text, relationship):
    p = load_profiles()[profile]
    turn = LabTurn(request_id="social-test", persona_id=profile, text=text, relationship=relationship, mood=p.mood)
    scenario = make_scenario(p, turn, 1)
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    return choose_plan(situation)


def test_role_and_temperament_change_an_insult_response_without_model_calls():
    relationship = Relationship(irritation=60)
    smith = plan("mira", "fuck you", relationship)
    host = plan("elin", "fuck you", relationship)
    assert smith.route == host.route == "authored"
    assert "damn" in smith.authored_text
    assert "damn" not in host.authored_text
    assert smith.authored_text != host.authored_text


def test_sustained_abuse_can_end_engagement():
    result = plan("daren", "fuck you", Relationship(irritation=90))
    assert result.route == "end" and result.authored_text == ""
    assert result.max_words == 0


def test_stranger_brevity_respects_service_role():
    guard = plan("daren", "What are you doing?", Relationship())
    host = plan("elin", "What are you doing?", Relationship())
    assert guard.max_words == 18 and guard.max_sentences == 1
    assert host.max_words == 40


def test_apology_does_not_erase_distrust():
    p = load_profiles()["mira"]
    before = Relationship(trust=-60, irritation=50)
    after, _, _ = relationship_effect(PlayerInput(text="I am sorry"), p.persona, before, positive_allowed=True)
    assert after.trust == -60
    assert after.irritation == 42


def test_apology_with_a_question_does_not_lose_the_question():
    result = plan("elin", "Sorry, where can I wait?", Relationship())
    assert result.route == "generate"
    assert result.knowledge_need == "required"


@pytest.mark.parametrize("text,expected",[("FUCK U","directed_insult"),("FIGHT ME","threat"),("fight me!","threat"),("Don't fight me","neutral"),("Fight me at chess","neutral"),('He said "FUCK U"',"neutral"),('"FIGHT ME"',"neutral"),("This is fucking cold","incidental_profanity")])
def test_targeted_chat_variants_do_not_penalize_quoted_or_incidental_speech(text,expected):
    from npc.behavior.appraisal import appraise_social
    from npc.contracts.context import PlayerInput,Persona,Relationship
    assert appraise_social(PlayerInput(text=text),Persona(name='Guard',occupation='guard',social_role='guard'),Relationship()).stimulus==expected
