# Social appraisal and persistent conversation state

This implemented slice maps observable inputs into a bounded response decision without a classifier or critic LLM call. It is an explicit English prototype, not a complete psychological model.

## Decision path

1. Validate input, scope and expected state revision; deduplicate request ID.
2. Classify observable stimulus using bounded English rules: neutral, incidental profanity, directed insult, threat, apology, gratitude or familiar rough banter. Quoted/reported abuse is excluded where recognized. Confidence below 0.6 prevents social penalties/gains.
3. Apply a versioned relationship reducer once; persist the heard input, score delta and mood in SQLite.
4. Build canonical context from persona, current state, relationship, perception and recent displayed exchanges. Compute willingness, tone and whether swearing is allowed.
5. Policy prioritizes combat/uncertain speech/visible threat, then withdrawal, authored boundaries and other cheap routes. Generate only when necessary. Validate output under existing deadlines and repair limits.
6. Durably stage the lab preview before exposing it. Only browser-acknowledged displayed replies become conversation memory. Cancellation preserves already-heard input but excludes undisplayed NPC replies.

The trace exposes these decisions and reasons, not an LLM chain of thought. No speech route triggers a mechanical attack.

## Current rule calibration

Persona adds `patience`, `assertiveness` (0..1) and `swearing` (`never` or `when_provoked`). Directed insults reduce favourability by 7 and trust by 4; irritation increases by `round(12 + 12 * (1 - patience))`. Threats reduce favourability/trust by 12 and add 20 fear/15 irritation. Apologies can remove 8 irritation but do not restore trust. Gratitude can add 1 favourability and remove 2 irritation. Conversational familiarity gains at most 1 per 60-second positive-gain window; praise/apology cannot farm trust. Scores are clamped to their contract ranges.

Rough banter requires familiarity >=60, trust >=40, favourability >=50 and an explicit joking marker. Profanity alone does not count as directed abuse. Strongly provoked assertive personas may swear if their authored boundary permits it. Patient hosts and formal officials use different authored boundaries. Repeated abuse can end the exchange at irritation >=80; sustained irritation >=85 can also cause disengagement. Threatened low-assertiveness/fearful NPCs can withdraw. Strangers without a service obligation generally get a brief response (18 words/one sentence), while service duty can justify engagement. These thresholds need labelled quality evaluation, including false positives and language coverage.

## Storage and memory contract

`src/npc/state/social_store.py` is a reusable initial SQLite store, not a full M02 implementation. Key: game, world, save branch, NPC and player. It stores relationship/mood/revision, a deduplicated input audit and staged/displayed turns. Short revision-checked transactions never span inference. Duplicate completed requests reuse the stored result without reapplying social effects. Changed input under the same ID conflicts. State updates and delivered-memory semantics are distinct.

Typed `DialogueMemory` and `SocialAppraisal` fields are carried through snapshot/situation contracts. At most eight acknowledged exchanges are retrieved via an indexed query; prompt packing retains newest contiguous whole exchanges within the byte budget. Player claims and previous model text remain untrusted dialogue, not world facts or new instructions. `history_used` and `history_omitted` report actual packing.

The lab defaults to `data/npc_lab/state.sqlite3`; `--state-db` isolates experiments. Explicit slider edits require the current revision. A 250 MB database stop-admission threshold prevents silent unbounded disk growth, but archival/retention maintenance is still future work. Read/write failures fail closed with typed errors. This is console display acknowledgement, not reliable game delivery, an outbox, crash-proof exactly-once generation, long-term semantic memory, save synchronization or verified semantic entailment.

See the [review](reviews/2026-10-31-social-state-character-stage.md) and [plan](plans/I02-I03-social-memory.md) for tests and remaining gates.
