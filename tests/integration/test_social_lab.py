import asyncio
import threading

import httpx
import pytest

from npc.contracts.dialogue import ProviderReply
from npc.generation.provider import OfflineProvider
from npc.state.social_store import SocialStore, StoreFailure
from tools.npc_lab.server import LabServer
from tools.npc_lab.service import CancelRequest, DisplayAck, LabService, LabStateEdit, LabTurn


def request(service, text, request_id):
    profile = next(p for p in service.info()["profiles"] if p["id"] == "mira")
    return LabTurn(request_id=request_id, persona_id="mira", text=text, relationship=profile["relationship"],
                   mood=profile["mood"], state_revision=profile["state_revision"])


def test_progressive_abuse_is_persistent_and_restart_remembers_displayed_turns(tmp_path):
    async def run():
        store = SocialStore(tmp_path / "social.sqlite3")
        service = LabService(OfflineProvider(), state_store=store)
        lines = []
        for i in range(3):
            turn = request(service, "fuck you", f"r-{i}")
            result = await service.turn(turn)
            lines.append(result["result"])
            await service.displayed(DisplayAck(request_id=turn.request_id, persona_id="mira"))
        assert lines[0]["response"]["text"] == "Mind your tongue."
        assert "damn" in lines[1]["response"]["text"]
        assert lines[2]["response"]["mode"] == "end"
        assert all(r["model_calls"] == 0 for r in lines)
        reopened = LabService(OfflineProvider(), state_store=SocialStore(store.path))
        profile = next(p for p in reopened.info()["profiles"] if p["id"] == "mira")
        assert profile["relationship"]["irritation"] == 83
        assert len(profile["history"]) == 3
        assert profile["history"][-1]["mode"] == "end"
    asyncio.run(run())


def test_completed_turn_replay_does_not_update_state_or_generate_again(tmp_path):
    async def run():
        service = LabService(OfflineProvider(), state_store=SocialStore(tmp_path / "state.sqlite3"))
        turn = request(service, "How is your work?", "r-1")
        first = await service.turn(turn)
        second = await service.turn(turn)
        assert second["cached"]
        assert first["saved_state"] == second["saved_state"]
        assert service.state_store.load(service.state_key("mira"))["revision"] == first["saved_state"]["state_revision"]
    asyncio.run(run())


def test_failed_durable_staging_does_not_expose_speech_cache(tmp_path, monkeypatch):
    async def run():
        store = SocialStore(tmp_path / "state.sqlite3")
        service = LabService(OfflineProvider(), state_store=store)
        def fail(*args): raise StoreFailure("state_unavailable")
        monkeypatch.setattr(store, "stage_preview", fail)
        with pytest.raises(StoreFailure): await service.turn(request(service, "How is work?", "r-1"))
        assert not service.speech_records
        assert not store.load(service.state_key("mira"))["history"]
    asyncio.run(run())


def test_cancelled_generation_retains_heard_input_but_not_npc_memory(tmp_path):
    async def run():
        started = asyncio.Event()
        class Waiting:
            async def generate(self, prompt, timeout_s):
                started.set(); await asyncio.sleep(20)
                return ProviderReply(content="unused", model="fake", finish_reason="stop")
        service = LabService(Waiting(), state_store=SocialStore(tmp_path / "state.sqlite3"))
        turn = request(service, "How is work?", "r-1")
        task = asyncio.create_task(service.turn(turn)); await started.wait()
        await service.cancel(CancelRequest(request_id="r-1"))
        result = await task
        assert result["result"]["status"] == "cancelled"
        saved = service.state_store.load(service.state_key("mira"))
        assert saved["revision"] > turn.state_revision
        assert not saved["history"]
    asyncio.run(run())


def test_http_state_revision_acknowledgement_and_override(tmp_path):
    service = LabService(OfflineProvider(), state_store=SocialStore(tmp_path / "state.sqlite3"))
    server = LabServer(service, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with httpx.Client(base_url=server.origin, timeout=5, trust_env=False) as client:
            headers = {"Origin":server.origin, "X-Lab-Token":server.token}
            turn = request(service, "fuck you", "r-http")
            result = client.post("/api/turn", json=turn.model_dump(mode="json"), headers=headers)
            assert result.status_code == 200
            state = result.json()["saved_state"]
            assert state["relationship"]["irritation"] > turn.relationship.irritation
            ack = client.post("/api/displayed", json={"request_id":"r-http","persona_id":"mira"}, headers=headers)
            assert ack.status_code == 200 and len(ack.json()["history"]) == 1
            override = dict(persona_id="mira", relationship=state["relationship"], mood="calm", state_revision=turn.state_revision)
            assert client.post("/api/state", json=override, headers=headers).status_code == 409
            override["state_revision"] = state["state_revision"]
            assert client.post("/api/state", json=override, headers=headers).status_code == 200
    finally:
        server.shutdown(); thread.join(timeout=2); server.server_close()
