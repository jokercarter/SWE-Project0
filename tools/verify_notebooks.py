"""Execute every bundled lesson in a clean, isolated kernel and save test evidence."""
import asyncio,json,sys,tempfile,time
from pathlib import Path
from jupyter_client import AsyncKernelManager
ROOT=Path(__file__).resolve().parents[1]

async def verify(path):
    nb=json.loads(path.read_text(encoding='utf8'))
    manager=AsyncKernelManager(kernel_name='python3')
    manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    await manager.start_kernel(cwd=tempfile.mkdtemp(prefix=path.stem+'-'))
    client=manager.client();client.start_channels();await client.wait_for_ready(timeout=60)
    errors=[];outputs=0;started=time.monotonic()
    try:
        for index,cell in enumerate(nb['cells']):
            if cell['cell_type']!='code':continue
            msg=client.execute(''.join(cell['source']),allow_stdin=False)
            while True:
                event=await client.get_iopub_msg(timeout=120)
                if event['parent_header'].get('msg_id')!=msg:continue
                kind=event['header']['msg_type'];content=event['content']
                if kind=='error':errors.append({'cell':index,'error':content['ename']+': '+content['evalue']})
                if kind in {'stream','display_data','execute_result'}:outputs+=1
                if kind=='status' and content['execution_state']=='idle':break
    finally:
        await manager.shutdown_kernel(now=True);client.stop_channels()
    result={'week':path.stem,'passed':not errors,'errors':errors,'output_events':outputs,'seconds':round(time.monotonic()-started,2)}
    print(json.dumps(result),flush=True);return result
async def main():
    results=[]
    for path in sorted((ROOT/'notebooks').glob('*.ipynb')):results.append(await verify(path))
    (ROOT/'output').mkdir(exist_ok=True)
    (ROOT/'output/notebook-test-results.json').write_text(json.dumps(results,indent=2),encoding='utf8')
    assert len(results)==12 and all(x['passed'] for x in results)
if __name__=='__main__':asyncio.run(main())
