"""Per-character voice table in Mantella's `skyrim_characters.csv` format (read only; never copied or modified).

Columns used: `name`, `voice_model`, `ref_id`, `base_id`. IDs are the 24-bit local form ID in hex. Rows without a
`voice_model` are ignored. The file starts with a UTF-8 BOM, so it is read with `utf-8-sig`. A missing or broken file
means an empty table.
"""

import csv
from pathlib import Path

# The table only describes vanilla characters, so IDs are matched only for forms owned by these plugins.
VANILLA_PLUGINS = {"skyrim.esm", "update.esm", "dawnguard.esm", "hearthfires.esm", "dragonborn.esm"}
MAX_BYTES = 16 * 1024 * 1024


def model_key(value: str) -> str:
    """`Male Even Toned` / `MaleEvenToned` -> `maleeventoned` (the Piper model file stem)."""
    return "".join(str(value).lower().split())


def _local(value) -> int | None:
    try:
        return int(str(value).strip(), 16) & 0xFFFFFF if str(value).strip() else None
    except ValueError:
        return None


class VoiceTable:
    def __init__(self, path: Path | str | None):
        self.path = Path(path) if path else None
        self._loaded = False
        self.by_ref: dict[int, str] = {}
        self.by_base: dict[int, str] = {}
        self._names: dict[str, set[str]] = {}

    def load(self):
        if self._loaded:
            return
        self._loaded = True
        try:
            if self.path is None or not self.path.is_file() or self.path.stat().st_size > MAX_BYTES:
                return
            with self.path.open("r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    model = model_key(row.get("voice_model") or "")
                    if not model:
                        continue
                    if (ref := _local(row.get("ref_id"))) is not None:
                        self.by_ref.setdefault(ref, model)
                    if (base := _local(row.get("base_id"))) is not None:
                        self.by_base.setdefault(base, model)
                    if name := " ".join((row.get("name") or "").split()).lower():
                        self._names.setdefault(name, set()).add(model)
        except (OSError, UnicodeError, csv.Error):
            self.by_ref, self.by_base, self._names = {}, {}, {}

    def lookup(self, *, ref: dict | None, base: dict | None, name: str = ""):
        """Return [(model, selected_by)] in order: reference ID, base ID, exact name (only when unambiguous)."""
        self.load()
        found = []

        def vanilla(form):
            return isinstance(form, dict) and str(form.get("plugin", "")).lower() in VANILLA_PLUGINS

        if vanilla(ref) and (key := _local(ref.get("local_id"))) in self.by_ref:
            found.append((self.by_ref[key], "voice_table:ref_id"))
        if vanilla(base) and (key := _local(base.get("local_id"))) in self.by_base:
            found.append((self.by_base[key], "voice_table:base_id"))
        models = self._names.get(" ".join(str(name).split()).lower(), set())
        if len(models) == 1:
            found.append((next(iter(models)), "voice_table:name"))
        return found
