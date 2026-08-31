#!/bin/bash
# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# ============================================================
#  BadWords Linux Bootstrapper v4.0
#  Run with: curl -fsSL "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/linux-setup.sh" | bash
# ============================================================

set -uo pipefail

REPO_OWNER="veritus-git"
REPO_NAME="BadWords"
TAG="${BADWORDS_TAG:-latest}"
BIN_NAME="badwords-setup-linux"

INSTALLER_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/setupfiles/setup.py"
INSTALLER_URL_FB="https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/setup.py"
PBS_FALLBACK_TAG="20250317"
PBS_FALLBACK_VER="3.12.9"

# ── Directories ───────────────────────────────────────────────
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/BadWords-bootstrap"
PBS_DIR="$CACHE_DIR/python"
TARGET_BIN="$CACHE_DIR/badwords-installer"
BW_TMP=$(mktemp -d 2>/dev/null || mktemp -d -t 'bw_tmp')
trap 'rm -rf "$BW_TMP"' EXIT INT TERM

mkdir -p "$CACHE_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || echo "")"
LOCAL_BIN="$SCRIPT_DIR/../installer/target/release/badwords-installer"
LOCAL_DEBUG="$SCRIPT_DIR/../installer/target/debug/badwords-installer"
LOCAL_SETUP="$SCRIPT_DIR/setup.py"
LOCAL_REPO=""
if [ -f "$LOCAL_SETUP" ]; then
    LOCAL_REPO="$(dirname "$SCRIPT_DIR")"
fi

# ── Helper: Rich Terminal Python Fallback ─────────────────────
invoke_python_fallback() {
    clear
    echo -e "user@computer:~$ curl -fsSL \"https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/linux-setup.sh\" | bash"
    echo -e "\033[36mDownloading BadWords Setup for Linux...\033[0m"
    echo ""
    echo -e "\033[36m========================================================================\033[0m"
    echo -e "\033[33m [!] Security & Compatibility Notice:\033[0m"
    echo -e "     The graphical installer binary could not run on this system"
    echo -e "     (unsupported environment or security policy)."
    echo -e "\033[36m========================================================================\033[0m"
    echo -e " How would you like to proceed?"
    echo -e "  \033[32m[1] Run Terminal Installer via Python (Recommended - 100% universal)\033[0m"
    echo -e "  \033[90m[2] Exit\033[0m"
    echo -e "\033[36m========================================================================\033[0m"

    read -r -p "Select an option [1 or 2]: " choice
    if [ "$choice" != "1" ]; then
        echo "Setup closed."
        exit 0
    fi

    echo ""
    echo -e "  \033[36mPreparing portable Python environment...\033[0m"

    PYTHON_BIN=""
    _find_cached_python() {
        local bin
        bin=$(find "$PBS_DIR/bin" -maxdepth 1 -type f -executable \( -name "python3" -o -name "python3.[0-9]*" \) ! -name "*-config" ! -name "*.py" 2>/dev/null | sort -V | tail -1 || true)
        if [ -z "$bin" ]; then
            bin=$(find "$PBS_DIR" -maxdepth 3 -type f -executable -name "python3" ! -name "*-config" 2>/dev/null | head -1 || true)
        fi
        echo "$bin"
    }

    if [ -d "$PBS_DIR" ]; then
        PYTHON_BIN=$(_find_cached_python)
        if [ -n "$PYTHON_BIN" ]; then
            if ! "$PYTHON_BIN" -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null || ! "$PYTHON_BIN" -m pip --version &>/dev/null; then
                PYTHON_BIN=""
            fi
        fi
    fi

    if [ -z "$PYTHON_BIN" ]; then
        echo -e "  \033[36mDownloading portable Python (python-build-standalone)...\033[0m"
        rm -rf "$PBS_DIR"
        mkdir -p "$PBS_DIR"

        ARCH=$(uname -m)
        case "$ARCH" in
            x86_64)        PBS_ARCH="x86_64-unknown-linux-gnu" ;;
            aarch64|arm64) PBS_ARCH="aarch64-unknown-linux-gnu" ;;
            *) echo "Unsupported CPU architecture: $ARCH" >&2; exit 1 ;;
        esac

        _PBS_URL=""
        _API_RESP=""
        if command -v curl &>/dev/null; then
            _API_RESP=$(curl -fsSL --max-time 15 "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest" 2>/dev/null || true)
        elif command -v wget &>/dev/null; then
            _API_RESP=$(wget -qO- --timeout=15 "https://api.github.com/repos/indygreg/python-build-standalone/releases/latest" 2>/dev/null || true)
        fi
        if [ -n "$_API_RESP" ]; then
            _PBS_URL=$(echo "$_API_RESP" | grep -o '"browser_download_url": "[^"]*cpython-3\.12[^"]*'"${PBS_ARCH}"'-install_only\.tar\.gz"' | head -1 | sed 's/.*"browser_download_url": "\(.*\)"/\1/' || true)
        fi
        if [ -z "$_PBS_URL" ]; then
            _PBS_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PBS_FALLBACK_TAG}/cpython-${PBS_FALLBACK_VER}+${PBS_FALLBACK_TAG}-${PBS_ARCH}-install_only.tar.gz"
        fi

        _ARCHIVE="$BW_TMP/pbs.tar.gz"
        if command -v curl &>/dev/null; then
            curl -fsSL "$_PBS_URL" -o "$_ARCHIVE" || { echo "Download failed." >&2; exit 1; }
        elif command -v wget &>/dev/null; then
            wget -qO "$_ARCHIVE" "$_PBS_URL" || { echo "Download failed." >&2; exit 1; }
        fi

        tar -xf "$_ARCHIVE" -C "$PBS_DIR" --strip-components=1 2>/dev/null || tar -xf "$_ARCHIVE" -C "$PBS_DIR"
        PYTHON_BIN=$(_find_cached_python)

        if ! "$PYTHON_BIN" -m pip --version &>/dev/null; then
            _GETPIP="$BW_TMP/get-pip.py"
            if command -v curl &>/dev/null; then
                curl -fsSL "https://bootstrap.pypa.io/get-pip.py" -o "$_GETPIP" || true
            else
                wget -qO "$_GETPIP" "https://bootstrap.pypa.io/get-pip.py" || true
            fi
            "$PYTHON_BIN" "$_GETPIP" --quiet 2>/dev/null || true
        fi
    fi

    # Install rich to temp
    echo -e "  \033[36mInstalling rich UI dependencies...\033[0m"
    PKG_DIR="$BW_TMP/packages"
    mkdir -p "$PKG_DIR"
    "$PYTHON_BIN" -m pip install rich --target "$PKG_DIR" --quiet 2>/dev/null || true

    # Download setup.py
    SETUP_PY="$BW_TMP/setup.py"
    downloaded=false
    if [ -f "$LOCAL_SETUP" ]; then
        cp "$LOCAL_SETUP" "$SETUP_PY"
        downloaded=true
    elif command -v curl &>/dev/null; then
        if curl -fsSL --max-time 30 "$INSTALLER_URL" -o "$SETUP_PY" 2>/dev/null; then
            downloaded=true
        elif curl -fsSL --max-time 30 "$INSTALLER_URL_FB" -o "$SETUP_PY" 2>/dev/null; then
            downloaded=true
        fi
    elif command -v wget &>/dev/null; then
        if wget -qO "$SETUP_PY" "$INSTALLER_URL" 2>/dev/null; then
            downloaded=true
        elif wget -qO "$SETUP_PY" "$INSTALLER_URL_FB" 2>/dev/null; then
            downloaded=true
        fi
    fi

    if [ "$downloaded" = false ]; then
        echo "Failed to download setup.py" >&2
        exit 1
    fi

    export PYTHONPATH="$PKG_DIR"
    printf '\033]0;BadWords Setup\007'
    clear
    local args=(--platform linux --bootstrap-python "$PYTHON_BIN")
    if [ -n "$LOCAL_REPO" ]; then
        args+=(--local-repo "$LOCAL_REPO")
    fi
    exec "$PYTHON_BIN" "$SETUP_PY" "${args[@]}" < /dev/tty
}

