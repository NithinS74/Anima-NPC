"""Conservative excerpts from a tab-separated, unattributed dialogue export.

This is not a lore extractor or quest evaluator. Personal/conditional dialogue is
omitted because this format does not establish its speaker or runtime eligibility.
"""

import re

from npc.contracts.knowledge import Evidence

_PERSONAL = re.compile(r"\b(?:i|me|my|mine|myself|we|us|our|ours|ourselves|you|your|yours|yourself)\b", re.I)
_STATE = re.compile(r"\b(?:dead|died|dies|killed|slain|missing|married|rescued|returned|destroyed|captured|"
                    r"abducted|kidnapped|escaped|arrested|freed|now|today|yesterday|tomorrow|recently|currently|since)\b", re.I)
_RECORD = re.compile(r"FormID:\s*([0-9a-f]{8})", re.I)


def dialogue_reference(hit: Evidence) -> Evidence | None:
    excerpts, record_ids = [], []
    for line in hit.text.splitlines():
        fields = line.split("\t")
        # Export chunks strip trailing whitespace. Without a following delimiter,
        # retain only text ending as a complete sentence, never an open fragment.
        if len(fields) < 7:
            continue
        record = _RECORD.fullmatch(fields[0].strip())
        if record is None or not fields[5].strip().isdigit():
            continue
        text = fields[6].strip()
        if len(fields) == 7 and not re.search(r"[.!][\"”’]?\s*$", text):
            continue
        if not text or "?" in text or _PERSONAL.search(text) or _STATE.search(text):
            continue
        excerpts.append(text)
        record_ids.append(record.group(1) + ":" + fields[5].strip())
        if len(excerpts) == 64:
            break
    if not excerpts:
        return None
    return hit.model_copy(update={"text": "\n".join(excerpts), "source_kind": "dialogue", "record_ids": tuple(record_ids)})
