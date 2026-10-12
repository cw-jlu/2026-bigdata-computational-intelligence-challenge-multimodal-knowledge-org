import json
import sys
from pathlib import Path
import fitz
from PIL import Image,ImageDraw,ImageFont
root=Path(sys.argv[1]); font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22); imgs=[]
for pdf in sorted(root.glob('*.pdf')):
    doc=fitz.open(pdf); p=doc[0]; p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(pdf.with_suffix('.png')); imgs.append(pdf.with_suffix('.png')); doc.close()
for start in range(0,len(imgs),4):
    sheet=Image.new('RGB',(2400,1700),'#CCD2D8'); draw=ImageDraw.Draw(sheet)
    for i,path in enumerate(imgs[start:start+4]):
        im=Image.open(path); im.thumbnail((2370,375)); sheet.paste(im,((2400-im.width)//2,i*420+30)); draw.text((25,i*420+5),path.stem,font=font,fill='black')
    sheet.save(root/f'contact-{start//4+1}.png')
print('Native Excel sheet PNGs:',len(imgs))
