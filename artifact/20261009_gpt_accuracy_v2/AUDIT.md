# 最终验证记录

主流程从原始输入重读并重建：32.4秒；便携Python流程同样重读：27.53秒；全新隔离虚拟环境仅按requirements安装后的原始数据重建：82.63秒。日志与命令在 audit/full_reproduction.log、full_run.json、portable_reproduction/ 和 clean_reproduction/。后者记录安装日志和完整requirements.lock.txt。这是当前实测，不保证其他机器耗时一致。

- 8节点文件结构、DOCX标题和五章、正文四图引用、32 PNG尺寸及绘图数据、16工作表固定列序/日期/数量类型/全部单元格、当日与历史截止边界：通过。
- 每个纳入事件三类来源定位、肯定关键字段至少两类支持、未知任务例外注明、子证据唯一分配、原始正文片段与Excel行：通过证据链一致性检查；该检查不提供官方内容准确率。
- 原始人工开发案例：28/28；其他七节点回归案例：14/14。首次失败和标签更正保留。原始案例详细依据在 audit/manual_case_review.md、cases_raw_records.json。
- 乱序/文件重新编号不影响当日事实，未来记录不影响截至节点主线：16/16。
- Word原生渲染71页，逐页检查，无空白页、无页外文字。所有节点页面拼图已查看；修复默认标题蓝色边框残留、证据索引孤行续页和强制分页造成的空白页。保留PDF/PNG、render_log.json和raster_checks.json，渲染日志记录最终DOCX SHA256。
- XLSX由artifact-tool生成，并进行内部检查和预览。其日期预览器显示序列值的局限已记录；openpyxl确认原生日期类型，Excel实际显示yyyy.mm.dd。16个原生工作表前4条数据预览已查看，列宽、换行、表头及全部单元格另作程序验证。原生日志含最终XLSX SHA256。
- 便携流程及全新虚拟环境各8个工作簿的所有单元格与主交付一致：通过，见 portable_content_comparison.json。全新环境的原始快照与全部事件JSONL SHA256也与主流程一致。
- 提交ZIP48文件，根目录日报/，无PDF、无辅助证据，CRC及48项SHA256逐个一致：通过。

提交ZIP SHA256：`728086a59f3259463737abdc3786e926fc2f4b5f7c4b8663db74a2e67fa8f6a4`。

LibreOffice不可用，文档技能脚本渲染尝试失败后使用本机Microsoft Word隐藏只读导出，没有修改日报。QA PDF只用于视觉验证，不进入可提交ZIP。完整复制的原始数据快照属于复现证据，也不进入日报ZIP。

以上结构、证据链及42个特选人工案例分别记录；没有官方重新评分，不把任一校验通过解释为整体事实正确。
