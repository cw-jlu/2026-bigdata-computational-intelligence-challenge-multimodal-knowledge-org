"""Raw-only inventory. Does not import the event matcher or any prior artifact."""
import json
from pathlib import Path
from collections import Counter, defaultdict
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parents[1] / 'audit'
DEST.mkdir(exist_ok=True)
vocab = defaultdict(Counter)
summary = []
for day in sorted((ROOT / '赛题2-初赛/数据').iterdir()):
    if not day.is_dir(): continue
    w = load_workbook(next(day.glob('*.xlsx')), data_only=True)
    for s in w:
        rows = list(s.values); hdr = rows[0]; groups = defaultdict(list)
        for i, v in enumerate(rows[1:], 2):
            r = dict(zip(hdr, v)); groups[r['批号']].append({'row': i, **r})
            for f in ['国家地区','目标类型','机舰名','活动区域','任务','起飞机场','出航港口']:
                if f in r: vocab[f][str(r[f])] += 1
        for batch, rr in groups.items():
            fields = ['国家地区','目标类型','任务','目标数量','开始经度','开始纬度'] if s.title == '飞机' else ['国家地区','机舰名','任务','数量','活动区域','首点时间','结束时间']
            summary.append({'date': day.name, 'sheet': s.title, 'batch': batch,
                            'fields': {f:dict(Counter(str(r[f]) for r in rr)) for f in fields}, 'rows': rr})
    w.close()
(DEST/'raw_inventory.json').write_text(json.dumps(vocab,ensure_ascii=False,indent=2),encoding='utf-8')
(DEST/'raw_batches.jsonl').write_text('\n'.join(json.dumps(r,ensure_ascii=False,default=str) for r in summary),encoding='utf-8')
print({k:len(v) for k,v in vocab.items()})
