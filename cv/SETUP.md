# Set up the optional Skyrim CV service

This folder contains the standalone screenshot-analysis service used by Anima's optional visual-reference bridge. It runs locally, uses YOLO plus a local Ollama VLM, and does not integrate with Mantella.

## Prerequisites

- Windows 10/11
- Python 3.11, Git and Git LFS
- Ollama
- Node.js 18+ only if you want the separate CV dashboard
- About 10 GB free disk space for Python packages and models

After installing Git LFS, run `git lfs install` once. From the repository root, run the provided setup script:

```powershell
.\cv\setupcv.bat
```

It creates `cv\.venv`, installs the CV-only dependencies, creates `cv\backend\.env` from its safe defaults, pulls `qwen2.5vl:3b`, and downloads/checks the configured YOLO weights. The virtual environment, VLM, weights and generated annotated images are local-only and are not committed.

If Ollama is not already running in the background, start it in a separate PowerShell window:

```powershell
ollama serve
```

## Run both local services

Open two PowerShell windows at the repository root.

```powershell
# Terminal 1: CV API
.\cv\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir cv\backend --port 8000
```

```powershell
# Terminal 2: Anima with the optional bridge enabled
.\run_anima.bat --offline --rag-config configs/rag/dialogue.example.json --cv-url http://127.0.0.1:8000
```

Open the URL printed by Anima (normally `http://127.0.0.1:8765`). In **Shape the encounter**, choose a PNG/JPEG under **Optional visual reference**, select **Analyze scene**, then attach it to the next turn. The bridge accepts PNG/JPEG files up to 10 MiB and waits up to 120 seconds by default for an initial local VLM pass. Add `--cv-timeout 180` to the Anima command if needed.

The descriptor is intentionally untrusted visual reference, not NPC perception, game truth, RAG evidence, or durable memory. Offline dialogue checks the connection but does not demonstrate natural visual grounding.

## Verify end to end

With both services running, execute from the repository root:

```powershell
.\cv\test_cv_anima_e2e.bat
```

It submits `cv\samples\sky1.jpeg` through the authenticated Anima bridge and verifies that the returned descriptor reaches `context.visual_context`, without becoming a trusted `ObservedFact`. The dialogue turn is a deterministic greeting, so no paid model or populated RAG index is required.

## Optional dashboard

```powershell
cd cv\frontend
npm run start
```

Open `http://127.0.0.1:5173` and upload a screenshot to inspect the raw CV response. The API must still be running on port 8000.

## Troubleshooting

| Symptom | Action |
|---|---|
| Anima reports `cv_timeout` | Check that Ollama and the CV API are running. First inference can be slow; relaunch Anima with `--cv-timeout 180`. |
| CV `/ready` reports the VLM unavailable | Run `ollama pull qwen2.5vl:3b`; ensure `ollama serve` is running. |
| CV `/ready` reports YOLO unavailable | Rerun `cv\setupcv.bat`, or set `SKYRIM_CV_YOLO_MODEL=yolo11n.pt` in `cv\backend\.env`. |
| Anima lacks the optional visual section | Start Anima with `--cv-url http://127.0.0.1:8000`, then refresh the browser. |
| Port 8000 is busy | Stop the prior API process or use a different free port and pass the matching `--cv-url` to Anima. |
