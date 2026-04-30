# --- BADWORDS WINDOWS INSTALLER v1.0 (PowerShell, Non-Interactive) ---
# Usage: irm https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install-windows.ps1 | iex
# Or local: powershell -ExecutionPolicy Bypass -File install-windows.ps1

$ErrorActionPreference = 'Continue'
$APP_NAME   = 'BadWords'
$APP_FOLDER = 'BadWords'

function Write-Log  { param($m) Write-Host "[UPDATE] $m" -ForegroundColor Green }
function Write-Info { param($m) Write-Host "[INFO]   $m" -ForegroundColor Cyan }
function Write-Warn { param($m) Write-Host "[WARN]   $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "[ERROR]  $m" -ForegroundColor Red }

Write-Host "================================================================================" -ForegroundColor Blue
Write-Host "                   BadWords - PORTABLE INSTALLER (Windows)                     " -ForegroundColor Blue
Write-Host "================================================================================" -ForegroundColor Blue

# ── Paths ───────────────────────────────────────────────────────────────────
$DefaultInstallDir  = "$env:LOCALAPPDATA\$APP_FOLDER"
$ResolveScriptDir   = "$env:APPDATA\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
$WrapperFile        = "$ResolveScriptDir\BadWords.py"

# Check Microsoft Store edition of Resolve
Get-ChildItem "$env:LOCALAPPDATA\Packages\BlackmagicDesign.DaVinciResolve_*" -ErrorAction SilentlyContinue | ForEach-Object {
    $storePath = "$($_.FullName)\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
    if (Test-Path $storePath) {
        $ResolveScriptDir = $storePath
        $WrapperFile      = "$storePath\BadWords.py"
    }
}

# ── Smart path detection from existing wrapper ───────────────────────────────
$InstallDir = $DefaultInstallDir
$DetectionMsg = ""
if (Test-Path $WrapperFile) {
    $line = Get-Content $WrapperFile -ErrorAction SilentlyContinue | Where-Object { $_ -match 'INSTALL_DIR' } | Select-Object -First 1
    # Handle both: INSTALL_DIR = r"""C:\path"""  and  INSTALL_DIR = r"C:\path"
    if ($line -match 'INSTALL_DIR\s*=\s*r?"{1,3}([^"]+)"{1,3}') {
        $detected = $matches[1].Trim()
        if ($detected -and (Test-Path $detected) -and (Test-Path "$detected\main.py")) {
            $InstallDir   = $detected
            $DetectionMsg = "Valid installation detected at: $InstallDir"
        }
    }
}
if ($DetectionMsg) { Write-Info $DetectionMsg }

$OldInstallDir = $InstallDir
$VenvDir  = "$InstallDir\venv"
$LibsDir  = "$InstallDir\libs"
$ModelsDir= "$InstallDir\models"
$BinDir   = "$InstallDir\bin"

# ── Menu ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "What would you like to do?" -ForegroundColor Yellow
Write-Host "  1) Standard Install/Update  — Install or update. Keeps settings & models." -ForegroundColor Green
Write-Host "  2) Repair Installation      — Replace core files. Keeps settings & models." -ForegroundColor Cyan
Write-Host "  3) Move Installation        — Move BadWords to a different folder." -ForegroundColor Blue
Write-Host "  4) Complete Reset           — Delete EVERYTHING and install from scratch."  -ForegroundColor Red
Write-Host "  5) Uninstall                — Remove BadWords completely." -ForegroundColor DarkRed
Write-Host ""
$choice = Read-Host "Select [1-5]"
if ([string]::IsNullOrWhiteSpace($choice)) { $choice = '1' }

switch ($choice) {
    '1' { $Mode = 'Update' }
    '2' { $Mode = 'Repair' }
    '3' { $Mode = 'Move'   }
    '4' { $Mode = 'FullWipe' }
    '5' { $Mode = 'Uninstall' }
    default { Write-Err "Invalid choice. Exiting."; exit 1 }
}
Write-Info "Selected: $Mode"

# ── Uninstall ─────────────────────────────────────────────────────────────────
if ($Mode -eq 'Uninstall') {
    Write-Host "WARNING: This will completely remove BadWords." -ForegroundColor DarkRed
    $confirm = Read-Host "Type 'yes' to confirm"
    if ($confirm -ne 'yes') { Write-Info "Cancelled."; exit 0 }
    if (Test-Path $InstallDir) { Remove-Item $InstallDir -Recurse -Force; Write-Info "Removed: $InstallDir" }
    if (Test-Path $WrapperFile) { Remove-Item $WrapperFile -Force; Write-Info "Removed wrapper from DaVinci Resolve." }
    Write-Log "Uninstall complete."
    exit 0
}

# ── Move: ask for new path ────────────────────────────────────────────────────
if ($Mode -eq 'Move') {
    Write-Host "Current path: $OldInstallDir" -ForegroundColor Green
    $newPath = Read-Host "Enter new absolute path (e.g. D:\BadWords)"
    if ([string]::IsNullOrWhiteSpace($newPath)) { Write-Err "Path cannot be empty."; exit 1 }
    if (-not [System.IO.Path]::IsPathRooted($newPath)) { Write-Err "Path must be absolute (e.g. D:\BadWords)."; exit 1 }
    # Ensure path ends with \BadWords
    if (-not $newPath.TrimEnd('\').EndsWith("\$APP_FOLDER") -and -not $newPath.TrimEnd('\').EndsWith("/$APP_FOLDER")) {
        $newPath = "$($newPath.TrimEnd('\'))\$APP_FOLDER"
    }
    if ($newPath -eq $OldInstallDir) { Write-Err "New path is identical to current path."; exit 1 }

    Write-Info "Moving files from $OldInstallDir to $newPath ..."
    New-Item -ItemType Directory -Path $newPath -Force | Out-Null
    # Move heavy dirs (venv, models, bin, saves) with robocopy /MOVE
    foreach ($d in @('venv','models','bin','saves')) {
        $src = "$OldInstallDir\$d"
        $dst = "$newPath\$d"
        if (Test-Path $src) {
            robocopy $src $dst /E /MOVE /NP /NJH /NJS | Out-Null
            Write-Info "Moved: $d"
        }
    }
    # Move user data files
    foreach ($f in @('pref.json','user.json','settings.json','badwords_debug.log')) {
        $src = "$OldInstallDir\$f"
        if (Test-Path $src) { Move-Item $src "$newPath\$f" -Force }
    }
    # Remove old dir
    if (Test-Path $OldInstallDir) { Remove-Item $OldInstallDir -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Log "Files moved to $newPath"

    $InstallDir = $newPath
    $VenvDir    = "$InstallDir\venv"
    $LibsDir    = "$InstallDir\libs"
    $BinDir     = "$InstallDir\bin"
    $ModelsDir  = "$InstallDir\models"
    # After move, treat as Repair (re-link venv, recreate wrapper)
    $Mode = 'Repair'
}

# ── Full Wipe: backup user data ───────────────────────────────────────────────
$BackupDir = $null
if ($Mode -eq 'FullWipe' -and (Test-Path $InstallDir)) {
    $BackupDir = [System.IO.Path]::GetTempPath() + "bw_backup_$([System.IO.Path]::GetRandomFileName())"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    foreach ($f in @('pref.json','user.json','settings.json')) {
        if (Test-Path "$InstallDir\$f") { Copy-Item "$InstallDir\$f" "$BackupDir\$f" }
    }
    Remove-Item $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Info "Full wipe complete. User data backed up."
}

# ── Fetch latest tag (GitHub → GitLab) ───────────────────────────────────────
Write-Info "Checking latest release..."
$LatestTag   = $null
$RepoZipUrl  = $null
$SourceRepo  = $null

try {
    $rel = Invoke-RestMethod "https://api.github.com/repos/veritus-git/BadWords/releases/latest" -TimeoutSec 15 -ErrorAction Stop
    $LatestTag  = $rel.tag_name
    $RepoZipUrl = "https://github.com/veritus-git/BadWords/archive/refs/tags/$LatestTag.zip"
    $SourceRepo = "GitHub"
} catch {
    Write-Warn "GitHub unavailable, trying GitLab..."
    try {
        $rels = Invoke-RestMethod "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases" -TimeoutSec 15 -ErrorAction Stop
        if ($rels.Count -gt 0) {
            $LatestTag  = $rels[0].tag_name
            $RepoZipUrl = "https://gitlab.com/badwords/BadWords/-/archive/$LatestTag/BadWords-$LatestTag.zip"
            $SourceRepo = "GitLab"
        }
    } catch {}
}

if (-not $LatestTag) { Write-Err "Could not determine latest version."; exit 1 }
Write-Log "Latest release: $LatestTag  (source: $SourceRepo)"

# ── Download & extract ────────────────────────────────────────────────────────
$TmpDir  = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "bw_install_$([System.IO.Path]::GetRandomFileName())")
New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
$ZipPath = "$TmpDir\repo.zip"

Write-Info "Downloading from $SourceRepo..."
Invoke-WebRequest -Uri $RepoZipUrl -OutFile $ZipPath -UseBasicParsing
Write-Info "Extracting..."
Expand-Archive -Path $ZipPath -DestinationPath "$TmpDir\extracted" -Force

$ExtractedDir = Get-ChildItem "$TmpDir\extracted" -Directory | Select-Object -First 1 -ExpandProperty FullName
$SourcePath   = "$ExtractedDir\src"
$AssetsPath   = "$ExtractedDir\assets"

if (-not (Test-Path "$SourcePath\main.py")) {
    Write-Err "Extraction failed — src\main.py not found."; Remove-Item $TmpDir -Recurse -Force; exit 1
}

# ── Prepare install dir ───────────────────────────────────────────────────────
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $ModelsDir  -Force | Out-Null
New-Item -ItemType Directory -Path $BinDir     -Force | Out-Null

# ── Sync files (Update) or full copy (Repair/FullWipe) ───────────────────────
Write-Info "Syncing application files..."
$isUpdate = ($Mode -eq 'Update')

$protected = @('pref.json','user.json','settings.json','badwords_debug.log','models','saves','venv','bin','libs')

if ($isUpdate) {
    # Write sync script to a temp file to avoid PowerShell f-string / brace conflicts
    $syncScript = @"
import os, shutil, hashlib

def get_hash(p):
    try:
        with open(p,'rb') as f: return hashlib.md5(f.read()).hexdigest()
    except: return None

for src in [r'$SourcePath', r'$AssetsPath']:
    if not os.path.isdir(src): continue
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        dst_dir = r'$InstallDir' if rel=='.' else os.path.join(r'$InstallDir', rel)
        os.makedirs(dst_dir, exist_ok=True)
        for f in files:
            s = os.path.join(root, f)
            d = os.path.join(dst_dir, f)
            if get_hash(s) != get_hash(d):
                shutil.copy2(s, d)
                name = os.path.join(rel, f) if rel != '.' else f
                print('  Updated: ' + name)
"@
    $syncPy = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "bw_sync_$([System.IO.Path]::GetRandomFileName()).py")
    [System.IO.File]::WriteAllText($syncPy, $syncScript, [System.Text.Encoding]::UTF8)

    # Find Python early (before main detection block below) — py launcher first (Windows standard)
    $earlyPy = $null
    foreach ($c in @('py', 'python', 'python3')) {
        try { $null = & $c --version 2>&1; $earlyPy = $c; break } catch {}
    }
    if (-not $earlyPy) {
        foreach ($p in @(
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
        )) { if (Test-Path $p) { $earlyPy = $p; break } }
    }
    if ($earlyPy) {
        & $earlyPy $syncPy 2>&1
    } else {
        Write-Warn "Python not found for sync - falling back to full copy for changed files."
        Copy-Item "$SourcePath\*"  $InstallDir -Recurse -Force
        if (Test-Path $AssetsPath) { Copy-Item "$AssetsPath\*" $InstallDir -Recurse -Force }
    }
    Remove-Item $syncPy -ErrorAction SilentlyContinue

    # Remove obsolete top-level files and dirs (mirrors update-linux.sh cleanup logic)
    $protectedItems = @('pref.json','user.json','settings.json','badwords_debug.log',
                        'BadWords.py','unins000.dat','unins000.exe',
                        'models','saves','venv','bin','libs','icons','layout',
                        '.git','.github','__pycache__')
    $srcTopNames = @()
    foreach ($sp in @($SourcePath, $AssetsPath)) {
        if (Test-Path $sp) { $srcTopNames += (Get-ChildItem $sp).Name }
    }
    foreach ($item in (Get-ChildItem $InstallDir -ErrorAction SilentlyContinue)) {
        if ($item.Name -in $protectedItems) { continue }
        if ($item.Name -notin $srcTopNames) {
            Remove-Item $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Info "Removed obsolete: $($item.Name)"
        }
    }
    # Remove obsolete files inside subdirectories
    foreach ($sp in @($SourcePath, $AssetsPath)) {
        if (-not (Test-Path $sp)) { continue }
        foreach ($srcSub in (Get-ChildItem $sp -Directory -Recurse -ErrorAction SilentlyContinue)) {
            $rel = $srcSub.FullName.Substring($sp.Length).TrimStart('\')
            $dstSub = Join-Path $InstallDir $rel
            if (-not (Test-Path $dstSub)) { continue }
            $srcFileNames = (Get-ChildItem $srcSub.FullName -File -ErrorAction SilentlyContinue).Name
            foreach ($dstFile in (Get-ChildItem $dstSub -File -ErrorAction SilentlyContinue)) {
                if ($dstFile.Name -notin $srcFileNames) {
                    Remove-Item $dstFile.FullName -Force -ErrorAction SilentlyContinue
                    Write-Info "Removed obsolete: $rel\$($dstFile.Name)"
                }
            }
        }
    }


} else {
    # Full copy
    Copy-Item "$SourcePath\*"  $InstallDir -Recurse -Force
    if (Test-Path $AssetsPath) { Copy-Item "$AssetsPath\*" $InstallDir -Recurse -Force }
    Write-Info "All files copied."
}

# ── Restore user data after Full Wipe ────────────────────────────────────────
if ($BackupDir -and (Test-Path $BackupDir)) {
    foreach ($f in @('pref.json','user.json','settings.json')) {
        if (Test-Path "$BackupDir\$f") { Copy-Item "$BackupDir\$f" "$InstallDir\$f" -Force }
    }
    Remove-Item $BackupDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Info "User data restored."
}

# ── Clean whisper cache ───────────────────────────────────────────────────────
$whisperCache = "$env:USERPROFILE\.cache\whisper"
if (Test-Path $whisperCache) { Remove-Item $whisperCache -Recurse -Force -ErrorAction SilentlyContinue }

# ── Find / install Python ─────────────────────────────────────────────────────
Write-Info "Locating Python interpreter..."
$PythonCmd = $null
$candidates = @('python','python3','py')
foreach ($c in $candidates) {
    try {
        $v = & $c --version 2>&1
        if ("$v" -match '3\.(10|11|12)\.') { $PythonCmd = $c; break }
    } catch {}
}
if (-not $PythonCmd) {
    foreach ($p in @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )) { if (Test-Path $p) { $PythonCmd = $p; break } }
}
if (-not $PythonCmd) {
    Write-Warn "Python 3.10-3.12 not found. Installing via winget..."
    winget install --id Python.Python.3.11 -e --silent --accept-source-agreements --accept-package-agreements 2>&1
    $PythonCmd = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    if (-not (Test-Path $PythonCmd)) { Write-Err "Python installation failed."; exit 1 }
}
Write-Info "Using Python: $PythonCmd"

# ── NVIDIA detection ──────────────────────────────────────────────────────────
$HasNvidia = $false
try {
    $gpu = (Get-WmiObject Win32_VideoController -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'NVIDIA' })
    if ($gpu) { $HasNvidia = $true }
} catch {}
if ($HasNvidia) { Write-Info "NVIDIA GPU detected — will install CUDA support." }
else            { Write-Info "No NVIDIA GPU detected — CPU mode." }

