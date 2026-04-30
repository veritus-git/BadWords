#!/bin/bash
set -e

# --- BADWORDS macOS INSTALLER v9.6.3 (NATIVE BASH / NO QUARANTINE) ---
# Copyright (c) 2026 Szymon Wolarz
#
# MacOS Features:
# - Bypasses Gatekeeper completely via Terminal execution.
# - Leverages Homebrew for Python and FFmpeg to keep it clean.
# - Automatically utilizes Apple Silicon (MPS) via native PyTorch.

PROCESS_NAME="Installation"

# --- TRAP: KEEP WINDOW OPEN ON EXIT ---
function finish {
    echo ""
    echo -e "${GREEN}${PROCESS_NAME} process finished.${NC}"
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
LATEST_TAG=$(curl -s "https://api.github.com/repos/veritus-git/BadWords/releases/latest" | python3 -c 'import json, sys; data=json.load(sys.stdin); print(data.get("tag_name", ""))' 2>/dev/null)

if [ -n "$LATEST_TAG" ]; then
    REPO_ZIP_URL="https://github.com/veritus-git/BadWords/archive/refs/tags/${LATEST_TAG}.zip"
    SOURCE_REPO="GitHub"
else
    LATEST_TAG=$(curl -s "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases" | python3 -c 'import json, sys; data=json.load(sys.stdin); print(data[0]["tag_name"] if isinstance(data, list) and len(data)>0 else "main")' 2>/dev/null || echo "main")
    REPO_ZIP_URL="https://gitlab.com/badwords/BadWords/-/archive/${LATEST_TAG}/BadWords-${LATEST_TAG}.zip"
    SOURCE_REPO="GitLab"
fi

RESOLVE_SCRIPT_DIR="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility"
WRAPPER_FILE="$RESOLVE_SCRIPT_DIR/BadWords.py"

# --- SMART PATH DETECTION & VALIDATION ---
DEFAULT_INSTALL_DIR="$HOME/Library/Application Support/$APP_NAME"
INSTALL_DIR_BASH="$DEFAULT_INSTALL_DIR"
DETECTION_MSG=""

if [ -f "$WRAPPER_FILE" ]; then
    DETECTED_PATH=$(grep -E "^INSTALL_DIR\s*=\s*" "$WRAPPER_FILE" | head -n 1 | sed -E "s/^INSTALL_DIR\s*=\s*r?['\"](.*)['\"]/\1/")
    
    # Walidacja
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

OLD_INSTALL_DIR="$INSTALL_DIR_BASH"

# Zmienne zależne
VENV_DIR="$INSTALL_DIR_BASH/venv"
LIBS_LINK="$INSTALL_DIR_BASH/libs"
MODELS_DIR="$INSTALL_DIR_BASH/models"
LOG_FILE="$INSTALL_DIR_BASH/badwords_debug.log"

echo -e "${BLUE}================================================================================${NC}"
echo -e "${BLUE}                   BadWords - PORTABLE INSTALLER (macOS)                        ${NC}"
echo -e "${BLUE}================================================================================${NC}"

if [ -n "$DETECTION_MSG" ]; then
    echo -e "$DETECTION_MSG"
fi

# ==========================================
# 1. MAIN MENU: INSTALLATION MODE SELECTION
# ==========================================
echo -e "\n${YELLOW}What would you like to do?${NC}"
echo -e "${GREEN}1) Standard Install/Update: Install or update the app. Keep your settings and models.${NC}"
echo -e "${CYAN}2) Repair Installation: Fix bugs by replacing core files. Keep your settings and models.${NC}"
echo -e "${RED}3) Complete Reset: Delete absolutely EVERYTHING and install from scratch.${NC}"
echo -e "${BOLD_RED}4) Uninstall: Remove BadWords completely from this Mac.${NC}"
echo ""
read -p "Select [1-4]: " WIPE_CHOICE

if [ -z "$WIPE_CHOICE" ]; then WIPE_CHOICE="1"; fi

case "$WIPE_CHOICE" in
    1) MODE_INSTALL="Update" ;;
    2) MODE_INSTALL="Clean Install" ;;
    3) MODE_INSTALL="Full Wipe" ;;
    4) MODE_INSTALL="Uninstall" ;;
    *) echo -e "${RED}[ERROR] Invalid choice. Exiting.${NC}"; exit 1 ;;
