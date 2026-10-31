# Issue-ready implementation backlog

These are local issue drafts, not published GitHub issues. Dependencies identify design/API prerequisites; use fixtures/fakes to work independently. All owners/reviewers unassigned. Each module issue inherits its linked TRD's failure modes, acceptance and handoff requirements.

## EPIC-00 - Believable game-independent NPC interaction

Goal: deliver the [general TRD](TRD.md) core through replay/console using an API provider, with conditional generation, scoped knowledge, persistent relationships and bounded validation. Done when G1-G4 in [team workflow](TEAM_WORKFLOW.md) pass and results are recorded. Skyrim, full CV and local inference are optional follow-up milestones.

## I00 - Shared contracts and fixtures

- Priority: P0. Dependencies: team review of [contracts](CONTRACTS.md).
- Scope: Pydantic/JSON schemas, two synthetic worlds, three NPCs, interface fakes, schema compatibility and example validation.
- Done: all boundary fixtures validate; malformed/unknown/stale input semantics documented; consumers can import stable interfaces without model/game dependencies.
- Excludes: provider calls, real game adapter and RAG indexing.

## I01 - Input normalization and replay adapter (M01)

- Priority: P0. Depends on I00. [TRD](modules/M01-input.md).
- Deliver replay reader, canonical event normalization and capability manifest.
- Done: partial/duplicate/stale inputs and same-name actor identities pass; two world packs use one core.

## I02 - Persona, directed relationships and memory (M02)

- Priority: P0. Depends on I00. [TRD](modules/M02-state.md).
- Deliver SQLite migrations/repository, event reducers, outbox and save scope.
- Done: restart, event deduplication, relationship bounds, bounded delivered history, explicit branch/reset, isolation and atomic compare-and-stage races pass. No automated summarizer/checkpoint reconstruction required.

## I03 - Behavior policy and authored responses (M03)

- Priority: P0. Depends on I00; agrees situation contract with I04. [TRD](modules/M03-behavior.md).
- Deliver configurable decision table, persona template catalog and plan interface.
- Done: stranger/friend/busy/hostile/silence plus mixed/indirect factual input produce labelled routes; `none|required|uncertain` knowledge need is explicit. No calls on authored/silent paths; repeated greetings cannot farm relationship gains.

## I04 - Two-stage context builder (M04)

- Priority: P0. Depends on I00; fake I01/I02/I05 initially. [TRD](modules/M04-context.md).
- Deliver situation construction, provenance/dependency records, eligibility resolver and budgeted assembly.
- Done: perception conflicts, inaccessible knowledge, stale CV and oversized history preserve mandatory constraints.

## I05 - General RAG folder lifecycle and connector (M05)

- Priority: P0. Depends on I00 only. [TRD](modules/M05-rag.md).
- Deliver managed Chroma setup, embedding manifest, parsers/chunker, validation/ingestion CLI and retrieval interface.
- Done: fresh setup, offline model checks, hash-based edit/delete/reuse, serialized staged rebuild/recovery, bounded indexed eligibility and nearest-secret tests pass; retrieval/post-packing relevance and 10x scale measured. Live hot reindex is deferred.
- Add chosen CPU embedding/Chroma/parser dependencies to the single requirements.txt and provide Windows bootstrap; no manual Chroma server setup.

## I06 - Compact prompt builder and API provider (M06)

- Priority: P0. Depends on I00; fake context/plan initially. [TRD](modules/M06-generation.md).
- Deliver provider-neutral generation interface, configured API adapter, usage/deadline controls and prompt templates.
- Done: provider failures/cancellation/schema/token cases pass; optional live smoke test records model/version and usage without committing credentials.
- Excludes: choosing a permanent model, fine-tuning and mandatory local GPU.

## I07 - Validation and one bounded repair (M07)

- Priority: P0. Depends on I00; I06 fake sufficient. [TRD](modules/M07-validation.md).
- Deliver structural checks, risk flags, repair requests and validated fallback catalog.
- Done: rejection matrix passes, total model call cap is two, no invalid candidate delivered, semantic limitations documented.

