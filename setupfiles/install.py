#!/usr/bin/env python3
# ============================================================
#  BadWords Installer  —  Cross-Platform GUI (Rich Terminal)
#  Copyright (c) 2026 Szymon Wolarz
# ============================================================
import argparse, hashlib, os, shutil, subprocess, sys, tempfile, threading, time

# ── Bootstrap rich if missing ────────────────────────────────
try:
    from rich.console import Console
    from rich.text import Text
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "--quiet"])
    from rich.console import Console
    from rich.text import Text

# ── Terminal dimensions & layout ──────────────────────────────
TERM_W = 88
TERM_H = 30
PAD    = "    "   # 4-space left margin

console = Console(width=TERM_W, highlight=False)

# ── Parse args ───────────────────────────────────────────────
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--platform", default=sys.platform)
parser.add_argument("--bootstrap-python", default=sys.executable)
ARGS, _ = parser.parse_known_args()
PLAT = ARGS.platform.lower()

# ── Platform helpers ─────────────────────────────────────────
APP_NAME = "BadWords"

def _default_install_dir():
    if PLAT.startswith("win"):
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), APP_NAME)
    if "mac" in PLAT or "darwin" in PLAT:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", APP_NAME)
    return os.path.join(os.path.expanduser("~"), ".local", "share", APP_NAME)

def _resolve_script_dirs():
    """Return all plausible DaVinci Resolve Scripts/Utility dirs on this system.
    Windows has many installation variants; we probe all of them."""
    results = []

    if PLAT.startswith("win"):
        appdata      = os.environ.get("APPDATA", "")
        localappdata = os.environ.get("LOCALAPPDATA", "")
        progdata     = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        bmd_base     = os.path.join("Blackmagic Design", "DaVinci Resolve")

        bases = []
        if appdata:
            bases.append(os.path.join(appdata, bmd_base, "Support"))
            bases.append(os.path.join(appdata, bmd_base))
        if progdata:
            bases.append(os.path.join(progdata, bmd_base, "Support"))
        if localappdata:
            pkg_root = os.path.join(localappdata, "Packages")
            if os.path.isdir(pkg_root):
                for pkg in os.listdir(pkg_root):
                    if pkg.lower().startswith("blackmagicdesign.davinciresolve"):
                        store_base = os.path.join(pkg_root, pkg, "LocalState", "AppDataRoaming", "Blackmagic Design", "DaVinci Resolve")
                        bases.append(os.path.join(store_base, "Support"))
                        bases.append(store_base)
        
        subs = ["Utility", "Resolve", "Comp", "Edit", ""]
        for b in bases:
            for s in subs:
                p = os.path.join(b, "Fusion", "Scripts", s) if s else os.path.join(b, "Fusion", "Scripts")
                results.append(p)

    elif "mac" in PLAT or "darwin" in PLAT:
        bases = [
            os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve"),
            os.path.join("/", "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve")
        ]
        subs = ["Utility", "Comp", "Edit", "Resolve", ""]
        for b in bases:
            for s in subs:
                p = os.path.join(b, "Fusion", "Scripts", s) if s else os.path.join(b, "Fusion", "Scripts")
                results.append(p)

    else:
        # Linux
        bases = [
            os.path.join(os.path.expanduser("~"), ".local", "share", "DaVinciResolve"),
            os.path.join("/", "opt", "resolve", "libs")  # the prompt said /opt/resolve/libs/fusion/Scripts
        ]
        subs = ["Utility", "Edit", "Comp", "Resolve", ""]
        for b in bases:
            for s in subs:
                # Linux Resolve paths sometimes use lowercase 'fusion' or uppercase 'Fusion'
                # The user provided fusion/Scripts so we use that but fallback to Fusion/Scripts is good practice
                # For safety, we will append both variants for the base subdirs.
                p1 = os.path.join(b, "fusion", "Scripts", s) if s else os.path.join(b, "fusion", "Scripts")
                p2 = os.path.join(b, "Fusion", "Scripts", s) if s else os.path.join(b, "Fusion", "Scripts")
                results.append(p1)
                results.append(p2)

    # Remove duplicates while preserving order
    seen, unique = set(), []
    for d in results:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique

_LOG_MESSAGES = []
_DEBUG_LOG_FILE = None

