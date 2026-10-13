"""Reconstruct facts from raw inputs only. Historical labels never feed decisions."""
from common import *
import argparse,collections,copy,re,sys
from openpyxl import load_workbook
import events
def expanded_vocabulary(folder):
    lex,regions,tasks=ORIGINAL_VOCAB(folder)
    discovered=[]
    for source in ['开源军情','网上舆论']:
        for p in sorted((folder/source).glob('*.txt')):
            text=p.read_text(encoding='utf-8-sig');m=re.search(r'正文[：:]([\s\S]*?)(?:\n\s*主题词[：:]|$)',text)
            body=m.group(1) if m else ''
            # This broad, source-independent candidate pass does not confer credibility.
            for match in re.finditer(r'(?<![A-Za-z0-9])(?:[A-Z]{1,4}[-－]?\d{1,3}[A-Z0-9]*(?:/[A-Z0-9-]+)?|歼[-－]?\d+[A-Z]*|轰[-－]?\d+[A-Z]*|空警[-－]?\d+|运[-－]?\d+|直[-－]?\d+|苏[-－]?\d+[A-Z0-9]*|米格[-－]?\d+[A-Z]*|伊尔[-－]?\d+|福克\s?50|台风|阵风)(?:[“”「」]?[^，。；\s]{0,15}?(?:战斗机|侦察机|巡逻机|预警机|运输机|直升机|轰炸机|无人机|战机))?',body):
                name=match.group();key=events.root_platform(name,'飞机')
                if key and key not in lex:lex[key]={'key':key,'name':name,'kind':'飞机','aliases':{events.norm(name),key}};discovered.append({'path':p.as_posix(),'quote':name,'key':key,'kind':'飞机','offset':match.start()})
            for match in re.finditer(r'([\u4e00-\u9fff·—\-]{2,16}号|\d{2,4}[A-Z]?型|[\u4e00-\u9fff·—\-]{2,14}级)(?:导弹)?(?:航空母舰|航母|驱逐舰|护卫舰|潜艇|补给舰|巡洋舰|两栖攻击舰|登陆舰|电子侦察船|巡逻舰|巡逻艇|直升机母舰)',body):
                name=match.group()
                # Strip actor/service prefix, retaining the vessel/class granularity.
                name=re.sub(r'^.*?(?:海军|军方|海上自卫队)','',name)
                for country in events.COUNTRIES:
                    if name.startswith(country) and not name.startswith(country+'号'):name=name[len(country):];break
                name=re.sub(r'^(?:[0-9]+|[一两二三四五六七八九十])艘','',name)
                normalized=events.norm(name)
                if any(events.norm(p['name']) in normalized or (p['kind']=='舰艇' and any(p['key']+suffix in normalized for suffix in ['号','级','型'])) for p in lex.values()):continue
                key=events.root_platform(name,'舰艇')
                if key and key not in lex:lex[key]={'key':key,'name':name,'kind':'舰艇','aliases':{events.norm(name),key+'号' if '号' in name else key}};discovered.append({'path':p.as_posix(),'quote':match.group(),'name':name,'key':key,'kind':'舰艇','offset':match.start()})
    DISCOVERY[folder.name]=discovered
    return lex,regions,tasks
ORIGINAL_VOCAB=events.vocabulary
events.vocabulary=expanded_vocabulary
DISCOVERY={}

