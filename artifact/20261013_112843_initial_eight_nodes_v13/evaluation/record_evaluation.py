"""Archive the user's displayed eight-node means without changing submitted files."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import json, hashlib

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[1]
RAW='赛程=initial；节点数=8；完整性=86.5219；准确性=70.8849；格式=96.9027；分析=60.0000；总分=各节点(完整性×25%+准确性×40%+格式×15%+分析×20%)的平均值'
METRICS={'completeness':'86.5219','accuracy':'70.8849','format':'96.9027','analysis':'60.0000'}
WEIGHTS={'completeness':'0.25','accuracy':'0.40','format':'0.15','analysis':'0.20'}
HISTORY={'v4':{'completeness':'74.8767','accuracy':'85.5277','format':'76.4282','analysis':'55.7500'},'v9':{'completeness':'86.2631','accuracy':'67.3760','format':'96.5612','analysis':'55.8750'},'v12':{'completeness':'86.2631','accuracy':'67.3760','format':'96.8050','analysis':'53.6250'}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def total(m):return sum(Decimal(m[k])*Decimal(WEIGHTS[k]) for k in WEIGHTS)
def display(v):return str(v.quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP))
def main():
    result=total(METRICS);assert result==Decimal('76.519840')
    comparisons={}
    for v,old in HISTORY.items():
        delta={k:Decimal(METRICS[k])-Decimal(old[k]) for k in WEIGHTS}
        comparisons[v]={'historical_metrics':old,'historical_total':str(total(old)),'metric_differences':{k:str(x) for k,x in delta.items()},'weighted_contributions':{k:str(delta[k]*Decimal(WEIGHTS[k])) for k in WEIGHTS},'total_difference':str(result-total(old)),'total_difference_display_4dp':display(result-total(old))}
    archives=[]
    for name in ['赛题2_初赛_v13_八节点正式提交包.zip','赛题2_初赛_v13_完整工程包.zip']:
        p=BASE/name;archives.append({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size})
    handoff=json.loads((BASE/'handoff_manifest.json').read_text(encoding='utf8'))
    assert all(x['sha256']==next(r['sha256'] for r in handoff['archives'] if r['file']==Path(x['path']).name) for x in archives)
    obj={'recorded_date':'2026-10-13','stage':'initial','node_count':8,'version':BASE.name,'source':'用户在本版本交付后的当前聊天反馈；未独立访问平台记录','raw_user_feedback':RAW,'reported_metrics':METRICS,'weights':WEIGHTS,'computed_total_from_displayed_means':str(result),'computed_total_display_4dp':display(result),'platform_total_separately_provided':False,'platform_submission_id':None,'platform_receipt':None,'per_node_scores':None,'deduction_details':None,'version_binding':'当前聊天在v13正式交付后用户反馈本版得分；本地ZIP哈希绑定未经平台回执独立核验','archives_unchanged':archives,'comparisons':comparisons,'highest_known_historical_computed_total_before_v13':{'version':'v4','value':'75.544485'},'new_highest_among_archived_user_reported_means':True,'limits':['展示均值可能舍入；不是平台未舍入独立总分','准确性不是事件正确率，完整性不是召回率','多项事实/分析/格式变化，不能将分差唯一归因于某项修复','评测前正式文件、ZIP、审计和handoff保持原样；评分记录追加，旧无评分声明指交付时状态']}
    dest=BASE/'evaluation/evaluation_initial_20261013.json';dest.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    doc='''# v13 初赛八节点评测记录

2026-10-13，用户在v13交付后的当前聊天反馈：initial、8节点；完整性86.5219、准确性70.8849、格式96.9027、分析60.0000。按展示均值加权，总分为 **76.5198**，较v4 **+0.9754**、较v9 **+2.3445**、较v12 **+2.7579**。这是目前已归档用户反馈中的最高计算总分；准确性仍低于v4。

|指标|权重|v13|较v4|较v9|较v12|
|---|---:|---:|---:|---:|---:|
|完整性|25%|86.5219|+11.6452|+0.2588|+0.2588|
|准确性|40%|70.8849|−14.6428|+3.5089|+3.5089|
|格式|15%|96.9027|+20.4745|+0.3415|+0.0977|
|分析|20%|60.0000|+4.2500|+4.1250|+6.3750|
|加权总分|100%|**76.5198**|**+0.9754**|**+2.3445**|**+2.7579**|

精确计算：`86.5219×0.25 + 70.8849×0.40 + 96.9027×0.15 + 60.0000×0.20 = 76.519840`。展示均值可能已舍入，没有另外提供平台未舍入总分。逐节点加权后取平均与均值加权等价，但本次没有逐节点数据。

相对v12，完整性、准确性、格式、分析对总分变化的贡献依次为+0.064700、+1.403560、+0.014655、+1.275000，合计+2.757915。相对v4依次为+2.911300、−5.857120、+3.071175、+0.850000，合计+0.975355。上述是分数分解，不是具体修改的因果归因；准确性不是事件正确率，完整性不是召回率。

## 版本绑定与原始反馈

本版为`artifact/20261013_112843_initial_eight_nodes_v13/`。绑定依据是当前聊天中v13交付后的“本版得分”反馈，未取得平台提交ID、回执、扣分明细或逐节点分数。[原始反馈、精确计算、版本比较和ZIP哈希](../artifact/20261013_112843_initial_eight_nodes_v13/evaluation/evaluation_initial_20261013.json)单独追加。

'''
    for a in archives:doc+=f"- {Path(a['path']).name} SHA256：`{a['sha256']}`。\n\n"
    doc+='''评测前48份正式文件、两个ZIP、冻结台账及原交付审计保持原样，不重打包改变已交付哈希。原README及handoff中的“无新评分、未上传”代表交付时状态；本次评分另存evaluation。没有平台回执，不能由此次反馈补造上传成功记录。

## 交付与复现

[v13源码、状态与交付说明](../artifact/20261013_112843_initial_eight_nodes_v13/README.md)包含八节点202条当日记录、8DOCX/8XLSX/32PNG、90页完整渲染修复、证据审计、原始事实重建与已审阅分析回放。本地完整工程ZIP通过Git LFS保存；拉取后使用`git lfs pull`取得完整二进制。新成绩支持本轮四项展示均值和计算总分，但没有逐字段反馈，不能直接确认哪条事实裁决或主线改写贡献了分数。
'''
    (ROOT/'docs/13-v13初赛评测记录.md').write_text(doc,encoding='utf8')
    section='''

## 2026-10-13 评测反馈（交付后追加）

用户反馈initial八节点：完整性 **86.5219**、准确性 **70.8849**、格式 **96.9027**、分析 **60.0000**；按展示均值计算总分 **76.5198**，较v4 **+0.9754**、较v9 **+2.3445**、较v12 **+2.7579**，成为目前已归档用户反馈中的最高计算总分。准确性仍低于v4，不把聚合指标解释为事件正确率。

[原始评分归档](evaluation/evaluation_initial_20261013.json)与[比较说明](../../docs/13-v13初赛评测记录.md)单独追加。平台提交ID、回执、逐节点分数和扣分明细未提供；版本绑定来自当前交付聊天。评测前48文件、两个ZIP、台账和原交付审计不修改，以上“无评分”陈述代表交付时状态。完整工程ZIP通过Git LFS保存，需`git lfs pull`。
'''
    p=BASE/'README.md'
    if '## 2026-10-13 评测反馈（交付后追加）' not in p.read_text(encoding='utf8'):p.write_text(p.read_text(encoding='utf8')+section,encoding='utf8')
    print('v13 weighted score',display(result),'exact',result,'all submitted archive hashes unchanged')
if __name__=='__main__':main()
