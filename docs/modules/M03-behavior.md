# M03 - Engagement and behavior policy

Status: proposed | Requirement: SYS-04 | Owner/reviewer: unassigned

Implementation note: a [scenario-preview subset](../GENERATION_VALIDATION.md) now supplies deterministic combat/threat/busy/closed/greeting routes and conservative generation limits in `src/npc/behavior/policy.py`. Full disclosure policy, cooldowns, repetition handling and the complete decision/template catalog remain planned. The requirements below describe the target module.

## Responsibility and interface

`decide(situation, state, policy_config) -> InteractionPlan` selects whether to respond, communication intent, affect, disclosure level, length and permissible cues. The plan is independent of the model provider. It consumes facts already resolved by context builder and does not query Chroma directly.

## Rule order

1. Check target validity, session termination and urgent interruptions.
2. Apply role/goal/availability and threat rules. Immediate combat can end engagement.
3. Interpret social context: stranger/friend/rival, status, trust, repeated interruption and explicit player intent.
4. Decide silence, refusal, warning, brief acknowledgement, factual reply or elaboration.
5. Select `silent`, `authored`, `generate` or `end`; define retrieval need only for novel knowledge-bearing speech.
6. Select eligible template/cue variants using persona, cooldown and seeded repetition avoidance.

Initial heuristics cover known greetings/refusals, not arbitrary natural-language understanding. `knowledge_need` is `none`, `required` or `uncertain`: known social-only input uses supplied persona/state/history; factual intent uses scoped retrieval; ambiguous factual content may use one bounded retrieval pass. Mixed greeting-plus-question must not be swallowed by a greeting rule. Unknown nuanced input routes to generation under a conservative plan with uncertainty/ignorance permitted; no second planning/classification LLM is added. Measure routing misses. Sarcasm comes from authored disposition/context; occupation can create a reason to assist strangers.

## Plan fields

`route`, `intent`, `affect`, `engagement`, `disclosure_policy`, `knowledge_need`, `max_words`, `max_sentences`, `allowed_cues`, `template_id`, `reason_codes`, `policy_version`. Silence has zero speech limits and may select a nonverbal cue. Defaults: greeting <=12 words, ordinary reply <=40 words/two sentences, explicit detail <=90 words/four sentences; detail is permitted only if NPC willingness and knowledge allow it.

## Acceptance / handoff

- Busy smith + repeated greeting -> authored refusal; zero retrieval/model calls.
- Helpful innkeeper + stranger -> brief assistance rather than generic rejection.
- Known player + low trust -> guarded reply; secrets remain inaccessible.
- Fearful stranger threatened -> warn/withdraw if supported; no generated attack command.
- Favorable friend during combat -> immediate safety behavior.
- Deliberate silence -> valid success, not an error fallback.

Provide a labelled decision table, template catalog and fake policy. Record disagreements as tuning decisions rather than calling one universal rule "realistic human behavior".

Implementation update: the [social-state slice](../SOCIAL_STATE.md) adds deterministic appraisal, persona temperament, SQLite directed relationships and bounded acknowledged dialogue history. The [separate lab](../NPC_LAB.md) exercises these contracts; production game delivery, full M02 semantics and semantic grounding are still future work.
