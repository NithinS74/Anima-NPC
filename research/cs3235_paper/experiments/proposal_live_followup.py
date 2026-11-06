"""Follow-up to proposal_live.py: retry the two failed calls and test why rumours were not voiced.

Three real API calls at most. Checks whether the NPC's own rumour reached the prompt, and whether
removing the short stranger word limit changes the reply.
"""
from __future__ import annotations

import asyncio
import json

import proposal_live as live

ks = live.ks
RELATIONS = {"stranger": dict(favourability=0, trust=0, familiarity=0, fear=0, irritation=0),
             "acquaintance": dict(favourability=30, trust=20, familiarity=60, fear=0, irritation=0)}
TESTS = [("retry_low", "low", "stranger"), ("retry_mid", "mid", "stranger"), ("low_familiar", "low", "acquaintance")]


async def main() -> None:
    from npc.contracts.context import Relationship
    from npc.generation.config import load_provider
    from npc.rag.backend import RAGService, Settings
    from npc.rag.backend.embeddings import LocalEmbedder
    from npc.rag.config import RAGConfig
    from npc.rag.local import LocalRetriever
    from npc.runtime.preview import PreviewLimits, PreviewRunner

    study = ks.load_study()
    service = RAGService(Settings(root=ks.WORK, kb_dir="corpus", data_dir="index"), embedder=LocalEmbedder(ks.MODELS))
    config = RAGConfig(kb_dir="corpus", data_dir="index", bindings=ks.bindings(study, {n: f"merged_{n}.md" for n in study["worlds"]}, "scoped"))
    provider = live.Budgeted(load_provider(live.ROOT / "configs/providers/gemini.yaml"))
    limits = PreviewLimits(response_timeout_ms=45000, model_cutoff_ms=44000, retrieval_timeout_ms=5000, max_input_bytes=12000, max_output_tokens=400)
    runner = PreviewRunner(provider, limits, retriever=LocalRetriever(config, service=service))
    world = study["worlds"]["kingdom"]
    rows = []
    for number, (name, level, relation) in enumerate(TESTS, 1):
        role = world["roles"][level]
        item = ks.scenario("kingdom", level, role, {"id": name, "text": live.WAR}, 100 + number)
        persona = item.snapshot.persona.model_copy(update=live.PERSONA[level])
        snapshot = item.snapshot.model_copy(update={"persona": persona, "relationship": Relationship.model_validate(RELATIONS[relation])})
        reply = await runner.run(item.model_copy(update={"snapshot": snapshot}))
        prompt = provider.prompts[-1]
        text = "\n".join(m.content for m in prompt.messages)
        rows.append({"test": name, "relation": relation, "reply": reply.response.text if reply.response else None, "status": reply.status,
                     "error": reply.error_code, "max_words": reply.plan.max_words, "max_sentences": reply.plan.max_sentences,
                     "own_marker_in_prompt": ks.markers_in(text, [world["topics"]["plan"][level], world["topics"]["route"][level]]),
                     "restricted_in_prompt": ks.markers_in(text, world["restricted_markers"][level]),
                     "system_prompt_start": prompt.messages[0].content[:320], "elapsed_ms": reply.elapsed_ms})
        print(json.dumps(rows[-1], ensure_ascii=False))
    (live.HERE / "results/proposal_live_followup.json").write_text(json.dumps({"provider_calls": provider.calls, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
