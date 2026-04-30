#!/usr/bin/env python3
# ============================================================
#  BadWords Installer  —  Cross-Platform GUI (Rich Terminal)
#  Copyright (c) 2026 Szymon Wolarz
# ============================================================
import argparse, hashlib, os, platform, shutil, subprocess, sys, tempfile

# ── Bootstrap rich if missing ────────────────────────────────
try:
    from rich.console import Console
    from rich.text import Text
    from rich.rule import Rule
    from rich import print as rprint
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "--quiet"])
    from rich.console import Console
    from rich.text import Text
    from rich.rule import Rule
    from rich import print as rprint

console = Console(highlight=False)

# ── Parse args ───────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--platform", default=sys.platform)
parser.add_argument("--bootstrap-python", default=sys.executable)
ARGS, _ = parser.parse_known_args()
PLAT = ARGS.platform.lower()   # "linux", "darwin"/"mac", "windows"/"win32"

# ── Platform constants ───────────────────────────────────────
APP_NAME = "BadWords"

def _default_install_dir():
    if "win" in PLAT:
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)
    if "mac" in PLAT or "darwin" in PLAT:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
    return os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

def _resolve_script_dir():
    if "win" in PLAT:
        base = os.environ.get("APPDATA", "")
        return os.path.join(base, "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility")
    if "mac" in PLAT or "darwin" in PLAT:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support",
                            "Blackmagic Design", "DaVinci Resolve", "Fusion", "Scripts", "Utility")
    return os.path.join(os.path.expanduser("~"), ".local", "share",
                        "DaVinciResolve", "Fusion", "Scripts", "Utility")

# ── UI helpers ───────────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def separator():
    console.print(Rule(style="dim white"))

def header():
    clear()
    console.print()
    console.print(Text("  BadWords Installer", style="bold white"), justify="left")
    console.print(Text("  Cross-Platform Setup — Linux / Windows / macOS", style="dim"), justify="left")
    separator()
    console.print(Text(
        "  Tip: For a fresh install or update, choose [1] and press Enter at every prompt.",
        style="green"
    ))
    separator()
    console.print()

def menu():
    console.print(Text("  Installation Options:", style="bold white"))
    console.print()
    lines = [
        ("[1]", "bold green",  "Standard Install / Update",
         "Install or update BadWords. Keeps your settings and models."),
        ("[2]", "bold cyan",   "Repair Installation",
         "Replace core files only. Keeps your settings and models."),
        ("[3]", "bold blue",   "Move Installation",
         "Relocate BadWords to a different folder."),
        ("[4]", "bold yellow", "Complete Reset",
         "Delete EVERYTHING and reinstall from scratch."),
        ("[5]", "bold red",    "Uninstall",
         "Remove BadWords completely from this system."),
    ]
    for key, style, name, desc in lines:
        t = Text()
        t.append(f"  {key} ", style=style)
        t.append(f"{name}\n", style="bright_white")
        t.append(f"      {desc}", style="dim")
        console.print(t)
        console.print()
    separator()
    console.print(Text("  [0] Exit", style="white"))
    separator()

def prompt_choice():
    console.print()
    t = Text("  Choose a menu option using your keyboard [1,2,3,4,5,0] : ", style="green")
    console.print(t, end="")
    try:
        return input().strip()
    except (KeyboardInterrupt, EOFError):
        return "0"

def pause(msg="  Press Enter to return to the menu..."):
    console.print()
    console.print(Text(msg, style="dim"))
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass

def log_info(msg):  console.print(Text(f"  [INFO] {msg}", style="green"))
def log_step(msg):  console.print(Text(f"  [....] {msg}", style="cyan"))
def log_ok(msg):    console.print(Text(f"  [ OK ] {msg}", style="bold green"))
def log_warn(msg):  console.print(Text(f"  [WARN] {msg}", style="yellow"))
def log_err(msg):   console.print(Text(f"  [ERR!] {msg}", style="bold red"))

