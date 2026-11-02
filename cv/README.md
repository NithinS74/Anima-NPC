# Skyrim CV

Skyrim CV is an optional, standalone local screenshot-analysis service for this Anima repository. It accepts a manually selected PNG/JPEG, combines general-object detection with a local Ollama VLM, validates a versioned Scene Descriptor JSON response, and exposes a small testing dashboard. It does not modify or integrate with Mantella.

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
.\cv\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv\backend --port 8000
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
.\cv\.venv\Scripts\python.exe -m pytest -q cv\backend\tests
```

To verify the integrated path after both services are running:

```powershell
.\cv\test_cv_anima_e2e.bat
```

The end-to-end check uses the authored greeting route, so it is deterministic and does not require a paid provider or populated RAG index.

## Limitations

- The bundled YOLO model is general-purpose rather than Skyrim-specific and can produce false positives.
- The VLM can make uncertain or incorrect claims. Anima treats all returned visual text as untrusted.
- First local inference can be slow; Anima's CV bridge defaults to a 120-second deadline.
- This is a manual developer/testing workflow, not automated game capture or NPC visibility modeling.
