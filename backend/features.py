"""Persistence, document search and authenticated Jupyter execution."""
import asyncio
import hashlib
import json
import time
from pathlib import Path
from urllib.parse import unquote
import sys
import os
import subprocess
import nbformat
from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from jupyter_client import AsyncKernelManager
from pydantic import BaseModel, Field
from sqlalchemy import text
from .main import app, engine, session, DATA, audit

def source_id(document_id,page,start):
    # Stable within backups and deduplicated uploads; below JS safe-integer limit.
    return int(hashlib.sha256(f'{document_id}:{page}:{start}'.encode()).hexdigest()[:13],16)

def locate_sources(rows,db):
    """Attach original-page paragraph/character positions without returning other pages."""
    documents={}
    for row in rows:
        identifier=row['document_id']
        if identifier not in documents:
            documents[identifier]=json.loads(db.execute(text('SELECT content FROM documents WHERE id=:id'),{'id':identifier}).scalar_one())
        page=documents[identifier][int(row['page'])-1]
        start=max(0,page.find(row['content']))
        row.update(paragraph=page[:start].count('\n\n')+1,start=start,end=start+len(row['content']))
    return rows

with engine.begin() as db:
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,name TEXT,hash TEXT UNIQUE,content TEXT,created REAL)')
    db.exec_driver_sql('CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(document_id UNINDEXED, page UNINDEXED, content)')
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS notebooks(id TEXT PRIMARY KEY,content TEXT)')

@app.get('/api/dashboard')
def dashboard(auth=Depends(session)):
    with engine.connect() as db:
        counts=[dict(x) for x in db.execute(text('SELECT kind,status,count(*) AS count FROM records GROUP BY kind,status')).mappings()]
        activity=[dict(x) for x in db.execute(text('SELECT * FROM activity ORDER BY id DESC LIMIT 30')).mappings()]
    return {'counts':counts,'activity':activity}

@app.get('/api/documents')
def documents(auth=Depends(session)):
    with engine.connect() as db:
        return [dict(x) for x in db.execute(text('SELECT id,name,created FROM documents ORDER BY created DESC')).mappings()]

@app.post('/api/documents')
async def upload(request: Request, auth=Depends(session)):
    from io import BytesIO
    from pypdf import PdfReader
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>10*1024*1024:
            raise HTTPException(413,'Maximum file size is 10 MB')
    name=Path(unquote(request.headers.get('x-filename','document.txt')).replace('\\','/')).name
    extension=Path(name).suffix.lower()
    if extension not in {'.txt','.md','.pdf'}: raise HTTPException(415,'Use PDF, TXT or Markdown')
    digest=hashlib.sha256(data).hexdigest()
    try:
        def parse():
            return [p.extract_text() or '' for p in PdfReader(BytesIO(data)).pages] if extension=='.pdf' else [data.decode('utf-8')]
        pages=await asyncio.to_thread(parse)
    except Exception:
        raise HTTPException(422,'Cannot extract text from this file')
    if not any(p.strip() for p in pages): raise HTTPException(422,'No text found; scanned PDFs require OCR')
    if sum(map(len,pages))>5_000_000:raise HTTPException(413,'Extracted text exceeds 5 MB')
    with engine.begin() as db:
        existing=db.execute(text('SELECT id FROM documents WHERE hash=:hash'),{'hash':digest}).first()
        if existing:return {'id':existing[0],'duplicate':True}
        db.execute(text('INSERT INTO documents VALUES (:id,:name,:hash,:content,:created)'),{'id':digest,'hash':digest,'name':name,'content':json.dumps(pages,ensure_ascii=False),'created':time.time()})
        for page,content in enumerate(pages,1):
            for start in range(0,len(content),1000):
                db.execute(text('INSERT INTO chunks(rowid,document_id,page,content) VALUES (:source,:id,:page,:content)'),{'source':source_id(digest,page,start),'id':digest,'page':page,'content':content[start:start+1200]})
    audit('Indexed document')
    return {'id':digest,'pages':len(pages)}

