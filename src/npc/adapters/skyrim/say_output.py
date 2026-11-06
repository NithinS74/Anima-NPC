"""`audio_output: "say"`: voice and lip files the engine plays when an actor says an Anima.esp topic (Mantella's route).

Layout (the engine looks files up by this exact name):
    Data/Sound/Voice/Anima.esp/<VoiceTypeEditorID>/<Quest10>_<Topic15>_<InfoFormID8hex>_1.wav (+ .lip)
Two topics are used alternately because the engine caches a voice file by path.
"""

from pathlib import Path
import re
import subprocess
import tempfile

from .assets import atomic_write, wav_duration
from .diagnostics import event as log_event

PLUGIN = "Anima.esp"
QUEST_PREFIX = "AnimaDialo"        # first 10 characters of the quest editor ID "AnimaDialogue"
TOPIC_PREFIX = "AnimaSpeechLine"   # first 15 characters of the topic editor IDs "AnimaSpeechLine1" / "...2"
INFO_FORM_IDS = {1: 0x805, 2: 0x807}  # local form IDs of the two unconditional INFO records in Anima.esp
VOICE_DIRECTORY = re.compile(r"^[A-Za-z0-9_]{1,64}$")
FACEFX_TIMEOUT_S = 15


def next_topic(last: int) -> int:
    """Mantella's alternation: after 0 or 2 comes 1, after 1 comes 2."""
    return 1 if last in (0, 2) else 2


def voice_stem(topic_index: int) -> str:
    return f"{QUEST_PREFIX}_{TOPIC_PREFIX}_{INFO_FORM_IDS[topic_index]:08X}_1"


def voice_folder(game_directory: Path, voice_type: str) -> Path:
    if not VOICE_DIRECTORY.match(voice_type or ""):
        raise ValueError("invalid voice type folder")
    return game_directory / "Data" / "Sound" / "Voice" / PLUGIN / voice_type


def make_lip(facefx_directory: str, wav: Path, text: str, lip: Path) -> bool:
    """Run FaceFXWrapper (no shell). Needs FaceFXWrapper.exe and FonixData.cdf in the folder; False means no lip file."""
    if not facefx_directory:
        return False
    folder = Path(facefx_directory)
    tool, data = folder / "FaceFXWrapper.exe", folder / "FonixData.cdf"
    if not tool.is_file() or not data.is_file():
        log_event("LIP_UNAVAILABLE", reason="facefx_files_missing", folder=str(folder))
        return False
    clean = " ".join("".join(c if c.isprintable() and c != '"' else " " for c in text).split())
    try:
        with tempfile.TemporaryDirectory() as work:
            subprocess.run([str(tool), "Skyrim", "USEnglish", str(data), str(wav), str(Path(work) / "resampled.wav"),
                            str(lip), clean], cwd=work, check=True, capture_output=True, timeout=FACEFX_TIMEOUT_S,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError) as error:
        log_event("LIP_FAILED", error=type(error).__name__)
        lip.unlink(missing_ok=True)
        return False
    if not lip.is_file() or lip.stat().st_size == 0:
        lip.unlink(missing_ok=True)
        return False
    return True


def stage_say(raw: bytes, game_directory: Path, voice_type: str, topic_index: int, text: str, facefx_directory: str = ""):
    """Write the WAV (and, when FaceFX is configured and works, the .lip). Returns (wav path, lip written, wav seconds)."""
    if topic_index not in INFO_FORM_IDS:
        raise ValueError("invalid topic index")
    seconds = wav_duration(raw)
    folder = voice_folder(game_directory, voice_type)
    wav, lip = folder / (voice_stem(topic_index) + ".wav"), folder / (voice_stem(topic_index) + ".lip")
    lip.unlink(missing_ok=True)  # never leave the previous line's lip data beside a new WAV
    atomic_write(wav, raw)
    return wav, make_lip(facefx_directory, wav, text, lip), seconds
