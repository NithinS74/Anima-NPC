# Final Research Paper Refinement — Anima NPC Dialogue System

You are working inside the existing Anima NPC research project repository.

Your task is to perform a comprehensive final revision of the existing IEEE research paper. The current paper is:

**Persona-Aware, Knowledge-Bounded NPC Dialogue Through Model-Agnostic LLM Orchestration**

The current five-page paper is a good foundation. Do not rewrite it from scratch, change its research direction, or unnecessarily expand its length.

The objective is to produce a polished, technically convincing IEEE conference paper that showcases the implemented system, its architecture, experimental results, and actual in-game demonstration.

## 1. First: Audit the entire existing paper

Inspect:
- Existing LaTeX source.
- Bibliography and citation usage.
- All architecture diagrams.
- Tables and experimental results.
- Existing experiment scripts and raw results.
- Skyrim connector implementation.
- Actual runtime logs and screenshots.
- Existing implementation documentation.

Verify that every numerical result and technical claim in the paper corresponds to the actual implementation or recorded experiment.

Identify and correct:
- Contradictory statements.
- Incorrect terminology.
- Inconsistent numerical values.
- Weak or unsupported claims.
- Missing technical explanations.
- Poorly structured paragraphs.
- Incorrect references.
- Repeated explanations.
- Incomplete figure descriptions.
- Formatting and IEEE layout issues.

Do not replace valid existing experimental results with invented ones.

## 2. Make the in-game implementation a major part of the Results section

This is the most important improvement.

The current paper discusses the architecture and controlled experiments but does not adequately showcase the actual Skyrim integration visually.

We need at least ONE clear, genuine screenshot of the system running inside Skyrim.

### Capture the screenshot

Run the actual game and use the existing AnimaConnector integration.

Capture a screenshot showing:
- Skyrim running normally.
- An NPC interaction or dialogue scene.
- The NPC/player interaction visible.
- The actual Anima-generated or authored response visible in the game's dialogue interface, wherever possible.

Prefer a screenshot that clearly communicates that this is an operating game-integrated NPC system rather than a standalone chatbot.

If necessary, investigate the previous black-region screenshot problem and fix the capture process.

Use actual screenshots from the running game. Do not generate illustrative screenshots, fabricate dialogue interfaces, composite fake game scenes, or use screenshots from the standalone web application as evidence of Skyrim integration.

Save the original screenshot in the research paper's figure directory.

### Insert the screenshot into the Results section

Add a dedicated subsection:

**In-Game Integration and Dialogue Delivery**

Discuss:
1. The native Skyrim connector integration.
2. How the game interaction reaches the Anima orchestration layer.
3. How NPC context and dialogue are obtained.
4. How the generated or authored response returns to the game.
5. The observed dialogue delivery and playback acknowledgement, where supported by actual test evidence.

Use a professional IEEE figure with a concise caption.

Suggested caption:

"Live Skyrim runtime demonstration of Anima's NPC dialogue integration, showing an in-game character interaction and the corresponding dialogue delivered through the native connector."

Adapt the caption to what the screenshot actually demonstrates.

The screenshot must be discussed in the Results text, not merely inserted without explanation.

## 3. Improve the Results and Discussion section

Reorganize the existing results into a logical progression:

### A. Retrieval Effectiveness
Retain the actual 24-query controlled retrieval evaluation.

Present:
- Precision@1.
- Precision@3.
- Recall@3.
- Mean Reciprocal Rank.

Explain what these measurements establish and why the controlled corpus is useful.

### B. RAG-Enabled Dialogue Comparison
Retain the seven completed matched pairs.

Present the existing comparison:
- RAG: 7/7 literal target mentions.
- No RAG: 1/7 literal target mentions.

Explain how retrieved evidence changed the generated responses, using the actual examples already documented.

Use precise terminology. Do not describe literal substring matching as semantic grounding or guaranteed factual correctness.

### C. In-Game Integration and Dialogue Delivery
Add the genuine Skyrim screenshot and explain the actual runtime integration.

Make this a meaningful part of the paper's implementation evaluation rather than a brief afterthought.

### D. Runtime Performance
Retain the measured retrieval performance:
- Query embedding.
- Vector query.
- Total retrieval latency.
- First-use latency.
- Knowledge synchronization time.

Explain that these are local retrieval measurements, not full end-to-end gameplay latency.

### E. Knowledge Update Demonstration
Show how the changed knowledge document was synchronized and how the updated fact became retrievable without a generator-training operation.

Connect this to the practical advantage of externally maintained knowledge.

## 4. Improve the technical explanation

Ensure the proposed architecture is clearly distinguished from existing techniques.

The paper should explain Anima's actual contribution:

