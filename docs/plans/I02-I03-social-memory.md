# Persistent social reactions and conversation context

User requested automatic, persistent relationship changes, context-sensitive reactions to insults, and an inspectable map of the NPC's response decision. Continue the authorized separate lab media/UI work; do not leave its copied assets or temporary model unverified. The new state/policy logic belongs in reusable core modules, with only UI wiring in the lab.

## Reviewed implementation approach (self-review before coding)

- Add a pure, versioned social appraisal/reducer: stimulus (neutral, directed insult, threat, apology, gratitude, rough banter), relationship-sensitive willingness, tone and permitted profanity. Distinguish quoted/reported insults and incidental profanity from abuse directed at the NPC. English prototype rules are bounded/explicit, not a semantic classifier guarantee. No extra model call and no hidden chain-of-thought requirement.
- Add authored persona patience/assertiveness/swearing boundaries. A patient host can set a boundary; an assertive irritated guard can answer sharply; familiar consensual rough banter differs from a stranger's abuse. Strangers generally get shorter replies, while service duty may justify engagement. Sustained abuse can end interaction. Speech never triggers mechanical attacks. Player claims do not set trust or prove world events.
- Store directed relationships, mood, deduplicated input events and acknowledged display history in SQLite keyed by game/world/save/NPC/player. Short transactions and expected revisions, no transaction across inference. Clamp scores, cap conversational positive gains with a cooldown, never grant instant trust for praise/apology. Preserve relationship state on restart. Bounded recent acknowledged history is supplied as untrusted dialogue, not world truth.
- Core snapshot/situation gain typed recent-dialogue and social-appraisal fields. Prompt packing keeps identity/current input, then includes recent whole exchanges only while the configured byte budget permits; omitted history is reported. Do not silently truncate the current message or let old model text become trusted instructions.
- Lab startup loads saved state; each submitted utterance updates the state once, feeds its new values into context and shows before/after reasons. Sliders become explicit revision-checked test overrides instead of overwriting automatic changes on every turn. Existing worlds/NPCs remain isolated. Reset clears the visible log/cancels work; it does not erase durable relationships. Browser acknowledges displayed responses before they become remembered dialogue. No claim of production game delivery/outbox semantics.
- Repeated request IDs do not reapply social changes or make a second successful generation once a preview is stored. Interrupted inputs remain recorded as said; rejected/cancelled NPC text never becomes delivered memory. Store failures suppress unstored replies. Database size has a stop-admission bound; recent history selection uses indexed bounded queries. This is an initial social-state slice, not all M02 tables/production delivery.

## Acceptance tests

Paired neutral/direct insult/incidental profanity/quoted abuse/banter/apology/threat cases; role/temperament/willingness differences; repeated abuse escalation and score bounds. SQLite restart, world/player/NPC isolation, event deduplication, revision conflicts, bounded history, undisplayed/cancelled exclusion and no praise farming. Prompt history budget/injection tests. Offline lab HTTP tests for state updates, explicit overrides and display acknowledgement. Full regression, UI reload/state-change checks and small live comparison if configured. Finish and verify media work, then push only source/docs/tests/public configuration to the existing branch and main as authorized.

## Results

Implemented and self-reviewed; see [verification and limitations](../reviews/2026-10-31-social-state-character-stage.md).

Final scope includes the subsequent user-requested persistent social-state slice and actual local Skyrim conversion. Earlier single-turn/optional-conversion observations above are planning history, superseded by the [current lab guide](../NPC_LAB.md). Verification: 254 offline tests, four actual rendered models, persistent browser escalation/reload, and local voice playback. Live Gemini memory calls fell back; successful live recall is not claimed.
