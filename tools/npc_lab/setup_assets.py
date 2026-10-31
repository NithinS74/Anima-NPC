"""Copy installed Piper runtime/selected voices to ignored lab assets. No downloads."""

import argparse
import shutil
from pathlib import Path

from tools.npc_lab.media import LabMedia


def copy_piper(source: Path, destination: Path, voices):
    if not (source / "piper.exe").is_file() or not (source / "LICENSE.md").is_file():
        raise ValueError("installed Piper runtime/license not found")
    for voice in set(voices):
        for suffix in (".onnx", ".onnx.json"):
            if not (source / "models/skyrim/low" / (voice + suffix)).is_file():
                raise ValueError("selected installed voice/model config missing")
    if source.resolve() == destination.resolve():
        raise ValueError("copy destination must differ from the game/mod installation")
    destination.mkdir(parents=True, exist_ok=True)
    for file in source.iterdir():
        if file.is_file() and file.suffix.lower() in {".exe", ".dll", ".ort", ".md"}:
            shutil.copy2(file, destination / file.name)
    shutil.copytree(source / "espeak-ng-data", destination / "espeak-ng-data", dirs_exist_ok=True)
    models = destination / "models/skyrim/low"
    models.mkdir(parents=True, exist_ok=True)
    for voice in set(voices):
        for suffix in (".onnx", ".onnx.json"):
            shutil.copy2(source / "models/skyrim/low" / (voice + suffix), models / (voice + suffix))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mantella-root", type=Path, required=True, help="MantellaSoftware folder containing piper/")
    args = parser.parse_args()
    try:
        media = LabMedia()
        copy_piper(args.mantella_root / "piper", media.piper, media.settings.voices.values())
        print("Copied installed Piper and four selected voices into ignored assets/private/npc_lab/piper/.")
        print("Original installation unchanged. Do not publish these local assets/model weights.")
    except (OSError, ValueError):
        print("Asset copy failed; check the installed Piper folder, selected voice files and available disk space.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
