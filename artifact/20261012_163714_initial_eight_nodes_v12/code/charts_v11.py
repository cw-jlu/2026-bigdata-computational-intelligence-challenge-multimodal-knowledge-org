from common import *
from PIL import Image,ImageDraw,ImageFont
NAMES=['01_舰机侦巡数量曲线图.png','02_中国主要机舰活动示意图.png','03_美国主要机舰活动示意图.png','04_其他国家主要机舰活动示意图.png']
def minute(s):return int(s[:2])*60+int(s[3:]) if s else None
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def wrap(d,txt,width,n):
    lines=[];line=''
    for c in txt:
        if d.textlength(line+c,font=font(n))>width:lines.append(line);line=c
        else:line+=c
    return lines+[line] if line else lines
def draw(data,dest):
    dest.mkdir(parents=True,exist_ok=True);ee=data['today_events'];when=dt(data['as_of'].replace('-','.'));title=f'{when.month}月{when.day}日';W=2400;ink='#152A3B';gray='#4E6173';colors={'飞机':'#C85E23','舰艇':'#286F9D'}
    chartdata={'as_of':data['as_of'],'event_ids':[e['id'] for e in ee],'sampling':'核实活动窗口整点参与量之和，不是去重实体数；线段只连接整点；未知时间不补造','hourly':[],'groups':[]}
    im=Image.new('RGB',(W,1230),'white');d=ImageDraw.Draw(im)
    d.text((W/2,40),title+'舰机侦巡数量曲线图',font=font(58),fill=ink,anchor='mt');d.text((W/2,130),'三海核实活动窗口参与量（架／艘）',font=font(38),fill=gray,anchor='mt')
    for hr in range(24):
        rec={'hour':hr}
        for kind,key in [('飞机','air'),('舰艇','ship')]:rec[key]=sum(e['facts']['quantity'] for e in ee if e['kind']==kind and e['facts']['start'] and e['facts']['end'] and minute(e['facts']['start'])<=hr*60<=minute(e['facts']['end']))
        chartdata['hourly'].append(rec)
    x0,x1,y0,y1=180,2260,270,960;top=max(4,max(max(r['air'],r['ship']) for r in chartdata['hourly'])+1)
    for i in range(top+1):
        y=y1-(y1-y0)*i/top;d.line((x0,y,x1,y),fill='#DDE4EA',width=2);d.text((x0-30,y),str(i),font=font(34),fill=gray,anchor='rm')
    for hr in range(24):
        x=x0+(x1-x0)*hr/23;d.line((x,y0,x,y1),fill='#EDF1F4');d.text((x,y1+20),f'{hr:02d}',font=font(30),fill=gray,anchor='mt')
    for kind,key,off in [('飞机','air',780),('舰艇','ship',1300)]:
        col=colors[kind];pts=[(x0+(x1-x0)*hr/23,y1-(y1-y0)*r[key]/top) for hr,r in enumerate(chartdata['hourly'])];d.line(pts,fill=col,width=6)
        for x,y in pts:d.ellipse((x-7,y-7,x+7,y+7),fill=col) if kind=='飞机' else d.rectangle((x-7,y-7,x+7,y+7),fill=col)
        d.line((off,220,off+65,220),fill=col,width=8);d.text((off+85,220),kind,font=font(36),fill=ink,anchor='lm')
    unknown=sum(not e['facts']['start'] or not e['facts']['end'] for e in ee)
    d.text((W/2,1035),'时刻（原数据未注明时区，沿用赛题记录）',font=font(34),fill=gray,anchor='mt')
    d.text((80,1110),f'口径：逐活动累加参与量；{unknown}条时间未知活动不进入整点统计。观测窗口不代表起降或逐秒在场。',font=font(32),fill=gray)
    d.text((80,1160),'来源：本节点独立冻结台账。架次／艘次合计另见正文及明细，不累加24个时刻取代当日总数。',font=font(30),fill=gray);im.save(dest/NAMES[0],dpi=(180,180))
    for titlegroup,name,selector in [('中国',NAMES[1],lambda e:e['facts']['country']=='中国'),('美国',NAMES[2],lambda e:e['facts']['country']=='美国'),('其他国家及台湾',NAMES[3],lambda e:e['facts']['country'] not in ['中国','美国'])]:
        rows=sorted([e for e in ee if selector(e)],key=lambda e:(e['facts']['start'] or '99',e['ref']));rh=140;H=400+max(len(rows),1)*rh;im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im)
        d.text((W/2,35),title+titlegroup+'主要机舰活动示意图',font=font(54),fill=ink,anchor='mt');d.text((W/2,110),'全部核实活动；参与数量单位：飞机架次／舰艇艘次',font=font(34),fill=gray,anchor='mt')
        x0,x1,y0=770,1700,250
        d.text((35,185),'主体／平台／数量',font=font(34),fill=ink);d.text((1740,185),'区域／任务',font=font(34),fill=ink)
        for hr in range(0,25,2):
            x=x0+(x1-x0)*hr/24;d.line((x,y0-5,x,y0+max(len(rows),1)*rh),fill='#DDE4EA',width=2);d.text((x,195),f'{hr:02d}',font=font(28),fill=gray,anchor='mt')
        for i,e in enumerate(rows):
            y=y0+i*rh;f=e['facts'];col=colors[e['kind']]
            if i%2==0:d.rectangle((20,y,W-20,y+rh),fill='#F3F6F8')
            for hr in range(0,25,2):
                x=x0+(x1-x0)*hr/24;d.line((x,y,x,y+rh),fill='#DAE1E7',width=1)
            label=f"{e['ref']} {f['country']} {f['quantity']}{'架次' if e['kind']=='飞机' else '艘次'}"
            d.text((35,y+8),label,font=font(36),fill=ink)
            for j,t in enumerate(wrap(d,f['platform'],715,32)):d.text((35,y+55+j*38),t,font=font(32),fill=ink)
            if f['start'] and f['end']:
                a=x0+(x1-x0)*minute(f['start'])/1440;b=x0+(x1-x0)*minute(f['end'])/1440;d.rectangle((a,y+46,max(b,a+3),y+88),fill=col);d.text(((a+b)/2,y+98),f"{f['start']}-{f['end']}",font=font(26),fill=ink,anchor='mt')
            else:d.text(((x0+x1)/2,y+65),'时间未充分核实',font=font(30),fill=gray,anchor='mm')
            for j,t in enumerate(wrap(d,f['region']+'／'+(f['task'] or '任务未知'),600,32)):d.text((1740,y+20+j*40),t,font=font(32),fill=ink)
        if not rows:d.text((W/2,y0+50),'无满足三源核验条件的当日记录',font=font(38),fill=gray,anchor='mt')
        y=H-90;d.text((40,y),'时刻00—24时；颜色：',font=font(30),fill=gray);d.rectangle((410,y+6,450,y+32),fill=colors['飞机']);d.text((465,y),'飞机',font=font(30),fill=ink);d.rectangle((625,y+6,665,y+32),fill=colors['舰艇']);d.text((680,y),'舰艇',font=font(30),fill=ink);d.text((900,y),'F编号回指明细和事实证据；图形不绘制航迹或补造位置。',font=font(29),fill=gray)
        im.save(dest/name,dpi=(180,180));chartdata['groups'].append({'name':name,'event_ids':[e['id'] for e in rows]})
    return chartdata