def enhance(ledger,extraction):
    allocation={a['id']:[] for a in extraction['atoms']}
    for e in ledger:
        for a in e['claims'].values():allocation[a['id']].append(e['id'])
        e['identity']={'entity_key':e['facts']['country']+'|'+e['key']+'|'+e['kind'],'precision':'named_vessel' if e['kind']=='舰艇' and '号' in e['platform'] else 'platform_model_or_class','physical_identity_proven':e['kind']=='舰艇' and '号' in e['platform'],'event_id':e['id']}
        e['radar_branch_investigation']={'all_rows':[r['row'] for r in e['rows']],'branches':[],'noise_rows':[],'decision':'保留完整记录；无证据删除噪声，无法消解的关键冲突排除'}
        if e['kind']=='飞机':
            groups=collections.defaultdict(list)
            for r in e['rows']:groups[(r.get('开始经度'),r.get('开始纬度'))].append(r['row'])
            e['radar_branch_investigation']['branches']=[{'start_coord':k,'rows':v,'hypotheses':['同批号不同活动或机体','并行错误观测','个别位置噪声'],'resolution':'没有唯一机体标识和独立时间/地点桥接时不选择分支'} for k,v in groups.items()]
        for field,fa in e['field_audit'].items():
            fa['evidence']={}
            for source,a in e['claims'].items():
                fa['evidence'][source]={'raw_value':a.get(field),'quote':a['snippet'],'file':a['path'],'locator':a['locator'],'unit':a.get('quantity_unit') if field=='quantity' else 'minutes_after_midnight' if field in ['start','end'] else None,'time_semantics':'正文观察区间/单点，非自动起降' if field in ['start','end'] else None,'assertion_state':'explicit' if a.get(field) is not None else 'not_mentioned','negative_scope':bool(re.search(r'未曾|并未|没有|否认|并非|未进入|未离开',a['snippet']))}
            fa['evidence']['雷达']={'raw_value':e.get(field),'file':e['radar_file'],'sheet':e['sheet'],'rows':[r['row'] for r in e['rows']],'all_values':e['values'].get(field),'time_semantics':'全部位置时间观测包络' if e['kind']=='飞机' else '首点/结束及全部发现时间'}
    extraction['allocation']=[{'atom_id':a['id'],'source':a['source'],'event_ids':allocation[a['id']],'state':'assigned' if allocation[a['id']] else 'unassigned','candidate_events':[c['event'] for c in extraction['candidates'] if c['atom']==a['id']],'reason':'独立锚定关联后字段另裁决' if allocation[a['id']] else '无唯一可核验关联；仍保留调查候选'} for a in extraction['atoms']]
    extraction['unparsed_fragments']=[{'path':d['path'],'body':d['body'],'fact':d['fact'],'reason':'正文未识别到已支持的平台词；不据标题或文件编号补造事件'} for d in extraction['documents'] if not d['atoms']]
    extraction['text_rooted_event_candidates']=[{'candidate_id':'TXT-'+a['id'],'entity_key':[a['country'],a['key'],a['kind']],'atomic_evidence':a,'radar_hypotheses':[c for c in extraction['candidates'] if c['atom']==a['id']],'decision':'关联调查后见事件台账' if allocation[a['id']] else '排除或待证：未取得三源同事件关联','competing_same_type_counts_not_independent':True} for a in extraction['atoms']]
    extraction['radar_rooted_branch_candidates']=[]
    for e in ledger:
        groups=collections.defaultdict(list)
        for r in e['rows']:
            sig=(r.get('国家地区'),r.get('目标类型',r.get('机舰名')),r.get('开始经度'),r.get('开始纬度'),r.get('首点时间'),r.get('结束时间'))
            groups[sig].append(r)
        for i,(sig,rr) in enumerate(groups.items()):
            extraction['radar_rooted_branch_candidates'].append({'candidate_id':e['id']+f'-B{i+1}','parent_batch':e['batch'],'signature':sig,'full_rows':rr,'decision':'仅作竞争分支调查；批号不证明同一实体或活动','text_hypotheses':[c for c in extraction['candidates'] if c['event']==e['id']]})
    groups=collections.defaultdict(list)
    for a in extraction['atoms']:groups[(a['source'],a['snippet'])].append(a['id'])
    extraction['duplicate_relationships']=[{'source':k[0],'snippet_sha256':hashlib.sha256(k[1].encode()).hexdigest(),'atom_ids':v,'independence':'同类别或复制语句不增加来源类型数'} for k,v in groups.items() if len(v)>1]
    assert all(len(v)<=1 for v in allocation.values()),'one atom assigned to incompatible events'
    return ledger,extraction

