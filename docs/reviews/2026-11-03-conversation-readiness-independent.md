# Independent conversation-readiness review

2026-11-03. Separate reviewer agent, explicitly authorized by the user. Read-only code/evidence review; no runtime edits, game actions, paid model calls or independent human-quality study performed. The deterministic classifier probes below were executed with the project interpreter. The working tree is under active development; references identify the inspected functions and line positions at review time.

## Verdict

**No-go for claiming complete human-like conversation or Anima-only gameplay readiness. Go for fixing the bounded defects below.** The core already has useful typed trust boundaries, deterministic policy, bounded inference/repair, scoped retrieval and reusable social storage. The installed Skyrim path does not yet compose all those mechanisms. Successful UI input and model/TTS calls are necessary engineering evidence, not proof of audible playback, coherent multi-turn behavior or emotional realism.

## P1 findings

### 1. Audio start acknowledgement precedes observed playback; silent failure is called interruption

`src/npc/adapters/skyrim/native/plugin.cpp:82-86,400-421,350-356`: a hashed resource ID is built from the relative path with priority0; filesystem existence, handle validity and Play() acceptance are checked, then started is emitted immediately. IsPlaying() is first checked after500ms. The inspected logs repeatedly show started -> interrupted after about0.52s, and the user reports no voice. This maps to the watchdog, not to later snapshot changes. No actual playing state is required before a timer can emit completed; a long paused interval or audio shorter than500ms can therefore bypass detection.

The exact engine load failure is **not established** by this review. File visibility to the OS does not prove engine-resource resolution through MO2. The pinned CommonLib exposes BSResourceNiBinaryStream(path).good()/lastError; it is not used. There is no explicit volume/output routing, no fresh-handle reset per file, and no resource-resolution diagnostic.

Fix now: canonicalize and preflight the engine resource path, log resource-open/lastError and handle/priority, initialize volume/routing/handle deliberately, and observe playing within a bounded startup grace. Never-started should fail, not be called interrupted; actual started then early stop is interrupted. Do not remove the watchdog and replace it with a fabricated completion timer. Unit-test never-playing, delayed start, early stop, normal finish, text-only and pause cases; live-test a known PCM sample and a newly generated random-name sample, including during an MO2 launch. Audible output remains a user/recording gate.

### 2. Skyrim has no acknowledged conversation history or accumulated social state

`protocol.py:164-204` creates a fresh StateSnapshot with persona only. Relationship defaults to zero, npc_state to None and recent_dialogue to empty (`contracts/context.py:88-99`). `bridge.py:320-338` invokes this on every turn; the native delivery branch at164-178 only updates delivery_status and publishes heard_text=None. It never commits memory. Closing/reopening dialogue replaces Session.

Consequences: a follow-up cannot refer to the last answer; repeated questions have no previous answer context; repeated insults do not accumulate relationship effects; apologies cannot modify a stored mood. These are absent Skyrim integration, not absent reusable core components.

Minimal wiring: keep a SocialStore key per `(game,world,game_epoch,NPC,player)`, independent of menu session. On start call ensure(default/authored relationship,mood); before input load/begin_turn with its *database* revision and dedup digest. Inject returned relationship, fresh NpcState and bounded history into the canonical snapshot. Preserve native snapshot revision separately. Stage the accepted preview and delivery correlation before exposing a command, then commit only a matched terminal completed native receipt. Failed/interrupted/cancelled replies must never become complete NPC history; input effects may remain because the player's admitted utterance already occurred. On menu close keep scoped stored state; on load/reset use the changed epoch to isolate other saves. Cross-restart save restoration requires an explicit stable save-branch identity and remains unproven.

Use existing SocialStore.ensure/load/begin_turn/stage_preview/displayed/cancel (`state/social_store.py:76-154`) and the lab service as a composition example, not a runtime import from tools/npc_lab. `DialogueMemory.source` currently only allows console_display (`context.py:76`), so deliberately add a native-completed adapter source or equivalent store label while preserving lab defaults. A completed receiver lifecycle is still not proof of hearing. Changed input under a duplicate ID must conflict; the current bridge's early inputs-dict short-circuit returns status without checking its text digest.

