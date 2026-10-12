"""Build the reviewed source metadata; this is not a fact adjudication or score estimator."""
from pathlib import Path
import json, hashlib
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
NODES=['2025-05-10','2025-05-18','2025-05-30','2025-06-09','2025-06-17','2025-06-29','2025-07-09','2025-07-17']
def save(name,obj):
    p=BASE/name;p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
retrieval=json.loads((BASE/'retrieval_log.json').read_text(encoding='utf-8'))
downloaded={r['id']:r for r in retrieval if r['status']=='downloaded'}
sources=[]
def add(sid,title,publisher,url,date,role,status,locator,use,limit,novelty,**kw):
    row=dict(id=sid,title=title,publisher=publisher,url=url,published_by=date,role=role,version_status=status,read_locator=locator,use=use,limits=limit,novelty=novelty,accessed_on='2026-10-12',event_truth_source=False,**kw)
    record=downloaded.get(sid)
    row['local_original']=None if not record else {k:record[k] for k in ['path','sha256','bytes','url','text_path','text_sha256']}
    row['retrieval_status']='downloaded' if record else 'web_read_notes_only'
    row['eligible_nodes_by_date']=[n for n in NODES if date and date<=n]
    row['historical_content_approved']=status.startswith('fixed_edition')
    row['may_count_as_external_empirical_background']=role=='historical_official_background' and row['historical_content_approved']
    row['independence_group']={'R01':'ODNI_ICD203_2015','R02':'USG_CIA_Primer_2009','R03':'GAO_2019','R04':'UK_linkage_review_2021','R05':'UK_linkage_review_2021','R06':'Japan_MOD','R07':'Japan_MOD','R08':'Singapore_MINDEF','R09':'UK_RAF'}[sid]
    sources.append(row)

