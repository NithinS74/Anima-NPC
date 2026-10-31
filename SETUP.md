# Development setup

Use Python 3.11 in a project virtual environment. Context construction and the generation/validation CLI work; a full NPC server is not implemented yet.

PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps --no-build-isolation
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
```

There is one dependency file: `requirements.txt`, containing the pinned API-first core/development environment verified on Windows/Python 3.11. Small test/document-review packages are included for the team's shared setup. Update pins deliberately with compatibility checks. Other OS/Python combinations need verification before claiming support.

Activation is optional; explicit interpreter paths ensure the right environment even when PowerShell activation policy is restrictive. If desired: `.\.venv\Scripts\Activate.ps1`.

I05 will add Chroma and the selected CPU embedding/parser packages to this same file when integrated and tested. No GPU/local LLM, Torch, CV or speech stack is required now. The RAG module will create/manage local storage and model assets; users will not manually provision a Chroma server for the embedded prototype.

Copy `.env.example` to `.env` when API testing needs provider settings. Keep keys in the backend, never browser JavaScript or commits. No model/provider is hardcoded. Tests/CI use fakes by default; dependency setup launches no game/server, records no audio and makes no paid model calls.

The `.venv`, `.tools` (and typo `.toolds`), temporary PDF renderings/extractions, runtime databases, logs, captures and model files are ignored. The current user-edited ignore file does not exclude `Knowledge base/kb`; check corpus privacy/licensing before tracking any contents. The reusable [reviewer skill](.agents/skills/review-npc-design/SKILL.md) is committed; invoke `$review-npc-design` in a compatible agent or ask it to read that file explicitly.

Run the [offline context scenarios](docs/CONTEXT_BUILDER.md) with `.\.venv\Scripts\python.exe -m npc.context fixtures/scenarios/smith_closing.json`. Editable install exposes `npc` from `src/` without copying files. Pinned setuptools/wheel build tools are in the single requirements file; `--no-build-isolation` uses that verified environment. `pyproject.toml` supplies package metadata and pytest discovery, not a second lock file.

Run the [generation/validation preview](docs/GENERATION_VALIDATION.md) with `.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json`. This uses a fake by default. Public [provider profiles](configs/providers/README.md) cover OpenRouter and Gemini; use the matching local key plus `NPC_LLM_MODEL` and explicit `--live --config ...` for an API test. An initial [Gemini 3.1 Flash-Lite experiment](docs/reviews/2026-10-31-behavior-quality-audit.md) ran successfully but found grounding/behavior/latency gaps; OpenRouter remains untested live.

The [repository structure guide](docs/REPOSITORY_STRUCTURE.md) shows where each teammate's code/tests belong. Context, prototype behavior, prompt/provider, structural validation and preview composition have offline tests. Remaining empty directories are scaffolded. No general core server or ingestion command exists yet; RAG/state/game-delivery behavior remains unimplemented.

The separate [manual NPC lab](docs/NPC_LAB.md) now has a local server entry point: double-click `run_npc_lab.bat` (live Gemini), or run `.\run_npc_lab.bat --offline` to test the UI without API calls. It uses the same `.venv`/requirements and opens `http://127.0.0.1:8765`; keep its terminal running and stop with Ctrl+C. Default timing is explicitly a 10-second development profile; `--realtime` tests 3 seconds. No general core server or ingestion command is implied.
