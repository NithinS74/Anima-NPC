import asyncio
import json

from npc.contracts.context import ContextScenario
from npc.contracts.dialogue import ProviderReply
from npc.rag.config import RAGConfig
from npc.rag.local import LocalRetriever
from npc.runtime.preview import PreviewLimits, PreviewRunner


def test_real_local_store_to_context_prompt_and_citation_without_http_or_llm(service, scenario_data):
    (service.settings.kb_dir / "world.txt").write_text("The healer works at the eastern gate.")
    (service.settings.kb_dir / "secret.txt").write_text("PRIVATE_SECRET nearest healer gate information.")
    assert service.sync().indexed == 2
    scenario_data["turn"]["facts"] = []
    scenario_data["turn"]["player_input"]["text"] = "Where is the healer?"
    scenario = ContextScenario.model_validate(scenario_data)
    config = RAGConfig(bindings=[dict(game_id=scenario.turn.scope.game_id, world_id=scenario.turn.scope.world_id,
                                     npc_ids=[scenario.turn.npc_id], source="world.txt")])
    class Provider:
        async def generate(self, prompt, timeout_s):
            data = json.loads(prompt.messages[1].content)
            assert data["retrieved_evidence"][0]["text"] == "The healer works at the eastern gate."
            assert "PRIVATE_SECRET" not in prompt.messages[1].content
            id = data["retrieved_evidence"][0]["id"]
            return ProviderReply(content=json.dumps(dict(mode="speech", text="Try the eastern gate.", evidence_ids=[id])),
                                 model="fake-local-test", finish_reason="stop")
    result = asyncio.run(PreviewRunner(Provider(), PreviewLimits(max_input_bytes=10000),
                                      retriever=LocalRetriever(config, service=service)).run(scenario))
    assert result.status == "model_success"
    assert result.response.text == "Try the eastern gate."
    assert result.response.evidence_ids == result.evidence_used
    assert result.knowledge.evidence[0].source == "world.txt"


def test_another_worker_cannot_query_while_explicit_ingestion_owns_file_lock(service, scenario):
    from npc.context import build_situation
    situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
    config = RAGConfig(bindings=[dict(game_id=situation.scope.game_id, world_id=situation.scope.world_id,
                                     npc_ids=[situation.npc_id], source="world.txt")])
    with service.lock:
        result = asyncio.run(LocalRetriever(config, service=service).retrieve(situation, timeout_s=0.5))
    assert result.status == "unavailable"
