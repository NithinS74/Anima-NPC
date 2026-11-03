# Scientific evaluation report — critical revision

Date: 2026-11-03. Runtime baseline `ff9fd7e95beac344b43e836027bc43f3e5c7b5bc`; no application runtime edits. Scripts, public datasets, raw outputs and analysis accompany the manuscript. The research title is **Persona-Aware, Knowledge-Bounded NPC Dialogue Through Model-Agnostic LLM Orchestration**.

## Executed measurements and their limits

| Experiment | Execution | Verified observations | Status / remaining gate |
|---|---|---|---|
| A: dense retrieval | Actual ONNX CPU MiniLM and embedded Chroma; 12 authored documents / 12 chunks; 24 fixed queries; top-k=3 | P@1=1.00, P@3=0.333, Recall@3=1.00, MRR=1.00 | Controlled mechanism assessment completed; independent relevance adjudication and larger natural-game corpus pending |
| B: RAG/no-RAG | Real configured gemini-3.5-flash-lite through unchanged PreviewRunner; alternating condition order | 7 complete pairs; literal target mentioned in 7/7 enabled and 1/7 disabled outputs; one additional unpaired RAG fallback | Partial; these are predeclared literal mentions, NOT semantic-grounding scores; four boundary prompts not reached before quota |
| C: persona/knowledge consistency | Four authored roles in actual calls; two shuffled, condition-blinded rating sheets generated | No human ratings completed | Pending independent evaluators; no persona score, claim-support percentage or agreement manufactured |
| D: backend comparison | Authenticated model listing and bounded readiness probes | One model produced study responses; other probes returned not-found/unavailable; configured unsupported reasoning setting returned bad-request | No real multi-backend comparison; structural abstraction evidence only |
| E: knowledge update | Actual source write + reindex + source-bound retrieval before/after | Forge changed from northern well to southern mill; new revision ID; sync 216.60 ms; no application training call | Retrieval-level portion completed; post-update generated answer not reached; remote parameter hashes inaccessible |
| F: timing | 30 warm retrievals; one fresh-process query; actual model response-ready records | Warm total retrieval mean 19.96 ms, median 19.83, sample SD 1.89; descriptive nearest-rank P95 23.00; fresh process query 257.95 ms | Local retrieval and small model timing sample measured; no game delivery/capture/frame-time distributions |

## Dataset and relevance methodology

Original Cedarvale fantasy-world fiction is in `fixtures/evaluation/paper_revision/`; it is not Skyrim lore and is not presented as an established benchmark. The installed knowledge directory had only its README. Twelve topic files each remain a single 220-token/32-overlap chunk. Queries and single-source labels were written before execution; raw results preserve hashes of query and corpus files. Gold is independent of ranking output, but was assigned by the same experiment author. This does **not** satisfy independent human relevance adjudication. Larger licensed/natural data and independent label review are required before broader effectiveness claims.

Each query has one relevant source, so P@3 has ceiling 1/3. Missing positions count incorrect. Metric definitions and validation are tested in `tests/unit/research/test_paper_evaluation.py`. No scores were inferred from passing software tests.

Generation combines the same public documents into a single bound public file, plus a separate excluded fictional private-code document. It therefore uses a different chunk layout from experiment A. Four new Cedarvale roles are authored explicitly; they do not silently reuse the lab Iona profile (which is a cargo registrar). Paired scenarios match identity, persona, neutral relationships, input, model and caps; no legacy smith location/state observations leak the answer. The enabled path adds the application's RAG instructions and passages, so this contrast is the implemented RAG path, not document-only causal isolation.

## Real model execution and stopping rule

The configured compatible Gemini model is `gemini-3.5-flash-lite`; the key was read locally and never stored in results. Existing profile reasoning setting was preserved for the study. Limits: 400 output tokens, 12,000 input bytes, 30-s per transport call, 60-s development response deadline/59-s model cutoff, at most one repair per turn, and a 54-request study cap. API sampling defaults apply; no deterministic sampling seed is claimed. Condition order alternates by case.

Seventeen study provider requests produced 15 final response records: 14 accepted generated responses (one with repair) and one fallback. The checkpoint RAG case's first candidate was invalid; its repair request returned `provider_rate_limited`, setting the fatal gate and stopping further calls. Seven matched pairs were complete; the eighth RAG trial has no no-RAG counterpart and is excluded from paired target/latency comparisons while retained in failure and all-observed accounting. No paid rerun was launched to fill missing rows. Prior readiness smoke requests are separate from these 17.

| Mode | Complete pairs | Target mentions | Paired mean ready ms | Paired median ms | Sample SD ms | All-observed generated/fallback |
|---|---:|---:|---:|---:|---:|---|
| No RAG | 7 | 1/7 | 1187.93 | 1201.42 | 373.12 | 7 generated / 0 fallback |
| RAG | 7 | 7/7 | 1263.66 | 1104.94 | 354.45 | 7 generated / 1 fallback (8 records) |

All-observed RAG mean is 1395.58 ms; no P95 is estimated for seven pairs. Input/output usage sums are in `analysis/generation_summary.json`; failed requests can have incomplete usage. No inference cost is invented.

Literal target matching is explicitly limited: the no-RAG guard answer contains `permit` but invents a cargo-manifest procedure. It therefore counts as a target mention without establishing faithfulness. Other no-RAG examples invent a central-well clinic or calendula/honey salve, whereas enabled outputs use the supplied eastern-gate clinic and silverleaf. These examples are qualitative observations, not an independently rated hallucination rate.

