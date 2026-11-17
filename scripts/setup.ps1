# One-command local setup for Food Truck Finder (Windows PowerShell 5.1 and PowerShell 7).
# Same steps as scripts/setup.sh, for teammates using PowerShell or VS Code's terminal on Windows.
#
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
# (-ExecutionPolicy Bypass applies to this one run only; it changes no system setting.)
#
# Safe to run again: it never overwrites an existing .env or your data.

$ErrorActionPreference = 'Stop'

# Always run from the repo root, even if called from elsewhere
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))

function Stop-WithMessage([string]$message) {
    Write-Host $message -ForegroundColor Red
    exit 1
}

# Native commands (docker) don't throw on failure; check their exit code instead
function Invoke-Checked([scriptblock]$command, [string]$failureMessage) {
    & $command
    if ($LASTEXITCODE -ne 0) { Stop-WithMessage $failureMessage }
}

Write-Host '==> Checking Docker'
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage "Docker isn't running. Start Docker Desktop, wait for it to finish starting, then run this again."
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-WithMessage "Docker Compose v2 is required ('docker compose', not 'docker-compose')."
}

Write-Host '==> Checking that ports 5433, 8000 and 5173 are free'
# 5433 = database (host side; a local Postgres on 5432 is fine), 8000 = Django, 5173 = Vite
# This project's own running containers are allowed to hold the ports (re-running setup)
$ownContainerPorts = (docker compose ps --status running 2>$null) -join "`n"
foreach ($requiredPort in 5433, 8000, 5173) {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        # If something accepts a connection, the port is taken
        $connectAttempt = $tcpClient.BeginConnect('127.0.0.1', $requiredPort, $null, $null)
        $portIsInUse = $connectAttempt.AsyncWaitHandle.WaitOne(300) -and $tcpClient.Connected
    } finally {
        $tcpClient.Close()
    }
    if ($portIsInUse -and ($ownContainerPorts -notmatch "$requiredPort->")) {
        Stop-WithMessage ("Port $requiredPort is already in use by another program or container.`n" +
            "Find a container using it:  docker ps --filter publish=$requiredPort`n" +
            "Find a program using it:    Get-NetTCPConnection -LocalPort $requiredPort | Select-Object OwningProcess")
    }
}

if (Test-Path '.env') {
    Write-Host '==> .env already exists, keeping it'
} else {
    Write-Host '==> Creating .env with a generated secret key and database password'
    # URL-safe random string (letters, digits, - and _), same character set as Python's token_urlsafe
    function New-UrlSafeSecret([int]$byteCount) {
        $randomBytes = New-Object byte[] $byteCount
        $randomGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $randomGenerator.GetBytes($randomBytes)
        $randomGenerator.Dispose()
        return [Convert]::ToBase64String($randomBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    }
    $djangoSecretKey = New-UrlSafeSecret 50
    $databasePassword = New-UrlSafeSecret 24

    $environmentLines = Get-Content '.env.example' | ForEach-Object {
        if ($_ -match '^DJANGO_SECRET_KEY=') { "DJANGO_SECRET_KEY=$djangoSecretKey" }
        elseif ($_ -match '^POSTGRES_PASSWORD=') { "POSTGRES_PASSWORD=$databasePassword" }
        elseif ($_ -match '^DJANGO_DEBUG=') { 'DJANGO_DEBUG=true' }
        else { $_ }
    }
    # Write UTF-8 WITHOUT a byte-order mark and with Unix line endings.
    # Windows PowerShell's Set-Content would add a BOM, which Docker Compose can misread.
    $environmentFilePath = Join-Path (Get-Location) '.env'
    $utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($environmentFilePath, (($environmentLines -join "`n") + "`n"), $utf8WithoutBom)
}

Write-Host '==> Building and starting containers (first run takes a few minutes)'
Invoke-Checked { docker compose up -d --build } 'docker compose up failed. See the output above.'

Write-Host '==> Waiting for the backend to be ready'
$backendIsReady = $false
for ($attemptNumber = 1; $attemptNumber -le 60; $attemptNumber++) {
    try {
        $healthResponse = Invoke-WebRequest -Uri 'http://localhost:8000/api/health/' -UseBasicParsing -TimeoutSec 5
        if ($healthResponse.StatusCode -eq 200) { $backendIsReady = $true; break }
    } catch {
        # Not up yet; try again
    }
    Start-Sleep -Seconds 2
}
if (-not $backendIsReady) {
    Stop-WithMessage "Backend didn't start within 2 minutes. Check:  docker compose logs backend"
}

# Migrations already ran when the backend started (entrypoint.sh); this is a no-op
# safety net in case the database container was slow on the first start.
Invoke-Checked { docker compose exec -T backend python manage.py migrate --noinput } 'Migrations failed. See the output above.'

Write-Host '==> Loading sample trucks'
Invoke-Checked { docker compose exec -T backend python manage.py seed_food_trucks } 'Loading sample trucks failed. See the output above.'

Write-Host ''
Write-Host 'Done. Everything is running in the background.' -ForegroundColor Green
Write-Host '  App:    http://localhost:5173'
Write-Host '  Admin:  http://localhost:8000/admin/'
Write-Host ''
Write-Host 'Create your own admin login (one time):'
Write-Host '  docker compose exec backend python manage.py createsuperuser'
Write-Host 'Watch logs:   docker compose logs -f'
Write-Host 'Stop:         docker compose down      (keeps your data)'