# ── Create/reuse venv ─────────────────────────────────────────────────────────
if (-not (Test-Path "$VenvDir\Scripts\python.exe")) {
    Write-Info "Creating virtual environment..."
    & $PythonCmd -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Err "venv creation failed."; exit 1 }
} else {
    Write-Info "Virtual environment already exists. Skipping creation."
}

$VenvPip    = "$VenvDir\Scripts\pip.exe"
$VenvPython = "$VenvDir\Scripts\python.exe"

Write-Info "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip 2>&1 | Out-Null

# ── Install AI libraries ──────────────────────────────────────────────────────
$torchInstalled = (& $VenvPip show torch 2>&1) -match 'Name: torch'
if ($isUpdate -and $torchInstalled) {
    Write-Info "AI libraries present. Running quick upgrade..."
    & $VenvPip install --upgrade faster-whisper stable-ts pypdf 2>&1 | Where-Object { $_ -notmatch 'already satisfied' }
} elseif ($HasNvidia) {
    Write-Info "Installing PyTorch (CUDA 12) + AI libraries..."
    & $VenvPip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
    & $VenvPip install faster-whisper stable-ts pypdf --extra-index-url https://download.pytorch.org/whl/cu121
} else {
    Write-Info "Installing PyTorch (CPU) + AI libraries..."
    & $VenvPip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    & $VenvPip install faster-whisper stable-ts pypdf
}

