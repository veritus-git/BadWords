#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/crash_report.py
ROLE: Early Startup Crash Reporter
DESCRIPTION:
Stdlib-only crash report packager and uploader matching the Settings -> Contact
webhook format so startup failures can be reported even when Qt/PySide6 fails.
"""

import io
import os
import platform
import re
import ssl
import sys
import tempfile
import urllib.request
import uuid
import zipfile

_MAX_LOG_BYTES = 512 * 1024


def _default_src_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def find_log_files(src_dir=None):
    """Return existing BadWords debug log file paths ordered by relevance."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    candidates = [
        os.path.join(base, "badwords_debug.log"),
        os.path.join(parent, "badwords_debug.log"),
        os.path.join(parent, ".dev_workspace", "badwords_debug.log"),
        os.path.join(tempfile.gettempdir(), "BadWords_Fallback", "badwords.log"),
    ]
    found = []
    seen = set()
    for path in candidates:
        norm = os.path.abspath(path)
        if norm not in seen and os.path.isfile(norm):
            seen.add(norm)
            found.append(norm)
    return found


def primary_log_hint(src_dir=None):
    """Return an existing log path or the expected log path for user messages."""
    existing = find_log_files(src_dir)
    if existing:
        return existing[0]
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    if os.path.isdir(os.path.join(parent, ".git")) or os.environ.get("BADWORDS_DEV") == "1":
        return os.path.join(parent, ".dev_workspace", "badwords_debug.log")
    return os.path.join(base, "badwords_debug.log")


def build_report(error_text, tb_text="", src_dir=None):
    """Return (title, body) summarizing the startup error and runtime context."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    err_str = str(error_text or "Startup error").strip()
    first_line = err_str.splitlines()[0] if err_str else "Startup error"
    title = "[Startup crash] {0}".format(first_line[:104])

    lines = [
        "Error: {0}".format(err_str),
        "",
        "Platform: {0}".format(platform.platform()),
        "Python: {0} ({1})".format(sys.version.split()[0], sys.executable),
        "sys.prefix: {0}".format(sys.prefix),
        "src_dir: {0}".format(base),
        "BADWORDS_EMBEDDED: {0}".format(os.environ.get("BADWORDS_EMBEDDED", "")),
        "argv: {0}".format(repr(sys.argv)),
        "PYTHONHOME set: {0}".format("PYTHONHOME" in os.environ),
        "CONDA_PREFIX set: {0}".format("CONDA_PREFIX" in os.environ),
        "VIRTUAL_ENV set: {0}".format("VIRTUAL_ENV" in os.environ),
        "PYTHONPATH: {0}".format(os.environ.get("PYTHONPATH", "")),
    ]
    if tb_text:
        lines.extend(["", "Traceback:", str(tb_text).strip()])

    return title, "\n".join(lines)


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


def _build_logs_zip(body_text, src_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("system_info.txt", body_text.encode("utf-8", errors="replace"))
        for idx, log_path in enumerate(find_log_files(src_dir)):
            try:
                size = os.path.getsize(log_path)
                with open(log_path, "rb") as f:
                    if size > _MAX_LOG_BYTES:
                        f.seek(size - _MAX_LOG_BYTES)
                    data = f.read()
                arc_name = os.path.basename(log_path) if idx == 0 else "{0}_{1}".format(idx, os.path.basename(log_path))
                zf.writestr(arc_name, data)
            except Exception:
                pass
    return buf.getvalue()


def send_report(error_text, tb_text="", src_dir=None, timeout=20):
    """Package startup diagnostics and POST to SUPPORT_WEBHOOK_URL. Never raises."""
    try:
        webhook_url, version = _read_app_constants(src_dir)
        if not webhook_url:
            return False

        title, body = build_report(error_text, tb_text=tb_text, src_dir=src_dir)
        raw_content = (
            "@here\n>>> **Version:** {0}\n**Email:** None\n**Title:** {1}\n\n**Body:**\n{2}"
        ).format(version, title, body)
        content_msg = raw_content[:1900]

        fields = {
            "title": title,
            "body": body,
            "email": "",
            "version": version,
            "content": content_msg,
        }
        zip_bytes = _build_logs_zip(body, src_dir)
        payload, content_type = build_multipart(fields, zip_bytes)

        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(payload)),
            "User-Agent": "BadWords/{0}".format(version),
        }

        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except Exception:
            ctx = ssl.create_default_context()

        req = urllib.request.Request(webhook_url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.getcode() in (200, 201, 202, 204)
    except Exception:
        return False
