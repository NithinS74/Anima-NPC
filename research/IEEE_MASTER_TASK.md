# MASTER TASK: Develop, Write, Validate and Review an IEEE Research Paper for the Model-Agnostic RAG-Based NPC Interaction System

## 1. ROLE AND EXPECTATIONS

Act as a combination of:

1. Senior academic researcher specializing in Artificial Intelligence, NLP, Retrieval-Augmented Generation (RAG), LLM systems and conversational agents.
2. Research paper author experienced in IEEE conference publications.
3. Software and system architect capable of reverse-engineering an existing implementation.
4. Experimental research analyst responsible for validating technical claims and results.
5. Independent IEEE research-paper reviewer responsible for identifying weaknesses, unsupported claims, methodological errors and presentation problems.

Your task is to create a complete, technically accurate and professionally written IEEE-format research paper based on the project implementation and documentation available in this repository.

This is an academic research submission, not a project report, product description or promotional document.

Do not start writing the paper immediately. First understand the actual project, inspect the implementation, identify its research contribution, and establish which claims can be supported by evidence.

Work autonomously through the stages below. Do not stop after producing an outline or asking me to write individual sections.

---

## 2. PROJECT CONTEXT AND CENTRAL RESEARCH DIRECTION

The project concerns an intelligent conversational NPC interaction system for video games.

The central research contribution we want to investigate and communicate is the use of a modular, model-agnostic orchestration layer combined with Retrieval-Augmented Generation (RAG) to enable contextually grounded NPC conversations.

The fundamental research motivation is:

Training or fine-tuning a separate language model for every game is expensive in terms of computational resources, training data, maintenance and deployment.

Different games have different:
- Worlds and environments.
- Characters and personalities.
- Lore and historical information.
- Quests and objectives.
- Items, locations and relationships.
- Dialogue styles and contextual requirements.

A conventional approach might require training or fine-tuning a separate model for every game or game domain.

We want to investigate a different approach.

The proposed architecture uses an orchestration layer that manages the interaction between game-specific knowledge, retrieval infrastructure, language models and the NPC interaction pipeline.

RAG allows relevant game-specific information to be retrieved and supplied as contextual information during inference rather than requiring the underlying language model to be retrained whenever the knowledge domain changes.

The orchestration layer should be presented as the central architectural contribution.

### Important research positioning

The paper must investigate and clearly explain:

- Why model-specific training and fine-tuning can be expensive and difficult to scale.
- Why RAG is appropriate for grounding NPC responses in domain-specific knowledge.
- How the orchestration layer separates game-specific knowledge from the underlying language model.
- How model abstraction enables different compatible models to be integrated.
- How retrieval, context construction, prompt management, model invocation and response processing work together.
- How the architecture can potentially be adapted to different games and model backends.
- What limitations remain, including retrieval quality, context-window constraints, hallucinations, inference latency and dependence on model capabilities.

Do not claim that RAG eliminates model training in every situation. Explain the specific advantages and trade-offs accurately.

Do not claim that the architecture is universally model-agnostic unless the implementation demonstrates a genuine abstraction or adapter mechanism.

The actual repository implementation is the authority on what has been built.

---

## 3. PHASE 1 — COMPLETE REPOSITORY AND PROJECT AUDIT

Before writing anything, inspect the repository comprehensively.

Search through:
- README files.
- Project documentation.
- Architecture documents.
- Implementation plans.
- Research and literature-survey documents.
- Source code.
- Backend services.
- Frontend integration.
- API routes.
- RAG implementation.
- Embedding generation.
- Vector database configuration.
- Retrieval mechanisms.
- LLM provider integrations.
- Prompt construction.
- Context management.
- NPC interaction logic.
- Configuration and environment files.
- Existing experimental results.
- Evaluation scripts.
- Test cases and execution logs.
- Existing diagrams and screenshots.

Do not restrict yourself to files with obvious names.

Follow the actual code execution path and understand how a request moves through the system.

Specifically establish:

1. What happens when a player initiates an interaction.
2. How the player's input is received and processed.
3. How relevant game information is retrieved.
4. How retrieved information is ranked or selected, if applicable.
5. How the context and prompt are constructed.
6. How the orchestration layer selects and invokes a model.
7. How the model response is processed.
8. How the NPC response reaches the user or game interface.
9. How different models or providers can be configured.
10. How game-specific knowledge can be changed or extended.

Identify the actual technologies, frameworks, models, databases, libraries and interfaces.

Do not assume that a feature exists simply because it appears in an implementation plan.

### Deliverable

Create:

`research/PROJECT_TECHNICAL_AUDIT.md`

