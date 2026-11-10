#!/usr/bin/env python3
import csv, html, json
from pathlib import Path
from urllib.parse import urlencode

BASE='https://bknavarre.github.io/roadmap-studio/'
DATA=Path('public/roadmap_data.json') if Path('public/roadmap_data.json').exists() else Path('/mnt/data/roadmap_data.json')
OUT=Path('public') if Path('public').is_dir() else Path('/mnt/data')

def vals(items,key,split=False):
    out=set()
    for x in items:
        v=str(x.get(key) or '').strip()
        if not v: continue
        parts=v.split(',') if split else [v]
        out.update(p.strip() for p in parts if p.strip())
    return sorted(out,key=str.casefold)

def link(view,name,display='timeline'):
    q={'view':view,'name':name,'display':display,'published':'1'}
    if display=='swimlane': q['mode']='FY'
    return BASE+'?'+urlencode(q)

d=json.loads(DATA.read_text(encoding='utf-8'))
items=d if isinstance(d,list) else d.get('items',d.get('records',[]))
# The Studio's useful shareable map dimensions.
groups=[
 ('Pillar','pillar',vals(items,'pillar')),
 ('Campus','campus',vals(items,'campus',True)),
 ('Functional Committee','fc',vals(items,'fc')),
]
rows=[]
for label,view,names in groups:
    for name in names:
        rows.append([label,name,'Roadmap',link(view,name,'timeline')])
        rows.append([label,name,'Swimlane',link(view,name,'swimlane')])

csv_path=OUT/'roadmap_links.csv'
with csv_path.open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f); w.writerow(['Group','Name','View','URL']); w.writerows(rows)

sections=[]
for label,view,names in groups:
    trs=[]
    for name in names:
        r=link(view,name,'timeline'); s=link(view,name,'swimlane')
        trs.append(f'<tr><td>{html.escape(name)}</td><td><a href="{html.escape(r)}" target="_blank">Open Roadmap</a></td><td><a href="{html.escape(s)}" target="_blank">Open Swimlane</a></td></tr>')
    sections.append(f'<section><h2>{html.escape(label)}s</h2><table><thead><tr><th>{html.escape(label)}</th><th>Roadmap</th><th>Swimlane</th></tr></thead><tbody>{"".join(trs)}</tbody></table></section>')

page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Roadmap Studio Link Directory</title><style>
body{font-family:Arial,sans-serif;background:#f5f7f9;color:#1e293b;margin:0;padding:28px}main{max-width:1100px;margin:auto}h1{margin-bottom:6px}p{color:#64748b}section{background:white;border:1px solid #dce3e8;border-radius:10px;padding:18px;margin:18px 0}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e5e7eb}th{background:#f8fafc}a{color:#0369a1;font-weight:600;text-decoration:none}a:hover{text-decoration:underline}@media(max-width:650px){body{padding:12px}th,td{padding:8px;font-size:14px}}
</style></head><body><main><h1>Roadmap Studio Link Directory</h1><p>Published, view-only links. Swimlanes open in FY mode; viewers can switch modes inside the view.</p>'''+''.join(sections)+'''</main></body></html>'''
html_path=OUT/'roadmap_links.html'; html_path.write_text(page,encoding='utf-8')
print(f'Generated {len(rows)} links across {sum(len(n) for _,_,n in groups)} roadmap entities')
for label,_,names in groups: print(label,len(names))
print(csv_path); print(html_path)
