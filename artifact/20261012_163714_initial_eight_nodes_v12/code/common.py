from pathlib import Path
import json,hashlib,datetime,os
BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('COMPETITION_PROJECT_ROOT') or (BASE/'inputs' if (BASE/'inputs/赛题2-初赛/数据').exists() else 'D:/CW/2026-bigdata-computational-intelligence-challenge-multimodal-knowledge-org')).resolve()
NODES=['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dt(s):return datetime.datetime.strptime(s,'%Y.%m.%d').date()
