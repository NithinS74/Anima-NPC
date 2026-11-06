import pytest


@pytest.fixture(autouse=True)
def bridge_port_free(monkeypatch):
    """A real bridge may be running on the dev machine; launcher tests must not depend on that port being free."""
    from npc.adapters.skyrim import __main__ as entry
    monkeypatch.setattr(entry, "port_taken", lambda port: False)
