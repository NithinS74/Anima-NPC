# Anima

Anima is the local conversation companion for testing the game-independent NPC system. It is a separate application surface, not a second context engine. Online hosting is future scope, following the user's clarification; this change adds no accounts or deployment infrastructure.

## Start

Complete [setup](../SETUP.md), then double-click [run_anima.bat](../run_anima.bat). It uses the existing `.venv`, loads provider settings from local `.env`, and opens `http://127.0.0.1:8765`. The batch defaults to live API calls, which may incur charges. Leave its terminal running; Ctrl+C stops it. Restart after changing provider configuration and refresh the browser after restarting. The old `run_npc_lab.bat` forwards to the new launcher.

```powershell
.\run_anima.bat
.\run_anima.bat --offline
.\run_anima.bat --realtime
.\run_anima.bat --development-timeout 60
.\run_anima.bat --state-db output/npc_lab/fresh-encounter.sqlite3
```

Manual-testing mode defaults to 30,000 ms response deadline / 29,450 ms model cutoff, with at most two calls including repair. `--realtime` preserves the core's 3,000/2,450 ms limits. Lab prompts remain bounded to 3,072 UTF-8 bytes, output to 160 tokens; the core CLI defaults remain unchanged. Fake/offline mode is labelled and is not a model-quality experiment.

## A conversation, rather than a dashboard

Choose a character from the left. Conversation framing brings their upper body/face closer; Full figure restores a wider view. Plus/minus changes the camera zoom with safe bounds. Drag the model to rotate. Use **Immerse** (or I while focus is outside a form) to hide side panels; the same header button returns to the normal layout. Journal independently toggles the conversation log. Mobile keeps the character/subtitles/input together, with a compact roster.

The current reply appears bottom-centre above the input, in a game-inspired subtitle treatment. Enter sends; Shift+Enter adds a line. Voice uses the existing installed Mantella Piper integration; replies appear before audio synthesis finishes. Voice can be muted and replayed. No facial lip sync is claimed. Anima's ivory/charcoal/amber palette and locally bundled Cinzel/Barlow Condensed fonts are stylistic choices under retained open-font licences; no proprietary Skyrim font is redistributed.

The four public fictional [personas](../fixtures/personas/npc_lab/README.md) remain distinct from their optional game-derived appearances. Local mapping: Mira/Adrianne, Elin/Hulda, Daren/Farkas in a guard kit, Iona/Lydia as a station-persona visual stand-in. See [private media setup](../configs/npc_lab/README.md). Without private assets, original illustrations work; voices are explicitly unavailable. Model/voice assets are not pushed and no game save is changed.

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

## Facial animation feasibility

Installed Skyrim archives contain head/eye `.tri` morph data. [PyNifly](https://github.com/BadDogSkyrim/PyNifly) supports expression TRI morphs; see its [morph documentation](https://baddogskyrim.github.io/BethesdaLibrary/file-formats/morphs-shapekeys/). The current converter bakes static geometry and disables skins, morphs and animation. Applying native expressions to these particular FaceGen heads requires topology-compatible morph transfer, eye/mouth handling, morph-preserving glTF export and expression/speech timing. Finding the files does not establish a working conversion. It is not a plug-in change, so it is deferred under the user's 'only if easy' condition. No procedural head bob is presented as a Skyrim facial animation.

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
