# Shared contracts v0.1

Status: broader pipeline interface proposal, with executable context contracts in [contracts/context.py](../src/npc/contracts/context.py) and a preview dialogue subset in [contracts/dialogue.py](../src/npc/contracts/dialogue.py). Validated examples are the [scenarios](../fixtures/scenarios/); behavior is documented in [context builder](CONTEXT_BUILDER.md) and [generation/validation](GENERATION_VALIDATION.md). I00 is only partially complete; unrelated pipeline objects below remain proposals.

## Common conventions

All boundary objects carry `schema_version: "0.1"` and correlation identifiers. IDs are opaque strings; never use NPC names as identity. Scope is `{game_id, world_id, save_branch_id}`. Simulation time and UTC capture time are separate. Latency/deadlines use a monotonic server clock. Do not transfer monotonic timestamps across processes; transfer remaining timeout/UTC expiry and translate at ingress.

Unknown values use null/absence explicitly; patch omission means unchanged in future patch transport. The initial context schema accepts exactly `0.1` and rejects unknown keys; no unvalidated extension values enter the situation. Future minor additions/extensions require explicit negotiation/tests, not automatic acceptance. Strict model-response bodies now exist as `ResponseBody`; they deliberately contain only mode/text/cue/evidence IDs, with correlation/state held by the trusted runner rather than authored by the model.

Preview-specific types are `InteractionPlan` (prototype policy subset), `PromptPackage` (messages, conservative input byte estimate and output-token cap), `ProviderReply` (raw text/finish reason/model/usage), `CurrentState`, `ValidationResult` and developer-only `TurnPreview`. `TurnPreview` includes diagnostics and is not the proposed public/delivered `TurnResult`. It has no persistence, outbox or acknowledgement semantics. Preview end/silence bodies require empty text. The inventory below describes the broader target, including fields not implemented by these types yet.

The [internal RAG component](RAG_INTEGRATION.md), with local default and optional HTTP transport, adds executable `Evidence` and `KnowledgeContext` in `contracts/knowledge.py`. `PromptPackage.evidence` holds only whole passages actually sent; response validation accepts only their IDs plus perceived observation IDs. `TurnPreview.knowledge`, `evidence_used` and `evidence_omitted` are inspection fields. The bridge uses trusted file-level bindings rather than the full proposed `RetrievalRequest`/`EvidenceSet` authorization and revision schema below.

## Boundary object inventory

| Object | Required content | Producer -> consumer |
|---|---|---|
| AdapterCapabilities | adapter/version, supported input facts and output cues, ack/cancel support | M01/M08 -> M09 |
| TurnInput | scope, request/session/player/NPC IDs, sequence, text/source/confidence, capture time, facts, expected_dialogue_revision | M01 -> M09/M04 |
| WorldEvent | event ID/type, scope, actors, time, source, witnesses, payload, confidence | M01 -> M02 |
| ObservedFact | fact ID/path/value, source, captured/simulation time, TTL, confidence, perceivers | M01/M10 -> M04 |
| StateSnapshot | storage revision, dialogue-relevant revision, turn epoch, NPC persona/runtime, directed relationship, grants, delivered memory | M02 -> M04/M03 |
| Situation | perceived facts, uncertain claims, goals/availability, social situation, dependencies | M04 -> M03 |
| InteractionPlan | route/intent/affect, disclosure, length, retrieval need, cues, reasons, policy version | M03 -> M04/M06/M07/M08 |
| RetrievalRequest | query, scope/time, trusted bounded eligibility policy/partitions, index revision, top_k/token limit/timeout | M04/M09 -> M05 |
| EvidenceSet | index/encoder versions, hits with text, locator, IDs, scope/access, validity, distances | M05 -> M04 |
| ContextBundle | persona, perception, relationship, plan, history, eligible evidence, uncertainties, budget, revision | M04 -> M06/M07 |
| PromptPackage | provider-neutral messages, schema, input estimate, output cap, template version/hash | M06 -> provider |
| CandidateResponse | strict response body, provider/model, usage, latency, finish reason | M06 -> M07 |
| ValidationResult | accepted flag, violations, severity, repair eligibility, validated response | M07 -> M09 |
| TurnResult | scope/IDs, mode/text/cue, source route, expiry, delivery ID; no private debug facts | M09 -> M08/client |
| DeliveryAck | scope/turn/delivery IDs, ack ID/sequence, status, start/observation times, reliable heard portion if available | M08 -> M02/M09 |

## Example input

```json
{
  "schema_version": "0.1",
  "scope": {"game_id": "demo", "world_id": "village", "save_branch_id": "save-a"},
  "request_id": "r-17",
  "session_id": "s-1",
  "npc_id": "smith-instance-4",
  "player_id": "player-1",
  "sequence": 17,
  "expected_dialogue_revision": 23,
  "captured_at": "2026-10-31T04:30:00Z",
  "simulation_time_s": 68400,
  "player_input": {"text": "Hello again. Got a moment?", "source": "text", "confidence": 1.0},
  "facts": [
    {"id": "f-shop", "path": "shop.open", "value": false, "source": "demo-adapter", "source_kind": "telemetry", "subject_id": "smith-instance-4", "captured_at": "2026-10-31T04:30:00Z", "simulation_time_s": 68400, "ttl_ms": 5000, "confidence": 1.0, "perceivers": ["smith-instance-4"]}
  ]
}
```

