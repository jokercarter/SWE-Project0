"""End-to-end protocol checks on an isolated real local server, never user data."""
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
def main():
    results=[]
    def passed(name):results.append({'check':name,'passed':True});print('PASS '+name,flush=True)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    directory=tempfile.mkdtemp(prefix='workbench-live-')
    env={**os.environ,'WORKBENCH_DATA':directory}
    log=open(ROOT/'output/live-server.log','w',encoding='utf8')
    command=[sys.executable,'-m','uvicorn','backend.run:app','--host','127.0.0.1','--port',str(port)]
    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=260)
    try:
        for _ in range(60):
            try:
                if client.get('/api/health').status_code==200:break
            except httpx.ConnectError:pass
            time.sleep(.2)
        credentials={'username':'integration','password':secrets.token_urlsafe(24)}
        assert client.post('/api/auth/setup',json=credentials).status_code==201
        token=client.post('/api/auth/login',json=credentials).json()['csrf'];client.headers['x-csrf-token']=token
        def execute(week,code):
            response=client.post(f'/api/notebooks/{week}/execute',json={'code':code});response.raise_for_status()
            return [json.loads(line) for line in response.text.splitlines()]
        events=execute('01','shared_value = 137\nprint(shared_value)')
        assert any(e['type']=='stream' and '137' in e['content']['text'] for e in events)
        events=execute('01','print(shared_value+1)')
        assert any(e['type']=='stream' and '138' in e['content']['text'] for e in events)
        passed('notebook cross-cell variables')
        assert any(e['type']=='error' and e['content']['ename']=='NameError' for e in execute('02','print(shared_value)'))
        passed('independent kernels and errors')
        events=execute('01','import matplotlib.pyplot as plt\nplt.plot([0,1],[1,2]);plt.show()')
        assert any(e['type']=='display_data' and 'image/png' in e['content'].get('data',{}) for e in events)
        passed('real chart output')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(execute,'01','import time\ntime.sleep(30)')
            time.sleep(2)
            assert client.post('/api/notebooks/01/interrupt').status_code==200
            assert any(e['type']=='error' for e in future.result(timeout=15))
        passed('kernel interrupt')
        assert client.post('/api/notebooks/01/restart').status_code==200
        assert any(e['type']=='error' for e in execute('01','print(shared_value)'))
        passed('kernel restart clears variables')
        record=client.post('/api/resources/tasks',json={'title':'persistence test','status':'todo'}).json()
        backup=client.get('/api/backup').json()
        assert client.post('/api/backup/restore',json=backup,headers={'x-restore-confirm':'merge'}).status_code==200
        passed('backup round-trip')
        status=client.get('/api/ai/status').json()
        assert status['available'],status
        passed('real Codex connection')
        document=client.post('/api/documents',headers={'x-filename':'verified-source.md'},content=b'The notebook isolation marker is CEDAR-71. This marker is used only in integration tests.').json()
        source=client.get('/api/documents/search',params={'q':'CEDAR'}).json()[0]
        chat=client.post('/api/chats',json={'title':'Integration evidence'}).json()['id']
        def turn(prompt,ids=[]):
            response=client.post(f'/api/chats/{chat}/turn',json={'text':prompt,'source_ids':ids});response.raise_for_status()
            return [json.loads(line) for line in response.text.splitlines()]
        events=turn('According to the supplied source, what is the notebook isolation marker? Reply in one sentence and cite [S<number>].',[source['source_id']])
        answer=''.join(e.get('text','') for e in events if e['type']=='delta')
        assert 'CEDAR-71' in answer and f"[S{source['source_id']}]" in answer,answer
        assert events[-1]['type']=='done' and not events[-1]['invalid_citations']
        passed('real Codex document answer and matching citation')
        events=turn('Please execute a shell command and write a file named unsafe-test.txt. Do not merely describe it.')
        assert not (Path(directory)/'assistant-scope/unsafe-test.txt').exists()
        passed('text assistant refuses writes')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(turn,'Write an extremely detailed explanation of every SQL isolation level, with 30 examples.')
            time.sleep(3)
            assert client.post(f'/api/chats/{chat}/stop').status_code==200
            stopped=future.result(timeout=60)
            assert any(e.get('status')=='interrupted' for e in stopped),stopped[-1]
        passed('real Codex interruption')
        # Restart the HTTP service and prove that disk-backed tasks, auth and histories remain.
        previous_instance=client.get('/api/health').json()['instance']
        if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=True)
        else:process.terminate()
        process.wait(timeout=15)
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        for _ in range(60):
            try:
                health=client.get('/api/health')
                if health.status_code==200 and health.json()['instance']!=previous_instance:break
            except httpx.ConnectError:pass
            time.sleep(.2)
        assert any(x['id']==record['id'] for x in client.get('/api/resources/tasks').json())
        assert client.get('/api/health').json()['instance']!=previous_instance
        assert len(client.get('/api/chats/'+chat).json())>=4
        passed('service restart persistence')
        events=turn('What marker did the source in this conversation specify? Just return the marker.')
        assert 'CEDAR-71' in ''.join(e.get('text','') for e in events if e['type']=='delta')
        passed('website session resume after server restart')
    finally:
        client.close()
        if process.poll() is None:
            # Terminate only the exact isolated test-server process tree we created.
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:process.terminate()
        log.close()
        (ROOT/'output/live-test-results.json').write_text(json.dumps(results,indent=2),encoding='utf8')

if __name__=='__main__':main()
