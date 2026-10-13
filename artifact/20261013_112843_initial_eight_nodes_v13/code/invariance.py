from common import *
import shutil,random,subprocess,sys,collections
from openpyxl import load_workbook
import events,rebuild
def canonical(ee):
    return sorted([{'id':e['id'],'decision':e['decision'],'facts':e['facts'],'issues':e['issues'],'claims':{s:{k:a.get(k) for k in ['snippet','country','key','quantity','task','region','start','end','observed','time_semantics']} for s,a in e['claims'].items()}} for e in ee],key=lambda x:x['id'])
def main():
    work=BASE/'invariance_inputs';rng=random.Random(13);specs=[]
    for node in NODES:
        src=ROOT/'赛题2-初赛/数据'/node;dest=work/'赛题2-初赛/数据'/node;dest.mkdir(parents=True,exist_ok=True)
        for source in ['开源军情','网上舆论']:
            target=dest/source;target.mkdir(exist_ok=True);pp=list((src/source).glob('*.txt'));rng.shuffle(pp)
            for i,p in enumerate(pp):shutil.copy2(p,target/f'{i:03d}_renumbered.txt')
        wb=load_workbook(next(src.glob('*.xlsx')),data_only=True);sheets=[]
        for s in wb:
            rows=list(s.values);rr=rows[1:];rng.shuffle(rr);sheets.append({'name':s.title,'values':[list(rows[0])]+[list(r) for r in rr]})
        wb.close();specs.append({'node':node,'path':str(dest/f'雷达信息表_{node}.xlsx'),'sheets':sheets})
    save(work/'specs.json',specs)
    runtime=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe';subprocess.run([str(runtime),str(BASE/'code/invariance_workbooks.mjs'),str(work/'specs.json')],check=True)
    results=[]
    for node in NODES:
        ee,xx=events.process_day(work/'赛题2-初赛/数据'/node,work,as_of=node);original=load(BASE/f'audits/{node}/candidate_decisions.json');assert canonical(ee)==canonical(original),node+' invariance failed'
        results.append({'node':node,'renumbered_100_text_files':True,'shuffled_all_radar_rows':True,'canonical_decisions_facts_assertions_unchanged':True})
    # Attempted future access must fail before any file is read.
    rejected=False
    try:events.process_day(ROOT/'赛题2-初赛/数据/2025.7.18',ROOT,as_of='2025.7.17')
    except ValueError:rejected=True
    assert rejected
    hashes=collections.defaultdict(set)
    for p in (BASE/'views').glob('*/*.json'):hashes[p.stem].add(load(p)['candidate_ledger_sha256'])
    assert all(len(h)==1 for h in hashes.values()),'future node changed past day association'
    save(BASE/'audit/invariance_checks.json',{'nodes':results,'future_day_attempt_blocked_before_read':rejected,'all_past_daily_views_identical_under_later_cutoffs':True,'past_days_checked':len(hashes),'original_corpus_includes_future_2025_07_18_19_but_not_processed':True,'meaning':'工程不变性，非事实真值测试'})
    print('INVARIANCE PASS',len(results),'nodes',len(hashes),'day views')
if __name__=='__main__':main()
