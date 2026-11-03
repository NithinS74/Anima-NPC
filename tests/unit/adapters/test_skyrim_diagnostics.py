"""Console attribution must not permit terminal injection or unbounded text."""
import logging

from npc.adapters.skyrim.diagnostics import LOGGER, configure, event


def test_console_label_escaping_and_bounded_rotating_file(tmp_path, capsys):
    original_handlers, original_level, original_propagate = list(LOGGER.handlers), LOGGER.level, LOGGER.propagate
    path = tmp_path / "logs" / "anima.log"
    try:
        configure(str(path))
        event("PLAYER_INPUT", text="HELLO\n[FAKE]\x1b[2J" + "x" * 4000)
        line = capsys.readouterr().out
        assert "[ANIMA] PLAYER_INPUT" in line
        assert len(line.splitlines()) == 1
        assert "\\n[FAKE]\\u001b[2J" in line
        assert len(line) < 1300
        assert path.read_text() == line
        file_handler = next(h for h in LOGGER.handlers if hasattr(h, "maxBytes"))
        assert file_handler.maxBytes == 1024 * 1024 and file_handler.backupCount == 2
        configure(str(path))
        event("READY", active=True)
        assert capsys.readouterr().out.count("[ANIMA] READY") == 1
        assert sum(getattr(h, "_anima_owned", False) for h in LOGGER.handlers) == 2
    finally:
        for handler in tuple(LOGGER.handlers):
            if handler not in original_handlers:
                LOGGER.removeHandler(handler); handler.close()
        LOGGER.setLevel(original_level); LOGGER.propagate = original_propagate
