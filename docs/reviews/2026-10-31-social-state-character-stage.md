# Social-state and character-stage implementation review

2026-10-31. Deliberate self-review using the development/design-review skills; no independent reviewer is claimed. Scope follows the reviewed [social plan](../plans/I02-I03-social-memory.md) and [media plan](../plans/I16-character-stage-voice.md). Baseline ad55dc1 was pushed before changes as requested.

Verdict: conditional go for local manual testing. Production game delivery, semantic grounding, multilingual social quality and alongside-game resource performance are not signed off.

## Findings and resolutions

- High: input effects and remembered NPC speech needed distinct lifecycles. Added revision-checked durable heard-input events, staged previews and explicit console display acknowledgement; cancelled/unstaged replies are excluded. Tests cover restart, isolation, replay, cancellation, staging failure and conflicting overrides. This is not a production delivery outbox.
- High: history must not become trusted world knowledge or overflow the prompt. Added typed untrusted dialogue, indexed last-eight retrieval and bounded whole-exchange packing. Tests cover hostile history and omission accounting.
- Medium: indiscriminate profanity punishment and identical boundaries would defeat persona testing. Added English appraisal distinguishing incidental/quoted speech, directed abuse and trusted marked banter; temperament-specific boundaries, positive-gain cooldown, short stranger replies and sustained-abuse disengagement. Paired tests cover these distinctions. Mixed apology/question keeps the question eligible for generation.
- Medium: local media paths and browser text must not become executable voice commands or arbitrary file reads. Fixed profile routes/private-path restrictions, one-line protocol normalization, validated-result-only speech, bounded WAV/GLB handling and one speech process at a time are tested. Private assets never enter Git.
- Medium: review/browser checks exposed missing SkeletonUtils, unscaled model centering, reversed facing and CSP blocking blob textures. Corrected dependency/import integrity, transforms and local blob fetch policy; visually inspected actual textured models for all four profiles.
- Medium: rejected POSTs with unread bodies reset Windows sockets. Drain only bounded declared bodies before early rejection; repeated rejection tests pass.
- Low: missing favicon generated a browser 404; point favicon to the existing original SVG.

## Verification

- `.\.venv\Scripts\python.exe -m pytest -q`: **254 passed**, final resumed run 7.57 s.
- `.\.venv\Scripts\python.exe -m pip check`: no broken requirements.
- Isolated headless Chrome, separate profile: four actual local 3D models, game stone backdrop, composer under centre stage, source labels, desktop/mobile layout without horizontal overflow. Prior browser tests exercised saved score escalation/reload, inert HTML input, voice replay and cancellation/reset. No claim of automated visual quality scoring.
- Actual local Mantella interactive Piper: HTTP 200 `audio/wav`, validated 2.464-second WAV, cold synthesis **3,735 ms** after reconnect. Earlier warm probes approximately 0.8-1.0 s. Audio latency is separate from text; no hard performance percentile is established.
- Actual Skyrim assemblies: Adrianne/blacksmith, Hulda/barkeeper, Farkas/guard kit and Lydia/iron stand-in. GLBs approximately 7.34, 6.99, 12.23 and 8.72 MB, with a real Whiterun stone texture background. Game files were only read. Static rest poses have no game animations or lip sync; user explicitly made animation optional, and no animation data was exported.
- Two live Gemini memory requests: first `provider_timeout` at 9,469 ms, second `provider_http_error` at 5,109 ms; both returned typed fallback. Second trace packed one prior displayed exchange. These do **not** prove successful live recall or model realism. Network interruption occurred during final work; servers were restarted and local media rechecked afterward.

## Remaining gates

English regex rules can misread negation, sarcasm, indirect threats and unrecognized quotations. Labels/thresholds need quality evaluation. Structural output validation does not prove entailment. No RAG, production save synchronization, game delivery guarantee, full long-term memory or actual mechanical hostility is implemented. Database admission stops at a configured 250 MB threshold; archival remains future work. Render caps do not establish a 4 GB alongside-game VRAM guarantee. Portable Blender/PyNifly are offline tools only. Current public code is suitable for iterative local testing with these limits disclosed.
