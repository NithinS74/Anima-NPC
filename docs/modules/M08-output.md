# M08 - Output connector and latency-aware pacing

Status: proposed | Requirement: SYS-10 | Owner/reviewer: unassigned

## Responsibility and interfaces

`deliver(validated_response, capabilities) -> DeliveryReceipt`; `cancel(turn_id)`; `ack(DeliveryAck)`. Deliver text, deliberate silence and supported cue/action intents. Optional TTS consumes only validated speech; optional STT lives before M01. No game-specific paths, voice model assumptions or animation IDs belong in the core.

## Lifecycle

Adapter declares capabilities (`text`, `audio`, `look_at`, `resume_task`, `guarded_stance`, etc.) and permitted parameter schemas. Core emits abstract cues; adapter maps only tested capabilities. Unsupported cues degrade to text/no-op and are logged. Combat, travel, inventory and quest mutations remain outside MVP action permissions.

Immediate engagement cues can run before dialogue generation only from the deterministic plan. Generated speech remains buffered until validation. Use TTL, turn/state revision and idempotency IDs for all outputs. At interruption cancel pending generation/TTS and discard obsolete files/results. Per-NPC ordering prevents a late reply from speaking over a newer turn.

Follow the [delivery lifecycle](../CONTRACTS.md#delivery-lifecycle). Expiry blocks new starts, not legitimate late reports of playback that started in time. M02 reconciles sequenced/idempotent acknowledgements and heard portions. Lack of ack is unknown, not success. Never blindly retry ambiguous speech on an adapter lacking idempotent delivery support. Report weaker guarantees when receiver-side epoch/expiry/cancel enforcement is unavailable; core cannot prevent all late playback in a legacy client. Silence completes deliberately, separately from timeout failure.

## Speech and pacing

Text-first is sufficient for initial API evaluation. STT needs confidence and audio disposal; TTS needs selected voice, cancellation, audio format and cleanup. Do not ask LLMs to emit audio paths. A glance or continuing a task can occupy a short wait, but cannot justify exceeding the measured deadline. No repeating "let me think" loop. Full animation design and Skyrim lip-sync implementation are separate adapter work.

## Acceptance / handoff

Fake adapter demonstrates speech, deliberate silence, cue-only result, unsupported cue, duplicate output, disconnect, cancellation and partial playback ack. TTS failure returns text; no rejected text is synthesized. Live Skyrim delivery remains explicitly unverified until tested in a disposable save/profile.
