#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/runtime_mode.py
ROLE: Runtime Mode Detection
DESCRIPTION:
Single source of truth for detecting whether BadWords is executing inside a
DaVinci Resolve host process or launched in Resolve-embedded mode.
"""

import os
import sys


def is_in_resolve_process():
    """Return True if currently executing inside a DaVinci Resolve / fuscript process."""
    for mod_name in ("__main__", "builtins"):
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        obj_res = getattr(mod, "resolve", None)
        if obj_res is not None:
            if type(obj_res).__name__ != "ResolveHandler" and hasattr(obj_res, "GetProjectManager"):
                return True
        obj_bmd = getattr(mod, "bmd", None)
        if obj_bmd is not None and hasattr(obj_bmd, "scriptapp"):
            return True
        for attr in ("fusion", "fu"):
            obj_fu = getattr(mod, attr, None)
            if obj_fu is not None and (hasattr(obj_fu, "GetResolve") or hasattr(obj_fu, "GetPrefs")):
                return True

    exe_lower = (sys.executable or "").lower()
    if "fscript" in exe_lower or "fuscript" in exe_lower:
        return True
    return False


def is_embedded_in_resolve():
    """Return True if BadWords was launched from inside DaVinci Resolve."""
    if os.environ.get("BADWORDS_EMBEDDED") == "1" or "--embedded" in sys.argv:
        return True
    return is_in_resolve_process()