Include:
- Actual architecture.
- Component responsibilities.
- End-to-end request lifecycle.
- Technologies and versions where verifiable.
- Actual implementation status.
- Relevant source-code file paths.
- Available experimental results.
- Missing experimental evidence.
- Potential research contributions.
- Technical limitations.
- Inconsistencies requiring resolution.

Clearly distinguish implemented features, partially implemented features, planned features and proposed future work.

---

## 4. PHASE 2 — ESTABLISH THE RESEARCH CONTRIBUTION

Based on the audit, formulate a defensible research problem.

Investigate these questions:

1. What is the limitation of conventional scripted NPC conversations?
2. What limitations arise when game-specific conversational agents depend on separately fine-tuned models?
3. What problems arise from directly connecting an LLM to a game without an intermediate orchestration layer?
4. How does RAG address the problem of domain-specific knowledge grounding?
5. What architectural advantages does separating retrieval, orchestration and model inference provide?
6. What makes the proposed architecture different from a basic RAG chatbot?
7. What evidence supports the claimed advantages?

Identify a precise research gap rather than making generic statements about AI in gaming.

### Expected contribution framing

Investigate whether the following contributions can be substantiated:

- A modular orchestration architecture for coordinating NPC dialogue generation.
- Separation of game-specific knowledge retrieval from language-model inference.
- A model-provider abstraction mechanism supporting interchangeable LLM backends.
- Context-grounded NPC response generation using RAG.
- An extensible architecture that reduces dependence on model-specific fine-tuning for domain adaptation.

Only retain contributions demonstrated by the implementation or supported by the experiments.

Do not invent novelty. If an architectural idea already exists in prior research, distinguish our particular implementation or integration contribution from the established technique.

---

## 5. PHASE 3 — LITERATURE REVIEW AND REFERENCE VALIDATION

Use the existing literature survey and research documents in the repository as the primary starting point.

Identify relevant literature covering:

- Retrieval-Augmented Generation.
- Dense retrieval and vector databases.
- Knowledge-grounded dialogue generation.
- Conversational agents in games.
- LLM-based NPC interaction.
- LLM orchestration and model abstraction.
- Prompt engineering and context management.
- Domain adaptation and fine-tuning.
- Evaluation of RAG systems.
- Contextual NPC dialogue and interactive storytelling.

For every important research claim:

1. Identify a credible supporting publication.
2. Verify the publication title.
3. Verify authors.
4. Verify publication year.
5. Verify conference, journal or publisher.
6. Verify DOI or official publication URL where available.
7. Confirm that the cited work actually supports the statement.
8. Include a properly formatted IEEE reference.

Prioritize peer-reviewed IEEE, ACM, ACL, NeurIPS, ICLR and other reputable research publications.

Use primary research publications rather than relying on blogs or vendor marketing.

Do not fabricate references, DOIs, authors or publication details.

Do not cite papers merely because their titles appear relevant.

Prepare a concise literature comparison table internally before writing the related-work section.

The related-work section must explain:
- What existing approaches accomplish.
- What limitations remain.
- How our research differs.
- Why our architecture is worth investigating.

Avoid turning this section into a long list of paper summaries.

---

## 6. PHASE 4 — DESIGN AND GENERATE THE ARCHITECTURE FIGURES

Architecture clarity is one of the highest priorities.

Inspect the source code and create figures based on the actual implementation.

Do not use generic architecture images from the internet.

Create the following figures wherever supported by the actual system.

### Figure 1: Overall Proposed System Architecture

Create a professional IEEE-quality system architecture diagram.

It should clearly communicate the relationships between:

- Player / game interface.
- NPC interaction interface.
- Input processing.
- Orchestration layer.
- Game-specific knowledge sources.
- Retrieval subsystem.
- Embedding model.
- Vector database.
- Context construction and prompt management.
- Model abstraction interface.
- Compatible LLM providers.
- Response processing.
- Final NPC response.

Only include components that exist in the implementation. If an architectural component is proposed rather than implemented, label it appropriately.

The orchestration layer should be visually central.

### Figure 2: End-to-End RAG and Orchestration Pipeline

Create a detailed workflow showing:

Player Input
→ Input Processing
→ Query / Context Preparation
→ Embedding Generation (if implemented)
→ Vector Retrieval
→ Relevant Context Selection
→ Context and Prompt Construction
→ Model Selection / Provider Adapter
→ LLM Inference
→ Response Processing
→ NPC Response Delivery.

Represent actual conditional paths, error handling and optional stages if present.

Clearly distinguish offline knowledge ingestion/indexing from online inference.

