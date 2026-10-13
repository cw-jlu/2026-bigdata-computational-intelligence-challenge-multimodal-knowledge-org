from common import *
import zipfile,argparse,os
def official(out):
    path=out/'赛题2_初赛_v13_八节点正式提交包.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted((out/'official').rglob('*')):
            if p.is_file():z.write(p,p.relative_to(out/'official').as_posix())
    return path
def engineering(out):
    path=out/'赛题2_初赛_v13_完整工程包.zip';manifest=[]
    excluded={'node_modules','__pycache__','independent_unpacked','portable_engineering_check'}
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        candidates=[]
        for directory,dirs,files in os.walk(out,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d not in excluded and not d.startswith(('reproduced_','invariance_')))
            candidates.extend(Path(directory)/name for name in sorted(files))
        for p in candidates:
            rel=p.relative_to(out)
            if any(part in excluded or part.startswith('reproduced_') or part.startswith('invariance_') for part in rel.parts):continue
            if not p.is_file() or p.suffix=='.zip' or p.name in {'engineering_package_manifest.json','handoff_manifest.json','engineering_zip_verification.json'}:continue
            z.write(p,'v13/'+rel.as_posix());manifest.append({'path':rel.as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    save(out/'engineering_package_manifest.json',{'members':len(manifest),'files':manifest,'zip_sha256':sha(path),'zip_bytes':path.stat().st_size,'note':'包不包含运行时/字体二进制或node_modules；包含原始输入、审计与QA'})
    return path
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=BASE);ap.add_argument('--engineering',action='store_true');a=ap.parse_args();out=a.output.resolve();p=engineering(out) if a.engineering else official(out);print(p,sha(p),p.stat().st_size)
