"""Repeatable project-only setup, runnable with the standard library alone."""

import shutil
import subprocess
import sys
from pathlib import Path


class SetupFailure(RuntimeError):
    pass


def setup(root: Path, *, python=sys.executable, version=None, run=subprocess.run):
    version = sys.version_info[:2] if version is None else version
    if tuple(version) != (3, 11):
        raise SetupFailure("Python 3.11 is required for the verified environment.")
    root = root.resolve()
    if not all((root / name).is_file() for name in ("requirements.txt", "pyproject.toml", ".env.example")):
        raise SetupFailure("Run from a complete Anima repository checkout.")

    def command(args):
        completed = run([str(arg) for arg in args], cwd=root, check=False)
        if completed.returncode:
            raise SetupFailure(f"A setup step failed (exit {completed.returncode}). Resolve the error above and rerun.")

    environment = root / ".venv"
    interpreter = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not environment.exists():
        print("Creating project .venv...", flush=True)
        command([python, "-m", "venv", environment])
    elif not interpreter.is_file():
        raise SetupFailure("Existing .venv is incomplete; move it aside manually before retrying. Nothing was deleted.")
    command([interpreter, "-c", "import sys; assert sys.version_info[:2] == (3, 11), 'Existing .venv must use Python 3.11'"])
    command([interpreter, "-m", "pip", "install", "-r", root / "requirements.txt"])
    command([interpreter, "-m", "pip", "install", "-e", ".", "--no-deps", "--no-build-isolation"])
    command([interpreter, "-m", "pip", "check"])
    template, destination = root / ".env.example", root / ".env"
    if not destination.exists():
        # Exclusive creation also prevents a second setup from overwriting keys.
        try:
            with destination.open("xb") as target, template.open("rb") as source:
                shutil.copyfileobj(source, target)
        except FileExistsError:
            pass
    command([interpreter, "-m", "pytest", "-q"])
    print("\nAnima setup complete. Try: run_anima.bat --offline", flush=True)
    print("For live calls, set the model and matching API key in your local .env, then run run_anima.bat.")
    print("Optional Skyrim models, fonts and Mantella voices are private local assets; see SETUP.md.")


def main():
    if len(sys.argv) != 1:
        print("Usage: setup.bat (no arguments)")
        return 2
    try:
        setup(Path(__file__).resolve().parents[1])
        return 0
    except (SetupFailure, OSError) as error:
        print(f"Setup error: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
