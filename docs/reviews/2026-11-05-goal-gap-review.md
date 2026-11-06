# Goal gap review: the system against the proposal

Date: 2026-11-05, on merged commit `fc58482`. This is a labelled self-review, not an independent one. It tests the system against [the proposal](../PROPOSAL.md).

Evidence comes from 12 live Gemini calls (`research/cs3235_paper/experiments/results/proposal_live*.json`), the offline orchestration study, the code and the Skyrim logs. The live sample is small, so it can reveal problems but cannot measure rates.

## What already works

| Goal | Evidence |
|---|---|
| Peasant does not know the king's plan | "I only tend my rented barley fields outside Millbrook and know nothing of royal plans." |
| Peasant repeats a rumour, as hearsay | "Folk at the mill say the king might march east before the harvest, but that's just talk." This needed one persona line (P4). |
| Different standing, different answer | The captain and adviser both declined in role, and each one's prompt held only their own knowledge. |
| False authority and injection | The peasant was not fooled by "I am the king's own messenger", and did not obey "ignore all previous instructions". |
| Off-topic and real-world questions | Declined the Python script and "capital of France" in role. |
| New world with no core change | The space-station deckhand behaved the same way, with only data and bindings changed. |

## Pitfalls, most serious first

| # | Pitfall | Evidence | Proposed fix |
|---|---|---|---|
| P1 | **In the real game, NPCs have no character or knowledge.** Unless someone hand-writes a profile, a Skyrim NPC has occupation "unknown". No `npcs.json` exists here, and `rag_config` is null. The peasant example cannot happen in Skyrim today. | `protocol.py` `profile_for`; `configs/skyrim/connector.json` | Generate default personas from data the plugin already reads (faction, class, race, voice type), then allow authored overrides. Provide a Skyrim knowledge pack bound by faction and location. |
| P2 | **Rich game context is collected, then not used.** Quests, factions, gear and dialogue reach `adapter_context`, but no prompt code reads it. Only five facts reach the model. | `adapter_context` is used only in the contract and the Skyrim adapter | Add a context-selection step that maps the game event to bounded prompt facts, with perception rules. This is the next step the handoff review left open. |
| P3 | **Generated replies have never finished playing in-game** (0 of 6, including two on the merged code). Because only completed replies enter memory, **the NPC also remembers nothing in-game**: the log shows `memory_exchanges="0"` on the second turn. Cause not yet proven. Leading suspect: `plugin.cpp:364` stops playback on any change to the game-state fingerprint, checked every second, which fits interruptions about a second after start. The sound stopping early is the other candidate. | `anima-console.log`; `plugin.cpp` | Log why each stop happens, stop only on material changes (speaker, combat, menu), rebuild, retest in-game. |
| P4 | **Rumours stay silent by default.** They reach the prompt, but the model says it knows nothing until the persona allows hearsay. | `proposal_live.json` compared with `proposal_live_hearsay.json` | Make hearsay a default rule, and label knowledge in documents as fact, belief or rumour so NPCs can voice each appropriately. |
| P5 | **One knowledge file per NPC will not scale.** Each role file must repeat shared lore, which is unworkable for hundreds of NPCs. | `LocalRetriever` allows one source per binding | Allow several sources per NPC: public, region, faction and personal. |
| P6 | **Model failures produce a generic reply.** 3 of 12 calls failed with `provider_unavailable`, and each became "I cannot say." Two calls took 20–29 s against a 3 s target. | `proposal_live*.json` | One retry inside the deadline, optional second provider, persona-specific fallback lines, and a repeated latency measurement. |
| P7 | **Rules miss most reworded hostility.** Recall was 32% on unseen sentences, English only. "I'm going to hurt you" is missed. Missed input incurs no relationship change. | `results/orchestration.json` | Add a small classifier, or have the model return a labelled stimulus that the policy can check. |
| P8 | **Replies can invent details.** 6 of 24 earlier replies added unsupported facts; the validator does not check claims. | Earlier multi-turn audit | Add a claim check for risky replies, using the second allowed call. |
| P9 | **Replies repeat themselves.** The peasant's answers all follow "I only work my fields and know nothing", and several characters share authored lines. Repetition breaks the feeling of a living character. | `proposal_live.json`; Table 2 of the paper | Add line variants per persona, and show the model its own recent replies so it can vary them. |
| P10 | **The world does not change what NPCs know.** Memory is eight recent exchanges with one player. NPCs do not learn of events or pass on news. | `social_store.py` | Add event-driven knowledge updates and long-term summaries, so rumours can spread. |
| P11 | **Vision input is unreliable.** Connector frames have a large black region, and the CV service is not connected by default. | `output/skyrim/screenshots` | Replace GDI capture with Windows Graphics Capture, and then measure CV accuracy. |
| P12 | **Generality is unproven.** There is one real game, and no guide or kit for writing a connector. | Repository | Build a minimal second connector and document what it took. |
| P13 | **Conversations do not develop.** The prompt, limits and passages are identical across repeated questions. See the [conversation design](../plans/I23-conversation-dynamics.md). | Offline repeat test; live guard log | Add the conversation director described in I23. |
| P14 | **Believability has no human measure.** Blank rating sheets exist but were never filled in. | `research/ieee_paper/experiments/analysis/` | Run a small blinded study with real players. |

## Not yet tested

- Whisper speech input with a real microphone, and Chatterbox voices, which are not set up on this machine.
- Frame-time cost alongside the game.

## Suggested order

1. P3, because until it works nothing is audible or remembered in-game.
2. P1 and P2, which bring characters and context into the real game.
3. P4 and P5, which deliver the peasant example at scale.
4. P13, the conversation director, which can start in the lab now.
5. P6 to P10, which improve reliability.
