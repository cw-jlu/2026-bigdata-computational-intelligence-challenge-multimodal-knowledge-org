"""Package only this version's reviewed source, evidence and deliverables."""
import hashlib,json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
V=Path(__file__).resolve().parents[1]
def read(p):return json.loads((V/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):(V/p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

def integrity():
    validation=read('output/validation.json');comparison=read('audit/clean_reproduction_comparison.json')
    word=read('audit/docx_visual_release/render_log.json');excel=read('audit/xlsx_native/native_excel_log.json')
    freeze=read('audit/new_cases_freeze.json');old=read('audit/baseline_preservation.json')
    checks={
        'eight_nodes_valid':validation['ok'],
        'standard_zip_48':validation['zip']['files']==48,
        'rendered_docx_exactly_delivered':all(sha(Path(r['docx']))==r['docx_sha256'] for r in word),
        'rendered_xlsx_exactly_delivered':all(sha(V/'output/日报'/r['date']/(r['date']+'机舰活动明细.xlsx'))==r['xlsx_sha256'] for r in excel),
        'frozen_new_cases_unchanged':all(sha(V/'audit'/r['file'])==r['sha256'] for r in freeze),
        'old_497_allowed_files_unchanged':old['checked']==497 and old['all_unchanged'],
        'clean_reproduction_58_equal':len(comparison['comparisons'])==58 and comparison['all_equal'],
        'new_development_pass':read('audit/new_development_results.json')['passed']==26,
        'new_reserved_pass':read('audit/new_reserved_results.json')['passed']==24,
        'old_development_42_pass':read('audit/development42_part28_final.json')['passed']==28 and read('audit/holdout_results.json')['passed']==14,
        'supplemental_development_relations_pass':read('audit/new_relation_results.json')['passed']==10,
        'validator_six_probes_rejected':read('audit/validator_probe_results.json')['all_rejected'],
        'input_invariance_pass':read('audit/invariance_results.json')['ok'],
    }
    save('audit/final_integrity.json',{'all_passed':all(checks.values()),'checks':checks,'submission_zip':{'file':'output/日报_gpt_accuracy_v3.zip','sha256':sha(V/'output/日报_gpt_accuracy_v3.zip')},'official_new_score':None,'warning':'工程与抽样检查不能外推全量准确率或官方分数。'})
    if not all(checks.values()):raise SystemExit(checks)

def package():
    integrity()
    files=[]
    for folder in ['code','config']:
        files.extend(p for p in (V/folder).iterdir() if p.is_file())
    files.extend(p for p in V.glob('*.md'))
    files.extend(p for p in V.glob('requirements*.txt'))
    files.extend(p for p in (V/'output').rglob('*') if p.is_file())
    files.extend(p for p in (V/'audit').iterdir() if p.is_file() and p.name not in ['engineering_manifest.json','engineering_package_validation.json'])
    for folder in ['docx_visual_release','xlsx_native','xlsx_visual']:
        files.extend(p for p in (V/'audit'/folder).rglob('*') if p.is_file())
    # The final clean run metadata is retained; its equal duplicate output and
    # snapshot remain on disk, and are reproducible with the documented command.
    files.extend(p for p in (V/'audit/repro_final').iterdir() if p.is_file() and p.name!='raw_snapshot.jsonl')
    files=sorted(set(files),key=lambda p:p.relative_to(V).as_posix())
    manifest=[{'path':p.relative_to(V).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
    save('audit/engineering_manifest.json',{'version':V.name,'files':manifest,'excluded':'运行时/.venv/node_modules/__pycache__、早期重复渲染、重复清洁输出、损坏验证探针副本；所有原文件仍在版本目录。manifest本身及ZIP事后校验记录不纳入自引用哈希。','raw_data':'原始处理范围快照、输入文件SHA和完整案例原文保留；仓库原TXT/XLSX在外部原目录。'})
    files.append(V/'audit/engineering_manifest.json')
    target=V/'工程交付_gpt_accuracy_v3.zip'
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            zi=ZipInfo(p.relative_to(V).as_posix(),date_time=(2026,10,9,0,0,0));zi.compress_type=ZIP_DEFLATED;zi.external_attr=0o644<<16
            z.writestr(zi,p.read_bytes(),compresslevel=9)
    with ZipFile(target) as z:
        expected=[p.relative_to(V).as_posix() for p in files]
        crc=z.testzip();names=z.namelist();bad=[r['path'] for r in manifest if hashlib.sha256(z.read(r['path'])).hexdigest()!=r['sha256']]
    result={'ok':crc is None and sorted(names)==sorted(expected) and not bad,'files':len(files),'bytes':target.stat().st_size,'sha256':sha(target),'crc_error':crc,'hash_errors':bad,'path':target.name,'note':'此记录在ZIP创建后保存于包外，避免包/记录自引用。包内manifest可独立重算。'}
    save('audit/engineering_package_validation.json',result)
    print(json.dumps(result,ensure_ascii=False))
    if not result['ok']:raise SystemExit(1)

if __name__=='__main__':package()