def debug_log(msg):
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{now}] {msg}"
    _LOG_MESSAGES.append(entry)
    if _DEBUG_LOG_FILE:
        try:
            with open(_DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except: pass

# ── Cancellation ─────────────────────────────────────────────
class UserCancelled(Exception):
    pass

# ── Single-keypress input ─────────────────────────────────────
def getch():
    """Read one keypress immediately (no Enter needed). Returns char or 'ESC'."""
    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getch()
            if ch in (b"\x00", b"\xe0"):
                msvcrt.getch()
                continue
            if ch in (b"\x1b", b"\x03"):
                return "ESC"
            try:
                return ch.decode("utf-8")
            except Exception:
                continue
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch in ("\x1b", "\x03"):
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    sys.stdin.read(10)
                return "ESC"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def readline_with_esc(show_cursor=True):
    """Read a line character-by-character. ESC/Ctrl+C cancels → raises UserCancelled."""
    if os.name == "nt":
        import msvcrt
        buf = []
        while True:
            ch = msvcrt.getch()
            if ch in (b"\x1b", b"\x03"):
                raise UserCancelled()
            if ch in (b"\r", b"\n"):
                sys.stdout.write("\r\n"); sys.stdout.flush()
                return "".join(buf)
            if ch in (b"\x08", b"\x7f"):
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b"); sys.stdout.flush()
                continue
            try:
                c = ch.decode("utf-8")
                if c.isprintable():
                    buf.append(c)
                    sys.stdout.write(c); sys.stdout.flush()
            except Exception:
                pass
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf = []
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\x1b", "\x03"):
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        sys.stdin.read(10)
                    raise UserCancelled()
                if ch in ("\r", "\n"):
                    sys.stdout.write("\r\n"); sys.stdout.flush()
                    return "".join(buf)
                if ch in ("\x7f", "\x08"):
                    if buf:
                        buf.pop()
                        sys.stdout.write("\b \b"); sys.stdout.flush()
                    continue
                if ch.isprintable():
                    buf.append(ch)
                    sys.stdout.write(ch); sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return "".join(buf)

# ── UI ───────────────────────────────────────────────────────
def _resize(w=TERM_W, h=TERM_H):
    """Resize terminal window."""
    if os.name == "nt":
        os.system(f"mode con cols={w} lines={h}")
    else:
        # ANSI resize works in Terminal.app (macOS) and most Linux terminals.
        # Use a slightly smaller height on macOS due to the menu bar.
        mac_h = max(h - 2, 24) if ("darwin" in PLAT or "mac" in PLAT) else h
        sys.stdout.write(f"\033[8;{mac_h};{w}t")
        sys.stdout.flush()
    time.sleep(0.2)

def _set_title(title="BadWords Setup"):
    """Set the terminal window title."""
    if os.name == "nt":
        os.system(f"title {title}")
    else:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def header():
    clear()
    console.print()
    console.print(Text("BadWords Installer", style="bold white"), justify="center", no_wrap=True)
    console.print(Text("Cross-Platform Setup  —  Linux / Windows / macOS", style="dim"), justify="center", no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}Tip: For a fresh install or update, choose [1] and press Enter at every prompt.", style="green"), no_wrap=True)
    console.print()

def menu():
    console.print(Text(f"{PAD}Installation Options:", style="bold white"), no_wrap=True)
    console.print()
    items = [
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
    for key, style, name, desc in items:
        t = Text(no_wrap=True)
        t.append(f"{PAD}{key} ", style=style)
        t.append(f"{name}\n", style="bright_white")
        t.append(f"{PAD}    {desc}", style="dim")
        console.print(t, no_wrap=True)
        console.print()
    console.print(Text(f"{PAD}[0] Exit", style="white"), no_wrap=True)
    console.print()

def prompt_choice():
    """Single keypress — no Enter needed. Scrollbar stays locked during menu."""
    console.print()
    console.print(Text(f"{PAD}Choose a menu option [1,2,3,4,5,0] : ", style="green"), end="", no_wrap=True)
    sys.stdout.flush()
    ch = getch()
    console.print(Text(ch if ch != "ESC" else "ESC", style="dim"))
    return ch

def pause(msg=None):
    msg = msg or f"{PAD}Press Enter to return to the menu..."
    _set_scrollbar(True)   # let user scroll while reading results
    console.print()
    console.print(Text(msg, style="dim"), no_wrap=True)
    try:
        readline_with_esc()
    except (UserCancelled, KeyboardInterrupt):
        pass

def log_info(msg):  _log_print("[INFO]", msg, "green",      "green")
def log_step(msg):  _log_print("[....]", msg, "cyan",       "cyan")
def log_ok(msg):    _log_print("[ OK ]", msg, "bold green",  "bold green")
def log_warn(msg):
    _log_print("[WARN]", msg, "yellow", "yellow")
    if _DEBUG_LOG_FILE: _log_print("[INFO]", f"More info in: {_DEBUG_LOG_FILE}", "dim", "dim")

def log_err(msg):
    _log_print("[ERR!]", msg, "bold red", "bold red")
    if _DEBUG_LOG_FILE: _log_print("[INFO]", f"More info in: {_DEBUG_LOG_FILE}", "dim", "dim")

# Continuation lines are indented to align with the text start,
# not crammed at the left edge.
_LOG_PFX_LEN = len(PAD) + 7   # "    [TAG] " = 4 + 7 chars

def _log_print(tag, msg, tag_style, msg_style):
    debug_log(f"{tag} {msg}")
    prefix    = f"{PAD}{tag} "
    available = TERM_W - 2 * _LOG_PFX_LEN  # symmetric right margin
    indent    = " " * _LOG_PFX_LEN

    if len(msg) <= available:
        # Fits on first line — print normally
        t = Text(no_wrap=True)
        t.append(prefix, style=tag_style)
        t.append(msg, style=msg_style)
        console.print(t, no_wrap=True)
        return

    # Break at last space within available window (word-wrap)
    bp = msg.rfind(' ', 0, available + 1)
    if bp > 0:
        first = msg[:bp]
        rest  = msg[bp + 1:]
    else:
        # No space in range: print everything on the tag line (terminal handles overflow)
        first = msg
        rest  = ""

    # First line (tag prefix + first chunk)
    t = Text(no_wrap=True)
    t.append(prefix, style=tag_style)
    t.append(first,  style=msg_style)
    console.print(t, no_wrap=True)

    # Continuation: ONE print call with soft_wrap=True.
    # Rich outputs the text as-is without inserting any \n mid-string.
    # The terminal soft-wraps if needed — clipboard selection gives the
    # full unbroken string (no embedded newlines or indent spaces).
    if rest:
        console.print(Text(indent + rest, style=msg_style), soft_wrap=True)

# ── Scrollbar control (Windows CMD) ──────────────────────────
def _set_scrollbar(enabled: bool):
    """Keep CMD scroll buffer always large so content is never lost.
    The 'enabled' flag is kept for API compatibility but we never shrink the buffer."""
    if os.name != "nt":
        return
    try:
        import ctypes
        STD_OUT = ctypes.windll.kernel32.GetStdHandle(-11)
        # Always 9999 — never shrink to TERM_H (that would cut history)
        ctypes.windll.kernel32.SetConsoleScreenBufferSize(STD_OUT, TERM_W | (9999 << 16))
    except Exception:
        pass

# ── Spinner (runs in background thread during heavy ops) ──────
_ANSI_CYAN  = "\033[36m"
_ANSI_RESET = "\033[0m"

class Spinner:
    FRAMES = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]

    def __init__(self, label):
        self.label   = label
        self._done   = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while not self._done.is_set():
            frame     = self.FRAMES[i % len(self.FRAMES)]
            line_text = f"{PAD}[{frame}]  {self.label}"
            # Pad without ANSI length confusion
            padding   = " " * max(0, TERM_W - 1 - len(line_text))
            sys.stdout.write(f"\r{_ANSI_CYAN}{line_text}{_ANSI_RESET}{padding}")
            sys.stdout.flush()
            time.sleep(0.09)
            i += 1

    def start(self):
        self._thread.start()
        return self

    def done(self, ok=True):
        self._done.set()
        self._thread.join()
        # Clear spinner line
        sys.stdout.write(f"\r{' ' * (TERM_W - 1)}\r")
        sys.stdout.flush()
        tag   = "[ OK ]" if ok else "[ERR!]"
        color = "bold green" if ok else "bold red"
        _log_print(tag, self.label, color, color)

# ── Utility ──────────────────────────────────────────────────
def md5(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None

def download(url, dest):
    """Download url → dest. Returns True on success. Windows-aware."""
    if shutil.which("curl"):
        r = subprocess.run(["curl", "-fsSL", "--retry", "3", url, "-o", dest],
                           capture_output=True)
        return r.returncode == 0 and os.path.isfile(dest)
    if shutil.which("wget"):
        r = subprocess.run(["wget", "-qO", dest, url], capture_output=True)
        return r.returncode == 0 and os.path.isfile(dest)
    # Fallback: PowerShell (always available on Windows)
    if os.name == "nt":
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Invoke-WebRequest -Uri '{url}' -OutFile '{dest}' -UseBasicParsing"],
            capture_output=True
        )
        return r.returncode == 0 and os.path.isfile(dest)
    return False

def get_latest_tag():
    """Return (tag, zip_url, source_repo). Uses release asset ZIP (stable structure)."""
    import json, urllib.request

    def _pick_asset_url(assets, tag):
        if PLAT.startswith("win"):
            kws = ["windows", "win"]
        elif "darwin" in PLAT or "mac" in PLAT:
            kws = ["linux", "mac", "macos"]   # macOS uses Linux zip
        else:
            kws = ["linux"]
        for kw in kws:
            for a in assets:
                if kw in a["name"].lower() and a["name"].endswith(".zip"):
                    return a["browser_download_url"]
        for a in assets:
            if a["name"].endswith(".zip"):
                return a["browser_download_url"]
        return f"https://github.com/veritus-git/BadWords/archive/refs/tags/{tag}.zip"

    GH_API = "https://api.github.com/repos/veritus-git/BadWords/releases/latest"
    UA     = "BadWords-Installer/2.0 (https://github.com/veritus-git/BadWords)"

    # --- Try urllib first (with proper User-Agent GitHub requires) ---
    try:
        req = urllib.request.Request(GH_API, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            tag  = data.get("tag_name", "")
            if tag:
                return tag, _pick_asset_url(data.get("assets", []), tag), "GitHub"
    except Exception:
        pass

    # --- Fallback: ask curl/wget to call the API (handles SSL quirks on macOS) ---
    try:
        import subprocess as _sp
        _hdrs = ["-H", f"User-Agent: {UA}", "-H", "Accept: application/vnd.github+json"]
        if shutil.which("curl"):
            r = _sp.run(["curl", "-fsSL", "--max-time", "15"] + _hdrs + [GH_API],
                        capture_output=True, text=True)
            if r.returncode == 0 and r.stdout:
                data = json.loads(r.stdout)
                tag  = data.get("tag_name", "")
                if tag:
                    return tag, _pick_asset_url(data.get("assets", []), tag), "GitHub"
    except Exception:
        pass

    # --- GitLab fallback ---
    try:
        GL_API = "https://gitlab.com/api/v4/projects/badwords%2FBadWords/releases"
        req = urllib.request.Request(GL_API, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.load(r)
            if isinstance(data, list) and data:
                tag = data[0]["tag_name"]
                return tag, f"https://gitlab.com/badwords/BadWords/-/archive/{tag}/BadWords-{tag}.zip", "GitLab"
    except Exception:
        pass

    return "main", "", ""

def detect_existing_install(default_dir, resolve_script_dirs):
    """Search all known Resolve script dirs for a BadWords wrapper with a valid INSTALL_DIR."""
    for resolve_dir in resolve_script_dirs:
        for wf in [os.path.join(resolve_dir, "BadWords.py"),
                   os.path.join(resolve_dir, "BadWords (Linux).py")]:
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
                    debug_log(f"Updated: {os.path.join(rel, fname)}")
    for item in os.listdir(dst):
        dp = os.path.join(dst, item)
        in_src = any(os.path.exists(os.path.join(s, item)) for s in src_paths)
        if os.path.isdir(dp):
            if item not in protected_dirs and not in_src:
                debug_log(f"Removing obsolete dir: {item}")
                shutil.rmtree(dp)
        else:
            if item not in protected_files and not in_src:
                debug_log(f"Removing obsolete file: {item}")
                os.remove(dp)

# ── Option 1 — Standard Install / Update ─────────────────────
def option_install_update():
    header()
    console.print(Text(f"{PAD}── Standard Install / Update ──", style="bold green"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    detected = detect_existing_install(default_dir, resolve_dirs)
    if detected:
        log_ok(f"Existing installation detected: {detected}")
        install_dir = detected
    else:
        install_dir = default_dir
        log_info(f"Default install path: {install_dir}")

    console.print()
    console.print(Text(f"{PAD}Install path: {install_dir}", style="dim"), no_wrap=True)
    console.print(Text(f"{PAD}Press Enter to accept, or type a custom path: ", style="cyan"), end="", no_wrap=True)
    sys.stdout.flush()
    custom = readline_with_esc()

    if custom:
        custom = os.path.expanduser(custom.strip())
        if not custom.endswith(APP_NAME):
            custom = os.path.join(custom.rstrip("/\\"), APP_NAME)
        install_dir = custom
        log_info(f"Using custom path: {install_dir}")

    venv_dir  = os.path.join(install_dir, "venv")
    libs_link = os.path.join(install_dir, "libs")
    models_dir = os.path.join(install_dir, "models")
    bin_dir   = os.path.join(install_dir, "bin")
    log_file  = os.path.join(install_dir, "badwords_debug.log")
    
    global _DEBUG_LOG_FILE
    _DEBUG_LOG_FILE = log_file
    try:
        with open(_DEBUG_LOG_FILE, "w", encoding="utf-8") as f:
            for entry in _LOG_MESSAGES: f.write(entry + "\n")
    except: pass

    # ── Source fetch ──────────────────────────────────────────
    console.print()
    log_step("Resolving source files...")
    tag, zip_url, source_repo = get_latest_tag()
    tmp_dl = tempfile.mkdtemp()
    source_path = assets_path = None

    try:
        if zip_url:
            sp_dl = Spinner(f"Downloading release {tag} from {source_repo}").start()
            zip_path = os.path.join(tmp_dl, "repo.zip")
            dl_ok = download(zip_url, zip_path)
            sp_dl.done(ok=dl_ok)
            if not dl_ok:
                log_err("Download failed.")
                pause()
                return
            sp_ex = Spinner("Extracting release archive").start()
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                z.extractall(tmp_dl)
            sp_ex.done(ok=True)

            # Support both archive structures:
            # A) asset ZIP: src/main.py  (flat, no top-level subfolder)
            # B) source ZIP: BadWords-2.0.3/src/main.py  (GitHub auto-archive)
            top_dirs = [d for d in os.listdir(tmp_dl)
                        if os.path.isdir(os.path.join(tmp_dl, d))
                        and d not in ("__MACOSX", "repo.zip")]

            candidate_roots = [tmp_dl]  # structure A: src/ at extract root
            if top_dirs:
                candidate_roots.insert(0, os.path.join(tmp_dl, top_dirs[0]))  # structure B

            extracted = None
            for root in candidate_roots:
                if os.path.isdir(os.path.join(root, "src")):
                    extracted = root
                    break

            if extracted:
                source_path = os.path.join(extracted, "src")
                assets_path = os.path.join(extracted, "assets")
            else:
                log_err("Could not find src/ in downloaded archive.")
                pause()
                return

        if not source_path or not os.path.isfile(os.path.join(source_path, "main.py")):
            log_err("main.py not found in source. Aborting.")
            pause()
            return

        # ── GPU detection ─────────────────────────────────────
        console.print()
        log_step("Detecting GPU hardware...")
        has_nvidia = False
        if os.name == "nt":
            # Windows: query WMI via PowerShell (same as legacy setup_windows.bat)
            try:
                r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "try{$g=Get-WmiObject Win32_VideoController -EA Stop "
                     "| Where-Object {$_.Name -like '*NVIDIA*'} "
                     "| Select-Object -First 1; if($g){'1'}else{'0'}}catch{'0'}"],
                    capture_output=True, text=True, timeout=15
                )
                has_nvidia = r.stdout.strip() == "1"
            except Exception as e:
                log_warn(f"GPU detection via WMI failed: {e}")
        else:
            # Linux/macOS: use lspci / lshw
            if shutil.which("lspci"):
                r = subprocess.run(["lspci"], capture_output=True, text=True)
                has_nvidia = "nvidia" in r.stdout.lower()
            if not has_nvidia and shutil.which("lshw"):
                r = subprocess.run(["lshw", "-C", "display"], capture_output=True, text=True)
                has_nvidia = "nvidia" in r.stdout.lower()
        if "mac" in PLAT or "darwin" in PLAT:
            import platform
            is_arm = platform.machine().lower() == "arm64"
            mode_name = "Apple Silicon Platform" if is_arm else "Intel Platform"
        else:
            mode_name   = "NVIDIA (CUDA 12)" if has_nvidia else "CPU (AMD/Intel)"
        nvidia_pkgs = "nvidia-cublas-cu12 nvidia-cudnn-cu12" if has_nvidia else ""
        log_ok(f"AI Engine Mode: {mode_name}")

        # ── Directory setup ───────────────────────────────────
        console.print()
        log_step("Preparing directories...")
        os.makedirs(install_dir, exist_ok=True)
        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

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
        console.print()
        ffmpeg_exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        ffmpeg_bin = os.path.join(bin_dir, ffmpeg_exe_name)
        if is_update and os.path.isfile(ffmpeg_bin):
            log_ok("Portable FFmpeg already present. Skipping download.")
        else:
            log_step("Downloading portable FFmpeg...")
            if os.name == "nt":
                # Windows: use Gyan.dev essentials build (ZIP, native .exe)
                ffmpeg_url = "https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip"
                ffmpeg_arc = os.path.join(install_dir, "ffmpeg_win.zip")
                sp_ff = Spinner("Downloading FFmpeg (Windows native)").start()
                dl_ok = download(ffmpeg_url, ffmpeg_arc)
                sp_ff.done(ok=dl_ok)
                if dl_ok:
                    import zipfile
                    sp_ex2 = Spinner("Extracting FFmpeg").start()
                    try:
                        with zipfile.ZipFile(ffmpeg_arc) as zf:
                            for member in zf.namelist():
                                fname = os.path.basename(member)
                                if fname in ("ffmpeg.exe", "ffprobe.exe"):
                                    data = zf.read(member)
                                    dest = os.path.join(bin_dir, fname)
                                    with open(dest, "wb") as out:
                                        out.write(data)
                        sp_ex2.done(ok=True)
                    except Exception as e:
                        sp_ex2.done(ok=False)
                        log_warn(f"FFmpeg extraction failed: {e}")
                    finally:
                        try: os.remove(ffmpeg_arc)
                        except Exception: pass
                else:
                    log_warn("FFmpeg download failed. App may not work without it.")
            else:
                # Linux/macOS: use johnvansickle static build
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
                ffmpeg_arc = os.path.join(install_dir, "ffmpeg_static.tar.xz")
                sp_ff = Spinner("Downloading FFmpeg (Linux static)").start()
                dl_ok = download(ffmpeg_url, ffmpeg_arc)
                sp_ff.done(ok=dl_ok)
                if dl_ok:
                    sp_ex2 = Spinner("Extracting FFmpeg").start()
                    try:
                        subprocess.run(["tar", "-xf", ffmpeg_arc, "-C", install_dir], check=True)
                        for name in ["ffmpeg", "ffprobe"]:
                            for root, _, files in os.walk(install_dir):
                                if name in files and "ffmpeg-" in root:
                                    dest = os.path.join(bin_dir, name)
                                    shutil.move(os.path.join(root, name), dest)
                                    os.chmod(dest, 0o755)
                                    break
                        for item in os.listdir(install_dir):
                            if item.startswith("ffmpeg-") and os.path.isdir(os.path.join(install_dir, item)):
                                shutil.rmtree(os.path.join(install_dir, item))
                        sp_ex2.done(ok=True)
                    except Exception as e:
                        sp_ex2.done(ok=False)
                        log_warn(f"FFmpeg install error: {e}")
                    finally:
                        try: os.remove(ffmpeg_arc)
                        except Exception: pass
                else:
                    log_warn("FFmpeg download failed. App may not work without it.")

        # ── Python for venv ───────────────────────────────────
        bootstrap_py = ARGS.bootstrap_python
        target_py = bootstrap_py if os.path.isfile(bootstrap_py) else sys.executable
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
        console.print()
        if not os.path.isdir(venv_dir):
            log_step(f"Creating virtual environment ({target_py})...")
            subprocess.run([target_py, "-m", "venv", venv_dir], check=True)
            log_ok("Virtual environment created.")
        else:
            log_ok("Virtual environment already exists.")

        if os.name == "nt":
            venv_py  = os.path.join(venv_dir, "Scripts", "python.exe")
            venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            venv_py  = os.path.join(venv_dir, "bin", "python")
            venv_pip = os.path.join(venv_dir, "bin", "pip")

        # ── Dependencies ──────────────────────────────────────
        console.print()
        log_step("Installing / upgrading dependencies...")

        def _pip_run(*args, label="pip", spinner=True):
            """Run pip with optional spinner; logs stderr on failure, never crashes."""
            sp = None
            if spinner:
                sp = Spinner(label).start()
            r = subprocess.run(
                [venv_py, "-m", "pip"] + list(args),
                capture_output=True, text=True
            )
            ok = r.returncode == 0
            if sp:
                sp.done(ok=ok)
            if not ok:
                for line in (r.stderr or "").splitlines()[-12:]:
                    if line.strip():
                        log_warn(f"  {line.strip()}")
            return ok

        _pip_run("install", "--upgrade", "pip", "-q", label="Upgrading pip", spinner=False)

        torch_ok = subprocess.run([venv_pip, "show", "torch"], capture_output=True).returncode == 0
        if is_update and torch_ok:
            log_info("PyTorch already present. Upgrading Whisper only...")
            _pip_run("install", "--upgrade", "faster-whisper", "stable-ts", "pypdf", "-q",
                     label="Upgrading Whisper / Stable-TS / PyPDF")
        elif not has_nvidia:
            _pip_run("install", "torch", "torchaudio",
                     "--index-url", "https://download.pytorch.org/whl/cpu", "-q",
                     label="Installing PyTorch (CPU build)")
            _pip_run("install", "faster-whisper", "stable-ts", "pypdf", "-q",
                     label="Installing Faster-Whisper + Stable-TS")
        else:
            # Try CUDA indexes newest → oldest, CPU as final fallback
            cuda_ok = False
            for cu_tag in ("cu124", "cu121", "cu118"):
                sp = Spinner(f"Installing PyTorch (CUDA {cu_tag})").start()
                r = subprocess.run(
                    [venv_py, "-m", "pip", "install", "torch", "torchaudio",
                     "--index-url", f"https://download.pytorch.org/whl/{cu_tag}", "-q"],
                    capture_output=True, text=True
                )
                if r.returncode == 0:
                    sp.done(ok=True)
                    cuda_ok = True
                    break
                else:
                    sp.done(ok=False)
                    log_warn(f"  {cu_tag} unavailable for this Python version — trying next...")
            if not cuda_ok:
                log_warn("All CUDA indexes failed. Falling back to CPU PyTorch.")
                _pip_run("install", "torch", "torchaudio",
                         "--index-url", "https://download.pytorch.org/whl/cpu", "-q",
                         label="Installing PyTorch (CPU fallback)")
            _pip_run("install", "faster-whisper", "stable-ts", "pypdf",
                     *nvidia_pkgs.split(), "-q",
                     label="Installing Faster-Whisper + Stable-TS + CUDA libs")

        pyside_ok = subprocess.run([venv_py, "-c", "import PySide6"], capture_output=True).returncode == 0
        if not pyside_ok:
            _pip_run("install", "PySide6", "-q", label="Installing PySide6 GUI library")
        else:
            log_info("PySide6 already installed.")
        log_ok("All dependencies installed.")

        # ── Libs symlink ──────────────────────────────────────
        console.print()
        log_step("Creating libs symlink...")
        site_pkgs = None
        lib_root = os.path.join(venv_dir, "Lib" if os.name == "nt" else "lib")
        for root, dirs, _ in os.walk(lib_root):
            if "site-packages" in dirs:
                site_pkgs = os.path.join(root, "site-packages")
                break
        if site_pkgs:
            if os.path.islink(libs_link) or os.path.isdir(libs_link):
                try:
                    os.remove(libs_link)
                except Exception:
                    shutil.rmtree(libs_link, ignore_errors=True)

            linked = False
            if os.name == "nt":
                r = subprocess.run(
                    f'mklink /J "{libs_link}" "{site_pkgs}"',
                    shell=True, capture_output=True
                )
                if r.returncode == 0:
                    debug_log(f"libs junction created: {libs_link} -> {site_pkgs}")
                    log_ok("libs link created.")
                    linked = True
            else:
                try:
                    os.symlink(site_pkgs, libs_link, target_is_directory=True)
                    debug_log(f"libs symlink created: {libs_link} -> {site_pkgs}")
                    log_ok("libs link created.")
                    linked = True
                except (OSError, NotImplementedError):
                    pass

            if not linked:
                sp_copy = Spinner("Copying libs (one-time fallback)").start()
                try:
                    shutil.copytree(site_pkgs, libs_link, dirs_exist_ok=True)
                    sp_copy.done(ok=True)
                except Exception as e:
                    sp_copy.done(ok=False)
                    log_warn(f"libs copy failed: {e}")
        else:
            log_warn("Could not locate site-packages in venv.")

        # ── DaVinci Resolve wrapper ───────────────────────────
        console.print()
        log_step("Configuring DaVinci Resolve integration...")

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
        # Check which Resolve dirs actually exist at the 'DaVinci Resolve' base level.
        # This is more reliable than checking deeper sub-folders which may not exist
        # until Resolve creates them on first launch.
        def _resolve_base_exists(d):
            p = d
            for _ in range(7):
                p = os.path.dirname(p)
                if os.path.basename(p) == "DaVinci Resolve":
                    return os.path.isdir(p)
            return False

        existing_resolve_dirs = [d for d in resolve_dirs if _resolve_base_exists(d)]
        # Fall back to standard per-user path (resolve_dirs[0]) if Resolve not yet opened
        targets = existing_resolve_dirs if existing_resolve_dirs else [resolve_dirs[0]]

        wrapper_count = 0
        for rd in targets:
            try:
                os.makedirs(rd, exist_ok=True)
                legacy_w = os.path.join(rd, "BadWords (Linux).py")
                if os.path.isfile(legacy_w):
                    os.remove(legacy_w)
                wp = os.path.join(rd, "BadWords.py")
                with open(wp, "w", encoding="utf-8") as f:
                    f.write(wrapper_content)
                os.chmod(wp, 0o755)
                debug_log(f"Wrapper written to: {wp}")
                wrapper_count += 1
            except Exception as exc:
                debug_log(f"Could not write wrapper to {rd}: {exc}")

        if wrapper_count > 0:
            log_ok("DaVinci Resolve wrapper installed.")
        else:
            log_err("Failed to write wrapper to any Resolve location.")

        open(log_file, "a").close()
        os.chmod(log_file, 0o666)

        # ── Done ─────────────────────────────────────────────
        console.print()
        console.print(Text(f"{PAD}✓  INSTALLATION SUCCESSFUL!", style="bold green"), no_wrap=True)
        console.print(Text(f"{PAD}   Mode : {mode_name}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Path : {install_dir}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Log  : {log_file}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Find the script inside Davinci Resolve -> Workspace -> Scripts -> BadWords.", style="dim"), no_wrap=True)
        console.print()

    finally:
        shutil.rmtree(tmp_dl, ignore_errors=True)

    pause(f"{PAD}Press Enter to exit...")

# ── Dummy stubs ───────────────────────────────────────────────
def option_dummy(n, label):
    header()
    console.print(Text(f"{PAD}You selected option {n}: {label}", style="cyan"), no_wrap=True)
    console.print(Text(f"{PAD}(This option is not yet implemented.)", style="dim"), no_wrap=True)
    pause()



# ── Main loop ─────────────────────────────────────────────────
def main():
    # One-time setup: resize + title + lock scrollbar
    _resize()
    _set_title("BadWords Setup")
    _set_scrollbar(False)
    while True:
        try:
            header()
            menu()
            choice = prompt_choice()
            if choice == "ESC" or choice == "0":
                _close_terminal()
            elif choice == "1":
                option_install_update()
            elif choice == "2":
                option_dummy(2, "Repair Installation")
            elif choice == "3":
                option_dummy(3, "Move Installation")
            elif choice == "4":
                option_dummy(4, "Complete Reset")
            elif choice == "5":
                option_dummy(5, "Uninstall")
            else:
                header()
                console.print(Text(f"{PAD}Invalid option. Please try again.", style="red"), no_wrap=True)
                time.sleep(1)
        except UserCancelled:
            # ESC pressed mid-operation → return to menu silently
            pass
        except KeyboardInterrupt:
            _close_terminal()
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            debug_log(f"CRASH: {err_msg}")
            log_err(f"An unexpected error occurred: {e}")
            pause("Press Enter to exit...")
            _close_terminal()

def _close_terminal():
    """Exit the process AND close the terminal window."""
    if os.name == "nt":
        # cmd /c automatically closes when python exits
        pass
    elif "darwin" in PLAT or "mac" in PLAT:
        # The bootstrapper used exec, so exiting Python closes the shell session.
        # Terminal.app closes the tab automatically when the process exits
        # (requires Terminal prefs: Shell → When shell exits: Close the window).
        # We also try AppleScript as a best-effort for default Terminal settings.
        subprocess.Popen(
            ["osascript", "-e",
             'tell application "Terminal" to close front window'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        # Linux: SIGHUP to parent closes the terminal session
        import signal
        try:
            os.kill(os.getppid(), signal.SIGHUP)
        except ProcessLookupError:
            pass
    sys.exit(0)

if __name__ == "__main__":
    main()
