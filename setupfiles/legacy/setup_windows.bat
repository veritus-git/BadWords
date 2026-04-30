@echo off
:: --- BADWORDS WINDOWS ENVIRONMENT CONFIGURATOR v3.0 ---
:: Called by the Inno Setup installer (ssPostInstall) after files are copied.
:: Args: %1=INSTALL_DIR  %2=FFMPEG_ZIP  %3=WIPE_MODE  %4=OLD_INSTALL_DIR
:: WIPE_MODE: 0=Install/Update  1=Repair  2=Move  3=FullReset  4=RemoveCompletely
:: GPU is AUTO-DETECTED -- no user choice needed.
:: Never uses "pause" -- silent-install safe. Exits 0 on success, 1 on failure.
setlocal EnableDelayedExpansion

set "PYTHONHOME="
set "PYTHONPATH="

set "INSTALL_DIR=%~1"
set "FFMPEG_ZIP=%~2"
set "WIPE_MODE=%~3"
set "OLD_INSTALL_DIR=%~4"

if "%INSTALL_DIR%"=="" goto :ERR_ARGS

set "VENV_DIR=%INSTALL_DIR%\venv"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "MODELS_DIR=%INSTALL_DIR%\models"
set "SAVES_DIR=%INSTALL_DIR%\saves"
set "LIBS_DIR=%INSTALL_DIR%\libs"

echo ===========================================================
echo       BadWords - Environment Configuration v3.0
echo ===========================================================
echo [INFO] Install Dir : %INSTALL_DIR%
echo [INFO] Wipe Mode   : %WIPE_MODE%
echo [INFO] Old Dir     : %OLD_INSTALL_DIR%

:: =====================================================================
:: STEP 1 - AUTO-DETECT NVIDIA GPU VIA WMI
:: =====================================================================
echo [INFO] Detecting GPU...
set "GPU_MODE=0"
for /f "delims=" %%G in ('powershell -NoProfile -Command "try{$g=Get-WmiObject Win32_VideoController -EA Stop | Where-Object {$_.Name -like '*NVIDIA*'} | Select-Object -First 1;if($g){'1'}else{'0'}}catch{'0'}" 2^>nul') do (
    if "%%G"=="1" set "GPU_MODE=1"
)
if "!GPU_MODE!"=="1" (
    echo [INFO] GPU: NVIDIA detected - CUDA mode enabled.
) else (
    echo [INFO] GPU: No NVIDIA found - CPU mode.
)

:: =====================================================================
:: STEP 2 - FIND PYTHON (py launcher -> direct paths -> where)
:: =====================================================================
echo [INFO] Searching for Python 3.10-3.13...
set "PYTHON_CMD="

:: Primary: py launcher (most reliable on Win10/11, handles all versions)
for %%V in (3.12 3.11 3.10 3.13) do (
    if not defined PYTHON_CMD (
        py -%%V --version >nul 2>&1
        if !errorlevel! equ 0 (
            set "PYTHON_CMD=py -%%V"
        )
    )
)
if defined PYTHON_CMD goto :PY_FOUND

:: Secondary: well-known install locations
for %%V in (312 311 310 313) do (
    if not defined PYTHON_CMD (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe"
        )
        if exist "%ProgramFiles%\Python%%V\python.exe" (
            set "PYTHON_CMD=%ProgramFiles%\Python%%V\python.exe"
        )
        if exist "%ProgramFiles(x86)%\Python%%V\python.exe" (
            set "PYTHON_CMD=%ProgramFiles(x86)%\Python%%V\python.exe"
        )
    )
)
if defined PYTHON_CMD goto :PY_FOUND

:: Tertiary: where python (skip WindowsApps Store shims)
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%P in ('where python 2^>nul') do (
        if not defined PYTHON_CMD (
            echo %%P | findstr /i "WindowsApps" >nul
            if !errorlevel! neq 0 set "PYTHON_CMD=%%P"
        )
    )
)
if defined PYTHON_CMD goto :PY_FOUND

echo [ERROR] Python 3.10+ not found. Install from python.org.
exit /b 1

:PY_FOUND
echo [INFO] Python: !PYTHON_CMD!

:: =====================================================================
:: STEP 3 - MODE 4: REMOVE COMPLETELY
:: =====================================================================
if "!WIPE_MODE!"=="4" goto :MODE_REMOVE

