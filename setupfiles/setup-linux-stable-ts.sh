#!/bin/bash
set -e

# --- BADWORDS LINUX INSTALLER v9.4 (TRUE ADDITIVE UPDATE) ---
# Copyright (c) 2026 Szymon Wolarz
#
# CHANGES v9.4:
# - True Additive Update: Recursively checks ALL folders and files. Creates missing dirs.
# - Clean Install: Strictly deletes everything except models, saves, pref.json.

# --- TRAP: ZATRZYMANIE OKNA NA KONIEC ---
function finish {
    echo ""
    echo -e "${GREEN}Installation process finished.${NC}"
    read -p "Press Enter to close this window..."
}
trap finish EXIT

# --- COLORS ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

APP_NAME="BadWords"
SOURCE_FOLDER_NAME="src" 

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}                   BadWords - PORTABLE INSTALLER (Linux)                        ${NC}"
echo -e "${BLUE}================================================================================${NC}"

# 1. WERYFIKACJA ŹRÓDŁA
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_PATH="$DIR/$SOURCE_FOLDER_NAME"

if [ ! -d "$SOURCE_PATH" ]; then
    echo -e "${RED}[ERROR] Folder '$SOURCE_FOLDER_NAME' not found in '$DIR'!${NC}"
    exit 1
fi

if [ ! -f "$SOURCE_PATH/main.py" ]; then
    echo -e "${RED}[ERROR] Missing 'main.py' in '$SOURCE_FOLDER_NAME'!${NC}"
    exit 1
fi

# ==========================================
# 2. WYBÓR TRYBU AKCELERACJI GPU
# ==========================================

echo -e "\n${YELLOW}============================= AI ENGINE SETUP =============================${NC}"
echo -e "${YELLOW}[CONFIG] Please select your hardware acceleration mode:${NC}"
echo -e "${GREEN}1) NVIDIA: NVIDIA GPUs acceleration${NC}"
echo -e "${CYAN}2) OTHER:  AMD/Intel GPUs, or pure CPU processing${NC}"
echo ""
read -p "Select [1-2]: " GPU_CHOICE

if [ -z "$GPU_CHOICE" ]; then GPU_CHOICE="1"; fi

NVIDIA_PACKAGES=""
MODE_NAME=""

case "$GPU_CHOICE" in
    1)
        MODE_NAME="NVIDIA (CUDA 12)"
        NVIDIA_PACKAGES="nvidia-cublas-cu12 nvidia-cudnn-cu12"
        ;;
    2)
        MODE_NAME="CPU (AMD/Intel)"
        NVIDIA_PACKAGES=""
        ;;
    *)
        echo -e "${RED}[ERROR] Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo -e "${YELLOW}[INFO] Selected Mode: $MODE_NAME${NC}"

# ==========================================
# 2.5. WYBÓR TRYBU INSTALACJI
# ==========================================

echo -e "\n${YELLOW}=========================== INSTALLATION MODE ===========================${NC}"
echo -e "${YELLOW}What would you like to do?${NC}"
echo -e "${GREEN}1) Standard Install/Update: Install or update the app. Keep your settings and models.${NC}"
echo -e "${CYAN}2) Repair Installation: Fix bugs by replacing core files. Keep your settings and models.${NC}"
echo -e "${RED}3) Complete Reset: Delete absolutely EVERYTHING and install from scratch.${NC}"
echo ""
read -p "Select [1-3]: " WIPE_CHOICE

if [ -z "$WIPE_CHOICE" ]; then WIPE_CHOICE="1"; fi

case "$WIPE_CHOICE" in
    1) MODE_INSTALL="Update" ;;
    2) MODE_INSTALL="Clean Install" ;;
    3) MODE_INSTALL="Full Wipe" ;;
    *) echo -e "${RED}[ERROR] Invalid choice. Exiting.${NC}"; exit 1 ;;
esac

echo -e "${YELLOW}[INFO] Selected Install Mode: $MODE_INSTALL${NC}"

# ==========================================
# 3. SMART PYTHON SELECTION (KOMPATYBILNOŚĆ)
# ==========================================
echo -e "\n${YELLOW}[INFO] Checking Python compatibility...${NC}"

# Get system python version
SYS_PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
SYS_PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

TARGET_PYTHON="python3"
NEED_INSTALL_PY=0

echo -e "System Python: $SYS_PY_MAJOR.$SYS_PY_MINOR"

