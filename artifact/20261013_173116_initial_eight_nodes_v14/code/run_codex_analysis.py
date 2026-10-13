from common import *
import subprocess,sys,argparse,os,time,re

def obj(props):return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}
STR={'type':'string'};ARR={'type':'array','items':STR}
BLOCK=obj({'text':STR,'premise_event_ids':ARR})
STAGE=obj({'text':STR,'premise_event_ids':ARR,'boundary_basis':STR})
EXT=obj({'text':STR,'premise_event_ids':ARR,'external_source_ids':ARR})
NODE=obj({'node':{'type':'string','enum':NODES},'question':STR,'selection_review':STR,'overall':BLOCK,'stage1':STAGE,'stage2':STAGE,'stage3':STAGE,'external':EXT,'judgment':BLOCK,'next_focus':STR})
SCHEMA=obj({'nodes':{'type':'array','items':NODE}})

def generate_one(run_id,cli,out=BASE,one=None):
 cfg=load(BASE/'prompts/runtime_config.json');packet=load(out/'prompts/evidence_packet.json')
 if one is not None:packet={'execution_policy':packet['execution_policy'],'nodes':[packet['nodes'][one]]}
 run=out/'audit/codex_runs'/run_id;assert not run.exists(), 'fresh run directory required';run.mkdir(parents=True)
 schema=run/'schema.json';save(schema,SCHEMA)
 prompt=(BASE/'prompts/analysis_prompt.txt').read_text(encoding='utf8')+json.dumps(packet,ensure_ascii=False,separators=(',',':'))
 constraint_file=BASE/'prompts/node_constraints.json'
 supplement=load(constraint_file).get(packet['nodes'][0]['node'],'') if constraint_file.exists() else ''
 if supplement:prompt+='\nAUTHORING_CONSTRAINTS:\n'+supplement
 (run/'prompt.txt').write_text(prompt,encoding='utf8');answer=run/'answer.json'
 args=[cli,'exec','--ignore-user-config','--ignore-rules','--skip-git-repo-check','--sandbox','read-only','--ephemeral','--model',cfg['model'],'-c','model_reasoning_effort="'+cfg['reasoning_effort']+'"','-c','hide_agent_reasoning=true','--json','--output-schema',str(schema.resolve()),'--output-last-message',str(answer.resolve()),'-']
 provider=cfg['provider']
 args[-1:-1]=['-c','model_provider='+json.dumps(provider['id'])]+sum((['-c','model_providers.'+provider['id']+'.'+key+'='+json.dumps(value)] for key,value in provider.items() if key!='id'),[])
 version=subprocess.run([cli,'--version'],capture_output=True,text=True,encoding='utf8').stdout.strip();assert version==cfg['cli_version_required'],f'Codex version drift: {version}'
 save(run/'invocation.json',{'argv_without_executable_path':args[1:],'cli_version':version,'cli_binary_sha256':sha(Path(cli)),'config':cfg,'prompt_sha256':sha(run/'prompt.txt'),'evidence_packet_sha256':sha(out/'prompts/evidence_packet.json'),'schema_sha256':sha(schema),'credential_included':False})
 start=time.time();p=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=run,encoding='utf8',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
 stdout,stderr=p.communicate(prompt,timeout=3600)
 # Do not persist private reasoning; keep operational events, usage, and answer only.
 events=[];violations=[]
 for line in stdout.splitlines():
  try:event=json.loads(line)
  except ValueError:continue
  item=event.get('item',{});kind=item.get('type','')
  if kind in ['reasoning','agent_reasoning']:continue
  if kind and kind not in ['agent_message','error']:violations.append(kind)
  events.append(event)
 save(run/'events.json',events);(run/'stderr.txt').write_text(stderr,encoding='utf8')
 save(run/'completion.json',{'exit_code':p.returncode,'elapsed_seconds':round(time.time()-start,3),'response_sha256':sha(answer) if answer.exists() else None,'unexpected_tool_item_types':violations,'output_usage':[e.get('usage') for e in events if e.get('usage')],'context_reused':False,'node_isolation':True,'input_node':packet['nodes'][0]['node']})
 assert p.returncode==0 and answer.exists(),stderr[-2000:]
 assert not violations,f'tool use invalidated isolated run: {violations}'
 validate(load(answer),packet);print('CODEX_RUN_VALID',run_id,flush=True)

