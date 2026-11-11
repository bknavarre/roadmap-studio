#!/usr/bin/env python3
"""Apply Roadmap Studio Idea, cross-pillar emphasis, and At Risk UI updates.
Run from the repository root: python apply_main_updates.py
"""
from pathlib import Path

candidates=[Path('src/main.jsx'),Path('main.jsx')]
p=next((x for x in candidates if x.is_file()),None)
if not p:
    raise SystemExit('Could not find src/main.jsx or main.jsx in the current folder.')
s=p.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global s
    if new in s:
        print(f'{label}: already applied')
        return
    if old not in s:
        raise SystemExit(f'{label}: expected code was not found; no file was written.')
    s=s.replace(old,new,1)
    print(f'{label}: applied')

replace_once(
"const isAtRisk=r=>!DONE.includes(r.status)&&dt(r.end)&&dt(r.end)<new Date();",
"const riskInfo=r=>{if(DONE.includes(r.status))return null;let now=new Date(),a=dt(r.start),b=dt(r.end);now=new Date(now.getFullYear(),now.getMonth(),now.getDate());if(b&&b<now)return{kind:'overdue',days:Math.max(1,Math.floor((now-b)/DAY)),label:`Overdue ${Math.max(1,Math.floor((now-b)/DAY))} days`};if(r.type!=='Project'||!a||!b||b<=a||now<=a)return null;let progress=Math.max(0,Math.min(100,Number(r.progress)||0)),progressDate=new Date(a.getTime()+(b-a)*(progress/100)),days=Math.floor((now-progressDate)/DAY);return days>30?{kind:'behind',days,label:`${days} days behind`}:null};const isAtRisk=r=>!!riskInfo(r);",
'At Risk schedule-lag logic')
replace_once(
'<div className="rowlabel" style={{left:p.left}}><strong>{r.title}{r.originSuffix&&<em> {r.originSuffix}</em>}</strong><span>{r.number}{r.type===\'Project\'&&` (${r.progress}%)`}</span></div>',
'<div className="rowlabel" style={{left:p.left}}><strong style={{fontWeight:r.origin&&r.pillar&&r.origin!==r.pillar?400:700,color:r.origin&&r.pillar&&r.origin!==r.pillar?\'#5f707b\':undefined}}>{r.title}{r.originSuffix&&<em> {r.originSuffix}</em>}</strong><span>{r.number}{r.type===\'Project\'&&` (${r.progress}%)`}{dashboardFilter===\'At Risk\'&&riskInfo(r)&&<em style={{marginLeft:7,padding:\'2px 6px\',border:\'1px solid #d59a65\',borderRadius:999,color:\'#9b5427\',background:\'#fff7ed\',fontStyle:\'normal\',fontSize:9}}>{riskInfo(r).label}</em>}</span></div>',
'Timeline cross-pillar weight and risk badge')
replace_once(
"<strong style={{display:'block',fontSize:12,lineHeight:1.3,color:'#223746'}}>{x.title}</strong><span style={{display:'block',fontSize:10,color:'#657887',marginTop:3}}>{x.number} · {fmt(x.start)} → {fmt(x.end)}</span>",
"<strong style={{display:'block',fontSize:12,lineHeight:1.3,color:x.origin&&x.pillar&&x.origin!==x.pillar?'#5f707b':'#223746',fontWeight:x.origin&&x.pillar&&x.origin!==x.pillar?400:700}}>{x.title}</strong><span style={{display:'block',fontSize:10,color:'#657887',marginTop:3}}>{x.number} · {fmt(x.start)} → {fmt(x.end)}</span>",
'Swimlane cross-pillar weight')
replace_once(
">{x.status}</span><span style={{fontSize:9,color:'#748590'}}>{x.fiscalYear||'No FY'}</span>",
">{x.type==='Idea'?(x.state||'Idea'):x.status}</span><span style={{fontSize:9,color:'#748590'}}>{x.fiscalYear||'No FY'}</span>",
'Idea state on swimlane card')
replace_once(
'<small>{x.type} • {x.status}</small>',
"<small>{x.type} • {x.type==='Idea'?(x.state||'Idea'):x.status}</small>",
'Idea state subtitle')
replace_once(
"['Planned date',x.plannedDate]",
"['Idea state',x.type==='Idea'?x.state:''],['Implementation date',x.type==='Idea'?x.implementationDate:''],['Planned date',x.plannedDate]",
'Idea details fields')
p.write_text(s,encoding='utf-8')
print(f'Updated {p}')
