#!/bin/bash
set -e

# --- BADWORDS LINUX INSTALLER v9.6.3 (CUSTOM PATH & SMART VALIDATION) ---
# Copyright (c) 2026 Szymon Wolarz
#
# CHANGES v9.6.3:
# - Added Smart Path Detection & Validation: verified against main.py existence.
# - Delayed Warning: Path validation messages now appear after the header.
# - Custom Path Suffix: ensures custom paths always end with /BadWords folder.

PROCESS_NAME="Installation"

# --- TRAP: KEEP WINDOW OPEN ON EXIT ---
function finish {
    echo ""
    echo -e "${GREEN}${PROCESS_NAME} process finished.${NC}"
    read -p "Press Enter to close this window..."
}
trap finish EXIT

# --- COLORS ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD_RED='\033[1;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ==========================================
# 0. PATHS & VARIABLES
# ==========================================
APP_NAME="BadWords"
SOURCE_FOLDER_NAME="src" 
ASSETS_FOLDER_NAME="assets"
RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
WRAPPER_FILE="$RESOLVE_SCRIPT_DIR/BadWords.py"
LEGACY_WRAPPER_FILE="$RESOLVE_SCRIPT_DIR/BadWords (Linux).py"

# --- SMART PATH DETECTION & VALIDATION ---
DEFAULT_INSTALL_DIR="$HOME/.local/share/$APP_NAME"
INSTALL_DIR_BASH="$DEFAULT_INSTALL_DIR"
DETECTION_MSG=""

CHECK_WRAPPER=""
if [ -f "$WRAPPER_FILE" ]; then
    CHECK_WRAPPER="$WRAPPER_FILE"
elif [ -f "$LEGACY_WRAPPER_FILE" ]; then
    CHECK_WRAPPER="$LEGACY_WRAPPER_FILE"
fi

if [ -n "$CHECK_WRAPPER" ]; then
    DETECTED_PATH=$(grep -E "^INSTALL_DIR\s*=\s*" "$CHECK_WRAPPER" | head -n 1 | sed -E "s/^INSTALL_DIR\s*=\s*r?['\"](.*)['\"]/\1/")
    
    # Walidacja: ścieżka musi istnieć i posiadać main.py
    if [ -n "$DETECTED_PATH" ] && [ -d "$DETECTED_PATH" ] && [ -f "$DETECTED_PATH/main.py" ]; then
        INSTALL_DIR_BASH="$DETECTED_PATH"
        DETECTION_MSG="${GREEN}[INFO] Valid installation detected at: $INSTALL_DIR_BASH${NC}"
    else
        INSTALL_DIR_BASH="$DEFAULT_INSTALL_DIR"
        if [ -n "$DETECTED_PATH" ]; then
            DETECTION_MSG="${YELLOW}[WARN] Wrapper points to an invalid location ($DETECTED_PATH). Using default path.${NC}"
        fi
    fi
fi

# Pamiętamy starą ścieżkę do celów sprzątania
OLD_INSTALL_DIR="$INSTALL_DIR_BASH"

# Zmienne zależne (początkowe)
VENV_DIR="$INSTALL_DIR_BASH/venv"
LIBS_LINK="$INSTALL_DIR_BASH/libs"
MODELS_DIR="$INSTALL_DIR_BASH/models"
BIN_DIR="$INSTALL_DIR_BASH/bin"
LOG_FILE="$INSTALL_DIR_BASH/badwords_debug.log"

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}                   BadWords - PORTABLE INSTALLER (Linux)                        ${NC}"
echo -e "${BLUE}================================================================================${NC}"

# Wyświetlamy informację o wykrytej ścieżce po nagłówku, a nie przed nim
if [ -n "$DETECTION_MSG" ]; then
    echo -e "$DETECTION_MSG"
fi

# ==========================================
# 1. MAIN MENU: INSTALLATION MODE SELECTION
# ==========================================
echo -e "\n${YELLOW}What would you like to do?${NC}"
echo -e "${GREEN}1) Standard Install/Update: Install or update the app. Keep your settings and models.${NC}"
echo -e "${CYAN}2) Repair Installation: Fix bugs by replacing core files. Keep your settings and models.${NC}"
echo -e "${BLUE}3) Move Installation: Change the BadWords installation folder (Moves all files).${NC}"
echo -e "${RED}4) Complete Reset: Delete absolutely EVERYTHING and install from scratch.${NC}"
echo -e "${BOLD_RED}5) Uninstall: Remove BadWords completely from this system.${NC}"
echo ""
read -p "Select [1-5]: " WIPE_CHOICE

if [ -z "$WIPE_CHOICE" ]; then WIPE_CHOICE="1"; fi