def options(cache,node):
    today=cache[node];seeds={(e['facts']['country'],e['key'],e['kind']) for e in today if e['decision']=='纳入' and e['facts']['country']!='中国'};result=[]
    for c,k,kind in sorted(seeds):
        hist=[e for ee in cache.values() for e in ee if e['decision']=='纳入' and e['facts']['country']==c and e['key']==k and e['kind']==kind];rejected=[{'event_id':e['id'],'date':e['date'],'issues':e['issues']} for ee in cache.values() for e in ee if e['decision']=='排除' and e['country']==c and e['key']==k]
        dates=sorted({e['date'] for e in hist},key=dt);all_dates=list(cache)
        result.append({'country':c,'key':k,'kind':kind,'platform':hist[-1]['platform'],'dates':dates,'event_ids':[e['id'] for e in hist],'eligible':len(dates)>=3,'conflict_candidates':rejected,'no_verified_record_dates':[d for d in all_dates if d not in dates],'observed_tasks':dict(collections.Counter(e['facts']['task'] for e in hist)),'directions':dict(collections.Counter(e['facts']['direction'] for e in hist)),'identity_scope':hist[-1]['identity']['precision'],'today_ids':[e['id'] for e in today if e['decision']=='纳入' and e['facts']['country']==c and e['key']==k]})
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=BASE);ap.add_argument('--input',type=Path,default=ROOT/'赛题2-初赛/数据');ap.add_argument('--nodes',nargs='*',default=NODES);args=ap.parse_args();out=args.output.resolve();inputdir=args.input.resolve();root=inputdir.parents[1];manifest=[];start=dt('2025.5.1')
    for node in args.nodes:
        # Each node owns a fresh view, lexicon and associations; never full-season filtering.
        cache={};node_manifest=[];end=dt(node)
        for offset in range((end-start).days+1):
            day=start+datetime.timedelta(days=offset);d=f'{day.year}.{day.month}.{day.day}';folder=inputdir/d
            ee,xx=events.process_day(folder,root,as_of=node);ee,xx=enhance(ee,xx);cache[d]=ee
            xx['text_only_lexical_discovery']=DISCOVERY[d]
            for p in sorted(folder.rglob('*')):
                if p.is_file():node_manifest.append({'path':p.relative_to(root).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size,'date':day.isoformat()})
            if node==args.nodes[-1]:
                save(out/f'evidence/daily/{d}/candidate_ledger.json',ee);save(out/f'evidence/daily/{d}/extraction.json',xx)
            save(out/f'views/{node}/{d}.json',{'candidate_ledger_sha256':hashlib.sha256(json.dumps(ee,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),'counts':dict(collections.Counter(e['decision'] for e in ee)),'atoms':len(xx['atoms']),'unparsed':len(xx['unparsed_fragments']),'future_input_used':False})
        selected=sorted([copy.deepcopy(e) for e in cache[node] if e['decision']=='纳入'],key=lambda e:(e['kind']!='飞机',e['facts']['country']!='中国',e['facts']['country'],e['start'] or 0,e['batch']))
        for i,e in enumerate(selected,1):e['ref']=f'F{i:02d}'
        frozen={'schema_version':13,'as_of':end.isoformat(),'today_events':selected,'verified_events':[e for ee in cache.values() for e in ee if e['decision']=='纳入'],'candidate_comparison':options(cache,node),'mainline':None,'verification_scope':'本节点5月1日起原始三源独立解析；正文与雷达分别召回，逐字段支持和冲突裁决','count_basis':'独立活动记录及参加数量；架次/艘次不是去重实体或真实总出动频次','unknown_policy':'辅助字段不足两类支持留空；关键冲突排除；飞机观察时间不填起降','geography_limits':'固定近似坐标窗为工程相容调查；不充作细地名第二类证据'}
        ad=out/f'audits/{node}';save(ad/'frozen_ledger.json',frozen);save(ad/'candidate_decisions.json',cache[node]);save(ad/'input_manifest.json',node_manifest);save(ad/'freeze_record.json',{'sha256':sha(ad/'frozen_ledger.json'),'as_of':end.isoformat(),'before_analysis':True,'input_max_date':max(x['date'] for x in node_manifest)})
        print(node,'today',dict(collections.Counter(e['decision'] for e in cache[node])),'history',len(frozen['verified_events']),'eligible mainlines',sum(o['eligible'] for o in frozen['candidate_comparison']),flush=True)
        manifest=node_manifest
    save(out/'evidence/input_manifest.json',manifest)
if __name__=='__main__':main()
