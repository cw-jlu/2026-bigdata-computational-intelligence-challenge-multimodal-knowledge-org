import json
from pathlib import Path
V=Path(__file__).resolve().parents[1]
spec=json.loads((V/'audit/holdout_cases.json').read_text(encoding='utf-8'))
events=[json.loads(x) for x in (V/'output/中间证据/events.jsonl').open(encoding='utf-8')]
results=[]
for c in spec['cases']:
    ee=[e for e in events if e['date']==c['date'] and e['batch']==c['batch'] and e['decision']=='纳入']; errors=[]
    if len(ee)!=c['included']: errors.append(f'纳入数量期望{c["included"]}，实际{len(ee)}')
    for key in ['direction','task']:
        if key in c and any(e[key]!=c[key] for e in ee): errors.append('字段'+key+'不符合原始标注')
    results.append({**c,'ok':not errors,'errors':errors,'actual':[{'event_id':e['event_id'],'direction':e['direction'],'task':e['task']} for e in ee]})
(V/'audit/holdout_results.json').write_text(json.dumps({'cases':len(results),'passed':sum(x['ok'] for x in results),'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'cases':len(results),'passed':sum(x['ok'] for x in results),'failures':[r for r in results if not r['ok']]},ensure_ascii=False))
raise SystemExit(1 if any(not r['ok'] for r in results) else 0)
