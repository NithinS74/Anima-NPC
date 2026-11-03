# Skyrim / vision pipeline integration self-review

2 November 2026. Self-review using the repository development/design-review
skills; not an independent review. User authorized checkpointing, merging GitHub
features and completing the connected mod-to-VLM-to-response path. STT/TTS are
explicitly left unconfigured at the user's request.

## Outcome and reviewed boundaries

Checkpoint `d29e8c7` preserves the local Skyrim mod layer. Merge `3c37d82` brings
in `origin/WIthCV` (`35cfb99`) without conflicts. The adapter now connects game
context/capture -> local CV/VLM -> bounded visual descriptor -> existing
context/policy/scoped RAG/provider/validation -> correlated native text/optional
WAV delivery and receipt. No second orchestrator or lab dependency was added.

`src/npc/adapters/skyrim/__main__.py` composes trusted RAG configuration and the
existing provider with a bounded prompt budget. CLI overrides do not rewrite
local configuration. Public defaults use scripted/offline generation; CV and
prompt attachment are explicit settings. STT/TTS remain null.

## Findings and resolutions

Reviewed locations: `src/npc/adapters/skyrim/bridge.py:228` (capture/CV),
`:274` (freshness), `:334` (no-response release);
`src/npc/adapters/skyrim/__main__.py:12` (composition);
`cv/backend/app/perception/pipeline.py:23` (admission), `:37` (retention);
`cv/backend/app/services/image_service.py:23` (decode bounds);
`cv/backend/app/vision/ollama_vlm.py:23` (readiness), `:33` (bounded inference);
`src/npc/vision/client.py:15` (URL validation), `:53` (bounded client).

- Resolved P1: game frames previously stopped at a file reference. Bridge context
  publication now calls the configured CV client. Session/revision/capture TTL
  checks reject obsolete results; missing/expired frames refresh on the next turn.
  Inference failure leaves text dialogue usable. Tests cover these paths.
- Resolved P1: builtin runner did not load RAG and its small prompt cap could
  prevent generated game turns. Composition now loads configured bindings, with
  a 12,000-byte input cap. The end-to-end test asserts real normalized evidence
  reaches the prompt, citation validation succeeds, and the correlated result is
  delivered exactly through the native command/receipt protocol.
- Resolved P1: a runner without a response retained the pending turn forever.
  It now records failure and releases the request without inventing speech.
- Resolved P1: incoming CV inference had no global admission bound; cancellation
  could otherwise permit overlapping native inference. One slot is retained until
  the worker settles, even after caller cancellation. Annotated output retains
  at most 100 images. Image dimensions are checked before pixel decoding.
- Resolved P2: CV and VLM response bodies were buffered without a streaming cap.
  Limits are now 128 KB and 256 KB respectively; VLM image size, detections, output
  tokens and total transport time are bounded. Malformed responses/model lists
  and invalid URL ports have explicit failure tests.
- Resolved P2: incoming CV setup used a second environment/unpinned requirements.
  Root `.venv` and pinned `requirements.txt` now supply image upload and test
  dependencies; CV tests run in the default suite. Default VLM-only mode avoids
  installing another detector/GPU stack. The incoming YOLO adapter is retained
  but disabled and not provisioned; enabling it needs separately pinned
  dependencies/weights and resource verification. No weights were downloaded.
- Preserved boundary: camera descriptions remain untrusted reference data, never
  canonical facts, retrieval eligibility, citations, identity or heard memory.
  Explicit attachment has tests for both enabled and disabled behavior. This is
  an uncertain visual wording feature, not implemented NPC visibility modeling.

## Verification

- Baseline before merge: `.venv/Scripts/python.exe -m pytest -q --tb=short`:
  **438 passed**.
- Final shared offline regression, same command: **492 passed**. This includes
  CV backend tests, actual CV ASGI/schema and Ollama HTTP client paths with fake
  inference, RAG/prompt/citation checks, native command acknowledgements, stale
  frames, no-response release, cancellation/admission and failure cases.
- `node --test tests/ui/camera.test.mjs tests/ui/facial.test.mjs`: **7 passed**.
  `node --check tools/npc_lab/web/app.js` and
  `node --check cv/frontend/src/app.js`: passed.
- `.venv/Scripts/python.exe -m pip check`: no broken requirements.
- Changed Markdown links and `git diff --check`: passed.
- `.venv/Scripts/python.exe scripts/build_skyrim_connector.py`: Windows x64
  Release DLL rebuilt, CTest **1/1 passed**, ZIP packaged at
  `output/skyrim-mod/AnimaConnector.zip`. No game installation was changed.
- Actual loopback Uvicorn startup for both CV and connector passed using isolated
  temporary configuration, an offline provider and disabled game capture. CV
  `/health` returned OK; `/ready` correctly returned false because Ollama was
  unreachable (`ConnectError`). Connector `/v1/health` reported configured CV
  and preview mode. Experiment-owned processes were terminated.
- Initial focused pytest/Node attempts encountered sandbox temporary-directory /
  process restrictions; authorized reruns passed. An initial startup experiment
  used too short a readiness-client timeout; correcting that experiment yielded
  the explicit unavailable-model result above, not inference success.

## Remaining gates and verdict

P1 for live readiness: this environment has no reachable configured Ollama VLM.
Install/start Ollama and explicitly prepare the model before testing real image
analysis. No real VLM inference, paid dialogue-provider call, microphone recording
or live Skyrim launch was performed. VLM grounding, cold/warm latency and game
frame-time/VRAM contention remain unmeasured.

P1 for live Skyrim: the matching
`Data/SKSE/Plugins/versionlib-1-6-318-0.bin` was not found in the referenced game
directory. Verify matching SKSE/Address Library, menu/actor extraction,
borderless capture, subtitles and interruption/load behavior on a disposable
profile. Native reports are best effort; production durable outbox, reliable
heard-memory and historical save reconstruction remain outside this slice.

Verdict: connected path built and offline/build verified; conditional go for
controlled live testing after prerequisites. It is not a claim that every planned
TRD module, perceptual accuracy or production delivery guarantee is complete.
