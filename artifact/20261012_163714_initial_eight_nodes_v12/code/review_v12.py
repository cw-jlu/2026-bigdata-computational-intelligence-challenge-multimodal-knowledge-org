"""Audit this visual-only revision against its retained v11 baseline."""
from common import *
from docx import Document
from lxml import etree
from copy import deepcopy
from zipfile import ZipFile
import charts

def without_picture_sizes(doc):
    body=deepcopy(doc._element.body)
    for e in body.iter():
        if etree.QName(e).localname in ['extent','ext']:
            for a in ['cx','cy']:e.attrib.pop(a,None)
    return etree.tostring(body,method='c14n')

def main():
    old=BASE.parent/'20261012_160950_initial_eight_nodes_v11';nodes=[]
    for n in NODES:
        a=old/f'official/{n}';b=BASE/f'official/{n}';da=Document(a/f'{n}日报.docx');db=Document(b/f'{n}日报.docx')
        assert [p.text for p in da.paragraphs]==[p.text for p in db.paragraphs]
        assert without_picture_sizes(da)==without_picture_sizes(db),n
        assert sha(a/f'{n}机舰活动明细.xlsx')==sha(b/f'{n}机舰活动明细.xlsx')
        for name in ['frozen_ledger.json','analysis_snapshot.json','chart_data.json','workbook_input.json']:
            assert sha(old/f'audits/{n}/{name}')==sha(BASE/f'audits/{n}/{name}'),(n,name)
        with ZipFile(a/f'{n}日报.docx') as za,ZipFile(b/f'{n}日报.docx') as zb:
            for name in ['word/styles.xml','word/fontTable.xml','word/settings.xml']:
                assert za.read(name)==zb.read(name),(n,name)
            embedded={hashlib.sha256(zb.read(p)).hexdigest() for p in zb.namelist() if p.startswith('word/media/')}
        for name in charts.NAMES:
            assert sha(b/'附件图表'/name) in embedded
            assert sha(b/'附件图表'/name)!=sha(a/'附件图表'/name)
        rows={'node':n,'daily_events':len(load(BASE/f'audits/{n}/frozen_ledger.json')['today_events']),'frozen_facts_unchanged':True,'analysis_unchanged':True,'docx_text_unchanged':True,'docx_body_except_image_dimensions_unchanged':True,'docx_fonts_styles_settings_unchanged':True,'xlsx_byte_identical':True,'chart_values_and_membership_identical':True,'four_pngs_restyled_and_embedded':True}
        nodes.append(rows)
    save(BASE/'visual_revision_comparison.json',{'baseline':old.name,'scope':'v12仅图表视觉修订；DOCX图片尺寸随纵横比适配','nodes':nodes,'daily_events':sum(n['daily_events'] for n in nodes),'status':'PASS','platform_evaluation':None})
    print('VISUAL-ONLY COMPARISON PASS: 205 facts, prose, fonts and 8 XLSX unchanged; 32 new PNGs embedded.')

if __name__=='__main__':main()
