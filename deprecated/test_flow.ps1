Write-Output "=== 1. Register ==="
$regBody = '{"username":"flowtest1","password":"TestPass123!"}'
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/auth/register" -Method POST -Body $regBody -ContentType "application/json" -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $regData = $r.Content | ConvertFrom-Json
    Write-Output "Player: $($regData.data.player.username)"
    Write-Output "Has auth: $($regData.data.auth.access_token -ne $null)"
} catch {
    Write-Output "Register failed: $($_.Exception.Message)"
    exit
}

Write-Output ""
Write-Output "=== 2. Login ==="
$loginBody = '{"username":"flowtest1","password":"TestPass123!"}'
try {
    $r2 = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -UseBasicParsing
    Write-Output "Status: $($r2.StatusCode)"
    $loginData = $r2.Content | ConvertFrom-Json
    $token = $loginData.data.access_token
    Write-Output "Token prefix: $($token.Substring(0, 20))..."
} catch {
    Write-Output "Login failed: $($_.Exception.Message)"
    exit
}

Write-Output ""
Write-Output "=== 3. Join matchmaking queue ==="
$headers = @{
    "Authorization" = "Bearer $token"
    "Accept" = "application/json"
    "Content-Type" = "application/json"
}
try {
    $r3 = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/matchmaking/queue" -Method POST -Body '{}' -Headers $headers -UseBasicParsing
    Write-Output "Status: $($r3.StatusCode)"
    Write-Output $r3.Content
} catch {
    $code = $_.Exception.Response.StatusCode.Value__
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $body = $reader.ReadToEnd()
    $reader.Close()
    Write-Output "Status: $code"
    Write-Output $body
}
