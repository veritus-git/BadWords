@echo off
:: --- BADWORDS AUTO-UPDATE (Windows, non-interactive) ---
:: Called by the BadWords GUI when the user clicks "Update Now".
:: Self-contained: installs Python & curl if missing.
:: Exits 0 on success, 1 on failure. Output goes to stdout.
setlocal EnableDelayedExpansion

:: ── Silence env conflicts ───────────────────────────────────────────────────
set "PYTHONHOME="
set "PYTHONPATH="

echo [UPDATE] BadWords Windows Auto-Update starting...

:: ── 1. Locate installation via wrapper ──────────────────────────────────────
set "WRAPPER_FILE=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"

:: Also check Microsoft Store edition path
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "WRAPPER_FILE=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
    )
)

set "INSTALL_DIR="
if exist "!WRAPPER_FILE!" (
    for /f "tokens=*" %%L in ('findstr /r "^INSTALL_DIR" "!WRAPPER_FILE!" 2^>nul') do (
        set "LINE=%%L"
        :: Extract path from: INSTALL_DIR = r"""C:\..."""
        for /f "tokens=2 delims=""" %%P in ("!LINE!") do (
            if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%%P"
        )
    )
)

:: Validate detected path
if not defined INSTALL_DIR (
    set "INSTALL_DIR=%APPDATA%\BadWords"
    echo [WARN] Could not read wrapper, using default: !INSTALL_DIR!
)
if not exist "!INSTALL_DIR!\main.py" (
    echo [ERROR] No valid BadWords installation found at !INSTALL_DIR!
    exit /b 1
)

echo [INFO] Installation path: !INSTALL_DIR!
set "VENV_DIR=!INSTALL_DIR!\venv"
set "VENV_PYTHON=!VENV_DIR!\Scripts\python.exe"
set "VENV_PIP=!VENV_DIR!\Scripts\pip.exe"

:: ── 2. Ensure Python is available ───────────────────────────────────────────
set "PYTHON_CMD="
where python >nul 2>&1 && (
    for /f "tokens=*" %%P in ('where python') do (
        if "!PYTHON_CMD!"=="" (
            echo %%P | findstr /i "WindowsApps" >nul || set "PYTHON_CMD=%%P"
        )
    )
)
if not defined PYTHON_CMD (
    for %%V in (312 311 310) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            goto :FOUND_PY
        )
    )
    :: Last resort: winget install Python 3.11
    echo [WARN] Python not found. Attempting to install via winget...
    winget install --id Python.Python.3.11 -e --silent --accept-source-agreements --accept-package-agreements
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if not exist "!PYTHON_CMD!" (
        echo [ERROR] Python installation failed. Please install Python 3.10-3.12 manually.
        exit /b 1
    )
    echo [INFO] Python installed at !PYTHON_CMD!
)
:FOUND_PY
echo [INFO] Using Python: !PYTHON_CMD!

:: ── 3. Ensure curl is available (ships with Win10 1803+) ────────────────────
where curl >nul 2>&1 || (
    echo [WARN] curl not found in PATH. Trying PowerShell fallback for downloads.
    set "USE_PS_DL=1"
)

:: ── 4. Fetch latest tag — GitHub first, GitLab fallback ─────────────────────
echo [INFO] Checking latest release...
set "LATEST_TAG="
set "REPO_ZIP_URL="
set "SOURCE_REPO="

:: GitHub
if not defined USE_PS_DL (
    for /f "delims=" %%T in ('curl -fsSL --connect-timeout 10 "https://api.github.com/repos/veritus-git/BadWords/releases/latest" ^| "!PYTHON_CMD!" -c "import json,sys; d=json.load(sys.stdin); print(d.get(\"tag_name\",\"\"))" 2^>nul') do set "LATEST_TAG=%%T"
) else (
    for /f "delims=" %%T in ('powershell -NoProfile -Command "(Invoke-RestMethod https://api.github.com/repos/veritus-git/BadWords/releases/latest).tag_name" 2^>nul') do set "LATEST_TAG=%%T"
)

if defined LATEST_TAG (
    set "REPO_ZIP_URL=https://github.com/veritus-git/BadWords/archive/refs/tags/!LATEST_TAG!.zip"
    set "SOURCE_REPO=GitHub"
    goto :GOT_TAG
)

:: GitLab fallback
echo [WARN] GitHub unavailable, trying GitLab...
if not defined USE_PS_DL (
    for /f "delims=" %%T in ('curl -fsSL --connect-timeout 10 "https://gitlab.com/api/v4/projects/badwords%%2FBadWords/releases" ^| "!PYTHON_CMD!" -c "import json,sys; d=json.load(sys.stdin); print(d[0][\"tag_name\"] if isinstance(d,list) and d else \"\")" 2^>nul') do set "LATEST_TAG=%%T"
) else (
    for /f "delims=" %%T in ('powershell -NoProfile -Command "(Invoke-RestMethod \"https://gitlab.com/api/v4/projects/badwords%%2FBadWords/releases\")[0].tag_name" 2^>nul') do set "LATEST_TAG=%%T"
)

if defined LATEST_TAG (
    set "REPO_ZIP_URL=https://gitlab.com/badwords/BadWords/-/archive/!LATEST_TAG!/BadWords-!LATEST_TAG!.zip"
    set "SOURCE_REPO=GitLab"
    goto :GOT_TAG
)

