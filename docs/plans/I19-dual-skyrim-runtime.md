# Dual Skyrim runtime support plan (I19)

2026-11-03. User requests support for Skyrim 1.7.104.0 while retaining 1.6.318.0, plus genuine in-game screenshots for the report. Work remains on latest; unrelated .gitignore/research/evaluation changes are preserved.

## Acceptance and boundaries

- One native plugin explicitly accepts 1.6.318.0 and 1.7.104.0, rejects other runtimes with a useful diagnostic, and uses a modern relocation/layout implementation rather than bypassing the version guard.
- Preserve the existing bridge wire protocol, observation filtering, delivery checks, bounded queues and old runtime selection. No Mantella runtime dependency, new dialogue orchestrator or paid calls needed for compatibility verification.
- Native dependency source is pinned, supports Address Library format 5 and the older AE format, and is packaged with license/source provenance. A legacy dependency manifest is retained for reproducibility of the previous 1.6.318-only build.
- Build/package metadata lists both runtime targets and separates build/offline checks from actual per-runtime game verification. C++ unit checks validate allowlist and supported-feature decisions; Python tests validate package metadata and build helper behavior. Full regression and native CTest run before readiness.
- Stage the reviewed artifact as a separate Anima mod for the user's current game, preserving existing mods/settings; use a disposable session/save, verify SKSE load/logs, bridge context and actual text delivery before claiming 1.7.104 readiness. Capture original screenshots only after genuine interaction. The 1.6.318 path is unit/build checked unless that executable is also available for a separate live run.

## Findings before implementation

Current source hard-codes 1.6.318 both in exported SKSE metadata and inside SKSEPlugin_Load. Its 2022 CommonLib pin understands older Address Library formats, not the installed format-5 versionlib-1-7-104-0.bin. New Skyrim also changes native layouts, so merely accepting another version is incorrect. Primary upstream CommonLibSSE-NG now handles those formats/layouts while retaining SE/AE branches. Candidate stable pin: alandtse/CommonLibSSE-NG v15.5.0, 8eaddedd1542290701ccb0e9e88b2af8b3cea597; inspect/build against its documented native dependencies and exported version flags. C++23/modern MSVC plus DirectXTK are build dependencies, separate from the root Python requirements.

The installed Visual Studio 2022 IDE is under F:/visual_studio/visual studio, but its C++ compiler/Windows 10 SDK have not yet been found. Prefer existing native components; otherwise prepare bounded project-local build tools, not a global Python dependency tree. Upstream prebuilt CommonLib may be used only when compiler family/toolset, runtime options and verified release hash match; otherwise compile pinned source. Do not reuse incompatible prebuilt objects.

## Implementation plan

1. Pin and fetch the modern CommonLib and required native dependencies under ignored .tools. Preserve the prior dependency manifest as legacy provenance. Resolve the compiler/SDK and source-build configuration without overwriting teammate checkouts.
2. Add a small dependency-free runtime compatibility header consumed by the plugin and C++ tests. Use the same two-version table for metadata and runtime admission; keep unknown/VR versions rejected. Move version rejection before engine dereferences; log selected runtime/build capabilities.
3. Adapt plugin calls to modern CommonLib accessors where runtime layouts differ. Replace hand-authored engine entry wrappers only where the new library provides the required equivalent. Verify every used relocation ID and struct access for both runtime branches; do not claim old ABI preservation merely from compilation.
4. Extend CMake and build helper for modern toolchain/dependency checks and native test targets. Package explicit target_runtimes and per-runtime live verification false by default; preserve source/licenses and old recipe. Add meaningful package/helper unit tests.
5. Review actual diff for version flags, unsafe struct claims, error initialization and preservation of old runtime branches. Run native build/CTest and full .venv pytest.
6. Stage as a separate mod and verify live 1.7.104 with user-coordinated restart (an already running game cannot acquire a new DLL). Start loopback bridge in offline/scripted mode initially; inspect actual context, stale/closed session handling, subtitles/receipts. Preserve logs and original screenshots. Update docs and report only what was observed. Actual 1.6.318 live validation remains explicit if the executable is unavailable.

## Plan self-review (before coding)

Review using develop-npc-component and review-npc-design; no delegated/independent reviewer. Go for bounded compatibility work. The principal correctness risks are V5 metadata flags, moved actor/player layouts, changed engine wrappers and wrongly advertising universal compatibility. Resolve with a current pinned library, exact runtime allowlist, native assertions/tests, package export inspection and a live session before promotion. No broad patching/signature scans, runtime injection or disabling compatibility checks is planned. Native build/install does not authorize replacing other mods, game executables or player saves. User authorization covers the new Anima integration and screenshots; preserve the rest of the installation.

## Compatibility review correction

Verified primary SKSE loader source for v2.1.2 and current master. The legacy loader rejects unknown versionIndependence bits; modern loaders' StructsPost629 bit would therefore break the old runtime. The plugin now declares **no generic version independence**, uses its exact two-version list, and sets the format-5 capability without falsely claiming NoStructUse. Both loader paths can admit an exact listed version. Since generic Address Library admission is not claimed, the plugin performs its own matching-file/header preflight before SKSE initialization; the modern library still parses/resolves the complete file. Native tests cover both exports, old/new formats, missing/truncated/mismatched files, and adjacent unsupported runtimes. The manual audio relocation shim is replaced by equivalent modern CommonLib methods using the same relocation IDs/flags.
