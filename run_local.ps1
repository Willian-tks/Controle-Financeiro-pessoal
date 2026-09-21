$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
$frontendDir = Join-Path $repoRoot "frontend"
$logDir = Join-Path $repoRoot "work\local-logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) { $pythonExe = (Get-Command python -ErrorAction Stop).Source }
$nodeExe = (Get-Command node -ErrorAction Stop).Source
$vitePath = Join-Path $frontendDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path $vitePath)) { throw "Dependências ausentes. Execute npm ci --include=dev na pasta frontend." }

# Os processos filhos herdam estas variáveis; não interpolar comandos PowerShell.
$env:LOCAL_DEV_FORCE_SQLITE = "1"
$env:CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
$env:JWT_SECRET = "dev-local-secret-change-me"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"

function Test-LocalHttp([string]$Url) {
    try { return (Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 }
    catch { return $false }
}

if (-not (Test-LocalHttp "http://127.0.0.1:8000/health")) {
    Start-Process -FilePath $pythonExe -ArgumentList @("-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $repoRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "api.out.log") -RedirectStandardError (Join-Path $logDir "api.err.log") | Out-Null
}
if (-not (Test-LocalHttp "http://127.0.0.1:5173/index.html")) {
    Start-Process -FilePath $nodeExe -ArgumentList @('"' + $vitePath + '"', "--host", "127.0.0.1", "--port", "5173", "--strictPort") -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir "frontend.out.log") -RedirectStandardError (Join-Path $logDir "frontend.err.log") | Out-Null
}

$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if ((Test-LocalHttp "http://127.0.0.1:8000/health") -and (Test-LocalHttp "http://127.0.0.1:5173/index.html")) { $ready = $true; break }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    Get-Content (Join-Path $logDir "api.err.log"), (Join-Path $logDir "frontend.err.log") -Tail 20 -ErrorAction SilentlyContinue
    throw "Ambiente não iniciou completamente. Consulte os logs em $logDir"
}
Write-Host "DOMUS disponível em http://127.0.0.1:5173/index.html"
Write-Host "API: http://127.0.0.1:8000/health — SQLite local"
Write-Host "Logs: $logDir"
