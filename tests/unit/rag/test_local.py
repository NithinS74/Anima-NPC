import asyncio
import threading
from types import SimpleNamespace

import pytest

from npc.context import build_situation
from npc.rag import HTTPRetriever, LocalRetriever, load_retriever
from npc.rag.config import RAGConfig


def config(situation, **changes):
    data = dict(bindings=[dict(game_id=situation.scope.game_id, world_id=situation.scope.world_id,
                              npc_ids=[situation.npc_id], source="world.txt")])
    data.update(changes)
    return RAGConfig.model_validate(data)


class Service:
    def __init__(self):
        self.calls = []
    def retrieve(self, query, **settings):
        self.calls.append((query, settings))
        return SimpleNamespace(model_dump=lambda: dict(query=query, matches=[dict(
            id="chunk-1", text="The healer works at the eastern gate.", source="world.txt", page=None,
            chunk_index=0, distance=0.1, truncated=False)]))


def test_local_calls_existing_backend_directly_with_source_prefilter(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    service = Service()
    result = asyncio.run(LocalRetriever(config(situation), service=service).retrieve(situation, timeout_s=1))
    assert result.status == "ok" and result.evidence[0].source == "world.txt"
    assert service.calls[0][1] == dict(source="world.txt", top_k=8, max_chars=6000)


def test_unbound_identity_is_denied_without_opening_backend(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    settings = config(situation).model_dump()
    settings["bindings"][0]["npc_ids"] = ["other-npc"]
    service = Service()
    result = asyncio.run(LocalRetriever(RAGConfig.model_validate(settings), service=service).retrieve(situation, timeout_s=1))
    assert result.status == "forbidden" and not service.calls


def test_missing_local_artifacts_report_unavailable_without_download_or_ingest(scenario, tmp_path):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    result = asyncio.run(LocalRetriever(config(situation), root=tmp_path).retrieve(situation, timeout_s=1))
    assert result.status == "unavailable"
    assert not list(tmp_path.iterdir())


def test_backend_failure_is_typed_without_resetting_data(scenario):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    class Fails:
        def retrieve(self, *args, **kwargs):
            raise OSError("index unavailable")
    result = asyncio.run(LocalRetriever(config(situation), service=Fails()).retrieve(situation, timeout_s=1))
    assert result.status == "unavailable"


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_or_cancellation_never_queues_another_cpu_query(scenario, cancel):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    async def run():
        started, release = threading.Event(), threading.Event()
        class Slow(Service):
            def retrieve(self, query, **settings):
                started.set()
                release.wait(timeout=2)
                return super().retrieve(query, **settings)
        service = Slow()
        adapter = LocalRetriever(config(situation), service=service)
        task = asyncio.create_task(adapter.retrieve(situation, timeout_s=0.05 if not cancel else 1))
        try:
            assert await asyncio.to_thread(started.wait, 1)
            if cancel:
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                assert (await task).status == "unavailable"
            # The caller has returned, but the real native worker still owns admission.
            assert (await adapter.retrieve(situation, timeout_s=0.1)).status == "unavailable"
            assert service.calls == []
        finally:
            release.set()
        for _ in range(100):
            await asyncio.sleep(0.005)
            recovered = await adapter.retrieve(situation, timeout_s=0.5)
            if recovered.status == "ok":
                break
        assert recovered.status == "ok" and len(service.calls) == 2
    asyncio.run(run())


def test_backend_selection_is_local_by_default_and_http_is_explicit(scenario, tmp_path):
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    path = tmp_path / "rag.json"
    path.write_text(config(situation).model_dump_json())
    assert isinstance(load_retriever(path), LocalRetriever)
    path.write_text(config(situation, backend="http").model_dump_json())
    assert isinstance(load_retriever(path), HTTPRetriever)