## Example state, situation and plan

```json
{
  "storage_revision": 23,
  "dialogue_revision": 23,
  "turn_epoch": 17,
  "persona": {"name": "Mira", "role": "blacksmith", "speech_style": "dry, direct", "goals": ["close shop and go home"]},
  "relationship": {"favourability": -10, "trust": -25, "familiarity": 40, "fear": 0, "irritation": 35},
  "situation": {"availability": "closing", "dependencies": [{"fact_id": "f-shop", "derived_state": "unavailable_for_trade", "affected_decisions": ["engagement", "length"], "confidence": 1.0, "reason": "shop_closed"}]},
  "plan": {"route": "authored", "intent": "refuse_briefly", "affect": "impatient", "engagement": "decline", "disclosure_policy": "public_only", "knowledge_need": "none", "max_words": 12, "max_sentences": 1, "allowed_cues": ["resume_task"], "template_id": "smith.closing.repeat_greeting.2", "reason_codes": ["shop_closed", "busy", "repeat_greeting"], "policy_version": "0.1"}
}
```

These are illustrative subobjects; production boundary wrappers include their own version/scope/IDs. Route `authored` skips retrieval and generation. It still validates and stages delivery.

```json
{
  "schema_version": "0.1",
  "scope": {"game_id": "demo", "world_id": "village", "save_branch_id": "save-a"},
  "request_id": "r-17",
  "turn_id": "t-17",
  "delivery_id": "d-17",
  "npc_id": "smith-instance-4",
  "state_revision": 24,
  "dialogue_revision": 23,
  "turn_epoch": 17,
  "delivery_status": "pending",
  "mode": "speech",
  "text": "The forge is cold. Try me tomorrow.",
  "cue": "resume_task",
  "source_route": "authored",
  "expires_at": "2026-10-31T04:30:03Z"
}
```

`state_revision` is the storage revision after staging. Storage writes such as logging need not invalidate dialogue. `dialogue_revision` changes only for relevant facts/relationships/permissions; `turn_epoch` changes on preemption/cancellation. Staging atomically checks both plus active ownership/expiry while inserting the outbox. A duplicate r-17 returns the recorded result with its current delivery status, never new dispatch permission. These are proposed fixtures, not evidence the mechanisms exist.

## Generated branch contract

For "Where can I buy iron?" while the shop is open, policy may choose `generate`, `intent: answer_trade_question`, `knowledge_need: required`. Ambiguous factual content may use `uncertain` and one bounded retrieval; social-only input uses `none`. The caller resolves a trusted eligibility policy before constructing:

```json
{
  "schema_version": "0.1",
  "request_id": "r-18",
  "scope": {"game_id": "demo", "world_id": "village", "save_branch_id": "save-a"},
  "query": "local iron suppliers",
  "eligibility": {"policy_id": "npc-trade-v1", "partitions": ["village-public", "smith-trade"]},
  "eligibility_hash": "grants-rev-9",
  "simulation_time_s": 72000,
  "index_revision": "kb-7",
  "top_k": 3,
  "max_tokens": 600,
  "timeout_ms": 150
}
```

Evidence hit example: `{chunk_id: "trade-2", document_id: "village-public-trade", text: "Hale sells iron at the east gate.", locator: "trade.md#supplies", valid_from_s: 0, valid_until_s: null, index_revision: "kb-7"}` plus source/scope/encoder metadata. Named fields here are explanatory notation, not JSON fixtures. An excluded secret cannot be submitted merely because its similarity score is high.

Eligibility is server-generated, never taken from player text or arbitrary client filters. Begin with indexed world/time fields plus access partitions derived from all required grants (public is itself a world-specific grant). M04 authorizes partitions; M05 compiles a supported filter vocabulary and rechecks results. Cap at 64 grants/16 authorized partitions and one filtered vector query per turn. Explicit document allowlists are for small fixtures only, capped at 256 IDs. Unsupported/over-limit requests fail closed with `eligibility_limit`/`unsupported_filter`. No full-corpus ID enumeration per turn; measure larger-corpus partition tuning before raising limits.

Strict candidate body:

```json
{"mode": "speech", "text": "Hale sells iron by the east gate. Tell him Mira sent you.", "cue": null, "evidence_ids": ["trade-2"]}
```

The example's referral sentence is permitted only if the plan authorizes that social gesture; evidence attribution alone cannot justify it. Silence candidate: `{"mode":"silence","text":"","cue":null,"evidence_ids":[]}` only when the plan permits silence. End interaction is `mode: "end"` with optional validated farewell under the plan's limits.

## Error and acknowledgement semantics

