from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import json,hashlib,collections,datetime
BASE=Path(__file__).resolve().parents[1]
NODES=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    scores=dict(zip(['completeness','accuracy','format','analysis'],map(Decimal,['86.1320','65.2266','96.5230','45.2500'])))
    weights=dict(zip(scores,map(Decimal,['0.25','0.40','0.15','0.20'])))
    total=sum(scores[k]*weights[k] for k in scores)
    v2=dict(zip(scores,map(Decimal,['84.4760','64.8389','76.5391','52.5000'])))
    stats=[]
    for n in NODES:
        f=read(BASE/f'audits/{n}/frozen_ledger.json');ee=f['today_events'];m=f['mainline'];cc=read(BASE/f'audits/{n}/candidate_decisions.json');a=read(BASE/f'audits/{n}/audit.json')
        stats.append({'node':n,'included_events':len(ee),'candidate_decisions':dict(collections.Counter(e['decision'] for e in cc)),'generic_region_events':sum(e['facts']['region'] in ['东海','南海','黄海'] for e in ee),'unknown_task_events':sum(e['facts']['task'] is None for e in ee),'mainline_dates':len(m['dates']),'stages':len(m['stages']),'single_date_stages':sum(len(s['dates'])==1 for s in m['stages']),'used_source_ids':a['used_source_ids'],'facts_sampled':4,'candidate_count':len(f['candidate_comparison']),'original_selected_candidate_suitable':next(x['suitable'] for x in f['candidate_comparison'] if (x['country'],x['key'])==(m['country'],m['key']))})
    assets=[]
    for name in ['赛题2_初赛_八节点_完整候选提交包.zip','赛题2_初赛_八节点_工程与证据包.zip']:
        p=BASE/name;assets.append({'name':name,'sha256':sha(p),'bytes':p.stat().st_size})
    result={'received_on':'2026-10-12','stage':'initial','node_count':8,'source':'user_reported_platform_evaluation','original_feedback':'赛程=initial；节点数=8；完整性=86.1320；准确性=65.2266；格式=96.5230；分析=45.2500；总分=各节点(完整性×25%+准确性×40%+格式×15%+分析×20%)的平均，分数出来了，写一下，然后把这版提交到GitHub，想想为什么分不够高','metrics':{k:str(v) for k,v in scores.items()},'weights':{k:str(v) for k,v in weights.items()},'weighted_contributions':{k:str(scores[k]*weights[k]) for k in scores},'weighted_total_exact_from_displayed_means':str(total),'weighted_total_4dp':str(total.quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP)),'total_is_derived_not_separately_reported':True,'loss_to_100_by_dimension_arithmetic_only':{k:str((100-scores[k])*weights[k]) for k in scores},'comparison_v2':{'metric_deltas':{k:str(scores[k]-v2[k]) for k in scores},'weighted_deltas':{k:str((scores[k]-v2[k])*weights[k]) for k in scores},'total_delta_exact':str(sum((scores[k]-v2[k])*weights[k] for k in scores))},'artifact_association':'user feedback refers to preceding v8 delivery in this chat','independently_verified_submission_binding':False,'platform_submission_id':None,'platform_receipt':None,'node_level_scores':None,'deduction_details':None,'formal_snapshot_unchanged':True,'delivery_assets':assets,'implementation_diagnostics':stats,'diagnostic_limits':['准确性评分不是事件正确率，完整性评分不是召回率','节点均值不定位具体事件或具体失分节点','实现问题为可核查观察；没有逐节点/逐字段扣分，不归因具体扣分数','原八节点日报、台账及两ZIP不改写，评测反馈作为交付后的独立记录']}
    (BASE/'evaluation/evaluation_initial_20261012.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'total':result['weighted_total_4dp'],'weighted':result['weighted_contributions'],'loss':result['loss_to_100_by_dimension_arithmetic_only'],'v2_delta':result['comparison_v2'],'diagnostics':stats},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
