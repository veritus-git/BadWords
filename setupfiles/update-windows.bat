@echo off
:: --- BADWORDS AUTO-UPDATE (Windows, non-interactive) ---
:: Logic mirrors update-linux.sh: Python sync+cleanup written to a temp script.
:: IMPORTANT: ALL characters in this file must be plain ASCII (0x00-0x7F).
:: Unicode chars (em-dash, box-drawing etc.) in batch files cause CMD to
:: misread UTF-8 byte sequences as quote chars in CP1252, breaking the parser.
:: Exits 0 on success, 1 on failure.
setlocal EnableDelayedExpansion
set "PYTHONHOME="
set "PYTHONPATH="

echo [UPDATE] BadWords Windows Auto-Update starting...

:: --- 1. Find Python ---
set "PYTHON_CMD="
where python >nul 2>&1 && (
    for /f "tokens=*" %%P in ('where python') do (
        if "!PYTHON_CMD!"=="" (
            echo %%P | findstr /i "WindowsApps" >nul || set "PYTHON_CMD=%%P"
        )
    )
)
if not defined PYTHON_CMD (
    for %%V in (313 312 311 310) do (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
            goto :FOUND_PY
        )
    )
    echo [WARN] Python not found. Trying winget...
    winget install --id Python.Python.3.11 -e --silent --accept-source-agreements --accept-package-agreements
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    if not exist "!PYTHON_CMD!" (
        echo [ERROR] Python install failed. Please install Python 3.10-3.12 manually.
        exit /b 1
    )
)
:FOUND_PY
echo [INFO] Using Python: !PYTHON_CMD!

:: --- 2. Locate installation ---
set "WRAPPER_FILE=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "WRAPPER_FILE=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
    )
)
set "INSTALL_DIR="
if exist "!WRAPPER_FILE!" (
    set "DETECT_PS=%TEMP%\_bw_det_%RANDOM%.ps1"
    powershell -NoProfile -Command "Set-Content -Path '!DETECT_PS!' -Encoding UTF8 -Value 'foreach($l in (Get-Content ''!WRAPPER_FILE!'' -EA SilentlyContinue)){if($l -match ''INSTALL_DIR\s*=''){$v=($l -split ''='',2)[1].Trim().TrimStart(''r'').Trim([char]34).Trim([char]39).Trim([char]34).Trim([char]39);if($v){$v;break}}}'"
    for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -File "!DETECT_PS!" 2^>nul') do (
        if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%%P"
    )
    del "!DETECT_PS!" 2>nul
)
if not defined INSTALL_DIR (
    set "INSTALL_DIR=%APPDATA%\BadWords"
    echo [WARN] Could not read wrapper, using default: !INSTALL_DIR!
)
if not exist "!INSTALL_DIR!\main.py" (
    echo [ERROR] No valid BadWords installation at: !INSTALL_DIR!
    exit /b 1
)
echo [INFO] Installation path: !INSTALL_DIR!
set "VENV_DIR=!INSTALL_DIR!\venv"
set "VENV_PYTHON=!VENV_DIR!\Scripts\python.exe"
set "VENV_PIP=!VENV_DIR!\Scripts\pip.exe"

:: --- 3. Check curl ---
where curl >nul 2>&1 || set "USE_PS_DL=1"

