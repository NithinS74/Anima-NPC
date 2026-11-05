# Independent Skyrim connection layer

This connector is independently authored and does not load, modify or call Mantella. It consists of an SKSE plugin (`AnimaConnector.dll`) and a loopback Python bridge. The built-in pipeline connects captured frames to the local VLM service, scoped RAG, the existing context/policy/provider/validation pipeline and native text/optional audio delivery. Player STT defaults to automatically prepared local Whisper base.en (English, CPU INT8). Chatterbox Turbo TTS is enabled automatically after its one-time setup. Native source/build verification and live-game verification are distinct; see the [implementation self-review](reviews/2026-11-02-skyrim-connector.md) and [integration plan](plans/I18-skyrim-vision-pipeline.md).

## What it captures

Opening the vanilla dialogue menu starts a conversation session after a short menu-settling delay. The plugin reads the engine's selected speaker, actor reference/base identity and source plugin, race, voice type, sex, combat/death state, weapon state, NPC-to-player line of sight, hostility, base factions and equipped hand items. It reads location/cell, interior status, game clock and outdoor weather. A bounded one-second full snapshot refresh keeps observations fresh; meaningful actor/dialogue changes invalidate pending output. It never scans the entire world or all quests.

The engine dialogue manager supplies the currently offered topic text, resolved response text entries, topic/info identifiers and associated quest/current stage. This is a read-only view of the current menu, not an exhaustive dialogue-condition evaluator. Limits: 16 topics and 8 response entries/topic; text fields are bounded. `dialogue_complete` means the observed manager list was not truncated, **not** that every possible line/branch has been enumerated. Runtime behavior on the selected Skyrim version still needs in-game verification.

Skyrim does not expose a definitive "everything this NPC knows" field. The payload preserves game observations and dialogue provenance. Biography, personality and knowledge references can be added by an explicit authored profile keyed by `base.plugin.lower():base.local_id.lower()`. Unconfigured roles/knowledge remain unknown. Factions, player-camera visibility and quest records do not automatically grant the NPC knowledge. Vanilla quest dialogue and its effects remain under the game's control; generated speech never executes quest, inventory or combat actions.

## Build and installation

The 0.2.0 plugin explicitly supports **SkyrimSE.exe 1.6.318.0 and 1.7.104.0** from one x64 DLL. Other runtimes remain rejected. Use the matching SKSE loader and Address Library for the selected executable:

| Runtime | Required Address Library | Header format | Verification |
|---|---|---:|---|
| 1.6.318.0 | `Data/SKSE/Plugins/versionlib-1-6-318-0.bin` | 2 | Native allowlist/metadata/library checks; separate live run still required |
| 1.7.104.0 | `Data/SKSE/Plugins/versionlib-1-7-104-0.bin` | 5 | Live load, Jenassa context and authored text delivery started/completed; see current review |

A pinned modern CommonLibSSE-NG supplies version-aware native layouts and both Address Library readers. Metadata uses an exact version list rather than generic version independence: old SKSE rejects the newer `StructsPost629` flag, and this plugin does use native structures. A matching-file/header preflight runs before SKSE initialization; CommonLib validates and resolves the complete library afterward. Merely bypassing a version guard is not compatibility. See [dual-runtime plan](plans/I19-dual-skyrim-runtime.md) and [current review](reviews/2026-11-03-dual-skyrim-runtime.md). Mantella, SkyUI, UIExtensions and a Mantella ESP are not dependencies of this connector.

Build with the project Python, CMake, and an x64 MSVC toolchain with C++23 support (Visual Studio 2022 17.14 or newer). The IDE alone does not install its C++/Windows SDK components:

```powershell
# First build only: download the pinned source dependencies if missing.
.\.venv\Scripts\python.exe scripts/build_skyrim_connector.py --fetch
# Subsequent builds:
.\.venv\Scripts\python.exe scripts/build_skyrim_connector.py
```

Build tools are separate from Python runtime dependencies. The build accepts CMake on PATH or the project-local `output/build-tools/cmake/data/bin/cmake.exe`. The latter can be prepared with `python -m pip install --target output/build-tools cmake==3.31.6`. Visual Studio 2022 is the default generator. For an already configured compiler environment, `--generator Ninja --build-dir output/skyrim-build-dual` uses a separate Release tree. Keep distinct build trees for different generators/toolchains. Pinned sources are recorded in `configs/skyrim/native-dependencies.json`; modified dependency checkouts are rejected rather than overwritten.

