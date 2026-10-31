# M07 - Output validation, critique and bounded repair

Status: proposed | Requirement: SYS-09 | Owner/reviewer: unassigned

## Responsibility

`validate(candidate, context, plan, current_revision) -> ValidationResult` returns accepted/rejected, violations, repaired candidate if any, and final fallback reason. M09 owns the shared deadline and total call count; M07 requests repair rather than initiating an unbounded loop.

## Checks in order

1. Parse schema, known speaker and allowed mode/cue. Reject unknown commands or extra state mutation fields.
2. Enforce plan word/sentence limits, nonempty speech and empty text for silence.
3. Check turn IDs, dialogue-relevant revision/turn epoch and cancellation. M02 must repeat these checks atomically during result/outbox staging, and M08 must guard dispatch/start. Benign telemetry does not invalidate replies; combat/target/grant changes do.
4. Check evidence IDs, scope and explicitly modeled forbidden disclosures. These are structural guarantees; existence of an evidence ID does not prove the sentence is entailed.
5. Detect obvious prompt leakage, assistant scaffolding and disallowed real-world digressions using authored rules.
6. Apply targeted optional semantic critique only when risk and remaining deadline justify it; broader persona/grounding review is primarily offline evaluation.

A content check must preserve intentional rude/sarcastic/hostile fictional characterization when the plan allows it. Blanket politeness would defeat the product. Domain-specific acceptance rules are versioned; no keyword list can guarantee all knowledge-boundary or injection resistance.

## Recovery

Whitespace/format normalization is allowed if meaning is unchanged. Do not blindly cut a response to the first N words. For substantive failure, one repair may receive the violation and original trusted context under the original intent and tighter limits. A separate LLM critic cannot consume a third call: critique belongs in that repair request or offline evaluation. Revalidate fully. When the earlier model cutoff is reached, use the reserved time for an authored fallback or silence/end as appropriate. The fallback also passes validation/staging. Persistence failure yields a typed unavailable result rather than an unsafe unrecorded dispatch.

Track `policy_silence`, `authored_success`, `model_success`, `repair_success`, `error_fallback` separately. No failed candidate is sent to TTS. The runtime must be able to explain why a candidate was rejected without exposing private prompts to players.

## Acceptance / handoff

Test long reply, malformed JSON, injected instruction echo, fabricated evidence ID, valid ID with contradictory text, unsupported cue, stale revision, critique timeout and failed repair. Assert at most two total model calls and one delivered response per turn. Document semantic limitations and include labelled human scoring instead of claiming that self-critique proves correctness.