@app.get('/api/documents/search')
def search(q:str='',auth=Depends(session)):
    if not q.strip(): return []
    with engine.connect() as db:
        # Quote tokens to avoid interpreting user text as FTS syntax. LIKE handles Chinese substrings.
        query=' OR '.join('"'+word.replace('"','""')+'"' for word in q[:200].split())
        found=[dict(x) for x in db.execute(text('SELECT chunks.rowid AS source_id,document_id,page,chunks.content,documents.name FROM chunks JOIN documents ON documents.id=chunks.document_id WHERE chunks MATCH :query ORDER BY rank LIMIT 20'),{'query':query}).mappings()]
        if found:return locate_sources(found,db)
        return locate_sources([dict(x) for x in db.execute(text('SELECT chunks.rowid AS source_id,document_id,page,chunks.content,documents.name FROM chunks JOIN documents ON documents.id=chunks.document_id WHERE instr(chunks.content,:query)>0 LIMIT 20'),{'query':q[:200]}).mappings()],db)

@app.get('/api/documents/{identifier}')
def document(identifier:str,auth=Depends(session)):
    with engine.connect() as db:
        row=db.execute(text('SELECT * FROM documents WHERE id=:id'),{'id':identifier}).mappings().first()
    if not row:raise HTTPException(404)
    return {'id':identifier,'name':row['name'],'pages':json.loads(row['content'])}

class Notebook(BaseModel):
    nbformat:int=4
    nbformat_minor:int=5
    metadata:dict=Field(default_factory=dict)
    cells:list[dict]=Field(default_factory=list,max_length=200)

@app.get('/api/notebooks/{identifier}')
def notebook(identifier:str,auth=Depends(session)):
    with engine.connect() as db:
        row=db.execute(text('SELECT content FROM notebooks WHERE id=:id'),{'id':identifier}).first()
    if row:return json.loads(row[0])
    if identifier not in {f'{i:02}' for i in range(1,13)}:raise HTTPException(404,'Unknown notebook')
    return json.loads((Path(__file__).resolve().parents[1]/'notebooks'/f'week-{identifier}.ipynb').read_text(encoding='utf8'))

def validate_notebook(data):
    notebook=nbformat.from_dict(data)
    nbformat.validate(notebook)
    if len(notebook.cells)>200:raise ValueError('Too many cells')
    return notebook

@app.put('/api/notebooks/{identifier}')
def save_notebook(identifier:str,body:Notebook,auth=Depends(session)):
    try:normalized=validate_notebook(body.model_dump())
    except Exception:raise HTTPException(422,'Invalid ipynb structure')
    content=nbformat.writes(normalized)
    if len(content)>2_000_000:raise HTTPException(413,'Notebook too large')
    with engine.begin() as db:
        db.execute(text('INSERT INTO notebooks VALUES (:id,:content) ON CONFLICT(id) DO UPDATE SET content=excluded.content'),{'id':identifier,'content':content})
    return {'ok':True}

kernels={}
locks={}
cancel_events={}

