from common import *
import urllib.request,pypdfium2 as pdfium
from pypdf import PdfReader
FILES={'B09':'https://www.mod.go.jp/msdf/en/release/202504/20250416en.pdf','B10':'https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf','B07':'https://www.international.gc.ca/transparency-transparence/assets/pdfs/indo-pacific-indo-pacifique/indo-pacific-indo-pacifique-en.pdf','B05':'https://www.mod.go.jp/msdf/en/release/202503/20250304_2en.pdf'}
def main():
 p=BASE/'evidence/external';p.mkdir(parents=True,exist_ok=True)
 for sid,u in FILES.items():
  try:
   f=p/(sid+'.pdf')
   with urllib.request.urlopen(u,timeout=45) as r:b=r.read();hdr=dict(r.headers)
   f.write_bytes(b);rd=PdfReader(f);pdf=pdfium.PdfDocument(str(f));save(p/(sid+'_access.json'),{'url':u,'sha256':sha(f),'metadata':dict(rd.metadata),'headers':hdr,'pages':len(pdf),'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
   for i in range(len(pdf)):
    t=pdf[i].get_textpage().get_text_range()
    if sid!='B07' or any(w.lower() in t.lower() for w in ['naval','frigate','military']):
     (p/f'{sid}_p{i+1}.txt').write_text(t,encoding='utf8')
     print(sid,i+1,t[:550] if sid=='B07' else t,flush=True)
  except Exception as e:print('ERROR',sid,e,flush=True)
if __name__=='__main__':main()
