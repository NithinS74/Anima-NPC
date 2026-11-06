"""I24 WP-B: candidate pool larger than top_k; at most top_k passages reach the prompt."""

import json

import pytest
from pydantic import ValidationError

from npc.behavior import choose_plan
from npc.context import build_situation
from npc.contracts.knowledge import Evidence, KnowledgeContext
from npc.generation.prompt import build_prompt
from npc.rag.config import RAGConfig
from npc.rag.evidence import normalize_result, select_binding


def config(**changes):
    data = dict(bindings=[dict(game_id="g", world_id="w", npc_ids=["n"], source="lore.txt")])
    data.update(changes)
    return RAGConfig.model_validate(data)


def test_candidate_k_defaults_above_top_k_and_is_bounded():
    assert config().candidate_k == 8 and config().top_k == 3
    with pytest.raises(ValidationError):
        config(candidate_k=9)
    with pytest.raises(ValidationError):
        config(top_k=3, candidate_k=2)
    with pytest.raises(ValidationError):
        config(top_k=4)


def test_normalize_accepts_up_to_candidate_k_and_reports_top_k(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    cfg = config()
    binding = cfg.bindings[0]
    matches = [dict(id=f"c{i}", text="text", source="lore.txt", chunk_index=i, distance=0.1, truncated=False) for i in range(8)]
    result = normalize_result(cfg, situation, binding, situation.player_input.text, dict(query=situation.player_input.text, matches=matches))
    assert len(result.evidence) == 8 and result.top_k == 3
    too_many = normalize_result(cfg, situation, binding, situation.player_input.text, dict(query=situation.player_input.text, matches=matches + matches[:1]))
    assert too_many.status == "unavailable"


def test_at_most_top_k_passages_reach_the_prompt(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    hits = tuple(Evidence(id=f"c{i}", text=f"Passage {i}.", source="lore.txt", chunk_index=i, distance=0.1) for i in range(8))
    for top_k in (1, 3):
        knowledge = KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status="ok", evidence=hits, top_k=top_k)
        prompt = build_prompt(situation, choose_plan(situation), max_input_bytes=12000, knowledge=knowledge)
        assert len(prompt.evidence) <= top_k
        assert len(json.loads(prompt.messages[1].content).get("retrieved_evidence", [])) <= top_k
