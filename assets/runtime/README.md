# Private Anima runtime media

This repository is private. The owner explicitly requested the educational runtime bundle for project collaborators; repository visibility is unchanged. Upstream rights and licences remain with their respective owners. This is not a new general redistribution licence; review rights before any public release.

`anima-media.zip` is tracked with Git LFS. It contains only four converted relaxed-pose character GLBs with native facial targets, four actual Skyrim location screenshots with UESP source metadata, two locally extracted Skyrim Futura fonts with source hashes, and the selected Windows Piper runtime/data/four voice models. Original Piper licence/configuration files are retained. It contains no API keys, player records, .venv, game archives, extraction tools, raw source meshes/textures, logs or conversion scratch files.

`manifest.json` records every file size/SHA-256 and the archive SHA-256. `setup.bat` retrieves an LFS pointer when needed and verifies/extracts this pack into ignored `assets/private/npc_lab/`. Previously managed files update; separately modified local files are preserved. Git LFS access uses the collaborator's existing repository authentication; no credentials are embedded in the app/bundle.

Use Git clone with Git LFS rather than downloading a source ZIP. If assets are pointers/missing, run `git lfs pull` and rerun setup. To intentionally rebuild after validated local conversion, run `.\.venv\Scripts\python.exe -m tools.npc_lab.package_runtime`, then stage the changed archive/manifest using Git LFS. Source-only development can omit this directory and retain illustrated fallbacks.

To ensure an existing teammate install uses exactly the shared runtime media, run **`setup.bat --sync-media`** after pulling. This intentionally replaces local runtime model/font/voice/scene overrides with verified bundle versions; `.env` and saved player state remain untouched. For automated checks combine `--no-pause --sync-media`. Normal setup preserves local overrides. Matching media does not force identical cloud-model responses or personal relationship state.
