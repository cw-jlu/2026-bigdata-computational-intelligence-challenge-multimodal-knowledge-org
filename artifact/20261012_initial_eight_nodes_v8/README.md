# initial v8：八节点完整重做与实测反馈

用户2026-10-12反馈初赛initial、8节点：完整性86.1320、准确性65.2266、格式96.5230、分析45.2500。按展示均值加权总分 **71.1521**，准确性评分不是事件正确率。

原评测48份正式文件在`official/`，完整候选赛段ZIP也保存在本目录，根层8个日期目录。原工程包大于GitHub单文件限制，完整工程/证据包按原SHA256存于[Release](https://github.com/cw-jlu/2026-bigdata-computational-intelligence-challenge-multimodal-knowledge-org/releases/tag/initial-v8-20261012)；其中包含原始输入、96页视觉检查、源码和逐节点冻结台账。Git归档解包后的原工程文件，便于直接审阅。资产说明和原始哈希见`evaluation/evaluation_initial_20261012.json`。

- [评分原文、精确计算和版本绑定限制](evaluation/evaluation_initial_20261012.json)
- [分数复盘与下一轮应检验的改进](evaluation/复盘.md)
- [评测前交付说明](交付说明.md)
- [原始输入/方法边界](输入与方法边界.md)
- [八节点总审计](stage_audit.json)、[逐节点矩阵](node_status_matrix.json)

八节点各有自己的audit.json、analysis.md、冻结台账、来源资格、纳入/排除抽查和视觉检查。原工程文件及原始输入由原工程ZIP逐成员解包归档；评测反馈和本README为交付后的新增记录，不改变正式报告、台账或原ZIP。早期stage_audit中的平台评测null/未上传是当时状态，当前用户反馈在evaluation中独立追加，没有伪造平台回执。

Windows PowerShell从本目录复现：`./Run-all.ps1 -Output 'C:/path/to/new-output'`。已封装原始inputs；依赖和可移植参数见dependencies.json、requirements.txt及交付说明。新的输出审查状态保持pending，不能自动冒称重新人工看过。

本轮71.1521是按节点均值推算值，未提供平台独立总分、提交ID、逐节点结果或扣分细项。复盘提出待检验解释，不将某条事件或图表当作已确定扣分原因。
