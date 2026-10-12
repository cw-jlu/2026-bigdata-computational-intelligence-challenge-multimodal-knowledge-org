from common import *
from openpyxl import load_workbook
import hashlib
def create():
 for n in NODES:
  ee=load(BASE/f'audits/{n}/candidate_decisions.json');included=sorted([e for e in ee if e['decision']=='纳入'],key=lambda e:hashlib.sha256(('20261012_review_'+e['id']).encode()).hexdigest())[:2]
  excluded=sorted([e for e in ee if e['decision']=='排除'],key=lambda e:hashlib.sha256(('20261012_review_'+e['id']).encode()).hexdigest())[:2];cards=[]
  for e in included+excluded:
   w=load_workbook(ROOT/e['radar_file'],data_only=True);s=w[e['sheet']];rows=list(s.values);h=rows[0];rr=[{'row':i,**dict(zip(h,r))} for i,r in enumerate(rows[1:],2) if r[0]==e['batch']];w.close()
   txt=[]
   for source,a in e['claims'].items():
    p=ROOT/a['path'];txt.append({'source':source,'file':a['path'],'sha256':sha(p),'full_text':p.read_text(encoding='utf-8-sig')})
   vals={k:sorted({str(r.get(k)) for r in rr}) for k in ['国家地区','目标类型','机舰名','目标数量','数量','任务','活动区域','首点时间','结束时间','位置时间'] if any(k in r for r in rr)}
   cards.append({'event_id':e['id'],'pipeline_decision':e['decision'],'radar_original_rows':rr,'radar_unique_values':vals,'texts':txt,'pipeline_facts':e['facts'],'pipeline_issues':e['issues'],'review_scope':'independent direct raw source reading; development sampling, not blind or external expert truth'})
  save(BASE/f'audits/{n}/independent_review_cards.json',cards)
def show(start,end):
 for n in NODES[start:end]:
  print('NODE',n)
  for c in load(BASE/f'audits/{n}/independent_review_cards.json'):
   print(c['event_id'],c['pipeline_decision'],'RADAR',c['radar_unique_values'])
   for t in c['texts']:print(t['source'],t['file'],t['full_text'])
   print('OUTPUT',c['pipeline_facts'],'ISSUES',c['pipeline_issues'])
if __name__=='__main__':
 import sys
 if len(sys.argv)==1:create()
 else:show(int(sys.argv[1]),int(sys.argv[2]))
