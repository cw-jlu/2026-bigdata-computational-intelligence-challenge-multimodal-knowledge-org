# 历史版本比较记录

本目录保存2026-10-12对全部可查历史版本的补充比较。结论见[历史全部版本与v8对照](../../docs/09-历史全部版本与v8对照.md)：已评测六版中v4总分75.5445最高，本次v8为71.1521，低4.3924。全部总分由用户反馈归档的四项展示均值计算，未取得未舍入官方总分或逐节点细项。

检查范围：14项版本/实验状态，57份实际DOCX第二节，28个关键代码文件的函数与差异，六版全部八节点当日活动计数，v4/v8八节点当日集合及主线的逐条差异。没有重新核验所有历史事件，也没有重新渲染历史文件，不新增视觉PASS。workflow试跑、未完成目录与v6单节点成果不参加八节点评分排名。

数据与定位：

- `scores.json`：六版四项、Decimal总分、v8相对每版的差值和权重贡献。
- `version_inventory.json`：14项范围和成绩可用状态。
- `actual_report_section2.json`、`report_text_profiles.json`：57份实际第二节、文本哈希、段落统计；不替代正式DOCX。
- `v4_v8_fact_and_mainline_comparison.json`：175条保留、30条新增、55次区域改变、零移除；事件/字段/旧排除理由/证据定位。
- `review_details.json`：六版当日计数、工作流真实试跑状态、八节点主线和格式对齐版对照。
- `code_excerpts.json`、`code_comparison_summary.json`及`.diff`：实际函数和源文件行号；共同弱点与版本差异分开。
- `comparison_read_manifest.json`：实际读取的文件哈希与读取方式。程序全文读取不等于代理逐字人工核验，语义判断限于正文讨论的片段。
- `sources/docs05_before_comparison.md`：更新评分总表前的来源快照，支持初始两版的原表格定位。

可在具有相应历史目录的原项目中使用bundled Python 3.12依次执行：

```powershell
python -X utf8 artifact/20261012_all_versions_comparison/compare_artifacts.py
python -X utf8 artifact/20261012_all_versions_comparison/derive_comparison.py
python -X utf8 artifact/20261012_all_versions_comparison/review_details.py
python -X utf8 artifact/20261012_all_versions_comparison/compare_code.py
```

仅使用标准库。`compare_artifacts.py`还会生成本地临时`fact_profiles_raw.json`，供差异计算；Git仅保存精简比较，不重复归档完整旧台账。新复核请在新的比较目录执行，保存旧记录。部分v5/v6及早期未完成目录只存在本机，Git中没有全量输入；源码比较会记录缺失文件，不能把不同输入范围的重跑称为完全复现。格式对齐版读取已冻结的Git提交，其具体SHA保存在inventory和DOCX定位中。

本次更正上一轮遗漏的v4格式和总分，并补入“v4单日阶段更多却得分更高”的反证，避免用阶段数、篇幅或引用数直接解释评分。原v8正式48文件、冻结台账、两份ZIP及Release附件保持原哈希。
