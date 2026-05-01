#!/bin/bash
# ============================================================
#  BadWords Linux Bootstrapper v2.0
#  Run with: bash <(curl -fsSL https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/linux-setup.sh)
#
#  Supports boot-time caching — subsequent runs within the same
#  Linux session launch the installer instantly from cache.
# ============================================================

set -euo pipefail

INSTALLER_URL="https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install.py"
INSTALLER_URL_FALLBACK="https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/install.py"
PBS_FALLBACK_TAG="20250317"
PBS_FALLBACK_VER="3.12.9"

# ── Persistent cache directory ────────────────────────────────
CACHE_DIR="$HOME/.cache/BadWords-bootstrap"
CACHE_VENV_PY="$CACHE_DIR/venv/bin/python"
CACHE_INSTALL="$CACHE_DIR/install.py"
CACHE_MARKER="$CACHE_DIR/boot_marker.txt"
PBS_PERMANENT_DIR="$CACHE_DIR/python"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
step() { echo -e "${CYAN}[>]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*" >&2; echo ""; read -r -p "Press Enter to close..."; exit 1; }

# ── Boot-time marker ─────────────────────────────────────────
_boot_time() {
    # /proc/uptime gives seconds since boot — combine with current time for boot timestamp
    if [ -f /proc/stat ]; then
        grep -m1 'btime' /proc/stat | awk '{print $2}' 2>/dev/null && return
    fi
    # Fallback: uptime-based
    awk '{print int('"$(date +%s)"' - $1)}' /proc/uptime 2>/dev/null || date +%s
}
BOOT_TIME=$(_boot_time)

# ── Helper: launch installer in THIS terminal ─────────────────
_launch_installer() {
    local py="$1"
    local script="$2"
    # Set terminal title
    printf '\033]0;BadWords Setup\007'
    clear
    exec "$py" "$script" --platform linux --bootstrap-python "$py"
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
        elif curl -fsSL --max-time 15 "$INSTALLER_URL_FALLBACK" -o "$CACHE_INSTALL" 2>/dev/null; then
            refresh_ok=true
        elif wget -qO "$CACHE_INSTALL" "$INSTALLER_URL" 2>/dev/null; then
            refresh_ok=true
        fi
        if [ "$refresh_ok" = false ]; then
            warn "Could not refresh install.py — launching from cached copy."
        fi

        echo -e "  ${CYAN}Launching instantly (cached environment)...${NC}"
        echo ""
        _launch_installer "$CACHE_VENV_PY" "$CACHE_INSTALL"
        exit 0
    fi
fi

# ── SLOW PATH: Full setup ─────────────────────────────────────
echo ""
echo -e "  ${GREEN}BadWords Linux Bootstrapper${NC}"
echo -e "  ${CYAN}Preparing environment...${NC}"
echo ""

mkdir -p "$CACHE_DIR"
BW_TMP=$(mktemp -d)
trap 'rm -rf "$BW_TMP"' EXIT INT TERM

# ── 1. Find system Python 3.10+ ──────────────────────────────
step "Looking for compatible Python (3.10+)..."
PYTHON_BIN=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PYTHON_BIN="$(command -v "$cmd")"
            ok "Found system Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
            break
        fi
    fi
done

# ── 2. Test venv support ──────────────────────────────────────
VENV_OK=false
if [ -n "$PYTHON_BIN" ]; then
    step "Testing virtual environment support..."
    _tv="$BW_TMP/test_venv"
    if "$PYTHON_BIN" -m venv "$_tv" &>/dev/null 2>&1 && [ -f "$_tv/bin/python" ]; then
        VENV_OK=true
        ok "venv works."
        rm -rf "$_tv"
    else
        warn "System venv not functional (missing python3-venv?). Will use portable Python."
    fi
fi

# ── 3. python-build-standalone fallback ──────────────────────
if [ -z "$PYTHON_BIN" ] || [ "$VENV_OK" = "false" ]; then
    PBS_BIN=$(find "$PBS_PERMANENT_DIR/bin" -name "python3*" -maxdepth 1 -type f -executable 2>/dev/null | sort -V | tail -1 || true)
    if [ -n "$PBS_BIN" ] && "$PBS_BIN" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
        ok "Reusing cached portable Python: $PBS_BIN"
        PYTHON_BIN="$PBS_BIN"
        VENV_OK=true
    else
        warn "Downloading portable Python (python-build-standalone)..."
        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64)        PBS_ARCH="x86_64-unknown-linux-gnu" ;;
            aarch64|arm64) PBS_ARCH="aarch64-unknown-linux-gnu" ;;
            *) die "Unsupported CPU architecture: $ARCH" ;;
        esac

        _PBS_URL=""
        _API_RESP=$(curl -fsSL --max-time 15 \
            "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest" 2>/dev/null || true)
        if [ -n "$_API_RESP" ]; then
            _PBS_URL=$(echo "$_API_RESP" \
                | grep -o '"browser_download_url": "[^"]*cpython-3\.12[^"]*'"${PBS_ARCH}"'-install_only\.tar\.gz"' \
                | head -1 | sed 's/.*"browser_download_url": "\(.*\)"/\1/' || true)
        fi
        if [ -z "$_PBS_URL" ]; then
            warn "GitHub API unavailable. Using fallback URL."
            _PBS_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PBS_FALLBACK_TAG}/cpython-${PBS_FALLBACK_VER}+${PBS_FALLBACK_TAG}-${PBS_ARCH}-install_only.tar.gz"
        fi

        step "Downloading portable Python..."
        _ARCHIVE="$BW_TMP/pbs.tar.gz"
        if command -v curl &>/dev/null; then
            curl -fsSL "$_PBS_URL" -o "$_ARCHIVE" || die "Download failed."
        elif command -v wget &>/dev/null; then
            wget -qO "$_ARCHIVE" "$_PBS_URL" || die "Download failed."
        else
            die "Neither curl nor wget found."
        fi

        step "Extracting portable Python..."
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

