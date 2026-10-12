from common import *
SOURCES={
'B04':{'title':'Fortschrittsbericht der Bundesregierung zur Umsetzung der Leitlinien zum Indo-Pazifik 2024','publisher':'德国联邦政府／外交部','url':'https://www.auswaertiges-amt.de/blob/2677458/949b428b80c94b46e906a115ab90b519/240925-llip-fortschrittsbericht-pdf-data.pdf','published_by':'2024-09-25','version_date':'2024-09-25','locator':'PDF第8页3.1，另核对第5页概要','period':'2023年9月至2024年8月报告期；部分2024年安排','date_basis':'v9轮重新下载，本轮沿用同哈希固定版13页固定PDF，页内25.09.2024与原站文件名相互印证','independence_group':'German_federal_government'},
'B01':{'title':'Australia–Japan–Philippines–United States Maritime Cooperative Activity Joint Statement','publisher':'四国国防部长联合／日本防卫省发布','url':'https://www.mod.go.jp/en/images/ea07e6ad451bbc35d870ab43fa2b402fd8537d17.pdf','published_by':'2024-04-06','version_date':'2024-04-06','locator':'PDF第1页第2—3段；完整两页v9轮通过web读取，本轮沿用同版','period':'2024年4月7日拟合作安排','date_basis':'固定PDF页末APRIL2024、元数据20240406；原发布日期见官方目录记录','independence_group':'Four_ministers_joint_statement'},
'B10':{'title':'Japan–U.S.–France Multilateral Exercise Pacific Steller (Announcement)','publisher':'日本海上幕僚监部','url':'https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf','published_by':'2025-02-06','version_date':'2025-02-06','locator':'固定PDF第1页第2—5项；v9轮web全文读取，本轮沿用同版','period':'2025年2月10—18日拟演习','date_basis':'PDF页首February6,2025与原站年月文件路径相互印证','independence_group':'JMSDF'},
'B12':{'title':'Canada’s Indo-Pacific Strategy: 2022 to 2023 Implementation Update','publisher':'加拿大环球事务部','url':'https://www.international.gc.ca/transparency-transparence/assets/pdfs/indo-pacific-indo-pacifique/2022-2023-en.pdf','published_by':'2024-12-31','version_date':'2024-12-31','locator':'PDF第6页／印刷页4，另核对PDF第1—2页版次','period':'2022—2023年实施情况；非2025出动统计','date_basis':'固定出版物封面2022to2023、版权页2024；无法精确到日，取2024年末为保守上界','independence_group':'Canada_GAC'}
}
USED={'2025.5.10':['B04'],'2025.5.18':['B04'],'2025.5.30':[],'2025.6.9':[],'2025.6.17':['B01'],'2025.6.29':[],'2025.7.9':['B12'],'2025.7.17':['B10']}
EXCLUDED=[
 {'id':'DAPA_P8A','url':'https://www.dapa.go.kr/dapa/doc/selectDoc.do?bbsSeq=326&docSeq=19316&menuSeq=3069','status':'v9轮search返回正文，open超时；无节点前固定附件或网页版本','reason':'当前页面旧署名日期不足以证明具体历史版本；不引用部署计划'},
 {'id':'RAF_RAMSTEIN','url':'https://www.raf.mod.uk/news/articles/exercise-ramstein-flag-2024-thats-a-wrap/','status':'v9轮实际读取当前正文；署名2024-10-10，网页当前2026','reason':'未确认节点前具体文字版本'},
 {'id':'RAF_NEWS_PDF','url':'https://www.rafnews.co.uk/uploads/RAF%20News%2018%20Oct%202024%20issuu.pdf','status':'搜索命中，web404/直连403','reason':'未取得固定PDF正文，不冒充全文读取'},
 {'id':'NAS_G550','url':'https://www.nas.gov.sg/archivesonline/data/pdfdoc/MINDEF_20070423001.pdf','status':'v9轮实际读3页固定稿；附件_2和_3获取失败','reason':'主稿仅防空体系演示，G550事实表正文缺失；不能以附件标题证明内容'},
 {'id':'MINDEF_G550_CURRENT','url':'https://www.mindef.gov.sg/news-and-events/latest-releases/2012apr13-news-releases-00184/','status':'检索当前页面及2026海上监视机资料','reason':'迁移后历史版本不明；2026资料晚于节点且用途不同'}]
def catalog(out=BASE):
 for sid,s in SOURCES.items():
  p=out/f'evidence/external/{sid}.pdf'
  if not p.exists():p=out/f'evidence/external/{sid}_read_excerpt.txt'
  assert p.exists(),p
  s.update(id=sid,source_id=sid,role='official_assessment',content_verified=True,reading_status='same conversation v9 cited-passage review retained; v10 unchanged cached fixed edition, no claim of fresh network retrieval',version_status='fixed_edition',version='dated fixed PDF, original language; no later translation used',retrieved_at='2026-10-12 Asia/Shanghai',units='历史安排或部署背景，不与赛内架次/艘次作规模同比',limits=['外部不验证比赛单次事件、不修补冲突','固定版日期有内文依据；不能绝对排除同URL历史替换'],local_path=p.relative_to(out).as_posix(),sha256=sha(p))
 for n in NODES:save(out/f'audits/{n}/source_catalog.json',{'schema_version':1,'sources':list(SOURCES.values())});save(out/f'audits/{n}/external_search_gaps.json',EXCLUDED)
 save(out/'evidence/external/used_sources.json',USED);save(out/'evidence/external/search_log.json',EXCLUDED)