## Local latency, environment and update

Recorded CPU: Intel Core i7-13700HX, 16 cores / 24 logical processors; reported RAM 16,886,128,640 bytes (approximately 15.7 GiB); Windows, Python 3.11.9. Production encoder is all-MiniLM-L6-v2-onnx-v1 (384 dimensions, CPUExecutionProvider), Chroma 1.5.9 and ONNX Runtime 1.23.2. No GPU/VRAM fitness claim is made.

Warm query embedding: mean 16.48 ms, median 16.59, SD 1.72. Chroma vector-query call: mean 2.17 ms, median 2.15, SD 0.43. Whole retrieval: mean 19.96 ms, median 19.83, SD 1.89. The single fresh-process query took 257.95 ms (embedding 225.85, vector query 31.41), after assets were already downloaded and an index existed. This is one first-use observation, not a disk-cold distribution. Initial indexing including first model use took 769.40 ms; update sync 216.60 ms. Raw per-trial observations and before/after passage/revision records are preserved.

The user launched Skyrim during real-model experiments. Network and background-game contention were not controlled. Response-ready times are server-side development-profile measurements; acquisition, native display, speech and frame time were not measured. The encoder timing experiment used a tiny local authored corpus. No 3-s real-time guarantee, scalable-corpus performance or statistical superiority follows.

## Actual running-game verification

After the user offered and launched SKSE, the actual process path was `D:/steam/steamapps/common/Skyrim Special Edition/SkyrimSE.exe`, FileVersion 1.7.104.0. Loaded modules included `skse64_1_7_104.dll` and SKSE_HTTP.dll from a mod-manager fix. The actual SKSE log reported SKSE_HTTP loaded correctly and checked Mantella-related plugins, but no AnimaConnector entry. Anima was absent from loaded modules and the standard plugin directory; bridge health on port 8768 was unreachable. Current native source explicitly declares and enforces 1.6.318.0 (`plugin.cpp:408,413`). Virtual mod paths do not resolve that code guard.

Consequently, the running game was checked directly rather than rejected only from documentation, but no Anima interaction was demonstrated. No genuine Anima in-game screenshot was captured, no screenshot was fabricated or relabelled, and no game installation/save was changed. A compatible installed connector and running bridge/restart test are required. Another HTTP plugin working does not prove this connector's compatibility. See `raw_results/game_availability.md`.

## Reproducible artifacts

- `experiments/scripts/evaluate.py`: fixed-label metrics, actual retrieval/warm timings and update; `--cold` fresh-process measurement.
- `experiments/scripts/generate_pairs.py`: capped actual-provider study; persists after each response and stops on auth/quota; refuses silent reruns over prior results.
- `experiments/scripts/analyze.py`: matched-pair vs all-observed accounting and blank blinded rater sheets; no API calls.
- `experiments/raw_results/retrieval_update.json`, `cold_query.json`, `paired_generation.json`: full observed evidence.
- `experiments/analysis/generation_summary.json`: computed aggregate values; paired/failure denominators explicit.
- `experiments/analysis/pending_rater_1.csv`, `pending_rater_2.csv`: explicitly unfilled judgments; condition key separate.
- `research/evidence/revision_pytest.xml`: full offline regression including meaningful evaluation-component checks.

## Implementation self-review and remaining research gates

Plan and implementation reviews are labelled self-reviews. Tests cover rank denominators, invalid/duplicate labels, nonfinite timings, unsafe run IDs, matched-scenario isolation, bounded transport/call budget, fatal auth/quota, unmatched failures, empty experiments and unfilled human ratings. Initial unit fixtures violated the existing two-message PromptPackage contract; fixtures were corrected without weakening the contract. Diagram review caught initial spacing/label-key defects; native TeX sources were corrected before final layout review.

Remaining substantive gates: independent relevance labels and semantic raters; larger/held-out and repeated samples; missing boundary prompts; completed post-update generation; controlled second real backend; compatible live-game interaction; controlled latency/resource distribution. These are reported as pending, not disguised by 509 executed functional checks or perfect tiny-corpus ranking. Final full regression count is taken from its actual XML/log, not assumed.


## Native compatibility follow-up (2026-11-03)

Separate from the model/retrieval study at baseline ff9fd7e, AnimaConnector 0.2.0 was built for exact runtimes 1.6.318.0 and 1.7.104.0. The current 1.7.104 game loaded it and supplied genuine Jenassa context. The offline authored greeting returned ?What do you need??; native receipts at 05:16:18.568217 UTC and 05:16:20.627733 UTC reported started/completed for delivery f7557716ca5944b38945b476583e1788. An earlier run reported started/interrupted when the menu closed. This verifies one text-delivery smoke test and interruption handling; it is not evidence for live model/RAG quality, audible voice, broad mod compatibility or latency performance. No paid calls were made. The old runtime remains build/unit checked without a live executable. Full Python regression 514 passed; native CTest 2/2 passed.

Original screenshots remain in ignored output/skyrim-mod. They have a large black region and cannot show a clear interaction, so no unsuitable screenshot is inserted into the paper. A clean genuine capture remains pending. See docs/reviews/2026-11-03-dual-skyrim-runtime.md for the labelled implementation self-review.
