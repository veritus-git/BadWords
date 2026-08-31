#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: setup.py
ROLE: Standalone BadWords Python CLI Installer & Management Engine (Fallback & Direct CLI Mode)
DESCRIPTION:
Provides robust installation, relocation, repair, reset, and uninstallation of BadWords
across Windows, Linux, and macOS without relying on compiled binaries.
"""

import os
import sys
import shutil
import subprocess
import argparse
import urllib.request
import ssl
import json
import zipfile
import tarfile
from pathlib import Path

APP_NAME = "BadWords"
APP_VERSION = "4.0.0"
GITHUB_REPO = "veritus-git/BadWords"
RELEASE_TAG_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/v{APP_VERSION}.zip"
MAIN_ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
DEV_ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/dev-v4.zip"

def log(msg): print(f"\033[94m[INFO]\033[0m  {msg}")
def ok(msg):  print(f"\033[92m[ OK ]\033[0m  {msg}")
def warn(msg): print(f"\033[93m[WARN]\033[0m  {msg}")
def err(msg): print(f"\033[91m[ERR ]\033[0m  {msg}", file=sys.stderr)
def step(pct, title, detail=""):
    d = f" - {detail}" if detail else ""
    print(f"\033[96m[STEP {pct:02d}%]\033[0m \033[1m{title}\033[0m{d}")

# ── Platform Defaults ──────────────────────────────────────────
def get_default_install_dir():
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser(r"~\AppData\Local"))
        return Path(local_appdata) / APP_NAME
    elif sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support")) / APP_NAME
    else:
        return Path(os.path.expanduser("~/.local/share")) / APP_NAME

def get_davinci_script_dirs():
    dirs = []
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", os.path.expanduser(r"~\AppData\Roaming"))
        dirs.append(Path(appdata) / r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules")
        pdata = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        dirs.append(Path(pdata) / r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules")
    elif sys.platform == "darwin":
        dirs.append(Path(os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")))
        dirs.append(Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"))
    else:
        dirs.append(Path(os.path.expanduser("~/.local/share/DaVinciResolve/Developer/Scripting/Modules")))
        dirs.append(Path("/opt/resolve/Developer/Scripting/Modules"))
    return dirs

def detect_nvidia_gpu():
    if sys.platform == "win32":
        if os.path.exists(r"C:\Windows\System32\nvcuda.dll") or os.path.exists(r"C:\Windows\System32\nvapi64.dll"):
            return True
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}")
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(key, i)
                    dev = winreg.OpenKey(key, sub)
                    desc, _ = winreg.QueryValueEx(dev, "DriverDesc")
                    if "nvidia" in str(desc).lower():
                        return True
                    i += 1
                except OSError:
                    break
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        for cmd in [["lspci"], ["lshw", "-C", "display"]]:
            try:
                out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
                if "nvidia" in out.stdout.lower():
                    return True
            except Exception:
                pass
    return False

# ── Shortcut & Integration Managers ────────────────────────────
def create_os_shortcuts(target_dir, create_desktop=True, create_menu=True):
    target_dir = Path(target_dir).resolve()
    icon_path = target_dir / "assets" / "icons" / "icon_default.ico"
    main_py = target_dir / "main.py"

    if sys.platform == "win32":
        pyw_path = target_dir / "venv" / "Scripts" / "pythonw.exe"
        ps_commands = ["$ws = New-Object -ComObject WScript.Shell;"]
        if create_desktop:
            ps_commands.append(f"$s1 = $ws.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\BadWords.lnk'); $s1.TargetPath = '{pyw_path}'; $s1.Arguments = '\"{main_py}\"'; $s1.WorkingDirectory = '{target_dir}'; $s1.IconLocation = '{icon_path},0'; $s1.Save();")
        if create_menu:
            ps_commands.append(f"$s2 = $ws.CreateShortcut([Environment]::GetFolderPath('Programs') + '\\BadWords.lnk'); $s2.TargetPath = '{pyw_path}'; $s2.Arguments = '\"{main_py}\"'; $s2.WorkingDirectory = '{target_dir}'; $s2.IconLocation = '{icon_path},0'; $s2.Save();")
        
        full_script = " ".join(ps_commands)
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", full_script], capture_output=True)
        
        # Register in Windows Add/Remove Programs (HKCU)
        try:
            import winreg
            hkcu = winreg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\BadWords"
            key = winreg.CreateKey(hkcu, key_path)
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "BadWords")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Szymon Wolarz")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target_dir))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(icon_path))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'python "{target_dir / "setupfiles" / "setup.py"}" --uninstall "{target_dir}"')
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, f"https://github.com/{GITHUB_REPO}")
            winreg.CloseKey(key)
        except Exception as e:
            warn(f"Could not register in Windows Registry: {e}")

    elif sys.platform.startswith("linux"):
        py_path = target_dir / "venv" / "bin" / "python"
        png_icon = target_dir / "assets" / "icons" / "icon_default.png"
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=BadWords
Comment=AI Automated Profanity & Silence Detection for DaVinci Resolve
Exec="{py_path}" "{main_py}"
Path={target_dir}
Icon={png_icon}
Terminal=false
Categories=AudioVideo;AudioVideoEditing;
StartupWMClass=BadWords
Keywords=davinci;resolve;subtitles;ai;whisper;
"""
        home = Path.home()
        apps_dir = home / ".local" / "share" / "applications"
        apps_dir.mkdir(parents=True, exist_ok=True)
        (apps_dir / "badwords.desktop").write_text(desktop_content, encoding="utf-8")

        if create_desktop:
            dt_dir = home / "Desktop"
            if dt_dir.exists():
                dt_file = dt_dir / "badwords.desktop"
                dt_file.write_text(desktop_content, encoding="utf-8")
                dt_file.chmod(0o755)
                subprocess.run(["gio", "set", str(dt_file), "metadata::trusted", "true"], capture_output=True)

        subprocess.run(["update-desktop-database", str(apps_dir)], capture_output=True)

