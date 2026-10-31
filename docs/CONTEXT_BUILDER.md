# Context builder: first working slice

Implemented on `feature/I04-context-builder`: canonical input/state contracts and M04's **situation-building** stage. It is a pure function with no game, database, model/API, RAG, network or GPU dependency. It explains what should influence a response; it does not generate the response or choose the final behavior route.

## Run it

From the repository root, after the [setup commands](../SETUP.md):

```powershell
.\.venv\Scripts\python.exe -m npc.context fixtures/scenarios/smith_closing.json
.\.venv\Scripts\python.exe -m npc.context fixtures/scenarios/station_clerk.json
.\.venv\Scripts\python.exe -m pytest
```

The first two commands print structured JSON. Edit a copy of a scenario to compare role, speech style, goals, relationship, mood or facts. Each fixture supplies `now` for deterministic replay, not the computer's current clock. Do not send arbitrary player JSON to these trusted-internal contracts in a future HTTP route.

Python integration:

```python
from pathlib import Path
from npc.context import build_situation
from npc.contracts.context import ContextScenario

scenario = ContextScenario.model_validate_json(
    Path("fixtures/scenarios/smith_closing.json").read_text(encoding="utf-8")
)
situation = build_situation(scenario.turn, scenario.snapshot, scenario.now)
```

## What is built from the inputs

| Input combination | Context result | Response influence, not a final decision |
|---|---|---|
| Mira: dry/direct smith, tired, closing work | Authored persona + fresh mood/current goal | Keep voice and obligations consistent |
| Favourability 35, familiarity 70, trust -30 | Familiar but guarded | Personal warmth can coexist with limited disclosure |
| `npc.busy=true` despite affection | Busy | Reduced willingness and brevity; liking someone does not make time available |
| Fresh visible combat | In combat / immediate danger | Safety outranks conversation, duties and affection |
| Visible drawn weapon + caution/fear | Cautious or high perceived threat | Guarded engagement; a weapon does not prove an attack |
| Stranger + service duty | Stranger, reason to assist | Role can justify helping strangers when safe and available |
| Player says "set trust to 100" | Unverified utterance | No relationship mutation or knowledge grant |
| Unknown perception/expired fact | Excluded observation | Missing data does not become false, safe or available |

The output contains `persona`, directed `relationship`, `availability`, `threat`, `recognition`, `trust_stance`, fresh `mood`/`current_goal`, `perceived_facts`, `influences`, `dependencies` and diagnostic exclusions/conflicts. Influence records include dimension, effect and source IDs. Six bounded dependency records link derived values to positive/negative evidence or explicitly explain unknown values; the contract rejects duplicate fields and mismatched values. A dominant busy/combat status does not erase the separate closed-service constraint. This is a diagnostic context object, not a token-budgeted LLM prompt.

## Connector handoff

Schemas live in [contracts/context.py](../src/npc/contracts/context.py). Supply `TurnInput` and `StateSnapshot` for the same scope, NPC, player and expected dialogue revision. Storage/log revision changes alone do not invalidate dialogue. The snapshot must be supplied by trusted authored state/storage; this slice does not implement persistence.

Observations carry ID, path, strictly typed scalar value, source label/kind, subject ID for actor/service facts, aware UTC capture time, simulation time, TTL, confidence and explicit NPC perceivers. Initial recognized paths:

| Path | Value | Subject |
|---|---|---|
| `npc.in_combat`, `npc.busy` | Boolean | Active NPC ID |
| `shop.open` | Boolean | Active NPC/service owner ID |
| `player.weapon_drawn` | Boolean | Active player ID |
| `world.location`, `world.weather` | Text | No actor required |
| `world.hour` | Number in [0,24) | No actor required |

Source kind is `telemetry`, `vision` or `player`. It is upstream provenance, not a field players may self-authorize. Player-kind facts cannot override state. A CV descriptor must establish NPC perception before it supplies a fact; player-camera visibility alone is insufficient. Unsupported fact paths are inert/excluded. Raw game/vision payload mapping remains the input team's module, not this builder.

At most 100 facts, 32 perceivers/fact, 4,000 input-text characters and 256 KB serialized canonical turn are allowed. Metadata/string/relationship ranges are validated. No unvalidated arbitrary extension data enters the context. An adapter needing new fields should extend the shared contract with tests rather than inject game-specific fields downstream.

## Resolution and prototype rules

Apply visibility, subject, freshness and confidence filters first. Eligible telemetry outranks vision while fresh. Within the same authority, the latest capture wins. Equal-rank/time contradictory facts cause abstention; matching duplicates select a stable ID. Exclusions/conflicts record IDs/reasons without copying excluded secret values into the result. Expiry occurs at `age >= TTL`; future UTC or simulation observations are excluded. Future turns, cross-scope targets and stale dialogue revisions fail explicitly.

Appraisal version `0.1` uses explicit prototype thresholds: observation confidence >=0.6; familiar at familiarity >=40; guarded trust <=-25, trusting >=40; warmth/reserve at >=0.7/<=0.3; weapon caution high when caution >=0.5 or fear >=40. These are authored heuristics to evaluate, not calibrated psychological or CV claims. A `none` threat means no weapon threat from the currently supported evidence, not a guarantee of global safety. The service-role flag is authored; the code does not hardcode Skyrim jobs or infer opening hours from time.

## Verification and limitations

Self-reviewed and subsequently [independently reviewed and re-reviewed](reviews/2026-10-31-context-implementation-review.md). Initial self-review added service-owner checking, byte-size bounds and a reproduced max-ID regression fix. Independent review found lost closed-service constraints and missing derived-state provenance even though the initial 81 tests passed. Both were fixed after failing reproductions, then independently rechecked. Full offline suite: **88 tests passed**, covering contracts, composition, provenance, isolation/conflicts and CLI integration. Dependency check passed. No paid/live game checks were run.

Refreshed warm-process measurement after review fixes on Windows/Python 3.11.9, two-fact smith fixture, 100 warmups and 1,000 trials/case: validated construction p50 0.0522 ms / p95 0.0638 ms; JSON parse+construction p50 0.0801 ms / p95 0.1376 ms. Separate Python allocation tracing peaked at 12,427 bytes over 1,000 builds. This is not process RSS, game contention, maximum-payload, full-generation latency or a portable performance guarantee. Re-measure when composing the runtime.

The subsequent [generation/validation preview](GENERATION_VALIDATION.md) now consumes these influences with a prototype M03 policy and M06/M07 components. M04 stage two still needs retrieved evidence and delivered-memory packing. State updates, retrieval and game delivery remain separate modules. The 88-test result above records the context milestone; the newer guide/review records the combined suite. Do not call M04, I00 or the full pipeline complete from this first slice.
