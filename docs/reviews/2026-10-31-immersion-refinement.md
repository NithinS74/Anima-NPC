# Immersion refinement and private runtime consistency

2026-10-31. Deliberate self-review under the repository skills plus actual browser automation/screenshots. User asked for small, justified immersion improvements, not a redesign. Both requested remotes were confirmed current at 4cb1462 before implementation. Authenticated GitHub metadata confirmed the repository is private; the owner explicitly authorized the educational runtime bundle for collaborators. Repository visibility is unchanged.

## Review findings and decisions

- Baseline desktop computed typography: character names 14 px, suggested dialogue 13 px, camera controls 12 px, subtitle 25 px, footer 10 px. These sizes were too small for the requested immersive conversation. Increased primary names/dialogue/controls and subtitles while preserving the roster/stage/journal layout and exact-prompt inspector. Mobile remains checked for overflow. A mojibake suggestion chevron found in visual review was replaced with a safe CSS escape.
- Characters were still baked from the imported arm pose. Actual native shoulder/elbow joints permitted a modest arms-down adjustment, guarded against missing rigs/excessive rotations. Applied before evaluated mesh baking; facial targets are retained. All four character renders were inspected. This is a relaxed static pose, not a native idle/body-animation clip.
- Original SVG scenery did not satisfy the requested actual-game setting. An experimental mesh-only render was visually unsuitable and was removed, not shipped. The accepted backgrounds are actual Skyrim location screenshots for Warmaiden's, the Bannered Mare, Whiterun and Dragonsreach from UESP, with exact source/attribution metadata and hashes retained in the runtime archive. Iona's hall remains a visual stand-in for the fictional registry persona. Images are decorative settings, not new knowledge grants. Original illustrations are fallback-only.
- Requiring each teammate to reconstruct the same private assets caused avoidable discrepancies. Added one explicit, owner-approved Git LFS archive with per-file hashes. It contains only the runtime models/scenes/fonts and selected Piper engine/data/four voices, including original licence/config files. Credentials, player state, original game archives, tools, conversion sources and scratch outputs remain excluded. Upstream rights are retained; no general redistribution licence or public-release approval is claimed.

## Runtime bundle and setup

The archive contains **382 files**, **279.7 MiB compressed**, **313.2 MiB extracted**. It is staged as a **134-byte Git LFS pointer**, not an ordinary large Git blob. Setup hydrates pointers with Git LFS, verifies the archive and each member, bounds file counts/sizes, rejects unsafe paths and extracts atomically per file into the existing ignored media location. Package-managed files update; explicit local overrides are preserved. .env/player state are not extracted or overwritten.

An actual fresh destination installed all files offline, loaded all four models/scenes/voices and original fonts, synthesized a valid Piper WAV (**23,596 bytes**) from the extracted runtime, and passed an idempotent repeat. This proves the pack is self-contained on the tested Windows machine without referencing the original game installation at playback. A fresh remote-clone/setup check is the final publication check; its result is recorded below when complete.

## Checks and limits

- Full offline Python regression: **302 passed** (6.38 s); includes pose symmetry/invalid input, JPEG bounds/fallbacks, LFS hydration, managed updates/local overrides, unsafe paths, corrupt packs and extraction-size/checksum failures.
- Camera/facial JavaScript unit tests: **7 passed**.
- Existing UI and native-media bots exercised models, actual fonts, role scenes, central subtitles, camera/immersion controls, native blinking and Piper-driven speech movement, pause/disable/reduced-motion reset and mobile layout without overflow. Screenshots of all four relaxed models with actual game backgrounds were manually inspected. Automated checks support UI correctness; visual immersion is a self-review judgment, not an independent human score.
- Native facial timing remains approximate; no skeletal idle clips, phoneme alignment or alongside-game VRAM percentile is established. Core context/policy/generation were not redesigned. Recall/grounding and production game-adapter delivery remain separate gates.
- Matching runtime file hashes does not force identical LLM output or personal saved relationships. Each developer supplies their own API key/configuration. For a reproducible behavioral comparison use the same provider/model/settings, scenario and a fresh isolated --state-db; offline scripted mode is deterministic.

A final consistency audit added explicit `setup.bat --sync-media`: default setup preserves local work, while sync mode replaces only runtime media overrides with bundle versions and leaves credentials/player state untouched. The managed-update test now covers both behaviors.
