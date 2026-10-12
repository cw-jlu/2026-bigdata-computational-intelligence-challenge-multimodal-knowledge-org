"""Verify archived bytes, source roles and dates; does not grade analysis or event truth."""
from pathlib import Path
import hashlib,json,argparse
from pypdf import PdfReader
BASE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write-manifest',action='store_true');args=parser.parse_args()
    rows=json.loads((BASE/'source_catalog.json').read_text(encoding='utf-8'))['sources']
    assert len(rows)==9 and len({r['id'] for r in rows})==9
    local=[r for r in rows if r['local_original']]
    assert len(local)==6
    for r in local:
        v=r['local_original'];p=BASE/v['path']
        assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],r['id']
        assert sha(BASE/v['text_path'])==v['text_sha256'],r['id']
        if p.suffix=='.pdf':assert len(PdfReader(p).pages)=={'R01':6,'R02':45,'R06':1,'R07':1}[r['id']]
    for r in rows:
        assert not r['event_truth_source']
        assert not (r['role']=='method' and r['may_count_as_external_empirical_background'])
        assert all(r['published_by']<=n for n in r['eligible_nodes_by_date'])
    assert {r['id'] for r in rows if not r['historical_content_approved']}=={'R04','R05','R09'}
    nodes=json.loads((BASE/'node_eligibility.json').read_text(encoding='utf-8'))['nodes']
    assert len(nodes)==8 and all(n['event_validation_sources']==[] for n in nodes)
    paths=sorted(p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in {'manifest.json','validation.json'})
    actual=[{'path':p.relative_to(BASE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    if args.write_manifest:save(BASE/'manifest.json',{'files':actual,'self_and_validation_excluded':True})
    assert json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))['files']==actual,'Archive manifest mismatch'
    result={'status':'PASS','scope':'bytes, expected PDF pages, metadata consistency and node date/role guards only','sources':9,'downloaded_originals':6,'pdfs':4,'html_originals':2,'archived_files_checked':len(actual),'historical_web_content_unverified':['R04','R05','R09'],'full_download_unavailable':['R03'],'event_facts_reverified':False,'analysis_rewrite_completed':False,'platform_score_gain_verified':False}
    save(BASE/'validation.json',result);print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
