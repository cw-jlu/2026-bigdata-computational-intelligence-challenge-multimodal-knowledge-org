from common import *
import os,subprocess,sys,shutil,argparse
PY=sys.executable
NODE='C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
def run(args,log):
    p=subprocess.run(args,capture_output=True,text=True,encoding='utf8',env={**os.environ,'PYTHONIOENCODING':'utf-8'});log.write(p.stdout+p.stderr);log.flush();p.check_returncode()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--node',default=NODE);args=ap.parse_args();dest=args.output.resolve()
    if dest.exists():raise RuntimeError('Use a new reproduction directory; existing output is never replaced')
    dest.mkdir(parents=True);shutil.copytree(BASE/'evidence/external',dest/'evidence/external')
    with (dest/'run.log').open('w',encoding='utf8') as log:
        print('Re-reading all original three-source inputs',flush=True);run([PY,str(BASE/'code/prepare.py'),'--output',str(dest)],log)
        import select_v11;select_v11.select(dest)
        # Replay the reviewed prose snapshots against freshly computed facts.
        # This reproduces saved analysis, not a claim of fresh model generation.
        for n in NODES:shutil.copyfile(BASE/f'audits/{n}/analysis_snapshot.json',dest/f'audits/{n}/analysis_snapshot.json')
        print('Generating all eight nodes from fresh frozen ledgers',flush=True);run([PY,str(BASE/'code/build.py'),'--output',str(dest)],log)
        run([args.node,str(BASE/'code/workbooks.mjs'),str(dest)],log)
        run([PY,str(BASE/'code/validate.py'),'--output',str(dest)],log)
    comparisons=[]
    from docx import Document
    from openpyxl import load_workbook
    from PIL import Image,ImageChops
    for n in NODES:
        a=BASE/f'audits/{n}/frozen_ledger.json';b=dest/f'audits/{n}/frozen_ledger.json';assert sha(a)==sha(b),(n,'frozen ledger')
        assert (BASE/f'audits/{n}/analysis.md').read_bytes()==(dest/f'audits/{n}/analysis.md').read_bytes()
        da=Document(BASE/f'official/{n}/{n}日报.docx');db=Document(dest/f'official/{n}/{n}日报.docx');assert da._element.body.xml==db._element.body.xml
        wa=load_workbook(BASE/f'official/{n}/{n}机舰活动明细.xlsx');wb=load_workbook(dest/f'official/{n}/{n}机舰活动明细.xlsx');assert wa.sheetnames==wb.sheetnames
        for s in wa.sheetnames:
            assert list(wa[s].values)==list(wb[s].values);assert [[c.data_type for c in r] for r in wa[s]]==[[c.data_type for c in r] for r in wb[s]]
        for p in (BASE/f'official/{n}/附件图表').glob('*.png'):
            q=dest/f'official/{n}/附件图表'/p.name;assert sha(p)==sha(q),(n,p.name)
        comparisons.append({'date':n,'raw_facts_recomputed':True,'frozen_sha256_equal':True,'analysis_equal':True,'docx_body_xml_equal':True,'xlsx_values_and_types_equal':True,'png_sha256_equal':True,'formal_package_members_verified':True})
    save(BASE/'reproduction_comparison.json',{'status':'PASS','output':str(dest),'nodes':comparisons,'container_difference_policy':'DOCX/XLSX ZIP member timestamps and core created/modified timestamps may differ; content, schema and PNGs must match'})
    print('ALL EIGHT RAW-INPUT REPRODUCTION CHECKS PASS',flush=True)
if __name__=='__main__':main()
