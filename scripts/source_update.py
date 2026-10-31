"""Optional, bounded fast-forward update of the checked-out branch."""

import os
import subprocess


def update_source(root, *, run=subprocess.run):
    def git(*args):
        return run(["git", *args], cwd=root, capture_output=True, text=True,
                   timeout=45, check=False,
                   env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GCM_INTERACTIVE": "Never"})

    try:
        status = git("status", "--porcelain")
        if status.returncode or status.stdout.strip():
            print("Source update skipped: local changes or no Git checkout. Using local files.", flush=True)
            return
        branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
        if branch.returncode:
            print("Source update skipped: detached HEAD.", flush=True)
            return
        upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
        if upstream.returncode:
            print("Source update skipped: branch has no upstream. Configure its tracking branch to enable pulls.", flush=True)
            return
        result = git("pull", "--ff-only", "--no-rebase", "--no-autostash")
        if result.returncode:
            print("Source update unavailable (network/access/diverged branch). Keeping local checkout; no reset performed.", flush=True)
        else:
            print("Source branch is up to date (fast-forward only).", flush=True)
    except (OSError, subprocess.TimeoutExpired):
        print("Source update unavailable. Continuing with local checkout.", flush=True)
