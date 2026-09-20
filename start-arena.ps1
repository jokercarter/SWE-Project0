param([int]$Port = 8080, [switch]$Build)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Build) { npm run build; if ($LASTEXITCODE) { throw 'Build failed' } }
if (!(Test-Path 'dist/arena/index.html')) { throw 'Run .\start-arena.ps1 -Build once first.' }
& .venv/Scripts/python.exe -m uvicorn backend.arena_public:app --host 0.0.0.0 --port $Port
