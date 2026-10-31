# Manual NPC lab

A standalone localhost interface for testing the existing NPC pipeline with four authored personas. UI/server code lives in `tools/npc_lab/`, public profiles in `fixtures/personas/npc_lab/`. The core package does not import or depend on this tool. No game installation is needed.

## Start and stop

After the project [setup](../SETUP.md), double-click **[run_npc_lab.bat](../run_npc_lab.bat)**. It finds the repo from its own path, uses `.venv`, opens your browser and starts the server at `http://127.0.0.1:8765`. Leave its terminal running. Press Ctrl+C in that terminal to stop it. A second copy cannot bind the same port; close the first or pass `--port 8767`.

The batch launcher defaults to **live Gemini**, reading `GEMINI_API_KEY` and `NPC_LLM_MODEL` from the existing local `.env`. Live messages send persona/player context to the configured API and can incur charges. No keys go to browser JavaScript. To use OpenRouter, supply its configured profile instead. The server reads the profile at startup; restart after changing model/key/profile files.

```powershell
.\run_npc_lab.bat
.\run_npc_lab.bat --offline
.\run_npc_lab.bat --realtime
.\run_npc_lab.bat --config configs/providers/openrouter.yaml
```

The module itself defaults to a deterministic fake, useful for offline UI testing:

```powershell
.\.venv\Scripts\python.exe -m tools.npc_lab --offline --open
.\.venv\Scripts\python.exe -m tools.npc_lab --live --open --config configs/providers/gemini.yaml
```

No extra requirements file, Node installation, frontend build, model download or GPU dependency is needed to use the lab. If the venv/config is missing, the launcher reports it instead of installing packages or inventing credentials.

## Use it

1. Select Mira (dry smith), Elin (warm innkeeper), Daren (reserved guard) or Iona (formal registrar).
2. Choose a relationship preset or change favourability, trust, familiarity, fear and irritation individually. Set mood, availability and whether the player has a drawn weapon. Closed service is unavailable for the guard, who has no service role.
3. Click a suggested question to fill the chat box, then Send. Enter sends; Shift+Enter adds a line. Ask the same question under different conditions to compare behavior.
4. Inspect the last-turn trace: resolved context, influences/exclusions, chosen plan, actual status/model, calls, usage and validation. `error_fallback` is distinct from `model_success`; the offline fake is explicitly labelled.
5. Use Reset/cancel to discard the visible test and request cancellation of an active turn. Controls lock while a turn is pending. Settings/profile changes clear the log so unrelated conditions are not mixed.
6. Export session downloads the current bounded trace as JSON. Export may contain everything you typed; review before sharing. The server does not automatically persist conversation logs.

**This is a single-turn lab.** Earlier messages appear in the browser log but are not supplied as conversation memory. Parameter changes never earn trust or alter a live game save. The UI retains at most 60 displayed messages and 30 exportable turn records. Reset clears these local records. There is no core memory implementation hidden inside this tool.

## Profiles and visuals

Profiles are structured JSON; see the [persona folder guide](../fixtures/personas/npc_lab/README.md). Identity, authored goals/style/boundaries and current motive go through existing canonical contracts. UI descriptions/testing notes are metadata, not extra secret knowledge or an alternative prompt engine. Restart after adding/editing profiles. Existing built-in portrait paths are a fixed whitelist; a new illustrated persona also needs an explicit portrait route.

Character images are original small SVG illustrations in `tools/npc_lab/web/portraits/`, with no animation/GPU render loop. A read-only check of the supplied Skyrim `Data` folder found `.bsa` archives and game plugins. No game mesh was extracted, copied or converted, and no Skyrim file was changed. This version is a 2D portrait console, not a 3D Skyrim viewer. Asset conversion remains separate optional work.

## Budgets and limits

Default quality-testing mode uses a **10-second development deadline**, 9,450 ms model cutoff and at most two calls including repair. `--realtime` uses the core's 3,000/2,450 ms timing. Both use a declared lab-specific **3,072-byte prompt cap**, because complete profiles plus controls measured 2,065–2,166 bytes before repairs. The core CLI's 2,048-byte default is unchanged. Output cap remains 160 tokens. Long inputs may still exceed the prompt cap and fall back; they are not silently truncated. The UI shows mode, timing and budget.

One reused runner and one persistent event loop retain the core admission/cancellation bounds. The single-user lab rejects overlapping turns rather than queueing them. HTTP workers are capped at eight and JSON bodies at 16 KB, with finite socket/call timeouts. Only fixed static routes are served. Loopback Host, same-origin POST and per-launch token checks guard the API. This standard-library server is a local developer tool, not a public service or the proposed production M09 API. Do not expose it on a LAN or deploy it as a game server.

The [behavior audit](reviews/2026-10-31-behavior-quality-audit.md) still applies: valid JSON is not proof of truth/persona quality. RAG, history, voluntary social silence, richer authored relationship behavior and game delivery remain core work. These profiles make differences easier to inspect; they do not certify that the model will obey every boundary.

## Verification

See the [implementation review](reviews/2026-10-31-manual-npc-lab.md). Offline regression: **196 tests passed**. Browser checks covered portrait loading, a fake chat turn, preset/profile reset and desktop/mobile layouts. A live Gemini request through the lab endpoint completed successfully; its plausible but unsupplied ambience details remain a recorded grounding limitation, not a successful semantic validation claim.
