@echo off
setlocal EnableDelayedExpansion

echo [UPDATE] BadWords Windows Auto-Update starting...

:: Locate installation via wrapper
set "WRAPPER_FILE=%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"

for /d %%D in ("%LOCALAPPDATA%\Packages\BlackmagicDesign.DaVinciResolve_*") do (
    if exist "%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve" (
        set "WRAPPER_FILE=%%D\LocalState\AppDataRoaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\BadWords.py"
    )
)

set "INSTALL_DIR="
if exist "!WRAPPER_FILE!" (
    for /f "tokens=*" %%L in ('findstr /r "^INSTALL_DIR" "!WRAPPER_FILE!" 2^>nul') do (
        set "LINE=%%L"
        for /f "tokens=2 delims=""" %%P in ("!LINE!") do (
            if "!INSTALL_DIR!"=="" set "INSTALL_DIR=%%P"
        )
    )
)

if not defined INSTALL_DIR (
    if exist "%LOCALAPPDATA%\BadWords\main.py" (
        set "INSTALL_DIR=%LOCALAPPDATA%\BadWords"
    ) else if exist "%USERPROFILE%\BadWords\main.py" (
        set "INSTALL_DIR=%USERPROFILE%\BadWords"
    ) else (
        set "INSTALL_DIR=%LOCALAPPDATA%\BadWords"
    )
)

echo [INFO] Detected installation path: !INSTALL_DIR!

:: Download latest BadWords setup executable
set "TMP_DIR=%TEMP%\bw_installer_update_%RANDOM%"
mkdir "!TMP_DIR!" 2>nul
set "SETUP_EXE=!TMP_DIR!\badwords-setup-windows.exe"

set "URL=https://github.com/veritus-git/BadWords/releases/latest/download/badwords-setup-windows.exe"
echo [INFO] Downloading native installer: !URL!

where curl >nul 2>&1
if !errorlevel! equ 0 (
    curl -fsSL "!URL!" -o "!SETUP_EXE!"
) else (
    powershell -NoProfile -Command "Invoke-WebRequest -Uri '!URL!' -OutFile '!SETUP_EXE!'"
)

if not exist "!SETUP_EXE!" (
    echo [ERROR] Could not download native installer from GitHub.
    rmdir /s /q "!TMP_DIR!" 2>nul
    exit /b 1
)

echo [INFO] Running native BadWords installer in headless mode...
"!SETUP_EXE!" --headless --install "!INSTALL_DIR!"
set "EXIT_CODE=!errorlevel!"

rmdir /s /q "!TMP_DIR!" 2>nul

if !EXIT_CODE! equ 0 (
    echo [UPDATE] BadWords successfully updated to v4!
    echo [UPDATE] Please restart BadWords from DaVinci Resolve or Desktop shortcut.
) else (
    echo [ERROR] Headless installer exited with error code !EXIT_CODE!
)

exit /b !EXIT_CODE!
