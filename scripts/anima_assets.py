"""Verify/hydrate the private project's LFS runtime pack and install safely."""

import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath

MAX_TOTAL = 768 * 1024 * 1024
MAX_FILE = 128 * 1024 * 1024


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def destination_for(root, name):
    relative = PurePosixPath(name)
    if not name or "\\" in name or relative.is_absolute() or ":" in name or ".." in relative.parts:
        raise ValueError("unsafe runtime asset path")
    if relative.parts[0] not in {"models", "fonts", "scenes", "piper"}:
        raise ValueError("unexpected runtime asset category")
    path = (root / str(relative)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("runtime asset escapes destination")
    return path


def install_runtime(root, command, *, sync=False):
    root = Path(root).resolve()
    manifest_path = root / "assets/runtime/manifest.json"
    if not manifest_path.is_file(): return  # small/source-only development checkout
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive_path = root / "assets/runtime/anima-media.zip"
    pointer = not archive_path.is_file()
    if not pointer:
        with archive_path.open("rb") as stream: pointer = stream.read(100).startswith(b"version https://git-lfs.github.com/spec/v1")
    if pointer:
        command(["git", "lfs", "version"])
        command(["git", "lfs", "install", "--local"])
        command(["git", "lfs", "pull", "--include=assets/runtime/anima-media.zip"])
    if archive_path.is_file() and archive_path.stat().st_size > MAX_TOTAL:
        raise ValueError("runtime archive size limit")
    if not archive_path.is_file() or digest(archive_path) != manifest["archive_sha256"]:
        raise ValueError("Runtime pack missing/corrupt. Install Git LFS and run git lfs pull, then rerun setup.")
    destination = root / "assets/private/npc_lab"
    if not destination.resolve().is_relative_to(root): raise ValueError("runtime destination escapes checkout")
    destination.mkdir(parents=True, exist_ok=True)
    state_path = destination / ".installed-runtime.json"
    previous = json.loads(state_path.read_text()) if state_path.is_file() else {}
    installed = {}; preserved = 0
    entries = manifest["files"]
    if not 1 <= len(entries) <= 5000: raise ValueError("runtime file count limit")
    with zipfile.ZipFile(archive_path) as archive:
        items = archive.infolist()
        if len(items) != len(entries) or len({item.filename for item in items}) != len(items):
            raise ValueError("runtime archive entry mismatch")
        if sum(item.file_size for item in items) > MAX_TOTAL: raise ValueError("runtime total size limit")
        for item in items:
            target = destination_for(destination, item.filename)
            if item.filename not in entries or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("unexpected runtime archive file")
            expected = entries[item.filename]
            if not 0 <= item.file_size <= MAX_FILE or item.file_size != expected["bytes"]:
                raise ValueError("runtime file size limit")
            current = digest(target) if target.is_file() else None
            if current == expected["sha256"]:
                installed[item.filename] = current; continue
            if not sync and current is not None and current != previous.get(item.filename):
                preserved += 1; continue  # retain explicitly generated local overrides
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".anima-install")
            try:
                checksum = hashlib.sha256(); size = 0
                with archive.open(item) as source, temporary.open("wb") as output:
                    while chunk := source.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_FILE: raise ValueError("runtime extraction limit")
                        checksum.update(chunk); output.write(chunk)
                if size != expected["bytes"] or checksum.hexdigest() != expected["sha256"]:
                    raise ValueError("runtime asset checksum mismatch")
                os.replace(temporary, target); installed[item.filename] = expected["sha256"]
            finally:
                temporary.unlink(missing_ok=True)
    temporary = state_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(installed), encoding="utf-8"); os.replace(temporary, state_path)
    print(f"Runtime media verified/installed ({len(installed)} files; {preserved} local overrides preserved).", flush=True)
