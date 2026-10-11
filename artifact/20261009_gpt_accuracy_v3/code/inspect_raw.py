"""Read only the original competition input; no other implementations are imported."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[3]
VERSION = Path(__file__).resolve().parents[1]

def main(input_root=None,audit=None):
    input_root=input_root or ROOT/'赛题2-初赛/数据'; audit=audit or VERSION/'audit'; audit.mkdir(parents=True,exist_ok=True)
    days = sorted((p for p in input_root.iterdir() if p.is_dir()), key=lambda p: datetime.strptime(p.name, '%Y.%m.%d'))
    raw, vocab = [], defaultdict(Counter)
    manifests=[]
    def source_id(p): return '赛题2-初赛/数据/'+p.relative_to(input_root).as_posix()
    def fingerprint(p):
        manifests.append({'file':source_id(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    for day in days:
        if datetime.strptime(day.name, '%Y.%m.%d') > datetime(2025, 7, 17):
            continue
        texts = []
        for source in ['开源军情', '网上舆论']:
            for p in sorted((day/source).glob('*.txt')):
                text = p.read_text(encoding='utf-8-sig')
                fields = dict(re.findall(r'^(抄收时间|发文时间|时间|标题|正文|主题词)[：:]\s*(.*)$', text, re.M))
                fingerprint(p)
                texts.append(dict(source=source, file=source_id(p), text=text, fields=fields))
        p = next(day.glob('*.xlsx'))
        fingerprint(p)
        w = load_workbook(p, read_only=True, data_only=True)
        radar = []
        for s in w:
            rows = iter(s.values); headers = next(rows)
            for n, values in enumerate(rows, 2):
                r = dict(zip(headers, values))
                radar.append(dict(sheet=s.title, row=n, file=source_id(p), data=r))
                for key in ['国家地区','目标类型','机舰名','任务','活动区域','起飞机场','出航港口']:
                    if key in r: vocab[key][str(r[key])] += 1
        w.close()
        raw.append(dict(date=day.name, texts=texts, radar=radar))
        print('raw input parsed',day.name,flush=True)
    (audit/'raw_inventory.json').write_text(json.dumps({k:dict(v) for k,v in vocab.items()}, ensure_ascii=False, indent=2), encoding='utf-8')
    (audit/'input_manifest.json').write_text(json.dumps({'input_root':str(input_root.resolve()),'cutoff':'2025.7.17','files':manifests},ensure_ascii=False,indent=2),encoding='utf-8')
    with (audit/'raw_snapshot.jsonl').open('w',encoding='utf-8') as f:
        for day in raw: f.write(json.dumps(day,ensure_ascii=False,default=str)+'\n')
    for d in raw:
        if d['date']!='2025.5.10': continue
        lines=[]
        for t in d['texts']: lines.append(f"{t['source']} | {Path(t['file']).name}\n{t['fields'].get('正文','')}\n")
        for sheet in ['飞机','舰船']:
            groups=defaultdict(list)
            for r in d['radar']:
                if r['sheet']==sheet: groups[r['data']['批号']].append(r)
            for batch, group in groups.items():
                keys=['国家地区','目标类型','机舰名','目标数量','数量','任务','活动区域','位置时间','首点时间','结束时间','经度','纬度','开始经度','开始纬度']
                vals={k:list(dict.fromkeys(str(r['data'][k]) for r in group if k in r['data'])) for k in keys}
                lines.append(f"{sheet} {batch} rows={[r['row'] for r in group]} {vals}\n")
        (audit/'day_2025.5.10_raw_review.txt').write_text('\n'.join(lines),encoding='utf-8')
    print({'days':len(raw),'texts':sum(len(d['texts']) for d in raw),'radar_rows':sum(len(d['radar']) for d in raw)})

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'赛题2-初赛/数据');p.add_argument('--audit',type=Path,default=VERSION/'audit');a=p.parse_args();main(a.input,a.audit)
