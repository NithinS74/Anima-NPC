import io
import json
from pathlib import Path
import struct
from types import SimpleNamespace
import wave

import pytest

from scripts import chatterbox_voices as voices
from scripts import setup_chatterbox as setup


def plugin(path):
    body = b"EDID" + struct.pack("<H", 10) + b"MaleKhaji\0"
    record = struct.pack("<4sIII8s", b"VTYP", len(body), 0, 0x13AE6, b"\0" * 8) + body
    path.write_bytes(struct.pack("<4sI4sIII", b"GRUP", 24 + len(record), b"VTYP", 0, 0, 0) + record)


def clip():
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000)
        wav.writeframes(b"\1\0" * 24000 * 9)
    return out.getvalue()


def test_voice_type_mapping_and_fuz_decode(tmp_path):
    source = tmp_path / "Skyrim.esm"; plugin(source)
    assert voices.voice_types(source) == {"skyrim.esm:00013ae6": "malekhaji"}
    raw = b"FUZE" + struct.pack("<II", 1, 3) + b"lip" + clip()
    assert voices.decode_clip(raw) == b"\1\0" * 24000 * 9
    with pytest.raises(ValueError): voices.decode_clip(b"FUZE")


def test_automatic_import_preserves_existing_references(tmp_path, monkeypatch):
    game = tmp_path / "game"; data = game / "Data"; data.mkdir(parents=True)
    plugin(data / "Skyrim.esm"); (data / "Skyrim - Voices_en0.bsa").touch()
    class Archive:
        def __init__(self, path): self.path, self.entries = path, {"sound/voice/skyrim.esm/malekhaji/line.fuz": None}
        def read(self, name): return b"FUZE" + struct.pack("<II", 1, 0) + clip()
    monkeypatch.setattr(voices, "BsaArchive", Archive)
    assert voices.prepare_voices(tmp_path, game) == 1
    path = tmp_path / "data/tts/voices/manifest.json"
    manifest = json.loads(path.read_text()); before = manifest["voices"]["skyrim.esm:00013ae6"]
    manifest["npcs"]["npc-override"] = before; path.write_text(json.dumps(manifest))
    assert voices.prepare_voices(tmp_path, game) == 1
    restored = json.loads(path.read_text())
    assert restored["voices"]["skyrim.esm:00013ae6"] == before
    assert restored["npcs"]["npc-override"] == before
    assert (path.parent / before["file"]).is_file()


def test_truncated_plugin_rejected(tmp_path):
    path = tmp_path / "Skyrim.esm"; path.write_bytes(b"GRUP")
    with pytest.raises(ValueError): voices.voice_types(path)


def test_setup_commands_and_success_marker(tmp_path, monkeypatch):
    interpreter = tmp_path / ".venv" / ("Scripts/python.exe" if setup.sys.platform == "win32" else "bin/python")
    interpreter.parent.mkdir(parents=True); interpreter.touch()
    game = tmp_path / "game"
    calls = []
    def prepare(root, source):
        assert root == tmp_path and source == game
        (root / "data/tts").mkdir(parents=True)
        return 3
    monkeypatch.setattr(voices, "prepare_voices", prepare)
    setup.setup(tmp_path, game=game, run=lambda args, **kwargs: calls.append(args) or SimpleNamespace(returncode=0))
    assert all(call[0] == str(interpreter) for call in calls)
    assert calls[-2][-3:] == ["-m", "npc.output.chatterbox", "--prepare"]
    assert calls[-1][-3:] == ["-m", "pytest", "-q"]
    assert json.loads((tmp_path / "data/tts/.chatterbox-ready.json").read_text())["voices"] == 3


def test_failed_setup_does_not_enable_tts(tmp_path):
    interpreter = tmp_path / ".venv" / ("Scripts/python.exe" if setup.sys.platform == "win32" else "bin/python")
    interpreter.parent.mkdir(parents=True); interpreter.touch()
    with pytest.raises(ValueError, match="failed"):
        setup.setup(tmp_path, run=lambda *a, **kw: SimpleNamespace(returncode=1))
    assert not (tmp_path / "data/tts/.chatterbox-ready.json").exists()


def test_game_discovery_uses_existing_config(tmp_path):
    game = tmp_path / "game"; (game / "Data").mkdir(parents=True); (game / "Data/Skyrim.esm").touch()
    config = tmp_path / "configs/skyrim/connector.json"; config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"game_directory": "game"}))
    assert setup.find_game(tmp_path) == game


@pytest.mark.parametrize("contents", [[], {"voices": []}, {"voices": {}, "npcs": []}])
def test_invalid_reference_manifest_is_preserved(tmp_path, contents):
    target = tmp_path / "data/tts/voices/manifest.json"; target.parent.mkdir(parents=True)
    target.write_text(json.dumps(contents))
    with pytest.raises(ValueError, match="invalid"):
        voices.prepare_voices(tmp_path, tmp_path / "game")
    assert json.loads(target.read_text()) == contents
