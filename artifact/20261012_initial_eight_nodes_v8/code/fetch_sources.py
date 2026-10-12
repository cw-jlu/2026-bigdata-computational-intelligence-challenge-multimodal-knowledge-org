from common import *
import urllib.request,re
from pypdf import PdfReader
import pypdfium2 as pdfium
FILES={'B01':'https://www.mod.go.jp/en/images/ea07e6ad451bbc35d870ab43fa2b402fd8537d17.pdf','B02':'https://www.nzdf.mil.nz/assets/Uploads/DocumentLibrary/NZDF-Annual-Report-2024_Web-version.pdf','B03':'https://www.defence.gov.au/sites/default/files/2024-10/Defence-Annual-Report-2023-24_FA.pdf'}
def main():
    p=BASE/'evidence/external';p.mkdir(parents=True,exist_ok=True)
    for sid,u in FILES.items():
        try:
            req=urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'})
            f=p/(sid+'.pdf')
            if f.exists():headers={};rd=PdfReader(f)
            else:
                with urllib.request.urlopen(req,timeout=50) as r:b=r.read();headers=dict(r.headers)
                f.write_bytes(b);rd=PdfReader(f)
            pdf=pdfium.PdfDocument(str(f))
            found=[]
            for i in range(len(pdf)):
                txt=pdf[i].get_textpage().get_text_range()
                terms=['HMNZS Aotearoa','Lekiu','Growler','Bersama','Malaysia','Pitch Black'] if sid!='B01' else ['maritime']
                if any(t.lower() in txt.lower() for t in terms):
                    found.append({'pdf_page':i+1,'text':txt});(p/f'{sid}_p{i+1}.txt').write_text(txt,encoding='utf8')
            save(p/(sid+'_access.json'),{'url':u,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'headers':headers,'metadata':dict(rd.metadata),'sha256':sha(f),'pages':len(rd.pages),'candidate_pages':[x['pdf_page'] for x in found],'reading_status':'pipeline_pdf_text_extraction; human_content_review_pending'})
            print(sid,dict(rd.metadata),'candidate pages',[x['pdf_page'] for x in found],flush=True)
        except Exception as e:save(p/(sid+'_error.json'),{'url':u,'error':str(e)});print(sid,'ERROR',e,flush=True)
if __name__=='__main__':main()