### Figure 3: Model-Agnostic Architecture

Explain how the model abstraction interface separates the orchestration logic from individual language-model implementations.

Show different compatible local or remote model providers only where supported.

Demonstrate which components remain unchanged when switching the model and which configurations or adapters must change.

### Optional Figure 4: Knowledge Ingestion and Indexing

If the repository contains a substantial knowledge-ingestion pipeline, illustrate:

Game Knowledge Sources
→ Document Processing
→ Chunking
→ Embedding Generation
→ Vector Storage
→ Retrieval Availability.

Do not force this figure into the paper if it is already adequately represented elsewhere.

### Figure quality requirements

- Use professional academic styling.
- White background.
- Consistent typography.
- Minimal colors.
- Clear arrows and labels.
- Logical grouping.
- No overlapping elements.
- No unnecessary decoration.
- Legible when reduced to IEEE two-column width.
- Export high-quality PDF/SVG or sufficiently high-resolution PNG.
- Prefer vector graphics.

Use TikZ, Mermaid with SVG export, Graphviz or another reproducible diagramming method.

Create editable source files for the diagrams.

Store all paper figures in:

`research/ieee_paper/figures/`

Ensure all figures are referenced correctly in the LaTeX source with proper captions and labels.

Do not use screenshots as substitutes for architectural diagrams.

---

## 7. PHASE 5 — EXPERIMENTAL VALIDATION AND RESULTS

This is critical.

Inspect all available experiment outputs, logs, benchmarks, evaluation scripts and test results.

Identify what can actually be reported.

Potential evaluation dimensions include:

### A. Retrieval Evaluation
- Retrieval relevance.
- Precision@K.
- Recall@K.
- Mean Reciprocal Rank (MRR).
- Context relevance.
- Retrieval latency.

Use only metrics for which the necessary ground truth or evaluation methodology exists.

### B. Response Quality
- Relevance to player input.
- Consistency with retrieved game knowledge.
- Contextual grounding.
- NPC personality consistency.
- Hallucination or unsupported-response rate.

Where human evaluation is used, document the evaluation protocol and number of evaluators.

### C. Performance
- Average inference latency.
- End-to-end response latency.
- Retrieval latency.
- Model inference latency.
- Resource consumption, where measured.

Report mean, median, standard deviation and sample count where data permits.

### D. Model-Agnostic Evaluation

If multiple model providers or backends are implemented and available, investigate whether the same orchestration workflow can operate with different models.

Compare:
- Integration requirements.
- Response quality.
- Latency.
- Retrieval-context compatibility.
- Configuration changes.

### E. Adaptability

Investigate whether game-specific knowledge can be changed without retraining the underlying model.

Do not claim that this demonstrates universal cross-game generalization unless actual cross-game experiments have been conducted.

### Experimental integrity requirements

Never fabricate experimental results.

Never invent latency measurements, benchmark results, evaluation scores, hardware specifications or dataset sizes.

Never report an unexecuted experiment as completed.

If a metric cannot be calculated from available evidence, mark it as unavailable.

If additional experiments would materially strengthen the paper, identify the minimum practical experiments that can be executed using the current codebase.

If possible, execute relevant existing tests and evaluation scripts without changing the core project implementation.

Create:

`research/EXPERIMENTAL_EVIDENCE.md`

This document must map every reported numerical result to its source, measurement method and evidence.

---

## 8. PHASE 6 — WRITE THE IEEE RESEARCH PAPER

Create a complete LaTeX research paper using the official IEEE conference format.

Use:

`\documentclass[conference]{IEEEtran}`

Use a clean IEEE two-column layout.

### Recommended title direction

Investigate a title along the lines of:

"An Orchestration-Driven, Model-Agnostic Retrieval-Augmented Generation Framework for Context-Aware NPC Interaction in Games"

You may improve the title if the technical audit identifies a more accurate research contribution.

### Required paper sections

I. INTRODUCTION

Explain the research problem, motivation, limitations of existing NPC dialogue systems, research objectives and contributions.

II. RELATED WORK

Present a focused discussion of relevant research, comparing existing approaches and identifying the research gap.

III. PROBLEM FORMULATION AND RESEARCH CONTRIBUTIONS

Define the problem and clearly state the proposed contributions.

IV. PROPOSED SYSTEM ARCHITECTURE

Explain the overall architecture, orchestration layer, RAG subsystem, model abstraction and system interactions.

Include Figure 1.

V. SYSTEM METHODOLOGY

Explain:
- Knowledge ingestion and preparation.
- Embedding and indexing.
- Query processing.
- Retrieval and context selection.
- Prompt construction.
- Model invocation.
- Response processing.
- Model switching and abstraction.