esac

echo -e "${YELLOW}[INFO] Selected Action: $MODE_INSTALL${NC}"

# ==========================================
# 2. UNINSTALL HANDLER
# ==========================================
if [ "$WIPE_CHOICE" -eq 4 ]; then
    PROCESS_NAME="Deinstallation"
    
    echo -e "\n${BOLD_RED}WARNING: You are about to completely remove BadWords from your Mac.${NC}"
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
    
    echo -e "${RED}[UNINSTALL] Complete. BadWords has been removed.${NC}"
    exit 0
fi

# ==========================================
# 3. HOMEBREW & SYSTEM DEPENDENCIES
# ==========================================
echo -e "\n${YELLOW}[INFO] Checking macOS requirements...${NC}"

if ! command -v brew &> /dev/null; then
    echo -e "${BOLD_RED}[WARN] Homebrew is not installed!${NC}"
    echo -e "${YELLOW}Homebrew is required to install Python and FFmpeg safely on macOS.${NC}"
    read -p "Would you like to install Homebrew now? [Y/n]: " INSTALL_BREW
    INSTALL_BREW=${INSTALL_BREW:-Y}
    
    if [[ "$INSTALL_BREW" =~ ^[Yy]$ ]]; then
        echo -e "${CYAN}[INSTALL] Downloading and installing Homebrew...${NC}"
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Determine brew path to add to current session
        if [ -x "/opt/homebrew/bin/brew" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x "/usr/local/bin/brew" ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
        
        if ! command -v brew &> /dev/null; then
            echo -e "${RED}[ERROR] Homebrew installation failed or isn't in PATH. Please install it manually.${NC}"
            exit 1
        fi
    else
        echo -e "${RED}[ERROR] Cannot continue without Homebrew. Exiting.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[OK] Homebrew found.${NC}"
fi

echo -e "\n${CYAN}[INSTALL] Checking Python and FFmpeg via Homebrew...${NC}"
brew install python@3.11 ffmpeg

TARGET_PYTHON="python3.11"
# Ensure we map the target python correctly if needed
if ! command -v python3.11 &> /dev/null; then
    TARGET_PYTHON=$(brew --prefix)/opt/python@3.11/bin/python3.11
fi

echo -e "${GREEN}[INFO] Using Python interpreter: $TARGET_PYTHON${NC}"

# ==========================================
# 3.5 FFMPEG PORTABLE LINK (into bin/)
# ==========================================
# DaVinci Resolve launches as a GUI app and does NOT load ~/.zshrc or ~/.bash_profile.
# This means Homebrew's PATH is invisible to it. We solve this by symlinking the
# Homebrew ffmpeg binary into our own install_dir/bin/ folder, which osdoc.py
# always checks first (Portable mode priority).
echo -e "\n${YELLOW}[FFMPEG] Linking FFmpeg into portable bin/ folder...${NC}"
BIN_DIR_MAC="$INSTALL_DIR_BASH/bin"
mkdir -p "$BIN_DIR_MAC"

# Find where Homebrew installed ffmpeg
BREW_FFMPEG=$(brew --prefix ffmpeg)/bin/ffmpeg
BREW_FFPROBE=$(brew --prefix ffmpeg)/bin/ffprobe

if [ -f "$BREW_FFMPEG" ]; then
    ln -sf "$BREW_FFMPEG" "$BIN_DIR_MAC/ffmpeg"
    ln -sf "$BREW_FFPROBE" "$BIN_DIR_MAC/ffprobe"
    echo -e "${GREEN}[OK] FFmpeg symlinked: $BIN_DIR_MAC/ffmpeg -> $BREW_FFMPEG${NC}"
else
    echo -e "${RED}[WARN] Could not find Homebrew FFmpeg at $BREW_FFMPEG. Falling back to PATH.${NC}"
fi

# ==========================================
# 4. IN-PLACE CLEANUP
# ==========================================
OLD_WHISPER_CACHE="$HOME/.cache/whisper"
echo -e "\n${RED}[CLEANUP] Processing old installation...${NC}"

if [ -d "$OLD_INSTALL_DIR" ]; then
    if [ "$WIPE_CHOICE" -eq 3 ]; then
        echo -e " - FULL WIPE selected. Backing up user data before deletion..."
        BW_TMP_BACKUP=$(mktemp -d)
        for f in user.json settings.json pref.json; do
            [ -f "$OLD_INSTALL_DIR/$f" ] && cp "$OLD_INSTALL_DIR/$f" "$BW_TMP_BACKUP/" && echo -e "   * Backed up: $f"
        done
        rm -rf "$OLD_INSTALL_DIR"
        mkdir -p "$INSTALL_DIR_BASH"
        for f in user.json settings.json pref.json; do
            [ -f "$BW_TMP_BACKUP/$f" ] && cp "$BW_TMP_BACKUP/$f" "$INSTALL_DIR_BASH/" && echo -e "   * Restored: $f"
        done
        rm -rf "$BW_TMP_BACKUP"
    elif [ "$WIPE_CHOICE" -eq 2 ]; then
        echo -e " - CLEAN INSTALL selected. Wiping environment in $OLD_INSTALL_DIR..."
        find "$OLD_INSTALL_DIR" -mindepth 1 -maxdepth 1 \
            ! -name "models" \
            ! -name "saves" \
            ! -name "pref.json" \
            ! -name "user.json" \
            ! -name "settings.json" \
            -exec rm -rf {} +
    fi
fi

if [ -d "$OLD_WHISPER_CACHE" ]; then
    rm -rf "$OLD_WHISPER_CACHE"
fi

echo -e "${GREEN}[CLEANUP] Complete.${NC}"

# ==========================================
# 5. SOURCE FETCH (Local vs Web)
# ==========================================
mkdir -p "$INSTALL_DIR_BASH"
mkdir -p "$MODELS_DIR"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOCAL_SRC="$DIR/$SOURCE_FOLDER_NAME"
LOCAL_ASSETS="$DIR/$ASSETS_FOLDER_NAME"

echo -e "\n${YELLOW}[INFO] Resolving BadWords source files...${NC}"

if [ -d "$LOCAL_SRC" ] && [ -f "$LOCAL_SRC/main.py" ]; then
    echo -e "${GREEN}[OK] Local source files detected. Installing from ZIP format.${NC}"
    
    if [ "$WIPE_CHOICE" -eq 1 ]; then
        echo -e "${CYAN}[UPDATE] Copying new and updated files...${NC}"
        cp -R -u "$LOCAL_SRC/"* "$INSTALL_DIR_BASH/" 2>/dev/null || cp -R "$LOCAL_SRC/"* "$INSTALL_DIR_BASH/"
        if [ -d "$LOCAL_ASSETS" ]; then cp -R -u "$LOCAL_ASSETS/"* "$INSTALL_DIR_BASH/" 2>/dev/null || cp -R "$LOCAL_ASSETS/"* "$INSTALL_DIR_BASH/"; fi
    else
        echo -e "${CYAN}[INSTALL] Copying all files...${NC}"
        cp -R "$LOCAL_SRC/"* "$INSTALL_DIR_BASH/"
        if [ -d "$LOCAL_ASSETS" ]; then cp -R "$LOCAL_ASSETS/"* "$INSTALL_DIR_BASH/"; fi
    fi
else
    echo -e "${YELLOW}[INFO] Local source not found (Running via curl one-liner).${NC}"
    echo -e "${CYAN}[DOWNLOADING] Fetching latest source code from ${SOURCE_REPO}...${NC}"
    
    TMP_DL_DIR=$(mktemp -d)
    ZIP_PATH="$TMP_DL_DIR/repo.zip"
    
    curl -fsSL "$REPO_ZIP_URL" -o "$ZIP_PATH"
    
    echo -e "${CYAN}[EXTRACTING] Unpacking source...${NC}"
    unzip -q -o "$ZIP_PATH" -d "$TMP_DL_DIR"
    
    EXTRACTED_DIR=$(find "$TMP_DL_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)
    
    if [ -d "$EXTRACTED_DIR/$SOURCE_FOLDER_NAME" ]; then
        cp -R "$EXTRACTED_DIR/$SOURCE_FOLDER_NAME/"* "$INSTALL_DIR_BASH/"
        if [ -d "$EXTRACTED_DIR/$ASSETS_FOLDER_NAME" ]; then
            cp -R "$EXTRACTED_DIR/$ASSETS_FOLDER_NAME/"* "$INSTALL_DIR_BASH/"
        fi
        echo -e "${GREEN}[OK] Download and extraction complete.${NC}"
    else
        echo -e "${RED}[ERROR] Failed to extract source properly. Check repository URL.${NC}"
        exit 1
    fi
    rm -rf "$TMP_DL_DIR"
fi

if [ ! -f "$INSTALL_DIR_BASH/main.py" ]; then
    echo -e "${RED}[ERROR] Critical file 'main.py' is missing in target directory!${NC}"
    exit 1
fi

# ==========================================
# 6. VENV CREATION
# ==========================================
if [ ! -d "$VENV_DIR" ]; then
    echo -e "\n${CYAN}[VENV] Creating isolated Virtual Environment...${NC}"
    $TARGET_PYTHON -m venv "$VENV_DIR" || {
        echo -e "${RED}[ERROR] Failed to create venv.${NC}"
        exit 1
    }
else
    echo -e "\n${GREEN}[VENV] Virtual Environment already exists. Skipping creation.${NC}"
fi

# ==========================================
# 7. VENV INSTALLATION
# ==========================================
echo -e "\n${CYAN}[INSTALL] Installing libraries into VENV...${NC}"
VENV_PIP="$VENV_DIR/bin/pip"

"$VENV_PIP" install --upgrade pip >/dev/null 2>&1

if [ "$WIPE_CHOICE" -eq 1 ] && "$VENV_PIP" show torch >/dev/null 2>&1; then
    echo -e "${GREEN}[INFO] AI libraries already installed. Skipping heavy PyTorch downloads...${NC}"
    "$VENV_PIP" install --upgrade faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
else
    # Na macOS wystarczy standardowy pakiet torch, obsługuje MPS out of the box
    echo -e "${CYAN}[INSTALL] Installing PyTorch (Apple Silicon / Intel Support) + Faster-Whisper + Stable-TS...${NC}"
    "$VENV_PIP" install torch torchaudio faster-whisper stable-ts pypdf || { echo -e "${RED}[ERROR] Install failed.${NC}"; exit 1; }
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
# 8. SYMLINK TRICK
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
# 9. DAVINCI RESOLVE CONFIGURATION
# ==========================================
echo -e "\n${YELLOW}[INFO] Configuring DaVinci Resolve integration...${NC}"
if [ ! -d "$RESOLVE_SCRIPT_DIR" ]; then
    mkdir -p "$RESOLVE_SCRIPT_DIR"
fi

# ==========================================
# 10. WRAPPER GENERATION
# ==========================================
echo -e "${YELLOW}[INFO] Generating wrapper script...${NC}"

# Tworzymy bezpośrednio pythonem tak samo jak w Linux, unikając problemów z backtickami czy pojedynczymi cudzysłowami
export INSTALL_DIR_BASH
export RESOLVE_SCRIPT_DIR
export WRAPPER_FILE

"$TARGET_PYTHON" -c "
import os
import sys
import stat

INSTALL_DIR = os.environ.get('INSTALL_DIR_BASH')
LIBS_DIR = os.path.join(INSTALL_DIR, 'libs')
TARGET_FILE = os.environ.get('WRAPPER_FILE')

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

# 11. LOG PREPARATION
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
echo -e "${GREEN}          PATH: $INSTALL_DIR_BASH${NC}"
echo -e "${GREEN}          LOGS: $LOG_FILE${NC}"
echo ""
echo -e "${GREEN}================================================================================${NC}"
