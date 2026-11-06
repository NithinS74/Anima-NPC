import json

import pytest

from npc.adapters.skyrim import autostart as a


def state(game=True, owned=False, healthy=False, restarts=0):
    return a.State(game, owned, healthy, restarts)


class FakeProcess:
    def __init__(self):
        self.alive, self.terminated = True, 0

    def poll(self):
        return None if self.alive else 1

    def terminate(self):
        self.alive, self.terminated = False, self.terminated + 1

    def wait(self, timeout):
        return 0

    def kill(self):
        self.alive = False


def run(game_states, *, healthy=False, die_after_start=False):
    games = iter(game_states)
    started = []

    def spawn(command, **kwargs):
        process = FakeProcess()
        process.alive = not die_after_start
        started.append((command, kwargs, process))
        return process

    settings = dict(a.DEFAULTS, poll_seconds=1, start_delay_seconds=0)
    a.watch(settings, ticks=len(game_states), is_game=lambda name: next(games), is_healthy=lambda url: healthy, spawn=spawn, sleep=lambda s: None)
    return started


def test_starts_when_game_appears_and_stops_when_it_exits():
    started = run([False, True, True, False, False])
    assert len(started) == 1
    assert started[0][2].terminated == 1


def test_does_nothing_while_game_is_closed():
    assert run([False, False, False]) == []


def test_never_starts_a_second_bridge_or_stops_one_started_by_hand():
    assert run([True, True, False], healthy=True) == []


def test_crashing_bridge_restarts_a_bounded_number_of_times():
    assert len(run([True] * 10, die_after_start=True)) == a.MAX_RESTARTS


def test_new_game_session_resets_the_restart_allowance():
    started = run([True] * 5 + [False] + [True] * 5, die_after_start=True)
    assert len(started) == a.MAX_RESTARTS * 2


@pytest.mark.parametrize("value,expected", [
    (state(game=False), "wait"), (state(game=False, owned=True), "stop"), (state(), "start"),
    (state(owned=True), "wait"), (state(healthy=True), "wait"), (state(restarts=a.MAX_RESTARTS), "wait"),
])
def test_decisions(value, expected):
    assert a.decide(value) == expected


def test_command_uses_the_configured_model_and_voice():
    command = a.bridge_command(dict(a.DEFAULTS), python="py")
    assert command[:3] == ["py", "-m", "npc.adapters.skyrim"]
    assert command[command.index("--provider-profile") + 1] == "configs/providers/gemini.yaml"
    assert "--local-speech" in command
    assert "--local-speech" not in a.bridge_command(dict(a.DEFAULTS, local_speech=False), python="py")


def test_settings_merge_defaults_and_reject_typos(tmp_path):
    path = tmp_path / "autostart.json"
    assert a.load_settings(path) == a.DEFAULTS
    path.write_text(json.dumps({"local_speech": False}), encoding="utf-8")
    assert a.load_settings(path)["local_speech"] is False
    path.write_text(json.dumps({"local_speach": False}), encoding="utf-8")
    with pytest.raises(ValueError, match="local_speach"):
        a.load_settings(path)
    path.write_text(json.dumps({"poll_seconds": 0}), encoding="utf-8")
    with pytest.raises(ValueError, match="poll_seconds"):
        a.load_settings(path)


def test_install_and_uninstall_touch_only_their_own_file(tmp_path):
    other = tmp_path / "other.cmd"
    other.write_text("keep", encoding="utf-8")
    python = tmp_path / "pythonw.exe"
    python.write_text("", encoding="utf-8")
    target = a.install(tmp_path, root=tmp_path, python=python)
    body = target.read_text(encoding="utf-8")
    assert "npc.adapters.skyrim.autostart" in body and str(python) in body
    assert a.uninstall(tmp_path) is True
    assert a.uninstall(tmp_path) is False
    assert other.read_text(encoding="utf-8") == "keep"


def test_install_refuses_a_missing_interpreter(tmp_path):
    with pytest.raises(FileNotFoundError):
        a.install(tmp_path, root=tmp_path, python=tmp_path / "missing.exe")
    assert not list(tmp_path.iterdir())


def watch_with_clock(times, ticks, healthy_checks=()):
    """Game visible on every tick. Clock calls: once when the game appears, then once per start decision."""
    clock, answers, started = iter(times), iter(healthy_checks), []
    def spawn(command, **kwargs):
        started.append(command)
        return FakeProcess()
    a.watch(dict(a.DEFAULTS, poll_seconds=1), ticks=ticks, is_game=lambda name: True, is_healthy=lambda url: next(answers, False),
            spawn=spawn, sleep=lambda s: None, clock=lambda: next(clock))
    return started


def test_start_waits_for_the_delay_after_the_game_appears():
    assert watch_with_clock([0, 5], ticks=1) == []  # 5 s after the game appeared: too early
    assert len(watch_with_clock([0, 5, 20], ticks=2)) == 1  # 20 s: past the 15 s delay


def test_no_bridge_is_spawned_when_one_answers_just_before_the_start():
    # the state check says unhealthy; the check right before spawning says healthy (the console bridge came up)
    assert watch_with_clock([0, 20], ticks=1, healthy_checks=[False, True]) == []
    assert len(watch_with_clock([0, 20], ticks=1, healthy_checks=[False, False])) == 1


def test_second_bridge_exits_before_loading_models_when_the_port_is_taken(tmp_path, monkeypatch, capsys):
    import socket
    import sys
    from npc.adapters.skyrim import __main__ as entry
    monkeypatch.undo()  # the conftest default hides the real probe
    with socket.socket() as holder:
        holder.bind(("127.0.0.1", 0))
        assert entry.port_taken(holder.getsockname()[1])
    config = tmp_path / "connector.json"
    config.write_text(json.dumps({"game_directory": str(tmp_path / "game"), "pipeline_mode": "inbox"}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["connector", "--config", str(config)])
    monkeypatch.setattr(entry, "port_taken", lambda port: True)  # overrides the conftest default
    monkeypatch.setattr("npc.adapters.skyrim.whisper.prepare_model", lambda root: pytest.fail("loaded a model"))
    monkeypatch.setattr("uvicorn.run", lambda *args, **kwargs: pytest.fail("started a server"))
    entry.main()
    assert "already running" in capsys.readouterr().out
