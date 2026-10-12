# 输入输出与复现约定

## 最小输入

截止日as_of（YYYY-MM-DD）；规则版本；用途historical_public_research或deidentified_demo；上游已核实事实摘要及原始定位；资料目录；期望输出范围。任务涉及本比赛时，事实台账的三源核验状态必须由上游提供，本Skill不做部队跟踪或雷达融合。

## 来源目录

source_catalog.json顶层为schema_version=1和sources数组。每个来源包含id、title、publisher、url、published_by、date_basis、role、independence_group、content_verified、version_status、locator。可加version_date、retrieved_at、rights、limits。

published_by是有证据的最迟公开日期或保守日期上界。若只知月份，可用该月末作上界并解释依据；完全不明则留空并排除。它不是为了通过检查而填写的任意日期。

version_status取fixed_edition、dated_publication、live_revised、translation_date_unverified或unknown。仅前两类通过此元数据资格检查；网页应另存所用版本并核验是否有后续改动。content_verified必须在真正读取相应段落后才可设为true。

role可为published_statistics、expert_report、official_policy、official_assessment、method或style。方法/写法材料不能作为外部实证增量。

## 输出

analysis.md：用户要求的正文，引用与判断对应。

audit.json：as_of、mode、used_source_ids、claims、missing_evidence、excluded_sources、rule_conflicts。其中claims按id、type、text、source_ids、locator、premise_claim_ids、limits记录；type为provided_fact、external_background、attributed_view、inference或method。提供简洁可检查的依据，不输出私人思维过程。

## 元数据检查命令

python scripts/audit_sources.py --catalog references/source_catalog.json --as-of 2025-05-10 --used E01 M01 --substantive E01 --output audit.json

返回码0为此项元数据检查通过，1为发现引用资格错误，2为输入/文件错误。该结果不是语义支持检查、事实核验或比赛评分。禁止把脚本PASS写成“所有事实已经验证”。

运行测试：python -m unittest discover -s scripts -p 'test_*.py' -v

环境：Python 3.10+，标准库即可；无需模型API密钥、网络或其他依赖。生成正文仍需要宿主模型；联网检索依赖宿主提供的浏览工具。