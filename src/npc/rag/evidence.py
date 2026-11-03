"""Identical source eligibility and evidence checks for local and HTTP retrieval."""

from npc.contracts.knowledge import Evidence, KnowledgeContext
from npc.rag.dialogue import dialogue_reference


def select_binding(config, situation):
    return next((binding for binding in config.bindings
                 if (binding.game_id, binding.world_id) == (situation.scope.game_id, situation.scope.world_id)
                 and situation.npc_id in binding.npc_ids), None)


def result_for(situation, binding, status, evidence=()):
    return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status=status, evidence=evidence,
                            source_kind="dialogue" if binding and binding.source_format == "dialogue_export" else "reference")


def normalize_result(config, situation, binding, query, data):
    if not isinstance(data, dict) or data.get("query") != query:
        return result_for(situation, binding, "unavailable")
    matches = data.get("matches")
    if not isinstance(matches, list) or len(matches) > config.top_k:
        return result_for(situation, binding, "unavailable")
    evidence, seen = [], set()
    for raw in matches:
        hit = Evidence.model_validate(raw)
        if hit.source != binding.source:
            return result_for(situation, binding, "unavailable")
        if hit.truncated or not hit.text.strip() or hit.id in seen:
            continue
        if config.max_distance is not None and hit.distance > config.max_distance:
            continue
        if binding.source_format == "dialogue_export":
            hit = dialogue_reference(hit)
            if hit is None:
                continue
        seen.add(hit.id)
        evidence.append(hit)
    return result_for(situation, binding, "ok" if evidence else "empty", tuple(evidence))
