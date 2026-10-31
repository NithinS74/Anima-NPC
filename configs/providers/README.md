# Provider profiles

Store public, reviewed transport settings here. `offline.yaml` selects a fake; `openrouter.yaml` and `gemini.yaml` select the shared chat-completions adapter. Model IDs are intentionally blank until chosen locally. No vendor SDK or extra requirements file is needed.

Put keys and `NPC_LLM_MODEL` in the root `.env` (see [.env.example](../../.env.example)); OS environment variables take precedence. OpenRouter reads `OPENROUTER_API_KEY`, Gemini reads `GEMINI_API_KEY`. Each can instead use the generic `NPC_LLM_API_KEY`. Never add an actual key field/value to a YAML profile. The strict loader rejects unknown fields and profiles over 16 KB.

Use `--live --config configs/providers/<profile>.yaml` with `python -m npc.runtime`. Without `--live`, that CLI uses the offline fake. Optional generic overrides are `NPC_LLM_BASE_URL` and `NPC_LLM_RESPONSE_FORMAT` (`json_object` or `none`). Another compatible endpoint can use a copied public profile with `provider: chat_completions`; compatibility still needs testing. HTTPS is required except loopback HTTP; local runtimes can use a nonsecret key placeholder if necessary.

Profile endpoints/authentication follow the official [OpenRouter chat-completion API](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion) and [Gemini OpenAI compatibility guide](https://ai.google.dev/gemini-api/docs/openai). A small [Gemini 3.1 Flash-Lite live experiment](../../docs/reviews/2026-10-31-behavior-quality-audit.md) confirmed transport/JSON compatibility for that model, with unresolved behavioral/grounding/latency gaps. OpenRouter and other models remain unverified. See the [preview guide](../../docs/GENERATION_VALIDATION.md) for commands, budgets and limitations.