if [ "$SYS_PY_MAJOR" -eq 3 ] && [ "$SYS_PY_MINOR" -ge 13 ]; then
    echo -e "${RED}[WARN] System Python ($SYS_PY_MAJOR.$SYS_PY_MINOR) is very new. Dependencies might break.${NC}"
    echo -e "${CYAN}[SEARCH] Looking for safe alternatives (3.10 - 3.12)...${NC}"
    
    FOUND_ALT=0
    for ver in "3.12" "3.11" "3.10"; do
        if command -v "python$ver" &> /dev/null; then
            TARGET_PYTHON="python$ver"
            echo -e "${GREEN}[OK] Found compatible alternative: $TARGET_PYTHON${NC}"
            FOUND_ALT=1
            break
        fi
    done
    
    if [ "$FOUND_ALT" -eq 0 ]; then
        echo -e "${YELLOW}[ACTION] Compatible Python not found.${NC}"
        echo -e "Do you want to install Python 3.12 SIDE-BY-SIDE? (Safe, won't replace system python)"
        read -p "[Y/n]: " INSTALL_CHOICE
        INSTALL_CHOICE=${INSTALL_CHOICE:-Y}
        
        if [[ "$INSTALL_CHOICE" =~ ^[Yy]$ ]]; then
            NEED_INSTALL_PY=1
            TARGET_PYTHON="python3.12"
        else
            echo -e "${RED}[WARN] Proceeding with Python $SYS_PY_MAJOR.$SYS_PY_MINOR. Installation may fail.${NC}"
        fi
    fi
else
    echo -e "${GREEN}[OK] System Python is compatible.${NC}"
fi

# Install Python if needed
if [ "$NEED_INSTALL_PY" -eq 1 ]; then
    echo -e "${CYAN}[INSTALL] Installing Python 3.12 and venv...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq || true
        sudo apt-get install -y python3.12 python3.12-venv python3.12-dev || {
            echo -e "${RED}[ERROR] Failed to install Python 3.12. Try manually.${NC}"
            exit 1
        }
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3.12 || true
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm python312 || true
    fi
fi

echo -e "${GREEN}[INFO] Using Python interpreter: $TARGET_PYTHON${NC}"

# ==========================================
# 4. ŚCIEŻKI
# ==========================================
INSTALL_DIR_BASH="$HOME/.local/share/$APP_NAME"
VENV_DIR="$INSTALL_DIR_BASH/venv"
LIBS_LINK="$INSTALL_DIR_BASH/libs"
MODELS_DIR="$INSTALL_DIR_BASH/models"
BIN_DIR="$INSTALL_DIR_BASH/bin"
LOG_FILE="$INSTALL_DIR_BASH/badwords_debug.log"
OLD_WHISPER_CACHE="$HOME/.cache/whisper"

# ==========================================
# 5. IN-PLACE CLEANUP (Zamiast backupów)
# ==========================================
echo -e "\n${RED}[CLEANUP] Processing old installation...${NC}"

if [ -d "$INSTALL_DIR_BASH" ]; then
    if [ "$WIPE_CHOICE" -eq 3 ]; then
        echo -e " - FULL WIPE selected. Deleting entire directory..."
        rm -rf "$INSTALL_DIR_BASH"
    elif [ "$WIPE_CHOICE" -eq 2 ]; then
        echo -e " - CLEAN INSTALL selected. Wiping environment (keeping models, saves, prefs)..."
        # Usuwa wszystko OPRÓCZ wskazanych
        find "$INSTALL_DIR_BASH" -mindepth 1 -maxdepth 1 \
            ! -name "models" \
            ! -name "saves" \
            ! -name "pref.json" \
            -exec rm -rf {} +
    else
        echo -e " - UPDATE selected. No preliminary cleanup required (Additive Mode)."
    fi
fi

if [ -d "$OLD_WHISPER_CACHE" ]; then
    rm -rf "$OLD_WHISPER_CACHE"
fi

echo -e "${GREEN}[CLEANUP] Complete.${NC}"

# ==========================================
# 6. SETUP APLIKACJI
# ==========================================
echo -e "\n${YELLOW}[INFO] Preparing directory structure...${NC}"
mkdir -p "$INSTALL_DIR_BASH"
mkdir -p "$MODELS_DIR" 
mkdir -p "$BIN_DIR"

if [ "$WIPE_CHOICE" -eq 1 ]; then
    echo -e "${CYAN}[UPDATE] Recursively updating files and creating missing folders...${NC}"
    python3 -c "
import os, shutil, hashlib

def get_hash(filepath):
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

src = '$SOURCE_PATH'
dst = '$INSTALL_DIR_BASH'

