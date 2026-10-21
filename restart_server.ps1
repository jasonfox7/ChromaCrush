# restart_server.ps1 — Kill anything on port 8000 and restart the backend.

Write-Host "=== Killing processes on port 8000 ===" -ForegroundColor Yellow
$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conns) {
    $procIds = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $procIds) {
        $proc = Get-Process -Id $p -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  Killing PID $p ($($proc.ProcessName))"
            Stop-Process -Id $p -Force
        }
    }
    Start-Sleep -Seconds 1
}
else {
    Write-Host "  Port 8000 is free"
}

Write-Host "`n=== Starting server ===" -ForegroundColor Green
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn src.modules.api.factory:create_app --factory --host 0.0.0.0 --port 8000
