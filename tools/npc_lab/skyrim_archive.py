"""Bounded, selective SSE BSA reading for the offline lab asset-import tool."""

import struct
from pathlib import Path, PurePosixPath

MAX_ASSET = 64 * 1024 * 1024


class BsaArchive:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries = {}
        self.size = self.path.stat().st_size
        with self.path.open("rb") as stream:
            header = stream.read(36)
            if len(header) != 36:
                raise ValueError("short BSA header")
            magic, version, offset, flags, folders, files, folder_names, file_names, _ = struct.unpack("<4s8I", header)
            if magic != b"BSA\x00" or version != 105 or offset != 36 or flags & 3 != 3:
                raise ValueError("only named Skyrim SE v105 BSA archives are supported")
            if folders > 10000 or files > 200000 or file_names > 64 * 1024 * 1024:
                raise ValueError("BSA index exceeds import bounds")
            self.flags = flags
            counts = []
            for _ in range(folders):
                record = stream.read(24)
                if len(record) != 24:
                    raise ValueError("short folder record")
                _, count, _, _ = struct.unpack("<QIIQ", record)
                counts.append(count)
            if sum(counts) != files:
                raise ValueError("inconsistent file count")
            records = []
            for count in counts:
                raw = stream.read(1)
                if not raw:
                    raise ValueError("short folder name")
                length = raw[0]
                folder = stream.read(length).rstrip(b"\x00").decode("utf-8")
                for _ in range(count):
                    record = stream.read(16)
                    if len(record) != 16:
                        raise ValueError("short file record")
                    _, size, data_offset = struct.unpack("<QII", record)
                    records.append((folder, size, data_offset))
            names = stream.read(file_names).split(b"\x00")
            if len(names) < files or not names[-1] == b"":
                raise ValueError("invalid filename table")
            for (folder, size, data_offset), raw_name in zip(records, names):
                name = self.normalize(folder + "/" + raw_name.decode("utf-8"))
                amount = size & 0x3FFFFFFF
                if name in self.entries or data_offset + amount > self.size:
                    raise ValueError("invalid duplicate/out-of-range BSA file")
                self.entries[name] = (size, data_offset)

    @staticmethod
    def normalize(name):
        name = name.replace("\\", "/").lower()
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or ":" in name:
            raise ValueError("unsafe archive path")
        return str(path)

    def read(self, name: str) -> bytes:
        name = self.normalize(name)
        size_flags, offset = self.entries[name]
        amount = size_flags & 0x3FFFFFFF
        if amount > MAX_ASSET:
            raise ValueError("compressed asset exceeds bound")
        with self.path.open("rb") as stream:
            stream.seek(offset)
            raw = stream.read(amount)
        if self.flags & 0x100:
            if not raw or raw[0] + 1 > len(raw):
                raise ValueError("invalid embedded filename")
            raw = raw[1 + raw[0]:]
        compressed = bool(self.flags & 4) != bool(size_flags & 0x40000000)
        if compressed:
            if len(raw) < 4:
                raise ValueError("short compression header")
            expected = struct.unpack("<I", raw[:4])[0]
            if expected > MAX_ASSET:
                raise ValueError("expanded asset exceeds bound")
            import lz4.frame
            import lz4.block
            if raw[4:8] == b"\x04\x22\x4d\x18":
                # Stream decompression caps expansion even if the frame lies.
                decoder = lz4.frame.LZ4FrameDecompressor()
                result = decoder.decompress(raw[4:], max_length=expected + 1)
            else:
                result = lz4.block.decompress(raw[4:], uncompressed_size=expected)
            if len(result) != expected:
                raise ValueError("decompressed size mismatch")
            return result
        return raw

    def extract(self, name: str, destination: Path):
        target = (destination / self.normalize(name)).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError("extraction escapes destination")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(self.read(name))
        return target
