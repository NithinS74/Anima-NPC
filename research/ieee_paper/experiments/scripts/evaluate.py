"""Isolated real-encoder retrieval/update experiment; no paid calls or core edits."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import platform
import shutil
import statistics
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DATASET = ROOT/'fixtures/evaluation/paper_revision'
OUT = ROOT/'research/ieee_paper/experiments/raw_results'

def rank_metrics(ranked, relevant):
    if not relevant or len(set(ranked)) != len(ranked):
        raise ValueError('Nonempty gold and unique ranked sources required')
    relevant=set(relevant)
    hits=[i+1 for i,s in enumerate(ranked) if s in relevant]
    return {'p1':float(bool(ranked and ranked[0] in relevant)),
            'p3':sum(s in relevant for s in ranked[:3])/3,
            'r3':len(set(ranked[:3])&relevant)/len(relevant),
            'rr':1/min(hits) if hits else 0.0}

def summarize(values):
    if not values or any(not math.isfinite(v) or v<0 for v in values):
        raise ValueError('Need nonnegative finite observations')
    ordered=sorted(values)
    return {'n':len(values),'mean_ms':statistics.mean(values),'median_ms':statistics.median(values),
            'sample_sd_ms':statistics.stdev(values) if len(values)>1 else None,
            'p95_ms':ordered[math.ceil(.95*len(values))-1] if len(values)>=30 else None,
            'min_ms':min(values),'max_ms':max(values)}

def validate_dataset(queries, names):
    seen=set()
    for q in queries:
        if not q.get('query','').strip() or q['id'] in seen or not q.get('relevant_sources') or not set(q['relevant_sources'])<=set(names):
            raise ValueError('Invalid query identity, content or gold source')
        if len(q['relevant_sources'])!=len(set(q['relevant_sources'])):
            raise ValueError('Duplicate gold source')
        seen.add(q['id'])
    if not queries:
        raise ValueError('Empty dataset')

def timed(fn):
    start=time.perf_counter(); value=fn()
    return value,(time.perf_counter()-start)*1000

class TimedEncoder:
    def __init__(self, inner):
        self.inner=inner; self.name=inner.name; self.samples=[]
    def offsets(self,text):
        return self.inner.offsets(text)
    def embed(self,texts):
        result,elapsed=timed(lambda:self.inner.embed(texts)); self.samples.append(elapsed)
        return result

class TimedCollection:
    def __init__(self,inner):
        self.inner=inner; self.samples=[]
    def __getattr__(self,key):
        return getattr(self.inner,key)
    def query(self,**kwargs):
        result,elapsed=timed(lambda:self.inner.query(**kwargs)); self.samples.append(elapsed)
        return result

def make_service(work):
    from npc.rag.backend import RAGService,Settings
    from npc.rag.backend.embeddings import LocalEmbedder
    encoder=TimedEncoder(LocalEmbedder(ROOT/'output/paper_revision/models'))
    service=RAGService(Settings(root=work,kb_dir='corpus',data_dir='index'),embedder=encoder)
    service.collection=TimedCollection(service.collection)
    return service,encoder

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cold',action='store_true'); parser.add_argument('--run-id',default='primary')
    args=parser.parse_args(argv)
    if not args.run_id.replace('-','').isalnum():
        raise ValueError('Run ID must be alphanumeric/hyphen')
    work=ROOT/'output/paper_revision'/args.run_id
    OUT.mkdir(parents=True,exist_ok=True)
    if args.cold:
        service,encoder=make_service(work)
        result,ms=timed(lambda:service.retrieve('Where can I find the blacksmith Mira working?',top_k=3))
        data={'first_query_in_fresh_process_ms':ms,'embedding_ms':encoder.samples[-1],
              'vector_query_ms':service.collection.samples[-1], 'sources':[m.source for m in result.matches]}
        (OUT/'cold_query.json').write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data)); return
    if (work/'index').exists():
        raise ValueError('Use a fresh --run-id; never overwrite prior index state')
    work.mkdir(parents=True,exist_ok=True)
    shutil.copytree(DATASET/'corpus',work/'corpus')
    queries=json.loads((DATASET/'queries.json').read_text())
    names=[p.name for p in (work/'corpus').glob('*.md')]
    validate_dataset(queries,names)
    service,encoder=make_service(work)
    report,index_ms=timed(service.sync)
    if report.errors:
        raise RuntimeError('Indexing failed')
    rows=[]
    for q in queries:
        result,elapsed=timed(lambda:service.retrieve(q['query'],top_k=3))
        sources=[m.source for m in result.matches]
        rows.append({**q,'ranked_sources':sources,'matches':[m.model_dump() for m in result.matches],
                     'retrieval_ms':elapsed,'embedding_ms':encoder.samples[-1],
                     'vector_query_ms':service.collection.samples[-1], 'metrics':rank_metrics(sources,q['relevant_sources'])})
    warm=[]
    for i in range(30):
        q=queries[i%len(queries)]
        _,ms=timed(lambda:service.retrieve(q['query'],top_k=3))
        warm.append({'query_id':q['id'],'retrieval_ms':ms,'embedding_ms':encoder.samples[-1],
                     'vector_query_ms':service.collection.samples[-1]})
    before=service.retrieve('Where is Mira\'s forge?',source='forge.md',top_k=3).model_dump()
    original=(work/'corpus/forge.md').read_text()
    updated=original.replace('northern well','southern mill')
    if updated==original: raise ValueError('Expected original update target missing')
    _,write_ms=timed(lambda:(work/'corpus/forge.md').write_text(updated,encoding='utf-8'))
    update,update_ms=timed(service.sync)
    after=service.retrieve('Where is Mira\'s forge?',source='forge.md',top_k=3).model_dump()
    if update.errors or 'southern mill' not in after['context'] or before['matches'][0]['id']==after['matches'][0]['id']:
        raise RuntimeError('Update retrieval verification failed')
    result={'baseline':'ff9fd7e','run_id':args.run_id,'corpus_documents':report.indexed,'corpus_chunks':report.chunks,
            'query_count':len(queries),'dataset_sha256':hashlib.sha256((DATASET/'queries.json').read_bytes()).hexdigest(),
            'corpus_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (DATASET/'corpus').glob('*.md')},
            'encoder':'all-MiniLM-L6-v2-onnx-v1','encoder_provider':'CPUExecutionProvider','chunk_tokens':220,'overlap_tokens':32,'top_k':3,
            'label_provenance':'Author-assigned before retrieval; no independent human adjudication',
            'indexing_ms_including_first_model_load':index_ms,
            'rank_metrics_macro':{k:statistics.mean(r['metrics'][k] for r in rows) for k in ['p1','p3','r3','rr']},
            'retrieval_queries':rows,'warm_queries':warm,
            'warm_latency':{k:summarize([r[k] for r in warm]) for k in ['retrieval_ms','embedding_ms','vector_query_ms']},
            'knowledge_update':{'write_ms':write_ms,'sync_ms':update_ms,'sync_report':update.model_dump(),'before':before,'after':after,
                                'generator_invoked':False,'answer_correctness':'unmeasured; no generated answer','training_step':False},
            'environment':{'python':platform.python_version(),'os':platform.platform(),'processor':platform.processor()},
            'limitations':['Small authored fiction; not Skyrim or independent gold.','No semantic generation or in-game latency measured.']}
    (OUT/'retrieval_update.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ['query_count','corpus_documents','corpus_chunks','rank_metrics_macro','warm_latency']},indent=2))

if __name__=='__main__':
    main()
