# Project technical audit

Audit date: 2026-11-02. Source baseline: `ff9fd7e95beac344b43e836027bc43f3e5c7b5bc`, branch `latest`. This is a source/evidence audit and labelled architecture self-review, not independent review or live-game certification.

## Scope and method

Read the root README, repository structure, team workflow, shared contracts, general TRD, decisions, RAG/generation module specifications, implementation and review documents. Inventoried source, lab/CV interfaces, tests, benchmarks, public fixtures, configuration and project-docs. Followed the execution path below rather than treating module plans as runtime facts. Private knowledge, player state and `.env` contents are excluded. Paper figures/results must derive from this baseline; subsequent experiments are logged separately.

## Actual architecture and responsibilities

| Component | Actual source | Status and boundary |
|---|---|---|
| Canonical schemas | `src/npc/contracts/{context,dialogue,knowledge}.py` | Implemented strict Pydantic contracts; broader production envelopes in docs remain proposals |
| Context appraisal | `src/npc/context/builder.py`, `focus.py`, `assembly.py` | Implemented scope/revision matching, freshness/perceiver/subject/confidence filtering, conflict selection, relationship appraisal and evidence rechecks |
| Engagement/social policy | `src/npc/behavior/{policy,appraisal}.py` | Implemented deterministic rules: authored greetings/refusals, end in combat/social disengagement, generated novel inputs; heuristic rather than learned policy |
| Orchestrator | `src/npc/runtime/preview.py` | Implemented PreviewRunner: policy before retrieval/generation, ownership/admission bounds, deadlines, stale/cancel handling, at most generation plus one repair |
| Retrieval abstraction | `src/npc/contracts/knowledge.py`, `src/npc/rag/__init__.py` | Retriever protocol; local and optional HTTP implementations |
| Local retrieval | `src/npc/rag/{local,evidence,config}.py` | Implemented trusted file binding by game/world/NPC; serialized worker; unavailable/forbidden/empty outcomes |
| Ingestion/vector store | `src/npc/rag/backend/{service,loaders,embeddings,config}.py` | Implemented supported-document parsing, token-offset chunks, CPU ONNX MiniLM embeddings, embedded Chroma cosine index, hash revisions and manifest publication |
| Prompt/provider | `src/npc/generation/{prompt,provider,config}.py` | Implemented neutral messages and ModelProvider protocol; one configurable chat-completions transport and deterministic offline fake |
| Candidate checks | `src/npc/validation/response.py` | Implemented strict JSON/schema, finish reason, modes, length, cues, state and packed evidence-ID checks; no semantic entailment guarantee |
| Social storage | `src/npc/state/social_store.py` | Partial production scope: SQLite relationships/revisions and bounded acknowledged lab history; no full generic durable delivery outbox |
| Local interface | `tools/npc_lab/{server,service}.py`, `web/` | Separate loopback HTTP/browser companion, calls same PreviewRunner; UI/media do not belong to core |
| Skyrim adapter | `src/npc/adapters/skyrim/{bridge,protocol,server,windows}.py`, `native/` | Implemented native game protocol/composition and best-effort command/receipt delivery; live readiness unverified |
| Optional vision | `src/npc/vision/client.py`, `cv/backend/app/` | Implemented loopback descriptor client and VLM service path, default VLM-only; actual inference not established here |
| Generic production input/output services | scaffold `src/npc/inputs`, `src/npc/output`; proposed M01/M08/M09 | Not a completed production deployment merely because directories/contracts exist |

## End-to-end request lifecycle

