# 赛题2初赛：GPT 独立重做，20261009_gpt_accuracy_v2

本目录包含八个节点的答案、完整代码、原始证据定位、人工案例、运行日志和校验记录。仅参考仓库规则、原始数据及旧 GPT 实现；没有读取或复制 Claude 代码及产物。旧目录和仓库文件保持原样。

可提交文件是 `output/日报_gpt_accuracy_v2.zip`：48 个文件，8 DOCX、8 XLSX、32 PNG。`复现材料_gpt_accuracy_v2.zip` 包含本版本代码、证据、核查记录和输出，供工程复核，不能直接提交为日报答案。分析见 `ANALYSIS.md`，最终验证记录见 `AUDIT.md`。

## 从原始输入复现

以下命令在本版本目录执行。输入是仓库的 `赛题2-初赛/数据`，不是旧版中间结果。Python 3.12/3.13，推荐 Windows 和系统中文字体。

```powershell
python -m venv .venv
& ./.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python code/run.py --input ../../赛题2-初赛/数据 --output output --audit audit --docx-python .venv/Scripts/python.exe --portable-xlsx
```

便携模式只需 Python 依赖，不需要模型、API 密钥、GPU、Node 或 Office。该模式已经在现有Python环境和全新隔离虚拟环境中分别从原始数据运行全部八节点，记录在 `audit/portable_reproduction/full_run.json`、`audit/clean_reproduction/full_run.json`，结果逐单元格与主交付内容比较。全新环境完整依赖锁定文件在 `audit/clean_reproduction/requirements.lock.txt`。两种写表引擎的样式和二进制文件可以不同，事件与字段应一致。

本机主交付使用 Codex 自带 Python 3.12.14 写 DOCX，Node 和 `@oai/artifact-tool` 2.8.89 写 XLSX；解析、绘图和校验使用 Python 3.13.9。代码会自动发现本机缓存运行库；`code/node_modules` 是本机运行库联接，不打入复现包，也不是必须下载的模型依赖。

```powershell
python code/run.py --input ../../赛题2-初赛/数据 --output output --audit audit
```

默认重新读取原始 TXT/XLSX，计算输入 SHA256，依次执行提取、重构、绘图、DOCX、XLSX、独立结构与证据链校验，最后生成 ZIP。任一子进程或最终校验失败即返回非零退出码。`--reuse-verified-snapshot` 仅用于开发调试，最终复现未使用。日期节点和规则参数固定在 `code/fusion.py`；不存在根据文件编号配对或按匹配阈值认定真值的步骤。

原始目录结构：

```text
赛题2-初赛/数据/
  2025.5.1/
    开源军情/*.txt
    网上舆论/*.txt
    雷达信息表_2025.5.1.xlsx    # 飞机、舰船，各300行
  ...
```

原始数据80天，每天两类各50篇文本。只处理截至末节点7月17日的78天，即7800篇文本、46800条雷达记录；7月18—19日不参与答案。每个日报的词典和关联只使用当天材料，历史章节再使用截至该节点已核验记录。

本机 Ryzen 7 8845H，8核16线程，约16GB内存，Windows 11。无需 GPU。实测运行时间和库版本在 `audit/full_run.json`、`audit/portable_reproduction/full_run.json`；热文件缓存时约半分钟，首次或磁盘较慢时约1—3分钟。建议留出4GB可用内存、1GB磁盘用于全部证据和视觉核查。首次安装依赖需网络，推断和生成过程完全本地。

Linux/macOS 应替换虚拟环境激活方式，并安装可用中文字体。核心流水线没有 Office 依赖；本次视觉核查使用 Windows Word/Excel，其他平台版式不能仅凭本次结果保证。

## 内容与格式检查

```powershell
python code/audit_cases.py --out audit/cases_final.json
python code/check_holdout.py
python code/invariance_checks.py
python code/review_coverage.py
python code/validate.py --output output --snapshot audit/raw_snapshot.jsonl
```

`audit_cases.py` 检查28条原始材料人工标签；`check_holdout.py` 检查其余七节点14条标签。后者参与过修复，是跨节点回归集，不是未触碰的测试集。`review_coverage.py` 仅为旧 GPT 覆盖比较，需要仓库旧 GPT 的 `evidence.jsonl`；其余生成与验证无需旧实现。`invariance_checks.py` 验证8节点雷达/文本乱序及文件独立重编号不改事实，以及加入节点之后记录不改历史主线。

可选视觉核查，需要本机安装 Word、Excel，以及 `requirements-qa.txt`：

```powershell
python -m pip install -r requirements-qa.txt
& ./code/render_word.ps1 -Reports ./output/日报 -Output ./audit/docx_visual
python code/rasterize_qa.py audit/docx_visual
& ./code/render_excel.ps1 -Reports ./output/日报 -Output ./audit/xlsx_native
python code/raster_excel.py audit/xlsx_native
python code/write_delivery_docs.py
python code/package_reproduction.py
```

Office 以隐藏、只读方式打开文件并导出 QA PDF，关闭时不保存。PDF/页面图片仅在 `audit`，日报提交 ZIP 不含 PDF。文档技能的 `render_docx.py` 曾因缺少 LibreOffice 失败，已采用本机 Word 实际渲染并记录回退。检查包括每页空白/越界检测、人工查看页面拼图、Excel 原生日期显示和16个工作表预览。结构、证据链一致性与人工样本复核是三个不同层次，均不能替代官方准确性评分。

## 代码及证据入口

| 文件 | 用途 |
|---|---|
| `inspect_raw.py` | 直接读取文本、Excel及原始行号；输入哈希与原始快照 |
| `fusion.py` | 正文子事件、别名、任务/时间/区域、雷达分支和逐字段裁决 |
| `reconstruct.py` | 所有日期事件、候选、排除理由和节点事实包 |
| `charts.py` / `report.py` | 从事实包写4图、完整日报和规定列的数据矩阵 |
| `workbooks.mjs` / `workbooks_fallback.py` | 主交付表格／便携表格 |
| `validate.py` | 独立保存格式常量，重新读交付文件、原始定位、日期及ZIP |
| `holdout_review.py` | 仅从原始三类数据提取其他节点审阅材料，不读融合输出 |
| `audit_cases.py` / `check_holdout.py` | 独立人工标签回归检查，标签不由输出生成 |

`output/中间证据/events.jsonl` 保存每条候选的纳入/排除、备选文本对和未解决冲突；`candidate_links.jsonl` 保存每次同型平台候选关联的支持、冲突、缺失字段及文本正文行号；`radar_tracks.jsonl` 保留原始Excel路径、工作表、行号和坐标；`claims.jsonl` 保留逐平台正文片段和字段依据。完整文本和原始行在 `audit/raw_snapshot.jsonl`，每个原始文件的校验值在 `audit/input_manifest.json`。

`factpack_<日期>.json` 是该节点当日事实和截止该节点的历史主线。DOCX 的 D/H 证据编号和 XLSX 备注可定位到原始文件序号、雷达行号及事件 ID；这些序号只作为引用位置，不参与匹配。`chart_datasets.json` 保存4图原始绘图数据，便于独立重算。

`audit/independent_cases_initial.json` 和 `cases_first_run.json` 保留初始标签及首次失败；当前标签、全部原始行和修订说明在 `independent_cases.json`、`manual_case_review.md`、`cases_raw_records.json`。`ANALYSIS.md` 明确列出错误修复、标签修正、覆盖变化和剩余风险。

每个节点样例均已在 `output/日报/<日期>/` 中提供。可提交ZIP结构严格为 `日报/<日期>/`。辅助证据与测试日志不放入提交ZIP。
