"""Freeze raw-evidence labels: initial 32 before matcher; 14 additional after calibration.

File prefixes here are ONLY source locators, never event correspondence.
Labels were decided by reading bodies and Excel rows, not generated predictions.
"""
import json, hashlib
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parents[1]
specs=[
 # category, day, open locator, opinion locator, radar batch, associate, include, basis
 ('同型平台','2025.5.10','035','041','AIR-BAF8BCA0C55F92',True,True,'中国歼-10C；海南岛东南海域；08:03—10:28；战备警巡；1架'),
 ('同型平台','2025.5.10','041','003','AIR-94408DEB623424',True,True,'中国歼-10C；苏岩礁；08:41—10:06；战备警巡；1架'),
 ('同型平台','2025.5.10','035','003','AIR-BAF8BCA0C55F92',False,None,'开源海南东南与舆论东海不一致，不能因歼-10C同型合并'),
 ('同型平台','2025.5.10','041','041','AIR-94408DEB623424',False,None,'开源苏岩礁与舆论海南东南不一致；活动起止时间不同'),
 ('同型平台','2025.5.10','037','018','AIR-A19EDC5BFA2976',True,True,'马来西亚A400M；钓鱼岛；远程兵力投送；14:55—16:20；舆论1架'),
 ('同型平台','2025.5.10','036','018','AIR-C98E9F2B779306',False,None,'孟加拉湾搜救与东海投送不是同一事件'),
 ('主体错配','2025.5.10','024','038','SHIP-30A046A0E6AFD2',True,False,'柯林斯级与长江口/东海吻合，但开源意大利与舆论/雷达澳大利亚冲突，不多数裁决'),
 ('主体错配','2025.5.10','046','028','AIR-4E92B86326A346',True,False,'E-767济州岛；开源/雷达日本，舆论俄罗斯；保留身份冲突'),
 ('区域错配','2025.5.10','017','039','AIR-3B6F61E3F12895',True,False,'台湾经国号11:44—13:14对海突击；开源孟加拉湾，舆论安达曼海，雷达约88E15N；不得合票定区'),
 ('区域错配','2025.5.10','029','011','SHIP-1BEADE90A1114F',True,False,'中国903A同一次08:08—10:33；两文本成山头黄海，雷达东海南部，无法消解'),
 ('异常轨迹','2025.5.10','039','017','SHIP-C8D66FB15B8C0B',True,False,'新加坡无敌20:42—22:07；雷达相同时刻南海与宁波并存，各7行，无坐标证明可删哪组'),
 ('异常轨迹','2025.5.10','002','020','SHIP-F4B78A88D06154',True,False,'056A连云港17:02—19:27；雷达同时东海与连云港并存，不能以首行东海填报'),
 ('文本冲突','2025.5.10','044','029','AIR-74BB12F6148F7E',True,False,'台湾P-3C14:46—16:16东海南部；开源1架，舆论2架，雷达1架'),
 ('文本冲突','2025.5.10','004','025','SHIP-49592BAB51B8FF',True,False,'无敌级东海中部；开源18:12起，舆论19:17起，结束均19:42；明确起始冲突'),
 ('文本冲突','2025.5.10','049','030','AIR-6A5EB9A4E1BBA4',True,False,'空警-600南康暗沙；开源空中警戒，舆论/雷达预警指挥；不可按型号默认任务'),
 ('文本冲突','2025.5.10','010','016','AIR-4A3B2D7C0D9623',True,False,'德国台风黄岩岛；开源18:04—19:54，雷达17:29起，舆论17:29观察点；开源时段不可被投票替代'),
 ('合编拆分','2025.5.10','023','032','AIR-3B564DE1F3DD6D',True,True,'英国合编开源包含P-8A1架及RC-135W2架，舆论032仅P-8A；雷达P-8A20:09—22:34；只给P-8A使用'),
 ('仅两源','2025.5.10','023',None,'AIR-093CB109918635',True,False,'英国RC-135W2架在合编开源及雷达，舆论无该型号；不能挪用P-8A报道'),
 ('合编拆分','2025.5.10','048','044','AIR-AF10F9EBB9E18A',True,True,'日本合编开源明确P-1一架；舆论P-1；雷达05:07—07:32东海反潜；SH-60K不是P-1'),
 ('仅两源','2025.5.10','048',None,'AIR-730DC2A79E3FDD',True,False,'合编开源SH-60K2架及雷达；无舆论SH-60K，不能套用P-1'),
 ('仅两源','2025.5.10','030',None,'AIR-B8FBF3CD333F7B',True,False,'意大利F-35B与P-72A合编；舆论仅P-72A，F-35B缺舆论'),
 ('合编拆分','2025.5.10','030','049','AIR-9740CBEDE14968',True,True,'意大利P-72A黄海中部02:49—04:14；情报监视侦察；舆论1架与雷达1架'),
 ('边界口径','2025.5.10','042','042','SHIP-86AD1B85DCDEF3',True,True,'新西兰奥特亚罗瓦；南海南部；例行部署；05:34—07:59；舆论/雷达1艘'),
 ('边界口径','2025.5.10','013','048','SHIP-0AB0D8C5EB8110',True,True,'澳大利亚安扎克；上海外海；02:16—04:41自由航行；舆论/雷达1艘'),
 ('同型平台','2025.5.18','034','018',None,True,True,'美国P-8A南海中部08:03—10:28联合巡逻，独立于纳土纳与北部湾活动'),
 ('文本冲突','2025.5.18','021','027',None,True,False,'北部湾11:28—12:58；开源1架，舆论2架，雷达1架'),
 ('主体错配','2025.5.18','049','010',None,True,False,'空警-600济州岛20:00—21:30；开源中国，舆论台湾'),
 ('异常轨迹','2025.5.18','010','005','AIR-1CC2A2CC80B4D1',True,False,'韩国E-737北康暗沙与南海；雷达至少两组南海/黄海坐标，不能取中位数伪造位置'),
 ('异常轨迹','2025.6.17','013','020','AIR-DF120E6AF82F7E',True,False,'菲律宾AW-15920:09—22:34长江口，雷达南海15N与东海31N并行'),
 ('主体错配','2025.6.17','028','028',None,True,False,'福克50济州岛05:14—06:44；开源新加坡，舆论印度'),
 ('异常轨迹','2025.7.17','036','002','AIR-CE2DA13274C502',True,False,'无侦-7东海17:35—19:00；雷达15N与29N并行，文本同意也不能隐藏轨迹冲突；原G31误用缺时间油气田文本，原始Excel时段重新人工核对后更正'),
 ('主体错配','2025.7.17','050','045',None,True,False,'无侦-7东海南部20:00—21:30；开源中国，舆论台湾'),
 # Held-out raw checks, added after matcher calibration and before final QA.
 ('留出时间冲突','2025.5.30','001','022','SHIP-18322D2B75D3A3',True,False,'071东海北部结束均19:23；开源17:53起，舆论18:45起，不能直接多数投票'),
 ('留出正常','2025.5.30','003','032','AIR-3504D0A15DE5CB',True,True,'新西兰P-8A济州岛17:13—19:38联合巡逻；舆论/雷达1架'),
 ('留出正常','2025.5.30','005','033','AIR-65D7D93F9F027D',True,True,'日本E-767曾母暗沙05:45—07:10预警指挥；舆论/雷达1架'),
 ('留出正常','2025.5.30','006','036','SHIP-A313B909D0B466',True,True,'澳大利亚柯林斯黄海中部17:24—19:49例行部署；开源/雷达1艘'),
 ('留出合编','2025.6.9','002','012','AIR-296F85D0C21B4E',True,True,'法国大西洋2黄海中部20:09—22:34反潜；舆论1架，不能给同编E-2C'),
 ('留出正常','2025.6.9','001','032','SHIP-287E8E861699DC',True,True,'韩国岛山安昌浩海州湾02:16—04:41战备巡逻；开源/雷达1艘'),
 ('留出异常','2025.6.9','006','030','SHIP-14EBF18869F04F',True,False,'中国093A舟山17:02—19:27远海训练；雷达南海/舟山两套不相容区域'),
 ('留出数量冲突','2025.6.29','005','002','AIR-DA502CEB047CB0',True,False,'意大利P-72A温州05:01—07:26；开源2架，舆论及雷达1架'),
 ('留出观测点','2025.6.29','003','012','AIR-48DC01049C8B5E',True,True,'印度MH-60R长江口；开源18:33为时点不当成起飞/完整活动起始；舆论和雷达17:29—19:54反潜，1架'),
 ('留出正常','2025.6.29','004','045','SHIP-9FECD5E6A9B96A',True,True,'韩国独岛长江口08:52—10:17编队警戒；开源/雷达1艘'),
 ('留出正常','2025.7.9','001','026','SHIP-07BC21EE7E20DD',True,True,'中国903A西沙02:38—04:03海上补给训练；舆论/雷达1艘'),
 ('留出单源字段','2025.7.9','002','015','SHIP-AF41F705A929BC',True,False,'山东号东海中部14:28—16:53三源关联，但两文本均未报艘数，不从单舰名称默认数量'),
 ('留出正常','2025.7.9','003','037','SHIP-04B85D89354CC0',True,True,'中国052C钓鱼岛20:20—22:45防空反导；开源/雷达1艘'),
 ('留出主体错配','2025.7.9','004','004','AIR-709F52DB8C9C84',True,False,'台风北黄海20:47—22:12；开源德国，舆论俄罗斯'),
]

