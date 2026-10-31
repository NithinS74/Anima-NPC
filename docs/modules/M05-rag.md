# M05 - Generalized local RAG

Status: proposed | Requirements: SYS-05, SYS-06 | Owner/reviewer: unassigned

## Responsibility

Ingest supported knowledge documents and provide scoped evidence to any caller. The module does not write prompts, decide NPC behavior or invoke the dialogue model. Chroma is the proposed MVP local vector store, behind a `VectorStore` interface. This is a practical choice to evaluate, not a claim it is universally best.

Use an embedded persistent client with one runtime owner for the local prototype. Chroma documents disk-backed persistence and recommends a server-backed instance for production: [official client reference](https://docs.trychroma.com/reference/python/client). Multiworker deployments must switch storage topology deliberately.

## Input and setup

Default root `Knowledge base/kb`; configurable once, not duplicated under another `kb`. Initial formats: UTF-8 `.txt`, `.md`, structured `.json`, `.csv`, and text-based `.pdf`. Scan only inside the resolved root, skip symlink escapes and hidden/temp files, cap file size/page count, report unsupported/encrypted/scanned PDFs. OCR, HTML and complex document tables are future work. Use page-aware extraction and show previews; plain text extraction can flatten diagrams/tables incorrectly.

Define per-document sidecar metadata and folder defaults with world, source, version/license, entity/region/faction, access grants, secrets, valid-from/until and document ID. Missing world/access metadata goes to quarantine, not unrestricted indexing. Authoritative persona files are separately validated into SQLite; embedding them does not make them state definitions.

Planned commands: `npc kb validate`, `npc kb ingest`, `npc kb status`, `npc kb rebuild --confirm`, `npc doctor`. Setup installs locked dependencies, creates data directories/collections and downloads/verifies a configured local embedding model with progress. Offline startup verifies existing artifacts and never silently downloads a different model. Chroma itself is created by the application; users do not need a separate database installation for this mode. CLI/scripts are deliverables of this issue, not currently working commands.

## Index lifecycle

Extract -> normalize -> document-aware chunk -> attach metadata -> embed -> stage -> validate -> activate index revision. Start around 300-500 tokens/chunk with 50-token overlap as tunable proposals; never cross access boundaries. IDs derive from document ID, source revision, chunk ordinal and normalized content hash. Manifest records file hash, parser/chunker/embedding versions, embedding dimension and index revision.

Unchanged files do not re-embed; reuse their manifest/vector entries. Changed files replace old chunks; confirmed deletion removes obsolete chunks, never a transient I/O error. Start with serialized explicit ingestion outside interactive sessions: stop admitting queries, close the single client, build/validate a staging index and activate its manifest before reopening. Keep one last-good generation for recovery, with staging/backup limits from the [resource profile](../RESOURCE_PROFILE.md). Defer concurrent hot reindex/snapshot retention. Encoder/dimension changes require a new collection/rebuild. Measure rebuild time/disk cost before adding live revision switching; never mix encoders/dimensions.

## Retrieval contract

`ingest(root, config) -> IngestReport`; `retrieve(RetrievalRequest) -> EvidenceSet`; `health() -> IndexStatus`.

Request includes query, scope, trusted eligibility policy/access partitions, simulation time, index revision, top_k and token/deadline limits. Implement bounded vocabulary/limits from [contracts](../CONTRACTS.md); indexed catalog lookup and filter construction count in retrieval latency. One authorized filtered query per turn, no per-document enumeration or unbounded fanout. Every required grant must hold before authorizing a partition. Unsupported/oversized policy fails closed. Recheck result scope/time/access; never replace preauthorization with global top-k followed only by filtering.

Default top_k=3, one CPU query-embedding worker, no model reranker, deadline <=150 ms warm target including authorization and query embedding. Return text, IDs/locators, scope, validity, distance and versions. Distance is model-specific, not calibrated confidence. Calibrate abstention; empty results are normal. Start without a retrieval cache; add one only if measured repeats justify it, keyed by query, eligibility hash, validity time and embedding/index revisions with explicit invalidation.

## Acceptance / handoff

Clean setup creates local storage without manual Chroma work. Two corpus packs work without source changes. Demonstrate duplicate ingest, edit/delete, extraction/metadata errors, empty KB, missing offline model diagnostics, encoder rebuild and interrupted staging recovery. Queries are typed unavailable during explicit ingestion; hot reindex is deferred. Test 10x corpus/grant scale against filter/work/storage bounds and an unauthorized nearest-vector secret. Provide CLI, manifest and retrieval plus post-packing relevance results.