Include Figure 2 and Figure 3 where appropriate.

VI. IMPLEMENTATION AND EXPERIMENTAL SETUP

Explain the actual implementation, technology stack, models, datasets, configuration and experimental environment.

VII. RESULTS AND DISCUSSION

Present verified experimental results using concise tables and figures.

Discuss the significance of the results, trade-offs, limitations and implications.

VIII. CONCLUSION AND FUTURE WORK

Summarize the actual contribution, findings and limitations.

Discuss reasonable future work without presenting planned features as completed work.

### Abstract requirements

The abstract should be approximately 150–200 words.

It must include:
- The research problem.
- The proposed architecture.
- The central technical contribution.
- The methodology.
- Important verified experimental findings.
- The significance of the work.

Do not include references in the abstract.

### Keywords

Use approximately 5–7 focused technical keywords.

### Writing style

Write in formal academic English.

The paper should be:
- Precise.
- Concise.
- Technically detailed.
- Objective.
- Naturally written.
- Consistent in terminology.
- Free of marketing language.
- Free of unnecessary repetition.

Avoid excessive adjectives and generic AI-generated phrases.

Do not write sentences such as:
"This revolutionary architecture transforms the gaming industry."

Instead, describe what was implemented, how it works and what evidence demonstrates its performance.

Do not deliberately manipulate wording to evade AI-detection systems. Focus on genuine originality, accurate attribution, independent technical analysis and properly cited sources. The authors must review and take responsibility for the final submission.

### Equations

Include mathematical formulations only where they improve the technical explanation.

Potential equations include:
- Dense retrieval similarity.
- Top-K document retrieval.
- RAG-conditioned response generation.
- Evaluation metrics.

Ensure every equation is correctly defined and relevant to the implementation.

Do not add equations merely to make the paper look more scientific.

### Tables

Use concise IEEE-quality tables for:
- Literature comparison.
- System components and responsibilities.
- Experimental configuration.
- Quantitative evaluation.
- Model comparison, if evidence supports it.

Avoid excessive tables.

---

## 9. PHASE 7 — STRICT IEEE FORMATTING AND PAGE MANAGEMENT

The paper is being prepared for an academic assignment requiring IEEE formatting.

Use six pages as the maximum working limit unless the assignment or selected conference specifies otherwise.

This is a project-specific target, not an assumption that every IEEE conference has the same page limit.

IMPORTANT:
- Six pages maximum, including references.
- Target approximately 5–6 pages.
- IEEE two-column conference layout.
- Correct font, margins and spacing from IEEEtran.
- No manual margin manipulation.
- No font-size reduction to artificially squeeze content.
- No excessive negative spacing.
- No unnecessary appendices.
- No oversized figures.
- No empty sections.
- No redundant explanations.

Manage the paper length by editing content, removing repetition and optimizing figures and tables.

If the paper exceeds six pages:
1. Identify the sections consuming the most space.
2. Remove redundant explanations.
3. Condense literature discussion.
4. Simplify tables.
5. Optimize figures.
6. Preserve methodological clarity and important experimental results.

Never remove critical research evidence simply to meet the page limit.

After compilation, programmatically verify the actual PDF page count.

The six-page limit must include the references.

---

## 10. PHASE 8 — INDEPENDENT RESEARCH-PAPER REVIEW

Once the initial paper has been written, stop acting as its author.

Switch roles completely.

Act as an independent IEEE conference reviewer who has no attachment to the project.

Review the paper critically.

### Technical correctness

Check:
- Whether the architecture matches the actual implementation.
- Whether RAG is explained correctly.
- Whether model agnosticism is technically justified.
- Whether the orchestration layer is sufficiently explained.
- Whether all data flows are correct.
- Whether the methodology is reproducible.
- Whether mathematical formulations are valid.
- Whether the results support the conclusions.

### Research quality

Check:
- Is the research problem sufficiently specific?
- Is the research gap genuine?
- Are the contributions clearly identifiable?
- Is the proposed approach differentiated from basic RAG implementations?
- Is the literature review relevant and adequately cited?
- Are the experiments sufficient?
- Are the limitations acknowledged?
- Are conclusions proportional to the available evidence?

### IEEE quality

Check:
- Correct conference formatting.
- Correct section hierarchy.
- Figure readability.
- Table readability.
- Correct citation numbering.
- Bibliographic consistency.
- No undefined abbreviations.
- No broken figure or table references.
- No overflow or layout problems.
- Maximum six pages.

### Language and originality

