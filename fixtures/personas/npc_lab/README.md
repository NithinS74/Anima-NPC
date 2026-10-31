# Public manual-test personas

Four fictional profiles for the separate [NPC lab](../../../docs/NPC_LAB.md):

| File | Contrast to test |
|---|---|
| [mira.json](mira.json) | Dry smith: work obligations, familiarity versus trust, customer privacy |
| [elin.json](elin.json) | Warm innkeeper: hospitality to strangers while protecting guests |
| [daren.json](daren.json) | Reserved guard: suspicion versus disproportionate hostility |
| [iona.json](iona.json) | Formal station registrar: cross-world behavior and unknown procedures |

`persona` uses the core `Persona` schema; `relationship` uses its five separate scores. `mood` and `current_goal` seed transient state. `world`/`location` provide test scope and an observable setting. `tagline`, `starters` and `testing_notes` help the tester; they do not enter the model as extra policy/knowledge.

The strict test-only wrapper is `LabProfile` in `tools/npc_lab/service.py`. IDs must match filenames, unknown fields fail validation, at most 16 profiles are loaded, and each file is capped at 16 KB. Edit these JSON files and restart the lab. Do not add keys, game binaries, real private player data or invented knowledge grants. A character's occupation alone does not establish particular prices, people, equipment or procedures.

For a repeatable comparison, use the same utterance, change one parameter, export both traces, and judge willingness, emotional proportionality, motives, voice and grounding. Multiple wordings may be plausible; an exact expected sentence is not the quality target. Existing policy limitations (including simplistic authored greetings) are deliberately visible rather than patched only in the test tool.

Persona temperament also includes `patience`, `assertiveness` and `swearing`. JSON values seed new stores; saved relationship/mood values survive profile reload and are changed through explicit test overrides. See [social-state rules](../../../docs/SOCIAL_STATE.md). Optional Skyrim appearances are visual stand-ins only; they grant no lore or memories to these fictional profiles.