:: --- 4. Fetch latest tag: GitHub first, GitLab fallback ---
echo [INFO] Checking latest release...
set "LATEST_TAG="
set "REPO_ZIP_URL="
set "SOURCE_REPO="
if not defined USE_PS_DL (
    for /f "delims=" %%T in ('curl -fsSL --connect-timeout 10 "https://api.github.com/repos/veritus-git/BadWords/releases/latest" ^| "!PYTHON_CMD!" -c "import json,sys;d=json.load(sys.stdin);print(d.get(\"tag_name\",\"\"))" 2^>nul') do set "LATEST_TAG=%%T"
) else (
    for /f "delims=" %%T in ('powershell -NoProfile -Command "(Invoke-RestMethod https://api.github.com/repos/veritus-git/BadWords/releases/latest).tag_name" 2^>nul') do set "LATEST_TAG=%%T"
)
if defined LATEST_TAG (
    set "REPO_ZIP_URL=https://github.com/veritus-git/BadWords/archive/refs/tags/!LATEST_TAG!.zip"
    set "SOURCE_REPO=GitHub"
    goto :GOT_TAG
)
echo [WARN] GitHub unavailable, trying GitLab...
if not defined USE_PS_DL (
    for /f "delims=" %%T in ('curl -fsSL --connect-timeout 10 "https://gitlab.com/api/v4/projects/badwords%%2FBadWords/releases" ^| "!PYTHON_CMD!" -c "import json,sys;d=json.load(sys.stdin);print(d[0][\"tag_name\"] if isinstance(d,list) and d else \"\")" 2^>nul') do set "LATEST_TAG=%%T"
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

:: --- 5. Download and extract ---
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
set "EXTRACTED_DIR="
for /d %%D in ("!TMP_DIR!\extracted\*") do (
    if "!EXTRACTED_DIR!"=="" set "EXTRACTED_DIR=%%D"
)
if not exist "!EXTRACTED_DIR!\src\main.py" (
    echo [ERROR] Extraction failed - src\main.py not found.
    rmdir /s /q "!TMP_DIR!"
    exit /b 1
)
set "SRC_MAIN=!EXTRACTED_DIR!\src"
set "SRC_ASSETS=!EXTRACTED_DIR!\assets"

:: --- 6. Sync + cleanup via Python (mirrors update-linux.sh exactly) ---
:: The Python script is written line-by-line using echo with DelayedExpansion
:: DISABLED so Python's != operator and ! chars are treated as plain text.
echo [INFO] Syncing files...
set "SYNC_PY=%TEMP%\_bw_sync_%RANDOM%.py"

setlocal DisableDelayedExpansion
echo import os, shutil, hashlib, sys                                         > "%SYNC_PY%"
echo src_paths = [p for p in [sys.argv[1], sys.argv[2]] if os.path.isdir(p)]>> "%SYNC_PY%"
echo dst = sys.argv[3]                                                       >> "%SYNC_PY%"
echo def get_hash(p):                                                        >> "%SYNC_PY%"
echo     try:                                                                >> "%SYNC_PY%"
echo         with open(p, 'rb') as fh: return hashlib.md5(fh.read()).hexdigest() >> "%SYNC_PY%"
echo     except Exception: return None                                       >> "%SYNC_PY%"
echo for src in src_paths:                                                   >> "%SYNC_PY%"
echo     for root, dirs, files in os.walk(src):                             >> "%SYNC_PY%"
echo         rel = os.path.relpath(root, src)                               >> "%SYNC_PY%"
echo         d_dir = dst if rel == '.' else os.path.join(dst, rel)          >> "%SYNC_PY%"
echo         os.makedirs(d_dir, exist_ok=True)                              >> "%SYNC_PY%"
echo         for fn in files:                                                >> "%SYNC_PY%"
echo             sf = os.path.join(root, fn)                                >> "%SYNC_PY%"
echo             df = os.path.join(d_dir, fn)                               >> "%SYNC_PY%"
echo             if get_hash(sf) != get_hash(df):                           >> "%SYNC_PY%"
echo                 shutil.copy2(sf, df)                                   >> "%SYNC_PY%"
echo                 lbl = fn if rel == '.' else os.path.join(rel, fn)      >> "%SYNC_PY%"
echo                 print('  Updated: ' + lbl)                             >> "%SYNC_PY%"
echo pf = {'pref.json','user.json','settings.json','badwords_debug.log','BadWords.py','unins000.dat','unins000.exe'} >> "%SYNC_PY%"
echo pd = {'models','saves','venv','bin','libs','icons','layout','.git','.github','__pycache__'} >> "%SYNC_PY%"
echo src_top = set()                                                         >> "%SYNC_PY%"
echo for s in src_paths: src_top.update(os.listdir(s))                      >> "%SYNC_PY%"
echo src_sub = {}                                                            >> "%SYNC_PY%"
echo for s in src_paths:                                                     >> "%SYNC_PY%"
echo     for r2, d2, f2 in os.walk(s):                                      >> "%SYNC_PY%"
echo         rel2 = os.path.relpath(r2, s)                                  >> "%SYNC_PY%"
echo         src_sub[rel2] = set(f2)                                        >> "%SYNC_PY%"
echo for item in sorted(os.listdir(dst)):                                    >> "%SYNC_PY%"
echo     if item in pf or item in pd: continue                              >> "%SYNC_PY%"
echo     if item not in src_top:                                             >> "%SYNC_PY%"
echo         full = os.path.join(dst, item)                                 >> "%SYNC_PY%"
echo         try:                                                            >> "%SYNC_PY%"
echo             if os.path.isdir(full): shutil.rmtree(full)                >> "%SYNC_PY%"
echo             else: os.remove(full)                                       >> "%SYNC_PY%"
echo             print('  Removed obsolete: ' + item)                       >> "%SYNC_PY%"
echo         except Exception as ex: print('  [WARN] rm ' + item + ': ' + str(ex)) >> "%SYNC_PY%"
echo for sub_rel, sub_files in src_sub.items():                             >> "%SYNC_PY%"
echo     if sub_rel == '.': continue                                         >> "%SYNC_PY%"
echo     sub_dst = os.path.join(dst, sub_rel)                               >> "%SYNC_PY%"
echo     if not os.path.isdir(sub_dst): continue                            >> "%SYNC_PY%"
echo     for df2 in sorted(os.listdir(sub_dst)):                            >> "%SYNC_PY%"
echo         if df2 not in sub_files:                                        >> "%SYNC_PY%"
echo             fp = os.path.join(sub_dst, df2)                            >> "%SYNC_PY%"
echo             try:                                                        >> "%SYNC_PY%"
echo                 if os.path.isdir(fp): shutil.rmtree(fp)                >> "%SYNC_PY%"
echo                 else: os.remove(fp)                                     >> "%SYNC_PY%"
echo                 print('  Removed obsolete: ' + os.path.join(sub_rel, df2)) >> "%SYNC_PY%"
echo             except Exception as ex: print('  [WARN] rm ' + df2 + ': ' + str(ex)) >> "%SYNC_PY%"
endlocal

"!PYTHON_CMD!" "!SYNC_PY!" "!SRC_MAIN!" "!SRC_ASSETS!" "!INSTALL_DIR!"
if !errorlevel! neq 0 echo [WARN] Sync exited with code !errorlevel! - continuing.
del "!SYNC_PY!" 2>nul
echo [INFO] File sync complete.

:: --- 7. Upgrade pip packages ---
:: Do NOT use pipes (|) inside if() blocks - CMD misparses them on some systems.
:: Running pip commands sequentially outside blocks avoids all issues.
set "PIP_OK=0"
if exist "!VENV_PYTHON!" set "PIP_OK=1"
if "!PIP_OK!"=="1" (
    echo [INFO] Upgrading pip packages...
    "!VENV_PYTHON!" -m pip install --upgrade pip >nul 2>&1
    "!VENV_PYTHON!" -m pip install --upgrade faster-whisper stable-ts pypdf >nul 2>&1
    echo [INFO] Packages upgraded.
)
if "!PIP_OK!"=="0" (
    if exist "!VENV_PIP!" (
        echo [INFO] Upgrading pip packages (pip fallback)...
        "!VENV_PIP!" install --upgrade faster-whisper stable-ts pypdf >nul 2>&1
        echo [INFO] Packages upgraded.
    ) else (
        echo [WARN] venv not found, skipping package upgrade.
    )
)

:: --- 8. Refresh libs junction (mirrors libs symlink in Linux) ---
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
