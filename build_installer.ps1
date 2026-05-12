$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path .\dist\SAR_Annotation.exe)) {
    throw "Missing .\dist\SAR_Annotation.exe. Run build_exe.ps1 first."
}

$iscc = $null
foreach ($candidate in @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)) {
    if (Test-Path $candidate) {
        $iscc = $candidate
        break
    }
}

if (-not $iscc) {
    throw "Inno Setup compiler not found. Install Inno Setup 6, then rerun this script."
}

& $iscc .\installer.iss

Write-Host "Installer build complete. The setup exe is in .\installer_output"
