#!/usr/bin/env bash
set -e

echo "[UPDATE] BadWords Linux Auto-Update starting..."

# Locate installation path via Resolve wrapper or default
WRAPPER="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility/BadWords.py"
INSTALL_DIR=""

if [ -f "$WRAPPER" ]; then
    INSTALL_DIR=$(grep -m1 '^INSTALL_DIR' "$WRAPPER" 2>/dev/null | cut -d'"' -f2 || true)
    if [ -z "$INSTALL_DIR" ]; then
        INSTALL_DIR=$(grep -m1 '^INSTALL_DIR' "$WRAPPER" 2>/dev/null | cut -d"'" -f2 || true)
    fi
fi

if [ -z "$INSTALL_DIR" ] || [ ! -d "$INSTALL_DIR" ]; then
    if [ -d "$HOME/.local/share/BadWords" ]; then
        INSTALL_DIR="$HOME/.local/share/BadWords"
    elif [ -d "$HOME/BadWords" ]; then
        INSTALL_DIR="$HOME/BadWords"
    else
        INSTALL_DIR="$HOME/.local/share/BadWords"
    fi
fi

echo "[INFO] Target installation directory: $INSTALL_DIR"

TMP_DIR=$(mktemp -d /tmp/bw_upd_XXXXXX)
SETUP_BIN="$TMP_DIR/badwords-setup-linux"
URL="https://github.com/veritus-git/BadWords/releases/latest/download/badwords-setup-linux"

echo "[INFO] Downloading native Linux installer from $URL..."
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$SETUP_BIN"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$SETUP_BIN" "$URL"
else
    echo "[ERROR] Neither curl nor wget found in PATH."
    rm -rf "$TMP_DIR"
    exit 1
fi

chmod +x "$SETUP_BIN"
echo "[INFO] Executing BadWords installer headlessly..."
"$SETUP_BIN" --headless --install "$INSTALL_DIR"
EXIT_CODE=$?

rm -rf "$TMP_DIR"

if [ $EXIT_CODE -eq 0 ]; then
    echo "[UPDATE] BadWords successfully updated to v4!"
    echo "[UPDATE] Please restart BadWords from DaVinci Resolve or Desktop application launcher."
else
    echo "[ERROR] Installer failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
