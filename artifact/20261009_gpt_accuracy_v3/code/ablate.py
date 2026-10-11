"""Separate event and analysis changes under identical data and presentation scope."""
import hashlib,json
from pathlib import Path
from fusion import build_day,choose_trend,choose_trend_v2_reference,NODES
V=Path(__file__).resolve().parents[1]
cache={d['date']:build_day(d)[0] for d in map(json.loads,(V/'audit/raw_snapshot.jsonl').open(encoding='utf-8'))}
records=[]
for node in NODES:
    event_ids=[e['event_id'] for e in cache[node] if e['decision']=='纳入'];old=choose_trend_v2_reference(node,cache);new=choose_trend(node,cache)
    brief=lambda t:{'country':t['country'],'platform':t['platform'],'dates':len(t['dates']),'stages':len(t['phases']),'event_ids':[e['event_id'] for e in t['evidence']]} if t else None
    records.append({'date':node,'identical_daily_event_ids':event_ids,'v3_facts_v2_analysis':brief(old),'v3_facts_v3_analysis':brief(new),'presentation_effect':'DOCX table width/phase explanations and full-range XLSX QA do not change event decisions; no separate official scores available.'})
(V/'audit/ablation_analysis.json').write_text(json.dumps({'data_sha256':hashlib.sha256((V/'audit/raw_snapshot.jsonl').read_bytes()).hexdigest(),'records':records,'causal_limit':'Implementation layers separated locally, no official rescores for ablations and no controlled model/prompt experiment.'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Eight-node local ablation recorded, no score attribution.')
