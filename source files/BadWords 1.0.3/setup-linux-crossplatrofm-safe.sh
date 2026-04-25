#!/bin/bash
set -e

# --- BADWORDS LINUX INSTALLER v2.5 (ROBUST & VERBOSE) ---
# Copyright (c) 2026 Szymon Wolarz
# Changes:
# - Restored explicit Bash logic for Resolve path detection (verbose logging)
# - Wrapper Path fixed to: ~/.local/share/DaVinciResolve/Fusion/Scripts/Utility/
# - Safe File Creation via Python (receives path from Bash)
# - Source folder set to "src"
# - PEP 668 Compliant (local libs)

# --- TRAP: ZATRZYMANIE OKNA NA KONIEC ---
function finish {
    echo ""
    echo -e "${GREEN}Script execution completed successfully!${NC}"
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
EXTRA_ENV_VARS=""

echo -e "${BLUE}========================================================${NC}"
echo -e "${BLUE}              BadWords - INSTALLER (Linux)              ${NC}"
echo -e "${BLUE}             Safe & Isolated Installation               ${NC}"
echo -e "${BLUE}========================================================${NC}"

# 1. Weryfikacja folderu źródłowego
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

# 2. Zależności systemowe
echo -e "${YELLOW}[INFO] Checking system dependencies...${NC}"

TARGET_PYTHON="python3" 

if [ -f /etc/os-release ]; then
    . /etc/os-release
    
    # Python 3.13 check
    IS_TOO_NEW=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 13) else 0)")
    
    if [ "$IS_TOO_NEW" -eq 1 ]; then
        PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        echo -e "${RED}[WARNING] Python $PY_VER detected.${NC}"
        echo -e "${YELLOW}[FIX] Attempting to install Python 3.11...${NC}"
        
        if [[ "$ID" == "fedora" || "$ID" == "rhel" || "$ID_LIKE" == *"fedora"* ]]; then
            sudo dnf install -y python3.11 python3.11-tkinter
            TARGET_PYTHON="/usr/bin/python3.11"
        elif [[ "$ID_LIKE" == *"debian"* || "$ID" == "debian" ]]; then
            sudo apt update
            sudo apt install -y python3.11 python3.11-venv python3.11-tk
            TARGET_PYTHON="/usr/bin/python3.11"
        elif [[ "$ID_LIKE" == *"arch"* ]]; then
             echo -e "${YELLOW}[ARCH] Using system python.${NC}"
        fi
        
        if command -v "$TARGET_PYTHON" &> /dev/null; then
            echo -e "${GREEN}[SUCCESS] Using $TARGET_PYTHON.${NC}"
        else
            echo -e "${RED}[ERROR] Python 3.11 not found. Continuing with system python.${NC}"
            TARGET_PYTHON="python3"
        fi
    else
        echo -e "${GREEN}[OK] System Python is compatible.${NC}"
    fi

    if [[ "$ID_LIKE" == *"debian"* || "$ID" == "debian" ]]; then
        sudo apt update
        sudo apt install -y python3-tk ffmpeg python3-pip pipx curl python3-venv
    elif [[ "$ID" == "fedora" || "$ID" == "rhel" || "$ID_LIKE" == *"fedora"* ]]; then
        sudo dnf install -y python3-tkinter ffmpeg pipx curl python3-pip
    elif [[ "$ID_LIKE" == *"arch"* ]]; then
        sudo pacman -S --noconfirm python-tk ffmpeg python-pipx curl python-pip
    fi
fi

pipx ensurepath > /dev/null 2>&1 || true

# 3. Definicja Ścieżek (Bash - do kopiowania)
INSTALL_DIR_BASH="$HOME/.local/share/$APP_NAME"
LIBS_DIR_BASH="$INSTALL_DIR_BASH/libs"

# 4. Instalacja Plików Aplikacji
echo -e "${YELLOW}[INFO] Preparing installation directory: $INSTALL_DIR_BASH${NC}"
rm -rf "$INSTALL_DIR_BASH"
mkdir -p "$INSTALL_DIR_BASH"
mkdir -p "$LIBS_DIR_BASH"

