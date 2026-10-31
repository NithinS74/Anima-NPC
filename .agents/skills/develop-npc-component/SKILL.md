---
name: develop-npc-component
description: Plan, review, implement, unit-test and regression-check NPC components or behavior changes. Use when a teammate or agent develops or fixes repository code; documentation-only changes need relevant document checks instead of runtime tests.
---

# Develop an NPC component

Follow this sequence for every implementation: **plan -> review the plan -> implement with unit tests -> review the change -> run regression -> report evidence**. Review/test fixes repeat the affected steps. Do not treat code that merely runs once as a finished component.

Resolve repository paths from the repository root. Read `AGENTS.md`, `README.md`, `docs/TEAM_WORKFLOW.md`, the relevant module TRD and `docs/CONTRACTS.md`. Consult `docs/RESOURCE_PROFILE.md` and `docs/EVALUATION.md` for affected runtime limits or acceptance targets. Inspect current code/tests and working-tree changes before choosing an approach; preserve teammates' unrelated work. The TRDs describe a target, not proof that a module exists.

## 1. Plan before implementation

Write a concise plan in the issue/PR or task notes before changing runtime code. Use a separate design document only when the change warrants one. Include:

- User-visible outcome, issue/requirement and concrete acceptance criteria.
- Files/component boundaries, public contracts and affected callers, state/storage/config changes and any migration or compatibility needs.
- Chosen approach, why the complexity is justified, and relevant alternatives or assumptions to verify. Keep one modular process and deterministic decisions where practical; API-first/model-independent generation remains the baseline.
- Unit cases for each new/changed component, applicable integration/contract cases, regression commands and relevant performance/failure checks. Include a reproducing case for a bug.

For a small fix this can be a short paragraph plus test cases; do not create planning bureaucracy. A plan-only request ends with reviewed planning, not unauthorized implementation.

## 2. Review the plan before coding

Use the sibling `review-npc-design` skill (`.agents/skills/review-npc-design/SKILL.md`) to challenge the relevant assumptions and contracts. Check correctness, missing cases, unneeded infrastructure, dependencies, bounded work and how the proposed tests could expose failure. Record findings and resolutions before implementation. Correct the plan if the approach changes materially.

A teammate or separately authorized reviewer agent may review it. Otherwise perform a deliberate self-review and label it as such; do not claim independence. Routine review is not a mandatory user-approval gate. Resolve actionable issues within authorized scope; ask only for a material unresolved product/contract decision. Do not spawn agents merely because this skill mentions review.

## 3. Implement with component unit tests

Implement a coherent reviewed slice and add or update meaningful unit tests for **every new or changed working component**. Test observable behavior and invariants, not one test per private function, implementation-shaped mocks or a coverage percentage alone. Reuse existing test structure. For a bug, demonstrate the regression case failing before the fix when practical, then passing; state when that reproduction was not possible.

Cover normal behavior, relevant boundaries, invalid/missing input and realistic failure paths. Include ordering/deduplication, isolation, cancellation/deadline, disclosure or persistence cases when the component owns them. Assertions need explicit expected outcomes; an LLM saying its answer looks correct is not a unit test.

Use `.venv` and the single `requirements.txt`. Default tests are deterministic and offline: fake model/adapter calls, controlled clocks, seeded random choices, temporary storage and disposable corpora. Unit tests must not require Skyrim, a microphone, GPU, credentials or paid provider calls. Keep actual database/vector-store contract checks in appropriate integration tests rather than mocking away storage semantics. Select a new dependency only when needed and verify/update its pin.

Do not add a test framework/plugin system merely to organize a small component. Keep model calls, workers, queues and memory bounded under the existing resource profile. Update contracts/fixtures and consumers together when a public interface intentionally changes.

## 4. Review the implemented change

Review the actual diff against the reviewed plan and acceptance criteria, including tests and affected consumers. Check logic, naming/contracts, failure recovery, resource/call/deadline budgets, state/knowledge boundaries and maintainability. Use `review-npc-design` for relevant design risks; identify self-review honestly if no separate reviewer was used.

Fix findings, add missing regression cases and rerun affected checks. Never weaken assertions, skip a failing test or silently change expected behavior just to obtain a pass. Intentional behavior changes require updated requirements/tests and an explanation. Do not refactor unrelated modules to satisfy an aesthetic preference.

## 5. Run unit and regression checks

Run focused component tests while iterating. Before declaring a code change ready, run the existing full offline regression suite from the repository root with the project interpreter, plus applicable contract/integration checks and configured lint/type/build checks. A typical Python command once tests exist is:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Discover the repository's actual commands/configuration; do not invent successful checks. When the first executable component is introduced, establish runnable unit tests and the regression command as part of that slice. `pytest` collecting no tests is not a passing regression suite. This repository currently has planning/setup files; do not fabricate runtime tests for documentation.

For dependency changes run `pip check` and test affected integrations. For resource-sensitive changes measure the relevant latency/call count, bounded work and contention checks; broad performance targets remain unproven until measured. Re-run after substantive review fixes. Default regression excludes opt-in paid/live game tests; report those separately as run or not run.

If a baseline test fails, reproduce/separate it from new failures and record its impact. A required check that cannot run stays explicitly unverified with a reason; do not label the component fully ready. Continue independent authorized work without hiding the limitation.

## 6. Handoff / definition of done

Report the implemented outcome, plan/review findings resolved, component tests added, exact regression/check commands and outcomes, and remaining risks/unrun checks. Include contract/migration/dependency changes and useful file references. Every implemented component must have meaningful unit coverage and passing applicable regression before being called ready. Tests reduce risk; they do not prove nothing can ever break or that technical debt is impossible.

Keep setup/docs current and never commit credentials, local knowledge, model weights or generated runtime files. This workflow does not authorize merging, pushing, modifying a game installation or paid calls on its own; follow the user's explicit session authorization for external actions.
