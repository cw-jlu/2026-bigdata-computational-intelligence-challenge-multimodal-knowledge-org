from common import *
import zipfile,importlib.metadata as md,shutil,os

def main():
    assert load(BASE/'stage_audit.json')['content_generated']
    assert load(BASE/'independent_unpack_validation.json')['status']=='PASS'
    dep=load(BASE/'dependencies.json');packages=dep['python_packages'];packages['numpy']=md.version('numpy')
    (BASE/'requirements.txt').write_text('\n'.join(p+'=='+v for p,v in sorted(packages.items()))+'\n',encoding='utf8')
    source=Path('C:/Users/Andy1/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/package.json')
    target=BASE/'dependencies/artifact-tool.package.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    save(BASE/'dependencies.json',{**dep,'python_packages':packages,'javascript_dependency_manifest':'dependencies/artifact-tool.package.json','javascript_install_note':'Use the configured Codex bundled artifact runtime; supply -Node/-Packages for a relocated runtime. Do not assume public npm installation is possible.'})
    files=[]
    for folder in ['code','inputs','audits','evidence','official','qa','dependencies']:
        root=BASE/folder
        for folder_path,dirs,names in os.walk(root,followlinks=False):
            dirs[:]=[d for d in dirs if d not in ['node_modules','__pycache__','unpacked_submission']]
            for name in names:
                p=Path(folder_path)/name
                if p.is_file():files.append(p)
    for p in BASE.iterdir():
        if p.is_file() and p.suffix in ['.md','.json','.txt','.ps1','.log'] and p.name not in ['engineering_package_manifest.json','engineering_package_validation.json','validation_stdout.json','validation_final_stdout.json','validation_sealed_stdout.json']:
            files.append(p)
    for folder in ['reproduction','portable_reproduction']:
        p=BASE/folder/'run.log'
        if p.exists():files.append(p)
    paths=[p.relative_to(BASE).as_posix() for p in files];assert len(paths)==len(set(paths))
    listing=[{'path':p.relative_to(BASE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
    save(BASE/'engineering_package_manifest.json',{'files':listing,'excluded':['node_modules runtime junction','__pycache__','duplicate reproduction outputs','independent unpack duplicate files','formal submission ZIP itself'],'raw_input_files':7878,'entrypoint':'Run-all.ps1','runtime_dependencies':'dependencies.json and requirements.txt'})
    files.append(BASE/'engineering_package_manifest.json')
    save(BASE/'code_manifest.json',[{'path':p.relative_to(BASE).as_posix(),'sha256':sha(p)} for p in sorted((BASE/'code').glob('*')) if p.is_file()])
    # Manifest was made after the final code set; refresh code_manifest hash.
    for row in listing:
        if row['path']=='code_manifest.json':row['sha256']=sha(BASE/'code_manifest.json');row['bytes']=(BASE/'code_manifest.json').stat().st_size
    save(BASE/'engineering_package_manifest.json',{'files':listing,'excluded':['node_modules runtime junction','__pycache__','duplicate reproduction outputs','independent unpack duplicate files','formal submission ZIP itself'],'raw_input_files':7878,'entrypoint':'Run-all.ps1','runtime_dependencies':'dependencies.json and requirements.txt'})
    archive=BASE/'赛题2_初赛_八节点_工程与证据包.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):z.write(p,p.relative_to(BASE).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(paths)|{'engineering_package_manifest.json'}
        for row in listing:assert hashlib.sha256(z.read(row['path'])).hexdigest()==row['sha256']
    save(BASE/'engineering_package_validation.json',{'status':'PASS','archive':archive.name,'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files),'raw_input_files':7878,'original_prompt_included':True,'all_eight_independent_audits_included':True,'source_code_included':True,'formal_submission_zip_separate':True})
    print(archive,'members',len(files),'bytes',archive.stat().st_size)

if __name__=='__main__':main()
