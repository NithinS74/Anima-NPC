# Dual Skyrim runtime implementation self-review

2026-11-03. User authorized 1.7.104 support while retaining 1.6.318, and genuine in-game screenshots for the report. This is a labelled self-review using develop-npc-component/review-npc-design; no independent reviewer agent was used. Plan: [I19](../plans/I19-dual-skyrim-runtime.md).

## Implemented result

One native 0.2.0 plugin accepts exactly Skyrim 1.6.318.0 and 1.7.104.0. A pinned current CommonLibSSE-NG handles old format-2 and new format-5 Address Libraries and runtime-dependent layouts. The old dependency manifest is preserved as provenance; game/bridge wire semantics, core generation, bounded delivery and other mods are unchanged.

The explicit SKSE metadata list and load-time admission share the native runtime table. No generic version independence is advertised: the older loader rejects unknown post-629 bits. The format-5 capability is present without falsely claiming NoStructUse. Missing/truncated/mismatched Address Library headers fail preflight before engine initialization; CommonLib performs full parsing/resolution. Modern audio wrappers replace the manual shim using the same known relocation IDs and flags.

## Source/build review

- `runtime_support.h`: exact allowlist and format preflight. Unknown adjacent builds and VR remain rejected.
- `version_metadata.h`: old/new packed versions, terminator, no generic independence flags and explicit V5 capability.
- `plugin.cpp`: runtime admission before game relocations; library diagnostics; updated wrappers; existing command checks/cancellation preserved.
- Native dependency pins include CommonLib v15.5.0 and required modern fmt/spdlog/DirectX headers/toolkit. All are source-pinned; fetch refuses dirty/mismatched checkouts. The historical pins remain separate.
- Build helper supports Visual Studio 2022 or a configured Ninja environment, with distinct build directory option. Package lists both targets and never infers live verification from compilation. Native sources, hashes, pins and licenses are retained.
- Package/helper tests cover dual target metadata, no invented live signoff, unchanged DLL bytes, generator-specific flags and preservation of dirty/mismatched checkouts.

## Checks completed

- Native Release DLL built with project-local official MSVC 14.44 / SDK 10.0.26100.0 and CMake 3.31.6/Ninja 1.13.0.
- CTest: **2/2 passed**: existing delivery guards and runtime/metadata/library-preflight checks (both versions, missing/wrong/truncated headers and unsupported builds).
- Actual compiled PE export inspection: SKSEPlugin_Load and SKSEPlugin_Version present; target versions 1.6.318.0 and 1.7.104.0; versionIndependence=0, extended V5 flag=2. DLL SHA256 recorded in `output/skyrim-mod/export-verification.json` and build manifest.
- Focused Python bridge/build checks: **34 passed**. Full project offline regression: **514 passed in 15.99 s** (`.venv/Scripts/python.exe -m pytest`); report in `output/skyrim-mod/regression.txt`.

Initial configuration lacked the local Ninja path; corrected from the installed wheel layout. An initial native test compile used a stale target configuration and then duplicate PCH generation exhausted E: space. Only this task's downloaded installer packages and redundant generated connector/test PCH files were removed after checking resolved paths; the completed CommonLib build was retained. Connector/test PCHs were disabled rather than deleting unrelated user data. Final native build and tests passed.

## Live verification status

Partial live verification completed on 1.7.104.0. After a user-coordinated MO2/SKSE restart, the actual AnimaConnector log records plugin 0.2.0 loading with Address Library format 5 at 10:38:54 local time and initialization on port 8768 at 10:39:04. The bridge received genuine Jenassa dialogue context (Skyrim.esm base 000B9982) at 05:09:42--05:09:48 UTC, including actor identity, offered dialogue, equipment and weather. The session closed at 05:09:50 UTC. This verifies native load and game-to-bridge observations; it does not yet verify response delivery.

Two automatic game-client screenshots were captured. Visual inspection of the later frame found a large black obstruction and clipped dialogue, so it is unsuitable for publication and is not included in the paper. Originals remain in ignored output/skyrim/screenshots. The desktop-control helper still fails during sandbox initialization. The user is coordinating the next restart/conversation; actual response receipts and a clear foreground screenshot remain pending. No old-runtime live claim is made.

Verdict: build/offline go for controlled 1.7.104 live test; 1.6.318 live behavior remains unverified on this machine until its matching executable/Address Library is available. No source push/main merge authorized or performed.


## Live delivery follow-up

A second user-coordinated launch at 10:43:11 local time loaded plugin 0.2.0 with format 5 and initialized port 8768. Controlled text input Hello traversed the actual offline preview/core pipeline, selecting the authored reply What do you need? (no model call). The native receiver reported started then interrupted for the first delivery when the dialogue closed. In an uninterrupted retry, delivery f7557716ca5944b38945b476583e1788 reported started at 05:16:18.568217 UTC and completed at 05:16:20.627733 UTC, session 14764-1793682809849-2-4. This verifies native text-delivery lifecycle, not audible voice, live model/RAG behavior or comprehensive game compatibility. The captured frames remain obscured; no publication screenshot is claimed. Verdict: go for the observed 1.7.104 authored text smoke test; broader live evaluation and a clear screenshot remain open, as does the old-runtime live run.
