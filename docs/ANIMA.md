# Anima

Anima is the local conversation companion for testing the game-independent NPC system. It is a separate application surface, not a second context engine. Online hosting is future scope, following the user's clarification; this change adds no accounts or deployment infrastructure.

## Start

After installing Python 3.11, Git and Git LFS (see [setup](../SETUP.md)), double-click [run_anima.bat](../run_anima.bat). It checks the local installation, runs setup automatically if needed, loads provider settings from local `.env`, and opens `http://127.0.0.1:8765`. The batch uses valid live configuration (may incur charges), otherwise a clearly labelled scripted offline preview. `--live` requires valid settings; `--offline` explicitly selects scripted responses. Leave its terminal running; Ctrl+C stops it. Restart after changing provider configuration and refresh the browser after restarting. `run_anima.bat` is the only application launcher; the earlier NPC Lab launcher was removed at the user's request.

```powershell
.\run_anima.bat
.\run_anima.bat --offline
.\run_anima.bat --realtime
.\run_anima.bat --development-timeout 60
.\run_anima.bat --state-db output/npc_lab/fresh-encounter.sqlite3
.\run_anima.bat --offline --rag-config configs/rag/dialogue.example.json --cv-url http://127.0.0.1:8000
```

Manual-testing mode defaults to 30,000 ms response deadline / 29,450 ms model cutoff, with at most two calls including repair. `--realtime` preserves the core's 3,000/2,450 ms limits. Lab prompts remain bounded to 3,072 UTF-8 bytes, output to 160 tokens; the core CLI defaults remain unchanged. Fake/offline mode is labelled and is not a model-quality experiment.

## Optional Skyrim CV reference

Run the standalone CV backend separately on loopback (`http://127.0.0.1:8000`), then pass `--cv-url http://127.0.0.1:8000` to Anima. The **Optional visual reference** control accepts a manually chosen PNG/JPEG (up to 10 MiB), forwards it through Anima's authenticated loopback bridge, and shows the compact returned descriptor. Checking **Attach** sends that descriptor to the next provider call as `untrusted_visual_reference`. The CV bridge allows 120 seconds by default because the first local VLM pass can be slow; override it with `--cv-timeout 1..180` when needed.

This is a manual developer/testing bridge. The descriptor is kept only in the lab process, is not written to social state, and can be cleared before a turn. It is deliberately not converted to `ObservedFact`, model evidence, NPC knowledge, identity, action, current game state, HUD text, or hidden information. A player-camera screenshot has no established NPC-visibility mapping; Anima instructs the provider to preserve uncertainty and use it only for cautious visible-detail wording. CV failures leave ordinary turns available. Offline scripted replies do not demonstrate visual grounding; inspect the LLM input or use a configured live provider to see the attached descriptor reach the model.

## A conversation, rather than a dashboard

Choose a character from the left. Conversation framing brings their upper body/face closer; Full figure restores a wider view. Plus/minus changes the camera zoom with safe bounds. Drag the model to rotate. Use **Immerse** (or I while focus is outside a form) to hide side panels; the same header button returns to the normal layout. Journal independently toggles the conversation log. Mobile keeps the character/subtitles/input together, with a compact roster.

The current reply appears bottom-centre above the input, in a game-inspired subtitle treatment. Enter sends; Shift+Enter adds a line. Voice uses the existing installed Mantella Piper integration; replies appear before audio synthesis finishes. Voice can be muted and replayed. Models imported with `--facial` reuse original head/eye/mouth/brow shapes for blinking, simple mood and speech movement. Timing follows playback approximately; it is not phoneme-accurate lip sync. Anima uses actual in-game screenshot backgrounds from Warmaiden's, the Bannered Mare, Whiterun and Dragonsreach, with an illustrated fallback when the runtime pack is absent. Bundled Cinzel/Barlow Condensed fonts are open-font fallbacks. When imported locally, the actual Skyrim Futura dialogue/interface fonts take over; the inspector reports which source is active. The owner-approved fonts are supplied inside the private project runtime pack; no repository visibility change was made.

The four public fictional [personas](../fixtures/personas/npc_lab/README.md) remain distinct from their optional game-derived appearances. Local mapping: Mira/Adrianne, Elin/Hulda, Daren/Farkas in a guard kit, Iona/Lydia as a station-persona visual stand-in. See [private media setup](../configs/npc_lab/README.md). Without private assets, original illustrations work; voices are explicitly unavailable. The required model/voice/font/scene runtime assets are supplied through the private repository's Git LFS pack; raw conversion sources and saved user data stay excluded. No game save is changed.

## Standing, memory and inspection

