# Documentation

Start with the [general TRD](TRD.md), then the [shared contracts](CONTRACTS.md) and relevant [module TRD](modules/README.md).

| Need | Read |
|---|---|
| Where to put code, tests and data | [Repository structure](REPOSITORY_STRUCTURE.md) |
| Run/understand the first working context builder | [Context builder](CONTEXT_BUILDER.md), [reviewed implementation plan](plans/I04-context-builder.md) |
| Generate/validate dialogue; configure OpenRouter or Gemini | [Preview guide](GENERATION_VALIDATION.md), [provider profiles](../configs/providers/README.md), [plan](plans/I06-I07-generation-validation.md), [review](reviews/2026-10-31-generation-validation-review.md) |
| Environment and single dependency file | [Setup](../SETUP.md) |
| How teammates implement and review | [Team workflow](TEAM_WORKFLOW.md), [development skill](../.agents/skills/develop-npc-component/SKILL.md) |
| Next work packages and dependencies | [Issue-ready backlog](BACKLOG.md) |
| Architecture tradeoffs | [Decisions](DECISIONS.md), [source reconciliation](TRACEABILITY.md) |
| Latency, quality and compute budgets | [Evaluation](EVALUATION.md), [resource profile](RESOURCE_PROFILE.md) |
| Design review conclusions | [Reviewed baseline](reviews/2026-10-31-design-review.md), [reviewer skill](../.agents/skills/review-npc-design/SKILL.md) |
| Context implementation review and fixes | [Independent implementation review](reviews/2026-10-31-context-implementation-review.md) |
| Does the current slice demonstrate believable behavior? | [Behavior-quality audit and remaining gaps](reviews/2026-10-31-behavior-quality-audit.md) |
| Talk to test personas in a separate browser interface | [Manual NPC lab](NPC_LAB.md), [profiles](../fixtures/personas/npc_lab/README.md), [implementation review](reviews/2026-10-31-manual-npc-lab.md) |
| Persistent relationships and bounded dialogue memory | [Social-state guide](SOCIAL_STATE.md), [latest self-review](reviews/2026-10-31-social-state-character-stage.md) |
| Local character models and Mantella voices | [Media configuration/setup](../configs/npc_lab/README.md) |
| Skyrim input extraction | [Mantella audit](research/MANTELLA.md) |
| Browser testing/demo choices | [Browser demo feasibility](research/BROWSER_DEMO.md) |
| User knowledge folder | [Knowledge folder contract](../Knowledge%20base/kb/README.md) |

Keep stable document paths and link instead of copying requirements into multiple places. Module behavior belongs in its TRD; shared wire contracts belong in `CONTRACTS.md`; source placement belongs in `REPOSITORY_STRUCTURE.md`. Research and reviews explicitly distinguish observations from proposals and measured results.
