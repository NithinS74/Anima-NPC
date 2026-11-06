# I24: Fixing the goal-gap pitfalls

Implements [the goal gap review](../reviews/2026-11-05-goal-gap-review.md) and [the conversation design](I23-conversation-dynamics.md). Planned by Opus; implemented by Sonnet agents; reviewed independently afterwards.

Hard limits for all work: no commits or pushes; no API calls; no game launch and no writing to the game folder; default tests stay offline and deterministic; preserve teammates' code; do not weaken a test to pass it. An intentional behaviour change updates its test and says why.

## Evidence that shaped this plan

- Receipts by delivery type: audio 0 completed, 5 interrupted, 1 failed; text-only 2 completed, 0 failed. This points at the audio path. `plugin.cpp:364` (any fingerprint change stops playback) is a secondary suspect. The sample is small.
- Interruption clears the subtitle (`Stop`), so the player also loses the text after about a second.
- Only completed receipts commit memory, so the NPC forgets every turn in-game.
- `Fingerprint` includes `sees_player` and the dialogue list, which can change without mattering. Each change also raises `snapshotSequence`, which can invalidate a turn or reply in progress.
- Four repeated questions produce an identical system prompt, limits and passages.

## WP-A: In-game delivery (P3)

Files: `native/plugin.cpp`, `native/audio_state.h`, native tests, `protocol.py`, `bridge.py`.

1. **Audio ending early is no longer an interruption.** `AudioState` gains `ended_early`, reported only after `IsPlaying` stays false for at least 300 ms, so a brief false reading is ignored. Then: stop mouth animation, keep the subtitle up to the planned duration, and report `completed` with `audio: "ended_early"`. The player did see the reply, so it counts as delivered.
2. **Stops have reasons.** `Stop` takes a reason (`barge_in`, `menu_closed`, `combat`, `actor_lost`, `state_changed`, `superseded`, `bridge_stop`, `audio_failed`, `end`) and logs it with `soundID`, elapsed and planned duration. Log each `IsPlaying` transition.
3. **Only material changes interrupt.** Split the fingerprint. Material: speaker reference, combat, dead, hostile, weapon drawn, location, cell. Everything else (`sees_player`, dialogue list, weather, equipment) still sends a snapshot but neither stops playback nor raises `snapshotSequence`. Check how the bridge uses `state_revision` so a same-revision snapshot updates data without cancelling work.
4. **Audio that cannot start.** If audio never starts within its window, keep the subtitle for the planned duration and report `completed` with `audio: "failed"`, instead of dropping a reply that the player can read.
5. **Receipts carry detail.** Add optional `reason` and `audio` (`full`, `ended_early`, `failed`, `none`) to the delivery event, backward compatible. Bridge logs them in `NATIVE_ACK`. Memory commit stays on `completed`.
6. **Barge-in still works.** A new player turn, menu close and combat still stop everything and report `interrupted`.
7. **Build and test.** Add native tests for the audio decisions. Build with `scripts/build_skyrim_connector.py`, run CTest and package the zip. Keep the source version in step with the 0.3.0 plugin already installed by raising it to the next version. Do not install it.

Unverified until a live run: whether the engine really plays 16 kHz SAPI audio. The new logs will show it.

## WP-B: Conversation director (P13, P4, P9, P8)

Follow I23 exactly. New `src/npc/context/conversation.py` and `src/npc/behavior/moves.py`; changes to `contracts/context.py`, `contracts/dialogue.py`, `state/social_store.py`, `behavior/policy.py`, `generation/prompt.py`, `validation/response.py`, `runtime/preview.py`, `rag/local.py`, `tools/npc_lab/`, `adapters/skyrim/bridge.py` and `protocol.py` only where state must be passed through.

