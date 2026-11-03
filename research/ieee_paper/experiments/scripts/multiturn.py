"""Isolated multi-turn study using existing Anima runtime, retrieval and social state."""
from __future__ import annotations
import argparse, asyncio, hashlib, importlib.util, json, platform, shutil, time
from datetime import datetime, timezone
from pathlib import Path
from npc.contracts.context import ContextScenario, Persona, PlayerInput, Relationship
from npc.generation.provider import ProviderFailure
from npc.state.social_store import SocialStore

ROOT=Path(__file__).resolve().parents[4]
DATA=ROOT/'fixtures/evaluation/anima_multiturn'
OUT=ROOT/'research/ieee_paper/experiments/raw_results'
WORK=ROOT/'output/anima_multiturn'
spec=importlib.util.spec_from_file_location('prior_metrics',Path(__file__).with_name('evaluate.py'))
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)

def dump(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')

def source_metrics(ranked,relevant):
    # Do not fill missing slots after source deduplication of top-three passages.
    return metrics.rank_metrics(list(dict.fromkeys(ranked)),relevant)

def scenario(profile,case,turn,state):
    data=json.loads((ROOT/'fixtures/scenarios/smith_available.json').read_text())
    stamp=datetime.now(timezone.utc).isoformat()
    scope={'game_id':'cedarvale-study','world_id':'village','save_branch_id':case['id']}
    request=f"{case['id']}-{turn['turn']}";npc='study-'+profile['id'];rev=state['revision']
    data['now']=stamp
    data['turn'].update(scope=scope,request_id=request,session_id='chat-'+case['id'],npc_id=npc,player_id='study-player',
        sequence=turn['turn'],expected_dialogue_revision=rev,captured_at=stamp,simulation_time_s=float(turn['turn']),facts=[],
        player_input={'text':turn['input'],'source':'text','confidence':1.0})
    data['snapshot'].update(scope=scope,npc_id=npc,player_id='study-player',storage_revision=rev,dialogue_revision=rev,
        turn_epoch=turn['turn'],persona=profile['persona'],relationship=state['relationship'].model_dump(),
        recent_dialogue=[m.model_dump() for m in state['history']],
        npc_state={'observed_at':stamp,'ttl_ms':60000,'mood':state['mood'],'current_goal':profile['current_goal']})
    return ContextScenario.model_validate(data)

class TraceProvider:
    def __init__(self,inner,max_calls=48,interval=3.0):
        if not 1<=max_calls<=48: raise ValueError('request budget must be 1..48')
        self.inner=inner;self.max_calls=max_calls;self.interval=interval;self.calls=[];self.fatal=False;self.last=0.0
    async def generate(self,prompt,timeout_s):
        if self.fatal or len(self.calls)>=self.max_calls: raise ProviderFailure('provider_unavailable')
        delay=max(0,self.interval-(time.monotonic()-self.last))
        if delay: await asyncio.sleep(delay)
        self.last=time.monotonic()
        row={'prompt':prompt.model_dump(mode='json'),'prompt_sha256':hashlib.sha256(prompt.model_dump_json().encode()).hexdigest()}
        self.calls.append(row);start=time.perf_counter()
        try:
            reply=await self.inner.generate(prompt,min(timeout_s,30.0));row.update(status='completed',reply=reply.model_dump(mode='json'));return reply
        except ProviderFailure as error:
            row.update(status='failed',error_code=error.code)
            if error.code in {'provider_auth','provider_rate_limited'}: self.fatal=True
            raise
        finally: row['provider_call_ms']=(time.perf_counter()-start)*1000

class TraceRetriever:
    def __init__(self,inner): self.inner=inner;self.calls=[]
    async def retrieve(self,situation,*,timeout_s):
        from npc.context.focus import resolve_question
        start=time.perf_counter();result=await self.inner.retrieve(situation,timeout_s=timeout_s)
        self.calls.append({'query':resolve_question(situation),'retrieval_ms':(time.perf_counter()-start)*1000,'result':result.model_dump(mode='json')})
        return result

async def conversation(runner,store,case,profile):
    from npc.contracts.context import Scope
    scope=Scope(game_id='cedarvale-study',world_id='village',save_branch_id=case['id'])
    key=store.key(scope,'study-'+profile['id'],'study-player')
    initial=Relationship.model_validate(profile['relationship'])
    store.ensure(key,initial,profile['mood']);rows=[]
    for turn in case['turns']:
        state=store.load(key);request=f"{case['id']}-{turn['turn']}"
        state,audit,cached=store.begin_turn(key,request,PlayerInput(text=turn['input']),Persona.model_validate(profile['persona']),state['revision'])
        if cached is not None: raise ValueError('study must use fresh state')
        item=scenario(profile,case,turn,state);start=time.perf_counter();reply=await runner.run(item)
        row={'turn':turn['turn'],'input':turn['input'],'history_before':[m.model_dump() for m in state['history']],
             'scenario':item.model_dump(mode='json'),'result':reply.model_dump(mode='json'),
             'response_ready_ms':(time.perf_counter()-start)*1000,'acknowledged_by_harness':False}
        rows.append(row)
        if reply.status not in {'model_success','repair_success'} or reply.response is None:
            store.cancel(key,request);break
        store.stage_preview(key,request,{'result':reply.model_dump(mode='json')},state['revision'])
        store.displayed(key,request);row['acknowledged_by_harness']=True
    return rows

def service(path):
    from npc.rag.backend import RAGService,Settings
    from npc.rag.backend.embeddings import LocalEmbedder
    encoder=metrics.TimedEncoder(LocalEmbedder(ROOT/'output/paper_revision/models'))
    obj=RAGService(Settings(root=path,kb_dir='corpus',data_dir='index'),embedder=encoder)
    obj.collection=metrics.TimedCollection(obj.collection)
    return obj,encoder

def prepare():
    if WORK.exists(): raise ValueError('study work exists; preserve previous run and choose a new study before rerunning')
    bench=WORK/'source_files';shutil.copytree(DATA/'corpus',bench/'corpus')
    queries=json.loads((DATA/'queries.json').read_text());metrics.validate_dataset(queries,[p.name for p in (DATA/'corpus').glob('*.md')])
    obj,encoder=service(bench);sync,index_ms=metrics.timed(obj.sync)
    if sync.errors: raise RuntimeError('source-file indexing failed')
    rows=[]
    for q in queries:
        result,elapsed=metrics.timed(lambda:obj.retrieve(q['query'],top_k=3))
        rows.append({**q,'matches':[m.model_dump() for m in result.matches],'retrieval_ms':elapsed,
                     'metrics':source_metrics([m.source for m in result.matches],q['relevant_sources'])})
    warm=[]
    for i in range(30):
        q=queries[i%len(queries)];result,elapsed=metrics.timed(lambda:obj.retrieve(q['query'],top_k=3))
        warm.append({'id':q['id'],'retrieval_ms':elapsed,'embedding_ms':encoder.samples[-1],'vector_query_ms':obj.collection.samples[-1]})
    dialog=WORK/'dialogue';(dialog/'corpus').mkdir(parents=True)
    anthology='\n\n'.join(p.read_text(encoding='utf-8').strip() for p in sorted((DATA/'corpus').glob('*.md')))
    (dialog/'corpus/public_reference.md').write_text(anthology,encoding='utf-8')
    chat,_=service(dialog);chat_sync,chat_index_ms=metrics.timed(chat.sync)
    if chat_sync.errors: raise RuntimeError('dialogue anthology indexing failed')
    before=obj.retrieve('Where is Mira based and what does she repair?',source='forge.md',top_k=3)
    forge=bench/'corpus/forge.md';forge.write_text(forge.read_text().replace('beside the northern well','beside the southern mill'),encoding='utf-8')
    update,update_ms=metrics.timed(obj.sync);after=obj.retrieve('Where is Mira based and what does she repair?',source='forge.md',top_k=3)
    dump(OUT/'multiturn_retrieval.json',{'corpus_documents':len(list((DATA/'corpus').glob('*.md'))),'source_index':sync.model_dump(),
        'indexing_ms':index_ms,'dialogue_anthology':chat_sync.model_dump(),'dialogue_indexing_ms':chat_index_ms,
        'queries':rows,'macro':{k:sum(r['metrics'][k] for r in rows)/len(rows) for k in ['p1','p3','r3','rr']},
        'warm_queries':warm,'warm_summary':{k:metrics.summarize([r[k] for r in warm]) for k in warm[0] if k!='id'},
        'knowledge_update':{'before':before.model_dump(),'after':after.model_dump(),'sync_ms':update_ms,'sync_report':update.model_dump(),'generator_invoked':False},
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((DATA/'corpus').glob('*.md'))},
        'anthology_sha256':hashlib.sha256(anthology.encode()).hexdigest(),'python':platform.python_version(),
        'label_provenance':'Author-assigned primary source, not exhaustive independent relevance; dedup top-three passage sources without slot refill.'})
    print('Prepared source benchmark and unchanged dialogue anthology; no model calls.')

