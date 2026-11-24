#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: config/runtime_data.py
ROLE: Runtime Data, Workspace Isolation, Atomic Preferences, Logging & Session Temp Manager
DESCRIPTION:
Decoupled data and filesystem management layer for BadWords:
1. DEV (.dev_workspace/) vs Installed environment detection and one-time src/ migration.
2. Persistent per-user OS profile fallback when the installation directory is read-only.
3. Atomic JSON writes with .bak corruption backup and key salvage for user.json and settings.json.
4. Single-write log deduplication (when stdout/stderr are redirected to badwords_debug.log)
   and 5 MB startup log trimming.
5. Session-protected temporary directory management with 24-hour stale cleanup.
6. Mac App Store (Apple App Sandbox) DaVinci Resolve container discovery.
"""

import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
import threading
import time
from typing import Callable, Optional, Set, Tuple


_CONFIG_LOCK = threading.RLock()

# Default 5 MB ceiling for badwords_debug.log; keep newest 2.5 MB when trimming on startup
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_KEEP_BYTES = 2560 * 1024

# Default 24-hour retention for stale temporary files from closed sessions
DEFAULT_TEMP_MAX_AGE_SECONDS = 86400


# ==========================================
# 1. DEV VS INSTALLED DETECTION & FALLBACKS
# ==========================================

def detect_dev_mode(install_dir: str) -> Tuple[bool, str]:
    """
    Detects if running in a development workspace (e.g. Git repository checkout).
    # INVARIANT: DEV mode isolates all runtime files into <repo_root>/.dev_workspace/.
    Returns: (is_dev: bool, repo_root: str)
    """
    if os.environ.get("BADWORDS_FORCE_INSTALLED") == "1":
        return False, ""
    if os.environ.get("BADWORDS_DEV") == "1":
        cur = os.path.abspath(install_dir)
        parent = os.path.dirname(cur)
        root = parent if os.path.basename(cur) == "src" else cur
        return True, root

    cur = os.path.abspath(install_dir)
    parent = os.path.dirname(cur)
    # 1. If install_dir is 'src' and parent has .git
    if os.path.basename(cur) == "src" and os.path.exists(os.path.join(parent, ".git")):
        return True, parent
    # 2. If install_dir itself has .git
    if os.path.exists(os.path.join(cur, ".git")):
        return True, cur
    # 3. If parent has .git
    if os.path.exists(os.path.join(parent, ".git")):
        return True, parent
    return False, ""


def is_dir_writable(dir_path: str) -> bool:
    """
    Empirically verifies whether dir_path can be created and written to.
    Note: On Windows, os.access(path, os.W_OK) only checks the FAT read-only attribute,
    NOT NTFS ACL permissions (such as C:\\Program Files). Probing with a temporary file
    guarantees accurate detection across Windows, Linux, and macOS.
    """
    if not dir_path:
        return False
    try:
        os.makedirs(dir_path, exist_ok=True)
        if not os.access(dir_path, os.W_OK):
            return False
        probe = os.path.join(dir_path, f".bw_write_probe_{os.getpid()}_{threading.get_ident()}")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("1")
        try:
            os.remove(probe)
        except Exception:
            pass
        return True
    except Exception:
        return False


def get_user_profile_data_dir(os_type: Optional[str] = None, home_dir: Optional[str] = None) -> str:
    """
    Returns the persistent per-user application data directory for fallback when
    the installation folder is read-only (e.g. C:\\Program Files or /Applications).
    # INVARIANT: Read-only install dirs fall back to persistent user profile data dir before OS temp.
    """
    sys_os = os_type or platform.system()
    home = home_dir or os.path.expanduser("~")
    if sys_os == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.join(home, "AppData", "Local")
        return os.path.join(base, "BadWords")
    elif sys_os == "Darwin":
        return os.path.join(home, "Library", "Application Support", "BadWords")
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        base = xdg if xdg else os.path.join(home, ".local", "share")
        return os.path.join(base, "BadWords")


def discover_sibling_installed_dir(install_dir: str, repo_root: str = "") -> str:
    """
    Dynamically discovers a sibling 'BadWords FILES' directory next to the repository root
    or installation folder without hardcoding developer machine paths.
    """
    override = os.environ.get("BADWORDS_SHARED_FILES_DIR", "").strip()
    if override and os.path.isdir(override):
        return os.path.abspath(override)

    roots = []
    if repo_root:
        roots.append(os.path.dirname(os.path.abspath(repo_root)))
    if install_dir:
        abs_inst = os.path.abspath(install_dir)
        roots.append(os.path.dirname(abs_inst))
        roots.append(os.path.dirname(os.path.dirname(abs_inst)))

    for r in roots:
        if not r:
            continue
        cand = os.path.join(r, "BadWords FILES")
        if os.path.isdir(cand):
            return os.path.abspath(cand)
    return ""


def migrate_stray_src_files_to_dev_workspace(install_dir: str, dev_data_dir: str) -> None:
    """
    One-time cleanup in DEV mode: migrates any stray config, saves, or logs from src/
    into .dev_workspace/ and removes temp/empty models from src/ so git stays clean.
    """
    try:
        os.makedirs(dev_data_dir, exist_ok=True)
    except Exception:
        return

    for fn in ("settings.json", "user.json", "pref.json", "badwords_debug.log"):
        src_cand = os.path.join(install_dir, fn)
        dst_cand = os.path.join(dev_data_dir, fn)
        if os.path.isfile(src_cand) and not os.path.isfile(dst_cand):
            try:
                shutil.copy2(src_cand, dst_cand)
            except Exception:
                pass
        if os.path.isfile(src_cand):
            try:
                os.remove(src_cand)
            except Exception:
                pass

    legacy_saves = os.path.join(install_dir, "saves")
    target_saves = os.path.join(dev_data_dir, "saves")
    if os.path.isdir(legacy_saves):
        try:
            os.makedirs(target_saves, exist_ok=True)
            for item in os.listdir(legacy_saves):
                s = os.path.join(legacy_saves, item)
                d = os.path.join(target_saves, item)
                if not os.path.exists(d):
                    shutil.move(s, d)
            shutil.rmtree(legacy_saves)
        except Exception:
            pass

    legacy_temp = os.path.join(install_dir, "temp")
    if os.path.isdir(legacy_temp):
        try:
            shutil.rmtree(legacy_temp)
        except Exception:
            pass

    legacy_models = os.path.join(install_dir, "models")
    if os.path.isdir(legacy_models) and not os.listdir(legacy_models):
        try:
            os.rmdir(legacy_models)
        except Exception:
            pass


def read_startup_ui_scale_prefs(install_dir: str = "") -> Tuple[Optional[str], Optional[int]]:
    """
    Lightweight read-only helper for startup before OSDoctor/BootSplash initialization.
    Reads ("ui_scale_mode", "ui_scale_pct") from the active runtime settings.json without
    creating files or mutating state. Returns (None, None) when missing/uninitialized.
    """
    try:
        base_dir = install_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        is_dev, repo_root = detect_dev_mode(base_dir)
        candidates = []
        if is_dev and repo_root:
            candidates.append(os.path.join(repo_root, ".dev_workspace", "settings.json"))
        else:
            candidates.append(os.path.join(base_dir, "settings.json"))
            candidates.append(os.path.join(get_user_profile_data_dir(), "settings.json"))

        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    mode = data.get("ui_scale_mode")
                    pct = data.get("ui_scale_pct")
                    norm_mode = mode if mode in ("auto", "manual") else None
                    norm_pct = int(pct) if pct is not None and norm_mode == "manual" else None
                    return norm_mode, norm_pct
            except Exception:
                continue
    except Exception:
        pass
    return None, None


# ==========================================
# 2. ATOMIC JSON PERSISTENCE & CORRUPT SALVAGE
# ==========================================

def atomic_write_json(file_path: str, data: dict, indent: int = 4) -> None:
    """
    Atomically writes a JSON dictionary to file_path using a sibling temp file,
    fsync, and os.replace, protected by a re-entrant lock.
    # INVARIANT: All user.json and settings.json writes must be atomic so power loss never truncates files.
    """
    if not file_path:
        raise ValueError("file_path must not be empty")
    parent = os.path.dirname(os.path.abspath(file_path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    payload = json.dumps(data, indent=indent, ensure_ascii=False)
    with _CONFIG_LOCK:
        tmp_path = f"{file_path}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(payload)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
            os.replace(tmp_path, file_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


def _salvage_json_primitives(raw_text: str, allowed_keys: Set[str]) -> dict:
    """
    Best-effort line/regex recovery of simple JSON key-value pairs from a partially
    truncated or corrupted JSON file, restricted to known schema keys.
    """
    recovered = {}
    if not raw_text:
        return recovered
    # Match `"key": value` pairs for strings, booleans, null, ints, floats
    pattern = re.compile(
        r'"([A-Za-z0-9_]+)"\s*:\s*('
        r'true|false|null|'
        r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|'
        r'"(?:[^"\\]|\\.)*"'
        r')'
    )
    for m in pattern.finditer(raw_text):
        k, raw_val = m.group(1), m.group(2)
        if k in allowed_keys:
            try:
                recovered[k] = json.loads(raw_val)
            except Exception:
                pass
    return recovered


def load_json_with_recovery(
    file_path: str,
    defaults: dict,
    log_err_fn: Optional[Callable[[str], None]] = None,
    log_info_fn: Optional[Callable[[str], None]] = None,
) -> Tuple[dict, bool]:
    """
    Loads a JSON config file safely. If the file is corrupted:
    1. Backs up the corrupted file to `<file_path>.bak` so user data is never silently lost.
    2. Salvages any valid key-value pairs from the corrupted text.
    3. Returns `(loaded_dict, was_corrupt)`.
    """
    if not file_path or not os.path.exists(file_path):
        return {}, False

    with _CONFIG_LOCK:
        raw_text = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
            loaded = json.loads(raw_text)
            if isinstance(loaded, dict):
                return loaded, False
            raise ValueError("Root JSON value is not an object/dict")
        except Exception as e:
            bak_path = f"{file_path}.bak"
            try:
                shutil.copy2(file_path, bak_path)
                if log_info_fn:
                    log_info_fn(f"Preserved backup of corrupted config at: {bak_path}")
            except Exception as be:
                if log_err_fn:
                    log_err_fn(f"Could not write corrupt config backup {bak_path}: {be}")

            salvaged = _salvage_json_primitives(raw_text, set(defaults.keys()))
            if log_err_fn:
                log_err_fn(
                    f"Corrupt config file {os.path.basename(file_path)} ({e}); "
                    f"backed up to {os.path.basename(bak_path)} and salvaged {len(salvaged)} key(s)."
                )
            return salvaged, True


# ==========================================
# 3. LOGGING DEDUPLICATION & 5 MB ROTATION
# ==========================================

def trim_log_file_if_needed(
    log_file: str,
    max_bytes: int = LOG_MAX_BYTES,
    keep_bytes: int = LOG_KEEP_BYTES,
) -> bool:
    """
    Checks if log_file exceeds max_bytes (default 5 MB). If so, trims the oldest content,
    keeping the newest keep_bytes (default 2.5 MB) aligned to a line boundary.
    Returns True if the file was trimmed.
    """
    if not log_file or not os.path.isfile(log_file):
        return False
    try:
        size = os.path.getsize(log_file)
        if size <= max_bytes:
            return False

        keep = max(64 * 1024, min(keep_bytes, max_bytes - 1024))
        with open(log_file, "rb") as f:
            f.seek(max(0, size - keep))
            tail = f.read()

        nl_idx = tail.find(b"\n")
        if 0 <= nl_idx < len(tail) - 1:
            tail = tail[nl_idx + 1:]

        header = (
            f"=== [LOG TRIMMED ON STARTUP: previous size {size} bytes exceeded {max_bytes} bytes; "
            f"kept newest {len(tail)} bytes] ===\n"
        ).encode("utf-8")

        tmp_path = f"{log_file}.{os.getpid()}.trim.tmp"
        with open(tmp_path, "wb") as out:
            out.write(header)
            out.write(tail)
            out.flush()
            try:
                os.fsync(out.fileno())
            except OSError:
                pass
        os.replace(tmp_path, log_file)
        return True
    except Exception:
        return False


def is_stream_redirected_to_file(stream, target_file_path: str) -> bool:
    """
    Returns True if `stream` (e.g. sys.__stdout__ or sys.__stderr__) refers to the same
    underlying file as `target_file_path` (which happens when the native C launcher
    redirects FD 1 and FD 2 to badwords_debug.log via dup2).
    # INVARIANT: Never print duplicate console lines when stdout/stderr points to badwords_debug.log.
    """
    if os.environ.get("BADWORDS_STDIO_REDIRECTED") == "1":
        return True
    if stream is None or not target_file_path or not os.path.exists(target_file_path):
        return False
    try:
        if not hasattr(stream, "fileno"):
            return False
        s_fd = stream.fileno()
        with open(target_file_path, "rb") as tf:
            return os.path.sameopenfile(s_fd, tf.fileno())
    except Exception:
        return False


# ==========================================
# 4. SESSION-PROTECTED TEMP CLEANUP
# ==========================================

def _is_pid_alive(pid: int) -> bool:
    """Checks whether a process with the given PID is currently alive on this OS."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:
        pass

    if sys.platform == "win32" or os.name == "nt":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                return False
            try:
                exit_code = ctypes.c_ulong(0)
                if k32.GetExitCodeProcess(h, ctypes.byref(exit_code)):
                    return exit_code.value == STILL_ACTIVE
                return True
            finally:
                k32.CloseHandle(h)
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False