for root, dirs, files in os.walk(src):
    rel_path = os.path.relpath(root, src)
    if rel_path == '.':
        dst_dir = dst
    else:
        dst_dir = os.path.join(dst, rel_path)
        
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
        print(f' - Created directory: {rel_path}')

    for file in files:
        s_path = os.path.join(root, file)
        d_path = os.path.join(dst_dir, file)
        
        s_hash = get_hash(s_path)
        d_hash = get_hash(d_path) if os.path.exists(d_path) else None
        
        rel_file = os.path.join(rel_path, file) if rel_path != '.' else file
        if s_hash != d_hash:
            print(f' - Updating/Adding: {rel_file}')
            shutil.copy2(s_path, d_path)
        else:
            print(f' - Skipped (identical): {rel_file}')
"
else
    echo -e "${YELLOW}[INFO] Copying new source files...${NC}"
    cp -r "$SOURCE_PATH/"* "$INSTALL_DIR_BASH/"
fi

# ==========================================
# 7. PORTABLE FFMPEG (STATIC BUILD)
# ==========================================
if [ "$WIPE_CHOICE" -eq 1 ] && [ -f "$BIN_DIR/ffmpeg" ]; then
    echo -e "\n${GREEN}[OK] Portable FFmpeg already exists (Update mode). Skipping download.${NC}"
else
    echo -e "\n${YELLOW}[FFMPEG] Installing Portable Static FFmpeg...${NC}"

    FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    FFMPEG_ARCHIVE="$INSTALL_DIR_BASH/ffmpeg_static.tar.xz"

    echo -e "${CYAN}[DOWNLOADING] $FFMPEG_URL${NC}"
    if command -v curl &> /dev/null; then
        curl -L "$FFMPEG_URL" -o "$FFMPEG_ARCHIVE"
    elif command -v wget &> /dev/null; then
        wget -O "$FFMPEG_ARCHIVE" "$FFMPEG_URL"
    else
        echo -e "${RED}[ERROR] curl or wget needed to download FFmpeg.${NC}"
        exit 1
    fi

    echo -e "${CYAN}[EXTRACTING] Unpacking FFmpeg...${NC}"
    tar -xf "$FFMPEG_ARCHIVE" -C "$INSTALL_DIR_BASH"
    find "$INSTALL_DIR_BASH" -name "ffmpeg" -type f -exec mv {} "$BIN_DIR/" \;
    find "$INSTALL_DIR_BASH" -name "ffprobe" -type f -exec mv {} "$BIN_DIR/" \;

    rm "$FFMPEG_ARCHIVE"
    find "$INSTALL_DIR_BASH" -type d -name "ffmpeg-*-static" -exec rm -rf {} +

    chmod +x "$BIN_DIR/ffmpeg"
    chmod +x "$BIN_DIR/ffprobe"

    if [ -f "$BIN_DIR/ffmpeg" ]; then
        echo -e "${GREEN}[OK] Portable FFmpeg installed in $BIN_DIR${NC}"
    else
        echo -e "${RED}[ERROR] Failed to install FFmpeg.${NC}"
        exit 1
    fi
fi

# ==========================================
# 8. TWORZENIE VENV
# ==========================================
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${CYAN}[VENV] Creating isolated Virtual Environment ($TARGET_PYTHON)...${NC}"
    $TARGET_PYTHON -m venv "$VENV_DIR" || {
        echo -e "${RED}[ERROR] Failed to create venv. Ensure venv is installed.${NC}"
        exit 1
    }
else
    echo -e "\n${GREEN}[VENV] Virtual Environment already exists. Skipping creation.${NC}"
fi

# ==========================================
# 9. INSTALACJA W VENV
# ==========================================
echo -e "\n${CYAN}[INSTALL] Installing libraries into VENV...${NC}"
VENV_PIP="$VENV_DIR/bin/pip"

# Upgrade pip inside venv
"$VENV_PIP" install --upgrade pip

# Install dependencies based on selection
if [ -z "$NVIDIA_PACKAGES" ]; then
    if [ "$WIPE_CHOICE" -eq 1 ]; then
        echo -e "${CYAN}[INSTALL] Upgrading Faster-Whisper + Stable-TS (CPU Mode)...${NC}"
        "$VENV_PIP" install --upgrade faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
    else
        echo -e "${CYAN}[INSTALL] Installing Faster-Whisper + Stable-TS (CPU Mode)...${NC}"
        "$VENV_PIP" install faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
    fi