case "$WIPE_CHOICE" in
    1) MODE_INSTALL="Update" ;;
    2) MODE_INSTALL="Clean Install" ;;
    3) MODE_INSTALL="Move Installation" ;;
    4) MODE_INSTALL="Full Wipe" ;;
    5) MODE_INSTALL="Uninstall" ;;
    *) echo -e "${RED}[ERROR] Invalid choice. Exiting.${NC}"; exit 1 ;;
esac

echo -e "${YELLOW}[INFO] Selected Action: $MODE_INSTALL${NC}"

# ==========================================
# 1.5 CUSTOM INSTALLATION PATH PROMPT
# ==========================================
# Pytamy o ścieżkę tylko przy pełnym wipe, przenoszeniu LUB gdy to pierwsza instalacja
if [ "$WIPE_CHOICE" -eq 4 ] || [ "$WIPE_CHOICE" -eq 3 ] || [ ! -d "$OLD_INSTALL_DIR" ]; then
    if [ "$WIPE_CHOICE" -ne 5 ]; then
        echo -e "\n${YELLOW}========================== PATH CONFIGURATION ==========================${NC}"
        if [ "$WIPE_CHOICE" -eq 3 ]; then
            echo -e "${GREEN}Current Path: $OLD_INSTALL_DIR${NC}"
            echo -e "${CYAN}Type a NEW absolute path to move BadWords to (e.g. ~/Documents)${NC}"
        else
            echo -e "\n${YELLOW}You can choose where to install BadWords${NC}"
            echo -e "${GREEN}Default/Current Path: $OLD_INSTALL_DIR${NC}"
            echo -e "${CYAN}Press [ENTER] to use this path, or type a custom absolute path (e.g. ~/Documents)${NC}"
        fi
        
        read -p "Path: " CUSTOM_PATH

        if [ -n "$CUSTOM_PATH" ]; then
            # Podmiana tyldy (~) na zmienną domową
            CUSTOM_PATH="${CUSTOM_PATH/#\~/$HOME}"
            
            # Zabezpieczenie przed "luźnym" wypakowaniem plików (Suffix Protection)
            if [[ "$CUSTOM_PATH" != *"/$APP_NAME" ]] && [[ "$CUSTOM_PATH" != *"/$APP_NAME/" ]]; then
                # Usuwamy ewentualny ukośnik na końcu i doklejamy folder BadWords
                CUSTOM_PATH="${CUSTOM_PATH%/}/$APP_NAME"
            fi
            
            if [ "$WIPE_CHOICE" -eq 3 ] && [ "$CUSTOM_PATH" == "$OLD_INSTALL_DIR" ]; then
                echo -e "${RED}[ERROR] New path is identical to the current one! Exiting.${NC}"
                exit 1
            fi
            
            INSTALL_DIR_BASH="$CUSTOM_PATH"
            echo -e "${GREEN}[INFO] Target path set to: $INSTALL_DIR_BASH${NC}"
            
            if [ "$WIPE_CHOICE" -eq 3 ] && [ -d "$OLD_INSTALL_DIR" ]; then
                echo -e "\n${YELLOW}[MOVE] Moving files from $OLD_INSTALL_DIR to $INSTALL_DIR_BASH...${NC}"
                mkdir -p "$(dirname "$INSTALL_DIR_BASH")"
                mv "$OLD_INSTALL_DIR" "$INSTALL_DIR_BASH"
                # Wymuś odświeżenie paczek pythona i venv przy zmianie ścieżki (Move traktowany jako Repair)
                WIPE_CHOICE=2 
                echo -e "${GREEN}[OK] Files automatically moved. Initiating fast re-link...${NC}"
            fi
            
            # Re-kalkulacja zmiennych zależnych na nową ścieżkę
            VENV_DIR="$INSTALL_DIR_BASH/venv"
            LIBS_LINK="$INSTALL_DIR_BASH/libs"
            MODELS_DIR="$INSTALL_DIR_BASH/models"
            BIN_DIR="$INSTALL_DIR_BASH/bin"
            LOG_FILE="$INSTALL_DIR_BASH/badwords_debug.log"
            OLD_INSTALL_DIR="$INSTALL_DIR_BASH"
        elif [ "$WIPE_CHOICE" -eq 3 ]; then
            echo -e "${RED}[ERROR] Path cannot be empty for moving! Exiting.${NC}"
            exit 1
        fi
    fi
else
    if [ "$WIPE_CHOICE" -ne 5 ]; then
        echo -e "${GREEN}[INFO] Using detected path: $OLD_INSTALL_DIR${NC}"
    fi
