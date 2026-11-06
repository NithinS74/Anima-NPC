"""Lay out the paper .docx as a PDF, reading every paragraph, table and image from the .docx itself.

Word and LibreOffice are not available on the build machine, so this is the PDF renderer. It follows
the template's page size, margins, fonts and spacing. Word's own line breaks may differ slightly.

Usage: python docx_to_pdf.py <paper.docx> <paper.pdf> [preview_dir]
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import docx
import fitz
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, PageTemplate, Paragraph, Table, TableStyle

FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("TNR", FONTS / "times.ttf"))
pdfmetrics.registerFont(TTFont("TNR-B", FONTS / "timesbd.ttf"))
pdfmetrics.registerFont(TTFont("TNR-I", FONTS / "timesi.ttf"))
pdfmetrics.registerFont(TTFont("TNR-BI", FONTS / "timesbi.ttf"))
pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-BI")
pdfmetrics.registerFont(TTFont("SYM", FONTS / "cambria.ttc", subfontIndex=1))

SINGLE = 1.15  # Times New Roman's natural line height as a multiple of its size
ALIGN = {WD_ALIGN_PARAGRAPH.CENTER: TA_CENTER, WD_ALIGN_PARAGRAPH.JUSTIFY: TA_JUSTIFY, WD_ALIGN_PARAGRAPH.LEFT: TA_LEFT, None: TA_LEFT}
HEADINGS = {"Heading 1": (14, HexColor("#365F91")), "Heading 2": (13, HexColor("#4F81BD"))}


def markup(paragraph: DocxParagraph, default_size: float, force_bold=False) -> str:
    parts = []
    for run in paragraph.runs:
        text = escape(run.text)
        text = "".join(f'<font name="SYM">{c}</font>' if c in "πΣ∈⊆" else c for c in text)
        if run.font.size:
            text = f'<font size="{run.font.size.pt}">{text}</font>'
        if run.font.subscript:
            text = f'<sub rise="2.5" size="{default_size * .7}">{text}</sub>'
        if run.bold or force_bold:
            text = f"<b>{text}</b>"
        if run.italic:
            text = f"<i>{text}</i>"
        parts.append(text)
    return "".join(parts)


def run_size(paragraph: DocxParagraph, fallback: float) -> float:
    sizes = [run.font.size.pt for run in paragraph.runs if run.font.size]
    return max(sizes) if sizes else fallback


def paragraph_flowable(paragraph: DocxParagraph, document, width: float):
    style = paragraph.style.name
    images = paragraph._p.findall(".//" + qn("a:blip"))
    fmt = paragraph.paragraph_format
    if images:
        blob = document.part.related_parts[images[0].get(qn("r:embed"))].blob
        extent = paragraph._p.find(".//" + qn("wp:extent"))
        cx, cy = int(extent.get("cx")) / 12700, int(extent.get("cy")) / 12700
        return Image(io.BytesIO(blob), width=cx, height=cy, hAlign="CENTER"), True
    if style in HEADINGS:
        size, colour = HEADINGS[style]
        before = fmt.space_before.pt if fmt.space_before is not None else 10
        look = ParagraphStyle(style, fontName="TNR-B", fontSize=size, leading=size * SINGLE, textColor=colour, spaceBefore=before, spaceAfter=3)
        # Like Word, keep a heading with the first lines of the next block, not all of it.
        return Paragraph(escape(paragraph.text), look), False
    size = run_size(paragraph, 12)
    leading = size * SINGLE * (fmt.line_spacing or 1.0)
    bullet = style == "List Bullet"
    indent = fmt.left_indent.pt if fmt.left_indent else (18 if bullet else 0)
    first = fmt.first_line_indent.pt if fmt.first_line_indent else 0
    look = ParagraphStyle(
        "body", fontName="TNR", fontSize=size, leading=leading, alignment=ALIGN.get(fmt.alignment, TA_LEFT),
        spaceAfter=fmt.space_after.pt if fmt.space_after is not None else 6,
        spaceBefore=fmt.space_before.pt if fmt.space_before is not None else 0,
        leftIndent=indent, firstLineIndent=first, textColor=black, allowWidows=0, allowOrphans=0,
        bulletFontName="TNR", bulletFontSize=size, bulletIndent=4,
    )
    return Paragraph(markup(paragraph, size), look, bulletText="•" if bullet else None), bool(fmt.keep_with_next)


def table_flowable(table: DocxTable, width: float):
    widths = [cell.width.pt for cell in table.rows[0].cells]
    rows = []
    for i, row in enumerate(table.rows):
        out = []
        for cell in row.cells:
            paragraph = cell.paragraphs[0]
            size = run_size(paragraph, 9)
            look = ParagraphStyle("cell", fontName="TNR", fontSize=size, leading=size * SINGLE, alignment=TA_LEFT)
            out.append(Paragraph(markup(paragraph, size), look))
        rows.append(out)
    flow = Table(rows, colWidths=widths, repeatRows=1, hAlign="CENTER")
    flow.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), .5, black), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return flow


def convert(source: Path, target: Path) -> None:
    document = docx.Document(source)
    width = letter[0] - 2 * inch
    story, group = [], []
    for child in document.element.body:
        kind = child.tag.split("}")[1]
        if kind == "p":
            flowable, keep = paragraph_flowable(DocxParagraph(child, document), document, width)
        elif kind == "tbl":
            table = DocxTable(child, document)
            # A table whose first row does not keep with the next may break across pages.
            splittable = not table.cell(0, 0).paragraphs[0].paragraph_format.keep_with_next
            flowable, keep = table_flowable(table, width), not splittable
        else:
            continue
        is_heading = kind == "p" and child.pPr is not None and child.pPr.pStyle is not None and child.pPr.pStyle.val.startswith("Heading")
        if is_heading and not group:
            story.append(CondPageBreak(72))
        group.append(flowable)
        if not keep:
            story.append(KeepTogether(group) if len(group) > 1 else group[0])
            group = []
    story.extend(group)
    props = document.core_properties
    frame = Frame(inch, inch, letter[0] - 2 * inch, letter[1] - 2 * inch, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    pdf = BaseDocTemplate(str(target), pagesize=letter, title=props.title, author=props.author, subject=props.subject)
    pdf.addPageTemplates([PageTemplate(id="page", frames=[frame])])
    pdf.build(story)


def report(target: Path, preview: Path | None) -> None:
    pdf = fitz.open(target)
    print("pages", len(pdf))
    import re

    for number, page in enumerate(pdf, 1):
        text = page.get_text()
        heads = re.findall(r"^(?:\d+\. [A-Z].*|References|Appendix|Acknowledgment)\s*$", text, re.M)
        print(number, len(text.split()), [h.strip() for h in heads])
        if preview:
            preview.mkdir(parents=True, exist_ok=True)
            page.get_pixmap(dpi=75).save(preview / f"p{number:02d}.png")


if __name__ == "__main__":
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    convert(source, target)
    report(target, Path(sys.argv[3]) if len(sys.argv) > 3 else None)
