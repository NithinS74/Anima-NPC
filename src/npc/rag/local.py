"""One local CPU retrieval at a time, without ingestion in interactive turns."""

import asyncio
import threading
from pathlib import Path

from npc.context.focus import resolve_question
from npc.rag.evidence import normalize_result, result_for, select_binding

ROOT = Path(__file__).resolve().parents[3]


class LocalRetriever:
    def __init__(self, config, *, root=ROOT, service=None):
        self.config = config
        self.root = Path(root).resolve()
        self._service = service
        self._gate = threading.Lock()
        self._pending = None

    def _service_ready(self):
        if self._service is None:
            data = (self.root / self.config.data_dir).resolve()
            model = data / "models/all-MiniLM-L6-v2/onnx"
            # Preparation is an explicit setup/CLI step, never an on-turn download.
            required = [data / "knowledge_base.manifest.json"] + [model / name for name in (
                "model.onnx", "config.json", "tokenizer.json", "vocab.txt", "special_tokens_map.json", "tokenizer_config.json")]
            if not all(path.is_file() for path in required):
                raise FileNotFoundError("Run setup or python -m npc.rag prepare first")
            from npc.rag.backend import RAGService, Settings
            self._service = RAGService(Settings(root=self.root, kb_dir=self.config.kb_dir, data_dir=self.config.data_dir))
            embedder = getattr(self._service, "embedder", None)
            if embedder is not None and hasattr(embedder, "embed"):
                from npc.context.conversation import set_encoder
                set_encoder(embedder.embed)  # already loaded for retrieval; reused for turn similarity
        return self._service

    async def retrieve(self, situation, *, timeout_s):
        binding = select_binding(self.config, situation)
        if binding is None:
            return result_for(situation, binding, "forbidden")
        if timeout_s <= 0 or not self._gate.acquire(blocking=False):
            return result_for(situation, binding, "unavailable")
        query = resolve_question(situation)

        def work():
            try:
                reply = self._service_ready().retrieve(query, top_k=self.config.candidate_k,
                                                      max_chars=self.config.max_chars, source=binding.source)
                return normalize_result(self.config, situation, binding, query, reply.model_dump())
            except (OSError, ValueError, RuntimeError, ImportError, KeyError, TypeError):
                return result_for(situation, binding, "unavailable")
            finally:
                # Release on actual worker completion, not caller cancellation.
                self._gate.release()

        task = asyncio.create_task(asyncio.to_thread(work))
        self._pending = task
        def settled(done):
            if not done.cancelled():
                done.exception()
            if self._pending is done:
                self._pending = None
        task.add_done_callback(settled)
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=timeout_s)
        except TimeoutError:
            return result_for(situation, binding, "unavailable")
