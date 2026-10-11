"""Authorized v2 comparison and source-review issue table. No score estimation."""
import hashlib,json
from pathlib import Path
from collections import Counter
V=Path(__file__).resolve().parents[1];B=V.parent/'20261009_gpt_accuracy_v2'
old=list(map(json.loads,(B/'output/中间证据/events.jsonl').open(encoding='utf-8')))
new=list(map(json.loads,(V/'output/中间证据/events.jsonl').open(encoding='utf-8')))
nodes=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
fields=['country','platform','platform_key','quantity','interval','region','direction','task','claims']
records=[]
for day in nodes:
    oo={e['event_id']:e for e in old if e['date']==day};nn={e['event_id']:e for e in new if e['date']==day}
    changes=[]
    for eventid in sorted(oo.keys()|nn.keys()):
        a,b=oo.get(eventid),nn.get(eventid)
        diff={f:{'v2':a.get(f) if a else None,'v3':b.get(f) if b else None} for f in [*fields,'decision','reasons'] if (a.get(f) if a else None)!=(b.get(f) if b else None)}
        if diff:changes.append({'event_id':eventid,'batch':(b or a)['batch'],'diff':diff})
    oldids={k for k,e in oo.items() if e['decision']=='纳入'};newids={k for k,e in nn.items() if e['decision']=='纳入'}
    op=json.loads((B/f'output/中间证据/factpack_{day}.json').read_text(encoding='utf-8'));np=json.loads((V/f'output/中间证据/factpack_{day}.json').read_text(encoding='utf-8'))
    slim=lambda tr:{k:tr[k] for k in ['country','platform','dates','phases']} if tr else None
    records.append({'date':day,'v2_included':len(oldids),'v3_included':len(newids),'v2_excluded':len(oo)-len(oldids),'v3_excluded':len(nn)-len(newids),'retained':sorted(oldids&newids),'added':sorted(newids-oldids),'removed':sorted(oldids-newids),'all_candidate_changes':changes,'mainline':{'v2':slim(op['trend']),'v3':slim(np['trend'])},'v3_air_quantity':sum(e['quantity'] for e in nn.values() if e['decision']=='纳入' and e['kind']=='飞机'),'v3_ship_quantity':sum(e['quantity'] for e in nn.values() if e['decision']=='纳入' and e['kind']=='舰船')})
(V/'audit/v2_comparison.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
spec=json.loads((V/'audit/new_development_cases.json').read_text(encoding='utf-8'));results=json.loads((V/'audit/new_development_results.json').read_text(encoding='utf-8'))
rr={r['id']:r for r in results['results']};table=[]
for c in spec['cases']:
    baseline=[e for e in old if e['date']==c['date'] and e['batch']==c['batch'] and e['decision']=='纳入']
    current=[e for e in new if e['date']==c['date'] and e['batch']==c['batch'] and e['decision']=='纳入']
    errors=[]
    if len(baseline)!=c['included']:errors.append('纳入判定不符合原始复核预期')
    for k,v in c['fields'].items():
        if any(e[k]!=v for e in baseline):errors.append('字段'+k+'不符合原始预期')
    table.append({'id':c['id'],'date':c['date'],'batch':c['batch'],'classification':'已确认v2问题' if errors else '已核查边界或正确案例','original_locations':rr[c['id']]['raw_locations'],'expected_relation':c['included'],'key_basis':c['basis'],'v2_behavior':{'included':len(baseline),'fields':[{k:e[k] for k in fields[:-1]} for e in baseline]},'fix':'同事件明确第三源反证不得被备选证据覆盖；先排除晚段冲突再解决文本独占' if errors else '保持原判定；增强全点及逐字段追溯，不宣称本条为失分位置','validation':{'v3_included':len(current),'source_case_passed':rr[c['id']]['ok']},'official_deduction':None})
(V/'audit/problem_table.json').write_text(json.dumps(table,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 原始证据诊断问题表','','官方未提供逐节点或逐事件扣分，下面是工程源证据复核，不是扣分定位。完整原始字段和全部Excel行在同名JSON及诊断审阅包。','','|案例|日期与批号|原始Excel定位|预期与关键依据|v2行为|修复与验证|','|---|---|---|---|---|---|']
for x in table:
    row=x['original_locations'];loc=row[0]['file']+' '+row[0]['sheet']+' 行'+','.join(str(r['row']) for r in row)
    lines.append('|'+ '|'.join([x['id'],x['date']+' '+x['batch'],loc,str(x['expected_relation'])+'起；'+x['key_basis'],str(x['v2_behavior']['included'])+'起；'+x['classification'],x['fix']+'；通过='+str(x['validation']['source_case_passed'])])+'|')
(V/'audit/problem_table.md').write_text('\n'.join(lines),encoding='utf-8')
# A provenance audit compares preexisting allowed reference hashes, without
# using or reading any other versions or their running intermediate results.
freeze=json.loads((V/'audit/baseline_freeze.json').read_text(encoding='utf-8'));root=V.parents[1]
preserved=[{'file':r['file'],'unchanged':hashlib.sha256((root/r['file']).read_bytes()).hexdigest()==r['sha256']} for r in freeze['references']]
(V/'audit/baseline_preservation.json').write_text(json.dumps({'checked':len(preserved),'all_unchanged':all(r['unchanged'] for r in preserved),'results':preserved},ensure_ascii=False,indent=2),encoding='utf-8')
print('Comparison written. Added:',sum(len(r['added']) for r in records),'removed:',sum(len(r['removed']) for r in records),'confirmed development issues:',sum(r['classification']=='已确认v2问题' for r in table))
