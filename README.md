# NPC

A game-independent orchestration system for believable NPC interactions. The system decides whether an NPC engages, what they know, and how they respond before asking a replaceable language model to express the response.

**Status:** context building and a generation/validation scenario preview are implemented and tested offline. The preview adds deterministic engagement rules, replaceable API generation, strict output checks and bounded repair. A [live Gemini sample](docs/reviews/2026-10-31-behavior-quality-audit.md) confirmed integration but exposed grounding, social-policy and latency gaps; realism is not signed off. OpenRouter remains untested live. The full game pipeline is not yet implemented; local inference is a later option.

Start with [setup](SETUP.md), the [general TRD](docs/TRD.md) and the [implementation backlog](docs/BACKLOG.md). The [documentation index](docs/README.md) links contracts, module TRDs, research and reviews.

| Location | Purpose |
|---|---|
| `src/npc/` | Runtime modules, game adapters and test-console assets |
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

The context command explains response influences. The runtime command exercises generation/validation using a fake provider by default. See the [generation guide](docs/GENERATION_VALIDATION.md) for **OpenRouter/Gemini configuration and live commands**. RAG, persistent state and game delivery remain planned. Skyrim/Mantella remains a best-effort reference adapter.

For **manual testing in a chat box**, double-click [run_npc_lab.bat](run_npc_lab.bat). It opens the separate localhost [NPC lab](docs/NPC_LAB.md) using live Gemini configuration from `.env`; pass `--offline` for the fake. Four [authored personas](fixtures/personas/npc_lab/README.md), original portraits, relationship/state controls, trace inspection and session export are included. Each message is an independent turn; the visible chat log is not conversation memory. The UI has no dependency on Skyrim or the core package's deployment.

For every component, follow **plan -> review plan -> implement with unit tests -> review change -> run regression**. Read the [development skill](.agents/skills/develop-npc-component/SKILL.md) yourself or ask your agent:

```text
Use $develop-npc-component to implement <issue/component>.
```

If your agent does not discover repository skills, ask it to read `.agents/skills/develop-npc-component/SKILL.md` explicitly. [AGENTS.md](AGENTS.md) routes repository-aware agents to the same workflow. The skill requires meaningful unit tests for each working component and applicable regression checks before readiness; reviews and passing checks must be reported honestly.

Create a separate branch for each task, named `feature/<issue-id>-<short-name>` (for example, `feature/I05-rag-ingestion`). Start from an up-to-date `main`, commit and push your branch, then open a **pull request targeting `main`**. Include the linked issue, changes, review findings and unit/regression test results; request a teammate review. Merge only after review approval and required checks pass. Do not push implementation changes directly to `main`. See the [team workflow](docs/TEAM_WORKFLOW.md) for details.

Repository: https://github.com/mohanchandrass/NPC
