# Post-Install Path Setup
# Run this in your current terminal to use 'local-ai' without restarting

$venvScripts = "$env:USERPROFILE\bin\local-ai-venv\Scripts"

# Add to current session PATH
$env:Path = "$env:Path;$venvScripts"

# For PowerShell, also import the module
$binDir = "$env:USERPROFILE\bin"
if (Test-Path "$binDir\local-ai.psm1") {
    Import-Module "$binDir\local-ai.psm1" -Force
}

Write-Host "PATH updated for current session!" -ForegroundColor Green
Write-Host "You can now use 'local-ai --help' in this terminal" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or use the .bat wrappers (work immediately):" -ForegroundColor Yellow
Write-Host "  local-ai-start" -ForegroundColor White
Write-Host "  local-ai-stop" -ForegroundColor White
