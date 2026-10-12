from common import *
import sys,collections,argparse
from docx import Document
from openpyxl import load_workbook
def chain_options(cache,node):
    seeds={(e['facts']['country'],e['key']) for e in cache[node] if e['decision']=='纳入' and e['facts']['country']!='中国'};options=[]
    for country,key in sorted(seeds):
        hist=[e for d,ee in cache.items() if dt(d)<=dt(node) for e in ee if e['decision']=='纳入' and e['facts']['country']==country and e['key']==key]
        dates=sorted({e['date'] for e in hist},key=dt);cut=0
        for i in range(1,len(dates)):
            if (dt(dates[i])-dt(dates[i-1])).days>=15:cut=i
        dates=dates[cut:];hist=[e for e in hist if e['date'] in dates];stages=[]
        for d in dates:
            ee=[e for e in hist if e['date']==d];sig=(tuple(sorted({e['facts']['direction'] for e in ee})),tuple(sorted({e['facts']['task'] or '未知' for e in ee})))
            if not stages or stages[-1]['signature']!=sig or (dt(d)-dt(stages[-1]['dates'][-1])).days>7:stages.append({'signature':sig,'dates':[d],'events':[e['id'] for e in ee]})
            else:stages[-1]['dates'].append(d);stages[-1]['events'].extend(e['id'] for e in ee)
        quality=sum(bool(e['facts']['task'])+bool(e['facts']['start'])+bool(e['facts']['end'])+(e['facts']['region'] not in ['东海','南海','黄海']) for e in hist)/(4*len(hist)) if hist else 0
        suitable=len(dates)>=3 and 2<=len(stages)<=3
        score=(int(suitable),quality,int(any(len(s['dates'])>1 for s in stages)),len({e['facts']['direction'] for e in hist}),min(len(dates),8))
        options.append({'country':country,'key':key,'platform':hist[-1]['facts']['platform'],'dates':dates,'events':[e['id'] for e in hist],'stages':stages,'score':score,'quality':quality,'suitable':suitable,'identity_scope':'具名舰艇专名活动' if '号' in hist[-1]['platform'] and hist[-1]['kind']=='舰艇' else '同主体同型平台，未证明同一实体','assessment':'按当日相关性、字段支持质量、明确空间/任务变化、阶段证据和覆盖比较；不以日期数量单独决定'})
    options.sort(key=lambda c:(c['score'],c['country'],c['key']),reverse=True);return options