async def shutdown_kernel(manager,client):
    """Stop the exact owned process tree, including Windows venv launcher children."""
    pid=getattr(manager.provisioner,'pid',None)
    if os.name=='nt' and pid:
        await asyncio.to_thread(subprocess.run,['taskkill','/PID',str(pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    await manager.shutdown_kernel(now=True)
    client.stop_channels()
class Execute(BaseModel):
    code:str=Field(max_length=100000)

@app.post('/api/notebooks/{identifier}/execute')
async def execute(identifier:str,body:Execute,auth=Depends(session)):
    if identifier not in {f'{i:02}' for i in range(1,13)}:raise HTTPException(404,'Unknown notebook')
    lock=locks.setdefault(identifier,asyncio.Lock())
    if lock.locked():raise HTTPException(409,'Kernel is busy')
    await lock.acquire()
    audit(f'Executed notebook {identifier}')
    cancellation=asyncio.Event();cancel_events[identifier]=cancellation
    async def events():
        manager=None
        try:
            if identifier not in kernels:
                manager=AsyncKernelManager(kernel_name='python3')
                # Explicit interpreter: never inherit a conflicting global Anaconda kernel spec.
                manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
                directory=DATA/'kernels'/hashlib.sha256(identifier.encode()).hexdigest()
                directory.mkdir(parents=True,exist_ok=True)
                await manager.start_kernel(cwd=str(directory))
                client=manager.client();client.start_channels()
                await client.wait_for_ready(timeout=30)
                kernels[identifier]=(manager,client)
            manager,client=kernels[identifier]
            msg_id=client.execute(body.code,allow_stdin=False,stop_on_error=True)
            total=0
            interrupted_at=None
            async with asyncio.timeout(120):
                while True:
                    if cancellation.is_set():
                        interrupted_at=interrupted_at or time.monotonic()
                        if time.monotonic()-interrupted_at>2:
                            # Windows/native blocking code may not respond to SIGINT.
                            # Terminate this kernel only and report the loss of variables explicitly.
                            await shutdown_kernel(manager,client);kernels.pop(identifier,None)
                            yield json.dumps({'type':'error','content':{'ename':'KernelInterrupted','evalue':'Blocking code did not respond to interrupt. Kernel stopped; variables were cleared. Run earlier cells again.','traceback':[]}})+'\n'
                            break
                    try:message=await client.get_iopub_msg(timeout=.5)
                    except Exception as error:
                        from queue import Empty
                        if isinstance(error,(Empty,asyncio.TimeoutError)):continue
                        raise
                    if message.get('parent_header',{}).get('msg_id')!=msg_id:continue
                    kind=message['header']['msg_type'];content=message['content']
                    packet=json.dumps({'type':kind,'content':content},ensure_ascii=False)+'\n'
                    total+=len(packet)
                    if total>5_000_000:raise ValueError('Output limit exceeded')
                    yield packet
                    if kind=='status' and content.get('execution_state')=='idle':break
        except (Exception,asyncio.CancelledError) as error:
            if manager:
                await manager.interrupt_kernel()
            if not isinstance(error,asyncio.CancelledError):
                yield json.dumps({'type':'error','content':{'ename':type(error).__name__,'evalue':'Execution interrupted, output limit reached or kernel unavailable','traceback':[]}})+'\n'
        finally:
            cancel_events.pop(identifier,None)
            lock.release()
    return StreamingResponse(events(),media_type='application/x-ndjson')

@app.post('/api/notebooks/{identifier}/{action}')
async def kernel_action(identifier:str,action:str,auth=Depends(session)):
    if action not in {'interrupt','restart'}:raise HTTPException(404)
    if identifier in kernels:
        manager,client=kernels[identifier]
        if action=='interrupt':
            if identifier in cancel_events:cancel_events[identifier].set()
            await manager.interrupt_kernel()
        else:
            if locks.get(identifier) and locks[identifier].locked():raise HTTPException(409,'Interrupt the active cell before restarting')
            await shutdown_kernel(manager,client);kernels.pop(identifier)
    return {'ok':True}

@app.websocket('/api/notebooks/{identifier}/ws')
async def kernel_socket(websocket:WebSocket,identifier:str):
    """Cookie plus first-message CSRF; secrets never appear in the websocket URL."""
    from urllib.parse import urlsplit
    import secrets
    host=websocket.headers.get('host','')
    origin=websocket.headers.get('origin','')
    if websocket.url.hostname not in {'127.0.0.1','localhost','testserver'} or urlsplit(origin).netloc!=host:
        await websocket.close(code=1008);return
    try:
        scope=dict(websocket.scope);scope.update(type='http',method='GET')
        auth=session(Request(scope))
    except HTTPException:
        await websocket.close(code=1008);return
    await websocket.accept()
    iterator=None
    try:
        payload=await asyncio.wait_for(websocket.receive_json(),10)
        if not secrets.compare_digest(str(payload.get('csrf','')),auth['csrf']):
            await websocket.close(code=1008);return
        response=await execute(identifier,Execute(code=payload.get('code','')),auth)
        iterator=response.body_iterator
        async for packet in iterator:
            await websocket.send_text(packet)
        await websocket.send_json({'type':'finished'})
    except WebSocketDisconnect:
        if identifier in kernels:await kernels[identifier][0].interrupt_kernel()
    except Exception:
        try:await websocket.send_json({'type':'error','content':{'ename':'ExecutionError','evalue':'Execution failed or kernel is busy','traceback':[]}})
        except Exception:pass
    finally:
        if iterator and hasattr(iterator,'aclose'):await iterator.aclose()
        try:await websocket.close()
        except RuntimeError:pass