Check:
- Grammar.
- Academic tone.
- Clarity.
- Repetition.
- Unsupported claims.
- Unattributed paraphrasing.
- Accidental plagiarism.
- Incorrect or missing citations.

Do not promise that the paper will pass a plagiarism checker or AI detector. The actual institutional plagiarism report must be generated separately.

### Reviewer scorecard

Create an internal assessment with scores out of 10 for:

1. Research problem and motivation.
2. Novelty and contribution.
3. Related work.
4. Technical methodology.
5. Architecture clarity.
6. Experimental validation.
7. Results and discussion.
8. IEEE formatting.
9. Academic writing.
10. Overall research quality.

For every category, explain weaknesses and required corrections.

Create:

`research/IEEE_REVIEW_REPORT.md`

Include:
- Overall assessment.
- Major concerns.
- Minor concerns.
- Unsupported claims.
- Missing evidence.
- Required revisions.
- Final reviewer recommendation.

Do not automatically give high scores. Be critical.

---

## 11. PHASE 9 — REVISE AND FINALIZE

After the independent review:

1. Fix all major technical issues.
2. Fix citation and reference problems.
3. Correct architecture diagrams.
4. Improve weak explanations.
5. Remove unsupported claims.
6. Improve experimental discussion.
7. Resolve all LaTeX warnings where practical.
8. Recompile the paper.
9. Recheck page count.
10. Review the final PDF visually.

Repeat the review until there are no unresolved critical issues.

Do not hide unresolved problems. If an issue cannot be fixed without new experimental evidence or author input, clearly document it.

---

## 12. REQUIRED DELIVERABLES

Create the following directory structure:

research/
│
├── PROJECT_TECHNICAL_AUDIT.md
├── EXPERIMENTAL_EVIDENCE.md
├── IEEE_REVIEW_REPORT.md
│
└── ieee_paper/
    │
    ├── main.tex
    ├── references.bib
    ├── README.md
    │
    ├── figures/
    │   ├── system_architecture.svg
    │   ├── rag_orchestration_pipeline.svg
    │   ├── model_agnostic_architecture.svg
    │   └── [additional figures if justified]
    │
    ├── figure_sources/
    │   └── [editable diagram source files]
    │
    ├── sections/
    │   └── [optional section files if using modular LaTeX]
    │
    ├── paper.pdf
    │
    └── paper_source.zip

The ZIP must contain everything needed to recreate the paper independently, including the LaTeX source, bibliography, figures and any required assets.

The README must explain:
- How to compile locally.
- Required LaTeX packages.
- How to upload the ZIP into Overleaf.
- How to regenerate the figures.
- Where to edit author information.

Do not commit secrets, API keys, environment variables or private credentials into the paper package.

---

## 13. FINAL ACCEPTANCE CHECKLIST

Before considering this task complete, verify:

[ ] The paper describes the actual project rather than an imagined architecture.

[ ] The orchestration layer is clearly identified as the central architectural contribution.

[ ] RAG is explained in sufficient technical depth.

[ ] Model agnosticism is demonstrated and not merely claimed.

[ ] The research gap is supported by literature.

[ ] All references are genuine and verified.

[ ] All technical claims have supporting evidence.

[ ] All numerical results have traceable sources.

[ ] No fabricated experiments or performance metrics exist.

[ ] Architecture diagrams match the implementation.

[ ] Figures are readable in IEEE two-column formatting.

[ ] All sections are logically connected.

[ ] The conclusion accurately reflects the experimental findings.

[ ] The document uses the IEEE conference template.

[ ] The final PDF is no longer than six pages.

[ ] All references, figures and tables render correctly.

[ ] The paper compiles successfully.

[ ] The independent reviewer report has been produced.

[ ] Major reviewer concerns have been resolved or explicitly documented.

[ ] The final source ZIP can be uploaded directly into Overleaf.

---

## 14. EXECUTION INSTRUCTIONS

Start by inspecting the entire repository and identifying all relevant project documentation, source files and experimental evidence.

Do not make unnecessary changes to the actual application code. This task is primarily concerned with research analysis, documentation, figures and paper generation.

Work in clearly separated phases, maintaining the audit and evidence documents as you progress.

If a crucial piece of information is missing, use a clearly marked placeholder or document the limitation instead of inventing information.

Do not stop at the first LaTeX compilation.

The expected outcome is a complete, technically defensible, professionally written IEEE research paper with accurate architecture diagrams, verified citations, traceable results, an independent review and a reproducible Overleaf-ready source package.

Prioritize research integrity, technical correctness, architectural clarity and concise academic communication over page-filling or decorative presentation.

Begin with Phase 1 now and continue through all phases until the deliverables are complete.