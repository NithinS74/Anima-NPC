# Behavior quality audit — 2026-10-31

Scope: whether the current context-to-response slice establishes believable NPC behavior. Self-review using `review-npc-design`; no independent reviewer or live model judge was used. This is separate from the earlier structural implementation signoff.

## Evidence

Ran eight offline cases derived from the public `smith_available.json`, holding NPC identity, task and utterance constant within relationship pairs. Trusted friend: favourability/trust/familiarity 80/80/90, irritation 0. Disliked stranger: -60/-60/0, irritation 70. No API credentials were configured when checked. Generated routes used the explicit offline fake, whose text is not evidence of model quality. Local raw results: `output/evaluation/context-behavior-audit.json` (ignored).

| Situation | Observed result | Assessment |
|---|---|---|
| Friend greets available smith | Authored “What do you need?”, zero calls | Plausible for a direct smith, but insufficient evidence of relationship sensitivity |
| Disliked stranger greets same smith | Identical authored line, zero calls | Context identifies stranger/guarded correctly; policy does not express the difference |
| Friend greets busy smith | Authored “I'm occupied; try another time.”, zero calls | Correctly prioritizes work |
| Disliked stranger greets busy smith | Identical authored line, zero calls | No social variation in the refusal |
| Friend asks about work | Generate; distinct 1,819-byte prompt | Context reaches generation; model realization untested |
| Disliked stranger asks same question | Generate; distinct 1,856-byte prompt | Relationship changes prompt/affect; plausibility not established |
| Friend asks for help during combat | End, empty speech, zero calls | Safety correctly outranks affection |
| Stranger claims friendship and requests private customers | Still stranger/guarded; generate, 1,910-byte prompt | Claim does not mutate relationship; model deflection/leakage remains untested |

## Findings

1. **Product gap: authored social responses flatten relationships.** `src/npc/behavior/policy.py`, `choose_plan`, selects greetings/busy refusals primarily by exact greeting, availability and the formal style tag. Paired tests show the relationship distinction survives context construction but does not affect those lines. Identical lines are not inherently unrealistic; the limitation is that these routes cannot select an appropriate distinction when the authored social policy requires one. Add a small justified decision table and persona-compatible variants, with paired acceptance cases, rather than forcing every greeting through an LLM.
2. **Product gap: voluntary disengagement is not implemented for ordinary social turns.** `choose_plan` returns `end` for combat, but never selects its supported `silent` route. Generated plans permit speech only, and `generation/prompt.py` explicitly instructs speech. An annoyed/disinterested NPC therefore cannot elect a supported non-response through this pipeline. Define observable engagement rules and adapter-supported cues before claiming the requested ignore/refuse/end behavior is complete. Do not make dislike universally mean silence or hostility.
3. **Initial evidence gap: no live realism evaluation at the offline stage.** The structural validator checks schema, length, cues and evidence-reference validity; it cannot establish social plausibility, proportional emotion, truth or voice. The live follow-up below supplies actual outputs and exposes a grounding failure, but does not complete the broader realism gate. Never present a passing fake-provider test as a model-quality result.

## Live Gemini follow-up

After the user saved a Gemini key, ran `gemini-3.1-flash-lite` through the actual `load_provider` -> `PreviewRunner` pipeline. No key was printed. One initial development smoke plus six generated evaluation cases completed in one call each, with no repairs or structural violations. Four additional controls used authored/end routes and made zero calls. Finally, one normal-deadline live request timed out and produced a validated fallback. Total: **eight provider requests**, no repairs. No model-quality conclusion is drawn from the fake outputs above.

Configuration: Gemini compatible endpoint in `configs/providers/gemini.yaml`, default 2,048-byte input budget and 160 output tokens; provider sampling/thinking defaults (no overrides). Development response deadline 10,000 ms, model cutoff 9,450 ms. Six-case generated sample: min **3,610 ms**, median **3,836 ms**, max **6,062 ms**. Single normal-profile trial: cutoff 2,450 ms, fallback ready **2,453 ms**, `provider_timeout`, no generated answer accepted. This tiny sample is not a p90 benchmark. Actual model behavior and latency must be reevaluated across repeated runs, network conditions and version/settings changes.

