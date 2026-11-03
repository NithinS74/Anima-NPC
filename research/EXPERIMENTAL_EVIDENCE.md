> Historical initial-draft record. Superseded for the current paper by REVISION_CHECKLIST.md, SCIENTIFIC_EVALUATION_REPORT.md and IEEE_FINAL_REVIEW.md (2026-11-03).

# Experimental evidence ledger

Date: 2026-11-02. Code baseline `ff9fd7e`, local branch `latest`. Application source was not modified for this study. Commands ran from the repository root using its `.venv`. These results are software-functional evidence; they are not a held-out language-model benchmark.

## Execution and provenance

| ID | Command / method | Actual outcome | Evidence / interpretation |
|---|---|---|---|
| E0 | `.venv/Scripts/python.exe -m pytest -q --tb=short` before dependency synchronization | Collection stopped with 7 errors: missing Chroma, python-docx and Pillow | Failed environment attempt; never counted as passing regression. Existing .venv predated fetched code. |
| E1 | `.venv/Scripts/python.exe -m pip install -r requirements.txt` | Completed successfully | Root pinned dependencies installed; no changes to requirements or runtime source; no embedding weights prepared |
| E2 | `.venv/Scripts/python.exe -m pytest -q --tb=short --junitxml=research/evidence/pytest.xml` | 492 passed, 0 failed, 0 skipped; pytest summary 20.76 s | `evidence/pytest.txt`, `evidence/pytest.xml`; single offline run. Test-suite duration is NOT dialogue inference latency |
| E3 | Parse E2 JUnit testcase class names, prefix-group counts | Counts in table below | `evidence/environment_and_counts.json`; subsets of E2, not independent extra experiments |
| E4 | `.venv/Scripts/python.exe -m pip check` | No broken requirements found | Command output observed in session; dependency consistency, not runtime accuracy |
| E5 | `node --test tests/ui/camera.test.mjs tests/ui/facial.test.mjs` | 7 passed, 0 failed | `evidence/node_tests.txt`; camera/facial mechanics, not immersion ratings |

## Current functional results used in manuscript

| Test grouping | Count (subset of 492) | What it can establish |
|---|---:|---|
| Shared context contracts | 32 | Typed context boundary validation |
| Context unit checks | 65 | Fact filtering/appraisal/conflict behavior on authored cases |
| Generation unit checks | 50 | Prompt/profile/HTTP-mock provider mechanics |
| Validation unit checks | 23 | Structural response acceptance/rejection |
| Runtime unit checks | 19 | Bounded routing, failures and cancellation behavior |
| RAG unit checks | 45 | Adapter/config/evidence/loader behavior |
| RAG storage integration | 13 | Real embedded Chroma storage with deterministic test embeddings |
| Context/RAG integration | 13 | Retrieval/evidence/prompt boundaries with controlled fixtures |
| Other existing Python checks | 232 | Remaining lab/state/adapters/setup/CV tests; no model-quality inference |
| Total Python checks | 492 | Entire configured suite: `tests` and `cv/backend/tests` |

The storage fixture `tests/integration/rag/conftest.py::TestEmbedder` uses normalized 128-bin hashed bag-of-words vectors, not production MiniLM. `test_local_pipeline.py` injects a scripted provider and a public/secret pair; it tests source exclusion, packing and citation mechanics. `test_store.py` covers unchanged ingestion, edit/delete, invalid/failed replacements, unpublished revisions, persistence and locking. No semantic retrieval score is inferred from those cases. Generation HTTP tests use HTTPX MockTransport. CV tests use fake inference. Structural schema/ID checks do not prove truth.

## Environment actually measured

Python 3.11.9; Windows reported as `Windows-10-10.0.26200-SP0`. Installed Pydantic 2.14.2, HTTPX 0.28.1, Chroma 1.5.9, ONNX Runtime 1.23.2, NumPy 2.4.6, pytest 9.2.0, pytest-asyncio 1.4.1.post1, pypdf 6.21.4 and FastAPI 0.162.0. Machine hardware and resource utilization were not measured; no CPU/GPU/RAM claims are made.

## Source-verified parameters, not performance results

- Default RAG chunk size 220 encoder tokens, overlap 32, embedding input guard 254 (`rag/backend/config.py`, `embeddings.py`).
- Dialogue RAG top-k at most 3; public example max_chars 6000 (`rag/config.py`, `configs/rag/dialogue.example.json`).
- Preview defaults: response timeout 3000 ms, model cutoff 2450 ms, retrieval timeout 750 ms, input cap 2048 bytes, output cap 160 tokens (`runtime/preview.py`). Different lab/connector profiles use larger budgets. These are policy settings, not achieved latency or token accuracy.
- At most two model invocations: initial plus one repair. Prompt evidence accounting cap 6000 bytes; each whole passage must also fit final byte budget (`generation/prompt.py`).

## Historical evidence (not rerun/current numerical results)

`docs/reviews/2026-10-31-behavior-quality-audit.md` records a tiny Gemini sample, including an accepted unsupported terminal/procedure answer. `docs/reviews/2026-11-01-openrouter-output-budget.md` records compatible OpenRouter transport and unsupported claims. These are dated qualitative warning cases, not a controlled comparison. Raw ignored logs were not included in this research package or revalidated. Manuscript does not reuse their latency numbers.

## Unavailable metrics and minimum next experiments

| Metric / claim | Current availability | Minimum meaningful next study |
|---|---|---|
| Precision/Recall@k, MRR | Unavailable: no held-out relevance labels | Public licensed lore corpus, independent query relevance judgements and fixed encoder/index settings |
| Groundedness/hallucination rate | Unavailable: structural tests insufficient | Claim-level evidence rubric, unknown-fact cases, independent blinded ratings and agreement |
| Persona/relationship consistency | Unavailable: no blinded evaluator sample | Paired state/persona cases, randomized output order, multiple raters, documented sample size |
| Mean/median/SD inference or end-to-end latency | Unavailable: no current repeated model timing sample | Fixed hardware, endpoint/model/settings, cold/warm separation, successful generation vs repair/fallback routes separately |
| Multiple-model quality/latency comparison | Unavailable: protocol support and historical diagnostics only | Same corpus, prompts, state cases and repeated runs on at least two available compatible backends |
| Cross-game generalization / reduced training cost | Unavailable | At least two distinct authored game packs, measured adaptation effort and controlled quality/cost baseline |
| Live Skyrim / VLM / VRAM fitness | Unavailable | Prepared live prerequisites, disposable game profile, actual outputs/frame times/memory measurements |

No paid provider, private credential, microphone, real-game launch, corpus scan, model download or player-state mutation was used. Knowledge adaptation is demonstrated at storage/configuration level; no universal generalization claim is supported.
