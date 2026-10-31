# NPC

A game-independent orchestration system for believable NPC interactions. The system decides whether an NPC engages, what they know, and how they respond before asking a replaceable language model to express the response.

**Status:** reviewed design baseline v0.2, 31 October 2026. This repository contains planning documents, contracts, issue drafts and a reusable reviewer skill; no runtime has been implemented or benchmarked. API-first evaluation is the initial path; local inference is a later option.

Start with the [overall technical requirements document](docs/TRD.md), then the [module TRDs](docs/modules/README.md) and [implementation backlog](docs/BACKLOG.md).

Supporting documents:

- [Shared contracts and complete example turn](docs/CONTRACTS.md)
- [Mantella input audit and integration experiment](docs/research/MANTELLA.md)
- [Source reconciliation and requirement traceability](docs/TRACEABILITY.md)
- [Team workflow and implementation sequence](docs/TEAM_WORKFLOW.md)
- [Evaluation and latency plan](docs/EVALUATION.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Independent design review and resolutions](docs/reviews/2026-10-31-design-review.md)
- [Concrete edge resource limits](docs/RESOURCE_PROFILE.md)
- [Browser demo feasibility](docs/research/BROWSER_DEMO.md)
- [Reusable reviewer skill](.agents/skills/review-npc-design/SKILL.md)
- [Single-file dependency setup](SETUP.md)
- [Knowledge folder contract](Knowledge%20base/kb/README.md)

The first implementation milestone is a replay-based turn through the full core pipeline. Skyrim/Mantella is a reference adapter and best-effort demo. Other game adapters, production animation and fine-tuning follow after the core is evaluated.

Repository: https://github.com/mohanchandrass/NPC
