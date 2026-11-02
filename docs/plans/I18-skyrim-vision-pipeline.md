# I18 Skyrim / vision / response integration

2 November 2026. User requests checkpoint, GitHub merge and a complete connected
mod-to-vision-to-response path. Local checkpoint is d29e8c7; incoming WIthCV is
35cfb99. Preserve both histories and the independently authored mod.

Acceptance: native context/capture -> bounded CV/VLM -> typed visual reference ->
existing context/policy/RAG/provider/validation -> correlated text/optional WAV ->
native receipt. Inbox and external HTTP modes remain supported. Configured built-in
mode actually composes RAG and vision. No implicit paid call, model download or game
installation. Failures, old sessions/revisions and expired frames cannot deliver
obsolete speech. A no-response runner releases admission. A deterministic integration
test crosses real HTTP CV schema, prompt and delivery boundaries, including speech
fakes. Actual model/game checks are separate gates.

Boundaries: adapter owns capture and correlation; src/npc/vision owns compact
client contracts; existing CV backend owns inference; core owns generation and
validation. Share the root .venv/requirements. Preserve incoming CV API/CLI paths.
Keep detector optional so VLM-only operation doesn't force a second GPU stack.
Bound inference to one admitted request and cap image/response/output retention.
Camera descriptors remain untrusted references, never perceived facts or evidence.
Automatic use is explicitly configured; default is off. No persistent heard-memory
claim follows native best-effort reports.

Plan self-review (not independent): reuse PreviewRunner rather than a second
orchestrator. Cap CV work separately; turn timeout includes waiting for context.
Bind frame provenance to session/revision and TTL; discard a late result. Cancellation
must not free inference admission before blocking detector work finishes. Avoid
adding heavyweight YOLO dependencies to the default API-first environment; retain
its existing lazy optional adapter. Speech service selection is pending user input;
existing localhost HTTP contracts remain usable meanwhile.

Tests: CV normalization/stream limits/errors; adapter frame success/failure/timeout,
TTL/revision/session replacement, RAG composition, no-response release; integrated
CV -> provider prompt -> TTS WAV -> game commands and terminal receipt using fakes.
Run root pytest, CV tests, pip check, JS checks and native build/CTest/package.
Document actual commands and live prerequisites before final integration commit.
