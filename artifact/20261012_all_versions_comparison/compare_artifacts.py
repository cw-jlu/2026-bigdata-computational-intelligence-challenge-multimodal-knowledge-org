from pathlib import Path
import json,hashlib,re,subprocess,io,zipfile,xml.etree.ElementTree as ET,collections
from decimal import Decimal,ROUND_HALF_UP
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
NODES=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
V={'gpt_initial':'20261008_001028_gpt-5.6solhigh','claude':'20261008_001929_claude-opus-5.5high','v2':'20261009_gpt_accuracy_v2','v3':'20261009_gpt_accuracy_v3','v4':'20261009_gpt_independent_v4','v5':'20261011_20250510_rebuild_v5','v6':'20261011_20250510_rebuild_v6','v7_unfinished':'20261011_initial_eight_nodes_v7','v8_unfinished':'20261011_initial_eight_nodes_v8','v8':'20261012_initial_eight_nodes_v8'}
reads=[]
def read(p):
    data=p.read_bytes();reads.append({'path':p.relative_to(ROOT).as_posix(),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'state':'fully_read_by_comparison_parser; selected_semantic_output_reviewed'})
    return data
def load(p):return json.loads(read(p).decode('utf-8-sig'))
def git(*args):
    r=subprocess.run(['git','-c','core.quotePath=false',*args],cwd=ROOT,capture_output=True)
    if r.returncode:raise RuntimeError(r.stderr.decode('utf8',errors='replace'))
    return r.stdout
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
def signature(pars):return hashlib.sha256('\n'.join(pars).encode('utf8')).hexdigest()
def docx(data,locator):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        doc=ET.fromstring(z.read('word/document.xml'));ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        pars=[''.join(p.itertext()) for p in []]
        pars=[''.join(p.findall('.//w:t',ns)[i].text or '' for i in range(len(p.findall('.//w:t',ns)))) for p in doc.findall('.//w:body/w:p',ns)]
        pars=[p for p in pars if p.strip()]
        heads=[(i,p) for i,p in enumerate(pars) if re.match(r'^[一二三四五六][、.．\s]',p)]
        start=next((i for i,p in heads if re.match(r'^二',p)),None)
        end=next((i for i,p in heads if re.match(r'^三',p)),len(pars))
        sec=pars[start+1:end] if start is not None else []
        return {'locator':locator,'sha256':hashlib.sha256(data).hexdigest(),'headings':[p for i,p in heads],'body_paragraph_sha256':signature(pars),'section2_paragraph_sha256':signature(sec),'section2_paragraphs':sec,'section2_chars':sum(map(len,sec)),'paragraph_count':len(pars),'tables':len(doc.findall('.//w:tbl',ns))}
def official_paths(k,base):
    if k=='gpt_initial':return base/'output'
    if k=='claude':return base/'output'
    if k in ['v2','v3','v4']:return base/'output/日报'
    if k=='v6':return base/'2025.5.10'
    if k=='v8':return base/'official'
    if k=='v5':return base/'output'
    return base/'official_nonexistent'
