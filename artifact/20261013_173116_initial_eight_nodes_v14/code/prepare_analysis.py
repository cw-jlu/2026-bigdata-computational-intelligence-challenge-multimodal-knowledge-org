"""Derive authoring inputs from freshly rebuilt ledgers, never old prose."""
from common import *
from collections import Counter
import source_config

POLICY=[
 ('日本','p1',[('2025.5.5','2025.5.5'),('2025.5.6','2025.5.6'),('2025.5.7','2025.5.10')]),
 ('加拿大','ch148',[('2025.5.2','2025.5.5'),('2025.5.7','2025.5.12'),('2025.5.18','2025.5.18')]),
 ('韩国','p8a',[('2025.5.5','2025.5.5'),('2025.5.12','2025.5.12'),('2025.5.21','2025.5.30')]),
 ('英国','rc135w',[('2025.5.27','2025.5.28'),('2025.6.3','2025.6.6'),('2025.6.9','2025.6.9')]),
 ('澳大利亚','p8a',[('2025.5.4','2025.5.24'),('2025.5.28','2025.6.8'),('2025.6.11','2025.6.17')]),
 ('新加坡','g550',[('2025.6.2','2025.6.6'),('2025.6.16','2025.6.16'),('2025.6.22','2025.6.29')]),
 ('加拿大','哈利法克斯',[('2025.5.10','2025.5.26'),('2025.6.24','2025.7.6'),('2025.7.8','2025.7.9')]),
 ('法国','戴高乐',[('2025.5.25','2025.6.9'),('2025.6.13','2025.7.11'),('2025.7.14','2025.7.17')]),
]
QUESTIONS=[
 '日本P-1的侦察记录是否代表反潜任务被替代，还是同一海域任务组合内的插入？',
 '加拿大CH-148多海域活动后重现南海联合巡逻，是任务与方向再现还是同一机体转移？',
 '韩国P-8A黄海反潜记录为何值得跟踪，当日两批说明任务集中还是机队扩大？',
 '英国RC-135W的ISR与电子侦察标签并存，是任务更替还是分类层次不同？',
 '澳大利亚P-8A南海反潜与黄海侦察并存，如何判断任务扩展与身份缺口？',
 '新加坡G550由东海ISR、空中警戒到黄海ISR，变化发生在任务还是地域层面？',
 '加拿大哈利法克斯级黄海编队警戒的重复记录，能说明何种模式，舰级身份留下何种替代解释？',
 '戴高乐号南海编队警戒与黄海战备巡逻后重现南海警戒，如何理解有限的任务组合变化？',
]
def prepare(out=BASE):
 packets=[]
 for n,policy,q in zip(NODES,POLICY,QUESTIONS):
  f=load(out/f'audits/{n}/frozen_ledger.json');country,key,ranges=policy
  c=next(x for x in f['candidate_comparison'] if x['country']==country and x['key']==key)
  assert c['eligible'];ids=set(c['event_ids']);events=sorted([e for e in f['verified_events'] if e['id'] in ids],key=lambda e:(dt(e['date']),e['start'] or 0,e['id']))
  stages=[]
  for i,(lo,hi) in enumerate(ranges):
   es=[e for e in events if dt(lo)<=dt(e['date'])<=dt(hi)];assert es
   stages.append({'id':f'S{i+1}','dates':sorted({e['date'] for e in es},key=dt),'events':[e['id'] for e in es], 'boundary_basis':'待模型根据本阶段任务、方向、窗口及与相邻阶段的区别说明；边界为本次低风险对照预先冻结的执行政策','count':{'evidence_days':len({e['date'] for e in es}),'events':len(es),'participation':sum(e['facts']['quantity'] for e in es)},'tasks':dict(Counter(e['facts']['task'] for e in es)),'directions':dict(Counter(e['facts']['direction'] for e in es))})
  assert {x for s in stages for x in s['events']}==ids
  selection={'country':country,'key':key,'kind':c['kind'],'platform':c['platform'],'dates':c['dates'],'events':c['event_ids'],'stages':stages,'selection_reason':'v14预先冻结主线用于最后一次改进与Codex重复运行对照；全部合格候选在输入中保留并要求比较，不冒称盲选','identity_scope':c['identity_scope']}
  record={'node':n,'as_of':f['as_of'],'frozen_sha256':sha(out/f'audits/{n}/frozen_ledger.json'),'question':q,'selection':selection,'events':[{'id':e['id'],'date':e['date'],'kind':e['kind'],'facts':e['facts']} for e in events],'conflict_candidates':c['conflict_candidates'],'no_verified_record_dates':c['no_verified_record_dates'],'candidates':[{k:x[k] for k in ['country','key','kind','platform','dates','observed_tasks','directions','identity_scope','today_ids']} | {'conflict_candidate_count':len(x['conflict_candidates'])} for x in f['candidate_comparison'] if x['eligible']],'external_sources':[source_config.SOURCES[x] for x in source_config.USED[n]]}
  packets.append(record);save(out/f'audits/{n}/analysis_input.json',record)
 save(out/'prompts/evidence_packet.json',{'execution_policy':'preserve_v13_mainline_and_stage_boundaries_after_new_raw_reconstruction','nodes':packets})
 # Runtime configuration is a reviewed immutable input, never regenerated from user defaults.
 assert (out/'prompts/runtime_config.json').exists()
 print('PREPARED',len(packets),'nodes')
if __name__=='__main__':prepare()
