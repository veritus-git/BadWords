# ============================================================
#  BadWords Windows Bootstrapper v2.0
#  Run with: irm https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install-windows.ps1 | iex
#
#  Sole purpose: prepare Python environment and launch install.py
#  Supports boot-time caching — subsequent runs within the same
#  Windows session launch instantly from the persistent cache.
# ============================================================

$ErrorActionPreference = "Continue"

$INSTALLER_URL    = "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install.py"
$INSTALLER_URL_FB = "https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/install.py"

# ── Persistent cache directory ────────────────────────────────
# Everything here survives between bootstrapper runs but is
# invalidated automatically when Windows reboots (boot-time marker).
$CacheDir     = Join-Path $env:LOCALAPPDATA "BadWords-bootstrap"
$CacheVenvPy  = Join-Path $CacheDir "venv\Scripts\python.exe"
$CacheInstall = Join-Path $CacheDir "install.py"
$CacheMarker  = Join-Path $CacheDir "boot_marker.txt"
$EmbedPyDir   = Join-Path $CacheDir "python"   # embedded Python fallback
$EmbedPyExe   = Join-Path $EmbedPyDir "python.exe"

$EMBED_URL  = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"
$GETPIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# ── Colors ────────────────────────────────────────────────────
function step($m) { Write-Host "[>] $m" -ForegroundColor Cyan }
function ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }
function warn($m) { Write-Host "[!]  $m" -ForegroundColor Yellow }
function die($m)  { Write-Host "[X]  $m" -ForegroundColor Red; Read-Host "Press Enter to close"; exit 1 }

# ── Helper: launch CMD and exit PS1 immediately ───────────────
function Launch-Installer($PyExe, $InstallPy, $ExtraPythonPath) {
    $PyArg = "`"$InstallPy`" --platform windows --bootstrap-python `"$PyExe`""
    $EnvBlock = ""
    if ($ExtraPythonPath) {
        $EnvBlock = "set PYTHONPATH=$ExtraPythonPath && "
    }
    $CmdLine = "$($EnvBlock)`"$PyExe`" $PyArg"
    Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c title BadWords Setup && $CmdLine" `
        -WindowStyle Normal
    # PS1 is no longer needed — close immediately
    exit 0
}

# ── Session marker: file in $env:TEMP (cleared on reboot) ───
# Much more reliable than Get-CimInstance which needs admin/WMI.
$SessionFile = Join-Path $env:TEMP "bw_bootstrap_session.txt"
$BootTime = "unknown"
try {
    $BootTime = (Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).LastBootUpTime.ToString("yyyyMMddHHmmss")
} catch {
    # Use a hash of $env:TEMP path + machine name as stable per-session key
    $BootTime = "$($env:COMPUTERNAME)_$($env:USERNAME)"
}

# ── FAST PATH: Check boot-time cache ─────────────────────────
# We use TWO checks: (1) the session temp-file AND (2) the boot-time marker.
# This handles both normal and fallback boot-time detection.
$TempFileOk    = Test-Path $SessionFile
$CacheFilesOk  = (Test-Path $CacheMarker) -and (Test-Path $CacheVenvPy) -and (Test-Path $CacheInstall)

if ($TempFileOk -and $CacheFilesOk) {
    # Double-check boot time if we have it (skip if "unknown" since temp file is sufficient)
    $stored = (Get-Content $CacheMarker -Raw -ErrorAction SilentlyContinue).Trim()
    $bootOk = ($BootTime -eq "unknown") -or ($stored -eq $BootTime)

    if ($bootOk) {
        Write-Host ""
        Write-Host "  BadWords Setup" -ForegroundColor White
        Write-Host "  Cached environment found — refreshing installer script..." -ForegroundColor DarkGray

        # Venv is cached (saves ~30s) but install.py is always refreshed
        # so the user always runs the latest version of the installer.
        $refreshOk = $false
        try {
            Invoke-WebRequest -Uri $INSTALLER_URL -OutFile $CacheInstall -UseBasicParsing -ErrorAction Stop
            $refreshOk = $true
        } catch { warn "GitHub unreachable, trying GitLab..." }
        if (-not $refreshOk) {
            try {
                Invoke-WebRequest -Uri $INSTALLER_URL_FB -OutFile $CacheInstall -UseBasicParsing -ErrorAction Stop
                $refreshOk = $true
            } catch {}
        }
        if (-not $refreshOk) {
            warn "Could not refresh install.py — launching from cached copy."
        }

        Write-Host "  Launching instantly (cached environment)..." -ForegroundColor DarkGray
        Write-Host ""
        Launch-Installer $CacheVenvPy $CacheInstall $null
    }
}

# ── SLOW PATH: Full setup ─────────────────────────────────────
Write-Host ""
Write-Host "  BadWords Windows Bootstrapper" -ForegroundColor White
Write-Host "  Preparing environment..." -ForegroundColor DarkGray
Write-Host ""

# Ensure cache dir exists
New-Item -ItemType Directory -Path $CacheDir -Force | Out-Null

# Temp dir for one-off files (test venv, zip downloads etc.)
$BW_TMP = Join-Path ([System.IO.Path]::GetTempPath()) ("bw_bs_" + [System.Guid]::NewGuid().ToString("N").Substring(0,8))
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

