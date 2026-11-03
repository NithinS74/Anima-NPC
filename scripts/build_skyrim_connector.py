"""Build/package the independent plugin. Never install it into Skyrim implicitly."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_RUNTIMES = ("1.6.318.0", "1.7.104.0")
NATIVE = ROOT / "src/npc/adapters/skyrim/native"


def command(arguments, cwd=ROOT):
    subprocess.run([str(value) for value in arguments], cwd=cwd, check=True)


def dependencies(fetch=False):
    pins = json.loads((ROOT / "configs/skyrim/native-dependencies.json").read_text(encoding="utf-8"))
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
        if fetch and (path / ".gitmodules").is_file():
            command(["git", "submodule", "update", "--init", "--depth", "1"], cwd=path)
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
    manifest = {"plugin_version": "0.3.0", "target_runtimes": list(SUPPORTED_RUNTIMES),
                "dll_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(), "dependencies": pins,
                "live_game_verified": False,
                "runtime_verification": {runtime: "not_live_verified" for runtime in SUPPORTED_RUNTIMES}}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dll, "SKSE/Plugins/AnimaConnector.dll")
        archive.write(NATIVE / "AnimaConnector.ini", "SKSE/Plugins/AnimaConnector.ini")
        archive.writestr("AnimaConnector/build.json", json.dumps(manifest, indent=2))
        archive.write(ROOT / "docs/SKYRIM_CONNECTOR.md", "AnimaConnector/README.md")
        archive.write(ROOT / "docs/reviews/2026-11-02-skyrim-connector.md", "AnimaConnector/reviews/2026-11-02-skyrim-connector.md")
        archive.write(ROOT / "configs/skyrim/native-dependencies.json", "AnimaConnector/source/native-dependencies.json")
        archive.write(ROOT / "configs/skyrim/native-dependencies.legacy-1.6.318.json", "AnimaConnector/source/native-dependencies.legacy-1.6.318.json")
        for source_file in NATIVE.rglob("*"):
            if source_file.is_file() and source_file.suffix in {".h", ".cpp", ".txt", ".cmake", ".ini"}:
                archive.write(source_file, "AnimaConnector/source/native/" + source_file.relative_to(NATIVE).as_posix())
        # Retain source licenses for statically linked/include-only dependencies.
        for name in pins:
            source = ROOT / ".tools" / name
            for filename in ("LICENSE", "LICENSE.txt", "LICENSE.MIT", "COPYING.txt"):
                if (source / filename).is_file():
                    archive.write(source / filename, f"AnimaConnector/licenses/{name}-{filename}")
            if name == "spdlog":
                archive.write(source / "include/spdlog/fmt/bundled/fmt.license.rst", "AnimaConnector/licenses/fmt-LICENSE.rst")
    (output / "build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def configure_arguments(cmake: Path, build: Path, generator: str):
    arguments = [cmake, "-S", NATIVE, "-B", build, "-G", generator, f"-DANIMA_DEPS={ROOT / '.tools'}"]
    if generator.startswith("Visual Studio"):
        arguments += ["-A", "x64"]
    else:
        arguments += ["-DCMAKE_BUILD_TYPE=Release"]
    return arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="download missing pinned build dependencies")
    parser.add_argument("--generator", default="Visual Studio 17 2022")
    parser.add_argument("--build-dir", type=Path, default=ROOT / "output/skyrim-build", help="Separate build trees for different native toolchains")
    args = parser.parse_args()
    try:
        pins = dependencies(args.fetch)
        cmake = find_cmake()
        build = args.build_dir.resolve()
        configure = configure_arguments(cmake, build, args.generator)
        command(configure)
        command([cmake, "--build", build, "--config", "Release", "--target", "AnimaConnector", "AnimaDeliveryTests", "AnimaRuntimeTests", "--parallel", "2"])
        command([cmake.parent / "ctest.exe", "--test-dir", build, "-C", "Release", "--output-on-failure"])
        dll = build / "Release/AnimaConnector.dll" if args.generator.startswith("Visual Studio") else build / "AnimaConnector.dll"
        print(package(dll, pins))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Connector build failed: {error}\n")


if __name__ == "__main__":
    main()
