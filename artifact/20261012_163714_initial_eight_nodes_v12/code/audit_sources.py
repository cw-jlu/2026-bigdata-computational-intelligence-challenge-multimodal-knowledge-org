#!/usr/bin/env python3
"""Offline date/version/citation checks. Does not verify claims or score a report."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

APPROVED_VERSIONS = {'fixed_edition', 'dated_publication'}
SUBSTANTIVE_ROLES = {'published_statistics', 'expert_report', 'official_policy', 'official_assessment'}


def parse_day(value: Any, field: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f'{field}: expected YYYY-MM-DD')
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f'{field}: invalid date {value!r}') from exc
    if result.isoformat() != value:
        raise ValueError(f'{field}: expected YYYY-MM-DD')
    return result


def audit(catalog: dict, as_of: str, used: list[str], substantive: list[str] | None = None) -> dict:
    cutoff = parse_day(as_of, 'as_of')
    if not isinstance(catalog, dict) or catalog.get('schema_version') != 1:
        raise ValueError('catalog must be an object with schema_version=1')
    rows = catalog.get('sources')
    if not isinstance(rows, list) or not rows:
        raise ValueError('sources must be a nonempty list')
    by_id: dict[str, dict] = {}
    eligible: list[str] = []
    excluded: list[dict] = []
    errors: list[str] = []
    warnings: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('each source must be an object')
        sid = row.get('id')
        if not isinstance(sid, str) or not sid:
            raise ValueError('each source requires a nonempty string id')
        if sid in by_id:
            raise ValueError(f'duplicate source id: {sid}')
        by_id[sid] = row
        reasons: list[str] = []
        for key in ('title', 'publisher', 'role', 'independence_group', 'locator'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                reasons.append(f'missing {key}')
        url = row.get('url', '')
        if not isinstance(url, str):
            reasons.append('invalid URL')
        else:
            parsed = urlparse(url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                reasons.append('invalid HTTP(S) URL')
        if row.get('content_verified') is not True:
            reasons.append('source content not verified')
        try:
            published = parse_day(row.get('published_by'), f'{sid}.published_by')
            if published > cutoff:
                reasons.append('publication upper bound after cutoff')
        except ValueError as exc:
            reasons.append(str(exc))
        if row.get('version_status') not in APPROVED_VERSIONS:
            reasons.append('historical version or translation date not established')
        if row.get('version_date') is not None:
            try:
                version = parse_day(row['version_date'], f'{sid}.version_date')
                if version > cutoff:
                    reasons.append('content version after cutoff')
            except ValueError as exc:
                reasons.append(str(exc))
        # retrieved_at is deliberately not a cutoff test: archival content can be fetched later.
        if reasons:
            excluded.append({'id': sid, 'reasons': reasons})
        else:
            eligible.append(sid)
    eligible_set = set(eligible)
    used_unique = list(dict.fromkeys(used))
    if len(used_unique) != len(used):
        warnings.append('duplicate citations do not add independent evidence')
    for sid in used_unique:
        if sid not in by_id:
            errors.append(f'unknown cited source: {sid}')
        elif sid not in eligible_set:
            errors.append(f'ineligible source cited: {sid}')
    substantive = list(dict.fromkeys(substantive or []))
    for sid in substantive:
        if sid not in used_unique:
            errors.append(f'substantive source not in used sources: {sid}')
        elif sid in by_id and by_id[sid]['role'] not in SUBSTANTIVE_ROLES:
            errors.append(f'method/style source cannot stand in for external factual evidence: {sid}')
    groups: dict[str, list[str]] = {}
    for sid in used_unique:
        if sid in by_id:
            group = by_id[sid].get('independence_group', '')
            groups.setdefault(group, []).append(sid)
    shared = {g: ids for g, ids in groups.items() if len(ids) > 1}
    if shared:
        warnings.append('some cited sources share an upstream independence group')
    warnings.append('Date checks do not prove authenticity, claim entailment, or event verification.')
    warnings.append('Dated webpages need a saved version before reproducible use; later edits may exist.')
    return {
        'schema_version': 1, 'as_of': as_of, 'status': 'PASS' if not errors else 'FAIL',
        'eligible_source_ids': eligible, 'excluded_sources': excluded,
        'used_source_ids': used_unique, 'declared_substantive_source_ids': substantive,
        'shared_independence_groups': shared, 'errors': errors, 'warnings': warnings,
        'claim_level_support_checked': False, 'competition_score_estimated': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True)
    parser.add_argument('--as-of', required=True)
    parser.add_argument('--used', nargs='*', default=[])
    parser.add_argument('--substantive', nargs='*', default=[])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        obj = json.loads(args.catalog.read_text(encoding='utf-8'))
        result = audit(obj, args.as_of, args.used, args.substantive)
        text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding='utf-8')
        print(text, end='')
        return 0 if result['status'] == 'PASS' else 1
    except (OSError, ValueError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
