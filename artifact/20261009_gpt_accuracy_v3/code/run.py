"""From original TXT/XLSX to all eight node answers, evidence, validation, ZIP."""
import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from inspect_raw import main as inspect_input
from reconstruct import run as reconstruct
from validate import check

V=Path(__file__).resolve().parents[1];ROOT=V.parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,default=ROOT/'赛题2-初赛/数据');p.add_argument('--output',type=Path,default=V/'output');p.add_argument('--audit',type=Path,default=V/'audit');p.add_argument('--reuse-verified-snapshot',action='store_true',help='Optional debugging only; default rereads all original inputs');p.add_argument('--docx-python',type=Path);p.add_argument('--node',type=Path);p.add_argument('--portable-xlsx',action='store_true');a=p.parse_args()
    begin=time.time();a.output.mkdir(parents=True,exist_ok=True);a.audit.mkdir(parents=True,exist_ok=True)
    if not a.reuse_verified_snapshot: inspect_input(a.input,a.audit)
    snapshot=a.audit/'raw_snapshot.jsonl';inter=a.output/'中间证据';daily=a.output/'日报'
    reconstruct(snapshot,inter)
    runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
    docx_python=a.docx_python or (runtime/'python/python.exe' if (runtime/'python/python.exe').exists() else Path(sys.executable))
    node=a.node or (runtime/'node/bin/node.exe' if (runtime/'node/bin/node.exe').exists() else None)
    commands=[]
    def execute(command):
        commands.append([str(x) for x in command]);print('running',Path(str(command[1])).name,flush=True)
        subprocess.run([str(x) for x in command],check=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    execute([sys.executable,V/'code/charts.py',inter,daily])
    execute([docx_python,V/'code/report.py',inter,daily])
    artifact_available=(V/'code/node_modules/@oai/artifact-tool').exists()
    if node and artifact_available and not a.portable_xlsx:
        execute([node,V/'code/workbooks.mjs',inter/'workbook_rows.json',daily,a.audit/'xlsx_visual']);engine='@oai/artifact-tool'
    else:
        execute([docx_python,V/'code/workbooks_fallback.py',inter/'workbook_rows.json',daily]);engine='openpyxl portable fallback (artifact tool unavailable or explicitly requested)'
    validation=check(a.output,snapshot)
    info={'seconds':round(time.time()-begin,2),'python':sys.version,'os':platform.platform(),'cpu':platform.processor(),'commands':commands,'xlsx_engine':engine,'docx_python':str(docx_python),'seed':4601,
        'input':str(a.input.resolve()),'output':str(a.output.resolve()),'original_input_reread':not a.reuse_verified_snapshot,
        'dependencies':{name:importlib.metadata.version(name) for name in ['openpyxl','python-docx','matplotlib','Pillow']},'validation_ok':validation['ok']}
    (a.audit/'full_run.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    if not validation['ok']: raise SystemExit('validation failed')
    print('all eight node answers and submission ZIP validated',flush=True)

if __name__=='__main__':main()
