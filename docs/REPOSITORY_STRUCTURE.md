# Repository structure and code placement

This is the agreed source layout for the modular monolith. Directories are scaffolded with `.gitkeep` so Git preserves them; they do not contain working runtime components yet. Add real code incrementally under the development skill, removing a directory's `.gitkeep` when its first tracked file is added. Package initializers/build configuration belong to the first executable slice, not placeholder implementations.

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

## Tracked versus local/generated

Track source, tests, small public fixtures, validated public config and documentation. Local `.venv/`, `.tools/`, `tmp/`, `data/`, `models/`, `logs/`, `captures/`, `recordings/` and `output/` are already ignored. Use `output/benchmarks/` for raw experiment results; place curated redacted conclusions in `docs/reviews/` when worth sharing. Do not delete teammates' local data to make the tree look tidy.

Generated-data ignore rules are root-anchored so `src/npc/output/` and future source directories named `models` are not hidden. The current user-edited `.gitignore` does not automatically exclude `Knowledge base/kb/`; preserve that choice and review corpus privacy/licensing before tracking it. Public fixture packs and private user knowledge are different inputs even when both contain lore.

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

Structure validation checks expected directories, ignored-path conflicts and document links. Runtime unit/regression tests must be introduced with the first executable component; none are claimed for this directory-only scaffold.
