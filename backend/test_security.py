import json
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from backend.test_features import signed
from backend.main import app, attempts, engine
from backend.codex_adapter import bridge, CodexError

def test_codex_unavailable_is_not_a_fake_answer(signed,monkeypatch):
    monkeypatch.setattr(bridge,'start',AsyncMock(side_effect=CodexError('Codex unavailable; retry manually')))
    response=signed.get('/api/ai/status')
    assert response.status_code==200 and response.json()['available'] is False
    assert 'answer' not in response.json()
    assert signed.post('/api/chats',json={'title':'failure test'}).status_code==503

def test_missing_authentication_is_reported(signed,monkeypatch):
    monkeypatch.setattr(bridge,'start',AsyncMock())
    monkeypatch.setattr(bridge,'rpc',AsyncMock(return_value={'requiresOpenaiAuth':True,'account':None}))
    assert signed.get('/api/ai/status').json()['available'] is False

def test_cross_origin_and_websocket_auth():
    with TestClient(app) as client:
        assert client.get('/api/health',headers={'host':'evil.example'}).status_code==403
        assert client.post('/api/auth/login',headers={'origin':'https://evil.example'},json={'username':'test','password':'test-only-password-123'}).status_code==403
        from starlette.websockets import WebSocketDisconnect
        import pytest
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/api/notebooks/01/ws',headers={'origin':'http://testserver'}):pass

def test_login_rate_limit():
    attempts.clear()
    with TestClient(app) as client:
        for _ in range(10):assert client.post('/api/auth/login',json={'username':'test','password':'incorrect-password-123'}).status_code==401
        assert client.post('/api/auth/login',json={'username':'test','password':'incorrect-password-123'}).status_code==429
    attempts.clear()

def test_backup_cannot_attach_arbitrary_desktop_thread(signed):
    backup=signed.get('/api/backup').json()
    backup['tables']['chats'].append({'id':'not-owned-desktop-thread','title':'Imported','created':1})
    assert signed.post('/api/backup/restore',json=backup,headers={'x-restore-confirm':'merge'}).status_code==200
    assert signed.post('/api/chats/not-owned-desktop-thread/turn',json={'text':'test'}).status_code==409

def test_pdf_and_upload_limits(signed):
    from pathlib import Path
    file=Path('public/pdfs/week-01.pdf').read_bytes()
    response=signed.post('/api/documents',content=file,headers={'x-filename':'week-01.pdf'})
    assert response.status_code==200 and response.json()['pages']>=1
    assert signed.post('/api/documents',content=file,headers={'x-filename':'renamed.pdf'}).json()['duplicate'] is True
    assert signed.post('/api/documents',content=b'x'*(10*1024*1024+1),headers={'x-filename':'large.txt'}).status_code==413
