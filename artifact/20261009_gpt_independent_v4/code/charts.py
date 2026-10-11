"""True-day charts. Lane diagrams avoid fabricated ship coordinates."""
import argparse,json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

COLORS={'东海':'#24628D','南海':'#AA5D29','黄海':'#397751'}

def render(p,out):
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],'axes.unicode_minus':False,'font.size':11})
    dest=out/'日报'/p['day']/'附件图表';dest.mkdir(parents=True,exist_ok=True)
    counter={'飞机':Counter(),'舰艇':Counter()};data=[]
    for e in p['events']:
        f=e['facts'];hour=int(f['start'].split(':')[0]);counter[e['kind']][hour]+=f['quantity'];data.append({'id':e['id'],'date':e['date'],'hour':hour,'kind':e['kind'],'quantity':f['quantity']})
    fig,ax=plt.subplots(figsize=(11,5),dpi=160)
    for kind,color,marker,unit in [('飞机','#24628D','o','架次'),('舰艇','#AA5D29','s','艘次')]:
        ax.plot(range(24),[counter[kind][h] for h in range(24)],color=color,marker=marker,label=kind+unit,linewidth=1.8,markersize=4)
    ax.set(title=p['day']+' 舰机侦巡数量曲线图',xlabel='活动起始小时（当日，小时）',ylabel='记录数量（架次 / 艘次）',xticks=range(0,24,2),xlim=(-0.4,23.4))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True));ax.grid(alpha=.18);ax.legend();fig.text(.5,.01,'每起事件按活动开始小时计入一次；不表示每小时在场数量。',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(dest/p['charts'][0]);plt.close(fig)
    for ix,(group,pred) in enumerate([('中国',lambda e:e['facts']['country']=='中国'),('美国',lambda e:e['facts']['country']=='美国'),('其他国家',lambda e:e['facts']['country'] not in ['中国','美国'])],1):
        es=sorted([e for e in p['events'] if pred(e)],key=lambda e:(e['facts']['direction'],e['facts']['start']))
        fig,ax=plt.subplots(figsize=(11,max(4.8,1.6+.43*len(es))),dpi=160)
        labels=[]
        for i,e in enumerate(es):
            f=e['facts'];st=int(f['start'][:2])+int(f['start'][3:])/60;en=int(f['end'][:2])+int(f['end'][3:])/60
            marker='^' if e['kind']=='飞机' else 's';color=COLORS[f['direction']]
            ax.plot([st,en],[i,i],color=color,linewidth=3,solid_capstyle='round');ax.scatter([st],[i],color=color,marker=marker,s=45,zorder=3)
            ax.text(en+.15,i,f'{f["quantity"]}'+('架次' if e['kind']=='飞机' else '艘次'),va='center',fontsize=9)
            labels.append(f'{e["ref"]} {f["country"]} {e["platform"]}\n{f["region"]}  {f["task"]}')
        if es:ax.set_yticks(range(len(es)),labels=labels,fontsize=9);ax.invert_yaxis()
        else:ax.set_yticks([]);ax.text(.5,.5,'当日无满足三源核验的该组记录',transform=ax.transAxes,ha='center')
        ax.set(xlabel='当日活动时间（小时）',ylabel='平台及具体活动区域（条目）',xlim=(0,25),xticks=range(0,25,3))
        fig.suptitle(p['day']+' '+group+'主要机舰活动示意图',fontsize=14,y=.99)
        handles=[Line2D([0],[0],color=c,lw=3,label=d) for d,c in COLORS.items()]+[Line2D([0],[0],color='#333333',marker=m,linestyle='',label=k) for m,k in [('^','飞机'),('s','舰艇')]]
        ax.legend(handles=handles,ncol=5,fontsize=9,loc='lower center',bbox_to_anchor=(.5,1.03));ax.grid(axis='x',alpha=.2)
        fig.text(.5,.01,'时空条带示意：每条线是一项当日活动，不绘制缺失坐标或虚构航线；其他国家含台湾。',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.035,1,.90));fig.savefig(dest/p['charts'][ix]);plt.close(fig)
    (out/'payloads'/ (p['day']+'.chart_data.json')).write_text(json.dumps({'day':p['day'],'curve':data,'diagrams':[e['id'] for e in p['events']],'source':'daily accepted events only'},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);x=a.parse_args()
    for f in sorted((x.output/'payloads').glob('*.json')):
        if '.chart_data' not in f.name:render(json.loads(f.read_text(encoding='utf-8')),x.output)
