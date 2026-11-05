# Default Whisper STT self-review

Scope: one automatic local speech-recognition default for the Skyrim connector, with no model picker or manual file placement. TTS/XTTS integration, native capture changes and pipeline interpretation remain separate. This is a labelled self-review using the development/design-review skills; no reviewer agent was delegated.

## Reviewed plan

Use faster-whisper with fixed English base.en, CPU INT8 and two CPU threads; pin its Hugging Face revision and Python dependencies. Prepare/download during setup or connector startup before microphone admission. Preserve explicit external STT URLs. Reuse the existing bounded subprocess, temporary WAV cleanup and loopback speech routes; no thread-only cancellation of inference. Test preparation/repair, CPU parameters, transcript/silence handling, timeout/cancellation, launch defaults, external endpoint compatibility and setup ordering, followed by offline regression.

## Implementation findings

- A null/missing launch configuration STT URL selects the built-in endpoint. Configuration files are not rewritten. Explicit external STT remains external; `--say` does not download/load Whisper.
- The launcher bootstraps missing speech dependencies with existing setup. Setup prepares the model before regression. A missing model is downloaded at startup; an unloadable model receives one forced repair attempt. Failure stops startup with a retry message. Cached startup/transcription works offline.
- The isolated worker uses local-only model lookup, one CPU worker, two CPU threads, INT8, English, VAD, beam size one and no previous-text conditioning. The existing 20-second worker deadline, admission flag and kill-before-file-cleanup apply. Per-utterance model loading is an explicit simplicity/teardown tradeoff, not a proven optimal latency design.
- Silence does not fabricate input. Confidence is a token-probability proxy, not calibrated accuracy. Transcript length/WAV limits are retained. No automatic microphone capture occurs during setup/startup.
- TTS stays off on normal launches. `--local-speech` adds the existing Windows TTS while STT uses Whisper. No voice mapping or XTTS behavior was introduced.
- Model weights/cache and smoke-test audio stay ignored; no dependency or game installation was modified outside the project environment. Existing context-handoff changes were preserved.

## Verification

- Initial focused speech/setup/connector suite: **67 passed**. Two additional repair/startup-failure cases were then added.
- Final full offline regression: `.venv/bin/python -m pytest -q`: **566 passed in 16.09 s** (outside the sandbox because of its previously identified asyncio shutdown limitation).
- `.venv/bin/python -m pip check`: no broken requirements. `git diff --check`: passed.
- Actual pinned model downloaded and loaded successfully on Linux/Python 3.11.18. Repeated preparation with `HF_HUB_OFFLINE=1` succeeded without downloading.
- Real offline worker smoke test using the upstream faster-whisper `tests/data/jfk.flac` public sample: 11.0 seconds of audio transcribed in **3.72 seconds**, including subprocess/model startup. Recognition included “asked not” in place of “ask not”; this is a functional test, not an accuracy signoff. Local result confidence proxy: 0.6714. No microphone or player audio was recorded.
- Published wheels verified for Windows Python 3.11: ctranslate2 4.8.5 win_amd64 and av 18.1.0 cp311-abi3 win_amd64. No CUDA/system FFmpeg installation needed for this CPU path, following [upstream documentation](https://github.com/SYSTRAN/faster-whisper).

Verdict: ready for a controlled Windows F8 speech-input test. Windows batch execution, actual microphone quality, Skyrim contention/frame times and end-to-end speech latency remain unverified. Run `run_skyrim_connector.bat`, open NPC dialogue, hold F8 and speak, release, and confirm `STT_READY` then `PLAYER_INPUT` in the bridge. Normal output remains subtitles until TTS is enabled separately.
