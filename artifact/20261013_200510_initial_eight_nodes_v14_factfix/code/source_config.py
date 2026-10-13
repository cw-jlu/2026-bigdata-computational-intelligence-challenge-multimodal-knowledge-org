from common import *
def source(sid,title,publisher,url,date,basis,period,locator,evidence,limits,extension='pdf'):
 p=BASE/f'sources/{sid}.{extension}'
 assert sha(p)==load(BASE/'sources/manifest.json')['files'][p.name], 'archived external source drift: '+sid
 return {'id':sid,'title':title,'publisher':publisher,'url':url,'published_by':date,'date_basis':basis,'content_period':period,'role':'official_assessment','independence_group':publisher+'_'+sid,'content_verified':True,'version_status':'fixed_edition','locator':locator,'local_path':f'sources/{sid}.{extension}','sha256':sha(p),'actual_read_scope':'本轮提取并阅读所列原文；PDF对应页或HWP内置首页预览已视觉检查','specific_evidence':evidence,'contribution':evidence,'limits':limits}
SOURCES={
 'E01':source('E01','Joint ISR Conducted by Japan, the United States, and Australia','日本防卫省','https://www.mod.go.jp/en/images/1124a_usa_aus-j.pdf','2023-11-24','固定公告页首日期','2023-11-19至20','PDF第1页第1项','公告明确日本P-1、美国海军P-8A、澳大利亚空军P-8A在日本周边水域及空域共同实施ISR，是多任务解释的具体历史案例。','不证明2025年任何出动参加同一机制，不提供本赛段频次基线或机体身份。'),
 'E03':source('E03','P-8A国内到达联合新闻稿','韩国防卫事业厅、韩国海军','https://www.dapa.go.kr/jfile/board/readDownloadFile.do?fileType=WT_CMS_DOC&fileTypeSeq=19316&fileNum=1','2024-06-19','固定HWP首页发布及分发均为2024-06-19 08:30，与发布页及文件名240619一致','2024-06交付，预计2025年中作战投入','HWP首页及正文末段，2024-06-19联合新闻稿','报告2024年6月19日3架到达，另3架计划6月30日到达；拟经约一年训练及评估后于2025年中投入作战，支持把本节点解释放在引进与形成能力的阶段背景中。','预计不等于完成，不把2025年5月比赛反潜记录擅改成训练；不证明机队扩充、实战状态或任务归因。','hwp'),
 'E04':source('E04','JDP 2-00 Understanding and Intelligence Support to Joint Operations 4th Edition','英国国防部','https://assets.publishing.service.gov.uk/media/653a4b0780884d0013f71bb0/JDP_2_00_Ed_4_web.pdf','2023-10-31','固定第4版August 2023；官方固定文件2023年10月路径，保守月末上界','2023年第4版','PDF第87页（印刷77）4.2、第96页（印刷86）4.15及RC135图注','SIGINT是来自电磁信号的情报，ISR是统筹任务、采集及加工的活动和过程，二者是不同层次概念；该页将英国RC135称为主要ISR平台。','术语层次支持相容解释，不证明比赛电子侦察具体为SIGINT某子类、采集对象或成果，不替代任务原句。'),
 'E06':source('E06','G550 Airborne Early Warning Fact Sheet Updated for Singapore Airshow 2012','新加坡国防部、新加坡国家档案馆','https://www.nas.gov.sg/archivesonline/data/pdfdoc/MINDEF_20070423001/MINDEF_20070423002_3.pdf','2012-02-23','固定PDF标题Updated 23 Feb 2012；不采用旧署名2007冒充本版日期','2012更新的G550-AEW改型能力说明','PDF第1页标题及第2—3正文段','G550-AEW用于空情感知和识别，是联网防空体系组成部分；其雷达针对空中目标检测、识别与跟踪，说明ISR描述与警戒用途并非必然互斥。','只针对AEW改型，不从型号背景补本次改型、任务、ADOC配属或联网成果；不能补造航迹或宣布战略重心转移。'),
 'E07':source('E07','Canada’s Indo-Pacific Strategy 2022 to 2023 Implementation Update','加拿大外交部','https://www.international.gc.ca/transparency-transparence/assets/pdfs/indo-pacific-indo-pacifique/2022-2023-en.pdf','2024-12-31','固定出版物版权页2024、PDF创建2024-04-25；无精确公开日，采用2024年末上界','2023实施回顾','PDF第6页（印刷4）Enhanced military presence in the region','报告Montréal于2023年3—8月，Ottawa、Vancouver于8—12月部署印太，参与NEON及HORIZON；HORIZON承诺每年派3艘舰并参加演习，提供多舰与多任务的具体历史背景。','背景多舰轮换是可能解释，不证明比赛哈利法克斯级记录对应这些具名舰；不证明2025部署、CH-148机体/母舰或单一舰体连续航程。'),
 'E08':source('E08','Japan-U.S.-France Multilateral Exercise Pacific Steller Announcement','日本海上幕僚监部','https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf','2025-02-06','固定公告页首日期','拟2025-02-10至18','PDF第1页开头及第2—5项','计划列戴高乐号与美日海军参加菲律宾以东海空域多科目训练，科目包括防空、反潜、数据链和交叉甲板，说明其合作活动不应被单一警戒标签概括。','仅计划公告，不证明实施、5—7月合作、警戒性质或两段连续部署；不填完整编队。')
}
USED={n:ss for n,ss in zip(NODES,[['E01'],['E07'],['E03'],['E04'],['E01'],['E06'],['E07'],['E04']])}
EXCLUDED=[{'ids':['E02'],'reason':'CH-148官方PDF搜索能定位，但原件多次超时/404；未取得原文，不采用搜索摘要'}, {'ids':['R01','R02','R03','R04','R05','R09'],'reason':'方法资料或动态网页历史版本不足，不作为事件背景'}, {'ids':['2025-06-Korea-operational-declaration'],'reason':'晚于5月30日节点，严禁补证或校准'}]
def catalog(out):
 for s in SOURCES.values():assert sha(BASE/s['local_path'])==s['sha256']
 save(out/'audit/source_catalog.json',{'schema_version':1,'sources':list(SOURCES.values()),'excluded':EXCLUDED})
 for n in NODES:
  used=[SOURCES[s] for s in USED[n]];assert all(s['published_by']<=dt(n).isoformat() for s in used)
  save(out/f'audits/{n}/source_eligibility.json',{'as_of':dt(n).isoformat(),'used':used,'excluded':EXCLUDED,'metadata_pass':True,'event_validation_sources':[],'E07_date_limit':'年度版权与PDF元数据提供年份上界，未取得独立日级发布回执'})