def generate(run_id,cli,out=BASE):
 from concurrent.futures import ThreadPoolExecutor
 import shutil
 cfg=load(BASE/'prompts/runtime_config.json')
 run=out/'audit/codex_runs'/run_id;assert not run.exists();run.mkdir(parents=True)
 def work(i):
  n=NODES[i]
  for attempt in range(1,cfg['max_node_attempts']+1):
   rel=run_id+'/'+n+'/attempt_'+str(attempt).zfill(2)
   try:
    generate_one(rel,cli,out,i)
    selected=out/'audit/codex_runs'/rel
    for name in ['answer.json','prompt.txt','invocation.json','completion.json']:shutil.copy2(selected/name,run/n/name)
    return {'node':n,'selected_attempt':attempt,'attempt_path':rel,'prompt_sha256':sha(selected/'prompt.txt'),'invocation_sha256':sha(selected/'invocation.json')}
   except AssertionError:
    selected=out/'audit/codex_runs'/rel
    events=load(selected/'events.json') if (selected/'events.json').exists() else []
    messages=json.dumps(events,ensure_ascii=False)
    if not any(x in messages for x in ['capacity','timed out','stream disconnected','Reconnecting','429','500','502','503']):raise
    if attempt==cfg['max_node_attempts']:raise
    print('RETRY_TRANSIENT',n,'attempt',attempt,flush=True)
    time.sleep(2)
 with ThreadPoolExecutor(max_workers=cfg['parallel_calls']) as pool:receipts=list(pool.map(work,range(8)))
 rows=[load(run/n/'answer.json')['nodes'][0] for n in NODES]
 save(run/'answer.json',{'nodes':rows})
 prompts={n:sha(run/n/'prompt.txt') for n in NODES};save(run/'prompt_manifest.json',prompts)
 save(run/'run_manifest.json',{'node_runs':receipts,'runtime_config_sha256':sha(BASE/'prompts/runtime_config.json'),'complete':True,'independent_contexts':8})
 (run/'prompt.txt').write_text(json.dumps(prompts,sort_keys=True),encoding='utf8')
 print('EIGHT_ISOLATED_CALLS_COMPLETE',run_id,flush=True)

def validate(result,packet):
 assert [x['node'] for x in result['nodes']]==[p['node'] for p in packet['nodes']]
 for r,p in zip(result['nodes'],packet['nodes']):
  ids=set(p['selection']['events']);used={s['id'] for s in p['external_sources']}
  for key in ['overall','stage1','stage2','stage3','external','judgment']:
   b=r[key];assert set(b['premise_event_ids'])<=ids and b['text'].strip(),(r['node'],key)
   if key.startswith('stage'):
    expected=set(p['selection']['stages'][int(key[-1])-1]['events']);assert set(b['premise_event_ids'])==expected
  assert set(r['external']['external_source_ids'])==used

def compile_result(run_id,out=BASE):
 packet=load(out/'prompts/evidence_packet.json');run=out/'audit/codex_runs'/run_id;r=load(run/'answer.json');validate(r,packet)
 for row,p in zip(r['nodes'],packet['nodes']):
  n=row['node'];selection=p['selection']
  for i in range(3):selection['stages'][i]['boundary_basis']=row[f'stage{i+1}']['boundary_basis']
  unit='架次' if selection['kind']=='飞机' else '艘次';stats=f"统计口径：主线共{len(selection['dates'])}个证据日期、{len(selection['events'])}条活动记录，参与数量合计{sum(e['facts']['quantity'] for e in p['events'])}{unit}；同型或同级重复出现不等于去重实体数，无核实记录日期不计为零活动。"
  normalization=[]
  for key in ['overall','stage1','stage2','stage3','external','judgment']:
   original=row[key]['text'];updated=re.sub(r'((?:合计|累计)(?:参与(?:数量)?|数量)?(?:按活动累计)?(?:为)?[一二三四五六七八九十\d]+)架(?!次)',r'\1架次',original)
   if updated!=original:normalization.append({'block':key,'operation':'aggregate_participation_unit_架_to_架次','original_text':original,'compiled_text':updated});row[key]['text']=updated
  blocks=[{'id':'Q01','type':'provided_fact','text':stats,'premise_event_ids':selection['events']}]
  for i,key in enumerate(['overall','stage1','stage2','stage3','external','judgment'],2):
   b=row[key];blocks.append({'id':f'Q{i:02d}','type':'external_background' if key=='external' else 'inference',**b})
  snap={'schema_version':14,'frozen_sha256':p['frozen_sha256'],'question':row['question'],'selection':selection,'blocks':blocks,'next_focus':row['next_focus'],'generation':{'run_id':run_id,'response_sha256':sha(run/'answer.json'),'prompt_sha256':sha(run/n/'prompt.txt'),'runtime_config_sha256':sha(BASE/'prompts/runtime_config.json'),'manual_editorial_changes':[],'deterministic_editorial_normalization':normalization,'actual_invocation_sha256':sha(run/n/'invocation.json')},'selection_review':row['selection_review']}
  save(out/f'audits/{n}/analysis_snapshot.json',snap)
 print('COMPILED',run_id,len(r['nodes']))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--run-id',required=True);ap.add_argument('--codex');ap.add_argument('--compile',action='store_true');ap.add_argument('--output',type=Path,default=BASE);a=ap.parse_args()
 if a.compile:compile_result(a.run_id,a.output.resolve())
 else:assert a.codex;generate(a.run_id,a.codex,a.output.resolve())
