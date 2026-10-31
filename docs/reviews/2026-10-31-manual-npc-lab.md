# Manual NPC lab implementation review — 2026-10-31

Followed the development/design-review skills. [Plan](../plans/I09-manual-npc-lab.md) reviewed before coding; implementation review below is **self-review**, not an independent reviewer signoff. Scope is the standalone test interface, not a fix or signoff for core behavior quality.

## Review and corrections

- Separate `tools/npc_lab/` imports the real core pipeline; there are no changes to `src/npc/`. Four strongly authored public JSON profiles reside in `fixtures/personas/npc_lab/`. No second prompt, memory or behavior implementation was introduced.
- Initial complete persona/control prompts exceeded the core CLI's byte cap. Measured 2,065–2,166 bytes, so the lab explicitly declares/shows a bounded 3,072-byte cap; core defaults remain unchanged. Unit cases ensure all four starters can reach generation under it.
- Review caught event-loop cleanup on failed port binding and corrected it. One persistent loop/runner handles API turns; cancellation remains responsive outside generation, slot ownership remains in the existing runner, and HTTP worker/body counts are bounded. Timing is fixed per launch so two runners cannot bypass one another's cleanup slot.
- Browser content uses text nodes, fixed static routes and no remote/CDN assets. Host/Origin/token checks and strict browser-control contracts prevent file-path/provider-policy overrides. Errors omit raw validation/provider secrets. Fake/live and fallback/model outcomes remain explicit.
- Browser review restored the introductory empty state after resets/profile changes. Controls lock during a request; reset requests cancellation and a browser epoch check prevents late output from entering a reset log. Earlier dialogue remains explicitly display-only, not a fabricated memory feature.

## Verification evidence

- `.\.venv\Scripts\python.exe -m pytest -q`: **196 passed in 4.61 s**, including 28 new profile/service/HTTP tests. Covers each working component, fresh canonical observations, invalid input, cross-profile scope, prompt sizes, concurrent admission, matching/nonmatching cancellation, fixed-route serving, private-path denial, Host/Origin/token checks and JSON body limits.
- Actual headless Chrome checks at 1440 px desktop and 390 px mobile: all four portraits loaded, an offline fake turn appeared with call/status metadata, friend preset set trust to 80 and cleared the log, switching to Iona changed the profile, no horizontal overflow, zero recorded JavaScript exceptions. Screenshots inspected at `output/screenshots/npc-lab-desktop.png` and `npc-lab-mobile.png` (ignored). Browser-control helper failed to initialize, so checks used an isolated headless Chrome profile with its own temporary data directory; user browser data was not accessed.
- Ran `run_npc_lab.bat --port 8765` from the repo's `tmp` working directory using PowerShell's normal file invocation; launcher changed to repo root, used `.venv`, started the live localhost service and opened the browser. A first manual test invocation used incorrect outer shell quoting and failed before executing the batch; normal invocation passed.
- Actual HTTP live Gemini 3.1 Flash-Lite request to Elin returned `model_success`, one call, **2,765 ms**, within the 10-second development profile. Response: “The benches are plenty and the fire is warm, traveler. Rest your feet as long as you like.” This demonstrates warm voice and functioning UI transport, **but benches/fire were not supplied facts**: the known grounding gap persists. It is not proof of real-time readiness or semantic correctness. Raw developer trace is ignored under `output/evaluation/npc-lab-live-smoke.json`.

## Verdict and remaining limits

**Go for local manual testing.** No new dependency, asset download, game modification or production service is required. Original illustrated 2D portraits replace the optional Skyrim conversion effort. UI alone does not resolve the [core behavior audit](2026-10-31-behavior-quality-audit.md); grounding, relationship-sensitive authored decisions, voluntary social silence, delivered memory and production delivery remain separate work. The lab is explicitly single-turn and developer-local. No promise of optimal latency, robust semantic verification or zero technical debt is made.
