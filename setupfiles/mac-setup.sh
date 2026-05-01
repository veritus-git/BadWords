#!/bin/bash
# ============================================================
#  BadWords macOS Bootstrapper v1.0
#  Run with: bash <(curl -fsSL https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/mac-setup.sh)
#
#  Purpose: prepare Python environment, launch install.py in a
#  fresh Terminal window, then exit immediately.
#  Supports boot-time caching — subsequent runs within the same
#  macOS session launch instantly from the persistent cache.
# ============================================================

set -euo pipefail

INSTALLER_URL="https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install.py"
INSTALLER_URL_FB="https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/install.py"

# ── Persistent cache directory ────────────────────────────────
CACHE_DIR="$HOME/Library/Caches/BadWords-bootstrap"
CACHE_VENV_PY="$CACHE_DIR/venv/bin/python"
CACHE_INSTALL="$CACHE_DIR/install.py"
CACHE_MARKER="$CACHE_DIR/boot_marker.txt"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
step() { echo -e "${CYAN}[>]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*" >&2; echo ""; read -r -p "Press Enter to close..."; exit 1; }

# ── Boot-time marker (clears cache on next boot) ──────────────
_boot_time() {
    # sysctl kern.boottime returns something like: { sec = 1746091234, usec = 0 }
    sysctl -n kern.boottime 2>/dev/null \
        | grep -oE 'sec = [0-9]+' \
        | grep -oE '[0-9]+' \
        || date +%s   # fallback: current unix timestamp (no caching on failure)
}
BOOT_TIME=$(_boot_time)

# ── Helper: run installer in THIS terminal window ─────────────
_launch_installer() {
    local py="$1"
    local script="$2"
    local extra_pypath="${3:-}"

    if [ -n "$extra_pypath" ]; then
        export PYTHONPATH="$extra_pypath"
    fi
    
    # Clear screen, then replace this shell with Python
    clear
    
    # To ensure a perfectly clean window title in Terminal.app (without args cluttering it),
    # we create a temporary script named "BadWords Setup" and execute it directly.
    local clean_script="$CACHE_DIR/BadWords Setup"
    echo "#!$py" > "$clean_script"
    cat "$script" >> "$clean_script"
    chmod +x "$clean_script"
    
    exec "$clean_script"
}

# ── FAST PATH: boot-time cache ────────────────────────────────
if [ -f "$CACHE_MARKER" ] && [ -f "$CACHE_VENV_PY" ] && [ -f "$CACHE_INSTALL" ]; then
    stored=$(cat "$CACHE_MARKER" 2>/dev/null || echo "")
    if [ "$stored" = "$BOOT_TIME" ]; then
        echo ""
        echo -e "  ${GREEN}BadWords Setup${NC}"
        echo -e "  ${CYAN}Cached environment found — refreshing installer script...${NC}"

        # Venv is cached (saves time) but install.py is always refreshed
        refresh_ok=false
        if curl -fsSL --max-time 15 "$INSTALLER_URL" -o "$CACHE_INSTALL" 2>/dev/null; then
            refresh_ok=true
        elif curl -fsSL --max-time 15 "$INSTALLER_URL_FB" -o "$CACHE_INSTALL" 2>/dev/null; then
            refresh_ok=true
        fi
        if [ "$refresh_ok" = false ]; then
            warn "Could not refresh install.py — launching from cached copy."
        fi

        echo -e "  ${CYAN}Launching instantly (cached environment)...${NC}"
        echo ""
        _launch_installer "$CACHE_VENV_PY" "$CACHE_INSTALL"
        # exec above replaces the shell — this line is never reached
        exit 0
    fi
fi

# ── SLOW PATH: Full setup ─────────────────────────────────────
echo ""
echo -e "  ${GREEN}BadWords macOS Bootstrapper${NC}"
echo -e "  ${CYAN}Preparing environment...${NC}"
echo ""

