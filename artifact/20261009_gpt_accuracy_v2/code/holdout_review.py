"""Select hard RAW cases without consulting fusion or generated decisions."""
import json
import re
from pathlib import Path
V=Path(__file__).resolve().parents[1]
NODES=['2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
days={d['date']:d for d in (json.loads(x) for x in (V/'audit/raw_snapshot.jsonl').open(encoding='utf-8'))}
out=[]
for node in NODES:
    d=days[node]; groups={}
    for r in d['radar']: groups.setdefault(r['data']['批号'],[]).append(r)
    selected=[]
    for b,rr in groups.items():
        if rr[0]['sheet']=='舰船' and len(set(r['data']['活动区域'] for r in rr))>1:
            selected.append((b,rr)); break
    for b,rr in groups.items():
        if rr[0]['sheet']=='飞机' and (max(r['data']['经度'] for r in rr)-min(r['data']['经度'] for r in rr)>4 or max(r['data']['纬度'] for r in rr)-min(r['data']['纬度'] for r in rr)>4):
            selected.append((b,rr)); break
    # Include a control: first original source article with a named ship.
    for b,rr in groups.items():
        if rr[0]['sheet']=='舰船' and len(set(r['data']['活动区域'] for r in rr))==1:
            selected.append((b,rr)); break
    for b,rr in selected:
        name=rr[0]['data'].get('目标类型',rr[0]['data'].get('机舰名'))
        key=re.split('型|级|号',name)[0].strip('“”')
        if not any(key in t['fields']['正文'] for t in d['texts']):
            key=re.match(r'.*?[0-9]+[A-Z]*',name).group() if re.match(r'.*?[0-9]+[A-Z]*',name) else key
        texts=[t for t in d['texts'] if key in t['fields']['正文']]
        out.append('\nDATE '+node+' BATCH '+b+'\n'+json.dumps([{'row':r['row'],'country':r['data']['国家地区'],'platform':r['data'].get('目标类型',r['data'].get('机舰名')),'quantity':r['data'].get('目标数量',r['data'].get('数量')),'task':r['data']['任务'],'region':r['data'].get('活动区域'),'time':r['data'].get('位置时间',r['data'].get('发现时间')),'xy':[r['data'].get('经度'),r['data'].get('纬度')],'anchor':[r['data'].get('开始经度'),r['data'].get('开始纬度')],'interval':[r['data'].get('首点时间'),r['data'].get('结束时间')]} for r in rr],ensure_ascii=False)+'\n'+'\n'.join(t['source']+' '+t['file']+'\n'+t['fields']['正文'] for t in texts))
(V/'audit/holdout_raw_review.txt').write_text('\n'.join(out),encoding='utf-8')
print('\n'.join(out))
