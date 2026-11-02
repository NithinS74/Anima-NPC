# Local VLM setup

Use Windows/Python 3.11 and the repository's root `.venv` and single pinned
`requirements.txt`. Run `setup.bat --no-update` or `cv/setupcv.bat`; local `.env`,
media and existing model overrides are preserved. No model is downloaded by setup
or by API startup. No second `cv/.venv` is needed.

Install Ollama separately, start its local service, and explicitly prepare the
configured model:

```powershell
ollama pull qwen2.5vl:3b
```

Configuration is in ignored `cv/backend/.env`, copied from `.env.example` by
`cv/setupcv.bat`. The default is VLM-only; `SKYRIM_CV_ENABLE_DETECTOR=false`
avoids loading a second inference stack alongside Skyrim. The legacy optional
YOLO wrapper is retained for future separately reviewed dependency/weights setup.

From the repository root, start the service:

```powershell
.\run_cv.bat
```

`GET http://127.0.0.1:8000/ready` checks whether the configured Ollama model is
available. Health alone does not prove inference readiness. If Ollama is absent,
the CV API still starts but analysis returns an unavailable error. No scene is
fabricated. The VLM can make mistakes; descriptors stay untrusted camera references.

For Skyrim, start a second terminal:

```powershell
.\run_skyrim_connector.bat --cv-url http://127.0.0.1:8000 --attach-visual-reference
```

See the [connector guide](../docs/SKYRIM_CONNECTOR.md) for native build/install,
actor/source RAG bindings and provider configuration. Keep STT/TTS null until
those services are configured. The bridge limits CV wait to 8 seconds by default
and discards old session/revision/expired frames. Warm the VLM separately before
game use; a cold pass may miss this deadline. A failed analysis leaves text
dialogue available. Explicit attachment permits cautious visual wording; it does
not grant the NPC knowledge of HUD, identity, quests or facts behind them.

For manual companion testing instead of the mod:

```powershell
.\run_anima.bat --offline --cv-url http://127.0.0.1:8000
```

Choose an image in **Optional visual reference**, analyze and explicitly attach
it to a turn. The lab allows a separate 120-second analysis timeout, configurable
with `--cv-timeout`; it does not slow ordinary dialogue turns.

All default tests are offline and use fake inference:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short
```

The separate manual-service check `cv/test_cv_anima_e2e.bat` needs running CV and
Anima services. It uses a deterministic greeting, so it checks transport/context
attachment rather than model realism. The optional static dashboard runs with
`npm run start` from `cv/frontend/` and does not add an npm build to the pipeline.

If port 8000 is occupied, use `run_cv.bat --port 8001` and supply the same origin
to the connector/lab. If `/ready` reports VLM unavailable, check Ollama's service
and exact configured model name. Live Skyrim, VLM quality, GPU/game contention
and latency must be measured separately from passing offline tests.
