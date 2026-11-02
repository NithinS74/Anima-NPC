# M01 - Input connectors

Status: proposed | Requirement: SYS-01 | Owner/reviewer: unassigned

Implementation update: the [independent Skyrim connector](../SKYRIM_CONNECTOR.md) now supplies a typed game/bridge boundary, screenshot files, player-input handoff and optional existing-preview binding. It uses its own SKSE plugin, with Mantella as reference only. This is a bounded adapter implementation, not completion of every M01 capability or verified live gameplay.

## Responsibility

Normalize player text, game snapshots/events and optional visual observations. Deliver versioned, ordered inputs without importing Skyrim names into the core. Maintain adapters for replay first and Mantella as a later reference experiment. Do not infer persona, retrieve lore or generate dialogue here.

## Interface and processing

`normalize(raw, adapter_config) -> TurnInput | InputError`; `apply_event(raw) -> WorldEvent`; `capabilities() -> AdapterCapabilities`.

Validate required identity, supported schema, text/array size limits and numeric ranges. Preserve source game IDs under `extensions`; use save-scoped actor instance IDs, never display names as keys. Normalize time and units while preserving original source values. Distinguish full snapshot, patch and event; absent patch fields do not erase state. Unknown/null differs from false/zero.

Every fact carries observation time, expiry and permitted perceivers. Unknown visibility cannot become known-to-everyone. Handle duplicates via event ID, reject stale sequence updates and request resynchronization after gaps. STT confidence attaches to player text; low confidence can lead to a repeat request, never automatic hostility.

Mantella work uses the [installed-source audit](../research/MANTELLA.md). Complete read-only mapping and replay capture before replacing any endpoint. Do not assume all game data is present in existing payloads.

## Failures and observability

Return structured `invalid_input`, `unsupported_version`, `out_of_order`, `resync_required` errors with correlation IDs. Keep raw captures opt-in, redacted and local. No prompt/provider calls in adapter tests. Define initial limits: text 4,000 characters; event payload 256 KB; visual entities 100; overrides require configuration.

## Acceptance / handoff

- Replay two game-shaped fixtures through the same canonical schema.
- Duplicate, partial, stale, missing-visibility and unknown-field cases preserve state semantics.
- Same-name NPCs remain distinct; save rollback cannot reuse future observations.
- Provide mapping table, fixtures, capability manifest and missing-data report. Live capture is a separate completion criterion and must not be claimed from source inspection.
