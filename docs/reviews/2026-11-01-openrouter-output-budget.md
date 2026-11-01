# OpenRouter reasoning/output budget fix

Plan: make OpenRouter reasoning explicitly configurable in the existing provider profile, disable it by default for short NPC dialogue, and classify a length-limited response without answer content as provider_output_limit. Preserve the 160-token output allowance, current total deadlines, two-call maximum and response validator. Expose the setting in the existing inspector and the specific failure in existing UI feedback. Correct the local Nemotron model ID to the fully qualified catalog ID without changing keys.

Plan self-review (not independent): this needs a boolean request setting, not a larger general token budget, an extra model call, or reasoning text displayed as NPC dialogue. Keep Gemini's existing reasoning_effort behavior unchanged; reject conflicting reasoning controls. Add request/profile, empty-length-response and runtime fallback regression cases. No new dependencies, queues or automatic retries.

Reproduction: current OpenRouter request returned HTTP 200, finish_reason=length, content=null, and nonempty reasoning at max_tokens=160. Current code classified that as provider_protocol. A minimal request with reasoning.enabled=false returned HTTP 200, finish_reason=stop, nonempty answer content and no reasoning. These were local live diagnostics against the configured free endpoint; no private key or reasoning text is stored here.

Reference: https://openrouter.ai/docs/guides/best-practices/reasoning-tokens documents that reasoning consumes max_tokens on Chat Completions, and that length-limited responses can contain no answer content.

Validation: focused provider/config/runtime tests and full offline regression, followed by a bounded live check through the actual context/RAG/prompt/validation pipeline. Final outcomes are reported in the task handoff; a working transport is not a grounding-quality signoff.

Implementation self-review: the new control is optional and strict-boolean, Gemini keeps its existing minimal-effort setting, conflicting controls fail configuration validation, and reasoning text is never used as answer text. Empty output at finish_reason=length reports a typed output-limit error without adding retries. Existing response validation and deadlines remain in force.

Focused validation: 60 provider/config/runtime tests passed. A live full lab -> existing RAG HTTP -> Nemotron -> validation check for ?Who is Eorlund Gray-Mane?? returned repair_success in approximately 3.94 seconds, with three passages packed and one repair after truncated initial output. The resulting answer contained unsupported personal/death claims: this verifies transport compatibility, not factual grounding, and the weak raw-dialogue retrieval/attribution remains a known limitation. No player state was written by that diagnostic; it used a disposable LabService without persistent storage.
