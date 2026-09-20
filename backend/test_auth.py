"""Run against a temporary database, never the user's workbench."""
import os
import tempfile
os.environ['WORKBENCH_DATA'] = tempfile.mkdtemp(prefix='workbench-test-')
from fastapi.testclient import TestClient
from backend.main import app

def test_auth_and_persistence():
    with TestClient(app) as client:
        assert client.get('/api/resources/notes').status_code == 401
        credentials={'username':'test','password':'test-only-password-123'}
        assert client.post('/api/auth/setup',json=credentials).status_code == 201
        assert client.post('/api/auth/setup',json=credentials).status_code == 409
        csrf=client.post('/api/auth/login',json=credentials).json()['csrf']
        assert client.post('/api/resources/notes',json={'title':'private'}).status_code == 403
        headers={'x-csrf-token':csrf}
        record=client.post('/api/resources/articles',json={'title':'Test article'},headers=headers).json()
        assert client.get('/api/public/articles').json() == []
        assert client.put('/api/resources/articles/'+record['id'],json={'title':'Test article','status':'published'},headers=headers).status_code == 200
        assert len(client.get('/api/public/articles').json()) == 1
        assert client.post('/api/auth/logout',headers=headers).status_code == 200
        assert client.get('/api/resources/articles').status_code == 401

def test_origin():
    with TestClient(app) as client:
        assert client.post('/api/auth/setup',headers={'origin':'https://other.example'},json={'username':'x','password':'long-password-123'}).status_code == 403
