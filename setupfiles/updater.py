#!/usr/bin/env python3
# --- BADWORDS AUTO-UPDATE (Cross-Platform) ---
# Called by the BadWords GUI when the user clicks "Update Now".
# No prompts, no terminal needed. Exits 0 on success, 1 on failure.
# Log output goes to stdout so BadWords can capture it.

import os
import sys
import shutil
import hashlib
import tempfile
import argparse
import subprocess
import json
import urllib.request
import ssl

def log(msg): print(f"[UPDATE] {msg}")
def info(msg): print(f"[INFO]   {msg}")
def warn(msg): print(f"[WARN]   {msg}")
def err(msg): print(f"[ERROR]  {msg}", file=sys.stderr)

def md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def fetch_json(url, timeout=10):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Updater/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get_latest_release():
    # 1. Try GitHub
    try:
        data = fetch_json("https://api.github.com/repos/veritus-git/BadWords/releases/latest")
        tag = data.get("tag_name", "").strip()
        if tag:
            zip_url = f"https://github.com/veritus-git/BadWords/archive/refs/tags/{tag}.zip"
            return tag, zip_url, "GitHub"
    except Exception as e:
        warn(f"GitHub API failed: {e}")

    # 2. Try GitLab fallback
    try:
        data = fetch_json("https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases")
        if isinstance(data, list) and data:
            tag = data[0].get("tag_name", "").strip()
        elif isinstance(data, dict):
            tag = data.get("tag_name", "").strip()
        
        if tag:
            zip_url = f"https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip"
            return tag, zip_url, "GitLab"
    except Exception as e:
        warn(f"GitLab API failed: {e}")

    return None, None, None

def download(url, dest):
    if shutil.which("curl"):
        r = subprocess.run(["curl", "-fsSL", "--retry", "3", url, "-o", dest], capture_output=True)
        return r.returncode == 0 and os.path.isfile(dest)
    if shutil.which("wget"):
        r = subprocess.run(["wget", "-qO", dest, url], capture_output=True)
        return r.returncode == 0 and os.path.isfile(dest)
    if os.name == "nt":
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing"],
            capture_output=True
        )
        return r.returncode == 0 and os.path.isfile(dest)
    
    # Python fallback
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp, open(dest, 'wb') as out:
            shutil.copyfileobj(resp, out)
        return os.path.isfile(dest)
    except Exception as e:
        err(f"Python download failed: {e}")
        return False

def two_way_sync(src_paths, dst, protected_files, protected_dirs):
    for src in src_paths:
        if not os.path.isdir(src): continue
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_dir = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(dst_dir, exist_ok=True)
            for fname in files:
                s_f = os.path.join(root, fname)
                d_f = os.path.join(dst_dir, fname)
                if md5(s_f) != md5(d_f):
                    shutil.copy2(s_f, d_f)
                    info(f"Updated: {os.path.join(rel, fname) if rel != '.' else fname}")

    # Remove obsolete top-level files/dirs
    all_src_items = set()
    for src in src_paths:
        if os.path.isdir(src):
            all_src_items |= set(os.listdir(src))

    for item in os.listdir(dst):
        if item in protected_files or item in protected_dirs: continue
        if item not in all_src_items:
            full = os.path.join(dst, item)
            try:
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
                info(f"Removed obsolete: {item}")
            except Exception as e:
                warn(f"Failed to remove {item}: {e}")

def main():
    parser = argparse.ArgumentParser(description="BadWords Auto-Updater")
    parser.add_argument("--install-dir", required=True, help="Path to BadWords installation directory")
    args = parser.parse_args()

    install_dir = args.install_dir
    if not os.path.isdir(install_dir) or not os.path.isfile(os.path.join(install_dir, "main.py")):
        err(f"Valid installation not found at: {install_dir}")
        sys.exit(1)

    info(f"Target installation directory: {install_dir}")

    # 1. Fetch latest release
    info("Checking latest release...")
    tag, zip_url, source_repo = get_latest_release()
    if not tag or not zip_url:
        err("Could not determine latest version from GitHub or GitLab.")
        sys.exit(1)

    log(f"Latest release: {tag} (source: {source_repo})")

    # 2. Download and extract
    tmp_dir = tempfile.mkdtemp(prefix="bw_update_")
    zip_path = os.path.join(tmp_dir, "repo.zip")

    info(f"Downloading source from {source_repo}...")
    if not download(zip_url, zip_path):
        err("Download failed.")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    info("Extracting...")
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_dir)
    except Exception as e:
        err(f"Extraction failed: {e}")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    # Support both flat src/ and github top-level folder
    top_dirs = [d for d in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, d)) and d not in ("__MACOSX",)]
    extracted_root = None
    for r in [tmp_dir] + [os.path.join(tmp_dir, d) for d in top_dirs]:
        if os.path.isdir(os.path.join(r, "src")) and os.path.isfile(os.path.join(r, "src", "main.py")):
            extracted_root = r
            break

    if not extracted_root:
        err("Extraction failed — src/main.py not found in archive.")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        sys.exit(1)

    source_path = os.path.join(extracted_root, "src")
    assets_path = os.path.join(extracted_root, "assets")

    # 3. Sync files
    info("Syncing files...")
    protected_files = {"pref.json", "user.json", "settings.json", "badwords_debug.log"}
    protected_dirs  = {"models", "saves", "venv", "bin", "libs"}
    
    two_way_sync([source_path, assets_path], install_dir, protected_files, protected_dirs)
    log("File sync complete.")

    # 4. Pip upgrades
    venv_dir = os.path.join(install_dir, "venv")
    if os.name == "nt":
        venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
    else:
        venv_pip = os.path.join(venv_dir, "bin", "pip")

    if os.path.isfile(venv_pip):
        info("Upgrading pip packages...")
        r = subprocess.run([venv_pip, "install", "--upgrade", "faster-whisper", "stable-ts", "pypdf"], 
                           capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if "Requirement already" not in line:
                info(line)
        if r.stderr:
            for line in r.stderr.splitlines():
                if "WARNING" in line or "ERROR" in line:
                    warn(line)
        log("Packages upgraded.")
    else:
        warn("venv pip not found — skipping package upgrade.")

    # 5. Refresh libs link
    info("Refreshing libs symlink...")
    libs_link = os.path.join(install_dir, "libs")
    lib_root = os.path.join(venv_dir, "Lib" if os.name == "nt" else "lib")
    site_pkgs = None
    if os.path.isdir(lib_root):
        for root, dirs, _ in os.walk(lib_root):
            if "site-packages" in dirs:
                site_pkgs = os.path.join(root, "site-packages")
                break

    if site_pkgs:
        if os.path.islink(libs_link) or os.path.isdir(libs_link):
            try: os.remove(libs_link)
            except Exception: shutil.rmtree(libs_link, ignore_errors=True)

        if os.name == "nt":
            subprocess.run(f'mklink /J "{libs_link}" "{site_pkgs}"', shell=True, capture_output=True)
        else:
            try: os.symlink(site_pkgs, libs_link, target_is_directory=True)
            except Exception: pass

    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)
    log(f"BadWords updated to {tag} successfully!")
    log("Please restart BadWords (close and relaunch from DaVinci Resolve).")

if __name__ == "__main__":
    main()