[ -n "$PYTHON_BIN" ] || die "No suitable Python 3.10+ found. Install with: sudo apt install python3 python3-venv"

# ── 4. Create bootstrap venv in cache ────────────────────────
step "Creating bootstrap environment..."

# Wipe stale venv (cache miss = boot changed)
if [ -d "$CACHE_DIR/venv" ]; then
    rm -rf "$CACHE_DIR/venv"
fi

if "$PYTHON_BIN" -m venv "$CACHE_DIR/venv" &>/dev/null && [ -f "$CACHE_VENV_PY" ]; then
    ok "Bootstrap venv created."
else
    die "Failed to create bootstrap virtual environment."
fi

# ── 5. Install rich ──────────────────────────────────────────
step "Installing dependencies (rich)..."
"$CACHE_VENV_PY" -m pip install --upgrade pip --quiet 2>/dev/null || true
"$CACHE_VENV_PY" -m pip install rich --quiet \
    || die "Failed to install 'rich'. Check your internet connection."
ok "Dependencies ready."

# ── 6. Download install.py into cache ────────────────────────
step "Downloading BadWords installer..."
downloaded=false
if command -v curl &>/dev/null; then
    if curl -fsSL --max-time 30 "$INSTALLER_URL" -o "$CACHE_INSTALL" 2>/dev/null; then
        downloaded=true
    elif curl -fsSL --max-time 30 "$INSTALLER_URL_FALLBACK" -o "$CACHE_INSTALL" 2>/dev/null; then
        downloaded=true
    fi
elif command -v wget &>/dev/null; then
    if wget -qO "$CACHE_INSTALL" "$INSTALLER_URL" 2>/dev/null; then
        downloaded=true
    elif wget -qO "$CACHE_INSTALL" "$INSTALLER_URL_FALLBACK" 2>/dev/null; then
        downloaded=true
    fi
fi
[ "$downloaded" = true ] || die "Failed to download install.py. Check your internet connection."
ok "Installer ready."

# ── 7. Write boot-time cache marker ──────────────────────────
echo "$BOOT_TIME" > "$CACHE_MARKER"
ok "Cache ready."

# ── 8. Launch installer in this terminal ─────────────────────
echo ""
echo -e "  ${CYAN}Launching BadWords Installer...${NC}"
sleep 0.3
_launch_installer "$CACHE_VENV_PY" "$CACHE_INSTALL"
# exec above replaces the shell — this line is never reached
exit 0