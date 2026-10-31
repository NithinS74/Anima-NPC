# Automatic launcher and setup self-review

This is a labelled self-review using the repository development/design-review skills. Scope: automate teammate setup without changing NPC context, model deadlines, social state or game integration. Plan: [automatic launch](../plans/ANIMA-auto-launch.md).

## Findings and resolutions

- Repeated pip/network/test work on every launch would delay manual testing. A local readiness check now compares the successful-setup fingerprint, pinned installed distribution versions, editable package location, configuration presence and runtime member presence/size. Setup runs once when readiness fails; healthy launches skip it. Full media hashes remain a setup-time check. Same-size media edits are intentionally outside this lightweight check; explicit `--sync-media` verifies/restores the bundle.
- Automatic source updates must preserve teammate work. Setup checks for a clean tracked/untracked working tree and a current tracking branch, then uses fast-forward-only pull with rebase/autostash disabled. It never resets, switches branches or creates merge commits. Missing Git, detached/no-upstream branches, network failure and divergence produce an explanation and retain local source. Git calls are bounded and noninteractive. `--no-update` skips source updates. Healthy launches do not pull.
- Pulling installer changes while retaining old Python definitions could mismatch the manifest. Setup re-executes once after its update attempt with `--no-update`, then performs installation. Git LFS is initialized locally and hydrates the one runtime archive when missing/a pointer; archive/member bounds and hash verification remain unchanged.
- A first install has no API key. Launcher auto mode explicitly announces a scripted offline preview when configuration is invalid/absent. `--live` still reports configuration failure; `--offline` overrides auto mode. No paid startup probe is made. Secrets and saved relationships are preserved; global Python/Git/Git LFS installation and private-repository sign-in remain prerequisites.

## Evidence

- Full offline Python regression: **317 passed**, including readiness/version/package-origin/media checks, launcher failure/argument propagation, provider selection, mocked dirty/detached/no-upstream/network/timeout failures and an actual local Git fast-forward followed by dirty-work preservation.
- Existing camera/facial JavaScript unit tests: **7 passed**. No UI layout or core turn behavior changed.
- Actual `run_anima.bat --offline --help` in the fresh GitHub teammate checkout with its `.venv` moved aside created a new environment, installed the single requirements file, verified all 382 media files, passed the then-current 316 tests and reached the app entry point. New script changes were overlaid locally for this automation test; the earlier remote asset-clone result is recorded in the [media review](2026-10-31-immersion-refinement.md).
- Removed one installed dependency and a character JPG in that isolated checkout: the launcher reran setup and repaired both successfully. A subsequent healthy launcher invocation skipped setup and reached help in **0.723 seconds** on this machine. This is a CLI startup sample, not a GPU/game or model-response benchmark.
- `pip check` reported no broken requirements. Batch invalid options display usage; explicit `--no-pause --no-update` setup is exercised separately. Existing API keys were never copied into the teammate checkout, and no paid LLM request was needed.

Verdict: go for this local setup/launcher slice. This does not establish production game delivery, model realism, cross-platform media compatibility or public-hosting readiness. Offline reuse requires an already valid cached installation; missing packages/LFS data still need connectivity and repository access.