# ── 2. Test venv support ──────────────────────────────────────
if ($PythonExe) {
    $testVenv = Join-Path $BW_TMP "test_venv"
    try {
        & $PythonExe -m venv $testVenv 2>$null | Out-Null
        if (Test-Path (Join-Path $testVenv "Scripts\python.exe")) {
            $VenvOk = $true
            ok "venv works."
        } else { warn "venv test produced no python.exe." }
    } catch { warn "venv test failed." }
}

# ── 3. Embedded Python fallback ───────────────────────────────
if (-not $PythonExe -or -not $VenvOk) {
    if (Test-Path $EmbedPyExe) {
        try {
            & $EmbedPyExe -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                ok "Reusing cached embedded Python: $EmbedPyExe"
                $PythonExe = $EmbedPyExe
                $VenvOk = $true
            }
        } catch {}
    }

    if (-not $VenvOk) {
        warn "No compatible Python found. Downloading embedded Python 3.12..."
        New-Item -ItemType Directory -Path $EmbedPyDir -Force | Out-Null

        $EmbedZip = Join-Path $BW_TMP "python-embed.zip"
        step "Downloading Python 3.12 embedded package..."
        try { Invoke-WebRequest -Uri $EMBED_URL -OutFile $EmbedZip -UseBasicParsing }
        catch { die "Failed to download embedded Python. Check your internet connection." }

        step "Extracting..."
        Expand-Archive -Path $EmbedZip -DestinationPath $EmbedPyDir -Force

        $pthFile = Get-ChildItem $EmbedPyDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($pthFile) {
            $c = Get-Content $pthFile.FullName -Raw
            $c = $c -replace "#import site", "import site"
            Set-Content -Path $pthFile.FullName -Value $c -Encoding ASCII
            ok "_pth patched for pip support."
        }

        step "Bootstrapping pip..."
        $GetPipScript = Join-Path $BW_TMP "get-pip.py"
        try { Invoke-WebRequest -Uri $GETPIP_URL -OutFile $GetPipScript -UseBasicParsing }
        catch { die "Failed to download get-pip.py." }
        & $EmbedPyExe $GetPipScript --quiet 2>$null
        if ($LASTEXITCODE -ne 0) { warn "pip bootstrap returned non-zero. Continuing..." }

        $PythonExe = $EmbedPyExe
        $VenvOk    = $true
        ok "Embedded Python ready."
    }
}

if (-not $PythonExe) { die "No suitable Python found. Install Python 3.10+ from https://python.org" }

# ── 4. Create bootstrap venv in cache (permanent) ─────────────
# Venv lives in $CacheDir\venv — persists for the session
step "Creating bootstrap environment..."
$BootstrapVenv = Join-Path $CacheDir "venv"
$BootstrapPy   = $null
$UseTargetFallback = $false

# Wipe stale venv if it exists (cache miss means boot changed, rebuild)
if (Test-Path $BootstrapVenv) {
    Remove-Item $BootstrapVenv -Recurse -Force -ErrorAction SilentlyContinue
}

try {
    & $PythonExe -m venv $BootstrapVenv 2>$null | Out-Null
    $BootstrapPy = $CacheVenvPy
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

# ── 5. Install rich into venv ─────────────────────────────────
step "Installing dependencies (rich)..."
$ExtraPythonPath = $null

if (-not $UseTargetFallback -and (Test-Path $BootstrapPy)) {
    & $BootstrapPy -m pip install --upgrade pip --quiet 2>$null | Out-Null
    & $BootstrapPy -m pip install rich --quiet 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        warn "venv pip failed. Falling back to --target."
        $UseTargetFallback = $true
    }
}

if ($UseTargetFallback) {
    $PkgDir = Join-Path $CacheDir "packages"
    New-Item -ItemType Directory -Path $PkgDir -Force | Out-Null
    & $PythonExe -m pip install rich --target $PkgDir --quiet 2>$null | Out-Null
    $ExtraPythonPath = $PkgDir
    $BootstrapPy = $PythonExe
}

ok "Dependencies ready."

# ── 6. Download install.py into cache ────────────────────────
step "Downloading BadWords installer..."
$downloaded = $false

try {
    Invoke-WebRequest -Uri $INSTALLER_URL -OutFile $CacheInstall -UseBasicParsing
    if (Test-Path $CacheInstall) { $downloaded = $true }
} catch { warn "GitHub unavailable. Trying GitLab fallback..." }

if (-not $downloaded) {
    try {
        Invoke-WebRequest -Uri $INSTALLER_URL_FB -OutFile $CacheInstall -UseBasicParsing
        if (Test-Path $CacheInstall) { $downloaded = $true }
    } catch {}
}

if (-not $downloaded) { die "Failed to download install.py from both GitHub and GitLab." }
ok "Installer ready."

# ── 7. Write cache markers ────────────────────────────────────
$BootTime | Set-Content -Path $CacheMarker -Encoding UTF8
# Session temp-file: presence = same boot session
"1" | Set-Content -Path $SessionFile -Encoding UTF8
ok "Cache ready."

# ── 8. Launch installer in CMD and exit PS1 immediately ───────
Write-Host ""
Write-Host "  Launching BadWords Installer..." -ForegroundColor Cyan
Write-Host ""

Launch-Installer $BootstrapPy $CacheInstall $ExtraPythonPath

} finally {
    # BW_TMP only holds throw-away files — safe to delete immediately
    if (Test-Path $BW_TMP) {
        Remove-Item -Path $BW_TMP -Recurse -Force -ErrorAction SilentlyContinue
    }
}
