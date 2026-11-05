# Vanilla dialogue delivery fix self-review

Scope: prevent arriving Anima output from cutting off the selected NPC's vanilla dialogue. Plan/review used develop-npc-component and review-npc-design; this is a self-review with no delegated agent.

Plan reviewed before coding: replace the hard-coded idle assumption with the engine's selected-speaker/active-line state, remove the normal-delivery stop call, retain pending-command polling and existing expiry/revision checks, and preserve explicit player barge-in. Exercise the engine-to-policy mapping through the existing standalone C++ delivery target, then run Python regression. No configuration, protocol, dependency or storage migration is needed.

The pinned [CommonLib MenuTopicManager header](https://github.com/alandtse/CommonLibSSE-NG/blob/8eaddedd1542290701ccb0e9e88b2af8b3cea597/include/RE/M/MenuTopicManager.h) exposes `IsCurrentSpeaker` and documents `currentTopicInfo` as valid while the NPC is talking. The native receiver now invokes `EvaluateDialogue`, which checks those fields and feeds the existing delivery policy. Missing managers, changed speakers and closed menus fail closed. An active line returns wait without an acknowledgement or insertion into the native seen-ID set, so subsequent polls can retry the same command. Invalid/expired commands are still rejected before waiting. The automatic `StopCurrentDialogue` call was removed; the explicit `BargeIn` path remains separate.

The actual native diff was reviewed for handle types, task-thread access, wait-path side effects and stop behavior. Actor handles are converted through the base reference accessor to the object-reference handle expected by CommonLib. No raw memory offsets, new relocation IDs, background polling mechanism or wait deadline extension was added. Existing unrelated Chatterbox/setup changes were preserved.

Verification:

- Standalone `tests/unit/adapters/skyrim_delivery.cpp` compiled and passed with both GCC and Clang using `-std=c++20 -Wall -Wextra -Werror`. Cases cover active-line waiting, repeated polls, line completion, expiry while waiting/after completion, changed speaker, closed menu and missing manager, alongside existing duplicate/state/combat/identity guards.
- `.venv/bin/python -m pytest -q`: **604 passed**, one third-party deprecation warning. These are offline checks, not native engine execution.
- `git diff --check`: passed.

The complete Windows SKSE DLL was not built on this Linux host, and live Skyrim behavior was not tested. Rebuild the DLL with the existing Windows build helper and reinstall its ZIP. In game, let a vanilla greeting/quest line run while Anima's reply arrives: the original line should finish before Anima starts. Also test a vanilla line that outlasts the pending reply's expiry (no late playback), closing dialogue while waiting, changing speakers, and intentional F8/text interruption. Verdict: source fix and offline mapping regression pass; Windows build and live verification remain required.
