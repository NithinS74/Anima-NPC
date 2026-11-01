"""Local RAG component with an optional HTTP compatibility transport."""

from npc.rag.http import HTTPRetriever, load_retriever
from npc.rag.local import LocalRetriever

__all__ = ["LocalRetriever", "HTTPRetriever", "load_retriever"]