def remove_os_shortcuts(target_dir=None):
    if sys.platform == "win32":
        try:
            home = Path.home()
            (home / "Desktop" / "BadWords.lnk").unlink(missing_ok=True)
            appdata = os.environ.get("APPDATA")
            if appdata:
                (Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "BadWords.lnk").unlink(missing_ok=True)
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
            winreg.DeleteKey(key, "BadWords")
            winreg.CloseKey(key)
        except Exception:
            pass
    elif sys.platform.startswith("linux"):
        home = Path.home()
        (home / ".local" / "share" / "applications" / "badwords.desktop").unlink(missing_ok=True)
        (home / "Desktop" / "badwords.desktop").unlink(missing_ok=True)

def update_davinci_wrappers(target_dir):
    target_dir = Path(target_dir).resolve()
    main_py = target_dir / "main.py"
    if sys.platform == "win32":
        py_bin = target_dir / "venv" / "Scripts" / "python.exe"
    else:
        py_bin = target_dir / "venv" / "bin" / "python"

    wrapper_code = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
# BadWords DaVinci Resolve Script Wrapper
import os
import sys
import subprocess

TARGET_PY = r"{py_bin}"
MAIN_SCRIPT = r"{main_py}"
APP_DIR = r"{target_dir}"

if __name__ == "__main__":
    if os.path.isfile(TARGET_PY) and os.path.isfile(MAIN_SCRIPT):
        env = os.environ.copy()
        env["PYTHONPATH"] = APP_DIR
        subprocess.Popen([TARGET_PY, MAIN_SCRIPT], cwd=APP_DIR, env=env)
    else:
        print("[BadWords] Installation directory not found. Please reinstall BadWords.")
