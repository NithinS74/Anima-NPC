I've reviewed the actual five-page PDF you uploaded. I agree with your criticism: the paper currently reads more like a software implementation report than an experimental research paper.

There are three fundamental things we need to fix, not just improve the formatting.

### 1. What is wrong with the current paper?

[Inbound Integration Endpoint Structure](https://images.openai.com/static-rsc-4/2U15lqIoef0let6EXHHdQSK8WwV4MtTa3nepKawq00yUGpCnFZgagp6RMYGRuy5YcSxwdHxuZa-7I8eJd5h3vMk046tkEiGRIc6huocVnwZZNSUoVwDDOf7nrk3EA5X1fWRH39oEFA6Rt2AIBMAFHdTbly187mBteVx3OSUkigY?purpose=inline)

Architecture diagrams are too basic

Pages 3–4 contain basic box-and-arrow diagrams. They lack the visual hierarchy, formal notation, component boundaries and presentation quality expected in a research paper.

[In Which Delga Sees Bujold the Unworthy Earn Her Name – Anna Plays Skyrim](https://images.openai.com/static-rsc-4/NwYV8i3AqO5ZQcvcMJcJgtK-kyrkIv1tOeUvSkI1I-LHnfLbauGupslF3WC8cpR8IMYzDpDRnNFe3z5Ukf2opi5oBTqRtVEy6jPNzw7TQjT8i1gyptXksLoOeT-anrxqK9nADtvMDm-X6SeAEtYfk1UuTEoUjkmecTN3WLWtBD0?purpose=inline)

No actual in-game evidence

There is no screenshot demonstrating the NPC interaction in the actual game. We should include one if the Skyrim integration is operational and we can capture a genuine interaction.

[AIPred: comprehensive prediction and analysis of non-histone acetylation via protein language model and interpretable machine learning | BMC Biology | Springer Nature Link](https://images.openai.com/static-rsc-4/GxWLDCfhr9a6OPaXQSE9XjGJemAaM4-y1-gi4CGLWbTvNmmybKSUl6Q8aaEQvbeIrBlnn9503AUmS_qsKyJov_FrYfDKV7mHinCIGEaroACuk6uENsjVjSN5Hwn8xCIdBHTkPnO3VYdlk5euMy656zyeW_heF3M4rbN9HIgI8XY?purpose=inline)

The results section is not scientific evaluation

Page 4 mainly reports 492 Python checks, seven Node checks and dependency verification. These establish software functionality, not conversational quality, retrieval effectiveness, persona consistency or performance.

The existing paper actually acknowledges that semantic grounding, persona consistency and real-time performance have not been experimentally evaluated. That's an important limitation, and we need to address it rather than simply rewrite the section.&#x20;

paper.pdf



## 2. The title should be changed to exactly this

## Persona-Aware, Knowledge-Bounded NPC Dialogue Through Model-Agnostic LLM Orchestration

Approved title

Use this exact title consistently in the PDF, LaTeX source and metadata.

I particularly like this title because it communicates three distinct aspects of the research:

- Persona-Aware: NPC responses must respect character identity, personality and interaction context.
- Knowledge-Bounded: Responses should be constrained by available and authorized game knowledge.
- Model-Agnostic LLM Orchestration: The orchestration architecture coordinates retrieval and inference without being tied to a single model provider.

## 3. What the new paper needs to demonstrate

We need to separate two kinds of evaluation.

| Engineering validation     | Scientific evaluation    |
| -------------------------- | ------------------------ |
| Python tests pass          | Retrieval relevance      |
| API works                  | Knowledge grounding      |
| Database integration works | Persona consistency      |
| Provider interface works   | Model-backend comparison |
| Response schema validates  | Response quality         |
| Error handling works       | Latency distribution     |

The 492 passing checks are still useful. We should retain them as a small implementation-validation subsection, but they must not dominate the Results and Discussion section.

The scientific evaluation needs actual measurements.

## 4. The new Codex prompt

This is a targeted revision prompt, not a replacement for the original task. Give it to Codex from the repository root, with the generated paper and its source files available.

The key instruction is that Codex must re-evaluate the research methodology, run real experiments, and rebuild the visual presentation, not just polish the existing PDF.

# CRITICAL REVISION TASK: Transform the Existing NPC Research Paper into a Scientifically Evaluated, Professionally Illustrated IEEE Conference Paper

You are now acting as a senior IEEE research-paper editor, experimental AI researcher, scientific evaluator, LaTeX specialist, and independent academic reviewer.

The previously generated paper is NOT acceptable as the final submission.

Your task is to critically revise the existing paper, improve its scientific contribution, conduct meaningful experiments using the actual project implementation, replace the weak diagrams with formal academic architecture diagrams, and produce a professionally formatted IEEE conference paper.

Do not simply rewrite sentences or improve the existing PDF's appearance.

The objective is to turn this into a credible research paper with:

- A clear research contribution.
- A technically accurate system architecture.
- Formal and professionally rendered diagrams.
- Actual in-game visual evidence where available.
- Quantitative scientific evaluation.
- Meaningful comparisons and discussion.
- Properly validated references.
- A concise IEEE conference presentation.

The repository implementation is the source of truth.

---

# 1. FINAL RESEARCH PAPER TITLE

Use this exact title everywhere:

"Persona-Aware, Knowledge-Bounded NPC Dialogue Through Model-Agnostic LLM Orchestration"

Do not modify, shorten, or substitute this title.

Preserve the existing author information and author order:

Mohan Chandra S S, Shreyas C, Nithish Gowda H N, Nithin S

RV University

Preserve the existing author identifiers and verify their ordering against the existing paper.

---

# 2. FIRST: AUDIT THE EXISTING PAPER AND ITS SOURCE FILES

Locate and inspect:

- The existing generated PDF.
- The current main.tex.
- All LaTeX section files.
- Existing bibliography.
- All existing figures.
- Figure source files.
- Research documentation.
- Existing literature survey.
- Project architecture documents.
- Actual source implementation.
- Experimental scripts and logs.
- Skyrim integration.
- NPC interaction interface.
- Existing screenshots and visual assets.

Do not discard useful existing technical explanations.

However, identify everything that needs to be corrected, replaced, expanded or removed.

Create:

research/REVISION_AUDIT.md

Include:

1. Weaknesses of the current paper.
2. Incorrect or unsupported research claims.
3. Weak architecture diagrams.
4. Missing in-game evidence.
5. Missing scientific experiments.
6. Existing results that are merely software tests.
7. Research contributions that can actually be defended.
8. Missing information needed for meaningful experiments.
9. Revised paper structure.

The existing paper uses the Anima orchestration prototype, PreviewRunner, MiniLM, Chroma, provider abstraction, deterministic engagement policies and a Skyrim adapter.

Verify every one of these details against the current repository before retaining them.

Do not assume that the implementation has not changed since the original paper was generated.

---

# 3. ESTABLISH THE RESEARCH CONTRIBUTION

The central research proposition is:

A persona-aware and knowledge-bounded NPC dialogue architecture can coordinate game context, retrieval-augmented knowledge access and interchangeable language-model backends through a dedicated orchestration layer.

The research should investigate how this architecture provides:

1. Persona consistency through authored character context.
2. Knowledge-bounded generation through scoped retrieval.
3. Separation of trusted game observations and untrusted player input.
4. Modular model invocation through a provider abstraction.
5. Controlled response acceptance and failure handling.
6. Adaptation of game-specific knowledge without requiring model retraining for every knowledge update.

Clearly distinguish:

- Established RAG techniques.
- Existing model-provider abstraction techniques.
- Our specific orchestration and integration contribution.
- Properties actually demonstrated through experiments.

Do not claim that RAG, model agnosticism or persona-conditioned dialogue is newly invented.

Do not claim that this architecture outperforms other systems unless experiments establish that conclusion.

---

# 4. REBUILD THE ARCHITECTURE FIGURES — HIGHEST VISUAL PRIORITY

The existing architecture figures are not acceptable.

They look like elementary flowcharts with rectangular boxes and basic arrows.

I want professionally typeset academic architecture diagrams that look like they belong in a serious IEEE conference publication.

## CRITICAL: USE NATIVE LATEX/TIKZ FOR THE DIAGRAMS

Use TikZ and appropriate LaTeX libraries to construct the main architecture figures.

The diagrams must:

- Be native vector diagrams rendered through LaTeX.
- Use consistent typography.
- Have professional component grouping.
- Use meaningful visual hierarchy.
- Distinguish data flows from control flows.
- Have consistent line weights and arrowheads.
- Use subtle, restrained academic colors.
- Use proper spacing and alignment.
- Remain readable at IEEE two-column scale.
- Have no overlapping labels or arrows.
- Use consistent terminology with the paper.

Do not generate generic architecture images using image-generation tools.

Do not use screenshots of flowcharts as architecture figures.

Do not use Mermaid screenshots as substitutes for the formal architecture diagrams.

TikZ source must be retained and editable.

## FIGURE 1 — OVERALL SYSTEM ARCHITECTURE

Create a detailed system architecture illustrating the actual implemented application.

Investigate and include the following conceptual boundaries where supported:

A. GAME INTERACTION LAYER

- Skyrim/game environment.
- Player interaction.
- NPC context.
- Game adapter.
- Input and response delivery.

B. CONTEXT AND PERSONA LAYER

- NPC persona definitions.
- Character identity.
- Relationship/social state.
- Trusted observations.
- Interaction snapshot.
- Context appraisal.

C. ORCHESTRATION LAYER\
This must be visually central and clearly highlighted.

Show:

- Engagement policy.
- Route selection.
- Request coordination.
- Retrieval coordination.
- Prompt/context construction.
- Provider invocation.
- Response validation.
- Bounded repair.
- Deadline and cancellation handling.

D. KNOWLEDGE RETRIEVAL LAYER

- Game knowledge sources.
- Document processing.
- Chunking.
- Embedding model.
- Vector database.
- Scoped retrieval.
- Evidence selection.

E. MODEL ABSTRACTION LAYER

- ModelProvider interface.
- Compatible provider implementations.
- Configurable inference endpoints.
- Model response contract.

F. RESPONSE DELIVERY

- Validated response.
- Adapter.
- NPC dialogue output.

Show the actual data and control relationships.

Do not place every component inside a single generic rectangle.

Use clearly grouped subgraphs or nested component boundaries.

Show the offline knowledge preparation path separately from online inference.

## FIGURE 2 — COMPLETE RAG AND ORCHESTRATION PIPELINE

Produce a formal pipeline diagram.

Show:

1. Player utterance.
2. Interaction snapshot acquisition.
3. Persona and trusted-context appraisal.
4. Engagement-policy decision.
5. Authored response / end interaction / generation branches.
6. Knowledge requirement assessment.
7. Source-bound retrieval.
8. Embedding and similarity search.
9. Evidence filtering.
10. Context and prompt construction.
11. Model-provider invocation.
12. Candidate response generation.
13. Structural and contextual validation.
14. Optional bounded repair.
15. Response acceptance or fallback.
16. Final NPC response delivery.

Represent:

- Error paths.
- Timeout paths.
- Stale response rejection.
- Authored-response bypasses.
- Retrieval bypasses where applicable.

The figure must communicate the actual execution sequence, not an idealized hypothetical architecture.

## FIGURE 3 — MODEL-AGNOSTIC PROVIDER ARCHITECTURE

Create a professional component-level diagram.

Illustrate how the orchestration layer communicates with the common ModelProvider interface.

Show actual compatible endpoints and providers from the implementation.

Distinguish:

- Common interface.
- Provider-specific configuration.
- HTTP transport.
- Provider response normalization.
- Model-specific differences.
- Offline test doubles.

Explain visually which parts of the orchestration architecture remain unchanged when a compatible backend is substituted.

Do not imply that every model API can be integrated without an adapter.

## FIGURE 4 — OFFLINE KNOWLEDGE INGESTION

If useful and supported, create a separate knowledge preparation architecture.

Show:

Game-specific documents\
→ Extraction\
→ Chunking\
→ Embedding generation\
→ Vector indexing\
→ Source/revision management\
→ Retrieval-ready knowledge.

Make it clear that knowledge updates occur independently of generator training.

## FIGURE DESIGN REQUIREMENTS

Use consistent colors across all figures.

Suggested restrained palette:

- Dark blue for orchestration.
- Light blue for context and persona.
- Muted teal for retrieval.
- Light grey for infrastructure.
- Muted orange for external model providers.
- White background.

Avoid bright gradients, shadows, 3D illustrations, decorative icons and excessive colors.

Every diagram must have an informative IEEE caption.

Store:

- TikZ source.
- Supporting LaTeX macros.
- Rendered output where required.

in:

research/ieee_paper/figures/\
research/ieee_paper/figure_sources/

Compile the figures and inspect the resulting PDF at actual two-column print size.

---

# 5. ADD GENUINE IN-GAME VISUAL EVIDENCE

The current paper has no actual screenshot demonstrating the NPC interaction inside the game.

This needs to be corrected if the Skyrim adapter can be executed.

Inspect the repository to identify how the Skyrim integration works.

Investigate:

- How the game is launched.
- How game context is acquired.
- How the NPC interaction is triggered.
- How generated dialogue is delivered.
- How screenshots can be captured.
- Whether the project has an existing gameplay demonstration.

If the game and integration can be run:

1. Launch the actual Skyrim environment using the existing project setup.
2. Trigger a genuine NPC interaction.
3. Use a meaningful player query related to the NPC's knowledge or persona.
4. Capture a real screenshot showing the in-game environment and NPC dialogue.
5. Capture additional screenshots only if they demonstrate a distinct useful capability.
6. Save the original unmodified captures.
7. Prepare appropriately cropped publication copies without altering the dialogue or creating misleading visual evidence.

The screenshot should demonstrate that the architecture connects to an actual game environment rather than existing only as a standalone web application or test harness.

### Recommended in-game figure

Figure 5: In-Game NPC Interaction Demonstration.

Prefer a composition that clearly shows:

- The actual game environment.
- NPC or character interaction.
- The player-facing dialogue.
- The generated response where visible.

If necessary, use two screenshots side by side:\
(a) In-game interaction context.\
(b) Resulting NPC dialogue.

Add a concise technical caption explaining what the interaction demonstrates.

Do not create a fake Skyrim screenshot.

Do not use unrelated stock images or generic fantasy artwork.

Do not paste a web-app screenshot and describe it as an in-game screenshot.

If the game cannot be launched or the interaction cannot be reproduced, document why and do not invent the image.

If genuine screenshots already exist in the repository, inspect them and reuse the best evidence.

Save final assets in:

research/ieee_paper/figures/

---

# 6. SCIENTIFIC RESULTS — REPLACE THE CURRENT RESULTS SECTION

THIS IS THE MOST IMPORTANT RESEARCH REVISION.

The current paper primarily reports:

- 492 Python checks.
- Seven Node checks.
- Dependency consistency.
- Mocked provider requests.
- Deterministic test embeddings.
- Chroma integration tests.

These are engineering validation results.

They are NOT sufficient scientific results.

Retain the 492 passing Python checks and other relevant software tests in a small subsection called:

"Implementation and Functional Verification"

Do not present test counts as the main experimental findings.

We need an actual experimental evaluation of the proposed NPC dialogue system.

First determine which experiments can be run with the existing implementation and available model endpoints.

Design experiments that test the central research claims.

## EXPERIMENT A — RETRIEVAL EFFECTIVENESS

Objective:

Determine whether the retrieval subsystem returns relevant game-specific knowledge for NPC interactions.

Method:

1. Identify the available game knowledge corpus.
2. Construct a representative query dataset based on the actual corpus.
3. Include different question types:
   - NPC identity.
   - Character background.
   - Locations.
   - Historical lore.
   - Factions.
   - Relationships.
   - Game-specific facts.
4. Establish relevant source passages for each query.
5. Use independent relevance labels rather than treating the retriever's own output as ground truth.
6. Execute retrieval across the dataset.

Measure where possible:

- Precision\@1.
- Precision\@3.
- Recall\@3.
- Mean Reciprocal Rank.
- Retrieval latency.

Use actual relevance judgments.

Do not calculate these metrics without a ground-truth relevance dataset.

Clearly report query count, corpus size, indexing configuration and retrieval settings.

## EXPERIMENT B — KNOWLEDGE GROUNDING

Objective:

Evaluate whether NPC responses remain consistent with the retrieved game knowledge.

Compare:

Condition 1: Generation without RAG.

Condition 2: Generation with RAG.

Keep the underlying model, persona instructions, question set and other relevant generation settings identical.

Use the same compatible model for both conditions initially.

Construct a held-out evaluation dataset containing:

- Answerable questions.
- Questions with incomplete knowledge.
- Questions whose answers are absent from the corpus.
- Questions attempting to introduce false game information.
- Questions involving restricted or unavailable knowledge.

Measure:

1. Claim-level support by retrieved evidence.
2. Unsupported factual claim rate.
3. Correct abstention when knowledge is unavailable.
4. Answer relevance.
5. Citation/evidence correctness, if supported by the response format.

Use human evaluation or a clearly documented independent assessment protocol for semantic support.

Do not confuse citation presence with semantic grounding.

Do not claim that schema validation proves factual correctness.

## EXPERIMENT C — PERSONA CONSISTENCY

Objective:

Investigate whether the architecture preserves NPC personality and character-specific behavior.

Create a set of questions that test:

- Character identity.
- Personality.
- Attitude.
- Knowledge boundaries.
- Social relationships.
- Role-specific behavior.
- Responses to inappropriate or irrelevant questions.

Evaluate the responses using a documented rubric.

Possible dimensions:

- Persona consistency.
- Character relevance.
- Contextual appropriateness.
- Knowledge consistency.

Use blinded human evaluation where practical.

Use at least two independent evaluators if available.

Report:

- Number of NPC personas.
- Number of prompts.
- Number of evaluated responses.
- Rating scale.
- Aggregated scores.
- Inter-rater agreement if calculated.

Do not manufacture human ratings.

If human evaluation cannot be completed, identify the evaluation as pending and do not present invented results.

## EXPERIMENT D — MODEL BACKEND COMPARISON

Objective:

Demonstrate the practical implications of model-agnostic orchestration.

Inspect the available provider configurations.

If at least two actual compatible models can be accessed, compare them under the same orchestration workflow.

Use:

- Identical questions.
- Identical persona context.
- Identical retrieval settings.
- Equivalent generation settings where possible.

Compare:

- Response relevance.
- Persona consistency.
- Grounding.
- Average response latency.
- Median response latency.
- P95 latency where sample size permits.
- Failure rate.
- Token usage where available.

Clearly distinguish model-specific quality differences from orchestration behavior.

Do not compare a real provider against the scripted OfflineProvider as if both were language models.

If only one actual backend is available, evaluate the provider abstraction structurally and report the limitation.

## EXPERIMENT E — KNOWLEDGE UPDATE WITHOUT MODEL RETRAINING

Objective:

Demonstrate the architectural benefit of external knowledge management.

Procedure:

1. Record the current knowledge index.
2. Query an existing game-specific fact.
3. Update or add a controlled knowledge document.
4. Re-index the changed knowledge.
5. Repeat the query.
6. Verify whether the updated fact is retrieved and reflected in the answer.
7. Verify that the generator model parameters remain unchanged.

Measure:

- Knowledge update time.
- Indexing time.
- Retrieval result before and after update.
- Response correctness before and after update.
- Whether model retraining was required.

Use a controlled example and record actual evidence.

Do not claim general cross-game transfer based on a single document update.

## EXPERIMENT F — LATENCY AND PERFORMANCE

Objective:

Measure the actual response pipeline.

Instrument separate stages:

- Context acquisition.
- Context appraisal.
- Embedding generation.
- Vector retrieval.
- Prompt construction.
- Model inference.
- Response validation.
- End-to-end response delivery.

Run repeated requests under documented conditions.

Report:

- Number of requests.
- Mean.
- Median.
- Standard deviation.
- P95 where justified.
- Warm and cold retrieval conditions where measurable.
- Model/backend configuration.
- Hardware and network conditions.

Do not report configured timeout values as actual measured latency.

Do not report the execution duration of the Python test suite as NPC response latency.

If an actual game is available, investigate whether end-to-end response delivery can be measured in-game.

---

# 7. EXPERIMENTAL INTEGRITY REQUIREMENTS

Do not fabricate any scientific result.

Do not invent:

- Retrieval scores.
- Grounding percentages.
- Persona ratings.
- Model comparisons.
- Response latency.
- Human evaluator feedback.
- Dataset sizes.
- Accuracy improvements.

Do not convert passing unit tests into scientific accuracy measurements.

Do not use arbitrary synthetic values to populate graphs.

For every reported measurement, maintain:

- Experiment identifier.
- Dataset/query source.
- Number of samples.
- Experimental configuration.
- Measurement method.
- Raw results.
- Aggregation method.
- Reproducible execution script.

Create:

research/ieee_paper/experiments/

Include:

- Evaluation scripts.
- Query datasets.
- Relevance labels.
- Raw result files.
- Analysis scripts.
- Experiment configuration.
- README documenting execution.

Create:

research/SCIENTIFIC_EVALUATION_REPORT.md

This must explain which experiments were completed, which were partially completed, and which remain pending.

If an experiment cannot be completed because an API key, paid endpoint, game installation, dataset or evaluator is unavailable, document the exact blocker.

You may create a reproducible evaluation harness for experiments that require additional execution, but never present unexecuted experiments as completed research.

---

# 8. REWRITE THE RESULTS AND DISCUSSION SECTION

The new Results and Discussion section must be organized around scientific questions, not software test categories.

Recommended structure:

VII. RESULTS AND DISCUSSION

A. Retrieval Effectiveness

Present retrieval measurements, relevance methodology and representative results.

B. Knowledge Grounding Evaluation

Compare RAG-enabled and RAG-disabled generation.

C. Persona Consistency Evaluation

Present the persona evaluation methodology and findings.

D. Model Backend Evaluation

Compare compatible real inference backends if available.

E. Knowledge Update Evaluation

Demonstrate whether the external knowledge index can be updated without retraining the generator.

F. Latency and Runtime Performance

Present measured response-stage and end-to-end latency.

G. Functional Verification and Implementation Evidence

Briefly summarize the existing 492 Python checks and relevant integration tests.

H. Limitations and Threats to Validity

Explain:

- Dataset limitations.
- Evaluation sample size.
- Human evaluation limitations.
- Model dependence.
- Retrieval errors.
- Semantic grounding limitations.
- Hardware and network dependence.
- Cross-game generalization limitations.

Do not force every subsection into the paper if there is no evidence to support it.

Prefer fewer completed, defensible experiments over many empty or fabricated experimental categories.

---

# 9. IMPROVE THE PAPER STRUCTURE

Use the following structure, adjusting subsections where necessary:

Abstract

Index Terms

I. Introduction

II. Related Work

III. Problem Formulation and Research Contributions

IV. Proposed System Architecture

V. System Methodology

VI. Implementation and Experimental Setup

VII. Results and Discussion

VIII. Conclusion and Future Work

References

Make the research questions explicit.

Suggested research questions:

RQ1: How effectively can scoped retrieval supply relevant game-specific knowledge to an NPC dialogue system?

RQ2: To what extent does retrieval-augmented generation improve evidence-grounded responses compared with generation without retrieval?

RQ3: How consistently does the orchestration architecture preserve NPC persona and knowledge boundaries?

RQ4: Can compatible language-model backends be substituted without modifying the core orchestration workflow?

RQ5: Can game-specific knowledge be updated independently of generator model retraining?

Only claim an RQ has been answered when there is actual experimental evidence.

---

# 10. ACADEMIC WRITING AND RESEARCH QUALITY

The paper must be formal, direct and concise.

Avoid:

- Marketing language.
- Generic AI-generated introductory statements.
- Excessive background explanations.
- Repeated descriptions of the architecture.
- Unsupported claims of novelty.
- Excessive technical implementation details unrelated to the research question.
- Long explanations of individual Python tests.

Focus on the research problem, methodology, implementation decisions, experiments and findings.

Preserve accurate technical details from the current paper.

Verify all references and citation details.

Do not invent literature or bibliographic information.

Clearly distinguish our implementation from existing research.

---

# 11. IEEE LATEX AND VISUAL FORMATTING

Use the IEEE conference document class:

\documentclass[conference]{IEEEtran}

Use native LaTeX for:

- Section formatting.
- Tables.
- Equations.
- Figure references.
- Bibliography.
- TikZ architecture diagrams.

Do not create diagrams in PowerPoint and paste low-resolution screenshots into the paper.

Use vector diagrams.

For genuine game screenshots, use high-quality image assets with appropriate cropping and figure placement.

Make sure:

- Figures remain readable in two-column layout.
- Captions are concise.
- Labels are consistent.
- References are correctly numbered.
- There are no broken references.
- There are no overlapping figures or text.
- No figures are pushed into awkward locations.
- The title and author block render properly.

---

# 12. STRICT SIX-PAGE LIMIT

Use six pages maximum, including references, as the working submission constraint.

Do not manipulate IEEE margins, font sizes or line spacing.

Prioritize content:

1. Research problem and contribution.
2. Architecture.
3. Methodology.
4. Scientific experiments and results.
5. Limitations.
6. References.

Use approximately:

- 0.5–0.75 page for the abstract and introduction opening.
- 0.5 page for related work.
- 0.5 page for problem formulation and contributions.
- 1–1.25 pages for architecture and methodology.
- 0.5 page for implementation and setup.
- 1.5–2 pages for scientific results and discussion.
- Remaining space for conclusion and references.

These are planning estimates, not fixed section quotas.

The scientific results must receive sufficient space.

Do not allow implementation test tables to consume the majority of the results section.

Compile and check the actual page count repeatedly.

If the paper exceeds six pages, condense explanations and optimize figures without removing essential scientific evidence.

---

# 13. INDEPENDENT REVIEW AFTER REVISION

After generating the revised paper, act as an independent IEEE reviewer.

Check:

1. Is the title accurately reflected in the paper?
2. Is persona awareness actually implemented and evaluated?
3. Is knowledge-bounded behavior technically explained and evaluated?
4. Is the orchestration contribution sufficiently differentiated from basic RAG?
5. Are the architecture diagrams formal and accurate?
6. Is actual in-game evidence included where available?
7. Are the results scientific rather than merely software-test statistics?
8. Are comparisons methodologically fair?
9. Are all measurements reproducible?
10. Are conclusions supported by evidence?
11. Are all citations genuine?
12. Is the document professionally formatted?
13. Is the six-page limit satisfied?

Create:

research/IEEE_FINAL_REVIEW\.md

Give honest scores for:

- Research contribution.
- Methodology.
- Experimental quality.
- Architecture clarity.
- Results and discussion.
- Related work.
- Academic writing.
- IEEE presentation.

Identify remaining weaknesses.

Resolve all critical issues before finalizing.

---

# 14. REQUIRED FINAL DELIVERABLES

Maintain the following structure:

research/\
│\
├── REVISION_AUDIT.md\
├── SCIENTIFIC_EVALUATION_REPORT.md\
├── IEEE_FINAL_REVIEW\.md\
│\
└── ieee_paper/\
│\
├── main.tex\
├── references.bib\
├── README.md\
├── paper.pdf\
├── paper_source.zip\
│\
├── figures/\
│   ├── system_architecture.pdf\
│   ├── rag_orchestration_pipeline.pdf\
│   ├── model_agnostic_architecture.pdf\
│   ├── knowledge_ingestion.pdf\
│   └── actual_skyrim_interaction.png\
│\
├── figure_sources/\
│   ├── system_architecture.tex\
│   ├── rag_orchestration_pipeline.tex\
│   ├── model_agnostic_architecture.tex\
│   └── knowledge_ingestion.tex\
│\
├── experiments/\
│   ├── datasets/\
│   ├── scripts/\
│   ├── raw_results/\
│   ├── analysis/\
│   └── README.md\
│\
└── sections/

Only include figures and experiments that actually exist. Do not create empty placeholders disguised as completed deliverables.

The ZIP must be self-contained and uploadable directly to Overleaf.

---

# 15. FINAL EXECUTION INSTRUCTIONS

This is a substantive research revision.

Do not simply produce another polished document based on the existing content.

First inspect the existing paper and repository.

Then rebuild the formal architecture figures, investigate actual in-game screenshot capture, implement and execute feasible scientific experiments, analyze their results, and rewrite the paper accordingly.

Keep the existing technical implementation intact unless an evaluation requires a minimal, isolated instrumentation change.

Prioritize scientific validity over impressive-looking numbers.

Prioritize formal diagrams over decorative illustrations.

Prioritize actual game evidence over stock images.

Prioritize reproducible experiments over Python test counts.

Prioritize a defensible research contribution over exaggerated novelty.

At the end, provide a concise execution report stating:

1. What was changed.
2. Which experiments were actually executed.
3. Their verified results.
4. Which experiments remain pending and why.
5. Which genuine in-game screenshots were captured.
6. Which diagrams were regenerated.
7. Final PDF page count.
8. Compilation status.
9. Independent review outcome.
10. Exact location of the final Overleaf-ready ZIP.

Begin with the audit and proceed through the complete revision without stopping after the first draft.

## 5. One important decision about the experiments

I would not insist that Codex complete all six experiments regardless of what the repository supports.

My preferred minimum scientific evaluation is:

Priority experiments

Recommended

1. RAG vs. No RAG

   This is probably the most important experiment. It directly tests whether retrieving game knowledge improves the responses.
2. Persona consistency and knowledge boundaries

   Tests whether NPCs maintain their identity and avoid claiming knowledge they do not possess.
3. Model backend comparison

   Demonstrates the practical value of the model-agnostic orchestration layer, provided multiple real backends are available.
4. Knowledge update without retraining

   Demonstrates one of the strongest architectural advantages of the proposed system.
5. Latency evaluation

   Establishes whether the architecture is practically suitable for interactive NPC conversations.

If Codex can complete these properly, we will have a substantially stronger paper.

## 6. What I want the final paper to look like

The final six-page paper should have this visual balance:

- Page 1: Title, abstract, introduction and research motivation.
- Page 2: Related work, research gap and contributions.
- Page 3: Large, formal system architecture diagram and architecture explanation.
- Page 4: RAG methodology, model abstraction and genuine in-game screenshot.
- Page 5: Scientific evaluation, quantitative tables and discussion.
- Page 6: Remaining results, limitations, conclusion and references.

This is a suggested layout, not a rigid page allocation.

One final recommendation: Make Codex produce the experimental results before it writes the final Results and Discussion section. Otherwise, it will probably repeat the same mistake: writing a convincing-sounding results section around whatever test logs it finds.

The paper needs to demonstrate that the proposed architecture works as a research contribution, not merely that the software runs.