# ── Utility ──────────────────────────────────────────────────
def md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def download(url, dest):
    if shutil.which("curl"):
        r = subprocess.run(["curl", "-fsSL", url, "-o", dest])
        return r.returncode == 0
    elif shutil.which("wget"):
        r = subprocess.run(["wget", "-qO", dest, url])
        return r.returncode == 0
    return False

def get_latest_tag():
    import json, urllib.request
    for url in [
        "https://api.github.com/repos/veritus-git/BadWords/releases/latest",
    ]:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.load(r)
                tag = data.get("tag_name", "")
                if tag:
                    return tag, f"https://github.com/veritus-git/BadWords/archive/refs/tags/{tag}.zip", "GitHub"
        except Exception:
            pass
    # GitLab fallback
    try:
        import urllib.request, json
        with urllib.request.urlopen(
            "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases", timeout=10
        ) as r:
            data = json.load(r)
            if isinstance(data, list) and data:
                tag = data[0]["tag_name"]
                return tag, f"https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip", "GitLab"
    except Exception:
        pass
    return "main", "", ""

def detect_existing_install(default_dir, resolve_script_dir):
    """Read INSTALL_DIR from wrapper if valid."""
    wrapper = os.path.join(resolve_script_dir, "BadWords.py")
    for wf in [wrapper, os.path.join(resolve_script_dir, "BadWords (Linux).py")]:
        if not os.path.isfile(wf):
            continue
        try:
            with open(wf, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("INSTALL_DIR"):
                        val = line.split("=", 1)[1].strip().strip("r\"'")
                        if os.path.isdir(val) and os.path.isfile(os.path.join(val, "main.py")):
                            return val
        except Exception:
            pass
    return None

# ── Sync logic ───────────────────────────────────────────────
def two_way_sync(src_paths, dst, protected_files, protected_dirs):
    for src in src_paths:
        if not os.path.exists(src):
            continue
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src)
            dst_dir = dst if rel == "." else os.path.join(dst, rel)
            os.makedirs(dst_dir, exist_ok=True)
            for fname in files:
                sp = os.path.join(root, fname)
                dp = os.path.join(dst_dir, fname)
                if md5(sp) != md5(dp):
                    shutil.copy2(sp, dp)
                    log_info(f"Updated: {os.path.join(rel, fname)}")
    # Cleanup obsolete
    for item in os.listdir(dst):
        dp = os.path.join(dst, item)
        in_src = any(os.path.exists(os.path.join(s, item)) for s in src_paths)
        if os.path.isdir(dp):
            if item not in protected_dirs and not in_src:
                log_warn(f"Removing obsolete dir: {item}")
                shutil.rmtree(dp)
        else:
            if item not in protected_files and not in_src:
                log_warn(f"Removing obsolete file: {item}")
                os.remove(dp)

