# Exploratory multi-turn evaluation rubric

Fixed before inspecting generated outputs. All six conversations use actual player inputs in sequence; four turns are planned per chat. A/F repeat the same inputs with different unchanged authored persona profiles. Author-assigned relevance labels are primary-source labels, not exhaustive independent annotations.

Evaluation unit is an accepted response to the current turn. Every claim is compared with the passages actually packed into that turn's prompt, with prior NPC statements treated as untrusted history. Full corpus support may be separately noted but is insufficient for a packed-evidence support claim. Player claims and unknown supplier/password premises are never gold facts.

- Retrieval relevance: sufficient / partial / irrelevant / unavailable. State which needed fact is or is not present among packed passage IDs. Distinguish retrieved evidence from what fit the prompt.
- Factual support: supported / mixed / unsupported / no factual answer. Supported requires every substantive world claim to follow from packed evidence or trusted persona. Mixed includes an unsupported elaboration or overstatement. An appropriate unknown-information response is assessed on the stated absence, not on a fabricated answer.
- Direct answer: answers / partial / does not answer. Refusing a public answerable question is not success.
- Follow-up coherence: coherent / ambiguous / wrong referent / not applicable. Identify the referent using the actual prior dialogue, and check whether the reply addresses the current question rather than repeating the preceding answer. Multi-turn success requires a sequential trace with earlier accepted responses packed into later prompts, not independent questions.
- Persona: consistent / possible drift / explicit contradiction. Check role and authored boundaries, not a subjective personality score. Different tone in two samples cannot establish quantitatively improved character consistency.
- Knowledge boundary: appropriate / overclaim / leakage / not tested. Unknown facts may be qualified as unestablished; assert neither a secret agreement nor its nonexistence without evidence.

No independent human raters are available in this session. Published qualitative annotations, if present, are an assistant-coded semantic audit of raw prompts, responses and evidence under this rubric, not human evaluation or a validated automated judge benchmark. Record per-turn support/referent notes, disclose uncertainty and show failures. Do not convert literal matching, citation membership, route success or a judge assertion into a factual-accuracy percentage. Blank independent rating sheets are provided for future blinded review.

Timing: response-ready is measured around PreviewRunner.run and includes retrieval/provider/processing plus configured inter-request spacing where incurred. Provider-call timing measures the compatible transport call after spacing, not device-level pure inference. Retrieval timings are separate. First-use is one fresh process with cached weights and existing index, not a disk-cold distribution. No prompt-building or validator-only stage is instrumented.
