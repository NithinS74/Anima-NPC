# M09 - Turn orchestrator, replay console and evaluation

Status: proposed | Requirement: SYS-11 | Owner/reviewer: unassigned

## Responsibility

Compose M01-M08 using their interfaces. Provide a replay/test console, request lifecycle and local debug trace. Core integration must not require Skyrim, audio devices, CV inference or paid API calls in CI. UI is a development console, not a new website product.

## Turn flow

Normalize -> reserve request/deduplicate and scope/NPC turn ownership -> load relevant revision/epoch -> build situation -> plan -> optional retrieval -> bounded context -> optional generation -> validation/optional repair -> atomic compare-and-stage result/outbox -> guarded delivery -> ack reconciliation. Recheck cancellation/relevant state at staging and dispatch; no transaction spans inference. Use a monotonic ingress deadline and earlier model cutoff, initially 2,450 ms with 550 ms reserved for fallback/commit/serialization. Report server response-ready separately from client delivery.

Expose planned `POST /api/npc-turn`, `POST /api/events`, `POST /api/delivery-acks`, `POST /api/turns/{id}/cancel`, `GET /api/health`, and developer-only trace lookup. Text/silence/cue outputs use one contract. Keep retrieved secrets/internal policy in an opt-in local debug channel, never in the player response object. Health indicates ready/degraded/unavailable dependencies rather than just a live process.

Use the [resource profile](../RESOURCE_PROFILE.md): single process, one global generation slot, two pending turns total and per-NPC arbitration across sessions initially. Priority cancellation/combat events bypass generation admission. On overload reject with typed busy status; never lose authoritative relationship events by coalescing them as telemetry. Bound retained sessions/workers/traces/history too. Shut down by invalidating pending output and preserving known delivery state; after restart ambiguous started speech is not replayed blindly.

## Console and telemetry

NPC selector, scenario/world selector, text input, recent turns, speech/silence/cue indicator, and validated test parameters (role/persona, relationship, location/time and availability). Parameter changes apply to an explicit test branch and invalidate pending turns, not overwrite live game state. Start with a portrait/text presentation; an optional compatible avatar viewer is described in [browser demo feasibility](../research/BROWSER_DEMO.md). Optional mic/audio comes later. Debug view shows plan, dependencies, filtered evidence IDs, token budget, relationship changes, stage timings, call count and fallback reasons. Keep secrets hidden by default.

## Acceptance / handoff

Implement fake vertical slice before real providers. Run [evaluation](../EVALUATION.md) and report generated-only plus all-route distributions. Verify restart, duplicate request, model failure, missing KB, state conflict, cancellation and overload without session crashes. Provide documented bootstrap/health/replay commands, one recorded demo scenario and requirement-mapped results. No mandatory cloud deployment.
