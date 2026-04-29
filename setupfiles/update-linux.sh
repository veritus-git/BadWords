#!/bin/bash
# --- BADWORDS AUTO-UPDATE (Linux, non-interactive) ---
# Called by the BadWords GUI when the user clicks "Update Now".
# No prompts, no terminal needed. Exits 0 on success, 1 on failure.
# Log output goes to stdout so BadWords can capture it.

set -e

# ── Colors (safe even without a TTY — used only in log lines) ──────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${GREEN}[UPDATE] $*${NC}"; }
info() { echo -e "${CYAN}[INFO]   $*${NC}"; }
warn() { echo -e "${YELLOW}[WARN]   $*${NC}"; }
err()  { echo -e "${RED}[ERROR]  $*${NC}" >&2; }

# ── 1. Locate existing installation ────────────────────────────────────────
APP_NAME="BadWords"
RESOLVE_SCRIPT_DIR="$HOME/.local/share/DaVinciResolve/Fusion/Scripts/Utility"
WRAPPER_FILE="$RESOLVE_SCRIPT_DIR/BadWords.py"
LEGACY_WRAPPER="$RESOLVE_SCRIPT_DIR/BadWords (Linux).py"
DEFAULT_INSTALL_DIR="$HOME/.local/share/$APP_NAME"

INSTALL_DIR="$DEFAULT_INSTALL_DIR"

# Try reading the path stored in the wrapper
CHECK_WRAPPER=""
[ -f "$WRAPPER_FILE" ]  && CHECK_WRAPPER="$WRAPPER_FILE"
[ -f "$LEGACY_WRAPPER" ] && CHECK_WRAPPER="$LEGACY_WRAPPER"

if [ -n "$CHECK_WRAPPER" ]; then
    DETECTED=$(grep -E "^INSTALL_DIR\s*=\s*" "$CHECK_WRAPPER" 2>/dev/null | head -n1 \
               | sed -E "s/^INSTALL_DIR\s*=\s*r?['\"](.*)['\"]/\1/")
    if [ -n "$DETECTED" ] && [ -d "$DETECTED" ] && [ -f "$DETECTED/main.py" ]; then
        INSTALL_DIR="$DETECTED"
        info "Detected installation at: $INSTALL_DIR"
    else
        warn "Wrapper path invalid or missing. Using default: $INSTALL_DIR"
    fi
fi

if [ ! -f "$INSTALL_DIR/main.py" ]; then
    err "No valid BadWords installation found at '$INSTALL_DIR'. Aborting."
    exit 1
fi

VENV_DIR="$INSTALL_DIR/venv"
VENV_PIP="$VENV_DIR/bin/pip"
LIBS_LINK="$INSTALL_DIR/libs"

# ── 2. Fetch latest tag — GitHub first, GitLab fallback ─────────────────────
info "Checking latest release..."
LATEST_TAG=""
REPO_ZIP_URL=""
SOURCE_REPO=""

# GitHub
LATEST_TAG=$(curl -fsSL --connect-timeout 10 \
    "https://api.github.com/repos/veritus-git/BadWords/releases/latest" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("tag_name",""))' \
    2>/dev/null || true)

if [ -n "$LATEST_TAG" ]; then
    REPO_ZIP_URL="https://github.com/veritus-git/BadWords/archive/refs/tags/${LATEST_TAG}.zip"
    SOURCE_REPO="GitHub"
else
    warn "GitHub unavailable, trying GitLab..."
    LATEST_TAG=$(curl -fsSL --connect-timeout 10 \
        "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases" \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["tag_name"] if isinstance(d,list) and d else "")' \
        2>/dev/null || true)
    if [ -n "$LATEST_TAG" ]; then
        REPO_ZIP_URL="https://gitlab.com/badwords/BadWords/-/archive/${LATEST_TAG}/BadWords-${LATEST_TAG}.zip"
        SOURCE_REPO="GitLab"
    fi
fi

if [ -z "$LATEST_TAG" ] || [ -z "$REPO_ZIP_URL" ]; then
    err "Could not determine latest version from GitHub or GitLab."
    exit 1
