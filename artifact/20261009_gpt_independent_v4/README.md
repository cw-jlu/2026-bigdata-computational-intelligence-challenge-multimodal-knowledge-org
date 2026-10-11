# 赛题2初赛：GPT 独立重做 v4

本目录保留独立代码、原始证据快照、抽查标注、验证记录和全部8个节点成果。原有 artifact、submission 和原始数据未被覆盖。只核查初始 GPT 版本 `20261008_001028_gpt-5.6solhigh`；未读取或复制 Claude 的代码与产物，也未借用其他 GPT 改进版实现。

## 交付入口

- `output/赛题2_初赛_八节点_提交.zip`：可提交压缩包，准确包含48个文件：8 DOCX、8 XLSX、32 PNG；没有PDF、代码或内部证据。
- `output/日报/{日期}/`：解压后的正式文件。
- `ANALYSIS.md`：实际数量、旧版覆盖差异、抽查修复与风险。
- `audit/VALIDATION_RECORD.md`：各类检查的依据和边界；版式核查见 `audit/VISUAL_REVIEW.md`。
- `工程交付_代码证据成果.zip`：工程交付包；不用于赛题提交。

## 运行环境与依赖

Python 3.13，依赖见 `requirements.txt`；新建虚拟环境实装的完整传递依赖见 `requirements.lock.txt`。Python 负责原始抽取、全局关联、逐字段核验、PNG、DOCX和校验。Node + `@oai/artifact-tool` 2.8.89负责XLSX创建与预览。具体解释器、模块入口、版本和哈希见 `audit/environment.json`。

本机 Node / 文档 Python 来自 Codex 附带的运行时。artifact-tool 不随工程包重分发；迁移机器须先具备该运行时，或设置 `ARTIFACT_TOOL_ENTRY` 为已有 `artifact_tool.mjs` 的绝对路径。不能仅安装 Python 依赖后假定 XLSX 可以生成。PNG需要微软雅黑或等效中文字体；Windows本机已具备。DOCX渲染核查另外使用打包的 `render_docx.py`、LibreOffice 25.8.6和Poppler；渲染并非生成提交ZIP的运行时依赖。

## 从仓库根目录复现（PowerShell）

以下命令使用新输出位置，不覆盖原始成果。`--reuse-evidence` 默认不启用，因此会重新读取原始三类来源，且只处理2025.5.1至2025.7.17。

```powershell
$v = 'artifact/20261009_gpt_independent_v4'
python -m venv "$v/.venv-reproduce"
# 此机器的全局pip配置有额外索引；以下两项只影响当前进程。
$env:PIP_CONFIG_FILE = (Resolve-Path "$v/audit/empty-pip.ini").Path
$env:PIP_EXTRA_INDEX_URL = ' '
& "$v/.venv-reproduce/Scripts/python.exe" -m pip install -r "$v/requirements.lock.txt"
$env:PYTHONIOENCODING = 'utf-8'
$docPython = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
$node = "$env:USERPROFILE/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
& "$v/.venv-reproduce/Scripts/python.exe" "$v/code/run.py" --input '赛题2-初赛/数据' --output "$v/reproduced/output" --doc-python $docPython --node $node
& "$v/.venv-reproduce/Scripts/python.exe" "$v/code/check_cases.py" --events "$v/reproduced/output/evidence/all_events.jsonl" --cases "$v/audit/gold_cases.json" --output "$v/reproduced/case_check.json"
& "$v/.venv-reproduce/Scripts/python.exe" "$v/code/compare_reproduction.py" --first "$v/output" --second "$v/reproduced/output" --record "$v/reproduced/comparison.json"
```

也可在依赖已安装后运行 `code/reproduce.ps1 -Python <解释器> -Node <Node解释器> -DocPython <文档解释器> -Output <新输出目录>`。所有脚本非交互、无需模型密钥，生成阶段模型调用为0。`run.py`子进程失败会立即停止；内容案例不通过时 `check_cases.py` 返回非零退出码。

