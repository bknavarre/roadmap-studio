#!/usr/bin/env python3
import json, sys
from pathlib import Path

IGNORED_FIELDS = {'generated', 'lastSuccessfulRefresh'}

def load_items(path):
    p=Path(path)
    if not p.exists(): return []
    d=json.loads(p.read_text(encoding='utf-8'))
    if isinstance(d, list): return d
    return d.get('items', d.get('records', []))

def stable_record(item):
    # Compare meaningful source fields, but not expansion identity/presentation fields.
    ignore={'id','pillar','category','originSuffix'}
    return {k:v for k,v in item.items() if k not in ignore}

def rollup(items):
    by={}
    for x in items:
        num=str(x.get('number') or '').strip()
        if not num: continue
        # A source record may expand to multiple pillar lines. Build a deterministic
        # source-level signature from every expanded membership.
        by.setdefault(num,[]).append(stable_record(x))
    return {k:sorted(v,key=lambda z:json.dumps(z,sort_keys=True,ensure_ascii=False)) for k,v in by.items()}

def main(old_path,new_path,status_path):
    old=rollup(load_items(old_path)); new=rollup(load_items(new_path))
    ok, nk=set(old),set(new)
    added=sorted(nk-ok); deleted=sorted(ok-nk)
    updated=sorted(k for k in ok&nk if old[k]!=new[k])
    sp=Path(status_path); status=json.loads(sp.read_text(encoding='utf-8'))
    status['changes']={'new':len(added),'updated':len(updated),'deleted':len(deleted)}
    status['changeRecords']={'new':added,'updated':updated,'deleted':deleted}
    sp.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Change summary: New={len(added)} Updated={len(updated)} Deleted={len(deleted)}")
if __name__=='__main__':
    if len(sys.argv)!=4: raise SystemExit('usage: roadmap_change_summary.py OLD_JSON NEW_JSON STATUS_JSON')
    main(*sys.argv[1:])
