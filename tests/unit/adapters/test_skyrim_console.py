import logging
import os
import sys
import time

import pytest

from npc.adapters.skyrim import console
from npc.adapters.skyrim.console import LogTail, colour_line


def test_colours_are_distinct_and_errors_are_red():
    plugin = colour_line("[2026] [AnimaConnector] [info] loaded", "PLUGIN")
    bridge = colour_line("10:00:00 [ANIMA] STARTUP port=8768", "ANIMA")
    assert plugin.startswith(console.CYAN + "[PLUGIN] ") and plugin.endswith(console.RESET)
    assert bridge.startswith(console.GREEN) and "[PLUGIN]" not in bridge
    assert colour_line("[x] [error] boom", "PLUGIN").startswith(console.RED + "[PLUGIN] ")
    assert colour_line("[ANIMA] DELIVERY_FAILED id=1", "ANIMA").startswith(console.RED)
    assert colour_line("Traceback (most recent call last):", "ANIMA").startswith(console.RED)
    assert colour_line("[x] [warning] slow", "PLUGIN").startswith(console.YELLOW)
    assert colour_line("plain\r\n", "ANIMA").endswith("plain" + console.RESET)


def test_tail_missing_file_then_appears(tmp_path):
    tail = LogTail(tmp_path / "log.txt")
    assert tail.read_new() == []
    (tmp_path / "log.txt").write_bytes(b"one\ntwo\n")
    assert tail.read_new() == ["one", "two"]
    assert tail.read_new() == []


def test_tail_returns_only_new_lines_and_waits_for_newline(tmp_path):
    path = tmp_path / "log.txt"
    path.write_bytes(b"a\npar")
    tail = LogTail(path)
    assert tail.read_new() == ["a"]
    with open(path, "ab") as handle:
        handle.write(b"tial\nb\r\n")
    assert tail.read_new() == ["partial", "b"]


def test_tail_restarts_after_truncation_and_replacement(tmp_path):
    path = tmp_path / "log.txt"
    path.write_bytes(b"old line one\nold line two\n")
    tail = LogTail(path)
    assert len(tail.read_new()) == 2
    path.write_bytes(b"new\n")  # truncated by a new game session
    assert tail.read_new() == ["new"]
    path.unlink()
    assert tail.read_new() == []
    path.write_bytes(b"after rotation\n")
    assert tail.read_new() == ["after rotation"]


def test_tail_detects_replacement_by_larger_file(tmp_path):
    path = tmp_path / "log.txt"
    path.write_bytes(b"x\n")
    tail = LogTail(path)
    tail.read_new()
    other = tmp_path / "other.txt"
    other.write_bytes(b"much longer replacement\nsecond\n")
    os.replace(other, path)
    assert tail.read_new() == ["much longer replacement", "second"]


def test_tail_tolerates_invalid_utf8(tmp_path):
    path = tmp_path / "log.txt"
    path.write_bytes(b"bad \xff byte\n")
    assert LogTail(path).read_new() == ["bad \ufffd byte"]


def test_start_tail_emits_prefixed_lines_and_none_path_is_noop(tmp_path):
    assert console.start_tail(None) is None
    path = tmp_path / "log.txt"
    path.write_bytes(b"[t] [AnimaConnector] [info] hello\n")
    seen = []
    thread = console.start_tail(path, emit=seen.append, interval=0.01)
    assert thread.daemon
    deadline = time.time() + 3
    while not seen and time.time() < deadline:
        time.sleep(0.02)
    assert seen and "[PLUGIN] [t] [AnimaConnector] [info] hello" in seen[0]


@pytest.mark.skipif(os.name != "nt", reason="Windows known-folder API")
def test_documents_folder_comes_from_known_folder_api():
    documents = console.documents_folder()
    assert documents is not None and documents.is_dir()
    assert console.plugin_log_path().name == "AnimaConnector.log"


def test_colour_formatter_formats_bridge_records():
    record = logging.LogRecord("x", logging.INFO, "f", 1, "STARTUP a=1", None, None)
    text = console.ColourFormatter("%(message)s").format(record)
    assert text == console.GREEN + "STARTUP a=1" + console.RESET


def test_turn_traffic_kinds_have_their_own_colours():
    kinds = ["PLAYER_INPUT", "PIPELINE_RESULT", "OUTPUT_STAGED", "TURN_TIMING", "AUDIO_OUTPUT", "NATIVE_ACK"]
    colours = {colour_line(f"10:00:00 [ANIMA] {kind} text=\"x\"", "ANIMA").split("1", 1)[0] for kind in kinds}
    assert all(colour_line(f"10:00:00 [ANIMA] {kind} a=1", "ANIMA").startswith(console.TRAFFIC[kind]) for kind in kinds)
    assert len(set(console.TRAFFIC[kind] for kind in kinds)) >= 5
    assert colour_line("10:00:00 [ANIMA] TURN_FAILED x=1", "ANIMA").startswith(console.RED)
    assert colour_line("10:00:00 [ANIMA] STARTUP port=1", "ANIMA").startswith(console.GREEN)
