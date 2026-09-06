# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# ============================================================
#  BadWords Windows Bootstrapper v4.0
#  Run with: irm "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/windows-setup.ps1" | iex
# ============================================================

$ErrorActionPreference = "Continue"

$RepoOwner        = "veritus-git"
$RepoName         = "BadWords"
$Tag              = if ($env:BADWORDS_TAG) { $env:BADWORDS_TAG } else { "latest" }
$BinName          = "badwords-setup-windows.exe"
$INSTALLER_URL    = "https://raw.githubusercontent.com/$RepoOwner/$RepoName/main/setupfiles/setup.py"
$INSTALLER_URL_FB = "https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/setup.py"
$EMBED_URL        = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
$GETPIP_URL       = "https://bootstrap.pypa.io/get-pip.py"

# -- Local File Detection --------------------------------------
$ScriptDir = ""
if ($MyInvocation.MyCommand.Path) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$LocalBin     = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\release\badwords-installer.exe" } else { "" }
$LocalDebug   = if ($ScriptDir) { Join-Path $ScriptDir "..\installer\target\debug\badwords-installer.exe" } else { "" }
$LocalSetup   = if ($ScriptDir) { Join-Path $ScriptDir "setup.py" } else { "" }
$LocalRepo    = if ($ScriptDir) { Split-Path -Parent $ScriptDir } else { "" }

# -- Directories -----------------------------------------------
$CacheDir   = Join-Path $env:LOCALAPPDATA "BadWords-bootstrap"
$EmbedPyDir = Join-Path $CacheDir "python"
$EmbedPyExe = Join-Path $EmbedPyDir "python.exe"
$TargetExe  = Join-Path $CacheDir "BadWords-Setup.exe"
$BW_TMP     = Join-Path ([System.IO.Path]::GetTempPath()) ("bw_bs_" + [System.Guid]::NewGuid().ToString("N").Substring(0,8))

New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null
New-Item -ItemType Directory -Path $BW_TMP -Force | Out-Null

# -- Helper: Run Rich Terminal Python Fallback -----------------
function Invoke-PythonFallback() {
    Clear-Host
    Write-Host "PS C:\Users\User> irm `"https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/windows-setup.ps1`" | iex" -ForegroundColor White
    Write-Host "Downloading BadWords Setup..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host " [!] Windows Security Notice:" -ForegroundColor Yellow
    Write-Host "     The graphical installer binary was blocked by Windows Smart App" -ForegroundColor White
    Write-Host "     Control (SAC) or SmartScreen because it lacks an EV certificate." -ForegroundColor White
    Write-Host "========================================================================" -ForegroundColor Cyan
    Write-Host " How would you like to proceed?" -ForegroundColor White
    Write-Host "  [1] Run Terminal Installer via Python (Recommended)" -ForegroundColor Green
    Write-Host "  [2] Exit (I want to change Windows Security settings and try again)" -ForegroundColor DarkGray
    Write-Host "========================================================================" -ForegroundColor Cyan
    
    $choice = Read-Host "Select an option [1 or 2]"
    if ($choice -ne "1") {
        Write-Host "Setup cancelled by user." -ForegroundColor Yellow
        exit 0
    }

    Write-Host ""
    Write-Host "Preparing portable Python environment..." -ForegroundColor Cyan

    try {
        # 1. Ensure portable Python exists (cached)
        $NeedDownload = $true
        if (Test-Path $EmbedPyExe) {
            try {
                & $EmbedPyExe -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    & $EmbedPyExe -m pip --version 2>$null | Out-Null
                    if ($LASTEXITCODE -eq 0) {
                        $NeedDownload = $false
                    }
                }
            } catch {}
        }

        if ($NeedDownload) {
            Write-Host "Downloading portable Python 3.12..." -ForegroundColor Cyan
            if (Test-Path $EmbedPyDir) {
                Remove-Item $EmbedPyDir -Recurse -Force -ErrorAction SilentlyContinue
            }
            New-Item -ItemType Directory -Path $EmbedPyDir -Force | Out-Null

            $EmbedZip = Join-Path $BW_TMP "python-embed.zip"
            try { Invoke-WebRequest -Uri $EMBED_URL -OutFile $EmbedZip -UseBasicParsing }
            catch { Write-Host "Failed to download embedded Python. Check your connection." -ForegroundColor Red; exit 1 }

            Expand-Archive -Path $EmbedZip -DestinationPath $EmbedPyDir -Force

            # Patch ._pth to enable pip/site-packages
            $pthFile = Get-ChildItem $EmbedPyDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($pthFile) {
                $c = Get-Content $pthFile.FullName -Raw
                $c = $c -replace "#import site", "import site"
                Set-Content -Path $pthFile.FullName -Value $c -Encoding ASCII
            }

            $GetPipScript = Join-Path $BW_TMP "get-pip.py"
            try { Invoke-WebRequest -Uri $GETPIP_URL -OutFile $GetPipScript -UseBasicParsing }
            catch { Write-Host "Failed to download get-pip.py." -ForegroundColor Red; exit 1 }
            & $EmbedPyExe $GetPipScript --quiet 2>$null
        }

        # 2. Install rich to temp
        Write-Host "Installing dependencies (rich UI)..." -ForegroundColor Cyan
        $PkgDir = Join-Path $BW_TMP "packages"
        New-Item -ItemType Directory -Path $PkgDir -Force | Out-Null
        & $EmbedPyExe -m pip install rich --target $PkgDir --quiet 2>$null | Out-Null

        # 3. Download setup.py to temp
        $SetupPy = Join-Path $BW_TMP "setup.py"
        $downloaded = $false

        if ($LocalSetup -and (Test-Path $LocalSetup)) {
            Copy-Item -Path $LocalSetup -Destination $SetupPy -Force
            $downloaded = $true
        }

        if (-not $downloaded) {
            try {
                Invoke-WebRequest -Uri $INSTALLER_URL -OutFile $SetupPy -UseBasicParsing -ErrorAction Stop
                if (Test-Path $SetupPy) { $downloaded = $true }
            } catch {}
        }
        if (-not $downloaded) {
            try {
                Invoke-WebRequest -Uri $INSTALLER_URL_FB -OutFile $SetupPy -UseBasicParsing -ErrorAction Stop
                if (Test-Path $SetupPy) { $downloaded = $true }
            } catch {}
        }

        if (-not $downloaded) {
            Write-Host "Failed to download setup.py." -ForegroundColor Red
            exit 1
        }

        # 4. Launch setup.py in CMD / Windows Terminal
        Write-Host "Launching BadWords Rich Setup..." -ForegroundColor Green
        $PyArg = "`"$SetupPy`" --platform windows --bootstrap-python `"$EmbedPyExe`""
        if ($LocalRepo -and (Test-Path $LocalSetup)) {
            $PyArg += " --local-repo `"$LocalRepo`""
        }
        $CmdLine = "set PYTHONPATH=$PkgDir&& `"$EmbedPyExe`" $PyArg"
        $CmdArgs = "/c title BadWords Setup && mode con cols=88 lines=30 && $CmdLine"

        $wt = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\wt.exe"
        if (Test-Path $wt) {
            Start-Process -FilePath $wt -ArgumentList "--size", "88,30", "cmd.exe", $CmdArgs -WindowStyle Normal
        } else {
            Start-Process -FilePath "cmd.exe" -ArgumentList $CmdArgs -WindowStyle Normal
        }
        exit 0

    } catch {
        Write-Host "Error in fallback: $_" -ForegroundColor Red
        exit 1
    }
}

