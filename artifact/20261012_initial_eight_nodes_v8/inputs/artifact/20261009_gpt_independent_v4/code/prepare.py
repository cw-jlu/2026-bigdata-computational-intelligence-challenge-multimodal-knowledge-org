"""Prepare daily output payloads; all content outside trend is today's accepted facts."""
import argparse,json
from collections import Counter
from pathlib import Path
from events import NODES,choose_chain,date

AIR_COLS=['日期','星期','国家地区','机型','批号','批次','架次','起飞基地','呼号','起飞时间','降落时间','活动方向','活动区域','任务描述','任务类型','备注']
SHIP_COLS=['日期','国家地区','舰船','批号','艘次','活动时间','活动方向','活动区域','任务','母港','备注']
CHART_NAMES=['01_舰机侦巡数量曲线图.png','02_中国主要机舰活动示意图.png','03_美国主要机舰活动示意图.png','04_其他国家主要机舰活动示意图.png']

def make(out,nodes=NODES):
    ee=[json.loads(l) for l in (out/'evidence/all_events.jsonl').read_text(encoding='utf-8').splitlines()];cache={}
    for e in ee:cache.setdefault(e['date'],[]).append(e)
    allid={e['id']:e for e in ee};payloads=[]
    for day in nodes:
        today=cache[day];accepted=sorted([e for e in today if e['decision']=='纳入'],key=lambda e:(e['kind'],e['facts']['direction'],e['facts']['country'],e['facts']['start'],e['key']))
        for i,e in enumerate(accepted,1):e['ref']=f'D{i:02d}'
        chain=choose_chain(day,{d:es for d,es in cache.items() if date(d)<=date(day)})
        if chain:
            chain['evidence']=[allid[i] for i in chain['events']]
            for g in chain['stages']:g['evidence']=[allid[i] for i in g['events']]
        rows={'飞机':[],'舰艇':[]}
        for e in accepted:
            f=e['facts'];remarks=f'{e["ref"]} {e["id"]}；活动{f["start"]}—{f["end"]}。'
            # Radar starts/ends are observation intervals; never equate to takeoff/landing.
            if e['base_candidate']:remarks+='雷达单源'+('起飞机场' if e['kind']=='飞机' else '出航港口')+'候选：'+e['base_candidate']+'。'
            remarks+='三源关联；逐字段支持见中间证据。'
            if e['kind']=='飞机':
                row=[day,'星期'+'一二三四五六日'[date(day).weekday()],f['country'],e['platform'],e['batch'],1,f['quantity'],None,None,None,None,f['direction'],f['region'],f'{f["start"]}—{f["end"]}在{f["region"]}执行{f["task"]}',f['task'],remarks]
            else:
                row=[day,f['country'],e['platform'],e['batch'],f['quantity'],f'{f["start"]}—{f["end"]}',f['direction'],f['region'],f['task'],None,remarks]
            rows[e['kind']].append(row)
        counts={'included':len(accepted),'excluded':sum(e['decision']=='排除' for e in today),'outside':sum(e['decision']=='域外' for e in today),
                'radar_candidates':len(today),'air':sum(e['facts']['quantity'] for e in accepted if e['kind']=='飞机'),'ship':sum(e['facts']['quantity'] for e in accepted if e['kind']=='舰艇'),
                'directions':dict(Counter(e['facts']['direction'] for e in accepted)),'countries':dict(Counter(e['facts']['country'] for e in accepted))}
        p={'day':day,'counts':counts,'events':accepted,'chain':chain,'xlsx':{'飞机':{'columns':AIR_COLS,'rows':rows['飞机']},'舰艇':{'columns':SHIP_COLS,'rows':rows['舰艇']}},
           'charts':CHART_NAMES,'excluded':[{'id':e['id'],'platform':e['platform'],'issues':e['issues'],'field_audit':e['field_audit']} for e in today if e['decision']=='排除']}
        folder=out/'payloads';folder.mkdir(exist_ok=True);(folder/(day+'.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8');payloads.append(p)
    (out/'node_counts.json').write_text(json.dumps([{'day':p['day'],**p['counts']} for p in payloads],ensure_ascii=False,indent=2),encoding='utf-8')
    return payloads

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args();make(x.output)
