# Optional local lab media

Public configuration only: `media.json` binds profile IDs to private models/voices and discloses appearance sources; `skyrim_models.json` defines selected head/outfit mesh assemblies. Raw extraction assets remain local. The owner-approved runtime archive is now tracked through Git LFS in the private project; normal setup installs it automatically. The lab works without them using original illustrations.

## Copy the installed Mantella voice runtime

```powershell
.\.venv\Scripts\python.exe -m tools.npc_lab.setup_assets --mantella-root "D:\MO2\mods\Mantella\SKSE\Plugins\MantellaSoftware"
```

This copies the existing custom Piper engine, its license/data and selected ONNX/JSON voices into ignored `assets/private/npc_lab/piper/`. The source installation is unchanged. This adapter uses Mantella's interactive `load_model`/`synthesize`/`exit` protocol, not standard Piper command-line flags. Weights/executables are not downloaded or redistributed by the repo. Profile mappings: Mira femalecommander, Elin femalenord, Daren maleguard, Iona femaleeventoned.

## Convert assets from an installed Skyrim SE copy

Verified local tooling: official portable [Blender 4.5.9](https://download.blender.org/release/Blender4.5/) (official SHA-256 checked), [PyNifly 30.2.0](https://github.com/BadDogSkyrim/PyNifly/releases/tag/v30.2.0), and `lz4==4.4.5` in the single root requirements file. Place portable tools under ignored `.tools/npc-assets/`; no global addon install or Blender preferences save is needed. Download/extract the Windows Blender archive into `blender/` and PyNifly release so `pynifly/io_scene_nifly/__init__.py` exists. These heavyweight offline tools are not launched during conversation or required by the core.

```powershell
.\.venv\Scripts\python.exe -m tools.npc_lab.import_skyrim --game-root "D:\steam\steamapps\common\Skyrim Special Edition" --blender ".tools\npc-assets\blender\blender-4.5.9-windows-x64\blender.exe" --pynifly-directory ".tools\npc-assets\pynifly" --profiles mira elin daren iona
```

The importer reads selected version-105 BSA entries and referenced textures, assembles static meshes with Blender/PyNifly, embeds resized textures, and writes GLB plus a Whiterun stone PNG under `assets/private/npc_lab/`. Only selected entries are extracted, not the full game. Conversion logs/manifests remain private there. Budget/check failures stop conversion. Original game files are unchanged. Verified GLB sizes were approximately 7.34/6.99/12.23/8.72 MB for Mira/Elin/Daren/Iona.

See [appearance mappings and limitations](../../docs/NPC_LAB.md). Default exports use static rest poses with simplified materials, not mod-exact appearances. The optional `--facial` extension below preserves native facial morphs, with approximate timing. Do not commit converted game data or voice models. Public Three.js 0.187.0 viewer code is vendored separately with MIT license and integrity manifest in `tools/npc_lab/web/vendor/`.

## Native facial expressions and original game fonts

The installed vanilla FaceGen heads/eyes for all four profiles matched the corresponding TRI connectivity and vertex counts. Opt in to the verified native facial import:

```powershell
.\.venv\Scripts\python.exe -m tools.npc_lab.import_skyrim --game-root "D:\steam\steamapps\common\Skyrim Special Edition" --blender ".tools\npc-assets\blender\blender-4.5.9-windows-x64\blender.exe" --pynifly-directory ".tools\npc-assets\pynifly" --profiles mira elin daren iona --facial --relaxed
```

This preserves a small allowlist of original blink/speech/mood deltas on matching head, eye, mouth and brow parts. Incorrect topology fails; it does not replace the character's face with a generic head. Export occurs to a temporary GLB and replaces the previous model after validation. Body geometry remains a static rest pose. Browser timing is app-driven and approximate; no native full-body clip, phoneme alignment or perfect lip sync is claimed. Expressions can be switched off, respect reduced motion, and reset speech movement when playback pauses/ends.

For the actual original dialogue font, obtain official portable [FFDec 26.4.0](https://github.com/jindrapetrik/jpexs-decompiler/releases/tag/version26.4.0), extract it under `.tools/npc-assets/ffdec/`, and ensure a compatible Java runtime is available. Then:

```powershell
.\.venv\Scripts\python.exe -m tools.npc_lab.import_font --game-root "D:\steam\steamapps\common\Skyrim Special Edition" --ffdec-jar ".tools\npc-assets\ffdec\ffdec.jar"
```

The importer reads the installed `Skyrim - Interface.bsa`, extracts `fontconfig.txt` and `fonts_en.swf`, and privately converts the embedded Futura CondensedLight/Futura Condensed into browser fonts. The local game configuration identifies CondensedLight as the dialogue font. Font files and their source/hash manifest stay in `assets/private/npc_lab/fonts/`. Nothing is published to Git or installed system-wide. Restart Anima and inspect **Inspect context** for the active typography source. Teammates without these assets retain the bundled open-font fallback.

Four original public SVG environments now distinguish the forge, inn, gate and registry. They live in `tools/npc_lab/web/scenes/` and require no game installation. They are role illustrations, not claimed game screenshots. The earlier stone-only background remains a compatible optional asset/fallback.

Use `--relaxed` to bake the modest arms-down posture using matching native shoulder/elbow rigs; unsafe or unmatched rotations fail. This is a static conversation pose, not a new animation clip. Actual screenshot backdrops and source metadata are in the installed runtime pack; original SVG art is fallback-only. The mesh-only scenery rendering experiment was rejected during visual review rather than shipped. See [private runtime packaging](../../assets/runtime/README.md).
