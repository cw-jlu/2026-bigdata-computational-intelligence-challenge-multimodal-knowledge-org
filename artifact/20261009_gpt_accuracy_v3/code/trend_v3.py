"""Compare current-day lines and segment observed geographic/mission changes."""
from collections import Counter
from datetime import datetime
from itertools import combinations
def date(s):return datetime.strptime(s,'%Y.%m.%d')
def phases(history):
    days=[]
    for d in sorted({e['date'] for e in history},key=date):
        ee=[e for e in history if e['date']==d]
        days.append({'date':d,'events':ee,'signature':(tuple(sorted({e['region'] for e in ee})),tuple(sorted({e['task'] for e in ee})))})
    boundaries=[]
    for i in range(1,len(days)):
        prev,cur=days[i-1],days[i]; gap=(date(cur['date'])-date(prev['date'])).days
        changes=[]
        if prev['signature'][0]!=cur['signature'][0]:changes.append('具体区域组合改变')
        if prev['signature'][1]!=cur['signature'][1]:changes.append('核验任务组合改变')
        if gap>=8:changes.append(f'证据间隔{gap}日')
        if changes:boundaries.append({'index':i,'previous_date':prev['date'],'current_date':cur['date'],'changes':changes,'previous_signature':prev['signature'],'current_signature':cur['signature'],'gap_days':gap})
    if not boundaries:return None
    def cost(lo,hi):
        ee=[e for day in days[lo:hi] for e in day['events']];n=len(ee)
        return sum(n-max(Counter(e[f] for e in ee).values()) for f in ['region','task'])
    def loss(splits):
        bounds=[0,*splits,len(days)];return sum(cost(a,b) for a,b in zip(bounds,bounds[1:]))
    b2=min(boundaries,key=lambda b:(loss([b['index']]),-len(b['changes']),-b['gap_days'],b['index'])); chosen=[b2['index']];l2=loss(chosen)
    triples=[]
    for x,y in combinations([b['index'] for b in boundaries],2):
        # Three phases require separate, sustained evidence regimes. A single
        # outlier date is described as variation, not promoted to a phase.
        if min(x,y-x,len(days)-y)>=2:triples.append((loss([x,y]),x,y))
    if triples:
        l3,x,y=min(triples)
        if l2>0 and (l2-l3)/l2>=.35:chosen=[x,y]
    pp=[];bounds=[0,*chosen,len(days)]
    for index,(lo,hi) in enumerate(zip(bounds,bounds[1:])):
        dd=days[lo:hi];ee=[e for d in dd for e in d['events']]
        boundary=next((b for b in boundaries if b['index']==lo),None)
        pp.append({'start':dd[0]['date'],'end':dd[-1]['date'],'dates':[x['date'] for x in dd],'event_ids':[e['event_id'] for e in ee],'regions':dict(Counter(e['region'] for e in ee)),'tasks':dict(Counter(e['task'] for e in ee)),'intervals':[e['interval'] for e in ee],'gaps':[(date(b['date'])-date(a['date'])).days for a,b in zip(dd,dd[1:])],'boundary':boundary,'first_observation':ee[0]['event_id'],'last_observation':ee[-1]['event_id'],'dominant_region':Counter(e['region'] for e in ee).most_common(1)[0][0],'dominant_task':Counter(e['task'] for e in ee).most_common(1)[0][0]})
    return pp,{'all_candidate_boundaries':boundaries,'two_phase_cost':l2,'selected_cost':loss(chosen),'three_phase_rule':'额外减少至少35%区内异质性，且每阶段至少两个证据日；不是按日期数自动取三段'}
def choose(node,cache):
    current=[e for e in cache[node] if e['decision']=='纳入' and e['country']!='中国']; candidates=[]
    keys=sorted({(e['country'],e['platform_key'],e['direction']) for e in current})
    for country,platform,direction in keys:
        seeds=[e for e in current if (e['country'],e['platform_key'],e['direction'])==(country,platform,direction)]
        hist=sorted([e for d,ee in cache.items() if date(d)<=date(node) for e in ee if e['decision']=='纳入' and (e['country'],e['platform_key'],e['direction'])==(country,platform,direction)],key=lambda e:(date(e['date']),e['interval'][0],e['region']))
        distinct=sorted({e['date'] for e in hist},key=date);start=0
        for i in range(1,len(distinct)):
            if (date(distinct[i])-date(distinct[i-1])).days>=15:start=i
        hist=[e for e in hist if e['date'] in distinct[start:]];dd=distinct[start:]; result=phases(hist) if len(dd)>=3 else None
        regional_return=sum(e['region'] in {x['region'] for x in seeds} for e in hist)
        mission_return=sum(e['task'] in {x['task'] for x in seeds} for e in hist)
        important=any(any(w in e['platform'] for w in ['航空母舰','两栖攻击舰','战略轰炸机']) for e in seeds)
        specific=any(e['region'] not in ['东海','南海','黄海'] for e in seeds)
        candidate={'country':country,'platform':seeds[0]['platform'],'platform_key':platform,'direction':direction,'current_event_ids':[e['event_id'] for e in seeds],'dates':dd,'date_count':len(dd),'same_specific_region_observations':regional_return,'same_current_task_observations':mission_return,'eligible':result is not None,'rejection':None if result else '不足三日或没有支持2—3阶段的实际变化','selection_basis':{'current_important_platform':important,'current_specific_region':specific,'same_region_ratio':round(regional_return/max(1,len(hist)),3),'same_task_ratio':round(mission_return/max(1,len(hist)),3)},'evidence':hist,'phases':result[0] if result else [],'segmentation':result[1] if result else {}}
        # Current relevance and observed region/task recurrence take precedence;
        # date count is used only to break otherwise comparable candidates.
        candidate['rank']=[int(important),int(specific),regional_return/max(1,len(hist)),mission_return/max(1,len(hist)),len(dd)]
        candidates.append(candidate)
    good=sorted([c for c in candidates if c['eligible']],key=lambda c:c['rank'],reverse=True)
    if not good:return None
    best=good[0].copy();best['gaps']=[(date(b)-date(a)).days for a,b in zip(best['dates'],best['dates'][1:])];best['identity_limit']='同主体、完整平台型号和同核心海域的活动线索；具名舰体可追踪专名，舰级与机型不证明同一实体，不据此推断意图或移动航迹'
    best['candidate_comparison']=[{k:v for k,v in c.items() if k not in ['evidence','phases','segmentation']} for c in sorted(candidates,key=lambda c:c['rank'],reverse=True)]
    best['selection_reason']=f"节点当日{best['platform']}在{best['direction']}仍有活动，优先比较重要平台和具体区域，再比较与当日区域、任务相同的历史比例；{len(best['dates'])}日期仅满足回溯要求并作末位比较，阶段来自具体区域或任务的实际变化。"
    return best
