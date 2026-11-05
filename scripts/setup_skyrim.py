"""Prepare the companion and install only Anima's DLL/INI into an existing game."""

import argparse
import configparser
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = {"1.6.318.0": 2, "1.7.104.0": 5}


def game_version(executable):
    if os.name != "nt":
        raise ValueError("Game installation must run on Windows")
    from ctypes import wintypes as W
    api = ctypes.WinDLL("version", use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [W.LPCWSTR, ctypes.POINTER(W.DWORD)]
    api.GetFileVersionInfoW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, W.LPVOID]
    api.VerQueryValueW.argtypes = [W.LPCVOID, W.LPCWSTR, ctypes.POINTER(W.LPVOID), ctypes.POINTER(W.UINT)]
    ignored = W.DWORD()
    size = api.GetFileVersionInfoSizeW(str(executable), ctypes.byref(ignored))
    if not 0 < size < 1024 * 1024:
        raise ValueError("Cannot read SkyrimSE.exe version")
    buffer = ctypes.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(executable), 0, size, buffer):
        raise ValueError("Cannot read SkyrimSE.exe version data")
    pointer, length = W.LPVOID(), W.UINT()
    if not api.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 16:
        raise ValueError("Missing executable version information")
    signature, _, ms, ls = struct.unpack("<4I", ctypes.string_at(pointer, 16))
    if signature != 0xFEEF04BD:
        raise ValueError("Invalid executable version information")
    return f"{ms >> 16}.{ms & 65535}.{ls >> 16}.{ls & 65535}"


def check_game(game, version_reader=game_version):
    if not (game / "Data/Skyrim.esm").is_file() or not (game / "SkyrimSE.exe").is_file():
        raise ValueError("Choose the Skyrim folder containing SkyrimSE.exe and Data")
    version = version_reader(game / "SkyrimSE.exe")
    if version not in RUNTIMES:
        raise ValueError(f"Skyrim {version} is unsupported; supported: {', '.join(RUNTIMES)}")
    if not (game / "skse64_loader.exe").is_file():
        raise ValueError("Install the matching SKSE loader first (see INSTALL_SKYRIM.md)")
    library = game / "Data/SKSE/Plugins" / ("versionlib-" + version.replace(".", "-") + ".bin")
    header = b""
    if library.is_file():
        with library.open("rb") as stream:
            header = stream.read(4)
    if header != struct.pack("<I", RUNTIMES[version]):
        raise ValueError(f"Install the matching Address Library: {library.name}")
    return version


def choose_provider(root, current):
    from dotenv import dotenv_values
    from npc.generation.config import load_provider
    values = {**dotenv_values(root / ".env", interpolate=False), **os.environ}
    profiles = []
    if current and current != "configs/providers/offline.yaml":
        profiles.append(current)
    profiles += ["configs/providers/gemini.yaml", "configs/providers/openrouter.yaml"]
    for name in dict.fromkeys(profiles):
        try:
            provider = load_provider(root / name, environ=values)
            from npc.generation.provider import OfflineProvider
            if not isinstance(provider, OfflineProvider):
                return name
        except ValueError:
            pass
    raise ValueError("Live dialogue is not configured. Fill NPC_LLM_MODEL and GEMINI_API_KEY (or OPENROUTER_API_KEY) in .env, then rerun. Keys stay local; setup makes no model API call.")


def install_mod(game, archive, version, port):
    with zipfile.ZipFile(archive) as package:
        for name, limit in [("AnimaConnector/build.json", 1024 * 1024),
                            ("SKSE/Plugins/AnimaConnector.dll", 64 * 1024 * 1024),
                            ("SKSE/Plugins/AnimaConnector.ini", 65536)]:
            if package.getinfo(name).file_size > limit:
                raise ValueError("Mod package exceeds expected size")
        manifest = json.loads(package.read("AnimaConnector/build.json"))
        dll = package.read("SKSE/Plugins/AnimaConnector.dll")
        template = package.read("SKSE/Plugins/AnimaConnector.ini").decode("utf-8-sig")
    if version not in manifest["target_runtimes"] or hashlib.sha256(dll).hexdigest() != manifest["dll_sha256"]:
        raise ValueError("Mod package runtime/hash verification failed")
    destination = game / "Data/SKSE/Plugins"
    destination.mkdir(parents=True, exist_ok=True)
    ini = destination / "AnimaConnector.ini"
    settings = configparser.ConfigParser()
    settings.read_string(ini.read_text(encoding="utf-8-sig") if ini.exists() else template)
    if not settings.has_section("Connection"):
        raise ValueError("Existing Anima INI is missing its Connection section")
    settings.set("Connection", "Port", str(port))
    for name, raw in [("AnimaConnector.dll", dll)]:
        path = destination / name
        if path.exists() and not path.with_suffix(path.suffix + ".anima-backup").exists():
            shutil.copy2(path, path.with_suffix(path.suffix + ".anima-backup"))
        temporary = path.with_suffix(".tmp"); temporary.write_bytes(raw); temporary.replace(path)
    output = io.StringIO(); settings.write(output)
    temporary = ini.with_suffix(".tmp"); temporary.write_text(output.getvalue(), encoding="utf-8"); temporary.replace(ini)


