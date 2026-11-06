"""Operating-system audio output for NPC speech (Windows `winsound`; a logged no-op elsewhere)."""

from pathlib import Path

from .diagnostics import event as log_event

try:  # winsound exists on Windows only.
    import winsound
except ImportError:  # pragma: no cover - platform dependent
    winsound = None


class SystemAudio:
    """Non-blocking, non-positional playback of one WAV file at a time."""

    def play(self, path: Path):
        if winsound is None:
            log_event("AUDIO_OUTPUT_UNAVAILABLE", reason="winsound_missing")
            return
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)

    def stop(self):
        if winsound is not None:
            winsound.PlaySound(None, 0)
