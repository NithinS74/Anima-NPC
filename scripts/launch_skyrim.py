"""Launch Anima services + Skyrim via SKSE as a single managed process tree."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def find_skse_loader(game_dir: Path) -> Path | None:
    candidates = [
        game_dir / "skse64_loader.exe",
        game_dir / "SKSE64_Loader.exe",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def wait_health(url: str, timeout: float = 30.0) -> bool:
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode())
                    if data.get("status") == "ok":
                        return True
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            pass
        time.sleep(0.5)
    return False


def run_launcher(args):
    if sys.platform != "win32":
        raise ValueError("This launcher runs on Windows only")

    game_dir = Path(args.game_directory).resolve() if args.game_directory else None
    if not game_dir:
        from scripts.setup_chatterbox import find_game
        game_dir = find_game(ROOT)
    if not game_dir:
        raise ValueError("Skyrim not found. Pass --game-directory")

    skse = find_skse_loader(game_dir)
    if not skse:
        raise ValueError(f"skse64_loader.exe not found in {game_dir}")

    interpreter = ROOT / ".venv" / "Scripts" / "python.exe"
    if not interpreter.is_file():
        raise ValueError(".venv not found. Run setup_skyrim.bat first")

    # Ensure connector.json exists
    connector_cfg = ROOT / "configs/skyrim/connector.json"
    if not connector_cfg.is_file():
        import shutil
        shutil.copyfile(ROOT / "configs/skyrim/connector.example.json", connector_cfg)

    print(f"[Anima] Game: {game_dir}")
    print(f"[Anima] SKSE: {skse}")
    print(f"[Anima] Python: {interpreter}")

    cv_proc = None
    bridge_proc = None

    def cleanup():
        for name, proc in [("CV", cv_proc), ("Bridge", bridge_proc)]:
            if proc and proc.poll() is None:
                print(f"[Anima] Stopping {name}...")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    try:
        # 1. Start CV service
        print("[Anima] Starting CV service (port 8000)...")
        cv_proc = subprocess.Popen(
            [str(interpreter), "-m", "uvicorn", "app.main:app", "--app-dir", "cv/backend",
             "--host", "127.0.0.1", "--port", "8000", "--limit-concurrency", "4"],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        # 2. Start Bridge
        print("[Anima] Starting bridge (port 8768)...")
        bridge_proc = subprocess.Popen(
            [str(interpreter), "-m", "npc.adapters.skyrim"],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

        # 3. Wait for health
        print("[Anima] Waiting for services...")
        if not wait_health("http://127.0.0.1:8000/ready", timeout=60):
            raise RuntimeError("CV service failed to start (check Ollama + qwen2.5vl:3b)")
        print("[Anima] CV ready")

        if not wait_health("http://127.0.0.1:8768/v1/health", timeout=60):
            raise RuntimeError("Bridge failed to start")
        print("[Anima] Bridge ready")

        if not wait_health("http://127.0.0.1:8768/v1/speech/health", timeout=60):
            print("[Anima] Warning: speech worker not ready yet (may still be loading)")

        # 4. Launch Skyrim via SKSE
        print(f"[Anima] Launching Skyrim via {skse}...")
        skyrim_proc = subprocess.Popen([str(skse)], cwd=game_dir)
        print("[Anima] Skyrim running. Close the game to stop Anima services.")

        # 5. Wait for Skyrim to exit
        skyrim_proc.wait()
        print("[Anima] Skyrim exited.")

    except KeyboardInterrupt:
        print("\n[Anima] Interrupted.")
    except Exception as e:
        print(f"[Anima] Error: {e}")
        return 1
    finally:
        cleanup()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-directory", type=Path, help="Skyrim installation folder")
    args = parser.parse_args()
    try:
        return run_launcher(args)
    except (ValueError, OSError) as e:
        print(f"[Anima] Launch failed: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())