def main():
    scores={}
    baseline=read(ROOT/'docs/05-评测标准与复现清单.md').decode('utf8')
    for key,label in [('claude','Claude Opus 5.5'),('gpt_initial','GPT-5.6')]:
        line=next(s for s in baseline.splitlines() if s.startswith('| '+label+' |'))
        vals=[s.strip() for s in line.split('|')[3:7]];scores[key]={'metrics':vals,'source':'docs/05-评测标准与复现清单.md','locator':line,'nodes':8}
    j=load(ROOT/'artifact'/V['v2']/'audit/evaluation_initial_20261009.json')
    # v2's exact metrics are also preserved in the v3/v4 feedback records.
    j3=load(ROOT/'artifact'/V['v3']/'audit/post_evaluation/evaluation_and_diagnosis.json')
    j4=load(ROOT/'artifact'/V['v4']/'audit/post_evaluation_trace/evaluation_comparison.json')
    for key,vals,source in [('v2',j3['v2'],'artifact/'+V['v2']+'/audit/evaluation_initial_20261009.json'),('v3',j3['v3'],'artifact/'+V['v3']+'/audit/post_evaluation/evaluation_and_diagnosis.json'),('v4',j4['v4'],'artifact/'+V['v4']+'/audit/post_evaluation_trace/evaluation_comparison.json')]:scores[key]={'metrics':vals,'source':source,'nodes':8}
    j8=load(ROOT/'artifact'/V['v8']/'evaluation/evaluation_initial_20261012.json');order=['completeness','accuracy','format','analysis'];weights=list(map(Decimal,['.25','.40','.15','.20']))
    scores['v8']={'metrics':[j8['metrics'][k] for k in order],'source':'artifact/'+V['v8']+'/evaluation/evaluation_initial_20261012.json','nodes':8}
    for k,s in scores.items():
        s['total_exact']=str(sum(Decimal(x)*w for x,w in zip(s['metrics'],weights)))
        s['total_4dp']=str(Decimal(s['total_exact']).quantize(Decimal('.0001'),rounding=ROUND_HALF_UP))
        delta=[Decimal(a)-Decimal(b) for a,b in zip(scores['v8']['metrics'],s['metrics'])]
        s['v8_minus_this_metrics']=list(map(str,delta));s['v8_minus_this_weighted']=list(map(str,(a*w for a,w in zip(delta,weights))))
        s['v8_minus_this_total_exact']=str(Decimal(scores['v8']['metrics'][0])*weights[0]+Decimal(scores['v8']['metrics'][1])*weights[1]+Decimal(scores['v8']['metrics'][2])*weights[2]+Decimal(scores['v8']['metrics'][3])*weights[3]-Decimal(s['total_exact']))
    profiles={};documents={};facts={}
    for k,folder in V.items():
        base=ROOT/'artifact'/folder;tree=official_paths(k,base)
        paths=list(tree.rglob('*.docx')) if tree.exists() else []
        paths=[p for p in paths if not any(x in p.parts for x in ['reproduction','audit','qa','__pycache__'])]
        sheets=list(tree.rglob('*.xlsx')) if tree.exists() else []
        images=list(tree.rglob('*.png')) if tree.exists() else []
        profiles[k]={'folder':'artifact/'+folder,'actual_official_files':{'docx':len(paths),'xlsx':len(sheets),'png':len(images)},'score_available':k in scores,'formal_nodes':sorted({re.search(r'2025\.\d+\.\d+',p.name)[0] for p in paths if re.search(r'2025\.\d+\.\d+',p.name)}),'code_present':bool(list((base/'code').glob('*.py'))) if (base/'code').exists() else bool(list(base.glob('*.py')))}
        for p in paths:
            node=re.search(r'2025\.\d+\.\d+',p.name)
            if node:documents.setdefault(k,{})[node[0]]=docx(read(p),p.relative_to(ROOT).as_posix())
        if k=='v4':
            for n in NODES:
                p=base/'output/payloads'/f'{n}.json';j=load(p)
                facts.setdefault(k,{})[n]={'counts':j['counts'],'events':j['events'],'line':j['chain']}
        if k=='v8':
            for n in NODES:
                p=base/'audits'/n/'frozen_ledger.json';j=load(p)
                facts.setdefault(k,{})[n]={'counts':{'included':len(j['today_events'])},'events':j['today_events'],'line':j['mainline']}
        if k in ['v2','v3']:
            j=load(base/'output/中间证据/reconstruction_summary.json')
            profiles[k]['node_event_counts']={r['date']:r['included'] for r in j['nodes']}
    prefix='artifact/赛题2_初赛_八节点_格式对齐版/';ref=git('rev-parse','origin/main').decode('ascii').strip()
    remote_paths=[p for p in git('ls-tree','-r','--name-only',ref,'--',prefix).decode('utf8').splitlines() if p]
    profiles['formatted']={'folder':prefix,'git_ref':ref,'actual_official_files':dict(collections.Counter(Path(p).suffix.lower() for p in remote_paths)),'member_count':len(remote_paths),'score_available':False,'formal_nodes':NODES}
    for p in remote_paths:
        if p.endswith('.docx'):
            data=git('show',ref+':'+p);node=re.search(r'2025\.\d+\.\d+',p)[0];documents.setdefault('formatted',{})[node]=docx(data,ref+':'+p)
            reads.append({'path':ref+':'+p,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'state':'fully_read_by_docx_parser; selected_semantic_output_reviewed'})
    save('scores.json',scores);save('version_inventory.json',profiles);save('actual_report_section2.json',documents)
    save('fact_profiles_raw.json',facts)
    save('comparison_read_manifest.json',reads)
    summary={'scores':scores,'inventory':profiles,'document_counts':{k:len(v) for k,v in documents.items()},'fact_examples':{k:{'event_keys':list(v[NODES[0]]['events'][0]),'event_first':{x:v[NODES[0]]['events'][0].get(x) for x in ['id','date','day','batch','kind','decision','facts']},'line_keys':list(v[NODES[0]]['line'])} for k,v in facts.items()}}
    print(json.dumps(summary,ensure_ascii=True,indent=2))
if __name__=='__main__':main()
