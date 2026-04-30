#!/bin/bash
# ============================================================
#  BadWords Linux Bootstrapper v1.0
#  Prepares Python environment and launches the installer UI.
#  This script does NOT install BadWords itself.
# ============================================================

INSTALLER_URL="https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/install.py"
PBS_FALLBACK_TAG="20250317"
PBS_FALLBACK_VER="3.12.9"
PBS_PERMANENT_DIR="$HOME/.local/share/badwords-python"

# ── Colors ────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'
step() { echo -e "${CYAN}[>]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }

# ── Cleanup on exit ───────────────────────────────────────────
BW_TMP=""
_cleanup() { [ -n "$BW_TMP" ] && rm -rf "$BW_TMP"; }
trap _cleanup EXIT INT TERM
BW_TMP=$(mktemp -d)

# ── 1. Find system Python 3.10+ ───────────────────────────────
step "Looking for compatible Python (3.10+)..."
PYTHON_BIN=""
for cmd in python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PYTHON_BIN="$cmd"
            ok "Found system Python: $PYTHON_BIN ($("$PYTHON_BIN" --version 2>&1))"
            break
        fi
    fi
done

# ── 2. Test venv capability (PEP 668 / missing ensurepip) ─────
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

# ── 3. Download python-build-standalone if needed ─────────────
if [ -z "$PYTHON_BIN" ] || [ "$VENV_OK" = "false" ]; then
    # Reuse previously downloaded portable Python
    PBS_BIN=$(find "$PBS_PERMANENT_DIR/bin" -name "python3*" -maxdepth 1 -type f -executable 2>/dev/null | sort -V | tail -1)
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

        # Try GitHub API for latest CPython 3.12
        _PBS_URL=""
        _API_RESP=$(curl -fsSL --max-time 15 \
            "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest" 2>/dev/null || true)
        if [ -n "$_API_RESP" ]; then
            _PBS_URL=$(echo "$_API_RESP" \
                | grep -o '"browser_download_url": "[^"]*cpython-3\.12[^"]*'"${PBS_ARCH}"'-install_only\.tar\.gz"' \
                | head -1 | sed 's/.*"browser_download_url": "\(.*\)"/\1/' || true)
        fi
        # Fallback to hardcoded known-good URL
        if [ -z "$_PBS_URL" ]; then
            warn "GitHub API unavailable. Using fallback URL."
            _PBS_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PBS_FALLBACK_TAG}/cpython-${PBS_FALLBACK_VER}+${PBS_FALLBACK_TAG}-${PBS_ARCH}-install_only.tar.gz"
        fi

        step "Downloading: $_PBS_URL"
        _ARCHIVE="$BW_TMP/pbs.tar.gz"
        if command -v curl &>/dev/null; then
            curl -fsSL "$_PBS_URL" -o "$_ARCHIVE" || die "Download failed."
        elif command -v wget &>/dev/null; then
            wget -qO "$_ARCHIVE" "$_PBS_URL" || die "Download failed."
        else
            die "Neither curl nor wget found. Cannot download Python."
        fi

        step "Extracting portable Python..."
        mkdir -p "$PBS_PERMANENT_DIR"
        tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR" --strip-components=2 2>/dev/null \
            || tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR" --strip-components=1 2>/dev/null \
            || tar -xf "$_ARCHIVE" -C "$PBS_PERMANENT_DIR"

        PYTHON_BIN=$(find "$PBS_PERMANENT_DIR/bin" -name "python3*" -maxdepth 1 -type f -executable 2>/dev/null | sort -V | tail -1)
        [ -n "$PYTHON_BIN" ] || die "Could not find Python binary after extraction."
        VENV_OK=true
        ok "Portable Python installed: $PYTHON_BIN"
    fi
fi

[ -n "$PYTHON_BIN" ] || die "No suitable Python found and portable download failed."

# ── 4. Create bootstrap venv ──────────────────────────────────
BOOTSTRAP_VENV="$BW_TMP/bw_venv"
step "Creating bootstrap environment..."
"$PYTHON_BIN" -m venv "$BOOTSTRAP_VENV" \
    || die "Failed to create bootstrap virtual environment."
VENV_PY="$BOOTSTRAP_VENV/bin/python"
VENV_PIP="$BOOTSTRAP_VENV/bin/pip"
ok "Bootstrap venv created."

# ── 5. Install rich into bootstrap venv ───────────────────────
step "Installing dependencies (rich)..."
# Upgrade pip silently first to avoid any pip warnings
"$VENV_PY" -m pip install --upgrade pip --quiet 2>/dev/null || true
"$VENV_PY" -m pip install rich --quiet \
    || die "Failed to install 'rich'. Check your internet connection."
ok "Dependencies ready."

# ── 6. Download install.py ────────────────────────────────────
INSTALL_PY="$BW_TMP/install.py"
step "Downloading BadWords installer..."
if command -v curl &>/dev/null; then
    curl -fsSL "$INSTALLER_URL" -o "$INSTALL_PY" || die "Failed to download install.py"
elif command -v wget &>/dev/null; then
    wget -qO "$INSTALL_PY" "$INSTALLER_URL" || die "Failed to download install.py"
else
    die "curl or wget required."
fi
[ -f "$INSTALL_PY" ] || die "installer script not found after download."
ok "Installer ready."

# ── 7. Launch installer ───────────────────────────────────────
echo ""
"$VENV_PY" "$INSTALL_PY" --platform linux --bootstrap-python "$PYTHON_BIN"