class SessionTempManager:
    """
    Tracks active temporary files/directories for the current session and coordinates
    safe cleanup across long editing sessions and multiple application instances.
    # INVARIANT: Active session temp files (audio, proxy video, extracted .bws) are never deleted mid-session.
    """

    def __init__(self, temp_dir: str):
        self.temp_dir = os.path.abspath(temp_dir)
        self.pid = os.getpid()
        self.started_at = time.time()
        self._lock = threading.RLock()
        self.active_paths: Set[str] = set()
        self._session_file = os.path.join(self.temp_dir, f".bw_session_{self.pid}.json")
        self._write_session_lock()

    def _write_session_lock(self) -> None:
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            data = {
                "pid": self.pid,
                "started_at": self.started_at,
                "protected_paths": sorted(self.active_paths),
                "updated_at": time.time(),
            }
            atomic_write_json(self._session_file, data)
        except Exception:
            pass

    def register_path(self, path: str) -> None:
        """Marks a temporary file or folder as actively in use by the current project/session."""
        if not path:
            return
        norm = os.path.abspath(path)
        with self._lock:
            if norm not in self.active_paths:
                self.active_paths.add(norm)
                self._write_session_lock()

    def unregister_path(self, path: str) -> None:
        """Releases session protection for a temporary file or folder."""
        if not path:
            return
        norm = os.path.abspath(path)
        with self._lock:
            if norm in self.active_paths:
                self.active_paths.discard(norm)
                self._write_session_lock()

    def _collect_live_sessions(self, include_self: bool = True) -> Tuple[Set[str], Set[str]]:
        """
        Scans `.bw_session_*.json` lock files in temp_dir.
        Removes stale lock files belonging to dead PIDs.
        Returns: (live_lock_files, protected_abs_paths)
        """
        live_locks: Set[str] = set()
        protected: Set[str] = set()

        if include_self:
            with self._lock:
                live_locks.add(os.path.abspath(self._session_file))
                protected.update(self.active_paths)

        if not os.path.isdir(self.temp_dir):
            return live_locks, protected

        try:
            for entry in os.listdir(self.temp_dir):
                if not (entry.startswith(".bw_session_") and entry.endswith(".json")):
                    continue
                lock_fp = os.path.abspath(os.path.join(self.temp_dir, entry))
                if lock_fp == os.path.abspath(self._session_file):
                    if include_self:
                        live_locks.add(lock_fp)
                    continue
                try:
                    with open(lock_fp, "r", encoding="utf-8") as f:
                        info = json.load(f)
                    other_pid = int(info.get("pid", -1))
                    if _is_pid_alive(other_pid):
                        live_locks.add(lock_fp)
                        for p in info.get("protected_paths", []):
                            if p:
                                protected.add(os.path.abspath(p))
                    else:
                        try:
                            os.remove(lock_fp)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        return live_locks, protected

    @staticmethod
    def _is_path_protected(candidate_abs: str, protected_roots: Set[str]) -> bool:
        for prot in protected_roots:
            if candidate_abs == prot:
                return True
            prefix = prot.rstrip("/\\") + os.sep
            if candidate_abs.startswith(prefix):
                return True
        return False

    def _is_transient_helper_for_current_pid(self, filename: str) -> bool:
        """Identifies one-shot helper scripts and concat lists that can be deleted immediately on session close."""
        if filename == "fw_downloader.py":
            return True
        if filename.startswith("bw_runner_") and filename.endswith(".py"):
            return True
        if filename.startswith("bw_drt_probe_") and filename.endswith(".drt"):
            return True
        pid_tag = f"_{self.pid}_"
        if pid_tag in filename and (
            filename.startswith("concat_audio_")
            or filename.startswith("concat_proxy_")
            or filename.startswith("tmp_part_")
            or filename.startswith("tmp_proxy_part_")
        ):
            return True
        return False

    def cleanup(
        self,
        max_age_seconds: int = DEFAULT_TEMP_MAX_AGE_SECONDS,
        close_session: bool = False,
        log_err_fn: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Safely cleans stale temporary files older than max_age_seconds (default 24 hours)
        while strictly protecting all files and folders registered to any live session.
        When close_session=True, also removes the current session lock and one-shot helper files.
        """
        try:
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir, exist_ok=True)
                return

            if close_session:
                with self._lock:
                    self.active_paths.clear()
                if os.path.exists(self._session_file):
                    try:
                        os.remove(self._session_file)
                    except Exception:
                        pass

            live_locks, protected_paths = self._collect_live_sessions(include_self=not close_session)
            now = time.time()

            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for f in files:
                    fp = os.path.abspath(os.path.join(root, f))
                    if fp in live_locks:
                        continue
                    if self._is_path_protected(fp, protected_paths):
                        continue
                    try:
                        if close_session and self._is_transient_helper_for_current_pid(f):
                            os.remove(fp)
                            continue
                        if now - os.path.getmtime(fp) > max_age_seconds:
                            os.remove(fp)
                    except Exception:
                        pass

                for d in dirs:
                    dp = os.path.abspath(os.path.join(root, d))
                    if self._is_path_protected(dp, protected_paths):
                        continue
                    try:
                        os.rmdir(dp)
                    except Exception:
                        pass
        except Exception as e:
            if log_err_fn:
                log_err_fn(f"cleanup_temp: failed to clear temp directory {self.temp_dir}: {e}")


# ==========================================
# 5. MAC APP STORE DAVINCI RESOLVE CONTAINERS
# ==========================================

_MAS_KNOWN_BUNDLE_IDS = (
    "com.blackmagic-design.DaVinciResolveLite",
    "com.blackmagic-design.DaVinciResolveAppStore",
    "com.blackmagic-design.DaVinciResolve",
    "com.blackmagic-design.DaVinciResolveStudio",
)


def get_macos_app_store_resolve_dirs(home_dir: Optional[str] = None) -> list:
    """
    Discovers existing Mac App Store (Apple App Sandbox) container directories for DaVinci Resolve:
        ~/Library/Containers/<bundle-id>/Data/Library/Application Support/Blackmagic Design/DaVinci Resolve
    Only returns paths whose container root (`~/Library/Containers/<bundle-id>`) actually exists on disk.
    """
    home = home_dir or os.path.expanduser("~")
    containers_root = os.path.join(home, "Library", "Containers")
    if not os.path.isdir(containers_root):
        return []

    candidate_bundles = list(_MAS_KNOWN_BUNDLE_IDS)
    try:
        for entry in os.listdir(containers_root):
            low = entry.lower()
            if ("davinci" in low or "blackmagic" in low) and entry not in candidate_bundles:
                candidate_bundles.append(entry)
    except Exception:
        pass

    found = []
    seen = set()
    for bid in candidate_bundles:
        container_dir = os.path.join(containers_root, bid)
        if not os.path.isdir(container_dir):
            continue
        resolve_support = os.path.join(
            container_dir,
            "Data",
            "Library",
            "Application Support",
            "Blackmagic Design",
            "DaVinci Resolve",
        )
        norm = os.path.abspath(resolve_support)
        if norm not in seen:
            seen.add(norm)
            found.append(resolve_support)
    return found