本次已在新建 `.venv` 中从零安装依赖并全量重抽取，产物保存在 `audit/reproduction/`；最后一次主线调整后重新执行制表、制图、正文和校验。原始证据字节、主线、正文、明细及PNG解码像素全部一致，详见复现日志和 `audit/reproduction_comparison.json`。容器时间戳和PNG压缩流不保证字节相同。

DOCX视觉核查复现命令：

```powershell
python "$v/code/render_qa.py" --artifact $v --python $docPython --renderer "$env:USERPROFILE/.codex/plugins/cache/openai-primary-runtime/documents/26.1007.11041/skills/documents/render_docx.py" --soffice-bin 'D:/APPfile/Libreoffice25.8.6/program'
```

渲染PNG与QA PDF仅存于 `audit/docx_preview/`，不会进入提交包。`render_qa.py`仅清理当前新版本自己的旧页图，防止缩短文档留下过期页。

## 数据、关联与核验

`events.py`只从事实段抽取主体、具体型号、区域、任务、明确数量和时间。型号归一保留变型；同文多平台拆为不同原子事实。日期、型号之外还需具体区域或显式时段锚点。每来源原子事实只对应一个雷达事件；无时间且同型同日候选不可区分时保留歧义。文件序号和标题相似度不参与关联。

雷达按批次保留全部Excel行，对各字段所有不同值、同刻异地、跳变、坐标越界和跨日时间进行审计。发现冲突不取首行或多数行代替。全局匹配分数只用于候选竞争，不能使事件通过事实核验。两文本相互支持但雷达冲突时保留同事件候选，冲突仍否决正式纳入。

正式纳入须三类来源完成关联，且主体、型号、数量、任务、起止时段、具体区域均有至少两类来源支持；任何明确未消解冲突均否决。仅两源候选保留在证据中，不伪造缺少的第三源。未获两类来源支持的起飞基地、呼号、母港不写成核实字段；原雷达基地只在备注标为单源候选。雷达观测时间不等同于起降时间。

日报正文（除第二章）、明细与四图只用节点当日。第二章只回溯至节点日，从当日外方主体同型平台形成至少三个证据日期、两至三阶段的主线；在15日断点切断，以具体区域、任务和7日以上间隔形成阶段。均匀证据不按日期中点强行分期。跨日批号不同不能证明同一机体或舰体。

## 中间证据和独立检查

本次“人工判读”指代理直接阅读原始资料进行独立于生成代码的判断，不表示已经获得外部军事专家复核。


- `output/evidence/{日期}.events.jsonl`：所有雷达候选，完整Excel行号/字段/坐标，两个文本原子事实的路径、事实片段与SHA256，逐字段支持来源、冲突和纳入/排除/域外理由。
- 同目录 `documents / atoms / candidates / ambiguities / unmatched_atoms`：原文事实段、拆分、全体同型候选的支持/冲突理由、歧义和未使用文本。以事件ID、原子事实ID关联文件，序号只用于原始定位。
- `input_manifest.jsonl`：实际读取7878个原始文件的哈希；不包含晚于最后节点的数据。
- `output/payloads/`：当日正式集合、主线日期阶段、图表数据和精确XLSX行。正文D01等编号对应当日证据索引。
- `audit/gold_cases.json`：从原始三类来源人工判读46条应关联/不应关联案例及关键字段，不由生成结果反推；生成程序不读取该文件。
- `cases_before / cases_after / cases_holdout_before / cases_final`：初始失败、修正和追加案例记录；一条人工错误标注的原版本单独保留。
- `audit/metamorphic.json`：随机改文本名并打乱Excel行序、首节点不读取未来数据的稳定性检查。重复该脚本须使用新artifact目录，已有样本目录不自动删除。
- `output/validation.json`：严格文件集合、工作表/列顺序/类型、日界、去重、合计、主线、PNG和ZIP字节/CRC校验。**这些是结构和内部一致性检查，不能证明内容准确。**

工程包排除虚拟环境、缓存、重复复现成果和变形测试输入副本；保留正式成果、全部中间证据、原始抽查快照、代码、依赖、QA页面/工作表预览、日志与分析。`code/package_engineering.py`生成并验证工程包和文件清单。
