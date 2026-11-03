# I21: Anima-only in-game interaction

2026-11-03. User requests an Anima-labelled conversation option, in-game text box using SkyUI-compatible UI, voice input/output, clear attributed console logs, generated dialogue and eventual removal of Mantella. Work stays on latest; preserve saves, other mods and research artifacts.

## Audit and acceptance matrix

- Existing: exact 1.6.318/1.7.104 native build, live 1.7.104 context and authored text receipts; [ANIMA] correlated logs and direct --say command. Missing: player-facing entry/text box, configured STT/TTS/live provider, explicitly authored game profiles/knowledge and isolated live run.
- Installed: SkyUI and UIExtensions. UIExtensions supplies reusable list/text-entry SWFs and mod callbacks. No Creation Kit/Papyrus compiler detected. Do not copy Mantella scripts/UI or relabel its replies.
- Speech: Windows David/Zira voices and en-US dictation recognizer installed; standalone local Piper assets also exist. Start with self-contained Windows speech endpoints for a deterministic installation without models/downloads; optional Piper quality upgrade is separate. No lab HTTP/runtime import into the core.

## Sequenced implementation checklist

- [ ] A. Local loopback speech service: bounded validated JSON -> mono PCM WAV and bounded microphone WAV -> transcript/confidence. Single in-flight worker, timeout, cancellation cleanup and no shell interpolation. Explicit health/startup failures; no fake STT text or silent claim of voice success. Unit tests/fake subprocess plus actual short synthesis/transcription check where available.
- [ ] B. Native UIExtensions-based Anima controls: F7 while normal NPC dialogue is open shows Anima Start/Type/Voice/End options; text entry returns through a new typed correlated game event into existing player_input. F8 push-to-talk remains. Cancel/close/combat/load invalidate UI/input. Reject callbacks unless our menu/session owns them; do not handle another mod's text. Bound all text/queues. Test pure UI state decisions and Python event mapping. Build/CTest exact supported runtimes. This is an in-game options menu, not yet an authored vanilla dialogue-list topic or MCM.
- [ ] C. Connect local STT/TTS and show actual feature health, transcript, audio synthesis/staging, native audio start/finish. Configure an existing compatible real provider only with a valid available model; bounded actual test authorized by the user's end-to-end request. Never pretend offline output is generated. Author NPC persona/knowledge explicitly; missing bindings remain unknown.
- [ ] D. Add a normal dialogue-list Anima topic and SkyUI MCM/settings with a small independently authored ESP/Papyrus layer. Establish buildable source/toolchain and test record/script packaging before installation. No speculative binary or uncompiled dummy scripts presented as working UI.
- [ ] E. Reversible Anima-only MO2 test profile (preserve Default), disabling Mantella ESP/native modules/software only there after A-D are staged. Do not remove installation or saves. User-coordinated SKSE restart; verify loaded modules, text, microphone, generated output, audible voice, stop/cancel and clean logs. Update research evidence only from actual observations.

## Plan self-review before coding

Self-review using develop-npc-component and review-npc-design; no delegation. Go for A/B with isolated contracts and tests. Use existing UIExtensions assets through their installed public event/Scaleform contract; do not invent a custom Flash toolchain or replace SkyUI. UI callback ownership and custom-menu closure are correctness gates. Native dialogue topic/MCM requires a real plugin/script build; it cannot be claimed from a hotkey menu. Speech is a loopback adapter service, never a second dialogue engine. Existing 32-event queue, one active session, 15-second mic and 30-second turn bounds remain. Failures leave text available and state speech failure clearly. Full .venv pytest, native CTest/build and actual installed-game checks precede readiness. Old-version live check remains unavailable. No main push or broad mod disablement.


## A/B implementation review update

Local Windows SAPI synthesis produced a valid 78926-byte 2.465-second PCM WAV. Synthetic recognition returned inaccurate words at confidence0.697, so recognition quality is explicitly unverified; no accuracy claim. Subprocess input is JSON/file-based, workers are single-flight, timeout/cancellation kills before temporary cleanup. Mounted endpoint review caught the parent bridge JSON-only/256KiB guard blocking microphone WAV; the new path-specific media/size allowance has an integration test. Focused Python42 passed. Native F7 UIExtensions list/text entry built with exact runtime allowlist and native ownership checks; CTest2/2 passed. Initial compile caught source BOM conversion and the absence of the old DebugNotification helper; fixed encoding and used the existing Papyrus Debug.Notification entry point. Installed-game UI visibility remains a gate, not established by those checks.


