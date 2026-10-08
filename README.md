# 多模态融合的知识组织与决策生成

2026 全国大数据与计算智能挑战赛参赛项目。

本项目面向连续多日的开源军情、网上舆论和雷达信息，构建可复现的多源信息融合与军事态势日报生成流程。

## 比赛任务

系统需要完成：

1. 解析和清洗 TXT 文本、XLSX 雷达记录；
2. 抽取并标准化国家、平台、批号、时间、区域、任务和数量等要素；
3. 关联不同来源，重建同一事件；
4. 识别文本冲突、主体—平台错配和雷达噪声，筛选可信事实；
5. 判断东海、南海、黄海活动方向并完成节点统计；
6. 追踪跨日活动主线，生成趋势分析；
7. 输出符合规范的 DOCX、XLSX 和 PNG 日报成果。

## 仓库结构

```text
.
├── docs/       # 赛题说明、数据口径、输出规范和复现要求
├── artifact/  # 不同模型的初赛实现与 Workflow 方案
├── 赛题2-初赛/数据/  # 初赛原始数据（已提交到 Git）
├── output/    # 仓库根目录的临时输出（不提交到 Git）
├── .env.example
└── README.md
```

## 环境配置

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

请根据本地数据集和模型服务修改 `.env`。不要提交真实密钥、数据集或生成结果。

## 运行方式

当前有两个可运行的规则基线，均以 `赛题2-初赛/数据` 为输入；初赛原始数据和各版本 `artifact/<版本>/output/` 内的日报、明细、图表、压缩包、中间结果均已提交到 Git，便于直接查看完整答案和复现。Claude 版本已有模块化抽取、轨迹解析、融合与报告代码，后续优先改进事件关联和事实核验。

```powershell
cd artifact/20261008_001929_claude-opus-5.5high
python run.py --input ../../赛题2-初赛/数据 --output output --stage prelim
```

方案与优先级见 [`artifact/20261008_005717_gpt-6_workflow全流程方案.md`](artifact/20261008_005717_gpt-6_workflow全流程方案.md)。

## 文档

详细说明见 [`docs/README.md`](docs/README.md)。

## 赛段分支

- `stage1`：初赛版本
- `stage2`：复赛版本
- `stage3`：决赛答辩版本
- `main`：公共文档和环境配置

每个阶段应保留可复现的代码、配置、依赖和最高成绩产物。
