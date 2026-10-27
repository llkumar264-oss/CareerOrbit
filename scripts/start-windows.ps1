$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

try {
    $health = Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -TimeoutSec 3
    $web = Invoke-WebRequest -Uri 'http://localhost:3000/' -UseBasicParsing -TimeoutSec 3
    if ($health.live_sending -and $web.Content.Contains('CareerOrbit')) {
        Write-Host 'CareerOrbit is already running on localhost:3000.'
        Start-Process 'http://localhost:3000'
        exit 0
    }
} catch { }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Install Docker Desktop, open it, and run START-WINDOWS.bat again.'
}
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'Start Docker Desktop and wait until its engine is ready, then run this file again.'
}

if (-not (Test-Path '.env')) {
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $keyBytes = New-Object byte[] 32
        $passwordBytes = New-Object byte[] 32
        $rng.GetBytes($keyBytes)
        $rng.GetBytes($passwordBytes)
        $key = [Convert]::ToBase64String($keyBytes).Replace('+', '-').Replace('/', '_')
        $password = [Convert]::ToBase64String($passwordBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        if (Test-Path 'storage/.encryption-key') {
            $key = [System.IO.File]::ReadAllText((Join-Path $projectRoot 'storage/.encryption-key')).Trim()
        }
        $template = [System.IO.File]::ReadAllText((Join-Path $projectRoot '.env.example'))
        $template = [regex]::Replace($template, '(?m)^ENCRYPTION_KEY=\r?$', 'ENCRYPTION_KEY=' + $key)
        $template = [regex]::Replace($template, '(?m)^POSTGRES_PASSWORD=\r?$', 'POSTGRES_PASSWORD=' + $password)
        [System.IO.File]::WriteAllText((Join-Path $projectRoot '.env'), $template, (New-Object System.Text.UTF8Encoding($false)))
    } finally { $rng.Dispose() }
    Write-Host 'Created local configuration. Existing provider credentials were not required.'
}

Write-Host 'Building and starting CareerOrbit. The first launch needs an internet connection and may take several minutes.'
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Run docker compose logs --tail=50 to inspect the cause.' }
$ready = $false
for ($attempt = 0; $attempt -lt 45; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -TimeoutSec 3
        $web = Invoke-WebRequest -Uri 'http://localhost:3000/' -UseBasicParsing -TimeoutSec 3
        if ($health.live_sending -and $web.Content.Contains('CareerOrbit')) { $ready = $true; break }
    } catch { }
    Start-Sleep -Seconds 2
}
if (-not $ready) { throw 'Services are still starting or failed. Run docker compose logs --tail=50.' }
Write-Host 'CareerOrbit is ready at localhost:3000. Stop it with: docker compose stop'
Start-Process 'http://localhost:3000'