Typed errors: `invalid_input`, `unsupported_version`, `state_conflict`, `resync_required`, `retrieval_unavailable`, `provider_timeout`, `provider_rate_limited`, `invalid_candidate`, `cancelled`, `delivery_failed`, `busy`. Client errors use an HTTP status plus `{error:{code,message,retryable},request_id}`. Runtime dependency failures generally produce a valid in-character fallback TurnResult with developer-only error details.

Ack statuses: `accepted`, `started`, `completed`, `interrupted`, `failed`; core additionally records `pending`, `expired`, `cancelled` and `unknown`. State mutation and ack/event deduplication are atomic. Clients without reliable acknowledgements cannot claim authoritative heard/action memory.

## Delivery lifecycle

- Arbitration is by scope/NPC across sessions. An owning session may preempt its old pending turn; another session gets `busy` initially. Combat/world-unload cancellation has priority.
- Ownership lasts through pending/accepted/started delivery, not merely until response-ready. Release on completed/interrupted/failed delivery or confirmed cancellation/handoff. For unknown delivery, require receiver reconciliation/observed idle or an explicit test-session reset before another session speaks; a timeout alone does not prove playback stopped. Receiver-incapable adapters document any conservative reset as best effort. Cancellation of already-started speech needs stop confirmation before handoff; a pending epoch can be invalidated immediately. Test another session arriving during playback and after a lost ack.
- `pending -> accepted -> started -> completed|interrupted|failed`. `pending|accepted -> expired|cancelled|failed` prevents new starts. Missing reliable evidence becomes `unknown`, never success. Silence is explicitly completed without speech.
- Before dispatch and receiver playback, check ID, active epoch, relevant revision and start-before expiry. Capable receivers enforce these checks/idempotency. Legacy clients without them expose best-effort guarantees; core checks alone cannot close receiver races.
- `expires_at` is latest permitted start, not mandatory finish. Playback may finish later. A late ack describes already-started output, never fresh start permission. After cancellation a reliable report of previously heard speech is retained as fact separately from dispatch eligibility.
- Acks include `ack_id`, increasing `ack_sequence` per delivery, `observed_at`, optional `started_at`, and optional `heard_text`/audio offsets plus an adapter-declared reliability flag. Deduplicate by scope/delivery/ack ID; never regress terminal status on reordered acks. A terminal ack may arrive without its start ack if it includes reliable start evidence; otherwise delivery stays unknown pending reconciliation. Retain conflicting terminal reports diagnostically rather than guessing full success.
- Interruption records only a reliably reported heard portion. Offsets alone do not imply word alignment/full text. Console ack means displayed, not that a human read it.
- Duplicate request lookup returns result plus lifecycle status. Only the outbox dispatcher owns pending dispatch. Completed, expired, cancelled or unknown output is not blindly redispatched, including after restart. Retry requires receiver idempotency/query support; otherwise preserve ambiguous delivery as unknown.
- MVP cues do not change combat/quests/inventory. Any later mechanical action requires a confirmed outcome event; acceptance is not execution success.

## Ownership rules

The independent Skyrim connector's adapter-specific wire protocol is implemented in `adapters/skyrim/protocol.py` and documented in [Skyrim connections](SKYRIM_CONNECTOR.md). Its full game envelope and screenshot references sit beside the executable `ContextScenario` subset; they do not extend `TurnInput` implicitly. Context-ready prewarms the future pipeline, player-turn supplies input, and correlated results return via a separate endpoint. Native playback acknowledgements are best effort and do not implement the broader production outbox/memory guarantees above.

M02 owns persistent mutations; M03 owns social decisions; M04 owns NPC knowledge eligibility and context selection; M05 enforces retrieval filters without NPC-specific business rules; M06 owns serialization/provider details; M07 owns acceptance; M08 owns transport/cues; M09 owns deadline, idempotency and scheduling. M10 supplies uncertain observations only.

## Implemented social-state and lab media slice

See [social state](SOCIAL_STATE.md) for typed `DialogueMemory`/`SocialAppraisal`, persona temperament, revision-checked SQLite relationships and bounded acknowledged recent history. This is partial state implementation, not the full delivery/outbox proposal. Reusable policy/storage stay in `src/npc/behavior/` and `src/npc/state/`; standalone HTTP, static models, voice and offline asset conversion stay in `tools/npc_lab/`. Public recipes live in `configs/npc_lab/`; all converted game assets/tools/weights remain ignored. Unit/integration cases live under the corresponding `tests/` owners.

### Dialogue-reference provenance and prompt citations

`SourceBinding.source_format` selects ordinary `reference` or the configured `dialogue_export` reader. `Evidence.source_kind` and `record_ids` preserve dialogue provenance. `KnowledgeContext.source_kind` remains explicit even for empty results; dialogue-export prompts retain player history but omit previous generated NPC replies as unverified knowledge. No saved history is deleted. `PromptPackage.evidence_aliases` maps short model labels only to packed original evidence IDs, avoiding observation-ID collisions. Response validation resolves labels back to original source IDs; unknown labels/omitted sources fail. Record IDs are inspection-only; dialogue entries sent to the model explicitly mark speaker unknown and conditions unresolved.