Acceptance: answer A completed -> follow-up prompt contains A exactly once; A interrupted/failed -> excluded; B/new NPC and another epoch -> isolated; close/reopen same NPC/epoch -> retained; duplicate input/ack -> no repeated social delta/history; disk/capacity failure -> explicit fail-closed state; at most8 whole recent exchanges and bounded bytes. Add a repeated factual query plus pronoun follow-up using a controlled fact oracle; update facts must supersede previous NPC assertions.

### 3. Barge-in is inconsistent and busy text can reset the whole session

`native/plugin.cpp:394` uses currentTopicInfo!=nullptr as vanillaTalking; `native/delivery.h:34` unconditionally chooses wait. No verified vanilla voice-stop API is called. CurrentTopicInfo is a dialogue bookkeeping pointer, not direct proof of an active audio instance. Existing native test explicitly expects waiting.

F8 stops Anima's owned sound before listen_start (`plugin.cpp:129-132`), but native text entry queues player_text without Stop (`243`). `Bridge.player_input` rejects active work/playback as busy; native Worker treats all409s as resync (`plugin.cpp:505-510`), potentially ending a valid conversation on ordinary barge-in.

Fix now: define explicit interrupt/queue policy for both text and microphone. Cancel prior generation/TTS, stop only the owned sound, order the interrupted receipt before admitting the replacement turn, and distinguish session-loss conflicts from ordinary busy/stale-request rejection. For vanilla speech, verify an actual actor/dialogue audio-stop mechanism against this runtime; the pinned Actor/AIProcess headers do not expose a simple StopTalking method. Do not guess a relocation or assume StopCurrentIdle stops audio. Regression should cover text during owned audio, input during generation, vanilla speech, double F8, delayed old callback and no interruption of another NPC/mod's audio. Measure stop latency and confirm no duplicate/late speech.

### 4. Requested guard warning/escalation is not implemented, and common directed input is misclassified

`behavior/appraisal.py:8-25`: DIRECT_INSULT matches fuck you/off but not the user's FUCK U. THREAT only matches selected future-harm phrases, not FIGHT ME. Executed probes returned FUCK U -> incidental_profanity/brief/neutral, FIGHT ME -> neutral/brief, fuck you -> directed_insult/boundary/angry. Quoted reported abuse and incidental profanity correctly avoided directed-insult classification in the probed cases.

`behavior/policy.py:28-40` can warn/end dialogue, but neither InteractionPlan/ResponseBody nor the native command protocol carries an authorized mechanical hostility action. Existing social thresholds aim at withdrawal/disengagement, not a second-insult attack. Merely generating an angry line does not make the actor hostile.

Fix now: add narrowly normalized directed-chat variants with negative cases; retain quotation/reporting, friendly banter and confidence protections. Add an authored guard-specific action policy with an idempotent warning counter, bounded expiry/reset and a correlated warning-completed receipt before a later insult can authorize hostility. Keep the action separate from model text: typed action ID, NPC/player/session, expected revision, expiry and policy reason. The native receiver must revalidate actor/readiness/scope, execute a verified game action once and acknowledge it. Never parse threats/hostility out of an LLM's prose.

Acceptance: first directed insult -> warning, acknowledged warning + second -> one hostile action for explicitly configured guard; duplicated inputs/acks -> no extra count/action; quoted abuse, incidental swear, HELLO, low-confidence STT, new epoch/NPC, stale/expired action and closed conversation -> no hostility. Define treatment of apology, elapsed time, injured/fearful NPC and allied guard. Those are authored gameplay rules, not measured human psychology.

## P2 findings

### 5. Authored personalities and knowledge are optional and currently missing in the live configuration

