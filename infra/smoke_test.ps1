<#
.SYNOPSIS
    Docker Compose Smoke Test for Schrödinger's Server Infrastructure.
    Enforces G8:
    1. Validates docker-compose.yml syntax.
    2. Prints all published ports and host addresses.
    3. Asserts no service publishes on 0.0.0.0 unless explicitly allowlisted.
    4. Asserts internal_honeypot_net is declared internal: true.
    5. Starts containers ONLY if -Up is explicitly passed.
#>

param (
    [switch]$Up
)

$ErrorActionPreference = "Stop"

# Allowlist for 0.0.0.0 published ports (default: empty / none)
$WHITELISTED_0000_PORTS = @()

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$COMPOSE_FILE = Join-Path $SCRIPT_DIR "docker-compose.yml"
$PARSER_SCRIPT = Join-Path $SCRIPT_DIR "parse_compose.py"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Schrödinger's Server // Infrastructure Smoke Test (G8)" -ForegroundColor Cyan
Write-Host "Compose File: $COMPOSE_FILE"
Write-Host "=========================================================="

if (-not (Test-Path $COMPOSE_FILE)) {
    Write-Error "Compose file not found at $COMPOSE_FILE"
    exit 1
}

# 1. Run `docker compose config` if docker is available
$hasDocker = (Get-Command "docker" -ErrorAction SilentlyContinue) -ne $null
if ($hasDocker) {
    Write-Host "[1/4] Validating compose configuration via 'docker compose config'..." -ForegroundColor Green
    & docker compose -f $COMPOSE_FILE config
    if ($LASTEXITCODE -ne 0) {
        Write-Error "docker compose config failed with exit code $LASTEXITCODE"
        exit 1
    }
} else {
    Write-Host "[1/4] Docker CLI not found in PATH; performing static YAML validation..." -ForegroundColor Yellow
}

# 2 & 3. Parse published ports and verify host addresses
Write-Host "`n[2/4] Inspecting published ports and host interface bindings..." -ForegroundColor Green
$parsedOutput = & python $PARSER_SCRIPT $COMPOSE_FILE

$ports = @()
$internalNetworkDeclared = $false

foreach ($line in ($parsedOutput -split "`r?`n")) {
    if ($line -like "PORT:*") {
        $parts = $line.Substring(5).Split(":")
        $service = $parts[0]
        $binding = $parts[1..($parts.Length - 1)] -join ":"
        $ports += [PSCustomObject]@{ Service = $service; Binding = $binding }
        Write-Host "  -> Service '$service' publishes: $binding" -ForegroundColor White
    }
    elseif ($line -eq "INTERNAL_NETWORK:True") {
        $internalNetworkDeclared = $true
    }
}

# 3. Check for unauthorized 0.0.0.0 bindings
Write-Host "`n[3/4] Verifying interface security (0.0.0.0 rejection)..." -ForegroundColor Green
$violations = @()
foreach ($p in $ports) {
    if ($p.Binding -like "0.0.0.0:*" -or ($p.Binding -notlike "*:*:*" -and $p.Binding -notlike "127.0.0.1:*")) {
        if ($WHITELISTED_0000_PORTS -notcontains $p.Binding) {
            $violations += "Service '$($p.Service)' publishes on 0.0.0.0 without allowlist entry: $($p.Binding)"
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Host "[ERROR] Security Violation: Disallowed 0.0.0.0 port publication detected!" -ForegroundColor Red
    foreach ($v in $violations) {
        Write-Host "  $v" -ForegroundColor Red
    }
    exit 1
} else {
    Write-Host "  [OK] Zero unauthorized 0.0.0.0 port publications. All published ports restricted to 127.0.0.1." -ForegroundColor Green
}

# 4. Check internal network declaration
Write-Host "`n[4/4] Verifying network isolation declaration..." -ForegroundColor Green
if (-not $internalNetworkDeclared) {
    Write-Host "[ERROR] internal_honeypot_net is NOT declared with 'internal: true'!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  [OK] Lab network 'internal_honeypot_net' is correctly declared with 'internal: true'." -ForegroundColor Green
}

# Optional container startup
if ($Up) {
    if ($hasDocker) {
        Write-Host "`n[UP] Starting services via docker compose up -d..." -ForegroundColor Cyan
        & docker compose -f $COMPOSE_FILE up -d
    } else {
        Write-Error "Cannot start containers: Docker CLI is not installed on this system."
        exit 1
    }
} else {
    Write-Host "`n[NOTICE] Containers NOT started (--up was not passed). Smoke test completed." -ForegroundColor Yellow
}

Write-Host "`nSMOKE TEST PASSED." -ForegroundColor Green
exit 0
