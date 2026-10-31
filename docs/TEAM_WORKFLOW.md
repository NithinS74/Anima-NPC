# Team workflow

This repository began empty. It contains a reviewed design baseline, not a running engine. Select implementation packages together before assigning work. The first commit/push contains planning/setup/skill files; issue drafts remain local until explicitly published.

## Contract-first collaboration

1. Review [TRD](TRD.md), [source differences](TRACEABILITY.md) and [contracts](CONTRACTS.md) together. Record acceptance of changed course scope separately if needed.
2. Select one owner/reviewer per issue in [backlog](BACKLOG.md). Historical names/roles do not automatically assign work.
3. Complete I00: executable schemas, shared fixtures and fakes. Use the corrected planning baseline to agree the first executable schema before independent implementation. Documentation version and future wire-schema version are separate.
4. Build one fake vertical slice through M09. Then replace one fake module at a time with the real implementation.
5. Merge small reviewed branches continuously. Contract changes require an example fixture and updates to every affected consumer in the same change.

Suggested first workstreams to choose from: knowledge/RAG; state/context/behavior; provider/validation; input/replay/runtime/evaluation. These are packages, not assignments to named people. Mantella audit can proceed alongside them without making Skyrim a dependency for the team.

## Sequenced milestones

| Gate | Deliverable | Exit condition |
|---|---|---|
| G0 | Review baseline and development environment | Setup works, roles selected, unresolved scope decisions logged |
| G1 | Contracts + fakes + replay | Complete authored/silent/generated fake turns with trace and cancellation |
| G2 | First real API slice | Three personas, deterministic routing, one API provider, bounded validation |
| G3 | RAG + persistent relationships | Scoped retrieval, restart/isolation, updated context and failure handling |
| G4 | Evaluation | Held-out quality metrics, real latency/cost report and measured gaps |
| G5 | Optional integration | Mantella capture/facade, speech and CV independently evaluated |

Use relative milestones, not stale week/deadline dates from the PDFs. Do not delay G2 waiting for CV, speech, 3D assets, summaries, live reindex or a full mod adapter. The [review report](reviews/2026-10-31-design-review.md) justifies what is implemented now versus deferred. Browser scenario parameters belong in I09; an optional avatar never becomes a second orchestration engine.

## Repository conventions

Future implementation layout: `src/npc/{contracts,inputs,state,behavior,context,rag,generation,validation,output,runtime}`, `tests/{contracts,unit,integration}`, `fixtures/`, `configs/`, `scripts/`. These directories are proposed, not placeholder claims of implementation.

Branches: `feature/<issue-id>-<short-name>`. PRs state resulting behavior, interface changes and relevant validation. Definition of done: contract documented, independent fake-based tests, failure/cancellation cases where applicable, no secrets or game/model binaries, runnable example, metrics relevant to the change, reviewer approval. Avoid tests that merely mirror implementation.

## Environment

Use the project `.venv`; never rely on a teammate's global Python packages. [SETUP](../SETUP.md) documents exact commands and dependency files. API keys belong in local `.env` based on `.env.example`. Local knowledge, generated audio and model/database directories are ignored. No framework or model dependency should be added without the owning module needing it.
