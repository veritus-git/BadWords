#!/bin/bash
# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

# ============================================================
#  BadWords macOS Bootstrapper v4.0
#  Run with: curl -fsSL "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/mac-setup.sh" | bash
# ============================================================

set -uo pipefail

REPO_OWNER="veritus-git"
REPO_NAME="BadWords"
TAG="${BADWORDS_TAG:-latest}"
BIN_NAME="badwords-setup-macos"
SETUP_PY_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/setupfiles/setup.py"

CACHE_DIR="$HOME/Library/Caches/BadWords-bootstrap"
mkdir -p "$CACHE_DIR"
TARGET_BIN="$CACHE_DIR/badwords-installer"
SETUP_PY="$CACHE_DIR/setup.py"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || echo "")"
LOCAL_BIN="$SCRIPT_DIR/../installer/target/release/badwords-installer"
LOCAL_DEBUG="$SCRIPT_DIR/../installer/target/debug/badwords-installer"
LOCAL_SETUP="$SCRIPT_DIR/setup.py"

# ── Helper: Python CLI Fallback ───────────────────────────────
invoke_python_fallback() {
    echo ""
    echo -e "\033[36m========================================================================\033[0m"
    echo -e "\033[33m [!] macOS Security / Gatekeeper Notice:\033[0m"
    echo -e "     The graphical installer binary was blocked or unsupported on"
    echo -e "     this system architecture."
    echo -e "\033[36m========================================================================\033[0m"
    echo -e " How would you like to proceed?"
    echo -e "  \033[32m[1] Run CLI Installer via Python (Recommended - 100% bypasses Gatekeeper)\033[0m"
    echo -e "  \033[90m[2] Exit (I want to change Privacy & Security settings and try again)\033[0m"
    echo -e "\033[36m========================================================================\033[0m"

    read -r -p "Select an option [1 or 2]: " choice
    if [ "$choice" != "1" ]; then
        echo "Setup cancelled by user."
        exit 0
    fi

    echo ""
    echo "Preparing Python environment..."

    PY_RUNNER=""
    if command -v python3 &>/dev/null; then
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
            PY_RUNNER="python3"
        fi
    fi

    if [ -z "$PY_RUNNER" ]; then
        echo "Error: Python 3.10+ is required for the CLI fallback. Please install Python." >&2
        exit 1
    fi

    if [ -f "$LOCAL_SETUP" ]; then
        cp "$LOCAL_SETUP" "$SETUP_PY"
    elif [ ! -f "$SETUP_PY" ]; then
        echo "Fetching setup engine..."
        curl -fsSL "$SETUP_PY_URL" -o "$SETUP_PY" || true
    fi

    exec "$PY_RUNNER" "$SETUP_PY" "$@"
}

# ── Helper: Start Native Executable Safely ─────────────────────
start_native_executable() {
    local bin="$1"
    shift
    chmod +x "$bin" 2>/dev/null || true
    xattr -d com.apple.quarantine "$bin" 2>/dev/null || true

    if "$bin" "$@"; then
        exit 0
    else
        invoke_python_fallback "$@"
    fi
}

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
echo "Downloading BadWords Setup for macOS..."

DOWNLOAD_URL=""
if [ "$TAG" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/latest/download/${BIN_NAME}"
else
    DOWNLOAD_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}/releases/download/${TAG}/${BIN_NAME}"
fi

downloaded=false
if curl -fSL --progress-bar "$DOWNLOAD_URL" -o "$TARGET_BIN" 2>/dev/null; then
    downloaded=true
else
    FALLBACK_URL=$(curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/releases" | grep "browser_download_url.*${BIN_NAME}" | head -1 | cut -d : -f 2,3 | tr -d '\" ' || true)
    if [ -n "$FALLBACK_URL" ]; then
        curl -fSL --progress-bar "$FALLBACK_URL" -o "$TARGET_BIN" && downloaded=true
    fi
fi

if [ "$downloaded" = true ] && [ -f "$TARGET_BIN" ]; then
    start_native_executable "$TARGET_BIN" "$@"
else
    invoke_python_fallback "$@"
fi
