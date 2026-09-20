$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pidFile = Join-Path $root '.workbench/server.pid'
if (!(Test-Path -LiteralPath $pidFile)) { Write-Host 'No recorded workbench server.'; exit 0 }
$workbenchPid = [int](Get-Content -LiteralPath $pidFile)
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$workbenchPid" -ErrorAction SilentlyContinue
if (!$process) { Write-Host 'Recorded server is no longer running.'; exit 0 }
if ($process.CommandLine -notlike '*uvicorn backend.run:app*' -or $process.ExecutablePath -notlike "$root*") { throw 'PID no longer belongs to this workbench. Refusing to stop it.' }
# Only terminate the recorded verified server tree, including its own kernels and Codex child.
taskkill /PID $workbenchPid /T /F
if ($LASTEXITCODE) { throw 'Could not stop the workbench process tree.' }
Remove-Item -LiteralPath $pidFile
