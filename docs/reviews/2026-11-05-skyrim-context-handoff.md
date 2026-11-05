# Skyrim context handoff self-review

Scope: deliver the complete collected game context to pipeline ingress. Interpretation, prompt selection, knowledge authorization, native capture and playback are outside this change. Review used the development and design-review skills; this is a self-review, with no delegated reviewer.

Plan reviewed before implementation: add one optional game-neutral, bounded JSON context to `ContextScenario`; populate it in the Skyrim mapping and enrich it with screenshot metadata/current VLM descriptor in the bridge. Keep existing HTTP/inbox fields compatible. Verify the actual built-in runner argument as well as serialized HTTP/inbox inputs, preserving nulls and provenance. No storage migration, new dependency, native build or model call is needed.

Implementation review: `adapter_context.source` identifies `anima-skse`; its payload preserves the full typed game event, authored profile, screenshot metadata and optional descriptor. Player input/confidence and scoped identity remain in the canonical turn. The JSON contract rejects non-JSON data and payloads over 256 KiB UTF-8. Existing scenarios omit the field safely. The canonical perception/policy and explicit visual prompt path are unchanged. The descriptor uses the existing revision/TTL checks; unavailable descriptors remain null. No additional inference or network operation is introduced. Existing native capture limits/truncation remain; this does not collect new game fields.

Validation on Linux/Python 3.11.18:

- Focused contracts/connector tests: **78 passed**.
- Full offline regression, `.venv/bin/python -m pytest -q`: **553 passed in 14.22 s**.
- `git diff --check` and compilation of the three changed runtime files passed.
- Initial sandbox execution stalled during asyncio shutdown; the offline tests completed outside the sandbox. Initial full regression had eight CLI import failures because editable package installation was missing in the newly created venv; after local installation, all tests passed. Pinned requirements were unchanged.

Tests verify complete game event/profile/visual preservation through built-in preview, HTTP and inbox paths, real offline runner delivery, STT confidence, missing optional data, JSON round trips, payload limits and unchanged perception. No new in-game, microphone, VLM or paid-provider check was run. Verdict: offline handoff ready; in-game verification remains separate. A pipeline consumer must explicitly read `scenario.adapter_context.payload`; this change does not claim improved response grounding.