echo -e "${YELLOW}[INFO] Copying application files from '$SOURCE_FOLDER_NAME'...${NC}"
cp -r "$SOURCE_PATH/"* "$INSTALL_DIR_BASH/"

# 5. INSTALACJA PAKIETÓW LOKALNYCH
echo -e "${YELLOW}[INFO] Installing helper libraries locally...${NC}"

python3 -m pip install pypdf --target="$LIBS_DIR_BASH" --upgrade --no-user 2>/dev/null || \
{
    echo -e "${RED}[ERROR] Failed to install pypdf locally.${NC}"
    exit 1
}
echo -e "${GREEN}[OK] pypdf installed.${NC}"

# 6. Konfiguracja Silnika AI
echo -e "\n${CYAN}------------ AI ENGINE SETUP ------------${NC}"
echo -e "\n${CYAN}Select GPU type:${NC}"
echo -e "${GREEN}1) NVIDIA (Standard - CUDA 12.x)${NC}"
echo -e "${GREEN}2) NVIDIA (Compatibility - CUDA 11.8)${NC}"
echo -e "${RED}3) AMD RADEON (Stable - ROCm 6.1)${NC}"
echo -e "${YELLOW}4) CPU Only${NC}"
echo ""
read -p "Select [1-4]: " gpu_choice

NEED_BASE_INSTALL=true
if pipx list | grep -q "package openai-whisper"; then
    CUR_ENV_PY=$(pipx runpip openai-whisper --version | awk '{print $NF}' | tr -d ')')
    TARGET_ENV_PY=$($TARGET_PYTHON --version 2>&1 | awk '{print $2}')
    if [[ "$CUR_ENV_PY" == "$TARGET_ENV_PY"* ]]; then
        NEED_BASE_INSTALL=false
    fi
fi

if [ "$NEED_BASE_INSTALL" = true ]; then
    pipx reinstall openai-whisper --python "$TARGET_PYTHON"
fi

ensure_torch_version() {
    local required_tag="$1"
    local index_url="$2"
    local current_ver=$(pipx runpip openai-whisper show torch 2>/dev/null | grep Version)
    
    if [[ "$current_ver" != *"$required_tag"* ]]; then
        echo -e "${YELLOW}[UPDATE] Installing Torch $required_tag...${NC}"
        pipx runpip openai-whisper uninstall -y torch torchvision torchaudio || true
        eval "pipx runpip openai-whisper install torch torchvision torchaudio --index-url $index_url"
    fi
}

if [ "$gpu_choice" == "1" ]; then
    ensure_torch_version "+cu121" "https://download.pytorch.org/whl/cu121"
elif [ "$gpu_choice" == "2" ]; then
    ensure_torch_version "+cu118" "https://download.pytorch.org/whl/cu118"
elif [ "$gpu_choice" == "3" ]; then
    ensure_torch_version "rocm" "https://download.pytorch.org/whl/rocm6.1"
    read -p "Apply HSA_OVERRIDE_GFX_VERSION=10.3.0? [Y/n]: " amd_override
    amd_override=${amd_override:-y} 
    if [[ "$amd_override" =~ ^[Yy]$ ]]; then
        EXTRA_ENV_VARS="os.environ['HSA_OVERRIDE_GFX_VERSION'] = '10.3.0'"
    fi
fi

# 7. KONFIGURACJA WRAPPERA DLA DAVINCI (Przywrócona logika Basha)
echo -e "\n${YELLOW}[INFO] Configuring DaVinci Resolve integration...${NC}"

RESOLVE_SCRIPT_DIR=""

# Sprawdzamy instalację DaVinci (standardowa ścieżka /opt/resolve)
if [ -d "/opt/resolve" ]; then
    # Używamy ścieżki Fusion/Scripts/Utility (zamiast starego Configs)
    RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
    
    if [ ! -d "$RESOLVE_SCRIPT_DIR" ]; then
        echo "Creating script directory: $RESOLVE_SCRIPT_DIR"
        mkdir -p "$RESOLVE_SCRIPT_DIR"
    fi
