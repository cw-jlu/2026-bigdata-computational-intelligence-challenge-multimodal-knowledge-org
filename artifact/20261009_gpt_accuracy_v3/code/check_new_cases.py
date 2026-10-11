"""Evaluate frozen raw-review labels; never import the event generator."""
import argparse,hashlib,json
from pathlib import Path
V=Path(__file__).resolve().parents[1]
def run(split,events_path,out):
    source=V/'audit'/f'new_{split}_cases.json'; spec=json.loads(source.read_text(encoding='utf-8'))
    events=list(map(json.loads,events_path.open(encoding='utf-8'))); results=[]
    for c in spec['cases']:
        ee=[e for e in events if e['date']==c['date'] and e['batch']==c['batch'] and e['decision']=='纳入'];errors=[]
        if c['label_status']!='human_reviewed': errors.append('人工定位无效，不能计作算法通过')
        elif len(ee)!=c['included']: errors.append(f"纳入起数期望{c['included']}实际{len(ee)}")
        for key,value in c.get('fields',{}).items():
            if not ee or any(e[key]!=value for e in ee): errors.append(f'字段{key}期望{value}实际{[e.get(key) for e in ee]}')
        results.append({'id':c['id'],'date':c['date'],'batch':c['batch'],'expected':c.get('included'),'basis':c['basis'],'ok':not errors,'errors':errors,'actual':[{k:e[k] for k in ['event_id','country','platform','quantity','interval','region','task']} for e in ee],'raw_locations':[{'file':r['file'],'sheet':r['sheet'],'row':r['row']} for r in c.get('raw_radar',[])]})
    result={'split':split,'label_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'denominator':len(results),'passed':sum(r['ok'] for r in results),'included_stratum':sum(c.get('included',0)>0 for c in spec['cases']),'excluded_stratum':sum(c.get('included')==0 for c in spec['cases']),'limitations':spec['method'],'results':results}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({k:result[k] for k in ['split','denominator','passed','included_stratum','excluded_stratum']},ensure_ascii=False));print(json.dumps([r for r in results if not r['ok']],ensure_ascii=False))
    return all(r['ok'] for r in results)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['development','reserved'],required=True);p.add_argument('--events',type=Path,default=V/'output/中间证据/events.jsonl');p.add_argument('--out',type=Path);a=p.parse_args();raise SystemExit(0 if run(a.split,a.events,a.out or V/'audit'/f'new_{a.split}_results.json') else 1)
