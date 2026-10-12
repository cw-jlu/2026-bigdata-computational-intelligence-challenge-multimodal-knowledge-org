"""Rasterize real Office PDFs and check text/page geometry, not a recreated table."""
import argparse,hashlib,json,re
from pathlib import Path
import fitz
from PIL import Image,ImageOps,ImageDraw
V=Path(__file__).resolve().parents[1]
def main(root):
    records=[]
    for pdf in sorted(root.rglob('*.pdf')):
        doc=fitz.open(pdf);pngs=[];checks=[]
        for i,page in enumerate(doc,1):
            out=pdf.with_name(pdf.stem+f'_page_{i:02d}.png');page.get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(out);pngs.append(out)
            text=page.get_text();bad=[];spans=[]
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        box=fitz.Rect(span['bbox'])
                        if not page.rect.contains(box):bad.append({'text':span['text'],'bbox':span['bbox']})
                        spans.append({'text':span['text'],'bbox':span['bbox'],'size':span['size']})
            checks.append({'page':i,'png':str(out),'text_characters':len(text),'blank':not text.strip(),'outside_page':bad,'replacement_glyphs':text.count('\ufffd'),'text_spans':spans})
        records.append({'pdf':str(pdf),'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(doc),'checks':checks})
        # Contact sheet is a navigation aid. Full page PNGs remain available.
        thumbs=[]
        for p in pngs:
            im=Image.open(p).convert('RGB');im.thumbnail((560,800));tile=Image.new('RGB',(580,830),'#dce1e5');tile.paste(im,((580-im.width)//2,25));ImageDraw.Draw(tile).text((8,6),p.name,fill='black');thumbs.append(tile)
        for offset in range(0,len(thumbs),4):
            group=thumbs[offset:offset+4];board=Image.new('RGB',(1160,830*((len(group)+1)//2)),'white')
            for i,im in enumerate(group):board.paste(im,((i%2)*580,(i//2)*830))
            board.save(pdf.with_name(pdf.stem+f'_contact_{offset//4+1}.png'))
    (root/'raster_checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'pdfs':len(records),'pages':sum(r['pages'] for r in records),'blank_pages':sum(c['blank'] for r in records for c in r['checks']),'outside_page_spans':sum(len(c['outside_page']) for r in records for c in r['checks'])},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);main(p.parse_args().root)
