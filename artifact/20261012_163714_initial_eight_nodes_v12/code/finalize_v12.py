from common import *
from PIL import Image,ImageChops
import shutil

def main():
    old=BASE.parent/'20261012_160950_initial_eight_nodes_v11'
    assert load(BASE/'visual_revision_comparison.json')['status']=='PASS'
    assert load(BASE/'reproduction_comparison.json')['status']=='PASS'
    assert load(BASE/'package_validation.json')['members']==48
    receipt=load(BASE/'qa/current_agent_visual_receipt.json');assert len(receipt['opened_contacts'])==32
    renders={r['node']:r for r in load(BASE/'word_render.json')};raster=load(BASE/'raster_records.json');pages=0;unchanged=0;changed=0
    for row in raster:
        n=row['node'];pages+=row['pages'];assert sha(BASE/f'official/{n}/{n}日报.docx').lower()==renders[n]['source_sha256'].lower()
        same=[];different=[]
        for p in row['page_pngs']:
            a=Image.open(old/p).convert('RGB');b=Image.open(BASE/p).convert('RGB')
            equal=a.size==b.size and ImageChops.difference(a,b).getbbox() is None
            (same if equal else different).append(p)
        assert len(same)==row['pages']-4 and len(different)==4,(n,len(same),len(different))
        unchanged+=len(same);changed+=len(different)
        record={'status':'reviewed_current_agent','renderer':renders[n]['renderer'],'docx_sha256':sha(BASE/f'official/{n}/{n}日报.docx'),'page_count':row['pages'],'reviewed_contacts':[p for p in receipt['opened_contacts'] if '/'+n+'/' in p],'body_pages_pixel_identical_to_v11':same,'updated_figure_pages':different,'findings':'未发现缺字、标签越界、重叠、图例遮挡或文档裁图。长平台名按主体与平台两行排，避免括号孤行。','xlsx_review':'与v11字节完全一致，沿用v11已完成的原生渲染检查；本轮未再次渲染XLSX。'}
        save(BASE/f'audits/{n}/visual_review.json',record)
        a=load(BASE/f'audits/{n}/audit.json');a['status']='complete_local_visual_only_revision';a['checks']['visual_review']='complete';a['checks']['semantic_support']='unchanged_v11_reviewed_fact_and_analysis_layer';a['checks']['raw_reproduction']='PASS';a['checks']['independent_review']='not_performed';save(BASE/f'audits/{n}/audit.json',a)
    assert pages==91 and unchanged==59 and changed==32
    save(BASE/'render_comparison.json',{'status':'PASS','total_pages':pages,'unchanged_body_pages_pixel_identical':unchanged,'updated_figure_pages':changed,'all_pages_visually_reviewed':True})
    matrix=load(BASE/'node_status_matrix.json')
    for r in matrix:r.update(visual_review='complete',raw_reproduction='PASS',independent_review='not_performed')
    save(BASE/'node_status_matrix.json',matrix)
    save(BASE/'stage_audit.json',{'status':'complete_local_visual_only_revision','version':'v12','baseline':old.name,'formal_file_count':48,'docx_count':8,'xlsx_count':8,'png_count':32,'docx_pages':pages,'daily_events':205,'daily_facts_changed':False,'analysis_changed':False,'docx_font_styles_changed':False,'xlsx_changed':False,'png_style_changed':32,'raw_reproduction':'PASS','archive_reader_check':'PASS','platform_score':None,'uploaded':False,'independent_blind_review':False,'nodes':matrix})
    save(BASE/'style_reference.json',{'reference':'提交示例文件/日报/2025.10.20/附件图表','reference_images':[{'name':p.name,'sha256':sha(p)} for p in sorted((BASE/'inputs/提交示例文件/日报/2025.10.20/附件图表').glob('*.png'))],'matched':['白底黑字及居中标题','浅灰虚线网格与黑色轴框','数量曲线红色圆点、蓝色方点','活动时间轴橙色飞机、蓝色舰艇','00:00至24:00横轴与条形旁区域/方向/任务标签'],'intentional_deviations':['图例放图框外，防止遮挡末行','晚间活动标签必要时置横条左侧，防止出框','保留F证据编号与统计口径说明','长平台名主体/平台分两行','严格保留核实事实和未知时间，不复制示例数值'],'font':{'path':'C:/Windows/Fonts/simhei.ttf','sha256':sha(Path('C:/Windows/Fonts/simhei.ttf'))}})
    (BASE/'README.md').write_text('''# 初赛八节点 v12 图表样式修订

以 v11 为基线，按提交示例的四类附图调整全部 32 张 PNG，并同步嵌入八份日报。历史 artifact 目录未覆盖。

本轮仅改图表呈现：白底、黑字、浅灰虚线网格；数量曲线采用红色圆点与蓝色方点，活动图采用橙蓝横条，区域、方向及任务紧邻横条。长平台名分行；晚间活动标签移至横条左侧以避免越界；图例放在图框外，避免示例中末行被遮挡的问题。

## 内容边界与验证

- 205 条当日事实、全部分析和正文文字保持 v11 原样；冻结台账和分析快照哈希一致。
- 8 份 DOCX 字体、样式、设置与正文 XML 保持一致，只有图片及其适配尺寸变化；8 份 XLSX 与 v11 字节一致。
- 曲线 24 时点数据和三组活动成员与 v11 完全一致。方向标签取既有核实字段，不增加事件或精度。
- 八份 DOCX 经 WPS Office（Word.Application COM）完整导出 PDF，再渲染 91 页 PNG；已目视检查。59 页正文与 v11 逐像素相同，32 页附图更新，无发现裁切或标签重叠。
- 8 份 XLSX 沿用 v11 完成的原生渲染检查，本轮用字节哈希确认未变；未宣称重新渲染工作簿。
- 本轮另从原始 TXT 和 XLSX 输入重新执行八节点流水线，冻结事实、分析快照、DOCX 正文 XML、工作簿值与类型以及 32 张 PNG 一致。分析是回放已审阅快照，不是重新由模型生成。
- 48 文件 ZIP 已逐成员校验名称、目录、CRC 和 SHA256。程序检查仅证明一致性与可复现性，不能证明隐藏标准答案或平台得分。

## 交付与复现

正式提交包：`赛题2_初赛_八节点_完整候选提交包.zip`，根目录为八个节点日期目录，每节点 1 DOCX、1 XLSX、4 PNG；全部文件也在 `official/`。

执行 `./run-all.ps1 -Output <新的绝对目录>` 可从原始输入复现，默认调用本机 Office 导出；`-SkipNativeRender` 可只复现成果并比较内容。需要依赖清单中的 Python 包、Codex artifact-tool Node 运行时及 Windows 黑体字体；不将运行时与字体二进制打入工程包。`code/charts.py` 为本轮图表实现；`code/review_v12.py` 用于与保留的同级 v11 目录比较；旧版本维护脚本为历史来源，不是本轮入口。

审计入口：`visual_revision_comparison.json`、`style_reference.json`、`render_comparison.json`、`reproduction_comparison.json`、`stage_audit.json`、`qa/current_agent_visual_receipt.json`。逐节点证据继续保存在 `audits/` 和 `evidence/`。

## 限制

v12 未取得新的平台评分，未上传。本轮不改事实裁决与分析，因此 v11 既有局限仍保留：候选组织仍利用雷达批次，别名与实体关联规则有限，坐标检查不是完整航迹重建，当前代理不是独立盲审。图片风格接近示例不等于平台格式满分，也不意味着准确性、完整性或总分提高。
''',encoding='utf8')
    (BASE/'artifact.md').write_text('''# v12 artifact contract

视觉参考为提交示例文件/日报/2025.10.20/附件图表四张PNG，当前代理已实际打开全部示例。
保留v11正文、五章、第二节跨日证据索引、仿宋正文16pt、黑体标题/章节、A4节设置和全部工作簿。
仅重绘32张附图并适配DOCX嵌入尺寸。白底黑字、虚线网格、红蓝数量曲线、橙蓝活动横条。
图例置图框外、长标签按语义分行、末时段标签左置，保留证据编号和统计口径。不得更改核实集合、原始时间、数量或区域。
正式48文件，8节点，历史版本保留。完整渲染及原始输入复现审计见README和stage_audit.json。
''',encoding='utf8')
    print('FINALIZED v12: 91 pages reviewed, 59 unchanged body pages, 32 restyled figure pages.')

if __name__=='__main__':main()