`protocol.py:152-161` falls back to name plus unknown occupation/social role and neutral traits. The inspected local config has profiles_file=null and rag_config=null. Captured factions/voice/available dialogue do not automatically become biography or allowed knowledge; that conservative behavior is sound. However, naming an NPC Whiterun Guard alone does not supply an authored guard persona or source binding. Generic model responses cannot validate personality variation.

Author a small explicit guard/merchant/companion fixture set, scoped knowledge bindings and initial traits; log profile/source IDs without secrets. Test controlled personality contrasts using the same utterance/facts/relationship. Do not infer private knowledge from factions or player-camera screenshots.

### 6. Existing history packing can remove prior NPC answers on dialogue-source retrieval

`generation/prompt.py:147-153` deliberately keeps only the prior player side when knowledge.source_kind==dialogue. That prevents old generated claims from becoming evidence, but loses what the NPC actually said for conversational follow-ups even after history is wired. Preserve acknowledged prior NPC wording in a separately labelled untrusted conversation channel when needed, while current authorized evidence remains the factual authority. Test references to earlier wording, corrected knowledge and a malicious prior response; do not promote memory to world truth.

### 7. UI and lifecycle remain partial

F7 UIExtensions controls/text now have actual user confirmation and native load/population logs. That is progress. The normal dialogue-list Anima topic, loaded compiled MCM/ESP, startup/service ownership and Mantella-disabled test profile remain unverified. The local bridge was observed disappearing during live tests, so a visible menu alone cannot establish system availability. Display service readiness/failure explicitly and package/start the companion reliably. Preserve Default mods/saves and make an isolated reversible Anima-only profile; test loaded modules after restart. Papyrus source or compiled PEX alone is not proof that the topic/MCM is registered in-game.

### 8. Emotion/realism metrics are not defined as empirical acceptance gates

The implemented Persona warmth/caution/patience/assertiveness and relationship favourability/trust/familiarity/fear/irritation are bounded authored parameters (`context.py:39-59`), and the reducer has inspectable rules (`appraisal.py:55-72`). Their values are not validated psychological measurements. The current Skyrim bridge does not even retain them. Generic SAPI voice also does not expose affect/prosody controls; energy-based mouth motion is not phoneme alignment.

Measure after mechanical/state correctness: directed-insult/threat precision/recall on fixed labelled English variants; false-hostility rate on quoted/incidental/uncertain inputs; delivered-history inclusion/exclusion and follow-up factual consistency; identity/style/role consistency with blind independent ratings; event-to-tone mapping against authored policy; audio-start/completion, barge-in latency and frame-time/CPU contention. Separate authored, fallback and generated routes in latency/quality denominators. Hold facts/settings constant for personality contrasts, repeat model trials and preserve failed/unmatched cases. Do not use passing test counts, an LLM critic or a few impressive responses as a human-realism score.

## What is already sound

One shared core, typed strict input/output boundaries, source-bound RAG, explicit unknowns, one bounded repair, cancellation/revision checks, correlated native receipts and escaped bounded console logs are justified. Reuse the existing store/context/prompt mechanisms instead of a second agent framework, semantic answer cache or unrestricted model-driven game actions. Native audio failure and memory/interrupt wiring should be fixed before new facial/emotional presentation work.

## Review execution limits

Inspected the native/bridge/protocol, current I21 plan, behavior/context/prompt/preview/state contracts, social-store/lab integration, speech service/worker and relevant tests. Ran only seven deterministic social-appraisal probes with .venv. No new regression, live game action, speech playback, provider request or independent human rating was performed by this reviewer. Parent's logs and the user's report supply the live observations above. Root-cause candidates for audio remain hypotheses until measured resource/audio diagnostics establish them.


## Independent implementation follow-up: audio, state and interruption wiring

Reviewed the subsequent root changes read-only. No live playback validation or new regression run was performed by this reviewer. A temporary offline fixture reproduction was executed for the cancelled-completion case below; it created no repository runtime state. The parent's reported focused/native test results remain distinct from this review.

### P1: cancelled staged delivery can make a later completed receipt permanently fail

