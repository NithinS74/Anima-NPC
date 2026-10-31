# Manual NPC lab: implementation plan and self-review

Outcome: a separate localhost browser chat box for manually testing four strongly authored personas with configurable relationship/state. A Windows `.bat` launcher uses the existing `.venv`, opens the browser and starts the lab. No Skyrim launch/modification, asset conversion, new package dependency, production HTTP API or core-runtime rewrite.

## Boundaries and acceptance

- `tools/npc_lab/` owns the test-only HTTP/composition code and static HTML/CSS/JS/portraits. It imports the existing core contracts, builder and `PreviewRunner`; the core never imports the lab. This separate location follows the user's explicit isolation request rather than the earlier proposed embedded `runtime/web/` console.
- `fixtures/personas/npc_lab/` holds validated public persona profiles: dry smith, hospitable innkeeper, suspicious guard and formal station clerk. Profiles include motives, style, boundaries, defaults and starter test questions. They are fictional test data, not extracted game NPCs or verified world/RAG knowledge.
- Chat controls: NPC, stranger/friend/distrusted presets, all five relationship scores, mood, available/busy/closed/combat and weapon state. Each turn builds fresh canonical observations/snapshot. Display route/status/intent, actual response, latency/model/call count and context influences. Do not present a fallback/fake as model success.
- API mode is a server launch option: offline by default; launcher explicitly starts Gemini live using existing local `.env`. Label the live mode/cost and development deadline in the UI. A `--realtime` launch option uses the unchanged core timing limits; quality-testing mode uses 10 s without claiming real-time success. Timing is fixed per launch to keep one reused runner and one admission slot across modes.
- Single-turn context is explicit: chat log is visual history only, capped at 60 messages. Do not invent a parallel memory/prompt pipeline in the lab. Parameter changes/reset clear the log and cancel pending work; revision/epoch and cancellation prevent a superseded result from appearing.
- One persistent asyncio loop and one reused runner per timing profile share a single lab admission guard (one turn globally). No pending queue. HTTP worker concurrency <=8; bounded body <=16 KB and finite socket timeouts. Cancellation bypasses inference. Static routes are a fixed whitelist, no filesystem browsing.
- Bind only `127.0.0.1`. Validate Host, same-origin POST and a per-launch CSRF token. Never serve `.env` or raw provider failures; render text using DOM text nodes. API requests supply a profile ID and validated test controls, never arbitrary file paths/provider URLs/keys/persona policy.
- Portraits are original small SVG illustrations, not 3D Skyrim meshes. Read-only game-directory check found BSA/plugin packaging. Extraction/rig conversion is not justified for this simple console; optional game asset work remains separate.

## Plan review (self-review, before implementation)

The separate console adds warranted manual observability without changing core behavior. Reuse current contracts/provider rather than duplicate generation or add dynamic agents. Standard-library local HTTP is sufficient for this single-user developer tool; it is not a deployment server. Four structured profiles provide targeted contrast but do not fix the already-recorded grounding/social-policy gaps. Interface traces must expose those gaps. Avoid browser-side keys, arbitrary static directories and unbounded server threads. Thread-to-loop coordination is needed only to keep cancellation responsive during one model call.

Implementation measurement: the four complete profile/control prompts were 2,065–2,166 bytes. The lab therefore explicitly uses a 3,072-byte cap (shown in the UI), preserving all inputs rather than quietly truncating or immediately falling back. Core CLI defaults remain 2,048 bytes. Oversize messages still fall back. The 3 s timing experiment includes this declared lab-specific prompt budget.

## Verification

Unit-test profile loading/schema, fresh scenario mapping, overrides/isolation, one-turn admission/cancellation, fake/live mode labels and timing. HTTP integration tests verify static/JSON routes, validation/body limits, Host/Origin/token guards, private-path denial and no secret leakage, using fake providers only. Run full offline regression and pip check. Smoke-check the real browser layout and a fake turn, plus one small opted-in live turn if configured. Validate launcher startup from another working directory; no additional paid regression suite.

## Results

Implemented the standalone lab, four validated authored profiles, original SVG portraits and `.bat` launcher. Self-review and corrections are recorded in the [review](../reviews/2026-10-31-manual-npc-lab.md). Full offline regression: **196 passed**, including 28 new tests. Desktop/mobile browser checks and one live Gemini turn through the actual HTTP endpoint passed; the live response still contained unsupplied ambience, explicitly recorded as a remaining core grounding gap. Launcher was verified from a different working directory. No new dependency, game asset import or runtime-core edit was required. See the [usage guide](../NPC_LAB.md) for exact limitations and commands.
