// Compatibility entry point. Arbitrary unauthenticated Python execution was removed.
import {spawn} from 'node:child_process';
import {existsSync} from 'node:fs';
const python=process.platform==='win32'?'.venv/Scripts/python.exe':'.venv/bin/python';
if(!existsSync(python)){console.error('Run .\\start.ps1 -Install first.');process.exit(1);}
const child=spawn(python,['-m','uvicorn','backend.run:app','--host','127.0.0.1','--port',process.env.PORT||'4173'],{stdio:'inherit',windowsHide:true});
child.on('exit',code=>process.exit(code||0));
process.on('SIGINT',()=>child.kill());
process.on('SIGTERM',()=>child.kill());
