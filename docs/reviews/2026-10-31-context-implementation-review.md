# Independent context-builder implementation review

Scope: uncommitted implementation on `feature/I04-context-builder`, first half of M04 plus the minimum I00 context schemas. This is an independent read-only agent review under `review-npc-design`, followed by root-agent fixes and independent re-review. It is separate from the earlier design review and implementation self-review.

## Initial findings

The reviewer independently ran the initial 81-test suite successfully and then reproduced two gaps outside that coverage:

| Severity | Finding | Failure example | Resolution |
|---|---|---|---|
| Medium | Independent service constraints disappeared behind dominant availability | Busy/closed smith had no closed-service influence; behavior policy could lose the explicit constraint against trading | Emit `service_closed` independently while keeping the dominant status; guard service role and owner |
| Medium | Derived states were not consistently linked to evidence | Station clerk was `available` from `npc.busy=false` without a dependency; explicit weapon absence also lacked a link | Add six bounded field/value/reason/source dependency records, including negative/unknown evidence, plus consistency validation |

Four targeted reproducing cases failed before correction. The fixes add busy+closed and combat+closed coverage, negative/unknown appraisal provenance, and dependency-schema checks. Existing wrong-owner and non-service cases explicitly assert no closed-service influence.

Source: [builder](../../src/npc/context/builder.py), [contracts](../../src/npc/contracts/context.py), [unit cases](../../tests/unit/context/test_builder.py), [contract cases](../../tests/contracts/test_context_contracts.py).

## Independent re-review

**Verdict: both findings resolved; go for integrating this first context-builder slice.** The reviewer reread the fixes and independently reran `.venv/Scripts/python.exe -m pytest -q`: **88 passed in 1.03 seconds**. No new readiness blocker was found. Root-agent regression also passed 88 tests, and `pip check` found no broken requirements.

The reviewer considered the pure bounded implementation, filtering before source priority, conflict abstention, isolated scopes/revisions, immutable state and separation of familiarity/trust/favourability appropriate. No speculative service, agent framework or plugin infrastructure was added.

## What this verdict does not cover

This is not confirmation that the entire TRD is implemented. M03 behavior decisions/templates; M04 evidence/history/token assembly; RAG and knowledge grants; provider/prompt integration; state persistence; and orchestration/validated delivery are intentionally deferred. The current context preview does not produce dialogue or an end-to-end NPC turn.

Maximum-payload performance, game CPU/RAM/frame-time contention and dialogue realism remain empirical gates. The reviewer did not validate live models, game integration or the separately reported small-fixture timing measurements. No paid calls, game actions, commits or pushes were performed by the reviewer.
