# Chatterbox Turbo setup self-review

Review follows develop-npc-component and review-npc-design. This is a self-review, not an independent review. [Reviewed plan](../plans/chatterbox-turbo-setup.md). User scope: automatic Turbo download/setup and controlled NPC voice conditioning, with minimal manual work.

## Implemented result

`setup_chatterbox.bat` bootstraps the existing project setup if necessary, then uses the single `.venv`/`requirements.txt`, selects a conservative Torch backend, downloads the pinned Turbo inference files, generates a diagnostic WAV, locates Skyrim, extracts bounded reference clips, runs regression and enables local TTS. It seeds/updates only the discovered game path in local connector configuration, preserving other authored settings. Runtime keeps explicitly configured external endpoints and their original request body; the built-in route receives NPC-base identity for overrides.

Model: ResembleAI/chatterbox-turbo revision `749d1c1a46eb10492095d68fbcf55691ccf137cd`; package chatterbox-tts 0.1.7. The duplicate non-meanflow generator is excluded. Weights, references, hashes/source metadata and generated WAVs remain ignored. No game installation, credentials, player state, runtime LFS archive or repository visibility was changed.

The offline importer reuses the existing selective BSA reader, reads vanilla/DLC VTYP editor IDs and decodes FUZ/XWM through bundled PyAV. It tries at most 20 clips per folder from at most 16 voice archives. References are keyed by plugin/local voice form ID; NPC base overrides take precedence. Existing custom references are preserved; invalid custom data fails clearly. These are automatically selected references, not audited voice-acting samples.

One persistent worker owns inference, with one request/no queue and a four-entry conditioning cache. Each request restores the selected speaker conditioning. Missing references do not use a different voice. Reference hashes/paths/PCM and generated audio bounds are checked. The worker warms audio kernels before readiness; startup is bounded to 120 seconds and speech to 20 seconds within the remaining bridge deadline. Cancellation/timeout kills the process and schedules one bounded background recovery. Requests during recovery fall back to subtitles; shutdown cancels/reaps recovery. Model code, memory/state decisions and native playback are otherwise unchanged.

## Findings resolved

- Upstream dependency conflicts required compatible NumPy, SymPy, tokenizer/Hub, FastAPI/Starlette and Pillow pins. The watermark dependency additionally required setuptools 80.9.0 because newer setuptools removed pkg_resources. The original runtime failure was reproduced with a real model load and fixed without disabling the watermark. A preflight now gives a clear error before loading the large model if the watermark import is unavailable.
- Real CPU inference exposed a cold-restart trap: loading a roughly 50-second worker inside the next 20-second speech request would repeatedly time out. Background recovery and degraded readiness prevent that loop; dedicated tests cover rejection during recovery and successful subsequent use.
- Setup now selects CUDA 12.4 wheels for GPU 0 with a conservative driver/compute-capability admission, otherwise CPU. Unsupported newer architectures, including Blackwell with this Torch pin, fall back to CPU. No manual CUDA toolkit installation is added. Hardware performance/VRAM compatibility remains an empirical gate.
- Discovered game paths must also configure audio staging. Setup now updates that path atomically while preserving existing endpoint/profile/port settings, after checks succeed.
- Adding NPC identity to every external TTS request would break strict legacy services. Only the built-in endpoint receives the extra field; external request compatibility has a regression case.

## Verification performed

- Final full offline regression: `.venv/bin/python -m pytest -q`: **604 passed in 15.96 s**, with one existing third-party Starlette/AnyIO deprecation warning. Tests ran outside the sandbox because of its previously observed asyncio shutdown limitation.
- `.venv/bin/python -m pip check`: **no broken requirements**. Runtime/scripts compile, `git diff --check` passes, and changed documentation file links resolve.
- Windows Python 3.11 binary-only dependency resolution passed for both CPU and CUDA 12.4 Torch backends. No compiler/source build was needed for resolution; this is not a Windows installation test.
- Both large model checkpoints downloaded from the pinned official repository and were verified against their official SHA256 metadata. Slow/interrupted initial transfers were resumed; a bounded parallel-range helper was used locally to finish verification. That diagnostic helper is not a user setup requirement or tracked project file.
- Actual offline CPU model load and setup CLI `python -m npc.output.chatterbox --prepare --device cpu` succeeded. Generated diagnostic output is PCM16 mono at 24 kHz, 1.8 seconds. First cold basic synthesis took 54.98 seconds, including lazy kernel work; it is not a warm latency claim.
- Actual resident worker loaded/warmed in 49.74 seconds. With a public upstream JFK reference and a diagnostic 90-second limit, it generated a 2-second PCM16/24-kHz line in **19.67 seconds**. The earlier 20-second production-limit attempt timed out. Local Whisper recognized the generated line as “Welcome to Anima.” No microphone/player recording or paid API was used.
- Unit/HTTP fixtures cover reference selection, override/cache isolation, path/hash/audio bounds, worker protocol/readiness, timeout/cancellation/recovery, automatic activation, external TTS compatibility, plugin/FUZ parsing, reference preservation, game-path configuration, GPU admission and setup failure gates. PyAV's XWMA demuxer is available on the test host.

Verdict: setup/runtime slice is offline-tested and actual CPU synthesis is verified. CPU Turbo is too close to the speech deadline to recommend for smooth conversation; it can legitimately fall back to subtitles. Actual Windows batch execution, installed-game voice BSA decoding, human/Khajiit similarity and naturalness, CUDA/VRAM fit, game contention, and native audible playback remain unverified. Those require the target Windows machine and a controlled in-game test; no live readiness is claimed.
