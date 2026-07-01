<#
    Installs "brother_ql_web" as an always-on Windows service (via NSSM).

    Run this ONCE, elevated:
        Right-click > Run with PowerShell (as Administrator), or from an admin
        PowerShell:  powershell -ExecutionPolicy Bypass -File .\install-windows-service.ps1

    Idempotent: safe to re-run (it removes any existing service of the same name
    first). Serves the web UI on http://<this-machine>/ (port 80).
#>
$ErrorActionPreference = 'Stop'

# --- must be elevated ---
$me = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $me.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator."
    exit 1
}

$Root = 'C:\Services\brother_ql_web'
$Nssm = Join-Path $Root 'bin\nssm.exe'
$Py   = Join-Path $Root '.venv\Scripts\python.exe'
$Svc  = 'BrotherQLWeb'
$Log  = Join-Path $Root 'logs'

New-Item -ItemType Directory -Force -Path $Log | Out-Null

# --- remove any existing service with this name (old Codex pywin32 service, or a prior run) ---
if (Get-Service $Svc -ErrorAction SilentlyContinue) {
    Write-Host "Removing existing '$Svc' service..."
    Stop-Service $Svc -Force -ErrorAction SilentlyContinue
    & $Nssm remove $Svc confirm 2>$null
    cmd.exe /c "sc delete $Svc" 2>$null | Out-Null
    Start-Sleep -Seconds 2
}

# --- install the new service: python serve.py (waitress on port 80) ---
Write-Host "Installing '$Svc' service..."
& $Nssm install $Svc $Py (Join-Path $Root 'serve.py')
& $Nssm set $Svc AppDirectory $Root
& $Nssm set $Svc DisplayName 'Brother QL Web (label printer)'
& $Nssm set $Svc Description 'Web UI for printing labels on the Brother QL-570.'
& $Nssm set $Svc Start SERVICE_AUTO_START
& $Nssm set $Svc AppStdout (Join-Path $Log 'service.log')
& $Nssm set $Svc AppStderr (Join-Path $Log 'service.log')
& $Nssm set $Svc AppRotateFiles 1
& $Nssm set $Svc AppRotateBytes 1048576
& $Nssm set $Svc AppExit Default Restart
& $Nssm set $Svc AppRestartDelay 3000

# --- firewall: allow inbound TCP 80 on all profiles so phones/other devices can reach it ---
if (-not (Get-NetFirewallRule -DisplayName 'Brother QL Web (HTTP 80)' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'Brother QL Web (HTTP 80)' -Direction Inbound `
        -Protocol TCP -LocalPort 80 -Action Allow -Profile Any | Out-Null
    Write-Host "Firewall rule for TCP 80 added."
}

# --- start + health check ---
Start-Service $Svc
Start-Sleep -Seconds 5
try {
    $r = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1/labeldesigner/' -TimeoutSec 8
    Write-Host ""
    Write-Host ("SUCCESS: service running (HTTP {0})." -f $r.StatusCode) -ForegroundColor Green
    Write-Host ("Open it at:  http://{0}/   or   http://localhost/" -f $env:COMPUTERNAME.ToLower() + '.local')
} catch {
    Write-Warning ("Service installed but the local web check failed: " + $_.Exception.Message)
    Write-Warning ("Check the log: " + (Join-Path $Log 'service.log'))
}
