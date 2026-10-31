# Generation/validation implementation review — 2026-10-31

Scope: [reviewed plan](../plans/I06-I07-generation-validation.md), prototype behavior, prompts, provider/configuration, structural validation and response-ready runtime. Followed the repository development/design-review skills. Plan review was self-review; implementation review and fix re-review were independently performed by the existing `context_implementation_review` reviewer agent, read-only.

## Findings and resolutions

| Severity | Finding and concrete failure | Resolution and verification |
|---|---|---|
| High | `src/npc/runtime/preview.py` `_invoke` awaited cancellation cleanup without a bound. A provider that delayed cleanup could hold the caller past the response deadline. | Caller returns without awaiting provider cleanup; a retained task keeps the single global admission occupied until it actually settles. Regression blocks cleanup with an event and requires prompt fallback plus zero additional calls while occupied. Reproduced failing before the fix, passing afterwards. |
| Medium | `src/npc/generation/prompt.py` omitted warmth/caution and influence codes. Reserved and warm NPCs with otherwise identical inputs generated identical prompts. | Compact numeric dispositions and influence codes now reach the trusted profile. Paired warm/reserved prompt test failed before the fix and passes afterwards; no full diagnostic ledger is sent. |

Independent re-review found both resolved, checked cancellation races/exception retrieval and independently reran **168 tests passing in 3.63 s**. No blocker remains for this slice. Verdict: **go for offline scenario previews and a separately opted-in API smoke test after local model/key configuration**. This is not a full-pipeline or production-readiness signoff.

## Justified scope and checks

One modular process, deterministic zero-call policy paths, one model call ordinarily and at most one repair. No always-on critic, extra agent runtime, plugin registry, queue service or vendor SDK. Strict parsing, bounded payloads and explicit late/stale/cancelled handling address concrete failures. The conservative byte budget is explicit; it does not claim portable exact tokenization. Mock HTTP transport exercises errors, size limits and total/drip deadlines without paid calls.

Main-agent full regression after fixes: **168 passed in 3.70 s** using `.\.venv\Scripts\python.exe -m pytest -q`. Tests cover every working component, CLI composition, secret-redacted configuration/errors, duplicate/extra schema fields, length/cue/evidence checks, repair failure, cancellation, state changes and admission contention. A deliberately false statement with valid structure passes a test to record the semantic gap honestly.

Editable installation refreshed with `pip install -e . --no-deps --no-build-isolation`; `pip check` reported no broken requirements. All three fixture CLI smoke checks passed offline (available smith/clerk: one fake call; closing smith: zero calls). These are pipeline checks, not LLM-quality measurements.

## Remaining limits

- Live OpenRouter/Gemini model/settings compatibility, semantic/persona quality and latency are unverified: no model/key was supplied, and no live calls were made.
- Asyncio cannot forcibly terminate arbitrary custom providers that repeatedly suppress cancellation. Their slot remains occupied; `asyncio.run()` shutdown can still wait on them. The response-ready behavior is for a persistent event loop; built-in HTTPX transport uses cooperative cancellation and transport/absolute timeouts.
- RAG, delivered history, persistent state, atomic staging, game delivery, real game resource contention and full behavior/template policy remain separate work. In-process preview state checks are not an atomic game dispatch guarantee.
- JSON/evidence-ID checks do not prove entailment, prevent every subtle leak or establish realism. Offline labelled evaluation remains necessary; no keyword checker is represented as semantic verification.

See the [preview guide](../GENERATION_VALIDATION.md) for exact commands, configuration precedence and the boundaries of this implementation.
