# Game demonstration availability

Checked 2026-11-03 after the user launched Skyrim through SKSE and authorized an interaction test/capture.

Observed running process: SkyrimSE.exe, PID 12912, executable `D:/steam/steamapps/common/Skyrim Special Edition/SkyrimSE.exe`.
Executable FileVersion: **1.7.104.0**. The standard `Data/SKSE/Plugins/AnimaConnector.dll`, `AnimaConnector.ini` and `versionlib-1-6-318-0.bin` were not found at this installation. Loopback connector health `http://127.0.0.1:8768/v1/health` was unreachable.

Current native source `src/npc/adapters/skyrim/native/plugin.cpp:408` declares compatibility only with 1.6.318.0; line 413 explicitly rejects a different runtime. The source was rechecked, not inferred only from documentation. Virtual mod-manager placement could differ from the physical folder, but does not resolve this explicit runtime mismatch.

No game installation, plugin, save or runtime was modified. No actual Anima NPC interaction was reproduced and no screenshot is claimed as such. A background/gameplay screenshot alone would not establish generated dialogue delivery and is therefore not substituted for Figure 5. To complete the demonstration, a compatible tested connector/runtime/profile and running bridge are required. Porting the plugin to 1.7.104.0 is a separate implementation/build/live-verification task, outside this paper revision's minimal instrumentation scope.

## Running-session follow-up

After the user explicitly requested checking version 1.7.104 rather than assuming failure, loaded-module inspection found skse64_1_7_104.dll and SKSE_HTTP.dll. The actual SKSE log reported initialization (SKSE version 2.3.1), checked MantellaDialogue/MantellaLauncher/MantellaSubtitles/SKSE_HTTP, and reported SKSE_HTTP loaded correctly. Neither that log nor loaded modules included AnimaConnector. A search for an Anima-named mod under D:/MO2/mods found none. These checks confirm the running game can load its current plugins, but do not establish that the current Anima connector works on this runtime. No DLL was installed or forced past its source-level version guard.