fi

# ==========================================
# 2. UNINSTALL HANDLER (EXECUTE & EXIT)
# ==========================================
if [ "$WIPE_CHOICE" -eq 5 ]; then
    PROCESS_NAME="Deinstallation"
    
    echo -e "\n${BOLD_RED}WARNING: You are about to completely remove BadWords from this system.${NC}"
    read -p "Type 'yes' to confirm uninstallation: " UNINSTALL_CONFIRM
    
    if [ "$UNINSTALL_CONFIRM" != "yes" ]; then
        echo -e "${YELLOW}[INFO] Uninstall cancelled by user.${NC}"
        exit 0
    fi

    echo -e "\n${RED}[UNINSTALL] Removing BadWords...${NC}"
    if [ -d "$OLD_INSTALL_DIR" ]; then
        rm -rf "$OLD_INSTALL_DIR"
        echo -e " - Removed app directory: $OLD_INSTALL_DIR"
    fi
    
    if [ -f "$WRAPPER_FILE" ]; then
        rm "$WRAPPER_FILE"
        echo -e " - Removed wrapper from DaVinci Resolve."
    fi
    # Czyszczenie legacy nazwy z Linuxa:
    if [ -f "$RESOLVE_SCRIPT_DIR/BadWords (Linux).py" ]; then
        rm "$RESOLVE_SCRIPT_DIR/BadWords (Linux).py"
        echo -e " - Removed legacy wrapper (BadWords (Linux).py)."
    fi
    
    echo -e "${RED}[UNINSTALL] Complete. BadWords has been removed.${NC}"
    exit 0
fi

# ==========================================
# 3. SOURCE FETCH (Local vs Web)
# ==========================================
REPO_ZIP_URL="https://gitlab.com/badwords/BadWords/-/archive/main/BadWords-main.zip"
# Zamiast hardcodowanego main, użyjemy API GitLaba do pobrania tagu najnowszego release.
# Fallback do 'main' jeśli API nie zadziała.
#LATEST_TAG=$(curl -s "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases" | python3 -c 'import json, sys; data=json.load(sys.stdin); print(data[0]["tag_name"] if isinstance(data, list) and len(data)>0 else "main")' 2>/dev/null || echo "main")
#REPO_ZIP_URL="https://gitlab.com/badwords/BadWords/-/archive/${LATEST_TAG}/BadWords-${LATEST_TAG}.zip"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOCAL_SRC="$DIR/$SOURCE_FOLDER_NAME"
LOCAL_ASSETS="$DIR/$ASSETS_FOLDER_NAME"

if [ -d "$LOCAL_SRC" ] && [ -f "$LOCAL_SRC/main.py" ]; then
    echo -e "${GREEN}[OK] Local source files detected. Installing from local files.${NC}"
    SOURCE_PATH="$LOCAL_SRC"
    ASSETS_PATH="$LOCAL_ASSETS"