fi

log "Latest release: $LATEST_TAG  (source: $SOURCE_REPO)"

# ── 3. Download & extract ────────────────────────────────────────────────────
TMP_DIR=$(mktemp -d)
ZIP_PATH="$TMP_DIR/repo.zip"

info "Downloading source from $SOURCE_REPO..."
if command -v curl &>/dev/null; then
    curl -fsSL "$REPO_ZIP_URL" -o "$ZIP_PATH"
elif command -v wget &>/dev/null; then
    wget -qO "$ZIP_PATH" "$REPO_ZIP_URL"
else
    err "Neither curl nor wget found."
    rm -rf "$TMP_DIR"
    exit 1
fi

info "Extracting..."
if command -v unzip &>/dev/null; then
    unzip -q -o "$ZIP_PATH" -d "$TMP_DIR"
else
    python3 -m zipfile -e "$ZIP_PATH" "$TMP_DIR"
fi

EXTRACTED_DIR=$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)
SOURCE_PATH="$EXTRACTED_DIR/src"
ASSETS_PATH="$EXTRACTED_DIR/assets"

if [ ! -f "$SOURCE_PATH/main.py" ]; then
    err "Extraction failed — src/main.py not found."
    rm -rf "$TMP_DIR"
    exit 1
fi

# ── 4. Sync files (update-only: additive + obsolete cleanup) ────────────────
info "Syncing files..."
python3 -c "
import os, shutil, hashlib

def get_hash(p):
    try:
        with open(p, 'rb') as f: return hashlib.md5(f.read()).hexdigest()
    except: return None

src_paths = [p for p in ['$SOURCE_PATH', '$ASSETS_PATH'] if os.path.isdir(p)]
dst = '$INSTALL_DIR'

for src in src_paths:
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        d_dir = dst if rel == '.' else os.path.join(dst, rel)
        os.makedirs(d_dir, exist_ok=True)
        for f in files:
            s_f = os.path.join(root, f)
            d_f = os.path.join(d_dir, f)
            if get_hash(s_f) != get_hash(d_f):
                shutil.copy2(s_f, d_f)
                print(f'  Updated: {os.path.join(rel,f) if rel!=\".\" else f}')

# Remove obsolete top-level files/dirs
protected_files = {'pref.json','user.json','settings.json','badwords_debug.log','ffmpeg_static.tar.xz'}
protected_dirs  = {'models','saves','venv','bin','libs'}
all_src_items   = set()
for src in src_paths:
    all_src_items |= set(os.listdir(src))

for item in os.listdir(dst):
    if item in protected_files or item in protected_dirs: continue
    if item not in all_src_items:
        full = os.path.join(dst, item)
        if os.path.isdir(full): shutil.rmtree(full)
        else: os.remove(full)
        print(f'  Removed obsolete: {item}')
"

log "File sync complete."

# ── 5. Upgrade pip packages ─────────────────────────────────────────────────
if [ -f "$VENV_PIP" ]; then
    info "Upgrading pip packages..."
    "$VENV_PIP" install --upgrade faster-whisper stable-ts pypdf 2>&1 | grep -v "^Requirement already"
    log "Packages upgraded."
else
    warn "venv pip not found — skipping package upgrade."
fi

# ── 6. Refresh libs symlink ─────────────────────────────────────────────────
if [ -d "$VENV_DIR" ]; then
    SITE_PACKAGES=$(find "$VENV_DIR/lib" -name "site-packages" -type d 2>/dev/null | head -n1)
    if [ -n "$SITE_PACKAGES" ]; then
        [ -L "$LIBS_LINK" ] && rm "$LIBS_LINK"
        ln -s "$SITE_PACKAGES" "$LIBS_LINK"
        info "libs symlink refreshed."
    fi
fi

# ── Cleanup ──────────────────────────────────────────────────────────────────
rm -rf "$TMP_DIR"

log "BadWords updated to $LATEST_TAG successfully!"
log "Please restart BadWords (close and relaunch from DaVinci Resolve)."
exit 0
