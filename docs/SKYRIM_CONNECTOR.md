# Independent Skyrim connection layer

This connector is independently authored and does not load, modify or call Mantella. It consists of an SKSE plugin (`AnimaConnector.dll`) and a loopback Python bridge. The image descriptor and new STT/LLM/TTS implementations are outside this component. Native source/build verification and live-game verification are distinct; see the [implementation self-review](reviews/2026-11-02-skyrim-connector.md) for current results.

## What it captures

Opening the vanilla dialogue menu starts a conversation session after a short menu-settling delay. The plugin reads the engine's selected speaker, actor reference/base identity and source plugin, race, voice type, sex, combat/death state, weapon state, NPC-to-player line of sight, hostility, base factions and equipped hand items. It reads location/cell, interior status, game clock and outdoor weather. A bounded one-second full snapshot refresh keeps observations fresh; meaningful actor/dialogue changes invalidate pending output. It never scans the entire world or all quests.

The engine dialogue manager supplies the currently offered topic text, resolved response text entries, topic/info identifiers and associated quest/current stage. This is a read-only view of the current menu, not an exhaustive dialogue-condition evaluator. Limits: 16 topics and 8 response entries/topic; text fields are bounded. `dialogue_complete` means the observed manager list was not truncated, **not** that every possible line/branch has been enumerated. Runtime behavior on the selected Skyrim version still needs in-game verification.

Skyrim does not expose a definitive "everything this NPC knows" field. The payload preserves game observations and dialogue provenance. Biography, personality and knowledge references can be added by an explicit authored profile keyed by `base.plugin.lower():base.local_id.lower()`. Unconfigured roles/knowledge remain unknown. Factions, player-camera visibility and quest records do not automatically grant the NPC knowledge. Vanilla quest dialogue and its effects remain under the game's control; generated speech never executes quest, inventory or combat actions.

## Build and installation

The initial plugin explicitly targets **SkyrimSE.exe 1.6.318.0**, the executable inspected in this workspace. Other runtimes are rejected, including 1.7.104. Use the matching SKSE loader and Address Library file `Data/SKSE/Plugins/versionlib-1-6-318-0.bin`. A download named for a different runtime is not proof of compatibility. Mantella, SkyUI, UIExtensions and a Mantella ESP are not dependencies of this connector.

Build with the project Python and a Windows x64 Visual Studio C++ toolchain:

```powershell
# First build only: download the pinned source dependencies if missing.
.\.venv\Scripts\python.exe scripts/build_skyrim_connector.py --fetch
# Subsequent builds:
.\.venv\Scripts\python.exe scripts/build_skyrim_connector.py
```

Build tools are separate from Python runtime dependencies. The build accepts CMake on PATH or the project-local `output/build-tools/cmake/data/bin/cmake.exe`. The latter can be prepared with `python -m pip install --target output/build-tools cmake==3.31.6`. For VS 2022 use `--generator "Visual Studio 17 2022"` with a fresh build directory. Pinned sources are recorded in `configs/skyrim/native-dependencies.json`; modified dependency checkouts are rejected rather than overwritten.

The build packages `output/skyrim-mod/AnimaConnector.zip`, including DLL/INI, source license notices, runtime target and DLL hash. Install it as a separate mod-manager mod, or copy the ZIP's `SKSE` directory into Skyrim's `Data` directory. It has no ESP to enable. The build script does not change the game installation. Keep a separate test save. Uninstall by removing only `AnimaConnector.dll`, `AnimaConnector.ini` and this connector's generated `Data/Sound/Voice/AnimaConnector` directory.

## Start the bridge

Run `run_skyrim_connector.bat` from the repository. It creates the ignored `configs/skyrim/connector.json` from the public example on first launch, then runs `python -m npc.adapters.skyrim`. Edit `game_directory` if Skyrim is elsewhere. Start the bridge before opening a game conversation; load Skyrim through SKSE.

The server binds **127.0.0.1:8768**. If changing its port, also change `Data/SKSE/Plugins/AnimaConnector.ini`. Health: `GET /v1/health`. The SKSE log directory contains `AnimaConnector.log`. The bridge's health status reports transport readiness, not that every downstream model or game API has passed a live check.

## Pipeline connections

