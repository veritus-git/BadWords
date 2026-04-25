@echo off
setlocal EnableDelayedExpansion

:: --- CLEANUP ENVIRONMENT ---
:: Usuwamy zmienne, ktore moga mieszać w Pythonie (stare instalacje)
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

:: Strategia A: System PATH (Najważniejsza, bo instalator doda tu Pythona)
where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do (
        set "CANDIDATE=%%i"
        echo !CANDIDATE! | findstr /i "WindowsApps" >nul
        if !errorlevel! neq 0 (
            :: Znaleziono cos w PATH, sprawdzamy wersje
            call :CHECK_VERSION "!CANDIDATE!"
            if !IS_VALID! equ 1 (
                set "PYTHON_CMD=!CANDIDATE!"
                goto :FOUND_PYTHON
            )
        )
    )
)

:: Strategia B: AppData (User Install) - Domyślna dla instalacji bez Admina
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :VERIFY_PYTHON )

:: Strategia C: Program Files (Jako fallback, gdyby jednak tam byl)
if exist "%ProgramFiles%\Python312\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%ProgramFiles%\Python311\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe" & goto :VERIFY_PYTHON )

:: Strategia D: Launcher (Ostateczność)
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
    echo [INFO] Repair/Reset Mode detected. Forcing clean reinstall...
    set "PIP_FLAGS=--no-warn-script-location --force-reinstall --ignore-installed"
)

echo [INFO] Installing AI libraries...
if "%GPU_MODE%"=="1" (
    echo [INFO] Hardware: NVIDIA GPU
    "%VENV_PYTHON%" -m pip install faster-whisper stable-ts pypdf %PIP_FLAGS%
) else (
    echo [INFO] Hardware: CPU
    "%VENV_PYTHON%" -m pip install faster-whisper stable-ts pypdf %PIP_FLAGS%
)

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
powershell -NoProfile -Command "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%INSTALL_DIR%\ffmpeg_tmp' -Force"
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

echo.
echo [SUCCESS] Configuration complete!
exit /b 0

:ERROR_ARGS
echo [ERROR] Invalid arguments.
pause
exit /b 1