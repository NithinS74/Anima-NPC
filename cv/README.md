# Skyrim CV

Skyrim CV is an optional local screenshot-analysis service. It accepts PNG/JPEG from the Skyrim mod bridge or manual lab uploads, calls a local Ollama VLM and validates a versioned Scene Descriptor response. VLM-only is the default; the incoming optional YOLO wrapper is retained but disabled. It does not modify Mantella.

For the complete installation and two-service workflow, use [SETUP.md](SETUP.md). The Anima-side bridge contract is documented in the repository [README](../README.md#optional-skyrim-cv--context-builder-workflow).

## What is included

- `backend/`: FastAPI API, YOLO wrapper, Ollama VLM client, schema validation, and deterministic unit tests.
- `frontend/`: dependency-free static testing dashboard.
- `samples/`: two small public screenshots for local tests.
- `scripts/test_cv_anima_e2e.py`: real local-service smoke test covering CV → authenticated Anima bridge → Context Builder.
- `docs/`: API, architecture, model-selection and descriptor-schema notes.

Downloaded models, virtual environments, submitted screenshots and annotated artifacts are deliberately local and ignored by Git.

## Quick start

From the repository root on Windows:

```powershell
.\cv\setupcv.bat
.\run_cv.bat
```

In another PowerShell window at the repository root:

```powershell
.\run_anima.bat --offline --rag-config configs/rag/dialogue.example.json --cv-url http://127.0.0.1:8000
```

In Anima, choose an image in **Optional visual reference**, analyze it, and explicitly attach the returned descriptor to the next turn. It enters the Context Builder as `Situation.visual_context` and is passed to a provider only as `untrusted_visual_reference`. It is never promoted to NPC perception, trusted game state, RAG evidence, or durable memory.

## API

```text
GET  /health
GET  /ready
POST /api/v1/analyze       multipart image upload
GET  /api/v1/artifacts/{id}.jpg
```

Run the backend tests from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q cv\backend\tests
```

To verify the integrated path after both services are running:

```powershell
.\cv\test_cv_anima_e2e.bat
```

The end-to-end check uses the authored greeting route, so it is deterministic and does not require a paid provider or populated RAG index.

## Limitations

- No detector weights are bundled or required in default VLM-only mode. The optional YOLO wrapper requires its own reviewed dependencies/weights before enabling it.
- The VLM can make uncertain or incorrect claims. Anima treats all returned visual text as untrusted.
- First local inference can be slow; Anima's CV bridge defaults to a 120-second deadline.
- The [Skyrim connector](../docs/SKYRIM_CONNECTOR.md) supplies automated game capture. Player-camera descriptions remain untrusted references; NPC visibility modeling is not implemented.
