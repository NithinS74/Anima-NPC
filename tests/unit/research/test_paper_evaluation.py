import importlib.util
from pathlib import Path
import pytest

PATH=Path(__file__).resolve().parents[3]/'research/ieee_paper/experiments/scripts/evaluate.py'
spec=importlib.util.spec_from_file_location('paper_evaluate',PATH)
e=importlib.util.module_from_spec(spec); spec.loader.exec_module(e)

def test_rank_metrics_distinguish_miss_rank_and_fixed_three_denominator():
    assert e.rank_metrics(['b','a','c'],['a'])==dict(p1=0,p3=1/3,r3=1,rr=.5)
    assert e.rank_metrics(['a'],['a'])==dict(p1=1,p3=1/3,r3=1,rr=1)
    assert e.rank_metrics([],['a'])==dict(p1=0,p3=0,r3=0,rr=0)
    assert e.rank_metrics(['x','y','a'],['a','b'])['r3']==.5

@pytest.mark.parametrize('ranked,gold',[(['a','a'],['a']),(['a'],[])])
def test_invalid_metrics_inputs_fail(ranked,gold):
    with pytest.raises(ValueError): e.rank_metrics(ranked,gold)

def test_summary_sd_and_small_sample_tail_policy():
    summary=e.summarize([1,2,3])
    assert summary['mean_ms']==2 and summary['sample_sd_ms']==1
    assert summary['p95_ms'] is None
    assert e.summarize(list(range(1,31)))['p95_ms']==29
    assert e.summarize([3])['sample_sd_ms'] is None

@pytest.mark.parametrize('values',[[],[-1],[float('nan')],[float('inf')]])
def test_invalid_timing_observations_fail(values):
    with pytest.raises(ValueError): e.summarize(values)

def test_dataset_requires_unambiguous_known_predeclared_gold():
    valid={'id':'a','query':'Where is the forge?','relevant_sources':['forge.md']}
    e.validate_dataset([valid],['forge.md'])
    for rows in [[],[valid,valid],[{**valid,'relevant_sources':['secret.md']}],[{**valid,'query':''}],[{**valid,'relevant_sources':['forge.md','forge.md']}]]:
        with pytest.raises(ValueError): e.validate_dataset(rows,['forge.md'])

def test_runner_rejects_unsafe_run_id_before_filesystem_or_services():
    with pytest.raises(ValueError): e.main(['--run-id','../escape'])
