"""Fetch declared public sources; never overwrite an archived source with changed bytes."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import argparse, hashlib, json, urllib.request
from pypdf import PdfReader
from html.parser import HTMLParser

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style'}:self.hidden+=1
        if tag in {'p','div','h1','h2','h3','li','br','tr','td','section'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style'}:self.hidden=max(0,self.hidden-1)
        if tag in {'p','div','h1','h2','h3','li','tr','section'}:self.parts.append('\n')
    def handle_data(self,data):
        if not self.hidden:self.parts.append(data)

BASE = Path(__file__).resolve().parent
SOURCES = [
    ('R01', 'https://donohueintellaw.ll.georgetown.edu/sites/default/files/assets/ICD%20203%20Analytic%20Standards.pdf', 'pdf'),
    ('R02', 'https://www.cia.gov/resources/csi/static/Tradecraft-Primer-apr09.pdf', 'pdf'),
    ('R03', 'https://www.gao.gov/assets/gao-20-283g.pdf', 'pdf'),
    ('R04', 'https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/quality-assessment-in-data-linkage', 'html'),
    ('R05', 'https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/longitudinal-linkage-of-administrative-data-design-principles-and-the-total-error-framework', 'html'),
    ('R06', 'https://www.mod.go.jp/msdf/en/release/202502/20250206-1en.pdf', 'pdf'),
    ('R07', 'https://www.mod.go.jp/en/images/1124a_usa_aus-j.pdf', 'pdf'),
    ('date_R03', 'https://www.gao.gov/products/gao-20-283g', 'html'),
    ('date_R04_R05', 'https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods', 'html'),
    ('date_R07', 'https://www.mod.go.jp/en/article/2023/11/8dfa1a2eef63c347c71faf9d76d96c3dbbc7c936.html', 'html'),
    ('rights_JMOD', 'https://www.mod.go.jp/en/notice.html', 'html'),
    ('rights_OGL', 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/', 'html'),
]

def fetch(item):
    sid,url,kind=item
    record={'id':sid,'url':url,'accessed_at':datetime.now(timezone.utc).isoformat()}
    try:
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (public-document research)'})
        with urllib.request.urlopen(request,timeout=50) as response:
            content=response.read()
            record.update(final_url=response.url,status_code=response.status,content_type=response.headers.get('Content-Type'),last_modified=response.headers.get('Last-Modified'))
        if kind=='pdf':assert content.startswith(b'%PDF'), 'Response is not a PDF'
        digest=hashlib.sha256(content).hexdigest()
        relative=Path('originals' if sid.startswith('R0') else 'provenance')/(sid+'.'+kind)
        path=BASE/relative
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Remote bytes changed; archive not overwritten')
        path.write_bytes(content)
        if kind=='pdf':
            doc=PdfReader(path)
            pages=[{'pdf_page':i+1,'text':p.extract_text() or ''} for i,p in enumerate(doc.pages)]
            record['pages']=len(pages)
            extracted='\n\n'.join(f'=== PDF PAGE {p["pdf_page"]} ===\n{p["text"]}' for p in pages)
        else:
            parser=TextParser(); parser.feed(content.decode('utf-8',errors='replace'))
            extracted='\n'.join(line.strip() for line in ''.join(parser.parts).splitlines() if line.strip())
        textpath=BASE/'extracted'/(sid+'.txt')
        textpath.parent.mkdir(exist_ok=True)
        textpath.write_text(extracted,encoding='utf-8')
        record.update(status='downloaded',path=relative.as_posix(),sha256=digest,bytes=len(content),text_path=textpath.relative_to(BASE).as_posix(),text_sha256=hashlib.sha256(textpath.read_bytes()).hexdigest())
    except Exception as exc:
        record.update(status='failed',error=str(exc))
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New empty directory; archive is never overwritten')
    args=parser.parse_args()
    BASE=args.output.resolve()
    if BASE.exists() and any(BASE.iterdir()):raise SystemExit('Output must be a new or empty directory')
    BASE.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,SOURCES))
    (BASE/'retrieval_log.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for r in rows:print(r['id'],r['status'],r.get('bytes',r.get('error')),flush=True)
