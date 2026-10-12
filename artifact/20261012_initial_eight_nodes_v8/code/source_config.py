from common import *
SOURCES={
'B04':{'title':'Fortschrittsbericht der Bundesregierung zur Umsetzung der Leitlinien zum Indo-Pazifik 2024','publisher':'德国联邦政府／德国外交部','url':'https://www.auswaertiges-amt.de/blob/2677458/949b428b80c94b46e906a115ab90b519/240925-llip-fortschrittsbericht-pdf-data.pdf','published_by':'2024-09-25','version_date':'2024-09-25','version_status':'fixed_edition','period':'报告期2023年9月至2024年8月','date_basis':'固定PDF每页25.09.2024；原发布渠道文件名与PDF ModDate相互核对','locator':'PDF第8页3.1第1段，另读第5页概要','role':'official_policy','independence_group':'German_federal_government','content_verified':True,'reading_status':'本轮下载并读取固定德文PDF第5和8页；仅引用3.1','units':'不引用宏观金额和编队数量；2024演习安排是历史背景'},
'B09':{'title':'Japan–Malaysia Bilateral Exercise MALPAN','publisher':'日本海上幕僚监部','url':'https://www.mod.go.jp/msdf/en/release/202504/20250416en.pdf','published_by':'2025-04-16','version_date':'2025-04-16','version_status':'fixed_edition','period':'2025-04-14至15日','date_basis':'官方2025新闻稿目录列明4月16日，并链接页首同日的固定英文PDF','locator':'PDF第1页2、4、5项','role':'official_assessment','independence_group':'JMSDF','content_verified':True,'reading_status':'本轮通过web读取PDF第1页全文；直连下载403，保存实际所读可定位摘录','units':'不把舰艇种类、演习期间和本比赛单日活动作数量同比'},
'B10':{'title':'Japan–U.S.–France Multilateral Exercise Pacific Steller','publisher':'日本海上幕僚监部','url':'https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf','published_by':'2025-02-06','version_date':'2025-02-06','version_status':'fixed_edition','period':'公告安排2025-02-10至18日演习','date_basis':'官方2025新闻稿目录列明2月6日；固定PDF页首同日','locator':'PDF第1页2至5项','role':'official_assessment','independence_group':'JMSDF','content_verified':True,'reading_status':'本轮web读取固定PDF第1页全文；下载403，保存实际摘录','units':'未来式演习公告属于当时公开安排，未升级为实际全部实施'},
}
EXCERPTS={'B09':'原文短摘（18词）：Harbor Phase: Diving exercise. Ocean Phase: Maneuvering exercise, COMMEX. RMN: KD MAHAMIRU, KD KINABALU.\n本轮所读第1页2、4、5项的释义：新闻稿日期2025年4月16日；4月14日港内、15日海上训练；区域马六甲海峡及巴生港；参与的马方平台为上述两舰和潜水人员。摘录不冒充完整PDF，下载403记录保留。', 'B10':'原文短摘（20词）：French Navy: FS CHARLES DE GAULLE. Tactical Exercise (Anti-Air Warfare, Anti-Submarine Warfare, LINKEX, Cross Deck etc.)\n本轮所读第1页2至5项的释义：2025年2月6日公告拟于2月10日至18日在菲律宾以东海空域举行合作演习；法国戴高乐等拟参与，科目为防空、反潜、数据链和跨甲板等。公告不等于活动已实施；摘录不冒充完整PDF。'}
USED={'2025.5.10':['B04'],'2025.5.18':['B04'],'2025.5.30':[],'2025.6.9':['B09'],'2025.6.17':['B01'],'2025.6.29':[],'2025.7.9':['B07'],'2025.7.17':['B10']}
def catalog(out=BASE):
    # The raw publication files/excerpts are immutable, and metadata is rebuilt
    # from the files actually present, rather than copied content_verified flags.
    allsrc=load(ROOT/'analysis_research_bundle/source_catalog.json')['sources']
    for s in allsrc:s['content_verified']=False;s['reading_status']='包内目录已读；本轮未读取相关全文，不引用'
    b01=load(BASE/'evidence/external/B01_access.json')
    SOURCES['B01']={'title':'Joint Statement Australia–Japan–Philippines–United States Maritime Cooperative Activity','publisher':'四国国防部长联合，日本防卫省原发布渠道','url':b01['url'],'published_by':'2024-04-06','version_date':'2024-04-06','version_status':'fixed_edition','period':'公告2024-04-07活动安排','date_basis':'官方发布页April 6 2024与PDF创建/修改日期同日，页末April 2024','locator':'PDF第1页第2至3段','role':'official_policy','independence_group':'Four_ministers_joint_statement','content_verified':True,'reading_status':'本轮读官方原发布页与下载PDF两页，正文仅采用第1页','units':'不引用规模数字；机构合作目标按归属表达'}
    b07=BASE/'evidence/external/B07.pdf'
    if b07.exists():
        SOURCES['B07']={'title':'Canada’s Indo-Pacific Strategy','publisher':'加拿大环球事务部','url':'https://www.international.gc.ca/transparency-transparence/assets/pdfs/indo-pacific-indo-pacifique/indo-pacific-indo-pacifique-en.pdf','published_by':'2022-12-31','version_date':'2022-11-30','version_status':'fixed_edition','period':'2022年政策版，不是2025活动统计','date_basis':'官方2022-11-27发布说明；本PDF为11月30日修订固定版，服务器Last-Modified为2022-12-01，ISBN 978-0-660-46258-5，采用年末保守公开上界','locator':'PDF第17页／印刷页14第2段','role':'official_policy','independence_group':'Canada_GAC','content_verified':True,'reading_status':'本轮下载固定PDF并实际读第17页，核查页1–3版次及元数据','units':'不引用拨款；仅政策对海军存在与合作的表述'}
    else:USED['2025.7.9']=[]
    for sid,text in EXCERPTS.items():
        p=out/f'evidence/external/{sid}_read_excerpt.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8')
    limits=['外部来源只提供历史背景、明确归属的政策或替代解释，不验证比赛事件、不消解三源冲突','未持有节点当日全部网页快照；固定PDF由页内日期和原发布方目录核对，但无法绝对排除同URL替换']
    for sid,s in SOURCES.items():
        s.update({'id':sid,'source_id':sid,'version':'所读固定出版物；保存文件或摘录哈希','retrieved_at':'2026-10-12 Asia/Shanghai','limits':limits})
        p=BASE/f'evidence/external/{sid}.pdf'
        s['local_path']=f'evidence/external/{sid}.pdf' if p.exists() else f'evidence/external/{sid}_read_excerpt.txt';s['sha256']=sha(p if p.exists() else out/s['local_path'])
    for n in NODES:
        save(out/f'audits/{n}/source_catalog.json',{'schema_version':1,'sources':list(SOURCES.values())+allsrc})
    save(out/'evidence/external/used_sources.json',USED)
if __name__=='__main__':catalog()
