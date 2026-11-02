# Testing and evaluation report

Automated unit and mocked pipeline/API tests are run with `pytest`; the final command results are recorded in the delivery report. External models are mocked there deliberately. A live check requires Ollama serving the configured pulled model, compatible Ultralytics/PyTorch weights, and a manually supplied screenshot. The current implementation exercises invalid images, oversized uploads, detection response mapping, descriptor constraints, annotation creation, malformed VLM JSON, schema-invalid VLM JSON, and API health/error handling.

No Skyrim screenshots or ground truth labels are included. Therefore no mAP, accuracy, or qualitative claims are reported. For each user-provided image, record relevant/missed detections, bounding-box alignment, unsupported VLM claims, uncertainty, and per-stage timings. Include tavern, outdoor, NPC, weapon/shield, creature, crowded, low-light, and HUD cases where available.

## Environment audit (2026-11-01)

The implementation was created in a previously empty, non-Git directory on macOS 26.6 arm64 with Python 3.11.0, Node 23.7.0, and about 64 GiB free. Ollama was installed but its local server was unreachable (`ConnectError` in the readiness check). PyTorch 2.15.0 was installed for this project and reported `mps_available=False`, so no M2/MPS latency is recorded. `pytest -q` passed 12 tests; dashboard lint and static build passed. Live YOLO/VLM inference remains unverified because the configured weights/model were not locally available and no manual Skyrim screenshot was supplied.
