"""Raw input -> auditable evidence without authoring any submission document."""
import argparse,json,time,hashlib
from pathlib import Path
from events import process_day,date,NODES

def write_jsonl(path,records):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as f:
        for r in records:f.write(json.dumps(r,ensure_ascii=False,default=str)+'\n')

def extract(inp,out,nodes=NODES):
    inp=inp.resolve();root=inp.parents[1];start=time.perf_counter();cache={};stats=[];manifest=[]
    for d in sorted(inp.iterdir(),key=lambda p:date(p.name)):
        if not d.is_dir() or date(d.name)>max(map(date,nodes)):continue
        ee,ev=process_day(d,root);cache[d.name]=ee
        write_jsonl(out/'evidence'/f'{d.name}.events.jsonl',ee)
        for name,data in ev.items():write_jsonl(out/'evidence'/f'{d.name}.{name}.jsonl',data)
        for f in sorted(d.rglob('*')):
            if f.is_file():manifest.append({'path':f.relative_to(root).as_posix(),'date':d.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
        stats.append({'date':d.name,'radar_candidates':len(ee),'included':sum(e['decision']=='纳入' for e in ee),'outside':sum(e['decision']=='域外' for e in ee),'excluded':sum(e['decision']=='排除' for e in ee),'unmatched_atoms':len(ev['unmatched_atoms']),'documents':len(ev['documents']),'atoms':len(ev['atoms'])})
        print(d.name,stats[-1]['included'],flush=True)
    write_jsonl(out/'evidence/input_manifest.jsonl',manifest)
    write_jsonl(out/'evidence/all_events.jsonl',[e for ee in cache.values() for e in ee])
    (out/'extraction.json').write_text(json.dumps({'seconds':round(time.perf_counter()-start,2),'days':stats},ensure_ascii=False,indent=2),encoding='utf-8')
    return cache

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--nodes',nargs='+',default=NODES);a=p.parse_args();extract(a.input,a.output,a.nodes)
