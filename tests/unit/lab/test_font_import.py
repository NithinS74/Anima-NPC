import json
import struct
from pathlib import Path

import pytest

from tools.npc_lab import import_font


def test_installed_font_import_uses_fixed_source_and_private_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(import_font, "ROOT", tmp_path)
    config = tmp_path / "configs/npc_lab/media.json"; config.parent.mkdir(parents=True)
    config.write_text(json.dumps(dict(piper_directory="assets/private/npc_lab/piper", voices={}, models={})))
    selected = []
    class Archive:
        def __init__(self, path): assert path == tmp_path / "game/Data/Skyrim - Interface.bsa"
        def extract(self, name, root):
            selected.append(name)
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b"installed asset")
            return path
    monkeypatch.setattr(import_font, "BsaArchive", Archive)
    raw = b"\x00\x01\x00\x00" + struct.pack(">H", 1) + b"\x00" * 22
    commands = []
    def execute(args, **kwargs):
        commands.append(args)
        assert kwargs["check"] and kwargs["timeout"] == 60
        destination = Path(args[5]); destination.mkdir(parents=True)
        for name in ["5_Futura CondensedLight.ttf", "7_Futura Condensed.ttf"]:
            (destination / name).write_bytes(raw)
    monkeypatch.setattr(import_font.subprocess, "run", execute)
    import_font.import_fonts(tmp_path / "game", tmp_path / "ffdec.jar")
    assert selected == ["interface/fonts_en.swf", "interface/fontconfig.txt"]
    assert commands[0][:5] == ["java", "-jar", str((tmp_path / "ffdec.jar").resolve()), "-export", "font"]
    private = tmp_path / "assets/private/npc_lab/fonts"
    assert (private / "FuturaCondensedLight.ttf").read_bytes() == raw
    assert (private / "manifest.json").is_file()


def test_missing_expected_font_stops_import(tmp_path, monkeypatch):
    monkeypatch.setattr(import_font, "ROOT", tmp_path)
    class Archive:
        def __init__(self, path): pass
        def extract(self, name, root): return tmp_path / "font.swf"
    monkeypatch.setattr(import_font, "BsaArchive", Archive)
    monkeypatch.setattr(import_font.subprocess, "run", lambda *a, **k: None)
    with pytest.raises(ValueError, match="font not found"):
        import_font.import_fonts(tmp_path, tmp_path / "ffdec.jar")
