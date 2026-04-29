@echo off
:: --- BADWORDS WINDOWS ENVIRONMENT CONFIGURATOR v2.0 ---
:: Called by the Inno Setup installer after files are copied.
:: Args: %1=INSTALL_DIR  %2=GPU_MODE(0/1)  %3=FFMPEG_ZIP  %4=WIPE_MODE(0/1/2/3)
:: WIPE_MODE: 0=Update(fast)  1=Repair  2=Move(re-link)  3=FullWipe(fresh)
setlocal EnableDelayedExpansion

set "PYTHONHOME="
set "PYTHONPATH="

set "INSTALL_DIR=%~1"
set "GPU_MODE=%~2"
set "FFMPEG_ZIP=%~3"
set "WIPE_MODE=%~4"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "BIN_DIR=%INSTALL_DIR%\bin"
set "MODELS_DIR=%INSTALL_DIR%\models"

if "%INSTALL_DIR%"=="" goto :ERROR_ARGS
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%MODELS_DIR%"  mkdir "%MODELS_DIR%"
if not exist "%BIN_DIR%"     mkdir "%BIN_DIR%"

cd /d "%INSTALL_DIR%"

echo ==================================================
echo      BadWords - Environment Configuration
echo ==================================================
echo [INFO] Install Dir : %INSTALL_DIR%
echo [INFO] GPU Mode    : %GPU_MODE%
echo [INFO] Wipe Mode   : %WIPE_MODE%

:: ── Whisper cache cleanup ─────────────────────────────────────────────────────
if exist "%USERPROFILE%\.cache\whisper" (
    echo [INFO] Removing Whisper model cache...
    rmdir /s /q "%USERPROFILE%\.cache\whisper" 2>nul
)

:: ==========================================
:: 1. FIND PYTHON
:: ==========================================
echo [INFO] Searching for Python 3.10 - 3.12...
set "PYTHON_CMD="

where python >nul 2>&1
if !errorlevel! equ 0 (
    for /f "tokens=*" %%i in ('where python') do (
        set "CANDIDATE=%%i"
        echo !CANDIDATE! | findstr /i "WindowsApps" >nul
        if !errorlevel! neq 0 (
            call :CHECK_VERSION "!CANDIDATE!"
            if !IS_VALID! equ 1 (
                set "PYTHON_CMD=!CANDIDATE!"
                goto :FOUND_PYTHON
            )
        )
    )
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe" & goto :VERIFY_PYTHON )
if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" ( set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe" & goto :VERIFY_PYTHON )
if exist "%ProgramFiles%\Python312\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python312\python.exe" & goto :VERIFY_PYTHON )
if exist "%ProgramFiles%\Python311\python.exe" ( set "PYTHON_CMD=%ProgramFiles%\Python311\python.exe" & goto :VERIFY_PYTHON )

py -3.12 --version >nul 2>&1
if !errorlevel! equ 0 ( set "PYTHON_CMD=py -3.12" & goto :FOUND_PYTHON )
py -3.11 --version >nul 2>&1
if !errorlevel! equ 0 ( set "PYTHON_CMD=py -3.11" & goto :FOUND_PYTHON )

goto :PYTHON_NOT_FOUND

:CHECK_VERSION
set "EXE=%~1"
set "IS_VALID=0"
for /f "tokens=2" %%v in ('"%EXE%" --version 2^>&1') do set "VER=%%v"
echo !VER! | findstr /b "3.10 3.11 3.12" >nul
if !errorlevel! equ 0 ( set "IS_VALID=1" )
exit /b

:VERIFY_PYTHON
"!PYTHON_CMD!" --version >nul 2>&1
if !errorlevel! neq 0 ( set "PYTHON_CMD=" & goto :PYTHON_NOT_FOUND )
goto :FOUND_PYTHON

:PYTHON_NOT_FOUND
echo [CRITICAL] Could not find Python 3.10-3.12.
pause
exit /b 1

:FOUND_PYTHON
echo [INFO] Selected: !PYTHON_CMD!

:: ==========================================
:: 2. CREATE VENV
:: ==========================================
if exist "%VENV_DIR%" (
    if not exist "%VENV_DIR%\Scripts\python.exe" (
        echo [WARN] Venv corrupted. Recreating...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        goto :VENV_READY
    )
)

echo [INFO] Creating virtual environment...
"!PYTHON_CMD!" -m venv "%VENV_DIR%"
if !errorlevel! neq 0 ( echo [ERROR] venv creation failed. & pause & exit /b 1 )

:VENV_READY
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ==========================================
:: 3. INSTALL DEPENDENCIES
:: ==========================================
echo [INFO] Upgrading pip...
"%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1

:: Fast path for Update/Move: skip heavy AI downloads if already installed
if "%WIPE_MODE%"=="0" goto :FAST_INSTALL
if "%WIPE_MODE%"=="2" goto :FAST_INSTALL
goto :FULL_INSTALL

:FAST_INSTALL
if exist "%VENV_DIR%\Lib\site-packages\torch" if exist "%VENV_DIR%\Lib\site-packages\faster_whisper" (
    echo [INFO] AI libraries present. Quick upgrade only...
    "%VENV_PIP%" install --upgrade faster-whisper stable-ts pypdf 2>&1 | findstr /v "already satisfied"
    goto :SKIP_AI
)

