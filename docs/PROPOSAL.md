# Project proposal: a generalised orchestration layer for living NPCs

Status: the project owner's research vision. It states the goal, not what has been achieved. Current evidence is in the [CS3235 paper](../research/cs3235_paper/) and the root [README](../README.md).

## Goal

Build a generalised system for making NPCs that seem truly alive: characters who talk with players the way people talk with each other, and who feel as if they live in the game world.

Natural conversation is only part of the goal. An NPC must also respond from its **standing in the world** and never act out of character. What it knows, believes, is willing to say and how it says it should all follow from who it is.

## Guiding example

A player asks a peasant what the king's plan is for the war and how he would fight it.

| Character | Should know | Believable reply |
|---|---|---|
| Peasant | Never met the king and has no access to war councils. May have heard rumours | Does not know the plan. May share an opinion based on rumours, if that suits the character |
| King's adviser | Attends the war council | Knows the plan, and decides whether to tell this player |

The same question should get a different reply from each, and both replies should be correct for that character. This is one case of the wider requirement that context must be **dynamic**: it depends on the NPC, the player, the moment and what was just said.

## The problem with current approaches

- **Scripted dialogue trees** are predictable and in character, but they cannot answer anything the writers did not anticipate.
- **A language model connected directly to an NPC** can answer anything, but it knows things the character should not, and players can pull it out of character.
- **Training a custom model for each game or character** is expensive and inflexible. World knowledge changes during development, and each change risks more training.
- **Game-specific integrations** do not transfer. Games expose context and accept output in very different ways, so a single universal connector is not practical.

## Proposed solution

An **orchestration layer** sits between the game and the language model, and it depends on neither.

```text
Game A / Game B / test console
        |  connectors (often built on a game's existing mod support)
        v
   Canonical input and output contracts
        |
        v
   ORCHESTRATION LAYER
   - persona, relationship and game state
   - decide whether and how the NPC engages
   - retrieve only what this NPC may know (RAG)
   - build the prompt
   - validate the reply
        |
        v
   Replaceable language model (hosted or local)
```

### Design principles

1. **Model-agnostic.** Any model that fits the provider interface can be used. Changing model should not change orchestration logic.
2. **Game-agnostic.** The core has no game-specific logic. Each game has a thin connector for its input and output, often built on the mods it already supports.
3. **World knowledge through RAG, not training.** Creators supply documents describing their world and bind them to characters, which avoids the cost of training a custom model and lets them update knowledge by editing files.
4. **Knowledge bounded by character.** Retrieval is limited to what that NPC could plausibly know, before the model sees anything. Being relevant to a question does not make a fact available.
5. **Character over helpfulness.** Refusing, deflecting, staying silent or ending the conversation can be the right response.
6. **Game state stays authoritative.** The model proposes dialogue. It cannot change quests, inventory or relationships.

### Context sources

- **Player input:** text, or speech through speech-to-text.
- **Game state:** identity, location, combat state and similar facts from the connector.
- **Persona and relationship:** authored character data and persistent standing with the player.
- **World knowledge:** documents retrieved for the current question.
- **Vision:** a computer-vision service can describe what the player's camera shows. This stays an untrusted reference, because what the player sees is not necessarily what the NPC sees.

## Why this is worth researching

- Creators can reuse one system across games instead of building per-game AI.
- Avoiding per-game training lowers cost and keeps world knowledge easy to change.
- Separating the layers lets each one be tested and improved on its own.

## Research questions

1. Can an orchestration layer keep an NPC within the knowledge its role allows, while still letting it answer what it should know?
2. Does retrieved world knowledge make replies more faithful to the world than a model alone?
3. Can the same core serve different worlds and connectors, and which parts actually need to change?
4. Where do these boundaries stop working, and what does that require next?

## What success looks like

- Different characters give different, role-appropriate answers to the same question.
- Restricted knowledge does not reach a character who should not have it.
- New worlds need new data and bindings, and new games need connectors, with no changes to the core.
- Models can be replaced through configuration.
- Replies arrive quickly enough for live conversation.
- Human players rate the characters as believable. This still needs a proper study.
