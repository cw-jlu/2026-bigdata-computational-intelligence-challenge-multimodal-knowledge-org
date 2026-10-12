"""Complete deterministic run. Model-free; optional supplied primary runtime paths."""
import argparse,os,subprocess,sys,time,json,platform
from pathlib import Path
from extract import extract
from prepare import make
from events import NODES

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--reuse-evidence',action='store_true');a.add_argument('--doc-python',default=sys.executable);a.add_argument('--node',default='node');x=a.parse_args()
    start=time.perf_counter();base=Path(__file__).resolve().parent;x.output=x.output.resolve();x.output.mkdir(parents=True,exist_ok=True)
    if not x.reuse_evidence:extract(x.input,x.output)
    make(x.output)
    subprocess.run([sys.executable,str(base/'charts.py'),'--output',str(x.output)],check=True)
    subprocess.run([x.doc_python,str(base/'report.py'),'--output',str(x.output)],check=True)
    subprocess.run([x.node,str(base/'workbook.mjs'),str(x.output)],check=True)
    subprocess.run([sys.executable,str(base/'validate.py'),'--input',str(x.input.resolve()),'--output',str(x.output)],check=True)
    (x.output/'run_record.json').write_text(json.dumps({'seconds':round(time.perf_counter()-start,2),'python':sys.version,'os':platform.platform(),'argv':sys.argv,'doc_python':x.doc_python,'node':x.node,'model_calls':0,'randomness':'none'},ensure_ascii=False,indent=2),encoding='utf-8')
