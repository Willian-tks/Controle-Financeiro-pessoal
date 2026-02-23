$ErrorActionPreference = "Stop"

$repoRoot = $PSScriptRoot
$apiDir = $repoRoot
$frontendDir = Join-Path $repoRoot "frontend"

if (-not (Test-Path (Join-Path $frontendDir "package.json"))) {
  throw "Pasta frontend não encontrada em: $frontendDir"
}

$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
  $pythonExe = "python"
}

$apiCommand = @(
  "Set-Location -Path '$apiDir'",
  "$env:CORS_ORIGINS='http://127.0.0.1:5173,http://localhost:5173'",
  "$env:JWT_SECRET='dev-local-secret-change-me'",
  "& '$pythonExe' -m uvicorn api.main:app --reload --port 8000"
) -join "; "

$frontendCommand = @(
  "Set-Location -Path '$frontendDir'",
  "$env:VITE_API_BASE_URL='http://127.0.0.1:8000'",
  "npm run dev"
) -join "; "

Start-Process powershell -ArgumentList @("-NoExit", "-Command", $apiCommand) | Out-Null
Start-Sleep -Milliseconds 600
Start-Process powershell -ArgumentList @("-NoExit", "-Command", $frontendCommand) | Out-Null

Write-Host "Ambiente local iniciado."
Write-Host "API: http://127.0.0.1:8000/health"
Write-Host "Frontend: http://127.0.0.1:5173"
