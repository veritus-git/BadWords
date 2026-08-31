# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# ============================================================
#  BadWords Windows Bootstrapper v4.0
#  Run with: irm "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/windows-setup.ps1" | iex
# ============================================================

$ErrorActionPreference = "Continue"

$RepoOwner = "veritus-git"
$RepoName  = "BadWords"
$Tag       = if ($env:BADWORDS_TAG) { $env:BADWORDS_TAG } else { "latest" }
$BinName   = "badwords-setup-windows.exe"
$SetupPyUrl = "https://raw.githubusercontent.com/$RepoOwner/$RepoName/main/setupfiles/setup.py"
$EmbedPyUrl = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"

$CacheDir   = Join-Path $env:LOCALAPPDATA "BadWords-bootstrap"
$EmbedPyDir = Join-Path $CacheDir "python"
$EmbedPyExe = Join-Path $EmbedPyDir "python.exe"
$TargetExe  = Join-Path $CacheDir "BadWords-Setup.exe"
$SetupPy    = Join-Path $CacheDir "setup.py"

New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null

# ── Local File Detection ──────────────────────────────────────
$ScriptDir = ""
if ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$LocalBin = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\release\badwords-installer.exe" } else { "" }
$LocalDebug = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\debug\badwords-installer.exe" } else { "" }
$LocalSetupPy = if ($ScriptDir) { Join-Path $ScriptDir "setup.py" } else { "" }

# ── Helper: Run Python CLI Fallback ───────────────────────────
function Invoke-PythonFallback() {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host " [!] Windows Security Notice:" -ForegroundColor Yellow
    Write-Host "     The graphical installer binary was blocked by Windows Smart App" -ForegroundColor White
    Write-Host "     Control (SAC) or SmartScreen because it lacks an EV certificate." -ForegroundColor White
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host " How would you like to proceed?" -ForegroundColor White
    Write-Host "  [1] Run CLI Installer via Python (Recommended - 100% bypasses security)" -ForegroundColor Green
    Write-Host "  [2] Exit (I want to change Windows Security settings and try again)" -ForegroundColor DarkGray
    Write-Host "========================================================================" -ForegroundColor Cyan
    
    $choice = Read-Host "Select an option [1 or 2]"
    if ($choice -ne "1") {
        Write-Host "Setup cancelled by user." -ForegroundColor Yellow
        exit 0
    }

    Write-Host ""
    Write-Host "Preparing Python environment for CLI installer..." -ForegroundColor Cyan

    # 1. Check for system python
    $PyRunner = ""
    try {
        $sysPy = Get-Command "python" -ErrorAction SilentlyContinue
        if ($sysPy) {
            $ver = & python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $PyRunner = "python"
            }
        }
    } catch {}

    # 2. If no system python, download portable embedded Python 3.12
    if (-not $PyRunner) {
        if (-not (Test-Path $EmbedPyExe)) {
            Write-Host "Downloading portable Python runtime..." -ForegroundColor Cyan
            $zipPath = Join-Path $CacheDir "python-embed.zip"
            Invoke-WebRequest -Uri $EmbedPyUrl -OutFile $zipPath -UseBasicParsing
            Expand-Archive -Path $zipPath -DestinationPath $EmbedPyDir -Force
            Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

            # Enable site-packages in ._pth
            $pth = Get-ChildItem $EmbedPyDir -Filter "python*._pth" | Select-Object -First 1
            if ($pth) {
                $c = (Get-Content $pth.FullName -Raw) -replace "#import site", "import site"
                Set-Content -Path $pth.FullName -Value $c -Encoding ASCII
            }
        }
        $PyRunner = $EmbedPyExe
    }

    # 3. Ensure setup.py is ready
    if ($LocalSetupPy -and (Test-Path $LocalSetupPy)) {
        Copy-Item -Path $LocalSetupPy -Destination $SetupPy -Force
    } elseif (-not (Test-Path $SetupPy)) {
        Write-Host "Fetching setup engine..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $SetupPyUrl -OutFile $SetupPy -UseBasicParsing
    }

    # 4. Launch setup.py
    Write-Host "Launching BadWords CLI Setup..." -ForegroundColor Green
    & $PyRunner $SetupPy
    exit 0
}

# ── Helper: Start Executable Safely ───────────────────────────
function Start-NativeExecutable($exePath, $arguments) {
    Unblock-File -Path $exePath -ErrorAction SilentlyContinue
    try {
        if ($arguments -and $arguments.Count -gt 0) {
            $p = Start-Process -FilePath $exePath -ArgumentList $arguments -PassThru -ErrorAction Stop
        } else {
            $p = Start-Process -FilePath $exePath -PassThru -ErrorAction Stop
        }
        if ($p -and $p.Id) {
            exit 0
        }
    } catch {
        # Process blocked by Smart App Control / security policy
        Invoke-PythonFallback
    }
}

# 1. Try local compiled binary first (if inside repo clone)
if ($LocalBin -and (Test-Path $LocalBin)) {
    Start-NativeExecutable $LocalBin $args
}
if ($LocalDebug -and (Test-Path $LocalDebug)) {
    Start-NativeExecutable $LocalDebug $args
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

# 2. Remote download binary
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

if ($Downloaded -and (Test-Path $TargetExe)) {
    Start-NativeExecutable $TargetExe $args
} else {
    # If binary download was not available (e.g. pre-release), fall back to Python CLI
    Invoke-PythonFallback
}
