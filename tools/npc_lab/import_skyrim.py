"""Offline, selective import of installed Skyrim assets for the private lab."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from tools.npc_lab.service import ROOT
from tools.npc_lab.skyrim_archive import BsaArchive


def referenced_textures(raw):
    return {BsaArchive.normalize(match.decode()) for match in re.findall(rb"textures[\\/][ -~]*?\.dds", raw, flags=re.I)}


def import_models(game_root: Path, blender: Path, addon: Path, profiles):
    data = game_root / "Data"
    private = ROOT / "assets/private/npc_lab"
    source = private / "source"
    manifest_dir = private / "conversion"; manifest_dir.mkdir(parents=True, exist_ok=True)
    definitions = json.loads((ROOT / "configs/npc_lab/skyrim_models.json").read_text())
    if not (addon / "io_scene_nifly/__init__.py").is_file() or not blender.is_file():
        raise ValueError("portable Blender/PyNifly paths unavailable")
    archives = [BsaArchive(p) for p in sorted(data.glob("Skyrim - Meshes*.bsa"))]
    archives += [BsaArchive(p) for p in sorted(data.glob("Skyrim - Textures*.bsa"))]
    index = {name: archive for archive in archives for name in archive.entries}
    background = "textures/architecture/whiterun/wrstoneblocks01.dds"
    if background in index:
        index[background].extract(background, source)
    previous = manifest_dir / "manifest.json"
    results = json.loads(previous.read_text()) if previous.exists() else {}
    for persona_id in profiles:
        definition = definitions[persona_id]
        if len(definition["meshes"]) > 8:
            raise ValueError("too many components")
        textures = set()
        for name in definition["meshes"]:
            path = index[name].extract(name, source)
            textures.update(referenced_textures(path.read_bytes()))
        for name in textures:
            if name in index:
                index[name].extract(name, source)
        manifest = dict(source=str(source.resolve()), addon_directory=str(addon.resolve()),
                        meshes=definition["meshes"], appearance=definition["appearance"],
                        background_source=str((source / background).resolve()),
                        background_output=str((private / "background/skyrim-stone.png").resolve()),
                        output=str((private / "models" / f"{persona_id}.glb").resolve()))
        config = manifest_dir / f"{persona_id}.json"
        config.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        # Importer resolves some shared race/eye defaults not named in the NIF.
        # One bounded second pass extracts only the missing defaults it reports.
        for attempt in range(2):
            result = subprocess.run([str(blender.resolve()), "--background", "--factory-startup", "--python",
                str(ROOT / "tools/npc_lab/blender_export.py"), "--", str(config.resolve())], cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=120)
            (manifest_dir / f"{persona_id}-pass{attempt}.log").write_text(result.stdout, encoding="utf-8")
            missing = set(re.findall(r"Could not find texture \w+: '([^']+\.dds)'", result.stdout))
            extracted = 0
            if attempt == 0:
                for raw_name in missing:
                    name = BsaArchive.normalize(raw_name)
                    if name in index:
                        index[name].extract(name, source); extracted += 1
            if not extracted:
                break
        output = Path(manifest["output"])
        if "LAB_EXPORTED" not in result.stdout or not output.is_file() or result.returncode:
            raise ValueError(f"conversion failed for {persona_id}; inspect private conversion log")
        results[persona_id] = dict(appearance=definition["appearance"], bytes=output.stat().st_size,
            sha256=hashlib.file_digest(output.open("rb"), "sha256").hexdigest(), meshes=definition["meshes"])
        print(f"Converted {persona_id}: {definition['appearance']} ({output.stat().st_size:,} bytes)", flush=True)
    (private / "conversion/manifest.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--pynifly-directory", type=Path, required=True)
    parser.add_argument("--profiles", nargs="+", choices=["mira", "elin", "daren", "iona"], default=["mira", "elin", "daren", "iona"])
    args = parser.parse_args()
    try:
        import_models(args.game_root, args.blender, args.pynifly_directory, args.profiles)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("Skyrim import failed; check paths and assets/private/npc_lab/conversion/ logs.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
