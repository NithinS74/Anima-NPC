"""Optional HTTP transport; the default application uses the local component."""

import json
from pathlib import Path
import httpx

from npc.context.focus import resolve_question
from npc.rag.config import RAGConfig, SourceBinding
from npc.rag.evidence import normalize_result, result_for, select_binding


class HTTPRetriever:
    def __init__(self, config: RAGConfig, *, transport=None):
        self.config = config
        self.transport = transport

    async def retrieve(self, situation, *, timeout_s):
        binding = select_binding(self.config, situation)
        if binding is None:
            return result_for(situation, binding, "forbidden")
        query = resolve_question(situation)
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=timeout_s, trust_env=False) as client:
                async with client.stream("POST", self.config.base_url + "/query", json=dict(
                    query=query, top_k=self.config.candidate_k, max_chars=self.config.max_chars, source=binding.source,
                )) as response:
                    response.raise_for_status()
                    payload = bytearray()
                    async for chunk in response.aiter_bytes():
                        payload.extend(chunk)
                        if len(payload) > 96000:
                            return result_for(situation, binding, "unavailable")
            return normalize_result(self.config, situation, binding, query, json.loads(payload))
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return result_for(situation, binding, "unavailable")


def load_retriever(path: Path | None):
    if path is None:
        return None
    if path.stat().st_size > 65536:
        raise ValueError("RAG configuration exceeds 64 KiB")
    config = RAGConfig.model_validate_json(path.read_text(encoding="utf-8"))
    if config.backend == "http":
        return HTTPRetriever(config)
    from npc.rag.local import LocalRetriever
    return LocalRetriever(config)
