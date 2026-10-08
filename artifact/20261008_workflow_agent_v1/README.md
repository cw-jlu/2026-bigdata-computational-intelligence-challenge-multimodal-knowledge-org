# Workflow + Agent 第一版实现

对应方案：`../20261008_workflow_agent方案_v1.md`。

这里的模型会在运行时读原文、检索证据、查询完整轨迹、提交事件并根据校验反馈修订。原有两个 artifact 是 coding agent 开发出的规则程序，本版保留运行时模型调查。

## 当前完成情况

- 无需 API 的无损预处理：TXT 多行字段、原文位置、XLSX 行号与格式、批号前导零、重复组、异常标签、轨迹与时空指标；按内容哈希保存原始文件副本。
- 本地 SQLite 证据库与分页工具：列记录、读原文、搜索、查轨迹、查已有事件、查基线词典、计算雷达时空关系。
- 有界工具调用循环：轮数/调用数/上下文限制、参数验证、错误反馈、调用记录和逐记录覆盖状态。
- 风险路线：逐事件风险评估与逐字段证据核验，再单独做当日候选的可信排序。
- 辩论路线：证成与质疑独立首轮、一次回应、裁决；角色模型可分别配置。
- 程序事实准入：三类来源、关键字段至少两类支持、引文存在、关键风险、冲突和异常处理、活动时间及三海边界。
- 写作 Agent：基于事实包选择跨日主线、生成规定章节，并提交带事件引用的正文。
- 确定性文件生成：DOCX、飞机/舰艇双表 XLSX、四张 PNG；检查章节、表头、数量总和、附件引用与文件可解析性。
- 检查点、事件修订记录、独立输出目录和配置/代码/输入指纹；失败或证据不足保持待审。

目前通过合成数据和脚本化模型响应验证工程流程，没有验证比赛原始数据，也没有获得比赛成绩。另已用用户提供的 DS 接口完成模型列表查询及一次真实工具调用往返测试；这仅验证连通性与工具协议，不代表事件分析效果。脚本化响应仅存在于测试文件，不作为生产可信判断的替代方案。

## 安装与预处理

在本目录执行（Python 3.10+）：

```powershell
python -m venv .venv
& .venv/Scripts/python.exe -m pip install -r requirements.txt
& .venv/Scripts/python.exe run.py --input "原始数据目录" --start 2025.5.1 --node 2025.5.10 --output output-risk --stage prepare
```

数据目录应包含 `2025.5.1/开源军情/*.txt`、`2025.5.1/网上舆论/*.txt`、`2025.5.1/*.xlsx`，雷达表名为“飞机”“舰船”。预处理不需要 API；缺失日期、缺少文件、解析失败写入 `quality.json`，不会以空输入冒充完整处理。

## 接入 DS / GPT / Claude

```powershell
Copy-Item config.example.json config.local.json
Copy-Item .env.example .env
```

在 `config.local.json` 中填写实际 `base_url` 和 `model`。`base_url` 为接口前缀：程序会追加 `/chat/completions` 或 `/messages`；前缀需要 `/v1` 时写入配置，不能填完整方法地址。示例没有假定用户的供应商、模型名或代理地址。

在本地 `.env` 中填写密钥，或提前设置环境变量。密钥仅从 `api_key_env` 指定的环境变量读取，不能写进 JSON 配置；`.env` 与 `config.local.json` 已忽略。

| 配置项 | 含义 |
|---|---|
| `protocol=openai` | OpenAI Chat Completions 兼容接口，可用于 GPT/DS 或对应网关 |
| `protocol=anthropic` | 原生 Claude Messages 接口 |
| `roles.analysis` | 主调查模型 |
| `roles.risk` | 风险评估和可信排序模型 |
| `roles.support/critic/judge` | 辩论各角色模型；回应复用 support |
| `roles.writer` | 主线分析和报告写作模型 |
| `extra_body` | 提供者允许的额外生成参数，例如 `max_tokens`、思考配置；不得覆盖消息和工具 |
| `preserve_reasoning_content` | DS 等需要保留此返回字段时开启，回传至后续工具轮次 |

