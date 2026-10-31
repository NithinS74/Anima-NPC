# Development setup

Use Python 3.11 in a project virtual environment. This is a reviewed design repository; setup prepares dependencies, not a working NPC server.

PowerShell from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

There is one dependency file: `requirements.txt`, containing the pinned API-first core/development environment verified on Windows/Python 3.11. Small test/document-review packages are included for the team's shared setup. Update pins deliberately with compatibility checks. Other OS/Python combinations need verification before claiming support.

Activation is optional; explicit interpreter paths ensure the right environment even when PowerShell activation policy is restrictive. If desired: `.\.venv\Scripts\Activate.ps1`.

I05 will add Chroma and the selected CPU embedding/parser packages to this same file when integrated and tested. No GPU/local LLM, Torch, CV or speech stack is required now. The RAG module will create/manage local storage and model assets; users will not manually provision a Chroma server for the embedded prototype.

Copy `.env.example` to `.env` when API testing needs provider settings. Keep keys in the backend, never browser JavaScript or commits. No model/provider is hardcoded. Tests/CI use fakes by default; dependency setup launches no game/server, records no audio and makes no paid model calls.

The `.venv`, `.tools` (and typo `.toolds`), temporary PDF renderings/extractions, databases, logs, private knowledge, captures and model files are ignored. The reusable [reviewer skill](.agents/skills/review-npc-design/SKILL.md) is committed; invoke `$review-npc-design` in a compatible agent or ask it to read that file explicitly.

No server-start/ingestion commands are offered because those modules have not been built. The next gate is executable contracts and one fake-provider vertical slice.
