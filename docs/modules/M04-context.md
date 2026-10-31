# M04 - Context builder and dependency resolution

Status: `build_situation` first slice implemented; `assemble` still proposed | Requirement: SYS-03 | Review: independent agent review/re-review passed; teammate PR approval pending

See [working context-builder guide](../CONTEXT_BUILDER.md), [source](../../src/npc/context/builder.py) and [implementation plan](../plans/I04-context-builder.md). This does not mark all of M04 complete.

## Responsibility and two-stage boundary

`build_situation(input, snapshot) -> Situation` determines what this NPC perceives, believes and needs to react to. `assemble(situation, plan, evidence, memory, budget) -> ContextBundle` produces final bounded context. M03 sits between these calls; M05 runs for required or uncertain knowledge need, with at most one retrieval pass. M06 formats the result, not this module. Uncertain retrieval may return empty and lead to honest ignorance; it does not start an agent/tool loop.

## Algorithm

Resolve identity and save branch; join fresh observations with persona, relationship, goals and recent delivered history. Apply visibility and freshness before any social inference. Select relevant events by proximity, salience and effect on the active NPC. Maintain source priority for conflicts but preserve uncertainty. Infer social effects through explicit rules with reason codes (e.g. visible weapon -> perceived threat -> lowered engagement).

Return dependency records `{fact_id, derived_state, affected_decisions, confidence, reason}`. Do not insert every telemetry value into the prompt. Core fields are mandatory: NPC identity/boundaries, plan, current constraints and response schema. Optional evidence/history/CV consume remaining tokens by relevance and freshness.

Retrieve only after caller resolves eligibility from the NPC's knowledge grants and current world. Final assembly rechecks eligibility, revision, validity time and scope of each evidence item. A source fact can be authoritative world truth but still excluded from this NPC's view. Recent history is trimmed before critical policy/persona. If the minimum prompt cannot fit, return a no-generation fallback request rather than silently removing safeguards.

## Budget and interfaces

Initial context target <=2,048 input tokens, configurable per provider. Reserve output headroom and provider message overhead. Provider tokenizer is preferred; conservative estimate requires a margin and actual-usage comparison. RAG evidence initially <=600 tokens, recent dialogue <=500, visual descriptors <=150; all share one total. Three 300-500-token hits may not fit: pack whole eligible excerpts by relevance, preserve source attribution and measure retrieval quality both before and after prompt packing. Do not silently cut away supporting facts while retaining their evidence IDs. Automated memory summaries are deferred.

ContextBundle contains structured persona, perceived situation, directed relationship, intent/constraints, accepted evidence, recent history, uncertainty notes, dependency records and revision/hash. Debug records are not all sent to the LLM.

## Acceptance / handoff

Supply fixtures for unseen theft, contradictory CV/telemetry, inaccessible secret, busy-friendly NPC, expired event and oversized history. Assert mandatory constraints survive pruning and each included fact has a source/effect. Swapping a Skyrim-shaped input for a synthetic space-station input must require no context-builder source changes.

Implementation update: the [social-state slice](../SOCIAL_STATE.md) adds deterministic appraisal, persona temperament, SQLite directed relationships and bounded acknowledged dialogue history. The [separate lab](../NPC_LAB.md) exercises these contracts; production game delivery, full M02 semantics and semantic grounding are still future work.