1. A lab player posts a typed turn to the loopback server, or the Skyrim adapter receives correlated game/player events. The lab creates a ContextScenario using authored persona and configured encounter controls; the connector composes its own runner. A game-independent replay entry point also accepts public scenario JSON (`src/npc/runtime/__main__.py`).
2. `LabService.turn` checks admission/persona/state, begins a revision-checked social turn when storage is configured, obtains bounded acknowledged history, then builds a scenario. The trusted connector must supply source/perceiver metadata; the schema alone does not authenticate arbitrary game facts.
3. `build_situation` verifies matching scope/NPC/player/revision and aware timestamps. It removes expired, future, unperceived, wrong-subject, low-confidence and player-claim facts. Telemetry outranks vision; unresolved equal-rank conflicts remain unknown. Persona, relationship and social appraisal produce explicit influences.
4. `choose_plan` routes routine inputs to authored replies or end states before any model call. Novel input is generated; who/where/when heuristically marks required knowledge, other generated requests use uncertain knowledge. This is not a semantic intent classifier.
5. `PreviewRunner` admits one local generation/retrieval chain, rejects busy work, bounds cancellation cleanup and checks turn epoch/dialogue revision. Retrieval is skipped for non-generated routes and when no retriever is configured.
6. `LocalRetriever` resolves the current/follow-up question and a trusted file binding matching game/world/NPC. Missing binding is forbidden. It performs one threaded retrieval under a gate held until actual completion; setup/index preparation is separate from interactive turns.
7. `RAGService.retrieve` reads committed manifest revisions for the bound source, embeds the query, and queries Chroma with a revision filter before ranking. Returned cosine distances order candidates; there is no learned reranker. The implementation enumerates manifest files/revisions per query: it does not yet satisfy the scalable indexed-authorization design in M05.
8. `normalize_result` rechecks query/source/count, rejects truncated/duplicate/empty evidence and optionally applies a distance threshold. Raw dialogue export has conservative personal/temporal filtering; unresolved speaker and quest conditions are never reconstructed. `assemble_knowledge` checks scope/NPC and observation-ID collisions.
9. `build_prompt` serializes policy/persona in system content; player text, retrieved passages, displayed history and optional uncertain visual description stay in data content. Whole evidence passages precede recent whole exchanges in packing. Short evidence aliases map only to packed IDs. Input control is a UTF-8 byte estimate plus reserve, not exact backend tokenization.
10. A configured object implementing `ModelProvider.generate(PromptPackage, timeout_s)` returns ProviderReply. OfflineProvider is scripted, not an LLM. ChatCompletionsProvider sends bounded nonstreaming HTTPX requests; profile/model/endpoint/key and optional reasoning/JSON support configure compatible APIs.
11. Validation rejects malformed/incomplete/stale responses, invalid modes/cues/length and unknown citations. A single repair can occur within the same cutoff. Timeouts/unavailable retrieval/invalid output lead to validated authored fallback when time permits. Stale/cancelled work produces no audible fallback. Valid evidence IDs do not establish that answer claims follow from those passages.
12. Lab response returns diagnostics and validated text to the browser. SQLite history becomes acknowledged only after the display callback; display is not proof of reading/hearing. Skyrim bridge correlates response/command/receipts and supports configured audio paths; its best-effort receipts are not the generic production outbox/heard-memory proposal.

## Knowledge ingestion and adaptation

`python -m npc.rag` owns explicit preparation/sync/status/query commands. Supported code formats: txt/md/markdown/pdf/docx/csv/json/html/htm. PDF extraction is text-based; no OCR is implemented. Default chunks are 220 encoder tokens with 32-token overlap, capped below the 254-token embedding input check. Source bytes plus pipeline/model/chunk/source parameters determine revision hashes. Upserted chunks become query-visible after manifest publication; old/abandoned revisions are cleaned separately. A file lock serializes sync/query. Failure can preserve last-good revisions; this is not full collection-level transactional hot reindexing.

Changing documents and trusted file bindings changes supplied domain context without an application training loop. This establishes a software adaptation mechanism, not cross-game response quality or the claim that training is never useful. Full proposed per-document grants, temporal partitions and robust dialogue eligibility remain unimplemented.

## Model substitution: precise scope

The actual abstraction is a Python protocol and provider-neutral messages/reply. Gemini and OpenRouter public profiles use the SAME compatible HTTP transport; they are not two unrelated native SDK adapters. Loopback compatible endpoints are accepted, but arbitrary model architectures, tool APIs, local GPU inference and equal quality across models are not demonstrated. JSON compliance, context capacity and reasoning/output-budget behavior still vary. New incompatible protocols need a new implementation of the small interface.