# ── PySide6 ───────────────────────────────────────────────────────────────────
$ps6 = (& $VenvPython -c "import PySide6" 2>&1) -as [string]
if ($LASTEXITCODE -ne 0) {
    Write-Warn "PySide6 not found. Installing..."
    & $VenvPip install PySide6
    if ($LASTEXITCODE -ne 0) { Write-Err "PySide6 installation failed."; exit 1 }
} else { Write-Info "PySide6 already installed." }

# ── FFmpeg (download only if missing) ─────────────────────────────────────────
if (-not (Test-Path "$BinDir\ffmpeg.exe")) {
    Write-Info "Downloading FFmpeg..."
    $ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    $ffmpegZip = "$TmpDir\ffmpeg.zip"
    Invoke-WebRequest -Uri $ffmpegUrl -OutFile $ffmpegZip -UseBasicParsing
    Expand-Archive -Path $ffmpegZip -DestinationPath "$TmpDir\ffmpeg_tmp" -Force
    Get-ChildItem "$TmpDir\ffmpeg_tmp" -Recurse -Filter "ffmpeg.exe"  | Select-Object -First 1 | Copy-Item -Destination "$BinDir\ffmpeg.exe"  -Force
    Get-ChildItem "$TmpDir\ffmpeg_tmp" -Recurse -Filter "ffprobe.exe" | Select-Object -First 1 | Copy-Item -Destination "$BinDir\ffprobe.exe" -Force
    if (Test-Path "$BinDir\ffmpeg.exe") { Write-Log "FFmpeg installed." }
    else { Write-Warn "FFmpeg extraction failed. Install manually if needed." }
}

