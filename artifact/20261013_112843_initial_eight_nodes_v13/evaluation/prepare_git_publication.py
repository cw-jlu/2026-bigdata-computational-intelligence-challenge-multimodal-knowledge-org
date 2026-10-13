"""Publish only v13 from a clean checkout of the fetched remote main."""
from pathlib import Path
import argparse,json,shutil,subprocess,hashlib

BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--worktree',type=Path,required=True);a=ap.parse_args();wt=a.worktree.resolve()
    def git(*args):return subprocess.check_output(['git','-C',str(wt),*args],encoding='utf8',errors='replace').strip()
    status=git('status','--porcelain')
    assert not status or git('branch','--show-current')=='codex/v13-evaluation-20261013','Only resume our publication branch'
    assert git('rev-parse','HEAD')==git('rev-parse','origin/main'),'Must start from fetched main'
    if git('branch','--show-current')!='codex/v13-evaluation-20261013':
        subprocess.run(['git','-C',str(wt),'switch','-c','codex/v13-evaluation-20261013'],check=True)
    manifest=json.loads((BASE/'engineering_package_manifest.json').read_text(encoding='utf8'))
    files={x['path'] for x in manifest['files']}
    files.update(['engineering_package_manifest.json','engineering_zip_verification.json','handoff_manifest.json','赛题2_初赛_v13_八节点正式提交包.zip','赛题2_初赛_v13_完整工程包.zip'])
    files.update(p.relative_to(BASE).as_posix() for p in (BASE/'evaluation').glob('*') if p.is_file() and p.suffix in {'.py','.json','.md'})
    prefix=BASE.relative_to(ROOT).as_posix();paths=[]
    for i,rel in enumerate(sorted(files)):
        assert not any(x in rel.split('/') for x in ['node_modules','__pycache__','reproduced_raw_v13','reproduced_raw_v13_final','invariance_inputs'])
        assert not Path(rel).name.startswith('.env')
        src=BASE/rel;dst=wt/prefix/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2('\\\\?\\'+str(src.resolve()),'\\\\?\\'+str(dst.resolve()));paths.append(prefix+'/'+rel)
        if (i+1)%2000==0:print('copied',i+1,flush=True)
    for rel in ['docs/13-v13初赛评测记录.md','docs/prompts/赛题2-初赛八节点-从原始证据重建-v13.md']:
        dst=wt/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dst);paths.append(rel)
    score='2026-10-13 最新实测：v13 initial八节点完整性 **86.5219**、准确性 **70.8849**、格式 **96.9027**、分析 **60.0000**；按展示均值加权总分 **76.5198**，较v4 **+0.9754**、较v9 **+2.3445**、较v12 **+2.7579**。目前已归档用户反馈中的最高计算总分为v13；准确性仍低于v4。[评分原文、版本绑定与限制](docs/13-v13初赛评测记录.md)，[本版完整交付与源码](artifact/20261013_112843_initial_eight_nodes_v13/README.md)。'
    for rel,line in [('README.md',score),('docs/README.md',score.replace('(docs/13-','(13-').replace('(artifact/','(../artifact/'))]:
        p=wt/rel;text=p.read_text(encoding='utf-8-sig');text=text.replace('已归档成绩中v4总分 **75.5445** 最高','v13评测前的最高总分对照为v4 **75.5445**').replace('v4仍为最高总分对照','当时v4仍为最高总分对照')
        p.write_text(text.rstrip()+'\n\n'+line+'\n',encoding='utf8');paths.append(rel)
    attr=wt/'.gitattributes';rules=f'\n{prefix}/** -text\n{prefix}/audits/*/frozen_ledger.json filter=lfs diff=lfs merge=lfs -text\n{prefix}/赛题2_初赛_v13_完整工程包.zip filter=lfs diff=lfs merge=lfs -text\n'
    attr.write_text(attr.read_text(encoding='utf8').rstrip()+'\n'+rules,encoding='utf8');paths.append('.gitattributes')
    spec=BASE/'evaluation/publication_pathspec.nul';spec.write_bytes(b'\x00'.join(p.encode('utf8') for p in paths)+b'\x00')
    subprocess.run(['git','-c','core.longpaths=true','-C',str(wt),'add','-f','--pathspec-from-file='+str(spec),'--pathspec-file-nul'],check=True)
    staged=git('diff','--cached','--name-only','-z').split('\x00');staged={p for p in staged if p};assert staged==set(paths),(len(staged),len(paths))
    result={'publication_checkout':str(wt),'base_remote_commit':git('rev-parse','HEAD'),'staged_files':len(staged),'scope':'only new v13 artifacts, v13 prompt/evaluation doc, shared index updates and v13 LFS rules','original_checkout_untouched':True,'original_submit_archives_unchanged':True}
    (BASE/'evaluation/publication_preparation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
