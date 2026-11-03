"""Validate the expanded report and package its allowlisted editable source."""
from pathlib import Path
import hashlib,json,re
from zipfile import ZipFile,ZIP_DEFLATED
from pypdf import PdfReader
HERE=Path(__file__).resolve().parent
TITLE='Persona-Aware, Knowledge-Bounded NPC Dialogue Through Model-Agnostic LLM Orchestration'
tex=(HERE/'main.tex').read_text(encoding='utf-8-sig');bib=(HERE/'references.bib').read_text(encoding='utf-8-sig')
pdf=PdfReader(HERE/'paper.pdf');text='\n'.join(p.extract_text() or '' for p in pdf.pages)
assert 1<=len(pdf.pages)<=7  # Expanded dialogue evidence; no strict six-page venue cap was supplied.
assert re.search(r'\\title\{([^}]+)\}',tex).group(1)==TITLE
assert pdf.metadata.title==TITLE
abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',tex,re.S).group(1)
words=len(abstract.split());assert 150<=words<=200,words
keys=set(re.findall(r'@\w+\{([^,]+),',bib));cited={k.strip() for group in re.findall(r'\\cite\{([^}]+)\}',tex) for k in group.split(',')}
labels=set(re.findall(r'\\label\{([^}]+)\}',tex));refs=set(re.findall(r'\\ref\{([^}]+)\}',tex))
assert cited<=keys and refs<=labels
assert len(re.findall(r'\\section\{',tex))==8
for usn in ['1RVU23CSE282','1RVU23CSE443','1RVU23CSE317','1RVU23CSE316']:assert usn in text
for rel in re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',tex):assert (HERE/rel).is_file(),rel
log=(HERE/'main.log').read_text(encoding='utf-8',errors='replace')
assert not re.search(r'Overfull|LaTeX Font Warning|Citation .* undefined|Reference .* undefined|There were undefined',log)
figures=['system_architecture','rag_orchestration_pipeline','model_agnostic_architecture','knowledge_ingestion']
for stem in figures:
    assert (HERE/'figures'/f'{stem}.pdf').is_file()
    assert '\\begin{tikzpicture}' in (HERE/'figure_sources'/f'{stem}.tex').read_text(encoding='utf-8-sig')
files=[HERE/x for x in ['main.tex','references.bib','README.md','REPORT_REVISION.md','validate_and_package.py']]
files+=[HERE/'figures'/f'{s}.pdf' for s in figures]
files+=sorted((HERE/'figure_sources').glob('*.tex'))
allowed={'.md','.py','.json','.csv','.txt'}
files+=sorted(p for p in (HERE/'experiments').rglob('*') if p.is_file() and p.suffix in allowed and '__pycache__' not in p.parts)
archive=HERE/'paper_source.zip'
with ZipFile(archive,'w',ZIP_DEFLATED) as z:
    for p in files:z.write(p,p.relative_to(HERE).as_posix())
with ZipFile(archive) as z:
    assert z.testzip() is None
    members=z.namelist()
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in members)
    assert all(not any(t in Path(n).parts for t in ['.env','models','index','__pycache__']) for n in members)
report={'title':TITLE,'pages':len(pdf.pages),'abstract_words':words,'references':len(keys),'undefined_citations':sorted(cited-keys),
 'undefined_references':sorted(refs-labels),'native_tikz_figures':figures,'main_paper_figures':3,'in_game_screenshot_included':False,
 'pdf_sha256':hashlib.sha256((HERE/'paper.pdf').read_bytes()).hexdigest(),'source_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'zip_members':members,'overfull_boxes':0,'font_shape_warnings':0,'underfull_hboxes':log.count('Underfull \\hbox'),
 'underfull_vboxes':log.count('Underfull \\vbox'),
 'distinct_model_inputs':8,'matched_pairs':7,'accepted_generated_outputs':14,'native_greeting_strings':2,'new_live_runs':0,
 'research_gates':['Independent semantic/persona and relevance ratings pending.','Rate limit prevented boundary/update generation completion.',
 'No real multi-backend comparison, live LLM/RAG game study or clear in-game screenshot.']}
output=HERE.parent/'evidence/report_expansion_document_validation.json'
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='zip_members'},indent=2))