The build packages `output/skyrim-mod/AnimaConnector.zip`, including DLL/INI, source license notices, both runtime targets, per-runtime verification status and DLL hash. Build/test success never automatically marks either runtime live-verified. Native source and dependency licenses are included; the previous dependency pins are retained in `configs/skyrim/native-dependencies.legacy-1.6.318.json` as provenance for the original source baseline, not as a drop-in dependency set for 0.2.0. Install it as a separate mod-manager mod, or copy the ZIP's `SKSE` directory into Skyrim's `Data` directory. It has no ESP to enable. The build script does not change the game installation. Keep a separate test save. Uninstall by removing only `AnimaConnector.dll`, `AnimaConnector.ini` and this connector's generated `Data/Sound/Voice/AnimaConnector` directory.

## Start the bridge

Run `run_skyrim_connector.bat` from the repository. It creates the ignored `configs/skyrim/connector.json` from the public example on first launch, then runs `python -m npc.adapters.skyrim`. Edit `game_directory` if Skyrim is elsewhere. Start the bridge before opening a game conversation; load Skyrim through SKSE.

The server binds **127.0.0.1:8768**. If changing its port, also change `Data/SKSE/Plugins/AnimaConnector.ini`. Health: `GET /v1/health`. The SKSE log directory contains `AnimaConnector.log`. The bridge's health status reports transport readiness, not that every downstream model or game API has passed a live check.

## Pipeline connections

The public example defaults to `pipeline_mode: "preview"`, composing the working core with an offline provider. Existing local configuration is preserved. The alternative `pipeline_mode: "inbox"` writes typed JSON events to `output/skyrim/inbox/` and waits for a result callback. Do not infer ordering from UUID filenames; use `kind`, `request_id`, `revision` and capture timestamps. Context is persisted before that session's player turn is emitted. Files remain local, subject to the output budget; archive them explicitly when the budget fills.

For a running external pipeline set `pipeline_mode: "http"` and `pipeline_url` to its loopback event endpoint. The bridge sends:

| Event | When | Contents |
|---|---|---|
| `context_ready` | Conversation begins | Actor/game/menu snapshot, profile/knowledge references, screenshot metadata |
| `context_updated` | Material context changes | Updated snapshot and revision |
| `player_turn` | Text/STT input arrives | Correlation/deadline, current game/profile, canonical `ContextScenario`, screenshot reference |
| `delivery` | Game reports output status | Delivery/request IDs, started/completed/interrupted/failed; no invented heard text |
| `context_closed` | Menu closes/save changes | Closed session ID |

`context_ready` is the prewarm/data-ingestion trigger. It does not fabricate a player utterance or ask the model to speak.

The full collected event also enters the pipeline through `scenario.adapter_context`, including in built-in preview mode. This optional shared ingress field has `source: "anima-skse"` and a bounded JSON `payload` containing `game_event`, `npc_profile`, `screenshot` and `image_description`. `game_event` preserves native event IDs, capture time, revision and the complete snapshot (actors, dialogue/quest entries and world fields). Player text/STT confidence and scoped identity remain in `scenario.turn`. Screenshot data is metadata/a local path, not image bytes; descriptors remain null when unavailable or expired. Existing top-level HTTP/inbox fields remain available for compatibility.

The connector delivers observations without interpreting them: canonical fact selection, prompt selection and knowledge authorization are unchanged. Presence in `adapter_context` does not establish NPC perception or grant knowledge. The descriptor reaches ingress regardless of prompt attachment; `attach_visual_reference` still controls the existing explicit prompt path.

The pipeline may return HTTP 202 and later call `POST /v1/pipeline/result`, or return the same result JSON immediately from its `player_turn` request. Other event responses should be HTTP 202/204. A result must refer to the exact pending session/request/NPC:

```json
{
  "session_id": "copy-from-player-turn",
  "request_id": "copy-from-player-turn",
  "npc_id": "copy-from-player-turn",
  "mode": "speech",
  "text": "The final validated line spoken by the NPC.",
  "audio_path": "response.wav"
}
```

