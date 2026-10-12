"""Finalize review records and human-readable delivery documentation."""
import hashlib,json
from pathlib import Path
V=Path(__file__).resolve().parents[1]
def read(p):return json.loads((V/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def md(name,s):(V/name).write_text(s.strip()+'\n',encoding='utf-8')

def main():
    comparison=read('audit/v2_comparison.json');word=read('audit/docx_visual_release/render_log.json');excel=read('audit/xlsx_native/native_excel_log.json')
    word_raster=read('audit/docx_visual_release/raster_checks.json');excel_raster=read('audit/xlsx_native/raster_checks.json')
    zoom=['audit/docx_visual_release/2025.6.17/report_page_02.png','audit/docx_visual_release/2025.5.30/report_page_09.png','audit/docx_visual_release/2025.5.10/report_page_05.png','audit/docx_visual_release/2025.7.17/report_page_02.png','audit/xlsx_native/2025.5.10_飞机_page_01.png','audit/xlsx_native/2025.6.17_飞机_page_01.png','audit/xlsx_native/2025.5.18_舰艇_page_01.png','audit/xlsx_native/2025.7.17_舰艇_page_01.png']
    contacts=sorted((V/'audit/docx_visual_release').rglob('*contact*.png'))+sorted((V/'audit/xlsx_native').glob('*contact*.png'))
    pngs=sorted((V/'output/日报').rglob('*.png'))
    manual={'reviewer':'Codex，使用view_image人工视觉检查；不是OCR结果替代人工检查','scope':{'docx_files':8,'docx_pages':sum(r['pages'] for r in word),'docx_review':'全部页联系图逐页检查，另查看所列4页完整放大图；不声称逐字校对69页每个像素','xlsx_files':8,'xlsx_used_ranges':16,'xlsx_pdf_pages':sum(r['pages'] for r in excel_raster),'xlsx_data_rows':sum(r['row_count']-1 for r in excel),'xlsx_review':'全部16个完整范围联系图（含分页尾行）检查，另查看所列4页完整放大图；读取所有单元格另由独立结构校验执行','png_files':len(pngs),'png_review':'32张独立原图逐张查看日期、文字、图例、数量与空组说明'},
        'reviewed_contacts':[{'file':p.relative_to(V).as_posix(),'sha256':sha(p)} for p in contacts],
        'reviewed_original_figures':[{'file':p.relative_to(V).as_posix(),'sha256':sha(p)} for p in pngs],
        'reviewed_full_pages':[{'file':p,'sha256':sha(V/p)} for p in zoom],
        'findings_and_fixes':[
            {'issue':'候选主线比较表可能未展示实际被选中的候选','fix':'实际选中候选固定置首，随后展示4个竞争候选；阶段表仍保留全部历史记录','status':'已修复'},
            {'issue':'初版图例/区域/平台标签偏小，密集图易读性不足','fix':'图宽8.4英寸，增大标签和图例字号，按记录数增加高度；密集其他国家图独占一页，独立PNG保持1512像素宽','status':'已修复；19条记录的DOCX嵌图文字仍较紧凑，可打开附图原PNG'},
            {'issue':'跨日矩阵与证据索引在页尾出现少量孤行，强制分页试验又导致上页段落孤立','fix':'段落不拆分，小矩阵与完整当日索引保持整块，取消强制索引分页，调整段后距与行距；保存各轮PDF/PNG供对照','status':'已修复；最终69页'},
            {'issue':'Word默认表格宽度、彩色标题与重复表头不适合提交报告','fix':'A4黑色标题、明确列宽、淡表格线、跨页重复表头及行不拆分','status':'已修复'},
            {'issue':'Excel长备注可能被固定行高截断','fix':'实际Excel只读导出全部保存范围，并以AutoFit测量后恢复原高不保存；213行最大所需45pt，小于交付82.1pt','status':'未发现截断'},
            {'issue':'部分Excel打印导出第二页只有尾行','fix':'QA文件保留并检查所有尾页，未裁掉任何数据；XLSX本身完整213行','status':'完整性通过；打印分页留白仍存在'},
            {'issue':'长Excel行号列表在Word窄列自动折行，少数数字跨行','fix':'未删除定位数字；原始完整列表与单行JSON另存中间证据','status':'无截断；折行是剩余可读性限制'},
        ],
        'final_result':'最终联系图和所列放大页未见文字出页、图例遮挡、正文附图漏引或末行丢失。布局自动检查只支持上述检查，不替代事实正确性。',
        'rendered_files_match_delivery':all(sha(Path(r['docx']))==r['docx_sha256'] for r in word) and all(sha(V/'output/日报'/r['date']/(r['date']+'机舰活动明细.xlsx'))==r['xlsx_sha256'] for r in excel),
        'automated_raster':{'word_outside_page':sum(len(c['outside_page']) for r in word_raster for c in r['checks']),'excel_outside_page':sum(len(c['outside_page']) for r in excel_raster for c in r['checks']),'blank_pages':sum(c['blank'] for r in word_raster+excel_raster for c in r['checks']),'xlsx_rows_may_clip':sum(c['may_clip'] for r in excel for c in r['row_height_checks'])}}
    (V/'audit/manual_visual_review.json').write_text(json.dumps(manual,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=['|节点|v2纳入→v3|v3排除候选|架次|艘次|新主线|历史日期/阶段|报告页数|','|---|---:|---:|---:|---:|---|---:|---:|']
    pages={r['date']:r['pages'] for r in word}
    for r in comparison:
        t=r['mainline']['v3'];rows.append(f"|{r['date']}|{r['v2_included']}→{r['v3_included']}|{r['v3_excluded']}|{r['v3_air_quantity']}|{r['v3_ship_quantity']}|{t['country']} {t['platform']}|{len(t['dates'])}/{len(t['phases'])}|{pages[r['date']]}|")
    nodetable='\n'.join(rows)
    md('README.md',r'''
# GPT accuracy v3：赛题2初赛 initial 八节点

本目录是新的完整交付版本。已完成8份DOCX、8份XLSX、32张PNG、可提交ZIP，以及源码、原始证据快照、人工案例、对照与视觉记录。旧GPT、v2和原提交包保持原样；不读取或复制Claude版本，也不使用其他正在运行版本的中间结果。

交付入口：

- `output/日报_gpt_accuracy_v3.zip`：正式提交包，根目录`日报/`，48个规范文件，无QA PDF。
- `工程交付_gpt_accuracy_v3.zip`：源代码、配置、依赖、证据、案例、全部正式产物和最终QA记录；详见`audit/engineering_manifest.json`。
- `output/日报/`：八节点可直接查看文件。
- `ANALYSIS.md`：原始证据问题、修复、主线对照与限制。
- `AUDIT.md`：结构、事实、视觉、复现检查分开报告。
- `VISUAL_REVIEW.md`：实际渲染范围、问题和修复。
- `audit/problem_table.md`及JSON：逐案例原始定位、依据、v2行为、修复与结果。

基线为`artifact/20261009_gpt_accuracy_v2`。用户给定评测：完整性84.4760、准确性64.8389、格式76.5391、分析52.5000，展示总分69.0354；旧GPT44.0519。本版本没有下一轮官方结果，不预测得分，不编造扣分位置，不把既有总分增量归因于提示词。

## 干净环境复现

从本版本目录执行，Python 3.13；已验证Windows 11、Python 3.13.9。`--input`应指向完整原始`赛题2-初赛/数据`目录。字体使用本机微软雅黑/宋体/黑体；字体和Office版本不同可能改变排版和PNG字节。正式输出使用artifact-tool；以下命令使用无需Node的openpyxl可移植路径，所有单元格、事件、报告文字与PNG已比较一致。

```powershell
py -3.13 -m venv .venv-repro
& ./.venv-repro/Scripts/python.exe -m pip --isolated install --index-url https://pypi.org/simple -r audit/requirements.lock.txt
& ./.venv-repro/Scripts/python.exe -X utf8 code/run.py --input ../../赛题2-初赛/数据 --output audit/reproduce/output --audit audit/reproduce --docx-python .venv-repro/Scripts/python.exe --portable-xlsx
& ./.venv-repro/Scripts/python.exe -X utf8 code/check_new_cases.py --split development --events audit/reproduce/output/中间证据/events.jsonl --out audit/reproduce/development_results.json
& ./.venv-repro/Scripts/python.exe -X utf8 code/check_new_cases.py --split reserved --events audit/reproduce/output/中间证据/events.jsonl --out audit/reproduce/reserved_results.json
& ./.venv-repro/Scripts/python.exe -X utf8 code/validate.py --output audit/reproduce/output --snapshot audit/reproduce/raw_snapshot.jsonl
```

默认运行重新读取原始7800个TXT和46800条雷达记录（5.1—7.17共78日），不默认复用快照；原数据还有7.18—7.19，截断于最后节点。节点正文、明细、统计、图表仅当日；第二节跨日历史截止该节点。运行不调用推理API，生成器为确定性规则，作者为Codex GPT-6，API快照不可取得。实际基线冻结、环境版本和参数见`audit/baseline_freeze.json`、`config/experiment_final.json`、`audit/repro_final/full_run.json`。

既有42例都是开发回归：`audit_cases.py`的28例和`check_holdout.py`的14例（旧文件仍名holdout，不能当本轮独立测试）。新26例开发及24例预留先从完整原始三源录入预期；新10条关系断言复用4个开发案例，不增加样本分母。请只执行检查，不重新运行`freeze_cases.py`覆盖冻结标签。

原生版式QA需要本地Microsoft Word/Excel，脚本隐藏只读打开、不保存原文件：

```powershell
pwsh -File code/render_word.ps1 -Reports audit/reproduce/output/日报 -Output audit/reproduce/docx_visual
pwsh -File code/render_excel_full.ps1 -Reports audit/reproduce/output/日报 -Output audit/reproduce/xlsx_native
& ./.venv-repro/Scripts/python.exe -X utf8 code/render_qa.py audit/reproduce/docx_visual
& ./.venv-repro/Scripts/python.exe -X utf8 code/render_qa.py audit/reproduce/xlsx_native
```

`requirements-qa.txt`包含PyMuPDF；完整锁文件已包含QA环境。本机技能提供的LibreOffice renderer尝试失败（未安装LibreOffice），已用实际Word和Excel原生导出及PDF栅格检查完成，失败日志保留。原始文件不打包复制一整套；工程包提供处理范围内完整原始快照和输入哈希，重新从原TXT/XLSX读取需仓库原数据。

## 证据与追溯

`output/中间证据/`保存全部78日事件（含排除）、逐字段支持/冲突/未知、原始雷达全部点、全部解析文本子事件、所有候选关联、竞争证据分配、未分配证据、八节点提报包和图表/表格数据。事件ID只用于定位；来源序号、整篇关键词、标题、评分均不是事实依据。排除候选不能直接进入可信日报；未知辅助字段留空并注明未核实。

`code/fusion_event_stage.py`保存事件核验阶段；`audit/event_verification_stage.json`与`audit/ablation_analysis.json`区分事件核验、固定事实下主线变化和版式变化。所有阶段均没有官方评分；不能据此证明提示词独立收益。

完整清洁重跑在`audit/repro_final/`；最终工程包省略旧轮次重复渲染和重复生成数据、损坏探针副本与本机运行时目录，但原目录保留所有实验。工程包内保存最终QA、日志、比较、原始标签和标签更正。新运行请使用新的输出路径。
''')
    md('ANALYSIS.md',f'''
# 原始核验、变化与分析

本轮先读取README、docs/01—07、原始结构、旧GPT及v2允许的代码/证据/分析，再冻结对照与参数。v2得分只有整体四项及用户给定总分，没有逐节点或逐事件扣分明细。以下“错误”指原始证据可确认的工程问题，不等于官方扣分原因。

## 诊断范围与实际错误

八节点v2纳入/排除各抽普通飞机、舰船并补易错边界，35份完整原始审阅包保存于`audit/diagnostic_raw_bundles.json`和`diagnostic_raw_review.txt`。分层为纳入飞机11、纳入舰船8、排除飞机8、排除舰船8；覆盖八节点。26个有人工预期的开发事件问题表另列原始TXT与Excel行号、关键依据、当前行为和修复结果。两者有重叠，不能相加成为独立样本数。

确认的漏报是2025.6.17加拿大CF-188早段：`AIR-EE80F16DB64B1B`，08:03—10:28、温州外海，完整雷达1架；军情001正文支持该时间与细区，舆论030支持东海联合巡逻1架。另一批`AIR-17B15F5CA30ADA`是17:42—19:12东海油气田：军情015为1架、舆论046为2架，属于无法消解的同活动明确数量冲突。v2为晚段另选宽区域030，从而绕过046的反证，随后以030不能重复分配排除了早段和晚段。本轮先保留晚段明确冲突并排除它，再将030分配早段。早段获得三类来源，关键事实至少两类支持；细区不是用粗东海包络推出来的。

该错误不是“提高分数阈值”或“减少数量”解决：80km分支、2400km/h跳点、5km同时刻、1分钟端点容差均沿用v2，已纳入212个事件全部保留，只补1个有证据事件，最终213个。无新增无依据字段、无已纳入关键字段更改、无删除。全部候选仍保存，八节点433个候选中213纳入、220排除。原冻结配置误写时间容差5分钟，实际代码始终1分钟；原记录保留，`experiment_final.json`明确更正，不能说实际改过阈值。

其他抽样覆盖：同日同型异时异地、主体错配、同核心海域不同具体区域、P-1/SH-60K及P-8A/RC-135W编队子证据、数量不一致、任务文本冲突、同批飞机分支、舰船持续区域冲突、未知起降/基地/呼号/母港。问题表明确区分已确认错误与原判定正确的边界，不把所有检查条目宣称为v2错误。

## 按事件与字段组织事实

完整平台别名归一保留型号边界，型号与具名舰体分开。明确新平台、新区域、新时段的子事件拆分；共享编队或指代不盲拆。同一子事件只分配兼容活动。国家、平台、时间、具体区域、任务、数量、轨迹以及辅助字段均分别存支持、冲突、未知和原始定位。竞争候选与配对、上下文反证、排除原因及证据占用可追溯；标题只警告不证明事实，相关评分只排序，不作为事实依据。

可信事件遵守三类来源核验：关键事实至少两类支持，第三类明确同事件冲突不能多数覆盖。仅两源事件仍是候选而非可信日报。军情无明确数量时，其数量保持未知；不能把另一来源的数量写回该篇文本。平台用途不能证明当次任务，具体任务缺双源时日报写“任务未核实”，不因此自动否定其他已核实活动。

雷达按时间排列保留全部点位、原始Excel行号，检查非法时刻、越界坐标、同时刻差异、速度跳点与分支；不以中位点或多数删除连续冲突。八节点433条候选轨迹中22条边界轨迹另存`trajectory_review.json`。80km等是工程筛查假设，不是已校准军用平台性能限值；粗海域不能证明细区。部分舰船孤立标签需其余完整同批字段和双类文本共同支持才能解释为噪声；持续多区域和飞机连续分支保持冲突。没有宣称建立普适、已独立验证的飞机去噪算法。

## 八节点对照与主线

{nodetable}

当日事件和历史线索的JSON对照见`audit/v2_comparison.json`，保留所有候选字段差异及新增/移除ID，不只比较最后数量。架次和艘次是各事件数量之和，不能与事件起数混用；当日曲线明确为按开始时段统计的侦巡事件量，不表示实时在场数量。

主线先比较与当前已核实重点有关的国家—完整平台—核心方向候选，优先当前重点、具体区域与任务一致性，再检查相邻活动间隔，日期数仅最后的平局项。截止当日、至少3个日期，>=15日断档限制线索；候选、选择理由和阶段边界均保存。八节点最后都是两阶段，没有因达到3日期硬切三段。区域/任务类别变化与8—14日间隔能作观察边界；三段要求更强的改进和每段至少2日期。本轮没有样本使用三段，不能说三段已独立验证。

每阶段写实际区域、任务分布及最大间隔，说明混合记录和单日阶段不能证明持续驻留。解释顺序是已核实记录→可观察的具体区域/任务变化→与数据一致的有限解释→平台轮换、采集覆盖、报道差异等其他可能。当前节点任务使用当日实际任务，不能用阶段众数代替。型号反复出现不证明同一实体跨日转移，不把日期缺口写成撤离，也不推定兵力增加或确定战略意图。

## 改动效果与限制

事件核验阶段先运行，确定早段补足与212保留。随后在固定v3事件集合上比较旧主线规则和新主线规则，`ablation_analysis.json`逐节点证明当日事件ID相同，仅选择/分段及分析改变。最后做表格、图中文字和分页迭代，保留多轮渲染记录。没有事件/分析/格式单项官方分数，也没有随机提示词对照；不能从旧GPT44.0519到v2展示总分69.0354的全部增量或本轮内容变化推断提示词因果收益。

剩余风险：复杂省略、开放型号/别名、宽区域无时间文本、同批分支的真实含义仍需人工全量审阅；工程轨迹容差不是经独立噪点标签校准的标准。人工目的抽样与同日同原文重叠限制外推。报告密集附图嵌入后文字较紧凑，完整PNG供单独查看；行号长列表有自动折行。船舶源数据没有坐标，活动示意采用区域与时间，未捏造经纬度。公开检索未取得官方成品样例，只按docs/04核验。没有新官方结果，不宣称得分提高。
''')
    md('AUDIT.md',f'''
# 分开报告的验证记录

## 结构与数据一致性

`output/validation.json`八节点通过；`deliverable_manifest.json`记录48个文件大小和SHA256。独立校验器使用字面日期列表、文件名、章节与列序，读取实际DOCX/XLSX/PNG和ZIP，核对原生日期、工作表、数值及节点边界；正文统计、侦巡曲线类别/数量、区域图全部记录字段从事件重算。每节点仅两工作表，飞机16列、舰艇11列，ZIP无PDF。正文明确引用附图1—4。节点外数据仅第二节截至当日历史，全部主线>=3日期。

它也复核原文片段、原始Excel行定位、双源字段支持和子证据唯一性，但其中表格逐格一致性仍使用生成出的行表，不能当作独立真值。原始案例核查另列。六份故意损坏副本全被拒绝（错误列名、当日日期、曲线数量、区域图字段、未来历史、漏引附图），见`validator_probe_results.json`；不把探针作为官方格式合格保证。

## 事实与关系样本

|样本组|分母|通过|用途与限制|
|---|---:|---:|---|
|既有开发42例|42|42|原28关系/字段案例+旧14案例；本轮全部开发|
|新开发事件|26|26|13纳入、13排除；修复、回归用|
|新预留事件|24|24|16纳入、8排除；冻结后检查，未用于事实修复|
|补充开发关系/字段断言|10|10|5应关联、5不应关联；复用4个新开发事件，不增加独立样本数|
|编号/输入顺序/未来截止不变性|16|16|工程属性检查，不是人工事实真值|

原始全文、全部雷达行、人工预期及依据均在冻结案例文件；checker不导入fusion或生成器来算期望。先录原始预期再读取对应候选结果。新24例为保留不用于修复的核查集，但与开发有同日/原文重叠，目的抽样而非IID；不外推全量正确率。35份诊断审阅材料与开发/预留相交，不能相加。

标签更正分别保存：新开发初稿一处虚拟定位在首次评估前被发现，改为真实`AIR-D259B796A74070`，原初稿保留；补充开发关系断言三条将最终事件数量误作本篇文本数量，完整原文表明应为未知，原标签、首次结果及更正保留在`new_relation_*initial.json`与`new_relation_label_corrections.json`。同时核查器首次误用event_id匹配track_id已修复。补充断言生成器未变；不将标签或检查器修正计作算法收益。旧42标签未更改。

## 实际版式

Microsoft Word实际只读渲染8份报告共69页，Excel完整16个UsedRange共22页、213行数据；页图及完整文本边界检查均保存。人工查看全部页联系图、32张原图，另放大4个报告页和4个Excel页，范围和SHA256见`manual_visual_review.json`，不能把联系图审阅说成逐字全页校对。最终未发现出页文字、空白页、替换字形、备注行高截断或末行丢失；长行号自动折行、打印末页留白和密集DOCX嵌图文字紧凑的限制明确保留。已渲染文件哈希与最终交付文件逐个比对。

文档技能提供的LibreOffice renderer失败后使用本机原生Office，并记录失败日志。当前环境未提供load_workspace_dependencies工具、artifact marker脚本也未找到；使用本机缓存权威artifact-tool包和文档渲染脚本。XLSX先用artifact-tool生成/全范围预览，再独立Excel原生渲染，不以生成器预览自证。

## 冻结、复现与旧文件保护

`baseline_freeze.json`冻结497个允许对照/规范文件哈希，`baseline_preservation.json`最终复核全未变；无Claude产物读取、无其他运行版本中间数据使用。`config/experiment_final.json`保存参数、更正说明与最后源文件哈希；没有推理API模型参数。完整依赖锁及原始输入清单保留。

从新建venv、原始三源完整重读运行全部八节点，`audit/repro_final/full_run.json`记录环境、依赖、命令和耗时；`clean_reproduction_comparison.json`比较9个中间结果、原始快照、8份DOCX全部文本、8份XLSX全部单元格、32张PNG，共58项全部相同。主交付与纯Python路径Excel引擎不同，ZIP/DOCX容器元数据和Excel样式不要求二进制相等，不能宣称跨操作系统排版字节可复现。

`audit/engineering_manifest.json`及包校验记录可检查工程ZIP；提交ZIP是48文件，工程ZIP才包含QA PDF和证据。没有官方重新评分；结构、抽样事实、实际视觉和复现各自证明范围不同，不相互替代。
''')
    md('VISUAL_REVIEW.md','''
# 实际版式检查

最终检查的是主交付文件，DOCX使用Microsoft Word ExportAsFixedFormat、XLSX使用Microsoft Excel全部已保存UsedRange导出；两者隐藏只读、不保存。`audit/docx_visual_release/`和`audit/xlsx_native/`包含PDF、逐页PNG、联系图、文本边界、源文件哈希及引擎日志。QA PDF不进入正式提交ZIP。

Word八节点页数：9、9、9、8、9、8、8、9，共69页。16个工作表完整范围22页，共213条数据，AutoFit需求最高45pt，交付82.1pt，无测得行高截断。独立解析所有原生日期、单元格、日期范围及正文引用；所有页自动检查出页文本、空页和替换字形，均为0。

人工检查全部报告页联系图和全部表格范围联系图（包括只有尾行的第2页），逐張查看32张独立PNG的图中文字和图例；另查看6.17/7.17分析与历史表、5.10当日索引、5.30密集其他国家图等4个原页以及4个长备注Excel原页。明确只放大这些代表页，不把自动边界检查等同于69页逐字校对。具体查看路径和SHA256在`manual_visual_review.json`。

修复记录：

|观察到的问题|修改|最终情况|
|---|---|---|
|主线比较表未保证展示所选候选|选中候选置首，再列4项竞争候选|选择可复核|
|图例、平台/细区标签太小|增加图宽、字号和随条目增加的图高|32图无图例遮挡；密集嵌图仍需原PNG放大|
|历史表、索引少量尾行被拆至下一页|小矩阵/完整索引保持整块，段落不拆分，取消强制索引分页|最终无2行孤表；69页|
|默认标题色及表格宽度|黑色标题、A4固定列宽、重复表头、淡边框|表格无出页|
|备注可能被固定高度截断|Excel实际AutoFit测量后恢复不保存|213行均足够，末行完整|
|Excel完整范围导出产生尾页留白|保留所有页并检查|有打印分页留白，无数据丢失|

迭代目录`docx_visual`、`docx_visual_final`、`docx_visual_delivery`、`docx_visual_checked`保存早期布局，最终以`docx_visual_release`为准。旧轮次仍在新版本目录，不覆盖既有提交。长雷达行号窄列折行存在，个别数字跨行；完整定位在JSON和原始证据里，未删除数字。无船舶真实坐标，示意图明确用区域/时间表示；图片不是伪造地理航迹。

官方成品样例：公开官网与赛题入口检索未取得可下载DOCX/XLSX，检索范围和页面记录见`official_sample_search.json`；不声称其他位置不存在。按仓库docs/04逐项核验。没有官方格式分结果，不能把本次视觉通过换算为官方分数。
''')
    print('Delivery documentation and visual record written; rendered-file matches:',manual['rendered_files_match_delivery'])

if __name__=='__main__':main()
