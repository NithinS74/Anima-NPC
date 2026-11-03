# Research contribution and evidence boundary

## Problem

Given player utterance, trusted NPC/game snapshot and separately indexed domain documents, produce a bounded, context-conditioned NPC reply without putting engagement decisions, knowledge authorization or durable world updates under unrestricted language-model control.

## Research questions

1. Can the same implemented orchestration path exercise authored, generated, repair, unavailable and cancelled outcomes while preserving scope and evidence boundaries?
2. Which parts of model substitution are configuration changes and which require protocol-specific adapters?
3. What do existing offline checks establish about document adaptation, and what remains unproven about semantic grounding and live performance?

## Contribution-to-evidence mapping

| Proposed contribution | Evidence | Permitted conclusion |
|---|---|---|
| Policy-controlled orchestration | PreviewRunner, behavior policy, runtime tests | Implemented deterministic routing and bounded optional generation |
| Separation of knowledge and model | RAG service/adapter, prompt packing, local-store integration tests | Documents can be reindexed and supplied without an application training loop |
| Replaceable compatible backend | ModelProvider protocol, compatible HTTP adapter, profile tests | Common orchestration contract; not universal model compatibility or quality equivalence |
| Evidence-aware output boundary | scope checks, whole-passage packing, alias validation tests | References restricted to packed evidence; not entailment verification |
| Context-aware game interface | lab plus Skyrim adapter with optional visual references | Implemented integration path; real-game reliability and visual grounding unmeasured |

## Novelty discipline

Existing work already combines language models, memory, retrieval and agent orchestration. Do not claim the first unified agent/NPC framework. This prototype investigates a particular separation of deterministic engagement, trusted context, file-scoped retrieval and bounded candidate acceptance. No new learning algorithm or demonstrated superiority is claimed. RAG and fine-tuning are complementary; even foundational RAG trains its components. Reduced training burden here is an architectural capability, not measured cost savings.

## Evaluation decision (self-review)

Use existing offline contract/unit/integration checks as functional evidence. Separate scripted/HTTP-mock inference and test embeddings from genuine model outputs. Existing live reports are dated diagnostics rather than a current benchmark. Do not fill missing metrics using earlier unrelated paper numbers. Submission strength will remain limited until held-out, blinded and controlled grounding/backend studies are conducted.
