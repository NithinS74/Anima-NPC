# Chatterbox Turbo automatic setup

User outcome: one setup command installs the pinned English Turbo model and prepares installed Skyrim voice references, then normal connector launch supplies validated text and the selected NPC voice to one resident synthesis worker. No manual model placement or separate speech application is required.

Plan and plan review were performed before implementation in the task notes, using develop-npc-component and review-npc-design. This is a self-review; no separate agent was delegated.

## Boundaries and acceptance

- Generic model setup, conditioning cache and bounded synthesis process belong in `src/npc/output/`; game-specific identity mapping and HTTP composition stay in `src/npc/adapters/skyrim/`.
- Thin setup entry points belong in `scripts/` and a Windows batch launcher. Reuse the existing selective BSA reader only in offline tooling. All weights, extracted clips, conversion metadata and synthesized audio remain ignored under `data/`/`output/`.
- Pin the package and exact model revision. Download only the inference checkpoints/tokenizer/voice encoder; avoid the unused duplicate generator. Preserve the single `.venv` and `requirements.txt`.
- Resolve NPC-base overrides before voice-type references. Every request explicitly restores conditioning, including cache hits. Missing references fail rather than choosing an unrelated voice. Do not modify persona, RAG, generated text, quest state or native playback.
- One resident model, one active synthesis, no queue, four conditioning entries, 120-second startup bound and 20-second synthesis bound inside the bridge deadline. Cancellation/HTTP disconnect kills stale work before restart. WAV validation and subtitle fallback remain in the existing delivery path.
- Setup discovers the game, reads vanilla/DLC VTYP records and decodes bounded samples from matching English voice archive folders. Preserve custom references and existing keys/state. Actual archive compatibility and voice quality require a Windows/game audition; fixture coverage is not live signoff.
- Write the enabling marker only after model load/synthesis, usable references and regression pass. Preserve configured external endpoints and their original request shape. Healthy runtime does not download model files.

## Self-review resolutions

The current machine has no usable NVIDIA driver. Fresh setup therefore uses CPU Torch wheels without CUDA prerequisites; compatible installed CUDA builds are retained and selected automatically. Speed and GPU fit remain measurement gates, not promises.

Upstream package metadata introduces compatibility constraints beyond NumPy, including Torch's SymPy pin, Transformers/tokenizer/Hub versions and Gradio's FastAPI/Starlette/Pillow bounds. Resolve compatible pins in the existing environment and rerun HTTP/RAG/Whisper regression; do not suppress dependency errors or introduce a second environment. Upstream is unmaintained, so use fixed package/model versions.

Unit coverage includes download pin/filter, device selection, voice isolation/override/cache restoration, invalid references/audio, process timeout/cancellation, HTTP lifecycle, external TTS compatibility, plugin/FUZ fixtures, setup sequencing, corrupt manifests and preservation of local settings. Run full offline regression, pip check and Windows binary-wheel resolution. Real model load/reference-conditioned synthesis and Windows Skyrim playback are separate evidence categories.
