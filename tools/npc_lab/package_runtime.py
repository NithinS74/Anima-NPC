"""Explicitly package only approved runtime media for the private team repo."""

import hashlib
import json
import zipfile
from pathlib import Path

from tools.npc_lab.media import LabMedia
from tools.npc_lab.service import ROOT


def package_runtime():
    private = ROOT / "assets/private/npc_lab"; output = ROOT / "assets/runtime"; output.mkdir(exist_ok=True)
    media = LabMedia(); files = []
    for id in ("mira", "elin", "daren", "iona"):
        files.extend([private / "models" / (id + ".glb"), private / "scenes" / (id + ".jpg")])
        media.model_bytes(id); media.scene_bytes(id)
    files.extend([private / "fonts/FuturaCondensedLight.ttf", private / "fonts/FuturaCondensed.ttf"])
    media.font_bytes("dialogue"); media.font_bytes("interface")
    for relative in ("fonts/manifest.json", "scenes/manifest.json"):
        files.append(private / relative)
    files.extend(p for p in media.piper.iterdir() if p.is_file() and (p.name == "piper.exe" or p.suffix.lower() in {".dll", ".ort", ".md"}))
    files.extend(p for p in (media.piper / "espeak-ng-data").rglob("*") if p.is_file())
    for voice in set(media.settings.voices.values()):
        files.extend(media.piper / "models/skyrim/low" / (voice + suffix) for suffix in (".onnx", ".onnx.json"))
    if not (media.piper / "LICENSE.md").is_file(): raise ValueError("Piper licence is required")
    entries = {}; archive_path = output / "anima-media.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for path in sorted(set(files)):
            if not path.is_file() or not path.resolve().is_relative_to(private.resolve()): raise ValueError("missing/unsafe runtime asset")
            relative = path.relative_to(private).as_posix()
            with path.open("rb") as stream: checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            entries[relative] = dict(bytes=path.stat().st_size, sha256=checksum)
            archive.write(path, relative)
    with archive_path.open("rb") as stream: checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = dict(schema_version=1, intended_visibility="private", archive_sha256=checksum,
                    archive_bytes=archive_path.stat().st_size, files=entries,
                    provenance="User-authorized private educational runtime bundle; original rights/licences retained.")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Packaged {len(entries)} runtime files, {archive_path.stat().st_size / 1024 / 1024:.1f} MiB. Use Git LFS.")


if __name__ == "__main__": package_runtime()
