# Module TRDs

All modules are proposed work packages, not implemented components. Each uses [shared contracts](../CONTRACTS.md) and [global requirements](../TRD.md). Choose one implementation owner and one reviewer before starting; historical roles are not assignments.

| ID | Module | Contract boundary | Dependencies |
|---|---|---|---|
| [M01](M01-input.md) | Input connectors | Raw input -> TurnInput / WorldEvent | Contracts |
| [M02](M02-state.md) | Persona, relationships and memory | Scoped events -> StateSnapshot | Contracts |
| [M03](M03-behavior.md) | Engagement and behavior | Situation + state -> InteractionPlan | M02 contract, M04 contract |
| [M04](M04-context.md) | Context builder | Input + state -> Situation -> ContextBundle | M01/M02; M05 for final evidence |
| [M05](M05-rag.md) | Generalized RAG | Folder -> index; RetrievalRequest -> EvidenceSet | Contracts only |
| [M06](M06-generation.md) | Prompt and model providers | ContextBundle + plan -> CandidateResponse | Contracts only; use fixtures |
| [M07](M07-validation.md) | Critique, validation and repair | Candidate + plan/context -> ValidationResult | Contracts; M06 repair interface |
| [M08](M08-output.md) | Output and pacing | ValidatedResponse -> delivery -> ack | Adapter capabilities |
| [M09](M09-runtime-evaluation.md) | Orchestrator, replay console, evaluation | TurnInput -> TurnResult + trace | All contracts; fake every module first |
| [M10](M10-vision.md) | Optional CV perception | Frames -> scoped VisualObservation | M01 visual contract |

This split is deliberately larger than the four-person team. A person can own multiple sequential packages. M05 and M06 can be implemented independently first; M03 and M04 should agree on their shared situation/plan boundary before coding.
