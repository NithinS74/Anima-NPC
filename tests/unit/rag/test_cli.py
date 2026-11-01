from npc.rag import __main__ as cli
from npc.rag import backend


def test_prepare_uses_local_service_warmup_and_sync_without_model_provider(monkeypatch, tmp_path, capsys):
    calls = []
    class Report:
        errors = {}
        def model_dump_json(self, **kwargs): return '{"indexed":1}'
    class Service:
        def __init__(self, settings):
            assert settings.root == tmp_path
        def warmup(self): calls.append("warmup")
        def sync(self): calls.append("sync"); return Report()
    monkeypatch.setattr(backend, "RAGService", Service)
    assert cli.main(["--root", str(tmp_path), "prepare"]) == 0
    assert calls == ["warmup", "sync"]
    assert '"indexed":1' in capsys.readouterr().out


def test_prepare_reports_failure_without_deleting_existing_inputs(monkeypatch, tmp_path):
    original = tmp_path / "world.txt"
    original.write_text("Keep this document")
    class Service:
        def __init__(self, settings): pass
        def warmup(self): raise OSError("model unavailable")
    monkeypatch.setattr(backend, "RAGService", Service)
    assert cli.main(["--root", str(tmp_path), "prepare"]) == 1
    assert original.read_text() == "Keep this document"
