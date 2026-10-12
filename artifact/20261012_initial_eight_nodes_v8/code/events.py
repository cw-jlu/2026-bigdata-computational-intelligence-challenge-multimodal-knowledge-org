"""Event reconstruction adapted from v4, with reviewed field-level corrections.

Association is a hypothesis. No association score is used as a truth criterion.
No imports from earlier GPT implementations; no model calls; no filename features.
"""
from __future__ import annotations
import hashlib, json, math, re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
import numpy as np
def linear_sum_assignment(cost):
    """Rectangular Hungarian algorithm, deterministic; no scipy dependency.
    Association optimization is not a truth decision. Rows <= columns.
    """
    n,m=cost.shape;u=[0.0]*(n+1);v=[0.0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;mins=[float('inf')]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=p[j0];delta=float('inf');j1=0
            for j in range(1,m+1):
                if not used[j]:
                    cur=float(cost[i0-1,j-1])-u[i0]-v[j]
                    if cur<mins[j]:mins[j]=cur;way[j]=j0
                    if mins[j]<delta:delta=mins[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:mins[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    result=sorted((p[j]-1,j-1) for j in range(1,m+1) if p[j])
    return [a for a,b in result],[b for a,b in result]
from openpyxl import load_workbook

NODES=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
COUNTRIES=['马来西亚','澳大利亚','新西兰','新加坡','菲律宾','加拿大','俄罗斯','意大利','中国','台湾','美国','英国','法国','德国','日本','韩国','印度','越南']
SEA={
 '东海':['东海','钓鱼岛','赤尾屿','上海外海','长江口外海','舟山外海','宁波外海','温州外海','冲绳海槽','苏岩礁'],
 '黄海':['黄海','青岛外海','成山头外海','海州湾外海','连云港外海','济州岛西部'],
 '南海':['南海','北部湾','琼州海峡','东沙','西沙','中沙','南沙','黄岩岛','美济礁','仁爱礁','万安滩','永暑礁','渚碧礁','礼乐滩','北康暗沙','南康暗沙','纳土纳群岛北部','曾母暗沙','海南岛东南','珠江口外海'],
}
# Coarse geographic plausibility windows, not exact boundaries or chart positions.
# Named coastal areas are never inferred merely from country/platform.
CENTERS={
 '钓鱼岛':(123.5,25.8),'赤尾屿':(124.5,25.9),'上海外海':(122.5,31.2),'长江口外海':(122.5,31.4),
 '舟山外海':(122.5,30),'宁波外海':(122,29.7),'温州外海':(121.5,27.8),'冲绳海槽':(127,27),
 '苏岩礁':(125.2,32.2),'东海油气田':(123.5,29),'东海南部':(124,26),'东海中部':(124,29),'东海北部':(124,31.8),
 '青岛外海':(121,35.8),'成山头外海':(123,37.3),'海州湾外海':(120.5,34.8),'连云港外海':(120.2,34.8),
 '济州岛西部':(125.5,33.4),'北黄海':(123.2,37.5),'南黄海':(123.2,34),'黄海中部':(124,36),
 '北部湾':(108.5,20),'琼州海峡':(110.2,20.2),'东沙':(116.7,20.7),'西沙':(112.3,16.8),'中沙':(114.5,16),
 '南沙':(114,10),'黄岩岛':(117.8,15.1),'美济礁':(115.5,9.9),'仁爱礁':(115.9,9.7),'万安滩':(109.7,7.5),
 '永暑礁':(112.9,9.5),'渚碧礁':(114.1,10.9),'礼乐滩':(116.5,11.4),'北康暗沙':(112.5,5.7),
 '南康暗沙':(112.3,5),'纳土纳群岛北部':(109,5),'曾母暗沙':(112.3,4),'海南岛东南':(111.8,18),'珠江口外海':(114,21.7),
 '南海南部':(111,8),'南海中部':(114,14),'南海北部':(114,20),
 '菲律宾海':(132,18),'孟加拉湾':(88,15),'安达曼海':(96,10),'北大西洋':(-35,40),
 '波斯湾':(52,26),'地中海':(18,35),'鄂霍次克海':(150,55),'日本海':(135,40),
 '渤海海峡':(121,38),'莫桑比克海峡':(42,-18),'巴伦支海':(40,74),'白令海':(-175,58),
 '黑海':(34,44),'中太平洋':(-155,22),'夏威夷':(-155,22),'关岛':(145,14),
}
GENERIC={'东海','南海','黄海'}

def date(s): return datetime.strptime(s,'%Y.%m.%d')
def norm(s): return re.sub(r'[\s“”"‘’·\-（）()、，：/]', '', str(s)).lower()
def direction(region):
    for d,terms in SEA.items():
        if any(t in region for t in terms):return d
    return '其他'
def compatible_region(a,b):
    if not a or not b:return None
    if a==b or a in b or b in a:return True
    return direction(a)==direction(b) and (a in GENERIC or b in GENERIC) and direction(a)!='其他'
def km(x,y):
    a,b,c,d=map(math.radians,[x[0],x[1],y[0],y[1]])
    return 6371*2*math.asin(min(1,math.sqrt(math.sin((b-d)/2)**2+math.cos(b)*math.cos(d)*math.sin((a-c)/2)**2)))
def position_support(region,points):
    if not points:return None
    x,y=median([p['lon'] for p in points]),median([p['lat'] for p in points])
    if region in GENERIC:
        if region=='东海':return 120<=x<=130 and 24<=y<=33.8
        if region=='黄海':return 118.5<=x<=127 and 32.8<=y<=40
        if region=='南海':return 104<=x<=122 and 2<=y<=24
    terms=[k for k in CENTERS if k in region]
    if not terms:return None
    k=max(terms,key=len); radius=340 if k in ['东海北部','东海中部','东海南部','南海北部','南海中部','南海南部','南沙','北黄海','南黄海','黄海中部'] else 210
    return km((x,y),CENTERS[k])<=radius
def minute(s):
    if s is None:return None
    return int(str(s).split(':')[0])*60+int(str(s).split(':')[1])
def fmt(t):return f'{int(t)//60:02d}:{int(t)%60:02d}' if t is not None else ''
def stamp(s):
    try:return datetime.strptime(str(s),'%Y.%m.%d %H:%M:%S')
    except ValueError:return None

def root_platform(s,kind):
    s=norm(s)
    if kind=='舰艇':return re.split(r'型|级|号',s,maxsplit=1)[0] if re.search('型|级|号',s) else s
    m=re.match(r'([a-z]+\d+[a-z]*(?:[a-z]\d+)?|[a-z]+\d+v?w?|f/a18e/f|rc135v/w|[\u4e00-\u9fff]+\d+[a-z]*|nh90|a330|a400m)',s)
    if m:return m.group(1)
    for suffix in ['多用途战斗机','反潜巡逻机','预警与控制机','电子侦察机','海上巡逻机','反潜直升机','无人机','舰载战斗机','战略轰炸机','战斗机']:
        if s.endswith(suffix):return s[:-len(suffix)]
    return s

def vocabulary(daydir):
    """Lexicon from today's radar labels only. No future-day scans."""
    w=load_workbook(next(daydir.glob('*.xlsx')),data_only=True)
    platforms={}; regions=set(GENERIC);tasks=set()
    for s in w:
        rows=list(s.values);hdr=rows[0]
        for r in rows[1:]:
            r=dict(zip(hdr,r));kind='飞机' if s.title=='飞机' else '舰艇'
            name=r['目标类型' if kind=='飞机' else '机舰名'];key=root_platform(name,kind)
            if key not in platforms:platforms[key]={'key':key,'name':name,'kind':kind,'aliases':set()}
            platforms[key]['aliases'].update([norm(name),key+'型' if kind=='舰艇' and key.isdigit() else key])
            tasks.add(r['任务'])
            if '活动区域' in r:regions.add(r['活动区域'])
    w.close()
    # Fixed geography terms, containing no dated observations.
    regions.update(['钓鱼岛海域','赤尾屿海域','上海外海','长江口外海','舟山外海','宁波外海','温州外海','冲绳海槽','苏岩礁附近海域','东海油气田海域','东海南部','东海中部','东海北部','北黄海','南黄海','黄海中部','青岛外海','成山头外海','海州湾外海','连云港外海','济州岛西部海域','北部湾','琼州海峡','东沙群岛海域','西沙群岛海域','中沙群岛海域','南沙群岛海域','黄岩岛海域','美济礁附近海域','仁爱礁附近海域','万安滩海域','南海北部','南海中部','南海南部','海南岛东南海域','南康暗沙海域','北康暗沙海域','纳土纳群岛北部海域','菲律宾海','孟加拉湾','安达曼海','北大西洋','地中海','波斯湾'])
    regions.update(['永暑礁附近海域','渚碧礁附近海域','礼乐滩海域','曾母暗沙海域','珠江口外海',
                    '渤海海峡','渤海','金兰湾','莫桑比克海峡','巴伦支海','白令海','黑海','鄂霍次克海','日本海','中太平洋','夏威夷附近海空域','关岛附近海空域',
                    '亚丁湾','泰国湾','塔斯曼海','阿拉伯海','红海','珊瑚海','印度洋','南太平洋','西北太平洋','西太平洋','波罗的海',
                    '台湾海峡','巴士海峡','巴林塘海峡','宫古水道','对马海峡'])
    # Optional synonyms preserve model variant specificity; no variant collapsing.
    for key,p in platforms.items():
        if key=='p8a':p['aliases'].update(['p8a反潜机','p8a海神'])
        if key=='无敌':p['aliases'].add('无敌级')
        if key=='056a':p['aliases'].add('056a型护卫舰')
    return platforms,regions,tasks

def text_atoms(path,source,day,lex,regions,tasks,root,_body=None,_segment=0):
    text=path.read_text(encoding='utf-8-sig');m=re.search(r'正文[：:]([\s\S]*?)(?:\n\s*主题词[：:]|$)',text)
    body=_body if _body is not None else (m.group(1).strip() if m else '')
    title=re.search(r'标题[：:]([^\n]+)',text);title=title.group(1).strip() if title else ''
    # Keep reportage facts before commentary; platform/mission capability words in
    # opinions about intent are not observations. Broadcast agency is not the actor.
    fact=re.split(r'有分析认为|分析认为|媒体评论认为|观察人士指出|有关讨论|围绕.*?的讨论|从公开可观察特征切入|媒体关注|外界分析|外界认为|从任务连续性角度|相关动向被|相关行动被|这一动向|这一部署|此次行动被|此次部署可能|有关分析|有观点认为|有助于外界|可能体现|被认为|引发外界',body,maxsplit=1)[0]
    # Strip news agency country mentions before the reported event.
    fact=re.sub(r'^据[^，。]*报道[，、]?', '',fact)
    if _body is None:
        chunks=[];current=''
        for part in re.findall(r'[^。；]+[。；]?',fact):
            npart=norm(part)
            explicit=any(alias in npart for p in lex.values() for alias in p['aliases'])
            located=any(norm(reg) in npart for reg in regions)
            if current and explicit and located and re.search(r'执行|活动|进入|离开|开展|展开',part):
                chunks.append(current);current=part
            else:current+=part
        if current:chunks.append(current)
        if len(chunks)>1:
            aa=[]
            for i,chunk in enumerate(chunks):
                cc,_=text_atoms(path,source,day,lex,regions,tasks,root,chunk,i);aa.extend(cc)
            return aa,{'path':path.relative_to(root).as_posix(),'source':source,'body':body,'fact':fact,'atoms':[a['id'] for a in aa],'segments':chunks,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    n=norm(fact)
    country_hits=[(n.find(norm(c)),c) for c in COUNTRIES if norm(c) in n]
    country=min(country_hits)[1] if country_hits else ('美国' if '美军' in n else '台湾' if '台军' in n else None)
    modelhits=[]
    for key,p in lex.items():
        for alias in sorted(p['aliases']):
            pos=n.find(alias)
            if pos>=0:modelhits.append((pos,pos+len(alias),key))
    # Longest overlapping alias wins. E.g. 歼-16D cannot also become 歼-16.
    modelhits.sort(key=lambda h:-(h[1]-h[0]));chosen=[]
    for h in modelhits:
        if not any(h[0]<g[1] and g[0]<h[1] for g in chosen):chosen.append(h)
    chosen.sort();chosen=list({h[2]:h for h in chosen}.values())
    regionhits=[(n.find(norm(r)),r) for r in regions if re.search(re.escape(norm(r))+r'(?!军|上自卫队)',n)]
    regionhits.sort(key=lambda x:(-len(x[1]),x[0],x[1]));region=regionhits[0][1] if regionhits else None
    allregions=[r for _,r in regionhits if not any(r!=q and r in q for _,q in regionhits)]
    taskhits=[t for t in sorted(tasks) if re.search(re.escape(t)+r'(?!机|船|飞机)',fact)]
    taskhits=[t for t in taskhits if not any(t!=q and t in q for q in taskhits)]
    # Unknown task is missing, not "routine deployment" inferred from prose.
    task=taskhits[0] if len(taskhits)==1 else None
    timehits=[]
    for m in re.finditer(r'(\d{1,2})时(?:(\d{1,2})分)?',fact):
        value=int(m[1])*60+int(m[2] or 0)
        if value<=1440:timehits.append(value)
    if not timehits:
        timehits=[int(m[1])*60+int(m[2]) for m in re.finditer(r'(\d{1,2}):(\d{2})',fact)]
    start,end=(timehits[0],timehits[-1]) if len(timehits)>=2 else (None,None)
    observed=timehits[0] if len(timehits)==1 else None
    dm=re.search(r'(2025)年(\d{1,2})月(\d{1,2})日',fact)
    factday=f'{int(dm[1])}.{int(dm[2])}.{int(dm[3])}' if dm else day
    relations=[s for s in ['进入','离开','持续活动'] if s in fact]
    atoms=[]
    cn={'一':1,'两':2,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}
    for pos,_,key in chosen:
        p=lex[key];prefix=n[max(0,pos-20):pos];q=None
        subject_hits=[(n[:pos].rfind(norm(c)),c) for c in COUNTRIES if norm(c) in n[:pos]]
        atom_country=max(subject_hits)[1] if subject_hits else country
        qtyhit=re.search(r'([0-9]+|[一两二三四五六七八九十])(?:架|艘)(?:[“”"\s])?$',prefix)
        qty=(int(qtyhit[1]) if qtyhit[1].isdigit() else cn[qtyhit[1]]) if qtyhit else None
        # "一艘中国093A" places the country between number and model.
        if qty is None:
            q=re.search(r'([0-9]+|[一两二三四五六七八九十])(?:架|艘)(?:中国|美国|台湾|日本|英国|法国|德国|印度)?$',prefix)
            if q:qty=int(q[1]) if q[1].isdigit() else cn[q[1]]
        quantity_basis='正文显式数量' if qty is not None else None
        quantity_unit=('艘' if '艘' in (qtyhit.group() if qtyhit else q.group() if q else '') else '架') if qty is not None else None
        # A shared proper name is not enough: "台风导弹巡洋舰" cannot
        # corroborate a Typhoon aircraft. Preserve explicit class/unit conflicts.
        local=n[pos:pos+len(key)+28]
        rolehits=[]
        for pattern,reported in [(r'直升机母舰|电子侦察船|船坞登陆舰|坦克登陆舰|导弹巡洋舰|导弹驱逐舰|导弹护卫舰|航空母舰|常规潜艇|核潜艇|综合补给舰|两栖攻击舰|护卫舰|母舰|巡逻艇','舰艇'),(r'战斗机|预警机|侦察机|运输机|无人机|直升机|巡逻机|电子战飞机|轰炸机|战机','飞机')]:
            mm=re.search(pattern,local)
            if mm:rolehits.append((mm.start(),-len(mm.group()),reported,mm.group()))
        reported_kind=min(rolehits)[2] if rolehits else None
        role_quote=min(rolehits)[3] if rolehits else None
        if qty is None and p['kind']=='舰艇' and '号' in p['name'] and key+'号' in n:
            # A singular named vessel is one named participant, not a default
            # count for a ship class. Class-only mentions stay unknown.
            qty=1;quantity_basis='正文单一具名舰艇专名；仅计该具名参加者'
        relpath=path.relative_to(root).as_posix()
        atom={'id':hashlib.sha256((relpath+'|'+key+'|'+str(_segment)).encode()).hexdigest()[:16],
              'path':relpath,'source':source,'date':factday,'country':atom_country,'platform':p['name'],'key':key,'kind':p['kind'],
              'region':region,'regions':allregions,'task':task,'task_candidates':taskhits,'quantity':qty,
              'quantity_basis':quantity_basis,
              'quantity_unit':quantity_unit,'reported_kind':reported_kind,'role_quote':role_quote,
              'start':start,'end':end,'observed':observed,'relations':relations,'snippet':fact,'title':title,
              'locator':{'section':'正文','line':next((i for i,line in enumerate(text.splitlines(),1) if line.startswith('正文')),None),'atomic_platform':key,'subevent_index':_segment},'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'multi_platform':len(chosen)>1,'date_basis':'explicit_body_date' if dm else 'same_day_input_directory'}
        atoms.append(atom)
    return atoms,{'path':path.relative_to(root).as_posix(),'source':source,'body':body,'fact':fact,'atoms':[a['id'] for a in atoms], 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def radar_events(daydir,root):
    file=next(daydir.glob('*.xlsx'));w=load_workbook(file,data_only=True);out=[]
    for s in w:
        rows=list(s.values);hdr=rows[0];g=defaultdict(list)
        for i,v in enumerate(rows[1:],2):g[v[0]].append({'row':i,**dict(zip(hdr,v))})
        for batch,rr in sorted(g.items()):
            air=s.title=='飞机';fields={'country':'国家地区','platform':'目标类型' if air else '机舰名','quantity':'目标数量' if air else '数量','task':'任务','base':'起飞机场' if air else '出航港口'}
            values={k:sorted(set(r[f] for r in rr),key=str) for k,f in fields.items()}
            conflicts=[f'雷达字段{k}多个明确值：{v}' for k,v in values.items() if len(v)!=1]
            coords=[];badrows=[];alltimes=[]
            for r in rr:
                tm=stamp(r['位置时间' if air else '发现时间'])
                if tm is None or tm.date()!=date(daydir.name).date():badrows.append({'row':r['row'],'reason':'观测时间不在当日或不能解析'})
                else:alltimes.append(tm)
                if air:
                    lon,lat=r['经度'],r['纬度'];valid=isinstance(lon,(int,float)) and isinstance(lat,(int,float)) and -180<=lon<=180 and -90<=lat<=90
                    if not valid:badrows.append({'row':r['row'],'reason':'坐标越界或缺失'})
                    elif tm:coords.append({'row':r['row'],'lon':lon,'lat':lat,'time':tm.isoformat()})
            coords.sort(key=lambda p:p['time'])
            trajectory=[]
            # Detect contemporaneous incompatible tracks and implausible displacement.
            for i,p in enumerate(coords):
                for q in coords[i+1:]:
                    seconds=abs((datetime.fromisoformat(q['time'])-datetime.fromisoformat(p['time'])).total_seconds())
                    dist=km((p['lon'],p['lat']),(q['lon'],q['lat']))
                    if dist>300 and (seconds<300 or dist/max(seconds/3600,1/3600)>1800):
                        trajectory.append({'rows':[p['row'],q['row']],'km':round(dist,1),'seconds':seconds,'reason':'同刻异地或超出宽松速度上界'})
            if trajectory:conflicts.append('雷达轨迹存在并行异地观测或不合理跳变，未能定位可独立删除的噪声行')
            regions=sorted(set(str(r['活动区域']) for r in rr)) if not air else []
            if len(regions)>1 and any(not compatible_region(a,b) for a in regions for b in regions):conflicts.append('雷达区域明确冲突：'+str(regions))
            if badrows:conflicts.append('雷达日期或坐标异常，保守保留候选')
            if air:
                start=min(alltimes).hour*60+min(alltimes).minute if alltimes else None
                end=max(alltimes).hour*60+max(alltimes).minute if alltimes else None
            else:
                starts=sorted(set(str(r['首点时间']) for r in rr));ends=sorted(set(str(r['结束时间']) for r in rr))
                if len(starts)!=1 or len(ends)!=1:conflicts.append('雷达显式活动起止时间不一致')
                st=stamp(starts[0]);en=stamp(ends[0]);start=st.hour*60+st.minute if st else None;end=en.hour*60+en.minute if en else None
                if not st or not en or st.date()!=date(daydir.name).date() or en.date()!=date(daydir.name).date() or en<st:conflicts.append('雷达活动时间异常')
            r={'id':daydir.name+'-'+batch,'date':daydir.name,'kind':'飞机' if air else '舰艇','batch':batch,
               'radar_file':file.relative_to(root).as_posix(),'sheet':s.title,'rows':rr,'values':values,
               'country':values['country'][0] if len(values['country'])==1 else None,
               'platform':values['platform'][0] if len(values['platform'])==1 else None,
               'quantity':values['quantity'][0] if len(values['quantity'])==1 else None,
               'task':values['task'][0] if len(values['task'])==1 else None,
               'base_candidate':values['base'][0] if len(values['base'])==1 else None,
               'regions':regions,'region':max(regions,key=len) if regions else None,'start':start,'end':end,
               'coords':coords,'radar_conflicts':conflicts,'trajectory_alerts':trajectory,'bad_rows':badrows}
            r['key']=root_platform(r['platform'] or '',r['kind']);out.append(r)
    w.close();return out

def compare(atom,r):
    if atom['key']!=r['key'] or atom['kind']!=r['kind']:return None
    supports=[];conflicts=[];score=20.0
    if atom['date']==r['date']:supports.append('日期');score+=3
    else:conflicts.append('日期');score-=50
    if atom['country']==r['country']:supports.append('主体');score+=5
    elif atom['country'] and r['country']:conflicts.append('主体');score-=5
    # Nested sea labels in a sentence cannot override its specific locality.
    regs=[atom['region']] if atom['region'] else []
    if r['kind']=='飞机':
        # A split/noisy track can still be a same-event hypothesis. The full
        # trajectory conflict remains a separate veto in audit_fields.
        loc=[position_support(a,[point]) for a in regs if a for point in r['coords']]
    else:loc=[compatible_region(a,b) for a in regs for b in r['regions'] if a]
    if True in loc:
        supports.append('区域');score+=10
        if r['kind']=='舰艇' and atom['region']==r['region'] and atom['region'] not in GENERIC:score+=12
    elif False in loc:conflicts.append('区域');score-=7
    time_delta=None
    if atom['start'] is not None and r['start'] is not None:
        time_delta=abs(atom['start']-r['start'])+abs(atom['end']-r['end'])
        if time_delta<=4:supports.append('起止时间');score+=20
        elif atom['end']<r['start']-3 or atom['start']>r['end']+3:conflicts.append('时段不重叠');score-=22
        else:conflicts.append('起止时间');score+=4-max(0,time_delta-4)/60
    elif atom['observed'] is not None and r['start'] is not None:
        if r['start']-3<=atom['observed']<=r['end']+3:supports.append('观测点时间');score+=8
        else:conflicts.append('观测点时间');score-=18
    if atom['task'] and r['task']:
        if atom['task']==r['task']:supports.append('任务');score+=6
        else:conflicts.append('任务');score-=5
    if atom['quantity'] is not None and r['quantity'] is not None:
        if atom['quantity']==r['quantity']:supports.append('数量');score+=2
        else:conflicts.append('数量');score-=2
    # An explicit model plus regional/time anchor is required, even for conflict candidates.
    anchored='区域' in supports or '起止时间' in supports
    return {'atom':atom['id'],'event':r['id'],'score':round(score,4),'supports':supports,'conflicts':conflicts,'time_delta':time_delta,'eligible':anchored and atom['date']==r['date']}

def assign(atoms,radars):
    """One atom per source per radar; multi-platform reports create distinct atoms.
    Hungarian optimization resolves competing same-model hypotheses globally.
    A non-unique regional/time anchor remains ambiguous rather than forced.
    """
    candidates=[];selected={};ambiguities=[]
    for source in ['开源军情','网上舆论']:
        aa=sorted([a for a in atoms if a['source']==source],key=lambda a:a['id'])
        mat=np.zeros((len(aa),len(radars)+len(aa)));links={}
        for i,a in enumerate(aa):
            for j,r in enumerate(radars):
                c=compare(a,r)
                if c is None:continue
                c['source']=source;c['path']=a['path'];candidates.append(c);links[i,j]=c
                if c['eligible']:mat[i,j]=c['score']
        if not aa:continue
        ix,jx=linear_sum_assignment(-mat)
        for i,j in zip(ix,jx):
            if j>=len(radars) or (i,j) not in links or mat[i,j]<=0:continue
            c=links[i,j];a=aa[i];r=radars[j]
            rivals=[q for (ii,jj),q in links.items() if ii==i and jj!=j and q['eligible']]
            # A generic report with no time and identical mission cannot distinguish
            # two sorties in the same sea. Global assignment alone is not evidence.
            indist=[q for q in rivals if abs(q['score']-c['score'])<1 and a['start'] is None and a['observed'] is None]
            if indist:
                ambiguities.append({'atom':a['id'],'path':a['path'],'event':r['id'],'alternatives':indist,'reason':'同型同日活动无法独立区分'});continue
            selected.setdefault(r['id'],{})[source]=a
            c['selected']=True
    # Bridge missing direct radar locality support through the OTHER text type.
    # This retains a contradicted same-event hypothesis rather than discarding
    # the offending source. Requires unique identity plus a specific locality or
    # matching explicit interval; broad sea alone is insufficient.
    used={a['id'] for ss in selected.values() for a in ss.values()}
    ambiguous_ids={x['atom'] for x in ambiguities}
    for a in sorted(atoms,key=lambda a:a['id']):
        if a['id'] in used or a['id'] in ambiguous_ids:continue
        targets=[]
        for r in radars:
            ss=selected.get(r['id'],{})
            if a['source'] in ss:continue
            for b in ss.values():
                if a['source']==b['source'] or a['key']!=b['key'] or a['country']!=b['country'] or a['date']!=b['date']:continue
                specific=(a['region']==b['region'] and a['region'] not in GENERIC and a['region'] is not None)
                exacttime=(a['start'] is not None and b['start'] is not None and abs(a['start']-b['start'])+abs(a['end']-b['end'])<=4)
                if specific or exacttime:targets.append((r,b))
        if len(targets)==1:
            r,b=targets[0];selected.setdefault(r['id'],{})[a['source']]=a;used.add(a['id'])
            candidates.append({'atom':a['id'],'event':r['id'],'source':a['source'],'path':a['path'],'score':None,
                               'supports':['文本主体','文本型号','文本具体区域或显式时段'],'conflicts':[],
                               'eligible':True,'selected':True,'bridge_atom':b['id'],'reason':'经另一文本类型保留冲突候选；不构成事实裁决'})
    return selected,candidates,ambiguities

def audit_fields(r,claims):
    """No majority vote. A stated conflict vetoes the event until explained."""
    issues=list(r['radar_conflicts']);facts={};audit={}
    sources={'雷达':r,**claims}
    for s,a in claims.items():
        if a.get('reported_kind') and a['reported_kind']!=r['kind']:
            issues.append(f'关键平台类别明确冲突：{s}正文为{a["role_quote"]}，雷达为{r["kind"]}')
        if a.get('quantity_unit') and a['quantity_unit']!=('架' if r['kind']=='飞机' else '艘'):
            issues.append(f'关键数量单位明确冲突：{s}为{a["quantity_unit"]}，雷达类别{r["kind"]}')
    for f in ['country','key','quantity','task','start','end']:
        vv={s:x.get(f) for s,x in sources.items() if x.get(f) is not None}
        if f in ['start','end']:
            # minute rounding only; no silently treating a shorter interval as full duration.
            vals=list(vv.values());agree=max(vals)-min(vals)<=2 if vals else False
        else:agree=len(set(vv.values()))==1
        if not agree and vv:issues.append(f'关键字段{f}明确冲突：{vv}')
        if agree and len(vv)>=2:facts[f]=next(iter(vv.values()))
        else:
            facts[f]=None
            # Known assertions require >=2 source types. Unstated optional
            # time/task/count fields stay unknown, never copied from radar.
            # Subject and platform identity remain mandatory.
            if agree and f in ['country','key','quantity']:issues.append(f'关键字段{f}不足两类来源支持')
        audit[f]={'values':vv,'support_types':list(vv) if agree else [],'conflicts':{} if agree else vv,'accepted':facts[f]}
    # Resolve region to the most specific text claim, checking all explicit regions
    # and the real radar trajectory. Wide region does not license a different locality.
    textregs=[(s,a['region']) for s,a in claims.items() if a['region']]
    region=max([v for _,v in textregs],key=len) if textregs else r['region']
    specific_candidate=region;precision_limit=None
    if r['kind']=='飞机' and len(textregs)==2 and compatible_region(textregs[0][1],textregs[1][1]):
        if any(reg in GENERIC for _,reg in textregs) and not all(reg==region for _,reg in textregs):
            # A broad sea mention cannot corroborate a finer place name. Radar
            # coordinates below only check plausibility, not exact polygons.
            region=next(reg for _,reg in textregs if reg in GENERIC)
            precision_limit='具体地名仅一类正文明确支持；雷达坐标不作为细地名第二票，输出共同支持的海域层级'
    regsupport=[];regconflicts=[]
    for s,a in claims.items():
        for reg in a['regions']:
            if compatible_region(region,reg):
                if s not in regsupport:regsupport.append(s)
            else:regconflicts.append({'source':s,'region':reg})
    if r['kind']=='飞机':
        p=position_support(specific_candidate or '',r['coords'])
        if p is True:regsupport.append('雷达')
        elif p is False:regconflicts.append({'source':'雷达','reason':'轨迹与文本具体区域不相容'})
    else:
        for reg in r['regions']:
            if compatible_region(region,reg):
                if '雷达' not in regsupport:regsupport.append('雷达')
            else:regconflicts.append({'source':'雷达','region':reg})
    if regconflicts:issues.append('关键区域冲突：'+str(regconflicts))
    if len(regsupport)<2:issues.append('关键区域不足两类来源支持')
    if not region:issues.append('具体区域缺失')
    facts['region']=region;facts['direction']=direction(region or '')
    audit['region']={'accepted':region,'specific_location_candidate':specific_candidate,'precision_limit':precision_limit,'support_types':regsupport,'conflicts':regconflicts,'radar_regions':r['regions']}
    for s,a in claims.items():
        if a['task_candidates'] and len(a['task_candidates'])>1:issues.append(f'{s}同一事实段出现多任务候选：{a["task_candidates"]}')
        if a['date']!=r['date']:issues.append(f'{s}日期不一致')
    if len(claims)!=2:issues.append('三类来源未全部关联，保留两源或单源候选')
    # Both subject and normalized model are supported by >=2 types above.
    facts['platform']=r['platform'];facts['country']=facts['country'] or r['country']
    facts['start']=fmt(facts['start']);facts['end']=fmt(facts['end'])
    return facts,audit,list(dict.fromkeys(issues))

def process_day(daydir,root,as_of):
    if date(daydir.name)>date(as_of):
        raise ValueError('Node-after data prohibited in this cutoff verifier')
    lex,regions,tasks=vocabulary(daydir);atoms=[];documents=[]
    for source in ['开源军情','网上舆论']:
        for p in sorted((daydir/source).glob('*.txt')):
            aa,doc=text_atoms(p,source,daydir.name,lex,regions,tasks,root);atoms.extend(aa);documents.append(doc)
    radars=radar_events(daydir,root);selected,candidates,ambiguities=assign(atoms,radars);out=[]
    for r in radars:
        claims=selected.get(r['id'],{});facts,fields,issues=audit_fields(r,claims)
        competitors=[]
        # Do not discard an unselected article merely because another article
        # received a higher association score. Test uniquely anchored rivals.
        for a in atoms:
            if a['id'] in {b['id'] for ss in selected.values() for b in ss.values()}:continue
            if a['key']!=r['key'] or a['date']!=r['date']:continue
            targets=[]
            for other in radars:
                if other['key']!=a['key']:continue
                for b in selected.get(other['id'],{}).values():
                    specific=a['region']==b['region'] and a['region'] not in GENERIC and a['region'] is not None
                    interval=a['start'] is not None and b['start'] is not None and abs(a['start']-b['start'])+abs(a['end']-b['end'])<=4
                    if specific or interval:targets.append(other['id'])
            if set(targets)=={r['id']}:
                alternate={**claims,a['source']:a};_,_,altissues=audit_fields(r,alternate)
                explicit=[i for i in altissues if '冲突' in i or '日期不一致' in i or '多任务' in i]
                competitors.append({'atom':a,'alternative_issues':altissues,'explicit_conflicts':explicit})
                issues.extend('未选正文竞争证据：'+i for i in explicit)
        issues=list(dict.fromkeys(issues))
        valid=not issues;decision='纳入' if valid and facts['direction']!='其他' else '域外' if valid else '排除'
        out.append({**r,'claims':claims,'competing_evidence':competitors,'facts':facts,'field_audit':fields,'issues':issues,'decision':decision,
                    'reason':'三源完成事件关联且各关键字段获得至少两类来源支持，无未消解冲突' if valid else '；'.join(issues)})
    used={a['id'] for aa in selected.values() for a in aa.values()}
    unmatched=[{**a,'reason':'没有独立且唯一的雷达事件对应，或候选发生资源竞争'} for a in atoms if a['id'] not in used]
    return out,{'documents':documents,'atoms':atoms,'candidates':candidates,'ambiguities':ambiguities,'unmatched_atoms':unmatched}

def choose_chain(node,cache):
    """Only today's foreign seed; platform-level thread, never same physical hull claim.
    Split at 15-day gaps, segment by concrete region/mission and 8-14-day gaps. If more
    than 3 regimes, use latest 3; uniform evidence cannot justify artificial phases.
    """
    today=[e for e in cache[node] if e['decision']=='纳入' and e['facts']['country']!='中国']
    options=[]
    for seed in today:
        chain=[]
        for d,ee in sorted(cache.items(),key=lambda p:date(p[0])):
            if date(d)>date(node):continue
            same=[e for e in ee if e['decision']=='纳入' and e['key']==seed['key'] and e['facts']['country']==seed['facts']['country']]
            # All same-day activities remain evidence; never arbitrarily pick first row.
            chain.extend(same)
        dates=sorted({e['date'] for e in chain},key=date)
        cut=0
        for i in range(1,len(dates)):
            if (date(dates[i])-date(dates[i-1])).days>=15:cut=i
        dates=dates[cut:];chain=[e for e in chain if e['date'] in dates]
        if len(dates)<3:continue
        grouped=[]
        for d in dates:
            ee=[e for e in chain if e['date']==d]
            sig=(tuple(sorted({e['facts']['direction'] for e in ee})),tuple(sorted({e['facts']['task'] for e in ee})),tuple(sorted({e['facts']['region'] for e in ee})))
            if not grouped or grouped[-1]['sig']!=sig or (date(d)-date(grouped[-1]['dates'][-1])).days>7:
                grouped.append({'sig':sig,'dates':[d],'events':ee})
            else:grouped[-1]['dates'].append(d);grouped[-1]['events'].extend(ee)
        if len(grouped)>3:
            grouped=grouped[-3:];chain=[e for g in grouped for e in g['events']];dates=sorted({e['date'] for e in chain},key=date)
        if len(dates)<3:continue
        if len(grouped)==1:continue  # no evidence-defined phase change
        gaps=[(date(b)-date(a)).days for a,b in zip(dates,dates[1:])]
        options.append({'seed':seed['id'],'country':seed['facts']['country'],'platform':seed['platform'],'key':seed['key'],'dates':dates,
                        'events':[e['id'] for e in chain],'stages':[{**g,'events':[e['id'] for e in g['events']]} for g in grouped],'gaps':gaps,
                        'identity_scope':'同一主体同型平台活动线索；批号跨日不同，不认定为同一机体或舰体'})
    if not options:return None
    return max(options,key=lambda c:(len(c['dates']),int(c['country']=='美国'),len({e for e in c['gaps'] if e>7})))
