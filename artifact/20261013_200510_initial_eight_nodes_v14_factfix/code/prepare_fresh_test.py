"""Stage the independent fresh-inference experiment before formal compilation."""
from common import *
import shutil,subprocess,sys,argparse
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();dest=a.output.resolve();assert not dest.exists();dest.mkdir(parents=True)
for folder in ['inputs','code','sources']:
 shutil.copytree(BASE/folder,dest/folder,ignore=shutil.ignore_patterns('__pycache__','node_modules'))
(dest/'prompts').mkdir();(dest/'evidence').mkdir();(dest/'audit').mkdir()
for name in ['analysis_prompt.txt','runtime_config.json']:shutil.copy2(BASE/'prompts'/name,dest/'prompts'/name)
shutil.copy2(BASE/'evidence/sample_structure.json',dest/'evidence/sample_structure.json')
env={**os.environ,'COMPETITION_PROJECT_ROOT':str(dest/'inputs'),'PYTHONIOENCODING':'utf-8'}
for command in [[sys.executable,dest/'code/rebuild.py','--output',dest],[sys.executable,dest/'code/prepare_analysis.py']]:subprocess.run([str(x) for x in command],cwd=dest,env=env,check=True)
actual=sha(dest/'prompts/evidence_packet.json');expected=sha(BASE/'prompts/evidence_packet.json');assert actual==expected,'fresh raw reconstruction changed model input'
save(dest/'audit/fresh_input_comparison.json',{'raw_rebuilt':True,'copied_ledgers':False,'input_packet_hash':actual,'reference_packet_hash':expected,'identical':True})
print('FRESH_INPUT_READY',dest,flush=True)
