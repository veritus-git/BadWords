#!/bin/bash
# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.
# ============================================================
#  BadWords macOS Bootstrapper v4.0 (Native)
#  Run with: curl -fsSL "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/mac-setup.sh" | bash
#
#  Downloads and launches the native BadWords Setup GUI.
# ============================================================

set -euo pipefail

REPO_OWNER="veritus-git"
REPO_NAME="BadWords"
TAG="${BADWORDS_TAG:-latest}"

BIN_NAME="badwords-setup-macos"

# 1. Local file detection (if executed inside repo)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd 2>/dev/null || echo "")"
LOCAL_BIN="$SCRIPT_DIR/../installer/target/release/badwords-installer"
LOCAL_DEBUG="$SCRIPT_DIR/../installer/target/debug/badwords-installer"

if [ -f "$LOCAL_BIN" ]; then
    chmod +x "$LOCAL_BIN"
    exec "$LOCAL_BIN" "$@"
elif [ -f "$LOCAL_DEBUG" ]; then
    chmod +x "$LOCAL_DEBUG"
    exec "$LOCAL_DEBUG" "$@"
elif [ -f "$SCRIPT_DIR/../installer/Cargo.toml" ] && command -v cargo &>/dev/null; then
    echo "Running local installer via cargo..."
    exec cargo run --release --manifest-path "$SCRIPT_DIR/../installer/Cargo.toml" -- "$@"
fi

# 2. Remote download
CACHE_DIR="$HOME/Library/Caches/BadWords-bootstrap"
mkdir -p "$CACHE_DIR"
TARGET_BIN="$CACHE_DIR/badwords-installer"

echo "Downloading BadWords Installer for macOS..."

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

if [ "$downloaded" = false ]; then
    echo "Error: Could not download BadWords installer binary." >&2
    echo "Please check your internet connection or download directly from:" >&2
    echo "https://github.com/${REPO_OWNER}/${REPO_NAME}/releases" >&2
    exit 1
fi

chmod +x "$TARGET_BIN"
xattr -d com.apple.quarantine "$TARGET_BIN" 2>/dev/null || true
exec "$TARGET_BIN" "$@"
