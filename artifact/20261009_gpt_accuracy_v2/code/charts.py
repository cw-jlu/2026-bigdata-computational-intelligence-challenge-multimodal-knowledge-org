import json
import sys
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

FILES=['01_舰机侦巡数量曲线图.png','02_中国主要机舰活动示意图.png','03_美国主要机舰活动示意图.png','04_其他国家主要机舰活动示意图.png']
COLORS={'东海':'#286994','南海':'#BA6138','黄海':'#437B54'}
RECON={'反潜巡逻','战备警巡','联合巡逻','情报监视侦察','海上侦察巡逻','电子侦察','联合巡航','战备巡逻','海上巡逻','海上监视侦察'}

def make(pack,folder):
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','Arial Unicode MS'],'axes.unicode_minus':False,'font.size':10})
    folder.mkdir(parents=True,exist_ok=True)
    ee=pack['events']; day=pack['date']; datasets=[]
    air=Counter(); ships=Counter(); recon=[e for e in ee if e['task'] in RECON]
    for e in recon: (air if e['kind']=='飞机' else ships)[e['interval'][0]//60]+=e['quantity']
    fig,ax=plt.subplots(figsize=(11,5.6),dpi=180)
    xx=list(range(24))
    ax.plot(xx,[air[x] for x in xx],color='#286994',marker='o',label='飞机（架次）',linewidth=2)
    ax.plot(xx,[ships[x] for x in xx],color='#BA6138',marker='s',label='舰艇（艘次）',linewidth=2)
    ax.set_title(f'{day} 舰机侦巡数量曲线图',pad=18,fontweight='bold')
    ax.set(xlabel='材料记录的活动开始小时（时）',ylabel='核验侦巡活动数量（架次／艘次）',xticks=range(0,24,2),xlim=(-.4,23.4),ylim=(0,max([*air.values(),*ships.values(),1])+1))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True)); ax.grid(axis='y',alpha=.25); ax.legend(frameon=False)
    fig.text(.08,.02,'口径：仅统计已核实侦巡任务，按活动开始小时计入；非同时在场数量，不累计轨迹点。',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,1)); fig.savefig(folder/FILES[0]); plt.close(fig)
    datasets.append({'filename':FILES[0],'date':day,'event_ids':[e['event_id'] for e in recon],'hours':xx,'air':[air[x] for x in xx],'ships':[ships[x] for x in xx],'quantity_unit':'架次/艘次','recon_tasks':sorted(RECON)})
    groups=[('中国',lambda e:e['country']=='中国'),('美国',lambda e:e['country']=='美国'),('其他国家',lambda e:e['country'] not in ('中国','美国'))]
    for index,(label,pred) in enumerate(groups,1):
        subset=sorted([e for e in ee if pred(e)],key=lambda e:(e['direction'],e['country'],e['interval'][0],e['event_id']))
        fig,ax=plt.subplots(figsize=(12,max(4.5,2.3+len(subset)*.43)),dpi=180)
        labels=[]
        for i,e in enumerate(subset):
            y=len(subset)-1-i; a,b=[x/60 for x in e['interval']]; color=COLORS[e['direction']]
            ax.plot([a,b],[y,y],linewidth=5,color=color,solid_capstyle='round',alpha=.75)
            ax.scatter([a],[y],marker='^' if e['kind']=='飞机' else 's',s=55,c=color,zorder=3)
            labels.append(f"{e['country']} {e['platform']}\n{e['region']}  {e['quantity']}{'架次' if e['kind']=='飞机' else '艘次'}")
        ax.set(yticks=list(reversed(range(len(subset)))),yticklabels=labels,xticks=range(0,25,3),xlim=(0,24),xlabel='材料记录的活动时间（时）',ylabel='核验活动记录（每行1起）')
        if not subset: ax.text(.5,.5,'当日无三源核验通过的该组核心海域活动',transform=ax.transAxes,ha='center'); ax.set_yticks([])
        else: ax.set_ylim(-.8,len(subset)-.2)
        ax.set_title(f'{day} {label}主要机舰活动示意图',pad=34,fontweight='bold')
        legend=[Line2D([0],[0],color=c,lw=4,label=d) for d,c in COLORS.items()]+[Line2D([0],[0],color='#333333',marker=m,linestyle='',label=l) for m,l in [('^','飞机'),('s','舰艇')]]
        ax.legend(handles=legend,loc='lower center',bbox_to_anchor=(.5,1.005),ncol=5,frameon=False,fontsize=9)
        ax.grid(axis='x',alpha=.25); ax.tick_params(axis='y',length=0,labelsize=9)
        fig.text(.06,.015,'时间与海域示意，不虚构舰艇经纬度。其他国家组包含台湾地区；线段为核验活动窗口，非起降时间。',fontsize=8.5)
        fig.tight_layout(rect=(0,.045,1,1)); fig.savefig(folder/FILES[index]); plt.close(fig)
        datasets.append({'filename':FILES[index],'date':day,'event_ids':[e['event_id'] for e in subset],'group':label,'records':[{'event_id':e['event_id'],'date':e['date'],'interval':e['interval'],'region':e['region'],'quantity':e['quantity'],'country':e['country'],'kind':e['kind']} for e in subset]})
    return datasets

if __name__=='__main__':
    source=Path(sys.argv[1]); target=Path(sys.argv[2]); all_data=[]
    for p in sorted(source.glob('factpack_*.json')):
        pack=json.loads(p.read_text(encoding='utf-8')); all_data+=make(pack,target/pack['date']/'附件图表')
    (source/'chart_datasets.json').write_text(json.dumps(all_data,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PNG charts created:',len(all_data))