:: =====================================================================
:: STEP 4 - ENSURE BASE DIRS EXIST
:: =====================================================================
if not exist "%INSTALL_DIR%"  mkdir "%INSTALL_DIR%"
if not exist "%MODELS_DIR%"   mkdir "%MODELS_DIR%"
if not exist "%SAVES_DIR%"    mkdir "%SAVES_DIR%"
if not exist "%BIN_DIR%"      mkdir "%BIN_DIR%"

:: =====================================================================
:: STEP 5 - MODE 2: MOVE INSTALLATION
:: =====================================================================
if "!WIPE_MODE!"=="2" (
    if "!OLD_INSTALL_DIR!"=="" goto :MOVE_DONE
    if /i "!OLD_INSTALL_DIR!"=="!INSTALL_DIR!" goto :MOVE_DONE
    if not exist "!OLD_INSTALL_DIR!" goto :MOVE_DONE

    echo [MOVE] Moving heavy dirs from old location...
    for %%D in (venv bin models saves) do (
        if exist "!OLD_INSTALL_DIR!\%%D" (
            robocopy "!OLD_INSTALL_DIR!\%%D" "!INSTALL_DIR!\%%D" /E /MOVE /NP /NJH /NJS >nul 2>&1
        )
    )
    :: Move user data files
    for %%F in (pref.json user.json settings.json badwords_debug.log) do (
        if exist "!OLD_INSTALL_DIR!\%%F" (
            copy /y "!OLD_INSTALL_DIR!\%%F" "!INSTALL_DIR!\%%F" >nul 2>&1
        )
    )
    echo [MOVE] Removing old directory...
    rmdir /s /q "!OLD_INSTALL_DIR!" 2>nul
    echo [MOVE] Done.
)
:MOVE_DONE

:: =====================================================================
:: STEP 6 - MODE 3: FULL RESET - backup JSONs, wipe venv+bin+libs
:: =====================================================================
if "!WIPE_MODE!"=="3" (
    echo [RESET] Backing up user data...
    for %%F in (user.json settings.json pref.json) do (
        if exist "!INSTALL_DIR!\%%F" (
            copy /y "!INSTALL_DIR!\%%F" "%TEMP%\bw_bak_%%F" >nul 2>&1
        )
    )
    echo [RESET] Wiping venv, bin, libs...
    if exist "!VENV_DIR!"  rmdir /s /q "!VENV_DIR!"
    if exist "!BIN_DIR!"   rmdir /s /q "!BIN_DIR!"
    if exist "!LIBS_DIR!"  rmdir /s /q "!LIBS_DIR!" 2>nul
    mkdir "%BIN_DIR%"
    if exist "%USERPROFILE%\.cache\whisper" rmdir /s /q "%USERPROFILE%\.cache\whisper" 2>nul
)

:: =====================================================================
:: STEP 7 - MODE 1: REPAIR - wipe env, keep user data & models
:: =====================================================================
if "!WIPE_MODE!"=="1" (
    echo [REPAIR] Wiping venv, bin, libs (keeping models/saves/data)...
    if exist "!VENV_DIR!"  rmdir /s /q "!VENV_DIR!"
    if exist "!BIN_DIR!"   rmdir /s /q "!BIN_DIR!"
    if exist "!LIBS_DIR!"  rmdir /s /q "!LIBS_DIR!" 2>nul
    mkdir "%BIN_DIR%"
    if exist "%USERPROFILE%\.cache\whisper" rmdir /s /q "%USERPROFILE%\.cache\whisper" 2>nul
)

:: =====================================================================
:: STEP 8 - VENV SETUP
:: =====================================================================
if exist "!VENV_DIR!\Scripts\python.exe" (
    echo [VENV] Virtual environment present.
    :: For Update mode (0/2), keep existing venv
    if "!WIPE_MODE!"=="0" goto :VENV_READY
    if "!WIPE_MODE!"=="2" goto :VENV_READY
)

:: Check for broken venv
if exist "!VENV_DIR!" (
    if not exist "!VENV_DIR!\Scripts\python.exe" (
        echo [VENV] Corrupted venv found. Removing...
        rmdir /s /q "!VENV_DIR!"
    )
)

