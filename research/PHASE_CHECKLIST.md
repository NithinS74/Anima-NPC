> Historical initial-draft record. Superseded for the current paper by REVISION_CHECKLIST.md, SCIENTIFIC_EVALUATION_REPORT.md and IEEE_FINAL_REVIEW.md (2026-11-03).

# IEEE paper execution checklist

Source of requirements: [complete master task](IEEE_MASTER_TASK.md). Preserve that document verbatim; this file tracks execution and evidence.

Started: 2026-11-02. Working branch: `latest`, baseline `ff9fd7e`.
Status: Phases 1-9 executed for an implementation-based draft. Five-page PDF and source ZIP verified. See [final acceptance reconciliation](FINAL_ACCEPTANCE.md) for restricted claims, missing empirical evidence and the self-review independence limitation.

## Execution rules

- [x] Save the complete user task locally.
- [x] Read repository structure, team workflow and current README.
- [x] Audit implementation before writing the paper.
- [x] Preserve application code, local user edits and private knowledge/credentials.
- [x] Distinguish implemented, partial, planned and proposed work.
- [x] Trace every technical/numerical claim to evidence; never invent metrics.
- [x] Verify primary publications and what each citation supports.
- [x] Keep paper and references within six IEEE conference pages.
- [x] Label a role-switched review as self-review; do not imply independent authorship.
- [x] Keep all work on latest; no publication, push or main merge authorized.

## Phase 1 - Repository and project audit

- [x] Inventory documentation, code, configuration, tests, benchmarks and research assets.
- [x] Read shared contracts and relevant module TRDs.
- [x] Trace player input, normalization, policy, retrieval, context, prompt/provider, validation and delivery.
- [x] Inspect model/provider configuration and knowledge ingestion/switching.
- [x] Record technology versions, implementation status, evidence gaps and inconsistencies.
- [x] Deliver PROJECT_TECHNICAL_AUDIT.md with source paths and limitations.

## Phase 2 - Defensible research contribution

- [x] Define the research problem and literature-supported gap.
- [x] Separate orchestration/integration contribution from established RAG techniques.
- [x] Retain only demonstrated abstraction, grounding and adaptation claims.
- [x] Record contribution-to-evidence mapping.

## Phase 3 - Literature and reference validation

- [x] Inspect existing survey/research documents first.
- [x] Verify title, authors, year, venue, DOI/official URL and claim support.
- [x] Prepare a literature comparison table and validated bibliography.
- [x] Compare RAG, retrieval, grounded dialogue, game agents, orchestration and adaptation.

## Phase 4 - Reproducible architecture figures

- [x] Overall architecture with central orchestration layer.
- [x] Online RAG/orchestration flow with conditional/error paths and offline ingestion.
- [x] Provider abstraction and actual compatible backends.
- [x] Add ingestion figure only if justified.
- [x] Save editable sources and vector exports; inspect at two-column size.

## Phase 5 - Experimental validation

- [x] Inventory existing logs/results; separate tests from quality/performance evidence.
- [x] Run practical existing offline tests/evaluations using project .venv.
- [x] Document exact commands, environment, sample counts, methods and limitations.
- [x] Calculate only supported retrieval/quality/latency metrics.
- [x] Assess backend substitution and knowledge adaptation at demonstrated scope.
- [x] Deliver EXPERIMENTAL_EVIDENCE.md mapping every reported number to provenance.

## Phase 6 - IEEE manuscript

- [x] IEEEtran conference main.tex, bibliography and author placeholders as needed.
- [x] Abstract 150-200 words; 5-7 keywords.
- [x] Introduction; related work; problem/contributions; architecture; methodology.
- [x] Implementation/setup; results/discussion; conclusion/future work.
- [x] Cite figures, tables and verified references; use equations only when useful.
- [x] Explain retrieval, model capability, hallucination, latency and generalization limits.

## Phase 7 - Compile and verify

- [x] Compile successfully; fix references, warnings and overflow where practical.
- [x] Programmatically verify at most six pages including references.
- [x] Render and visually inspect all pages, figures and tables.

## Phase 8 - Critical reviewer-role self-review

- [x] Review correctness, novelty, evidence, reproducibility, language and IEEE layout.
- [x] Score all ten requested categories with reasons and corrections.
- [x] Deliver IEEE_REVIEW_REPORT.md with severity-ranked findings and recommendation.
- [x] Disclose that role switching is self-review rather than independent external review.

## Phase 9 - Revise and package

- [x] Resolve major issues or explicitly document evidence/author blockers.
- [x] Recompile, recount pages and inspect final PDF again.
- [x] Deliver paper.pdf and Overleaf-ready paper_source.zip.
- [x] README: local build, packages, Overleaf, figure regeneration and author editing.
- [x] Validate ZIP contents/reproducibility and absence of secrets/private data.
- [x] Reconcile every final acceptance requirement in the master task.

## Progress and decisions

- 2026-11-02: Preserved user task and established checklist before audit. Repository structure permits documentation without runtime changes/tests. README identifies offline slices and partial production integration; these claims require code/evidence verification.

- 2026-11-02: Phase 1 audit completed against actual context/policy/RAG/provider/validation/lab/Skyrim code; stale planning statements and unsupported old-template metrics excluded.
- 2026-11-02: Contribution mapping and eight verified primary references recorded. No first-framework or universal model-agnostic claim retained.
- 2026-11-02: Existing .venv lacked fetched dependencies; initial test collection failed. Installed the single pinned requirements file. Full rerun: 492 Python checks passed; 7 Node checks passed; pip check found no broken requirements. These are functional checks, not model-quality results.
- 2026-11-02: Three reproducible SVG/PDF diagrams generated. No fourth ingestion figure added because the offline path is already represented. Arrow and label defects corrected by visual review.
- 2026-11-02: Complete IEEEtran manuscript, evidence ledger and ten-category critical reviewer-role self-review delivered. Semantic-quality, retrieval, cross-game and real-time effectiveness claims remain unavailable and are documented rather than fabricated.
- 2026-11-02: User confirmed author order/USNs; RV University retained from supplied project documents. Rebuilt final five-page paper (173-word abstract, six keywords, eight references).
- 2026-11-02: All final pages visually inspected; citations/labels/assets checked. No overfull boxes or font-shape warnings. One underfull float-related vertical box and engine-pass PDF version notices remain documented. Final output is PDF 1.7.
- 2026-11-02: Source-only ZIP extracted to an isolated scratch folder and compiled successfully; normalized text of all five rebuilt pages matches delivered PDF. Source archive uses an explicit file allowlist.
- 2026-11-02: Final acceptance reconciliation records limitations. No independent external review, paid/live model test or game launch occurred. No commit/push/main merge performed.
