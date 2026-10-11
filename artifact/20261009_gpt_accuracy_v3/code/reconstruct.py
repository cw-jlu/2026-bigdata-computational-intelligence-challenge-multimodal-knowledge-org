"""Build evidence bundles from raw inputs; rendering never influences decisions."""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from collections import Counter
from fusion import NODES, build_day, choose_trend, date_value

VERSION=Path(__file__).resolve().parents[1]
ROOT=VERSION.parents[1]

def write_json(p,data): p.write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def write_jsonl(p,data):
    with p.open('w',encoding='utf-8') as f:
        for x in data: f.write(json.dumps(x,ensure_ascii=False,default=str)+'\n')

def run(snapshot,out):
    begin=time.time(); out.mkdir(parents=True,exist_ok=True)
    cache={}; claims=[]; tracks=[]; coverage=[]
    for line in snapshot.open(encoding='utf-8'):
        raw=json.loads(line)
        e,c,t,cover=build_day(raw)
        cache[raw['date']]=e; claims+=c; tracks+=t; coverage+=cover
    ev=[e for ee in cache.values() for e in ee]
    write_jsonl(out/'events.jsonl',ev); write_jsonl(out/'claims.jsonl',claims)
    write_jsonl(out/'radar_tracks.jsonl',tracks); write_jsonl(out/'source_coverage.jsonl',coverage)
    write_jsonl(out/'candidate_links.jsonl',[a for e in ev for a in e['candidates']])
    packs=[]; summary=[]
    for node in NODES:
        included=[e for e in cache[node] if e['decision']=='纳入']; excluded=[e for e in cache[node] if e['decision']=='排除']
        trend=choose_trend(node,cache)
        ids={c for e in included for c in e['claims']}
        pack={'date':node,'events':included,'excluded':excluded,'trend':trend,'claims':{c['claim_id']:c for c in claims if c['claim_id'] in ids or (trend and c['claim_id'] in {x for e in trend['evidence'] for x in e['claims']})},
            'policy':{'daily_date':node,'history_cutoff':node,'rule':'三类同一事件、字段两类支持、明确冲突排除；单源任务及基地不作为事实'}}
        write_json(out/f'factpack_{node}.json',pack); packs.append(pack)
        write_json(out/f'trend_candidates_{node}.json',trend['candidate_comparison'] if trend else [])
        summary.append({'date':node,'included':len(included),'excluded':len(excluded),'air_events':sum(e['kind']=='飞机' for e in included),'ship_events':sum(e['kind']=='舰船' for e in included),
            'air_quantity':sum(e['quantity'] for e in included if e['kind']=='飞机'),'ship_quantity':sum(e['quantity'] for e in included if e['kind']=='舰船'),
            'directions':dict(Counter(e['direction'] for e in included)),'unknown_task':sum(e['task']=='任务未核实' for e in included),
            'trend':{'country':trend['country'],'platform':trend['platform'],'dates':len(trend['dates']),'stages':len(trend['phases'])} if trend else None,
            'exclusion_reasons':dict(Counter(r for e in excluded for r in e['reasons']))})
    write_jsonl(out/'field_evidence.jsonl',[{'event_id':e['event_id'],'date':e['date'],'decision':e['decision'],'fields':e['field_evidence'],'allocation':e['evidence_allocation']} for e in ev])
    used={c for e in ev if e['decision']=='纳入' for c in e['claims']}
    write_jsonl(out/'unallocated_claims.jsonl',[{**c,'decision':'候选未纳入','reason':'没有完成三源同事件独占核验；不能把两源文字线索升级为可信日报'} for c in claims if c['claim_id'] not in used])
    write_json(out/'reconstruction_summary.json',{'days':len(cache),'events':len(ev),'included':sum(e['decision']=='纳入' for e in ev),'nodes':summary,'seconds':round(time.time()-begin,2),'python':sys.version,'os':platform.platform()})
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return packs

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--snapshot',type=Path,default=VERSION/'audit/raw_snapshot.jsonl'); p.add_argument('--output',type=Path,default=VERSION/'output/中间证据'); args=p.parse_args()
    run(args.snapshot,args.output)
