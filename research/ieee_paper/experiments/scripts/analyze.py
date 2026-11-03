"""Analyze saved observations; never contact models or populate human ratings."""
from pathlib import Path
import importlib.util,json,csv,hashlib,random
ROOT=Path(__file__).resolve().parents[4]
spec=importlib.util.spec_from_file_location('paper_metrics',Path(__file__).with_name('evaluate.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
RATING_FIELDS=['sample_id','persona','question','response','persona_1_to_5','relevance_1_to_5','supported_claims','unsupported_claims','abstention_appropriate','notes']

def aggregate(d):
    by={}
    for row in d['scenarios']:
        group=by.setdefault(row['case']['id'],{})
        if row['rag_enabled'] in group: raise ValueError('Duplicate condition for a case')
        group[row['rag_enabled']]=row
    complete={k:v for k,v in by.items() if set(v)=={False,True}}
    summary={'completed_pairs':len(complete),'completed_response_records':len(d['scenarios']),
        'provider_requests':len(d['provider_calls']),
        'provider_failures':[c.get('error_code') for c in d['provider_calls'] if c['status']=='failed'],
        'unpaired_ids':[k for k,v in by.items() if len(v)!=2],
        'semantic_grounding_scores':'Unavailable: literal target mentions are not entailment or independent human ratings.',
        'conditions':{}}
    for flag,label in [(False,'no_rag'),(True,'rag')]:
        rows=[v[flag] for v in complete.values()]; allrows=[r for r in d['scenarios'] if r['rag_enabled']==flag]
        targets=[r for r in rows if r['literal_target_match'] is not None]
        summary['conditions'][label]={'paired_n':len(rows),'all_observed_n':len(allrows),
          'target_mentions':sum(r['literal_target_match'] for r in targets),'target_denominator':len(targets),
          'paired_response_ready':m.summarize([r['observed_response_ready_ms'] for r in rows]) if rows else None,
          'all_observed_response_ready':m.summarize([r['observed_response_ready_ms'] for r in allrows]) if allrows else None,
          'accepted_generated_n':sum(r['result']['status'] in ['model_success','repair_success'] for r in allrows),
          'fallback_n':sum(r['result']['status']=='error_fallback' for r in allrows),
          'repair_success_n':sum(r['result']['status']=='repair_success' for r in allrows),
          'input_tokens':sum(r['result']['input_tokens'] for r in allrows),
          'output_tokens':sum(r['result']['output_tokens'] for r in allrows)}
    return summary

def blinded_sheets(rows):
    ratings=[]; key=[]
    for row in rows:
        sample=hashlib.sha256((row['case']['id']+str(row['rag_enabled'])).encode()).hexdigest()[:10]
        item={k:'' for k in RATING_FIELDS}
        item.update(sample_id=sample,persona=row['case']['persona'],question=row['case']['question'],
            response=row['result']['response']['text'] if row['result'].get('response') else '')
        ratings.append(item)
        key.append({'sample_id':sample,'case_id':row['case']['id'],'rag_enabled':row['rag_enabled'],'status':row['result']['status']})
    random.Random(20261103).shuffle(ratings)
    return ratings,key

def main():
    base=ROOT/'research/ieee_paper/experiments'; out=base/'analysis';out.mkdir(exist_ok=True)
    d=json.loads((base/'raw_results/paired_generation.json').read_text())
    summary=aggregate(d)
    (out/'generation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    ratings,key=blinded_sheets(d['scenarios'])
    for i in [1,2]:
        with (out/f'pending_rater_{i}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=RATING_FIELDS);writer.writeheader();writer.writerows(ratings)
    (out/'rating_condition_key.json').write_text(json.dumps(key,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
