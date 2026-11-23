#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/crash_report.py
ROLE: Startup & Runtime Crash Reporter
DESCRIPTION:
Stdlib-only crash report packager, privacy scrubber, anti-spam deduplicator,
and runtime exception hook installer matching the Settings -> Support webhook
format so startup and runtime failures are safely delivered to Discord.
Must remain parseable by Python 3.8 grammar.
"""

import getpass
import hashlib
import io
import json
import os
import platform
import re
import ssl
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
import zipfile

_MAX_LOG_BYTES = 256 * 1024
_MAX_TB_CHARS = 4000
_MAX_PER_SESSION = 3
_MAX_PER_HOUR = 5
_HOUR_WINDOW_SEC = 3600
_MAX_STORED_FINGERPRINTS = 500

_MEDIA_EXT_PATTERN = (
    r"mp4|mov|mkv|avi|webm|mxf|mts|m2ts|wmv|flv|"
    r"wav|mp3|flac|m4a|aac|ogg|opus|wma|aiff|"
    r"docx|doc|pdf|txt|rtf|odt|srt|ass|vtt|"
    r"bws|drt|fcpxml|otio|edl|xml"
)
_MEDIA_PATH_RE = re.compile(
    r'(?:[A-Za-z]:[\\/]|/)[^\s"\'\<\>\|\*\?\r\n]+?\.(' + _MEDIA_EXT_PATTERN + r')\b',
    re.IGNORECASE,
)
_WIN_USER_PATH_RE = re.compile(r'([A-Za-z]:[\\/]+Users[\\/]+)([^\\/\s"\'\<\>]+)', re.IGNORECASE)
_WIN_DOCS_PATH_RE = re.compile(r'([A-Za-z]:[\\/]+Documents and Settings[\\/]+)([^\\/\s"\'\<\>]+)', re.IGNORECASE)
_UNIX_USER_PATH_RE = re.compile(r'(/(?:home|Users)/)([^/\s"\'\<\>]+)')
_WEBHOOK_RE = re.compile(r'https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/[^\s"\'\<\>]+', re.IGNORECASE)
_EMAIL_RE = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
_HEX_ADDR_RE = re.compile(r'0x[0-9a-fA-F]+')


def _default_src_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_dev_checkout(src_dir):
    if os.environ.get("BADWORDS_FORCE_INSTALLED") == "1":
        return False
    if os.environ.get("BADWORDS_DEV") == "1":
        return True
    base = os.path.abspath(src_dir)
    parent = os.path.dirname(base)
    return os.path.exists(os.path.join(base, ".git")) or os.path.exists(os.path.join(parent, ".git"))


def _resolve_app_data_candidates(src_dir=None, app_data_dir=None):
    """Return ordered list of candidate runtime data directories."""
    cands = []
    if app_data_dir:
        cands.append(os.path.abspath(app_data_dir))
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    if _is_dev_checkout(base):
        cands.append(os.path.join(parent, ".dev_workspace"))
        cands.append(os.path.join(base, ".dev_workspace"))
    else:
        cands.append(base)
        cands.append(parent)
    cands.append(os.path.join(tempfile.gettempdir(), "BadWords_Fallback"))
    seen = set()
    unique = []
    for p in cands:
        norm = os.path.abspath(p)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def _resolve_writable_data_dir(src_dir=None, app_data_dir=None):
    for cand in _resolve_app_data_candidates(src_dir, app_data_dir):
        if os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    if _is_dev_checkout(base):
        target = os.path.join(parent, ".dev_workspace")
    else:
        target = base if os.access(base, os.W_OK) else os.path.join(tempfile.gettempdir(), "BadWords_Fallback")
    try:
        os.makedirs(target, exist_ok=True)
    except Exception:
        return tempfile.gettempdir()
    return target


def get_auto_crash_report_pref(src_dir=None, app_data_dir=None):
    """Read auto_crash_report preference from user.json without importing GUI/osdoc.

    Returns True, False, or None if not yet recorded. Never raises.
    """
    for cand in _resolve_app_data_candidates(src_dir, app_data_dir):
        user_file = os.path.join(cand, "user.json")
        if os.path.isfile(user_file):
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "auto_crash_report" in data:
                    val = data.get("auto_crash_report")
                    if isinstance(val, bool):
                        return val
                    if val is None:
                        return None
                    if str(val).strip().lower() in ("true", "1", "yes"):
                        return True
                    if str(val).strip().lower() in ("false", "0", "no"):
                        return False
                return None
            except Exception:
                return None
    return None


def _read_app_constants(src_dir=None):
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)

    version = ""
    for v_cand in (
        os.path.join(parent, ".version"),
        os.path.join(base, ".version"),
        os.path.join(base, "config", ".version"),
    ):
        if os.path.isfile(v_cand):
            try:
                with open(v_cand, "r", encoding="utf-8") as f:
                    v = f.read().strip().lstrip("vV")
                if v:
                    version = v
                    break
            except Exception:
                pass

    webhook_url = ""
    const_path = os.path.join(base, "config", "app_constants.py")
    if os.path.isfile(const_path):
        try:
            with open(const_path, "r", encoding="utf-8") as f:
                text = f.read()
            m_url = re.search(r'SUPPORT_WEBHOOK_URL\s*=\s*["\']([^"\']+)["\']', text)
            if m_url:
                webhook_url = m_url.group(1).strip()
            if not version:
                m_ver = re.search(r'_DEFAULT_VERSION\s*=\s*["\']([^"\']+)["\']', text)
                if m_ver:
                    version = m_ver.group(1).strip()
        except Exception:
            pass

    return webhook_url, (version or "Unknown")


def find_log_files(src_dir=None, app_data_dir=None):
    """Return existing BadWords debug log file paths ordered by relevance."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    candidates = []
    for d in _resolve_app_data_candidates(base, app_data_dir):
        candidates.append(os.path.join(d, "badwords_debug.log"))
        candidates.append(os.path.join(d, "badwords.log"))
    candidates.append(os.path.join(base, "badwords_debug.log"))
    candidates.append(os.path.join(os.path.dirname(base), "badwords_debug.log"))

    found = []
    seen = set()
    for path in candidates:
        norm = os.path.abspath(path)
        if norm not in seen and os.path.isfile(norm):
            seen.add(norm)
            found.append(norm)
    return found


