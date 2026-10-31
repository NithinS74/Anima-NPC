"""Optional local Skyrim font import; no game font is distributed with Anima."""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from tools.npc_lab.media import LabMedia
from tools.npc_lab.service import ROOT
from tools.npc_lab.skyrim_archive import BsaArchive


def import_fonts(game_root, ffdec_jar, *, java="java"):
    private = ROOT / "assets/private/npc_lab"
    source = private / "source"
    archive = BsaArchive(Path(game_root) / "Data/Skyrim - Interface.bsa")
    swf = archive.extract("interface/fonts_en.swf", source)
    archive.extract("interface/fontconfig.txt", source)
    extracted = private / "fonts-extracted"
    subprocess.run([java, "-jar", str(Path(ffdec_jar).resolve()), "-export", "font", str(extracted.resolve()),
                    str(swf.resolve())], check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    destination = private / "fonts"; destination.mkdir(parents=True, exist_ok=True)
    selected = {"FuturaCondensedLight.ttf": "5_Futura CondensedLight.ttf", "FuturaCondensed.ttf": "7_Futura Condensed.ttf"}
    manifest = {}
    for filename, original in selected.items():
        matches = list(extracted.rglob(original))
        if len(matches) != 1:
            raise ValueError("expected installed English font not found")
        shutil.copy2(matches[0], destination / filename)
        manifest[filename] = dict(source="Skyrim - Interface.bsa / interface/fonts_en.swf", verified_tool="FFDec 26.4.0",
                                  sha256=hashlib.sha256((destination / filename).read_bytes()).hexdigest())
    if not LabMedia(ROOT).game_fonts_ready():
        raise ValueError("extracted font validation failed")
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Imported the installed Skyrim dialogue/interface fonts locally. Restart Anima.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument("--ffdec-jar", type=Path, required=True)
    args = parser.parse_args()
    try:
        import_fonts(args.game_root, args.ffdec_jar)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Font import failed. Check the game, Java and FFDec paths; no game files were modified.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
