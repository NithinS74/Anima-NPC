# Critical revision checklist

Requirements: [full revision task](IEEE_REVISION_TASK.md). Plan/review: [revision audit](REVISION_AUDIT.md).

- [x] Preserve request and audit existing manuscript/code/evidence.
- [x] Record isolated evaluation plan and labelled plan self-review before implementation.
- [x] Check real provider, encoder, game and capture feasibility.
- [x] Define fixed public corpus, queries, labels and provenance.
- [x] Implement isolated evaluation and meaningful offline tests.
- [x] Execute feasible real-embedding/index/model experiments; preserve raw results.
- [x] Analyze results and document pending human/backend/game conditions.
- [x] Replace three diagrams with native TikZ; add ingestion figure.
- [x] Apply exact approved title and preserve author order/USNs.
- [x] Rewrite results after measurements; reduce test-count prominence.
- [x] Run focused/full regression and document implementation self-review.
- [x] Build <=6 pages, visually review and revise.
- [x] Produce final critical self-review with honest scores and remaining gates.
- [x] Package Overleaf sources, extract/recompile and verify.


## Execution outcomes — 2026-11-03

- Runtime baseline ff9fd7e unchanged. Original full task and critical revision request retained; initial draft backed up locally. Exact approved title and confirmed authors/USNs appear in source and PDF metadata.
- Real CPU MiniLM/Chroma experiment: 12 original fictional documents, 24 author-labelled queries. P@1, Recall@3, MRR 1.00; P@3 0.333 at its single-relevant-source ceiling. Independent label adjudication remains pending.
- Actual model experiment: 7 matched pairs plus 1 unmatched RAG fallback, 17 provider calls. Literal target mentions 7/7 vs 1/7; this is not a semantic-grounding score. Rate limiting stopped the study; boundary and post-update generation trials remain unexecuted.
- Thirty warm retrievals measured; mean 19.96 ms, median 19.83, SD 1.89, descriptive P95 23.00. One fresh-process query 257.95 ms; update sync 216.60 ms. Tiny-corpus and uncontrolled network/background-game limitations recorded.
- Four native TikZ figures compiled. First three appear in manuscript; separate ingestion diagram is supplied without redundant main-paper space. Initial layout/label defects fixed after visual review.
- User-launched SKSE checked directly: runtime 1.7.104 loaded SKSE_HTTP/Mantella-related plugins, no AnimaConnector; bridge unavailable. Source explicitly guards 1.6.318.0. No Anima in-game interaction or screenshot claimed; installation/save unchanged.
- Seventeen meaningful offline harness tests; current full regression 509 passed. Initial invalid two-message test fixtures and metric/partial-pair failure paths documented. Core code/requirements unchanged.
- Final self-review is labelled; human ratings, independent peer review, real multi-backend comparison and compatible in-game proof remain external research gates.
- All publication package validation/rebuild results are recorded in research/evidence/revision_document_validation.json and revision_zip_rebuild_verification.json. Checklist completion denotes execution and explicit gap reporting, not completion of unavailable experiments.
## Final execution report

1. Replaced title/prose/results and old SVG figures with measured pilot-study content and native grouped TikZ.
2. Executed actual 24-query MiniLM/Chroma retrieval, 30 warm timings, one fresh-process query, document update/retrieval, and 17 real provider requests yielding seven matched pairs plus one fallback.
3. Raw results/aggregation and label limits are recorded in SCIENTIFIC_EVALUATION_REPORT.md; no semantic/persona success score is invented.
4. Independent labels/raters, missing boundary/update generation, second backend and live delivery remain pending for the stated reasons.
5. No genuine Anima in-game screenshot captured; actual running modules/logs checked and blocker documented.
6. Four native TikZ diagrams compiled; three used in the manuscript.
7. Five pages including references.
8. Main build and extracted source-ZIP rebuild succeed; no undefined labels/citations, overfull boxes or font-shape warnings. Underfull layout notices visually checked and documented.
9. Final review is a labelled self-review: conditional go for a pilot draft, major empirical revision before strong semantic/game claims.
10. Overleaf ZIP: research/ieee_paper/paper_source.zip. No commit/push/main merge.


## Native compatibility follow-up (2026-11-03)

Separate from the model/retrieval study at baseline ff9fd7e, AnimaConnector 0.2.0 was built for exact runtimes 1.6.318.0 and 1.7.104.0. The current 1.7.104 game loaded it and supplied genuine Jenassa context. The offline authored greeting returned ?What do you need??; native receipts at 05:16:18.568217 UTC and 05:16:20.627733 UTC reported started/completed for delivery f7557716ca5944b38945b476583e1788. An earlier run reported started/interrupted when the menu closed. This verifies one text-delivery smoke test and interruption handling; it is not evidence for live model/RAG quality, audible voice, broad mod compatibility or latency performance. No paid calls were made. The old runtime remains build/unit checked without a live executable. Full Python regression 514 passed; native CTest 2/2 passed.

Original screenshots remain in ignored output/skyrim-mod. They have a large black region and cannot show a clear interaction, so no unsuitable screenshot is inserted into the paper. A clean genuine capture remains pending. See docs/reviews/2026-11-03-dual-skyrim-runtime.md for the labelled implementation self-review.