else
    if [ "$WIPE_CHOICE" -eq 1 ]; then
        echo -e "${CYAN}[INSTALL] Upgrading Faster-Whisper + Stable-TS + $MODE_NAME Support...${NC}"
        "$VENV_PIP" install --upgrade faster-whisper stable-ts pypdf $NVIDIA_PACKAGES || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
    else
        echo -e "${CYAN}[INSTALL] Installing Faster-Whisper + Stable-TS + $MODE_NAME Support...${NC}"
        "$VENV_PIP" install faster-whisper stable-ts pypdf $NVIDIA_PACKAGES || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
    fi
fi

echo -e "${GREEN}[SUCCESS] Dependencies installed in VENV.${NC}"

# ==========================================
# 10. SYMLINK TRICK
# ==========================================
echo -e "\n${YELLOW}[LINKING] Creating 'libs' compatibility link...${NC}"
SITE_PACKAGES_DIR=$(find "$VENV_DIR/lib" -name "site-packages" -type d | head -n 1)

if [ -d "$SITE_PACKAGES_DIR" ]; then
    if [ -L "$LIBS_LINK" ]; then rm "$LIBS_LINK"; fi
    ln -s "$SITE_PACKAGES_DIR" "$LIBS_LINK"
    echo -e "${GREEN}[OK] Symlink '$LIBS_LINK' created.${NC}"
else
    echo -e "${RED}[ERROR] Could not locate site-packages in venv!${NC}"
    exit 1
fi

# ==========================================
# 11. KONFIGURACJA DAVINCI
# ==========================================
echo -e "\n${YELLOW}[INFO] Configuring DaVinci Resolve integration...${NC}"
RESOLVE_SCRIPT_DIR=""

if [ -d "/opt/resolve" ]; then
    RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
else
    RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
fi

mkdir -p "$RESOLVE_SCRIPT_DIR"
export WRAPPER_TARGET_DIR="$RESOLVE_SCRIPT_DIR"

# ==========================================
# 12. GENEROWANIE WRAPPERA
# ==========================================
echo -e "${YELLOW}[INFO] Generating wrapper script...${NC}"

python3 -c "
import os
import sys
import stat

APP_NAME = \"$APP_NAME\"
WRAPPER_NAME = \"BadWords (Linux).py\"

HOME = os.path.expanduser(\"~\")
INSTALL_DIR = os.path.join(HOME, \".local\", \"share\", APP_NAME)
LIBS_DIR = os.path.join(INSTALL_DIR, \"libs\")

RESOLVE_DIR = os.environ.get('WRAPPER_TARGET_DIR')
if not RESOLVE_DIR:
    RESOLVE_DIR = os.getcwd()

TARGET_FILE = os.path.join(RESOLVE_DIR, WRAPPER_NAME)

content = f\"\"\"import sys
import os
import traceback

INSTALL_DIR = r'{INSTALL_DIR}'
LIBS_DIR = r'{LIBS_DIR}'
MAIN_SCRIPT = os.path.join(INSTALL_DIR, 'main.py')

if os.path.exists(LIBS_DIR):
    if LIBS_DIR in sys.path:
        sys.path.remove(LIBS_DIR)
    sys.path.insert(0, LIBS_DIR)

if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, 'r', encoding='utf-8') as f:
            code = f.read()
        global_vars = globals().copy()
        global_vars['__file__'] = MAIN_SCRIPT
        exec(code, global_vars)
    except Exception as e:
        print(f'Error executing BadWords: {{e}}')
        traceback.print_exc()
else:
    print(f'CRITICAL: Script not found at {{MAIN_SCRIPT}}')
\"\"\"

try:
    with open(TARGET_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    st = os.stat(TARGET_FILE)
    os.chmod(TARGET_FILE, st.st_mode | stat.S_IEXEC)
    
    print(f\"[PYTHON] Wrapper created: {TARGET_FILE}\")
except Exception as e:
    print(f\"[ERROR] Wrapper creation failed: {e}\")
    sys.exit(1)
"

# 13. PRZYGOTOWANIE LOGÓW
echo -e "\n${YELLOW}[INFO] Initializing Log File...${NC}"
touch "$LOG_FILE"
chmod 666 "$LOG_FILE"
echo -e "${GREEN}[OK] Log file created at: $LOG_FILE${NC}"

echo ""
echo -e "${GREEN}================================================================================${NC}"
echo ""
echo -e "${GREEN}                            INSTALLATION SUCCESSFUL!${NC}"
echo -e "${GREEN}                     Find the script in Workspace -> Scripts${NC}"
echo ""
echo -e "${GREEN}          MODE: $MODE_NAME${NC}"
echo -e "${GREEN}          LOGS: $LOG_FILE${NC}"
echo ""
echo -e "${GREEN}================================================================================${NC}"

chmod +x "$RESOLVE_SCRIPT_DIR"