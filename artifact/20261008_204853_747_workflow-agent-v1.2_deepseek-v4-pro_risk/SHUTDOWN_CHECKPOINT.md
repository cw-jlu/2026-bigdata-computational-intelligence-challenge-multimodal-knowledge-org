# 关机前保存记录

2026-10-08：v1.2运行已于22:15:49因磁盘空间不足退出，当前没有运行进程。SQLite integrity_check通过。已保存405条记录的调查状态，其中319条调查完成；已有38条候选事件，尚未生成完整可信报告。

完整trace压缩为traces.jsonl.gz，逐字节解压哈希验证通过，校验值见trace_archive.json。包括可能不完整的最后一行，保留原样。密钥和本地配置不进入Git。

续跑同一实验须使用本目录code内的v1.2代码快照和experiment_config.json；当前开发源码为v1.3，不能直接用于原实验。先腾出磁盘空间，解压traces.jsonl.gz到traces.jsonl，再使用实现目录的Python环境执行本目录code/run.py，指定原始数据、2025.5.1至2025.5.10、--output本目录、--config本目录experiment_config.json、--env-file本地密钥文件、--stage all。其他电脑需重建依赖与本地密钥文件，不要使用process.json旧PID。只跳过已完成调查。

若测试v1.3结束循环修复，应使用新实验目录；原v1.2数据作为对照保留。

## 2026-10-08 当前工作区恢复检查

已在 `D:\code\python\2026-bdci-multimodal-knowledge\2026-bigdata-computational-intelligence-challenge-multimodal-knowledge-org` 恢复 `traces.jsonl`，其解压字节数与 SHA-256 均匹配 `trace_archive.json`。v1.2 代码签名与 `run_config.json` 一致，SQLite `integrity_check` 为 `ok`。使用当前工作区的原始数据执行 `--stage prepare` 成功：7000 条记录、527 组轨迹、0 项文件质量问题，说明输入指纹可续接旧实验。当前仍有 405 条记录的调查状态、其中 319 条完成，以及 38 条候选事件；尚未执行新的模型调查。此工作区没有 `DS_API_KEY`，需本地配置后再继续 `--stage all`。
