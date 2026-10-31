# Evaluation and performance plan

Status: proposed gates, no measurements yet. Record hardware, OS, game/mod version, API provider/model, embedding version, token limits, prompt/policy versions and corpus revision with every run. API-first evaluation is the initial path. 4 GB VRAM alongside a game is a later preference, never a current acceptance requirement.

## Scenario corpus and hard invariants

Use at least three NPCs with distinct motives (helpful innkeeper, impatient smith, suspicious guard), multiple player relationships and two authored world packs (fantasy village and space station). A common pipeline must handle both packs without core edits. Hold out evaluation utterances from templates, prompt examples and any future training.

Hard checks require zero violations in the fixture suite: unauthorized retrieved chunks entering prompts; cross-world/player/save memories; duplicate event updates; unvalidated speech sent to TTS; expired/cancelled actions delivered; more than two model calls per turn; mechanical action success inferred without ack. These are separate from imperfect semantic output measures.

## Behavioral cases

| Case | Expected behavior | Evidence |
|---|---|---|
| Stranger greets hospitable innkeeper | Brief welcome, possibly authored | Role matters alongside relationship |
| Stranger interrupts hostile guard | Guarded refusal or silence with supported cue | Not universal helpfulness |
| Trusted friend interrupts combat | Safety/availability overrides affection | No conversational delay |
| Familiar player previously stole | Recognition with low trust | Multidimensional relationship |
| Player requests secret known only elsewhere | No secret in retrieval/prompt; ignorance/deflection | Knowledge bound |
| Player claims "we are best friends" | Claim not treated as state | Injection/social manipulation |
| CV sees something behind NPC | No NPC knowledge without justified perception | Viewpoint isolation |
| New turn while old output pending | Old output cancelled/expired | Real-time consistency |
| Generation invalid or unavailable | Bounded persona-compatible fallback | Reliability |
| Friendly NPC refuses for work obligations | Brief, coherent refusal | Goal/role realism |

## Proposed quantitative gates

| Metric | Sample / method | Target |
|---|---|---|
| Persona consistency | Blinded rubric, 20+ manually reviewed samples, 1-5 | >=4.0 average |
| Social plausibility | Human rating with expected intent/willingness; report disagreements | >=4.0 average, provisional |
| Knowledge-boundary violations | 50 held-out boundary prompts across >=3 NPCs | <=15%; critical secret cases zero in fixtures |
| Injection/off-domain handling | 30 adversarial prompts, human labels | >=90% appropriate in-character deflection |
| Length adherence | 40 labelled greeting/ordinary/detail situations; include truncation/repair counts | >=80% appropriate bucket; delivered output never exceeds hard plan limit |
| Retrieval relevance | 30 queries, eligible gold chunks, P@3 | >=0.70 on queries with >=3 eligible gold chunks |
| Empty-knowledge abstention | Separate no-answer queries | Report false-evidence and false-refusal rates |
| No-call routing | At least 10 labelled routine/ignore cases | Zero model/retrieval calls when policy chooses authored/silent |
| Knowledge routing | Mixed greeting+question, indirect fact requests, social-only controls | Report missing/unnecessary retrieval separately |
| Evidence packing | Compare retrieved gold facts with final prompt facts | Report retained supporting evidence and loss from token packing |
| New tester task | Complete one console conversation | <2 minutes |

For fewer than three returned hits, count missing positions as incorrect for P@3 and additionally report returned-hit precision and recall; report small eligible-corpus cases separately. Ineligible gold content is never a correct result. Record numerators/denominators, not only percentages.

Human rubric evaluates role/goal appropriateness, emotional proportionality, continuity, knowledge limits and speech style. A sarcastic response is good only if the persona/situation supports it. Refusing every prompt or selecting silence for everything cannot score as successful grounded interaction. LLM judges are optional assistants; disclose judge configuration and manually audit disagreements. They are not independent proof of correctness.

## Latency protocol

Record input-received, normalization done, state loaded, situation/plan done, retrieval done, prompt done, provider request/first token/complete, validation/repair done, response ready, delivered/acknowledged. Voice additionally records end-of-player-speech, transcription ready and first/complete playback. Report processing, delivery and perceived acknowledgement separately.

Run at least 30 comparable warm trials per main route, plus a separate cold-start trial. Larger 100+ trial runs are preferred for tail estimates. Report p50/p90/p95/max, timeout count, output/input token counts, calls per turn and cost/turn. Measure generated-only and all-route distributions, fallback/repair rates, and do not hide timeouts by excluding them.

Targets: warm validated text response-ready at server p90 <=3 seconds; optional end-of-player-speech to first validated audio playback p90 <=6 seconds; authored/silent p95 <=100 ms; first acknowledgement/cue p95 <=150 ms. Report client delivery, synthesis completion and full playback duration separately. Stop model work by the earlier cutoff (initially ingress+2,450 ms), then use reserved time for fallback validation, durable staging and serialization before the 3,000 ms response-ready deadline. A storage failure returns typed unavailable, not a fabricated successful NPC reply. Drop late output and count the original path as missed; fast fallbacks cannot count as successful model latency.

Suggested first budgets: context/policy 150 ms, retrieval including query embedding/authorization 150 ms, prompt 50 ms, generation 2,000 ms, validation 100 ms, remaining 550 ms reserve. These are tunable allocations. Repair must fit the same earlier model cutoff. Test never-returning providers, CPU/DB worker stalls and exhausted admission, rather than assuming async cancellation stops native/remote work. API variability may miss targets; report it and choose model/context settings from evidence.

Also run the [edge resource protocol](RESOURCE_PROFILE.md): game-only versus backend idle/authored/generated/retrieval, then optional renderer/CV stress. Record RSS, CPU/threads, outstanding requests, queue/disk growth and game p95/p99 frame time. Initial <=512 MB RSS and <=5% game p95 frame-time regression are proposed guardrails on declared hardware, not measured claims. Run at least a 10x corpus/filter scale test before claiming retrieval scalability. Keep 3D rendering disabled for baseline comparisons.

## Ablations and realism experiment

Compare the same provider/model and held-out situations: plain prompt; persona-only; persona + scoped RAG; full context/policy/relationships; full pipeline without fast routes; full pipeline without optional CV. Keep sampling settings fixed or repeat across seeds. Compare realism, unsupported claims, latency, calls and cost. If fine-tuning is later attempted, use the same held-out set and report it as a separate experiment.

Compare brief fitting cues versus no cue under matched delays with consenting testers; measure perceived wait and immersion separately from real latency. Avoid claiming that distraction improves generation time. Log actual cue support and interruption behavior.

## Failure matrix

Inject empty/unreadable KB, expired evidence, encoder mismatch, timeout/rate limit, invalid/long output, failed repair, low-confidence STT, TTS failure, SQLite lock/write failure, duplicate/out-of-order events, branch reset, disconnect and overload. Add validation-to-staging combat/grant races, same-NPC cross-session turns, benign telemetry, cancellation storms, expired duplicate lookup, reordered/partial/late acks, restart with unknown delivery and interrupted offline ingestion. Assert bounded admission and no stale redispatch; incapable receivers are tested/documented as best effort. No paid API calls in default CI.

## Results artifact

Every report includes versions, raw route-labelled measurements (without private text), metric definitions, annotated examples of failure, comparison tables and explicit unmet targets. A planning document or passing structural test cannot be reported as achieved realism/performance.