1. **State contract.** `ConversationState`: bounded (16 topics, 8 told items, 8 player claims, 8 recent phrases; short strings). Optional and empty by default, so existing scenarios and fixtures still validate.
2. **Persistence.** New `conversation_state` table via `CREATE TABLE IF NOT EXISTS`, same scope key. Written in the same transaction as `displayed()`, so only completed turns update it. Duplicate receipts must not double-count. Save-branch isolation follows the existing key.
3. **Reading turns.** Pure `read_turn(text, state, similarity)` returning new, repeat, rephrase, follow_up, push_back, shared_news, stall, answered or return. `similarity` is injected: MiniLM when the local model is already loaded, otherwise a deterministic token-overlap fallback. It never downloads on a turn or fails the turn. Thresholds are named constants, calibrated on a labelled test set in `fixtures/evaluation/conversation/`.
4. **Moves.** Pure `choose_move(act, state, persona)` implementing the I23 table. Existing hard rules in `policy.py` still decide first and are unchanged. Repetition never changes knowledge access or trust.
5. **Plan.** `InteractionPlan` gains optional `move`. Length follows move and bounded rapport, within existing contract limits. Rapport never changes trust, favourability or knowledge.
6. **Dynamic prompt.** Add a conversation brief, the move instruction, phrases to avoid and already-told items. Update the instructions to allow in-character opinion and hearsay, labelled as such, while still barring invented facts (P4). Must stay inside the byte budget; if space is short, drop raw history before the brief.
7. **Fresh material.** Retrieve a larger candidate pool (up to 8), remove told passages, keep at most 3. An empty result on a repeated topic flags exhaustion and selects **Admit limit**.
8. **Reply checks.** New violations: `repeated_reply` (similar to recent NPC replies, or same opening words), `move_not_made` (Expand with no new material only) and `unsupported_name` (capitalised mid-sentence names absent from the prompt, P8). All use the existing one repair; total model calls stay at two or fewer.
9. **Varied lines (P9).** Authored and fallback lines come from pools keyed by intent and persona traits, chosen deterministically from the request ID, skipping lines recently used. A single-line pool falls back to that line.
10. **Visibility.** Trace and Inspect context show turn type, move and state.

11. **Openings and goodbyes.** Mantella has its model greet automatically when a conversation starts (`automatic_greeting = True`) and ends on goodbye words with a set line. Anima waits for the player, and answers a plain "Hello" with a fixed line. Add:
    - An **Opening** move when a session starts, using state: first meeting, returning soon after, or returning after a long gap and referring to the last topic. It is off by default in the core and on in the Skyrim profile. The line must not fabricate a player utterance or be recorded as one, and it enters memory only on a completed receipt.
    - Use an authored line for strangers and routine greetings, for speed and no API cost. Use the model when there is shared history worth mentioning, generated when the session opens, so it is ready at once. If the player speaks first, cancel it.
    - A **Farewell** move: goodbye phrases close the conversation with a persona-appropriate line, without a model call. A negation or a quoted goodbye must not end it.

## WP-C: Real game characters, context and knowledge (P1, P2, P5, P6)

Runs after WP-A and WP-B, since it touches shared files.

1. **Default characters (P1).** Adapter-side `derive_persona(snapshot)` using `configs/skyrim/role_rules.json`, matching names, factions, class and equipment to occupation, role, traits and goals. Authored profiles always win. Unknown NPCs get a plain townsperson persona, not "unknown". Rules live in the adapter or config, never in core.
2. **Using collected context (P2).** Add an optional generic `scene` list to the contract: bounded label, value and provenance. The Skyrim adapter fills it with what the NPC can perceive: place, time, weather, its own faction and gear, the player's visible gear. Quest stages and hidden state stay out. It goes to the prompt as data, and grants no knowledge. `adapter_context` stays unchanged.
3. **Layered knowledge (P5).** `SourceBinding` accepts several `sources` and optional `roles`, with `source` still valid. Filtering stays before ranking, and every hit is checked against the allowed set. Provide `configs/rag/skyrim.example.json`. No copyrighted lore is added to the repository.
4. **Failures (P6).** One retry for `provider_unavailable` and timeouts only, after a short delay, inside the deadline and the two-call limit. Never retry auth or rate-limit errors. Fallback lines come from the pools in WP-B instead of "I cannot say.".

## Corrections from plan review

An independent Sonnet review checked this plan against the code. Where these conflict with the sections above, these win. Work packages run one at a time, in the order A, B, C, because they share `bridge.py` and `protocol.py`.

**WP-A**
- `BargeIn` keeps its explicit `++snapshotSequence`. A non-material change still updates `lastSnapshot`, or the one-second poll fires again. Such a change replaces `session.event` only and does not refresh published context; this is intended.
- `Stop` becomes `Stop(reason, status, audio)`. `reason` and `audio` are added to `GameEvent`, which forbids extra fields.
- A `completed` receipt commits memory through `displayed()`. Committing on `ended_early` and `audio: "failed"` is deliberate, because the player saw the subtitle. The bridge cannot distinguish whether the reply was heard.
- One audio window: if audio is not observed within the existing 2 s, it counts as `audio: "failed"`. The subtitle then runs to its planned duration and reports `completed`, and neither step waits for `expires_at_ms`. `audioStartExpiry` must not produce a `failed` receipt first.