def setup(root, game, *, run=subprocess.run, version_reader=game_version):
    from scripts.setup_chatterbox import find_game, install_torch, configure_game
    game = (game or find_game(root))
    if game is None:
        raise ValueError('Skyrim was not found. Run setup_skyrim.bat --game-directory "D:\\Games\\Skyrim Special Edition"')
    game = game.resolve()
    version = check_game(game, version_reader)
    archive = root / "mod/AnimaConnector.zip"
    if not archive.is_file():
        archive = root / "output/skyrim-mod/AnimaConnector.zip"
    if not archive.is_file():
        raise ValueError("Compiled AnimaConnector.zip is missing; use the complete release bundle")
    interpreter = root / ".venv/Scripts/python.exe"
    if sys.platform != "win32":
        interpreter = root / ".venv/bin/python"
    def command(args):
        if run([str(arg) for arg in args], cwd=root, check=False).returncode:
            raise ValueError("Setup step failed; resolve the error above and rerun (downloads are cached)")
    install_torch(interpreter, command, probe=lambda args, **kw: run(args, cwd=root, **kw))
    command([interpreter, "-m", "pip", "install", "-r", root / "requirements.txt"])
    command([interpreter, "-m", "pip", "install", "-e", ".", "--no-deps", "--no-build-isolation"])
    command([interpreter, "-m", "pip", "check"])
    if not (root / ".env").exists():
        shutil.copyfile(root / ".env.example", root / ".env")
    configure_game(root, game)
    config = root / "configs/skyrim/connector.json"
    raw = json.loads(config.read_text(encoding="utf-8"))
    raw["provider_profile"] = choose_provider(root, raw.get("provider_profile"))
    ollama = shutil.which("ollama")
    if not ollama:
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe"
        ollama = str(candidate) if candidate.is_file() else None
    if not ollama:
        raise ValueError("Install/start Ollama first (see INSTALL_SKYRIM.md), then rerun setup")
    command([ollama, "pull", "qwen2.5vl:3b"])
    command([interpreter, "-m", "npc.adapters.skyrim.whisper", "--prepare"])
    command([interpreter, "-m", "npc.output.chatterbox", "--prepare"])
    from scripts.chatterbox_voices import prepare_voices
    count = prepare_voices(root, game)
    if not count:
        raise ValueError("No usable English Skyrim voice references found")
    raw.update(cv_url=raw.get("cv_url") or "http://127.0.0.1:8000", attach_visual_reference=True,
               pipeline_mode="preview")
    if raw.get("rag_config"):
        command([interpreter, "-m", "npc.rag", "--root", root, "prepare"])
    command([interpreter, "-m", "pytest", "-q"])
    install_mod(game, archive, version, raw.get("port", 8768))
    temporary = config.with_suffix(".tmp"); temporary.write_text(json.dumps(raw, indent=2), encoding="utf-8"); temporary.replace(config)
    marker = root / "data/tts/.chatterbox-ready.json"
    marker.write_text(json.dumps({"model": "chatterbox-turbo", "voices": count}))
    print("Installed Anima DLL/INI. Start run_cv.bat, then run_skyrim_connector.bat, then Skyrim through SKSE.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-directory", type=Path)
    args = parser.parse_args()
    try:
        if sys.version_info[:2] != (3, 11):
            raise ValueError("Use Python 3.11")
        interpreter = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if not interpreter.is_file():
            subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], check=True)
        if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
            return subprocess.run([str(interpreter), str(Path(__file__).resolve()), *sys.argv[1:]], cwd=ROOT).returncode
        sys.path.insert(0, str(ROOT))
        setup(ROOT, args.game_directory)
        return 0
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        print(f"Skyrim setup stopped: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
