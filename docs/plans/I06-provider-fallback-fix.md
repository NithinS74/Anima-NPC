# Provider fallback diagnosis and fix

Plan and pre-implementation self-review, 2026-10-31. User reports all generated lab responses falling back. A direct request with the configured key/model returned HTTP 200 in 12.81 seconds, exceeding the existing lab cutoff of 9.45 seconds. This establishes one timeout cause, not every historic HTTP failure.

Change only the manual lab development deadline to a configurable 30 seconds (range 1..60), with 550 ms response reserve, and derive the HTTP bridge wait from that budget. Preserve core/realtime 3-second limits and the two-call budget. Add optional typed reasoning_effort to public provider config, omitted unless configured; Gemini profile uses minimal per official compatibility documentation. Classify HTTP 400/404/5xx with safe error codes, never provider bodies/secrets. Browser feedback explains common fallback causes. No hidden retries or validation bypasses.

Self-review: a larger development budget enables manual quality testing but does not establish game latency readiness. HTTP bridge must not still cancel after 12 seconds. Minimal thinking may not eliminate thinking or network latency; verify live through the actual context/prompt/validation path. Unit cases cover default/override/realtime bounds, bridge budget, optional wire parameter and invalid configuration, status mapping/redaction/no retries. Full offline regression plus bounded live generated turns with displayed-memory acknowledgement. Record actual outcome, including failures.

## Results / implementation self-review

263 offline tests pass (5.83 seconds). Focused provider/lab checks: 71 pass. Browser JavaScript syntax and Git whitespace checks pass. Tests cover wire settings, invalid configuration, error redaction/no retries, timing bounds/realtime isolation and HTTP bridge waiting the full development budget.

Live diagnosis: original gemini-3.1-flash-lite returned one HTTP 200 in 12.81 s, exceeding the old cutoff, then repeated HTTP 503 with an explicit high-demand message. Minimal reasoning did not cure its unavailability. A comparison gemini-2.5-flash-lite returned HTTP 404 and a migration message. gemini-3.5-flash-lite returned HTTP 200 in 4.12 s and was explicitly selected in the local ignored .env; keys unchanged, no automatic switching policy.

After restart, actual HTTP lab turns with context/prompt/validation returned model_success on gemini-3.5-flash-lite in 1,250 and 1,218 ms (one call each, no violations). This tiny sample establishes connectivity and validated generation, not a latency percentile or realism. The second reply failed to recall Rowan despite five packed history exchanges; memory-quality/grounding remains a separate known issue. The earlier failed responses remain acknowledged history in the local test store, illustrating why semantic recall needs independent evaluation.

Self-review verdict: go for manual generation testing; real-time performance and recall quality remain unproven. No core deadline relaxation, hidden retries, raw error exposure or validation bypass was introduced. Public provider profile remains model-agnostic; only the local ignored model selection changed. Google reasoning parameter mapping was checked against https://ai.google.dev/gemini-api/docs/openai/#thinking .