# ── Helper: Start Native Executable Safely ─────────────────────
function Clear-FileZoneIdentifier($path) {
    if (-not $path -or -not (Test-Path $path)) { return }
    try { Unblock-File -LiteralPath $path -ErrorAction SilentlyContinue } catch {}
    try { Unblock-File -Path $path -ErrorAction SilentlyContinue } catch {}
    try { Remove-Item -LiteralPath "$path:Zone.Identifier" -Force -ErrorAction SilentlyContinue } catch {}
}

function Start-NativeExecutable($exePath, $arguments) {
    Clear-FileZoneIdentifier $exePath
    $parent = Split-Path -Parent $exePath
    if ($parent) {
        Clear-FileZoneIdentifier (Join-Path $parent "BadWords.exe")
    }
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
        Invoke-PythonFallback
    }
}

# 0. Force fallback check (for testing or explicitly requested CLI mode)
if ($env:BADWORDS_FORCE_FALLBACK -or ($args -and ($args -contains "--fallback" -or $args -contains "--cli"))) {
    Invoke-PythonFallback
}

# 1. Try local compiled or placed binary first (if inside repo clone)
$LocalRootBin = if ($ScriptDir) { Join-Path $ScriptDir "..\badwords-setup-windows.exe" } else { "" }
if ($LocalRootBin -and (Test-Path $LocalRootBin)) {
    Start-NativeExecutable $LocalRootBin $args
}
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
    try {
        $ApiUrl = "https://api.github.com/repos/$RepoOwner/$RepoName/releases"
        $Releases = Invoke-RestMethod -Uri $ApiUrl -UseBasicParsing -Headers @{"User-Agent"="BadWords-Bootstrapper"}
        $Asset = $Releases | ForEach-Object { $_.assets } | Where-Object { $_.name -like "*windows*.exe" -or $_.name -eq $BinName } | Select-Object -First 1
        if ($Asset) {
            Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $TargetExe -UseBasicParsing
            $Downloaded = $true
        }
        $LauncherAsset = $Releases | ForEach-Object { $_.assets } | Where-Object { $_.name -eq "BadWords.exe" } | Select-Object -First 1
        if ($LauncherAsset) {
            $TargetLauncher = Join-Path $CacheDir "BadWords.exe"
            Invoke-WebRequest -Uri $LauncherAsset.browser_download_url -OutFile $TargetLauncher -UseBasicParsing -ErrorAction SilentlyContinue
        }
    } catch {}
}

# Download BadWords.exe native launcher directly if available
$LauncherUrl = if ($Tag -eq "latest") {
    "https://github.com/$RepoOwner/$RepoName/releases/latest/download/BadWords.exe"
} else {
    "https://github.com/$RepoOwner/$RepoName/releases/download/$Tag/BadWords.exe"
}
$TargetLauncher = Join-Path $CacheDir "BadWords.exe"
try {
    Invoke-WebRequest -Uri $LauncherUrl -OutFile $TargetLauncher -UseBasicParsing -ErrorAction SilentlyContinue
} catch {}
Clear-FileZoneIdentifier $TargetExe
Clear-FileZoneIdentifier $TargetLauncher

if ($Downloaded -and (Test-Path $TargetExe)) {
    Start-NativeExecutable $TargetExe $args
} else {
    Invoke-PythonFallback
}