## Live UI finding and revised plan self-review

User reports F7 pauses after the Anima notification but renders no list. Actual native log confirms menu dispatch on0.3.0, not successful menu population. Existing population waits in the regular game task, which may not progress under the custom menu pause. Correction before promotion: populate the Scaleform menu through bounded SKSE AddUITask work, independently of the paused game task; only UI values are touched there. Native snapshots/events remain on the game task. Use an atomic menu request generation, at most one queued UI task, cancel on owner end, and log actual root-object/invoke success. Keep UI callbacks/session validation and do not count dispatch or a paused screen as a working menu. Test generation invalidation and rerun native/Python checks before another controlled restart.


## Dialogue/MCM authoring plan review

Official Caprica0.3.0 compiler is available locally (SHA2560037e54cf3a1021e976278d9a637e8ae541aaf9ebeb8d274b6c2cfe32f4ee559). Official SkyUI source exposes SKI_ConfigBase initialization/options; SkyUI runtime remains an installed dependency, not copied Anima code. .NET runtimes exist but no SDK. Prefer a pinned typed Mutagen0.53.1 build tool targetingnet8 to create/read-back the Anima ESP rather than guessing TES4/QUST/DIAL/INFO/VMAD bytes. A bounded project-local SDK install must check expanded disk requirements and source hash; preserve unrelated tools. Author Anima scripts only, compile against accurate API declarations/official SDK interfaces, package actual PEX plus original PSC. Unit/read-back tests must verify Anima topic, quest/script associations and masters. This remains unverified until a real compiled ESP/PEX is generated and loaded. No empty placeholder plugin or altered Mantella records is acceptable.


Second live UI observation: UI-thread root lookup and method invocation succeeded but the list remained invisible. Primary SKSE PapyrusUI.cpp InvokeArrayT shows that UI.InvokeStringA expands strings into separate scalar arguments. The initial native call incorrectly passed one GFx array. Corrected to the exact scalar argument sequence used by UIExtensions' public script, retaining UI-task scheduling and ownership guards. Method lookup success alone was insufficient; actual user-visible entries remain the acceptance gate. The bridge was also offline during this test; its availability is a separate failure and must be restored before response tests.


## Conversation review: immediate repair plan (self-reviewed)

User confirms UI/text now work but voice is inaudible and vanilla speech does not interrupt. Independent authorized reviewer found that native started receipts precede any observed IsPlaying, all failures occur at the500ms watchdog, text barge-in conflicts can resync/end sessions, and Skyrim snapshots omit social/history state. Repair order: (1) engine resource preflight/canonical path/new handle/explicit routing and priority; bounded observed-start state machine reporting failed when never played; (2) owned text/voice barge-in cancels old generation/playback and stops current actor dialogue using verified StopCurrentDialogue virtual, with resync restricted to actual session loss; (3) wire existing SocialStore/history to native completed delivery rather than generation success; (4) explicit calibrated social-input variants, warned-and-acknowledged escalation with typed native action; (5) finish native dialogue topic/MCM and isolated profile/live checks. Mechanical hostility is user-authorized but must be deterministic and opt-in per authored guard policy, request-deduplicated and revision/actor/session checked; generated text cannot trigger combat. Every changed slice gets meaningful tests and full regression before promotion. No human-realism guarantee follows.


## Memory policy compatibility correction

To satisfy explicit recall/follow-up requirements, dialogue-source prompts now retain prior NPC utterances under npc_utterance_unverified instead of deleting them. This intentionally changes the previous omission policy; it does not elevate a prior model claim to current facts, observations or source evidence. The regression oracle is updated to require the exact history only in the untrusted user-data compartment, absence from NPC_CONTEXT/observations/retrieved_evidence, unchanged current input and an explicit not-world-facts instruction. Semantic resistance to memory contamination remains an empirical quality gate, not proven by structural tests. Two full-suite failures identified the old omission assertion; requirements/tests are changed deliberately rather than suppressing them.
