"""Recheck retrieved knowledge against the current interaction before prompting."""

from npc.contracts.knowledge import KnowledgeContext


def assemble_knowledge(situation, knowledge: KnowledgeContext) -> KnowledgeContext:
    if knowledge.scope != situation.scope or knowledge.npc_id != situation.npc_id:
        return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status="forbidden")
    if knowledge.status != "ok":
        return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id, status=knowledge.status, source_kind=knowledge.source_kind, top_k=knowledge.top_k)
    # Observation IDs share the output citation namespace. Do not allow collisions.
    seen = {fact.id for fact in situation.perceived_facts}
    eligible = []
    for hit in knowledge.evidence:
        if hit.id in seen or hit.truncated or not hit.text.strip():
            continue
        seen.add(hit.id)
        eligible.append(hit)
    return KnowledgeContext(scope=situation.scope, npc_id=situation.npc_id,
                            status="ok" if eligible else "empty", evidence=tuple(eligible), source_kind=knowledge.source_kind, top_k=knowledge.top_k)
