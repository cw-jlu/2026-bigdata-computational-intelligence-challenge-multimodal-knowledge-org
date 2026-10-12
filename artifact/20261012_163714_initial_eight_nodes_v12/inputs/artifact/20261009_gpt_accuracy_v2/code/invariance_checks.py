"""Behavioral safeguards: reordering/renumbering and future-cutoff invariance."""
import copy
import json
import random
from pathlib import Path
from fusion import build_day,choose_trend,NODES,date_value
V=Path(__file__).resolve().parents[1]
raw={d['date']:d for d in (json.loads(x) for x in (V/'audit/raw_snapshot.jsonl').open(encoding='utf-8'))}
def facts(ee):
    return sorted([(e['country'] or '',e['platform_key'] or '',e['batch'],e['kind'],e['quantity'] or 0,tuple(e['interval']),e['region'],e['task'] or '',e['decision']) for e in ee],key=str)
checks=[]
for day in NODES:
    baseline=build_day(raw[day])[0]; changed=copy.deepcopy(raw[day]); random.Random(4601).shuffle(changed['radar']); random.Random(4602).shuffle(changed['texts'])
    for i,t in enumerate(changed['texts']): t['file']=t['file'].rsplit('/',1)[0]+f'/independently_renumbered_{9000-i}.txt'
    shuffled=build_day(changed)[0]
    checks.append({'date':day,'kind':'原始雷达顺序/TXT顺序/文件名重新编号不影响事件事实与纳入','ok':facts(baseline)==facts(shuffled)})
allcache={d:build_day(r)[0] for d,r in raw.items()}
for day in NODES:
    prefix={d:ee for d,ee in allcache.items() if date_value(d)<=date_value(day)}
    alltrend=choose_trend(day,allcache); prefixtrend=choose_trend(day,prefix)
    checks.append({'date':day,'kind':'加入节点之后材料不影响该节点主线','ok':alltrend==prefixtrend})
(V/'audit/invariance_results.json').write_text(json.dumps({'ok':all(c['ok'] for c in checks),'checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'ok':all(c['ok'] for c in checks),'failed':[c for c in checks if not c['ok']]},ensure_ascii=False))
raise SystemExit(1 if any(not c['ok'] for c in checks) else 0)
