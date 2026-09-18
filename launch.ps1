Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Error "Environment not found. Run .\setup.ps1 first."
}
Push-Location $RepoRoot
try { & $VenvPython -m wpi_sensitivity @args }
finally { Pop-Location }
