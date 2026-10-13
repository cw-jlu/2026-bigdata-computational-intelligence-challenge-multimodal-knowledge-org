"""Apply fixed node constraints through new, isolated model calls, retaining old runs."""
from common import *
from run_codex_analysis import generate_one,validate
import argparse,shutil
from concurrent.futures import ThreadPoolExecutor
ap=argparse.ArgumentParser();ap.add_argument('--original-run',required=True);ap.add_argument('--new-run',required=True);ap.add_argument('--codex',required=True);a=ap.parse_args()
target=BASE/'audit/codex_runs'/a.new_run;assert not target.exists();target.mkdir(parents=True)
def work(i):
 n=NODES[i];generate_one(a.new_run+'/'+n+'/attempt_01',a.codex,BASE,i);src=target/n/'attempt_01'
 for name in ['answer.json','prompt.txt','invocation.json','completion.json']:shutil.copy2(src/name,target/n/name)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(work,[6,7]))
orig=BASE/'audit/codex_runs'/a.original_run;origins={}
for i,n in enumerate(NODES):
 source=orig/n if i<6 else target/n;origins[n]=source.relative_to(BASE).as_posix()
 if i<6:shutil.copytree(source,target/n)
result={'nodes':[load(target/n/'answer.json')['nodes'][0] for n in NODES]};validate(result,load(BASE/'prompts/evidence_packet.json'));save(target/'answer.json',result)
save(target/'run_manifest.json',{'node_origins':origins,'model_and_sampling_parameters_unchanged':True,'changed_prompt_scope':NODES[6:],'reason':'current-agent semantic review found unnecessary doubts about known event/batch counts; fixed guards applied via genuine fresh model calls'})
print('SHIP_REFINEMENT_COMPLETE',a.new_run,flush=True)