mkdir -p "$CACHE_DIR"
BW_TMP=$(mktemp -d)
trap 'rm -rf "$BW_TMP"' EXIT INT TERM

# ── 1. Find Python 3.10+ ──────────────────────────────────────
step "Looking for compatible Python (3.10+)..."
PYTHON_BIN=""

# Check common locations in priority order
for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PYTHON_BIN="$(command -v "$cmd")"
            ok "Found system Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
            break
        fi
    fi
done

# Homebrew locations (Apple Silicon and Intel)
if [ -z "$PYTHON_BIN" ]; then
    for brew_py in \
        /opt/homebrew/bin/python3 \
        /opt/homebrew/bin/python3.13 \
        /opt/homebrew/bin/python3.12 \
        /opt/homebrew/bin/python3.11 \
        /opt/homebrew/bin/python3.10 \
        /usr/local/bin/python3 \
        /usr/local/bin/python3.13 \
        /usr/local/bin/python3.12 \
        /usr/local/bin/python3.11 \
        /usr/local/bin/python3.10; do
        if [ -x "$brew_py" ]; then
            if "$brew_py" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
                PYTHON_BIN="$brew_py"
                ok "Found Homebrew Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
                break
            fi
        fi
    done
fi

# pyenv
if [ -z "$PYTHON_BIN" ] && [ -d "$HOME/.pyenv/versions" ]; then
    for py in "$HOME"/.pyenv/versions/3.1[0-9]*/bin/python3; do
        if [ -x "$py" ] && "$py" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PYTHON_BIN="$py"
            ok "Found pyenv Python: $PYTHON_BIN"
            break
        fi
    done
fi

# ── 2. Test venv support ──────────────────────────────────────
VENV_OK=false
if [ -n "$PYTHON_BIN" ]; then
    step "Testing virtual environment support..."
    _tv="$BW_TMP/test_venv"
    if "$PYTHON_BIN" -m venv "$_tv" &>/dev/null && [ -f "$_tv/bin/python" ]; then
        VENV_OK=true
        ok "venv works."
    else
        warn "System venv not functional. Will use portable Python."
    fi
fi

# ── 3. python-build-standalone fallback ───────────────────────
PBS_PERMANENT_DIR="$CACHE_DIR/python"
PBS_FALLBACK_TAG="20250317"
PBS_FALLBACK_VER="3.12.9"

if [ -z "$PYTHON_BIN" ] || [ "$VENV_OK" = "false" ]; then
    # Reuse previously downloaded portable Python
    PBS_BIN=$(find "$PBS_PERMANENT_DIR/bin" -name "python3*" -maxdepth 1 -type f -executable 2>/dev/null | sort -V | tail -1 || true)
    if [ -n "$PBS_BIN" ] && "$PBS_BIN" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
        ok "Reusing cached portable Python: $PBS_BIN"
        PYTHON_BIN="$PBS_BIN"
        VENV_OK=true
    else
        warn "Downloading portable Python (python-build-standalone)..."
        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64)        PBS_ARCH="x86_64-apple-darwin" ;;
            arm64|aarch64) PBS_ARCH="aarch64-apple-darwin" ;;
            *) die "Unsupported CPU architecture: $ARCH" ;;
        esac

        # Try GitHub API for latest CPython 3.12
        _PBS_URL=""
        _API_RESP=$(curl -fsSL --max-time 15 \
            "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest" 2>/dev/null || true)
        if [ -n "$_API_RESP" ]; then
            _PBS_URL=$(echo "$_API_RESP" \
                | grep -o '"browser_download_url": "[^"]*cpython-3\.12[^"]*'"${PBS_ARCH}"'-install_only\.tar\.gz"' \
                | head -1 \
                | sed 's/.*"browser_download_url": "\(.*\)"/\1/' || true)
        fi
        # Fallback to hardcoded known-good URL
        if [ -z "$_PBS_URL" ]; then
            warn "GitHub API unavailable. Using fallback URL."
            _PBS_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PBS_FALLBACK_TAG}/cpython-${PBS_FALLBACK_VER}+${PBS_FALLBACK_TAG}-${PBS_ARCH}-install_only.tar.gz"
        fi

        step "Downloading portable Python..."
        _ARCHIVE="$BW_TMP/pbs.tar.gz"
        curl -fsSL "$_PBS_URL" -o "$_ARCHIVE" || die "Download failed. Check your internet connection."

        step "Extracting..."
        mkdir -p "$PBS_PERMANENT_DIR"
        tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR" --strip-components=2 2>/dev/null \
            || tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR" --strip-components=1 2>/dev/null \
            || tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR"

        PYTHON_BIN=$(find "$PBS_PERMANENT_DIR/bin" -name "python3*" -maxdepth 1 -type f -executable 2>/dev/null | sort -V | tail -1 || true)
        [ -n "$PYTHON_BIN" ] || die "Could not find Python binary after extraction."
        VENV_OK=true
        ok "Portable Python ready: $PYTHON_BIN"
    fi
