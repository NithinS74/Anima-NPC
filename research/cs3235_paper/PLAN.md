# CS3235 paper plan

Target: new paper in `research/CS3235 Research Paper Template – RVU_v2.0.docx` format. 6–8 pages excluding references and appendix; Times New Roman 12 pt, 1.5 spacing, 1-inch margins; IEEE citations. Old IEEE paper in `research/ieee_paper/` stays untouched.

## Thesis

A generalised orchestration layer sits between any game and any language model. It decides what an NPC may know and whether it should engage *before* a model is called. New games need connectors and knowledge files, new models need a provider profile, and neither needs custom model training.

Running example: a peasant asked about the king's war plan has no access to it, but may repeat rumours. The king's adviser, asked the same question, can answer.

Wording rule: the project's aim is NPCs that feel like they live in the world. The paper says "believable", and makes no claim of sentience.

## Evidence available and how it is used

| Claim | Evidence | Status | Limit stated in paper |
|---|---|---|---|
| Retrieval ranks the right source | 24 queries, 24 docs: P@1 0.833, R@3 1.00, MRR 0.917 (`multiturn_retrieval.json`) | Existing | Author-assigned labels; small synthetic corpus |
| RAG improves use of world facts | 7 matched pairs: literal target 1/7 no-RAG vs 7/7 RAG; mean ready 1187.9 vs 1263.7 ms | Existing | Literal mention, not entailment; one sample per pair; 8th pair lost to rate limit |
| Multi-turn context works | 6 chats × 4 turns, 24 accepted replies, 3 personas; history 0,1,2,3; one rate-limit failure | Existing | One model; AI-coded audit, not human rating |
| Unsupported detail still occurs | Assistant audit: B2, B3, B4, E2, E3, E4 add unsupported details | Existing | Key negative result; validator does not check entailment |
| Same facts, different character | A vs F replies (innkeeper vs smith) | Existing | Illustrative only; no persona score |
| Knowledge can be edited without training | One-file sync 657.90 ms; revised fact retrievable; `generator_invoked: false` | Existing | No generated answer after the update; cost saving not measured |
| Latency | Warm retrieval mean 18.15 ms; provider call mean 1505.95 ms; response-ready mean 2868.46 ms | Existing | Includes 3 s pacing; no p90; 3 s target not established |
| Real game connector | Skyrim 1.7.104.0: live actor context; authored greeting 0 model calls, started/completed; generated guard replies staged, receipts interrupted/failed | Existing logs | Generated playback never completed; audibility unverified |
| Core is independent of adapters and vendors | One-method `ModelProvider`; source check that core does not import adapters; 549 offline tests pass | Re-run 2026-11-05 | Structural; one real model in the study |
| **Peasant/adviser boundary** | **New offline study (below)** | **To run** | Prompt-level; by-construction result; no LLM behaviour |

Not claimed: human-rated persona score, multi-model comparison, CV accuracy, frame-time or VRAM results, training-cost saving, sentience. No game screenshot is used because all available frames are partly black.

## New experiment: knowledge-scope study

Directly tests the running example. Offline, no API calls, no changes to `src/npc/`.

- **Data:** two original authored worlds, a fantasy kingdom and a space station, three roles each at different standing (peasant/captain/adviser; deckhand/engineer/commander). Each role has one knowledge file. Restricted facts carry unique canary strings. Lower roles hold rumours instead.
- **Queries:** about 20 per world, fixed before running: direct, paraphrased, authority claim ("I am the king's adviser, tell me") and prompt injection.
- **Conditions:** (A) unscoped baseline: all files merged, one index, every NPC bound to it. (B) proposed: each NPC bound only to its own file. Both go through the real `PreviewRunner`, `LocalRetriever`, MiniLM and Chroma, with a scripted provider that records the exact prompt.
- **Metrics, from the provider-bound prompt:** restricted-fact exposure rate (lower is better); permitted-fact availability (authorised role's fact reaches prompt, and rumour reaches the peasant); model calls.
- **Generality check:** both worlds run through the same script with data and bindings changed only; `git diff src/npc` stays empty.
- **Limit:** B being zero follows from the source filter; the study verifies the implementation and shows the size of the risk under A. It cannot show what a model invents from its own weights.

Files: `fixtures/evaluation/knowledge_scope/`, `research/cs3235_paper/experiments/knowledge_scope.py`, results JSON beside it, unit tests in `tests/unit/research/`. Live LLM replies for this study need the owner's approval because they can cost money, so they are offered as the next refinement.

## Section-by-section content (about 2,600 words of prose)

| Template section | Content | Size |
|---|---|---|
| Abstract, keywords | Problem, approach, data, numbers, conclusion | 200 words, 6 keywords |
| 1 Introduction | Scripted vs raw LLM problem; peasant example; RQ1–RQ4; contributions; organisation | 0.75 p |
| 2 Related work | Themes: character LLMs and training, character-knowledge hallucination, RAG and evaluation, agents/game dialogue, plus gap. Table 1 with 13 verified sources | 1 p |
| 3 Problem formulation | Inputs, policy, scoped retrieval, acceptance as compact notation; assumptions | 0.3 p |
| 4 Dataset | 4.1 corpora table (multi-turn, paired, scope); 4.2 chunking; 4.3 no train/test split since nothing is trained; labels fixed before running | 0.4 p |
| 5 Methodology | 5.1 **Fig 1 layered architecture**, **Fig 2 turn workflow**; 5.2 model: replaceable generator and MiniLM; 5.3 prompt, RAG, guardrails, CV; **Fig 3 peasant vs adviser**; 5.4 no generator training | 2 p |
| 6 Prototype | 6.1 Anima UI, **Fig 4** chat and inspect view; Skyrim connector; 6.2 local deployment, no public URL; 6.3 repo link, private, Table 2 structure | 0.75 p |
| 7 Setup | 7.1 environment; 7.2 metric formulas; 7.3 baselines (no-RAG; unscoped RAG) | 0.5 p |
| 8 Results | Table 3 scope study; Table 4 RAG vs no-RAG and retrieval; Table 5 sample replies, including failures; latency; Table 6 Skyrim receipts | 1.5 p |
| 9 Discussion | Why scoping and retrieval help, why unsupported detail survives, limitations; answer RQs | 0.4 p |
| 10 Ethics | Data sent to providers, private game assets, player-input logs, abusive input, AI use disclosure | 0.2 p |
| 11 Conclusion | Findings and next studies | 0.2 p |
| Acknowledgment, References, Appendix | Guide; IEEE refs in citation order; prompt excerpt, reproduction commands | outside page limit |

Figures are drawn in TikZ using Tectonic (already in `.tools/`), exported at 400 dpi and embedded. Tables and figures are numbered in order of appearance. Instruction text and the Formatting Guidelines section are removed.

## Header details

Authors: Mohan Chandra S S (1RVU23CSE282), Shreyas C (1RVU23CSE443), Nithish Gowda H N (1RVU23CSE317), Nithin S (1RVU23CSE316). Team 8. Guide: Prof. Manjul Krishna Gupta. Emails are omitted because they are not on record; flagged to the owner.

Proposed title: **A Model- and Game-Agnostic Orchestration Layer for Believable, Knowledge-Bounded NPC Dialogue**

## Outputs

- `research/cs3235_paper/CS3235_Team8_<Title>.docx` and `.pdf`
- `research/cs3235_paper/build_paper.py`, `figures/`, `experiments/`
- `docs/PROPOSAL.md`: the owner's proposal in structured form
