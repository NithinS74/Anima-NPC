import struct

import lz4.frame
import pytest

from tools.npc_lab.skyrim_archive import BsaArchive, MAX_ASSET
from tools.npc_lab.import_skyrim import referenced_textures


def archive(path, *, name="model.nif", folder="meshes", flags=3, body=b"game asset", expected=None):
    raw = body
    if flags & 4:
        raw = struct.pack("<I", len(body) if expected is None else expected) + lz4.frame.compress(body)
    if flags & 0x100:
        embedded = (folder + "\\" + name).encode()
        raw = bytes([len(embedded)]) + embedded + raw
    folder_bytes = folder.encode() + b"\x00"
    names = name.encode() + b"\x00"
    offset = 36 + 24 + 1 + len(folder_bytes) + 16 + len(names)
    header = struct.pack("<4s8I", b"BSA\x00", 105, 36, flags, 1, 1, len(folder_bytes), len(names), 0)
    record = struct.pack("<QIIQ", 0, 1, 0, 60)
    data = header + record + bytes([len(folder_bytes)]) + folder_bytes + struct.pack("<QII", 0, len(raw), offset) + names + raw
    path.write_bytes(data)
    return BsaArchive(path)


@pytest.mark.parametrize("flags", [3,7,0x107])
def test_selective_sse_read_handles_raw_lz4_and_embedded_names(tmp_path, flags):
    data = archive(tmp_path / "test.bsa", flags=flags)
    assert data.read("meshes\\model.nif") == b"game asset"
    output = data.extract("meshes/model.nif", tmp_path / "out")
    assert output.read_bytes() == b"game asset"
    assert not (tmp_path / "out/textures").exists()


def test_archive_path_traversal_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="unsafe"):
        archive(tmp_path / "unsafe.bsa", folder="../outside")


def test_decompression_bomb_header_is_rejected_before_decode(tmp_path):
    data = archive(tmp_path / "huge.bsa", flags=7, expected=MAX_ASSET+1)
    with pytest.raises(ValueError, match="expanded"):
        data.read("meshes/model.nif")


def test_short_archive_and_out_of_range_file_are_rejected(tmp_path):
    path=tmp_path/"bad.bsa"; path.write_bytes(b"BSA")
    with pytest.raises(ValueError): BsaArchive(path)
    valid=archive(path); raw=path.read_bytes(); path.write_bytes(raw[:-1])
    with pytest.raises(ValueError, match="out-of-range"): BsaArchive(path)


def test_texture_reference_collection_is_normalized_and_bounded_to_paths():
    references = referenced_textures(b'\x00textures\\actors\\Face.DDS\x00noise\x00textures/clothes/apron.dds\x00')
    assert references == {"textures/actors/face.dds", "textures/clothes/apron.dds"}
    with pytest.raises(ValueError, match="unsafe"):
        referenced_textures(b'textures/../../escape.dds')
