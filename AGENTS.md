# Working in this repository

Before implementing or changing a working component, read and follow [.agents/skills/develop-npc-component/SKILL.md](.agents/skills/develop-npc-component/SKILL.md). It requires a plan and plan review before coding, meaningful unit tests for every new/changed component, implementation review and applicable regression checks before declaring readiness.

Use [.agents/skills/review-npc-design/SKILL.md](.agents/skills/review-npc-design/SKILL.md) for the relevant design/correctness/edge-resource review. A self-review must be labelled; separate agent delegation requires authorization. Routine plan review does not require repeatedly asking the user for permission.

Read the relevant module TRD, shared contracts and [team workflow](docs/TEAM_WORKFLOW.md). Use the project `.venv` and single `requirements.txt`. Current repository status is documented in `README.md`; do not mistake planned modules or example commands for implemented runtime behavior.

Before adding files, consult [repository structure](docs/REPOSITORY_STRUCTURE.md) for module ownership and test/data placement. Keep runtime logic in `src/npc/`, game protocols in `adapters/`, tests in `tests/`, and reusable public data in `fixtures/`. Replace a `.gitkeep` when the directory gains real tracked contents; do not turn scaffold directories into dummy implementations or empty tests.

Documentation-only changes need relevant link/example/skill validation rather than invented component tests. Never report unrun checks or an empty test suite as passing regression. Preserve unrelated teammate changes.
