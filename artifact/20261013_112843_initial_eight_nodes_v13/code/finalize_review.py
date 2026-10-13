"""Record completed agent review; this is a receipt, not a semantic test."""
from common import *
from collections import Counter
import shutil
from audit_sources import audit as audit_sources

def main():
    priority=load(BASE/'audit/priority_30_55_review.json');samples=load(BASE/'audit/stratified_review.json')
    pids={r['current']['id'] for r in priority};sids={r['current']['id'] for r in samples}
    assert len(priority)==85 and len(samples)==53
    for r in priority:r['reviewer']='current_Codex_agent_known_history_not_blind';r['semantic_review_receipt']='audit/final_semantic_review.json'
    save(BASE/'audit/priority_30_55_review.json',priority)
    save(BASE/'audit/final_semantic_review.json',{
        'reviewer':'current Codex agent who authored outputs and knew historical answers',
        'independent_blind_review':False,
        'priority_rows':85,'priority_categories':dict(Counter(r['category'] for r in priority)),
        'stratified_rows':53,'priority_sample_overlap':len(pids&sids),'unique_reviewed_event_ids':len(pids|sids),
        'node_day_candidate_denominator':427,
        'sample_method':'each node: SHA256(event ID) deterministic ordering, first two of admitted/excluded/outside-domain; add every trajectory anomaly not already sampled',
        'scope':'Agent read the factual source excerpts, extracted values, field adjudications in all 85 priority and 53 stratified cards. Six concurrent trajectory anomalies had all coordinates directly inspected. All radar rows also program inspected. No claim of reading every original paragraph or expert geographical adjudication.',
        'trajectory_verdict':'six batches contain persistent contemporaneous coordinate groups (6/6 or 6/7 rows), not removable isolated points; multiple-entity or mixed-batch hypotheses remain unresolved; no majority/text-fit branch selected',
        'time_verdict':'three current-day X时起 records conservatively excluded for unresolved start/time-scope discrepancy; partial observation window is a plausible alternative, not disproved by this implementation',
        'dependency_verdict':'exact cross-type copied factual paragraphs count 0; saved citation origins still limit source independence. No exact duplicate does not establish editorial independence.',
        'semantic_support_verdict':'current-agent evidence review completed with known limitations; no empirical error-rate or hidden-truth accuracy established',
        'platform_score':None,
        'reviewed_ids':sorted(pids|sids)
    })
    screen=load(BASE/'audit/strait_and_auxiliary_screen.json')
    screen['agent_review']={'reviewed_factual_excerpts':4,'auxiliary_verdict':'four matches are generic commentary about distance from bases/homeports; no concrete base, homeport, takeoff/landing or entry/exit value; leave unknown optional fields blank','strait_verdict':'screen found no explicit three-sea entry/exit relationship; does not certify universal semantic recall'}
    save(BASE/'audit/strait_and_auxiliary_screen.json',screen)
    repro=BASE/'reproduced_raw_v13_final'
    r=load(repro/'reproduction_comparison.json');assert r['status']=='PASS' and len(r['facts'])==8 and len(r['products'])==48
    shutil.copy2(repro/'reproduction_comparison.json',BASE/'audit/final_raw_reproduction_comparison.json')
    shutil.copy2(repro/'run.log',BASE/'audit/final_raw_reproduction_run.log')
    shutil.copy2(repro/'independent_zip_verification.json',BASE/'audit/reproduced_zip_verification.json')
    catalog=load(BASE/'audit/source_catalog.json')
    renders=load(BASE/'word_render.json');xrenders=load(BASE/'excel_render.json')
    visual=[];matrix=[];analysis=[]
    for n in NODES:
        frozen=load(BASE/f'audits/{n}/frozen_ledger.json');snap=load(BASE/f'audits/{n}/analysis_snapshot.json');ar=load(BASE/f'audits/{n}/audit.json')
        assert snap['frozen_sha256']==sha(BASE/f'audits/{n}/frozen_ledger.json')
        ids={e['id'] for e in frozen['verified_events']}
        assert all(set(b.get('premise_event_ids',[]))<=ids for b in snap['blocks'])
        sourcecheck=audit_sources(catalog,dt(n).isoformat(),ar['used_source_ids'],ar['used_source_ids']);assert sourcecheck['status']=='PASS'
        save(BASE/f'audits/{n}/source_metadata_check.json',sourcecheck)
        wr=next(q for q in renders if q['node']==n);assert wr['source_sha256'].lower()==sha(BASE/f'official/{n}/{n}日报.docx')
        er=[q for q in xrenders if q['node']==n];assert len(er)==4 and all(q['source_sha256'].lower()==sha(BASE/f'official/{n}/{n}机舰活动明细.xlsx') for q in er)
        pagefiles=sorted((BASE/f'qa/docx/{n}').glob('page-*.png'));assert len(pagefiles)==wr['pages']
        contacts=sorted((BASE/f'qa/docx/{n}').glob('contact-*.png'));assert len(contacts)==3
        hashes={p.relative_to(BASE).as_posix():sha(p) for p in (BASE/f'official/{n}').rglob('*') if p.is_file()}
        visual.append({'node':n,'docx_pages':wr['pages'],'all_pages_viewed_in_contact_sheets':[p.relative_to(BASE).as_posix() for p in contacts],
            'viewing_method':'agent visual inspection of every page in 2x2 contact sheets; selected originals enlarged, not every page enlarged to 100%',
            'xlsx_all_filled_ranges':[q['range'] for q in er],'xlsx_renderers':['@oai/artifact-tool','WPS Office 12.0 through Excel COM'],
            'xlsx_all_range_images_viewed':f'qa/xlsx_native/{n}/contact-1.png','pngs_all_four_viewed':f'qa/charts/{n}/contact-1.png',
            'docx_renderer':wr['renderer'],'rasterizer':'pypdfium2 5.14.0, scale 1.5',
            'result':'no unresolved overflow/obscured labels/garbled text/empty page found in viewed images','official_sha256':hashes})
        ar['status']='local_delivery_review_complete'
        ar['checks'].update({'source_metadata':'PASS_metadata_only','semantic_support':'current_agent_review_completed_see_audit/final_semantic_review.json','unchanged_fact_layer':'PASS','visual_review':'completed_all_pages_and_filled_ranges_see_audit/final_visual_review.json','raw_input_reproduction':'PASS_reviewed_analysis_replay'})
        ar['reviewed_analysis_snapshot_sha256']=sha(BASE/f'audits/{n}/analysis_snapshot.json')
        ar['semantic_review_receipt']='audit/final_semantic_review.json';save(BASE/f'audits/{n}/audit.json',ar)
        selection=snap['selection'];events=[e for e in frozen['verified_events'] if e['id'] in selection['event_ids']]
        title=selection['country']+selection['platform'];qty=sum(e['facts']['quantity'] for e in events)
        matrix.append({'node':n,'records':len(frozen['today_events']),'mainline':title,'historical_dates':len(selection['dates']),'historical_events':len(events),'participation_quantity':qty,'docx_pages':wr['pages'],'files':6,'fact_rebuild':'PASS','analysis':'authored_and_reviewed','render':'reviewed','raw_reproduction':'PASS'})
        analysis.append({'node':n,'question':snap['question'],'overall':snap['blocks'][0]['text'],'new_analysis_md':f'audits/{n}/analysis.md','snapshot_hash':sha(BASE/f'audits/{n}/analysis_snapshot.json'),'all_stage_premise_ids':[{k:b[k] for k in ['id','text','premise_event_ids']} for b in snap['blocks'] if b['id'] in ['A02','A03','A04']]})
    save(BASE/'audit/final_visual_review.json',{'docx_pages_total':sum(q['docx_pages'] for q in visual),'xlsx_workbooks':8,'xlsx_filled_range_panels':32,'standalone_pngs':32,'reviewer':'current Codex agent','nodes':visual,'fixed_counterexample':'qa/pagination_before/7月9日旧空白第8页；标题段落分页修复','renderer_fallback':'packaged documents render_docx.py failed because LibreOffice soffice.exe absent; real WPS COM PDF export succeeded'})
    save(BASE/'audit/final_node_matrix.json',matrix);save(BASE/'audit/analysis_changes.json',analysis)
    # The reviewed snapshot itself remains immutable; later receipts supersede its authoring-time pending label.
    save(BASE/'audit/final_reading_receipt.json',{
        'program_only_manifests':['audit/program_read_manifest.json','audit/history_inventory.json','audit/actual_historical_section2.json','audit/score_archives.json','audit/raw_to_ledger_coverage.json'],
        'agent_body_read':'v13 prompt; root/docs READMEs; docs01-05 and07-12; submission format; analysis skill/README/generation_prompt/catalog; historical comparison/fusion/v9-v12 README and selected source code/audit excerpts; research README/application_notes/catalog/node eligibility/reading log; reused parser/chart/workbook/build modules',
        'agent_original_read':'actual sample DOCX/XLSX structure and sample rendered DOCX/4PNG; all 85 priority and53 sample factual excerpts; six complete anomaly coordinate groups; all current analysis bodies/claims and all current DOCX pages via contact sheets; all XLSX native filled range panels; all32PNG; R06/R07 one-page fixed originals/text/render',
        'history_program_read':'21 local version folders, 81 actual historical DOCX section2 extractions plus8 recovered Git DOCX; six score JSONs plus initial two feedback values in docs05',
        'history_secondary_reference':'history_review.json and existing all-version/fusion diagnostics used for navigation, not event truth; precise unobserved model configs unknown',
        'external_unread_originals':'R03 full original not re-read, R08 only prior summary; excluded from formal empirical references. R04/R05 historical versions uncertified, method only.',
        'scope_limits':'No claim that all historical source code or all original TXT prose was manually read. Some earlier combined tool reads truncated; docs08/10/11/12 subsequently reread in full. Program counts are not agent full-body reading.'
    })
    rows=['|节点|可信当日记录|分析主线|历史日期/活动/参与数|DOCX页数|6份正式文件/视觉/原始复现|','|---|---:|---|---|---:|---|']
    for q in matrix:rows.append(f"|{q['node']}|{q['records']}|{q['mainline']}|{q['historical_dates']}/{q['historical_events']}/{q['participation_quantity']}|{q['docx_pages']}|全部完成/已检查/PASS|")
    table='\n'.join(rows)
    (BASE/'八节点状态矩阵.md').write_text('# v13 八节点最终状态\n\n'+table+'\n\n参与数为架次或艘次，非去重实体数。90页全文渲染以逐页联系图检查；语义审阅为当前作者检查，非独立盲审。\n',encoding='utf8')
    diff=load(BASE/'audit/version_differences.json')
    drows=['|节点|相对v4新增/撤回/区域变化|相对v9新增/撤回/区域变化|相对v12新增/撤回/区域变化|','|---|---|---|---|']
    for n in NODES:
        vals=[]
        for v in ['v4','v9','v12']:
            d=next(r for r in diff if r['node']==n and r['version']==v);vals.append(f"{len(d['added'])}/{len(d['removed'])}/{len(d['field_changes'])}")
        drows.append('|'+n+'|'+'|'.join(vals)+'|')
    text='''# 相对v4/v9/v12的事实与分析变化

本表比较真实历史XLSX活动ID与活动区域；同一展示口径，不把历史成绩当事实真值。当前八节点202条，相对v4保留172条、新增30条、撤回3条；保留集合中52项区域精度不同。相对v9与v12均为保留202条、撤回3条、没有新增和保留项区域变化。旧v8的30条新增和55项区域变更全部保留逐项调查记录；后三项撤回后，当日保留项中的精度变化为52。

'''+ '\n'.join(drows)+'''

撤回的三项是5月30日澳大利亚P-8A、6月9日加拿大CP-140、6月29日印度MH-60R。军情“X时起”与另外两源窗口的开始值不同。当前保守裁决不把它们纳入，仍保存“只是部分观测范围”的合理替代解释；未证明活动虚假，也没有由撤回数推算准确性改善。事实修复还扩展正文独有词表、后置数量和完整并行轨迹调查；候选增加不等于自动纳入。

所有八份第二节均由本轮代理在新冻结事实之后重新写作，未加载旧分析快照。以下是论证变化与保留理由；大致结论沿用并不表示事实沿用。v13与v12事实、主线、分析同时变化，不能当作纯分析受控实验。

|节点|相对v12实际第二节的变化或保留理由|
|---|---|
|5月10日|德国台风改为日本P-1。用同海域内5月6日侦察插入及7/8/10日反潜回归检验任务替代，减少地域与任务同时改变带来的解释混杂。|
|5月18日|巴登-符腾堡号改为加拿大CH-148。5月5日同日反潜与联合两活动可检验“全面替代”；18日参加数与5日同任务比较，不能推成整体出动减少。|
|5月30日|保留韩国P-8A的黄海重复主线；完整8日期9活动14架次，明确当日两个窗口3架次与机队增长之间的差别，以21日之后多次重复限制“偶发一条”解释。|
|6月9日|保留英国RC-135W，改以5月28日与6月9日同日两任务并存为关键对照；两类标签再现不推出新增能力，也不借一般能力补具体任务。|
|6月17日|保留澳方P-8A，但移除5月30日时间范围未消解记录，历史14活动改13活动；阶段与数量重算。两节点前海域任务与17日两个窗口比较，R07仅限制型号等同单一反潜任务。|
|6月29日|保留新加坡G550。比较初段东海侦察、16日警戒、22/29日黄海侦察回归；2架次仍在既有1—2范围内，不自动升级AEW改型。|
|7月9日|保留哈利法克斯级11日期完整历史，9日黄海警戒对“南海记录意味黄海终止”有反证意义；舰级身份不能支持两日单舰往返。|
|7月17日|保留戴高乐号13日期。早期7日南海模式作为基线，黄海两日作为单海域描述的反证，14/16/17日作为再现。R06多科目计划仅限制“一平台一科目”解释，不桥接2月至7月部署。|

每节点具体候选取舍、阶段边界、前提与缺证日期见audits/D/mainline_selection.json、analysis.md、analysis_snapshot.json、audit.json。六节点保留主线是重新比较后的结果，不是旧SELECT决定。

本轮查获分页空白并修复，DOCX总页数91改90。附图4长标签及全部XLSX填充范围已查看。当前无新平台评分、提交回执或逐字段真值；不声称提分、隐藏答案或上传成功。
'''
    (BASE/'事实差异与分析变化.md').write_text(text,encoding='utf8')
    readme='''# 赛题2 初赛 v13 完整八节点交付

2026-10-13执行用户指定v13入口，完成本地八节点事实重建、实际分析写作、全部正式48文件、证据审计、完整渲染修复、两次原始输入复现及独立物理解包。工程包最终CRC/逐成员哈希另见engineering_zip_verification.json，交付ZIP哈希见handoff_manifest.json。

正式提交包：赛题2_初赛_v13_八节点正式提交包.zip。ZIP根层直接八个日期目录，8份全章节DOCX、8份仅飞机/舰艇两表XLSX、32张规定名称PNG；代码、审计、PDF均不进入正式ZIP。完整工程包：赛题2_初赛_v13_完整工程包.zip。

'''+table+'''

各视图严格为5月1日至节点，最后视图78日实际解析7800篇TXT、8327正文原子候选、4249雷达分支候选、13019竞争关联；428原子未分配，254个正文独有词表发现，未识别文档数0不等于完美语义抽取。八节点当日共427雷达批次，纳入202、排除与域外保留逐项去向。完整最新视图1939项可信历史活动。

三源需能关联同一事件，关键字段至少两类支持且无未消解第三类冲突；关联分数仅组织配对。没有雷达优先，未知辅助留空。细地名不把近似中心圆当权威边界，6个持续并行异地分支不删为单点噪声，明确三项时间范围歧义保守排除。

本轮85条优先材料和53条分层样本去重合并132个事件，其中6个重叠；具体分层分母、字段值、原句、行号和竞争链均保存。审阅者是知晓历史答案的当前作者，未做独立盲审。全量程序解析与有限直接语义阅读分开见audit/final_reading_receipt.json。输出一致性、不变性与复现检查不能证明真实正确率或赛事得分。

已读取八套历史反馈，v4加权75.5445为已知最高对照，v9为74.1754，v12为73.7619；均为用户反馈展示均值计算，没有独立平台回执。没有取得本轮新评分，没有上传、外部付费模型调用或Git push。

## 文件导航

- official/D/：正式6文件。
- audits/D/frozen_ledger.json：原始视图重建事实，analysis_snapshot.json绑定其SHA256。
- audits/D/analysis.md、mainline_selection.json、audit.json：实际论证、全合格候选筛查、代表性比较、claim索引。
- evidence/daily/D/与audits/节点/input_manifest.json：逐日期候选、雷达全部行、分支/竞争、未匹配去向，以及各节点截止内读取清单。
- audit/priority_30_55_review.json、stratified_review.json：逐项原文审计；final_semantic_review.json为直接审阅范围与限制。
- audit/version_differences.json、事实差异与分析变化.md、八节点状态矩阵.md：正式历史对照与最终状态。
- qa/、word_render.json、excel_render.json、audit/final_visual_review.json：90页DOCX、32表格范围面板、32PNG；WPS 12.0 COM全文导出及pdfium真实渲染。全部页面联系图已查看，选择性放大原页，未声称每页均100%放大。
- inputs/和audit/archived_raw_input_manifest.json：8095份原始数据/模板/规则/采用资料，逐文件SHA256；其中比赛原始80日8080文件完整归档，7月18/19日未参与截止内运算。
- code/、requirements-lock.txt、environment.json、run-all.ps1：原始重建与交付工程。
- audit/final_raw_reproduction_comparison.json及run.log：修复分页后的最终复现；audit/physical_unpack_verification.json：正式ZIP48文件物理解包并重开。

## 一键原始输入复现

解压工程包后在v13目录执行，输出目录必须尚不存在：

```powershell
.\\run-all.ps1 -Output D:\\CW\\v13_raw_replay_new -SkipNativeRender
```

不加SkipNativeRender会调用本机Word.Application/Excel.Application COM（本机映射到WPS）完整导出并栅格化。其他机器可显式指定-Python、-Node和-NodeModules，Python依赖见requirements-lock.txt；需提供可用@oai/artifact-tool运行库和中文字体，运行时二进制、字体和node_modules未随工程包分发。路径、当前环境和渲染器实际版本见environment.json/渲染日志，不承诺无依赖直接运行。

入口强制COMPETITION_PROJECT_ROOT为工程包inputs，逐节点重读TXT/XLSX创建新事实台账，重建后才与本轮基准哈希比较。既有事实台账从不作为生成输入。事实哈希不符即停止分析回放，须重新审阅写作，不能盲用author_analysis.py的固定文字。

分析步骤是本轮已审阅analysis_snapshot的哈希绑定回放，未重新调用模型推理；author_analysis.py记录本轮实际文字与选择，不是自动推理服务。最终原始复现八事实哈希相同；8DOCX正文OOXML相同，8XLSX全部值/类型/数字格式相同，32PNG字节哈希相同。DOCX/XLSX容器元数据可变，不能称48文件字节全部一致。结构与数值验证为独立代码路径，不代表另一位独立语义审阅者。

## 资料与剩余限制

仅6月17日采用R07固定2023 ISR事例、7月17日采用R06固定2025年2月演习计划，两个原件页均实际查看、哈希与节点资格检查通过；只是解释边界，不补比赛第三源、不证明本赛段机制或部署。其他方法资料/旧网页摘要没有升级为正式事件实证。

空间包络仍是工程相容性检查，缺少权威细地名边界和测量误差模型；正文抽取未经过完整独立语言标注，别名与引用依赖仍有限。单点/开始范围、同型实体身份和缺证间隔保留审计问题。没有未处理的已确认可修复生成问题；下一轮应以具体原始补证或真实平台反馈展开，不无证据调阈值。
'''
    (BASE/'README.md').write_text(readme,encoding='utf8')
    (BASE/'progress.md').write_text('''# v13 最终执行记录

Goal本地完成条件：八节点原始重建、分析、48正式文件、审计、视觉修复、原始复现与两包交付。四项里程碑均已完成；平台评分单独待验证。

1. 规则/历史/模板定位完成；新增21版本目录程序索引及Git实际8DOCX恢复，真实阅读范围见audit/final_reading_receipt.json。
2. 全视图事实重算完成；202当日记录、1939最新历史事实、85优先条目和53分层样本审阅；原文反例和更正前标签保存。
3. 八份具体分析完成；八个冻结哈希绑定，完整历史/冲突/缺证日期及代表性候选取舍均保存。
4. 全48正式文件生成、90页全文及全部填充范围/32PNG视觉检查完成；发现7月9日空白页已修复。最终新目录原始事实重建+已审阅分析回放PASS，编号/行序/未来输入不变性PASS，正式ZIP物理解包重开PASS。

工程ZIP最后逐成员CRC/哈希验证记录写在包外，避免自身哈希循环；对应handoff_manifest.json。无评分、未上传，不推算得分。

'''+table+'\n\n历史成果只读保留，已有用户工作不改动。当前无待处理已确认可修复问题；剩余为原始缺证、身份/范围解释与外部评分未知，不无限生成变体。\n',encoding='utf8')
    print('FINAL REVIEW RECEIPTS AND DOCUMENTATION WRITTEN',len(matrix),'nodes')
if __name__=='__main__':main()
