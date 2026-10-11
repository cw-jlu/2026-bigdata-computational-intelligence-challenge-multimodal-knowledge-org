"""Read two explicitly selected GPT traces; export only visible messages/metadata.

No reasoning bodies, compaction summaries, credentials or other sessions are exported.
Only the first generation task in each trace is used for comparable execution stats.
"""
import collections
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
ART = REPO / 'artifact'
V2 = ART / '20261009_gpt_accuracy_v2'
V4 = ART / '20261009_gpt_independent_v4'
TRACES = {
    'v2': Path('C:/Users/Evann/.codex/archived_sessions/rollout-2026-10-09T11-08-30-01a11ea2-3abe-7701-aa06-84f47d474d12.jsonl'),
    'v4': Path('C:/Users/Evann/.codex/sessions/2026/10/09/rollout-2026-10-09T16-57-55-01a11fe2-2167-7542-a78d-09197e59dd1c.jsonl'),
}
NODES = ['2025.5.10', '2025.5.18', '2025.5.30', '2025.6.9', '2025.6.17', '2025.6.29', '2025.7.9', '2025.7.17']

def digest(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def save(name, obj):
    (HERE / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def loadlines(p):
    with p.open(encoding='utf-8') as f:
        return [json.loads(l) for l in f if l.strip()]

def text_of(p):
    return '\n'.join(c.get('text', '') for c in p.get('content', []) if c.get('type') in ['input_text', 'output_text', 'text'])

def inspect_trace(name, path):
    counts = collections.Counter()
    calls = []; messages = []; users = []; contexts = []; usage = {}; compactions = []
    developer_hashes = []; meta = {}; start = {}; end = {}; settings = []
    prefix_hasher = hashlib.sha256()
    with path.open('rb') as f:
        for n, raw in enumerate(f, 1):
            o = json.loads(raw); p = o.get('payload', {}); typ = o.get('type')
            prefix_hasher.update(raw)
            counts[(typ, p.get('type', ''))] += 1
            if typ == 'session_meta':
                meta = {k: p.get(k) for k in ['id', 'timestamp', 'cwd', 'originator', 'cli_version', 'source', 'model_provider', 'forked_from_id']}
                meta['base_instructions_sha256'] = digest(json.dumps(p.get('base_instructions', {}), sort_keys=True))
            if typ == 'turn_context':
                contexts.append({'line': n, 'timestamp': o.get('timestamp'), 'model': p.get('model'), 'effort': p.get('effort'), 'approval_policy': p.get('approval_policy'), 'sandbox_policy': p.get('sandbox_policy')})
            if typ == 'compacted':
                compactions.append({'line': n, 'timestamp': o.get('timestamp')})
            if typ == 'event_msg' and p.get('type') == 'thread_settings_applied':
                settings.append({'line': n, 'timestamp': o.get('timestamp'), 'keys': sorted(p)})
            if typ == 'response_item' and p.get('type') == 'message':
                if p.get('role') == 'developer':
                    s = text_of(p)
                    developer_hashes.append({'line': n, 'sha256': digest(s), 'characters': len(s)})
                if p.get('role') == 'user':
                    s = text_of(p)
                    if not s.lstrip().startswith('<'):
                        users.append({'line': n, 'timestamp': o.get('timestamp'), 'text': s, 'sha256': digest(s), 'characters': len(s)})
                if p.get('role') == 'assistant' and p.get('phase') in ['commentary', 'final']:
                    messages.append({'line': n, 'timestamp': o.get('timestamp'), 'phase': p.get('phase'), 'text': text_of(p)})
            if typ == 'response_item' and p.get('type') in ['custom_tool_call', 'function_call']:
                s = p.get('input', p.get('arguments', ''))
                refs = collections.Counter(re.findall(r'tools\.([A-Za-z0-9_]+)\s*\(', s))
                calls.append({'line': n, 'timestamp': o.get('timestamp'), 'name': p.get('name'), 'call_id': p.get('call_id'), 'input_sha256': digest(s), 'input_characters': len(s), 'nested_tool_reference_counts': dict(refs), 'input': s})
            if typ == 'token_usage_record':
                usage[p.get('response_id', str(n))] = p.get('usage', {})
            if typ == 'event_msg' and p.get('type') == 'task_started' and not start:
                start = {'line': n, 'timestamp': o.get('timestamp'), **{k: p.get(k) for k in ['turn_id', 'started_at', 'model_context_window']}}
            if typ == 'event_msg' and p.get('type') == 'task_complete':
                end = {'line': n, 'timestamp': o.get('timestamp'), **{k: p.get(k) for k in ['turn_id', 'duration_ms', 'completed_at']}}
                if p.get('last_agent_message'):
                    messages.append({'line': n, 'timestamp': o.get('timestamp'), 'phase': 'final', 'text': p['last_agent_message']})
                break
    sums = {k: sum(x.get(k, 0) for x in usage.values()) for k in ['input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_output_tokens', 'total_tokens']}
    summary = {'trace': str(path), 'task_prefix_sha256': prefix_hasher.hexdigest(), 'metadata': meta, 'task_start': start, 'task_end': end,
               'contexts': contexts, 'compactions': compactions, 'developer_block_hashes': developer_hashes, 'tool_calls': len(calls),
               'top_level_tool_counts': dict(collections.Counter(c['name'] for c in calls)), 'visible_assistant_messages': len(messages),
               'usage_records_deduplicated': len(usage), 'usage_sum': sums,
               'nested_reference_count_note': '静态工具引用数不是实际嵌套调用次数；不将exec包装调用数量当作工程质量指标。',
               'token_note': '每个response_id仅计算一次usage；累计输入含多次重复上下文，不是独立阅读量。',
               'scope': '仅第一生成任务；不含后续比较、评测反馈或本次trace审计；不导出推理正文。'}
    save(name + '_trace_summary.json', summary)
    save(name + '_visible_timeline.json', {'users': users, 'assistant': messages, 'tools': calls})
    return summary, users

def brief_v2(e, claims):
    return {'event_id': e['event_id'], 'date': e['date'], 'batch': e['batch'], 'kind': e['kind'], 'decision': e['decision'],
            'country': e['country'], 'platform': e['platform'], 'quantity': e['quantity'], 'interval': e['interval'], 'region': e['region'],
            'task': e['task'], 'facts': e['facts'], 'reasons': e['reasons'], 'corrections': e['corrections'],
            'radar_file': e['radar_file'], 'radar_rows': e['radar_rows'], 'competing_tracks': e['competing_tracks'],
            'claims': [claims[i] for i in e['claims']]}

def brief_v4(e):
    return {k: e[k] for k in ['id', 'date', 'batch', 'kind', 'decision', 'country', 'platform', 'quantity', 'start', 'end', 'region', 'task',
                             'facts', 'field_audit', 'issues', 'radar_file', 'rows', 'radar_conflicts', 'trajectory_alerts', 'claims']}

def compare_events():
    old = [e for e in loadlines(V2 / 'output/中间证据/events.jsonl') if e['date'] in NODES]
    new = [e for e in loadlines(V4 / 'output/evidence/all_events.jsonl') if e['date'] in NODES]
    claims = {c['claim_id']: c for c in loadlines(V2 / 'output/中间证据/claims.jsonl')}
    old_by = collections.defaultdict(list); new_by = {}
    for e in old: old_by[(e['date'], e['batch'])].append(e)
    for e in new: new_by[(e['date'], e['batch'])] = e
    old_in = {k for k, es in old_by.items() if any(e['decision'] == '纳入' for e in es)}
    new_in = {k for k, e in new_by.items() if e['decision'] == '纳入'}
    lost = []; gained = []; retained = []; rows = []
    for k in sorted(old_in - new_in):
        lost.append({'key': list(k), 'v2': [brief_v2(e, claims) for e in old_by[k] if e['decision'] == '纳入'], 'v4': brief_v4(new_by[k])})
    for k in sorted(new_in - old_in):
        gained.append({'key': list(k), 'v2': [brief_v2(e, claims) for e in old_by.get(k, [])], 'v4': brief_v4(new_by[k])})
    for k in sorted(new_in & old_in):
        retained.append({'key': list(k), 'v2': [brief_v2(e, claims) for e in old_by[k] if e['decision'] == '纳入'], 'v4': brief_v4(new_by[k])})
    for d in NODES:
        oo = [e for e in old if e['date'] == d]; nn = [e for e in new if e['date'] == d]
        rows.append({'date': d, 'v2_candidates': len(oo), 'v4_candidates': len(nn), 'v2_included': sum(e['decision']=='纳入' for e in oo),
                     'v4_included': sum(e['decision']=='纳入' for e in nn), 'retained_batches': sum(k[0]==d for k in old_in & new_in),
                     'removed_batches': sum(k[0]==d for k in old_in-new_in), 'added_batches': sum(k[0]==d for k in new_in-old_in)})
    issue_counts = collections.Counter(s for rec in lost for s in rec['v4']['issues'])
    categories = collections.Counter()
    primary = collections.Counter()
    for rec in lost:
        s=';'.join(rec['v4']['issues'])
        if '三类来源未全部关联' in s:
            primary['无时段文本同型同日歧义，缺文本来源'] += 1
        elif '雷达轨迹' in s:
            primary['多分支雷达全批次否决'] += 1
        elif '关键字段quantity' in s:
            primary['实名舰艇缺显式数量'] += 1
        elif '关键字段task明确冲突' in s:
            primary['关联文本任务冲突'] += 1
        elif '关键字段task不足' in s:
            primary['单源任务整体排除'] += 1
        else:
            primary['具体区域与轨迹容差冲突'] += 1
        for category, tokens in {'radar_anomaly':['雷达轨迹','雷达区域明确冲突','雷达日期或坐标异常'],
                                 'time':['关键字段start','关键字段end'], 'task':['关键字段task','多任务候选'],
                                 'quantity':['关键字段quantity'], 'region':['关键区域','具体区域缺失'],
                                 'missing_text_type':['三类来源未全部关联'], 'subject':['关键字段country']}.items():
            if any(t in s for t in tokens): categories[category]+=1
    changed = []
    for rec in retained:
        a = rec['v2'][0]; f = rec['v4']['facts']; delta = {}
        for k in ['country', 'quantity', 'task', 'region']:
            if a[k] != f[k]: delta[k] = [a[k], f[k]]
        interval = [int(t[:2])*60+int(t[3:]) for t in [f['start'], f['end']]]
        if a['interval'] != interval: delta['interval'] = [a['interval'], interval]
        if delta: changed.append({'key': rec['key'], 'delta': delta})
    save('event_comparison.json', {'unit': '原始日期+雷达批号，仅用于两实现审计定位，不作为运行时关联依据；v2可能拆成多个轨迹分支，不能混同候选数',
                                  'node_counts': rows, 'v2_included_events': sum(e['decision']=='纳入' for e in old),
                                  'v4_included_events': len(new_in), 'retained_batches': len(old_in&new_in), 'removed_batches': len(lost), 'added_batches': len(gained),
                                  'removed_issue_categories_overlapping': dict(categories), 'removed_primary_categories_disjoint': dict(primary), 'removed_exact_issues': dict(issue_counts),
                                  'retained_changed_count': len(changed), 'retained_changed_fields': changed,
                                  'removed': lost, 'added': gained, 'retained': retained})
    return rows, lost, gained

def compare_inputs():
    old = json.loads((V2 / 'audit/input_manifest.json').read_text(encoding='utf-8'))['files']
    new = loadlines(V4 / 'output/evidence/input_manifest.jsonl')
    a = {e['file'].replace('\\', '/'): (e['sha256'], e['bytes']) for e in old}
    b = {e['path'].replace('\\', '/'): (e['sha256'], e['bytes']) for e in new}
    out = {'v2_file_count': len(a), 'v4_file_count': len(b), 'all_paths_hashes_sizes_equal': a == b,
           'v2_only': sorted(a.keys()-b.keys()), 'v4_only': sorted(b.keys()-a.keys()),
           'changed': [p for p in a.keys()&b.keys() if a[p]!=b[p]],
           'basis': '两轮生成时保存的7878个原始TXT/Excel的SHA256与字节数，未将代码生成结果当作内容真值。'}
    assert out['all_paths_hashes_sizes_equal']
    save('input_comparison.json', out)

def export_raw_examples():
    comparison = json.loads((HERE / 'event_comparison.json').read_text(encoding='utf-8'))
    selected = {
        ('2025.7.9', 'SHIP-AF41F705A929BC'): '实名山东号漏报：三源身份、任务、时段、区域相同；文本未显式写一艘。',
        ('2025.6.9', 'AIR-8C086A90C01249'): '轰6K任务冲突：v2采用长江口无时段军情，v4采用东海南部远程轰炸文本；两种关联选择不同，不能以模型输出判真。',
        ('2025.5.18', 'AIR-1CC2A2CC80B4D1'): 'E737并行轨迹：相同时间南海/黄海两套点位；v2选择文本限定分支，v4整批否决。',
        ('2025.6.17', 'SHIP-37F0DC0E1C2114'): '075早段：具体连云港文本与晚段泛黄海竞争，v4区分度评分不足；需要联合所有文本解歧。',
        ('2025.5.10', 'AIR-9D6E262963D302'): 'RC135任务未知：活动三源已关联，具体任务仅雷达单源；v2标未知，v4整体排除。',
        ('2025.5.10', 'SHIP-A429047D9CB3EB'): '新增815A：检查平台名称与任务抽取差异。',
        ('2025.5.10', 'AIR-026EC345AA8CFC'): '保留事件具体区域细化：大海域兼容不等于两文本独立证明细区。',
    }
    out = []
    for rec in comparison['removed'] + comparison['added'] + comparison['retained']:
        k = tuple(rec['key'])
        if k not in selected: continue
        paths = {c['file'] for e in rec['v2'] for c in e['claims']}
        paths.update(c['path'] for c in rec['v4']['claims'].values())
        raw = []
        for rel in sorted(paths):
            path = REPO / rel
            raw.append({'path': rel, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'text': path.read_text(encoding='utf-8-sig')})
        # Independent raw Excel read; no generated event row is used as the truth.
        from openpyxl import load_workbook
        rv = rec['v4']; book = load_workbook(REPO / rv['radar_file'], read_only=True, data_only=True)
        sheet = book['飞机' if rv['kind']=='飞机' else '舰船']; values = list(sheet.values); header = values[0]
        rows = [{'row': n, 'data': dict(zip(header, vals))} for n, vals in enumerate(values[1:], 2) if vals[0] == k[1]]
        book.close()
        out.append({'key': list(k), 'review_focus': selected[k], 'raw_texts': raw, 'radar_path': rv['radar_file'], 'raw_radar_rows': rows,
                    'v2_event_ids': [e['event_id'] for e in rec['v2']], 'v4_event_id': rv['id']})
    assert len(out) == len(selected)
    save('raw_review_examples.json', {'basis': '审计后从原始TXT和Excel重新读取；7个定向案例不是无偏抽样；人工结论另见TRACE_REVIEW.md。', 'cases': out})

def compare_labels():
    development = json.loads((V2 / 'audit/independent_cases.json').read_text(encoding='utf-8'))['cases']
    holdout = json.loads((V2 / 'audit/holdout_cases.json').read_text(encoding='utf-8'))['cases']
    gold = json.loads((V4 / 'audit/gold_cases.json').read_text(encoding='utf-8'))
    pairs = []
    for old in development + holdout:
        if 'expect_inclusion' in old:
            expected = bool(old['expect_inclusion'])
        elif 'included' in old:
            expected = bool(old['included'])
        else:
            continue  # Candidate association labels are not event inclusion labels.
        for new in gold:
            if not new['expect_association'] or '雷达' not in new['refs']:
                continue  # Negative association to a specified TXT is a different test.
            if new['date'] != old['date'] or new['refs']['雷达']['batch'] != old['batch']:
                continue
            pairs.append({'v2': old, 'v4': {k: new[k] for k in ['id', 'date', 'expect_association', 'expect_include', 'expected_fields', 'basis']},
                          'v2_expect_include': expected, 'include_disagreement': expected != new['expect_include'],
                          'identity_limit': '按原始日期/批号定位，须结合文本引用和分支核对；候选关联与事件纳入标签分别处理。'})
    save('case_label_comparison.json', {'scope': 'v2开发28例中明确纳入标签以及跨节点14例，与v4全部46例中关联肯定案例对照。',
                                       'pairs': pairs, 'pairs_count': len(pairs), 'disagreement_count': sum(p['include_disagreement'] for p in pairs)})

def compare_context_read():
    out = {}
    for name, path in TRACES.items():
        timeline = json.loads((HERE / (name + '_visible_timeline.json')).read_text(encoding='utf-8'))
        call = timeline['tools'][1]  # Both traces' second exec explicitly reads README.
        records = []
        for n, raw in enumerate(path.open(encoding='utf-8'), 1):
            obj = json.loads(raw); payload = obj.get('payload', {})
            if obj.get('type') == 'response_item' and payload.get('type') == 'custom_tool_call_output' and payload.get('call_id') == call['call_id']:
                body = json.dumps(payload.get('output', ''), ensure_ascii=False)
                records.append({'line': n, 'timestamp': obj.get('timestamp'), 'has_v2_score_69_0354': '69.0354' in body})
                break
        out[name] = {'read_call_line': call['line'], 'output': records}
    save('repository_context_comparison.json', {'readme_trace_markers': out,
          'finding': 'v4首次读取README的工具返回含v2成绩69.0354；v2首次读取没有该成绩。因此用户提示相同，但仓库上下文不是冻结快照。不能从此标记推断它具体造成了多少分差。',
          'not_inferred': '模型后端具体快照、temperature、sampling seed、官方评测是否随机均未从这些记录取得。'})

def compare_trends():
    out = []
    for day in NODES:
        a = json.loads((V2 / f'output/中间证据/factpack_{day}.json').read_text(encoding='utf-8'))['trend']
        b = json.loads((V4 / f'output/payloads/{day}.json').read_text(encoding='utf-8'))['chain']
        out.append({'date': day, 'v2': {k: a[k] for k in ['country', 'platform', 'dates']},
                    'v4': {k: b[k] for k in ['country', 'platform', 'dates']},
                    'v2_stages': [{'dates': s['dates'], 'regions': s['regions'], 'tasks': s['tasks']} for s in a['phases']],
                    'v4_stages': b['stages']})
    save('trend_comparison.json', out)

def save_metrics_and_manifest():
    old = [Decimal(s) for s in ['84.4760', '64.8389', '76.5391', '52.5000']]
    new = [Decimal(s) for s in ['74.8767', '85.5277', '76.4282', '55.7500']]
    weights = [Decimal(s) for s in ['0.25', '0.40', '0.15', '0.20']]
    save('evaluation_comparison.json', {'source': 'v2归档的用户评测反馈与当前聊天用户反馈，未获取平台逐节点扣分。',
         'stage': 'initial', 'nodes': 8, 'metrics_order': ['completeness', 'accuracy', 'format', 'analysis'],
         'v2': [str(x) for x in old], 'v4': [str(x) for x in new], 'weights': [str(x) for x in weights],
         'v2_total': str(sum(x*w for x,w in zip(old,weights))), 'v4_total': str(sum(x*w for x,w in zip(new,weights))),
         'weighted_contributions': [str((y-x)*w) for x,y,w in zip(old,new,weights)],
         'delta': str(sum((y-x)*w for x,y,w in zip(old,new,weights)))})
    archives = []
    for path, expected in [(V2/'output/日报_gpt_accuracy_v2.zip', '728086a59f3259463737abdc3786e926fc2f4b5f7c4b8663db74a2e67fa8f6a4'),
                           (V4/'output/赛题2_初赛_八节点_提交.zip', 'db718c7cdf686b7b70970bbecb265d6c75d65ee28b48e56d829da5eed7ab4176'),
                           (V4/'工程交付_代码证据成果.zip', '7d685a7732f6a88f84558b772fe585ee3d2a71267b224f7b3b8b9a7f63cd0631')]:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, f'Previously delivered archive changed: {path}'
        archives.append({'path': path.relative_to(REPO).as_posix(), 'sha256': actual, 'matches_pre_audit_delivery_record': True})
    files = [{'path': p.relative_to(HERE).as_posix(), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(HERE.iterdir()) if p.is_file() and p.name != 'audit_manifest.json']
    save('audit_manifest.json', {'previous_archives_unchanged': archives, 'new_audit_files': files,
         'scope': '本次trace审计文件，独立于预评测工程包；不包含原始trace全文、推理正文或凭据。'})

def main():
    summaries = {}; prompts = {}
    for name, path in TRACES.items():
        summary, users = inspect_trace(name, path)
        summaries[name] = summary
        prompts[name] = max(users, key=lambda u: u['characters'])
    save('prompt_comparison.json', {'exact_equal': prompts['v2']['text'] == prompts['v4']['text'], 'v2': prompts['v2'], 'v4': prompts['v4']})
    rows, lost, gained = compare_events()
    compare_inputs()
    export_raw_examples()
    compare_labels()
    compare_context_read()
    compare_trends()
    save_metrics_and_manifest()
    print(json.dumps({'prompt_exact_equal': prompts['v2']['text']==prompts['v4']['text'],
                      'execution': {k:{'model':v['contexts'][0]['model'], 'effort':v['contexts'][0]['effort'], 'duration_minutes':v['task_end']['duration_ms']/60000,
                                      'tool_calls':v['tool_calls'], 'compactions':len(v['compactions']), 'usage':v['usage_sum']} for k,v in summaries.items()},
                      'node_counts':rows, 'removed':len(lost), 'added':len(gained)}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
