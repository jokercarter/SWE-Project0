"""Opt-in live protocol smoke test; uses only a new website-owned test thread."""
import asyncio
import os
import tempfile
import sys
os.environ['WORKBENCH_DATA']=tempfile.mkdtemp(prefix='workbench-codex-probe-')
from backend.codex_adapter import bridge

async def main():
    try:
        await bridge.start()
        print('initialize: PASS',flush=True)
        account=await bridge.rpc('account/read',{'refreshToken':False})
        print('account/read:',(account.get('account') or {}).get('type','configured provider'),flush=True)
        if '--status-only' in sys.argv:return
        result=await bridge.rpc('thread/start',bridge.parameters())
        identifier=result['thread']['id']
        print('independent thread/start: PASS',flush=True)
        queue=asyncio.Queue();bridge.queues[identifier]=queue
        turn=await bridge.rpc('turn/start',{'threadId':identifier,'input':[{'type':'text','text':'This is a website integration test. Remember the marker ORCHID-27. Reply only ORCHID-27. Do not call tools.'}]})
        print('turn/start: PASS',flush=True)
        answer=''
        async with asyncio.timeout(180):
            while True:
                event=await queue.get();method=event['method']
                if method=='item/agentMessage/delta':answer+=event['params']['delta']
                if method in {'error','bridge/error'}:print('generation event:',method,flush=True)
                if method=='turn/completed':
                    print('turn/completed:',event['params']['turn']['status'],flush=True);break
        print('answer:',answer[:300],flush=True)
        assert 'ORCHID-27' in answer
        bridge.queues.pop(identifier,None)
        await bridge.close()
        await bridge.start()
        await bridge.rpc('thread/resume',{'threadId':identifier,**bridge.parameters()})
        print('resume after process restart: PASS',flush=True)
        queue=asyncio.Queue();bridge.queues[identifier]=queue
        await bridge.rpc('turn/start',{'threadId':identifier,'input':[{'type':'text','text':'What marker did I give you? Reply only the marker, no tools.'}]})
        answer=''
        async with asyncio.timeout(180):
            while True:
                event=await queue.get()
                if event['method']=='item/agentMessage/delta':answer+=event['params']['delta']
                if event['method']=='turn/completed':break
        assert 'ORCHID-27' in answer
        print('multi-turn context: PASS',flush=True)
    finally:await bridge.close()

asyncio.run(main())