默认角色配置只是占位映射，可改为任何已配置的 provider。Claude 经过 OpenAI 兼容网关时应选择 `openai` 协议。不同模型对参数、工具调用与 JSON Schema 的支持需要收到实际接口信息后联调。

接口实现参考：[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)、[Claude 工具结果协议](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)。2026-10-08 已验证 DS `deepseek-v4-pro` 在关闭思考的轻量测试中完成工具调用与结果回传；思考模式和完整调查流程尚待联调。实际配置保存在忽略的 `config.local.json`，密钥保存在忽略的 `.env`。

## 分阶段运行

```powershell
# 调查；开发时可加 --max-seeds 5 限制本次记录数
& .venv/Scripts/python.exe run.py --input "原始数据目录" --start 2025.5.1 --node 2025.5.10 --output output-risk --config config.local.json --env-file .env --stage analyze

# 可信判定
& .venv/Scripts/python.exe run.py --input "原始数据目录" --start 2025.5.1 --node 2025.5.10 --output output-risk --config config.local.json --env-file .env --stage review --trust-mode risk

# 报告
& .venv/Scripts/python.exe run.py --input "原始数据目录" --start 2025.5.1 --node 2025.5.10 --output output-risk --config config.local.json --env-file .env --stage report
```

一次运行全流程时用 `--stage all`。相同输入、代码和配置可在同一输出目录续跑；完成的 seed 调查与可信核验会复用。报告生成和相对排序目前会重新执行，保留每次调用轨迹。

若比较 `debate`，全过程添加 `--trust-mode debate`，使用独立的 `output-debate` 目录。切换模型、规则、代码、节点或判定路线需要新目录；程序会阻止混用旧检查点。两路线若需严格共用同一候选集，可先固定并审阅 `events.jsonl`；第一版 CLI 暂不支持跨实验导入候选，后续可加受指纹约束的导入入口。

初次接入建议先 `prepare`，再用小数量 seed 做 `analyze`，检查证据与工具轨迹后扩展。未完成覆盖、文件缺失或解析问题会阻止标准日报生成，不会偷偷回退成规则报告。

## 中间结果与状态

v1.1 默认将每次实验保存在仓库 `artifact/时间戳_workflow-agent-v1.1_模型名称_可信路线/`。时间戳使用 Asia/Shanghai，包含毫秒。省略 `--output` 自动创建新目录；续跑时显式指定原目录。默认优先使用本地 `config.local.json` 和 `.env`。

雷达调查默认按完整轨迹组调度，全部点仍留在证据库；每篇文本单独调查。`coverage.jsonl` 中 `reviewed_as_group` 区分轨迹组核查与逐条核查，组完成不表示每个异常点都被采信。节点日任务优先，之后调查历史日期。写作时历史主线候选和事件可分页查询，避免把全部历史塞进单次上下文。

除下面的业务结果外，每次实验保留 `code/` 源码快照、`run_config.json` 配置与指纹、`run_status.json` 执行状态、`invocations.jsonl` 续跑记录、`run.log` 阶段日志，以及 `trace_summary.json` 调用和用量汇总。

`traces.jsonl` 记录 task/角色/模型/独立 task_run_id、北京时间、完整提示词与工具定义、每轮消息、原生请求与响应（不含认证头）、工具调用 ID/参数/返回、HTTP 重试、请求 ID、耗时、usage、失败类型和预算耗尽。已知 API 密钥会在输出时脱敏。汇总对原生与规范化响应去重，保留截断响应返回的用量；超时且未返回 usage 的请求用量无法确认。

