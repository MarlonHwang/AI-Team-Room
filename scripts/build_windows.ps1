param(
    [string]$Python = "python",
    [string]$Version = "0.1.1"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildVenv = Join-Path $RepoRoot ".venv-build-windows"
$BuildPython = Join-Path $BuildVenv "Scripts\python.exe"
$WorkRoot = Join-Path $RepoRoot "build\windows"
$DistRoot = Join-Path $RepoRoot "dist\windows"
$PackageRoot = Join-Path $DistRoot "AI-Team-Room-Windows-x64"
$ZipPath = Join-Path $DistRoot "AI-Team-Room-$Version-Windows-x64.zip"

if (-not (Test-Path -LiteralPath $BuildPython)) {
    & $Python -m venv $BuildVenv
}

& $BuildPython -m pip install --disable-pip-version-check -r (Join-Path $RepoRoot "requirements-build.txt")
& $BuildPython -m pip install --disable-pip-version-check --no-deps $RepoRoot

if (Test-Path -LiteralPath $WorkRoot) {
    Remove-Item -LiteralPath $WorkRoot -Recurse -Force
}
if (Test-Path -LiteralPath $PackageRoot) {
    Remove-Item -LiteralPath $PackageRoot -Recurse -Force
}
if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

New-Item -ItemType Directory -Path $WorkRoot -Force | Out-Null
New-Item -ItemType Directory -Path $PackageRoot -Force | Out-Null

$Common = @(
    "--noconfirm",
    "--clean",
    "--onefile",
    "--paths", (Join-Path $RepoRoot "src"),
    "--collect-data", "ai_team_room",
    "--workpath", (Join-Path $WorkRoot "work"),
    "--specpath", (Join-Path $WorkRoot "spec"),
    "--distpath", $PackageRoot
)

& $BuildPython -m PyInstaller @Common --name "AI-Team-Room" (Join-Path $RepoRoot "scripts\windows_server_entry.py")
& $BuildPython -m PyInstaller @Common --name "aitr" (Join-Path $RepoRoot "scripts\windows_client_entry.py")

Copy-Item -LiteralPath (Join-Path $RepoRoot "LICENSE") -Destination $PackageRoot
Copy-Item -LiteralPath (Join-Path $RepoRoot "NOTICE") -Destination $PackageRoot
Set-Content -LiteralPath (Join-Path $PackageRoot "README-WINDOWS.txt") -Encoding UTF8 -Value @"
AI Team Room for Windows
========================

1. Double-click AI-Team-Room.exe.
2. Your browser opens the local meeting room automatically.
3. Create a meeting and paste each generated invitation into that AI session.

Keep AI-Team-Room.exe and aitr.exe in the same folder. Windows may display an
Unknown Publisher warning because this early release is not code-signed yet.
The room listens only on this computer (127.0.0.1) unless explicitly configured
otherwise.
"@

Compress-Archive -LiteralPath $PackageRoot -DestinationPath $ZipPath -CompressionLevel Optimal
Write-Output $ZipPath
