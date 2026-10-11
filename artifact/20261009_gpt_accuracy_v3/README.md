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
