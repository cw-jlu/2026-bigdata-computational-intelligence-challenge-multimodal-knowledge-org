"""Canonical OOXML packages without changing cells, prose, styles, or images."""
from common import *
import zipfile,io,posixpath,re,argparse
from xml.etree import ElementTree as ET
STAMP=(2025,1,1,0,0,0)

def write_zip(path,parts):
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name in sorted(parts):
   info=zipfile.ZipInfo(name,STAMP);info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=0;info.external_attr=0
   z.writestr(info,parts[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def canonicalize(path):
 before=sha(path)
 with zipfile.ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
 changed=[]
 # artifact-tool randomizes relation IDs. Canonicalize both relation declarations
 # and their owner references, preserving every target, type and XML attribute.
 for name in sorted(parts):
  if not name.endswith('.rels'):continue
  root=ET.fromstring(parts[name]);rels=sorted(root,key=lambda e:(e.get('Type',''),e.get('Target',''),e.get('TargetMode','')))
  mapping={e.get('Id'):f'rId{i+1}' for i,e in enumerate(rels)}
  s=parts[name].decode('utf8')
  s=re.sub(r'\bId="([^"]+)"',lambda m:'Id="'+mapping.get(m[1],m[1])+'"',s)
  parts[name]=s.encode('utf8')
  if name=='_rels/.rels':continue
  folder,leaf=posixpath.split(name);owner=posixpath.join(posixpath.dirname(folder),leaf[:-5])
  if owner in parts:
   s=parts[owner].decode('utf8');s=re.sub(r'\b(r:(?:id|embed|link))="([^"]+)"',lambda m:m[1]+'="'+mapping.get(m[2],m[2])+'"',s);parts[owner]=s.encode('utf8')
  changed.append({'relationship_part':name,'owner':owner,'relationships':len(mapping)})
 write_zip(path,parts)
 with zipfile.ZipFile(path) as z:assert z.testzip() is None
 return {'path':path.name,'before':before,'after':sha(path),'normalized':'ZIP member timestamps/order/compression and equivalent relationship IDs','relationships':changed}

def process(out):
 records=[canonicalize(p) for p in sorted((out/'official').rglob('*')) if p.suffix in ['.docx','.xlsx']]
 save(out/'audit/package_normalization.json',records);print('CANONICALIZED',len(records))

def pack(out):
 parts={p.relative_to(out/'official').as_posix():p.read_bytes() for p in (out/'official').rglob('*') if p.is_file()};assert len(parts)==48
 archive=out/'initial_eight_nodes_v14.zip';write_zip(archive,parts);save(out/'audit/official_hashes.json',{'zip_sha256':sha(archive),'files':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(parts.items())}});print('PACKED',archive,sha(archive));return archive
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=BASE);ap.add_argument('--pack',action='store_true');a=ap.parse_args();process(a.output.resolve())
 if a.pack:pack(a.output.resolve())