`audio_path` is relative to `audio_root` (default `output/pipeline/audio`), or an absolute path contained there. The pipeline must finish writing the file before submitting it. Only PCM16 mono/stereo WAV, 8-48 kHz, at most 30 seconds/6 MB, is accepted. Text must be the final validated transcript used for this audio; the bridge cannot verify semantic text/audio correspondence. It never asks the LLM to choose a filesystem path.

Alternatively return text without `audio_path` and configure `tts_url`. The bridge POSTs `{request_id,text,voice}` to that endpoint and expects `audio/wav` bytes. This calls the existing/future TTS service; it does not introduce another speech model. Without either audio source, output is subtitle-only. Explicit `silence` requires empty text and no audio. `end` can include a farewell; the native side closes the menu after delivery.

The command channel stages verified audio under `Data/Sound/Voice/AnimaConnector/<delivery-id>.wav`, attaches it to the NPC using Skyrim's audio engine and adds an NPC-associated subtitle. It waits while vanilla dialogue owns the speaker. Optional amplitude-based mouth movement is controlled by `AnimateMouth` in the INI; it is approximate, not `.lip` or phoneme-aligned animation. Engine playback/subtitle behavior still requires a live smoke test. Terminal delivery removes the staged file. A process crash may leave an orphan file; remove orphan files only while the game/bridge are stopped.

## Player speech input

Hold **F8** while in a conversation, speak, then release. The native plugin sends `listen_start`/`listen_stop`; the bridge records the default Windows microphone as 16 kHz PCM16 mono, with a 15-second cap. Recording starts only from this explicit control. A null/missing `stt_url` selects the built-in Whisper endpoint at connector launch; explicitly configured external URLs are preserved. The STT endpoint receives raw `audio/wav` and returns JSON `{ "text": "...", "confidence": 0.95 }`. Source audio is deleted after reading. Closing the session shuts down recording.

Run `run_skyrim_connector.bat` normally: no STT flags, manual model downloads, file moves, CUDA setup or system FFmpeg installation are required. The launcher runs project setup if Whisper dependencies are missing. Setup prepares the pinned `Systran/faster-whisper-base.en` revision; connector startup also prepares it if absent and verifies that it loads before accepting recordings. First preparation requires internet/disk space; subsequent starts use ignored `data/stt/hub/` offline. Downloads can resume after interruption; an unloadable cached model is repaired once. A failed preparation stops startup with a retry instruction rather than claiming readiness.

The fixed decoder uses English, CPU INT8, two CPU threads and one worker, with VAD and a single decoding beam. Each utterance runs in an isolated process with a 20-second limit; cancellation/timeout kills it before temporary WAV/request cleanup. This reloads the model per utterance to keep teardown reliable; measure latency alongside Skyrim before claiming real-time performance. `confidence` is a mean token-probability proxy, not a calibrated accuracy estimate. Silence produces no fabricated player utterance. Only local inference is used; no speech API key is needed.

`GET /v1/speech/health` reports built-in STT readiness. `--local-speech` now adds the existing Windows TTS to Whisper STT; it no longer selects Windows dictation. It still uses the default Windows voice. For NPC-conditioned speech, use the Chatterbox setup below; XTTS is not installed.

To prepare manually for diagnostics (normal users need no extra step):

```powershell
.\.venv\Scripts\python.exe -m npc.adapters.skyrim.whisper --prepare
```

An existing STT client can bypass recording and POST its result to `/v1/player-input`:

```json
{"session_id":"from-context-ready","input_id":"unique-utterance-id","text":"Hello.","source":"stt","confidence":0.95}
```

For a text-only test use `source: "text"`. A duplicate input ID does not generate another reply. There is one active turn/delivery; input during playback is rejected until the game reports interruption/completion. The connector does not start a second microphone or implement a new recognizer.

## Screenshots and image-descriptor handoff

On conversation start and material context updates, the bridge captures the foreground game's client area by process ID and saves PNG under `output/skyrim/screenshots/`. Payload metadata includes the file path, frame capture time, source event and `viewpoint: "player_camera"`. Set `cv_url` to `http://127.0.0.1:8000` to send the frame to the local CV service. `image_description` then carries a compact validated descriptor; it stays null when disabled/unavailable/stale. Capture or analysis failure permits ordinary dialogue. Retention defaults to 100 frames; old frames may be removed.

