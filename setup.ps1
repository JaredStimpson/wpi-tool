Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

try {
    if (-not (Test-Path $VenvPython)) {
        $Launcher = Get-Command py -ErrorAction SilentlyContinue
        if ($null -eq $Launcher) {
            throw "Python launcher not found. Install 64-bit Python 3.12 from python.org."
        }
        & py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)"
        & py -3.12 -m venv (Join-Path $RepoRoot ".venv")
    }
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install --requirement (Join-Path $RepoRoot "requirements.lock")
    & $VenvPython -m pip install --editable $RepoRoot
    & $VenvPython -m wpi_sensitivity --self-test
    & $VenvPython -c "import importlib.util; print('Excel automation: ' + ('available' if importlib.util.find_spec('xlwings') else 'unavailable'))"
    Write-Host "Setup complete. Launch with .\launch.ps1"
}
catch {
    Write-Error "Setup failed: $($_.Exception.Message)"
    exit 1
}
