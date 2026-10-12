from common import *
from copy import deepcopy
SELECT={'2025.5.10':('德国','台风'),'2025.5.18':('德国','巴登符腾堡'),'2025.5.30':('韩国','p8a'),'2025.6.9':('马来西亚','莱库'),'2025.6.17':('澳大利亚','p8a'),'2025.6.29':('新加坡','g550'),'2025.7.9':('加拿大','哈利法克斯'),'2025.7.17':('法国','戴高乐')}
def select(out=BASE):
 for n,(country,key) in SELECT.items():
  p=out/f'audits/{n}/frozen_ledger.json';f=load(p);prev=sha(p);m=deepcopy(next(c for c in f['candidate_comparison'] if c['country']==country and c['key']==key))
  if n=='2025.5.10':
   m['stages']=[{'dates':['2025.5.1','2025.5.2'],'events':[e['id'] for e in f['verified_events'] if e['id'] in m['events'] and e['date'] in ['2025.5.1','2025.5.2']],'boundary_basis':'东海与黄海训练、巡逻的前段；两个海域分别陈述，不推连续驻留'},m['stages'][2],m['stages'][3]]
  if n=='2025.6.17':
   datesets=[['2025.5.19','2025.5.24','2025.5.28'],['2025.5.29','2025.5.30'],['2025.6.2','2025.6.6','2025.6.8','2025.6.11','2025.6.14','2025.6.16','2025.6.17']]
   m['stages']=[{'dates':ds,'events':[e['id'] for e in f['verified_events'] if e['id'] in m['events'] and e['date'] in ds],'boundary_basis':b} for ds,b in zip(datesets,['南海反潜为主并有联合巡逻；每条活动独立','5月29日黄海、30日东海，出现核实区域转换','6月2日起再次以南海反潜为主；节点日并有黄海记录，不能称只在南海活动'])]
  m['selected']=True;m['suitable']=True;m['selection_reason']='比较当日仍出现的候选后，优先可解释的阶段变化、重复证据与字段质量。更长但频繁混合多区域的线索不压成均匀三段；单日阶段明确标出。'
  f['mainline']=m;save(p,f);save(out/f'audits/{n}/freeze_revisions.json',{'before_selection_sha256':prev,'after_selection_sha256':sha(p),'fact_records_changed':False,'reason':'在分析生成前根据候选比较重新选择主线和证据阶段，事实集不变'})
  save(out/f'audits/{n}/freeze_record.json',{'as_of':f['as_of'],'path':f'audits/{n}/frozen_ledger.json','sha256':sha(p),'cutoff_check':all(dt(e['date'])<=dt(n) for e in f['verified_events']),'frozen_before_analysis':True})
  print(n,m['country'],m['platform'],len(m['dates']),[s['dates'] for s in m['stages']])
if __name__=='__main__':select()