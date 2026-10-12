from common import *
import re,collections
from docx import Document
CORRIDORS=['台湾海峡','巴士海峡','巴林塘海峡','宫古水道','对马海峡']

def relation_card(e):
 claims=[]
 for source,a in e['claims'].items():
  # Work on the already associated factual segment, never on title/filename.
  text=re.split(r'从公开信息看|相关活动可能|相关行动可能|相关动向可能',a['snippet'])[0]
  for verb in ['进入','离开']:
   for m in re.finditer(verb,text):
    left=text[max(0,m.start()-5):m.start()]
    neg=bool(re.search(r'未|没有|否认|并非|不是',left))
    tail=text[m.end():];loc=next((r for r in sorted(a.get('regions',[]),key=len,reverse=True) if tail.startswith(r)),None)
    indirect=loc is None and bool(re.match(r'(?:该|这一|任务|指定)(?:任务)?海域',tail))
    # Do not turn an omitted object into an asserted core-sea crossing.
    if indirect and len(a.get('regions',[]))==1:loc=a['regions'][0]
    claims.append({'source':source,'relation':verb,'object':loc,'object_basis':'explicit' if loc and not indirect else 'single-region anaphora' if loc else 'unresolved','negated':neg,'quote':text,'file':a['path'],'locator':a['locator'],'sha256':a['sha256']})
 accepted=[]
 for verb in ['进入','离开']:
  positives=[c for c in claims if c['relation']==verb and c['object'] and not c['negated']]
  for obj in sorted({c['object'] for c in positives}):
   support=sorted({c['source'] for c in positives if c['object']==obj})
   negatives=[c for c in claims if c['relation']==verb and c['object']==obj and c['negated']]
   if len(support)>=2 and not negatives:accepted.append({'relation':verb,'object':obj,'support_types':support})
 region=e['field_audit']['region']
 return {'event_id':e['id'],'activity':{'object':e['facts']['region'],'support_types':region['support_types'],'conflicts':region['conflicts']},'entry_exit_claims':claims,'accepted_entry_exit':accepted,'formal_policy':'Only verified activity is reported; single-source or unresolved entry/exit is not promoted. Start/end observations are not boundary-crossing times. Entry and later exit are not inherently contradictory.'}

def main():
 records=[];raw=[]
 for p in sorted((BASE/'evidence/daily').glob('*/raw_texts.json'),key=lambda p:dt(p.parent.name)):
  for a in load(p):
   raw.append({'date':p.parent.name,'path':a['path'],'sha256':a['sha256'],'corridors':[x for x in CORRIDORS if x in a['text']]})
 for n in NODES:
  ad=BASE/f'audits/{n}';f=load(ad/'frozen_ledger.json');old=load(BASE/f'evidence/v10_baseline/{n}/frozen_ledger.json');m=f['mainline'];today=f['today_events']
  assert all(dt(e['date'])<=dt(n) for e in f['verified_events'])
  assert all(e['date']==n for e in today)
  assert {e['id']:e['facts'] for e in today}=={e['id']:e['facts'] for e in old['today_events']}
  all_related=[e for e in f['verified_events'] if e['key']==m['key'] and e['facts']['country']==m['country']]
  assert set(m['events'])=={e['id'] for e in all_related}
  assert 2<=len(m['stages'])<=3 and set(sum([x['events'] for x in m['stages']],[]))==set(m['events'])
  cards=[relation_card(e) for e in today];scope=[x for x in raw if dt(x['date'])<=dt(n)]
  corridors=[x for x in scope if x['corridors']]
  # No corridor instance exists in this supplied input. Do not claim a tested
  # universal corridor route resolver from a zero-case audit.
  save(ad/'relation_review.json',{'node':n,'raw_text_files_in_scope':len(scope),'corridor_terms':CORRIDORS,'corridor_documents':corridors,'events':cards,'scope_limit':'Phrase/object audit of associated source segments; not a complete route reconstruction model. Corridor admission needs explicit supported core-sea entry/exit, never geographic adjacency.'})
  ps=[p.text for p in Document(BASE/f'official/{n}/{n}日报.docx').paragraphs]
  second=ps.index('二、重点态势分析');third=ps.index('三、外（台）机舰活动情况');fifth=ps.index('五、次日关注重点')
  outside=ps[:second]+ps[third:]
  assert not any(re.search(r'\[H\d|\[B\d',s) for s in outside)
  assert second<ps.index('本节引用与跨日证据索引')<third
  dates=[dt(x) for x in m['dates']];gaps=[{'from':a.isoformat(),'to':b.isoformat(),'days':(b-a).days} for a,b in zip(dates,dates[1:]) if (b-a).days>1]
  omitted=[e for e in all_related if e['id'] not in old['mainline']['events']]
  # Retain excluded/outside candidates with matching subject/model as context;
  # they are not reclassified as verified history.
  unresolved=[]
  for p in (BASE/'evidence/daily').glob('*/candidate_ledger.json'):
   if dt(p.parent.name)>dt(n):continue
   for e in load(p):
    if e['key']==m['key'] and (e['facts']['country']==m['country'] or any(a['country']==m['country'] for a in e['claims'].values())) and e['decision']!='纳入':unresolved.append({'event_id':e['id'],'decision':e['decision'],'issues':e['issues']})
  row={'node':n,'today_events':len(today),'daily_facts_changed':False,'full_related_verified_events':len(all_related),'restored_history':[{'id':e['id'],'date':e['date'],'facts':e['facts']} for e in omitted],'missing_related_verified_events':[],'stages':m['stages'],'observational_gaps':gaps,'related_unverified_candidates':unresolved,'corridor_documents_in_scope':len(corridors),'accepted_entry_exit_claims':sum(len(c['accepted_entry_exit']) for c in cards),'second_section_history_scope':'full stage','history_outside_second_section':False}
  save(ad/'three_module_changes.json',{'facts':'daily event decisions and values unchanged; entry/exit source-object audit added, unsupported relations not asserted','analysis':row,'format':'Historical/external index moved inside section II; section V rewritten using current-day facts only; template, workbook schema and four PNG definitions retained'})
  records.append(row)
 save(BASE/'evidence/v11_revision_audit.json',{'nodes':records,'raw_text_files':len(raw),'corridor_documents':[x for x in raw if x['corridors']],'restored_history_total':sum(len(x['restored_history']) for x in records),'daily_events':sum(x['today_events'] for x in records),'platform_evaluation':None})
 print('Revision audit',sum(len(x['restored_history']) for x in records),'historical records restored; daily facts unchanged')
if __name__=='__main__':main()
