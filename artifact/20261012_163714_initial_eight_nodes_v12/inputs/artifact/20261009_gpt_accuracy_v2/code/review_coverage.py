"""Separate post-generation coverage and contradictory-evidence review.

Reads only the prior GPT evidence, never other competitor artifacts.
Contradiction flags are review leads, not ground-truth labels or scores.
"""
import json
from collections import Counter
from pathlib import Path

V=Path(__file__).resolve().parents[1]
ROOT=V.parents[1]
def jl(p): return [json.loads(s) for s in p.open(encoding='utf-8')]
events=jl(V/'output/中间证据/events.jsonl')
claims=jl(V/'output/中间证据/claims.jsonl')
old=jl(ROOT/'artifact/20261008_001028_gpt-5.6solhigh/output/中间结果/evidence.jsonl')
nodes=json.loads((V/'output/中间证据/reconstruction_summary.json').read_text(encoding='utf-8'))['nodes']
comparisons=[]; flags=[]
for n in nodes:
    day=n['date']; a=[e for e in old if e['date']==day and e['decision']=='纳入']; b=[e for e in events if e['date']==day and e['decision']=='纳入']
    aa={e['batch'] for e in a}; bb={e['batch'] for e in b}
    comparisons.append({'date':day,'old':len(a),'new':len(b),'common_batches':len(aa&bb),'added_batches':sorted(bb-aa),'removed_batches':sorted(aa-bb),
        'old_shared_open_claim_extra_uses':sum(v-1 for v in Counter(e['open_file'] for e in a).values() if v>1),
        'note':'Batch IDs used solely to compare coverage in the same original radar input. TXT numbering never establishes an association. Shared articles with explicit different platform claims can be legitimate.'})
    for e in b:
        used=[c for c in claims if c['claim_id'] in e['claims']]
        for c in claims:
            if c['date']!=day or c['claim_id'] in e['claims'] or c['platform']!=e['platform_key']: continue
            if c['interval']!=e['interval'] or not c['region']: continue
            same_region=c['region']==e['region'] or c['region']==e['direction'] or (e['region']==e['direction'] and any(x['region']==c['region'] for x in used))
            if not same_region: continue
            contradictions=[]
            if c['country'] and c['country']!=e['country']: contradictions.append('country')
            if c['quantity'] is not None and c['quantity']!=e['quantity']: contradictions.append('quantity')
            if c['tasks'] and e['task']!='任务未核实' and e['task'] not in c['tasks']: contradictions.append('task')
            if contradictions: flags.append({'event_id':e['event_id'],'date':day,'file':c['file'],'quote':c['quote'],'fields':contradictions})
summary={'comparison':comparisons,'total_old':sum(x['old'] for x in comparisons),'total_new':sum(x['new'] for x in comparisons),
         'newly_added':sum(len(x['added_batches']) for x in comparisons),'removed':sum(len(x['removed_batches']) for x in comparisons),
         'same_time_same_area_additional_conflict_flags':flags,
         'limits':'Exact-window scan of extracted claims can miss unparsed text, broad-place ambiguity and partial-window contradictions; the manual raw cases remain separate. This is not an accuracy estimate.'}
(V/'audit/coverage_comparison.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['total_old','total_new','newly_added','removed']},ensure_ascii=False))
print('Additional exact-window contradictions:',len(flags))
