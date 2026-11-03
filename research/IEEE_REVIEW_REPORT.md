> Historical initial-draft record. Superseded for the current paper by REVISION_CHECKLIST.md, SCIENTIFIC_EVALUATION_REPORT.md and IEEE_FINAL_REVIEW.md (2026-11-03).

# IEEE reviewer-role self-review

Review date: 2026-11-02. This is a critical role-switched **self-review** of the manuscript against source revision `ff9fd7e`, following the repository design-review skill. It is not an independent external review, blinded assessment, or institutional plagiarism report. No separate reviewer agent was used.

## Overall assessment

An inspectable systems prototype with an appropriately bounded integration contribution. The manuscript describes implemented orchestration and documents meaningful offline regression. Its main weakness is empirical: software test counts cannot establish the proposed benefits for context-grounded NPC dialogue. The current version is useful as an implementation-based academic draft, but requires major empirical revision for a research venue expecting effectiveness evidence.

## Major findings (severity ranked)

1. **P1 - Missing semantic/effectiveness validation.** `ieee_paper/main.tex`, Results and Discussion; `../src/npc/validation/response.py:66` only checks evidence-ID membership. A candidate can cite a real passage while inventing a procedure. There is no held-out relevance or claim-level grounding sample. Correction: remove all efficacy/superiority implications; explicitly state unavailable metrics and propose blinded, controlled RAG/no-RAG comparisons. Current resolution: claim narrowing and missing-evidence discussion completed. Empirical gap remains and prevents effectiveness claims; no fabricated metric substitutes for it.
2. **P1 - Model-agnostic wording must remain restricted.** `../src/npc/generation/provider.py:22` defines the protocol; `:52` implements one chat-completions transport. Gemini/OpenRouter are profiles using the same transport. Compatibility does not guarantee equal instruction following or quality. Current resolution: title uses replaceable backends, abstract/body/Fig. 3 distinguish compatible configuration from new protocol adapters; fake provider is labelled non-LLM. Real controlled multi-backend evaluation remains unavailable.
3. **P1 - Initial authorship mismatch (resolved).** The original IEEE example and survey disagree about team membership. Inferring authors risks incorrect attribution. Resolution: user confirmed Mohan Chandra S S, Shreyas C, Nithish Gowda H N and Nithin S, in that order, with USNs replacing emails. The final author block includes those details and retains RV University from the supplied documents. The initial placeholder is removed; authors should still review the final affiliation and submission version.
4. **P2 - Authorization/scalability scope.** `../src/npc/rag/evidence.py:7` binds a source by game/world/NPC; `../src/npc/rag/backend/service.py:190` builds revision filters by scanning manifest entries. Missing document-level temporal/grant semantics and unmeasured manifest scaling prevent full M05/security/resource claims. Current resolution: described as file-level authorization with explicit limitations, not an implemented production access model. No runtime change made in this research task.
5. **P2 - Functional test evidence can be misread as a benchmark.** The 492 checks include lab/media/setup/CV and use mocks/test embeddings; the 13 storage integration checks do not evaluate real MiniLM semantics. Current resolution: test table includes mutually exclusive subsets, methods name real Chroma and deterministic vectors, discussion denies quality/performance inference. All numerical results map to the evidence ledger.
6. **P2 - Prior diagnostic provenance is limited.** Historical qualitative failures come from tracked developer reports; ignored raw live logs were not revalidated, and code has changed. Current resolution: historical warnings only, no reused timing distributions or current failure rates. Current real-model conclusions remain unavailable.

## Minor findings and corrections

- Initial diagram PDF conversion omitted SVG marker arrowheads. Resolved by explicit vector arrow polygons and re-rendering.
- Initial model diagram labels touched/exceeded boxes. Resolved by shorter labels without reducing the paper font or changing margins.
- Initial XeTeX build substituted Computer Modern for IEEE Times-family shapes. Corrected via explicit T1 font encoding before class initialization; final build/font verification recorded in `evidence/document_validation.json`.
- No new dense-retrieval equation is needed: the formalization describes actual component composition without pretending the generic retrieval formulation is novel.
- Literature survey entries without validated metadata were excluded. RAG training and parameter-efficient fine-tuning are acknowledged to avoid a false universal retraining comparison.
- Dates and source baseline are explicit. No unpublished human-study sample, hardware specification, funding, ethics approval or plagiarism-detector outcome is claimed.

## Scorecard (out of 10)

| Category | Score | Weakness and required improvement |
|---|---:|---|
| Research problem and motivation | 7 | Concrete state/knowledge/turn boundary; motivate with observed gameplay failures in a future study |
| Novelty and contribution | 4 | Integration of established techniques; strengthen comparison and measured benefit rather than claiming first architecture |
| Related work | 6 | Eight verified foundational sources; expand close recent NPC-framework comparison before venue submission |
| Technical methodology | 7 | Reproducible source trace and control flow; add full semantic evaluation protocol and actual model experiments |
| Architecture clarity | 8 | Three editable vector diagrams and explicit authority boundaries; document deployment-specific interfaces further if expanded |
| Experimental validation | 3 | Offline functional checks only; held-out grounding, ablations and real-backend comparisons required |
| Results and discussion | 6 | Honest traceability and limits; effectiveness questions remain unanswered |
| IEEE formatting | 8 | IEEEtran two-column build, standard margins and five-page target; confirmed authors are included and final build checks must be consulted |
| Academic writing | 8 | Focused, nonpromotional and explicit limitations; revise further with human author/editor input |
| Overall research quality | 5 | Coherent systems draft, currently insufficient evidence for broad effectiveness claims |

## Unsupported claims removed or prohibited

No claims of novel RAG, universal model agnosticism, guaranteed hallucination elimination, superior realism, cross-game generalization, cost savings, 4 GB VRAM feasibility, achieved real-time generation, production delivery guarantees, or the old example's trained-model/voice metrics. Test passage counts are not independent quality ratings. Display acknowledgement is not proof of hearing.

## Required revisions and final recommendation

Document-level revisions are to align diagrams, narrow claims, verify citations, compile and visually inspect within six pages, and package source reproducibly. Those are resolved/verified in the execution checklist and final document-validation artifact. Remaining empirical issues are explicitly retained in the paper rather than hidden.

**Recommendation: major revision before effectiveness-oriented conference submission; conditional go for author review of this implementation-based assignment draft.** Review the confirmed author block and affiliation, obtain genuine independent/teammate review if required, run the stated held-out studies before adding effectiveness claims, and complete the institution's actual submission/originality process. A review-role switch does not create independence.

## Final build follow-up

Five-page output retained after author confirmation and paragraph-spacing revisions. All pages and the three vector diagrams were visually inspected. No undefined citations/references, missing font shapes or overfull boxes remain. One underfull vertical box around floats and engine-pass PDF inclusion-version notices remain documented in the README; final output requests PDF 1.7. Source package clean-room recompilation and document checks are recorded in the final validation artifact.
