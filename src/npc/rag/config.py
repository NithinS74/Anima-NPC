"""Trusted backend, world/NPC and source selection."""

from typing import Annotated, Literal
from urllib.parse import urlsplit
from pydantic import Field, StrictInt, field_validator, model_validator
from npc.contracts.context import Contract, Identifier

class SourceBinding(Contract):
    game_id: Identifier
    world_id: Identifier
    npc_ids: Annotated[tuple[Identifier, ...], Field(min_length=1, max_length=64)]
    source: Annotated[str, Field(strict=True, min_length=1, max_length=512)]
    source_format: Literal["reference", "dialogue_export"] = "reference"

    @field_validator("source")
    @classmethod
    def relative_source(cls, value):
        if value.startswith("/") or "\\" in value or ":" in value or ".." in value.split("/"):
            raise ValueError("source must be an exact path relative to the RAG knowledge root")
        return value


class RAGConfig(Contract):
    backend: Literal["local", "http"] = "local"
    kb_dir: str = "Knowledge base/kb"
    data_dir: str = "data/rag"
    base_url: str = "http://127.0.0.1:8000"
    bindings: Annotated[tuple[SourceBinding, ...], Field(min_length=1, max_length=64)]
    top_k: Annotated[StrictInt, Field(ge=1, le=3)] = 3
    max_chars: Annotated[StrictInt, Field(ge=256, le=12000)] = 6000
    max_distance: float | None = Field(default=None, ge=0)

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value):
        url = urlsplit(value)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("expected HTTP(S) service URL without credentials/query/fragment")
        return value.rstrip("/")

    @model_validator(mode="after")
    def unambiguous_bindings(self):
        keys = [(b.game_id, b.world_id, npc) for b in self.bindings for npc in b.npc_ids]
        if len(keys) != len(set(keys)):
            raise ValueError("each game/world/NPC must have exactly one source binding")
        return self
