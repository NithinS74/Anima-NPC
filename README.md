# Anima

A game-independent orchestration system for believable NPC interactions. The system decides whether an NPC engages, what they know, and how they respond before asking a replaceable language model to express the response.

The independent [Skyrim connector](docs/SKYRIM_CONNECTOR.md) connects SKSE game context/screenshots through optional local VLM, scoped RAG, NPC generation/validation and native text/audio delivery. Start `run_cv.bat`, then `run_skyrim_connector.bat --cv-url http://127.0.0.1:8000`; add `--attach-visual-reference` to include the untrusted descriptor in prompts. The default provider is scripted/offline; Whisper STT prepares automatically on CPU; run `setup_chatterbox.bat` once for automatic Chatterbox Turbo TTS and local NPC voice references. It has no Mantella runtime dependency. Offline checks do not establish live Skyrim/model compatibility; consult the guide and [integration review](docs/reviews/2026-11-02-skyrim-vision-pipeline.md).

**Status:** context building and a generation/validation scenario preview are implemented and tested offline. The preview adds deterministic engagement rules, replaceable API generation, strict output checks and bounded repair. A [live Gemini sample](docs/reviews/2026-10-31-behavior-quality-audit.md) confirmed integration but exposed grounding, social-policy and latency gaps; realism is not signed off. A small [OpenRouter/Nemotron diagnostic](docs/reviews/2026-11-01-openrouter-output-budget.md) also verified answer text with reasoning disabled; response quality remains unverified. The full game pipeline is not yet implemented; local inference is a later option.

Install Python 3.11, Git and Git LFS, clone the repository, then start **[run_anima.bat](run_anima.bat)**. It automatically runs setup when dependencies or shared runtime media are missing/outdated; `--offline` uses scripted responses. Run **[setup.bat](setup.bat)** explicitly to request a safe source update. Setup creates/reuses the venv, preserves `.env`, installs the single requirements file and runs regression. See [setup](SETUP.md), the [general TRD](docs/TRD.md) and the [implementation backlog](docs/BACKLOG.md). The [documentation index](docs/README.md) links contracts, module TRDs, research and reviews.

| Location | Purpose |
|---|---|
| `src/npc/` | Runtime modules and contracts; game adapters have separate owners |
| `tests/` | Unit, contract and offline integration regression |
| `fixtures/` | Shared public worlds, scenarios and labelled evaluation data |
| `configs/` | Public authored settings; credentials stay in local `.env` |
| `scripts/` | Thin setup/maintenance/developer entry points |
| `tools/npc_lab/` | Separate local browser interface for manual NPC tests |
| `benchmarks/` | Quality, latency and game-resource measurement harnesses |
| `docs/` | Requirements, decisions, workflow, research and reviews |
| `.agents/skills/` | Development and design-review workflows |
| `Knowledge base/kb/` | User corpus; check privacy/licensing before tracking files |

See the [repository structure guide](docs/REPOSITORY_STRUCTURE.md) for the tree and module ownership. Remaining empty directories contain `.gitkeep`; they are not working components. Local environments, scratch files and runtime output are ignored.

Try the [offline context preview](docs/CONTEXT_BUILDER.md) after [setup](SETUP.md):

```powershell
.\.venv\Scripts\python.exe -m npc.context fixtures/scenarios/smith_closing.json
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json
.\.venv\Scripts\python.exe -m pytest
```

The context command explains response influences. The runtime command exercises generation/validation using a fake provider by default. See the [generation guide](docs/GENERATION_VALIDATION.md) for **OpenRouter/Gemini configuration and live commands**. An initial [persistent social-state slice](docs/SOCIAL_STATE.md) is implemented; An internal [local RAG component](docs/RAG_INTEGRATION.md) now owns ingestion, CPU embeddings and scoped dialogue retrieval inside NPC-main; full M05 authorization and production game delivery remain planned. Skyrim/Mantella remains a best-effort reference adapter.

