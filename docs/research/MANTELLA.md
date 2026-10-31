# Mantella input audit

31 October 2026 | Read-only source inspection, not a live game/network capture

## Local installation inspected

User supplied `D:\MO2\mods\Mantella`. The folder contains Papyrus source scripts, `Mantella.esp`, an SKSE plugin tree and the packaged Mantella executable. MO2 metadata reports `version=d2026.10.25.0`; the archive basename contains `Mantella-98631-0-14-1777401380.zip`, suggesting a 0.14 package. This is not a verified running executable version. Do not use the MO2 date version as a protocol version.

Relevant installed files:

- `Scripts/Source/MantellaConversation.psc`: actor/context construction, player-input requests and HTTP round trips.
- `Scripts/Source/MantellaConstants.psc`: installed protocol keys and route casing.
- `Scripts/Source/SKSE_HTTP.psc`: native typed dictionary and localhost request declarations.
- `Scripts/Source/MantellaInterface.psc`: conversation/action mod events and custom event injection.
- `Scripts/Source/MantellaRepository.psc`: configurable HTTP port; default assignment 4999.

No installed scripts, configuration, game saves or credentials were modified. No secret-key file contents were read.

## Observed local data path

Papyrus game scripts read engine information -> construct typed dictionaries through SKSE_HTTP -> call `sendLocalhostHttpRequest(handle, repository.HttpPort, route)` -> external Mantella backend -> typed reply and game-side handling. This is not a universal game-memory reader. The installed script's main route constant is **`Mantella`** (capital M). Upstream backend currently shows **`/mantella`** (lowercase). HTTP paths can be case sensitive: verify the actual plugin/backend normalization before writing a proxy.

Local source anchors: `MantellaConversation.psc` lines 958-977 build actors; lines 994-1023 build context; `MantellaConstants.psc` line 3 sets the route; `MantellaRepository.psc` declares HttpPort and assigns its default. Line numbers refer to this inspected installation and can change with upgrades.

## Mapping into our core

The following mappings are our proposed adapter design, based on the installed scripts, not a claim that these fields are continuously refreshed or available in every request.

| Installed payload | Proposed use | Limitation |
|---|---|---|
| actor base ID / reference ID | Definition versus runtime NPC identity | Add world/save scope and stable load-order mapping |
| name, race, gender, voice type | Descriptive/voice metadata | Names do not identify unique instances; no personality inference from race/gender |
| relationship rank | Optional prior/source attribute | Preserve raw rank; do not equate it to favourability/trust |
| combat and enemy flags | Availability/threat evidence | Freshness and target scope require validation |
| equipment description | Potentially relevant observable gear | Presence in payload does not prove NPC visibility |
| location, hour, game days | Situation and simulation clock | Partial updates and change-tracking settings affect freshness |
| nested weather ID/classification | Environment observation | Keep raw ID and adapter-generated label |
| nearby actors | Proximity context | Current local scan is player-centered; not automatic NPC perception |
| in-game event strings | Narrative observations | Free text lacks guaranteed actor IDs, witnesses or event types |
| custom player/context values | Extension mechanism | Validate allowed fields; not trusted instructions |

Complete quest state, NPC schedule/needs, line-of-sight, inventory ownership, reliable witnessed-event attribution and persistent save branch identity are not established by this audit. Some may be exposed by additional mods or custom scripts; mark unknown until measured.

## Upstream cross-check

The [upstream conversation script](https://github.com/art-from-the-machine/Mantella-Spell/blob/main/Scripts/Source/MantellaConversation.psc) confirms the general Papyrus-to-localhost approach. The [backend route](https://github.com/art-from-the-machine/Mantella/blob/main/src/http/routes/mantella_route.py) handles initialization, conversation start/continue, player input and end. [Communication constants](https://github.com/art-from-the-machine/Mantella/blob/main/src/http/communication_constants.py) define the JSON vocabulary. The [game manager](https://github.com/art-from-the-machine/Mantella/blob/main/src/game_manager.py) consumes actor/context data. These mutable upstream references are supporting evidence; the local installed interface governs our adapter experiment.

## Reuse strategy

Start by reusing the concept and transport boundary: existing game observations -> a thin canonical adapter -> our orchestrator. Keep the core independent of Mantella's prompt/memory/LLM design. We can learn from its extraction path without adopting its conversational behavior. Reusing or modifying third-party code requires recording its license and notices; [Mantella's repository](https://github.com/art-from-the-machine/Mantella) identifies AGPL-3.0. No third-party implementation has been copied into this repository.

Two experiments, in order:

1. **Input-only capture/replay:** observe a normal conversation's payloads using supported debug logging or an opt-in local relay. Redact player/secret data; retain protocol shape, revisions and timings. Build fixtures and feed our engine offline. Mantella remains responsible for its own replies during this experiment.
2. **Compatibility facade, best effort:** in a separate MO2 profile/disposable save, route the mod to our localhost facade and reproduce its handshake/start/continue/end state machine. Map our validated results back to expected responses. Text replies alone may be insufficient: audio/lip/subtitle/topic lifecycle and action acknowledgements need their own compatibility work. Avoid two services binding the same port. Back up and document any future configuration changes before applying them.

The mod event API can add contextual events and receive action notifications; source inspection does not establish that it can replace the entire backend without protocol work. A passive input bridge is a smaller first goal than full output replacement.

## Audit issue acceptance

Record executable/mod version and source hashes; capture initialize/start/player/continue/end messages; verify route casing and port; label full versus partial fields; identify actual update cadence and perception limitations; replay a captured conversation into canonical input; publish a gap/capability report. Only then decide whether a full compatibility adapter fits the semester. No live capture or game launch has yet been performed.
