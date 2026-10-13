from common import *
import zipfile,os
KEEP=['inputs','code','prompts','sources','evidence','views','audits','audit','frozen_analysis','official','qa']
ROOT_FILES=['README.md','交付与复现说明.md','progress.md','run_v14.ps1','requirements-lock.txt','workbooks.json','word_render.json','excel_render.json','raster_records.json','delivery_verification.json','independent_zip_verification.json']
def collect(folder,prefix=''):
 result={}
 for current,dirs,files in os.walk(folder,followlinks=False):
  dirs[:]=[d for d in dirs if d not in ['node_modules','__pycache__'] and not d.startswith('unpacked_')]
  for name in files:
   p=Path(current)/name;result[prefix+p.relative_to(folder).as_posix()]=p
 return result
def main():
 members={}
 for folder in KEEP:members.update(collect(BASE/folder,folder+'/'))
 for name in ROOT_FILES:
  if (BASE/name).exists():members[name]=BASE/name
 for label in ['reproduced_fresh_v14','reproduced_frozen_v14']:
  root=BASE/label
  for folder in ['code','prompts','audits','audit','official','qa']:
   if (root/folder).exists():members.update(collect(root/folder,label+'/'+folder+'/'))
  for name in ['word_render.json','excel_render.json','raster_records.json','delivery_verification.json','independent_zip_verification.json']:
   if (root/name).exists():members[label+'/'+name]=root/name
 manifest={name:{'sha256':sha(p),'bytes':p.stat().st_size} for name,p in sorted(members.items())}
 save(BASE/'engineering_manifest.json',manifest);members['engineering_manifest.json']=BASE/'engineering_manifest.json'
 archive=BASE/'赛题2_初赛_v14_完整工程包.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,p in sorted(members.items()):
   info=zipfile.ZipInfo(name,(2025,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
 with zipfile.ZipFile(archive) as z:assert len(z.namelist())==len(members) and z.testzip() is None
 save(BASE/'engineering_archive_receipt.json',{'archive':archive.name,'sha256':sha(archive),'members':len(members),'bytes':archive.stat().st_size,'raw_input_files':len(load(BASE/'audit/input_copy_manifest.json')['files']),'credentials_included':False,'node_modules_included':False,'independent_rebuilds':'Both fresh-model and frozen-analysis experiments; raw input duplicated once only','score':'v14 pending platform evaluation'})
 print('ENGINEERING_PACKAGE',len(members),'members',archive.stat().st_size,'bytes',sha(archive),flush=True)
if __name__=='__main__':main()