def history(out,node,today):
    places={'Claude':ROOT/f'artifact/20261008_001929_claude-opus-5.5high/output/中间结果/{node}/events.jsonl','v2':ROOT/f'artifact/20261009_gpt_accuracy_v2/output/中间证据/factpack_{node}.json','v3':ROOT/f'artifact/20261009_gpt_accuracy_v3/output/中间证据/factpack_{node}.json','v4':ROOT/f'artifact/20261009_gpt_independent_v4/output/payloads/{node}.json'};histories={};records=[]
    for v,p in places.items():
        if p.exists():
            obj=[json.loads(l) for l in p.read_text(encoding='utf8').splitlines() if l.strip()] if p.suffix=='.jsonl' else load(p);ee=obj if isinstance(obj,list) else obj.get('events',[]);histories[v]=ee
            save(out/f'audits/{node}/historical/{v}.json',obj);records.append({'version':v,'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'reading_status':'pipeline_read_full_records','events':len(ee)})
        else:histories[v]=[];records.append({'version':v,'path':p.relative_to(ROOT).as_posix(),'reading_status':'missing'})
    diffs=[]
    for e in today:
        old={v:[q for q in xx if e['batch'] in json.dumps(q,ensure_ascii=False)] for v,xx in histories.items()};action='保留并重新核验' if e['decision']=='纳入' and old.get('v4') else '新增或恢复' if e['decision']=='纳入' else '移除历史候选' if any(old.values()) else '排除或域外原始候选'
        diffs.append({'event_id':e['id'],'action':action,'decision':e['decision'],'facts':e['facts'],'basis':{'field_audit':e['field_audit'],'issues':e['issues'],'radar_file':e['radar_file'],'sheet':e['sheet'],'rows':[r['row'] for r in e['rows']],'claims':e['claims']},'historical_matches':old,'field_corrections':{'region_precision':e['field_audit']['region'].get('precision_limit'),'unknown_task':e['facts']['task'] is None,'start_end_are_observations_not_takeoff_landing':e['kind']=='飞机'}})
    save(out/f'audits/{node}/version_diff.json',diffs);return records
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=BASE);ap.add_argument('--resume',action='store_true');a=ap.parse_args();out=a.output.resolve();import events
    sample=ROOT/'提交示例文件/日报/2025.10.20';doc=Document(sample/'2025.10.20日报.docx');w=load_workbook(sample/'2025.10.20机舰活动明细.xlsx')
    structure={'reference_sha256':sha(sample/'2025.10.20日报.docx'),'sections':[{k:getattr(s,k).cm for k in ['page_width','page_height','top_margin','bottom_margin','left_margin','right_margin']} for s in doc.sections],'paragraphs':[{'index':i,'text':p.text,'style':p.style.name,'xml':p._p.xml} for i,p in enumerate(doc.paragraphs)],'sheets':[{'name':s.title,'headers':[c.value for c in s[1]],'types':[[c.data_type for c in r] for r in list(s.rows)[1:4]],'sample_values':[[c.value for c in r] for r in list(s.rows)[1:4]],'widths':{k:v.width for k,v in s.column_dimensions.items()}} for s in w]};save(out/'evidence/sample_structure.json',structure)
    reads=[]
    for fold in ['artifact/20261008_001929_claude-opus-5.5high/bdci','artifact/20261009_gpt_accuracy_v2/code','artifact/20261009_gpt_accuracy_v3/code','artifact/20261009_gpt_independent_v4/code']:
        for p in sorted((ROOT/fold).glob('*.py')):
            text=p.read_text(encoding='utf-8-sig');reads.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'chars':len(text),'status':'pipeline_full_code_read_for_comparison'})
    save(out/'evidence/historical_code_inventory.json',reads);cache={};manifest=[];start=dt('2025.5.1')
    for node in NODES:
        end=dt(node)
        for offset in range((end-start).days+1):
            day=start+datetime.timedelta(days=offset);d=f'{day.year}.{day.month}.{day.day}'
            if d in cache:continue
            folder=ROOT/'赛题2-初赛/数据'/d;texts=[]
            for p in sorted(folder.rglob('*')):
                if not p.is_file():continue
                manifest.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size,'date':day.isoformat()})
                if p.suffix=='.txt':texts.append({'path':p.relative_to(ROOT).as_posix(),'text':p.read_text(encoding='utf-8-sig'),'sha256':sha(p)})
                if p.suffix=='.xlsx':
                    rw=load_workbook(p,data_only=True);save(out/f'evidence/daily/{d}/radar.json',{'path':p.relative_to(ROOT).as_posix(),'sheets':{s.title:[{'row':i,'values':r} for i,r in enumerate(s.values,1)] for s in rw}});rw.close()
            cp=out/f'evidence/daily/{d}/candidate_ledger.json';xp=out/f'evidence/daily/{d}/extraction.json';rp=out/f'evidence/daily/{d}/raw_texts.json'
            if a.resume and all(p.exists() and p.stat().st_size for p in [cp,xp,rp]):
                previous=load(rp);assert [(x['path'],x['sha256']) for x in texts]==[(x['path'],x['sha256']) for x in previous];ee,xx=load(cp),load(xp)
            else:ee,xx=events.process_day(folder,ROOT,as_of=node)
            cache[d]=ee
            for name,obj in [('raw_texts',texts),('candidate_ledger',ee),('extraction',xx)]:save(out/f'evidence/daily/{d}/{name}.json',obj)
        selected=[e for e in cache[node] if e['decision']=='纳入'];selected.sort(key=lambda e:(e['kind']!='飞机',e['facts']['country']!='中国',e['facts']['country'],e['start'] or 0,e['batch']))
        for i,e in enumerate(selected,1):e['ref']=f'F{i:02d}'
        opts=chain_options(cache,node);chosen=next((x for x in opts if x['suitable']),None)
        frozen={'schema_version':2,'as_of':end.isoformat(),'verification_scope':f'2025-05-01至{end.isoformat()}全部每日100篇TXT与完整雷达批次，三源关联及逐字段冲突闸门','today_events':selected,'verified_events':[e for d,ee in cache.items() if dt(d)<=end for e in ee if e['decision']=='纳入'],'candidate_comparison':opts,'mainline':chosen,'count_basis':'独立活动参与数量之和；架次/艘次不是去重实体、舰日或报道数','unknown_policy':'不足两类支持的辅助字段留空；明确冲突不能留空绕过；飞机观测起止不作起降','geography_limits':'坐标窗口仅做相容性检查；细区域需两类明确支持；不从近似坐标窗口补造细地名'}
        save(out/f'audits/{node}/historical_read_files.json',history(out,node,cache[node]));save(out/f'audits/{node}/candidate_decisions.json',cache[node]);save(out/f'audits/{node}/frozen_ledger.json',frozen);save(out/f'audits/{node}/input_manifest.json',[x for x in manifest if x['date']<=end.isoformat()]);save(out/f'audits/{node}/freeze_record.json',{'as_of':end.isoformat(),'path':f'audits/{node}/frozen_ledger.json','sha256':sha(out/f'audits/{node}/frozen_ledger.json'),'cutoff_check':all(x['date']<=end.isoformat() for x in manifest),'frozen_before_analysis':True})
        print(node,dict(collections.Counter(e['decision'] for e in cache[node])),len(selected),'mainline',chosen and (chosen['country'],chosen['platform'],chosen['dates']),flush=True)
    save(out/'evidence/input_manifest.json',manifest)
if __name__=='__main__':main()
