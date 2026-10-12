"""Conservative diagnostic for postposed quantities; never edits formal ledgers."""
from pathlib import Path
import json,re
from collections import defaultdict

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parents[1]
V9=ROOT/'artifact/20261012_134432_initial_eight_nodes_v9'
CN={'一':1,'两':2,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10}

def probe(snippet,platform,kind,platforms_in_segment):
    # A role phrase cannot be shared among multiple participants.
    if len(set(platforms_in_segment))!=1:return None
    role='航母' if kind=='舰艇' and '航空母舰' in platform else None
    if role is None:return None
    # Inspect only the factual snippet supplied by the upstream parser.
    pattern=r'期间有([0-9]+|[一两二三四五六七八九十])艘'+role+r'参与'
    matches=list(re.finditer(pattern,snippet))
    if not matches:return None
    values={int(m[1]) if m[1].isdigit() else CN[m[1]] for m in matches}
    if len(values)!=1:return {'status':'explicit_internal_conflict','quotes':[m[0] for m in matches]}
    return {'status':'explicit_postposed_quantity','value':next(iter(values)),'unit':'艘','quotes':[m[0] for m in matches]}

def main():
    assert probe('期间有一艘航母参与。','辽宁号航空母舰','舰艇',['辽宁'])['value']==1
    assert probe('期间有两艘航母参与。','辽宁号航空母舰','舰艇',['辽宁'])['value']==2
    assert probe('期间有一艘航母参与。','辽宁号航空母舰','舰艇',['辽宁','山东']) is None
    assert probe('期间有一艘航母参与。','054A型护卫舰','舰艇',['054a']) is None
    assert probe('期间有一艘航母参与。期间有两艘航母参与。','辽宁号航空母舰','舰艇',['辽宁'])['status']=='explicit_internal_conflict'
    results=[]
    for node in ['2025.5.10','2025.5.18','2025.5.30','2025.6.9','2025.6.17','2025.6.29','2025.7.9','2025.7.17']:
        ex=json.loads((V9/f'evidence/daily/{node}/extraction.json').read_text(encoding='utf-8'))
        segments=defaultdict(list)
        for a in ex['atoms']:segments[a['path'],a['locator']['subevent_index']].append(a['key'])
        for a in ex['atoms']:
            r=probe(a['snippet'],a['platform'],a['kind'],segments[a['path'],a['locator']['subevent_index']])
            if r:
                results.append({'node':node,'path':a['path'],'atom_id':a['id'],'old_quantity':a['quantity'],'old_basis':a['quantity_basis'],'new_evidence':r,'value_changed':r.get('value')!=a['quantity'],'action':'upgrade evidence provenance only' if r.get('value')==a['quantity'] else 'hold for conflict adjudication; never silently override'})
    data={'status':'diagnostic_complete','boundary_checks':5,'original_atom_matches':results,'new_events_accepted':0,'formal_output_modified':False,'limitation':'narrow pattern; not a general coreference resolver; synthetic boundary checks are not independent blind evaluation'}
    (BASE/'quantity_probe_results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