echo [VENV] Creating virtual environment...
!PYTHON_CMD! -m venv "!VENV_DIR!"
if !errorlevel! neq 0 (
    echo [ERROR] venv creation failed. Check Python installation.
    exit /b 1
)
echo [VENV] Created OK.

:VENV_READY
set "VENV_PYTHON=!VENV_DIR!\Scripts\python.exe"

:: =====================================================================
:: STEP 9 - PIP UPGRADE
:: =====================================================================
echo [PIP] Upgrading pip...
"!VENV_PYTHON!" -m pip install --upgrade pip --quiet 2>&1 | findstr /v "already"

:: =====================================================================
:: STEP 10 - AI LIBRARIES (SMART: skip heavy downloads if Update+present)
:: =====================================================================
:: Fast path: Update/Move mode + torch already installed
if "!WIPE_MODE!"=="0" (
    "!VENV_PYTHON!" -c "import torch" >nul 2>&1
    if !errorlevel! equ 0 (
        "!VENV_PYTHON!" -c "import faster_whisper" >nul 2>&1
        if !errorlevel! equ 0 (
            echo [PIP] AI libraries present. Quick upgrade only...
            "!VENV_PYTHON!" -m pip install --upgrade faster-whisper stable-ts pypdf --quiet 2>&1 | findstr /v "already"
            goto :PIP_AI_DONE
        )
    )
)
if "!WIPE_MODE!"=="2" (
    "!VENV_PYTHON!" -c "import torch" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [PIP] AI libraries present (Move mode). Quick upgrade only...
        "!VENV_PYTHON!" -m pip install --upgrade faster-whisper stable-ts pypdf --quiet 2>&1 | findstr /v "already"
        goto :PIP_AI_DONE
    )
)

:: Full install based on GPU auto-detect
if "!GPU_MODE!"=="1" (
    echo [PIP] Installing AI libraries with NVIDIA CUDA 12 support...
    "!VENV_PYTHON!" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
    if !errorlevel! neq 0 (
        echo [WARN] CUDA install failed. Falling back to CPU...
        "!VENV_PYTHON!" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    )
    "!VENV_PYTHON!" -m pip install faster-whisper stable-ts pypdf nvidia-cublas-cu12 nvidia-cudnn-cu12 --quiet
) else (
    echo [PIP] Installing AI libraries (CPU mode)...
    "!VENV_PYTHON!" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    "!VENV_PYTHON!" -m pip install faster-whisper stable-ts pypdf --quiet
)
if !errorlevel! neq 0 (
    echo [ERROR] AI library installation failed.
    exit /b 1
)

:PIP_AI_DONE
:: PySide6
"!VENV_PYTHON!" -c "import PySide6" >nul 2>&1
if !errorlevel! neq 0 (
    echo [PIP] Installing PySide6...
    "!VENV_PYTHON!" -m pip install PySide6 --quiet
    if !errorlevel! neq 0 (
        echo [ERROR] PySide6 installation failed.
        exit /b 1
    )
) else (
    echo [PIP] PySide6 present.
)
echo [PIP] Done.

:: =====================================================================
:: STEP 11 - FFMPEG
:: =====================================================================
:: Skip if Update/Move mode and ffmpeg already works
if "!WIPE_MODE!"=="0" (
    if exist "!BIN_DIR!\ffmpeg.exe" (
        "!BIN_DIR!\ffmpeg.exe" -version >nul 2>&1
        if !errorlevel! equ 0 (
            echo [FFMPEG] Already installed and functional. Skipping.
            goto :FFMPEG_DONE
        )
    )
)
if "!WIPE_MODE!"=="2" (
    if exist "!BIN_DIR!\ffmpeg.exe" (
        "!BIN_DIR!\ffmpeg.exe" -version >nul 2>&1
        if !errorlevel! equ 0 (
            echo [FFMPEG] Already installed and functional (Move). Skipping.
            goto :FFMPEG_DONE
        )
    )
)

if not exist "!FFMPEG_ZIP!" (
    echo [FFMPEG] No zip provided. Skipping.
    goto :FFMPEG_DONE
)