def primary_log_hint(src_dir=None, app_data_dir=None):
    """Return an existing log path or the expected log path for user messages."""
    existing = find_log_files(src_dir, app_data_dir)
    if existing:
        return existing[0]
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    if _is_dev_checkout(base):
        return os.path.join(parent, ".dev_workspace", "badwords_debug.log")
    return os.path.join(base, "badwords_debug.log")


def sanitize_crash_text(text, src_dir=None):
    """Scrub usernames, home directories, hostnames, webhooks, emails, and private media paths."""
    if not text:
        return ""
    out = str(text)

    # Collect active OS and path-extracted usernames before replacing paths
    tokens = set()
    try:
        tokens.add(getpass.getuser())
    except Exception:
        pass
    for env_key in ("USERNAME", "USER", "LOGNAME", "COMPUTERNAME", "HOSTNAME"):
        val = os.environ.get(env_key, "").strip()
        if val:
            tokens.add(val)
    try:
        node = platform.node()
        if node:
            tokens.add(node)
    except Exception:
        pass
    for regex in (_WIN_USER_PATH_RE, _WIN_DOCS_PATH_RE, _UNIX_USER_PATH_RE):
        for m in regex.finditer(out):
            if m.group(2):
                tokens.add(m.group(2))

    # 1. Scrub private media/script/project paths BEFORE home-dir substitution
    def _scrub_media(match):
        full = match.group(0)
        ext = match.group(1)
        lowered = full.replace("\\", "/").lower()
        if "/badwords/" in lowered and ("/src/" in lowered or "/setupfiles/" in lowered or "/tests/" in lowered):
            return full
        return "<MEDIA_FILE>." + ext.lower()

    out = _MEDIA_PATH_RE.sub(_scrub_media, out)

    # 2. Scrub explicit user home path (both separator styles)
    try:
        home = os.path.expanduser("~")
        if home and len(home) > 2:
            for variant in set([home, os.path.abspath(home), home.replace("\\", "/"), home.replace("/", "\\")]):
                if variant and len(variant) > 2:
                    pattern = re.compile(re.escape(variant), re.IGNORECASE)
                    out = pattern.sub("<USER_HOME>", out)
    except Exception:
        pass

    # 3. Scrub profile paths across Windows/macOS/Linux
    out = _WIN_USER_PATH_RE.sub(r"<USER_HOME>", out)
    out = _WIN_DOCS_PATH_RE.sub(r"<USER_HOME>", out)
    out = _UNIX_USER_PATH_RE.sub(r"\1<USER>", out)

    # 4. Scrub remaining username / hostname occurrences
    for tok in sorted(tokens, key=len, reverse=True):
        if len(tok) >= 3 and tok.lower() not in ("root", "user", "admin", "linux", "windows", "python", "badwords"):
            out = re.sub(r'(?<![A-Za-z0-9_])' + re.escape(tok) + r'(?![A-Za-z0-9_])', "<REDACTED>", out, flags=re.IGNORECASE)

    # 5. Scrub webhooks and email addresses
    out = _WEBHOOK_RE.sub("<WEBHOOK_REDACTED>", out)
    out = _EMAIL_RE.sub("<EMAIL_REDACTED>", out)

    return out


