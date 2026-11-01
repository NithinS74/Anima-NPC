"""Reusable ingestion/embedding/store implementation, owned by npc.rag."""

from .config import Settings
from .service import RAGService

__all__ = ["Settings", "RAGService"]
