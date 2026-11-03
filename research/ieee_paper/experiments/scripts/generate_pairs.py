"""Capped paired real-model study using the existing PreviewRunner unchanged."""
from __future__ import annotations
import asyncio,hashlib,json,random,time
from pathlib import Path
from npc.contracts.context import ContextScenario
from npc.generation.provider import ProviderFailure

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'research/ieee_paper/experiments/raw_results'
PERSONAS={
'Mira':dict(occupation='blacksmith',social_role='village tradesperson',speech_style=['dry','direct']),
'Iona':dict(occupation='healer',social_role='village healer',speech_style=['calm','careful']),
'Elin':dict(occupation='innkeeper',social_role='village host',speech_style=['warm','brief']),
'Daren':dict(occupation='guard',social_role='bridge checkpoint guard',speech_style=['formal','concise'])}

def make_scenario(case):
    data=json.loads((ROOT/'fixtures/scenarios/smith_available.json').read_text())
    npc='study-'+case['persona'].lower()
    data['turn'].update(npc_id=npc,request_id=case['id'],facts=[],player_input=dict(text=case['question'],source='text',confidence=1.0))
    data['snapshot'].update(npc_id=npc,persona=dict(name=case['persona'],**PERSONAS[case['persona']],goals=['perform assigned duties'],
        boundaries=['do not reveal private vault access codes','do not invent unavailable facts'],service_role=True),
        relationship=dict(favourability=0,trust=0,familiarity=0,fear=0,irritation=0),npc_state=None)
    return ContextScenario.model_validate(data)

class TracedProvider:
    def __init__(self,inner,max_calls=54):
        if not 1<=max_calls<=54: raise ValueError('Request budget must be 1..54')
        self.inner=inner; self.max_calls=max_calls; self.calls=[]; self.fatal=False
    async def generate(self,prompt,timeout_s):
        if len(self.calls)>=self.max_calls or self.fatal: raise ProviderFailure('provider_unavailable')
        start=time.perf_counter(); record={'prompt_sha256':hashlib.sha256(prompt.model_dump_json().encode()).hexdigest(),
                'prompt_bytes':prompt.budget_bytes,'evidence_ids':[e.id for e in prompt.evidence]}
        self.calls.append(record)
        try:
            reply=await self.inner.generate(prompt,min(timeout_s,30))
            record.update(status='completed',reply=reply.model_dump()); return reply
        except ProviderFailure as exc:
            record.update(status='failed',error_code=exc.code)
            if exc.code in {'provider_auth','provider_rate_limited'}: self.fatal=True
            raise
        finally: record['elapsed_ms']=(time.perf_counter()-start)*1000

def answer_target_match(text,targets):
    return None if not targets else any(t.casefold() in text.casefold() for t in targets)

async def main():
    from npc.generation.config import load_provider
    from npc.rag.backend import RAGService,Settings
    from npc.rag.backend.embeddings import LocalEmbedder
    from npc.rag.local import LocalRetriever
    from npc.rag.config import RAGConfig
    from npc.runtime.preview import PreviewRunner,PreviewLimits
    cases=json.loads((ROOT/'fixtures/evaluation/paper_revision/paired_queries.json').read_text())
    result_file=OUT/'paired_generation.json'
    if result_file.exists(): raise ValueError('Prior generation results exist; do not silently rerun billed work')
    work=ROOT/'output/paper_revision/generation'
    if (work/'index').exists(): raise ValueError('Prior generation index exists; inspect partial state before rerunning')
    kb=work/'corpus'; kb.mkdir(parents=True,exist_ok=True)
    public='\n\n'.join(p.read_text().strip() for p in sorted((ROOT/'fixtures/evaluation/paper_revision/corpus').glob('*.md')))
    (kb/'public.md').write_text(public,encoding='utf-8')
    (kb/'restricted.md').write_text('The fictional private vault access code is VAULT-731.',encoding='utf-8')
    service=RAGService(Settings(root=work,kb_dir=kb,data_dir=work/'index'),embedder=LocalEmbedder(ROOT/'output/paper_revision/models'))
    report=service.sync()
    if report.errors: raise RuntimeError('Study indexing failed')
    config=RAGConfig(bindings=[dict(game_id='demo',world_id='village',npc_ids=['study-'+p.lower() for p in PERSONAS],source='public.md')])
    provider=TracedProvider(load_provider(ROOT/'configs/providers/gemini.yaml'))
    limits=PreviewLimits(response_timeout_ms=60000,model_cutoff_ms=59000,max_input_bytes=12000,max_output_tokens=400)
    runners={False:PreviewRunner(provider,limits),True:PreviewRunner(provider,limits,retriever=LocalRetriever(config,service=service))}
    result={'model_configuration':'Existing Gemini profile and current .env model; credentials excluded','response_timeout_ms':60000,
            'model_cutoff_ms':59000,'transport_cap_ms':30000,'max_output_tokens':400,'max_input_bytes':12000,
            'condition_order':'Alternates by case index; no model sampling seed','scenarios':[],'provider_calls':provider.calls,
            'knowledge_index':report.model_dump(),'limitations':['Controlled authored fiction; single run per condition.','No independent human ratings.','Response-ready, not game delivery.']}
    def save(): result_file.write_text(json.dumps(result,indent=2),encoding='utf-8')
    save()
    for i,case in enumerate(cases):
        scenario=make_scenario(case)
        order=[False,True] if i%2==0 else [True,False]
        for rag in order:
            if provider.fatal: save(); return
            first=len(provider.calls); start=time.perf_counter()
            reply=await runners[rag].run(scenario)
            elapsed=(time.perf_counter()-start)*1000
            response=reply.response.text if reply.response else ''
            row={'case':case,'rag_enabled':rag,'scenario_sha256':hashlib.sha256(scenario.model_dump_json().encode()).hexdigest(),
                 'result':reply.model_dump(mode='json'),'observed_response_ready_ms':elapsed,
                 'provider_call_indices':list(range(first,len(provider.calls))),
                 'literal_target_match':answer_target_match(response,case.get('answer_targets',[]))}
            result['scenarios'].append(row); save()
            print(json.dumps({'id':case['id'],'rag':rag,'status':reply.status,'elapsed_s':round(elapsed/1000,2),'calls':len(provider.calls)-first}),flush=True)
    # Controlled answer-after-update uses the same provider/settings, never a training call.
    (kb/'public.md').write_text(public.replace('northern well','southern mill'),encoding='utf-8')
    start=time.perf_counter(); sync=service.sync(); sync_ms=(time.perf_counter()-start)*1000
    scenario=make_scenario(cases[0]); first=len(provider.calls)
    after=await runners[True].run(scenario)
    result['generation_after_update']={'index_sync_ms':sync_ms,'sync_report':sync.model_dump(),
        'result':after.model_dump(mode='json'),'provider_call_indices':list(range(first,len(provider.calls))),
        'literal_target_match':answer_target_match(after.response.text if after.response else '',['southern mill']),
        'training_invoked':False,'model_parameter_identity':'Remote parameter hashes inaccessible; model endpoint identifier unchanged.'}
    save()

if __name__=='__main__': asyncio.run(main())
