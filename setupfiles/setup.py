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
parser.add_argument("--local-repo", default="")
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
        
        subs = ["Utility"]
        for b in bases:
            for s in subs:
                p = os.path.join(b, "Fusion", "Scripts", s)
                results.append(p)

    elif "mac" in PLAT or "darwin" in PLAT:
        bases = [
            os.path.join("/", "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve"),
            os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Blackmagic Design", "DaVinci Resolve")
        ]
        subs = ["Utility"]
        for b in bases:
            for s in subs:
                p = os.path.join(b, "Fusion", "Scripts", s)
                results.append(p)

    else:
        # Linux
        bases = [
            os.path.join(os.path.expanduser("~"), ".local", "share", "DaVinciResolve"),
            os.path.join("/", "opt", "resolve", "libs")
        ]
        subs = ["Utility"]
        for b in bases:
            for s in subs:
                p_upper = os.path.join(b, "Fusion", "Scripts", s)
                p_lower = os.path.join(b, "Fusion", "Scripts", s)
                results.append(p_upper)  # always try uppercase Fusion first
                results.append(p_lower)

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
        try:
            old = termios.tcgetattr(fd)
        except (termios.error, OSError):
            # stdin is not a TTY (pipe, subshell, CI, etc.) — fallback to plain readline
            line = sys.stdin.readline()
            return line[0] if line else "ESC"
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
    """Read a line character-by-character. ESC/Ctrl+C cancels → raises UserCancelled.
    Handles bracketed paste and Windows Ctrl+V."""
    if os.name == "nt":
        import msvcrt
        buf = []
        while True:
            ch = msvcrt.getwch()
            if ch == "\x03":
                raise UserCancelled()
            if ch == "\x1b":
                if msvcrt.kbhit():
                    next_ch = msvcrt.getwch()
                    if next_ch in ("[", "O"):
                        while msvcrt.kbhit():
                            seq_ch = msvcrt.getwch()
                            if seq_ch.isalpha() or seq_ch == "~":
                                break
                    continue
                else:
                    raise UserCancelled()
            if ch in ("\r", "\n"):
                sys.stdout.write("\r\n"); sys.stdout.flush()
                return "".join(buf)
            if ch in ("\x08", "\x7f"):
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b"); sys.stdout.flush()
                continue
            if ch == "\x16":
                try:
                    import ctypes
                    ctypes.windll.user32.OpenClipboard(0)
                    hData = ctypes.windll.user32.GetClipboardData(13)
                    raw_paste = ""
                    if hData:
                        pData = ctypes.windll.kernel32.GlobalLock(hData)
                        raw_paste = ctypes.wstring_at(pData)
                        ctypes.windll.kernel32.GlobalUnlock(hData)
                    ctypes.windll.user32.CloseClipboard()
                    for c in raw_paste:
                        if c in ("\r", "\n"):
                            break
                        if c.isprintable():
                            buf.append(c)
                            sys.stdout.write(c)
                    sys.stdout.flush()
                except Exception:
                    pass
                continue
            if ch in ("\x00", "\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getwch()
                continue
            if ch.isprintable():
                buf.append(ch)
                sys.stdout.write(ch); sys.stdout.flush()
    else:
        import tty, termios, select
        fd = sys.stdin.fileno()
        try:
            old = termios.tcgetattr(fd)
        except (termios.error, OSError):
            try:
                return input()
            except (EOFError, KeyboardInterrupt):
                raise UserCancelled()
        buf = []
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch == "\x03":
                    raise UserCancelled()
                if ch == "\x1b":
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r:
                        next_ch = sys.stdin.read(1)
                        if next_ch == "[":
                            # Could be a bracketed paste sequence \x1b[200~ or an ANSI escape
                            # Read up to 4 more chars to distinguish them
                            r2, _, _ = select.select([sys.stdin], [], [], 0.05)
                            if r2:
                                code_ch = sys.stdin.read(1)
                                if code_ch == "2":
                                    # Possibly \x1b[200~ (bracketed paste start)
                                    r3, _, _ = select.select([sys.stdin], [], [], 0.05)
                                    if r3:
                                        code_ch2 = sys.stdin.read(1)
                                        if code_ch2 == "0":
                                            r4, _, _ = select.select([sys.stdin], [], [], 0.05)
                                            if r4:
                                                code_ch3 = sys.stdin.read(1)
                                                if code_ch3 == "0":
                                                    # Consume the trailing "~"
                                                    r5, _, _ = select.select([sys.stdin], [], [], 0.05)
                                                    if r5:
                                                        sys.stdin.read(1)  # consume "~"
                                                    # Now read pasted content until \x1b[201~
                                                    while True:
                                                        rc, _, _ = select.select([sys.stdin], [], [], 0.2)
                                                        if not rc:
                                                            break
                                                        pc = sys.stdin.read(1)
                                                        if pc == "\x1b":
                                                            # Consume [201~
                                                            r_end, _, _ = select.select([sys.stdin], [], [], 0.05)
                                                            if r_end:
                                                                sys.stdin.read(10)  # consume tail
                                                            break
                                                        if pc in ("\r", "\n"):
                                                            break  # single-line input: stop at newline
                                                        if pc.isprintable():
                                                            buf.append(pc)
                                                            sys.stdout.write(pc)
                                                    sys.stdout.flush()
                                                    continue
                                                else:
                                                    # Not bracketed paste — consume until letter/~
                                                    seq = code_ch3
                                                    while True:
                                                        rq, _, _ = select.select([sys.stdin], [], [], 0.05)
                                                        if not rq:
                                                            break
                                                        sc = sys.stdin.read(1)
                                                        if sc.isalpha() or sc == "~":
                                                            break
                                                    continue
                                        else:
                                            # Consume until end of sequence
                                            seq = code_ch2
                                            while True:
                                                rq, _, _ = select.select([sys.stdin], [], [], 0.05)
                                                if not rq:
                                                    break
                                                sc = sys.stdin.read(1)
                                                if sc.isalpha() or sc == "~":
                                                    break
                                            continue
                                    continue
                                else:
                                    # Regular ANSI escape (arrow keys etc.) — consume until letter/~
                                    seq = code_ch
                                    while True:
                                        rq, _, _ = select.select([sys.stdin], [], [], 0.05)
                                        if not rq:
                                            break
                                        sc = sys.stdin.read(1)
                                        if sc.isalpha() or sc == "~":
                                            break
                                    continue
                            continue
                        elif next_ch == "O":
                            # F-key or cursor key sequence
                            r2, _, _ = select.select([sys.stdin], [], [], 0.05)
                            if r2:
                                sys.stdin.read(1)
                            continue
                        continue
                    else:
                        raise UserCancelled()
                if ch in ("\r", "\n"):
                    sys.stdout.write("\r\n"); sys.stdout.flush()
                    return "".join(buf)
                if ch in ("\x7f", "\x08"):
                    if buf:
                        buf.pop()
                        sys.stdout.write("\b \b"); sys.stdout.flush()
                    continue
                # Ctrl+V on Linux/macOS — read clipboard via system tools
                if ch == "\x16":
                    try:
                        import subprocess as _sp
                        clip_txt = ""
                        for _cmd in (["xclip", "-selection", "clipboard", "-o"],
                                     ["xsel", "--clipboard", "--output"],
                                     ["pbpaste"]):
                            try:
                                res = _sp.run(_cmd, capture_output=True, text=True, timeout=2)
                                if res.returncode == 0:
                                    clip_txt = res.stdout
                                    break
                            except (FileNotFoundError, _sp.TimeoutExpired):
                                continue
                        for c in clip_txt:
                            if c in ("\r", "\n"):
                                break
                            if c.isprintable():
                                buf.append(c)
                                sys.stdout.write(c)
                        sys.stdout.flush()
                    except Exception:
                        pass
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
    elif "mac" in PLAT or "darwin" in PLAT:
        # macOS terminal natively appends process name, which we already set to "BadWords Setup" via bash.
        # Setting ANSI title here creates a duplicate like "BadWords Setup — BadWords Setup".
        pass
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

def get_latest_tag(force_main=False):
    """Return (tag, zip_url, source_repo). Uses release asset ZIP (stable structure)."""
    if force_main:
        return "main", "https://github.com/veritus-git/BadWords/archive/refs/heads/main.zip", "GitHub (dev)"
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

def _clean_legacy_inno_setup(install_dir):
    """Silently cleans up old Inno Setup uninstaller files and registry keys on Windows."""
    if not PLAT.startswith("win"): return
    import winreg
    
    # 1. Delete uninstaller files
    for f in ["unins000.exe", "unins000.dat", "unins000.msg"]:
        p = os.path.join(install_dir, f)
        if os.path.isfile(p):
            try: os.remove(p)
            except Exception: pass

    # 2. Delete registry keys from HKCU and HKLM
    paths = [
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    def delete_reg_key(hive_str, subkey):
        try:
            cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            subprocess.run(["reg", "delete", f"{hive_str}\\{subkey}", "/f"], 
                           creationflags=cf, capture_output=True)
        except Exception: pass

    for hive, hive_str in [(winreg.HKEY_CURRENT_USER, "HKCU"), (winreg.HKEY_LOCAL_MACHINE, "HKLM")]:
        for p in paths:
            try:
                with winreg.OpenKey(hive, p, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                    num_subkeys = winreg.QueryInfoKey(key)[0]
                    to_delete = []
                    for i in range(num_subkeys):
                        sk_name = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, sk_name) as sk:
                                display_name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                if "BadWords" in str(display_name):
                                    to_delete.append(p + "\\" + sk_name)
                        except Exception: pass
            except Exception:
                to_delete = []
                
            for sk_path in to_delete:
                delete_reg_key(hive_str, sk_path)

def _create_davinci_wrappers(install_dir, resolve_dirs):
    """Generates and writes the DaVinci Resolve Python wrapper for the given install_dir."""
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
    def _resolve_base_exists(d):
        p = d
        for _ in range(7):
            p = os.path.dirname(p)
            bn = os.path.basename(p)
            if bn in ("DaVinci Resolve", "DaVinciResolve", "resolve"):
                return os.path.isdir(p)
        return False

    existing_resolve_dirs = [d for d in resolve_dirs if _resolve_base_exists(d)]
    targets = existing_resolve_dirs if existing_resolve_dirs else [resolve_dirs[0]]

    for rd in targets:
        scripts_dir = os.path.dirname(rd)
        if os.path.exists(scripts_dir):
            for root, _, files in os.walk(scripts_dir):
                for f in files:
                    if f.startswith("BadWords") and f.endswith(".py"):
                        p = os.path.join(root, f)
                        try: os.remove(p)
                        except: pass

    wrapper_count = 0
    for rd in targets:
        try:
            os.makedirs(rd, exist_ok=True)
            wp = os.path.join(rd, "BadWords.py")
            with open(wp, "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            os.chmod(wp, 0o755)
            debug_log(f"Wrapper written to: {wp}")
            wrapper_count += 1
            break
        except Exception as exc:
            debug_log(f"Could not write wrapper to {rd}: {exc}")

    return wrapper_count > 0


# ── Option 1 — Standard Install / Update ─────────────────────
def option_install_update(force_main=False, preset_path=None, title="── Standard Install / Update ──", title_color="green"):
    header()
    if force_main:
        console.print(Text(f"{PAD}── Dev Install (main) ──", style="bold magenta"), no_wrap=True)
    else:
        console.print(Text(f"{PAD}{title}", style=f"bold {title_color}"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    if preset_path:
        # Path was chosen upstream (e.g. by option_reset) — skip detect & prompt
        install_dir = preset_path
        log_info(f"Using preset install path: {install_dir}")
    else:
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

    # Aggressively clean up old Inno Setup (Add/Remove Programs) leftovers
    _clean_legacy_inno_setup(install_dir)

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
    
    repo_root = ARGS.local_repo if ARGS.local_repo else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_src = os.path.join(repo_root, "src")
    local_assets = os.path.join(repo_root, "assets")
    local_main = os.path.join(local_src, "main.py")

    source_path = assets_path = None
    tmp_dl = None

    if os.path.isfile(local_main):
        log_ok("Local source repository detected. Using local files.")
        source_path = local_src
        assets_path = local_assets if os.path.isdir(local_assets) else None

    if not source_path:
        tag, zip_url, source_repo = get_latest_tag(force_main)
        tmp_dl = tempfile.mkdtemp()

    try:
        if not source_path and zip_url and tmp_dl:
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
        protected_files = {"pref.json", "user.json", "settings.json", "badwords_debug.log"}
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
            elif "mac" in PLAT or "darwin" in PLAT:
                # macOS: use Homebrew and symlink (Legacy behavior)
                sp_ff = Spinner("Installing FFmpeg via Homebrew").start()
                if not shutil.which("brew"):
                    sp_ff.done(ok=False)
                    log_err("Homebrew is required for macOS installation. Please install brew first.")
                    raise UserCancelled()
                
                # Install ffmpeg using brew (blocks until done)
                r = subprocess.run(["brew", "install", "ffmpeg"], capture_output=True)
                sp_ff.done(ok=(r.returncode == 0))
                
                if r.returncode == 0 or b"already installed" in r.stdout or b"already installed" in r.stderr:
                    try:
                        brew_prefix = subprocess.run(["brew", "--prefix", "ffmpeg"], capture_output=True, text=True).stdout.strip()
                        brew_ffmpeg = os.path.join(brew_prefix, "bin", "ffmpeg")
                        brew_ffprobe = os.path.join(brew_prefix, "bin", "ffprobe")
                        
                        if os.path.isfile(brew_ffmpeg):
                            sym_ffmpeg = os.path.join(bin_dir, "ffmpeg")
                            if os.path.lexists(sym_ffmpeg): os.remove(sym_ffmpeg)
                            os.symlink(brew_ffmpeg, sym_ffmpeg)
                            
                        if os.path.isfile(brew_ffprobe):
                            sym_ffprobe = os.path.join(bin_dir, "ffprobe")
                            if os.path.lexists(sym_ffprobe): os.remove(sym_ffprobe)
                            os.symlink(brew_ffprobe, sym_ffprobe)
                            
                        log_ok(f"Symlinked Homebrew FFmpeg into bin/ directory.")
                    except Exception as e:
                        log_err(f"Symlink failed: {e}")
                else:
                    log_warn("Homebrew FFmpeg installation failed.")
            else:
                # Linux: use johnvansickle static build
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
        
        success = _create_davinci_wrappers(install_dir, resolve_dirs)
        if success:
            log_ok("DaVinci Resolve wrapper installed.")
        else:
            log_warn("Failed to write wrapper to any Resolve location.")



        open(log_file, "a").close()
        os.chmod(log_file, 0o666)

        if force_main:
            try:
                import json
                dev_path = os.path.join(install_dir, "dev.json")
                with open(dev_path, "w", encoding="utf-8") as f:
                    json.dump({"dev_mode": True}, f)
                log_ok("Created dev.json for dev installation.")
            except Exception as e:
                log_warn(f"Failed to create dev.json: {e}")

        # ── Done ─────────────────────────────────────────────
        console.print()
        console.print(Text(f"{PAD}✓  INSTALLATION SUCCESSFUL!", style="bold green"), no_wrap=True)
        console.print(Text(f"{PAD}   Mode : {mode_name}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Path : {install_dir}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Log  : {log_file}", style="green"), no_wrap=True)
        console.print(Text(f"{PAD}   Find the script inside Davinci Resolve -> Workspace -> Scripts -> BadWords.", style="dim"), no_wrap=True)
        console.print()

    finally:
        if tmp_dl:
            shutil.rmtree(tmp_dl, ignore_errors=True)

    pause(f"{PAD}Press Enter to exit...")

# ── Dummy stubs ───────────────────────────────────────────────
def option_dummy(n, label):
    header()
    console.print(Text(f"{PAD}You selected option {n}: {label}", style="cyan"), no_wrap=True)
    console.print(Text(f"{PAD}(This option is not yet implemented.)", style="dim"), no_wrap=True)
    pause()


# ── Option 2 — Repair Installation ─────────────────────────────
def option_repair():
    header()
    console.print(Text(f"{PAD}-- Repair Installation --", style="bold cyan"), no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}This will:", style="bold white"), no_wrap=True)
    console.print(Text(f"{PAD}  1. Remove core files, venv, and binaries", style="cyan"), no_wrap=True)
    console.print(Text(f"{PAD}  2. Preserve your models, saves, and settings", style="green"), no_wrap=True)
    console.print(Text(f"{PAD}  3. Reinstall the core components from scratch", style="cyan"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    log_step("Searching via DaVinci Resolve wrapper...")
    wrapper_dir = detect_existing_install(default_dir, resolve_dirs)
    if wrapper_dir:
        log_ok(f"Wrapper found -> {wrapper_dir}")
        install_dir = wrapper_dir
    else:
        log_warn("No wrapper detected. Falling back to deep scan...")
        sp_scan = Spinner("Deep-scanning system for BadWords installations").start()
        found_dirs = _deep_search_badwords()
        sp_scan.done(ok=True)
        if not found_dirs:
            console.print()
            log_err("No BadWords installation found to repair.")
            pause()
            return
        install_dir = found_dirs[0]
        log_ok(f"Installation found -> {install_dir}")

    console.print()
    console.print(Text(f'{PAD}Type "yes" to confirm Repair and press Enter: ', style="bold yellow"), end="", no_wrap=True)
    sys.stdout.flush()
    try:
        answer = readline_with_esc()
    except UserCancelled:
        console.print()
        log_info("Repair cancelled.")
        pause()
        return
    console.print()

    if answer.strip().lower() != "yes":
        log_info("Repair cancelled.")
        pause()
        return

    console.print()
    log_step(f"Cleaning core files in: {install_dir}")
    
    # Files/folders to KEEP
    protected = {"models", "saves", "pref.json", "user.json", "settings.json", "badwords_debug.log", "dev.json", "venv"}
    
    sp_rm = Spinner("Removing core components").start()
    errors = []
    try:
        if os.path.exists(install_dir):
            for item in os.listdir(install_dir):
                if item in protected:
                    continue
                p = os.path.join(install_dir, item)
                try:
                    if os.path.isdir(p):
                        def on_rm_error(func, path, exc_info):
                            import stat
                            try:
                                current_mode = os.stat(path).st_mode
                                os.chmod(path, current_mode | stat.S_IWRITE)
                                func(path)
                            except Exception:
                                pass
                        shutil.rmtree(p, onerror=on_rm_error)
                        if os.path.exists(p):
                            if os.name == "nt":
                                subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", p], capture_output=True)
                            else:
                                subprocess.run(["rm", "-rf", p], capture_output=True)
                    else:
                        os.remove(p)
                except Exception as e:
                    errors.append(f"{item}: {e}")
        sp_rm.done(ok=not bool(errors))
    except Exception as e:
        sp_rm.done(ok=False)
        errors.append(str(e))

    if errors:
        for err in errors:
            log_warn(f"Failed to remove {err}")

    console.print()
    log_step("Starting fresh installation phase...")
    option_install_update(preset_path=install_dir, title="── Repair Installation ──", title_color="cyan")


# ── Option 3 — Move Installation ───────────────────────────────
def option_move():
    header()
    console.print(Text(f"{PAD}── Move Installation ──", style="bold blue"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    # ── Detect current installation ────────────────────────
    log_step("Searching via DaVinci Resolve wrapper...")
    wrapper_dir = detect_existing_install(default_dir, resolve_dirs)
    if wrapper_dir:
        log_ok(f"Found -> {wrapper_dir}")
        install_dir = wrapper_dir
    else:
        log_warn("No wrapper detected — falling back to deep scan...")
        sp_scan = Spinner("Deep-scanning system for BadWords installations").start()
        found_dirs = _deep_search_badwords()
        sp_scan.done(ok=True)
        if not found_dirs:
            console.print()
            log_err("No BadWords installation found to move.")
            pause()
            return
        install_dir = found_dirs[0]
        log_ok(f"Found -> {install_dir}")

    # ── Ask for destination ────────────────────────────
    console.print()
    console.print(Text(f"{PAD}Current location: {install_dir}", style="dim"), no_wrap=True)
    console.print(Text(f"{PAD}New location (or Enter to cancel): ", style="blue"), end="", no_wrap=True)
    sys.stdout.flush()
    try:
        raw = readline_with_esc()
    except UserCancelled:
        console.print()
        log_info("Move cancelled.")
        pause()
        return

    if not raw.strip():
        log_info("Move cancelled.")
        pause()
        return

    new_path = os.path.expanduser(raw.strip())
    if not new_path.endswith(APP_NAME):
        base = new_path.rstrip("/\\")
        # On Windows, bare drive letters like "G:" need a trailing sep
        # otherwise os.path.join("G:", "BadWords") → "G:BadWords" (relative!)
        if os.name == "nt" and len(base) == 2 and base[1] == ":":
            base = base + "\\"
        new_path = os.path.join(base, APP_NAME)

    if os.path.abspath(install_dir) == os.path.abspath(new_path):
        console.print()
        log_warn("Source and destination are the same. Nothing to do.")
        pause()
        return

    if os.path.exists(new_path):
        console.print()
        log_err(f"Destination already exists: {new_path}")
        pause()
        return

    console.print()

    # ── Step 1: Move directory ───────────────────────────
    sp_mv = Spinner(f"Moving files to {new_path}").start()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(new_path)), exist_ok=True)
        shutil.move(install_dir, new_path)
        sp_mv.done(ok=True)
    except Exception as e:
        sp_mv.done(ok=False)
        log_err(f"Move failed: {e}")
        pause()
        return

    # ── Step 2: Transplant venv — no re-download needed ──────────
    # Python venv executables (bin/pip, bin/python) contain hardcoded
    # absolute shebangs → broken after shutil.move. Fix: rescue the
    # site-packages (all the actual packages), delete only the broken
    # venv shell, create a fresh venv with correct shebangs, then swap
    # the new empty site-packages for the rescued ones.
    old_venv = os.path.join(new_path, "venv")
    old_libs = os.path.join(new_path, "libs")
    new_venv = os.path.join(new_path, "venv")
    new_libs = os.path.join(new_path, "libs")

    # Locate site-packages inside the (broken) moved venv
    console.print()
    log_step("Locating installed packages in moved venv...")
    old_lib_root = os.path.join(old_venv, "Lib" if os.name == "nt" else "lib")
    old_site_pkgs = None
    for root, dirs, _ in os.walk(old_lib_root):
        if "site-packages" in dirs:
            old_site_pkgs = os.path.join(root, "site-packages")
            break

    # Rescue: move site-packages to a temp sibling dir BEFORE deleting venv
    rescued_pkgs = os.path.join(new_path, ".bw_pkgs_rescue")
    if old_site_pkgs and os.path.isdir(old_site_pkgs):
        sp_rescue = Spinner("Rescuing packages from stale venv").start()
        try:
            if os.path.exists(rescued_pkgs):
                shutil.rmtree(rescued_pkgs, ignore_errors=True)
            shutil.move(old_site_pkgs, rescued_pkgs)
            sp_rescue.done(ok=True)
        except Exception as e:
            sp_rescue.done(ok=False)
            log_warn(f"Could not rescue packages: {e} — will re-install from internet.")
            rescued_pkgs = None
    else:
        log_warn("No site-packages found in moved venv — will re-install from internet.")
        rescued_pkgs = None

    # Delete the stale venv shell (executables with wrong shebangs)
    if os.path.exists(old_venv):
        sp_rm = Spinner("Removing stale venv shell").start()
        shutil.rmtree(old_venv, ignore_errors=True)
        if os.name != "nt":
            subprocess.run(["rm", "-rf", old_venv], capture_output=True)
        sp_rm.done(ok=not os.path.exists(old_venv))
    if os.path.islink(old_libs) or os.path.isdir(old_libs):
        try:
            os.remove(old_libs)
        except Exception:
            shutil.rmtree(old_libs, ignore_errors=True)

    # Pick best available Python
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

    log_step(f"Creating fresh venv ({target_py})...")
    try:
        subprocess.run([target_py, "-m", "venv", new_venv], check=True, capture_output=True)
        log_ok("Virtual environment created.")
    except Exception as e:
        log_err(f"Failed to create venv: {e}")
        if rescued_pkgs and os.path.exists(rescued_pkgs):
            shutil.rmtree(rescued_pkgs, ignore_errors=True)
        pause()
        return

    if os.name == "nt":
        venv_py = os.path.join(new_venv, "Scripts", "python.exe")
    else:
        venv_py = os.path.join(new_venv, "bin", "python")

    # Locate where new venv's (empty) site-packages are
    new_lib_root = os.path.join(new_venv, "Lib" if os.name == "nt" else "lib")
    new_site_pkgs = None
    for root, dirs, _ in os.walk(new_lib_root):
        if "site-packages" in dirs:
            new_site_pkgs = os.path.join(root, "site-packages")
            break

    transplanted = False
    if rescued_pkgs and new_site_pkgs:
        # Swap: remove the new empty site-packages, put in the rescued ones
        sp_swap = Spinner("Transplanting packages into new venv").start()
        try:
            shutil.rmtree(new_site_pkgs, ignore_errors=True)
            shutil.move(rescued_pkgs, new_site_pkgs)
            sp_swap.done(ok=True)
            log_ok("All packages transplanted — no downloads needed.")
            transplanted = True
            # On Windows, PySide6 DLLs have path-sensitive internal references
            # that break when moved between drives/directories. Force-reinstall
            # only PySide6 (small) to get correct DLL paths — PyTorch stays cached.
            if os.name == "nt":
                sp_ps = Spinner("Fixing PySide6 DLL paths (Windows)").start()
                r = subprocess.run(
                    [venv_py, "-m", "pip", "install", "--force-reinstall", "PySide6", "-q"],
                    capture_output=True, text=True)
                sp_ps.done(ok=r.returncode == 0)
                if r.returncode != 0:
                    log_warn("PySide6 re-install failed — app may not start correctly.")
        except Exception as e:
            sp_swap.done(ok=False)
            log_warn(f"Transplant failed: {e}")
            if os.path.exists(rescued_pkgs):
                shutil.rmtree(rescued_pkgs, ignore_errors=True)
    elif rescued_pkgs:
        shutil.rmtree(rescued_pkgs, ignore_errors=True)

    if not transplanted:
        # Fallback: full re-install (only if transplant wasn't possible)
        console.print()
        log_step("Re-installing dependencies (fallback)...")

        def _pip(label, *args):
            sp = Spinner(label).start()
            r = subprocess.run([venv_py, "-m", "pip"] + list(args),
                               capture_output=True, text=True)
            sp.done(ok=r.returncode == 0)
            if r.returncode != 0:
                for ln in (r.stderr or "").splitlines()[-8:]:
                    if ln.strip():
                        log_warn(f"  {ln.strip()}")
            return r.returncode == 0

        _pip("Upgrading pip", "install", "--upgrade", "pip", "-q")
        has_nvidia = False
        try:
            has_nvidia = subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0
        except Exception:
            pass
        if not has_nvidia:
            _pip("Installing PyTorch (CPU)", "install", "torch", "torchaudio",
                 "--index-url", "https://download.pytorch.org/whl/cpu", "-q")
        else:
            cuda_ok = False
            for cu_tag in ("cu124", "cu121", "cu118"):
                if _pip(f"Installing PyTorch (CUDA {cu_tag})", "install", "torch", "torchaudio",
                        "--index-url", f"https://download.pytorch.org/whl/{cu_tag}", "-q"):
                    cuda_ok = True
                    break
            if not cuda_ok:
                _pip("Installing PyTorch (CPU fallback)", "install", "torch", "torchaudio",
                     "--index-url", "https://download.pytorch.org/whl/cpu", "-q")
        _pip("Installing Faster-Whisper + Stable-TS + PyPDF",
             "install", "faster-whisper", "stable-ts", "pypdf", "-q")
        if subprocess.run([venv_py, "-c", "import PySide6"], capture_output=True).returncode != 0:
            _pip("Installing PySide6", "install", "PySide6", "-q")
        log_ok("Dependencies installed.")

    # ── Step 3: Recreate libs symlink ────────────────────────
    console.print()
    log_step("Creating libs link...")
    final_site_pkgs = new_site_pkgs
    if not final_site_pkgs or not os.path.isdir(final_site_pkgs):
        for root, dirs, _ in os.walk(new_lib_root):
            if "site-packages" in dirs:
                final_site_pkgs = os.path.join(root, "site-packages")
                break
    if final_site_pkgs:
        linked = False
        if os.name == "nt":
            r = subprocess.run(f'mklink /J "{new_libs}" "{final_site_pkgs}"',
                               shell=True, capture_output=True)
            linked = (r.returncode == 0)
        else:
            try:
                os.symlink(final_site_pkgs, new_libs, target_is_directory=True)
                linked = True
            except (OSError, NotImplementedError):
                pass
        if not linked:
            sp_copy = Spinner("Copying libs (fallback)").start()
            try:
                shutil.copytree(final_site_pkgs, new_libs, dirs_exist_ok=True)
                sp_copy.done(ok=True)
            except Exception as e:
                sp_copy.done(ok=False)
                log_warn(f"libs copy failed: {e}")
        else:
            log_ok("libs link created.")
    else:
        log_warn("Could not locate site-packages in new venv.")

    # ── Step 6: Update DaVinci Resolve wrapper ───────────────
    console.print()
    log_step("Updating DaVinci Resolve wrapper...")
    if _create_davinci_wrappers(new_path, resolve_dirs):
        log_ok("Wrapper updated.")
    else:
        log_warn("Failed to update wrapper.")

    # ── Done ─────────────────────────────────────────
    console.print()
    console.print(Text(f"{PAD}+ MOVE SUCCESSFUL!", style="bold blue"), no_wrap=True)
    console.print(Text(f"{PAD}  BadWords is now at: {new_path}", style="blue"), no_wrap=True)
    console.print()
    pause(f"{PAD}Press Enter to exit...")





# ── Option 5 — Uninstall (Deep Search) ───────────────────────

# Signature files unique to a BadWords installation.
# If a directory contains at least _BW_MATCH_MIN of these, it's ours.
_BW_SIGNATURES = frozenset({
    "main.py", "engine.py", "api.py",
    "algorythms.py", "gui.py", "osdoc.py", "config.py"
})
_BW_MATCH_MIN = 3   # >=3 of 7 files = confirmed BadWords dir


def _is_badwords_dir(d):
    """Return True if directory d contains enough BadWords signature files."""
    try:
        contents = set(os.listdir(d))
    except OSError:
        return False
    return len(_BW_SIGNATURES & contents) >= _BW_MATCH_MIN


def _deep_search_badwords():
    """
    Scan well-known OS-specific locations for BadWords installation dirs.
    Strategy (2-level walk to stay fast):
      1. Any immediate child named 'badwords' (case-insensitive) + verified with signatures
      2. Any immediate child (any name) containing >=3 signature files
      3. Any grandchild named 'badwords' + verified with signatures
      4. Any grandchild (any name) containing >=3 signature files
    Returns a sorted list of unique absolute directory paths.
    """
    home = os.path.expanduser("~")

    if PLAT.startswith("win"):
        roots = list(filter(None, [
            os.environ.get("LOCALAPPDATA", ""),
            os.environ.get("APPDATA", ""),
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("PROGRAMFILES(X86)", ""),
            home,
            "C:\\",
        ]))
    elif "darwin" in PLAT or "mac" in PLAT:
        roots = [
            os.path.join(home, "Library", "Application Support"),
            os.path.join(home, "Applications"),
            "/Applications",
            "/usr/local",
            "/opt",
        ]
    else:  # Linux
        roots = [
            os.path.join(home, ".local", "share"),
            os.path.join(home, ".local"),
            home,
            "/opt",
            "/usr/local",
        ]

    found = set()

    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        try:
            level1 = os.listdir(root)
        except OSError:
            continue

        for name1 in level1:
            path1 = os.path.join(root, name1)
            if not os.path.isdir(path1):
                continue

            # Level-1: name match OR signature match
            if name1.lower() == "badwords":
                if _is_badwords_dir(path1):
                    found.add(os.path.abspath(path1))
            elif _is_badwords_dir(path1):
                found.add(os.path.abspath(path1))

            # Level-2: scan children of this dir
            try:
                for name2 in os.listdir(path1):
                    path2 = os.path.join(path1, name2)
                    if not os.path.isdir(path2):
                        continue
                    if name2.lower() == "badwords" and _is_badwords_dir(path2):
                        found.add(os.path.abspath(path2))
                    elif name2.lower() != "badwords" and _is_badwords_dir(path2):
                        found.add(os.path.abspath(path2))
            except OSError:
                pass

    return sorted(found)


def option_uninstall():
    header()
    console.print(Text(f"{PAD}-- Uninstall BadWords --", style="bold red"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    # Fast path: detect via Resolve wrapper
    log_step("Searching via DaVinci Resolve wrapper...")
    wrapper_dir = detect_existing_install(default_dir, resolve_dirs)
    if wrapper_dir:
        log_ok(f"Wrapper found -> {wrapper_dir}")
    else:
        log_warn("No wrapper detected (may be corrupted or already removed).")

    # Deep search across popular OS locations
    sp_scan = Spinner("Deep-scanning system for BadWords installations").start()
    found_dirs = _deep_search_badwords()
    sp_scan.done(ok=True)

    # Merge wrapper result + deep search (deduplicated, wrapper first)
    all_install_dirs = list(dict.fromkeys(
        [os.path.abspath(d) for d in ([wrapper_dir] if wrapper_dir else []) + found_dirs]
    ))

    if not all_install_dirs:
        console.print()
        log_warn("No BadWords installation found anywhere on this system.")
        log_info(f"Default location checked: {default_dir}")
        pause()
        return

    # Show what was found
    console.print()
    console.print(Text(f"{PAD}Found {len(all_install_dirs)} BadWords installation(s):", style="bold white"), no_wrap=True)
    for d in all_install_dirs:
        console.print(Text(f"{PAD}  * {d}", style="red"), no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}Additionally, ALL BadWords wrappers will be removed from", style="white"), no_wrap=True)
    console.print(Text(f"{PAD}every DaVinci Resolve script directory on this system.", style="white"), no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}This removes EVERYTHING -- app files, venv, models, settings.", style="bold red"), no_wrap=True)
    console.print()
    console.print(Text(f'{PAD}Type "yes" to confirm and press Enter: ', style="bold yellow"), end="", no_wrap=True)
    sys.stdout.flush()
    try:
        answer = readline_with_esc()
    except UserCancelled:
        console.print()
        log_info("Uninstall cancelled.")
        pause()
        return
    console.print()

    if answer.strip().lower() != "yes":
        log_info("Uninstall cancelled.")
        pause()
        return

    _do_uninstall(resolve_dirs, all_install_dirs)

    # Done summary
    console.print()
    console.print(Text(f"{PAD}+ UNINSTALL SUCCESSFUL!", style="bold green"), no_wrap=True)
    console.print(Text(f"{PAD}  BadWords has been completely removed from this system.", style="green"), no_wrap=True)
    console.print()
    pause(f"{PAD}Press Enter to exit...")



def _do_uninstall(resolve_dirs, all_install_dirs):
    """
    Core deletion engine — no UI prompts, no pause.
    Removes all Resolve wrappers and every directory in all_install_dirs.
    Called by both option_uninstall() and option_reset().
    Returns a list of error strings (empty = all OK).
    """
    errors = []

    # Step 1: Remove DaVinci Resolve wrappers
    log_step("Removing DaVinci Resolve wrappers...")
    wrappers_removed = 0
    for rd in resolve_dirs:
        scripts_dir = os.path.dirname(rd)
        if not os.path.exists(scripts_dir):
            continue
        for root, dirs, files in os.walk(scripts_dir):
            for fname in files:
                if fname.startswith("BadWords") and fname.endswith(".py"):
                    wp = os.path.join(root, fname)
                    try:
                        os.remove(wp)
                        debug_log(f"Removed wrapper: {wp}")
                        wrappers_removed += 1
                    except Exception as e:
                        debug_log(f"Could not remove wrapper {wp}: {e}")
                        errors.append(f"Wrapper: {wp}")

    if wrappers_removed > 0:
        log_ok(f"Removed {wrappers_removed} wrapper file(s) from Resolve script directories.")
    else:
        log_warn("No DaVinci Resolve wrappers found (may have already been removed).")

    # Step 2: Clean Windows registry (before dir removal)
    if PLAT.startswith("win"):
        log_step("Cleaning Windows registry entries...")
        for d in all_install_dirs:
            try:
                _clean_legacy_inno_setup(d)
            except Exception as e:
                log_warn(f"Registry cleanup error for {d}: {e}")
        log_ok("Registry cleaned.")

    # Step 3: Remove all found installation directories
    for install_dir in all_install_dirs:
        log_step(f"Deleting: {install_dir}")
        sp = Spinner(f"Removing {os.path.basename(install_dir)}").start()
        try:
            def on_rm_error(func, path, exc_info):
                import stat
                try:
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                except Exception:
                    pass
            
            shutil.rmtree(install_dir, onerror=on_rm_error)
            
            # Robust OS-level fallback if Python's rmtree fails on tricky symlinks/permissions
            if os.path.exists(install_dir):
                if os.name == "nt":
                    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", install_dir], capture_output=True)
                else:
                    subprocess.run(["rm", "-rf", install_dir], capture_output=True)
            
            if os.path.exists(install_dir):
                raise OSError("Directory is locked or contains undeletable files.")
                
            sp.done(ok=True)
        except Exception as e:
            sp.done(ok=False)
            debug_log(f"rmtree error on {install_dir}: {e}")
            errors.append(f"{install_dir}: {e}")
            # Removed log_err to prevent duplicated UI spam; caller handles printing the errors.

    return errors


# ── Option 4 — Complete Reset ──────────────────────────────────
def option_reset():
    header()
    console.print(Text(f"{PAD}-- Complete Reset --", style="bold magenta"), no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}This will:", style="bold white"), no_wrap=True)
    console.print(Text(f"{PAD}  1. Remove EVERYTHING (app, venv, models, settings, wrappers)", style="magenta"), no_wrap=True)
    console.print(Text(f"{PAD}  2. Perform a fresh Standard Install from scratch", style="cyan"), no_wrap=True)
    console.print()

    resolve_dirs = _resolve_script_dirs()
    default_dir  = _default_install_dir()

    # Fast path: detect via Resolve wrapper
    log_step("Searching via DaVinci Resolve wrapper...")
    wrapper_dir = detect_existing_install(default_dir, resolve_dirs)
    if wrapper_dir:
        log_ok(f"Wrapper found -> {wrapper_dir}")
    else:
        log_warn("No wrapper detected (will still deep-scan for leftovers).")

    # Deep search
    sp_scan = Spinner("Deep-scanning system for BadWords installations").start()
    found_dirs = _deep_search_badwords()
    sp_scan.done(ok=True)

    # Merge + deduplicate
    all_install_dirs = list(dict.fromkeys(
        [os.path.abspath(d) for d in ([wrapper_dir] if wrapper_dir else []) + found_dirs]
    ))
    
    # Save the old path so we can reinstall there by default
    reinstall_default = all_install_dirs[0] if all_install_dirs else default_dir

    # Show what will be wiped
    console.print()
    if all_install_dirs:
        console.print(Text(f"{PAD}The following installation(s) will be wiped:", style="bold white"), no_wrap=True)
        for d in all_install_dirs:
            console.print(Text(f"{PAD}  * {d}", style="magenta"), no_wrap=True)
    else:
        console.print(Text(f"{PAD}No existing installation found — will do a clean install.", style="dim"), no_wrap=True)
    console.print()
    console.print(Text(f"{PAD}All data (models, settings, saves) will be permanently lost.", style="bold magenta"), no_wrap=True)
    console.print()
    console.print(Text(f'{PAD}Type "yes" to confirm Complete Reset and press Enter: ', style="bold yellow"), end="", no_wrap=True)
    sys.stdout.flush()
    try:
        answer = readline_with_esc()
    except UserCancelled:
        console.print()
        log_info("Reset cancelled.")
        pause()
        return
    console.print()

    if answer.strip().lower() != "yes":
        log_info("Reset cancelled.")
        pause()
        return

    # ── Phase 1: Uninstall ────────────────────────────────────
    console.print()
    console.print(Text(f"{PAD}[ Phase 1 / 2 ]  Wiping existing installation...", style="bold magenta"), no_wrap=True)
    console.print()

    if all_install_dirs:
        errors = _do_uninstall(resolve_dirs, all_install_dirs)
        if errors:
            console.print()
            log_warn("Some items could not be removed — continuing with install anyway:")
            for err in errors:
                console.print(Text(f"{PAD}  * {err}", style="yellow"), no_wrap=True)
    else:
        log_info("Nothing to wipe — proceeding directly to install.")

    # ── Phase 2: Fresh install ────────────────────────────────
    console.print()
    console.print(Text(f"{PAD}[ Phase 2 / 2 ]  Installing BadWords from scratch...", style="bold cyan"), no_wrap=True)
    console.print()

    # Let the user pick a new install path (or keep the default which is the previous install location)
    console.print(Text(f"{PAD}Install path: {reinstall_default}", style="dim"), no_wrap=True)
    console.print(Text(f"{PAD}Press Enter to use this path, or type a custom path: ", style="cyan"), end="", no_wrap=True)
    sys.stdout.flush()
    try:
        custom_path = readline_with_esc()
    except UserCancelled:
        custom_path = ""

    if custom_path.strip():
        custom_path = os.path.expanduser(custom_path.strip())
        if not custom_path.endswith(APP_NAME):
            custom_path = os.path.join(custom_path.rstrip("/\\"), APP_NAME)
        log_info(f"New install path: {custom_path}")
    else:
        custom_path = reinstall_default
        log_info(f"Using path: {custom_path}")

    option_install_update(preset_path=custom_path, title="── Complete Reset ──", title_color="yellow")


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
            elif choice.lower() == "d":
                option_install_update(force_main=True)
            elif choice == "2":
                option_repair()
            elif choice == "3":
                option_move()
            elif choice == "4":
                option_reset()
            elif choice == "5":
                option_uninstall()
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