def pending_cases(cases,report):
    completed={c['id'] for c in report.get('scenarios',[]) if len(c['turns'])==next((len(x['turns']) for x in cases if x['id']==c['id']),-1) and all(t['acknowledged_by_harness'] for t in c['turns'])}
    return [c for c in cases if c['id'] not in completed]

async def generate(profile_path,resume=False):
    from npc.generation.config import load_provider
    from npc.rag.local import LocalRetriever
    from npc.rag.config import RAGConfig
    from npc.runtime.preview import PreviewRunner,PreviewLimits
    target=OUT/'multiturn_dialogue.json'
    if target.exists() and not resume: raise ValueError('model records exist; explicit --resume required')
    if resume and not target.exists(): raise ValueError('no prior study to resume')
    if not (WORK/'dialogue/index/knowledge_base.manifest.json').exists(): raise ValueError('prepare first')
    cases=json.loads((DATA/'scenarios.json').read_text())
    provider=TraceProvider(load_provider(ROOT/profile_path));obj,_=service(WORK/'dialogue')
    cfg=RAGConfig(bindings=[dict(game_id='cedarvale-study',world_id='village',npc_ids=['study-elin','study-mira','study-daren'],source='public_reference.md')])
    retriever=TraceRetriever(LocalRetriever(cfg,service=obj))
    limits=PreviewLimits(response_timeout_ms=60000,model_cutoff_ms=59000,retrieval_timeout_ms=2000,max_input_bytes=24000,max_output_tokens=400)
    runner=PreviewRunner(provider,limits,retriever=retriever);store=SocialStore(WORK/('study-resume.sqlite3' if resume else 'study.sqlite3'))
    report={'provider_profile':profile_path,'limits':limits.__dict__ if hasattr(limits,'__dict__') else str(limits),'acknowledgement':'harness console-display simulation, not game delivery','scenarios':[],'provider_calls':provider.calls,'retrieval_calls':retriever.calls,'independent_human_ratings':False}
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'));provider.calls=report['provider_calls'];retriever.calls=report['retrieval_calls']
        cases=pending_cases(cases,report);report['bounded_resume_after_cooldown']=True
    dump(target,report)
    for case in cases:
        if provider.fatal or len(provider.calls)>=provider.max_calls:break
        profile=json.loads((ROOT/f"fixtures/personas/npc_lab/{case['persona_id']}.json").read_text())
        first=len(provider.calls);rfirst=len(retriever.calls)
        rows=await conversation(runner,store,case,profile)
        report['scenarios'].append({'id':case['id'],'title':case['title'],'persona':profile,'turns':rows,'provider_call_range':[first,len(provider.calls)],'retrieval_call_range':[rfirst,len(retriever.calls)]})
        dump(target,report)
        print(json.dumps({'scenario':case['id'],'turns':len(rows),'generated':sum(t['acknowledged_by_harness'] for t in rows),'calls':len(provider.calls)}),flush=True)
    dump(target,report)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');parser.add_argument('--cold',action='store_true');parser.add_argument('--generate',action='store_true');parser.add_argument('--resume',action='store_true');parser.add_argument('--provider-profile',default='configs/providers/gemini.yaml');args=parser.parse_args()
    if sum([args.prepare,args.cold,args.generate])!=1:parser.error('choose exactly one explicit phase')
    if args.prepare:prepare()
    elif args.generate:asyncio.run(generate(args.provider_profile,args.resume))
    else:
        obj,enc=service(WORK/'source_files');reply,elapsed=metrics.timed(lambda:obj.retrieve('Who leads the Northern Guild?',top_k=3))
        dump(OUT/'multiturn_cold.json',{'first_query_fresh_process_ms':elapsed,'embedding_ms':enc.samples[-1],'vector_query_ms':obj.collection.samples[-1],'matches':[m.model_dump() for m in reply.matches]})
if __name__=='__main__':main()
