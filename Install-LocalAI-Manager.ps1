#!/usr/bin/env pwsh
# Install-LocalAI-Manager.ps1
# Quick installer for Local AI Manager Python refactor

$ErrorActionPreference = 'Stop'

Write-Host "Local AI Manager Python Installer" -ForegroundColor Cyan
Write-Host "=" * 40 -ForegroundColor Cyan

# Check Python
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python not found! Please install Python 3.10 or later."
    exit 1
}

$version = & python --version 2>&1
Write-Host "Found: $version" -ForegroundColor Green

# Navigate to package directory
$pkgDir = "$env:USERPROFILE\bin\local-ai-manager"
if (-not (Test-Path $pkgDir)) {
    Write-Error "Package directory not found: $pkgDir"
    Write-Host "Please ensure the local-ai-manager folder is in ~/bin"
    exit 1
}

Set-Location $pkgDir

# Create virtual environment
$venvDir = "$env:USERPROFILE\bin\local-ai-venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
    & python -m venv "$venvDir"
}

# Install package
Write-Host "Installing package and dependencies..." -ForegroundColor Yellow
& "$venvDir\Scripts\pip.exe" install -e "$pkgDir" -q

if ($LASTEXITCODE -ne 0) {
    Write-Error "Installation failed!"
    exit 1
}

Write-Host "Package installed successfully!" -ForegroundColor Green

# Initialize configuration
Write-Host "`nInitializing configuration..." -ForegroundColor Yellow
& "$venvDir\Scripts\local-ai.exe" config-init

# Add venv Scripts to PATH if not already there
Write-Host "`nAdding to PATH..." -ForegroundColor Yellow
$venvScripts = "$venvDir\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -notlike "*$venvScripts*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$venvScripts", "User")
    Write-Host "  Added venv Scripts to PATH" -ForegroundColor Green
    Write-Host "  [NOTE] Restart your terminal for PATH changes to take effect" -ForegroundColor Yellow
} else {
    Write-Host "  PATH already contains venv Scripts" -ForegroundColor Green
}

# Create convenient aliases
Write-Host "`nCreating command shortcuts..." -ForegroundColor Yellow
$binDir = "$env:USERPROFILE\bin"

$shortcuts = @{
    "local-ai.bat" = '@"%~dp0local-ai-venv\Scripts\local-ai.exe" %*'
    "local-ai-start.bat" = '@"%~dp0local-ai-venv\Scripts\local-ai.exe" start %*'
    "local-ai-stop.bat" = '@"%~dp0local-ai-venv\Scripts\local-ai.exe" stop'
    "local-ai-status.bat" = '@"%~dp0local-ai-venv\Scripts\local-ai.exe" status'
    "steam-watcher.bat" = '@"%~dp0local-ai-venv\Scripts\local-ai.exe" steam start'
}

foreach ($name in $shortcuts.Keys) {
    $content = $shortcuts[$name]
    $path = Join-Path $binDir $name
    Set-Content -Path $path -Value $content
    Write-Host "  Created: $name" -ForegroundColor DarkGray
}

# Create shell script wrappers for Git Bash
Write-Host "`nCreating Git Bash wrappers..." -ForegroundColor Yellow

$shellWrappers = @{
    "local-ai" = @'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE="$HOME/bin/local-ai-venv/Scripts/python.exe"
if [ ! -f "$PYTHON_EXE" ]; then
    echo "Error: Python not found at $PYTHON_EXE"
    exit 1
fi
"$PYTHON_EXE" -m local_ai_manager "$@"
'@
    "local-ai-start" = @'
#!/bin/bash
"$HOME/bin/local-ai-venv/Scripts/python.exe" -m local_ai_manager start "$@"
'@
    "local-ai-stop" = @'
#!/bin/bash
"$HOME/bin/local-ai-venv/Scripts/python.exe" -m local_ai_manager stop "$@"
'@
    "local-ai-status" = @'
#!/bin/bash
"$HOME/bin/local-ai-venv/Scripts/python.exe" -m local_ai_manager status "$@"
'@
}

foreach ($name in $shellWrappers.Keys) {
    $content = $shellWrappers[$name]
    $path = Join-Path $binDir $name
    Set-Content -Path $path -Value $content -Encoding UTF8
    # Try to set executable bit (works in Git Bash)
    try {
        attrib +x $path | Out-Null
    } catch {}
    Write-Host "  Created: $name (shell)" -ForegroundColor DarkGray
}

# Create PowerShell function wrapper
$psWrapper = @"
# Local AI Manager PowerShell wrapper
function local-ai {
    & "$venvDir\Scripts\local-ai.exe" @args
}

# Export function
Export-ModuleMember -Function local-ai
"@

$psModulePath = "$binDir\local-ai.psm1"
Set-Content -Path $psModulePath -Value $psWrapper
Write-Host "  Created: local-ai.psm1" -ForegroundColor DarkGray

# Add to PowerShell profile for auto-loading (if $PROFILE is available)
if ($PROFILE) {
    $profileDir = Split-Path -Parent $PROFILE
    if ($profileDir -and -not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    
    if ($profileDir) {
        $importLine = "Import-Module '$binDir\local-ai.psm1' -ErrorAction SilentlyContinue"
        if (-not (Test-Path $PROFILE) -or (Get-Content $PROFILE -Raw) -notlike "*$importLine*") {
            Add-Content -Path $PROFILE -Value "`n# Local AI Manager`n$importLine" -Encoding UTF8
            Write-Host "  Added to PowerShell profile" -ForegroundColor DarkGray
        }
    }
} else {
    Write-Host "  Skipping PowerShell profile (not available in this environment)" -ForegroundColor DarkGray
}

Write-Host "`n" + "=" * 40 -ForegroundColor Cyan
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""

# Detect shell type
$shellType = if ($env:MSYSTEM) { "Git Bash" } elseif ($PSVersionTable.PSEdition) { "PowerShell" } else { "CMD" }
Write-Host "Detected shell: $shellType" -ForegroundColor Cyan
Write-Host ""

Write-Host "Available commands:" -ForegroundColor Yellow

if ($env:MSYSTEM -or $env:TERM -eq "xterm") {
    # Git Bash or similar
    Write-Host "  local-ai --help              Full CLI (use now)" -ForegroundColor White
    Write-Host "  local-ai-start [options]     Start server (use now)" -ForegroundColor White
    Write-Host "  local-ai-stop                Stop server (use now)" -ForegroundColor White
    Write-Host "  local-ai-status              Check status (use now)" -ForegroundColor White
    Write-Host ""
    Write-Host "NOTE: Shell scripts work immediately in Git Bash!" -ForegroundColor Green
} else {
    # Windows PowerShell/CMD
    Write-Host "  local-ai --help              Full CLI with all commands" -ForegroundColor White
    Write-Host "  local-ai-start [options]     Quick start alias" -ForegroundColor White
    Write-Host "  local-ai-stop                Quick stop alias" -ForegroundColor White
    Write-Host "  local-ai-status              Quick status alias" -ForegroundColor White
    Write-Host ""
    Write-Host "IMPORTANT:" -ForegroundColor Yellow
    Write-Host "  1. Use .bat commands now (local-ai-start, local-ai-stop)" -ForegroundColor White
    Write-Host "  2. Or restart your terminal for 'local-ai' to work" -ForegroundColor White
    Write-Host "  3. PowerShell users: run 'local-ai' after restarting PowerShell" -ForegroundColor White
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  ~/.config/local-ai/local-ai-config.json" -ForegroundColor White
