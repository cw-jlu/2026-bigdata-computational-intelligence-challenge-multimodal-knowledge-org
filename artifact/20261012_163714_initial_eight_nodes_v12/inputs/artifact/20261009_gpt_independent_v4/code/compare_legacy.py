"""Read ONLY initial GPT evidence, not any other model/version artifact."""
import argparse,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--artifact',type=Path,required=True);x=a.parse_args();base=x.artifact.resolve();root=base.parents[1]
    oldfile=root/'artifact/20261008_001028_gpt-5.6solhigh/output/中间结果/evidence.jsonl'
    old=[json.loads(l) for l in oldfile.read_text(encoding='utf-8').splitlines()]
    new=[json.loads(l) for l in (base/'output/evidence/all_events.jsonl').read_text(encoding='utf-8').splitlines()]
    nodes=json.loads((base/'output/node_counts.json').read_text(encoding='utf-8'));days={p['day'] for p in nodes};rows=[];changes=[];reuse=[]
    for p in nodes:
        d=p['day'];aa={e['batch']:e for e in old if e['date']==d and e['decision']=='纳入'};bb={e['batch']:e for e in new if e['date']==d and e['decision']=='纳入'}
        added=set(bb)-set(aa);removed=set(aa)-set(bb);common=set(aa)&set(bb)
        rows.append({'date':d,'old':len(aa),'new':len(bb),'common':len(common),'added':len(added),'removed':len(removed),'excluded':p['excluded'],'outside':p['outside'],'radar_candidates':p['radar_candidates']})
        for b in sorted(added|removed):
            ne=next(e for e in new if e['date']==d and e['batch']==b)
            changes.append({'date':d,'batch':b,'change':'新增' if b in added else '移除','new_decision':ne['decision'],'new_reason':ne['reason'],'old':aa.get(b),'new_fact':ne['facts']})
        for key in ['open_file','opinion_file']:
            uses=defaultdict(list)
            for e in aa.values():uses[e[key]].append(e['batch'])
            for file,bs in uses.items():
                if len(bs)>1:reuse.append({'date':d,'type':key,'file':file,'batches':bs})
    issue=Counter();primary=Counter()
    for e in new:
        if e['date'] not in days or e['decision']!='排除':continue
        text=' '.join(e['issues']);tags=[]
        for name,hit in [('雷达轨迹/区域异常','雷达轨迹' in text or '雷达区域明确冲突' in text),('主体冲突','country明确冲突' in text),('数量冲突','quantity明确冲突' in text),('时间冲突','start明确冲突' in text or 'end明确冲突' in text),('任务冲突','task明确冲突' in text or '多任务候选' in text),('区域冲突','关键区域冲突' in text),('字段不足两源','不足两类来源' in text),('缺来源关联','三类来源未全部' in text)]:
            if hit:tags.append(name);issue[name]+=1
        primary[tags[0] if tags else '其他']+=1
    r={'comparison':rows,'totals':{k:sum(p[k] for p in rows) for k in ['old','new','common','added','removed','excluded','outside','radar_candidates']},
       'old_accepted_reuse':reuse,'exclusion_tags_nonexclusive':dict(issue),'exclusion_primary_exclusive':dict(primary),'changes':changes,
       'old_provenance':{'path':oldfile.relative_to(root).as_posix(),'sha256':hashlib.sha256(oldfile.read_bytes()).hexdigest()},
       'interpretation':'覆盖差异按日期+雷达批号对照；批号只用于同一原始雷达事件的版本比较，不是文本对应依据。数量变化不是完整性/准确性成绩。'}
    (base/'audit/legacy_comparison.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:r[k] for k in ['comparison','totals','exclusion_primary_exclusive']},ensure_ascii=False,indent=2))
