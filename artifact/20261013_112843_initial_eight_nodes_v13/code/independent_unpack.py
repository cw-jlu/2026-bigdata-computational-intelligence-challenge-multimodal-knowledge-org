"""Physically extract an expected 48-member ZIP, then reopen without builders."""
from common import *
import zipfile
from verify_delivery import verify,NAMES

def main():
    archive=BASE/'赛题2_初赛_v13_八节点正式提交包.zip'
    folder=(BASE/'qa/independent_unpacked').resolve()
    assert not folder.exists(),'Use a fresh physical extraction directory'
    expected={f'{n}/{n}日报.docx' for n in NODES}|{f'{n}/{n}机舰活动明细.xlsx' for n in NODES}|{f'{n}/附件图表/{x}' for n in NODES for x in NAMES}
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==48 and set(z.namelist())==expected
        assert z.testzip() is None
        for member in z.namelist():
            target=(folder/member).resolve()
            assert target.is_relative_to(folder)
        z.extractall(folder)
    rows=[]
    for p in sorted(folder.rglob('*')):
        if p.is_file():
            rel=p.relative_to(folder).as_posix()
            assert sha(p)==sha(BASE/'official'/rel)
            rows.append({'path':rel,'sha256':sha(p),'bytes':p.stat().st_size})
    nodes=verify(BASE,official_root=folder)
    save(BASE/'audit/physical_unpack_verification.json',{'status':'PASS','zip_sha256':sha(archive),'files_physically_extracted_and_reopened':48,'members':rows,'nodes':nodes,'code_path':'ZIP -> new folder -> OOXML/openpyxl/Pillow; no builders','independent_human_reviewer':False})
    print('PHYSICAL UNPACK AND REOPEN PASS',48)
if __name__=='__main__':main()
