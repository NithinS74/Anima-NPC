"""Build/package the independent plugin. Never install it into Skyrim implicitly."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "src/npc/adapters/skyrim/native"


def command(arguments, cwd=ROOT):
    subprocess.run([str(value) for value in arguments], cwd=cwd, check=True)


def dependencies(fetch=False):
    pins = json.loads((ROOT / "configs/skyrim/native-dependencies.json").read_text())
    for name, pin in pins.items():
        path = ROOT / ".tools" / name
        if not path.exists():
            if not fetch:
                raise ValueError(f"Missing {name}; rerun with --fetch to download pinned build dependencies")
            path.mkdir(parents=True)
            command(["git", "init", path])
            command(["git", "remote", "add", "origin", pin["url"]], cwd=path)
            command(["git", "fetch", "--depth", "1", "origin", pin["commit"]], cwd=path)
            command(["git", "checkout", "--detach", "FETCH_HEAD"], cwd=path)
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True).strip()
        if revision != pin["commit"] or dirty:
            raise ValueError(f"{name} checkout differs from the pinned source; preserve it and use a clean pinned checkout")
    return pins


def find_cmake():
    choices = [ROOT / "output/build-tools/cmake/data/bin/cmake.exe"]
    if discovered := shutil.which("cmake"):
        choices.append(Path(discovered))
    for path in choices:
        if path.is_file():
            return path
    raise ValueError("Install CMake >=3.25, or install cmake==3.31.6 into output/build-tools with pip --target")


def package(dll: Path, pins):
    output = ROOT / "output/skyrim-mod"
    output.mkdir(parents=True, exist_ok=True)
    path = output / "AnimaConnector.zip"
    manifest = {"plugin_version": "0.1.0", "target_runtime": "1.6.318.0",
                "dll_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(), "dependencies": pins,
                "live_game_verified": False}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dll, "SKSE/Plugins/AnimaConnector.dll")
        archive.write(NATIVE / "AnimaConnector.ini", "SKSE/Plugins/AnimaConnector.ini")
        archive.writestr("AnimaConnector/build.json", json.dumps(manifest, indent=2))
        archive.write(ROOT / "docs/SKYRIM_CONNECTOR.md", "AnimaConnector/README.md")
        archive.write(ROOT / "docs/reviews/2026-11-02-skyrim-connector.md", "AnimaConnector/reviews/2026-11-02-skyrim-connector.md")
        # Retain source licenses for statically linked/include-only dependencies.
        for name in pins:
            source = ROOT / ".tools" / name
            for filename in ("LICENSE", "LICENSE.txt", "LICENSE.MIT"):
                if (source / filename).is_file():
                    archive.write(source / filename, f"AnimaConnector/licenses/{name}-{filename}")
            if name == "spdlog":
                archive.write(source / "include/spdlog/fmt/bundled/fmt.license.rst", "AnimaConnector/licenses/fmt-LICENSE.rst")
    (output / "build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="download missing pinned build dependencies")
    parser.add_argument("--generator", default="Visual Studio 16 2019")
    args = parser.parse_args()
    try:
        pins = dependencies(args.fetch)
        cmake = find_cmake()
        build = ROOT / "output/skyrim-build"
        command([cmake, "-S", NATIVE, "-B", build, "-G", args.generator, "-A", "x64", f"-DANIMA_DEPS={ROOT / '.tools'}"])
        command([cmake, "--build", build, "--config", "Release", "--target", "AnimaConnector", "AnimaDeliveryTests", "--parallel", "2"])
        command([cmake.parent / "ctest.exe", "--test-dir", build, "-C", "Release", "--output-on-failure"])
        print(package(build / "Release/AnimaConnector.dll", pins))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Connector build failed: {error}\n")


if __name__ == "__main__":
    main()
