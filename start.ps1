param([switch]$Install, [int]$Port = 4173)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Install -or !(Test-Path '.venv/Scripts/python.exe')) {
    if (!(Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv }
    & .venv/Scripts/python.exe -m pip install --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.lock.txt
    if ($LASTEXITCODE) { throw 'Python dependency installation failed' }
    npm ci
    if ($LASTEXITCODE) { throw 'Node dependency installation failed' }
}
npm run build
if ($LASTEXITCODE) { throw 'Build failed' }
& .venv/Scripts/python.exe -m alembic upgrade head
if ($LASTEXITCODE) { throw 'Migration failed' }
New-Item -ItemType Directory -Path '.workbench' -Force | Out-Null
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) { throw "Port $Port is already in use. Stop its known owner or choose -Port." }
$workbenchProcess = Start-Process -FilePath "$PSScriptRoot/.venv/Scripts/python.exe" -ArgumentList @('-m','uvicorn','backend.run:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput "$PSScriptRoot/.workbench/server.log" -RedirectStandardError "$PSScriptRoot/.workbench/server-error.log"
$workbenchProcess.Id | Set-Content '.workbench/server.pid'
for ($attempt=0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    try { $health=Invoke-RestMethod "http://127.0.0.1:$Port/api/health"; if ($health.status -eq 'ok') { Write-Host "Workbench ready: http://127.0.0.1:$Port/app/"; exit 0 } } catch {}
}
throw 'Server did not become ready. Check .workbench/server-error.log.'
