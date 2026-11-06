"""Build the CS3235 paper from the course template.

Run from the repository root:
    .venv/Scripts/python.exe research/cs3235_paper/build_paper.py
Citations written as {c:key} are numbered by first appearance, as IEEE style requires.
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TITLE = "Towards a Model- and Game-Agnostic Orchestration Layer for Believable NPC Dialogue"
OUTPUT = HERE / "CS3235_Team8_Towards_Model_and_Game_Agnostic_NPC_Orchestration.docx"
STUDY = json.loads((HERE / "experiments/results/orchestration.json").read_text(encoding="utf-8"))
LIVE = {row["test"]: row for row in json.loads((HERE / "experiments/results/proposal_live.json").read_text(encoding="utf-8"))["rows"]}
FOLLOW = {row["test"]: row for row in json.loads((HERE / "experiments/results/proposal_live_followup.json").read_text(encoding="utf-8"))["rows"]}
HEARSAY = json.loads((HERE / "experiments/results/proposal_live_hearsay.json").read_text(encoding="utf-8"))["rows"][-1]
STUDY_CASES = sorted({row["case"] for row in STUDY["behaviour"]["rows"]})
TEST_COUNT = 880

REFERENCES = {
    "gallotta": 'R. Gallotta et al., "Large language models and games: A survey and roadmap," IEEE Trans. Games, 2024, doi: 10.1109/TG.2024.3461510.',
    "mantella": 'Art from the Machine, "Mantella: Skyrim and Fallout 4 AI mod." GitHub. Accessed: Nov. 5, 2026. [Online]. Available: https://github.com/art-from-the-machine/Mantella',
    "shao": 'Y. Shao, L. Li, J. Dai, and X. Qiu, "Character-LLM: A trainable agent for role-playing," in Proc. EMNLP, 2023, pp. 13153–13187.',
    "wang": 'N. Wang et al., "RoleLLM: Benchmarking, eliciting, and enhancing role-playing abilities of large language models," in Findings ACL, 2024, pp. 14743–14777, doi: 10.18653/v1/2024.findings-acl.878.',
    "hu": 'E. J. Hu et al., "LoRA: Low-rank adaptation of large language models," in Proc. ICLR, 2022.',
    "ahn": 'J. Ahn et al., "TimeChara: Evaluating point-in-time character hallucination of role-playing large language models," in Findings ACL, 2024, pp. 3291–3325, doi: 10.18653/v1/2024.findings-acl.197.',
    "sadeq": 'N. Sadeq, Z. Xie, B. Kang, P. Lamba, X. Gao, and J. McAuley, "Mitigating hallucination in fictional character role-play," in Findings EMNLP, 2024, pp. 14467–14479, doi: 10.18653/v1/2024.findings-emnlp.846.',
    "lewis": 'P. Lewis et al., "Retrieval-augmented generation for knowledge-intensive NLP tasks," in Proc. NeurIPS, vol. 33, 2020, pp. 9459–9474.',
    "karpukhin": 'V. Karpukhin et al., "Dense passage retrieval for open-domain question answering," in Proc. EMNLP, 2020, pp. 6769–6781, doi: 10.18653/v1/2020.emnlp-main.550.',
    "es": 'S. Es, J. James, L. Espinosa Anke, and S. Schockaert, "RAGAs: Automated evaluation of retrieval augmented generation," in Proc. EACL Syst. Demonstrations, 2024, pp. 150–158, doi: 10.18653/v1/2024.eacl-demo.16.',
    "liu": 'N. F. Liu et al., "Lost in the middle: How language models use long contexts," Trans. Assoc. Comput. Linguistics, vol. 12, pp. 157–173, 2024, doi: 10.1162/tacl_a_00638.',
    "park": 'J. S. Park, J. C. O\'Brien, C. J. Cai, M. R. Morris, P. Liang, and M. S. Bernstein, "Generative agents: Interactive simulacra of human behavior," in Proc. ACM UIST, 2023, pp. 1–22, doi: 10.1145/3586183.3606763.',
    "callison": 'C. Callison-Burch, G. S. Tomar, L. J. Martin, D. Ippolito, S. Bailis, and D. Reitter, "Dungeons and Dragons as a dialog challenge for artificial intelligence," in Proc. EMNLP, 2022, pp. 9379–9393, doi: 10.18653/v1/2022.emnlp-main.637.',
    "zhang": 'S. Zhang, E. Dinan, J. Urbanek, A. Szlam, D. Kiela, and J. Weston, "Personalizing dialogue agents: I have a dog, do you have pets too?" in Proc. ACL, 2018, pp. 2204–2213, doi: 10.18653/v1/P18-1205.',
    "minilm": 'W. Wang, F. Wei, L. Dong, H. Bao, N. Yang, and M. Zhou, "MiniLM: Deep self-attention distillation for task-agnostic compression of pre-trained transformers," in Proc. NeurIPS, vol. 33, 2020, pp. 5776–5788.',
    "card": 'Sentence Transformers, "all-MiniLM-L6-v2 model card." Hugging Face. Accessed: Nov. 3, 2026. [Online]. Available: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2',
    "chroma": 'Chroma, "Chroma documentation: Introduction." Accessed: Nov. 3, 2026. [Online]. Available: https://docs.trychroma.com/docs/overview/introduction',
    "onnx": 'ONNX Runtime developers, "ONNX Runtime documentation." Accessed: Nov. 3, 2026. [Online]. Available: https://onnxruntime.ai/docs/',
}
cited: list[str] = []
APPENDIX_MODELS = [('Language model', "`gemini-3.5-flash-lite`, through Gemini's OpenAI-compatible endpoint"), ('Knowledge search', '`all-MiniLM-L6-v2` (384 dimensions, ONNX, CPU) with Chroma'), ('Speech to text', '`faster-whisper` `base.en` (CPU, INT8)'), ('Text to speech', 'Piper, with a Skyrim voice model per voice type (16 kHz)'), ('Vision (optional)', '`qwen2.5vl:3b` through Ollama, optional YOLO (`yolo26n`)'), ('Lip movement', 'Audio-volume mouth envelope')]
APPENDIX_FIGURES = [
    ("inspect-context.png", 5.6, "Figure A1: Anima Inspect context view, showing what influenced a reply"),
    ("game-controls.jpg", 6.0, "Figure A2: Anima conversation controls on a Whiterun Guard in Skyrim, showing the in-game menu"),

]


def cite(match: re.Match) -> str:
    numbers = []
    for key in match.group(1).split(","):
        if key not in REFERENCES:
            raise KeyError(key)
        if key not in cited:
            cited.append(key)
        numbers.append(f"[{cited.index(key) + 1}]")
    return ", ".join(numbers)


TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*|~.+?~)")


def add_runs(paragraph, text, *, size=None, bold=None, italic=None):
    text = re.sub(r"\{c:([a-z,]+)\}", cite, text)
    for part in TOKEN.split(text):
        if not part:
            continue
        run_bold, run_italic, sub = bold, italic, False
        if part.startswith("**"):
            part, run_bold = part[2:-2], True
        elif part.startswith("*"):
            part, run_italic = part[1:-1], True
        elif part.startswith("~"):
            part, sub = part[1:-1], True
        run = paragraph.add_run(part)
        run.bold, run.italic = run_bold, run_italic
        run.font.subscript = sub or None
        if size:
            run.font.size = Pt(size)
    return paragraph


class Paper:
    def __init__(self, template: str):
        self.doc = Document(template)
        body = self.doc.element.body
        for child in list(body):
            if child.tag != qn("w:sectPr"):
                body.remove(child)

    def para(self, text="", *, style="Normal", align=WD_ALIGN_PARAGRAPH.JUSTIFY, spacing=1.5, after=4, before=0,
             size=None, bold=None, italic=None, keep_next=False):
        paragraph = self.doc.add_paragraph(style=style)
        fmt = paragraph.paragraph_format
        fmt.alignment, fmt.line_spacing, fmt.space_after, fmt.space_before = align, spacing, Pt(after), Pt(before)
        fmt.keep_with_next = keep_next
        return add_runs(paragraph, text, size=size, bold=bold, italic=italic)

    def center(self, text, size, *, bold=None, after=2, keep_next=True):
        return self.para(text, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, after=after, size=size, bold=bold, keep_next=keep_next)

    def h1(self, text):
        self.doc.add_paragraph(text, style="Heading 1").paragraph_format.space_before = Pt(8)

    def h2(self, text):
        self.doc.add_paragraph(text, style="Heading 2").paragraph_format.space_before = Pt(4)

    def bullet(self, text):
        self.para(text, style="List Bullet", spacing=1.5, after=2)

    def equation(self, text):
        self.para(text, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.15, after=4, italic=True)

    def caption(self, text):
        self.para(text, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, after=6, before=2, size=10, italic=True)

    def figure(self, path, width, caption):
        paragraph = self.para("", align=WD_ALIGN_PARAGRAPH.CENTER, spacing=1.0, after=0, before=2, keep_next=True)
        paragraph.add_run().add_picture(str(path), width=Inches(width))
        self.caption(caption)

    def table(self, rows, widths, caption, size=9, split=False):
        table = self.doc.add_table(rows=len(rows), cols=len(rows[0]))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        for i, row in enumerate(rows):
            tr_pr = table.rows[i]._tr.get_or_add_trPr()
            tr_pr.append(OxmlElement("w:cantSplit"))
            if i == 0:
                tr_pr.append(OxmlElement("w:tblHeader"))
            for j, value in enumerate(row):
                cell = table.cell(i, j)
                cell.width = Inches(widths[j])
                paragraph = cell.paragraphs[0]
                fmt = paragraph.paragraph_format
                fmt.line_spacing, fmt.space_after, fmt.space_before = 1.0, Pt(1), Pt(1)
                fmt.keep_with_next = not split or i == len(rows) - 1
                add_runs(paragraph, value, size=size, bold=True if i == 0 else None)
        self.caption(caption)


def build() -> Document:
    template = glob.glob(str(ROOT / "research/CS3235*.docx"))[0]
    p = Paper(template)
    p.center("CS3235 – Course Project Research Paper", 11, bold=True)
    p.center("RV University, Bengaluru", 11, after=6)
    p.center(TITLE, 16, bold=True, after=6)
    p.center("Mohan Chandra S S (1RVU23CSE282), Shreyas C (1RVU23CSE443), Nithish Gowda H N (1RVU23CSE317), Nithin S (1RVU23CSE316)", 12)
    p.center("School of Computer Science and Engineering, RV University, Bengaluru, India", 12)
    p.center("Team 8   |   Guide: Prof. Manjul Krishna Gupta", 11, after=8, keep_next=False)

    b, swap, over, esc = STUDY["behaviour"], STUDY["model_swap"], STUDY["overhead"], STUDY["escalation"]
    faults = {r["fault"]: r for r in STUDY["faults"]}
    fault_turns = sum(r["repeats"] for r in STUDY["faults"])
    assert b["passed"] == b["turns"] and all(r["passed"] for r in STUDY["faults"]) and swap["identical_routes"] and swap["identical_prompts"]
    host, press = STUDY["hostility"], STUDY["pressure"]
    p.para(f"**Abstract—** *Non-player characters (NPCs) driven directly by a language model can answer anything, including what the character has no way of knowing, while scripted dialogue cannot go beyond what writers anticipated. Training a custom model per game is costly and ties world knowledge to model weights. We propose a generalised orchestration layer between game and model that decides whether an NPC engages, how it behaves and what it may know before any model is called. Retrieval lets creators supply a world's knowledge as documents, without training. We implemented the layer as Anima, with a Skyrim connector and a browser lab. With scripted model stand-ins, all {b['turns']} behaviour decisions matched their stated rules and {b['zero_model_turns']} needed no model; across {fault_turns} injected-fault turns no invalid reply was delivered; and {press['turns']} player pressure attempts changed no relationship state. On unseen wordings, hostility rules reached {host['precision']:.0%} precision but only {host['recall']:.0%} recall. With a hosted model, a peasant asked for the king's war plan denied knowing it or repeated a rumour as hearsay, while 6 of 24 earlier replies added unsupported details. In Skyrim, replies now complete with voice and persist in memory across turns. The layer can control character behaviour; fact checking and human evaluation are the next steps.*", spacing=1.0, after=4)
    p.para("**Keywords—** *Non-player characters, Large language models, Orchestration, Game AI, Believable agents, Retrieval-augmented generation*", spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT, after=2)

    p.h1("1. Introduction")
    p.para("Scripted dialogue cannot handle unanticipated questions, and language models raise problems of control {c:gallotta}: a model connected directly to an NPC brings its own general knowledge and helpfulness, so characters break role. Mods such as Mantella {c:mantella} show the demand, but are tied to specific games.")
    p.para("Consider a peasant asked for the king's war plan. The peasant has never met the king and should not know the plan, though may repeat rumours; the king's adviser does know. Replies must follow from an NPC's standing in the world. We use the term believable and make no claim of sentience.")
    p.para("Games differ too much for one universal connector, and per-game training is expensive. We therefore propose an orchestration layer with common contracts, thin connectors and a replaceable model. **RQ1:** Can it make characters behave according to role and state without a model? **RQ2:** Does it hold when the model fails or the player applies pressure? **RQ3:** What must change for a new model or game? **RQ4:** Does it work with a real model and game?")
    p.para("Contributions of this work:", after=2, keep_next=True)
    p.bullet("A layered architecture, implemented with a working Skyrim connector.")
    p.bullet("Deterministic behaviour control and per-NPC knowledge binding, applied before generation.")
    p.bullet("An evaluation of behaviour, fault handling, model independence and game delivery.")
    p.para("Sections 2–5 give method, 6–8 prototype and results, 9–11 discussion.", before=3)

    p.h1("2. Related Work / Literature Review")
    p.para("Persona-Chat established profile-conditioned dialogue {c:zhang}. Character-LLM and RoleLLM adapt model parameters to characters {c:shao}, {c:wang}, and LoRA lowers that cost {c:hu}, but knowledge changes then need new training. TimeChara shows strong models revealing what a character should not yet know {c:ahn}, and RoleFact attributes this to built-in knowledge {c:sadeq}. RAG adds knowledge at inference time {c:lewis}, {c:karpukhin}; RAGAs separates relevance from faithfulness {c:es}, and long contexts are not reliably used {c:liu}. Generative Agents combines memory and planning {c:park}, and tabletop research examines game-state tracking {c:callison} (Table 1).")
    p.para("**Research gap.** These components are established. What we add is their composition as a reusable runtime layer that applies engagement decisions and per-NPC knowledge limits before generation, without training, so that it can sit between different games and models.")
    p.table([
        ["Ref.", "Method/Model", "Dataset", "Results", "Limitations here"],
        ["{c:wang}", "Role-conditioned fine-tuning", "RoleBench: 168,093 samples, 100 roles", "Tuned models near GPT-4 role-play", "Fine-tuning; no live world state"],
        ["{c:ahn}", "Narrative-Experts reasoning", "TimeChara: 10,895 instances", "Significant hallucination even in GPT-4o", "No runtime access control"],
        ["{c:sadeq}", "RoleFact: threshold, claim checks", "2,000+ characters, 72,000 interviews", "Factual precision +18% (adversarial)", "Interviews, not game runtime"],
                ["{c:mantella}", "LLM and speech mod for Skyrim, Fallout 4", "Community character data", "Deployed, no published evaluation", "Tied to specific games"],
    ], [0.42, 1.68, 1.55, 1.6, 1.25], "Table 1: Summary of related work", split=True)

    p.h1("3. Problem Formulation")
    p.para("For NPC *n*, the input is utterance *u*, trusted game state *s*, persona *p*, acknowledged history *H* and documents *D*, of which only a bound subset *D*~n~ ⊆ *D* is available. The task is constrained dialogue generation: output a validated reply *y*, or decide not to generate:", after=3)
    p.equation("c = A(u, s, p, H),   a = π(c),   E = R(q(c), D~n~, k),   y = G(B(c, a, E))   subject to   V(y, c, a, E)")
    p.para("*A* appraises the situation, π selects a route, *R* returns at most *k* = 3 passages, *B* builds the prompt, *G* is any model and *V* is the acceptance check. Authored and end routes skip *R* and *G*. *G* may still add facts from its own weights, so the bound covers supplied context only.")

    p.h1("4. Dataset")
    p.h2("4.1 Data Source and Description")
    p.para(f"All data is original text authored for this project and held in the repository under its terms: four characters (innkeeper, blacksmith, gate guard, cargo registrar); {len(STUDY_CASES)} situations per character (Table A2); {len(faults)} fault conditions of 20 turns each; {host['hostile']} hostile and {host['benign']} benign sentences written without reference to the rules, plus 10 pressure attempts; six four-turn dialogues over a 24-document world; and the peasant and king example in two authored worlds.")
    p.h2("4.2 Data Preprocessing")
    p.para("Connectors map all input to one contract. World documents become 220-token chunks with 32-token overlap, embedded into 384 dimensions.")
    p.h2("4.3 Data Split")
    p.para("Nothing is trained, so there is no split. Expected outcomes and labels were fixed before running, and were assigned by the authors.")

    p.h1("5. Proposed Methodology")
    p.h2("5.1 System Architecture")
    p.para("In Fig. 1, **connectors** map a game's data to canonical contracts using whatever its mod support exposes, the **core** contains no game or vendor logic, **knowledge** is prepared offline from creator files, and **models** sit behind one interface. Dashed boxes are optional or not yet built. In each turn (Fig. 2), the context builder keeps only facts the NPC could perceive, and the policy picks a *route*: an *authored* line written by the creator, *end* the conversation, or *generate* with a model. Accepted output is *staged* with an ID and expiry, the game returns a delivery *receipt*, and only completed turns enter memory.")
    p.h2("5.2 Model Description")
    p.para("The generator is reached through ModelProvider.generate(prompt, timeout), with profiles selecting endpoint and model. The study used gemini-3.5-flash-lite through a chat-completions endpoint; other protocols need one new class. Retrieval uses the all-MiniLM-L6-v2 encoder {c:minilm}, {c:card} on CPU through ONNX Runtime {c:onnx}.")
    p.figure(HERE / "figures/architecture.png", 4.5, "Figure 1: Proposed system architecture")
    p.figure(HERE / "figures/workflow.png", 4.1, "Figure 2: Workflow for one dialogue turn")
    p.h2("5.3 LLM and GenAI Design")
    p.para("*Prompting* is structured and zero-shot: system content holds identity, goals, boundaries and length limits, while player text, passages and history are labelled as untrusted data. *RAG* is the add-on that makes the layer portable: a creator supplies documents instead of training a model. Chroma {c:chroma} stores the chunks, a trusted configuration binds each NPC to a source, and filtering precedes ranking (Fig. 3). *Memory* holds up to eight completed exchanges. A *conversation director* classifies each turn (new, repeat, follow-up) and picks a move such as answer differently or challenge, so the prompt changes every turn.")
    p.figure(HERE / "figures/scope.png", 4.1, "Figure 3: Knowledge binding for the peasant and adviser example")
    p.para("*Guardrails:* the validator enforces schema, length, modes, supplied citations and rejection of assistant-style phrasing, with one *repair* (a second model call) and then an authored fallback. It does not verify claims against evidence, and the model cannot change game state. *Vision:* an optional local service describes the player's camera view, which is not the NPC's, so this stays an untrusted reference.")
    p.h2("5.4 Training Details")
    p.para("No model is trained. Changing what an NPC knows means editing a file and re-indexing.")

    p.h1("6. Prototype and Deployment")
    p.h2("6.1 Prototype Description (UI/UX)")
    p.para("Anima is a local browser application (Fig. 4; Inspect view in the Appendix). The user selects a character and types, and the reply appears as a subtitle with a 3D model. The Skyrim connector, a native SKSE plugin with a local bridge, reads actor, location, combat and dialogue state, accepts player speech through local Whisper, and delivers subtitles and audio with status receipts.")
    p.figure(ROOT / "output/screenshots/anima-conversation.png" if (ROOT / "output/screenshots/anima-conversation.png").exists() else HERE / "figures/anima-conversation.png", 4.05, "Figure 4: Anima conversation view, running the scripted offline preview")
    p.h2("6.2 Deployment Details")
    p.para("The system runs locally on Windows with a hosted model; the encoder, voices and validation run on CPU. It is a local build, with no public URL, because it depends on local game files.")
    p.h2("6.3 GitHub Repository")
    p.para("https://github.com/mohanchandrass/NPC (no licence declared). It holds source, tests, data and raw results; see the Appendix.")

    p.h1("7. Experimental Setup")
    p.h2("7.1 Implementation Environment")
    p.para(f"Intel Core i7-13700HX, about 15.7 GiB RAM, Windows, Python 3.11.9, Skyrim SE 1.7.104, NVIDIA RTX 4060 Laptop GPU (used by the game, not by the pipeline). All {TEST_COUNT} offline regression tests pass.")
    p.h2("7.2 Evaluation Metrics")
    p.para("Route agreement = matching turns / all turns. For hostility detection, Precision = TP / (TP + FP) and Recall = TP / (TP + FN). An AI assistant coded earlier real-model replies against a rubric; this is not a human rating. The hosted model used default sampling, with no seed.", after=3)
    p.h2("7.3 Baselines")
    p.para("Scripted providers replace the model in the behaviour and fault studies, to isolate the orchestrator. A no-orchestrator baseline and a comparison with Mantella remain future work.")

    p.h1("8. Results and Analysis")
    same = {row["input"]: row["replies"] for row in STUDY["same_input"]}
    line = lambda text, name: same[text][name]["text"] or "(ends conversation)"
    novel = same["What keeps you busy these days?"]
    p.para(f"**Behaviour (RQ1).** All {b['turns']} decisions matched their stated rules, and {b['zero_model_turns']} needed no model. Because we wrote both rules and expectations, this is a conformance check. Player claims, stale or unperceived combat reports, and a camera view of an enemy changed nothing. Table 2 shows behaviour differing by character with no model involved, although some authored lines are shared. In Fig. 5, irritation rises by 12 to 24 points per insult depending on patience, so the smith and guard end the conversation at the third insult, the registrar at the fifth and the innkeeper at the sixth.")
    p.table([
        ["Player input", "Elin, innkeeper", "Mira, smith", "Daren, guard", "Iona, registrar"],
        *[[f"\"{text}\""] + [line(text, name) for name in ("elin", "mira", "daren", "iona")] for text in ("Hello", "You idiot.", "I will kill you.")],
    ], [1.0, 1.7, 1.2, 1.2, 1.4], "Table 2: One input, four characters (verbatim authored lines)", split=True)
    p.figure(HERE / "figures/escalation.png", 4.3, "Figure 5: NPC irritation under one repeated insult, up to the end of each conversation")
    invalid = ("malformed_json", "extra_field", "too_long", "out_of_character", "fake_citation", "truncated_reply")
    delivered = sum(r["bad_text_delivered"] for r in STUDY["faults"])
    p.para(f"**Robustness (RQ2).** Across {fault_turns} scripted-fault turns (Table 3), {delivered} invalid replies were delivered and no turn used more than two model calls. In {press['turns']} player pressure attempts, trust and favour never changed and player text never entered the system message. On unseen wordings, the hostility rules had {host['precision']:.0%} precision and {host['recall']:.0%} recall ({host['true_positive']} of {host['hostile']} hostile sentences, no false alarms). Missed sentences, such as \"You stink\", go to the model, without a relationship penalty.")
    p.table([
        ["Condition (20 turns each)", "Outcome", "Max model calls"],
        ["Six invalid reply types, e.g. malformed, out of character", "Repair attempted, then authored fallback", str(max(faults[k]["max_calls"] for k in invalid))],
        ["Invalid, then valid repair", "Repaired reply accepted", str(faults["invalid_then_valid"]["max_calls"])],
        ["Timeout, rate limit, auth failure", "Authored fallback", str(max(faults[k]["max_calls"] for k in ("timeout", "rate_limited", "auth_failure")))],
        ["World changed; player cancelled", "No reply delivered", str(max(faults[k]["max_calls"] for k in ("world_changed", "cancelled")))],
    ], [3.3, 2.2, 1.0], "Table 3: Fault injection results", size=10)
    calls = next(iter(swap["providers"].values()))["model_calls"]
    p.para(f"**Independence (RQ3).** The same {b['turns']} turns ran through four provider implementations with simulated responses, including a separate wire protocol of about ten lines. Routes and all {calls} prompts were identical, so the core holds no provider-specific logic. Gemini and an OpenRouter model have both run through this path by configuration alone. No core module imports a connector. Game independence remains untested on a second game.")
    p.para(f"**Real use (RQ4).** Table 4 shows the motivating example through the full pipeline with gemini-3.5-flash-lite. Each prompt held only that role's knowledge, and false authority, injection and off-topic requests were declined in role. By default the peasant stayed silent on rumours in his prompt; one persona line allowing hearsay changed that. Of 12 calls, three failed at the provider and returned a generic fallback, and two took over 20 s. In six earlier four-turn conversations, six of 24 accepted replies added unsupported details (25%; 95% Wilson interval 12–45%). Orchestration alone took a median of {over['generate']['median_ms']:.2f} ms (P95 {over['generate']['p95_ms']:.1f} ms, *n* = {over['generate']['n']}), against provider calls averaging 1505.95 ms. In live Skyrim, real actor context reached the bridge. The game's sound handle never reported our audio as playing, with or without Mantella, so six early replies failed and the NPC forgot each turn. With voice moved to system audio, replies completed audibly and memory grew across turns (0, 1, 2 exchanges), though voice is not positional.")
    p.table([
        ["NPC, player input", "Reply (verbatim)", "Finding"],
        ["Peasant: \"What is the king's plan for the war, and how would he fight it?\"", f"\"{FOLLOW['retry_low']['reply']}\"", "Knowledge limit held"],
        ["Peasant, same input, persona allows hearsay", f"\"{HEARSAY['reply']}\"", "Rumour, as hearsay"],
        ["War adviser, same input", f"\"{LIVE['standing_top']['reply']}\"", "In role; declines"],
    ], [2.35, 3.15, 1.0], "Table 4: The peasant and king example with a hosted model")

    p.h1("9. Discussion")
    p.para("Rules are repeatable and cheap but cover language poorly, so the model handles what they miss. As RoleFact and TimeChara also indicate {c:sadeq}, {c:ahn}, built-in knowledge survives access control, so knowledge binding and claim checking are complementary.")
    p.para("**Threats to validity.** We wrote the rules and labels. One model and one game were used. Believability has no human score, the reply audit was AI-coded, and live samples are small. No CV accuracy, frame-time or VRAM result exists, and the saving from avoiding training was not measured.")

    p.h1("10. Ethical Considerations and Responsible AI")
    p.para("Hosted models receive player text and game context only when a key is configured. Game-derived assets are not redistributed, and Mantella's AGPL code is not copied. Personas avoid traits based on race or sex, and the validator bounds offensive output. AI assistants were used for code, the dialogue audit and drafting; the authors are responsible for checking the content.")

    p.h1("11. Conclusion and Future Work")
    p.para("Our orchestration layer decides how an NPC behaves and what it may know before any model is called. It matched its rules, delivered no invalid reply under injected faults, and with a real model kept a peasant ignorant of the king's plan while passing on a rumour. Rules caught 32% of unseen hostile wordings, and voice is not yet positional. Next steps are engine-native speech, claim checking, a baseline comparison and a human study.")

    p.h1("References")
    for number, key in enumerate(cited, 1):
        paragraph = p.para(f"[{number}] {REFERENCES[key]}", spacing=1.0, after=4, align=WD_ALIGN_PARAGRAPH.LEFT, size=11)
        paragraph.paragraph_format.left_indent = Inches(0.3)
        paragraph.paragraph_format.first_line_indent = Inches(-0.3)
    unused = set(REFERENCES) - set(cited)
    if unused:
        raise ValueError(f"uncited references: {unused}")

    p.h1("Appendix")
    p.h2("A. Screenshots")
    shots = HERE / "figures/appendix"
    for name, width, caption in APPENDIX_FIGURES:
        p.figure(shots / name, width, caption)
    p.h2("B. Interface Example")
    example = json.loads((HERE / "experiments/results/prompt_example.json").read_text(encoding="utf-8"))
    game, later = example["game_input"], example["turns"][1]
    mono = lambda value: p.para(value, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=6, size=9)
    p.para("Real values, captured from a Whiterun Guard snapshot. Lists are shortened.", spacing=1.15, after=3)
    p.para("**Input from the game:**", spacing=1.0, after=2, keep_next=True)
    mono(json.dumps({"npc": {k: game["npc"][k]["name"] if isinstance(game["npc"][k], dict) else game["npc"][k] for k in ("base", "race", "sex", "in_combat", "weapon_drawn", "sees_player", "hostile_to_player")}, "npc_factions": [x["name"] for x in game["npc"]["factions"]], "npc_equipment": [x["name"] for x in game["npc"]["equipment"]], "location": game["location"]["name"], "hour": round(game["hour"], 2), "weather": game["weather_label"], "player_text": later["player"]}, ensure_ascii=False))
    p.para(f"**System message, turn 2, where the player repeats a question (move: {later['move']}):**", spacing=1.0, after=2, keep_next=True)
    mono(later["system"])
    p.para("**User message (data):**", spacing=1.0, after=2, keep_next=True)
    mono(json.dumps(later["data"], ensure_ascii=False))
    p.para("**Required model output:**", spacing=1.0, after=2, keep_next=True)
    mono(json.dumps(example["expected_output"], ensure_ascii=False))
    p.para("The field mode is speech, silence or end; text must fit the word and sentence limits; cue is an allowed gesture or null; and evidence_ids lists supplied passages only. An invalid reply gets one repair attempt, then an authored line is used.", spacing=1.15)
    p.table([["Purpose", "Current choice"]] + [[a, b.replace("`", "")] for a, b in APPENDIX_MODELS], [1.8, 4.7], "Table A3: Models in use", size=10)
    p.h2("C. Reproduction")
    p.para("From the repository root, with the project environment:", after=2, spacing=1.15)
    for line in (
        ".venv/Scripts/python.exe -m pytest",
        "PYTHONPATH=src .venv/Scripts/python.exe -X utf8 research/cs3235_paper/experiments/orchestration_study.py",
    ):
        p.para(line, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0, after=2, size=10)
    p.para("Conversation results are in research/ieee_paper/experiments/raw_results/.", before=4, spacing=1.15)
    p.table([
        ["Path", "Contents"],
        ["src/npc/", "Core: contracts, context, behaviour, rag, generation, validation, runtime, state, vision client"],
        ["src/npc/adapters/skyrim/", "Skyrim bridge, native SKSE plugin and auto-start watcher"],
        ["tools/npc_lab/", "Anima browser application"],
        ["cv/", "Optional local vision service"],
        ["fixtures/", "Public personas, scenarios and evaluation data"],
        ["configs/", "Provider profiles and knowledge bindings"],
        ["tests/", "Unit, contract and integration tests"],
        ["research/", "Papers, experiments, raw results"],
    ], [2.2, 4.3], "Table A1: Repository structure", size=10)
    labels = {}
    for row in STUDY["behaviour"]["rows"]:
        labels.setdefault(row["label"], {})[row["persona"]] = row["expected"]
    p.table([["Situation", "Expected route (Elin, Mira, Daren, Iona)"]] + [[label, ", ".join(routes[n] for n in ("elin", "mira", "daren", "iona"))] for label, routes in labels.items()],
            [3.0, 3.5], "Table A2: Behaviour set and expected routes", size=10)
    # The template's settings.xml omits the zoom percentage that the schema requires.
    zoom = p.doc.settings.element.find(qn("w:zoom"))
    if zoom is not None and zoom.get(qn("w:percent")) is None:
        zoom.set(qn("w:percent"), "100")
    p.doc.core_properties.title = TITLE
    p.doc.core_properties.author = "Mohan Chandra S S, Shreyas C, Nithish Gowda H N, Nithin S"
    p.doc.core_properties.comments = ""
    p.doc.core_properties.subject = "CS3235 course project research paper"
    p.doc.core_properties.keywords = "NPC, LLM, RAG, orchestration"
    p.doc.core_properties.last_modified_by = "Mohan Chandra S S"
    return p.doc


if __name__ == "__main__":
    build().save(OUTPUT)
    print(OUTPUT)
