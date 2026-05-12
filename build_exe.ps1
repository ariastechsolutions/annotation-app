$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m PyInstaller --noconfirm --clean SAR_Annotation.spec

Write-Host "Build complete. The executable is in .\dist\SAR_Annotation.exe"