fi

[ -n "$PYTHON_BIN" ] || die "No suitable Python 3.10+ found. Install via: brew install python3"

# ── 4. Create bootstrap venv in cache ────────────────────────
step "Creating bootstrap environment..."

# Wipe stale venv (cache miss = boot changed, rebuild)
if [ -d "$CACHE_DIR/venv" ]; then
    rm -rf "$CACHE_DIR/venv"
fi

EXTRA_PYPATH=""
if "$PYTHON_BIN" -m venv "$CACHE_DIR/venv" &>/dev/null && [ -f "$CACHE_VENV_PY" ]; then
    ok "Bootstrap venv created."
else
    warn "venv creation failed. Using --target fallback."
    PKG_DIR="$CACHE_DIR/packages"
    mkdir -p "$PKG_DIR"
    CACHE_VENV_PY="$PYTHON_BIN"
    EXTRA_PYPATH="$PKG_DIR"
fi

# ── 5. Install rich ───────────────────────────────────────────
step "Installing dependencies (rich)..."
if [ -z "$EXTRA_PYPATH" ]; then
    "$CACHE_VENV_PY" -m pip install --upgrade pip --quiet 2>/dev/null || true
    "$CACHE_VENV_PY" -m pip install rich --quiet \
        || { warn "venv pip failed, trying --target fallback..."
             PKG_DIR="$CACHE_DIR/packages"; mkdir -p "$PKG_DIR"
             "$PYTHON_BIN" -m pip install rich --target "$PKG_DIR" --quiet
             EXTRA_PYPATH="$PKG_DIR"
             CACHE_VENV_PY="$PYTHON_BIN"; }
else
    "$PYTHON_BIN" -m pip install rich --target "$EXTRA_PYPATH" --quiet \
        || die "Failed to install 'rich'. Check your internet connection."
fi
ok "Dependencies ready."

# ── 6. Download install.py into cache ────────────────────────
step "Downloading BadWords installer..."
downloaded=false
if curl -fsSL --max-time 30 "$INSTALLER_URL" -o "$CACHE_INSTALL" 2>/dev/null; then
    downloaded=true
else
    warn "GitHub unavailable. Trying GitLab fallback..."
    if curl -fsSL --max-time 30 "$INSTALLER_URL_FB" -o "$CACHE_INSTALL" 2>/dev/null; then
        downloaded=true
    fi
fi
[ "$downloaded" = true ] || die "Failed to download install.py from both GitHub and GitLab."
ok "Installer ready."

# ── 7. Write boot-time cache marker ──────────────────────────
echo "$BOOT_TIME" > "$CACHE_MARKER"
ok "Cache marker written."

# ── 8. Launch installer in this terminal window ──────────────
echo ""
echo -e "  ${CYAN}Launching BadWords Installer...${NC}"
sleep 0.5
_launch_installer "$CACHE_VENV_PY" "$CACHE_INSTALL" "$EXTRA_PYPATH"
# exec above replaces the shell — this line is never reached
exit 0
