@echo off
setlocal EnableDelayedExpansion

:: --- CLEANUP ENVIRONMENT ---
:: Remove variables that might interfere with Python (old installations)
set "PYTHONHOME="
set "PYTHONPATH="

:: --- ARGUMENTS ---
set "INSTALL_DIR=%~1"
set "GPU_MODE=%~2"
set "FFMPEG_ZIP=%~3"
set "WIPE_MODE=%~4"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "BIN_DIR=%INSTALL_DIR%\bin"

if "%INSTALL_DIR%"=="" goto :ERROR_ARGS
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

cd /d "%INSTALL_DIR%"

echo ==================================================
echo      BadWords - Environment Configuration
echo ==================================================

:: ==========================================
:: 1. SEARCH FOR PYTHON (Prioritize PATH & AppData)
:: ==========================================
echo [INFO] Searching for Python (3.10 - 3.12)...
set "PYTHON_CMD="

:: Strategy A: System PATH (Highest priority, as installer adds Python here)
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do (
        set "CANDIDATE=%%i"
        echo !CANDIDATE! | findstr /i "WindowsApps" >nul
        if !errorlevel! neq 0 (
            :: Found something in PATH, checking version
            call :CHECK_VERSION "!CANDIDATE!"
            if !IS_VALID! equ 1 (
                set "PYTHON_CMD=!CANDIDATE!"
                goto :FOUND_PYTHON
            )
        )
    )
)

:: Strategy B: AppData (User Install) - Default for non-Admin installs
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :VERIFY_PYTHON )

:: Strategy C: Program Files (Fallback)
if exist "%ProgramFiles%\Python312\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%ProgramFiles%\Python311\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe" & goto :VERIFY_PYTHON )

:: Strategy D: Launcher (Last resort)
py -3.12 --version >nul 2>&1
if !errorlevel! equ 0 ( set "PYTHON_CMD=py -3.12" & goto :FOUND_PYTHON )

goto :PYTHON_NOT_FOUND

:: --- SUBROUTINE: CHECK VERSION ---
:CHECK_VERSION
set "EXE=%~1"
set "IS_VALID=0"
for /f "tokens=2" %%v in ('"%EXE%" --version 2^>^&1') do set "VER=%%v"
echo !VER! | findstr /b "3.10 3.11 3.12" >nul
if !errorlevel! equ 0 (
    echo [INFO] Found valid python in PATH: !VER!
    set "IS_VALID=1"
)
exit /b

:VERIFY_PYTHON
"!PYTHON_CMD!" --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] Python at "!PYTHON_CMD!" is broken.
    set "PYTHON_CMD="
    goto :PYTHON_NOT_FOUND
)
goto :FOUND_PYTHON

:PYTHON_NOT_FOUND
echo.
echo [CRITICAL ERROR] Could not find Python 3.10-3.12.
echo The installer should have installed it and added it to PATH.
pause
exit /b 1

:FOUND_PYTHON
echo [INFO] Selected Interpreter: "!PYTHON_CMD!"

:: ==========================================
:: 2. CREATE VENV
:: ==========================================
if exist "%VENV_DIR%" (
    echo [INFO] Venv exists. Checking integrity...
    if not exist "%VENV_DIR%\Scripts\python.exe" (
        echo [WARN] Venv corrupted. Recreating...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        goto :VENV_READY
    )
)

echo [INFO] Creating virtual environment...
"!PYTHON_CMD!" -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo [ERROR] Failed to create venv using "!PYTHON_CMD!"
    pause
    exit /b 1
)

:VENV_READY
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

:: ==========================================
:: 3. INSTALL DEPENDENCIES
:: ==========================================
echo [INFO] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1

:: Flag logic based on Wipe Mode
if "%WIPE_MODE%"=="0" (
    echo [INFO] Standard Install/Update detected. Using fast upgrade...
    set "PIP_FLAGS=--upgrade"
) else (
    echo [INFO] Repair/Reset Mode detected. Fresh environment expected...
    set "PIP_FLAGS="
)

:: --- SMART SKIP FOR AI LIBRARIES ---
echo [INFO] Checking AI libraries...
if "%WIPE_MODE%"=="0" (
    if exist "%VENV_DIR%\Lib\site-packages\torch" if exist "%VENV_DIR%\Lib\site-packages\faster_whisper" (
        echo [INFO] AI libraries already installed. Quick update detected.
        echo [INFO] Skipping heavy downloads...
        goto :SKIP_AI_INSTALL
    )
)

echo [INFO] Installing AI libraries...
if "%GPU_MODE%"=="1" (
    echo [INFO] Hardware: NVIDIA GPU ^(CUDA + CPU Support^)
    echo [INFO] Installing full PyTorch ^(Supports BOTH CUDA and CPU^)...
    "%VENV_PYTHON%" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 %PIP_FLAGS%
    "%VENV_PYTHON%" -m pip install faster-whisper stable-ts pypdf --extra-index-url https://download.pytorch.org/whl/cu121 %PIP_FLAGS%
    goto :SKIP_AI_INSTALL
)

