"""Small evidence boundary for the existing folder-RAG connector."""

from typing import Annotated, Literal, Protocol

from pydantic import Field, StrictBool, StrictInt

from npc.contracts.context import Contract, Identifier, Scope, Situation

RetrievalStatus = Literal["disabled", "not_requested", "ok", "empty", "unavailable", "forbidden"]


class Evidence(Contract):
    id: Identifier
    text: Annotated[str, Field(strict=True, min_length=1, max_length=12000)]
    source: Annotated[str, Field(strict=True, min_length=1, max_length=512)]
    page: Annotated[StrictInt, Field(ge=1)] | None = None
    chunk_index: Annotated[StrictInt, Field(ge=0)]
    distance: float = Field(ge=0)
    truncated: StrictBool = False
    source_kind: Literal["reference", "dialogue"] = "reference"
    record_ids: Annotated[tuple[Identifier, ...], Field(max_length=64)] = ()


class KnowledgeContext(Contract):
    scope: Scope
    npc_id: Identifier
    status: RetrievalStatus
    source_kind: Literal["reference", "dialogue"] = "reference"
    evidence: Annotated[tuple[Evidence, ...], Field(max_length=3)] = ()


class Retriever(Protocol):
    async def retrieve(self, situation: Situation, *, timeout_s: float) -> KnowledgeContext: ...