- Persona-aware context appraisal.
- Deterministic engagement and routing.
- Source-bound knowledge retrieval.
- Context and evidence construction.
- Model-provider abstraction.
- Bounded response validation.
- Native game integration and dialogue delivery.

Explain how these components work together.

Avoid claiming that Anima invented RAG, persona prompting, dense retrieval, or provider abstraction.

Emphasize that the contribution is the integration of these mechanisms into a policy-controlled NPC dialogue architecture.

Explain the model-agnostic design accurately: the common provider contract enables compatible inference backends, while incompatible APIs require adapters.

## 5. Remove unnecessary implementation-status commentary

The paper should read as a research publication, not a development progress report.

Remove distracting statements about:
- Internal development interruptions.
- Rate-limit troubleshooting details that do not contribute to the research.
- Unnecessary descriptions of uncompleted development tasks.
- Internal debugging history.
- Repeated explanations of software-test counts.

Keep relevant methodological constraints and limitations that affect interpretation of the results.

Do not introduce unsupported claims or conceal material methodological weaknesses.

For runtime compatibility, document the actual tested configuration and the demonstrated integration. Do not claim that multiple runtime versions passed live tests unless corresponding test evidence exists. There is no need to make unverified older-runtime compatibility a central discussion in this paper.

## 6. Strengthen the academic writing

Review the entire manuscript for:
- Clear research motivation.
- Precise problem formulation.
- Explicit research contributions.
- Strong transitions between sections.
- Concise technical descriptions.
- Consistent terminology.
- Correct use of scientific language.
- Appropriate distinction between measurements and interpretations.

Avoid unnecessarily complicated language and excessive implementation details.

The paper should communicate a clear research story:

1. NPCs require persona consistency and bounded knowledge.
2. Conventional authored dialogue has limited flexibility.
3. LLMs offer flexible dialogue but require context and knowledge controls.
4. Anima introduces a policy-controlled orchestration architecture.
5. The architecture integrates retrieval, persona/context appraisal, provider abstraction and response validation.
6. Controlled experiments demonstrate retrieval behavior and preliminary RAG-enabled dialogue differences.
7. The Skyrim demonstration shows the system operating in an actual game environment.

## 7. Review figures and tables

Retain and refine the existing native TikZ diagrams.

Ensure:
- Figure 1 clearly explains the complete architecture.
- Figure 2 explains online dialogue execution.
- Figure 3 explains provider abstraction.
- The new Skyrim screenshot is visually clear.
- All figures are referenced in the body text.
- Captions explain the research significance rather than simply naming the image.
- Labels remain readable in IEEE two-column printing.
- No figure is stretched or distorted.

Do not replace the existing editable TikZ figures with generated raster diagrams.

## 8. Bibliography and citation audit

Verify each reference:
- Correct author names.
- Correct title.
- Correct publication venue.
- Correct year.
- Correct page numbers or article identifiers.
- Valid DOI or publication URL where applicable.

Add authoritative references for important implementation technologies where academically appropriate, including MiniLM, Chroma and ONNX Runtime.

Ensure every citation supports the statement it accompanies.

Do not invent references.

## 9. IEEE formatting and final PDF

Preserve the exact title.

Preserve the existing author information and author order.

Keep the manuscript within the five-to-six-page target, including references, unless the actual conference specifies a different limit.

Ensure:
- IEEE two-column layout.
- Correct margins and typography.
- No overlapping figures.
- No orphaned headings.
- No clipped text.
- No excessively small diagrams.
- Consistent mathematical notation.
- Correct table formatting.
- Proper figure numbering.
- References fit cleanly.

Prioritize research quality and readability over forcing an arbitrary page count.

## 10. Final deliverables

Produce:

1. Updated IEEE LaTeX manuscript.
2. Updated bibliography.
3. Original in-game screenshot.
4. Updated TikZ diagrams, retaining editable source.
5. Final compiled PDF.
6. Complete self-contained LaTeX source ZIP.
7. README with compilation instructions.

Compile the final PDF from the exact source included in the ZIP, then verify that the PDF and ZIP correspond to the same final revision.

### Final acceptance criteria

The paper is complete only when:

- The research contribution is clearly articulated.
- All experimental numbers are traceable to actual results.
- The Results section includes the real Skyrim in-game demonstration.
- The in-game screenshot is referenced and discussed in the paper.
- The RAG experiment is described with appropriate scientific precision.
- The retrieval and performance results are correctly presented.
- The bibliography and citations are verified.
- The IEEE layout is clean and professional.
- The final PDF compiles successfully.
- The source ZIP is complete and reproducible.

Do not merely provide a list of recommended edits. Implement the changes, compile the paper, inspect every page, and provide a concise final change report.