# Documentation

Start with the [general TRD](TRD.md), then the [shared contracts](CONTRACTS.md) and relevant [module TRD](modules/README.md).

| Need | Read |
|---|---|
| Where to put code, tests and data | [Repository structure](REPOSITORY_STRUCTURE.md) |
| Environment and single dependency file | [Setup](../SETUP.md) |
| How teammates implement and review | [Team workflow](TEAM_WORKFLOW.md), [development skill](../.agents/skills/develop-npc-component/SKILL.md) |
| Next work packages and dependencies | [Issue-ready backlog](BACKLOG.md) |
| Architecture tradeoffs | [Decisions](DECISIONS.md), [source reconciliation](TRACEABILITY.md) |
| Latency, quality and compute budgets | [Evaluation](EVALUATION.md), [resource profile](RESOURCE_PROFILE.md) |
| Design review conclusions | [Reviewed baseline](reviews/2026-10-31-design-review.md), [reviewer skill](../.agents/skills/review-npc-design/SKILL.md) |
| Skyrim input extraction | [Mantella audit](research/MANTELLA.md) |
| Browser testing/demo choices | [Browser demo feasibility](research/BROWSER_DEMO.md) |
| User knowledge folder | [Knowledge folder contract](../Knowledge%20base/kb/README.md) |

Keep stable document paths and link instead of copying requirements into multiple places. Module behavior belongs in its TRD; shared wire contracts belong in `CONTRACTS.md`; source placement belongs in `REPOSITORY_STRUCTURE.md`. Research and reviews explicitly distinguish observations from proposals and measured results.
