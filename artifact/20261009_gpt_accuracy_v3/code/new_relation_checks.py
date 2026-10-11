"""Supplemental development assertions; manual labels precede evaluation.

These reuse four development cases, and must not increase the independent
sample denominator. This module never imports the fusion generator.
"""
import argparse, hashlib, json
from pathlib import Path
V=Path(__file__).resolve().parents[1]

def freeze():
    path=V/'audit/new_relation_expectations.json'
    if path.exists(): raise SystemExit('Frozen labels already exist; do not overwrite')
    specs=[
        ('2025.5.10','AIR-AF10F9EBB9E18A','开源军情','048','P1',True,1,'日本P-1与SH-60K共享编队区域，但全文明确P-1为1架；SH-60K的2架不能转移给P-1。'),
        ('2025.5.10','AIR-AF10F9EBB9E18A','开源军情','048','SH60K',False,2,'同一编队不等于同一平台；P-1雷达不能关联SH-60K子证据。'),
        ('2025.5.10','AIR-093CB109918635','开源军情','023','RC135W',True,2,'正文英国RC-135W为2架；共有编队区域可以支持关联，缺网上舆论仍不能纳入。'),
        ('2025.5.10','AIR-093CB109918635','开源军情','023','P8A',False,1,'英国P-8A子证据不能用来证明RC-135W数量或平台。'),
        ('2025.6.17','SHIP-37F0DC0E1C2114','开源军情','041','075',True,1,'同编队075与901可分别关联各自平台；早段连云港05:56—07:21支持075。'),
        ('2025.6.17','SHIP-37F0DC0E1C2114','开源军情','035','075',False,1,'晚段20:20—22:45黄海的同型075不支持早段连云港活动。'),
        ('2025.6.17','AIR-EE80F16DB64B1B','开源军情','001','CF188',True,1,'早段温州08:03—10:28与完整雷达一致。'),
        ('2025.6.17','AIR-EE80F16DB64B1B','开源军情','015','CF188',False,1,'晚段油气田17:42—19:12不能关联早段温州。'),
        ('2025.6.17','AIR-EE80F16DB64B1B','网上舆论','030','CF188',True,1,'东海联合巡逻1架的宽区域文本可以兼容早段，但不能覆盖晚段同事件明确数量反证。'),
        ('2025.6.17','AIR-EE80F16DB64B1B','网上舆论','046','CF188',False,2,'晚段油气田2架且时刻明确，不支持早段1架。'),
    ]
    dev=json.loads((V/'audit/new_development_cases.json').read_text(encoding='utf-8'))['cases']
    rows=[]
    for i,(date,batch,source,prefix,platform,expected,quantity,basis) in enumerate(specs,1):
        case=next(c for c in dev if c['date']==date and c['batch']==batch)
        raw=[r for r in case['raw_texts'] if source+'/' +prefix+'_' in r['file'].replace('\\','/')]
        if len(raw)!=1: raise ValueError((prefix,len(raw)))
        rows.append(dict(id=f'R{i:02}',date=date,batch=batch,source=source,file_prefix=prefix,platform=platform,should_associate=expected,quantity=quantity,basis=basis,raw_text=raw[0],raw_radar=case['raw_radar']))
    path.write_text(json.dumps({'method':'从已保存的四个开发案例完整原始正文和雷达人工补写10个关系/字段断言；不是新增独立样本，不能与26或24累加。先保存期望再执行checker。','assertions':rows},ensure_ascii=False,indent=2),encoding='utf-8')

def check():
    path=V/'audit/new_relation_expectations.json';spec=json.loads(path.read_text(encoding='utf-8'))
    events=list(map(json.loads,(V/'output/中间证据/events.jsonl').open(encoding='utf-8')))
    claims=list(map(json.loads,(V/'output/中间证据/claims.jsonl').open(encoding='utf-8')))
    links=list(map(json.loads,(V/'output/中间证据/candidate_links.jsonl').open(encoding='utf-8')))
    results=[]
    for s in spec['assertions']:
        cc=[c for c in claims if c['date']==s['date'] and c['source']==s['source'] and '/'+s['file_prefix']+'_' in c['file'].replace('\\','/') and c['platform']==s['platform']]
        trackids={e['track_id'] for e in events if e['date']==s['date'] and e['batch']==s['batch']}
        ll=[x for x in links if x['track_id'] in trackids and x['claim_id'] in {c['claim_id'] for c in cc}]
        associated=any(x['eligible'] for x in ll)
        errors=[]
        if len(cc)!=1: errors.append('平台子证据数量不等于1')
        if any(c['quantity']!=s['quantity'] for c in cc): errors.append('数量解析错误')
        if associated!=s['should_associate']: errors.append('关联判定不同于人工预期')
        results.append({'id':s['id'],'ok':not errors,'errors':errors,'expected_relation':s['should_associate'],'actual_relation':associated,'actual_quantities':[c['quantity'] for c in cc],'claims':[c['claim_id'] for c in cc],'links':ll})
    out={'denominator':10,'passed':sum(r['ok'] for r in results),'positive':5,'negative':5,'distinct_existing_development_cases':4,'label_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'limitation':spec['method'],'results':results}
    (V/'audit/new_relation_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False));return all(r['ok'] for r in results)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','check']);a=p.parse_args()
    if a.action=='freeze':freeze()
    else:raise SystemExit(0 if check() else 1)
