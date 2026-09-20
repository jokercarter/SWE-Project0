from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .main import app
from . import features
from . import codex_adapter
from . import management

@app.on_event('shutdown')
async def shutdown():
    for manager,client in list(features.kernels.values()):
        await features.shutdown_kernel(manager,client)
    await codex_adapter.bridge.close()

ROOT=Path(__file__).resolve().parents[1]

@app.get('/app')
@app.get('/app/{route:path}')
@app.get('/portfolio/{route:path}')
@app.get('/blog/{route:path}')
def workbench(route:str=''):
    return FileResponse(ROOT/'workbench-dist'/'index.html')

if (ROOT/'workbench-dist'/'assets').exists():
    app.mount('/assets',StaticFiles(directory=ROOT/'workbench-dist'/'assets'),name='assets')
app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='portfolio')