**Shape the encounter** expands scenario controls. Sliders/presets are explicit revision-checked overrides; they do not overwrite automatic state on every turn. Heard insults/threats/apologies and other recognized input change directed relationship/mood under the [social-state rules](SOCIAL_STATE.md). Saved state and the last eight acknowledged displayed exchanges survive restart/reload; prompt packing may omit whole older exchanges. Clear view does not erase durable state. Use an isolated `--state-db` for a clean experiment.

**Inspect context** opens three views:

- **Impact map:** authored role/temperament, standing, eligible world/NPC state, willingness/tone, influence effects and their source IDs, resolved dependencies, selected route and response limits.
- **LLM input:** the actual provider-bound messages and public generation settings for each call, including a separate captured repair attempt. Authored/silent/no-call turns explicitly show no LLM input. This is captured at invocation, not reconstructed later. Keys, authorization headers and provider response bodies are excluded.
- **Full trace:** canonical context, plan, validation, state delta and timings. Player/history remain untrusted data, not verified world facts. These are observable policy records, not hidden model reasoning.

Export writes a bounded conversation/trace file and can include everything you typed and the captured prompt. Review exports before sharing.

## Boundaries and current quality

Stable internal paths (`tools/npc_lab`, `configs/npc_lab`, `fixtures/personas/npc_lab`, and existing local storage) are retained for teammate compatibility; the product/launcher is Anima. UI/rendering/speech/diagnostics stay outside `src/npc`. Core context adds explicit recognition/trust/service duty in the prompt, while full provenance stays in canonical context and the inspector. Redundant labels are omitted to preserve budgets. Every model attempt uses one complete system message containing the response shape, persona and safe repair guidance.

This is still a loopback-only companion. Hosting, multi-user accounts, production game input/output, RAG, semantic entailment and complete long-term memory are not implemented by this UI change. Tests demonstrate implemented context effects, not a complete model of human psychology. Live checks found and fixed schema/repair issues, but recall quality still varies. See the [self-review and UI evidence](reviews/2026-10-31-anima-immersion.md).

## Native facial expressions

The follow-up conversion experiment verified matching head/eye topology for every profile and now preserves native Skyrim blink, speech and mood shapes, including matching mouth/brow components. Use `--facial` in the [optional importer](../configs/npc_lab/README.md). The browser uses those real morph targets with simple app-driven timing; the body uses a relaxed arms-down static pose. Expressions can be toggled, honour reduced-motion preferences, pause in hidden tabs, and speech motion returns to neutral when audio stops. This is not a native Skyrim animation-clip player or phoneme lip-sync implementation. See [verification](reviews/2026-10-31-setup-native-faces.md).

## Repeat the UI checks

Python regression: `.\.venv\Scripts\python.exe -m pytest -q`. Camera unit tests: `node --test tests/ui/camera.test.mjs` (optional Node 22+, no npm dependencies). Browser checks use an isolated offline database and Chrome profile, never a signed-in personal profile. Start the app in a separate terminal:

```powershell
.\run_anima.bat --offline --port 8766 --state-db output/npc_lab/ui-check.sqlite3
```

Launch an isolated Chrome with remote debugging and the test URL; update the executable path if needed:

```powershell
$animaProfile = Join-Path (Get-Location) 'tmp/anima-ui-browser'
Start-Process -FilePath 'C:/Program Files/Google/Chrome/Application/chrome.exe' -ArgumentList @('--headless=new','--no-first-run','--no-default-browser-check','--remote-debugging-port=9223',('--user-data-dir="' + $animaProfile + '"'),'http://127.0.0.1:8766') -WindowStyle Hidden
node tests/ui/anima-browser.cjs
```

The opt-in bot submits dialogue, asserts offline mode, checks camera/subtitles/inspector/immersion/mobile overflow and captures screenshots under ignored `output/screenshots/`. It uses an actual local model where configured. Inspect screenshots as well as the automated assertions. Stop the isolated browser/test server after review. No paid call is part of default regression.

Optional private-media UI verification: `node tests/ui/anima-media-browser.cjs`, using the same isolated offline browser/server setup. Unlike the basic UI check, this requires imported game fonts, native-morph models and local Piper assets. It checks four scenes/models, blink/mood/speech movement, pause/reduced-motion reset and mobile overflow. It makes no LLM API calls. Current setup/media review: [results](reviews/2026-10-31-setup-native-faces.md).

The [latest immersion review](reviews/2026-10-31-immersion-refinement.md) records the measured text-size changes, actual screenshot selection, relaxed native-rig posing and runtime bundle test. `setup.bat` verifies and installs the private LFS archive automatically. It preserves explicit local overrides and needs no game installation for the provided media. Rebuild commands can use `--facial --relaxed`.
