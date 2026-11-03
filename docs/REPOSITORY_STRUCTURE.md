# Repository structure and code placement

This is the agreed source layout for the modular monolith. Context construction, prototype behavior, prompt/provider, validation and preview runtime have code/tests; other empty directories retain `.gitkeep`. Add code incrementally under the development skill, removing the placeholder when the directory gains tracked files. `pyproject.toml` configures the source package and test discovery; `requirements.txt` remains the single pinned environment file. Current scope is in [context builder](CONTEXT_BUILDER.md) and [generation/validation](GENERATION_VALIDATION.md). Public API profiles live in `configs/providers/`.

```text
NPC/
|-- README.md                 Start here: status and navigation
|-- AGENTS.md                 Agent workflow entry point
|-- SETUP.md                  Environment/setup commands
|-- requirements.txt          One pinned dependency list
|-- .env.example              Public configuration names, no credentials
|-- .agents/skills/           Reusable development/review instructions
|-- src/npc/                  Python runtime source, one application
|   |-- contracts/            Shared boundary schemas and small protocols
|   |-- adapters/             Game/replay transport and protocol mappings
|   |   |-- replay/           Synthetic/replayed game inputs and delivery
|   |   `-- mantella/         Optional Skyrim/Mantella compatibility
|   |-- inputs/               Canonical input normalization/validation
|   |-- state/                SQLite repositories, relationship reducers, memory
|   |   `-- migrations/       Versioned state-schema migrations
|   |-- behavior/             Engagement policy, intent, authored responses
|   |-- context/              Perception, eligibility, dependencies, packing
|   |-- rag/                  Ingestion, indexing, embeddings, retrieval
|   |-- generation/           Prompt rendering and model-provider adapters
|   |-- validation/           Candidate checks and repair decisions
|   |-- output/               Delivery lifecycle, cue validation, optional TTS
|   |-- vision/               Optional visual-descriptor processing
|   `-- runtime/              Composition, turn lifecycle, HTTP entry points
|       `-- web/              Test-console HTML/CSS/JS, when implemented
|-- tests/
|   |-- unit/                 Isolated component behavior
|   |-- contracts/            Shared schemas and boundary compatibility
|   `-- integration/          Cross-module/storage/offline replay checks
|-- fixtures/
|   |-- worlds/               Small team-authored public world/NPC packs
|   |-- scenarios/            Deterministic turn, event and delivery scenarios
|   `-- evaluation/           Held-out labelled prompts and expected evidence
|-- configs/                  Public authored policy/persona/runtime settings
|-- scripts/                  Setup/maintenance/developer entry scripts
|-- tools/npc_lab/            Separate local manual-test UI/server, imports core
|-- run_anima.bat             Windows launcher for that test tool
|-- benchmarks/               Latency, quality and resource evaluation harnesses
|-- docs/                     TRDs, contracts, decisions, research and reviews
`-- Knowledge base/kb/        User corpus, separate from public test fixtures
```

## Where each work package goes

| Work | Source home | Test home / main reference |
|---|---|---|
| I00 shared schemas/fakes | `src/npc/contracts/`; test-only fakes in `tests/` | `tests/contracts/`; [contracts](CONTRACTS.md) |
| M01 input normalization | `src/npc/inputs/` | `tests/unit/inputs/` when implemented; [M01](modules/M01-input.md) |
| Game/replay protocol mapping | `src/npc/adapters/<adapter>/` | `tests/unit/adapters/`, `tests/integration/`; [Mantella audit](research/MANTELLA.md) |
| M02 persistent state | `src/npc/state/`, SQL/schema changes in `state/migrations/` | `tests/unit/state/`, storage checks in `tests/integration/`; [M02](modules/M02-state.md) |
| M03 engagement policy | `src/npc/behavior/`; authored data in `configs/` | `tests/unit/behavior/`; [M03](modules/M03-behavior.md) |
| M04 context assembly | `src/npc/context/` | `tests/unit/context/`; [M04](modules/M04-context.md) |
| M05 reusable RAG | `src/npc/rag/` | `tests/unit/rag/`, real local index tests in `tests/integration/`; [M05](modules/M05-rag.md) |
| M06 prompt/provider calls | `src/npc/generation/` | `tests/unit/generation/`, provider contract checks in `tests/contracts/`; [M06](modules/M06-generation.md) |
| M07 candidate acceptance | `src/npc/validation/` | `tests/unit/validation/`; [M07](modules/M07-validation.md) |
| M08 delivery and cues | `src/npc/output/`; game mapping in `adapters/` | `tests/unit/output/`, delivery scenarios in `tests/integration/`; [M08](modules/M08-output.md) |
| M09 composition/console | `src/npc/runtime/`, static files in `runtime/web/` | `tests/unit/runtime/`, full offline turns in `tests/integration/`; [M09](modules/M09-runtime-evaluation.md) |
| M10 optional perception | `src/npc/vision/` | `tests/unit/vision/` when implemented; [M10](modules/M10-vision.md) |
| Metrics/performance experiments | `benchmarks/`; reusable application logic stays in `src/npc/` | [evaluation](EVALUATION.md), [resource profile](RESOURCE_PROFILE.md) |

Only the test category directories are created initially. Add mirrored component test folders when there are actual tests to place in them; do not create empty test files to suggest coverage.

## Boundaries that keep the layout maintainable

- `contracts` holds data shapes/protocols, not implementations or a dependency-injection framework. It must not import concrete providers, HTTP routes or game modules.
- `adapters` translates game/replay protocols in both directions. `inputs` validates canonical inputs; `output` owns generic delivery lifecycle. Skyrim keys never leak into behavior, context or RAG. Provider-specific LLM APIs live in `generation`, not game adapters.
- `runtime` wires modules together and owns scheduling/deadlines. Business modules do not import runtime wiring or each other's concrete storage/provider internals; pass the small interfaces they actually need. This is one process, not a folder-to-service mapping.
- Keep logic close to its owner. A two-module helper can stay with its owner or a narrowly named shared module once real reuse is demonstrated. Do not start a catch-all `utils`, `services`, generic plugin registry or duplicate parallel `backend` tree.
- `configs` contains validated public authored settings, not Python business logic, API keys or generated state. `.env` is local secret configuration. User documents go in `Knowledge base/kb`, not in test fixtures.
- `fixtures` is the single home for reusable small public datasets. Test-only helpers/fakes stay in `tests`; one-test data can stay beside its test. Use temporary directories for generated databases and output, not committed binary snapshots by default.
- `scripts` contains thin operational entry points calling package code; do not duplicate the orchestrator or retriever there. Keep benchmark scenarios/data reusable and results separate from code.
- Test-console UI stays thin and calls the same backend contracts as adapters. No second orchestration engine or frontend framework is implied. If a real separate frontend becomes necessary, review that change before adding another project/build tree.

User-requested standalone lab: `tools/npc_lab/` owns its local HTTP bridge and static assets; `fixtures/personas/npc_lab/` owns public test personas. It composes the existing `PreviewRunner` without core imports of UI code or a second pipeline. This is a deliberate reviewed placement exception to the earlier future `runtime/web/` console suggestion, keeping test UI out of core deployment. See [NPC lab](NPC_LAB.md); the production M09 HTTP API remains separate work.

## Tracked versus local/generated

Track source, tests, small public fixtures, validated public config and documentation. Local `.venv/`, `.tools/`, `tmp/`, `data/`, `models/`, `logs/`, `captures/`, `recordings/` and `output/` are already ignored. Use `output/benchmarks/` for raw experiment results; place curated redacted conclusions in `docs/reviews/` when worth sharing. Do not delete teammates' local data to make the tree look tidy.

Generated-data ignore rules are root-anchored so `src/npc/output/` and future source directories named `models` are not hidden. The internal RAG setup now explicitly ignores local documents under `Knowledge base/kb/` except its public README/placeholder, plus the generated `data/rag/` model/index cache. Review corpus privacy/licensing before deliberately sharing files through public fixtures. Public fixture packs and private user knowledge are different inputs even when both contain lore.

## Plan and structure self-review

Review performed using the development/design-review skills; this is a self-review, not an independent agent review.

| Check | Decision |
|---|---|
| All TRD modules have a clear owner directory | Yes; optional vision has a home but no inference implementation |
| Input/output versus game adapters overlap | Resolved: adapters map protocol; canonical normalization and delivery policy have separate owners |
| Shared interfaces versus implementations | Contracts stay dependency-light; runtime composes implementations |
| Unit/regression/evaluation organization | Three offline test categories; optional measurements in benchmarks; shared fixture home |
| Root and documentation navigation | Short root README plus documentation index; established document paths retained |
| Git visibility | Root-anchor generated-data ignores; verified runtime source is not hidden; preserve the existing KB rule removal |
| Premature infrastructure | No microservices, placeholder APIs, build framework, dummy tests or new dependencies |
| Implementation readiness | Go for I00/fake slice; directory existence is not code or test coverage |

The table above records the original structure-only self-review. The first executable context slice has now introduced contract/unit/integration tests; see its [guide](CONTEXT_BUILDER.md) for current results. Remaining scaffold folders are not implementations or coverage claims.

## Implemented social-state and lab media slice

See [social state](SOCIAL_STATE.md) for typed `DialogueMemory`/`SocialAppraisal`, persona temperament, revision-checked SQLite relationships and bounded acknowledged recent history. This is partial state implementation, not the full delivery/outbox proposal. Reusable policy/storage stay in `src/npc/behavior/` and `src/npc/state/`; standalone HTTP, static models, voice and offline asset conversion stay in `tools/npc_lab/`. Public recipes live in `configs/npc_lab/`; all converted game assets/tools/weights remain ignored. Unit/integration cases live under the corresponding `tests/` owners.

Anima is the user-facing companion name. Existing `tools/npc_lab/` and persona/config/storage paths are retained deliberately for compatibility, not a second implementation. `run_anima.bat` is the only application launcher; the old launcher was removed at the user's request. Optional dependency-free Node camera tests and UI bot live in `tests/ui/`; default Python CI still needs no browser/GPU/game assets.

`setup.bat` is a thin Python 3.11 discovery wrapper; `scripts/setup_environment.py` owns repeatable project-only setup. Public original scene illustrations live under `tools/npc_lab/web/scenes/`. Offline native-face/font conversion remains tool code under `tools/npc_lab/`, while all extracted models/morphs/fonts and portable third-party tools stay ignored.

The owner-approved `assets/runtime/anima-media.zip` is the narrowly scoped Git LFS runtime bundle for this private project. Its manifest/provenance are ordinary tracked text. `scripts/anima_assets.py` handles bounded verified setup-time extraction into ignored `assets/private/npc_lab/`, preserving explicit local overrides. Conversion scratch, .venv, keys and player state remain excluded.

Automatic launch/bootstrap stays under `scripts/`: `launch_anima.py` coordinates readiness/setup, `check_environment.py` checks the local venv/media, and `source_update.py` owns bounded optional fast-forward updates. These scripts never enter the core turn pipeline.

## Internal local RAG

The independent Skyrim connection layer lives in `src/npc/adapters/skyrim/`, including its native SKSE source/build recipe under `native/`. Public settings/dependency pins are in `configs/skyrim/`; local settings are ignored. `scripts/build_skyrim_connector.py` builds/tests/packages the DLL without altering a game installation. Python boundary tests and a standalone C++ delivery check live under `tests/unit/adapters/`. See [Skyrim connector](SKYRIM_CONNECTOR.md).

The incoming `cv/` tree retains its standalone inference API/dashboard and CLI paths for compatibility. It uses the root `.venv`, pinned `requirements.txt` and root test discovery (including `cv/backend/tests`). `src/npc/vision/` owns the typed loopback client shared by the lab and Skyrim adapter. The adapter composes the core `PreviewRunner` with configured RAG and optional visual reference; it does not import lab HTTP/assets. VLM-only is the default; the legacy optional detector wrapper loads only when explicitly enabled. `run_cv.bat` starts the loopback inference API.

`src/npc/rag/backend/` owns the reused document loaders, chunking/CPU encoder and embedded Chroma service; `src/npc/rag/local.py` adapts it to NPC evidence without a second HTTP server. Configuration and evidence normalization stay in `src/npc/rag/`. Generated model/index files are under ignored `data/rag/`; user knowledge under `Knowledge base/kb/` is now explicitly ignored except its public README/placeholder. Backend storage tests live in `tests/integration/rag/`, pure loader/adapter/CLI tests in `tests/unit/rag/`. `python -m npc.rag` is the local maintenance entry point; setup prepares the model/index outside dialogue turns. No standalone RAG frontend is copied into the application.
