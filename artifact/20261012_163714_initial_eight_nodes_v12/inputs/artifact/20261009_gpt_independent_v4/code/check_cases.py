"""Read frozen manually labelled evidence. Compare; never derive expected labels."""
import argparse,json
from pathlib import Path

def check(events,cases):
    results=[]
    for c in cases:
        refs=c['refs'];op=refs['开源军情']['path'];po=refs.get('网上舆论',{}).get('path')
        candidates=[e for e in events if e['date']==c['date'] and any(a['path']==op for a in e['claims'].values())]
        if '雷达' in refs:candidates=[e for e in candidates if e['batch']==refs['雷达']['batch']]
        associated=bool(candidates and (po is None or any(any(a['path']==po for a in e['claims'].values()) for e in candidates)))
        # For absent opinion cases only open/radar association is expected.
        relevant=[e for e in candidates if po is None or any(a['path']==po for a in e['claims'].values())]
        included=any(e['decision']=='纳入' for e in relevant)
        field_errors=[]
        for f,value in c.get('expected_fields',{}).items():
            if not any(e['facts'].get(f)==value for e in relevant):field_errors.append({'field':f,'expected':value,'actual':[e['facts'].get(f) for e in relevant]})
        ok=associated==c['expect_association'] and (c['expect_include'] is None or included==c['expect_include']) and not field_errors
        results.append({'id':c['id'],'category':c['category'],'expected_association':c['expect_association'],
                        'actual_association':associated,'expected_include':c['expect_include'],'actual_include':included,
                        'ok':ok,'field_errors':field_errors,'basis':c['basis'],'events':[e['id'] for e in relevant],'issues':{e['id']:e['issues'] for e in relevant}})
    return {'n':len(results),'passed':sum(r['ok'] for r in results),'failures':[r for r in results if not r['ok']],'results':results,
            'truth_provenance':'人工从原始文本正文和Excel行判读；生成程序不读取gold_cases；抽样非全量真值'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--events',type=Path,required=True);p.add_argument('--cases',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ee=[json.loads(s) for s in a.events.read_text(encoding='utf-8').splitlines()]
    r=check(ee,json.loads(a.cases.read_text(encoding='utf-8')));a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':r['passed'],'n':r['n'],'failures':r['failures']},ensure_ascii=False,indent=2))

    if r["passed"]!=r["n"]:raise SystemExit(1)