echo [FFMPEG] Extracting...
set "FFMPEG_TMP=!INSTALL_DIR!\ffmpeg_tmp"
if exist "!FFMPEG_TMP!" rmdir /s /q "!FFMPEG_TMP!"
powershell -NoProfile -Command "Expand-Archive -Path '!FFMPEG_ZIP!' -DestinationPath '!FFMPEG_TMP!' -Force"
for /r "!FFMPEG_TMP!" %%F in (ffmpeg.exe ffprobe.exe) do (
    copy /y "%%F" "!BIN_DIR!\" >nul 2>&1
)
rmdir /s /q "!FFMPEG_TMP!" 2>nul
echo [FFMPEG] Installed.

:FFMPEG_DONE

:: =====================================================================
:: STEP 12 - LIBS JUNCTION (venv site-packages -> libs)
:: =====================================================================
set "SITE_PKG=!VENV_DIR!\Lib\site-packages"
if exist "!SITE_PKG!" (
    :: Remove old junction/dir/symlink
    if exist "!LIBS_DIR!" (
        rmdir "!LIBS_DIR!" >nul 2>&1
        if exist "!LIBS_DIR!" rmdir /s /q "!LIBS_DIR!" 2>nul
    )
    mklink /J "!LIBS_DIR!" "!SITE_PKG!" >nul
    if !errorlevel! equ 0 (
        echo [LIBS] Junction created.
    ) else (
        echo [WARN] mklink /J failed. Trying PowerShell...
        powershell -NoProfile -Command "New-Item -ItemType Junction -Path '!LIBS_DIR!' -Target '!SITE_PKG!' -Force | Out-Null"
    )
)

:: =====================================================================
:: STEP 13 - DAVINCI RESOLVE WRAPPER (Base64-encoded - no escaping issues)
:: Wrapper Python is embedded as Base64 (pure [A-Za-z0-9+/=] - CMD safe).
:: PowerShell decodes it, substitutes INSTALL_DIR, writes to Resolve scripts.
:: =====================================================================
echo [WRAPPER] Detecting DaVinci Resolve installation...

:: Standard install path
set "RESOLVE_DIR=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
:: Microsoft Store edition detection
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "RESOLVE_DIR=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
    )
)
if not exist "!RESOLVE_DIR!" mkdir "!RESOLVE_DIR!"

:: Write INSTALL_DIR to temp file (no quoting issues)
(echo !INSTALL_DIR!)> "%TEMP%\bw_setup_idir.txt"
(echo !RESOLVE_DIR!\BadWords.py)> "%TEMP%\bw_setup_wpath.txt"