def compute_crash_fingerprint(error_text, tb_text="", category="Runtime"):
    """Compute a stable deduplication hash for an error + callstack."""
    err_first = ""
    if error_text:
        err_first = sanitize_crash_text(str(error_text).strip().splitlines()[0])
        err_first = _HEX_ADDR_RE.sub("0xADDR", err_first)[:160]

    frames = []
    if tb_text:
        for line in str(tb_text).splitlines():
            s = line.strip()
            if s.startswith('File "') or s.startswith("File '"):
                m = re.match(r'File\s+["\']([^"\']+)["\'],\s+line\s+(\d+)(?:,\s+in\s+(\S+))?', s)
                if m:
                    fname = os.path.basename(m.group(1))
                    lineno = m.group(2)
                    func = m.group(3) or "?"
                    frames.append("{0}:{1}:{2}".format(fname, lineno, func))
    tail_frames = "|".join(frames[-4:])
    raw_sig = "{0}|{1}|{2}".format(category, tail_frames, err_first)
    return hashlib.sha256(raw_sig.encode("utf-8", errors="replace")).hexdigest()[:16]


class _CrashRateLimiter:
    """Thread-safe in-memory and disk-persisted anti-spam limiter."""

    def __init__(self):
        self._lock = threading.Lock()
        self._seen_session = set()
        self._session_count = 0
        self._in_progress = threading.local()

    def is_reentrant(self):
        return bool(getattr(self._in_progress, "active", False))

    def set_reentrant(self, val):
        self._in_progress.active = bool(val)

    def _ledger_path(self, src_dir=None, app_data_dir=None):
        data_dir = _resolve_writable_data_dir(src_dir, app_data_dir)
        return os.path.join(data_dir, "crash_guard_state.json")

    def _load_ledger(self, path, now):
        state = {"fingerprints": {}, "timestamps": []}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    fps = raw.get("fingerprints", {})
                    if isinstance(fps, dict):
                        items = sorted(
                            ((str(k), float(v)) for k, v in fps.items()),
                            key=lambda kv: kv[1],
                            reverse=True,
                        )[:_MAX_STORED_FINGERPRINTS]
                        state["fingerprints"] = dict(items)
                    ts_list = raw.get("timestamps", [])
                    if isinstance(ts_list, list):
                        state["timestamps"] = [
                            float(t) for t in ts_list if (now - float(t)) < _HOUR_WINDOW_SEC
                        ]
            except Exception:
                pass
        return state

    def _save_ledger(self, path, state):
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    def try_acquire(self, fingerprint, src_dir=None, app_data_dir=None):
        """Return (allowed: bool, reason: str) and reserve slot if allowed.

        Identical fingerprints are permanently deduplicated (never sent twice).
        """
        now = time.time()
        with self._lock:
            if self._session_count >= _MAX_PER_SESSION:
                return False, "session_cap"
            if fingerprint in self._seen_session:
                return False, "session_duplicate"

            ledger_path = self._ledger_path(src_dir, app_data_dir)
            state = self._load_ledger(ledger_path, now)
            if fingerprint in state["fingerprints"]:
                self._seen_session.add(fingerprint)
                return False, "already_reported"

            recent_ts = [t for t in state["timestamps"] if (now - t) < _HOUR_WINDOW_SEC]
            if len(recent_ts) >= _MAX_PER_HOUR:
                return False, "hourly_cap"

            self._seen_session.add(fingerprint)
            self._session_count += 1
            state["fingerprints"][fingerprint] = now
            if len(state["fingerprints"]) > _MAX_STORED_FINGERPRINTS:
                keep = sorted(state["fingerprints"].items(), key=lambda kv: kv[1], reverse=True)[:_MAX_STORED_FINGERPRINTS]
                state["fingerprints"] = dict(keep)
            recent_ts.append(now)
            state["timestamps"] = recent_ts
            self._save_ledger(ledger_path, state)
            return True, "ok"

    def reset_for_tests(self):
        with self._lock:
            self._seen_session.clear()
            self._session_count = 0


