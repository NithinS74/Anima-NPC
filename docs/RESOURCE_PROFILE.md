# Initial edge resource profile

These are explicit, configurable starting limits for implementation, not measured hardware guarantees. Optimize for a single player interacting with one NPC alongside a game. A modular monolith and bounded workers are sufficient; no orchestration framework or distributed scheduler is needed.

| Resource | Initial limit / behavior | Reason |
|---|---|---|
| Model calls | 0 for authored/silent, 1 ordinary generation, max 2 including repair | Bound cost/latency; no separate planner/critic |
| Global generation concurrency | 1 active local provider request | Prevent session/cancellation storms |
| Pending turn admission | 2 total, at most 1 per NPC | Bounded wait; waiting counts against ingress deadline |
| Active NPC ownership | One turn per world/save/NPC across sessions | Prevent overlapping speech and state races |
| Active retained sessions | 16, idle eviction after 30 minutes | Bound live objects; persisted relationships remain |
| Priority events | Cancellation/combat processed outside generation queue | Interruptions cannot wait behind inference |
| Embeddings/vector queries | CPU, 1 worker, 1 in-flight query; explicit native thread caps initially 1 where supported | API-first does not eliminate local CPU contention |
| Ingestion | Explicit offline command, 1 parser/embedding worker, batch <=32 chunks | No surprise background compute during play |
| KB guardrails | <=1,000 files, 20 MB/file, 200 PDF pages/file, <=50,000 chunks, 1 GB extracted text total | Fail with actionable limit diagnostics; not a universal capacity claim |
| Index storage | At most active + one staging/last-good generation; 2 GB total prototype budget | Before new staging discard only the previous backup, never active data; abort if insufficient disk |
| Grant/filter expansion | <=64 grants, <=16 authorized access partitions, explicit fixture allowlist <=256 IDs, 1 filtered query | Avoid per-turn full-corpus/fanout work |
| Prompt | Target <=2,048 input tokens, initial output <=160 including JSON | Bound inference; evaluate detail/truncation separately |
| History in memory | Last 8 delivered turns/NPC, <=8 KB serialized history/session before token packing | Bound context-building work; no initial summarizer |
| Trace retention | Redacted ring <=1,000 turns or 50 MB, whichever first | Avoid unbounded diagnostic growth |
| Persisted event/turn growth | Retain IDs needed for dedup while branch active; 100 MB soft warning, 250 MB stop-admission threshold for prototype state DB | No blind deletion of authoritative events; explicit archive/reset needed |
| Query/response caches | None initially beyond loaded persona/model metadata | Add only with measured hit rate and invalidation design |
| CV/demo rendering | Disabled by default in contention benchmark; explicitly enabled in separate runs | Avoid attributing renderer GPU cost to core |

Choose replacement pending input rather than unlimited backlog for the owning NPC; acknowledge preemption. Preserve authoritative game events; only superseded telemetry snapshots may be coalesced. If admitted work cannot fit its remaining deadline, reject it as busy instead of starting doomed generation.

Cancellation releases dispatch eligibility immediately, but the global local-request slot remains accounted for until that request finishes or hits its bounded transport timeout. Remote providers may continue work/billing even after local cancellation; record this uncertainty. Repeated timeouts open a short circuit breaker (initially three consecutive failures, 10-second cooldown) that serves authored fallback rather than issuing more requests. This is a small counter/timer, not a new service.

Use async network I/O and bounded worker admission for blocking DB/embedding operations. Merely cancelling an await does not stop a native computation. Drop late results, cap queued tasks and configure finite transport/SQLite busy timeouts. Start DB busy timeout at 50 ms within remaining turn budget, with no unbounded retry loop. Under persistent storage failure return a typed unavailable result; do not pretend durable interaction succeeded.

API keys/corpus contents remain backend-only. Retention/export/reset commands must not silently remove active event IDs or resurrect old delivery IDs. On state storage threshold, stop admitting state-changing turns and request explicit maintenance. Durable relationships are never arbitrarily LRU-evicted.

## What to measure before changing limits

Run game-only, game+idle backend, game+authored turns, game+generated turns, and game+retrieval. Then separately enable ingestion (a stress experiment), CV or 3D rendering. Record process RSS, CPU utilization, thread count, peak GPU/VRAM where applicable, provider work outstanding, queue depth, disk footprint, game average frame time and p95/p99 frame time.

Proposed initial acceptance guardrails: core+CPU retrieval RSS <=512 MB and <=5% regression in game p95 frame time compared with matched game-only runs. These are hypotheses to validate on declared hardware, not portable performance promises. If the embedding backend misses them, tune threads/model/operation scheduling before introducing services. A later local LLM has its own separately measured RAM/VRAM budget; 4 GB VRAM alongside the game remains a preference.