fi

# Fallback jeśli /opt/resolve nie istnieje, ale użytkownik ma folder domowy Resolve
if [ -z "$RESOLVE_SCRIPT_DIR" ] || [ ! -d "$RESOLVE_SCRIPT_DIR" ]; then
    echo -e "${RED}[WARNING] Could not detect DaVinci Resolve installation at /opt/resolve.${NC}"
    echo "Attempting to force create standard user path..."
    RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
    mkdir -p "$RESOLVE_SCRIPT_DIR"
fi

if [ -d "$RESOLVE_SCRIPT_DIR" ]; then
    echo -e "${CYAN}[INFO] Target Script Directory: $RESOLVE_SCRIPT_DIR${NC}"
else
    echo -e "${RED}[ERROR] Failed to find or create target directory. Using current folder.${NC}"
    RESOLVE_SCRIPT_DIR="$PWD"
fi

# Przekazujemy wyliczoną przez Basha ścieżkę do Pythona
export WRAPPER_TARGET_DIR="$RESOLVE_SCRIPT_DIR"

# 8. GENEROWANIE PLIKU (Python)
# Python używany tylko do bezpiecznego zapisu pliku, ścieżkę bierze z Basha
echo -e "${YELLOW}[INFO] Writing wrapper script via Python...${NC}"

python3 -c "
import os
import sys
import stat

APP_NAME = \"$APP_NAME\"
WRAPPER_NAME = \"BadWords (Linux).py\"
EXTRA_ENV = \"$EXTRA_ENV_VARS\"

# Ścieżki instalacyjne
HOME = os.path.expanduser(\"~\")
INSTALL_DIR = os.path.join(HOME, \".local\", \"share\", APP_NAME)
LIBS_DIR = os.path.join(INSTALL_DIR, \"libs\")

# Pobieramy ścieżkę docelową wyliczoną wcześniej przez Basha
RESOLVE_DIR = os.environ.get('WRAPPER_TARGET_DIR')
if not RESOLVE_DIR or not os.path.exists(RESOLVE_DIR):
    # Ostateczny fallback w Pythonie
    RESOLVE_DIR = os.getcwd()

TARGET_FILE = os.path.join(RESOLVE_DIR, WRAPPER_NAME)

content = f\"\"\"import sys
import os
import traceback

# --- GPU COMPATIBILITY ---
{EXTRA_ENV}
# -------------------------

INSTALL_DIR = r'{INSTALL_DIR}'
LIBS_DIR = r'{LIBS_DIR}'
MAIN_SCRIPT = os.path.join(INSTALL_DIR, 'main.py')

# Inject Local Libs (PEP 668)
if os.path.exists(LIBS_DIR) and LIBS_DIR not in sys.path:
    sys.path.insert(0, LIBS_DIR)

# Append App Dir
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
    
    print(f\"[PYTHON] Successfully created: {TARGET_FILE}\")
except Exception as e:
    print(f\"[PYTHON-ERROR] Failed to create wrapper: {e}\")
    sys.exit(1)
"

echo ""
echo -e "${GREEN}=======================================================${NC}"
echo -e "${GREEN}        DONE! Please restart DaVinci Resolve${NC}"
echo -e "${GREEN}       Find the script in Workspace -> Script.${NC}"
echo -e "${GREEN}=======================================================${NC}"
echo ""

chmod +x "$RESOLVE_SCRIPT_DIR"

# Verification log
export PATH="$HOME/.local/bin:$PATH"
if command -v whisper &> /dev/null; then
    echo -e "${CYAN}[VERIFICATION] Checking installed Torch version:${NC}"
    echo -e "${CYAN}[DEBUG] Whisper found at: $(which whisper)${NC}"
    echo ""
    pipx runpip openai-whisper list | grep torch || echo "Torch not found?"  
    echo -e "${YELLOW}Check above: '+cu' = Nvidia, '+rocm' = AMD.${NC}"
fi