_RATE_LIMITER = _CrashRateLimiter()


def reset_rate_limiter_for_tests():
    _RATE_LIMITER.reset_for_tests()


def build_report(error_text, tb_text="", src_dir=None, category="Startup crash", extra_context=None):
    """Return sanitized (title, body) summarizing the error and runtime context."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    clean_err = sanitize_crash_text(str(error_text or "Unexpected error").strip(), src_dir=base)
    first_line = clean_err.splitlines()[0] if clean_err else "Unexpected error"
    cat_label = str(category or "Crash").strip()
    title = "[{0}] {1}".format(cat_label, first_line[:96])

    fp = compute_crash_fingerprint(clean_err, tb_text=tb_text, category=cat_label)
    os_summary = "{0} {1} ({2})".format(
        platform.system() or "Unknown",
        platform.release() or "",
        platform.machine() or "",
    ).strip()

    lines = [
        "Fingerprint: {0}".format(fp),
        "Category: {0}".format(cat_label),
        "Error: {0}".format(clean_err),
        "",
        "OS: {0}".format(os_summary),
        "Python: {0}".format(sys.version.split()[0]),
        "BADWORDS_EMBEDDED: {0}".format(os.environ.get("BADWORDS_EMBEDDED", "")),
        "PYTHONHOME set: {0}".format("PYTHONHOME" in os.environ),
        "CONDA_PREFIX set: {0}".format("CONDA_PREFIX" in os.environ),
        "VIRTUAL_ENV set: {0}".format("VIRTUAL_ENV" in os.environ),
    ]
    if extra_context and isinstance(extra_context, dict):
        for k, v in extra_context.items():
            lines.append("{0}: {1}".format(k, sanitize_crash_text(str(v), src_dir=base)))

    if tb_text:
        clean_tb = sanitize_crash_text(str(tb_text).strip(), src_dir=base)
        if len(clean_tb) > _MAX_TB_CHARS:
            clean_tb = "...(truncated)...\n" + clean_tb[-_MAX_TB_CHARS:]
        lines.extend(["", "Traceback:", clean_tb])

    return title, "\n".join(lines)


def _build_logs_zip(body_text, src_dir, app_data_dir=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("system_info.txt", body_text.encode("utf-8", errors="replace"))
        for idx, log_path in enumerate(find_log_files(src_dir, app_data_dir=app_data_dir)):
            try:
                size = os.path.getsize(log_path)
                with open(log_path, "rb") as f:
                    if size > _MAX_LOG_BYTES:
                        f.seek(size - _MAX_LOG_BYTES)
                    raw_text = f.read().decode("utf-8", errors="replace")
                clean_log = sanitize_crash_text(raw_text, src_dir=src_dir)
                arc_name = os.path.basename(log_path) if idx == 0 else "{0}_{1}".format(idx, os.path.basename(log_path))
                zf.writestr(arc_name, clean_log.encode("utf-8", errors="replace"))
            except Exception:
                pass
    return buf.getvalue()


def build_multipart(fields, zip_bytes):
    """Build multipart/form-data payload matching Settings -> Contact."""
    boundary = "----BadWordsBoundary{0}".format(uuid.uuid4().hex)
    body_bytes = bytearray()
    crlf = b"\r\n"

    for key, val in fields.items():
        body_bytes.extend(b"--" + boundary.encode("ascii") + crlf)
        disp = 'Content-Disposition: form-data; name="{0}"'.format(key)
        body_bytes.extend(disp.encode("utf-8") + crlf + crlf)
        body_bytes.extend(str(val).encode("utf-8") + crlf)

    if zip_bytes is not None:
        body_bytes.extend(b"--" + boundary.encode("ascii") + crlf)
        body_bytes.extend(
            b'Content-Disposition: form-data; name="file"; filename="logs.zip"' + crlf
        )
        body_bytes.extend(b"Content-Type: application/zip" + crlf + crlf)
        body_bytes.extend(zip_bytes)
        body_bytes.extend(crlf)

    body_bytes.extend(b"--" + boundary.encode("ascii") + b"--" + crlf)
    content_type = "multipart/form-data; boundary={0}".format(boundary)
    return bytes(body_bytes), content_type


def post_support_report(webhook_url, version, title, body, email="Brak", zip_bytes=None, timeout=20):
    """Format and POST support or crash report to SUPPORT_WEBHOOK_URL. Return (ok, detail)."""
    if not webhook_url:
        return False, "Missing webhook URL"

    safe_ver = str(version or "Unknown").strip() or "Unknown"
    safe_email = str(email or "").strip() or "Brak"
    safe_title = str(title or "").strip() or "No title"
    safe_body = str(body or "").strip()

    # Relay server at SUPPORT_WEBHOOK_URL validates the original Polish header markers.
    raw_content = (
        "@here\n>>> **Wersja:** {0}\n**Email:** {1}\n**Tytuł:** {2}\n\n**Treść:**\n{3}"
    ).format(safe_ver, safe_email, safe_title, safe_body)
    content_msg = raw_content[:1900]

    fields = {
        "title": safe_title,
        "body": safe_body,
        "email": safe_email,
        "version": safe_ver,
        "content": content_msg,
    }
    payload, content_type = build_multipart(fields, zip_bytes)

    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(payload)),
        "User-Agent": "BadWords/{0}".format(safe_ver),
    }

    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()

    try:
        req = urllib.request.Request(webhook_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            code = resp.getcode()
            resp_text = resp.read().decode("utf-8", errors="replace") if hasattr(resp, "read") else ""
            return (code in (200, 201, 202, 204)), resp_text
    except urllib.error.HTTPError as he:
        err_body = ""
        try:
            err_body = he.read().decode("utf-8", errors="replace").strip()
        except Exception:
            pass
        detail = "HTTP {0}: {1}".format(he.code, err_body or he.reason)
        return False, detail
    except Exception as e:
        return False, str(e)


def send_report(
    error_text,
    tb_text="",
    src_dir=None,
    timeout=20,
    category="Startup crash",
    app_data_dir=None,
    bypass_rate_limit=False,
    allow_dev=False,
    suppress_in_dev=False,
    extra_context=None,
):
    """Package sanitized diagnostics and POST to SUPPORT_WEBHOOK_URL. Never raises."""
    if _RATE_LIMITER.is_reentrant():
        return False
    _RATE_LIMITER.set_reentrant(True)
    try:
        base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
        if suppress_in_dev and not allow_dev and _is_dev_checkout(base):
            if os.environ.get("BADWORDS_FORCE_CRASH_SEND") != "1":
                return False

        webhook_url, version = _read_app_constants(base)
        if not webhook_url:
            return False

        if not bypass_rate_limit:
            fp = compute_crash_fingerprint(error_text, tb_text=tb_text, category=category)
            allowed, _ = _RATE_LIMITER.try_acquire(fp, src_dir=base, app_data_dir=app_data_dir)
            if not allowed:
                return False

        title, body = build_report(
            error_text,
            tb_text=tb_text,
            src_dir=base,
            category=category,
            extra_context=extra_context,
        )
        zip_bytes = _build_logs_zip(body, base, app_data_dir=app_data_dir)
        ok, _ = post_support_report(
            webhook_url,
            version=version,
            title=title,
            body=body,
            email="Brak",
            zip_bytes=zip_bytes,
            timeout=timeout,
        )
        return ok
    except Exception:
        return False
    finally:
        _RATE_LIMITER.set_reentrant(False)


_PENDING_LOCK = threading.Lock()
_PENDING_THREADS = []


def _track_thread(th):
    with _PENDING_LOCK:
        _PENDING_THREADS[:] = [t for t in _PENDING_THREADS if t.is_alive()]
        _PENDING_THREADS.append(th)


def wait_for_pending_reports(timeout=3.5):
    """Wait briefly for active background crash uploads before exiting."""
    deadline = time.time() + float(timeout)
    with _PENDING_LOCK:
        threads = list(_PENDING_THREADS)
    for th in threads:
        remaining = deadline - time.time()
        if remaining <= 0:
            break
        try:
            if th.is_alive():
                th.join(timeout=remaining)
        except Exception:
            pass


def send_report_async(
    error_text,
    tb_text="",
    src_dir=None,
    timeout=15,
    category="Startup crash",
    app_data_dir=None,
    bypass_rate_limit=False,
    allow_dev=False,
    suppress_in_dev=True,
    extra_context=None,
):
    """Dispatch send_report on a daemon thread and return (thread, result_dict)."""
    result = {"done": False, "ok": False}

    def _worker():
        try:
            result["ok"] = bool(
                send_report(
                    error_text,
                    tb_text=tb_text,
                    src_dir=src_dir,
                    timeout=timeout,
                    category=category,
                    app_data_dir=app_data_dir,
                    bypass_rate_limit=bypass_rate_limit,
                    allow_dev=allow_dev,
                    suppress_in_dev=suppress_in_dev,
                    extra_context=extra_context,
                )
            )
        finally:
            result["done"] = True

    th = threading.Thread(target=_worker, name="BadWords-CrashReport", daemon=True)
    _track_thread(th)
    th.start()
    return th, result


def send_runtime_crash_async(
    exc_type,
    exc_value,
    exc_tb,
    context_label="Main thread",
    src_dir=None,
    app_data_dir=None,
    allow_dev=False,
):
    """Format an uncaught runtime exception and upload asynchronously if user opted in."""
    try:
        if exc_type is not None and issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            return None
    except Exception:
        pass

    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    if get_auto_crash_report_pref(base, app_data_dir=app_data_dir) is not True:
        return None

    err_name = getattr(exc_type, "__name__", "Error") if exc_type else "Error"
    err_msg = "{0}: {1}".format(err_name, exc_value) if exc_value else err_name
    tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

    if not allow_dev and _is_dev_checkout(base) and os.environ.get("BADWORDS_FORCE_CRASH_SEND") != "1":
        return None

    th, _ = send_report_async(
        err_msg,
        tb_text=tb_text,
        src_dir=base,
        timeout=15,
        category="Auto crash ({0})".format(context_label),
        app_data_dir=app_data_dir,
        bypass_rate_limit=False,
        allow_dev=allow_dev,
        suppress_in_dev=not allow_dev,
    )
    return th


def _log_uncaught_exception(exc_type, exc_value, exc_tb, context_label):
    try:
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        msg = "[Uncaught {0}] {1}: {2}\n{3}".format(
            context_label,
            getattr(exc_type, "__name__", "Error"),
            exc_value,
            tb_str,
        )
        osdoc_mod = sys.modules.get("osdoc")
        if osdoc_mod is not None and hasattr(osdoc_mod, "log_error"):
            osdoc_mod.log_error(msg)
        elif sys.__stderr__ is not None:
            sys.__stderr__.write(msg + "\n")
            sys.__stderr__.flush()
    except Exception:
        pass


_HOOKS_INSTALLED = False


def install_runtime_crash_hooks(src_dir=None, app_data_dir=None, allow_dev=False):
    """Idempotently install sys.excepthook and threading.excepthook for runtime crashes."""
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return False

    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    orig_sys_hook = sys.excepthook

    def _bw_sys_excepthook(exc_type, exc_value, exc_tb):
        try:
            if not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
                _log_uncaught_exception(exc_type, exc_value, exc_tb, "Main thread")
                send_runtime_crash_async(
                    exc_type,
                    exc_value,
                    exc_tb,
                    context_label="Main thread",
                    src_dir=base,
                    app_data_dir=app_data_dir,
                    allow_dev=allow_dev,
                )
        except Exception:
            pass
        if orig_sys_hook:
            orig_sys_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _bw_sys_excepthook

    if hasattr(threading, "excepthook"):
        orig_th_hook = threading.excepthook

        def _bw_threading_excepthook(args):
            try:
                exc_type = getattr(args, "exc_type", None)
                exc_value = getattr(args, "exc_value", None)
                exc_tb = getattr(args, "exc_traceback", None)
                th = getattr(args, "thread", None)
                th_name = getattr(th, "name", "Background thread") if th else "Background thread"
                if exc_type is not None and not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
                    _log_uncaught_exception(exc_type, exc_value, exc_tb, th_name)
                    send_runtime_crash_async(
                        exc_type,
                        exc_value,
                        exc_tb,
                        context_label=th_name,
                        src_dir=base,
                        app_data_dir=app_data_dir,
                        allow_dev=allow_dev,
                    )
            except Exception:
                pass
            if orig_th_hook:
                orig_th_hook(args)

        threading.excepthook = _bw_threading_excepthook

    _HOOKS_INSTALLED = True
    return True
