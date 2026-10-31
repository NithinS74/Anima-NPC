# Set up Anima

## Windows: recommended path for teammates

Install **Python 3.11** (with the Python launcher) and Git. Clone the repository, then double-click **[setup.bat](setup.bat)**. No administrator privileges, GPU, Node, Skyrim or API key are needed for basic setup.

```powershell
git clone https://github.com/mohanchandrass/NPC.git
cd NPC
.\setup.bat
.\run_anima.bat --offline
```

`setup.bat` finds Python 3.11, creates/reuses the project's `.venv`, installs the single pinned `requirements.txt`, installs the project in editable mode, checks dependencies, creates `.env` from `.env.example` **only if absent**, and runs the full offline Python regression. It stops on a failed step and keeps the result visible. Existing credentials, saved state and game files are preserved. It does not install Python globally, make LLM calls, download model weights, or import private game assets. For automation use `setup.bat --no-pause`; it returns a nonzero code on failure. Rerunning is supported.

The first launch above is an **offline preview with scripted responses**. The four personas and role-specific backgrounds work immediately; actual Skyrim appearances, fonts and voices are optional local assets.

## Enable real model responses

Open the newly created local `.env` and set your own key and model. For the default Gemini profile:

```dotenv
GEMINI_API_KEY=your-own-key
NPC_LLM_MODEL=gemini-3.5-flash-lite
```

This model was tested locally on 2026-10-31; availability/quotas may change. Model selection is configurable, not hardcoded. Never commit `.env`, paste keys into shared chat, or put them in public YAML/browser code. `setup.bat` will not replace an existing `.env`.

Run `run_anima.bat` for live calls (may incur API charges). Keep the terminal open; Ctrl+C stops it. Restart after editing provider settings, then refresh the browser. Default URL: `http://127.0.0.1:8765`. Another instance can use `--port 8767`.

For OpenRouter, set `OPENROUTER_API_KEY` and its model ID, then run:

```powershell
.\run_anima.bat --config configs/providers/openrouter.yaml
```

See [provider configuration](configs/providers/README.md). OpenRouter is covered offline but remains untested live. Manual testing allows 30 seconds by default (`--development-timeout 1..60`); `--realtime` preserves the core three-second limit. Timeout, quota, authentication and server failures remain typed fallbacks; a fallback is not successful model generation.

## Optional game models, native expressions, voices and actual fonts

These assets are **not in Git**. Every teammate needs their own local installation/source assets to reproduce them. Basic setup does not require them. Follow [local media setup](configs/npc_lab/README.md):

| Optional feature | Local prerequisite |
|---|---|
| Actual character models and native blink/speech/mood morphs | Installed Skyrim SE; portable Blender 4.5.9 + PyNifly 30.2.0; run the importer with `--facial` |
| Mantella Piper voices | Installed MantellaSoftware/Piper; run the existing voice-copy command |
| Original Skyrim Futura dialogue/interface font | Installed English Skyrim SE; Java + portable FFDec 26.4.0; run the font importer |

Private files stay under ignored `assets/private/npc_lab/`; portable conversion tools under `.tools/`. Game files are only read, not changed. Without private fonts, Anima uses openly licensed fallback fonts and says so in the inspector. The four role scenes are original public illustrations, not Skyrim screenshots. Facial movement uses native game morph shapes with app-driven blink/mood/speech timing; it is not full skeletal animation or phoneme-aligned lip sync.

## Common setup issues

| Symptom | Action |
|---|---|
| Python 3.11 not found | Install Python 3.11 and its launcher; reopen the terminal and retry. |
| Existing `.venv` is incomplete or uses another Python | Move it aside manually and rerun. Setup never deletes an existing environment automatically. |
| Package installation fails | Restore internet access or fix the reported pip/index error, then rerun setup. |
| Missing model/key on live launch | Fill `.env`, or use `run_anima.bat --offline` for the scripted preview. |
| Port already in use | Stop the existing Anima terminal or use another `--port`. |
| Illustrations/no voice/fallback font | Optional private assets have not been imported; the core app still works. |
| API fallback | Inspect the error code and exact input in **Inspect context**; check network, model availability and quota. |

## Manual commands and contributor checks

If you prefer explicit PowerShell commands:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Copy `.env.example` only if `.env` does not already exist. Activation is optional; explicit paths avoid PowerShell execution-policy issues. Python 3.11/Windows is the verified setup; other combinations need testing. There is one requirements file. `pyproject.toml` contains package metadata/test discovery, not a competing dependency lock.

Use the [development workflow](.agents/skills/develop-npc-component/SKILL.md), [repository structure](docs/REPOSITORY_STRUCTURE.md), [context preview](docs/CONTEXT_BUILDER.md) and [generation guide](docs/GENERATION_VALIDATION.md). Optional UI tests require Node 22+ and Chrome; they are separate from basic setup and documented in [Anima](docs/ANIMA.md).

Current implementation is a core context/policy/generation/structural-validation slice with initial social persistence and a separate local companion. RAG, production game delivery and hosting are future work. `.venv`, `.tools`, `.toolds`, `.env`, generated state/logs and private assets are ignored. The user-controlled KB folder is not automatically ignored; check privacy before tracking its contents.