echo [ERROR] Could not determine latest version from GitHub or GitLab.
exit /b 1

:GOT_TAG
echo [UPDATE] Latest release: !LATEST_TAG!  (source: !SOURCE_REPO!)

:: ── 5. Download & extract ───────────────────────────────────────────────────
set "TMP_DIR=%TEMP%\bw_update_%RANDOM%"
mkdir "!TMP_DIR!"
set "ZIP_PATH=!TMP_DIR!\repo.zip"

echo [INFO] Downloading from !SOURCE_REPO!...
if not defined USE_PS_DL (
    curl -fsSL "!REPO_ZIP_URL!" -o "!ZIP_PATH!"
) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '!REPO_ZIP_URL!' -OutFile '!ZIP_PATH!'"
)
if not exist "!ZIP_PATH!" (
    echo [ERROR] Download failed.
    rmdir /s /q "!TMP_DIR!"
    exit /b 1
)

echo [INFO] Extracting...
powershell -NoProfile -Command "Expand-Archive -Path '!ZIP_PATH!' -DestinationPath '!TMP_DIR!\extracted' -Force"

:: Find extracted subfolder
set "EXTRACTED_DIR="
for /d %%D in ("!TMP_DIR!\extracted\*") do (
    if "!EXTRACTED_DIR!"=="" set "EXTRACTED_DIR=%%D"
)

if not exist "!EXTRACTED_DIR!\src\main.py" (
    echo [ERROR] Extraction failed — src\main.py not found.
    rmdir /s /q "!TMP_DIR!"
    exit /b 1
)

:: ── 6. Sync files with Python ───────────────────────────────────────────────
echo [INFO] Syncing files...

:: Write Python sync script to a temp file (multiline -c doesn't work in CMD)
set "SYNC_PY=!TMP_DIR!\bw_sync.py"
(
echo import os, shutil, hashlib
echo.
echo def get_hash^(p^):
echo     try:
echo         with open^(p, 'rb'^) as f: return hashlib.md5^(f.read^(^)^).hexdigest^(^)
echo     except: return None
echo.
echo src_paths = [p for p in [r'!EXTRACTED_DIR!\src', r'!EXTRACTED_DIR!\assets'] if os.path.isdir^(p^)]
echo dst = r'!INSTALL_DIR!'
echo.
echo for src in src_paths:
echo     for root, dirs, files in os.walk^(src^):
echo         rel = os.path.relpath^(root, src^)
echo         d_dir = dst if rel == '.' else os.path.join^(dst, rel^)
echo         os.makedirs^(d_dir, exist_ok=True^)
echo         for f in files:
echo             s_f = os.path.join^(root, f^)
echo             d_f = os.path.join^(d_dir, f^)
echo             if get_hash^(s_f^) != get_hash^(d_f^):
echo                 shutil.copy2^(s_f, d_f^)
echo                 name = os.path.join^(rel, f^) if rel != '.' else f
echo                 print^('  Updated: ' + name^)
echo.
echo protected_files = {'pref.json','user.json','settings.json','badwords_debug.log'}
echo protected_dirs  = {'models','saves','venv','bin','libs'}
echo all_src = set^(^)
echo for src in src_paths:
echo     all_src ^|= set^(os.listdir^(src^)^)
echo.
echo for item in os.listdir^(dst^):
echo     if item in protected_files or item in protected_dirs: continue
echo     if item not in all_src:
echo         full = os.path.join^(dst, item^)
echo         try:
echo             if os.path.isdir^(full^): shutil.rmtree^(full^)
echo             else: os.remove^(full^)
echo             print^('  Removed obsolete: ' + item^)
echo         except Exception as e:
echo             print^('  [SKIP] Could not remove ' + item + ': ' + str^(e^)^)
) > "!SYNC_PY!"

"!PYTHON_CMD!" "!SYNC_PY!"
if !errorlevel! neq 0 (
    echo [ERROR] File sync failed.
    rmdir /s /q "!TMP_DIR!"
    exit /b 1
)

:: ── 7. Upgrade pip packages ─────────────────────────────────────────────────
if exist "!VENV_PIP!" (
    echo [INFO] Upgrading pip packages...
    "!VENV_PIP!" install --upgrade faster-whisper stable-ts pypdf 2>&1 | findstr /v "already satisfied"
) else (
    echo [WARN] venv pip not found, skipping package upgrade.
)

:: ── 8. Refresh libs junction ────────────────────────────────────────────────
set "LIBS_DIR=!INSTALL_DIR!\libs"
if exist "!VENV_DIR!\Lib\site-packages" (
    if exist "!LIBS_DIR!" ( rmdir "!LIBS_DIR!" >nul 2>&1 )
    mklink /J "!LIBS_DIR!" "!VENV_DIR!\Lib\site-packages" >nul 2>&1
    echo [INFO] libs junction refreshed.
)

rmdir /s /q "!TMP_DIR!" 2>nul

echo [UPDATE] BadWords updated to !LATEST_TAG! successfully!
echo [UPDATE] Please restart BadWords (close and relaunch from DaVinci Resolve).
exit /b 0
