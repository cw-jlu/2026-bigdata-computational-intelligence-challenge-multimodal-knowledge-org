from common import *
import pypdfium2 as f
from raster_qa import contacts
def main(out=BASE):
 for n in NODES:
  p=out/f'qa/xlsx_native/{n}';files=[];texts=[]
  for pdf in sorted(p.glob('*.pdf')):
   doc=f.PdfDocument(str(pdf))
   for i in range(len(doc)):
    name=p/f'{pdf.stem}-{i+1}.png';doc[i].render(scale=1.2).to_pil().save(name);files.append(name);texts.append({'file':pdf.name,'page':i+1,'text':doc[i].get_textpage().get_text_range()})
  save(out/f'audits/{n}/xlsx_native_rendered_text.json',texts);contacts(files,p,'contact',4)
  print(n,len(files),'native Excel page images',flush=True)
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=BASE);main(ap.parse_args().output.resolve())
