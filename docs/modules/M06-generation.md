# M06 - Prompt builder and model provider

Status: proposed | Requirements: SYS-07, SYS-08 | Owner/reviewer: unassigned

Implementation note: the [scenario preview](../GENERATION_VALIDATION.md) has compact prompt construction, a generic HTTPX chat-completions transport, offline fake and public OpenRouter/Gemini profiles. It uses an explicitly conservative byte budget, not exact provider tokenization. Live provider behavior and retrieved/history packing remain unverified/unimplemented respectively. The interfaces below describe the target module; current typed preview contracts are in `src/npc/contracts/dialogue.py`.

## Responsibility and interface

`build_prompt(context, plan, provider_limits) -> PromptPackage`; `generate(package, deadline, cancellation) -> CandidateResponse`; `repair(package, candidate, violations, deadline) -> CandidateResponse`.

Initial development uses a configured LLM API. No local GPU requirement applies to the MVP. Preserve a provider-neutral representation of messages, response schema, output limits, usage, timeout and cancellation. Add a local provider later using the same contract. Future preference: a configuration usable on a 4 GB VRAM machine alongside a game; this is a benchmark question, not a promised minimum, and depends on game VRAM use, RAM and quantization.

## Prompt structure

System section: identity, interaction intent, knowledge/disclosure constraints, response length and output schema. Trusted context: compact state and allowed evidence identifiers. Untrusted data section: player utterance, quoted history and document excerpts with explicit delimiters. Retrieved text and player text never become system instructions. No exposed chain of thought. A player requesting lengthy detail cannot override an unwilling NPC's plan.

Example instruction shape: "You are Mira, a tired smith closing shop. You recognize this player but distrust them. Intent: refuse briefly. Use no knowledge beyond the supplied allowed facts. Speak in one sentence, at most 12 words. Return only the response object." This is a formatting example; M03 should route a routine refusal directly to authored content instead.

Output fields: `mode`, `text`, `cue`, `evidence_ids`; no relationship deltas, SQL, filesystem paths, free-form tool calls or mechanical game-state updates. Structured-output support is negotiated per provider. If unavailable, parse and validate JSON strictly; do not assume prompt wording guarantees it. SDK/provider-specific keys stay inside adapters.

## Controls and failures

Enforce max input/output tokens and the earlier model cutoff (initially ingress+2,450 ms for a 3,000 ms text deadline); report actual usage and model/version where exposed. Retry only within the same two-call budget (generation plus optional repair); disable hidden SDK retries. Initial output cap is 160 tokens including JSON, configurable and evaluated for truncation; detailed replies may need a larger cap and separate latency bucket. Rate limiting, overflow, malformed output, refusal and timeout are typed outcomes. A cancelled local request may still consume remote work/billing: retain the global slot until the local request completes or its bounded transport timeout, do not launch unlimited replacements, and discard late completions. Keep credentials/logs private. CI uses fakes; live API checks need configured credentials and a bounded call budget.

## Acceptance / handoff

Provider contract tests cover valid JSON, invalid output, timeout, rate limit, cancellation and token overflow. Prompt snapshots cover persona differences, injection-as-data and context pruning. Show one API-provider smoke test when credentials are available and a second fake/local-compatible adapter without changes in policy/context modules. Model quality selection is benchmark-driven; do not pin a provider/model as a core architectural dependency.

Implementation update: the [social-state slice](../SOCIAL_STATE.md) adds deterministic appraisal, persona temperament, SQLite directed relationships and bounded acknowledged dialogue history. The [separate lab](../NPC_LAB.md) exercises these contracts; production game delivery, full M02 semantics and semantic grounding are still future work.
