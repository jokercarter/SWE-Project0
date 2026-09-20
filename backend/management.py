"""Portable data backups, application CSV and curriculum APIs."""
import csv
import io
import json
import secrets
import time
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import text
from .main import app, engine, session, KINDS, Record

ROOT=Path(__file__).resolve().parents[1]

@app.get('/api/curriculum')
def curriculum():
    return json.loads((ROOT/'public/curriculum.json').read_text(encoding='utf8'))

@app.get('/api/backup')
def backup(auth=Depends(session)):
    # JSON data only: no credentials, sessions, executable SQL or kernel working files.
    with engine.connect() as db:
        payload={'version':1,'created':time.time(),'tables':{table:[dict(x) for x in db.execute(text('SELECT * FROM '+table)).mappings()] for table in ['records','documents','notebooks','activity','chats','messages']}}
    return Response(json.dumps(payload,ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':'attachment; filename=workbench-backup.json'})

@app.post('/api/backup/preview')
async def preview(request:Request,auth=Depends(session)):
    data=await read_backup(request)
    return {'counts':{k:len(v) for k,v in data['tables'].items()},'mode':'Merge by ID; existing records with matching IDs are replaced. Credentials remain unchanged.'}

async def read_backup(request):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>30_000_000:raise HTTPException(413,'Backup exceeds 30 MB')
    try:
        body=json.loads(data)
        if body['version']!=1:raise ValueError()
        allowed={'records':{'id','kind','title','body','status','updated'},'documents':{'id','name','hash','content','created'},'notebooks':{'id','content'},'activity':{'id','action','created'},'chats':{'id','title','created'},'messages':{'id','chat_id','role','content','sources','status','created'}}
        if set(body['tables'])!=set(allowed):raise ValueError()
        for table,rows in body['tables'].items():
            if not isinstance(rows,list) or len(rows)>100000:raise ValueError()
            for row in rows:
                if set(row)!=allowed[table]:raise ValueError()
                if table=='records':
                    if row['kind'] not in KINDS:raise ValueError()
                    Record(**row)
                if table=='documents':
                    pages=json.loads(row['content'])
                    if not isinstance(pages,list) or not all(isinstance(p,str) for p in pages):raise ValueError()
                if table=='notebooks':
                    from .features import validate_notebook
                    validate_notebook(json.loads(row['content']))
        return body
    except Exception:raise HTTPException(422,'Invalid backup schema or content')

@app.post('/api/backup/restore')
async def restore(request:Request,auth=Depends(session)):
    body=await read_backup(request)
    if request.headers.get('x-restore-confirm')!='merge':raise HTTPException(422,'Preview and confirm merge first')
    with engine.begin() as db:
        for table,rows in body['tables'].items():
            for row in rows:
                columns=','.join(row);values=','.join(':'+k for k in row)
                updates=','.join(k+'=excluded.'+k for k in row if k!='id')
                db.execute(text(f'INSERT INTO {table} ({columns}) VALUES ({values}) ON CONFLICT(id) DO UPDATE SET {updates}'),row)
        db.execute(text('DELETE FROM chunks'))
        for document in db.execute(text('SELECT id,content FROM documents')).mappings().all():
            for page,content in enumerate(json.loads(document['content']),1):
                for start in range(0,len(content),1000):
                    from .features import source_id
                    db.execute(text('INSERT INTO chunks(rowid,document_id,page,content) VALUES (:source,:id,:page,:content)'),{'source':source_id(document['id'],page,start),'id':document['id'],'page':page,'content':content[start:start+1200]})
        db.execute(text('INSERT INTO activity(action,created) VALUES (:action,:created)'),{'action':'Restored backup (merge)','created':time.time()})
    return {'ok':True}

CSV_FIELDS=['title','status','company','role','url','due','interview','tags','reflection','body']

@app.get('/api/applications/export')
def export_csv(auth=Depends(session)):
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=CSV_FIELDS);writer.writeheader()
    with engine.connect() as db:
        for row in db.execute(text("SELECT * FROM records WHERE kind='applications'")).mappings():
            try:details=json.loads(row['body'])
            except ValueError:details={'body':row['body']}
            item={k:str(details.get(k,'')) for k in CSV_FIELDS};item.update(title=row['title'],status=row['status'])
            # Spreadsheet formula injection protection.
            writer.writerow({k: "'"+v if v.startswith(('=','+','-','@','\t','\r')) else v for k,v in item.items()})
    return Response('\ufeff'+stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=applications.csv'})

@app.post('/api/applications/import')
async def import_csv(request:Request,auth=Depends(session)):
    raw=await request.body()
    if len(raw)>2_000_000:raise HTTPException(413,'CSV too large')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        if not reader.fieldnames or 'title' not in reader.fieldnames:raise ValueError()
        rows=list(reader)
        if len(rows)>2000:raise ValueError()
        records=[]
        for row in rows:
            record=Record(title=row['title'],status=row.get('status') or 'saved',body=json.dumps({k:row.get(k,'') for k in CSV_FIELDS if k not in {'title','status'}},ensure_ascii=False))
            records.append({**record.model_dump(),'id':secrets.token_hex(16),'kind':'applications','updated':time.time()})
    except Exception:raise HTTPException(422,'Invalid UTF-8 CSV; title column required')
    with engine.begin() as db:
        for record in records:db.execute(text('INSERT INTO records VALUES (:id,:kind,:title,:body,:status,:updated)'),record)
    return {'imported':len(records)}
