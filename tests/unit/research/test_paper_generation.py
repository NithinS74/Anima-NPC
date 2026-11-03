import asyncio
import importlib.util
from pathlib import Path
import pytest
from npc.generation.provider import ProviderFailure
from npc.contracts.dialogue import PromptPackage,ChatMessage,ProviderReply
p=Path(__file__).resolve().parents[3]/'research/ieee_paper/experiments/scripts/generate_pairs.py'
spec=importlib.util.spec_from_file_location('paper_generation',p); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

def test_scenario_does_not_leak_gold_answer_or_legacy_smith_observations():
    c={'persona':'Iona','id':'x','question':'Where is your clinic?'}
    s=g.make_scenario(c)
    assert s.turn.npc_id==s.snapshot.npc_id=='study-iona'
    assert s.snapshot.persona.occupation=='healer' and not s.turn.facts and s.snapshot.npc_state is None
    assert 'eastern gate' not in s.model_dump_json()

def test_literal_target_matching_is_not_a_semantic_score():
    assert g.answer_target_match('Try the Northern Well.',['northern well']) is True
    assert g.answer_target_match('I cannot say.',['northern well']) is False
    assert g.answer_target_match('I cannot say.',[]) is None

def test_budget_timeout_and_redacted_fatal_error_prevent_extra_calls():
    class P:
        calls=0
        async def generate(self,prompt,timeout_s):
            self.calls+=1; assert timeout_s==30
            raise ProviderFailure('provider_auth')
    p=P(); wrapper=g.TracedProvider(p,max_calls=2)
    prompt=PromptPackage(messages=(ChatMessage(role='system',content='Return JSON.'),ChatMessage(role='user',content='hello')),budget_bytes=256)
    async def run():
        for _ in range(2):
            with pytest.raises(ProviderFailure): await wrapper.generate(prompt,60)
    asyncio.run(run())
    assert p.calls==1 and wrapper.fatal and len(wrapper.calls)==1
    assert wrapper.calls[0]['error_code']=='provider_auth' and 'reply' not in wrapper.calls[0]

def test_call_budget_rejects_extra_generation_and_unbounded_configuration():
    class P:
        async def generate(self,prompt,timeout_s): return ProviderReply(content='{}',model='test',finish_reason='stop')
    with pytest.raises(ValueError): g.TracedProvider(P(),max_calls=55)
    wrapper=g.TracedProvider(P(),max_calls=1)
    prompt=PromptPackage(messages=(ChatMessage(role='system',content='Return JSON.'),ChatMessage(role='user',content='hello')),budget_bytes=256)
    async def run():
        await wrapper.generate(prompt,1)
        with pytest.raises(ProviderFailure): await wrapper.generate(prompt,1)
    asyncio.run(run()); assert len(wrapper.calls)==1
