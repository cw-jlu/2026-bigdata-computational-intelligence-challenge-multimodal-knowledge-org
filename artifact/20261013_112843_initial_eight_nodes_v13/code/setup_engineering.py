from common import *
import shutil,subprocess,platform,sys,importlib.metadata,os,io,collections
from docx import Document
def main():
    src=ROOT/'赛题2-初赛/数据';dest=BASE/'inputs/赛题2-初赛/数据';shutil.copytree(src,dest,dirs_exist_ok=True)
    shutil.copytree(ROOT/'提交示例文件/日报/2025.10.20',BASE/'inputs/提交示例文件/日报/2025.10.20',dirs_exist_ok=True)
    for name in ['R06.pdf','R07.pdf']:
        p=ROOT/f'research/20261012_score_improvement_sources/originals/{name}';q=BASE/'inputs'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    for name in ['01-赛题总览与赛程.md','02-数据说明与判定口径.md','03-系统处理流程与算法要求.md','04-日报交付格式与文件规范.md','05-评测标准与复现清单.md','prompts/赛题2-初赛八节点-从原始证据重建-v13.md']:
        p=ROOT/'docs'/name;q=BASE/'inputs/docs'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
    p=ROOT/'提交示例文件/提交格式说明.md';q=BASE/'inputs/提交示例文件/提交格式说明.md';shutil.copy2(p,q)
    files=[{'path':p.relative_to(BASE/'inputs').as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted((BASE/'inputs').rglob('*')) if p.is_file()];save(BASE/'audit/archived_raw_input_manifest.json',files)
    env={'python':sys.version,'executable':sys.executable,'os':platform.platform(),'cpu_logical_count':os.cpu_count(),'gpu_used':False,'external_model_api_calls':0,'model_precise_backend':'unknown','packages':{n:importlib.metadata.version(n) for n in ['numpy','openpyxl','python-docx','Pillow','pypdfium2','pypdf']},'node':'bundled runtime, user-overridable path','artifact_tool':'bundled @oai/artifact-tool required','renderer':'Native Office COM full export; pdfium rasterization','limitations':'exact model sampling parameters unavailable; no platform upload/score'}
    save(BASE/'environment.json',env);(BASE/'requirements-lock.txt').write_text('\n'.join(k+'=='+v for k,v in env['packages'].items())+'\n',encoding='utf8')
    revision='a49ec55237c73dbf27b6c947da72780604f6db4e';prefix='artifact/赛题2_初赛_八节点_格式对齐版';git='C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe';res=subprocess.run([git,'ls-tree','-rz','--name-only',revision,'--',prefix],cwd=ROOT,capture_output=True,check=True);names=res.stdout.decode('utf8').strip('\0').split('\0');sections=[]
    for name in names:
        if not name.endswith('.docx'):continue
        raw=subprocess.run([git,'show',revision+':'+name],cwd=ROOT,capture_output=True,check=True).stdout
        q=BASE/'audit/git_formatted_originals'/Path(name).name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);doc=Document(io.BytesIO(raw));paras=[p.text for p in doc.paragraphs];begin=next(i for i,x in enumerate(paras) if x.startswith('二、'));end=next((i for i,x in enumerate(paras) if i>begin and x.startswith('三、')),len(paras));sections.append({'path':name,'commit':revision,'sha256':sha(q),'section2':paras[begin:end]})
    save(BASE/'audit/git_formatted_intake.json',{'commit':revision,'members':names,'counts':dict(collections.Counter(Path(n).suffix for n in names)),'actual_second_sections':sections,'score':'not_found; no transferred score'})
    coverage=[];methodcounts=collections.Counter()
    for p in sorted((BASE/'evidence/daily').glob('*/extraction.json')):
        x=load(p);coverage.append({'date':p.parent.name,'texts':len(x['documents']),'atoms':len(x['atoms']),'text_rooted_candidates':len(x.get('text_rooted_event_candidates',[])),'radar_branch_candidates':len(x.get('radar_rooted_branch_candidates',[])),'unassigned_atoms':len(x['unmatched_atoms']),'unparsed_fragments':len(x['unparsed_fragments']),'competing_links':len(x['candidates']),'discovered_text_only_labels':len(x.get('text_only_lexical_discovery',[]))})
        for e in load(p.parent/'candidate_ledger.json'):
            for a in e['claims'].values():
                if a.get('time_semantics')=='explicit_activity_start_without_end' and e['decision']=='排除':methodcounts['单端起始范围未消解']+=1
    save(BASE/'audit/raw_to_ledger_coverage.json',{'days':coverage,'totals':{k:sum(d[k] for d in coverage) for k in coverage[0] if k!='date'},'unmatched_not_hidden':True,'truth_recall_not_established':True,'time_scope_limits':dict(methodcounts)})
    print('archived',len(files),'input/template/source/rule files','coverage days',len(coverage),'git original reports',len(sections))
if __name__=='__main__':main()
