import ast,difflib,json,collections
from compare_artifacts import ROOT,OUT,V,read,load,reads,save,NODES
SELECTION=[
('gpt_initial','solution.py',['text_score','similarity','build_events','choose_trend']),
('claude','bdci/fusion.py',['_vote','verify']),('claude','bdci/tracking.py',['build_mainline','_phase']),
('v2','code/fusion.py',['adjudicate','choose_trend']),('v3','code/fusion_event_stage.py',None),('v3','code/trend_v3.py',None),
('v4','code/events.py',['text_atoms','audit_fields','choose_chain']),('v4','code/report.py',['write']),
('v5','code/events_base.py',['audit_fields']),('v6','code/events.py',['audit_fields']),('v6','code/build.py',None),
('v8','code/events.py',['text_atoms','audit_fields','choose_chain']),('v8','code/select_lines.py',None),('v8','code/build.py',None),
('v8_unfinished','code/prepare.py',None),('v8_unfinished','code/common.py',None)]
def functions(text):
    tree=ast.parse(text);lines=text.splitlines()
    return {n.name:{'line_start':n.lineno,'line_end':n.end_lineno,'text':'\n'.join(lines[n.lineno-1:n.end_lineno])} for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
def main():
    excerpts=[];cache={};missing=[]
    for k,rel,names in SELECTION:
        path=ROOT/'artifact'/V[k]/rel
        if not path.exists():missing.append(path.relative_to(ROOT).as_posix());continue
        text=read(path).decode('utf-8-sig');cache[(k,rel)]=text;fs=functions(text)
        if names is None:chosen=fs
        else:chosen={n:fs[n] for n in names if n in fs}
        excerpts.append({'version':k,'path':path.relative_to(ROOT).as_posix(),'functions':chosen,'whole_file_lines':len(text.splitlines())})
    workflows=[]
    for folder,rel in [('20261008_workflow_agent_v1','workflow_agent'),('20261008_204137_976_workflow-agent-v1.1_deepseek-v4-pro_risk','code/workflow_agent'),('20261008_204853_747_workflow-agent-v1.2_deepseek-v4-pro_risk','code/workflow_agent')]:
        profile={'folder':folder,'modules':{}}
        for module in ['engine.py','analysis.py','trust.py','report.py']:
            text=read(ROOT/'artifact'/folder/rel/module).decode('utf-8-sig');fs=functions(text)
            profile['modules'][module]={'function_names':list(fs),'lines':len(text.splitlines())}
        workflows.append(profile)
    changes=[]
    for old,new,rel in [('v4','v8','code/events.py'),('v6','v8','code/events.py')]:
        if (old,rel) not in cache or (new,rel) not in cache:continue
        a=cache[(old,rel)];b=cache[(new,rel)]
        d='\n'.join(difflib.unified_diff(a.splitlines(),b.splitlines(),fromfile=V[old]+'/'+rel,tofile=V[new]+'/'+rel,n=3))
        (OUT/f'{old}_to_{new}_events.diff').write_text(d+'\n',encoding='utf8',newline='\n')
        fa,fb=functions(a),functions(b)
        changes.append({'old':old,'new':new,'same_function_text':[k for k in sorted(fa.keys()&fb.keys()) if fa[k]['text']==fb[k]['text']],'changed_functions':[k for k in sorted(fa.keys()&fb.keys()) if fa[k]['text']!=fb[k]['text']],'added_functions':sorted(fb.keys()-fa.keys())})
    save('code_excerpts.json',excerpts);save('code_comparison_summary.json',{'module_differences':changes,'workflow_profiles':workflows,'missing_code_inputs':missing})
    manifest=json.loads((OUT/'comparison_read_manifest.json').read_text(encoding='utf8'));save('comparison_read_manifest.json',manifest+reads)
    print(json.dumps({'code_files_read':len(reads),'excerpts':len(excerpts),'module_differences':changes,'workflow_profiles':workflows},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
