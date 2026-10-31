# Proposed architecture decisions

31 October 2026 | All provisional until team review or benchmark evidence

| ID | Decision | Rationale / revisit trigger |
|---|---|---|
| ADR-01 | Game-independent core with replay adapter first | Core can be built/tested without mod work; revisit only if canonical schema loses essential game semantics |
| ADR-02 | Python 3.11+, FastAPI modular monolith | Lightweight interfaces and local deployment; split processes only for measured isolation/scale needs |
| ADR-03 | SQLite authority, Chroma retrieval | Explicit state differs from approximate retrieval; server-backed store when concurrency/deployment needs exceed local prototype |
| ADR-04 | Policy before generation | Silence, refusal and routine greetings can avoid model calls; evaluate social errors and repetition |
| ADR-05 | Directed multi-field relationships | Favourability alone cannot represent trust, familiarity and threat; tune fields using scenario results |
| ADR-06 | API-first, replaceable provider | Explicit user preference; local later. 4 GB VRAM with game is aspirational, not guaranteed |
| ADR-07 | Buffer short output before delivery | Validation must precede irreversible speech; sentence streaming requires separate validated incremental protocol |
| ADR-08 | At most one repair within one turn deadline | Bounds delay/cost; no always-on second-model critique |
| ADR-09 | NPC knowledge eligibility before ranking | Similarity never authorizes disclosure; fail closed when access metadata is missing |
| ADR-10 | Optional visual descriptors, asynchronous CV | Preserves CV direction without blocking text evaluation; never conflate player view with NPC perception |
| ADR-11 | Authoritative event updates, acknowledged output memory | Avoid model-created relationships and memories of unplayed dialogue |
| ADR-12 | No retrieval/semantic response cache or fine-tuning initially | Measure orchestration first; immutable persona rendering is inexpensive if useful |
| ADR-13 | Bounded delivered history and explicit branch/reset first | Defer summaries/vector memory/historical checkpoint reconstruction until tests justify them |
| ADR-14 | Serialized offline ingestion, bounded authorization filters | Avoid unneeded live revision lifecycle and per-document query work |
| ADR-15 | Scope/NPC arbitration and atomic compare-and-stage | Prevent real races without a distributed scheduler; explicit receiver capability limits |
| ADR-16 | Portrait/parameter browser lab, optional compatible avatar | Exercise the same core; timebox asset presentation after G2 |
| ADR-17 | One pinned requirements.txt | Shared team setup; add CPU RAG dependencies when integration is implemented |

Open decisions: initial API model/provider and spend limit; reference hardware; exact embedding implementation/packaging; authored disclosure/relationship weights; baseline CV vocabulary/model; minimum adapter cue support; reliable save checkpoints; actual installed Mantella protocol/version. API keys remain local configuration. Decide these using benchmark/capture issues, without blocking contract work.
