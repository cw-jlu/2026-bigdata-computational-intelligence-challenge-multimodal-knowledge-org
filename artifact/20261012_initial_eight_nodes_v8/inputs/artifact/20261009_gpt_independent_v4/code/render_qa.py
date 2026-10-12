"""Run packaged DOCX renderer and log every page; PDF is QA-only, never in ZIP."""
import argparse,subprocess,json,os
from pathlib import Path

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--artifact',type=Path,required=True);p.add_argument('--python',required=True);p.add_argument('--renderer',type=Path,required=True);p.add_argument('--soffice-bin',type=Path,required=True);a=p.parse_args();base=a.artifact.resolve();results=[]
    env=dict(os.environ);env['PATH']=str(a.soffice_bin)+os.pathsep+env['PATH'];env['PYTHONIOENCODING']='utf-8'
    for f in sorted((base/'output/日报').glob('*/*日报.docx')):
        dest=base/'audit/docx_preview'/f.parent.name;dest.mkdir(parents=True,exist_ok=True)
        # Remove only task-owned old page images after resolving the exact scope;
        # a shorter new document must not inherit stale last-page screenshots.
        safe=(base/'audit/docx_preview').resolve()
        for old in dest.glob('page-*.png'):
            if not old.resolve().is_relative_to(safe):raise RuntimeError('Unexpected QA path')
            old.unlink()
        cmd=[a.python,str(a.renderer.resolve()),str(f),'--output_dir',str(dest),'--emit_pdf','--verbose']
        r=subprocess.run(cmd,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (dest/'render.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        rr={'date':f.parent.name,'exit_code':r.returncode,'png_pages':len(list(dest.glob('page-*.png'))),'command':cmd};results.append(rr);print(rr['date'],rr['exit_code'],rr['png_pages'],flush=True)
        if r.returncode:raise SystemExit(r.returncode)
    (base/'audit/docx_render.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