# ── libs junction ─────────────────────────────────────────────────────────────
$sitePackages = "$VenvDir\Lib\site-packages"
if (Test-Path $LibsDir) { Remove-Item $LibsDir -Force -ErrorAction SilentlyContinue }
if (Test-Path $sitePackages) {
    cmd /c "mklink /J `"$LibsDir`" `"$sitePackages`"" | Out-Null
    Write-Info "libs junction created."
}

# ── DaVinci Resolve wrapper ───────────────────────────────────────────────────
Write-Info "Creating DaVinci Resolve wrapper..."
New-Item -ItemType Directory -Path $ResolveScriptDir -Force -ErrorAction SilentlyContinue | Out-Null

$wrapperContent = @"
import sys
import os
import traceback

INSTALL_DIR = r"""$InstallDir"""
LIBS_DIR    = os.path.join(INSTALL_DIR, 'libs')
VENV_LIBS   = os.path.join(INSTALL_DIR, 'venv', 'Lib', 'site-packages')
MAIN_SCRIPT = os.path.join(INSTALL_DIR, 'main.py')

if os.path.exists(VENV_LIBS) and VENV_LIBS not in sys.path:
    sys.path.insert(0, VENV_LIBS)
if os.path.exists(LIBS_DIR) and LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)
if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, 'r', encoding='utf-8') as f:
            code = f.read()
        g = globals().copy()
        g['__file__'] = MAIN_SCRIPT
        exec(code, g)
    except Exception as e:
        print(f'Error executing BadWords: {e}')
        traceback.print_exc()
else:
    print(f'CRITICAL: Script not found at {MAIN_SCRIPT}')
"@

$wrapperContent | Out-File -FilePath $WrapperFile -Encoding utf8 -Force
Write-Log "Wrapper created: $WrapperFile"

# ── Cleanup ───────────────────────────────────────────────────────────────────
Remove-Item $TmpDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "                         INSTALLATION SUCCESSFUL!" -ForegroundColor Green
Write-Host "                  Find the script in Workspace -> Scripts" -ForegroundColor Green
Write-Host "   MODE : $Mode" -ForegroundColor Green
Write-Host "   PATH : $InstallDir" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