# ── Helper: Start Native Executable Safely ─────────────────────
start_native_executable() {
    local bin="$1"
    shift
    chmod +x "$bin" 2>/dev/null || true

    if "$bin" "$@"; then
        exit 0
    else
        invoke_python_fallback "$@"
    fi
}

# 0. Force fallback check (for testing or explicitly requested CLI mode)
if [ "${BADWORDS_FORCE_FALLBACK:-0}" = "1" ] || [[ " $* " =~ " --fallback " ]] || [[ " $* " =~ " --cli " ]]; then
    invoke_python_fallback "$@"
fi

# 1. Local file detection (if executed inside repo clone)
if [ -f "$LOCAL_BIN" ]; then
    start_native_executable "$LOCAL_BIN" "$@"
elif [ -f "$LOCAL_DEBUG" ]; then
    start_native_executable "$LOCAL_DEBUG" "$@"
elif [ -f "$SCRIPT_DIR/../installer/Cargo.toml" ] && command -v cargo &>/dev/null; then
    echo "Compiling and running local installer via cargo..."
    exec cargo run --release --manifest-path "$SCRIPT_DIR/../installer/Cargo.toml" -- "$@"
fi

# 2. Remote download
echo "Downloading BadWords Setup for Linux..."

DOWNLOAD_URL=""
if [ "$TAG" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest/download/${BIN_NAME}"
else
    DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/${TAG}/${BIN_NAME}"
fi

downloaded=false
if command -v curl &>/dev/null; then
    if curl -fSL --progress-bar "$DOWNLOAD_URL" -o "$TARGET_BIN" 2>/dev/null; then
        downloaded=true
    fi
elif command -v wget &>/dev/null; then
    if wget -q --show-progress -O "$TARGET_BIN" "$DOWNLOAD_URL" 2>/dev/null; then
        downloaded=true
    fi
fi

if [ "$downloaded" = false ]; then
    FALLBACK_URL=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases" 2>/dev/null | grep "browser_download_url.*${BIN_NAME}" | head -1 | cut -d : -f 2,3 | tr -d '\" ' || true)
    if [ -n "$FALLBACK_URL" ]; then
        curl -fSL --progress-bar "$FALLBACK_URL" -o "$TARGET_BIN" 2>/dev/null && downloaded=true
    fi
fi

if [ "$downloaded" = true ] && [ -f "$TARGET_BIN" ]; then
    start_native_executable "$TARGET_BIN" "$@"
else
    invoke_python_fallback "$@"
fi