**WP-B**
- Add `candidate_k` (up to 8) to `RAGConfig`, separate from `top_k`, which stays at most 3. `LocalRetriever` passes it to the service, and `normalize_result` checks against it. Told passages are matched on stable evidence IDs, and at most `top_k` passages reach the prompt.
- `choose_plan` runs before retrieval and `InteractionPlan` is immutable. After retrieval, `preview.py` applies `apply_material(plan, knowledge, state)`, which uses `model_copy` to change the move to **Admit limit** when a repeated topic has nothing new.
- `begin_turn` stores the turn type. `stage_preview` stores the reply, move and evidence IDs. `PipelineResult` gains optional `move` and `evidence_ids`; external pipelines that omit them still work, and turn type comes from `begin_turn`.
- `displayed()` applies conversation state only when `UPDATE ... WHERE displayed=0` changes a row, because SQLite reports a row changed on repeats otherwise. A test covers duplicate receipts.
- `SocialStore` accepts versions 0, 1 and 2, and migrates version 1 to 2 with `ALTER TABLE` or `CREATE TABLE IF NOT EXISTS`. A test opens a real version 1 file.
- Brief sections have byte caps. At the default 2048-byte budget, drop in this order: raw history, already-told items, phrases to avoid, brief detail. The move instruction goes last. A test confirms that an ordinary turn still fits at 2048 without `PromptTooLarge`.
- New violations are added to `ViolationCode`. `unsupported_name` allows the player's words, persona, history, evidence, observations and common words, with possessive and quoted-word tests. Fallback lines are not checked for repetition but do avoid recently used lines.

**WP-C**
- A provider retry uses the second of the two calls, so a retried call that returns an invalid reply gets no repair; it goes to the fallback. The retry delay counts against `model_cutoff_ms`.

## Mantella independence

Checked on 2026-11-05, read-only, with the game running.

