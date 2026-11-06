# CS3235 paper

New paper in the RV University CS3235 template. The earlier IEEE paper in `research/ieee_paper/` is unchanged. [PLAN.md](PLAN.md) records the plan that went to review; the final paper applies that review's cuts.

| File | Purpose |
|---|---|
| `CS3235_Team8_*.docx` | The paper, built on the course template |
| `CS3235_Team8_*.pdf` | PDF laid out from the `.docx` |
| `build_paper.py` | Paper content and `.docx` builder |
| `docx_to_pdf.py` | PDF renderer, used because Word and LibreOffice are not on the build machine |
| `figure_sources/` | Editable TikZ for Figures 1–3 |
| `experiments/` | Knowledge-scope study and its results |

## Rebuild

Run from the repository root.

```sh
.venv/Scripts/python.exe research/cs3235_paper/build_paper.py
python research/cs3235_paper/docx_to_pdf.py <paper.docx> <paper.pdf>
```

`docx_to_pdf.py` needs `reportlab`, `pymupdf`, `python-docx` and Windows' Times New Roman. These are authoring tools, so they are not in `requirements.txt`.

Compile a figure with Tectonic from `figure_sources/`, then export the PDF to PNG at 500 dpi:

```sh
../../../.tools/tectonic/tectonic.exe --outdir ../figures architecture.tex
```

## Studies

`experiments/orchestration_study.py` produces the paper's results. It uses the real pipeline with scripted providers and makes no API calls.

```sh
PYTHONPATH=src .venv/Scripts/python.exe -X utf8 research/cs3235_paper/experiments/orchestration_study.py
python research/cs3235_paper/experiments/plot_escalation.py
.venv/Scripts/python.exe -m pytest tests/unit/research
```

`experiments/knowledge_scope.py` measures whether restricted facts reach a lower-standing NPC's prompt. It is kept for reference, and the paper does not report it.
