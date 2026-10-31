---
name: review-npc-design
description: Review NPC architecture, TRDs or implementation changes for justified complexity, correctness, and efficient operation alongside a game. Use for a requested design review or milestone readiness audit.
---

# Review NPC design

Use the repository's current user decisions and contracts as the baseline. Read `docs/TRD.md`, `docs/CONTRACTS.md`, `docs/DECISIONS.md`, the affected module TRDs and the evaluation/backlog documents as needed. Resolve repository-relative paths from the repository root, not this skill directory.

## Review standard

The goal is maintainable, measured fitness for purpose. Neither the fewest lines nor the most abstractions establishes an optimal implementation. Do not promise zero technical debt or proven runtime performance from a document review.

Preserve API-first, model-independent generation and the user's 4 GB VRAM preference as a future experiment, not a minimum guarantee. The intended runtime is explicit modules with deterministic decisions where practical and model calls only when needed. No autonomous multi-agent runtime, compulsory classification call, or always-on LLM critic is needed to satisfy that intent. This does not prohibit independent reviewer agents during development.

For each meaningful mechanism, identify the user outcome, concrete failure it prevents, current implementation cost and simpler sufficient alternative. Classify it as implement now, preserve a contract for later, measure first, or remove. Keep warranted reliability/knowledge boundaries; do not remove them merely to reduce code. Avoid speculative distributed infrastructure, generic plugin frameworks and unmeasured caches.

## Evidence to inspect

- Walk an authored/silent turn, a generated knowledge-bearing turn, a failed/late generation and an interrupted turn end to end. Trace IDs, state changes, evidence eligibility, model calls, delivery and memory.
- Check NPC arbitration across sessions, atomic validation-to-stage behavior, idempotency after expiry, ambiguous/partial acknowledgements and what an incapable game adapter can actually guarantee.
- Separate world truth, perception, player claims and memory. Follow one inaccessible secret through filtering, context, model output and evaluation. A valid evidence ID is not semantic entailment.
- Account for the whole deadline, including persistence/fallback/delivery reserve. Cancellation of a local task may not cancel provider billing/work. Verify every concurrency/queue/background task has a bound and that optional CV/indexing/demo rendering competes fairly with the game.
- Assess RAG query-filter size, embedding/collection lifecycle, missing metadata, query-vs-index races, source attribution and token packing. Avoid full-corpus scans/enumerations per turn and stateful reindex machinery without a measured need.
- Check objective quality measures against refusal/silence gaming, route-mix latency gaming, small sample uncertainty, renderer/GPU confounding and missing provider/model versions.
- Distinguish implemented/tested facts, documented invariants, hypotheses and optional scope. Use existing checks and targeted experiments; default to fakes and no paid/live game actions.

Browse primary documentation when a technical claim is uncertain or version-sensitive. Do not claim a benchmark or asset compatibility check was run when only source documentation was inspected. If delegating a review, keep it read-only unless edits were requested and avoid giving the reviewer a desired verdict.

## Deliverable

Return severity-ranked findings with exact file/line references, a concrete failure scenario, the justified correction and its verification. Report what is sound, unnecessary complexity, missing requirements, remaining empirical risks and a go/conditional-go/no-go verdict for the next milestone. Distinguish blockers to starting implementation from gates for claiming readiness or expanding scope.

If fixes are authorized, make narrow consistent changes across contracts/modules/backlog, then verify affected examples and links. Record resolutions without rewriting unrelated scope. Recommend new infrastructure only with a concrete trigger. A review request never by itself authorizes committing, pushing, changing mods, recording players or calling a paid API; use explicit session authorization for those actions.