else
    echo -e "${YELLOW}[INFO] Local source not found (Running via curl one-liner).${NC}"
    echo -e "${CYAN}[DOWNLOADING] Fetching latest source code from GitLab...${NC}"
    
    TMP_DL_DIR=$(mktemp -d)
    ZIP_PATH="$TMP_DL_DIR/repo.zip"
    
    # Próbujemy curl lub wget
    if command -v curl &> /dev/null; then
        curl -fsSL "$REPO_ZIP_URL" -o "$ZIP_PATH"
    elif command -v wget &> /dev/null; then
        wget -qO "$ZIP_PATH" "$REPO_ZIP_URL"
    else
        echo -e "${RED}[ERROR] 'curl' or 'wget' is required to download source.${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}[EXTRACTING] Unpacking source...${NC}"
    # Używamy unzip jeśli istnieje, inaczej modułu zipfile pythona3
    if command -v unzip &> /dev/null; then
        unzip -q -o "$ZIP_PATH" -d "$TMP_DL_DIR"
    else
        python3 -m zipfile -e "$ZIP_PATH" "$TMP_DL_DIR"
    fi
    
    EXTRACTED_DIR=$(find "$TMP_DL_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    
    if [ -d "$EXTRACTED_DIR/$SOURCE_FOLDER_NAME" ]; then
        SOURCE_PATH="$EXTRACTED_DIR/$SOURCE_FOLDER_NAME"
        ASSETS_PATH="$EXTRACTED_DIR/$ASSETS_FOLDER_NAME"
        echo -e "${GREEN}[OK] Download and extraction complete.${NC}"
    else
        echo -e "${RED}[ERROR] Failed to extract source properly. Check repository URL.${NC}"
        exit 1
    fi
fi

if [ ! -f "$SOURCE_PATH/main.py" ]; then
    echo -e "${RED}[ERROR] Missing 'main.py' in '$SOURCE_PATH'!${NC}"
    exit 1
fi

# ==========================================
# 4. GPU ACCELERATION MODE SELECTION (AUTO-DETECT)
# ==========================================
NVIDIA_PACKAGES=""
MODE_NAME=""

echo -e "\n${YELLOW}============================= AI ENGINE SETUP =============================${NC}"
echo -e "${YELLOW}[INFO] Detecting system hardware for AI acceleration...${NC}"

# Auto-detect Nvidia GPU presence
HAS_NVIDIA=0
if command -v lspci &> /dev/null && lspci | grep -i nvidia &> /dev/null; then
    HAS_NVIDIA=1
elif command -v lshw &> /dev/null && sudo lshw -C display 2>/dev/null | grep -i nvidia &> /dev/null; then
    HAS_NVIDIA=1
fi

if [ "$HAS_NVIDIA" -eq 1 ]; then
    MODE_NAME="NVIDIA (CUDA 12)"
    NVIDIA_PACKAGES="nvidia-cublas-cu12 nvidia-cudnn-cu12"
    echo -e "${GREEN}[OK] NVIDIA GPU detected. Selected Mode: $MODE_NAME${NC}"
else
    MODE_NAME="CPU (AMD/Intel)"
    NVIDIA_PACKAGES=""
    echo -e "${CYAN}[OK] No NVIDIA GPU detected. Selected Mode: $MODE_NAME${NC}"
fi

# ==========================================
# 5. SMART PYTHON SELECTION (COMPATIBILITY)
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
# 6. IN-PLACE CLEANUP (Using OLD_INSTALL_DIR)
# ==========================================
OLD_WHISPER_CACHE="$HOME/.cache/whisper"
echo -e "\n${RED}[CLEANUP] Processing old installation...${NC}"

if [ -d "$OLD_INSTALL_DIR" ]; then
    if [ "$WIPE_CHOICE" -eq 3 ]; then
        echo -e " - FULL WIPE selected. Backing up user data before deletion..."
        # Temporarily preserve user data files
        BW_TMP_BACKUP=$(mktemp -d)
        for f in user.json settings.json pref.json; do
            [ -f "$OLD_INSTALL_DIR/$f" ] && cp "$OLD_INSTALL_DIR/$f" "$BW_TMP_BACKUP/" && echo -e "   * Backed up: $f"
        done
        rm -rf "$OLD_INSTALL_DIR"
        mkdir -p "$INSTALL_DIR_BASH"
        # Restore preserved files
        for f in user.json settings.json pref.json; do
            [ -f "$BW_TMP_BACKUP/$f" ] && cp "$BW_TMP_BACKUP/$f" "$INSTALL_DIR_BASH/" && echo -e "   * Restored: $f"
        done
        rm -rf "$BW_TMP_BACKUP"
    elif [ "$WIPE_CHOICE" -eq 2 ]; then
        echo -e " - CLEAN INSTALL selected. Wiping environment in $OLD_INSTALL_DIR..."
        # Deletes everything EXCEPT the specified folders and user data files
        find "$OLD_INSTALL_DIR" -mindepth 1 -maxdepth 1 \
            ! -name "models" \
            ! -name "saves" \
            ! -name "pref.json" \
            ! -name "user.json" \
            ! -name "settings.json" \
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
# 7. APPLICATION SETUP (TRUE TWO-WAY SYNC)
# ==========================================
echo -e "\n${YELLOW}[INFO] Preparing directory structure...${NC}"
mkdir -p "$INSTALL_DIR_BASH"
mkdir -p "$MODELS_DIR" 
mkdir -p "$BIN_DIR"

if [ "$WIPE_CHOICE" -eq 1 ]; then
    echo -e "${CYAN}[UPDATE] Syncing files and removing obsolete scripts...${NC}"
    python3 -c "
import os, shutil, hashlib

def get_hash(filepath):
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

src_paths = ['$SOURCE_PATH', '$ASSETS_PATH']
dst = '$INSTALL_DIR_BASH'

# 1. Update/Add files from src to dst
for src in src_paths:
    if not os.path.exists(src):
        continue
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

# 2. Cleanup obsolete files from dst that are no longer in src
protected_files = ['pref.json', 'user.json', 'settings.json', 'badwords_debug.log', 'ffmpeg_static.tar.xz']
protected_dirs = ['models', 'saves', 'venv', 'bin', 'libs']

for item in os.listdir(dst):
    d_path = os.path.join(dst, item)
    exists_in_src = any(os.path.exists(os.path.join(s, item)) for s in src_paths)
    
    if os.path.isdir(d_path):
        if item not in protected_dirs and not exists_in_src:
            print(f' - Removing obsolete directory: {item}')
            shutil.rmtree(d_path)
    else:
        if item not in protected_files and not exists_in_src:
            print(f' - Removing obsolete file: {item}')
            os.remove(d_path)
"
else
    echo -e "${YELLOW}[INFO] Copying new source files...${NC}"
    cp -r "$SOURCE_PATH/"* "$INSTALL_DIR_BASH/"
    if [ -d "$ASSETS_PATH" ]; then cp -r "$ASSETS_PATH/"* "$INSTALL_DIR_BASH/"; fi
fi

# ==========================================
# 8. PORTABLE FFMPEG (STATIC BUILD)
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
# 9. VENV CREATION
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
# 10. VENV INSTALLATION
# ==========================================
echo -e "\n${CYAN}[INSTALL] Installing libraries into VENV...${NC}"
VENV_PIP="$VENV_DIR/bin/pip"

# Upgrade pip inside venv
"$VENV_PIP" install --upgrade pip >/dev/null 2>&1

# Install dependencies based on selection
if [ "$WIPE_CHOICE" -eq 1 ] && "$VENV_PIP" show torch >/dev/null 2>&1; then
    # UPDATE + torch already installed: skip heavy PyTorch downloads
    echo -e "${GREEN}[INFO] AI libraries already installed. Skipping heavy PyTorch downloads...${NC}"
    "$VENV_PIP" install --upgrade faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
elif [ -z "$NVIDIA_PACKAGES" ]; then
    # CPU OPTIMIZATION LOGIC
    echo -e "${CYAN}[INSTALL] Downloading CPU-optimized PyTorch to save disk space...${NC}"
    "$VENV_PIP" install torch torchaudio --index-url https://download.pytorch.org/whl/cpu || { echo -e "${RED}[ERROR] PyTorch Install failed.${NC}"; exit 1; }
    echo -e "${CYAN}[INSTALL] Installing Faster-Whisper + Stable-TS (CPU Mode)...${NC}"
    "$VENV_PIP" install faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
else
    # NVIDIA CUDA LOGIC
    echo -e "${CYAN}[INSTALL] Installing Faster-Whisper + Stable-TS + $MODE_NAME Support...${NC}"
    "$VENV_PIP" install faster-whisper stable-ts pypdf $NVIDIA_PACKAGES || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
fi

echo -e "\n${CYAN}[INSTALL] Checking PySide6...${NC}"
if "$VENV_DIR/bin/python" -c "import PySide6" 2>/dev/null; then
    echo -e "${GREEN}[INFO] PySide6 is already installed. Skipping...${NC}"
else
    echo -e "${YELLOW}[WARN] PySide6 not found. Downloading this GUI library...${NC}"
    "$VENV_PIP" install PySide6 || { echo -e "${RED}[ERROR] PySide6 Install failed.${NC}"; exit 1; }
fi

echo -e "${GREEN}[SUCCESS] Dependencies installed in VENV.${NC}"

# ==========================================
# 11. SYMLINK TRICK
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
# 12. DAVINCI RESOLVE CONFIGURATION
# ==========================================
echo -e "\n${YELLOW}[INFO] Configuring DaVinci Resolve integration...${NC}"
if [ ! -d "$RESOLVE_SCRIPT_DIR" ]; then
    mkdir -p "$RESOLVE_SCRIPT_DIR"
fi
export WRAPPER_TARGET_DIR="$RESOLVE_SCRIPT_DIR"

if [ -f "$RESOLVE_SCRIPT_DIR/BadWords (Linux).py" ]; then
    rm "$RESOLVE_SCRIPT_DIR/BadWords (Linux).py"
    echo -e "${CYAN} - Removed legacy wrapper: BadWords (Linux).py${NC}"
fi

# ==========================================
# 13. WRAPPER GENERATION
# ==========================================
echo -e "${YELLOW}[INFO] Generating wrapper script...${NC}"

python3 -c "
import os
import sys
import stat

APP_NAME = \"$APP_NAME\"
WRAPPER_NAME = \"BadWords.py\"

INSTALL_DIR = r\"$INSTALL_DIR_BASH\"
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

# 14. LOG PREPARATION
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
echo -e "${GREEN}          PATH: $INSTALL_DIR_BASH${NC}"
echo -e "${GREEN}          LOGS: $LOG_FILE${NC}"
echo ""
echo -e "${GREEN}================================================================================${NC}"

chmod +x "$RESOLVE_SCRIPT_DIR"