field_truth={
 'G01':{'country':'中国','region':'海南岛东南海域','task':'战备警巡','quantity':1,'start':'08:03','end':'10:28'},
 'G02':{'country':'中国','region':'苏岩礁附近海域','task':'战备警巡','quantity':1,'start':'08:41','end':'10:06'},
 'G05':{'country':'马来西亚','region':'钓鱼岛海域','task':'远程兵力投送','quantity':1,'start':'14:55','end':'16:20'},
 'G17':{'country':'英国','region':'海南岛东南海域','task':'联合巡逻','quantity':1,'start':'20:09','end':'22:34'},
 'G19':{'country':'日本','region':'东海','task':'反潜巡逻','quantity':1,'start':'05:07','end':'07:32'},
 'G22':{'country':'意大利','region':'黄海中部','task':'情报监视侦察','quantity':1,'start':'02:49','end':'04:14'},
 'G23':{'country':'新西兰','region':'南海南部','task':'例行部署','quantity':1,'start':'05:34','end':'07:59'},
 'G24':{'country':'澳大利亚','region':'上海外海','task':'自由航行','quantity':1,'start':'02:16','end':'04:41'},
 'G25':{'country':'美国','region':'南海中部','task':'联合巡逻','quantity':1,'start':'08:03','end':'10:28'},
 'G34':{'country':'新西兰','region':'济州岛西部海域','task':'联合巡逻','quantity':1,'start':'17:13','end':'19:38'},
 'G35':{'country':'日本','region':'曾母暗沙海域','task':'预警指挥','quantity':1,'start':'05:45','end':'07:10'},
 'G36':{'country':'澳大利亚','region':'黄海中部','task':'例行部署','quantity':1,'start':'17:24','end':'19:49'},
 'G37':{'country':'法国','region':'黄海中部','task':'反潜巡逻','quantity':1,'start':'20:09','end':'22:34'},
 'G38':{'country':'韩国','region':'海州湾外海','task':'战备巡逻','quantity':1,'start':'02:16','end':'04:41'},
 'G41':{'country':'印度','region':'长江口外海','task':'反潜巡逻','quantity':1,'start':'17:29','end':'19:54'},
 'G42':{'country':'韩国','region':'长江口外海','task':'编队警戒部署','quantity':1,'start':'08:52','end':'10:17'},
 'G43':{'country':'中国','region':'西沙群岛海域','task':'海上补给训练','quantity':1,'start':'02:38','end':'04:03'},
 'G45':{'country':'中国','region':'钓鱼岛海域','task':'防空反导训练','quantity':1,'start':'20:20','end':'22:45'},
}
cases=[]
for i,(cat,day,op,po,batch,assoc,include,basis) in enumerate(specs,1):
    d=ROOT/'赛题2-初赛/数据'/day
    refs={}
    for source,prefix in [('开源军情',op),('网上舆论',po)]:
        if prefix:
            path=next((d/source).glob(prefix+'_*'))
            t=path.read_text(encoding='utf-8-sig');body=t.split('正文：')[-1].split('主题词：')[0].strip()
            refs[source]={'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'body':body}
    # For non-specified batches the original Excel is searched by raw platform/time,
    # keeping candidate row snapshots for manual audit. The test resolves by open path.
    if batch:
        path=next(d.glob('*.xlsx'));w=load_workbook(path,data_only=True)
        s=w['飞机' if batch.startswith('AIR') else '舰船'];hdr=list(s.values)[0]
        rr=[{'row':j,**dict(zip(hdr,r))} for j,r in enumerate(list(s.values)[1:],2) if r[0]==batch]
        refs['雷达']={'path':path.relative_to(ROOT).as_posix(),'sheet':s.title,'batch':batch,'rows':rr}
        w.close()
    cases.append({'id':f'G{i:02d}','category':cat,'date':day,'expect_association':assoc,'expect_include':include,'expected_fields':field_truth.get(f'G{i:02d}',{}),'basis':basis,'refs':refs})
(BASE/'audit/gold_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
print('frozen raw-only labels:',len(cases))
