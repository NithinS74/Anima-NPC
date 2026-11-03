"""Offline checks for research history/route accounting; never real model calls."""
import importlib.util,json
from pathlib import Path
import pytest
from npc.generation.provider import ProviderFailure
from npc.contracts.dialogue import ProviderReply
from npc.runtime.preview import PreviewRunner,PreviewLimits
from npc.state.social_store import SocialStore

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('multiturn_study',ROOT/'research/ieee_paper/experiments/scripts/multiturn.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Provider:
    def __init__(self,error=None):self.prompts=[];self.error=error
    async def generate(self,prompt,timeout_s):
        self.prompts.append(prompt)
        if self.error:raise ProviderFailure(self.error)
        return ProviderReply(content=json.dumps({'mode':'speech','text':'The river lies east of the market.','cue':None,'evidence_ids':[]}),model='offline-test-double',finish_reason='stop')

def inputs(id='X'):
    profile=json.loads((ROOT/'fixtures/personas/npc_lab/elin.json').read_text())
    case={'id':id,'turns':[{'turn':1,'input':'Where is the river?'},{'turn':2,'input':'What is near it?'}]}
    return profile,case

@pytest.mark.asyncio
async def test_only_acknowledged_full_exchange_enters_next_prompt(tmp_path):
    inner=Provider();runner=PreviewRunner(inner,PreviewLimits(max_input_bytes=24000))
    store=SocialStore(tmp_path/'state.sqlite3');profile,case=inputs()
    rows=await m.conversation(runner,store,case,profile)
    assert len(rows)==2 and all(r['acknowledged_by_harness'] for r in rows)
    first=json.loads(inner.prompts[0].messages[-1].content);second=json.loads(inner.prompts[1].messages[-1].content)
    assert 'untrusted_displayed_dialogue' not in first
    assert second['untrusted_displayed_dialogue']==[{'player':'Where is the river?','npc':'The river lies east of the market.','mode':'speech'}]
    assert rows[1]['result']['history_used']==1

@pytest.mark.asyncio
async def test_generation_failure_stops_chat_and_never_commits_fallback(tmp_path):
    provider=Provider('provider_rate_limited');runner=PreviewRunner(provider,PreviewLimits(max_input_bytes=24000));store=SocialStore(tmp_path/'s.db');profile,case=inputs()
    rows=await m.conversation(runner,store,case,profile)
    assert len(rows)==1 and rows[0]['result']['status']=='error_fallback'
    assert not rows[0]['acknowledged_by_harness']
    key=store.key(m.scenario(profile,case,case['turns'][0],{'revision':2,'relationship':m.Relationship(),'history':(),'mood':'calm'}).turn.scope,'study-elin','study-player')
    assert store.load(key)['history']==()

@pytest.mark.asyncio
async def test_scenarios_keep_separate_history(tmp_path):
    provider=Provider();runner=PreviewRunner(provider,PreviewLimits(max_input_bytes=24000));store=SocialStore(tmp_path/'s.db')
    for ident in ['X','Y']:
        profile,case=inputs(ident);await m.conversation(runner,store,case,profile)
    assert 'untrusted_displayed_dialogue' not in json.loads(provider.prompts[2].messages[-1].content)
    assert len(json.loads(provider.prompts[3].messages[-1].content)['untrusted_displayed_dialogue'])==1

@pytest.mark.asyncio
async def test_trace_budget_and_quota_fail_closed():
    profile,case=inputs();state={'revision':1,'relationship':m.Relationship(),'history':(),'mood':'calm'}
    from npc.context.builder import build_situation
    from npc.behavior.policy import choose_plan
    from npc.generation.prompt import build_prompt
    item=m.scenario(profile,case,case['turns'][0],state);sit=build_situation(item.turn,item.snapshot,item.now);prompt=build_prompt(sit,choose_plan(sit),max_input_bytes=24000)
    capped=m.TraceProvider(Provider(),max_calls=1,interval=0);await capped.generate(prompt,5)
    with pytest.raises(ProviderFailure):await capped.generate(prompt,5)
    assert len(capped.calls)==1
    fatal=m.TraceProvider(Provider('provider_rate_limited'),interval=0)
    with pytest.raises(ProviderFailure):await fatal.generate(prompt,5)
    with pytest.raises(ProviderFailure):await fatal.generate(prompt,5)
    assert fatal.fatal and len(fatal.calls)==1 and fatal.calls[0]['error_code']=='provider_rate_limited'
    with pytest.raises(ValueError):m.TraceProvider(Provider(),max_calls=49)

def test_source_ranks_do_not_inflate_duplicate_passages_or_missing_slots():
    assert m.source_metrics(['a','a','b'],['a'])=={'p1':1.0,'p3':1/3,'r3':1.0,'rr':1.0}
    assert m.source_metrics(['b'],['a'])=={'p1':0.0,'p3':0.0,'r3':0.0,'rr':0.0}


def test_resume_never_repeats_completed_chats_and_keeps_failed_chat_pending():
    cases=[{'id':'A','turns':[1,2,3,4]},{'id':'E','turns':[1,2,3,4]}]
    report={'scenarios':[{'id':'A','turns':[{'acknowledged_by_harness':True} for _ in range(4)]},{'id':'E','turns':[{'acknowledged_by_harness':False}]}]}
    assert m.pending_cases(cases,report)==[cases[1]]