- **Independent:** Anima has its own DLL, port (8768 vs Mantella's 4999), audio folder and HTTP client. No code imports or calls Mantella, and it does not use `SKSE_HTTP`. It installs into the real `Data` folder, outside Mantella's MO2 mod.
- **Hidden requirements:** the in-game text box needs UIExtensions, and the settings menu needs SkyUI. Both are separate MO2 mods that stay on when Mantella is off. `docs/SKYRIM_CONNECTOR.md` wrongly says they are not dependencies. Hold-F8 speech and `--say` need neither.
- **Not yet ruled out:** every live test so far ran with `MantellaDialogue.dll` and `MantellaSubtitles.dll` loaded in the same game process, and the latter hooks the subtitle system. Interference could contribute to the audio interruptions. The only proof is a run with Mantella disabled.

Added to WP-A: at start-up, the plugin logs which other dialogue mods are loaded (`GetModuleHandle` only, for diagnostics, with no dependency), and the docs are corrected. Live acceptance runs the same conversation twice, with Mantella on and off. The installed DLL (11-03 15:19) is older than the last build (15:48) and differs from it, so live results need the new build installed first.

## WP-A2: Voice, using Mantella's approach

Runs straight after WP-A. Owner request: TTS must work, and we should reuse what Mantella already does well.

**How Mantella does it (read from the installed mod):**
1. Generates speech with `piper.exe` and a Skyrim voice model for each voice type (68 voices, 16 kHz, `maleguard.onnx`, `femalenord.onnx` and so on).
2. Generates a `.lip` file with `FaceFXWrapper.exe`.
3. Writes both into `Sound/Voice/Mantella.esp/MantellaVoice00/`, named after a dialogue info record.
4. Has the NPC speak through the engine: `actor.Say(topic)`, alternating two prepared topics, with `MantellaDialogue.dll` and `MantellaSubtitles.dll` handling the speaker and subtitle.

Anima differs at steps 1 to 4: SAPI's default voice, no lip file, and its own sound handle instead of `Say`.

**Lead on the interruptions:** Mantella wrote fresh voice files at 23:00 and 23:01 on 2026-11-05, the same minutes as both interrupted Anima turns. Mantella may have been speaking through the same NPC at the same time. This is not proven, but it makes the Mantella-off test decisive.

**Stage 1, now: Piper voices.** Add `PiperSpeech` beside `WindowsSpeech` in `adapters/skyrim/speech.py`, reusing the protocol in `tools/npc_lab/media.py` without importing lab code into the adapter. `--local-speech` uses Piper when it is available and falls back to SAPI, with the engine logged. The folder is configurable, defaulting to the project's `assets/private/npc_lab/piper`, so Mantella need not be installed or running. Map the NPC's voice type to a model; `scripts/chatterbox_voices.py` already reads voice-type records and shows how. Unknown voice types fall back by sex. Bounded subprocess and timeout, no Mantella imports, one active synthesis at a time. Tests use a fake `piper.exe`.

**Stage 2, only if needed: engine `Say`.** Run the Mantella-off test with the WP-A build first. If audio completes with Mantella off, the sound handle is fine, and Mantella was the conflict. If it still fails, build the `Say` route: our own `Anima.esp` with two topics, voice files in its folder, and native code to trigger speech. This is much larger, because it needs a new plugin file and native hooks equivalent to Mantella's two DLLs.

**Licensing:** Mantella is AGPL-3.0. Reuse the approach and run its tools, but write our own code. Do not paste Mantella source into this repository. Piper and the voice models are already in the owner-approved runtime media.

## WP-D: Faster replies

Runs with WP-A2, before WP-B.

**Measured (2026-11-05):**

| Step | Time | Note |
|---|---|---|
| Loopback HTTP | About 3 ms | So gRPC cannot save anything meaningful |
| Plugin polling | Up to 100 ms each way | `sleep_for(100ms)` in `Worker` |
| Orchestration | About 1 ms | Measured earlier |
| Model, normal | 1.1 to 2.6 s, median 1.4 s | 24 calls |
| Model, bad cases | 6 s, 20 s, 29 s; failures after 3.7 to 9.5 s | Live, no cutoff in the connector |
| Piper | About 0.7 s per call; 0.1 to 0.25 s warm | Measured three times with the real binary. An earlier single 3.8 s first run did not reproduce: it came from uncached files |
| Windows speech | Under 1 s | Log resolution is one second |

The model and its slow cases dominate, not the transport. gRPC is rejected, because the local hops are already milliseconds and the model's API is HTTP regardless.

Suspected, to be confirmed by timing: `run_turn` waits on `context_task`, which captures and PNG-encodes a full screenshot even when no CV service is connected, and `ChatCompletionsProvider` may open a new connection per request.

1. **Stage timing first.** Log millisecond timings for each stage of a turn (input to bridge, context wait, retrieval, model, validation, TTS, staging, native start) as one `TURN_TIMING` line.
2. **Stop waiting for unused screenshots.** When no CV service is connected, do not capture or wait.
3. **Reuse connections.** One long-lived `httpx.AsyncClient` per provider, so each turn avoids a new TLS handshake. Close it cleanly; tests stay on `MockTransport`.
4. **Cut off slow calls.** A real-time connector profile: if the model has not answered in a set time (default 4 s, configurable), abandon the call and retry once inside the two-call limit, then use the fallback line. Worst-case wait becomes about 8 s, not 29 s. Hedging (a parallel second request) is rejected for now: it spends quota on normal variance.
5. **Warm Piper.** Keep one process per recently used voice loaded if its protocol permits, otherwise pre-load on session start. Bounded to a few models, killed on timeout and shutdown.
6. **Tighter polling while busy.** Poll every 25 ms while a turn or delivery is pending, 100 ms otherwise. Native change, built with WP-B's or a later build.

Later options, not in this package: an immediate look or nod before speech, per-sentence streaming (small gain on one- or two-sentence replies, and validation must see text first) and a local model through the same interface, which removes network delay but needs a VRAM test beside the game.

Target, to be measured live: typical input to first speech under 3 s, worst case about 8 s.

## Scope cut (2026-11-05, usage limit)

The owner asked to drop anything unnecessary and finish what is planned. Dropped: the local language model, any live API runs, WP-A2 Stage 2 (engine `Say`), per-sentence streaming, and the paper update beyond a short status note. Kept, in this order: WP-A (done), WP-A2 Stage 1 and WP-D 1 to 5 (in progress), WP-A3 native (vanilla speech suppression, 25 ms polling), WP-B (conversation director plus openings and farewells), WP-C reduced to P1 and P2 only (default personas and scene context). WP-C items P5 (layered knowledge) and P6 are only done if budget allows.

## Deferred, with reasons

| Pitfall | Why not now |
|---|---|
| P7 hostility coverage | Needs its own labelled evaluation; a bad classifier wrongly penalizes players |
| P10 world events and spreading rumours | Depends on the director being proven first |
| P11 screen capture | Needs a live game to test a capture backend |
| P12 second game | Needs a second game chosen by the team |
| P14 human study | Needs people |

## Acceptance

- Scripted repeated-question conversations, with fake models: the prompt differs each turn, the move follows the table, and the same reply is rejected.
- Repetition unlocks no restricted knowledge. A test proves this.
- Interrupted replies do not update conversation state. A retried question is not treated as a repeat.
- At most two model calls per turn, including retry and repair.
- Existing fixtures and old databases still load.
- Added processing under 30 ms when measured offline, excluding the model.
- Native CTest and the full offline suite pass.
- Live in-game playback, memory across turns and live reply quality are reported separately as not yet run.
