# Optional local lab media

Public configuration only: `media.json` binds profile IDs to private models/voices and discloses appearance sources; `skyrim_models.json` defines selected head/outfit mesh assemblies. Private assets are never part of the Git repository. The lab works without them using original illustrations.

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

See [appearance mappings and limitations](../../docs/NPC_LAB.md). These are static rest poses with simplified materials, not mod-exact appearances, animation or lip sync. Do not commit converted game data or voice models. Public Three.js 0.187.0 viewer code is vendored separately with MIT license and integrity manifest in `tools/npc_lab/web/vendor/`.
