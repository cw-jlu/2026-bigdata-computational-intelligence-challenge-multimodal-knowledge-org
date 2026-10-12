"""Persist engineer-authored expectations BEFORE evaluating v3. No v3 import/output."""
import json,hashlib
from pathlib import Path
V=Path(__file__).resolve().parents[1]
raw={d['date']:d for d in map(json.loads,(V/'audit/raw_snapshot.jsonl').open(encoding='utf-8'))}
# Expectations transcribed after reading original bodies and whole radar groups.
# Each tuple: date,batch,included,field assertions,basis. Not official ground truth.
dev=[
('2025.5.10','AIR-AF10F9EBB9E18A',1,{'country':'日本','quantity':1},'军情048双平台各自数量，舆论044与雷达05:07至07:32反潜；不可用SH60K子证据'),
('2025.5.10','SHIP-0AB0D8C5EB8110',1,{'region':'上海外海','task':'自由航行'},'军情013上海外海时段；舆论048东海一艘；雷达全批上海外海'),
('2025.5.10','AIR-093CB109918635',0,{},'军情023给RC135W两架，但没有同平台舆论，不能以P8A替代'),
('2025.5.10','SHIP-68266087799BA6',0,{},'军情022两艘、舆论005一艘、雷达一艘，数量冲突且地中海非核心'),
('2025.5.18','AIR-1CC2A2CC80B4D1',1,{'region':'南海'},'军情010北康暗沙、舆论005南海空中警戒；全雷达两条持续分支。仅南海分支兼容，两文本未双证细区'),
('2025.5.18','SHIP-ECABEF995CFE86',0,{},'福建号青岛与冲绳两时段；舆论022东海反潜不支持黄海当次活动'),
('2025.5.30','AIR-2CED63D9B93476',1,{'region':'南海','task':'情报监视侦察'},'军情020仁爱礁具体区域仅单类；舆论017与雷达双证任务，细区不得填充'),
('2025.5.30','SHIP-29CFC354BE658A',1,{'region':'海南岛东南海域'},'军情021与舆论019和全雷达区域一致'),
('2025.5.30','AIR-D259B796A74070',0,{},'军情041舆论043越南苏30MK2黑海；不能关联温州苏30MKM'),
('2025.5.30','SHIP-BC7F7098D5891F',0,{},'补给舰渤海海峡三源相符但非核心，无明确进入三海证据'),
('2025.6.9','AIR-74C830734B7E44',1,{'region':'黄海'},'无侦7当日14:17至16:42全雷达黄海，文本细区未双类核实'),
('2025.6.9','AIR-17158C46B3466C',0,{},'英国梅林全轨迹中太平洋，三源相符但非核心'),
('2025.6.9','SHIP-06BADA890B9E98',0,{},'039A塔斯曼海三源相符但非核心'),
('2025.6.17','SHIP-37F0DC0E1C2114',1,{'region':'连云港外海'},'军情041早段联合巡航、舆论001细区；军情035晚段不能合并'),
('2025.6.17','SHIP-6730D1DD73162A',0,{},'901早段连云港仅军情041与雷达；舆论018为晚段补给任务，不够三源'),
('2025.6.17','AIR-EE80F16DB64B1B',1,{'interval':[483,628],'region':'东海'},'军情001温州08:03至10:28；舆论030东海联合巡逻一架；晚段油气田数量矛盾不得抢占此证据'),
('2025.6.29','AIR-0D82C71F1168E5',1,{'region':'北部湾'},'军情028北部湾精确任务时段、舆论005同细区退出、雷达全点连续'),
('2025.6.29','SHIP-F074EEF8CFC29A',1,{'region':'北康暗沙海域'},'辽宁早段北康部署不同于晚段中沙巡航'),
('2025.6.29','AIR-9FEEE24198FA00',0,{},'B52鄂霍次克海非核心'),
('2025.6.29','SHIP-6351219F599C74',0,{},'军情024及雷达11:39开始，舆论036明确行动时段12:52开始，未说明观测子窗口，保持冲突'),
('2025.7.9','AIR-6987CB8DEA50B8',1,{'region':'东沙群岛海域'},'歼11B军情049及舆论018细区同；军情047早段长江口另一活动'),
('2025.7.9','SHIP-AF41F705A929BC',1,{'region':'东海中部'},'山东军情002舆论015早段部署；军情024舆论029晚段北部不可合并'),
('2025.7.9','AIR-19BFB95853D451',0,{},'军情032F35B两架，但缺同平台舆论'),
('2025.7.17','AIR-C15D6D93C98ECD',0,{},'福克50孟加拉湾非核心'),
('2025.7.17','SHIP-FFA2892E84A5DC',0,{},'054A珊瑚海非核心，不与黄海两次活动合并'),
('2025.7.17','AIR-CE2DA13274C502',1,{'region':'东海','task':'情报监视侦察'},'无侦军情036舆论00217:35至19:00配东海分支；20:00台湾舆论不能误配中国'),
]
# Reserved source audit: v2-stratified ordinary inclusions and exclusions. These
# expectations never feed repairs. Overlap in raw documents with development is
# disclosed, so this is a reserved record audit, not an IID independent test set.
reserved=[
('2025.5.10','AIR-3B564DE1F3DD6D',1,{'quantity':1,'region':'南海'},'军情023P8A一架非RC135W两架；舆论032联合巡逻20:09至22:34'),
('2025.5.10','SHIP-65264CA1B8CB37',1,{'region':'东海南部'},'军情006一艘细区，舆论047东海精确时段，雷达细区'),
('2025.5.18','AIR-21D56C7A7D64EE',1,{'country':'美国','region':'南海'},'军情047纳土纳巡逻，舆论024美军一架；全点南海；细区单文本'),
('2025.5.18','SHIP-5946CAFDE26C1A',1,{'region':'钓鱼岛海域'},'军情044舆论008法国地平线同具体区域'),
('2025.5.30','AIR-6D87BDE4F5F959',1,{'region':'南海','task':'电子侦察'},'军情042EA18G一架细区；舆论042仅南海20:31至22:56，编号相同只定位'),
('2025.5.30','SHIP-7AE284DDE9E3AF',1,{'region':'赤尾屿海域'},'军情014及全雷达赤尾屿战备，舆论031东海一艘'),
('2025.6.9','AIR-900D3E39F755EC',1,{'task':'电子侦察'},'军情034明确11:21至13:46电子侦察，舆论004英国一架同任务'),
('2025.6.9','SHIP-DAC6E72221D22D',1,{'region':'南海','interval':[494,639]},'军情043舆论037戴高乐08:14至10:39编队警戒，非晚段联合巡航'),
('2025.6.17','AIR-15297A9B050E29',1,{'region':'南海','task':'反潜巡逻'},'军情012P8A与F35A早段，舆论036澳方一架南海；黄海是另次活动'),
('2025.6.17','SHIP-FBF2A35D9790DF',1,{'region':'青岛外海'},'军情043舆论042台湾康定同细区，母港/舰体舷号不双源核实'),
('2025.6.29','AIR-E13BD57A156414',1,{'quantity':1,'region':'黄海'},'军情016F35A一架、MC55A两架，舆论023F35A空中警戒'),
('2025.6.29','SHIP-30C0D1B212BAC3',1,{'region':'南海北部'},'军情035维克兰特一艘细区，舆论003南海具名舰时段，雷达细区'),
('2025.7.9','AIR-E6002140F96CB5',1,{'region':'曾母暗沙海域'},'军情044舆论045RQ4同细区；雷达全点校核，型号用途不作任务依据'),
('2025.7.9','SHIP-CBF728BABB4814',1,{'region':'南康暗沙海域'},'军情014细区一艘，舆论022南海17:24至19:49反潜；雷达细区'),
('2025.7.17','AIR-85185794114528',1,{'quantity':2,'region':'东海'},'军情017B52训练08:14至10:39，舆论019两架东海；全雷达两架'),
('2025.7.17','SHIP-F1DA41EB38AC4D',1,{'region':'万安滩海域'},'军情010猎豹万安滩，舆论009南海一艘例行部署，雷达同细区'),
('2025.5.10','AIR-3B6F61E3F12895',0,{},'军情017孟加拉湾，舆论039安达曼海同时间对海突击，具体区域互冲突'),
('2025.5.18','AIR-9125036AEE9867',0,{},'军情030台湾E2K预警指挥，舆论031及全雷达情报监视侦察，明确任务冲突'),
('2025.5.30','AIR-C79BCBFCEFACE4',0,{},'军情048韩国E737宁波两架，舆论016及雷达一架，数量明确冲突'),
('2025.6.9','AIR-56868B35824176',0,{},'法国大西洋2军情031孟加拉湾、舆论017安达曼海同时间联合巡逻，区域冲突'),
('2025.6.17','AIR-22F9D447BC6296',0,{},'日本F15J军情017温州空中警戒与舆论006及雷达对海突击训练冲突'),
('2025.6.29','AIR-CB26BFFF95D0CA',0,{},'军情001歼15与歼20拆开；歼15缺同平台舆论不能用歼20替代'),
('2025.7.9','AIR-7737E779E0E243',0,{},'澳P8A军情01318:10开始，舆论041及雷达17:29开始；同日期核心海域不解决明确时间差'),
('2025.7.17','AIR-03D99EFF28BDEC',0,{},'澳MC55军情035东沙、舆论043上海，细区与核心海域不同'),
]
def freeze(records,name):
    cases=[]
    for i,(date,batch,n,fields,basis) in enumerate(records,1):
        rows=[r for r in raw[date]['radar'] if r['data']['批号']==batch]
        if not rows: # retain explicit annotation error rather than fabricate location
            cases.append({'id':name+str(i),'date':date,'batch':batch,'label_status':'invalid_locator','original_expected':n,'basis':basis});continue
        platform=rows[0]['data'].get('目标类型',rows[0]['data'].get('机舰名'))
        # Review bundle includes ALL same-model text from the existing raw-only
        # diagnostic, otherwise whole day to avoid selecting favorable evidence.
        texts=raw[date]['texts']
        cases.append({'id':name+str(i),'date':date,'batch':batch,'included':n,'fields':fields,'basis':basis,'raw_radar':rows,'raw_texts':texts,'label_status':'human_reviewed'})
    path=V/'audit'/('new_'+name+'_cases.json')
    path.write_text(json.dumps({'method':'Engineer source review; v2 only supplies membership strata, never labels. No v3 evaluation before this freeze. Purposeful sample; do not extrapolate. Reserved document overlap disclosed.','cases':cases},ensure_ascii=False,indent=2),encoding='utf-8')
    return {'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':len(cases),'invalid_locators':sum(c['label_status']!='human_reviewed' for c in cases)}
(V/'audit/new_cases_freeze.json').write_text(json.dumps([freeze(dev,'development'),freeze(reserved,'reserved')],indent=2),encoding='utf-8')
print('Human expectations persisted; no candidate output inspected.')