```text
output-risk/
  raw/<sha256>.txt或.xlsx   原始文件副本
  state.sqlite             证据、事件与检查点
  manifest.json            输入清单与指纹
  quality.json             文件问题、记录和轨迹异常
  run_config.json          代码与配置指纹，不含密钥
  coverage.jsonl           每条输入记录的处理结果
  events.jsonl             pending / trusted / excluded 事件和逐字段证据
  event_revisions.jsonl    事件修订内容
  reviews.jsonl            风险或辩论判定与依据
  traces.jsonl             完整带时间戳的模型/工具/重试 trace
  trace_summary.json       各角色用量、耗时、工具错误和任务失败汇总
  code/                    本次源码快照，不含环境文件和本地密钥
  run_status.json          最新一次启动/完成/失败状态
  invocations.jsonl        多次启动和续跑记录
  ranking/<日期>.json      相对可信排序，不改变绝对风险和准入
  report_packet.json       已准入事实、历史事件、程序统计
  narrative.json           主线、正文与事件引用
  summary.json             进度和未覆盖记录
  validation.json          交付结构检查及限制
  日报/                    DOCX / XLSX / 四张 PNG
```

`trusted` 表示模型证据判断通过当前程序门槛，不表示经过独立人工确认。结构、引文与数字检查无法证明语义正确，需要标注集评测。

候选无法调查完、模型预算耗尽、关键字段风险高、冲突/异常未解释时保持 `pending`；`excluded` 是带理由的排除，仍保留原始证据。排名第一、低风险标签、辩论一致均不能跳过程序准入。

## 测试

```powershell
& .venv/Scripts/python.exe -m unittest discover -s tests -v
```

测试不调用外部 API。包含多行原文和信源保留、前导零、未来数据隔离、输入变更防混用、引文伪造、复制证据、未解决冲突、预算限制、工具参数修复、两种可信路线、三家协议适配和合成端到端交付/续跑。

## 第一版限制与下一步

- 只有本地全文 OR 关键词召回，没有向量索引；未知别名由模型扩展检索。大数据下 SQLite JSON 扫描可能较慢，当前应先小样本测量。
- 来源独立性只做精确复制检查；相似转载和共同引用依靠模型核验，尚无独立转引图算法。
- 轨迹初始分组按单文件/工作表/批号；跳变与字段不一致标记保留，不自动删除或拆成确定事件。
- 基线词典复制自 Claude artifact 的 `bdci/lexicon.py`，版本标记为基线快照；未经独立核验，近似地理中心不能当真实观测或权威边界。
- 关键字段采用严格准入；数量和时间不足时会降低召回。架次/批次/艘次统计采用“一准入活动=一批，精确数量=该事件架/艘次”的初版口径，需原始数据与官方示例验证。
- 排序超过规模或上下文预算时标为未完成，保留绝对风险结果；不伪造全局排序。模型概率没有做统计校准。
- 跨日主线暂限定相同标准主体/平台，不能覆盖所有复杂编队变化。同型号不是同一个体；需样本验证语义关联。
- 事件显式拆分/废弃的专用工具尚未实现。可创建不同事件，但不能静默删除已有来源和冲突；需重新分配来源的事件先待审，保留修订记录。
- 第一张图是节点日逐小时侦巡活动区间覆盖（任务含侦察/巡逻/侦巡/监视/反潜），不是逐小时独立雷达观测。后三张是区域矩阵示意，尚未按官方地图样式对齐。
- 报告只做文件结构、引用和数字检查；没有自动语义审校，也没有 Word 页面的渲染与视觉验收，不能宣称比赛交付已经验收。
- DS 仅完成轻量真实工具测试，GPT/Claude 接口待提供；没有原始数据端到端效果。未来优先测事件错配、字段准确率、风险等级实际错误率、召回率、成本及调用稳定性，再调清洗和预算。


### v1.2 真实数据运行

显式 `finish_seed(pending)` 表示调查完成但证据不足；事件仍待审。预算/接口中断表示调查未完成，可续跑。首次完整节点使用500000字符上下文、80次工具调用、24轮；保留v1.1试跑用于对照。最新实验目录见 `latest_experiment.txt`；`process.json`记录启动进程，`run_status.json`记录运行状态，`run.log`记录进度，`traces.jsonl`记录逐次调用，`trace_summary.json`在本次运行结束时汇总。
