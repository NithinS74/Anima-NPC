# Generation/validation test slice

Plan reviewed before coding using both repository skills (self-review). Build on the uncommitted context slice on `feature/I04-context-builder`; do not lose or silently commit that work. A new feature branch carries the combined working changes until they can be split/reviewed in PRs.

## Outcome

Run a scenario through context -> small deterministic interaction plan -> compact prompt -> replaceable provider -> validation -> at most one repair -> validated fallback. Expose offline and explicitly opted-in live CLI modes. No RAG, persistent game state, HTTP server, speech, outbox/delivery guarantee or full M03/M04 completion is implied.

## Plan and acceptance

1. Add strict interaction/response/provider-result/preview contracts. Supply the minimal behavior plan needed by generation: combat ends, busy/closed/threat/uncertain transcription/greetings can use authored text without a model; other turns generate under identity/knowledge/length constraints. Preserve mixed-input questions rather than matching a greeting prefix.
2. Format only a compact context view, not the complete diagnostics. Keep player/observations in a separate untrusted data message. No secrets or provider credentials in prompts. Use an explicit conservative byte budget including framing reserve; no unverified claim of exact provider tokenization. Oversize required context yields fallback, not silent loss of identity/constraints. Output token cap is configured at the provider.
3. Implement a provider protocol and one HTTPX chat-completions-compatible adapter, plus deterministic offline fake. Configure base URL, model, key and optional JSON-object response format. No SDK dependency or hidden retries. Require HTTPS except loopback HTTP, forbid URL userinfo/query/fragment, redact errors and bound response bytes/content/usage. Generic compatibility is a transport choice, not a promise every vendor/model supports it.
4. Validate complete JSON/schema, mode, length, cues, evidence references, finish reason, revision/epoch/cancellation and obvious assistant/prompt scaffolding. Checks do not prove semantic entailment or persona realism. No always-on LLM critic. Rejected raw text is never delivered or fed back as trusted instruction.
5. A single-runner preview shares one monotonic ingress deadline and earlier model cutoff. At most two provider calls including repair; rate-limit/timeout/auth/transport failures fall back directly. Recheck cancellation/state before accepting even a fallback. Hold one global request slot while the underlying local request is active; no unbounded queues. This is a scenario harness, not production multiplayer/state ownership.
6. Unit-test every working module; integration tests use injected HTTPX mock transport/fake providers and controlled clocks. Exercise malformed/long output, repair/failure, stalled/drip-fed response, cancellation, stale state, prompt budget and zero-call routes. Run full regression and independent review when available/authorized. Live calls require explicit CLI opt-in and local configuration, never default CI.

## Plan-review decisions

- Keep context pure; generation policy is a separate behavior module. Minimal deterministic policy is necessary to avoid sending busy/combat turns to a model merely for a demo. It is not a generic planning agent.
- Use asyncio total timeouts around transport and the whole provider call; HTTPX inactivity timeout alone is not an absolute deadline. Reject late completion even if a fake/provider ignores its timeout.
- Default real-time profile remains 3,000 ms response deadline, model cutoff 2,450 ms. A separately labelled development timeout can be longer for slow APIs without claiming the real-time target passes.
- Start with no external retrieved evidence/history. Perceived observation IDs can be cited; unknown lore must be treated as unknown. No semantic-grounding guarantee is claimed from a valid ID or keyword check.
- Keep keys in `.env`/environment; configuration inspection prints presence only. Never copy credentials from installed Mantella or another application. No live test can be completed before the user supplies provider/model/key.
- Readiness requires offline regression and documented review findings. Missing live credentials are reported as unverified live behavior, not a successful smoke test.

## Results

Implemented strict dialogue contracts, prototype behavior policy, compact prompt construction, replaceable HTTPX provider, offline fake, configuration loader, structural validator and reusable bounded preview runner/CLI. Public OpenRouter/Gemini profiles live in `configs/providers/`; keys/model remain local. No new dependency pins were needed; the existing pinned HTTPX/dotenv/YAML packages now also appear as package runtime metadata.

Independent review found slow cancellation cleanup could delay the caller, and prompts dropped numeric disposition/influence distinctions. Added reproducing tests (both failed), fixed both, then reran regression: **168 passed**. The reviewer independently repeated the suite and signed off for offline previews and an opted-in live smoke once configured. See the [review report](../reviews/2026-10-31-generation-validation-review.md) and [usage/limitations guide](../GENERATION_VALIDATION.md). Live APIs, semantic quality, game latency/resource use and production staging/delivery remain unverified.