add('R01','ICD 203: Analytic Standards','ODNI','https://www.intelligence.gov/assets/documents/intelligence-community-directives/ICD_203.pdf','2015-01-02','method','fixed_edition_mirror','PDF第1、3—4页；D.6.e(2)—(8)','区分事实、假设、判断；比较解释并说明判断变化；避免只写限制而回避结论。','方法不是额外事件实证，也不是本赛题评分细则；概率措辞不等于事件核验置信度，不机械复制概率表。','旧M01来源补齐本地原文',date_basis='PDF封面02 January 2015；大学档案创建日期一致、入藏日期2019-02-21；馆藏另列Date Issued 2015-01-01，与封面不一致，采用封面日期。',mirror_note='官方两地址直接下载403；本地来自Georgetown档案。已将相关条款与官方web正文对照，不声称二进制相同。',read_scope='cover and selected analytic clauses, not whole institutional responsibilities')
add('R02','A Tradecraft Primer: Structured Analytic Techniques for Improving Intelligence Analysis','US Government / CIA CSI','https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf','2009-03-31','method','fixed_edition','PDF第1、11、14、18—19页；印刷页7、10、14—15','检查隐含假设和信息质量；比较证据对解释的区分能力。','不是比赛标准；不照搬示例计分或预测流程，不将多篇报道简单计票。','旧M02来源重新下载并定位',date_basis='封面March 2009，以月末为保守公开日期上界；文件名apr09不作为发布日期。',read_scope='selected method sections and cover; 45-page file not claimed fully read')
add('R03','Assessing Data Reliability (GAO-20-283G)','U.S. Government Accountability Office','https://www.gao.gov/assets/gao-20-283g.pdf','2019-12-16','method','fixed_edition_web_read','PDF第7、24—25页；印刷页4、21—22；第4节Tracing to and from Source Documents','从原始材料到候选查漏项，从台账到原始材料查误纳；将适用性与完整性、准确性分别评估。','PDF完整下载失败，只有在线核读记录；抽查不是全量保证；本赛题分数不等于该指南质量指标。','本轮新增方法来源',date_basis='GAO发布页明确Published/Publicly Released Dec 16, 2019；封面December 2019。',date_evidence_url='https://www.gao.gov/products/gao-20-283g',read_scope='selected pages through web tool; not full 72-page review',local_note='notes/R03.md')
add('R04','Quality assessment in data linkage','James Doidge, Peter Christen, Katie Harron / ONS and Government Analysis Function','https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/quality-assessment-in-data-linkage','2021-07-16','method','dated_web_current_snapshot','第2.1—2.5节、第3.1—3.3节及第5节','区分相似、算法关联和真实同一；检查错误合并/拆分及已关联和未关联记录。','当前HTML、图片资产未另存；无独立历史字节快照，严格节点引用暂不通过。仅作为工程方法参考；不要将关联precision/recall等同比赛准确性/完整性。','本轮新增完整方法章节',date_basis='章节标示Updated 16 July 2021；父发布页2020-08-25首发、2021-07-16更新。标示不证明每个字节未后改。',read_scope='selected sections; references not individually read')
add('R05','Longitudinal linkage of administrative data; design principles and the total error framework','Louisa Blackwell and Nicky Rogers / ONS','https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/longitudinal-linkage-of-administrative-data-design-principles-and-the-total-error-framework','2021-07-16','method','dated_web_current_snapshot','第2节；第4.1—4.2节；第5.2—5.4节；附录对象/事件及纵向误差定义','区分对象、事件、缺失和观察截止；检查未关联残余和事后更正造成的未来信息泄漏。','当前HTML历史字节版本未认证，严格节点引用暂不通过；仅工程方法参考。原文是行政统计，迁移到赛题为本项目建议，不是作者对赛题验证。','本轮新增完整方法章节',date_basis='章节与父发布页均标示2021-07-16更新；不是独立历史快照证明。',read_scope='selected sections and error taxonomy; no independent validation of cited administrative datasets')
add('R06','Japan-U.S.-France Multilateral Exercise (Pacific Steller), Announcement','Maritime Staff Office, Japan','https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf','2025-02-06','historical_official_background','fixed_edition','PDF第1页第2—5项及will conduct句','补齐B10完整原文，检查计划与实施、多种演练科目与单一任务的区别。','同一公告只有一个来源组；拟定2025-02-10至18日在菲律宾以东活动，不能证明计划已实施或比赛5—7月任何事件。','旧B10只有摘录，本轮补齐PDF',date_basis='PDF页首February 6, 2025与官方发布目录/路径一致。',read_scope='complete one-page PDF',relevant_nodes=['2025-07-17'])
add('R07','Joint ISR Conducted by Japan, the United States, and Australia','Ministry of Defense, Japan','https://www.mod.go.jp/en/images/1124a_usa_aus-j.pdf','2023-11-24','historical_official_background','fixed_edition','PDF第1页第1项及第3项','澳大利亚P-8A执行联合ISR的具体历史参照，约束把同型号活动全部解释为反潜的推断。','公告的意图和意义属于发布方表述；2023年事例不验证2025年比赛活动，更不能补当次任务或身份。','本轮新增固定版历史案例',date_basis='PDF页首November 24, 2023；原发布网页同日并直接链接该PDF。',date_evidence_url='https://www.mod.go.jp/en/article/2023/11/8dfa1a2eef63c347c71faf9d76d96c3dbbc7c936.html',period='2023-11-19至20；不作2025节点频次基线',read_scope='complete one-page PDF',relevant_nodes=['2025-06-17'])
add('R08','G550 - Airborne Early Warning, Fact Sheet','Singapore MINDEF / National Archives of Singapore','https://www.nas.gov.sg/archivesonline/data/pdfdoc/20070423988.pdf','2007-04-23','historical_official_background','fixed_edition_web_read','PDF第1页第1—3项','帮助核对G550-AEW具体改型及称谓，避免通用G550与特定改型自动等同。','本包仅链接和摘要；能力介绍不证明当次任务；原文的未来式采购安排不证明2025在场数量。','本轮新增固定版实体参考',date_basis='国家档案馆保存的PDF正文Date: 23 Apr 07。',read_scope='one-page text read online; full original not redistributed',local_note='notes/R08.md',relevant_nodes=['2025-06-29'])
add('R09','UK and US extend Rivet Joint support until 2035','Royal Air Force','https://www.raf.mod.uk/news/articles/uk-and-us-extend-rivet-joint-support-until-2035/','2021-10-26','entity_reference','dated_web_current_snapshot','2021-10-26文章第2段','RC-135W / Rivet Joint / Airseeker的别名线索，供回原文核对。','当前网页不能单凭旧日期认证历史文字版本；暂不纳入正式节点引用，也不能自动把RC-135全系列合并为W型。','本轮新增实体参考，版本待核',date_basis='网页署明26 Oct 2021，无独立历史快照。',read_scope='dated article relevant body read online; no full-text republication',local_note='notes/R09.md')
save('source_catalog.json',{'compiled_on':'2026-10-12','stage':'initial','nodes':NODES,'sources':sources,'not_a_truth_database':True,'platform_score_gain_verified':False})

notes={
'R03':'# R03 在线阅读记录\n\n原文：https://www.gao.gov/assets/gao-20-283g.pdf\n\n本轮已在线核读PDF第7、24—25页，PDF共72页；直接下载403，不存在本地完整PDF。第25页/印刷22页区分从原始文档查向数据库寻找遗漏，以及由数据库回查原始文档寻找错误纳入或录入。应用到赛题，需要同时检查纳入项和未进入候选集的原始记录。不是平台评分细则，也未完成本轮事件审计。\n',
'R08':'# R08 在线阅读记录\n\n原文：https://www.nas.gov.sg/archivesonline/data/pdfdoc/20070423988.pdf\n\n新加坡MINDEF于2007-04-23发布的1页G550-AEW资料，第1—3项说明这一具体改型及当时计划用途。已读正文，本包不重新分发全文。只能作为名称和功能背景；通用G550名称不足以确认AEW改型，计划采购数不能作为2025年出动数。\n',
'R09':'# R09 在线阅读记录\n\n原文：https://www.raf.mod.uk/news/articles/uk-and-us-extend-rivet-joint-support-until-2035/\n\nRAF页面标示2021-10-26，第2段将RC-135W Rivet Joint与Airseeker对应。已读相关正文，仅记录别名研究线索。当前网页历史文字版本未独立认证，暂不用于正式节点引用；不能把所有RC-135型号或同日所有同型号记录合并。\n'}
for sid,text in notes.items():
    (BASE/'notes').mkdir(exist_ok=True);(BASE/'notes'/f'{sid}.md').write_text(text,encoding='utf-8')

