"""Package only this version, with no runtime junctions or other artifacts."""
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,ZipInfo

V=Path(__file__).resolve().parents[1]
target=V/'复现材料_gpt_accuracy_v2.zip'
manifest=V/'reproduction_manifest.json'
excluded={'node_modules','__pycache__','.venv','.git'}
entries=[]
for folder,dirs,files in os.walk(V,topdown=True,followlinks=False):
    dirs[:]=[d for d in dirs if d not in excluded and not Path(folder,d).is_symlink()]
    for name in sorted(files):
        p=Path(folder,name)
        if p in (target,manifest) or p.suffix in ('.pyc','.pyo'): continue
        if not p.resolve().is_relative_to(V.resolve()): raise RuntimeError('External file in version package')
        entries.append({'path':p.relative_to(V).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
entries.sort(key=lambda e:e['path'])
assert any(e['path']=='code/fusion.py' for e in entries)
assert len([e for e in entries if e['path'].startswith('output/日报/')])==48
assert not any('node_modules' in e['path'].split('/') for e in entries)
manifest.write_text(json.dumps({'files':len(entries),'entries':entries,'note':'This manifest excludes itself and the reproduction ZIP. External runtime junctions excluded; original inputs remain in repository, raw audit snapshot included.'},ensure_ascii=False,indent=2),encoding='utf-8')
with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=7) as z:
    for e in entries:
        zi=ZipInfo(V.name+'/'+e['path'],date_time=(2026,10,9,0,0,0));zi.compress_type=ZIP_DEFLATED;zi.external_attr=0o644<<16
        z.writestr(zi,(V/e['path']).read_bytes())
    z.write(manifest,V.name+'/reproduction_manifest.json')
with ZipFile(target) as z:
    assert z.testzip() is None
    for e in entries: assert hashlib.sha256(z.read(V.name+'/'+e['path'])).hexdigest()==e['sha256']
print(json.dumps({'files':len(entries)+1,'zip_bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},ensure_ascii=False))
