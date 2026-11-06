# Install Anima in Skyrim

This release contains the Windows x64 SKSE plugin and the Python companion. The companion runs outside Skyrim and supplies Whisper input, optional local vision, dialogue generation and Chatterbox Turbo voice output. Mantella is not required.

## 1. Prerequisites

- Windows x64 and Python **3.11** with the Python launcher (`py`).
- SkyrimSE.exe **1.6.318.0** or **1.7.104.0**. Other versions are rejected; do not bypass that check.
- Matching [SKSE](https://skse.silverlock.org/) and [Address Library](https://www.nexusmods.com/skyrimspecialedition/mods/32444) already installed. The native plugin needs the matching `versionlib-1-6-318-0.bin` (format 2) or `versionlib-1-7-104-0.bin` (format 5) under `Data/SKSE/Plugins`.
- The [Microsoft Visual C++ x64 runtime](https://aka.ms/vs/17/release/vc_redist.x64.exe).
- [Ollama for Windows](https://ollama.com/download/windows), installed and running. Setup downloads `qwen2.5vl:3b`; you do not move its files manually.
- A dialogue provider account, API key and model identifier. Use Gemini or OpenRouter. Inference may incur provider charges when you submit dialogue.
- Internet and enough disk space for Python packages, approximately 3 GB of Chatterbox checkpoints, Whisper and the VLM. GPU memory is shared with Skyrim. CPU Chatterbox was slow in testing; GPU latency/VRAM fit must be tested on your machine.

## 2. Extract and configure

Extract `Anima-Skyrim-0.3.0.zip` to a normal writable folder, for example `D:\Anima`. Keep the companion folder separate from the game directory. The archive contains an `Anima` folder; run commands from that folder.

Create `.env` from `.env.example` if it does not exist (setup also creates it). Edit with Notepad and fill:

```dotenv
GEMINI_API_KEY=your-key
NPC_LLM_MODEL=your-provider-model-id
```

For OpenRouter, fill `OPENROUTER_API_KEY` instead. Keep unused keys blank; never put keys in the public YAML files. Setup selects an already-configured profile and refuses to silently use scripted replies. It does not make a dialogue-model API call during installation. Existing `.env` and custom endpoint settings are preserved.

Close Skyrim before installing/updating the DLL.

## 3. Run setup once

Double-click **`setup_skyrim.bat`**. It attempts game discovery. If it cannot find the game, run from Command Prompt or PowerShell:

```powershell
.\setup_skyrim.bat --game-directory "D:\Games\Skyrim Special Edition"
```

Setup checks runtime/SKSE/Address Library, creates/reuses the project environment, installs pinned packages, chooses a conservative supported CUDA build or CPU fallback, prepares Whisper/Chatterbox/the VLM, imports vanilla/DLC voice references and runs offline checks. First setup can take substantial download/model preparation time. Rerun after fixing a reported prerequisite; completed downloads are cached.

After checks pass it installs only `Data/SKSE/Plugins/AnimaConnector.dll` and `AnimaConnector.ini`, aligns the port, and configures live dialogue plus visual attachment in `configs/skyrim/connector.json`. A previous DLL is backed up once with `.anima-backup`; existing INI values such as your push-to-talk key are preserved. It does not alter saves, quests, other mods or game archives.

For mod-manager installation instead, the native archive is `mod/AnimaConnector.zip`. Install it as its own mod and retain SKSE/Address Library prerequisites. Avoid deploying an older managed Anima DLL over the current one. The Python companion and its downloaded models remain in `D:\Anima`, not in `Data`.

## 4. Start and play (single launcher)

**Option A — One command (recommended):**
```powershell
.\launch_skyrim.bat
```
Or with explicit game path:
```powershell
.\launch_skyrim.bat --game-directory "D:\Games\Skyrim Special Edition"
```
This starts CV (port 8000), the bridge (port 8768), waits for both to be healthy, launches Skyrim via SKSE, and shuts everything down when you close the game.

**Option B — Manual (three terminals):**
Keep Ollama running. Open **`run_cv.bat`**, then **`run_skyrim_connector.bat`**. Leave both terminals open. The bridge loads/warm-ups the speech model before accepting requests; CPU startup took about 50 seconds on the development host.

Check:

- `http://127.0.0.1:8000/ready`: CV/Ollama model is ready.
- `http://127.0.0.1:8768/v1/health`: bridge ready, no last error.
- `http://127.0.0.1:8768/v1/speech/health`: Chatterbox worker ready.

Launch Skyrim **through SKSE** (through your mod manager if applicable). Use a separate test save, borderless/windowed mode, and keep Skyrim in the foreground for screenshot capture. Open ordinary NPC dialogue, wait for the vanilla greeting to finish, hold **F8**, speak, and release. F8 deliberately interrupts existing speech; automatic Anima output waits for an active vanilla line to finish within its expiry. F7's optional text panel uses UIExtensions if installed; F8 does not require it.

The reply should appear as a subtitle and play from the selected NPC. Unknown/missing voice references, timeouts or synthesis failure retain subtitle output; that is a degraded result, not a successful voice test. Automatic reference selection needs listening review for human/Khajiit similarity and naturalness.

To see correlated diagnostics, start the bridge with:

```powershell
.\run_skyrim_connector.bat --log-file output/skyrim/anima-console.log
```

Look for `SESSION_OPEN`, `STT_READY`, `PLAYER_INPUT`, `PIPELINE_RESULT`, `TTS_READY`, `OUTPUT_STAGED`, then `NATIVE_ACK` started/completed. The SKSE log directory also contains `AnimaConnector.log`. A green bridge health response alone is not proof of model/audio delivery.

## 5. First-run checks

1. Speak to one human NPC; confirm transcription, response, matching subtitle and audible voice.
2. Switch to a Khajiit; confirm voice type changes and does not inherit the previous speaker.
3. Close dialogue during generation/playback; no late speech should start and current Anima audio should stop.
4. Let Anima output arrive during vanilla speech; the vanilla line should finish, or the pending Anima output should expire.
5. Check one unobstructed screenshot/descriptor under `output/skyrim`; verify CV is actually ready. Cold VLM inference can exceed the eight-second bridge allowance; warm it before judging visual results.
6. Measure delay and frame rate with both vision and speech active. The current CPU Turbo path can exceed the speech deadline; a generated 2-second reference-conditioned line took 19.67 seconds on the development CPU. GPU operation alongside Skyrim is not signed off.

RAG and richer authored personas are optional, separately configured content. Existing `rag_config`/`profiles_file` settings are preserved. Do not use the village-lab RAG bindings as Skyrim permissions or grant every NPC an entire dialogue dump. The connector passes collected game data through the pipeline input; this release does not invent biographies or quest knowledge. See `docs/RAG_INTEGRATION.md` and `docs/SKYRIM_CONNECTOR.md` for explicit scoped bindings.

Stop with Ctrl+C in both service terminals. To uninstall, stop the game/bridge and remove this mod's DLL/INI and generated `Data/Sound/Voice/AnimaConnector` files, or disable its mod-manager entry. Keep your local `.env` and data if you intend to reinstall. Restore the backed-up DLL only if intentionally reverting to the old build.

The native DLL's build provenance and live-verification status are recorded with the release. A successful cross-build and offline tests do not establish in-game ABI, microphone, archive-decoding, visual grounding or voice quality on your installation.
