from pathlib import Path
import json,collections,hashlib,re
from compare_artifacts import ROOT,OUT,NODES,V,load,read,reads,save
def index(records):
    d=collections.defaultdict(list)
    for e in records:d[(e['date'],e['kind'],e['batch'])].append(e)
    assert all(len(v)==1 for v in d.values()),'Ambiguous batch identities require manual mapping'
    return {k:v[0] for k,v in d.items()}
def compact(e):return {'id':e['id'],'date':e['date'],'kind':e['kind'],'batch':e['batch'],'facts':e['facts'],'decision':e['decision'],'issues':e.get('issues',[]),'evidence':{k:{'path':v.get('path'),'sha256':v.get('sha256'),'locator':v.get('locator')} for k,v in e.get('claims',{}).items()},'radar_file':e['radar_file'],'radar_rows':[r.get('row') for r in e.get('rows',[])]}
def main():
    facts=json.loads((OUT/'fact_profiles_raw.json').read_text(encoding='utf8'))
    docs=json.loads((OUT/'actual_report_section2.json').read_text(encoding='utf8'))
    delta=[];mainlines=[];totals=collections.Counter();changed_fields=collections.Counter()
    for n in NODES:
        old=index(facts['v4'][n]['events']);new=index(facts['v8'][n]['events']);intersection=old.keys()&new.keys();changes=[]
        excluded=[json.loads(line) for line in read(ROOT/'artifact'/V['v4']/'output/evidence'/f'{n}.events.jsonl').decode('utf8').splitlines() if line]
        excluded=[e for e in excluded if e['decision']!='纳入']
        old_excluded=index(excluded)
        added=[];removed=[]
        for k in sorted(new.keys()-old.keys()):
            e=compact(new[k]);e['v4_exclusion']=compact(old_excluded[k]) if k in old_excluded else None;added.append(e)
        for k in sorted(old.keys()-new.keys()):removed.append(compact(old[k]))
        for k in sorted(intersection):
            fields={f:{'v4':old[k]['facts'].get(f),'v8':new[k]['facts'].get(f)} for f in ['country','key','platform','quantity','task','start','end','region','direction'] if old[k]['facts'].get(f)!=new[k]['facts'].get(f)}
            if fields:changes.append({'key':list(k),'fields':fields,'v4':compact(old[k]),'v8':compact(new[k])});changed_fields.update(fields.keys())
        row={'date':n,'v4_included':len(old),'v8_included':len(new),'retained':len(intersection),'added':len(added),'removed':len(removed),'retained_changed':len(changes),'changes':changes,'added_records':added,'removed_records':removed}
        totals.update({k:row[k] for k in ['v4_included','v8_included','retained','added','removed','retained_changed']});delta.append(row)
        def stages(line):
            return [{'dates':s.get('dates',[]),'event_ids':s.get('events',[]),'keys':list(s)} for s in line.get('stages',[])]
        mainlines.append({'date':n,**{k:{'country':facts[k][n]['line'].get('country'),'platform':facts[k][n]['line'].get('platform'),'dates':facts[k][n]['line']['dates'],'stages':stages(facts[k][n]['line'])} for k in ['v4','v8']}})
    text_stats={}
    for k,dd in docs.items():
        common=set(dd[next(iter(dd))]['section2_paragraphs'])
        for d in dd.values():common&=set(d['section2_paragraphs'])
        text_stats[k]={'reports':len(dd),'mean_section2_chars':sum(d['section2_chars'] for d in dd.values())/len(dd),'identical_paragraphs_in_all_reports':[p for p in sorted(common) if len(p)>30],'all_section2_extracted':all(d['section2_paragraphs'] for d in dd.values()),'first_paragraphs_by_node':{n:d['section2_paragraphs'][:2] for n,d in dd.items()}}
    formatted_matches=[]
    for n,d in docs['formatted'].items():
        formatted_matches.append({'date':n,'whole_body_matches':[k for k,dd in docs.items() if k!='formatted' and n in dd and d['body_paragraph_sha256']==dd[n]['body_paragraph_sha256']],'section2_matches':[k for k,dd in docs.items() if k!='formatted' and n in dd and d['section2_paragraph_sha256']==dd[n]['section2_paragraph_sha256']]})
    phase_stats={k:{'stages':sum(len(r[k]['stages']) for r in mainlines),'single_date_stages':sum(len(s['dates'])==1 for r in mainlines for s in r[k]['stages']),'mean_dates':sum(len(r[k]['dates']) for r in mainlines)/8} for k in ['v4','v8']}
    result={'mapping_basis':'Node date + original radar type and batch identify output units; this is an output comparison, not a truth adjudication or text-source matching rule. All keys unique in these node snapshots.','totals':dict(totals),'changed_field_counts':dict(changed_fields),'nodes':delta,'mainlines':mainlines,'phase_stats':phase_stats,'formatted_matches':formatted_matches}
    save('v4_v8_fact_and_mainline_comparison.json',result);save('report_text_profiles.json',text_stats)
    manifest=json.loads((OUT/'comparison_read_manifest.json').read_text(encoding='utf8'));save('comparison_read_manifest.json',manifest+reads)
    preview={'totals':dict(totals),'changed_field_counts':dict(changed_fields),'nodes':[{k:v for k,v in r.items() if not isinstance(v,list)} for r in delta],'phase_stats':phase_stats,'formatted_matches':formatted_matches,'text_stats':{k:{x:v for x,v in v.items() if x!='first_paragraphs_by_node'} for k,v in text_stats.items()},'first_node_paragraphs':{k:v['first_paragraphs_by_node'].get(NODES[0],[]) for k,v in text_stats.items()},'added_example':delta[0]['added_records'][:1]}
    print(json.dumps(preview,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
