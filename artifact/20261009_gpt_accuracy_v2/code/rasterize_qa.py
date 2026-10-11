import json
import sys
from pathlib import Path
import fitz
from PIL import Image,ImageDraw,ImageFont
root=Path(sys.argv[1]); summaries=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for pdf in sorted(root.glob('*/report.pdf')):
    doc=fitz.open(pdf); imgs=[]; blank=[]; overflow=[]
    for i,p in enumerate(doc):
        png=pdf.parent/f'page-{i+1}.png'; pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5)); pix.save(png)
        imgs.append(png)
        if len(p.get_text().strip())<15 and not p.get_images(): blank.append(i+1)
        for b in p.get_text('blocks'):
            if b[0]<-1 or b[1]<-1 or b[2]>p.rect.width+1 or b[3]>p.rect.height+1: overflow.append(i+1)
    for start in range(0,len(imgs),4):
        sheet=Image.new('RGB',(1800,2600),'#CDD2D8'); draw=ImageDraw.Draw(sheet)
        for k,path in enumerate(imgs[start:start+4]):
            im=Image.open(path).convert('RGB'); im.thumbnail((880,1240)); x=(k%2)*900+(900-im.width)//2; y=(k//2)*1300+35
            sheet.paste(im,(x,y)); draw.text((x,y-28),pdf.parent.name+f'  page {start+k+1}',font=font,fill='black')
        sheet.save(pdf.parent/f'contact-{start//4+1}.png')
    # Remove only obsolete generated QA pictures inside the explicitly supplied
    # QA directory; never recurse or follow a junction into another workspace.
    for pattern,limit in [('page-*.png',len(imgs)),('contact-*.png',(len(imgs)+3)//4)]:
        for stale in pdf.parent.glob(pattern):
            number=int(stale.stem.rsplit('-',1)[1])
            if number>limit and stale.resolve().is_relative_to(root.resolve()): stale.unlink()
    summaries.append({'date':pdf.parent.name,'pages':len(imgs),'blank_pages':blank,'text_outside_page':sorted(set(overflow)),'engine':'Word PDF + PyMuPDF 108dpi'})
    doc.close()
(root/'raster_checks.json').write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summaries,ensure_ascii=False))
