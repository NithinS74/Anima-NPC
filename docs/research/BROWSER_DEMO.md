# Browser testing and character demo feasibility

31 October 2026 | Documentation-based feasibility check; no asset import or viewer benchmark performed

## Recommendation

Use a browser scenario lab as the main test/demo interface. A character portrait, parameter controls and text/silence/cue output are straightforward additions to the already-planned FastAPI-served HTML/JS console. They exercise the actual system without Skyrim. Start there. A 3D avatar is optional presentation after the real pipeline works, not a realism/performance gate.

## Parameterized scenario lab

Select authored NPC/persona and world pack; set validated favourability, trust, familiarity, irritation/fear, location/time, role goal and availability; enter player text or replay a scenario. Apply settings to an explicit isolated test branch. Reset/replay restores the fixture; parameter edits cancel pending turns and increment the relevant revision/epoch. Controls never overwrite a live game NPC. Test-only state overrides are a local developer feature, not a game adapter permission.

Display character portrait/name, speech or deliberate silence, engagement cue and optional audio. Developer controls expose why the plan was chosen, knowledge used, token/call count, latency and relationship changes. Keep API keys and raw restricted knowledge on the backend; do not let HTML text become executable markup. Save scenario fixtures for repeatable before/after comparison.

The UI calls the same `/api/npc-turn` and delivery contracts as replay/game adapters; it does not implement a second orchestration pipeline. The browser can acknowledge display, which is distinct from proof that the user read/heard the line.

## Optional avatar path

If an already-compatible, permitted-to-use `.glb`/glTF asset is available, a small Three.js view can load it through [GLTFLoader](https://threejs.org/docs/pages/GLTFLoader). Existing animation clips can be played through [AnimationMixer](https://threejs.org/docs/pages/AnimationMixer). That establishes loader/animation feasibility; it does not guarantee a given character has suitable clips or facial expressions.

Humanoid VRM is another option: the [three-vrm examples](https://github.com/pixiv/three-vrm/blob/dev/packages/three-vrm/examples/index.html) demonstrate model loading, expressions, look-at and animations. VRM assets carry usage metadata and can have different permissions: [official license metadata reference](https://vrm.dev/en/vrm/meta/license/). Use a team-owned or explicitly permitted demo avatar, retaining its source/terms. No asset has yet been selected.

This is **not** automatic reuse of an installed Skyrim character. Game meshes/materials/skeletons require format conversion, asset permission checks and animation/rig compatibility work; this audit has not established a ready-to-use asset/export route. Do not make game extraction or retargeting part of the initial demo. Here "character model" can simply mean the persona/state definition, displayed with a portrait.

## Timebox and stop condition

After G2 works, allow one short prototype (at most one developer day) using one existing compatible avatar, one camera/light setup and any supplied idle clip. Map only existing supported cues; no rig authoring, motion capture, general retargeting or phoneme lip-sync. If the asset needs conversion, lacks usable animation or causes noticeable GPU cost, keep the portrait/text console. Do not spend the core evaluation milestone on animation.

When enabled, cap rendering at 30 FPS, limit pixel ratio/texture sizes and pause when hidden. Measure renderer-on/off frame time and memory, dispose replaced assets, and keep 3D disabled during core/game contention benchmarks unless explicitly testing it. A browser avatar can demonstrate expression and pacing, but does not prove real-game action compatibility.

## Implementation status

This request investigates feasibility and updates the plan. No website/viewer has been built, no model downloaded, no game asset copied and no new frontend/GPU dependency added. The console work is I09; optional avatar prototype is I16.
