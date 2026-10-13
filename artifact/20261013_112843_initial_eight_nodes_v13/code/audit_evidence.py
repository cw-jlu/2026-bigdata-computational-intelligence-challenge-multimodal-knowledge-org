from common import *
from collections import Counter,defaultdict
import argparse,re
from openpyxl import load_workbook
def compact(e):
    return {'id':e['id'],'decision':e['decision'],'facts':e['facts'],'issues':e['issues'],'texts':{s:{'path':a['path'],'quote':a['snippet'],'values':{k:a.get(k) for k in ['country','key','quantity','quantity_basis','task','region','start','end','observed','reported_kind','quantity_unit']}} for s,a in e['claims'].items()},'radar':{'file':e['radar_file'],'sheet':e['sheet'],'rows':e['rows'],'values':e['values'],'regions':e['regions'],'coords':e['coords'],'alerts':e['trajectory_alerts']},'field_audit':e['field_audit']}
def main():
    history=load(ROOT/'artifact/20261012_all_versions_comparison/v4_v8_fact_and_mainline_comparison.json');priority=[];samples=[];summary=[];differences=[]
    versions={'v4':'20261009_gpt_independent_v4','v8':'20261012_initial_eight_nodes_v8','v9':'20261012_134432_initial_eight_nodes_v9','v10':'20261012_152733_initial_eight_nodes_v10','v11':'20261012_160950_initial_eight_nodes_v11','v12':'20261012_163714_initial_eight_nodes_v12'}
    for node in NODES:
        current=load(BASE/f'audits/{node}/candidate_decisions.json');byid={e['id']:e for e in current};frozen=load(BASE/f'audits/{node}/frozen_ledger.json')
        refs={};oldvalues={}
        for version,folder in versions.items():
            paths=list((ROOT/f'artifact/{folder}/official/{node}').glob('*.xlsx')) or list((ROOT/f'artifact/{folder}/output/日报/{node}').glob('*.xlsx'))
            if not paths:paths=[p for p in (ROOT/f'artifact/{folder}/output').rglob(f'{node}机舰活动明细.xlsx')]
            values={}
            for p in paths:
                wb=load_workbook(p,data_only=True)
                for sh in wb:
                    rows=list(sh.values);hdr=[str(x).replace('\n','') for x in rows[0]]
                    for row in rows[1:]:
                        v=dict(zip(hdr,row));batch=v.get('批号');
                        if batch:values[node+'-'+str(batch)]={'sheet':sh.title,'values':v,'source':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}
                wb.close()
            oldvalues[version]=values
            refs[version]=set(values)
        h=next(x for x in history['nodes'] if x['date']==node)
        for category,items in [('新增30',h.get('added_records',[])),('区域55',h.get('changes',[]))]:
            # added is a list in the comparison schema; tolerate summary integers.
            if not isinstance(items,list):continue
            for item in items:
                ident=item.get('v8',{}).get('id') or item.get('id') or '-'.join([item['key'][0],item['key'][2]])
                if ident not in byid:raise ValueError('historical candidate absent '+ident)
                e=byid[ident];priority.append({'category':category,'node':node,'historical':{v:oldvalues[v].get(ident) for v in versions},'current':compact(e),'裁决':'保留当前三源双支持且无冲突' if e['decision']=='纳入' else '按当前原文排除/域外','precision_basis':e['field_audit']['region'],'reviewer':'current_agent_known_history_not_blind; semantic_receipt_pending'})
        sampleids=set()
        for decision in ['纳入','排除','域外']:
            group=sorted([e for e in current if e['decision']==decision],key=lambda e:hashlib.sha256(e['id'].encode()).hexdigest())
            for e in group[:2]:samples.append({'stratum':decision,'node':node,'denominator':len(group),'current':compact(e)});sampleids.add(e['id'])
        for e in current:
            if e['trajectory_alerts'] or e['bad_rows']:
                if e['id'] not in sampleids:samples.append({'stratum':'雷达异常','node':node,'denominator':sum(bool(q['trajectory_alerts'] or q['bad_rows']) for q in current),'current':compact(e)});sampleids.add(e['id'])
        included={e['id'] for e in current if e['decision']=='纳入'}
        for version in ['v4','v9','v12']:
            differences.append({'node':node,'version':version,'retained':sorted(included&refs[version]),'added':sorted(included-refs[version]),'removed':sorted(refs[version]-included),'field_changes':[{'id':e['id'],'old_region':oldvalues[version][e['id']]['values'].get('活动区域'),'new_region':e['facts']['region']} for e in current if e['id'] in included&refs[version] and oldvalues[version][e['id']]['values'].get('活动区域')!=e['facts']['region']]})
        for e in frozen['today_events']:
            assert len(e['claims'])==2 and not e['issues']
            for field in ['country','key','quantity','task','region']:
                assert len(e['field_audit'][field]['support_types'])>=2,(e['id'],field)
            for a in e['claims'].values():
                p=ROOT/a['path'];assert sha(p)==a['sha256'];assert a['snippet'].strip() in re.sub(r'^据[^，。]*报道[，、]?','',p.read_text(encoding='utf-8-sig').split('正文：',1)[-1].strip()) or a['snippet'] in p.read_text(encoding='utf-8-sig'),(e['id'],a['path'])
        summary.append({'node':node,'radar_candidates':len(current),'decisions':dict(Counter(e['decision'] for e in current)),'all_history_verified':len(frozen['verified_events']),'cutoff':frozen['as_of'],'selected_fact_hash':sha(BASE/f'audits/{node}/frozen_ledger.json'),'sample_unique':len(sampleids),'independent_blind_review':False})
    save(BASE/'audit/priority_30_55_review.json',priority);save(BASE/'audit/stratified_review.json',samples);save(BASE/'audit/version_differences.json',differences);save(BASE/'audit/evidence_audit_summary.json',summary)
    print('priority',dict(Counter(p['category'] for p in priority)),'sample',len(samples),'radar',sum(s['radar_candidates'] for s in summary),'selected',sum(s['decisions'].get('纳入',0) for s in summary))
    ap=argparse.ArgumentParser();ap.add_argument('--node');ap.add_argument('--category');a=ap.parse_args()
    if a.node:
        for p in priority:
            if p['node']==a.node and (not a.category or p['category']==a.category):
                e=p['current'];print(p['category'],e['id'],e['decision'],e['facts'],e['issues']);[print(s,x['values'],x['quote']) for s,x in e['texts'].items()]
if __name__=='__main__':main()
