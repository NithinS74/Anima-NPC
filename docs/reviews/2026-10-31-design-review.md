# Design review and implementation readiness

31 October 2026 | Reviewed baseline v0.1; corrected planning baseline v0.2

## Verdict

**Go for executable contracts and the fake/API vertical slice; no architecture rewrite is needed.** Independent read-only review and a separate forward test of the reusable reviewer skill both found the modular monolith, deterministic policy, conditional RAG and bounded generation justified. They independently identified the same lifecycle/resource risks. A final independent reread confirmed the high-severity planning findings were addressed; its remaining ownership-lifetime and revision-naming clarifications are now included in contracts. The table records requirements fixed in v0.2, not runtime features already proven by tests.

There is no defensible promise of universally optimal or technical-debt-free code before implementation and profiling. Our standard is justified complexity, explicit invariants, small replaceable boundaries, measured contention and tracked tradeoffs. A contract review can authorize the next implementation milestone; it cannot certify realism, scalability or latency.

## Findings and resolutions

| Severity | Baseline gap / failure scenario | Corrected requirement | Verification required in implementation |
|---|---|---|---|
| High | Combat/grant change after validation but before staging permits stale dispatch | Atomic relevant-revision/epoch/cancellation compare-and-stage; dispatch/receiver guard | Inject event precisely between validation and commit; suppress stale result |
| High | Two sessions target same NPC and produce overlapping replies | Scope/NPC ownership across sessions; another session gets busy initially | Concurrent same-NPC and separate-NPC cases |
| High | Duplicate lookup redispatches expired/completed output; late start/completion/partial acks corrupt memory | Separate result lookup from dispatch permission; explicit lifecycle, sequenced ack reconciliation and unknown state | Retry after expiry/restart, reordered acks, reliable partial playback |
| High | Provider consumes entire 3-second budget, leaving no fallback/commit time | Earlier model cutoff, initially 2,450 ms; 550 ms reserve; response-ready vs delivery distinction | Never-returning provider, blocking retrieval and DB-lock cases |
| High | Per-session limits permit unbounded total work; cancelled provider/CPU tasks still run | Concrete global admission/worker/retention limits and outstanding-request accounting | Cancellation storms, many sessions, sustained traces, game frame-time/RSS measurements |
| Medium | Huge eligible-document lists/fanout defeat bounded retrieval; hot reindex consumes game resources | Indexed bounded access partitions/filters, one query, fail-closed limits; serialized offline ingest | Corpus/grant scale, nearest secret, interrupted staging/recovery |
| Medium | Greeting heuristic misses embedded/indirect factual questions | `none|required|uncertain` knowledge need; at most one conservative retrieval, no planning LLM | Mixed greeting/factual, indirect lore question, social-only false positives |
| Medium | Six seconds for complete voice playback conflicts with 40-90-word dialogue | Measure end-of-player-speech to first validated audio; full playback separately | Voice trace with timestamps and duration |
| Medium | All memory/reindex/save mechanisms bundled into first milestone | Bounded delivered history and explicit branch/reset now; summaries, vector memory, full rollback and hot reindex deferred | Core slice works without deferred mechanisms |
| Medium | Three 300-500-token hits exceed 600-token evidence budget | Preserve complete supporting excerpts/source IDs; evaluate after prompt packing | Gold evidence present before retrieval but lost in context packing |
| Low | Four requirements files complicate a small team's setup | One pinned `requirements.txt`, later RAG packages added when integrated | Clean install/check from that single file |

Receiver-side cancellation/expiry cannot be guaranteed for incapable legacy game clients. Such adapters must advertise best-effort behavior; do not claim their behavior satisfies strong receiver guarantees solely because core tests pass. No meaningful review can eliminate that external limitation in advance.

## Complexity assessment

| Mechanism | Disposition | Why |
|---|---|---|
| Typed module contracts within one process | Keep now | Independent team development without RPC/distributed overhead |
| Persona + separate trust/familiarity/favourability | Keep now | Directly required for believable social behavior |
| Authored decisions/refusals/silence | Keep now | Product behavior and zero-call latency path |
| SQLite events/dedup + transactional outbox | Keep now, small tables/functions | Prevent duplicate relationship changes and unrecorded dispatch; not a generic event-sourcing framework |
| Scoped RAG + provenance | Keep now | Prevents feeding arbitrary world secrets to every NPC |
| Runtime self-critique | Conditional repair only | Ordinary turn uses one call; broad judging is offline |
| Background summaries/vector episodic memory | Defer | Bounded history tests central continuity first |
| Concurrent hot reindex/version retention | Defer | Explicit offline ingestion is enough for corpus demos |
| Retrieval/semantic caches | Measure first | Invalidation is debt unless real reuse offsets it |
| Multi-process services, agent frameworks, general scheduler/plugin frameworks | Exclude initially | No demonstrated scale/failure need |
| Browser portrait/parameter lab | Include in existing console | Tests system behavior with low extra scope |
| Browser 3D avatar | Optional one-day experiment | Compatible assets may be easy; game extraction/retargeting is separate work |
| CV/speech/local model | Preserve interfaces; implement separately | Avoid blocking API-first behavior evaluation and crowding game compute |

## Missing proof and next gate

Build I00/I09 fake slice with one authored/silent and one generated route, then API generation and scoped retrieval. Prove lifecycle invariants with controlled races/failures. Establish three persona baselines, restart persistence, mixed-intent routing and game-only versus backend-on resource measurements. Choose model/embedding/caching optimizations from those results, not from document size or assumed consumer hardware.

The reviewer skill is [review-npc-design](../../.agents/skills/review-npc-design/SKILL.md). Its structural validator passed, and independent forward use reproduced concrete findings without receiving the expected answer. This validates useful reviewer behavior, not the eventual correctness of code.