:FULL_INSTALL
echo [INFO] Installing AI libraries...
if "%GPU_MODE%"=="1" (
    echo [INFO] Mode: NVIDIA GPU (CUDA 12)
    "%VENV_PIP%" install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
    "%VENV_PIP%" install faster-whisper stable-ts pypdf --extra-index-url https://download.pytorch.org/whl/cu121
) else (
    echo [INFO] Mode: CPU only
    "%VENV_PIP%" install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    "%VENV_PIP%" install faster-whisper stable-ts pypdf
)
if !errorlevel! neq 0 ( echo [ERROR] AI library install failed. & pause & exit /b 1 )

:SKIP_AI

echo [INFO] Checking PySide6...
"%VENV_PYTHON%" -c "import PySide6" >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARN] PySide6 not found. Installing...
    "%VENV_PIP%" install PySide6
    if !errorlevel! neq 0 ( echo [ERROR] PySide6 install failed. & pause & exit /b 1 )
) else (
    echo [INFO] PySide6 already installed.
)

:: ==========================================
:: 4. FFMPEG
:: ==========================================
if "%WIPE_MODE%"=="0" (
    if exist "%BIN_DIR%\ffmpeg.exe" (
        echo [INFO] FFmpeg present. Skipping (Update mode).
        goto :SKIP_FFMPEG
    )
)
if "%WIPE_MODE%"=="2" (
    if exist "%BIN_DIR%\ffmpeg.exe" (
        echo [INFO] FFmpeg present. Skipping (Move mode).
        goto :SKIP_FFMPEG
    )
)
if not exist "%FFMPEG_ZIP%" goto :SKIP_FFMPEG

echo [INFO] Extracting FFmpeg...
powershell -NoProfile -Command "Expand-Archive -Path \"%FFMPEG_ZIP%\" -DestinationPath \"%INSTALL_DIR%\ffmpeg_tmp\" -Force"
for /r "%INSTALL_DIR%\ffmpeg_tmp" %%F in (ffmpeg.exe, ffprobe.exe) do ( copy /y "%%F" "%BIN_DIR%\" >nul )
rmdir /s /q "%INSTALL_DIR%\ffmpeg_tmp" 2>nul
del /f /q "%FFMPEG_ZIP%" 2>nul
echo [INFO] FFmpeg installed.

:SKIP_FFMPEG

:: ==========================================
:: 5. LIBS JUNCTION
:: ==========================================
if exist "%INSTALL_DIR%\libs" ( rmdir "%INSTALL_DIR%\libs" >nul 2>&1 )
if exist "%VENV_DIR%\Lib\site-packages" (
    mklink /J "%INSTALL_DIR%\libs" "%VENV_DIR%\Lib\site-packages" >nul
    echo [INFO] libs junction created.
)

:: ==========================================
:: 6. DAVINCI RESOLVE WRAPPER
:: ==========================================
echo [INFO] Configuring DaVinci Resolve wrapper...
set "RESOLVE_DIR=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"

:: Microsoft Store edition detection
for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "RESOLVE_DIR=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
    )
)

if not exist "!RESOLVE_DIR!" mkdir "!RESOLVE_DIR!"
set "WRAPPER_FILE=!RESOLVE_DIR!\BadWords.py"

:: Generate wrapper using Python (avoids all batch escaping issues)
"%VENV_PYTHON%" -c "
import sys, os
install = r\"\"\"%INSTALL_DIR%\"\"\"
libs    = os.path.join(install, 'libs')
venv_l  = os.path.join(install, 'venv', 'Lib', 'site-packages')
main    = os.path.join(install, 'main.py')
target  = r\"\"\"%WRAPPER_FILE%\"\"\"

content = f'''import sys\nimport os\nimport traceback\n\nINSTALL_DIR = r\\\"\\\"\\\"{install}\\\"\\\"\\\"\nLIBS_DIR    = os.path.join(INSTALL_DIR, \"libs\")\nVENV_LIBS   = os.path.join(INSTALL_DIR, \"venv\", \"Lib\", \"site-packages\")\nMAIN_SCRIPT = os.path.join(INSTALL_DIR, \"main.py\")\n\nif os.path.exists(VENV_LIBS) and VENV_LIBS not in sys.path:\n    sys.path.insert(0, VENV_LIBS)\nif os.path.exists(LIBS_DIR) and LIBS_DIR not in sys.path:\n    sys.path.insert(0, LIBS_DIR)\nif INSTALL_DIR not in sys.path:\n    sys.path.append(INSTALL_DIR)\n\nif os.path.exists(MAIN_SCRIPT):\n    try:\n        with open(MAIN_SCRIPT, \"r\", encoding=\"utf-8\") as f:\n            code = f.read()\n        g = globals().copy()\n        g[\"__file__\"] = MAIN_SCRIPT\n        exec(code, g)\n    except Exception as e:\n        print(f\"Error executing BadWords: {e}\")\n        import traceback; traceback.print_exc()\nelse:\n    print(f\"CRITICAL: Script not found at {MAIN_SCRIPT}\")\n'''

os.makedirs(os.path.dirname(target), exist_ok=True)
with open(target, 'w', encoding='utf-8') as f:
    f.write(content)
print('[OK] Wrapper created:', target)
"

echo.
echo [SUCCESS] Configuration complete!
timeout /t 1 >nul
exit /b 0

:ERROR_ARGS
echo [ERROR] Missing INSTALL_DIR argument.
pause
exit /b 1