"""Bundle the compiled mod with a clean companion source/setup distribution."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def distributable(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if any(part in {".git", ".venv", ".tools", "output", "data", "__pycache__", "private_audit"} for part in path.parts):
        return False
    if path.name.startswith(".env") and path.name != ".env.example":
        return False
    if path.suffix.lower() in {".pem", ".key", ".sqlite", ".sqlite3", ".log", ".pyc", ".bsa", ".fuz", ".xwm", ".onnx", ".pth", ".safetensors"}:
        return False
    if name in {"assets/runtime/anima-media.zip", "assets/runtime/manifest.json"}:
        return False  # optional browser-lab media is not part of the game companion
    return True


def package(root, names):
    mod = root / "output/skyrim-mod/AnimaConnector.zip"
    guide = root / "INSTALL_SKYRIM.md"
    if not mod.is_file() or not guide.is_file():
        raise ValueError("Build the current AnimaConnector.zip and install guide first")
    with zipfile.ZipFile(mod) as archive:
        build = json.loads(archive.read("AnimaConnector/build.json"))
        dll = archive.read("SKSE/Plugins/AnimaConnector.dll")
        if hashlib.sha256(dll).hexdigest() != build["dll_sha256"]:
            raise ValueError("Native package hash mismatch")
    destination = root / "output/release"; destination.mkdir(parents=True, exist_ok=True)
    result = destination / "Anima-Skyrim-0.3.0.zip"
    temporary = result.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(set(names)):
            path = root / name
            if distributable(name) and path.is_file():
                archive.write(path, "Anima/" + name)
        archive.write(mod, "Anima/mod/AnimaConnector.zip")
        archive.writestr("Anima/RELEASE.json", json.dumps({"version": "0.3.0", "dll_sha256": build["dll_sha256"],
            "target_runtimes": build["target_runtimes"], "live_game_verified": False,
            "model_weights_included": False}, indent=2))
    temporary.replace(result)
    (destination / (result.name + ".sha256")).write_text(hashlib.sha256(result.read_bytes()).hexdigest() + "  " + result.name + "\n")
    return result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    raw = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    names = raw.decode().strip("\0").split("\0")
    print(package(ROOT, names))


if __name__ == "__main__":
    main()
