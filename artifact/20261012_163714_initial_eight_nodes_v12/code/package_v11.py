from common import *
import os,zipfile

def main():
 assert load(BASE/'stage_audit.json')['formal_file_count']==48
 assert load(BASE/'reproduction_comparison.json')['status']=='PASS'
 allowed={'audits','code','evidence','inputs','official','qa'}
 skip={'node_modules','__pycache__','independent_unpacked'}
 selected=[]
 for root,dirs,files in os.walk(BASE,followlinks=False):
  root=Path(root);rel=root.relative_to(BASE)
  dirs[:]=[d for d in dirs if d not in skip and (rel.parts or d in allowed)]
  for name in files:
   p=root/name;r=p.relative_to(BASE)
   if not rel.parts:
    if p.suffix not in {'.md','.txt','.json','.ps1','.log'}:continue
    if name in {'engineering_manifest.json','engineering_package.json'}:continue
   if p.suffix=='.pyc':continue
   selected.append(p)
 # Keep compact reproduction proof without packaging repeated output trees.
 for sub in ['reproduction_final','one_click_reproduction']:
  for name in ['run.log','package_validation.json','submission_manifest.json']:
   p=BASE/sub/name
   if p.exists():selected.append(p)
 rows=[{'path':p.relative_to(BASE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(selected))]
 save(BASE/'engineering_manifest.json',{'files':rows,'binaries_vendored':False,'manifest_self_excluded_from_hash_list':True,'repeated_reproduction_outputs_omitted':True})
 dest=BASE/'赛题2_初赛_v11_完整工程包.zip'
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
  for r in rows:z.write(BASE/r['path'],r['path'])
  z.write(BASE/'engineering_manifest.json','engineering_manifest.json')
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  assert set(z.namelist())=={r['path'] for r in rows}|{'engineering_manifest.json'}
  for r in rows:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256'],r['path']
 save(BASE/'engineering_package.json',{'status':'PASS','archive':dest.name,'sha256':sha(dest),'bytes':dest.stat().st_size,'members':len(rows)+1,'member_hashes_verified':True,'runtime':'dependency manifest and tested run-all.ps1 supplied; Codex runtime, Office and fonts not redistributed','uploaded':False})
 print('Engineering ZIP verified',len(rows)+1,'members',dest.stat().st_size,'bytes',flush=True)
if __name__=='__main__':main()