## I08 - Output delivery and pacing cues (M08)

- Priority: P1, text output stub P0. Depends on I00 and I02 outbox contract. [TRD](modules/M08-output.md).
- Deliver capability-aware text/silence/cue adapter, ack/cancel protocol and cue TTL.
- Done: duplicate/interrupted/disconnected/expired/reordered/partial ack cases pass; unknown delivery is not blindly retried after restart. Unsupported cues degrade; pending output is never remembered as delivered. Declare legacy receiver limitations.

## I09 - Runtime vertical slice and replay console (M09)

- Priority: P0. Depends on I00 first; fake all other modules. [TRD](modules/M09-runtime-evaluation.md).
- Deliver request lifecycle, ingress deadline/earlier model cutoff, global call/worker/admission limits, parameterized portrait console, local trace and health.
- Done: fake turn then real API slice, same-NPC cross-session and compare-and-stage races, overload/cancellation/restart tests; debug data isolated; test parameters use an explicit test branch. Avatar rendering is optional I16.

## I10 - Evaluation suite and baseline report

- Priority: P0, fixture writing can start after I00; measurements after I09. [Plan](EVALUATION.md).
- Deliver held-out prompts, labelled retrieval corpus, scoring rubric, failure-injection harness and route-labelled latency/cost report.
- Done: three NPCs/two packs, hard invariants, clarified text/voice targets, routing/packing errors, ablations and game frame-time/RSS contention reported with raw counts/unmet gates. No paid calls in default CI.

## I11 - Mantella installed protocol capture

- Priority: P1, input feasibility study. Depends on I01 contract. [Audit](research/MANTELLA.md).
- Deliver verified running version, source hashes, sanitized initialize/start/player/continue/end capture, route/port verification and field freshness/gap report.
- Done: one real conversation replays into canonical input; no game configuration changed silently. Source inspection alone is not completion.

## I12 - Optional Skyrim compatibility facade

- Priority: P2. Depends on I11, I08/I09 and explicit supported output capabilities.
- Deliver isolated-profile protocol bridge and text/audio lifecycle proof of concept, with documented reversible setup.
- Done: one NPC interaction plus interruption/end works in a disposable save; limitations recorded. Skip full integration if it blocks core evaluation.

## I13 - Optional speech I/O

- Priority: P2. Depends on I01/I08. Deliver STT confidence/audio disposal and validated-text TTS/cancellation.
- Done: recorded utterance accuracy spot checks, playable samples, audio failure -> text, and voice latency report. No new microphone/voice recording by default in core tests.

## I14 - Optional CV descriptor pipeline (M10)

- Priority: P2 implementation, P0 mock contract in I00. [TRD](modules/M10-vision.md).
- Deliver event-triggered descriptor inference, viewpoint/freshness checks and labelled scene evaluation.
- Done: uncertain/occluded/non-NPC-visible observations cannot leak knowledge; core works with CV disabled.

## I15 - Local-model feasibility on constrained hardware

- Priority: future experiment. Depends on I10 baseline. User preference: 4 GB VRAM machine alongside game, not a minimum requirement.
- Deliver provider adapter, candidate/quantization comparison, peak VRAM/RAM, game frame-time impact, quality and latency results with actual game load.
- Done: publish viable settings or measured infeasibility; retain API provider throughout. No guarantee that a game and chosen model fit together in 4 GB.

## I16 - Optional compatible browser avatar prototype

- Priority: optional, after G2. Depends on working I09 console and a permitted ready-to-use GLB/VRM asset. [Feasibility](research/BROWSER_DEMO.md).
- Timebox: one developer day, one avatar/view, existing animation only. No Skyrim extraction, rig conversion or general lip-sync work.
- Done: use existing output cues, render-off fallback works, hidden-tab pause/resource cleanup and renderer-on/off measurement. If assets require substantial work, keep portrait/text. This does not block core acceptance.
