# Generation and validation preview

This executable slice composes context -> deterministic behavior plan -> prompt -> provider -> validation -> optional repair. It produces a **response-ready preview**, not game delivery. See the [implementation plan](plans/I06-I07-generation-validation.md) and [review](reviews/2026-10-31-generation-validation-review.md).

## Run offline

After [setup](../SETUP.md), from the repository root:

```powershell
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_closing.json
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/station_clerk.json --text "Hello"
.\.venv\Scripts\python.exe -m pytest
```

The available smith uses a deterministic fake provider; it is not an LLM and cannot demonstrate response quality. The closing smith uses an authored refusal with zero model calls. JSON output includes the plan, response, status, violations, call count, usage completeness and timing profile. `--text` changes the utterance; edit a copy of the fixture to change persona, relationship or perceived state. Scenario timestamps are deterministic replay inputs.

## Configure OpenRouter or Gemini

Public transport settings belong in [configs/providers](../configs/providers/README.md). Copy `.env.example` to `.env` once and fill the relevant values locally:

```dotenv
# OpenRouter profile:
OPENROUTER_API_KEY=your-local-key
NPC_LLM_MODEL=your-selected-provider-model-id
```

Or use `GEMINI_API_KEY` and a Gemini model ID with the Gemini profile. Leave the unused key blank. No model is selected by default: choose one supported by your account and test its JSON support, quality, latency and output-token behavior.

```powershell
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json --live --config configs/providers/openrouter.yaml
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json --live --config configs/providers/gemini.yaml
```

Run one command for your configured provider. `--live` explicitly permits transmitting the scenario context to that API and can incur charges. Without it, the CLI always uses the fake, even if keys exist. Keys remain backend-only; never place them in YAML, fixtures or browser code. OS environment variables override `.env`; the selected profile's key variable takes precedence over the generic `NPC_LLM_API_KEY`. `NPC_LLM_MODEL`, `NPC_LLM_BASE_URL` and `NPC_LLM_RESPONSE_FORMAT` override public profile values. Set response format to `none` only when a compatible endpoint lacks JSON-object mode; strict parsing/validation still applies. There is no automatic fallback to a different vendor.

If an API cannot finish inside the default cutoff, an explicitly labelled development experiment can use:

```powershell
.\.venv\Scripts\python.exe -m npc.runtime fixtures/scenarios/smith_available.json --live --config configs/providers/openrouter.yaml --development-timeout-ms 10000
```

This reports `timing_profile: development`; success does not establish real-time performance. Missing key/model gives a sanitized configuration error before network use. Exit code 0 means an accepted preview (including authored/end), 1 means fallback/cancelled/busy, and 2 means invalid configuration/scenario. A fallback after an API error is not a successful live-generation test.

## What is enforced

| Component | Implemented behavior |
|---|---|
| `behavior/policy.py` | Combat end, uncertain-transcription clarification, threat warning, busy/closed refusal and exact greeting fast paths; conservative generation otherwise. Mixed greeting/question reaches generation. Prototype rules, not general intent understanding. |
| `generation/prompt.py` | Compact identity, goals, boundaries, warmth/caution, influence codes, relationship and current state; separate untrusted player/observation message. No complete diagnostic ledger or excluded values. |
| `generation/provider.py` | Replaceable async protocol, HTTPX chat-completions transport and offline fake; HTTPS except loopback; bounded body; sanitized failures; no hidden retries, redirects, tools or streaming delivery. |
| `validation/response.py` | Strict JSON/extra-field/duplicate-key rejection, finish reason, word/sentence/character limits, modes/cues, perceived evidence references, revision/epoch and basic assistant scaffolding checks. |
| `runtime/preview.py` | One shared model cutoff, at most two calls including one fresh repair, validated fallback, stale/cancelled result suppression, one active local provider request per reused runner. No waiting-work queue. |

Default timing is 3,000 ms response-ready with a 2,450 ms model cutoff, preserving validation/fallback reserve. Input packing uses a conservative **2,048 UTF-8 byte budget including a 256-byte framing reserve**, not an exact universal tokenizer. Oversize required context falls back before calling; it is not silently truncated. Default output cap is 160 model tokens including JSON; models that spend this on reasoning or truncate need evaluation/configuration. Repairs share the original cutoff and contain violation codes rather than rejected raw text. Auth/rate/transport/timeout failures receive no retry.

Reuse one `PreviewRunner` in a persistent integration. Its admission remains occupied until local provider cleanup settles even when the caller has already received a timeout/fallback. This bounds outstanding work without making slow cleanup block the response. Arbitrary custom providers that refuse cancellation cannot be forcibly stopped by asyncio; they keep the slot occupied, and event-loop/process shutdown may wait for them. The supported HTTPX adapter uses absolute and transport timeouts. Local cancellation does not guarantee remote cancellation or prevent billing.

## Verification and remaining scope

Offline regression covers each working component, mock HTTP payloads/errors/drip responses, structural failures/repair, persona differences, stale state, timeout, cancellation, slow cleanup and admission contention. The independent review reproduced two bugs despite an initially green suite: omitted disposition in prompts and cleanup delaying the caller. Both have regression tests and fixes. See the [review evidence](reviews/2026-10-31-generation-validation-review.md).

An initial [live Gemini 3.1 Flash-Lite sample](reviews/2026-10-31-behavior-quality-audit.md) now confirms this model works through the configured transport. It also exposed invented role/world details and social-policy gaps. Six development-profile generated samples took 3.6–6.1 seconds; one normal-profile request timed out at the cutoff and used fallback. This is not a quality/latency signoff or a general compatibility guarantee. OpenRouter remains untested live. No game/VRAM performance benchmark has been established.

Valid JSON and evidence IDs do not prove truth, entailment, lack of subtle disclosure or believable characterization. A test deliberately demonstrates that a false claim can pass structural checks. Unknown lore is constrained by prompting only; retrieval, explicit disclosure policies and labelled semantic/persona evaluation remain needed. There is no always-on LLM critic.

RAG/history packing, persistent relationships/memory, atomic validation-to-stage, idempotent game delivery, full M03 arbitration/cooldowns, browser console/characters and audio remain outside this slice. Authored responses are prototype variants, not a complete persona/template catalog. The preview cannot guarantee a game state remains unchanged after its final check. Do not connect it directly to an audible/game dispatch path until M02/M08 lifecycle guards exist.
