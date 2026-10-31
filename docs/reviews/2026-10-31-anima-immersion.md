# Anima immersion and context-flow review

2026-10-31. Self-review under the repository development/design-review skills, plus automated interaction with an actual browser and manual inspection of captured renders. No independent reviewer is claimed. [Plan and scope correction](../plans/ANIMA-immersive-app.md). Backup **b102c3d** was tested and pushed to both branch/main before implementation. User clarified hosting/accounts are later; none were added.

Verdict: **go for local Anima/system experimentation; conditional go for the next game-adapter integration slice**. Not signed off as a human simulation, complete game integration or online service.

## Findings resolved

| Severity | Finding and correction | Evidence |
|---|---|---|
| High | Prompt inspection previously required guessing/rebuilding the input. Task-local [provider capture](../../tools/npc_lab/diagnostics.py) now records exact packages at invocation, separately for initial/repair calls; no-call routes show no prompt. No keys/headers are recorded. | Exact equality against the receiving provider, concurrent-task isolation, authored/no-call and repair tests in [diagnostic tests](../../tests/unit/lab/test_diagnostics.py). |
| High | Live repair returned dialogue/actions or dialogue_response instead of the canonical response schema. [Prompt builder](../../src/npc/generation/prompt.py) now shows a literal four-field JSON shape and keeps persona/schema/repair guidance together in one complete system message; it also states sentence/word limits in prose. | Captured rejected candidates reproduced the problem. Later live short-stranger turn recovered via repair; validation remained strict and two-call bounded. |
| Medium | Recognition/trust stance/service obligation were mainly implied by scores/influence names. Added their explicit resolved values to the model context, while omitting redundant labels to preserve budgets. | Paired stranger/guarded versus familiar/trusting prompt checks; full regression retains budget/secret-exclusion tests. |
| Medium | Adding context/schema text overflowed the existing 2,048-byte repair fixture. Compacted duplicate labels and instructions rather than increasing the core cap or weakening the test. | Original repair-budget regression passes with persona, schema, user data and safe repair guidance intact. |
| Medium | Far-away full-body framing and a uniformly green palette weakened the requested conversation experience. [Stage](../../tools/npc_lab/web/stage.js), [camera](../../tools/npc_lab/web/camera.mjs), and [UI](../../tools/npc_lab/web/index.html) now use close/full-figure views, bounded zoom, neutral/warm lighting, charcoal/ivory/amber styling and central subtitles. | Four actual local model appearances rendered and visually reviewed, desktop/mobile screenshots, camera unit tests. |
| Low | Debug labels in the scene interrupted immersion. Moved detailed context/prompt/trace to an explicit inspector, collapsed overrides, retained an optional journal and added immersive mode. | UI bot checks tabs, exact input, subtitles, view controls, keyboard/normal immersion, mobile overflow and browser errors. |

## Context-to-response audit

| Input | Implemented effect and route | Remaining limit |
|---|---|---|
| NPC identity, occupation, role, goals/style/boundaries | Canonical Persona -> context influences -> policy/compact prompt; disclosure boundary persists regardless of friendliness. | Occupation does not prove procedures/lore; semantic compliance remains evaluated separately. |
| Patience/assertiveness/warmth/caution/swearing | Appraisal, threat/willingness, authored boundaries, affect, generation disposition and permitted profanity. | English heuristic rules, not a learned emotional model. |
| Directed player standing | Favourability/trust/familiarity/fear/irritation retained separately, persisted by scope; recognition/trust stance explicit in the prompt. | Faction hierarchy, player rank/reputation and richer social norms require explicit future contracts/input; no hidden invented values. |
| Current NPC status and observed setting | Freshness/perceiver/scope filtering -> availability/threat/mood/current goal with source dependencies; combat/drawn weapon/service closure can dominate affection. | Real adapters must provide trustworthy timestamps/perception; current UI supplies controlled fixtures. |
| Player utterance | Untrusted data; recognized insults/threats/apologies/banter change social state once and can route to a brief boundary/end without a model. | Negation/sarcasm/indirect abuse/language coverage are not solved. |
| Earlier dialogue | Last eight acknowledged displayed exchanges, bounded whole-exchange packing and omission counts. May be recalled as what was said, never world proof. | Long-term memory absent; even packed relevant history does not guarantee the LLM uses it correctly. |
| Selected plan | Route, affect, knowledge need, brevity/mode/cue limits; structural validation, revision checks and bounded repair. | Valid fields/evidence IDs do not establish semantic entailment or realistic psychology. |

The inspector's **impact map** renders these implemented influences/dependencies and their source IDs. It is an observable appraisal map, not a claim to reproduce hidden human reasoning. Core code imports no UI/media diagnostics; Anima composes the same existing runtime.

## Verification

- Full offline Python suite: **269 passed** (7.54 s); final command `.\.venv\Scripts\python.exe -m pytest -q`.
- Node built-in camera unit tests: **3 passed**; `node --test tests/ui/camera.test.mjs`. JavaScript syntax checks passed. No npm dependency/build introduced.
- `pip check`: no broken requirements; no dependency additions for the redesign.
- UI bot: Anima branding/local fonts; zoom and close/full-figure views; fake chat turn and matching central subtitle; 20 impact cards in the sample; actual provider input visible; immersive mode and mobile layout without horizontal overflow; no browser errors. Four local game-derived model appearances and game backdrop checked separately. Screenshots were inspected, including desktop/mobile, immersive view, prompt and impact panels, and Daren's close framing. Optional browser script is [tests/ui/anima-browser.cjs](../../tests/ui/anima-browser.cjs); instructions in [Anima guide](../ANIMA.md).
- Live initial diagnostics found two-sentence guard responses plus malformed repair schemas. After the correction, the final isolated sample returned **repair_success**, one valid 13-word/one-sentence guard reply, **2 calls / 2,907 ms**, with both actual prompts captured. Follow-up returned model_success in **3,031 ms**, one call, with one prior exchange packed, but did not acknowledge the remembered name. These tiny samples prove neither latency percentiles nor reliable recall/persona quality. The strict validation/fallback path remains necessary.
- One HTTP smoke attempt met a 409 conflict; subsequent live checks used isolated state rather than overwrite a concurrently active user's conversation. No successful game delivery is claimed.

## Facial animation and remaining integration gate

Read-only BSA inspection found installed femalehead/malehead/eye TRI files. PyNifly's [official repository](https://github.com/BadDogSkyrim/PyNifly) and [morph documentation](https://baddogskyrim.github.io/BethesdaLibrary/file-formats/morphs-shapekeys/) describe expression morphs. The current local [exporter](../../tools/npc_lab/blender_export.py) intentionally freezes geometry and exports with animation/skins/morphs disabled. Applying TRI deltas to each specific FaceGen head and preserving them into glTF would be a separate topology/conversion/timing experiment, not a simple plug-in reuse. Deferred under the user's optional/easy-only condition; no native facial animation or lip sync was fabricated.

Next integration work should replay/capture actual game inputs through the canonical contracts, compare the impact map/prompt against source game observations, then verify adapter delivery/acknowledgement and interruptions. The standalone companion does not provide those adapter guarantees. Keep hosting, account systems and distributed infrastructure deferred. Private Skyrim/voice assets remain ignored; only application source, public fixtures/configuration and openly licensed fonts are publishable.
