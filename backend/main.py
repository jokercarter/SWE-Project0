"""Local workbench API. Private resources require a session and CSRF token."""
import hashlib
import os
import secrets
import time
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, event, text

DATA = Path(os.environ.get('WORKBENCH_DATA', Path(__file__).resolve().parents[1] / '.workbench'))
DATA.mkdir(parents=True, exist_ok=True)
engine = create_engine(f'sqlite:///{DATA / "workbench.db"}')

@event.listens_for(engine, 'connect')
def configure(connection, _):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')

with engine.begin() as db:
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS admin (id INTEGER PRIMARY KEY CHECK(id=1), username TEXT NOT NULL, password TEXT NOT NULL)')
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, csrf TEXT NOT NULL, expires REAL NOT NULL)')
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, status TEXT NOT NULL, updated REAL NOT NULL)')
    db.exec_driver_sql('CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, action TEXT NOT NULL, created REAL NOT NULL)')

app = FastAPI(title='Joker Carter Workbench')
INSTANCE = secrets.token_hex(8)
hasher = PasswordHasher()
attempts = {}
KINDS = {'tasks', 'notes', 'applications', 'projects', 'articles', 'progress', 'courses', 'profile', 'study', 'legacy', 'links'}

def audit(action):
    """Only operation names, never bodies, credentials or model prompts."""
    with engine.begin() as db:
        db.execute(text('INSERT INTO activity(action,created) VALUES (:action,:created)'),{'action':action,'created':time.time()})

@app.middleware('http')
async def local_boundary(request: Request, call_next):
    from starlette.responses import JSONResponse
    from urllib.parse import urlsplit
    if request.url.hostname not in {'localhost', '127.0.0.1', 'testserver'}:
        return JSONResponse({'detail': 'Invalid host'}, status_code=403)
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.headers.get('host'):
        return JSONResponse({'detail': 'Cross-origin request denied'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response

def session(request: Request):
    token = hashlib.sha256(request.cookies.get('workbench_session', '').encode()).hexdigest()
    with engine.connect() as db:
        row = db.execute(text('SELECT * FROM sessions WHERE token=:token AND expires>:now'), {'token': token, 'now': time.time()}).mappings().first()
    if not row:
        raise HTTPException(401, 'Please sign in')
    if request.method not in {'GET', 'HEAD', 'OPTIONS'} and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
        raise HTTPException(403, 'Invalid CSRF token')
    return dict(row)

class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=12, max_length=256)

class Record(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default='', max_length=100000)
    status: str = Field(default='draft', max_length=40)

@app.get('/api/health')
def health():
    with engine.connect() as db:
        db.execute(text('SELECT 1'))
    return {'status': 'ok', 'instance': INSTANCE}

@app.get('/api/auth/status')
def auth_status():
    with engine.connect() as db:
        return {'setupRequired': db.execute(text('SELECT id FROM admin')).first() is None}

@app.post('/api/auth/setup', status_code=201)
def setup(credentials: Credentials):
    with engine.begin() as db:
        result = db.execute(text('INSERT OR IGNORE INTO admin VALUES (1,:username,:password)'), {'username': credentials.username, 'password': hasher.hash(credentials.password)})
        if not result.rowcount:
            raise HTTPException(409, 'Administrator already configured')
    return {'ok': True}

@app.post('/api/auth/login')
def login(credentials: Credentials, request: Request, response: Response):
    client = request.client.host
    now = time.time()
    recent = [t for t in attempts.get(client, []) if now-t < 300]
    attempts[client] = recent
    if len(recent) >= 10:
        raise HTTPException(429, 'Try again in five minutes')
    recent.append(now)
    with engine.begin() as db:
        admin = db.execute(text('SELECT * FROM admin')).mappings().first()
        try:
            if not admin or credentials.username != admin['username']:
                raise HTTPException(401, 'Invalid credentials')
            hasher.verify(admin['password'], credentials.password)
        except VerificationError:
            raise HTTPException(401, 'Invalid credentials')
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute(text('INSERT INTO sessions VALUES (:token,:csrf,:expires)'), {'token': hashlib.sha256(token.encode()).hexdigest(), 'csrf': csrf, 'expires': now+28800})
    attempts.pop(client, None)
    response.set_cookie('workbench_session', token, httponly=True, samesite='strict', max_age=28800)
    return {'csrf': csrf}

@app.get('/api/auth/me')
def me(auth=Depends(session)):
    return {'csrf': auth['csrf']}

@app.post('/api/auth/logout')
def logout(response: Response, auth=Depends(session)):
    with engine.begin() as db:
        db.execute(text('DELETE FROM sessions WHERE token=:token'), auth)
    response.delete_cookie('workbench_session')
    return {'ok': True}

def check_kind(kind):
    if kind not in KINDS:
        raise HTTPException(404, 'Unknown resource')

@app.get('/api/resources/{kind}')
def records(kind: str, auth=Depends(session)):
    check_kind(kind)
    with engine.connect() as db:
        return [dict(row) for row in db.execute(text('SELECT * FROM records WHERE kind=:kind ORDER BY updated DESC'), {'kind':kind}).mappings()]

@app.post('/api/resources/{kind}', status_code=201)
def create(kind: str, record: Record, auth=Depends(session)):
    check_kind(kind)
    data = {**record.model_dump(), 'id':secrets.token_hex(16), 'kind':kind, 'updated':time.time()}
    with engine.begin() as db:
        db.execute(text('INSERT INTO records VALUES (:id,:kind,:title,:body,:status,:updated)'), data)
        db.execute(text('INSERT INTO activity(action,created) VALUES (:action,:created)'), {'action':f'Created {kind}', 'created':data['updated']})
    return data

@app.put('/api/resources/{kind}/{identifier}')
def update(kind: str, identifier: str, record: Record, auth=Depends(session)):
    check_kind(kind)
    with engine.begin() as db:
        result=db.execute(text('UPDATE records SET title=:title,body=:body,status=:status,updated=:updated WHERE id=:id AND kind=:kind'), {**record.model_dump(), 'updated':time.time(), 'id':identifier, 'kind':kind})
        if not result.rowcount:
            raise HTTPException(404, 'Record not found')
    audit(f'Updated {kind}: {record.status}')
    return {'ok':True}

@app.get('/api/public/{kind}')
def published(kind: str):
    if kind not in {'projects','articles','profile','courses'}:
        raise HTTPException(404)
    with engine.connect() as db:
        return [dict(row) for row in db.execute(text("SELECT * FROM records WHERE kind=:kind AND status='published' ORDER BY updated DESC"), {'kind':kind}).mappings()]

@app.delete('/api/resources/{kind}/{identifier}')
def delete_record(kind: str, identifier: str, auth=Depends(session)):
    check_kind(kind)
    with engine.begin() as db:
        db.execute(text('DELETE FROM records WHERE kind=:kind AND id=:id'), {'kind':kind,'id':identifier})
        db.execute(text('INSERT INTO activity(action,created) VALUES (:action,:created)'), {'action':f'Deleted {kind}', 'created':time.time()})
    return {'ok':True}
