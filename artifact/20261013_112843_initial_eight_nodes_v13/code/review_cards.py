from common import *
import argparse,collections
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--node');ap.add_argument('--mode',default='delta');a=ap.parse_args();rows=[]
    for node in [a.node] if a.node else NODES:
        cp=BASE/f'audits/{node}/candidate_decisions.json'
        if not cp.exists():continue
        new=load(cp);oldf=load(ROOT/f'artifact/20261012_163714_initial_eight_nodes_v12/audits/{node}/frozen_ledger.json');old={e['batch']:e for e in oldf['today_events']}
        if a.mode=='mainlines':
            f=load(BASE/f'audits/{node}/frozen_ledger.json');print(node)
            for o in f['candidate_comparison']:
                if not o['eligible']:continue
                print(o['country'],o['key'],len(o['dates']),o['observed_tasks'],o['directions'])
                for e in f['verified_events']:
                    if e['id'] in o['event_ids']:print(e['date'],e['id'],e['facts']['region'],e['facts']['task'],e['facts']['quantity'],e['facts']['start'],e['facts']['end'])
            continue
        for e in new:
            if a.mode=='delta' and ((e['decision']=='纳入')==(e['batch'] in old)):continue
            if a.mode=='excluded' and e['decision']!='排除':continue
            card={'node':node,'id':e['id'],'old':old.get(e['batch'],{}).get('decision','未纳入'),'new':e['decision'],'platform':e['platform'],'country':e['country'],'issues':e['issues'],'texts':{s:{'path':q['path'],'quote':q['snippet'],'quantity':q['quantity'],'quantity_basis':q['quantity_basis'],'task':q['task'],'region':q['region']} for s,q in e['claims'].items()},'competitors':e['competing_evidence'],'radar':{'values':e['values'],'regions':e['regions'],'times':[e['start'],e['end']],'alerts':e['trajectory_alerts'],'rows':e['rows']}}
            rows.append(card)
    save(BASE/f'audit/{a.mode}_review_cards.json',rows)
    print(json.dumps(rows,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
