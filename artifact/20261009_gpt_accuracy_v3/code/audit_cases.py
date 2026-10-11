"""Independent annotated raw-source fixtures, separate from rendering code."""
import argparse
import json
from pathlib import Path
from fusion import build_day

V=Path(__file__).resolve().parents[1]

def run(snapshot,out):
    spec=json.loads((V/'audit/independent_cases.json').read_text(encoding='utf-8'))
    required=set(c['date'] for c in spec['cases'])
    days={d['date']:d for d in (json.loads(x) for x in snapshot.open(encoding='utf-8')) if d['date'] in required}
    data={d:build_day(raw) for d,raw in days.items()}
    results=[]
    for c in spec['cases']:
        events,claims,tracks,_=data[c['date']]
        tt=[t for t in tracks if t['batch']==c['batch']]
        ee=[e for e in events if e['batch']==c['batch']]
        errors=[]; evidence={'radar':[{'file':t['radar_file'],'sheet':t['kind'],'rows':t['rows']} for t in tt]}
        if not tt: errors.append('找不到标注雷达原始批号')
        if 'source' in c:
            docs=[t for t in days[c['date']]['texts'] if t['source']==c['source'] and Path(t['file']).name.startswith(c['file_prefix'])]
            if len(docs)!=1: errors.append('原始文件定位不唯一')
            else:
                evidence['text']={'file':docs[0]['file'],'body':docs[0]['fields']['正文']}
                cc=[x for x in claims if x['file']==docs[0]['file'] and x['platform']==c['expected'].get('platform')]
                if len(cc)!=1: errors.append('平台子事实解析数量不正确')
                else:
                    x=cc[0]; evidence['parsed']=x
                    for f,v in c['expected'].items():
                        actual=x['tasks'] if f=='task' else x.get(f)
                        if (f=='task' and v not in actual) or (f!='task' and actual!=v): errors.append(f'字段{f}:期望{v},实际{actual}')
                    links=[a for e in ee for a in e['candidates'] if a['claim_id']==x['claim_id']]
                    associated=any(a['eligible'] for a in links)
                    evidence['links']=links
                    if associated!=c['should_associate']: errors.append(f'应关联={c["should_associate"]}，实际={associated}')
        if 'expect_inclusion' in c:
            actual=any(e['decision']=='纳入' for e in ee)
            if actual!=c['expect_inclusion']: errors.append(f'应纳入={c["expect_inclusion"]}，实际={actual}')
            evidence['decisions']=[{'event_id':e['event_id'],'decision':e['decision'],'reasons':e['reasons'],'corrections':e['corrections']} for e in ee]
        if 'expect_task' in c and any(e['task']!=c['expect_task'] for e in ee if e['decision']=='纳入'):
            errors.append('不应把平台名称或单源雷达任务升级为核实任务')
        if 'expect_competing_tracks' in c and len(tt)!=c['expect_competing_tracks']: errors.append('竞争轨迹分支数不符')
        results.append(dict(id=c['id'],category=c['category'],basis=c['basis'],ok=not errors,errors=errors,evidence=evidence))
    out.write_text(json.dumps({'annotation_method':spec['annotation_method'],'cases':len(results),'passed':sum(x['ok'] for x in results),'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(results),'passed':sum(x['ok'] for x in results),'failures':[{k:x[k] for k in ['id','errors']} for x in results if not x['ok']]},ensure_ascii=False))
    return results

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path,default=V/'audit/cases_first_run.json'); args=p.parse_args()
    results=run(V/'audit/raw_snapshot.jsonl',args.out)
    raise SystemExit(1 if any(not r['ok'] for r in results) else 0)
