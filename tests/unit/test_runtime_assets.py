import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from scripts.anima_assets import destination_for, install_runtime


def bundle(root, content, *, filename="models/mira.glb"):
    folder = root / "assets/runtime"; folder.mkdir(parents=True, exist_ok=True)
    path = folder / "anima-media.zip"
    with zipfile.ZipFile(path, "w") as archive: archive.writestr(filename, content)
    manifest = dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    files={filename:dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest())})
    (folder / "manifest.json").write_text(json.dumps(manifest))
    return path


def test_install_is_verified_idempotent_and_updates_only_managed_files(tmp_path):
    bundle(tmp_path, b"first model")
    def forbidden(*a): raise AssertionError("hydrated pack needs no network")
    install_runtime(tmp_path, forbidden)
    target = tmp_path / "assets/private/npc_lab/models/mira.glb"
    assert target.read_bytes() == b"first model"
    install_runtime(tmp_path, forbidden)
    bundle(tmp_path, b"updated model"); install_runtime(tmp_path, forbidden)
    assert target.read_bytes() == b"updated model"
    target.write_bytes(b"my generated local override")
    bundle(tmp_path, b"another team update"); install_runtime(tmp_path, forbidden)
    assert target.read_bytes() == b"my generated local override"
    (tmp_path / ".env").write_text("keep local credentials")
    install_runtime(tmp_path, forbidden, sync=True)
    assert target.read_bytes() == b"another team update"
    assert (tmp_path / ".env").read_text() == "keep local credentials"


def test_lfs_pointer_is_hydrated_before_extraction(tmp_path):
    path = bundle(tmp_path, b"model"); actual = path.read_bytes()
    path.write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:placeholder\n")
    commands = []
    def command(args):
        commands.append(args)
        if args[:3] == ["git", "lfs", "pull"]: path.write_bytes(actual)
    install_runtime(tmp_path, command)
    assert commands == [["git","lfs","version"],["git","lfs","pull","--include=assets/runtime/anima-media.zip"]]


@pytest.mark.parametrize("name", ["../.env", "/outside", "fonts/../../.env", "piper\\..\\.env", "C:/outside", ".env"])
def test_archive_paths_cannot_escape_or_write_configuration(tmp_path, name):
    with pytest.raises(ValueError): destination_for(tmp_path, name)


def test_corrupt_pack_fails_before_any_extraction(tmp_path):
    path = bundle(tmp_path, b"model"); path.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="missing/corrupt"):
        install_runtime(tmp_path, lambda a: None)
    assert not (tmp_path / "assets/private").exists()


def test_unexpected_member_path_is_rejected(tmp_path):
    bundle(tmp_path, b"do not overwrite keys", filename="../.env")
    with pytest.raises(ValueError): install_runtime(tmp_path, lambda a: None)
    assert not (tmp_path / ".env").exists()


def test_file_size_cap_is_checked_before_writing(tmp_path, monkeypatch):
    import scripts.anima_assets as module
    bundle(tmp_path, b"too large for the test limit")
    monkeypatch.setattr(module, "MAX_FILE", 2)
    with pytest.raises(ValueError, match="size limit"):
        install_runtime(tmp_path, lambda a: None)
    assert not (tmp_path / "assets/private/npc_lab/models/mira.glb").exists()


def test_wrong_per_file_checksum_cannot_commit_a_partial_asset(tmp_path):
    bundle(tmp_path, b"model")
    path = tmp_path / "assets/runtime/manifest.json"; manifest = json.loads(path.read_text())
    manifest["files"]["models/mira.glb"]["sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="checksum mismatch"):
        install_runtime(tmp_path, lambda a: None)
    assert not (tmp_path / "assets/private/npc_lab/models/mira.glb").exists()
    assert not list((tmp_path / "assets/private/npc_lab").rglob("*.anima-install"))
