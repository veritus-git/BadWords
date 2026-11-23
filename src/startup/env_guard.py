#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/env_guard.py
ROLE: Startup Environment Guard
DESCRIPTION:
Validates Python version compatibility, strips foreign Python/Conda site-packages
paths from sys.path, locates the isolated BadWords venv interpreter, and checks
required packages without importing heavy modules.
"""

import importlib.util
import os
import re
import sys

from startup import SUPPORTED_MAX_EXCL, SUPPORTED_MIN

HARD_REQUIRED = ("PySide6", "numpy")
SOFT_REQUIRED = ("faster_whisper", "av", "pypdf")
PIP_NAMES = {
    "PySide6": "PySide6",
    "numpy": "numpy",
    "faster_whisper": "faster-whisper",
    "av": "av<19",
    "pypdf": "pypdf",
}

_POSIX_VER_RE = re.compile(r"python(\d+)\.(\d+)", re.IGNORECASE)
_WIN_VER_RE = re.compile(r"[Pp]ython(\d)(\d{1,2})(?:[\\/]|$)")


def check_python_version(version_info=None):
    """Return True if Python major.minor is within [3.10, 3.13)."""
    vi = version_info if version_info is not None else sys.version_info
    try:
        pair = (int(vi[0]), int(vi[1]))
    except Exception:
        return False
    return SUPPORTED_MIN <= pair < SUPPORTED_MAX_EXCL


def _extract_path_py_version(entry):
    if not isinstance(entry, str) or not entry:
        return None
    m = _POSIX_VER_RE.search(entry)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    m = _WIN_VER_RE.search(entry)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    return None


def prune_mismatched_version_paths(paths=None, current=None):
    """Remove sys.path entries tagged with a different Python major.minor version."""
    target = sys.path if paths is None else paths
    cur = current if current is not None else sys.version_info[:2]
    cur_pair = (int(cur[0]), int(cur[1]))

    kept = []
    removed = []
    for entry in list(target):
        ver = _extract_path_py_version(entry)
        if ver is not None and ver != cur_pair:
            removed.append(entry)
        else:
            kept.append(entry)

    target[:] = kept
    return removed


def find_venv_python(src_dir):
    """Return the path to BadWords' own venv Python executable, or None.

    Never returns a system/global Python interpreter.
    """
    abs_src = os.path.abspath(src_dir)
    parent_dir = os.path.dirname(abs_src)

    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    if sys.prefix != base_prefix and sys.executable:
        abs_prefix = os.path.abspath(sys.prefix)
        for root in (abs_src, parent_dir):
            try:
                if os.path.commonpath([abs_prefix, root]) == root and os.path.isfile(sys.executable):
                    return sys.executable
            except ValueError:
                pass

    is_win = (sys.platform == "win32" or os.name == "nt")
    candidates = []
    for root in (abs_src, parent_dir):
        if is_win:
            candidates.append(os.path.join(root, "venv", "Scripts", "python.exe"))
        else:
            candidates.append(os.path.join(root, "venv", "bin", "python3"))
            candidates.append(os.path.join(root, "venv", "bin", "python"))

    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    return None


def missing_packages(names):
    """Check package availability via find_spec without importing heavy modules."""
    missing = []
    for name in names:
        try:
            spec = importlib.util.find_spec(name)
        except Exception:
            spec = None
        if spec is None:
            missing.append(name)
    return missing
