import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).resolve().parents[3]/'research/ieee_paper/experiments/scripts/analyze.py'
spec=importlib.util.spec_from_file_location('paper_analysis',p);a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def row(id,rag,status,ms,hit):
    return {'case':{'id':id,'persona':'Mira','question':'Where?'},'rag_enabled':rag,'literal_target_match':hit,
      'observed_response_ready_ms':ms,'result':{'status':status,'input_tokens':10,'output_tokens':5,'response':{'text':'Answer'}}}

def test_pairing_excludes_unmatched_case_but_preserves_failure_accounting():
    rows=[row('a',False,'model_success',10,False),row('a',True,'model_success',20,True),row('b',True,'error_fallback',40,False)]
    s=a.aggregate({'scenarios':rows,'provider_calls':[{'status':'failed','error_code':'provider_rate_limited'}]})
    assert s['completed_pairs']==1 and s['unpaired_ids']==['b']
    assert s['conditions']['rag']['paired_response_ready']['mean_ms']==20
    assert s['conditions']['rag']['all_observed_response_ready']['mean_ms']==30
    assert s['conditions']['rag']['fallback_n']==1 and s['provider_failures']==['provider_rate_limited']
    assert s['conditions']['rag']['target_mentions']==s['conditions']['rag']['target_denominator']==1
    with pytest.raises(ValueError): a.aggregate({'scenarios':rows+[rows[0]],'provider_calls':[]})

def test_zero_completed_trials_remains_unmeasured_not_perfect():
    s=a.aggregate({'scenarios':[],'provider_calls':[]})
    assert s['completed_pairs']==0 and s['conditions']['rag']['paired_response_ready'] is None
    assert s['conditions']['rag']['target_denominator']==0

def test_blinding_keeps_condition_key_separate_and_human_scores_blank():
    ratings,key=a.blinded_sheets([row('a',False,'model_success',10,False),row('a',True,'model_success',20,True)])
    assert len({r['sample_id'] for r in ratings})==2
    assert all('rag_enabled' not in r and r['persona_1_to_5']==r['supported_claims']=='' for r in ratings)
    assert {r['sample_id'] for r in ratings}=={r['sample_id'] for r in key}
