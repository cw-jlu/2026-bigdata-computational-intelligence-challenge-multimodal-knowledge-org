from common import *
import shutil

def copy_one(src,rel):
    target=BASE/'inputs'/rel
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():shutil.copyfile(src,target)
    assert sha(src)==sha(target)
    return {'path':'inputs/'+rel,'sha256':sha(target),'bytes':target.stat().st_size}

def main():
    rows=[]
    for r in load(BASE/'evidence/input_manifest.json'):rows.append(copy_one(ROOT/r['path'],r['path']))
    for fold in ['提交示例文件/日报','analysis_research_bundle']:
        for p in sorted((ROOT/fold).rglob('*')):
            if p.is_file():rows.append(copy_one(p,p.relative_to(ROOT).as_posix()))
    for p in sorted((ROOT/'docs').glob('*.md')):rows.append(copy_one(p,p.relative_to(ROOT).as_posix()))
    for p in sorted((ROOT/'docs/prompts').glob('*.md')):rows.append(copy_one(p,p.relative_to(ROOT).as_posix()))
    p=ROOT/'提交示例文件/提交格式说明.md';rows.append(copy_one(p,p.relative_to(ROOT).as_posix()))
    for fold in ['artifact/20261008_001929_claude-opus-5.5high/bdci','artifact/20261009_gpt_accuracy_v2/code','artifact/20261009_gpt_accuracy_v3/code','artifact/20261009_gpt_independent_v4/code']:
        for p in sorted((ROOT/fold).rglob('*')):
            if p.is_file() and p.suffix in ['.py','.md','.json','.txt','.toml']:rows.append(copy_one(p,p.relative_to(ROOT).as_posix()))
    for n in NODES:
        for rel in [f'artifact/20261008_001929_claude-opus-5.5high/output/中间结果/{n}/events.jsonl',f'artifact/20261009_gpt_accuracy_v2/output/中间证据/factpack_{n}.json',f'artifact/20261009_gpt_accuracy_v3/output/中间证据/factpack_{n}.json',f'artifact/20261009_gpt_independent_v4/output/payloads/{n}.json']:
            p=ROOT/rel
            if p.exists():rows.append(copy_one(p,rel))
    # Only the calling chat's exact human instruction is extracted; no system,
    # developer, unrelated chat or tool messages are copied into the artifact.
    rollout=Path('C:/Users/Andy1/.codex/sessions/2026/10/11/rollout-2026-10-11T23-55-34-01a12bad-3093-7240-9852-fc1781d85fef.jsonl')
    found=[]
    for line in rollout.open(encoding='utf8'):
        j=json.loads(line);p=j.get('payload',{})
        if j.get('type')=='response_item' and p.get('role')=='user':
            text='\n'.join(c.get('text','') for c in p.get('content',[]) if c.get('type')=='input_text')
            if text.startswith('请在当前项目重新制作'):found.append(text)
    assert found,'Exact user prompt not found'
    (BASE/'user_request_original.md').write_text(found[0],encoding='utf8')
    shutil.copyfile(ROOT/'analysis_research_bundle/generation_prompt.md',BASE/'module_generation_prompt_original.md')
    save(BASE/'packaged_input_manifest.json',rows)
    print('Packaged inputs',len(rows),'bytes',sum(r['bytes'] for r in rows),'prompt chars',len(found[0]))

if __name__=='__main__':main()