CV waits at most `cv_timeout_s` (default 8 seconds) within the player's total turn deadline. Results are bound to session/revision and expire `visual_ttl_s` after capture (default 15 seconds). A subsequent turn refreshes expired/missing visual context. Slow cold inference can finish too late and be discarded; warm the VLM separately. The descriptor is available for inspection by default. Only explicit `attach_visual_reference: true` includes it in the built-in provider prompt as untrusted player-camera reference. It never becomes NPC perception, state, a RAG source or a valid citation. HUD/identity/quest claims must not be treated as known facts.

This first capture backend uses Windows GDI. Use borderless/windowed Skyrim; exclusive fullscreen, overlays or protected rendering can produce missing/black frames. That behavior needs an actual game check. Captured HUD/quest text is player-visible data and must not be promoted into NPC knowledge by a future descriptor.

## Existing pipeline smoke binding

Set `pipeline_mode: "preview"` to compose the existing `PreviewRunner` and configured provider profile. The default profile is scripted/offline; changing it to a live profile can make paid calls when the player submits input. Set `rag_config` to a trusted RAG configuration with `game_id: "skyrim"`, your `world_id` and actual actor reference IDs such as `ref:00013478`. Prepare the index with the existing [RAG commands](RAG_INTEGRATION.md) before play. Unbound identities fail closed; authored profile knowledge labels alone do not grant retrieval access. No ingestion/model download occurs during a turn. The built-in path uses a 12,000-byte prompt cap to accommodate game observations, evidence and optional visual reference.

Run `run_cv.bat` in one terminal and `run_skyrim_connector.bat` in another. See [CV setup](../cv/SETUP.md) for the Ollama prerequisite; `GET http://127.0.0.1:8000/ready` checks the local model without downloading it. Leave `stt_url` null for automatic Whisper STT. Leave `tts_url` null for automatically prepared Chatterbox, or subtitle-only output before Chatterbox setup. Explicit external URLs are preserved. Submit text to `/v1/player-input` using the active session ID from `/v1/health`; validated output is returned through the plugin's command polling. The [integration tests](../tests/unit/adapters/test_skyrim_connector.py) exercise this path with deterministic inference and game boundaries.

This composes the current canonical game-context subset. Production social memory and reliable heard-memory commits remain unimplemented for this best-effort native receiver. Console acknowledgements do not establish game delivery.

## Guarantees and limits

The handoff inbox stops admission at 4,096 retained event files; archive processed records explicitly. Its total storage budget is independent of the screenshot count limit.

Game object access is on the engine task thread; HTTP runs on a worker. Queues, requests, payloads, turns, microphone time, screenshots and output size are bounded. Commands carry session/NPC identity, state revision, delivery ID and start expiry. Native dedup prevents repeated polling from replaying speech. Combat/menu close/load changes stop output. Late callbacks are rejected; an expired command requests stop rather than assuming it was heard. Acknowledgements are best effort and do not establish word-level heard portions.

Offline tests use fake game/capture/model/device boundaries. They verify mapping, actor identity, visibility, context-before-turn, stale state, callbacks, duplicate/expired commands, file containment and cleanup. No real microphone, Skyrim launch or paid model call runs in these tests. Live readiness requires opening one conversation, checking exported topics/responses and frame, submitting one text/STT utterance, hearing/watching one response, and testing menu close/combat/load interruption.


## Identifying Anima output alongside other mods

Start `run_skyrim_connector.bat --log-file output/skyrim/anima-console.log` in a visible terminal. Every diagnostic has a timestamp and `[ANIMA]` label. Startup lists provider profile and RAG/STT/TTS availability. The default offline profile is scripted, not a live language model. A Mantella.exe window, its speech recognition and its synthesized responses belong to Mantella; Anima neither consumes nor relabels them.

With normal NPC dialogue open, use another terminal to submit directly to Anima:

```powershell
.\.venv\Scripts\python.exe -m npc.adapters.skyrim --say "HELLO"
```

