#!/usr/bin/env python3
"""Build public/roadmap_data.json from four ServiceNow Excel exports.

Designed for a UT System OneDrive-synced folder now and a future ServiceNow API source later.
This script does not call Roadmunk, GraphQL, email, Power Automate, or GitHub APIs.
"""
from __future__ import annotations
import argparse, hashlib, html, json, re, shutil, sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from pipeline_rules import process_df, process_ideas_df

FILES={
 'Project':'PMO Daily Roadmunk - Projects*.xlsx',
 'Demand':'PMO Daily Roadmunk - Demands*.xlsx',
 'Enhancement':'PMO Daily Roadmunk - Enhancements*.xlsx',
 'Idea':'PMO Daily Roadmunk - Ideas*.xlsx',
}
ENDPOINT={'Project':'pm_project','Demand':'dmn_demand','Enhancement':'rm_enhancement','Idea':'idea'}
ROLLUP={'APPS':'OTIS','INFRA':'OTIS','OTISCS':'OTIS','OTIS-CS':'OTIS','SI':'OTIS','SIS SERVICES':'B&CS'}

def latest(folder:Path, pattern:str)->Path:
    files=[p for p in folder.glob(pattern) if not p.name.startswith('~$')]
    if not files: raise FileNotFoundError(f'Missing source: {pattern}')
    return max(files,key=lambda p:p.stat().st_mtime)

def clean_description(v):
    s=str(v or ''); m=re.search(r"href=['\"]([^'\"]+)['\"]",s)
    link=html.unescape(m.group(1)) if m else ''
    text=re.sub(r'<br\s*/?>','\n',s,flags=re.I);text=re.sub(r'<[^>]+>','',text);text=html.unescape(text)
    text=re.sub(r'\n\s*(Project|Idea) Link:.*','',text,flags=re.I|re.S).strip()
    return text,link

def build(input_dir:Path):
    frames=[]; sources={}
    for typ,pattern in FILES.items():
        path=latest(input_dir,pattern); raw=pd.read_excel(path,engine='openpyxl')
        out=process_ideas_df(raw) if typ=='Idea' else process_df(raw,typ)
        frames.append(out);sources[typ]={'file':path.name,'rows':len(raw),'modifiedUtc':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat()}
    df=pd.concat(frames,ignore_index=True)
    source_count=int(df['SN Project Number'].nunique())
    df['Category']=df['Pillar'].astype(str)
    df['Pillar']=df['Pillar'].replace(ROLLUP);df['Originating Pillar']=df['Originating Pillar'].replace(ROLLUP)
    df['External ID']=df['SN Project Number'].astype(str)+'_'+df['Pillar'].astype(str)+'_'+df['Category'].astype(str)
    df=df.drop_duplicates('External ID').reset_index(drop=True)
    # Stable aliases retained only as fallback; current UI uses actual title.
    counts=defaultdict(int);aliases={}
    for _,r in df[['SN Project Number','Type','Originating Pillar']].drop_duplicates().iterrows():
        k=(str(r['Type']),str(r['Originating Pillar']));counts[k]+=1;aliases[str(r['SN Project Number'])]=f'{k[0]} {k[1]} {counts[k]}'
    items=[]
    for _,r in df.iterrows():
        num=str(r['SN Project Number']);typ=str(r['Type']);pillar=str(r['Pillar']);origin=str(r['Originating Pillar']);category=str(r['Category'])
        desc,link=clean_description(r.get('Description_Raw',''))
        if not link:link=f'https://utsystem.service-now.com/{ENDPOINT[typ]}.do?sysparm_query=number={num}'
        title=str(r.get('Raw_Title') or r.get('Title') or aliases[num]).strip()
        items.append({'id':str(r['External ID']),'number':num,'type':typ,'title':title,'alias':aliases[num],
          'origin':origin,'pillar':pillar,'category':category,'originSuffix':'' if pillar==origin else f'*{origin}*',
          'start':str(r.get('Start Date','')),'end':str(r.get('End Date','')),'progress':int(float(r.get('% Complete',0) or 0)),
          'status':str(r.get('Status','')),'risk':str(r.get('Risk','')),'active':str(r.get('Active','')),
          'fiscalYear':str(r.get('Cleaned_Fiscal_Year_Value','')),'campus':str(r.get('Campus','')),'teams':str(r.get('Teams','')),
          'fc':str(r.get('Functional Committee','')),'manager':str(r.get('Project Manager','')),'plannedDate':str(r.get('Planned Date','')),
          'description':desc,'serviceNowUrl':link})
    payload={'generated':datetime.now(timezone.utc).isoformat(),'sourceCount':source_count,'expandedCount':len(items),'items':items}
    validate(payload)
    return payload,sources

def validate(data):
    if data['sourceCount']<100: raise ValueError(f"Source count suspiciously low: {data['sourceCount']}")
    if data['expandedCount']<100: raise ValueError(f"Expanded count suspiciously low: {data['expandedCount']}")
    ids=[x['id'] for x in data['items']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate item IDs found')
    required=('number','type','title','pillar','category','status','serviceNowUrl')
    missing=[x.get('id') for x in data['items'] if any(not str(x.get(k,'')).strip() for k in required)]
    if missing:raise ValueError(f'Missing required fields on {len(missing)} rows; first: {missing[:5]}')

def atomic_write(path:Path,data):
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8');tmp.replace(path)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input-dir',required=True);ap.add_argument('--output',default='public/roadmap_data.json');ap.add_argument('--status',default='public/roadmap_status.json');ap.add_argument('--archive-dir')
    a=ap.parse_args(); payload,sources=build(Path(a.input_dir));atomic_write(Path(a.output),payload)
    status={'lastSuccessfulRefresh':payload['generated'],'sourceRecords':payload['sourceCount'],'roadmapLines':payload['expandedCount'],'sources':sources}
    atomic_write(Path(a.status),status)
    if a.archive_dir:
        d=Path(a.archive_dir)/datetime.now().strftime('%Y%m%d_%H%M%S');d.mkdir(parents=True,exist_ok=True)
        for meta in sources.values():shutil.copy2(Path(a.input_dir)/meta['file'],d/meta['file'])
    print(json.dumps(status,indent=2))
if __name__=='__main__':main()
