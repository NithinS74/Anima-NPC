"""Knowledge-scope study: does restricted world knowledge reach a lower-standing NPC's prompt?

Runs the real PreviewRunner, LocalRetriever, MiniLM encoder and Chroma index. The provider is a
recording stub, so no network or language model is involved: results describe the provider-bound
prompt, not what a model would say.

Run from the repository root:
    .venv/Scripts/python.exe -X utf8 research/cs3235_paper/experiments/knowledge_scope.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import platform
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "fixtures/evaluation/knowledge_scope"
OUT = Path(__file__).with_name("results") / "knowledge_scope.json"
WORK = ROOT / "output/knowledge_scope"
MODELS = ROOT / "output/paper_revision/models"
GAME = "scope-study"
CONDITIONS = ("unscoped", "scoped")


def load_study(path: Path = DATA) -> dict:
    return json.loads((path / "study.json").read_text(encoding="utf-8"))


def markers_in(text: str, markers) -> list[str]:
    folded = text.casefold()
    return [m for m in markers if m.casefold() in folded]


def validate_study(study: dict, path: Path = DATA) -> None:
    """Reject data that would make the measurement meaningless."""
    for name, world in study["worlds"].items():
        all_restricted = {m for ms in world["restricted_markers"].values() for m in ms}
        for query in world["queries"]:
            leaked = markers_in(query["text"], all_restricted)
            if leaked:
                raise ValueError(f"{query['id']} contains restricted marker {leaked}: player text must not supply it")
            if query["topic"] not in world["topics"]:
                raise ValueError(f"{query['id']} has unknown topic")
        for level, role in world["roles"].items():
            text = (path / name / role["file"]).read_text(encoding="utf-8")
            present = markers_in(text, world["restricted_markers"][level])
            if present:
                raise ValueError(f"{name}/{role['file']} holds its own restricted markers {present}")
            for topic, allowed in world["topics"].items():
                if not markers_in(text, [allowed[level]]):
                    raise ValueError(f"{name}/{role['file']} lacks its {topic} marker {allowed[level]!r}")


def rate(numerator: int, denominator: int) -> dict:
    return {"n": numerator, "of": denominator, "rate": numerator / denominator if denominator else None}


def summarize(rows: list[dict]) -> dict:
    """Denominators use only turns that reached the model route."""
    generated = [r for r in rows if r["route"] == "generate"]
    restricted = [r for r in generated if r["level"] != "top"]
    summary = {
        "turns": len(rows),
        "generated_turns": len(generated),
        "non_generated_turns": len(rows) - len(generated),
        "restricted_exposure": rate(sum(bool(r["exposed"]) for r in restricted), len(restricted)),
        "own_knowledge_available": rate(sum(r["own_marker_present"] for r in generated), len(generated)),
    }
    for level in ("low", "mid", "top"):
        subset = [r for r in generated if r["level"] == level]
        summary[level] = {
            "restricted_exposure": rate(sum(bool(r["exposed"]) for r in subset), len(subset)),
            "own_knowledge_available": rate(sum(r["own_marker_present"] for r in subset), len(subset)),
        }
    for kind in ("direct", "paraphrase", "authority", "injection"):
        subset = [r for r in restricted if r["kind"] == kind]
        summary[f"exposure_{kind}"] = rate(sum(bool(r["exposed"]) for r in subset), len(subset))
    return summary


class RecordingProvider:
    """Stores the exact prompt and returns the scripted reply. It is not a language model."""

    def __init__(self):
        from npc.generation.provider import OfflineProvider

        self.inner = OfflineProvider()
        self.prompts = []

    async def generate(self, prompt, timeout_s):
        self.prompts.append(prompt)
        return await self.inner.generate(prompt, timeout_s)


def scenario(world: str, level: str, role: dict, query: dict, sequence: int):
    from npc.contracts.context import ContextScenario

    data = json.loads((ROOT / "fixtures/scenarios/smith_available.json").read_text(encoding="utf-8"))
    profile = json.loads((ROOT / "fixtures/personas/npc_lab/mira.json").read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).isoformat()
    scope = {"game_id": GAME, "world_id": world, "save_branch_id": "study"}
    persona = {**profile["persona"], "name": role["name"], "occupation": role["occupation"],
               "social_role": role["social_role"], "service_role": False}
    npc = f"{world}-{level}"
    data["now"] = stamp
    data["turn"].update(scope=scope, request_id=f"{npc}-{query['id']}", session_id=npc, npc_id=npc,
                        player_id="study-player", sequence=sequence, expected_dialogue_revision=0,
                        captured_at=stamp, simulation_time_s=float(sequence), facts=[],
                        player_input={"text": query["text"], "source": "text", "confidence": 1.0})
    data["snapshot"].update(scope=scope, npc_id=npc, player_id="study-player", storage_revision=0,
                            dialogue_revision=0, turn_epoch=sequence, persona=persona,
                            relationship={"favourability": 0, "trust": 0, "familiarity": 0, "fear": 0, "irritation": 0},
                            recent_dialogue=[],
                            npc_state={"observed_at": stamp, "ttl_ms": 60000, "mood": "calm",
                                       "current_goal": "get through the day"})
    return ContextScenario.model_validate(data)


def build_corpus(study: dict, work: Path) -> dict:
    """Same text in both conditions.

    Every role file is shared public lore plus that role's own section, so retrieval has to rank
    competing chunks. The unscoped baseline merges the lore and all three role sections.
    """
    corpus = work / "corpus"
    corpus.mkdir(parents=True)
    merged = {}
    for name, world in study["worlds"].items():
        lore = (DATA / name / "public_lore.md").read_text(encoding="utf-8").strip()
        parts = [lore]
        for role in world["roles"].values():
            text = (DATA / name / role["file"]).read_text(encoding="utf-8").strip()
            (corpus / role["file"]).write_text(f"{lore}\n\n{text}", encoding="utf-8")
            parts.append(text)
        merged[name] = f"merged_{name}.md"
        (corpus / merged[name]).write_text("\n\n".join(parts), encoding="utf-8")
    return merged


def bindings(study: dict, merged: dict, condition: str) -> list[dict]:
    rows = []
    for name, world in study["worlds"].items():
        for level, role in world["roles"].items():
            source = merged[name] if condition == "unscoped" else role["file"]
            rows.append({"game_id": GAME, "world_id": name, "npc_ids": [f"{name}-{level}"], "source": source})
    return rows


async def run_condition(study: dict, merged: dict, condition: str, service) -> list[dict]:
    from npc.rag.config import RAGConfig
    from npc.rag.local import LocalRetriever
    from npc.runtime.preview import PreviewLimits, PreviewRunner

    config = RAGConfig(kb_dir="corpus", data_dir="index", bindings=bindings(study, merged, condition))
    provider = RecordingProvider()
    limits = PreviewLimits(response_timeout_ms=30000, model_cutoff_ms=29000, retrieval_timeout_ms=5000,
                           max_input_bytes=12000, max_output_tokens=160)
    runner = PreviewRunner(provider, limits, retriever=LocalRetriever(config, service=service))
    rows, sequence = [], 0
    for name, world in study["worlds"].items():
        for level, role in world["roles"].items():
            for query in world["queries"]:
                sequence += 1
                before = len(provider.prompts)
                start = time.perf_counter()
                reply = await runner.run(scenario(name, level, role, query, sequence))
                elapsed = (time.perf_counter() - start) * 1000
                new = provider.prompts[before:]
                text = "\n".join(m.content for p in new for m in p.messages)
                own = world["topics"][query["topic"]][level]
                rows.append({
                    "condition": condition, "world": name, "level": level, "role": role["name"],
                    "query": query["id"], "kind": query["kind"], "topic": query["topic"],
                    "route": reply.plan.route if reply.plan else None, "status": reply.status,
                    "model_calls": len(new),
                    "evidence_chunks": [e.id for p in new[:1] for e in p.evidence],
                    "evidence_sources": sorted({e.source for p in new[:1] for e in p.evidence}),
                    "exposed": markers_in(text, world["restricted_markers"][level]),
                    "own_marker_present": bool(markers_in(text, [own])),
                    "ready_ms": elapsed,
                })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, default=WORK)
    args = parser.parse_args()
    study = load_study()
    validate_study(study)
    if args.work.exists():
        shutil.rmtree(args.work)
    merged = build_corpus(study, args.work)

    from npc.rag.backend import RAGService, Settings
    from npc.rag.backend.embeddings import LocalEmbedder

    service = RAGService(Settings(root=args.work, kb_dir="corpus", data_dir="index"), embedder=LocalEmbedder(MODELS))
    start = time.perf_counter()
    sync = service.sync()
    index_ms = (time.perf_counter() - start) * 1000
    if sync.errors:
        raise RuntimeError(f"indexing failed: {sync.errors}")

    rows = []
    for condition in CONDITIONS:
        rows += asyncio.run(run_condition(study, merged, condition, service))
    results = {c: summarize([r for r in rows if r["condition"] == c]) for c in CONDITIONS}
    for c in CONDITIONS:
        ready = [r["ready_ms"] for r in rows if r["condition"] == c and r["route"] == "generate"]
        results[c]["ready_ms"] = {"mean": statistics.mean(ready), "median": statistics.median(ready)}
    report = {
        "note": "Prompt-level measurement with a recording stub; no language model was called.",
        "python": platform.python_version(),
        "index": sync.model_dump(),
        "index_ms": index_ms,
        "results": results,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
