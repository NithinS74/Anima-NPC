"""Does the peasant voice rumours when his persona says he may? One real API call, one retry at most.

The only change from proposal_live.py is one persona boundary line. No core code changes.
Run from the repository root.
"""
from __future__ import annotations

import asyncio
import json

import proposal_live as live

ks = live.ks
HEARSAY = ("speaks only of what this person has seen or heard", "may pass on rumours heard locally, clearly as hearsay, and may offer an opinion on them")


async def main() -> None:
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
    role = world["roles"]["low"]
    rows = []
    for attempt in range(2):
        item = ks.scenario("kingdom", "low", role, {"id": f"hearsay{attempt}", "text": live.WAR}, 200 + attempt)
        persona = item.snapshot.persona.model_copy(update={**live.PERSONA["low"], "boundaries": HEARSAY})
        reply = await runner.run(item.model_copy(update={"snapshot": item.snapshot.model_copy(update={"persona": persona})}))
        answer = reply.response.text if reply.response else None
        rows.append({"attempt": attempt, "reply": answer, "status": reply.status, "error": reply.error_code, "max_words": reply.plan.max_words,
                     "restricted_in_reply": ks.markers_in(answer or "", world["restricted_markers"]["low"]), "elapsed_ms": reply.elapsed_ms})
        print(json.dumps(rows[-1], ensure_ascii=False))
        if reply.status in {"model_success", "repair_success"}:
            break
    (live.HERE / "results/proposal_live_hearsay.json").write_text(json.dumps({"provider_calls": provider.calls, "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
