"""Offline import of bounded reference clips from an installed Skyrim SE game."""

import hashlib
import io
import json
from pathlib import Path
import struct
import wave
import zlib

from tools.npc_lab.skyrim_archive import BsaArchive


def voice_types(plugin):
    """Read only the top-level VTYP group, not quests or saved player data."""
    result = {}
    with plugin.open("rb") as stream:
        size = plugin.stat().st_size
        while stream.tell() < size:
            header = stream.read(24)
            if len(header) != 24:
                raise ValueError("truncated plugin header")
            tag, amount = struct.unpack_from("<4sI", header)
            if tag == b"GRUP":
                if amount < 24 or stream.tell() + amount - 24 > size:
                    raise ValueError("invalid plugin group")
                end = stream.tell() + amount - 24
                if header[8:12] == b"VTYP":
                    while stream.tell() < end:
                        record = stream.read(24)
                        if len(record) != 24:
                            raise ValueError("truncated voice record")
                        kind, length, flags, form = struct.unpack_from("<4sIII", record)
                        if length > 65536 or stream.tell() + length > end:
                            raise ValueError("voice record exceeds bounds")
                        raw = stream.read(length)
                        if kind != b"VTYP":
                            continue
                        if flags & 0x40000:
                            raw = zlib.decompressobj().decompress(raw[4:], 65537)
                            if len(raw) > 65536:
                                raise ValueError("expanded voice record exceeds bounds")
                        cursor = 0
                        while cursor + 6 <= len(raw):
                            field, count = struct.unpack_from("<4sH", raw, cursor); cursor += 6
                            if cursor + count > len(raw):
                                raise ValueError("truncated voice field")
                            if field == b"EDID":
                                name = raw[cursor:cursor + count].rstrip(b"\0").decode("utf-8").lower()
                                result[f"{plugin.name.lower()}:{form & 0xffffff:08x}"] = name
                            cursor += count
                stream.seek(end)
            else:
                if stream.tell() + amount > size:
                    raise ValueError("invalid plugin record")
                stream.seek(amount, 1)
    return result


def decode_clip(raw):
    import av
    if raw[:4] == b"FUZE":
        if len(raw) < 12 or struct.unpack_from("<I", raw, 4)[0] != 1:
            raise ValueError("invalid FUZ header")
        offset = 12 + struct.unpack_from("<I", raw, 8)[0]
        if offset >= len(raw):
            raise ValueError("truncated FUZ audio")
        raw = raw[offset:]
    chunks, frames = [], 0
    with av.open(io.BytesIO(raw)) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=24000)
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                chunks.append(converted.to_ndarray().tobytes())
                frames += converted.samples
                if frames > 24000 * 15:
                    return b"".join(chunks)[:24000 * 15 * 2]
        for converted in resampler.resample(None):
            chunks.append(converted.to_ndarray().tobytes())
    return b"".join(chunks)


def prepare_voices(root, game):
    import av
    from npc.output.chatterbox import TurboEngine, TurboRequest
    target = root / "data/tts/voices"
    target.mkdir(parents=True, exist_ok=True)
    manifest_file = target / "manifest.json"
    manifest = json.loads(manifest_file.read_text()) if manifest_file.exists() else {"voices": {}, "npcs": {}}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("voices"), dict):
        raise ValueError("invalid existing voice reference manifest")
    if not isinstance(manifest.setdefault("npcs", {}), dict):
        raise ValueError("invalid NPC reference overrides")
    data = game / "Data"
    plugins = [data / name for name in ("Skyrim.esm", "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm")]
    definitions = {key: name for plugin in plugins if plugin.is_file() for key, name in voice_types(plugin).items()}
    archives = [BsaArchive(path) for path in sorted(data.glob("*Voices*.bsa"))[:16]]
    candidates = {}
    for archive in archives:
        for name in sorted(archive.entries):
            parts = name.split("/")
            if len(parts) == 5 and parts[:2] == ["sound", "voice"] and name.endswith((".fuz", ".wav", ".xwm")):
                candidates.setdefault((parts[2], parts[3]), [])
                if len(candidates[(parts[2], parts[3])]) < 20:
                    candidates[(parts[2], parts[3])].append((archive, name))
    for key, editor_id in definitions.items():
        if key in manifest["voices"]:  # preserve explicit existing references/overrides
            try:
                TurboEngine(root, None).reference(TurboRequest(request_id="setup", text="check", voice_key=key))
                continue
            except (ValueError, OSError):
                if "sources" not in manifest["voices"][key]:
                    raise ValueError(f"Existing custom reference is invalid: {key}; repair it before setup") from None
        clips, sources = [], []
        for archive, name in candidates.get((key.split(":")[0], editor_id), []):
            try:
                raw = archive.read(name)
                pcm = decode_clip(raw)
                if len(pcm) < 24000:  # skip clips shorter than half a second
                    continue
                clips.append(pcm); sources.append({"archive": archive.path.name, "entry": name,
                    "sha256": hashlib.sha256(raw).hexdigest()})
                if sum(map(len, clips)) >= 24000 * 8 * 2:
                    break
            except (ValueError, OSError, av.FFmpegError):
                continue
        pcm = b"".join(clips)[:24000 * 10 * 2]
        if len(pcm) <= 24000 * 5 * 2:
            continue
        name = hashlib.sha256(key.encode()).hexdigest()[:24] + ".wav"
        out = io.BytesIO()
        with wave.open(out, "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(24000); wav.writeframes(pcm)
        raw = out.getvalue(); (target / name).write_bytes(raw)
        manifest["voices"][key] = {"file": name, "sha256": hashlib.sha256(raw).hexdigest(),
            "voice_type": editor_id, "sources": sources}
    serialized = json.dumps(manifest, indent=2)
    if len(serialized.encode("utf-8")) > 128 * 1024:
        raise ValueError("voice reference manifest exceeds 128 KiB")
    temporary = manifest_file.with_suffix(".tmp")
    temporary.write_text(serialized, encoding="utf-8"); temporary.replace(manifest_file)
    return len(manifest["voices"])
