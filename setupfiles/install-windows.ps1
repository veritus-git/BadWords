# ============================================================
#  BadWords Windows Bootstrapper v1.0
#  Run with: irm https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install-windows.ps1 | iex
#
#  Sole purpose: prepare Python environment and launch install.py
# ============================================================

$ErrorActionPreference = "Continue"

$INSTALLER_URL    = "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install.py"
$INSTALLER_URL_FB = "https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/install.py"
$PBS_PERMANENT    = Join-Path $env:LOCALAPPDATA "BadWords-bootstrap"
$EMBED_URL        = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
$GETPIP_URL       = "https://bootstrap.pypa.io/get-pip.py"

# ── Colors ────────────────────────────────────────────────────
function step($m) { Write-Host "[>] $m" -ForegroundColor Cyan }
function ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function warn($m) { Write-Host "[!]  $m" -ForegroundColor Yellow }
function die($m)  { Write-Host "[X]  $m" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "  BadWords Windows Bootstrapper" -ForegroundColor White
Write-Host "  Preparing environment..." -ForegroundColor DarkGray
Write-Host ""

# ── Temp dir (cleaned on exit) ────────────────────────────────
$BW_TMP = Join-Path ([System.IO.Path]::GetTempPath()) ("bw_bootstrap_" + [System.Guid]::NewGuid().ToString("N").Substring(0,8))
New-Item -ItemType Directory -Path $BW_TMP -Force | Out-Null

try {

# ── 1. Find system Python 3.10+ ───────────────────────────────
step "Looking for compatible Python (3.10+)..."
$PythonExe = $null
$VenvOk    = $false

foreach ($cmd in @("py", "python", "python3")) {
    try {
        $verStr = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $verStr -match "^3\.(1[0-9]|[2-9]\d)") {
            $found = (Get-Command $cmd -ErrorAction SilentlyContinue)
            $PythonExe = if ($found) { $found.Source } else { $cmd }
            ok "Found Python $verStr : $PythonExe"
            break
        }
    } catch {}
}

# ── 2. Test venv ──────────────────────────────────────────────
if ($PythonExe) {
    step "Testing virtual environment support..."
    $testVenv = Join-Path $BW_TMP "test_venv"
    try {
        & $PythonExe -m venv $testVenv 2>$null | Out-Null
        if (Test-Path (Join-Path $testVenv "Scripts\python.exe")) {
            $VenvOk = $true
            ok "venv works."
            Remove-Item $testVenv -Recurse -Force -ErrorAction SilentlyContinue
        } else {
            warn "venv creation produced no python.exe."
        }
    } catch {
        warn "venv test failed."
    }
}

# ── 3. Download embedded Python if needed ─────────────────────
if (-not $PythonExe -or -not $VenvOk) {
    $PbsDir = Join-Path $PBS_PERMANENT "python"
    $PbsExe = Join-Path $PbsDir "python.exe"

    # Reuse existing cached embedded Python
    if (Test-Path $PbsExe) {
        try {
            & $PbsExe -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                ok "Reusing cached embedded Python: $PbsExe"
                $PythonExe = $PbsExe
                $VenvOk = $true
            }
        } catch {}
    }

    if (-not $VenvOk) {
        warn "No compatible Python found. Downloading embedded Python 3.12..."
        New-Item -ItemType Directory -Path $PbsDir -Force | Out-Null

        $EmbedZip = Join-Path $BW_TMP "python-embed.zip"
        step "Downloading Python 3.12 embedded package..."
        try {
            Invoke-WebRequest -Uri $EMBED_URL -OutFile $EmbedZip -UseBasicParsing
        } catch {
            die "Failed to download embedded Python. Check your internet connection."
        }

        step "Extracting..."
        Expand-Archive -Path $EmbedZip -DestinationPath $PbsDir -Force

        # Enable pip support: uncomment 'import site' in _pth file
        $pthFile = Get-ChildItem $PbsDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pthFile) {
            $pthContent = Get-Content $pthFile.FullName -Raw
            $pthContent  = $pthContent -replace "#import site", "import site"
            Set-Content -Path $pthFile.FullName -Value $pthContent -Encoding ASCII
            ok "_pth file patched for pip support."
        }

        # Bootstrap pip
        step "Bootstrapping pip..."
        $GetPipScript = Join-Path $BW_TMP "get-pip.py"
        try {
            Invoke-WebRequest -Uri $GETPIP_URL -OutFile $GetPipScript -UseBasicParsing
        } catch {
            die "Failed to download get-pip.py."
        }
        & $PbsExe $GetPipScript --quiet 2>$null
        if ($LASTEXITCODE -ne 0) { warn "pip bootstrap returned non-zero. Continuing..." }

        $PythonExe = $PbsExe
        $VenvOk    = $true
        ok "Embedded Python ready: $PythonExe"
    }
}

