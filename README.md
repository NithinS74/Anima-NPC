# NPC

A game-independent orchestration system for believable NPC interactions. The system decides whether an NPC engages, what they know, and how they respond before asking a replaceable language model to express the response.

**Status:** reviewed design baseline v0.2 with source/test directory scaffolding. No runtime has been implemented or benchmarked. API-first evaluation is the initial path; local inference is a later option.

Start with [setup](SETUP.md), the [general TRD](docs/TRD.md) and the [implementation backlog](docs/BACKLOG.md). The [documentation index](docs/README.md) links contracts, module TRDs, research and reviews.

| Location | Purpose |
|---|---|
| `src/npc/` | Runtime modules, game adapters and test-console assets |
| `tests/` | Unit, contract and offline integration regression |
| `fixtures/` | Shared public worlds, scenarios and labelled evaluation data |
| `configs/` | Public authored settings; credentials stay in local `.env` |
| `scripts/` | Thin setup/maintenance/developer entry points |
| `benchmarks/` | Quality, latency and game-resource measurement harnesses |
| `docs/` | Requirements, decisions, workflow, research and reviews |
| `.agents/skills/` | Development and design-review workflows |
| `Knowledge base/kb/` | User corpus; check privacy/licensing before tracking files |

See the [repository structure guide](docs/REPOSITORY_STRUCTURE.md) for the complete tree, module-to-folder mapping and placement rules. Empty scaffold directories contain `.gitkeep`; they are not working components. Local environments, scratch files and runtime output are ignored.

The first implementation milestone is a replay-based turn through the full core pipeline. Skyrim/Mantella is a reference adapter and best-effort demo. Other game adapters, production animation and fine-tuning follow after the core is evaluated.

For every component, follow **plan -> review plan -> implement with unit tests -> review change -> run regression**. Read the [development skill](.agents/skills/develop-npc-component/SKILL.md) yourself or ask your agent:

```text
Use $develop-npc-component to implement <issue/component>.
```

If your agent does not discover repository skills, ask it to read `.agents/skills/develop-npc-component/SKILL.md` explicitly. [AGENTS.md](AGENTS.md) routes repository-aware agents to the same workflow. The skill requires meaningful unit tests for each working component and applicable regression checks before readiness; reviews and passing checks must be reported honestly.

Repository: https://github.com/mohanchandrass/NPC
