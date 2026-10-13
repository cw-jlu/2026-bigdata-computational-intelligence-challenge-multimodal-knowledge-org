"""Sample-aligned charts; only presentation changes, all values from frozen facts."""
from common import *
from PIL import Image,ImageDraw,ImageFont
from functools import lru_cache
NAMES=['01_舰机侦巡数量曲线图.png','02_中国主要机舰活动示意图.png','03_美国主要机舰活动示意图.png','04_其他国家主要机舰活动示意图.png']
W=2400
COLORS={'飞机':'#DC742C','舰艇':'#4D8FB5'}
def minute(s):return int(s[:2])*60+int(s[3:]) if s else None
@lru_cache(None)
def font(n):return ImageFont.truetype('C:/Windows/Fonts/simhei.ttf',n)
def wrap(d,txt,width,n):
    lines=[];line=''
    for c in txt:
        if d.textlength(line+c,font=font(n))>width:lines.append(line);line=c
        else:line+=c
    return lines+[line] if line else lines
def dashed(d,x0,y0,x1,y1):
    if x0==x1:
        for y in range(int(y0),int(y1),15):d.line((x0,y,x0,min(y+8,y1)),fill='#E5E5E5',width=2)
    else:
        for x in range(int(x0),int(x1),15):d.line((x,y0,min(x+8,x1),y1),fill='#E5E5E5',width=2)
def rotated_tick(im,text,x,y):
    tile=Image.new('RGBA',(125,48),(255,255,255,0));td=ImageDraw.Draw(tile)
    td.text((0,0),text,font=font(32),fill='black');tile=tile.rotate(45,expand=True,resample=Image.Resampling.BICUBIC)
    im.paste(tile,(round(x-tile.width*.72),round(y)),tile)