Default `pipeline_mode: "inbox"` writes typed JSON events to `output/skyrim/inbox/` and waits for a result callback. This is a usable handoff for the unfinished pipeline: a consumer watches new event IDs and posts results. Do not infer ordering from UUID filenames; use `kind`, `request_id`, `revision` and capture timestamps. Context is persisted before that session's player turn is emitted. Files remain local, subject to the output budget; archive them explicitly when the budget fills.

For a running external pipeline set `pipeline_mode: "http"` and `pipeline_url` to its loopback event endpoint. The bridge sends:

| Event | When | Contents |
|---|---|---|
| `context_ready` | Conversation begins | Actor/game/menu snapshot, profile/knowledge references, screenshot metadata |
| `context_updated` | Material context changes | Updated snapshot and revision |
| `player_turn` | Text/STT input arrives | Correlation/deadline, current game/profile, canonical `ContextScenario`, screenshot reference |
| `delivery` | Game reports output status | Delivery/request IDs, started/completed/interrupted/failed; no invented heard text |
| `context_closed` | Menu closes/save changes | Closed session ID |

`context_ready` is the prewarm/data-ingestion trigger. It does not fabricate a player utterance or ask the model to speak. All game-specific data remains in the `game` envelope, because the existing core supports only a small canonical fact vocabulary. The connector does not silently inject unsupported dialogue or quest fields into the current prompt builder.

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

Hold **F8** while in a conversation, speak, then release. The native plugin sends `listen_start`/`listen_stop`; the bridge records the default Windows microphone as 16 kHz PCM16 mono, with a 15-second cap. Recording starts only from this explicit control and only when `stt_url` is configured. The STT endpoint receives raw `audio/wav` and returns JSON `{ "text": "...", "confidence": 0.95 }`. Source audio is deleted after reading. Closing the session shuts down recording.

An existing STT client can bypass recording and POST its result to `/v1/player-input`:

```json
{"session_id":"from-context-ready","input_id":"unique-utterance-id","text":"Hello.","source":"stt","confidence":0.95}
```

For a text-only test use `source: "text"`. A duplicate input ID does not generate another reply. There is one active turn/delivery; input during playback is rejected until the game reports interruption/completion. The connector does not start a second microphone or implement a new recognizer.

## Screenshots and image-descriptor handoff

On conversation start, the bridge captures the foreground game's client area by process ID and saves PNG under `output/skyrim/screenshots/`. Payload metadata includes the file path, frame capture time, source event and `viewpoint: "player_camera"`. `image_description` is deliberately null. No VLM call or screenshot upload occurs. A failed/minimized/nonforeground capture does not block conversation data. Retention defaults to 100 frames; old frames may be removed, so downstream consumers must copy any frame they need to retain.

This first capture backend uses Windows GDI. Use borderless/windowed Skyrim; exclusive fullscreen, overlays or protected rendering can produce missing/black frames. That behavior needs an actual game check. Captured HUD/quest text is player-visible data and must not be promoted into NPC knowledge by a future descriptor.

## Existing pipeline smoke binding

Set `pipeline_mode: "preview"` to compose the existing `PreviewRunner` and configured provider profile. The default profile is scripted/offline; changing it to a live profile can make paid calls when the player submits input. It exercises the current canonical context subset only. It does not create production social memory, import knowledge automatically, or convert console acknowledgements into game-heard memory. Use external HTTP mode for the full pipeline's eventual input/output endpoints.

## Guarantees and limits

The handoff inbox stops admission at 4,096 retained event files; archive processed records explicitly. Its total storage budget is independent of the screenshot count limit.

Game object access is on the engine task thread; HTTP runs on a worker. Queues, requests, payloads, turns, microphone time, screenshots and output size are bounded. Commands carry session/NPC identity, state revision, delivery ID and start expiry. Native dedup prevents repeated polling from replaying speech. Combat/menu close/load changes stop output. Late callbacks are rejected; an expired command requests stop rather than assuming it was heard. Acknowledgements are best effort and do not establish word-level heard portions.

Offline tests use fake game/capture/model/device boundaries. They verify mapping, actor identity, visibility, context-before-turn, stale state, callbacks, duplicate/expired commands, file containment and cleanup. No real microphone, Skyrim launch or paid model call runs in these tests. Live readiness requires opening one conversation, checking exported topics/responses and frame, submitting one text/STT utterance, hearing/watching one response, and testing menu close/combat/load interruption.
