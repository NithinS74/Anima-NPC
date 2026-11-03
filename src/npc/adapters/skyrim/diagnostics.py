"""Bounded, attributable Skyrim diagnostics; staging is distinct from delivery."""

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

LOGGER = logging.getLogger("npc.adapters.skyrim")


def event(kind: str, **fields):
    # JSON escapes newlines/ESC and keeps untrusted text on one terminal line.
    values = " ".join(f"{key}={json.dumps(str(value)[:1024], ensure_ascii=True)}" for key, value in fields.items())
    LOGGER.info("%s %s", kind, values)


def shutdown():
    for handler in tuple(LOGGER.handlers):
        if getattr(handler, "_anima_owned", False):
            LOGGER.removeHandler(handler)
            handler.close()


def configure(log_file: str | None = None):
    shutdown()
    formatter = logging.Formatter("%(asctime)s [ANIMA] %(message)s", datefmt="%H:%M:%S")
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(path, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8"))
    for handler in handlers:
        handler._anima_owned = True
        handler.setFormatter(formatter)
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
