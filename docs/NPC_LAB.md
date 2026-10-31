# Manual NPC lab

A separate localhost test room composing the existing core pipeline. Left: characters and test conditions. Centre: actual locally converted Skyrim models, game stone backdrop, and the text box directly below. Right: conversation, speech replay and inspectable reaction trace. UI, rendering and speech integration stay in `tools/npc_lab/`; core code never imports this tool.

## Start

Complete [setup](../SETUP.md), then double-click [run_npc_lab.bat](../run_npc_lab.bat). The launcher uses the project `.venv`, opens `http://127.0.0.1:8765` and defaults to live Gemini using local `.env`. Leave its terminal running; Ctrl+C stops it. Restart after changing provider settings. Keys stay in the backend. Live calls can incur charges.

```powershell
.\run_npc_lab.bat
.\run_npc_lab.bat --offline
.\run_npc_lab.bat --realtime
.\run_npc_lab.bat --config configs/providers/openrouter.yaml
.\run_npc_lab.bat --state-db output/npc_lab/experiment.sqlite3
```

The module entry point defaults to offline: `.\.venv\Scripts\python.exe -m tools.npc_lab --offline --open`. No frontend build, Node install, game installation or model downloads are needed for the basic illustrated lab. Optional 3D rendering uses browser GPU resources; it is not a measured alongside-game performance result.

## Conversations and parameters

Select a persona, type below the central character, and send. Relationships and mood now change from heard input and survive reload/restart in `data/npc_lab/state.sqlite3`. Each NPC has separate state for the lab player. The browser acknowledges displayed replies; the most recent eight exchanges are eligible as untrusted prompt memory, subject to the byte budget. Trace fields report history used/omitted. See [social-state rules](SOCIAL_STATE.md).

Sliders and presets are explicit, revision-checked debug overrides. Availability and drawn weapon are per-turn test conditions. They never change a game save. Clear/reset cancels pending work and clears the visible log; it **does not erase saved relationships or memory**. Use a separate `--state-db` for a fresh experiment. Export downloads bounded visible traces, which can contain your input; review before sharing.

Inspect the reaction path (stimulus, willingness, tone and route), score deltas, resolved context, validation, model calls and timings. This is an observable policy trace, not hidden model reasoning. The fake provider is labelled. Valid JSON does not establish truth or realism.

## Actual models and voices

The local installation was selectively read and converted; no game files were modified. The stage uses real Skyrim mesh/texture data with these explicit appearance mappings:

| Persona | Appearance |
|---|---|
| Mira | Adrianne Avenicci, blacksmith outfit |
| Elin | Hulda, barkeeper outfit |
| Daren | Farkas face, assembled Skyrim guard kit |
| Iona | Lydia, iron outfit; visual stand-in for the station persona |

These are static assembled rest poses, with simplified portable materials/body-weight assembly. They do not reproduce the current modded game appearance exactly. No idle animation or lip sync is implemented. Appearance does not grant Skyrim memories or lore to the fictional personas.

Copied Mantella Piper voices are selected per profile. Text is displayed before synthesis; automatic speech and replay use only validated server-recorded responses. Voice is local, separate from LLM generation, and explicitly unavailable if assets are missing. No OS voice substitutes for Mantella. Measured local browser probes synthesized short replies in approximately 0.8-1.0 seconds; cold starts can take longer.

Game assets, converted models, voices and executables are local and ignored under `assets/private/npc_lab/` and `.tools/`. They are **not pushed**. Teammates without those assets get original illustrated portraits and no voice. See [media setup](../configs/npc_lab/README.md) for reproducible commands and source versions.

## Bounds and verification

Development mode: 10,000 ms response deadline, 9,450 ms model cutoff, at most two calls including repair. `--realtime`: 3,000/2,450 ms. Lab prompt cap: 3,072 UTF-8 bytes; core CLI default remains 2,048. Whole exchanges are omitted when necessary; current input/identity are not silently truncated. Output cap remains 160 tokens. These are configured bounds, not successful model latency percentiles.

One runner/event loop, no turn queue, at most eight HTTP workers, 16 KB JSON bodies, finite socket timeouts. Loopback Host/Origin and launch-token checks protect POSTs. Fixed media routes, bounded self-contained GLB validation, 30 FPS rendering cap, hidden-tab pause and resource disposal limit optional viewer work. Speech permits one subprocess at a time with timeout/cancellation and validated bounded WAV output. This local standard-library server is not a production public API.

Latest [self-review and evidence](reviews/2026-10-31-social-state-character-stage.md): 254 offline tests passed, four actual models visually inspected, desktop/mobile layout and reload/escalation/audio checks exercised. Two live Gemini memory requests fell back (timeout, HTTP error); the second packed one prior exchange. Successful live model recall, semantic grounding, production delivery and game-resource targets remain unverified. RAG is not implemented.
