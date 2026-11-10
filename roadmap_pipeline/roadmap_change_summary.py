#!/usr/bin/env python3
import json, sys
from pathlib import Path

# Fields that are presentation/expansion identity rather than source business data.
PRESENTATION_FIELDS = {'id', 'pillar', 'category', 'originSuffix', 'alias'}

# Business fields used for the headline New / Updated / Deleted project counts.
# One ServiceNow number counts once regardless of how many pillar rows it expands into.
BUSINESS_FIELDS = {
    'number', 'type', 'title', 'origin', 'start', 'end', 'progress', 'status',
    'risk', 'active', 'fiscalYear', 'campus', 'teams', 'fc', 'manager',
    'plannedDate', 'description', 'serviceNowUrl'
}

FIELD_GROUPS = {
    'status': {'status', 'risk', 'active', 'progress'},
    'dates': {'start', 'end', 'plannedDate', 'fiscalYear'},
    'manager': {'manager'},
    'organization': {'origin', 'campus', 'teams', 'fc'},
    'title/type': {'title', 'type'},
    'description/link': {'description', 'serviceNowUrl'},
}

def load_items(path):
    p = Path(path)
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(d, list):
        return d
    return d.get('items', d.get('records', []))

def normalized_business_record(item):
    return {k: item.get(k, '') for k in sorted(BUSINESS_FIELDS) if k != 'number'}

def project_rollup(items):
    """Collapse expanded pillar rows to one deterministic business record per SN number."""
    by = {}
    for item in items:
        num = str(item.get('number') or '').strip()
        if not num:
            continue
        rec = normalized_business_record(item)
        if num not in by:
            by[num] = rec
        else:
            # Expanded rows should have identical business values. If they do not,
            # preserve all variants so a genuine source-level discrepancy is visible.
            current = by[num]
            if isinstance(current, dict) and current != rec:
                by[num] = [current, rec]
            elif isinstance(current, list) and rec not in current:
                current.append(rec)
    for num, value in list(by.items()):
        if isinstance(value, list):
            by[num] = sorted(value, key=lambda z: json.dumps(z, sort_keys=True, ensure_ascii=False))
    return by

def changed_fields(old_record, new_record):
    # Normal case: a single collapsed source record.
    if isinstance(old_record, dict) and isinstance(new_record, dict):
        return sorted(k for k in set(old_record) | set(new_record)
                      if old_record.get(k, '') != new_record.get(k, ''))
    # Multiple inconsistent expanded variants are treated as a source discrepancy.
    return ['expandedVariant'] if old_record != new_record else []

def group_for_field(field):
    for group, fields in FIELD_GROUPS.items():
        if field in fields:
            return group
    return 'other'

def main(old_path, new_path, status_path):
    old = project_rollup(load_items(old_path))
    new = project_rollup(load_items(new_path))
    ok, nk = set(old), set(new)

    added = sorted(nk - ok)
    deleted = sorted(ok - nk)
    common = sorted(ok & nk)

    updated = []
    details = {}
    group_projects = {group: set() for group in list(FIELD_GROUPS) + ['other']}

    for num in common:
        fields = changed_fields(old[num], new[num])
        if not fields:
            continue
        updated.append(num)
        details[num] = fields
        for field in fields:
            group_projects[group_for_field(field)].add(num)

    group_counts = {k: len(v) for k, v in group_projects.items() if v}

    sp = Path(status_path)
    status = json.loads(sp.read_text(encoding='utf-8'))
    status['changes'] = {
        'new': len(added),
        'updated': len(updated),
        'deleted': len(deleted),
    }
    status['changeRecords'] = {
        'new': added,
        'updated': updated,
        'deleted': deleted,
    }
    # Diagnostics: which meaningful fields caused projects to count as updated.
    # Group counts may overlap because one project can change in more than one category.
    status['changeDetails'] = group_counts
    status['updatedFieldsByProject'] = details
    status['changeCounting'] = 'unique ServiceNow records (number), not expanded roadmap lines'

    sp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Change summary: New={len(added)} Updated={len(updated)} Deleted={len(deleted)}")
    if group_counts:
        print('Updated project categories: ' + ', '.join(f'{k}={v}' for k, v in sorted(group_counts.items())))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit('usage: roadmap_change_summary.py OLD_JSON NEW_JSON STATUS_JSON')
    main(*sys.argv[1:])