:: Generate wrapper via PowerShell using Base64-encoded Python template.
:: The template uses __IDIR__ as placeholder, replaced with actual path.
set "WRAP_PS=%TEMP%\bw_wrap_gen.ps1"
(
echo $idir  = [IO.File]::ReadAllText("$env:TEMP\bw_setup_idir.txt").Trim()
echo $wpath = [IO.File]::ReadAllText("$env:TEMP\bw_setup_wpath.txt").Trim()
echo $b64   = "aW1wb3J0IHN5cywgb3MsIHRyYWNlYmFjawpJTlNUQUxMX0RJUiA9IHInX19JRElSX18nCkxJQlNfRElSICAgID0gb3MucGF0aC5qb2luKElOU1RBTExfRElSLCAnbGlicycpClZFTlZfTElCUyAgID0gb3MucGF0aC5qb2luKElOU1RBTExfRElSLCAndmVudicsICdMaWInLCAnc2l0ZS1wYWNrYWdlcycpCk1BSU5fU0NSSVBUID0gb3MucGF0aC5qb2luKElOU1RBTExfRElSLCAnbWFpbi5weScpCmlmIG9zLnBhdGguZXhpc3RzKFZFTlZfTElCUykgYW5kIFZFTlZfTElCUyBub3QgaW4gc3lzLnBhdGg6CiAgICBzeXMucGF0aC5pbnNlcnQoMCwgVkVOVl9MSUJTKQppZiBvcy5wYXRoLmV4aXN0cyhMSUJTX0RJUikgYW5kIExJQlNfRElSIG5vdCBpbiBzeXMucGF0aDoKICAgIHN5cy5wYXRoLmluc2VydCgwLCBMSUJTX0RJUikKaWYgSU5TVEFMTF9ESVIgbm90IGluIHN5cy5wYXRoOgogICAgc3lzLnBhdGguYXBwZW5kKElOU1RBTExfRElSKQppZiBvcy5wYXRoLmV4aXN0cyhNQUlOX1NDUklQVCk6CiAgICB0cnk6CiAgICAgICAgd2l0aCBvcGVuKE1BSU5fU0NSSVBULCAncicsIGVuY29kaW5nPSd1dGYtOCcpIGFzIGY6CiAgICAgICAgICAgIGNvZGUgPSBmLnJlYWQoKQogICAgICAgIGcgPSBnbG9iYWxzKCkuY29weSgpCiAgICAgICAgZ1snX19maWxlX18nXSA9IE1BSU5fU0NSSVBUCiAgICAgICAgZXhlYyhjb2RlLCBnKQogICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgIHByaW50KCdFcnJvciBleGVjdXRpbmcgQmFkV29yZHM6ICcgKyBzdHIoZSkpCiAgICAgICAgdHJhY2ViYWNrLnByaW50X2V4YygpCmVsc2U6CiAgICBwcmludCgnQ1JJVElDQUw6IE5vdCBmb3VuZDogJyArIE1BSU5fU0NSSVBUKQo="
echo $bytes  = [Convert]::FromBase64String($b64)
echo $code   = [Text.Encoding]::UTF8.GetString($bytes)
echo $code   = $code.Replace("__IDIR__", $idir)
echo [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($wpath)) > $null
echo [IO.File]::WriteAllText($wpath, $code, [Text.Encoding]::UTF8)
echo Write-Host "[OK] Wrapper: $wpath"
) > "%WRAP_PS%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%WRAP_PS%"
set "WRAP_RC=!errorlevel!"
del "%WRAP_PS%" 2>nul
del "%TEMP%\bw_setup_idir.txt" 2>nul
del "%TEMP%\bw_setup_wpath.txt" 2>nul
if !WRAP_RC! neq 0 (
    echo [WARN] Wrapper generation failed (code !WRAP_RC!). Check DaVinci Resolve installation.
)


:: =====================================================================
:: STEP 14 - RESTORE JSON AFTER FULL RESET
:: =====================================================================
if "!WIPE_MODE!"=="3" (
    echo [RESET] Restoring user data...
    for %%F in (user.json settings.json pref.json) do (
        if exist "%TEMP%\bw_bak_%%F" (
            copy /y "%TEMP%\bw_bak_%%F" "!INSTALL_DIR!\%%F" >nul 2>&1
            del "%TEMP%\bw_bak_%%F" 2>nul
        )
    )
)

echo.
echo [SUCCESS] BadWords configured successfully!
exit /b 0

:: =====================================================================
:: MODE 4: REMOVE COMPLETELY
:: =====================================================================
:MODE_REMOVE
echo [REMOVE] Removing BadWords completely...

:: 1. Remove DaVinci Resolve wrappers (standard path)
set "RES_WRAPPER=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
if exist "!RES_WRAPPER!" (
    del /f /q "!RES_WRAPPER!" 2>nul
    echo [REMOVE] Deleted standard wrapper.
)

:: 2. Remove MS Store DaVinci Resolve wrapper
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    set "STORE_W=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
    if exist "!STORE_W!" (
        del /f /q "!STORE_W!" 2>nul
        echo [REMOVE] Deleted Store wrapper.
    )
)

:: 3. Remove Inno Setup uninstall registry keys (both possible GUIDs)
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-1234567890}_is1" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords_is1" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords" /f >nul 2>&1
echo [REMOVE] Registry entries cleared.

:: 4. Whisper cache
if exist "%USERPROFILE%\.cache\whisper" (
    rmdir /s /q "%USERPROFILE%\.cache\whisper" 2>nul
    echo [REMOVE] Whisper cache cleared.
)

:: 5. Remove entire install directory last
if exist "!INSTALL_DIR!" (
    rmdir /s /q "!INSTALL_DIR!"
    echo [REMOVE] Installation directory removed.
)

echo [REMOVE] BadWords completely removed.
exit /b 0

:: =====================================================================
:: ERROR HANDLERS
:: =====================================================================
:ERR_ARGS
echo [ERROR] Missing INSTALL_DIR argument.
exit /b 1