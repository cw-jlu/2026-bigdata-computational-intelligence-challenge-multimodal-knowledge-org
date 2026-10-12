from pathlib import Path
import json,collections,re
from compare_artifacts import ROOT,OUT,NODES,V,read,load,reads,save
def main():
    delta=json.loads((OUT/'v4_v8_fact_and_mainline_comparison.json').read_text(encoding='utf8'))
    added=[e for r in delta['nodes'] for e in r['added_records']]
    reasons=collections.Counter(s for e in added if e['v4_exclusion'] for s in e['v4_exclusion']['issues'])
    docs=json.loads((OUT/'actual_report_section2.json').read_text(encoding='utf8'))
    near=[]
    for n in NODES:
        a=docs['v4'][n]['section2_paragraphs'];b=docs['formatted'][n]['section2_paragraphs']
        normalize=lambda s:re.sub(r'\s+','',s)
        count=sum(any(normalize(p) in normalize(q) for q in b) for p in a)
        near.append({'date':n,'v4_paragraphs':len(a),'v4_paragraphs_preserved_in_formatted':count,'fraction':count/len(a)})
    allnodes=[]
    for n in NODES:
        allnodes.append({'date':n,'version_first_paragraphs':{k:v[n]['section2_paragraphs'][:1] for k,v in docs.items() if n in v}})
    workflow={}
    for name in ['20261008_204137_976_workflow-agent-v1.1_deepseek-v4-pro_risk','20261008_204853_747_workflow-agent-v1.2_deepseek-v4-pro_risk']:
        j=load(ROOT/'artifact'/name/'summary.json');workflow[name]={k:len(v) if isinstance(v,list) else v for k,v in j.items()}
    claude=load(ROOT/'artifact'/V['claude']/'output/summary.json')
    oldp=ROOT/'artifact'/V['gpt_initial']/'output/中间结果/evidence.jsonl'
    old=[json.loads(x) for x in read(oldp).decode('utf8').splitlines() if x]
    old_counts=dict(collections.Counter(e['date'] for e in old if e['date'] in NODES and e['decision']=='纳入'))
    assert sum(old_counts.values())==269
    inventory=json.loads((OUT/'version_inventory.json').read_text(encoding='utf8'))
    for i,(folder,j) in enumerate(workflow.items()):
        inventory['workflow_v1_'+str(i+1)]={'folder':'artifact/'+folder,'actual_official_files':{'docx':0,'xlsx':0,'png':0},'score_available':False,'formal_nodes':[],'run_summary':j}
    read(ROOT/'artifact/20261008_workflow_agent_v1/README.md')
    inventory['workflow_v1']={'folder':'artifact/20261008_workflow_agent_v1','actual_official_files':{'docx':0,'xlsx':0,'png':0},'score_available':False,'formal_nodes':[],'scope':'framework and synthetic tests, no competition deliverable'}
    assert len(inventory)==14
    save('version_inventory.json',inventory)
    result={'v4_old_exclusion_reasons_for_v8_30_added_nonexclusive':dict(reasons),'v4_v8_mainlines':delta['mainlines'],'formatted_v4_paragraph_containment':near,'all_nodes_first_paragraphs':allnodes,'claude_counts_by_node':{r['node']:r['core_events'] for r in claude},'claude_total_node_events':sum(r['core_events'] for r in claude),'workflow_runs':workflow,'initial_gpt_node_counts':old_counts,'initial_gpt_schema':list(old[0]),'initial_gpt_first_scalars':{k:v for k,v in old[0].items() if not isinstance(v,(dict,list))},'region_changes_by_node':{r['date']:[{'id':e['v4']['id'],'country':e['v4']['facts']['country'],'platform':e['v4']['facts']['platform'],**e['fields']} for e in r['changes']] for r in delta['nodes']}}
    save('review_details.json',result)
    manifest=json.loads((OUT/'comparison_read_manifest.json').read_text(encoding='utf8'));save('comparison_read_manifest.json',manifest+reads)
    print(json.dumps({k:v for k,v in result.items() if k not in ['region_changes_by_node','v4_v8_mainlines']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
