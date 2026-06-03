# Start previous ACKO blue website (frontend SPA) at http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:SERVE_REACT_UI = "True"

Write-Host "Starting ACKO website (previous UI) at http://127.0.0.1:8000/"
Write-Host "Pages: Home, Quote, Claim, Dashboard, Ask AI (hash links)"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
