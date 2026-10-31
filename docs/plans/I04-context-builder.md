# I04 first slice: NPC situation and response influences

Status: plan reviewed before implementation (self-review); implementation/check results recorded below.

## Outcome and boundary

Build a pure, game-independent `build_situation(turn, snapshot, now)` that explains how NPC identity/role, transient state, player relationship and fresh perceivable observations interact. This is the first half of M04 and the minimum I00 schemas needed by it. It consumes canonical input; teammates still own game/CV capture and normalization.

Output includes selected observations, exclusions/conflicts, appraised availability/threat/relationship, and source-linked influences on willingness, tone, brevity and disclosure. It does not select a final dialogue route, update trust, retrieve knowledge, call a model, render a prompt or deliver speech. Those remain M03/M02/M05/M06/M08. A scenario CLI previews this output without any network/game/GPU dependency.

## Implementation plan

1. Add validated bounded Pydantic contracts for scope, persona, runtime state, directed relationship, observation, turn, snapshot and situation. Reject wrong scope/NPC/player/revision, invalid values and unsupported schema versions. Use a narrow typed fact vocabulary plus inert extension data; no raw game keys.
2. Resolve fresh NPC-perceivable observations deterministically by configured source priority and time; preserve conflict/exclusion reasons. Unknown visibility, future/expired facts, low confidence and player assertions cannot become NPC knowledge. Equal-authority/time contradictions abstain instead of arbitrary winner selection.
3. Compose explicit response influences from persona/role + state + relationship + selected facts. Combat overrides availability, visible weapon interacts with fear/caution, familiarity differs from trust, and busy/closed-shop obligations differ from generic hostility. Keep unknown facts unknown and trace each inference to its source fields.
4. Add two public synthetic world scenarios and an offline CLI so input teams can see exact contracts and the user can inspect the output now. Use normal source packaging and the existing pytest dependency; no service/agent framework or dynamic rule engine.
5. Unit-test contracts and builder behavior, run full offline regression, test the CLI with real fixtures, and measure a small CPU-only construction baseline. Document limits and the not-yet-implemented stages.

## Plan self-review

- Keep M03 ownership: context produces influences/appraisal, not authored dialogue or a hidden generation policy.
- Keep source authority in trusted builder configuration; a player text field cannot claim telemetry priority. Source labels still require authenticated adapters in the future runtime.
- Freshness is based on an explicit aware UTC `now`, not player clocks. Verify observation world time does not come from the future of the supplied turn. Snapshot observation freshness is not assumed: transient availability is unknown unless supplied fresh facts establish it.
- No relationship deltas from player statements/CV. No secret grants based on favourability, occupation or inferred faction knowledge.
- Limit input sizes and use immutable validated models; no arbitrary plugin system, background workers, model calls or persistent caches.
- Test unseen/expired/ambiguous weapon facts, cross-world/player leakage, contradictory telemetry/CV, same-time ties, claim injection, busy-friendly versus threatening situations, and pure deterministic non-mutation.
- Stage-two evidence/history packing remains deferred until M03/M05 contracts are integrated. This slice cannot claim end-to-end latency, response realism or correct generated dialogue.

## Verification record

Implemented: bounded immutable contracts, pure situation resolution/appraisal, two synthetic-world fixtures and offline JSON preview. Initial review found service ownership ambiguity and max-ID provenance bounds; owner validation was added and a max-ID regression test was observed failing before its source-reference fix. Two early fixture setup failures were corrected without weakening assertions. Extra disposition/scene-grounding, threshold and payload tests cover the affected rules.

Commands: `.venv/Scripts/python.exe -m pip install -e . --no-deps --no-build-isolation`; initial regression 81 passed, final `.venv/Scripts/python.exe -m pytest -q` -> **88 passed** after independent-review fixes; `pip check` -> no broken requirements. Offline CLI returns the expected familiar/guarded/busy result. Small CPU-only timings and limits are in [context guide](../CONTEXT_BUILDER.md). No API/game/GPU testing or generated-dialogue quality claim.

Initial self-review verdict was followed by an independent review requested by the user. It found suppressed closed-service constraints and incomplete appraisal provenance. Four reproducing cases failed, fixes added independent constraints/six validated dependency records, and the reviewer independently reran 88 tests with a go verdict. See the [review report](../reviews/2026-10-31-context-implementation-review.md). This is not completion of I00/M04/full pipeline or a substitute for teammate PR approval. Runtime delivery/revision guarantees remain pending state/orchestration work. Changes remain on a feature branch; no direct main implementation push.
