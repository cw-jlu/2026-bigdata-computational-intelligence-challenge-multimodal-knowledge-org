"""Read raw full records for a stratified v2 audit. Output is review material, not labels."""
import json, sys
from pathlib import Path
from collections import defaultdict
from fusion import canon_platform,NODES
sys.stdout.reconfigure(encoding='utf-8')
V=Path(__file__).resolve().parents[1]; B=V.parent/'20261009_gpt_accuracy_v2'
raw={x['date']:x for x in map(json.loads,(V/'audit/raw_snapshot.jsonl').open(encoding='utf-8'))}
events=[e for e in map(json.loads,(B/'output/中间证据/events.jsonl').open(encoding='utf-8')) if e['date'] in NODES]
bundles=[]
for day in NODES:
    ee=[e for e in events if e['date']==day]; chosen=[]
    for decision in ['纳入','排除']:
        candidates=[e for e in ee if e['decision']==decision]
        # Ordinary first aircraft + first ship, plus edge event. No output used as truth.
        for kind in ['飞机','舰船']:
            chosen.append(next(e for e in candidates if e['kind']==kind))
    edge=next((e for e in ee if e['decision']=='纳入' and (e['competing_tracks']>1 or e['corrections'] or e['task']=='任务未核实')),None)
    if edge and edge not in chosen: chosen.append(edge)
    for e in chosen:
        rr=[r for r in raw[day]['radar'] if r['data']['批号']==e['batch']]
        texts=[t for t in raw[day]['texts'] if canon_platform(str(rr[0]['data'].get('目标类型',rr[0]['data'].get('机舰名')))) in canon_platform(t['fields']['正文']) or any(c['file']==t['file'] for c in e['candidates'])]
        bundles.append({'date':day,'batch':e['batch'],'baseline':{k:e[k] for k in ['decision','country','platform','region','interval','task','quantity','reasons','claims','radar_rows']},'raw_radar':rr,'raw_texts':texts})
(V/'audit/diagnostic_raw_bundles.json').write_text(json.dumps(bundles,ensure_ascii=False,indent=2),encoding='utf-8')
for b in bundles:
    r=b['raw_radar'][0]['data']; print('\n',b['date'],b['batch'],b['baseline'])
    keys=['国家地区','目标类型','机舰名','目标数量','数量','任务','活动区域','位置时间','首点时间','结束时间','经度','纬度','开始经度','开始纬度']
    print('RAW',{'rows':[r['row'] for r in b['raw_radar']], **{k:list(dict.fromkeys(str(r['data'][k]) for r in b['raw_radar'] if k in r['data'])) for k in keys}})
    for t in b['raw_texts']: print(t['source'],Path(t['file']).name,t['fields']['正文'])