`PLAYER_INPUT` records accepted text, `PIPELINE_RESULT` distinguishes authored/model/fallback routes and model call count, and `OUTPUT_STAGED` records the accepted text awaiting the game. Only `NATIVE_ACK` represents the native receiver's started/completed/interrupted/failed status. Completion is not proof of hearing. Session/request/delivery IDs correlate the stages. Rejected/duplicate inputs are not relabelled as new successful turns. Uppercase greetings currently use the same case-insensitive authored greeting policy; no shout-sensitive behavior is claimed.

The optional local log includes dialogue text; keep it private unless selected for publication. Text fields are escaped to one line and capped at 1024 characters. File output rotates at 1 MiB with two backups. Full prompts, provider keys and raw responses are not logged. No per-frame snapshots or command polls are printed. Close/reopen NPC dialogue after restarting the bridge to establish a fresh session.

## Chatterbox Turbo NPC voices

Run **`setup_chatterbox.bat` once**, then start `run_skyrim_connector.bat` normally. The script uses the same project `.venv` and `requirements.txt`, installs pinned dependencies, downloads the pinned English Turbo checkpoint/tokenizer/voice encoder/generator, generates a setup WAV, finds Skyrim and extracts short voice references. No manual model downloads, file moving, external FFmpeg installation or separate speech server is required. A fresh machine still needs the repository's Python 3.11 prerequisites. Downloads total approximately 3 GB for model files plus Python packages; allow several GB of free space and internet for first setup.

Game discovery checks the existing connector configuration, Bethesda's Windows registry entry and Steam libraries. If automatic discovery fails, supply the game folder once:

```powershell
.\setup_chatterbox.bat --game-directory "D:\Games\Skyrim Special Edition"
```

Fresh setup installs CPU Torch wheels to avoid CUDA installation/driver steps. A compatible already-installed CUDA Torch build is preserved, and the worker uses CUDA when that build reports it available; otherwise it uses CPU. No GPU speed, VRAM fit or real-time CPU performance is guaranteed. The current pinned Torch release does not establish compatibility with every GPU generation. Test alongside the game before claiming readiness.

The importer reads vanilla/DLC VTYP editor IDs and the matching voice folders in installed English voice BSAs. Bundled PyAV decodes FUZ/XWM audio; generated 5–10-second PCM16 references and source hashes stay under ignored `data/tts/voices/`. It attempts a bounded number of clips per voice type and preserves existing entries/overrides. These automatically selected clips need listening review for acting, music/noise and pronunciation; no claim of curated performance quality is made. It does not import saved player data, alter game files or commit extracted assets. Mod-added voice definitions are not automatically imported in this first slice.

`manifest.json` maps `voices` by `plugin:local-form-id`. Optional `npcs` entries use the NPC base `plugin:local-form-id` and the same `{file,sha256}` reference shape. NPC overrides take precedence over voice types. References must remain inside the voice directory and contain 5–15 seconds of PCM16. Missing/mismatched references fail synthesis; the bridge reports a TTS failure and retains subtitles rather than choosing an unrelated voice. The setup marker is written only after model preparation, usable references and offline regression succeed. A partial download or missing game does not enable TTS.

One resident worker owns the loaded model and serves one request at a time, with four cached reference conditionings. Every request explicitly selects/restores its voice conditioning, including cache hits. Startup has a 120-second readiness limit; synthesis has a 20-second limit within the bridge's remaining deadline. A disconnected/cancelled request or timeout kills the worker; subsequent work restarts it. Generated audio stays buffered and is validated as PCM16 before native delivery. No partial audio streaming or automatic laugh/emotion tags are added. Turbo does not implement the original model's CFG/exaggeration knobs.

Runtime uses only cached model files. `GET /v1/speech/health` reports worker readiness. `output/chatterbox/setup-check.wav` is a diagnostic sample using the model's built-in voice; it is not an NPC voice audition. Run an in-game human and Khajiit test and check matching text/voice, interruption and repeated voice switching. Linux/offline fixture tests do not prove native Windows playback or game-archive compatibility.

Dependencies are pinned to a compatible set because upstream Chatterbox also requires older NumPy, tokenizer, Hugging Face Hub, FastAPI/Starlette and Pillow versions. The unused upstream Gradio UI is not started. Upstream's project status is unmaintained; code/package and model revisions are pinned rather than following moving branches. See [Chatterbox source](https://github.com/resemble-ai/chatterbox) and [model files](https://huggingface.co/ResembleAI/chatterbox-turbo).