if (-not $PythonExe) { die "No suitable Python found. Install Python 3.10+ from https://python.org" }

# ── 4. Create bootstrap venv ──────────────────────────────────
step "Creating bootstrap environment..."
$BootstrapVenv  = Join-Path $BW_TMP "venv"
$BootstrapPy    = $null
$BootstrapPip   = $null
$UseTargetFallback = $false

try {
    & $PythonExe -m venv $BootstrapVenv 2>$null | Out-Null
    $BootstrapPy  = Join-Path $BootstrapVenv "Scripts\python.exe"
    $BootstrapPip = Join-Path $BootstrapVenv "Scripts\pip.exe"
    if (Test-Path $BootstrapPy) {
        ok "Bootstrap venv created."
    } else {
        throw "venv python.exe missing"
    }
} catch {
    warn "venv creation failed. Using --target fallback for packages."
    $UseTargetFallback = $true
    $BootstrapPy = $PythonExe
}

# ── 5. Install rich ───────────────────────────────────────────
step "Installing dependencies (rich)..."
if (-not $UseTargetFallback -and (Test-Path $BootstrapPy)) {
    & $BootstrapPy -m pip install --upgrade pip --quiet 2>$null | Out-Null
    & $BootstrapPy -m pip install rich --quiet 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        warn "venv pip failed. Falling back to --target."
        $UseTargetFallback = $true
    }
}

if ($UseTargetFallback) {
    $PkgDir = Join-Path $BW_TMP "packages"
    New-Item -ItemType Directory -Path $PkgDir -Force | Out-Null
    & $PythonExe -m pip install rich --target $PkgDir --quiet 2>$null | Out-Null
    $env:PYTHONPATH = "$PkgDir;$env:PYTHONPATH"
    $BootstrapPy = $PythonExe
}

ok "Dependencies ready."

# ── 6. Download install.py ────────────────────────────────────
step "Downloading BadWords installer..."
$InstallPy = Join-Path $BW_TMP "install.py"
$downloaded = $false

try {
    Invoke-WebRequest -Uri $INSTALLER_URL -OutFile $InstallPy -UseBasicParsing
    if (Test-Path $InstallPy) { $downloaded = $true }
} catch {
    warn "GitHub unavailable. Trying GitLab fallback..."
}

if (-not $downloaded) {
    try {
        Invoke-WebRequest -Uri $INSTALLER_URL_FB -OutFile $InstallPy -UseBasicParsing
        if (Test-Path $InstallPy) { $downloaded = $true }
    } catch {}
}

if (-not $downloaded) { die "Failed to download install.py from both GitHub and GitLab." }
ok "Installer ready."

# ── 7. Launch installer in a new CMD window (black background) ───────────────
Write-Host ""
Write-Host "  Launching BadWords Installer..." -ForegroundColor Cyan
Write-Host ""

# Build the Python command line — use quoted paths to handle spaces
$PyArg  = "`"$InstallPy`" --platform windows --bootstrap-python `"$PythonExe`""

# Pass PYTHONPATH through environment if we used the --target fallback
$EnvBlock = ""
if ($env:PYTHONPATH) {
    $EnvBlock = "set PYTHONPATH=$($env:PYTHONPATH) && "
}

# /k keeps the window open after the installer exits (user sees the result)
# Title is set so the taskbar shows "BadWords Installer"
$CmdLine = "$($EnvBlock)`"$BootstrapPy`" $PyArg"
Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/k title BadWords Installer && $CmdLine" `
    -Wait `
    -WindowStyle Normal

} finally {
    if (Test-Path $BW_TMP) {
        Remove-Item -Path $BW_TMP -Recurse -Force -ErrorAction SilentlyContinue
    }
}
