"""Package only the new artifact. Preserve files; exclude runtimes and duplicates."""
import argparse,hashlib,json,zipfile
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(base):
    base=base.resolve();archive=base/'工程交付_代码证据成果.zip';manifest=base/'工程文件清单.json';record=base/'audit/engineering_package.json'
    skip={archive,manifest,record};files=[]
    for p in base.rglob('*'):
        if not p.is_file() or p in skip:continue
        rel=p.relative_to(base);parts=rel.parts
        if any(n.startswith('.venv') or n=='__pycache__' for n in parts):continue
        if len(parts)>1 and parts[0]=='audit' and (parts[1] in ['reproduction','metamorphic_input','audit']):continue
        if parts[0] in ['reproduced']:continue
        if p.suffix in ['.pdf','.pyc']:continue
        files.append(p)
    files.sort(key=lambda p:p.relative_to(base).as_posix())
    rows=[{'path':p.relative_to(base).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
    manifest.write_text(json.dumps({'files':rows,'count':len(rows),'note':'本清单不列自身、工程ZIP与其生成后的校验记录，避免循环哈希；提交ZIP有独立校验。'},ensure_ascii=False,indent=2),encoding='utf-8')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in files+[manifest]:
            info=zipfile.ZipInfo(p.relative_to(base).as_posix(),(2026,10,9,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        names=z.namelist();expected={p.relative_to(base).as_posix() for p in files+[manifest]}
        assert len(names)==len(expected) and set(names)==expected
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'] for r in rows)
    r={'ok':True,'entries':len(files)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'zip':archive.name,'note':'工程包非赛题提交包；排除虚拟环境/重复复现/变形输入/缓存/QA PDF，保留正式48文件、提交ZIP、代码、依赖、中间证据与核查记录。'}
    record.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(r,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);a=p.parse_args();run(a.artifact)