save('node_eligibility.json',{'note':'资格与贡献分开；方法不是外部实证，未认证网页只供工程研究。','nodes':[{ 'node':n,'fixed_version_method_sources':['R01','R02','R03'],'date_eligible_background_sources':['R06','R07','R08'],'provisional_method_only':['R04','R05'],'excluded_from_formal_citation_pending_history':['R09'],'event_validation_sources':[]} for n in NODES]})
save('reading_log.json',{'read_on':'2026-10-12','pdf_visual_pages':{'R01':[1,3,4],'R02':[1,11,14,18,19],'R06':[1],'R07':[1]},'rendered_but_not_claimed_read':['R02-p20.png'],'pdf_page_numbering':'1-based physical PDF pages; R02 printed page = PDF page - 4 in inspected sections','web_only_read':{'R03':['PDF 7','PDF 24-25'],'R08':['one-page PDF text'],'R09':['dated article relevant body']},'html_sections_read':{'R04':['2.1-2.5','3.1-3.3','5'],'R05':['2','4.1-4.2','5.2-5.4','selected appendix error definitions']},'originals_are_untrusted_reference_material':True,'limitations':['R01 official and mirror selected clauses compared; no byte equivalence claimed','GAO PDF locally unavailable','HTML extraction is not a complete offline rendering of images or interactive content','No independent blind review of event facts']})
save('review_schema.json',{'purpose':'建议的人工复核记录结构；未对任何事件自动裁决','required_fields':{'node_cutoff':'YYYY-MM-DD','candidate_id':'本地候选编号，不采用输入文件序号作事件身份','entity_identity_level':'class/model/named_platform/unique_vehicle','event_link_candidates':'包含未选竞争配对','source_links':'每类来源各自文件与段落/行号及同事件理由','atomic_fact':'一次只记录数量/时间/任务/区域等一个事实','per_source_values':'各源独立原文值、单位、否定/引用范围；missing与conflict分别标记','supporting_source_types':'不得由来源篇数代替来源类型','third_source_counterevidence':'明确反证与未能消解原因','decision':'纳入/排除/待决；外部资料不得充当第三源','delta_from_version':'新增/移除/字段修正/仅表述调整','review_status':'未复核/已读原文/复核存在分歧'},'prohibited_shortcuts':['把v4高分当真值','按版本多数投票','单源值复制为第二源支持','未知数量默认1','不同窗口架次直接同比','只抽查已纳入项就声称无漏项']})
save('excluded_or_deferred.json',{'items':[
 {'url':'https://www.navair.navy.mil/product/P-8A-Poseidon','decision':'deferred','reason':'当前产品页未核实节点前具体版本；用固定版R07作有限历史参照，不拿当前规格补赛内事实'},
 {'url':'https://www.defence.gov.au/news-events/releases/2026-05-27/fourteenth-p-8a-poseidon-aircraft-arrives-complete-australias-maritime-patrol-fleet','decision':'excluded','reason':'搜索结果发布日期2026-05-27晚于全部2025节点；未采用正文或数量'},
 {'url':'https://media.defense.gov/2024/Dec/12/2003610855/-1/-1/0/KOREA_18-34.PDF','decision':'not_used','reason':'PDF工具访问403；采购批准也不能作为2025节点出动数'},
 {'prior_source_ids':['D01','D02'],'decision':'not_added','reason':'现有SIPRI军费/军贸背景对当前八条具体主线缺乏直接区分作用，不为增加引用而重复下载'}]})
baseline=ROOT/'artifact/20261012_163714_initial_eight_nodes_v12'
rows=[]
for n in NODES:
    d='.'.join(str(int(x)) for x in n.split('-'))
    p=baseline/'audits'/d/'analysis.md'
    text=p.read_text(encoding='utf-8')
    rows.append({'node':n,'v12_analysis_path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'existing_question':text.splitlines()[2],'question_selection_redone':False,'facts_reverified_this_turn':False})
save('baseline_binding.json',{'version':'v12','purpose':'用于选择检索问题；不是重核事实','analyses':rows})
print('Built source catalog:',len(sources),'sources;',len([s for s in sources if s['local_original']]),'downloaded originals')
