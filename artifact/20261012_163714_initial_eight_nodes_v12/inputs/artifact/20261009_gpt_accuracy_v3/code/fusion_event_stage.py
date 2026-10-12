"""Evidence-first event reconstruction. No titles/scores/file numbers establish truth.

Each platform mention is a separate claim. Identity, contradiction detection,
radar reconstruction, fact adjudication and presentation are separate steps.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime
from statistics import median

NODES=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
AIR_COLS=['日期','星期','国家地区','机型','批号','批次','架次','起飞基地','呼号','起飞时间','降落时间','活动方向','活动区域','任务描述','任务类型','备注']
SHIP_COLS=['日期','国家地区','舰船','批号','艘次','活动时间','活动方向','活动区域','任务','母港','备注']
COUNTRIES=['中国','台湾','日本','美国','英国','法国','德国','意大利','俄罗斯','澳大利亚','新西兰','新加坡','韩国','印度','菲律宾','越南','马来西亚','加拿大']
SUBJECT_ALIASES={'美军':'美国','台军':'台湾','俄军':'俄罗斯','中国大陆':'中国','台湾地区':'台湾','解放军':'中国'}
TASKS=['对海突击训练','反潜巡逻','战备警巡','空中警戒','联合巡逻','远程轰炸训练','情报监视侦察','海上侦察巡逻','舰载机起降训练','电子侦察','预警指挥','电子对抗训练','远海训练','实弹射击训练','联合巡航','战备巡逻','海上巡逻','编队警戒部署','联合搜救训练','海上护航','例行部署','两栖作战训练','海上监视侦察','自由航行','友好访问','防空反导训练','海上补给训练','远程兵力投送','搜救训练','空中加油支援']
REGION_GROUPS={
 '东海':['东海','东海北部','东海中部','东海南部','钓鱼岛海域','赤尾屿海域','上海外海','长江口外海','舟山外海','宁波外海','温州外海','冲绳海槽','苏岩礁附近海域','东海油气田海域'],
 '南海':['南海','南海北部','南海中部','南海南部','北部湾','琼州海峡','东沙群岛海域','西沙群岛海域','中沙群岛海域','南沙群岛海域','黄岩岛海域','美济礁附近海域','仁爱礁附近海域','万安滩海域','海南岛东南海域','渚碧礁附近海域','礼乐滩海域','北康暗沙海域','南康暗沙海域','珠江口外海','永暑礁附近海域','曾母暗沙海域','纳土纳群岛北部海域'],
 '黄海':['黄海','北黄海','南黄海','黄海中部','青岛外海','成山头外海','海州湾外海','济州岛西部海域','连云港外海'],
 '其他':['安达曼海','鄂霍次克海','中太平洋','白令海','菲律宾海','夏威夷附近海空域','巴伦支海','西太平洋','孟加拉湾','阿拉伯海','塔斯曼海','渤海海峡','黑海','西北太平洋','南太平洋','日本海','红海','珊瑚海','波斯湾','地中海','波罗的海','金兰湾','泰国湾','关岛附近海空域','北大西洋','莫桑比克海峡','印度洋','渤海','亚丁湾','台湾海峡','巴士海峡','巴林塘海峡','宫古水道','对马海峡']}
REGIONS=sorted((r for rs in REGION_GROUPS.values() for r in rs),key=len,reverse=True)
# Deliberately overlapping broad plausibility envelopes, NOT exact geographic
# truth or a way to manufacture a specific place from coordinates.
ENVELOPES={'东海':(119,131,23,34),'黄海':(117,128,32,41),'南海':(104,123,-1,24)}
OTHER_ENVELOPES={'孟加拉湾':(78,100,5,24),'安达曼海':(87,101,3,20),'菲律宾海':(124,155,0,35),'北大西洋':(-85,15,15,75),'波斯湾':(45,60,20,33),'地中海':(-7,38,28,48),'莫桑比克海峡':(30,52,-30,-5),'日本海':(125,143,32,50),'鄂霍次克海':(134,165,42,64),'阿拉伯海':(45,80,-2,28),'白令海':(160,180,48,68),'巴伦支海':(10,65,65,85),'夏威夷附近海空域':(-170,-145,10,32),'关岛附近海空域':(135,155,5,22),'波罗的海':(8,35,50,70),'黑海':(25,45,38,48),'红海':(30,46,10,33),'渤海':(115,125,35,43),'渤海海峡':(117,127,35,42),'印度洋':(20,110,-50,25),'亚丁湾':(40,60,8,20),'南太平洋':(130,180,-60,0),'中太平洋':(-175,-100,-20,40),'西太平洋':(125,180,-10,50),'西北太平洋':(130,180,20,65),'塔斯曼海':(140,180,-55,-20),'珊瑚海':(135,175,-35,-5),'泰国湾':(97,107,0,16),'金兰湾':(106,114,8,16)}

def date_value(s): return datetime.strptime(s,'%Y.%m.%d')
def normal(s): return re.sub(r'[\s“”‘’"·\-_/（）()「」]', '', str(s)).upper()
def uid(s): return hashlib.sha256(s.encode()).hexdigest()[:12]
def direction(r):
    return next((k for k,rs in REGION_GROUPS.items() if r in rs),'其他')
def region_relation(a,b):
    if not a or not b: return 'missing'
    if a==b: return 'exact'
    if a in ('东海','南海','黄海') and direction(b)==a: return 'contains'
    if b in ('东海','南海','黄海') and direction(a)==b: return 'contains'
    return 'conflict'
def regions_in(s):
    hits=[]
    for r in REGIONS:
        if r in s and not any(r in x for x in hits): hits.append(r)
    # A sentence can explicitly give core sea + its finer place.
    return [r for r in hits if not (r in ('东海','南海','黄海') and any(x!=r and direction(x)==r for x in hits))]
def canon_platform(name):
    s=normal(name)
    code=re.match(r'(F/A\S+)',str(name))
    if code: return normal(code.group(1).split('“')[0])
    m=re.match(r'(?:[A-Z]+[0-9]+[A-Z]*(?:/[A-Z]+)?|[0-9]+[A-Z]*|歼[0-9]+[A-Z]*|轰[0-9]+[A-Z]*|运[0-9]+|空警[0-9]+|无侦[0-9]+|直[0-9]+|苏[0-9]+[A-Z]*|图[0-9]+[A-Z]*|米格[0-9]+[A-Z]*|伊尔[0-9]+|幻影[0-9]+[0-9]*|福克[0-9]+)',s)
    if m: return m.group()
    for suffix in ['舰载战斗机','多用途战斗机','反潜巡逻机','空中预警机','预警与控制机','空中预警管制机','导弹驱逐舰','导弹护卫舰','综合补给舰','航空母舰','直升机母舰','常规潜艇','攻击核潜艇','导弹巡洋舰','两栖攻击舰','近海巡逻舰','多用途巡逻舰','反潜护卫舰','坦克登陆舰','船坞登陆舰','船坞运输舰','电子侦察船','轻型护卫舰','濒海战斗舰']:
        if s.endswith(suffix): s=s[:-len(suffix)]; break
    return s.rstrip('型号级')

def strip_reporter(body):
    return re.sub(r'^据[^，。]*?(?:报道|消息)[，：:]\s*','',body)
def fact_sentence(body):
    # Commentary about intentions/roles is not an event fact.
    s=strip_reporter(body)
    return re.split(r'有分析|有观点|外界分析|外界认为|观察人士|媒体关注|有关讨论|相关动态显示|相关动向引发|这一(?:动向|行动|活动|部署|训练|过程|平台)|此次行动',s)[0]
def times_in(s):
    vals=[]
    for m in re.finditer(r'(\d{1,2})\s*(?:时(?:\s*(\d{1,2})\s*分)?|:\s*(\d{2}))',s):
        h=int(m.group(1)); mi=int(m.group(2) or m.group(3) or 0)
        if h<24 and mi<60: vals.append((h*60+mi,m.group(),m.start()))
    return vals
def num(s):
    if s.isdigit(): return int(s)
    return {'一':1,'两':2,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}.get(s)

def parse_segment(t,day,lexicon):
    body=t['fields'].get('正文',''); fact=fact_sentence(body); norm=normal(fact)
    title=t['fields'].get('标题','')
    mentions=[]
    for p, aliases in lexicon.items():
        for a in sorted(aliases,key=lambda x:(-len(x),x)):
            # Full model boundaries prevent 歼15 from matching 歼15D, P3C/P3CK.
            pattern=re.escape(a)+r'(?![A-Z0-9])'
            m=re.search(pattern,norm)
            if m:
                mentions.append((m.start(),m.end(),p)); break
    mentions.sort()
    # Do not emit aliases swallowed by a longer platform mention.
    mentions=[m for m in mentions if not any(n[0]<=m[0] and n[1]>m[1] for n in mentions)]
    reg=regions_in(fact); title_reg=regions_in(title)
    tm=times_in(fact); dates=re.findall(r'(2025)年(\d+)月(\d+)日',fact)
    actual_date='.'.join(str(int(v)) for v in dates[0]) if dates else day
    claims=[]
    for i,(start,end,p) in enumerate(mentions):
        prefix=norm[:start]
        subject_hits=[(prefix.rfind(normal(c)),c) for c in COUNTRIES if normal(c) in prefix]
        subject_hits += [(prefix.rfind(normal(a)),c) for a,c in SUBJECT_ALIASES.items() if normal(a) in prefix]
        country=max(subject_hits)[1] if subject_hits else ''
        if not country and i: country=claims[-1]['country']
        qhits=list(re.finditer(r'([0-9]+|[一两二三四五六七八九十])(?:架|艘)',prefix))
        q=None; qquote=''
        if qhits:
            m=qhits[-1]
            # A count before the previous platform does not apply to this one.
            if not i or m.start()>=mentions[i-1][1]: q=num(m.group(1)); qquote=m.group()
        if q is None and norm[start:].startswith(p+'号') and p!='经国' and re.search(r'(?:航空母舰|导弹驱逐舰|导弹护卫舰|综合补给舰|直升机母舰|巡洋舰|两栖攻击舰|巡逻舰|潜艇)',fact):
            q=1; qquote='单一具名舰艇专名:'+p+'；不是对舰级或机型默认数量1'
        tasks=[]
        for task in sorted(TASKS,key=len,reverse=True):
            if re.search(re.escape(task)+r'(?!机)',fact) and not any(task in x for x in tasks): tasks.append(task)
        conflicts=[]
        if actual_date!=day: conflicts.append('正文日期与目录日期冲突')
        if len(reg)>1: conflicts.append('正文含多个不可包含的区域，不能归为单一位置')
        if reg and title_reg and not any(region_relation(a,b)!='conflict' for a in reg for b in title_reg): conflicts.append('标题与正文区域冲突')
        interval=[tm[0][0],tm[1][0]] if len(tm)>=2 else ([tm[0][0],None] if tm else [None,None])
        claims.append(dict(claim_id=uid(t['file']+'|'+p),file=t['file'],source=t['source'],date=actual_date,
            country=country,platform=p,quantity=q,region=reg[0] if len(reg)==1 else '',tasks=tasks,
            interval=interval,conflicts=conflicts,quote=fact.strip(),title=title,
            spans={'quantity':qquote,'time':[v[1] for v in tm],'region':reg,'platform_alias':norm[start:end]},
            line=next((j for j,l in enumerate(t['text'].splitlines(),1) if l.startswith('正文')),None),
            multi_platform=len(mentions)>1))
    return claims

def parse_text(t,day,lexicon):
    """Split explicit independent event sentences; retain shared formation scope."""
    body=t['fields'].get('正文',''); chunks=[]; current=''
    for part in re.findall(r'[^。；]+[。；]?',body):
        normalized=normal(part)
        explicit=any(re.search(re.escape(a)+r'(?![A-Z0-9])',normalized) for aa in lexicon.values() for a in aa)
        if current and explicit and regions_in(part) and re.search(r'执行|活动|进入|离开|开展|展开',part):
            chunks.append(current);current=part
        else: current+=part
    if current: chunks.append(current)
    claims=[]
    for index,chunk in enumerate(chunks):
        segment={**t,'fields':{**t['fields'],'正文':chunk}}
        cc=parse_segment(segment,day,lexicon)
        for c in cc:
            c['subevent_index']=index
            if len(chunks)>1: c['claim_id']=uid(t['file']+'|'+c['platform']+'|'+str(index))
            c['entity_kind']='named_hull' if re.search(re.escape(c['platform'])+r'号',normal(chunk)) and not re.search(r'经国',c['platform']) else 'platform_type'
            c['date_basis']='explicit_body_date' if re.search(r'2025年\d+月\d+日',chunk) else 'same-day_file_date'
        claims.extend(cc)
    return claims

def distance(a,b):
    x1,y1=a; x2,y2=b
    dlat=math.radians(y2-y1); dlon=math.radians(x2-x1)
    z=math.sin(dlat/2)**2+math.cos(math.radians(y1))*math.cos(math.radians(y2))*math.sin(dlon/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(z)))
def radar_time(v):
    try: return datetime.strptime(str(v),'%Y.%m.%d %H:%M:%S')
    except ValueError: return None
def coord_support(region,xy):
    d=direction(region)
    box=ENVELOPES.get(d) or OTHER_ENVELOPES.get(region)
    if box is None or xy is None: return None
    x0,x1,y0,y1=box; x,y=xy
    return x0<=x<=x1 and y0<=y<=y1

def reconstruct_radar(day):
    batches=defaultdict(list)
    for r in day['radar']: batches[(r['sheet'],str(r['data']['批号']))].append(r)
    tracks=[]
    for (sheet,batch),rows in batches.items():
        clusters=[]
        if sheet=='飞机':
            for r in sorted(rows,key=lambda r:(float(r['data']['开始经度']),float(r['data']['开始纬度']),str(r['data']['位置时间']))):
                d=r['data']; anchor=(float(d['开始经度']),float(d['开始纬度']))
                match=next((c for c in clusters if distance(c['anchor'],anchor)<80),None)
                if match is None: match={'anchor':anchor,'rows':[]}; clusters.append(match)
                match['rows'].append(r)
        else: clusters=[{'anchor':None,'rows':rows}]
        for ci,c in enumerate(clusters):
            rr=sorted(c['rows'],key=lambda r:r['row']); fieldmap={'country':'国家地区','platform':'目标类型' if sheet=='飞机' else '机舰名','quantity':'目标数量' if sheet=='飞机' else '数量','task':'任务','base':'起飞机场' if sheet=='飞机' else '出航港口'}
            vals={f:sorted(set(str(r['data'].get(k,'')) for r in rr)) for f,k in fieldmap.items()}
            # A unanimous field is safe to extract. Competing values remain explicit.
            fields={f:v[0] if len(v)==1 else None for f,v in vals.items()}
            fields['platform']=canon_platform(fields['platform']) if fields['platform'] else None
            fields['quantity']=int(float(fields['quantity'])) if fields['quantity'] else None
            conflicts=[f'雷达同一轨迹{f}不一致:{v}' for f,v in vals.items() if len(v)>1 and f!='base']
            pts=[]; bad=[]
            for r in rr:
                d=r['data']; dt=radar_time(d.get('位置时间' if sheet=='飞机' else '发现时间'))
                if dt is None or dt.date()!=date_value(day['date']).date(): bad.append({'row':r['row'],'reason':'位置/发现时间无效或非当日'}); continue
                if sheet=='飞机':
                    xy=(float(d['经度']),float(d['纬度']))
                    if not (-180<=xy[0]<=180 and -90<=xy[1]<=90): bad.append({'row':r['row'],'reason':'经纬度越界'}); continue
                    pts.append({'row':r['row'],'time':dt.isoformat(),'xy':xy,'minute':dt.hour*60+dt.minute})
            pts.sort(key=lambda p:p['time'])
            # Do not remove a coherent competing track by a majority vote.
            jumps=[]
            for a,b in zip(pts,pts[1:]):
                seconds=(datetime.fromisoformat(b['time'])-datetime.fromisoformat(a['time'])).total_seconds()
                km=distance(a['xy'],b['xy'])
                if km>5 and (seconds<=0 or km/max(seconds/3600,1/3600)>2400): jumps.append({'from_row':a['row'],'to_row':b['row'],'distance_km':round(km,2),'seconds':seconds})
            if jumps: conflicts.append('轨迹存在同刻位置冲突或超过2400km/h跳变；不按点数投票')
            if sheet=='飞机':
                ts=[radar_time(r['data']['位置时间']) for r in rr if radar_time(r['data']['位置时间'])]
                interval=[min(ts).hour*60+min(ts).minute,max(ts).hour*60+max(ts).minute] if ts else [None,None]
                region_values=[]
                xy=(median(p['xy'][0] for p in pts),median(p['xy'][1] for p in pts)) if pts else None
            else:
                starts=set(str(r['data']['首点时间']) for r in rr); ends=set(str(r['data']['结束时间']) for r in rr)
                if len(starts)!=1 or len(ends)!=1: conflicts.append('舰船活动起止字段不一致')
                start=radar_time(next(iter(starts))) if len(starts)==1 else None
                end=radar_time(next(iter(ends))) if len(ends)==1 else None
                interval=[start.hour*60+start.minute if start else None,end.hour*60+end.minute if end else None]
                if start and (start.date()!=date_value(day['date']).date() or not end or end.date()!=start.date() or end<start): conflicts.append('舰船活动时段越日或倒置')
                region_values=sorted(set(str(r['data']['活动区域']) for r in rr)); xy=None
            if fields['quantity'] is None or not 1<=fields['quantity']<=100: conflicts.append('数量缺失、不一致或超出审查上限')
            if len(pts)<2 and sheet=='飞机': conflicts.append('有效轨迹点不足2')
            if bad: conflicts.append('存在无效时间或越界坐标；未有独立依据隔离')
            tracks.append(dict(track_id=uid(day['date']+'|'+sheet+'|'+batch+'|'+str(c['anchor'])),date=day['date'],kind=sheet,batch=batch,
                fields=fields,raw_values=vals,rows=[r['row'] for r in rr],raw_rows=rr,radar_file=rr[0]['file'],
                interval=interval,region_values=region_values,xy=xy,points=pts,anomalies=bad,jumps=jumps,conflicts=conflicts,
                competing_tracks=len(clusters),anchor=c['anchor']))
    return tracks

def time_relation(a,b):
    if a[0] is None or b[0] is None: return 'missing'
    if a[1] is None or b[1] is None:
        point=a[0] if a[1] is None else b[0]; span=b if a[1] is None else a
        if span[1] is None: return 'exact' if abs(a[0]-b[0])<=1 else 'conflict'
        return 'point-in-window' if span[0]-1<=point<=span[1]+1 else 'conflict'
    if abs(a[0]-b[0])<=1 and abs(a[1]-b[1])<=1: return 'exact'
    if max(a[0],b[0])>min(a[1],b[1])+1: return 'separate'
    return 'conflict'

def compare_claim(track,claim):
    f=track['fields']; support=[]; conflict=list(claim['conflicts']); missing=[]
    if claim['date']!=track['date']: conflict.append('日期冲突')
    for key in ['platform','country','quantity']:
        a=f[key]; b=claim[key]
        if a is None or b is None or b=='': missing.append(key)
        elif a==b: support.append(key)
        else: conflict.append(f'{key}冲突:雷达={a},文本={b}')
    if claim['tasks']:
        if f['task'] in claim['tasks'] and len(claim['tasks'])==1: support.append('task')
        else: conflict.append(f'task冲突:雷达={f["task"]},文本={claim["tasks"]}')
    else: missing.append('task')
    tr=time_relation(track['interval'],claim['interval'])
    if track['kind']=='飞机' and tr=='conflict' and all(v is not None for v in claim['interval']+track['interval']) and claim['interval'][0]<=track['interval'][0] and claim['interval'][1]>=track['interval'][1]:
        tr='observation-contained'
    if tr in ('exact','point-in-window'): support.append('time')
    elif tr=='observation-contained': support.append('observed-time-subset')
    elif tr in ('conflict','separate'): conflict.append('time冲突:'+str(track['interval'])+'/'+str(claim['interval']))
    else: missing.append('time')
    region_rel='missing'
    if track['kind']=='舰船':
        rel=[region_relation(r,claim['region']) for r in track['region_values']]
        region_rel='exact' if 'exact' in rel else 'contains' if 'contains' in rel else 'conflict' if claim['region'] else 'missing'
        if any(x in ('exact','contains') for x in rel): support.append('region')
        elif claim['region']: conflict.append('region冲突:'+str(track['region_values'])+'/'+claim['region'])
        else: missing.append('region')
    else:
        point_checks=[coord_support(claim['region'],p['xy']) for p in track['points']]
        geo=False if False in point_checks else True if point_checks and all(x is True for x in point_checks) else coord_support(claim['region'],track['xy'])
        if geo is True: support.append('region-broad')
        elif geo is False: conflict.append('region冲突:轨迹坐标不在文本核心海域宽容包络内')
        else: missing.append('region')
    return dict(claim_id=claim['claim_id'],file=claim['file'],source=claim['source'],line=claim['line'],support=support,conflict=conflict,missing=missing,region_relation=region_rel,
        time_relation=tr,eligible=not conflict and f['platform']==claim['platform'] and f['country']==claim['country'] and bool(claim['region']))

def claims_relation(a,b):
    reasons=[]
    for f in ['country','platform','quantity']:
        if a[f] is not None and b[f] is not None and a[f]!=b[f]: reasons.append(f+'文本互冲突')
    if region_relation(a['region'],b['region'])=='conflict': reasons.append('具体区域文本互冲突')
    if a['tasks'] and b['tasks'] and set(a['tasks'])!=set(b['tasks']): reasons.append('任务文本互冲突')
    if time_relation(a['interval'],b['interval']) in ('conflict','separate'): reasons.append('活动时段文本互冲突')
    return reasons

def adjudicate(track,a,b):
    f=track['fields']; conflicts=list(track['conflicts'])+claims_relation(a,b); corrections=[]
    if track['kind']=='舰船':
        candidates=[r for r in track['region_values'] if region_relation(r,a['region'])!='conflict' and region_relation(r,b['region'])!='conflict']
        if len(candidates)==1:
            region=candidates[0]
            bad=[r for r in track['raw_rows'] if region_relation(str(r['data']['活动区域']),region)=='conflict']
            if bad:
                # Independent text agreement + an isolated substitution in an
                # otherwise identical observation tuple. Never count votes.
                text_agreement=region_relation(a['region'],b['region']) in ('exact','contains')
                for r in bad:
                    d=r['data']; peers=[p for p in track['raw_rows'] if p['row']!=r['row'] and p['data']['活动区域']==region and p['data']['首点时间']==d['首点时间'] and p['data']['结束时间']==d['结束时间']]
                    if text_agreement and len(bad)==1 and len(peers)>=2:
                        corrections.append({'row':r['row'],'field':'活动区域','raw':d['活动区域'],'accepted':region,'reason':'同批同起止孤立区域替换；两类文本区域兼容，并有相同时段的连续同区域观测；隔离该行，不以多数票认定'})
                    else: conflicts.append('雷达区域冲突不能由连续性与两类文本共同消解')
        else:
            region=''; conflicts.append('三源无唯一兼容具体区域')
    else:
        rel=region_relation(a['region'],b['region'])
        region=a['region'] if rel=='exact' else direction(a['region']) if rel=='contains' else ''
        if not region: conflicts.append('文本具体区域不能建立包含关系')
        # Geographic envelopes only support the sea; a finer location needs two
        # textual classes. We deliberately do not infer precise sea areas.
        if region and any(coord_support(region,p['xy']) is False for p in track['points']): conflicts.append('文本区域与雷达完整轨迹存在明确冲突，不能由中位点覆盖')
    checks={}
    for key in ['country','platform','quantity','task']:
        value=f[key]; sources=['雷达'] if value is not None else []
        for c in (a,b):
            cv=c['tasks'] if key=='task' else c[key]
            if (key=='task' and value in cv) or (key!='task' and cv==value): sources.append(c['source'])
        checks[key]={'value':value,'sources':sources}
        if len(set(sources))<2:
            if key=='task' and not a['tasks'] and not b['tasks']:
                checks[key]={'value':'任务未核实','sources':[],'status':'unknown','candidate':value,'reason':'两文本只证实活动，雷达具体任务为单源候选；不输出为事实'}
            else: conflicts.append(key+'不足两类来源支持')
    time_sources=['雷达']; final_interval=track['interval']
    for c in (a,b):
        if time_relation(track['interval'],c['interval'])=='exact': time_sources.append(c['source'])
    if track['kind']=='飞机' and time_relation(a['interval'],b['interval'])=='exact' and all(x is not None for x in a['interval']) and a['interval'][0]<=track['interval'][0] and a['interval'][1]>=track['interval'][1]:
        final_interval=a['interval']; time_sources=[a['source'],b['source']]
        if time_relation(final_interval,track['interval'])=='exact': time_sources.append('雷达')
    checks['activity_window']={'value':final_interval,'sources':time_sources,'radar_observation_window':track['interval'],'note':'雷达位置时间不是起飞/降落时间；文本一致时段可包含部分观测'}
    if len(time_sources)<2: conflicts.append('活动起止时段不足两类来源支持')
    region_sources=[]
    if region:
        region_sources=[c['source'] for c in (a,b) if region_relation(c['region'],region) in ('exact','contains')]
        if track['kind']=='舰船' or coord_support(region,track['xy']) is True: region_sources.append('雷达')
    checks['region']={'value':region,'sources':region_sources,'specificity_note':'飞机单文本细分区域仅保留为候选；宽容包络不证明具体地点'}
    if len(set(region_sources))<2: conflicts.append('区域不足两类来源支持')
    checks['date']={'value':track['date'],'sources':['雷达',a['source'],b['source']]}
    return dict(facts=checks,region=region,direction=direction(region),conflicts=list(dict.fromkeys(conflicts)),corrections=corrections)

def contextual_conflicts(track,a,b,claims):
    """An additional explicitly located claim cannot disappear after pair ranking.

    Require the same full platform and an exact event window plus compatible
    place, or an exact specific ship area when no explicit time separates it.
    Broad sea/unknown time alone cannot identify the same activity.
    """
    out=[]
    for c in claims:
        if c['claim_id'] in (a['claim_id'],b['claim_id']) or c['platform']!=track['fields']['platform']: continue
        compatible_place=all(region_relation(c['region'],x['region'])!='conflict' for x in (a,b))
        exact_window=time_relation(track['interval'],c['interval'])=='exact'
        specific_anchor=track['kind']=='舰船' and c['region'] not in ('东海','南海','黄海','') and c['region'] in track['region_values'] and time_relation(track['interval'],c['interval']) not in ('conflict','separate')
        if compatible_place and (exact_window or specific_anchor):
            link=compare_claim(track,c)
            material=[x for x in link['conflict'] if not x.startswith('标题')]
            if material: out.append({'claim_id':c['claim_id'],'file':c['file'],'line':c['line'],'source':c['source'],'conflicts':material,'identity_basis':'完整型号、明确同活动窗口与兼容区域' if exact_window else '同一舰型、同一具体区域且无时间分离','quote':c['quote']})
    return out

def field_ledger(event,track,claims):
    ledger={}
    get=lambda c,k:c['tasks'] if k=='task' else c['interval'] if k=='activity_window' else c.get(k)
    for key in ['date','country','platform','activity_window','region','task','quantity','trajectory','base','callsign','named_entity']:
        fact=event['facts'].get(key); entries=[]
        if key in ['date','country','platform','quantity','task','activity_window','region','base','trajectory']:
            value=track['date'] if key=='date' else track['interval'] if key=='activity_window' else track['region_values'] if key=='region' else track['points'] if key=='trajectory' else track['fields'].get(key)
            entries.append({'source':'雷达','file':track['radar_file'],'sheet':track['kind'],'rows':track['rows'],'value':value,'role':'support' if fact and '雷达' in fact['sources'] else 'candidate'})
        for c in claims:
            if c['platform']!=event['platform_key']: continue
            value=get(c,key)
            if value in (None,'',[],[None,None]): continue
            role='support' if c['claim_id'] in event['claims'] and fact and c['source'] in fact['sources'] else 'candidate'
            if any(c['claim_id']==x['claim_id'] for x in event.get('contextual_conflicts',[])): role='conflict'
            entries.append({'source':c['source'],'file':c['file'],'line':c['line'],'subevent_index':c.get('subevent_index',0),'claim_id':c['claim_id'],'value':value,'quote':c['quote'],'role':role})
        ledger[key]={'accepted':fact['value'] if fact else None,'status':fact.get('status','verified') if fact else 'unknown','evidence':entries,'unknown_reason':None if fact else '未有双类同事件支持；候选不作为输出事实'}
    ledger['trajectory']['status']='reviewed_observations' if track['kind']=='飞机' else 'unknown'
    ledger['trajectory']['unknown_reason']='舰船原始数据无坐标，区域记录不等于地理轨迹' if track['kind']=='舰船' else None
    ledger['trajectory']['checks']={'all_rows_read':track['rows'],'sorted_points':track['points'],'jumps':track['jumps'],'invalid_rows':track['anomalies'],'competing_branches':track['competing_tracks'],'tolerance_basis':'80km按起始坐标区分候选分支，2400km/h为宽松跳点检查，5km为同刻容差；工程假设不证明区域细分，未按点数消解分支'}
    return ledger

def build_day(day):
    tracks=reconstruct_radar(day)
    # The lexicon is built from this day's input only. No future-date training.
    names={}
    for r in day['radar']:
        name=str(r['data'].get('目标类型',r['data'].get('机舰名',''))); p=canon_platform(name)
        names.setdefault(p,name)
    lexicon={p:{p,normal(name)} if p not in COUNTRIES else {p+'号',normal(name)} for p,name in names.items()}
    # Aircraft nickname aliases that preserve the full type rather than family.
    aliases={'NH90':['NH90凯门鳄'],'AW159':['AW159野猫'],'P8A':['P8A海神'],'RQ4':['全球鹰无人机'],'经国号':['经国'],'幻影20005':['幻影20005'],'大西洋2':['大西洋2']}
    for p,aa in aliases.items():
        if p in lexicon: lexicon[p].update(aa)
    claims=[c for t in day['texts'] for c in parse_text(t,day['date'],lexicon)]
    claim_by_id={c['claim_id']:c for c in claims}
    events=[]; all_candidates=[]
    for track in tracks:
        candidates=[]
        for c in claims:
            # Same model is a candidate even when the subject is inconsistent:
            # a wrong-country third source must be recorded, not disappear.
            if c['platform']==track['fields']['platform']:
                x=compare_claim(track,c); x['track_id']=track['track_id']; candidates.append(x); all_candidates.append(x)
        compatible={s:[x for x in candidates if x['source']==s and x['eligible']] for s in ['开源军情','网上舆论']}
        pairs=[]
        for aa in compatible['开源军情']:
            for bb in compatible['网上舆论']:
                a,b=claim_by_id[aa['claim_id']],claim_by_id[bb['claim_id']]
                verdict=adjudicate(track,a,b)
                contextual=contextual_conflicts(track,a,b,claims)
                verdict['contextual_conflicts']=contextual
                if contextual: verdict['conflicts']+=['另有明确同事件文本冲突，不能由选择两条相符文本覆盖:'+','.join(x['claim_id'] for x in contextual)]
                strength=sum(sum({'time':6,'region':1,'task':2,'quantity':2}.get(s,1) for s in x['support'])+5*(x['region_relation']=='exact') for x in (aa,bb))
                pairs.append({'claims':[aa['claim_id'],bb['claim_id']],'verdict':verdict,'evidence_strength':strength})
        good=[p for p in pairs if not p['verdict']['conflicts']]
        # All good alternatives are retained. Ranking is used solely to select
        # the better located evidence, and never substitutes for fact checks.
        selected=None
        if good:
            good.sort(key=lambda p:p['evidence_strength'],reverse=True)
            if len(good)==1 or good[0]['evidence_strength']>good[1]['evidence_strength']: selected=good[0]
        reasons=[]
        if not selected:
            if not compatible['开源军情']: reasons.append('缺少无冲突开源军情关联')
            if not compatible['网上舆论']: reasons.append('缺少无冲突网上舆论关联')
            reasons+=list(dict.fromkeys(c for p in pairs for c in p['verdict']['conflicts']))
            if len(good)>1: reasons.append('多个关联候选无法唯一消歧')
            reasons+=track['conflicts']
        v=selected['verdict'] if selected else None
        if selected and v['direction']=='其他': reasons.append('非三大核心海域，保留核验结果但排除日报')
        event=dict(event_id='E'+track['track_id'],date=day['date'],kind=track['kind'],country=track['fields']['country'],platform=names.get(track['fields']['platform'],track['fields']['platform']),platform_key=track['fields']['platform'],batch=track['batch'],quantity=track['fields']['quantity'],interval=v['facts']['activity_window']['value'] if v else track['interval'],
            region=v['region'] if v else '',direction=v['direction'] if v else '其他',task=v['facts']['task']['value'] if v else track['fields']['task'],
            radar_file=track['radar_file'],radar_rows=track['rows'],points=track['points'],xy=track['xy'],track_id=track['track_id'],
            facts=v['facts'] if v else {},corrections=v['corrections'] if v else [],claims=selected['claims'] if selected else [],
            candidate_pairs=pairs,candidates=candidates,decision='纳入' if selected and not reasons else '排除',reasons=list(dict.fromkeys(reasons)),
            base_candidate=track['fields']['base'],base_verified=False,raw_region_values=track['region_values'],raw_field_values=track['raw_values'],competing_tracks=track['competing_tracks'],
            trajectory_note='批号包含多个相隔80km以上的起始坐标分支；仅可使用两类文本共同限定的分支，不按点数选真轨迹' if track['competing_tracks']>1 else '')
        event['contextual_conflicts']=v.get('contextual_conflicts',[]) if v else [x for p in pairs for x in p['verdict'].get('contextual_conflicts',[])]
        event['field_evidence']=field_ledger(event,track,claims)
        event['association_status']='three_source_verified' if selected and not reasons else 'insufficient_or_conflicting'
        event['evidence_allocation']={'selected':event['claims'],'alternatives':[p['claims'] for p in good],'policy':'候选通过逐字段裁决后才可比较证据定位；明确同事件反证优先保留，平台子证据独占'}
        events.append(event)
    # Cross-event ownership: only explicit different platform mentions in one
    # document may support different event records. A platform claim is single-use.
    owners=defaultdict(list)
    for e in events:
        if e['decision']=='纳入':
            for c in e['claims']: owners[c].append(e)
    for c,ee in owners.items():
        if len(ee)>1:
            for e in ee: e['decision']='排除'; e['reasons'].append('同一平台文本子证据被多个雷达事件竞争，不能唯一分配')
    used={c for e in events if e['decision']=='纳入' for c in e['claims']}
    coverage=[]
    for t in day['texts']:
        cc=[c for c in claims if c['file']==t['file']]
        coverage.append({'file':t['file'],'source':t['source'],'date':day['date'],'claim_ids':[c['claim_id'] for c in cc],
            'included_claims':[c['claim_id'] for c in cc if c['claim_id'] in used],
            'reason':'已纳入全部/部分平台子证据' if any(c['claim_id'] in used for c in cc) else '无可核验核心事件；具体关联/冲突见候选表' if cc else '无法从正文提取当日雷达词典中的平台；保留原文待查'})
    return events,claims,tracks,coverage

def choose_trend(node,cache):
    current=[e for e in cache[node] if e['decision']=='纳入' and e['country']!='中国']
    best=None
    for seed in current:
        hist=sorted([e for d,ee in cache.items() if date_value(d)<=date_value(node) for e in ee if e['decision']=='纳入' and e['country']==seed['country'] and e['platform_key']==seed['platform_key']],key=lambda e:(date_value(e['date']),e['interval'][0]))
        # Broad/model recurring activity is not an identified individual hull.
        # Keep only the latest temporal segment ending in today's seed.
        distinct=sorted(set(e['date'] for e in hist),key=date_value)
        start=0
        for i in range(1,len(distinct)):
            if (date_value(distinct[i])-date_value(distinct[i-1])).days>=15: start=i
        hist=[e for e in hist if e['date'] in distinct[start:]]
        if len(set(e['date'] for e in hist))<3: continue
        # Consecutive evidence runs share region AND task; mission/geography or
        # 8-14 day gaps produce substantive stage boundaries.
        daily=[]
        for d in sorted(set(e['date'] for e in hist),key=date_value):
            ee=[e for e in hist if e['date']==d]
            daily.append({'date':d,'events':ee,'signature':(tuple(sorted(set(e['direction'] for e in ee))),tuple(sorted(set(e['task'] for e in ee))))})
        runs=[]
        for item in daily:
            if runs and item['signature']==runs[-1][-1]['signature'] and (date_value(item['date'])-date_value(runs[-1][-1]['date'])).days<=7: runs[-1].append(item)
            else: runs.append([item])
        # If many short runs, group adjacent runs at the largest content changes.
        boundaries=[]
        for i in range(1,len(daily)):
            prev,cur=daily[i-1],daily[i]; gap=(date_value(cur['date'])-date_value(prev['date'])).days
            change=3*(prev['signature'][0]!=cur['signature'][0])+2*(prev['signature'][1]!=cur['signature'][1])+gap/7
            boundaries.append((change,i))
        splits=sorted(i for _,i in sorted(boundaries,reverse=True)[:2]) if len(daily)>=5 else [max(boundaries)[1]]
        phases=[]; bounds=[0]+splits+[len(daily)]
        for lo,hi in zip(bounds,bounds[1:]):
            dd=daily[lo:hi]; ee=[e for x in dd for e in x['events']]
            phases.append({'start':dd[0]['date'],'end':dd[-1]['date'],'dates':[x['date'] for x in dd],
                'event_ids':[e['event_id'] for e in ee],'regions':dict(__import__('collections').Counter(e['region'] for e in ee)),
                'tasks':dict(__import__('collections').Counter(e['task'] for e in ee)),
                'intervals':[e['interval'] for e in ee],
                'gaps':[(date_value(b['date'])-date_value(a['date'])).days for a,b in zip(dd,dd[1:])]})
        trend={'country':seed['country'],'platform':seed['platform'],'platform_key':seed['platform_key'],'evidence':hist,'phases':phases,
            'dates':[x['date'] for x in daily],'gaps':[(date_value(b['date'])-date_value(a['date'])).days for a,b in zip(daily,daily[1:])],
            'identity_limit':'同主体同型平台的活动线索，不证明同一机体/舰体；只关联任务与区域变化'}
        rank=(len(daily),sum(len(x) for x in runs),len(hist))
        if best is None or rank>best[0]: best=(rank,trend)
    return best[1] if best else None