def draw(data,dest):
    dest.mkdir(parents=True,exist_ok=True);ee=data['today_events'];when=dt(data['as_of'].replace('-','.'))
    title=f'{when.month}月{when.day}日';full=f'{when.year}年{title}'
    chartdata={'as_of':data['as_of'],'event_ids':[e['id'] for e in ee],'sampling':'核实活动窗口整点参与量之和，不是去重实体数；线段只连接整点；未知时间不补造','hourly':[],'groups':[]}
    for hr in range(24):
        rec={'hour':hr}
        for kind,key in [('飞机','air'),('舰艇','ship')]:rec[key]=sum(e['facts']['quantity'] for e in ee if e['kind']==kind and e['facts']['start'] and e['facts']['end'] and minute(e['facts']['start'])<=hr*60<=minute(e['facts']['end']))
        chartdata['hourly'].append(rec)
    im=Image.new('RGB',(W,1320),'white');d=ImageDraw.Draw(im)
    d.text((W/2,24),title+'舰机侦巡数量曲线图',font=font(54),fill='black',anchor='mt')
    x0,x1,y0,y1=120,2330,110,1040;top=max(4,max(max(r['air'],r['ship']) for r in chartdata['hourly'])+1)
    for i in range(top+1):
        y=y1-(y1-y0)*i/top;dashed(d,x0,y,x1,y);d.line((x0-8,y,x0,y),fill='black',width=2);d.text((x0-20,y),str(i),font=font(34),fill='black',anchor='rm')
    for hr in range(24):
        x=x0+50+(x1-x0-100)*hr/23;dashed(d,x,y0,x,y1);d.line((x,y1,x,y1+10),fill='black',width=2);rotated_tick(im,f'{hr:02d}:00',x,y1+16)
    d.rectangle((x0,y0,x1,y1),outline='black',width=2);d.text((40,560),'数\n量',font=font(34),fill='black',anchor='mm',spacing=5)
    for kind,key,col,ly in [('飞机','air','#C0392B',170),('舰艇','ship','#21618C',224)]:
        pts=[(x0+50+(x1-x0-100)*hr/23,y1-(y1-y0)*r[key]/top) for hr,r in enumerate(chartdata['hourly'])];d.line(pts,fill=col,width=6)
        for x,y in pts:(d.ellipse if kind=='飞机' else d.rectangle)((x-9,y-9,x+9,y+9),fill=col)
    d.rounded_rectangle((1940,130,2305,264),radius=6,fill='white',outline='#CCCCCC',width=3)
    for kind,col,ly in [('飞机','#C0392B',170),('舰艇','#21618C',224)]:
        d.line((1960,ly,2028,ly),fill=col,width=6);(d.ellipse if kind=='飞机' else d.rectangle)((1985,ly-9,2003,ly+9),fill=col)
        d.text((2045,ly),kind+('（架）' if kind=='飞机' else '（艘）'),font=font(36),fill='black',anchor='lm')
    d.text((W/2,1166),'时段',font=font(36),fill='black',anchor='mt');unknown=sum(not e['facts']['start'] or not e['facts']['end'] for e in ee)
    d.text((90,1223),f'注：逐活动累加核实窗口的整点参与量；{unknown}条时间未知记录不入曲线，不将24个时刻相加作为当日总数。',font=font(28),fill='#555555')
    d.text((90,1265),'时间沿用赛题记录（未注明时区）；观测窗口不代表起降或逐秒在场。来源：本节点冻结台账。',font=font(28),fill='#555555');im.save(dest/NAMES[0],dpi=(180,180))
    for titlegroup,name,selector in [('中国',NAMES[1],lambda e:e['facts']['country']=='中国'),('美国',NAMES[2],lambda e:e['facts']['country']=='美国'),('其他国家及台湾',NAMES[3],lambda e:e['facts']['country'] not in ['中国','美国'])]:
        rows=sorted([e for e in ee if selector(e)],key=lambda e:(e['facts']['start'] or '99',e['ref']));rh=128;n=max(len(rows),3);H=310+n*rh
        im=Image.new('RGB',(W,H),'white');d=ImageDraw.Draw(im);d.text((W/2,28),full+titlegroup+'主要机舰活动示意图',font=font(51),fill='black',anchor='mt')
        x0,x1,y0,y1=795,2335,125,125+n*rh
        for hr in range(0,25,2):
            x=x0+(x1-x0)*hr/24;dashed(d,x,y0,x,y1);d.line((x,y1,x,y1+10),fill='black',width=2);d.text((x,y1+23),f'{hr:02d}:00',font=font(31),fill='black',anchor='mt')
        d.rectangle((x0,y0,x1,y1),outline='black',width=2)
        for i,e in enumerate(rows):
            f=e['facts'];y=y0+(i+.5)*rh;prefix=f"{e['ref']} {e['kind']} | {f['country']}";platform=f"{f['platform']}({f['quantity']})";label=prefix+' | '+platform
            lines=[label] if d.textlength(label,font=font(34))<=755 else [prefix]+wrap(d,platform,755,34)
            assert len(lines)<=3,(name,label)
            for j,t in enumerate(lines):d.text((x0-20,y+(j-(len(lines)-1)/2)*38),t,font=font(34),fill='black',anchor='rm')
            d.line((x0-9,y,x0,y),fill='black',width=2);annotation=f['region']+' / '+f['direction']+' / '+(f['task'] or '任务未充分核实')
            if f['start'] and f['end']:
                a=x0+(x1-x0)*minute(f['start'])/1440;b=x0+(x1-x0)*minute(f['end'])/1440;d.rectangle((a,y-29,max(b,a+3),y+29),fill=COLORS[e['kind']]);width=d.textlength(annotation,font=font(32))
                if b+14+width<=x1-8:tx=b+14;anchor='lm';lines=[annotation]
                elif a-14-width>=x0+8:tx=a-14;anchor='rm';lines=[annotation]
                else:
                    right=x1-b-22;left=a-x0-22;side=max(left,right);lines=wrap(d,annotation,side,32);assert len(lines)<=2,(name,annotation,side)
                    tx=b+14 if right>=left else a-14;anchor='lm' if right>=left else 'rm'
                for j,t in enumerate(lines):
                    yy=y+(j-(len(lines)-1)/2)*37;box=d.textbbox((tx,yy),t,font=font(32),anchor=anchor);assert box[0]>=x0 and box[2]<=x1,(name,annotation,box)
                    d.text((tx,yy),t,font=font(32),fill='black',anchor=anchor)
            else:
                for j,t in enumerate(wrap(d,'时间未充分核实；'+annotation,x1-x0-50,32)):d.text(((x0+x1)/2,y-18+j*37),t,font=font(32),fill='#555555',anchor='mm')
        if not rows:d.text(((x0+x1)/2,(y0+y1)/2),'无满足三源核验条件的当日记录',font=font(36),fill='#555555',anchor='mm')
        d.text(((x0+x1)/2,y1+69),'时段',font=font(36),fill='black',anchor='mt')
        # External legend cannot obscure a late-day activity, unlike the sample's last row.
        ly=H-48;d.rectangle((1900,ly-17,1960,ly+17),fill=COLORS['飞机']);d.text((1975,ly),'飞机',font=font(32),fill='black',anchor='lm');d.rectangle((2130,ly-17,2190,ly+17),fill=COLORS['舰艇']);d.text((2205,ly),'舰艇',font=font(32),fill='black',anchor='lm')
        d.text((38,H-96),'F编号对应当日明细；括号数量为架次／艘次，横条表示已核实观测窗口。',font=font(28),fill='#555555');d.text((38,H-52),'全部当日核实活动；未知时间不画横条，不补造位置或航迹。',font=font(28),fill='#555555')
        im.save(dest/name,dpi=(180,180));chartdata['groups'].append({'name':name,'event_ids':[e['id'] for e in rows]})
    return chartdata
