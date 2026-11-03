# Final IEEE review — revised manuscript

Date: 2026-11-03. **Reviewer-role self-review, not independent external peer review.** Evaluated the revised source/PDF against runtime ff9fd7e and saved experiment artifacts. The complete user revision request is in IEEE_REVISION_TASK.md. No reviewer agent or fabricated human judge was used.

## Assessment

The revision materially improves the paper: the exact approved title is applied to source/PDF metadata; three main diagrams are now grouped native TikZ; an additional native ingestion diagram is supplied; software-test tables no longer dominate results; actual MiniLM/Chroma ranking, index updates, warm/fresh-process timing, and real-model paired outputs are reported. The paper remains a small controlled pilot, not a completed independent semantic evaluation or verified game deployment.

## Major findings and resolutions

1. **P1: insufficient independent grounding/persona evidence remains.** Seven matched pairs contain one sample per condition and only answerable questions. A literal target mention can coexist with an unsupported claim (no-RAG guard/cargo-manifest example). Correction implemented: targets are named literal diagnostics, not grounding accuracy; persona/claim-level ratings and unexecuted boundary cases remain pending. Two blank blinded sheets are supplied. No unsupported semantic success rate appears.
2. **P1: retrieval gold lacks independent adjudication.** Twenty-four queries over twelve authored documents are clean and easy; each relevant source ranks first. Correction implemented: exact provenance, query/source counts, fixed labels, P@3 ceiling 1/3 and limited external validity are prominent. Perfect controlled scores do not establish broad game relevance. Independent natural-corpus evaluation remains required.
3. **P1: quota-dependent incomplete generation study.** The study stops at a real provider rate limit after seventeen calls, leaving seven pairs plus one unmatched RAG fallback. Correction implemented: pairing excludes the unmatched case only from matched comparisons; all-observed failure/latency accounting retains it. Four boundary questions and post-update generation are explicitly unexecuted. No extra trial is silently imputed or billed.
4. **P1: no Anima in-game interaction established.** The user's running SKSE session was inspected directly. It loads SKSE_HTTP and Mantella-related plugins, but no AnimaConnector; the bridge is unavailable. Current native source explicitly guards 1.6.318.0 while the executable is 1.7.104.0. Correction implemented: no fake/stock/web screenshot; exact blocker recorded. Porting/installing/restarting a compatible build is separate work; another plugin's success is not Anima compatibility.
5. **P2: implemented RAG-path confound.** RAG mode adds prompt instructions as well as evidence. Correction implemented: the text calls it an ablation of the implemented RAG path; model/persona/question/caps are matched but no document-only causal effect is claimed. A future empty-evidence condition with identical system instructions would improve attribution.
6. **P2: backend and update scope.** One real model produced study outputs; other readiness probes are not a comparison. Index update proves new retrieval content, not a post-update generated answer or unchanged remote parameter hashes. Correction implemented: RQ4 is structural; RQ5 retrieval-level only. No universal API compatibility or measured retraining-cost advantage claimed.
7. **P2: timing scope.** Seven model pairs and thirty tiny-corpus retrievals are not real-time production distributions. Skyrim was running during model calls; network/CPU contention is uncontrolled. Correction implemented: response-ready/development caps distinguished from live delivery, P95 omitted for seven pairs, cold query is one observation and GPU/frame-time outcomes unavailable.

## Presentation and implementation corrections

- Initial native TikZ drafts overlapped because fixed node coordinates did not account for text wrapping; pipeline changed to relative placement and architecture spacing expanded.
- A custom `label` style shadowed TikZ's built-in label mechanism; renamed it so component-group headings render. Provider wording shortened and ingestion spacing corrected.
- Old SVG generator/assets are superseded and removed from the active source package to avoid mixing old elementary figures with the new native ones.
- Full approved title and confirmed author order/USNs preserved. RV University retained.
- Existing requirements and runtime code unchanged. Seventeen new offline evaluation tests check real failure/denominator/blinding invariants; full regression actually passed **509 tests**. The previous unit-fixture two-message failure was corrected without weakening contracts.

## Scores out of 10

| Category | Score | Remaining requirement |
|---|---:|---|
| Research contribution | 5 | Established techniques integrated; contribution remains a controlled systems study |
| Methodology | 6 | Matched settings and raw data improve reproducibility; independent labels, empty-evidence control and repetition needed |
| Experimental quality | 4 | Real measurements now exist, but tiny authored data and incomplete quota-limited generation constrain validity |
| Architecture clarity | 8 | Native grouped boundaries and control/error paths; additional ingestion source supplied |
| Results and discussion | 7 | Denominators/failures/limitations explicit; semantic and cross-backend findings still absent |
| Related work | 6 | Eight verified primary sources; closer recent framework comparison would strengthen venue positioning |
| Academic writing | 8 | Precise claims and caveats; further human author editing appropriate |
| IEEE presentation | 8 | IEEEtran, <=6 pages, native vector figures, verified title/author metadata; final build/visual report is authoritative |

## Verdict

**Conditional go for author review of a measured pilot-study draft; major revision before making strong persona/semantic-grounding or production-game claims.** The revision addresses the original software-report problem with actual observations, without pretending the missing independent/game/backend studies are complete. Remaining empirical gates are visible rather than critical factual misrepresentations. Genuine independent teammate/peer review and institutional originality checks remain outside this role-switched self-review.


## Native compatibility follow-up (2026-11-03)

Separate from the model/retrieval study at baseline ff9fd7e, AnimaConnector 0.2.0 was built for exact runtimes 1.6.318.0 and 1.7.104.0. The current 1.7.104 game loaded it and supplied genuine Jenassa context. The offline authored greeting returned ?What do you need??; native receipts at 05:16:18.568217 UTC and 05:16:20.627733 UTC reported started/completed for delivery f7557716ca5944b38945b476583e1788. An earlier run reported started/interrupted when the menu closed. This verifies one text-delivery smoke test and interruption handling; it is not evidence for live model/RAG quality, audible voice, broad mod compatibility or latency performance. No paid calls were made. The old runtime remains build/unit checked without a live executable. Full Python regression 514 passed; native CTest 2/2 passed.

Original screenshots remain in ignored output/skyrim-mod. They have a large black region and cannot show a clear interaction, so no unsuitable screenshot is inserted into the paper. A clean genuine capture remains pending. See docs/reviews/2026-11-03-dual-skyrim-runtime.md for the labelled implementation self-review.
