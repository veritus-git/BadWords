# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# ============================================================
#  BadWords Windows Bootstrapper v4.0 (Native)
#  Run with: irm "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/windows-setup.ps1" | iex
#
#  Downloads and launches the native BadWords Setup GUI without terminal.
# ============================================================

$ErrorActionPreference = "Stop"

$RepoOwner = "veritus-git"
$RepoName  = "BadWords"
$Tag       = if ($env:BADWORDS_TAG) { $env:BADWORDS_TAG } else { "latest" }
$BinName   = "badwords-setup-windows.exe"

# 1. Local file detection (if executed inside repo)
$ScriptDir = ""
if ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$LocalBin = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\release\badwords-installer.exe" } else { "" }
$LocalDebug = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\debug\badwords-installer.exe" } else { "" }

function Start-Executable($exePath, $arguments) {
    Unblock-File -Path $exePath -ErrorAction SilentlyContinue
    if ($arguments -and $arguments.Count -gt 0) {
        Start-Process -FilePath $exePath -ArgumentList $arguments
    } else {
        Start-Process -FilePath $exePath
    }
}

if ($LocalBin -and (Test-Path $LocalBin)) {
    Start-Executable $LocalBin $args
    exit 0
}
if ($LocalDebug -and (Test-Path $LocalDebug)) {
    Start-Executable $LocalDebug $args
    exit 0
}
$CargoToml = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\Cargo.toml" } else { "" }
if ($CargoToml -and (Test-Path $CargoToml) -and (Get-Command "cargo" -ErrorAction SilentlyContinue)) {
    Write-Host "Compiling and launching BadWords Setup via cargo..." -ForegroundColor Cyan
    if ($args -and $args.Count -gt 0) {
        cargo run --release --manifest-path "$CargoToml" -- $args
    } else {
        cargo run --release --manifest-path "$CargoToml"
    }
    exit 0
}

# 2. Remote download
$CacheDir = Join-Path $env:LOCALAPPDATA "BadWords-bootstrap"
New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
$TargetExe = Join-Path $CacheDir "BadWords-Setup.exe"

Write-Host "Downloading BadWords Setup..." -ForegroundColor Cyan

$DownloadUrl = if ($Tag -eq "latest") {
    "https://github.com/$RepoOwner/$RepoName/releases/latest/download/$BinName"
} else {
    "https://github.com/$RepoOwner/$RepoName/releases/download/$Tag/$BinName"
}

$Downloaded = $false
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $TargetExe -UseBasicParsing
    $Downloaded = $true
} catch {
    # Fallback to checking GitHub API for release assets
    try {
        $ApiUrl = "https://api.github.com/repos/$RepoOwner/$RepoName/releases"
        $Releases = Invoke-RestMethod -Uri $ApiUrl -UseBasicParsing -Headers @{"User-Agent"="BadWords-Bootstrapper"}
        $Asset = $Releases | ForEach-Object { $_.assets } | Where-Object { $_.name -like "*windows*.exe" -or $_.name -eq $BinName } | Select-Object -First 1
        if ($Asset) {
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TargetExe -UseBasicParsing
            $Downloaded = $true
        }
    } catch {}
}

if (-not $Downloaded -or -not (Test-Path $TargetExe)) {
    Write-Host "Error: Failed to download BadWords installer." -ForegroundColor Red
    Write-Host "Please download the installer directly from:" -ForegroundColor Yellow
    Write-Host "https://github.com/$RepoOwner/$RepoName/releases"
    exit 1
}

# 3. Launch native GUI without terminal
Start-Executable $TargetExe $args
exit 0