# ── Option 1 — Standard Install/Update ───────────────────────
def option_install_update():
    header()
    console.print(Text("  ── Standard Install / Update ──", style="bold green"))
    separator()

    resolve_dir = _resolve_script_dir()
    default_dir = _default_install_dir()

    # Smart path detection
    detected = detect_existing_install(default_dir, resolve_dir)
    if detected:
        log_ok(f"Existing installation detected: {detected}")
        install_dir = detected
    else:
        install_dir = default_dir
        log_info(f"Default install path: {install_dir}")

    # Custom path prompt
    console.print()
    console.print(Text(f"  Install path: {install_dir}", style="dim"))
    console.print(Text("  Press Enter to accept, or type a custom path: ", style="cyan"), end="")
    try:
        custom = input().strip()
    except (KeyboardInterrupt, EOFError):
        custom = ""

    if custom:
        custom = os.path.expanduser(custom)
        if not custom.endswith(APP_NAME):
            custom = os.path.join(custom.rstrip("/\\"), APP_NAME)
        install_dir = custom
        log_info(f"Using custom path: {install_dir}")

    venv_dir    = os.path.join(install_dir, "venv")
    libs_link   = os.path.join(install_dir, "libs")
    models_dir  = os.path.join(install_dir, "models")
    bin_dir     = os.path.join(install_dir, "bin")
    log_file    = os.path.join(install_dir, "badwords_debug.log")

    # ── Source fetch ─────────────────────────────────────────
    separator()
    log_step("Resolving source files...")
    tag, zip_url, source_repo = get_latest_tag()
    tmp_dl = tempfile.mkdtemp()
    source_path = None
    assets_path = None
    try:
        if zip_url:
            log_step(f"Downloading latest release from {source_repo} ({tag})...")
            zip_path = os.path.join(tmp_dl, "repo.zip")
            if not download(zip_url, zip_path):
                log_err("Download failed.")
                pause()
                return
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(tmp_dl)
            extracted = next(
                (os.path.join(tmp_dl, d) for d in os.listdir(tmp_dl)
                 if os.path.isdir(os.path.join(tmp_dl, d)) and d != "__MACOSX"), None
            )
            if extracted and os.path.isdir(os.path.join(extracted, "src")):
                source_path = os.path.join(extracted, "src")
                assets_path = os.path.join(extracted, "assets")
                log_ok("Source downloaded and extracted.")
            else:
                log_err("Could not find src/ in downloaded archive.")
                pause()
                return
        if not source_path or not os.path.isfile(os.path.join(source_path, "main.py")):
            log_err("main.py not found in source. Aborting.")
            pause()
            return

        # ── GPU detection (Linux) ─────────────────────────────
        separator()
        log_step("Detecting GPU hardware...")
        has_nvidia = False
        if shutil.which("lspci"):
            r = subprocess.run(["lspci"], capture_output=True, text=True)
            has_nvidia = "nvidia" in r.stdout.lower()
        if not has_nvidia and shutil.which("lshw"):
            r = subprocess.run(["lshw", "-C", "display"], capture_output=True, text=True)
            has_nvidia = "nvidia" in r.stdout.lower()
        mode_name = "NVIDIA (CUDA 12)" if has_nvidia else "CPU (AMD/Intel)"
        nvidia_pkgs = "nvidia-cublas-cu12 nvidia-cudnn-cu12" if has_nvidia else ""
        log_ok(f"AI Engine Mode: {mode_name}")

        # ── Directory setup ───────────────────────────────────
        separator()
        log_step("Preparing directories...")
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        # ── File sync ─────────────────────────────────────────
        log_step("Syncing application files...")
        protected_files = {"pref.json", "user.json", "settings.json", "badwords_debug.log", "ffmpeg_static.tar.xz"}
        protected_dirs  = {"models", "saves", "venv", "bin", "libs"}
        src_list = [s for s in [source_path, assets_path] if s and os.path.isdir(s)]
        is_update = os.path.isdir(venv_dir)
        if is_update:
            two_way_sync(src_list, install_dir, protected_files, protected_dirs)
        else:
            for sp in src_list:
                if os.path.isdir(sp):
                    shutil.copytree(sp, install_dir, dirs_exist_ok=True)
        log_ok("Files synced.")

        # ── FFmpeg ────────────────────────────────────────────
        separator()
        ffmpeg_bin = os.path.join(bin_dir, "ffmpeg")
        if is_update and os.path.isfile(ffmpeg_bin):
            log_ok("Portable FFmpeg already present. Skipping download.")
        else:
            log_step("Downloading portable FFmpeg...")
            ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            ffmpeg_arc = os.path.join(install_dir, "ffmpeg_static.tar.xz")
            if download(ffmpeg_url, ffmpeg_arc):
                subprocess.run(["tar", "-xf", ffmpeg_arc, "-C", install_dir], check=True)
                for name in ["ffmpeg", "ffprobe"]:
                    found = None
                    for root, _, files in os.walk(install_dir):
                        if name in files and "ffmpeg-" in root:
                            found = os.path.join(root, name)
                            break
                    if found:
                        dest = os.path.join(bin_dir, name)
                        shutil.move(found, dest)
                        os.chmod(dest, 0o755)
                # Cleanup extracted dir
                for item in os.listdir(install_dir):
                    if item.startswith("ffmpeg-") and os.path.isdir(os.path.join(install_dir, item)):
                        shutil.rmtree(os.path.join(install_dir, item))
                os.remove(ffmpeg_arc)
                log_ok("FFmpeg installed.")
            else:
                log_warn("FFmpeg download failed. App may not work without it.")

        # ── Python selection for venv ─────────────────────────
        bootstrap_py = ARGS.bootstrap_python
        target_py = bootstrap_py if os.path.isfile(bootstrap_py) else sys.executable

        # Prefer system Python 3.10-3.12
        for cmd in ["python3.12", "python3.11", "python3.10", "python3"]:
            exe = shutil.which(cmd)
            if exe:
                try:
                    r = subprocess.run([exe, "-c",
                        "import sys; exit(0 if (3,10) <= sys.version_info < (3,13) else 1)"],
                        capture_output=True)
                    if r.returncode == 0:
                        target_py = exe
                        break
                except Exception:
                    pass

        # ── Venv ──────────────────────────────────────────────
        separator()
        if not os.path.isdir(venv_dir):
            log_step(f"Creating virtual environment ({target_py})...")
            subprocess.run([target_py, "-m", "venv", venv_dir], check=True)
            log_ok("Virtual environment created.")
        else:
            log_ok("Virtual environment already exists.")

        venv_py  = os.path.join(venv_dir, "bin", "python")
        venv_pip = os.path.join(venv_dir, "bin", "pip")

        # ── Dependencies ──────────────────────────────────────
        separator()
        log_step("Installing / upgrading dependencies...")
        subprocess.run([venv_py, "-m", "pip", "install", "--upgrade", "pip", "-q"], check=True)

        torch_installed = subprocess.run(
            [venv_pip, "show", "torch"], capture_output=True).returncode == 0

        if is_update and torch_installed:
            log_info("PyTorch already present. Upgrading Whisper only...")
            subprocess.run([venv_pip, "install", "--upgrade",
                "faster-whisper", "stable-ts", "pypdf", "-q"], check=True)
        elif not has_nvidia:
            log_step("Installing CPU-optimised PyTorch (smaller download)...")
            subprocess.run([venv_pip, "install", "torch", "torchaudio",
                "--index-url", "https://download.pytorch.org/whl/cpu", "-q"], check=True)
            subprocess.run([venv_pip, "install",
                "faster-whisper", "stable-ts", "pypdf", "-q"], check=True)
        else:
            log_step("Installing NVIDIA-accelerated packages...")
            subprocess.run([venv_pip, "install",
                "faster-whisper", "stable-ts", "pypdf"] + nvidia_pkgs.split(), check=True)

        pyside_ok = subprocess.run(
            [venv_py, "-c", "import PySide6"], capture_output=True).returncode == 0
        if not pyside_ok:
            log_step("Installing PySide6 GUI library...")
            subprocess.run([venv_pip, "install", "PySide6", "-q"], check=True)
        else:
            log_info("PySide6 already installed.")
        log_ok("All dependencies installed.")

        # ── Libs symlink ──────────────────────────────────────
        separator()
        log_step("Creating libs symlink...")
        site_pkgs = None
        for root, dirs, _ in os.walk(os.path.join(venv_dir, "lib")):
            if "site-packages" in dirs:
                site_pkgs = os.path.join(root, "site-packages")
                break
        if site_pkgs:
            if os.path.islink(libs_link):
                os.remove(libs_link)
            os.symlink(site_pkgs, libs_link)
            log_ok(f"libs -> {site_pkgs}")
        else:
            log_warn("Could not locate site-packages in venv.")

        # ── DaVinci Resolve wrapper ───────────────────────────
        separator()
        log_step("Configuring DaVinci Resolve integration...")
        os.makedirs(resolve_dir, exist_ok=True)

        # Remove legacy wrapper
        legacy_w = os.path.join(resolve_dir, "BadWords (Linux).py")
        if os.path.isfile(legacy_w):
            os.remove(legacy_w)
            log_info("Removed legacy wrapper.")

        wrapper_path = os.path.join(resolve_dir, "BadWords.py")
        qt_lib_dir   = os.path.join(install_dir, "libs", "PySide6", "Qt", "lib")
        libs_dir_abs = os.path.join(install_dir, "libs")
        main_script  = os.path.join(install_dir, "main.py")

        wrapper_content = f'''\
import sys, os, traceback

if sys.platform.startswith('linux'):
    import ctypes
    _qt_lib_dir = r'{qt_lib_dir}'
    _qt_preload = [
        'libQt6Core.so.6','libQt6Network.so.6','libQt6DBus.so.6',
        'libQt6Gui.so.6','libQt6Widgets.so.6','libQt6OpenGL.so.6','libQt6XcbQpa.so.6',
    ]
    if os.path.isdir(_qt_lib_dir):
        for _lib in _qt_preload:
            _p = os.path.join(_qt_lib_dir, _lib)
            if os.path.exists(_p):
                try: ctypes.CDLL(_p, mode=ctypes.RTLD_GLOBAL)
                except OSError: pass

INSTALL_DIR = r'{install_dir}'
LIBS_DIR    = r'{libs_dir_abs}'
MAIN_SCRIPT = r'{main_script}'

if os.path.exists(LIBS_DIR):
    if LIBS_DIR in sys.path: sys.path.remove(LIBS_DIR)
    sys.path.insert(0, LIBS_DIR)
if INSTALL_DIR not in sys.path:
    sys.path.append(INSTALL_DIR)

if os.path.exists(MAIN_SCRIPT):
    try:
        with open(MAIN_SCRIPT, encoding='utf-8') as f: code = f.read()
        gv = globals().copy(); gv['__file__'] = MAIN_SCRIPT
        exec(code, gv)
    except Exception as e:
        print(f'Error: {{e}}'); traceback.print_exc()
else:
    print(f'CRITICAL: {{MAIN_SCRIPT}} not found')
'''
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)
        log_ok(f"Wrapper: {wrapper_path}")

        # ── Log file ──────────────────────────────────────────
        open(log_file, "a").close()
        os.chmod(log_file, 0o666)

        # ── Done ──────────────────────────────────────────────
        separator()
        console.print()
        console.print(Text("  ✓  INSTALLATION SUCCESSFUL!", style="bold green"))
        console.print(Text(f"     Mode : {mode_name}", style="green"))
        console.print(Text(f"     Path : {install_dir}", style="green"))
        console.print(Text(f"     Log  : {log_file}", style="green"))
        console.print(Text("     Find BadWords in DaVinci Resolve → Workspace → Scripts", style="dim"))
        console.print()

    finally:
        shutil.rmtree(tmp_dl, ignore_errors=True)

    pause("  Press Enter to exit...")

# ── Dummy stubs ───────────────────────────────────────────────
def option_dummy(n, label):
    header()
    console.print(Text(f"  You selected option {n}: {label}", style="cyan"))
    console.print(Text("  (This option is not yet implemented.)", style="dim"))
    pause()

# ── Main loop ─────────────────────────────────────────────────
def main():
    while True:
        header()
        menu()
        choice = prompt_choice()
        if choice == "1":
            option_install_update()
        elif choice == "2":
            option_dummy(2, "Repair Installation")
        elif choice == "3":
            option_dummy(3, "Move Installation")
        elif choice == "4":
            option_dummy(4, "Complete Reset")
        elif choice == "5":
            option_dummy(5, "Uninstall")
        elif choice == "0":
            console.print(Text("\n  Goodbye.\n", style="dim"))
            sys.exit(0)
        else:
            header()
            console.print(Text("  Invalid option. Please try again.", style="red"))
            pause()

if __name__ == "__main__":
    main()