echo [INFO] Hardware: CPU ONLY
echo [INFO] Downloading CPU-optimized PyTorch to save disk space...
"%VENV_PYTHON%" -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu %PIP_FLAGS%
"%VENV_PYTHON%" -m pip install faster-whisper stable-ts pypdf --extra-index-url https://download.pytorch.org/whl/cpu %PIP_FLAGS%

:SKIP_AI_INSTALL

if !errorlevel! neq 0 (
    echo [ERROR] Failed to install libraries.
    pause
    exit /b 1
)

:: ==========================================
:: 4. FFMPEG & FINALIZE
:: ==========================================

if "%WIPE_MODE%"=="0" (
    if exist "%BIN_DIR%\ffmpeg.exe" (
        echo [INFO] Portable FFmpeg found. Skipping extraction ^(Update mode^).
        goto :SKIP_FFMPEG
    )
)

if not exist "%FFMPEG_ZIP%" goto :SKIP_FFMPEG

echo [INFO] Extracting FFmpeg...
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"
:: DEBUG FIX: Escaped double quotes protect apostrophes in usernames
powershell -NoProfile -Command "Expand-Archive -Path \"!FFMPEG_ZIP!\" -DestinationPath \"!INSTALL_DIR!\ffmpeg_tmp\" -Force"
echo [INFO] Installing binaries...
for /r "%INSTALL_DIR%\ffmpeg_tmp" %%F in (ffmpeg.exe, ffprobe.exe) do ( copy /y "%%F" "%BIN_DIR%\" >nul )
rmdir /s /q "%INSTALL_DIR%\ffmpeg_tmp" 2>nul
del /f /q "%FFMPEG_ZIP%" 2>nul

:SKIP_FFMPEG
if exist "libs" goto :LIBS_EXIST
echo [INFO] Linking libraries...
for /d %%D in ("%VENV_DIR%\Lib\site-packages") do set "SITE_PACKAGES=%%D"
mklink /J "libs" "!SITE_PACKAGES!" >nul
:LIBS_EXIST

:: ==========================================
:: 5. LINK WITH DAVINCI RESOLVE
:: ==========================================
echo [INFO] Linking with DaVinci Resolve...

:: Determine default path
set "RESOLVE_SCRIPT_DIR=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"

:: Check for Microsoft Store edition (overrides default path)
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "RESOLVE_SCRIPT_DIR=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
    )
)

:: Create subfolders if they do not exist (e.g., Utility)
if not exist "!RESOLVE_SCRIPT_DIR!" (
    mkdir "!RESOLVE_SCRIPT_DIR!"
)

set "WRAPPER_FILE=!RESOLVE_SCRIPT_DIR!\BadWords.py"

:: Generate clean Python code directly to file
:: (Spaces before '>' removed to prevent trailing spaces in batch)
echo import sys> "!WRAPPER_FILE!"
echo import os>> "!WRAPPER_FILE!"
echo import traceback>> "!WRAPPER_FILE!"
:: DEBUG FIX: TRIPLE QUOTES PROTECT AGAINST APOSTROPHE ERRORS IN USERNAMES!
echo INSTALL_DIR = r"""%INSTALL_DIR%""">> "!WRAPPER_FILE!"
echo LIBS_DIR = os.path.join(INSTALL_DIR, 'libs')>> "!WRAPPER_FILE!"
echo MAIN_SCRIPT = os.path.join(INSTALL_DIR, 'main.py')>> "!WRAPPER_FILE!"
echo if os.path.exists(LIBS_DIR) and LIBS_DIR not in sys.path:>> "!WRAPPER_FILE!"
echo     sys.path.insert(0, LIBS_DIR)>> "!WRAPPER_FILE!"
echo if INSTALL_DIR not in sys.path:>> "!WRAPPER_FILE!"
echo     sys.path.append(INSTALL_DIR)>> "!WRAPPER_FILE!"
echo if os.path.exists(MAIN_SCRIPT):>> "!WRAPPER_FILE!"
echo     try:>> "!WRAPPER_FILE!"
echo         with open(MAIN_SCRIPT, 'r', encoding='utf-8') as f:>> "!WRAPPER_FILE!"
echo             code = f.read()>> "!WRAPPER_FILE!"
echo         g = globals().copy()>> "!WRAPPER_FILE!"
echo         g['__file__'] = MAIN_SCRIPT>> "!WRAPPER_FILE!"
echo         exec(code, g)>> "!WRAPPER_FILE!"
echo     except Exception as e:>> "!WRAPPER_FILE!"
echo         print(f"Error executing BadWords: {e}")>> "!WRAPPER_FILE!"
echo         traceback.print_exc()>> "!WRAPPER_FILE!"
echo else:>> "!WRAPPER_FILE!"
echo     print(f"CRITICAL: Script not found at {MAIN_SCRIPT}")>> "!WRAPPER_FILE!"

if exist "!WRAPPER_FILE!" (
    echo [SUCCESS] Wrapper successfully created at: !WRAPPER_FILE!
) else (
    echo [ERROR] Failed to create wrapper file at: !WRAPPER_FILE!
)

echo.
echo [SUCCESS] Configuration complete!
:: Auto-close timeout (will gracefully exit without waiting for a key press)
timeout /t 1 >nul
exit /b 0

:ERROR_ARGS
echo [ERROR] Invalid arguments.
pause
exit /b 1