In the inspected Bridge.invalidate, the social row is cancelled but active delivery_status remains pending/started and delivery.kind becomes stop. The delivery handler then calls SocialStore.displayed for a matching completed receipt before terminal bookkeeping. Because the row is cancelled, displayed raises StateConflict(display_conflict); status/sequence/cleanup are not advanced. An offline reproduction produced exactly: StateConflict display_conflict; delivery_status pending; command_kind stop; history_count0. The history exclusion is conservative, but the sender can retry a terminal event that can never commit and retain the staged WAV/event queue.

Track cancellation-requested deliveries explicitly. A correlated late terminal event for such a delivery should finalize receiver cleanup/bookkeeping without adding complete NPC history. Preserve the distinct case where completion was already committed before cancellation. Test invalidate-staged -> completed, invalidate-started -> completed, duplicate terminal, subsequent new turn and storage failure. Do not weaken the cancelled=0 store guard to make the failing commit pass.

### P1: native barge-in needs an input/turn generation to reject already downloaded old commands

Stopping only an active handle does not invalidate an old speak command already downloaded or in flight in the native commands queue. It still has the same session/NPC/snapshot revision and can be accepted after the user interrupts. Clearing the local queue is not sufficient for an in-flight poll. Bridge previous_task cancellation cannot invalidate commands already outside the bridge.

Advance a native dialogue/input generation before admitting replacement text/microphone input, carry it end-to-end and reject older commands. One minimal existing-contract approach is a fresh incremented state/dialogue revision snapshot queued before the new input event; another is an explicit input generation in events/commands. Preserve FIFO snapshot/input admission and validate the new generation at native Apply. Test commands downloaded before input and returned after input, including authored fast response and cancellation while TTS runs. No old response may start after the new input was accepted.

### P2: rapid replacement inputs can lose the oldest cleanup barrier

Session.previous_task holds one task. A -> B -> C admission before B begins can replace the stored A reference with B; C only waits B, while A/provider cleanup can still be pending. The core's existing provider ownership/admission limits should prevent duplicate inference, but the newest turn can become busy/failed rather than cleanly following cleanup. Add a rapid three-input test with delayed/cancellation-resistant cleanup. Keep a bounded explicit cleanup chain/set or rely on one runner-owned cancellation/admission mechanism; do not add an unbounded queue or claim local cancellation stopped remote billing.

### P2: service/state failure and replay coverage is still needed

SocialStore failure in the native delivery-ack path is not translated to a useful bridge health error before raising. Ensure unavailable/full storage is visible and fails closed without fabricating memory or leaving normal native event processing permanently opaque. Test a cached staged-but-uncompleted request after bridge restart, same ID with changed payload across menu sessions, new NPC/epoch isolation, stage failure after WAV creation and complete-ack database failure. Existing in-session fingerprint rejection and removal of a just-created WAV on stage failure are sound.

### Positive changes and remaining empirical gates

- AudioState now waits for observed IsPlaying, has bounded startup/overrun handling and distinguishes never-started failure from interruption. Native resource-stream preflight, path normalization, fresh handle, explicit volume/priority/output model and observed-start logs directly address the earlier missing diagnostics. These establish a better state machine, not proven audible voice. Timing tolerance may classify a fully heard clip as interrupted under large polling delays; measure it rather than weakening it into arbitrary completion.
- The bridge now composes the existing store, keeps database and native revisions distinct, injects relationship/mood/recent dialogue, stages before exposing output and labels committed history game_completed while preserving the lab default. This is the right reuse and keeps knowledge/history separate.
- Same-session changed-ID-content reuse is rejected before a second social update, and completed/failed history tests exercise useful observable behavior. Current tests do not cover the two P1 orderings above.
- Retain current semantic limits: acknowledged conversation is untrusted history, not world truth; epoch-scoped state is not save-checkpoint reconstruction; lifecycle completion is not proof of hearing; guard mechanical escalation and vanilla speech stop require their own verified contracts and tests.

Follow-up verdict: **conditional go after the two P1 cancellation/order defects are addressed; no live voice or complete-conversation signoff.**
