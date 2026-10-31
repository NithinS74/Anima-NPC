# Team workflow

This repository began empty. It now contains a reviewed design baseline and the first [context-construction slice](CONTEXT_BUILDER.md), not a complete NPC engine. Select implementation packages together before assigning work; issue drafts remain local until explicitly published.

## Contract-first collaboration

For each implementation task, teammates and agents follow the [development skill](../.agents/skills/develop-npc-component/SKILL.md): plan, review that plan before coding, implement with unit tests for each new/changed working component, review the diff and run applicable regression. Use the [reviewer skill](../.agents/skills/review-npc-design/SKILL.md) to check relevant design assumptions. Read [AGENTS.md](../AGENTS.md) for agent entry instructions. Routine review may be explicitly labelled self-review; an independent review must actually be independent.

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

The [repository structure guide](REPOSITORY_STRUCTURE.md) defines the scaffolded source/test tree and maps each TRD to its code home. Put game/replay mappings under `src/npc/adapters/`, shared schemas under `contracts/`, and composition/console assets under `runtime/`. Directory existence does not imply implemented behavior. Use the guide as the single source for placement instead of starting another backend tree or duplicating fixtures.

Branches: `feature/<issue-id>-<short-name>`. PRs state resulting behavior, interface changes and validation. Definition of done: reviewed plan, reviewed implementation, meaningful unit tests for each new/changed working component, passing existing offline regression and relevant contract/integration checks, failure/cancellation cases where applicable, updated docs, no secrets/game binaries, runnable example and relevant metrics. Record review findings, exact checks/outcomes and unverified limitations. Team PR review remains part of merging; it need not block an agent from implementing an already-reviewed authorized plan. Avoid tests that merely mirror implementation or claims that tests guarantee no future breakage.

## Environment

Use the project `.venv`; never rely on a teammate's global Python packages. [SETUP](../SETUP.md) documents exact commands and dependency files. API keys belong in local `.env` based on `.env.example`. Runtime generated audio and model/database directories are ignored; the user knowledge folder is not automatically excluded by the current ignore rules. Check corpus privacy/licensing before tracking it. No framework/model dependency should be added without the owning module needing it.
