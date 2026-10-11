"""Freeze only the authorized GPT references and specification; never scan other runs."""
import hashlib, json, platform, sys
from pathlib import Path
V=Path(__file__).resolve().parents[1]; ROOT=V.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
refs=[]
for name in ['20261009_gpt_accuracy_v2','20261008_001028_gpt-5.6solhigh']:
    base=ROOT/'artifact'/name
    for p in sorted(base.rglob('*')):
        relative=p.relative_to(base)
        if any(x in relative.parts for x in ['.venv','node_modules','__pycache__']): continue
        if p.is_file(): refs.append({'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
spec=[{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)} for p in [ROOT/'README.md',*sorted((ROOT/'docs').glob('[0-9][0-9]-*.md'))]]
config={'version':V.name,'comparison':'20261009_gpt_accuracy_v2','stage':'initial','nodes':['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17'], 'data_start':'2025.5.1','data_cutoff':'2025.7.17','model':'deterministic local rules; no inference API','parameters':{'air_anchor_branch_km':80,'jump_speed_kmh':2400,'same_time_km':5,'time_endpoint_tolerance_minutes':5,'line_gap_break_days':15}, 'authoring_agent':'Codex GPT-6; API model snapshot not exposed','baseline_score':{'completeness':84.4760,'accuracy':64.8389,'format':76.5391,'analysis':52.5000,'weighted_display_mean':69.0354},'official_node_details':None,'seed':4601,'python':sys.version,'os':platform.platform(),'attribution':'No controlled prompt-only experiment; do not claim independent prompt effect or next-version score.'}
(V/'audit/baseline_freeze.json').write_text(json.dumps({'references':refs,'specification':spec,'experiment':config},ensure_ascii=False,indent=2),encoding='utf-8')
(V/'config/experiment.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
print('Frozen authorized reference files:',len(refs))
