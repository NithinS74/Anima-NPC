"""Bootstrap Anima using only the standard library and its project environment."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def launch(root, args, *, run=subprocess.run, python=sys.executable):
    interpreter = root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    def command(argv):
        return run([str(arg) for arg in argv], cwd=root, check=False).returncode
    ready = interpreter.is_file() and command([interpreter, root / "scripts/check_environment.py"]) == 0
    if not ready:
        print("Preparing Anima automatically; first setup needs internet and may take a few minutes.", flush=True)
        result = command([python, root / "scripts/setup_environment.py"])
        if result:
            return result
        if command([interpreter, root / "scripts/check_environment.py"]):
            print("Setup finished but readiness failed. See SETUP.md; no app started.")
            return 1
    print("Starting Anima. Configured API calls may incur charges; --offline uses scripted responses.", flush=True)
    return command([interpreter, "-m", "tools.npc_lab", "--auto", "--open", *args])


if __name__ == "__main__":
    try:
        raise SystemExit(launch(ROOT, sys.argv[1:]))
    except OSError:
        print("Could not start setup/application. Check Python 3.11 and SETUP.md.")
        raise SystemExit(1)
