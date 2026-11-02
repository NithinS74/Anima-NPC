# Independent Skyrim connector implementation self-review

2 November 2026. Self-review using the repository development/design-review skills; not an independent review. Scope follows the user's instruction to build the connection layer independently of Mantella and leave the image descriptor disconnected.

## Resolved findings

- Relevant-state revisions are separate from refresh sequence numbers. One-second snapshots update capture time without invalidating pending replies merely because the clock advanced. Material changes cancel pending work; the receiver independently checks the revision before speaking.
- NPC reference identity, base definition and load epoch are separate. Unknown knowledge stays unknown; visibility-gated facts alone enter the current canonical core view. Offered dialogue retains engine provenance and truncation status.
- Duplicate polls retain a delivery until a game report; native delivery IDs suppress repeat playback. Expiry requests stop rather than assuming playback never started. Old session/results and reordered terminal reports cannot restart speech.
- Native game access stays on game tasks; HTTP stays on a bounded worker. Screenshot capture has a single native-call admission gate, and screenshots are not sent to a VLM. Retention/output size/inbox count, turn counts, HTTP bodies and background tasks are bounded.
- Microphone cleanup waits for an in-flight native recording start; release cancels the 15-second timer, permitting the next utterance. An unconfigured STT control keeps the conversation intact and does not record. TTS failure preserves text when time remains.
- Audio paths are confined to the pipeline audio root and validated as bounded PCM WAV; game-facing filenames come from bridge-generated delivery IDs. Session/revision checks run after asynchronous preparation and before staging; terminal reports remove staged audio.
- The installed compiler cannot build CommonLib's newer main branch. The build pins its C++20-compatible 3.7.0 release instead of installing a system compiler or modifying third-party source. Two resource/audio convenience calls use documented Address Library relocations. Pinned source hashes and required license notices accompany the package.

## Verification

- Focused Python connector checks cover canonical mapping/visibility, schema/URL validation, screenshot/WAV artifacts, context-before-input, duplicate/cancel/expiry, HTTP routes/callbacks, failed pipeline, STT device boundary and TTS success/text fallback. Tests use fakes and no microphone/game/provider.
- Full Python regression: **438 passed**, including **21 connector cases**, after fixing the existing venv's stale editable-project registration. The initial eight CLI import failures were environment failures (`No module named npc`); `pip install -e . --no-deps --no-build-isolation --no-index` repaired the local registration without downloading runtime dependencies.
- Native Windows x64 Release DLL compiled with MSVC 19.29, CMake 3.31.6 and pinned dependencies. `scripts/build_skyrim_connector.py` also builds/runs `AnimaDeliveryTests` through CTest (one executable covering valid, duplicate, vanilla-speaking, changed state, expiry boundary, wrong NPC/session, missing/combat actor and invalid file ID).
- Packaging succeeded at `output/skyrim-mod/AnimaConnector.zip`, including DLL/INI, runtime/hash manifest and third-party license notices. `git diff --check` passed. No dependency was added to the Python runtime requirements.

## Remaining live gates

P1 before claiming live readiness: load with SKSE and the matching 1.6.318 Address Library; verify active-speaker/menu-response extraction, actor-attached audio, subtitle lifetime and stop/load behavior. Source inspection and a successful native build do not establish those engine behaviors. The supplied Data directory did not contain that Address Library file during this work.

P2: validate GDI capture in borderless Skyrim and default-microphone MCI recording on this hardware. Fullscreen/overlay capture can fail or produce black frames. Amplitude mouth motion is approximate; no phoneme-aligned lip sync is claimed. Knowledge and dialogue coverage are deliberately bounded, and save scoping is per load rather than historical save-checkpoint persistence.

Verdict: implemented and offline/build verified; go for the first controlled in-game smoke test. No live game launch, real recording, paid model call, Mantella modification, commit or push was performed. No production game-heard memory guarantee is claimed.
