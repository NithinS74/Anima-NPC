# Teammate setup, role scenes and native facial media review

2026-10-31. Self-review following the repository development/design-review skills and [reviewed plan](../plans/ANIMA-setup-scenes-faces.md). Both remotes were confirmed current at 8cf8b6e before work. No independent review or production game-integration sign-off is claimed.

Verdict: **go for teammate setup and local companion/media testing**. Core realism, reliable recall, game adapter delivery, full-body animation and phoneme-aligned lip sync remain separate gates.

## Setup audit and fixes

The earlier manual commands were valid but insufficiently direct for a new teammate: Python selection, venv setup, editable install, blank-key configuration and offline versus live launch were scattered. [SETUP.md](../../SETUP.md) now leads with clone -> setup.bat -> run_anima.bat --offline, with prerequisites, live-key setup, optional private media and troubleshooting separated.

[setup.bat](../../setup.bat) discovers Python 3.11 and calls the stdlib-only [bootstrap](../../scripts/setup_environment.py). It creates/reuses .venv, rejects incomplete/incompatible environments without deletion, installs the single requirements file and editable package, checks dependencies, exclusively seeds .env only when absent and runs offline regression. Existing keys/data are preserved. It does not install a global runtime, import game data, make paid calls or require Node/Chrome/GPU. Double-click keeps results visible; --no-pause returns immediately for automation. The user requested only run_anima.bat, so the old NPC Lab launcher is removed and current links were updated.

Evidence: a fresh public-files-only checkout in an ignored temporary folder had no venv, API key or private assets. setup.bat created the environment and passed all **272** tests present in that initial snapshot. The updated repeat run passed **283** tests, preserved .env byte-for-byte and launched an offline app with all public scenes and no game assets. One further setup guard test was then added; final root regression passes **284** tests. This distinguishes actual installation evidence from later test additions. Setup/version/failure/credential-preservation unit cases are in [setup tests](../../tests/unit/test_setup_environment.py).

## Native facial morph experiment and implementation

Read-only extraction used installed vanilla Skyrim SE BSA entries and the already verified PyNifly 30.2.0/Blender 4.5.9 tooling. Actual FaceGen heads had **996 female / 898 male vertices** and eyes **176 female / 186 male vertices**; triangle connectivity matched their native TRI sources for all four profiles. Head/eye/mouth/brow matches were checked before transferring deltas. The specific NPC base face remains the basis; no generic replacement face is substituted.

The [offline converter](../../tools/npc_lab/blender_export.py) now optionally retains a small native morph allowlist, applies transforms consistently when baking the assembled pose and exports morph targets. [Topology/displacement checks](../../tools/npc_lab/face_import.py) reject mismatched connectivity, invalid indices, nonfinite or excessive deltas. Native import is explicit with --facial; ordinary static import remains supported. GLB is written to a temporary path, checked for size/self-containment and atomically replaces the previous model. Converted sizes: Mira **7,475,584**, Elin **7,126,932**, Daren **12,357,392**, Iona **8,860,608 bytes**; four facial parts are present in each.

The browser [controller](../../tools/npc_lab/web/facial.mjs) uses native BlinkLeft/BlinkRight, Aah/Oh/BMP and mood targets. Timing is app-driven: idle blinking and simple playback-time speech movement, not captured Skyrim clips, audio phoneme analysis or full skeletal animation. The existing capped renderer only redraws changed weights. Stop/pause/end disables mouth movement; character changes/disposal reset state; the Expressions toggle and reduced-motion preference reset weights. Hidden tabs retain the existing paused-render boundary. Source game files are unchanged; all geometry/morphs remain private.

Actual isolated browser/Piper test observed native blink weights, angry mood weights and changing mouth weights during WAV playback, then verified zero speech weights on pause and all-zero weights for disabled/reduced-motion state. Blink, expression and speaking screenshots were visually inspected, along with all four character/scene renders and mobile layout. Daren's helmet obscures much of the face; body pose/material/FaceGen conversion limitations remain. No exact speech synchronization or game-frame performance claim is made.

## Fonts and backgrounds

The old Cinzel/Barlow pairing was **not** Skyrim's font. The installed fontconfig explicitly maps DialogueFont to **Futura CondensedLight**. Official portable FFDec **26.4.0** and the installed Java runtime extracted the embedded font from the privately copied fonts_en.swf. [Font importer](../../tools/npc_lab/import_font.py) privately selects dialogue/interface fonts, validates their bounded sfnt headers and records source/hashes. The fixed server routes expose only these known local files. Browser verification confirmed the AnimaSkyrimDialogue font was loaded; screenshots show the original glyphs. Nothing is installed as a system font or published to Git. Missing/private-font failures retain the licensed public fallback and explicit inspector status.

Four original public SVG environments now distinguish **forge, inn, village gate and registry**. Fixed persona IDs select them, unknown IDs fall back safely, and scene routes are allowlisted. They are authored role illustrations, not screenshots taken from Skyrim. Media/HTTP tests cover distinct scenes, missing fonts, path/size/header failures and fixed routes. Font-import unit tests run without Java/game assets.

## Final checks

- Full default Python regression: **284 passed** (6.20 s), .venv interpreter.
- Camera/facial Node built-in tests: **7 passed**. No npm dependencies added.
- Fresh setup and idempotent repeat: successful; configuration hash unchanged; public-only offline app smoke passed.
- Existing Anima UI bot passed, now rendering the locally imported Skyrim font. Native-media bot passed all four scenes/models, real morphs, actual Piper-driven speech motion, pause/disable/reduced-motion reset and mobile overflow checks; no browser errors. Source: [media bot](../../tests/ui/anima-media-browser.cjs).
- Dependency, documentation-link, syntax, bundled-font/vendor integrity and private-asset/credential publication checks passed. Real batch failure/unknown-option cases returned exit 1/2 without creating partial environment/config files. No requirements pin changes were needed.

Remaining limits: private assets cannot be reconstructed from a Git checkout alone; teammates need their own game/Mantella installation and optional portable tools for identical visuals. Core setup is independent of these assets. Runtime is still loopback-only; no hosting/account system was added. Native shape reuse improves presentation but establishes neither human-like NPC reasoning nor reliable game delivery.
