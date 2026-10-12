from common import *
from PIL import Image,ImageDraw,ImageFont
import pypdfium2 as pdfium
def contacts(files,folder,prefix,count=4):
    for off in range(0,len(files),count):
        fs=files[off:off+count];tiles=[]
        for f in fs:
            im=Image.open(f).convert('RGB');im.thumbnail((1200,1740));tiles.append((f.name,im))
        cellw=1220;cellh=max(im.height for _,im in tiles)+42;can=Image.new('RGB',(cellw*2,cellh*((len(fs)+1)//2)),'#DDE2E7');d=ImageDraw.Draw(can)
        for i,(name,im) in enumerate(tiles):
            x=i%2*cellw;y=i//2*cellh;d.text((x+10,y+10),name,fill='black');can.paste(im,(x+10,y+35))
        can.save(folder/f'{prefix}-{off//count+1}.png')
def main():
    records=[]
    for n in NODES:
        folder=BASE/f'qa/docx/{n}';pdf=pdfium.PdfDocument(str(folder/'report.pdf'));files=[];text=[]
        for i in range(len(pdf)):
            p=folder/f'page-{i+1:02d}.png';pdf[i].render(scale=1.5).to_pil().save(p);files.append(p);t=pdf[i].get_textpage().get_text_range();text.append({'page':i+1,'text':t,'chars':len(t),'width':pdf[i].get_width(),'height':pdf[i].get_height()})
        save(BASE/f'audits/{n}/rendered_text.json',text);contacts(files,folder,'contact',4);records.append({'node':n,'pages':len(pdf),'page_pngs':[p.relative_to(BASE).as_posix() for p in files]})
        xfolder=BASE/f'qa/xlsx/{n}';contacts(sorted(xfolder.glob('*.png')),xfolder,'contact',4)
        cfolder=BASE/f'qa/charts/{n}';cfolder.mkdir(parents=True,exist_ok=True);contacts(sorted((BASE/f'official/{n}/附件图表').glob('*.png')),cfolder,'contact',4)
        print(n,'pages',len(pdf),flush=True)
    save(BASE/'raster_records.json',records)
if __name__=='__main__':main()
