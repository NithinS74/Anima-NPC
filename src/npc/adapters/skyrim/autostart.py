"""Start the Anima bridge when Skyrim starts and stop it when Skyrim exits.

The watcher changes no game files and makes no model calls. Model requests only happen later, when
a player speaks to an NPC. Settings live in configs/skyrim/autostart.json.

    python -m npc.adapters.skyrim.autostart            Run the watcher
    python -m npc.adapters.skyrim.autostart --install  Also run it at Windows sign-in
    python -m npc.adapters.skyrim.autostart --uninstall
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[4]
STARTUP_NAME = "AnimaSkyrimAutostart.cmd"
LOCK_PORT = 8769
MAX_RESTARTS = 3
DEFAULTS = {
    "game_process": "SkyrimSE.exe",
    "provider_profile": "configs/providers/gemini.yaml",
    "local_speech": True,
    "log_file": "output/skyrim/anima-console.log",
    "health_url": "http://127.0.0.1:8768/v1/health",
    "poll_seconds": 5,
    # Wait this long after the game appears: the plugin's LaunchConsole may start the bridge first.
    "start_delay_seconds": 15,
}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def load_settings(path: Path) -> dict:
    """Read settings, rejecting unknown keys so that a typo cannot silently change behaviour."""
    settings = dict(DEFAULTS)
    if path.is_file():
        values = json.loads(path.read_text(encoding="utf-8"))
        unknown = set(values) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"unknown autostart settings: {sorted(unknown)}")
        settings.update(values)
    if settings["poll_seconds"] < 1:
        raise ValueError("poll_seconds must be at least 1")
    if settings["start_delay_seconds"] < 0:
        raise ValueError("start_delay_seconds must not be negative")
    return settings


def bridge_command(settings: dict, python: str = sys.executable) -> list[str]:
    command = [python, "-m", "npc.adapters.skyrim", "--provider-profile", settings["provider_profile"], "--log-file", settings["log_file"]]
    if settings["local_speech"]:
        command.append("--local-speech")
    return command


@dataclass(frozen=True)
class State:
    game_running: bool
    owned_alive: bool  # A bridge this watcher started is still running.
    bridge_healthy: bool  # Something answers on the bridge port, possibly started by hand.
    restarts: int


def decide(state: State) -> str:
    """Return 'start', 'stop' or 'wait'. Never takes over a bridge this watcher did not start."""
    if not state.game_running:
        return "stop" if state.owned_alive else "wait"
    if state.owned_alive or state.bridge_healthy or state.restarts >= MAX_RESTARTS:
        return "wait"
    return "start"


def game_running(process: str) -> bool:
    result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {process}", "/NH"], capture_output=True, text=True, creationflags=NO_WINDOW, check=False)
    return process.casefold() in result.stdout.casefold()


def bridge_healthy(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except (URLError, OSError):
        return False


def watch(settings: dict, *, root: Path = ROOT, ticks: int | None = None, is_game=game_running, is_healthy=bridge_healthy, spawn=subprocess.Popen, sleep=time.sleep, clock=time.monotonic) -> None:
    """Run the watcher loop. `ticks` and the injected functions let tests run it without a game."""
    process, restarts, was_running, seen_at = None, 0, False, 0.0
    count = 0
    while ticks is None or count < ticks:
        count += 1
        running = is_game(settings["game_process"])
        if running and not was_running:
            restarts, seen_at = 0, clock()  # A new game session gets a fresh restart allowance.
        was_running = running
        alive = process is not None and process.poll() is None
        action = decide(State(running, alive, False if alive else is_healthy(settings["health_url"]), restarts))
        if action == "start" and (clock() - seen_at < settings["start_delay_seconds"] or is_healthy(settings["health_url"])):
            action = "wait"  # too early, or a bridge came up since the check above (checked again right before spawning)
        if action == "start":
            process = spawn(bridge_command(settings), cwd=root, creationflags=NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            restarts += 1
        elif action == "stop":
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            process = None
        sleep(settings["poll_seconds"])


def startup_folder() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"


def install(folder: Path, root: Path = ROOT, python: Path | None = None) -> Path:
    """Add a launcher to the current user's Startup folder. Needs no admin rights."""
    python = python or root / ".venv/Scripts/pythonw.exe"
    if not python.is_file():
        raise FileNotFoundError(f"project interpreter not found: {python}")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / STARTUP_NAME
    target.write_text(f'@echo off\r\ncd /d "{root}"\r\nstart "" "{python}" -m npc.adapters.skyrim.autostart\r\n', encoding="utf-8")
    return target


def uninstall(folder: Path) -> bool:
    target = folder / STARTUP_NAME
    if target.is_file():
        target.unlink()
        return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/skyrim/autostart.json")
    args = parser.parse_args()
    if args.uninstall:
        print("Removed." if uninstall(startup_folder()) else "Nothing to remove.")
        return
    settings = load_settings(args.config)
    if args.install:
        print(f"Installed: {install(startup_folder())}")
    # Holding this port keeps a second watcher from starting.
    lock = socket.socket()
    try:
        lock.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        print("The watcher is already running.")
        return
    watch(settings)


if __name__ == "__main__":
    main()
