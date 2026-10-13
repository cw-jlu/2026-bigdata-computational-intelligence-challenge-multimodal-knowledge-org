"""A fresh directory rebuilds all raw facts; frozen and fresh inference are distinct."""
from common import *
import argparse,subprocess,shutil,sys
def run(args,folder,env):
 print('RUN',Path(str(args[0])).name,' '.join(str(x) for x in args[1:3]),flush=True)
 subprocess.run([str(x) for x in args],cwd=folder,env=env,check=True)

def reproduce(dest,mode,node,modules,codex=None,render=False):
 assert not dest.exists(),'use a new empty output path'
 lock=load(BASE/'audit/input_copy_manifest.json')
 for record in lock['files']:assert sha(BASE/'inputs'/record['path'])==record['sha256'],'raw input differs: '+record['path']
 dest.mkdir(parents=True)
 # No ledgers, DOCX, XLSX, charts or prior candidate labels are copied.
 for folder in ['inputs','code','sources']:
  shutil.copytree(BASE/folder,dest/folder,ignore=shutil.ignore_patterns('__pycache__','node_modules'))
 (dest/'prompts').mkdir();(dest/'evidence').mkdir();(dest/'audit').mkdir()
 for name in ['analysis_prompt.txt','runtime_config.json','node_constraints.json']:shutil.copy2(BASE/'prompts'/name,dest/'prompts'/name)
 shutil.copy2(BASE/'evidence/sample_structure.json',dest/'evidence/sample_structure.json')
 env={**os.environ,'COMPETITION_PROJECT_ROOT':str(dest/'inputs'),'PYTHONIOENCODING':'utf-8'}
 run([sys.executable,dest/'code/rebuild.py','--output',dest],dest,env)
 run([sys.executable,dest/'code/prepare_analysis.py'],dest,env)
 if mode=='frozen':
  assert (BASE/'frozen_analysis').exists(),'final reviewed analysis has not been frozen'
  for n in NODES:
   snap=load(BASE/f'frozen_analysis/{n}.json');assert snap['frozen_sha256']==sha(dest/f'audits/{n}/frozen_ledger.json'),f'{n} raw fact drift; stop and re-author'
   snap['execution']={'mode':'frozen_replay_after_raw_rebuild','actual_model_calls_this_node':0,'reference_snapshot_sha256':sha(BASE/f'frozen_analysis/{n}.json')}
   save(dest/f'audits/{n}/analysis_snapshot.json',snap)
 else:
  assert codex,'fresh mode requires authorized Codex CLI'
  run([sys.executable,dest/'code/run_codex_analysis.py','--run-id','fresh_01','--codex',codex],dest,env)
  run([sys.executable,dest/'code/run_codex_analysis.py','--run-id','fresh_01','--compile'],dest,env)
 run([sys.executable,dest/'code/build.py','--output',dest],dest,env)
 if not (dest/'code/node_modules').exists():
  subprocess.run(['cmd','/c','mklink','/J',str(dest/'code/node_modules'),str(modules)],check=True,capture_output=True)
 run([node,dest/'code/workbooks.mjs',dest],dest,env)
 run([sys.executable,dest/'code/canonicalize.py','--output',dest,'--pack'],dest,env)
 run([sys.executable,dest/'code/verify_delivery.py','--output',dest,'--zip',dest/'initial_eight_nodes_v14.zip'],dest,env)
 if render:
  for script in ['render_word.ps1','render_excel.ps1']:run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',dest/'code'/script,'-Output',dest],dest,env)
  for script in ['raster_qa.py','raster_excel.py']:run([sys.executable,dest/'code'/script,'--output',dest],dest,env)
 reference=load(BASE/'audit/official_hashes.json');actual=load(dest/'audit/official_hashes.json');matches={k:actual['files'][k]==v for k,v in reference['files'].items()}
 save(dest/'audit/reproduction_result.json',{'mode':mode,'raw_reconstruction':True,'copied_fact_ledgers':False,'copied_formal_files':False,'fresh_inference':mode=='fresh','analysis_binding_checked':True,'matching_file_hashes':sum(matches.values()),'files':matches,'zip_identical':actual['zip_sha256']==reference['zip_sha256'],'comparison_limit':'fresh analysis wording may differ; inspect substantive conclusions separately'})
 if mode=='frozen':assert all(matches.values()) and actual['zip_sha256']==reference['zip_sha256']
 print('REPRODUCTION_COMPLETE',mode,sum(matches.values()),'/48 matching hashes',flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--mode',choices=['frozen','fresh'],required=True);ap.add_argument('--node',required=True);ap.add_argument('--modules',type=Path,required=True);ap.add_argument('--codex');ap.add_argument('--render',action='store_true');a=ap.parse_args();reproduce(a.output.resolve(),a.mode,a.node,a.modules.resolve(),a.codex,a.render)