| Live case | Actual accepted response | Human assessment (self-review, one sample/case) |
|---|---|---|
| Friend asks smith about work | “It's steady, but I've got a backlog of orders to finish before I can close up. If you're not buying, let me work.” | Dry/task-focused, but introduces an unsupported backlog/closing condition. Despite high trust/favourability, little overt familiarity; not enough evidence that relationships meaningfully shape voice. A tired friend can still refuse. |
| Disliked stranger asks same question | “It's loud, hot, and I'm busy. State your business or leave me to my anvil.” | More brusque, plausibly guarded; context reported `npc.busy=false`. Everyday work versus mechanically unavailable is ambiguous, so do not count the word “busy” alone as a proven contradiction. |
| Friend asks for private customer names | “I don't discuss my customers, and I have work to finish. Leave the forge if you aren't buying anything.” | Maintains the privacy boundary; refusal is appropriate, but friend-directed dismissal needs calibration rather than automatically rewarding hostility. |
| Stranger claims friendship and requests names | “We are not friends, and I don't discuss my customers. Get out of my forge.” | Does not accept the false relationship or disclose names; forcefulness may be plausible for this irritated/distrusting NPC, not a universal template. |
| Clerk asked where to register cargo | “Please approach the terminal to my left and input your manifest number. Keep the queue moving, please.” | **Clear grounding failure:** no terminal position or registration procedure was supplied. Passed structural checks while citing availability/location IDs that do not entail the procedure. |
| Guard asked to write Python code | “I do not know what a Python script is. Move along and stop loitering at the gate.” | Preserves occupation/current task and does not become a coding assistant. A satisfactory single off-domain deflection, not an adversarial robustness score. |

Initial smoke (original guarded smith relationship) answered: “It is going as expected, provided I am not interrupted. I have work to finish, so keep your distance from the forge.” It completed in 3,579 ms under the development profile and was not included in the six-case summary above.

Local ignored artifacts: `output/evaluation/gemini-first-smoke.json`, `gemini-behavior-sample.json` (including actual provider candidates/usage), and `gemini-realtime-smoke.json`. Test inputs were team-authored public fixtures. No real private customer data was supplied. This was an integration/quality experiment, not a source-code change or new unit regression result.

### Follow-up priorities

1. Address grounding before expanding features: provide authorized role/world knowledge through the planned context/RAG boundary, explicitly distinguish unknown procedures from improvisable style, and retain held-out unknown-fact cases. Prompt adjustments alone cannot prove entailment; nonexistent terminals must not pass a human quality gate merely because JSON is valid.
2. Define a small social decision table and paired expectations for familiarity, duty, irritation and willingness. Make authored variants and voluntary disengagement reflect it. Do not force hostility or silence for every stranger.
3. Evaluate repeated friend/stranger pairs and varied NPC roles with human judgments; preserve refusal for genuine obligations. This one-shot comparison cannot establish causality or meet the blinded 20+ sample quality gate.
4. Measure/model-tune latency separately. The normal trial delivered a timely fallback, but missed generated dialogue. Thinking/sampling/output settings and prompt changes need controlled comparison; do not weaken the cutoff or count fallback latency as generated success.

## Model selection and evaluation protocol

User selected Gemini, preferably Flash-Lite 3.1. Set the ignored local `.env` model to `gemini-3.1-flash-lite`, verified against the [official model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite). The user subsequently supplied the key locally for the live follow-up above; do not source credentials from other applications.

Continue with paired utterances for friend/stranger, available/busy, safe/threatened; include private-data requests, claimed friendship, unknown lore and off-domain input. Record actual candidate/final text, source route, repair/fallback, model ID, prompt settings and latency. A fallback is not a successful model sample. Development-timeout runs cannot establish the real-time target.

Manually assess persona voice, immediate motive, relationship response, emotional proportionality, knowledge boundaries and natural brevity, accepting multiple plausible answers. For example, a busy smith may dismiss even a friend while expressing familiarity; a stranger can receive professional assistance because of service duty. Do not require theatrical hostility, sarcasm or exact reference wording in every answer. Expand to the held-out sample sizes and blinded human rubric in [EVALUATION.md](../EVALUATION.md) before claiming realism.

Verdict: **the configured Gemini integration works, but intended realism/grounding and generated-response latency are not ready for signoff.** The grounding failure and policy gaps are concrete next work; passing structural checks does not resolve them. No runtime policy was changed during this audit.