For **manual testing in a chat box**, double-click [run_anima.bat](run_anima.bat). It opens the separate localhost [Anima companion](docs/ANIMA.md) using valid Gemini configuration from `.env`, or a clearly labelled scripted preview when configuration is absent; pass `--offline` to require the fake or `--live` to require API configuration. Four [authored personas](fixtures/personas/npc_lab/README.md), persistent relationship reactions, bounded displayed-conversation memory, trace inspection and export are included. Characters sit on the left; the central model has the text box below. Optional local Skyrim models, a game backdrop and copied Mantella voices are available through [media setup](configs/npc_lab/README.md); the owner-approved runtime media archive is now included via Git LFS in this private repository. Raw game/conversion files remain ignored. The basic illustrated UI works without Skyrim and stays separate from core deployment. See the [current setup/media review](docs/reviews/2026-10-31-setup-native-faces.md); reliable recall and human realism are still not signed off.

## Optional Skyrim CV → Context Builder workflow

The included standalone [CV service](cv/README.md) feeds its validated `scene_descriptor` JSON into Anima's **Context Builder** as an optional `Situation.visual_context`. Install it once with `cv\\setupcv.bat`, then start both local services:

```powershell
# Terminal 1 — repository root: Skyrim CV service
cd C:\path\to\Anima-NPC
.\run_cv.bat

# Terminal 2 — repository root: Anima
cd C:\path\to\Anima-NPC
.\run_anima.bat --offline --rag-config configs/rag/dialogue.example.json --cv-url http://127.0.0.1:8000
```

In Anima, expand **Shape the encounter**, choose a PNG/JPEG under **Optional visual reference**, click **Analyze scene**, then check **Attach to next turn**. The bridge sends the image to the local CV API, normalizes the returned Scene Descriptor, and passes it to `build_situation(...)`. Open **Inspect context** to view `context.visual_context`; the exact provider input includes it as `untrusted_visual_reference`.

This is intentionally not a canonical `ObservedFact`: a manually selected player-camera screenshot does not establish what a particular NPC can see. Therefore it does not change availability, combat/threat, relationships, RAG eligibility, durable memory, identity, quest state, or other trusted context. The model receives it only as uncertain visual reference; its uncertainty/provenance are preserved. If CV is unavailable, leave it unattached and normal dialogue continues. See [Anima](docs/ANIMA.md) and [the integration plan](docs/plans/I10-local-cv-bridge.md).

For every component, follow **plan -> review plan -> implement with unit tests -> review change -> run regression**. Read the [development skill](.agents/skills/develop-npc-component/SKILL.md) yourself or ask your agent:

```text
Use $develop-npc-component to implement <issue/component>.
```

If your agent does not discover repository skills, ask it to read `.agents/skills/develop-npc-component/SKILL.md` explicitly. [AGENTS.md](AGENTS.md) routes repository-aware agents to the same workflow. The skill requires meaningful unit tests for each working component and applicable regression checks before readiness; reviews and passing checks must be reported honestly.

Create a separate branch for each task, named `feature/<issue-id>-<short-name>` (for example, `feature/I05-rag-ingestion`). Start from an up-to-date `main`, commit and push your branch, then open a **pull request targeting `main`**. Include the linked issue, changes, review findings and unit/regression test results; request a teammate review. Merge only after review approval and required checks pass. Do not push implementation changes directly to `main`. See the [team workflow](docs/TEAM_WORKFLOW.md) for details.

Repository: https://github.com/mohanchandrass/NPC

Anima includes close/full-figure camera views and zoom, centred subtitles, an immersive view, and **Inspect context** for the impact map and exact provider-bound inputs (including repairs). The [latest self-review](docs/reviews/2026-10-31-anima-immersion.md) records UI-bot, regression and live findings. Optional native facial morphs and actual locally imported Skyrim fonts are now available, with four distinct role scenes; hosting remains future scope; the next integration milestone is real game input/output, not another UI orchestration engine.

The [setup/media follow-up](docs/reviews/2026-10-31-setup-native-faces.md) records a fresh teammate install, original-font verification and native blink/speech/mood checks. The supplied runtime assets remain in the private project; source-only checkouts still work with illustrated fallbacks. Facial timing is approximate, and the body now uses a conservatively relaxed static pose.

The latest [immersion review](docs/reviews/2026-10-31-immersion-refinement.md) justified larger text, actual game screenshot backgrounds and native-rig arms-down posing without a layout redesign. The [runtime pack](assets/runtime/README.md) supplies the required models/fonts/voices/scenes to repository collaborators; clone with Git LFS and run setup. No API keys or game archives are included.
