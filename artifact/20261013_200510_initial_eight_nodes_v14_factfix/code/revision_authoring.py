"""Reuse genuinely unchanged node authoring, and call Codex for the corrected node.

This authoring helper records provenance. Portable fresh reproduction always
calls all eight nodes through run_codex_analysis.py instead.
"""
from common import *
import argparse,shutil,time
import run_codex_analysis as model

def run(prior,out,run_id,codex):
    packet=load(out/'prompts/evidence_packet.json');run=out/'audit/codex_runs'/run_id
    assert not run.exists();run.mkdir(parents=True);origins=[]
    for i,n in enumerate(NODES[:-1]):
        previous=load(prior/f'audits/{n}/analysis_input.json')
        assert previous==packet['nodes'][i],f'{n}: authoring packet changed, cannot reuse'
        src=prior/'audit/codex_runs/reviewed_A'/n
        if run_id.endswith('B'):src=prior/'audit/codex_runs/reviewed_B'/n
        prompt=(BASE/'prompts/analysis_prompt.txt').read_text(encoding='utf8')+json.dumps({'execution_policy':packet['execution_policy'],'nodes':[packet['nodes'][i]]},ensure_ascii=False,separators=(',',':'))
        extra=load(BASE/'prompts/node_constraints.json').get(n,'')
        if extra:prompt+='\nAUTHORING_CONSTRAINTS:\n'+extra
        assert prompt== (src/'prompt.txt').read_text(encoding='utf8'),f'{n}: actual original prompt differs'
        shutil.copytree(src,run/n)
        origins.append({'node':n,'mode':'reuse_verified_unchanged_actual_inference','source':str(src),'prompt_sha256':sha(src/'prompt.txt'),'new_model_calls':0})
    n=NODES[-1];cfg=load(BASE/'prompts/runtime_config.json')
    for attempt in range(1,cfg['max_node_attempts']+1):
        rel=run_id+'/revision_attempt_'+str(attempt).zfill(2)
        try:
            model.generate_one(rel,codex,out,7);src=out/'audit/codex_runs'/rel;break
        except AssertionError:
            events=load(out/'audit/codex_runs'/rel/'events.json')
            if not any(x in json.dumps(events) for x in ['capacity','timed out','stream disconnected','Reconnecting','429','500','502','503']) or attempt==cfg['max_node_attempts']:raise
            time.sleep(2)
    shutil.copytree(src,run/n)
    origins.append({'node':n,'mode':'new_actual_isolated_inference','source':str(src),'prompt_sha256':sha(src/'prompt.txt'),'new_model_calls':1})
    save(run/'answer.json',{'nodes':[load(run/n/'answer.json')['nodes'][0] for n in NODES]})
    save(run/'reuse_and_new_invocations.json',{'node_origins':origins,'new_successful_model_calls':1,'prior_nodes_raw_ledgers_and_authoring_packets_exact':True})
    model.compile_result(run_id,out)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--output',type=Path,default=BASE);ap.add_argument('--run-id',required=True);ap.add_argument('--codex',required=True);a=ap.parse_args();run(a.prior.resolve(),a.output.resolve(),a.run_id,a.codex)