## Technologies and version evidence

Pinned requirements, not yet proof of installed versions: Python 3.11 target; Pydantic 2.14.2, HTTPX 0.28.1, Chroma 1.5.9, ONNX Runtime 1.23.2, NumPy 2.4.6, FastAPI 0.162.0, pytest 9.2.0, pypdf 6.21.4. SQLite comes from Python. Embedding implementation identifies `all-MiniLM-L6-v2-onnx-v1` with CPUExecutionProvider. Browser assets use vendored Three.js; optional CV calls local Ollama. Actual installed versions and checks belong in the evidence log. No reference hardware, measured VRAM budget or offline generation stack is established by dependency pins.

## Existing research and numerical evidence

- `project-docs/RM - Literature Review.pdf`: 18-page survey; useful seed titles include Generative Agents, Character-LLM and Dungeons and Dragons. Its claim that a unified framework is absent is not a proven novelty claim; entries lack complete verified references and must be checked individually.
- `project-docs/IEEE-overleafexample.tex`: describes trained 2.67M-parameter offline dialogue, voice pipelines and scores. No corresponding training/evaluation artifacts were found in the audited runtime tree. Treat as a template/example, exclude its numbers and claims.
- `docs/reviews/2026-10-31-behavior-quality-audit.md`: historical small Gemini integration/quality diagnostic, including unsupported cargo-terminal instructions despite accepted structure. Changed policy/prompts since then prevent treating it as current performance. Refer to it as a documented failure case, not a new measured score.
- `docs/reviews/2026-11-01-openrouter-output-budget.md`: historical compatible-API diagnostic and approximately 3.94 s repaired answer with unsupported claims. Not comparative backend evaluation.
- `docs/reviews/2026-11-02-skyrim-vision-pipeline.md`: records prior 492-test regression, native build/CTest and unavailable Ollama. Historical self-report until rerun; no live Skyrim/VLM accuracy evidence.
- `benchmarks/` and `fixtures/evaluation/` contain placeholders. There is no implemented held-out research benchmark or labelled retrieval relevance set there.

## Missing evidence and limitations

No validated retrieval Precision/Recall/MRR, hallucination rate, blinded human persona evaluation, multiple-model controlled comparison, RAG ablation, cross-game generalization, training-cost comparison or game frame-time/VRAM study was found. Historical live diagnostics are tiny and nonrandomized. Fake providers validate mechanics, not factuality. Real Chroma tests use deterministic test embeddings, not production MiniLM semantic relevance. Byte budgets are conservative estimates, and deadlines are configured limits rather than achieved performance. Cancellation cannot guarantee cancellation of remote billing. File-level bindings are materially weaker than the full M05 grant/revision design.

## Inconsistencies requiring explicit handling

README/workflow/module TRDs contain stale sentences (RAG/history packing unimplemented, knowledge not ignored, no game path) contradicted by newer code and reviews. Preserve application docs during this research-only task and use code as authority. Public RAG example binds manual-lab/village NPCs to one dialogue file; it is not automatically valid for arbitrary Skyrim NPCs. The old paper example's author list and the survey's team list differ: the user subsequently confirmed the author order and USNs on 2026-11-02, and these are now in the manuscript. RV University is retained from supplied documents.

## Defensible contribution and plan self-review

Conditional go for a systems prototype paper: evaluate an orchestration boundary that decides engagement before retrieval/model work, separates authoritative observations from approximate retrieved knowledge, and validates replaceable model outputs under bounded work. RAG, retrieval, persona prompting and provider interfaces individually are established techniques. Claim an implementation/integration contribution and offline functional evidence, not a novel learning algorithm or proven superior realism. Keep naturalness, semantic faithfulness, multi-game transfer and real-time generation as open empirical gates. Paper writing can proceed once evidence and primary references are recorded; submission readiness requires candid review of those gaps.