"""
    count = 0
    for d in get_davinci_script_dirs():
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / "BadWords.py").write_text(wrapper_code, encoding="utf-8")
            count += 1
        except Exception:
            pass
    if count > 0:
        ok(f"DaVinci Resolve script wrapper updated in {count} directory/ies.")

def remove_davinci_wrappers():
    for d in get_davinci_script_dirs():
        w = d / "BadWords.py"
        if w.exists():
            try:
                w.unlink()
                ok(f"Removed DaVinci wrapper from: {w}")
            except Exception:
                pass

# ── Core Engine Tasks ──────────────────────────────────────────
def find_local_repo(hint_path=None):
    candidates = [hint_path, ".", "..", "../..", "/mnt/dump/BadWords"]
    for c in candidates:
        if not c:
            continue
        p = Path(c).resolve()
        if (p / "src" / "main.py").is_file() and (p / "assets").is_dir():
            return p
    return None

def download_and_extract_source(target_dir):
    step(25, "Fetching BadWords source code...", "Connecting to GitHub repository")
    temp_zip = target_dir / "temp_source.zip"
    
    urls = [RELEASE_TAG_URL, MAIN_ZIP_URL, DEV_ZIP_URL]
    success = False
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for url in urls:
        try:
            log(f"Trying: {url}")
            req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Setup-CLI"})
            with urllib.request.urlopen(req, context=ctx, timeout=20) as resp, open(temp_zip, "wb") as out:
                shutil.copyfileobj(resp, out)
            if temp_zip.is_file() and temp_zip.stat().st_size > 5000:
                success = True
                break
        except Exception as e:
            warn(f"Failed to fetch from {url}: {e}")

    if not success:
        raise RuntimeError("Could not download BadWords source code from GitHub. Check your internet connection.")

    step(35, "Extracting application files...", "Deploying source code and assets")
    with zipfile.ZipFile(temp_zip, "r") as z:
        for member in z.infolist():
            parts = member.filename.split("/")
            if len(parts) > 1 and parts[1]:
                rel_path = "/".join(parts[1:])
                dest = target_dir / rel_path
                if member.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(member) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
    temp_zip.unlink(missing_ok=True)
    ok("Source code deployed.")

def ensure_ffmpeg(target_dir):
    bin_dir = target_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    target_ff = bin_dir / ffmpeg_exe

    if target_ff.is_file():
        ok("Portable FFmpeg binary already present.")
        return

    # Check system ffmpeg
    sys_ff = shutil.which("ffmpeg")
    if sys_ff and os.path.isfile(sys_ff):
        shutil.copy(sys_ff, target_ff)
        if sys.platform != "win32":
            target_ff.chmod(0o755)
        ok("Copied system FFmpeg as local runtime.")
        return

    step(45, "Configuring portable media engine...", "Downloading portable FFmpeg")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    if sys.platform == "win32":
        url = "https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip"
        zip_path = target_dir / "ffmpeg_temp.zip"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Setup"})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(zip_path, "wb") as out:
                shutil.copyfileobj(resp, out)
            with zipfile.ZipFile(zip_path, "r") as z:
                for name in z.namelist():
                    if name.endswith("bin/ffmpeg.exe") or name.endswith("ffmpeg.exe"):
                        with z.open(name) as src, open(target_ff, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        break
            zip_path.unlink(missing_ok=True)
            ok("FFmpeg for Windows installed.")
            return
        except Exception as e:
            warn(f"Could not download Windows FFmpeg: {e}")

    elif sys.platform.startswith("linux"):
        url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        tar_path = target_dir / "ffmpeg.tar.xz"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BadWords-Setup"})
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(tar_path, "wb") as out:
                shutil.copyfileobj(resp, out)
            subprocess.run(["tar", "-xf", str(tar_path), "-C", str(target_dir)], check=True)
            for p in target_dir.glob("ffmpeg-*"):
                if p.is_dir() and (p / "ffmpeg").is_file():
                    shutil.copy(p / "ffmpeg", target_ff)
                    target_ff.chmod(0o755)
                    shutil.rmtree(p, ignore_errors=True)
                    break
            tar_path.unlink(missing_ok=True)
            ok("FFmpeg for Linux installed.")
            return
        except Exception as e:
            warn(f"Could not download Linux FFmpeg: {e}")

def setup_python_environment(target_dir, base_python=None):
    venv_dir = target_dir / "venv"
    step(55, "Configuring Python virtual environment...", "Setting up isolated runtime")
    
    py_exec = base_python or sys.executable
    if not venv_dir.exists():
        log(f"Creating virtual environment using {py_exec}...")
        res = subprocess.run([py_exec, "-m", "venv", str(venv_dir)], capture_output=True)
        if res.returncode != 0:
            subprocess.run([py_exec, "-m", "virtualenv", str(venv_dir)], check=True)
        ok("Virtual environment created.")
    else:
        ok("Virtual environment already exists.")

    if sys.platform == "win32":
        v_py = venv_dir / "Scripts" / "python.exe"
    else:
        v_py = venv_dir / "bin" / "python"

    step(65, "Upgrading core package manager...", "Updating pip, setuptools & wheel")
    subprocess.run([str(v_py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel", "--quiet"], check=True)

    step(75, "Installing GUI framework...", "Configuring PySide6 Qt6 engine")
    subprocess.run([str(v_py), "-m", "pip", "install", "PySide6", "--quiet"], check=True)

    step(85, "Installing AI speech engine...", "Configuring Faster-Whisper, PyPDF & ONNX")
    subprocess.run([str(v_py), "-m", "pip", "install", "faster-whisper", "pypdf", "--quiet"], check=True)

    if detect_nvidia_gpu():
        step(90, "Configuring GPU acceleration...", "Installing NVIDIA CUDA 12 libraries (cuBLAS, cuDNN)")
        subprocess.run([str(v_py), "-m", "pip", "install", "nvidia-cublas-cu12", "nvidia-cudnn-cu12", "--quiet"], check=False)
        ok("NVIDIA CUDA 12 hardware acceleration enabled.")

# ── Primary Operations ─────────────────────────────────────────
def run_install(target_dir, local_repo=None):
    target_dir = Path(target_dir).resolve()
    print(f"\n\033[1m=== BadWords {APP_VERSION} Installation ===\033[0m")
    log(f"Destination: {target_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    repo = find_local_repo(local_repo)

    if repo and repo != target_dir:
        step(25, "Deploying local application files...", f"Copying from {repo}")
        for item in ["src", "assets", "setupfiles", "config.py", "main.py", "LICENSE", "README.md"]:
            src_item = repo / item
            dst_item = target_dir / item
            if src_item.is_dir():
                shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
            elif src_item.is_file():
                shutil.copy(src_item, dst_item)
        ok("Local application files deployed.")
    elif not (target_dir / "main.py").is_file():
        download_and_extract_source(target_dir)

    ensure_ffmpeg(target_dir)
    setup_python_environment(target_dir)
    
    step(95, "Configuring system integrations...", "Creating DaVinci wrapper & OS shortcuts")
    update_davinci_wrappers(target_dir)
    create_os_shortcuts(target_dir)
    
    print(f"\n\033[92m[✓] BadWords {APP_VERSION} installed successfully!\033[0m")
    print(f"    Location: {target_dir}")
    print("    You can launch BadWords from your Desktop, Start Menu, or inside DaVinci Resolve (Workspace > Scripts > BadWords).\n")

def run_repair(target_dir):
    target_dir = Path(target_dir).resolve()
    print(f"\n\033[1m=== Repairing BadWords in {target_dir} ===\033[0m")
    if not target_dir.exists():
        err("Target directory does not exist.")
        return False

    ensure_ffmpeg(target_dir)
    setup_python_environment(target_dir)
    update_davinci_wrappers(target_dir)
    create_os_shortcuts(target_dir)
    ok("Repair completed successfully.")
    return True

def run_move(src_dir, dst_dir):
    src_dir = Path(src_dir).resolve()
    dst_dir = Path(dst_dir).resolve()
    print(f"\n\033[1m=== Moving BadWords ===\033[0m")
    log(f"From: {src_dir}")
    log(f"To:   {dst_dir}")

    if not src_dir.exists():
        err("Source directory does not exist.")
        return False

    dst_dir.mkdir(parents=True, exist_ok=True)
    step(30, "Transferring files...", "Copying application and packages")
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    step(75, "Updating virtual environment and wrappers...", "Fixing runtime paths")
    update_davinci_wrappers(dst_dir)
    create_os_shortcuts(dst_dir)

    step(90, "Cleaning old directory...", "Removing source files")
    shutil.rmtree(src_dir, ignore_errors=True)
    
    ok("Relocation completed successfully.")
    return True

def run_uninstall(target_dir):
    target_dir = Path(target_dir).resolve()
    print(f"\n\033[1m=== Uninstalling BadWords ===\033[0m")
    log(f"Removing from: {target_dir}")

    step(30, "Removing system integrations...", "Cleaning DaVinci wrappers & shortcuts")
    remove_davinci_wrappers()
    remove_os_shortcuts(target_dir)

    step(70, "Deleting application directory...", "Removing files and virtual environment")
    if target_dir.exists():
        shutil.rmtree(target_dir, ignore_errors=True)

    ok("BadWords has been completely uninstalled from this computer.")
    return True

# ── Interactive CLI Menu ───────────────────────────────────────
def interactive_menu():
    default_dir = get_default_install_dir()
    while True:
        print("\n" + "="*50)
        print(f"      BadWords {APP_VERSION} Setup & Management CLI")
        print("="*50)
        print(f"  [1] Install / Update BadWords")
        print(f"  [2] Move Installation to Another Directory")
        print(f"  [3] Repair Environment & Fix Integrations")
        print(f"  [4] Reset Application (Clean Reinstall)")
        print(f"  [5] Uninstall BadWords")
        print(f"  [6] Exit")
        print("="*50)

        choice = input("\nSelect an option [1-6]: ").strip()
        if choice == "1":
            custom_path = input(f"Install location [{default_dir}]: ").strip()
            target = Path(custom_path) if custom_path else default_dir
            run_install(target)
            break
        elif choice == "2":
            src = input(f"Current location [{default_dir}]: ").strip() or str(default_dir)
            dst = input("New destination path: ").strip()
            if dst:
                run_move(src, dst)
            break
        elif choice == "3":
            loc = input(f"BadWords location to repair [{default_dir}]: ").strip() or str(default_dir)
            run_repair(loc)
            break
        elif choice == "4":
            loc = input(f"BadWords location to reset [{default_dir}]: ").strip() or str(default_dir)
            run_uninstall(loc)
            run_install(loc)
            break
        elif choice == "5":
            loc = input(f"BadWords location to uninstall [{default_dir}]: ").strip() or str(default_dir)
            confirm = input(f"Are you sure you want to completely remove BadWords from {loc}? (y/N): ").strip().lower()
            if confirm == "y":
                run_uninstall(loc)
            break
        elif choice == "6":
            print("Setup closed.")
            break

# ── Entry Point ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f"BadWords {APP_VERSION} CLI Installer")
    parser.add_argument("--install", nargs="?", const="", help="Install BadWords to specified directory")
    parser.add_argument("--repair", nargs="?", const="", help="Repair BadWords installation")
    parser.add_argument("--uninstall", nargs="?", const="", help="Uninstall BadWords")
    parser.add_argument("--move", nargs=2, metavar=("SRC", "DST"), help="Move BadWords to another folder")
    parser.add_argument("--reset", nargs="?", const="", help="Clean reinstall BadWords")
    parser.add_argument("--local-repo", help="Path to local repository clone")
    parser.add_argument("--quiet", action="store_true", help="Non-interactive quiet execution")

    args = parser.parse_args()
    default_dir = get_default_install_dir()

    if args.install is not None:
        target = Path(args.install) if args.install else default_dir
        run_install(target, args.local_repo)
    elif args.repair is not None:
        target = Path(args.repair) if args.repair else default_dir
        run_repair(target)
    elif args.uninstall is not None:
        target = Path(args.uninstall) if args.uninstall else default_dir
        run_uninstall(target)
    elif args.move:
        run_move(args.move[0], args.move[1])
    elif args.reset is not None:
        target = Path(args.reset) if args.reset else default_dir
        run_uninstall(target)
        run_install(target, args.local_repo)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
