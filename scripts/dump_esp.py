"""Minimal read-only Skyrim SE plugin (.esp/.esm/.esl) record dumper. Standard library only."""

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import struct
import zlib

COMPRESSED = 0x00040000


@dataclass
class Record:
    type: str
    flags: int
    form_id: int
    version: int
    size: int
    subrecords: list = field(default_factory=list)  # (type, bytes)

    def sub(self, name):
        return [data for kind, data in self.subrecords if kind == name]


@dataclass
class Group:
    label: bytes
    group_type: int
    size: int  # total size including the 24-byte header
    children: list = field(default_factory=list)

    def walk(self):
        for child in self.children:
            yield child
            if isinstance(child, Group):
                yield from child.walk()


def parse_subrecords(data):
    result, offset, extended = [], 0, None
    while offset < len(data):
        kind = data[offset:offset + 4].decode("ascii")
        (size,) = struct.unpack_from("<H", data, offset + 4)
        offset += 6
        if kind == "XXXX":
            (extended,) = struct.unpack_from("<I", data, offset)
            offset += size
            continue
        if extended is not None:
            size, extended = extended, None
        result.append((kind, data[offset:offset + size]))
        offset += size
    return result


def parse_block(data, offset, end):
    items = []
    while offset < end:
        kind = data[offset:offset + 4].decode("ascii")
        (size,) = struct.unpack_from("<I", data, offset + 4)
        if kind == "GRUP":
            label = data[offset + 8:offset + 12]
            (group_type,) = struct.unpack_from("<I", data, offset + 12)
            group = Group(label, group_type, size)
            group.children = parse_block(data, offset + 24, offset + size)
            items.append(group)
            offset += size
        else:
            flags, form_id, _vc, version = struct.unpack_from("<IIIH", data, offset + 8)
            body = data[offset + 24:offset + 24 + size]
            if flags & COMPRESSED:
                body = zlib.decompress(body[4:])
            items.append(Record(kind, flags, form_id, version, size, parse_subrecords(body)))
            offset += 24 + size
    if offset != end:
        raise ValueError("block size mismatch")
    return items


def parse_esp(data: bytes):
    """Return the list of top-level items: the TES4 Record followed by top-level Groups."""
    return parse_block(data, 0, len(data))


def cstring(data):
    return data.split(b"\0", 1)[0].decode("utf-8", "replace")


def describe(item, depth=0):
    pad = "  " * depth
    if isinstance(item, Group):
        yield f"{pad}GRUP label={item.label!r} type={item.group_type} size={item.size}"
        for child in item.children:
            yield from describe(child, depth + 1)
        return
    yield f"{pad}{item.type} id={item.form_id:08X} flags={item.flags:#x} ver={item.version} size={item.size}"
    for kind, data in item.subrecords:
        text = f" {cstring(data)!r}" if kind in {"EDID", "MAST", "CNAM", "SNAM", "NAM1"} and data[-1:] == b"\0" else ""
        yield f"{pad}  {kind}[{len(data)}] {data[:48].hex()}{text}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--types", nargs="*", help="only show top-level groups with these labels (and TES4)")
    args = parser.parse_args()
    for item in parse_esp(args.path.read_bytes()):
        if args.types and isinstance(item, Group) and item.label.decode("ascii") not in args.types:
            continue
        print("\n".join(describe(item)))


if __name__ == "__main__":
    main()
