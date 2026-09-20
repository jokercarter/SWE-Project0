import json
import pytest
from fastapi.testclient import TestClient
# test_auth sets a temporary data directory before application imports.
from backend.test_auth import app
from backend import features, management, codex_adapter

@pytest.fixture
def signed():
    with TestClient(app) as client:
        credentials={'username':'test','password':'test-only-password-123'}
        client.post('/api/auth/setup',json=credentials)
        client.headers['x-csrf-token']=client.post('/api/auth/login',json=credentials).json()['csrf']
        yield client

def test_documents_backup_and_sources(signed):
    result=signed.post('/api/documents',content='数据库事务要么提交要么回滚。 SQL transactions are atomic.'.encode(),headers={'x-filename':'%E7%AC%94%E8%AE%B0.md'})
    assert result.status_code==200
    identifier=result.json()['id']
    assert signed.get('/api/documents/'+identifier).json()['name']=='笔记.md'
    sources=signed.get('/api/documents/search?q=transactions').json()
    assert sources and sources[0]['page']==1
    assert signed.get('/api/documents/search?q=事务').json()
    assert signed.post('/api/documents',content=b'a',headers={'x-filename':'a.exe'}).status_code==415
    assert signed.post('/api/documents',content=b'%PDF-invalid',headers={'x-filename':'a.pdf'}).status_code==422
    backup=signed.get('/api/backup').json()
    assert 'admin' not in backup['tables'] and 'sessions' not in backup['tables']
    assert signed.post('/api/backup/preview',json=backup).status_code==200
    assert signed.post('/api/backup/restore',json=backup).status_code==422
    assert signed.post('/api/backup/restore',json=backup,headers={'x-restore-confirm':'merge'}).status_code==200
    assert signed.get('/api/documents/search?q=transactions').json()[0]['source_id']==sources[0]['source_id']
    backup['tables']['records'].append({'invalid':'row'})
    assert signed.post('/api/backup/restore',json=backup,headers={'x-restore-confirm':'merge'}).status_code==422

def test_csv_and_crud(signed):
    record=signed.post('/api/resources/applications',json={'title':'=badformula','status':'saved','body':json.dumps({'company':'Example','reflection':'one,two\nthree'})}).json()
    output=signed.get('/api/applications/export')
    assert "'=badformula" in output.text
    assert signed.post('/api/applications/import',content=output.content).json()['imported']>=1
    assert signed.post('/api/applications/import',content=b'wrong\nvalue').status_code==422
    assert signed.delete('/api/resources/applications/'+record['id']).status_code==200

def test_notebook_schema_and_access(signed):
    for week in range(1,13):
        result=signed.get(f'/api/notebooks/{week:02}')
        assert result.status_code==200
        nb=result.json()
        features.validate_notebook(nb)
        assert len(''.join(nb['cells'][1]['source']))>100
    nb=signed.get('/api/notebooks/01').json()
    assert signed.put('/api/notebooks/01',json=nb).status_code==200
    nb['cells'][1]['outputs']=[{'output_type':'bogus'}]
    assert signed.put('/api/notebooks/01',json=nb).status_code==422
    assert signed.get('/api/notebooks/../../config').status_code!=200
    with TestClient(app) as visitor:
        for path in ['resources/tasks','documents','notebooks/01','chats','ai/status','backup']:
            assert visitor.get('/api/'+path).status_code==401
        assert visitor.post('/api/notebooks/01/execute',json={'code':'print(1)'}).status_code==401
        assert visitor.post('/api/chats',json={}).status_code==401

def test_curriculum(signed):
    data=signed.get('/api/curriculum').json()
    assert len(data)==12
    assert all(len(w['chapters'])==4 for w in data)
