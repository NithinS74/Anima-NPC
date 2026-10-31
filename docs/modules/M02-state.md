# M02 - Persona, relationship and memory store

Status: proposed | Requirements: SYS-02, SYS-03 | Owner/reviewer: unassigned

## Responsibility and interfaces

SQLite is the durable authority for authored NPC configuration, runtime state and memory. Expose `load_snapshot(scope, npc_id, player_id)`, `apply_event(event, expected_revision)`, `stage_turn(result, expected_dialogue_revision, turn_epoch)`, `ack_delivery(ack)`, and `select_branch(branch_id)`.

Minimum tables: `world_branches`, `npc_definitions`, `npc_instances`, `relationships`, `events`, `sessions`, `turns`, `memories`, `delivery_outbox`, `schema_migrations`. Every runtime primary key includes world/save branch scope. Relationships are directed from an NPC to a player; never aggregate everyone into one favourability meter.

## State rules

Author immutable identity/persona separately from mutable goals, mood and relationships. Model favourability/trust [-100,100], familiarity/fear/irritation [0,100]. Use versioned event weights and explicit decay rules. Prototype example only: witnessed assistance +5 favourability, fulfilled promise +8 trust, witnessed theft -15 trust, repeated greeting familiarity gain capped at +1 per cooldown. Tune empirically. Fear decays with elapsed simulation time, not request count. Familiarity does not decay by default. Stable persona does not drift every turn.

Events need ID, source, witness scope, attribution and simulation time. Deduplicate atomically with revision changes. Player assertions cannot serve as proof of game actions. Cap repeated-event gains to avoid greeting/gift farming. Authored faction reputation can set a prior but is distinct from personal trust.

Use the [delivery lifecycle](../CONTRACTS.md#delivery-lifecycle) for heard memory. Record actual heard portions only when the adapter reports them reliably; otherwise mark delivery unknown. Session memory starts with bounded delivered turns; relationship/event state persists across sessions. Preserve "player said X" separately from "X is true". Automated summaries/vector episodic memory are deferred; future summaries cite source events, remain untrusted narrative data and cannot promote rumors into fact. The core records acknowledged mechanics as observations, not authority to change the game itself.

## Failure and concurrency

Use transactions and optimistic revisions, one writer path initially, bounded lock retries and explicit `state_conflict`. Serialize active turns per scope/NPC across sessions. In one short transaction, staging checks dialogue-relevant revision, turn epoch and cancellation before inserting the result/outbox; no transaction spans inference. Separate storage revision from relevant dialogue revision so log writes do not starve replies. A failed durable write cannot dispatch output with no record. Select an explicit branch/reset for synthetic saves; historical checkpoint restoration is deferred until a real adapter supports it. Without reliable save identity, use session-only persistence. See the [resource profile](../RESOURCE_PROFILE.md) for retention and bounds.

## Acceptance / handoff

Restart persistence, two worlds/two players isolation, duplicate assistance, conflicting revisions, explicit branch/reset, combat between validation and staging, concurrent sessions for one NPC, benign telemetry during generation, expired/reordered acknowledgements and interrupted speech must pass. Supply migrations, authored personas, event weights and a fake repository. No LLM is needed for relationship updates or initial bounded history.

Implementation update: the [social-state slice](../SOCIAL_STATE.md) adds deterministic appraisal, persona temperament, SQLite directed relationships and bounded acknowledged dialogue history. The [separate lab](../NPC_LAB.md) exercises these contracts; production game delivery, full M02 semantics and semantic grounding are still future work.
