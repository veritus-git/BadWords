#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: app_constants.py
ROLE: Configuration
DESCRIPTION:
Global constants used throughout the application.
"""

import platform

# ==========================================
# APPLICATION INFO
# ==========================================
APP_NAME = "BadWords"
_DEFAULT_VERSION = "4.0.2"

def _detect_version() -> str:
    # 1. Stamped version file (created by installer, updater, or CI build)
    try:
        import os
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        for cand in [
            os.path.join(cur_dir, "..", "..", ".version"),
            os.path.join(cur_dir, "..", ".version"),
            os.path.join(cur_dir, ".version"),
        ]:
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    v = f.read().strip().lstrip('vV')
                    if v:
                        return v
    except Exception:
        pass

    # 2. Dynamic Git tag detection when running inside repository
    try:
        import subprocess, os
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        git_dir = os.path.join(cur_dir, "..", "..", ".git")
        if os.path.exists(git_dir):
            repo_root = os.path.dirname(git_dir)
            import re
            for cmd in (
                ["git", "describe", "--tags", "--exact-match"],
                ["git", "describe", "--tags", "--abbrev=0"],
                ["git", "describe", "--tags"],
            ):
                try:
                    raw = subprocess.check_output(
                        cmd,
                        cwd=repo_root,
                        stderr=subprocess.DEVNULL,
                        timeout=1.5
                    )
                    out = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
                    out = out.strip()
                    if out:
                        cleaned = re.sub(r'-\d+-g[0-9a-fA-F]+$', '', out)
                        return cleaned.lstrip("vV")
                except Exception:
                    pass
    except Exception:
        pass

    return _DEFAULT_VERSION

VERSION = _detect_version()
SUPPORT_WEBHOOK_URL = "http://frog02.mikr.us:41385/"
POSTHOG_API_KEY = "phc_mNTg2LuyNaVX8AG7vW63JZKCXr2PLVGGHHT7jNv3BdKR"
POSTHOG_HOST = "https://eu.i.posthog.com"

# ==========================================
# WINDOW & GUI SETTINGS
# ==========================================
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# Global Scale Factor (defaults: 0.85 on macOS, 1.0 on standard 1080p/4K Windows/Linux)
SCALE_FACTOR = 0.85 if IS_MAC else 1.0
UI_SCALE_PERCENT = 100

def set_ui_scale(pct: int | float):
    """
    Sets global UI scaling factor from a percentage (75% to 150%) and recomputes layout tokens.
    """
    global SCALE_FACTOR, UI_SCALE_PERCENT, CFG_WINDOW_W_BASE, CFG_WINDOW_H_BASE, SETTINGS_WINDOW_W, SETTINGS_WINDOW_H
    global SIDEBAR_WIDTH, BTN_HEIGHT, INPUT_HEIGHT
    global FONT_XS, FONT_SM, FONT_BASE, FONT_MD, FONT_LG, FONT_XL, FONT_TITLE, FONT_DISPLAY

    clamped_pct = max(75, min(150, int(round(float(pct)))))
    UI_SCALE_PERCENT = clamped_pct
    factor = float(clamped_pct) / 100.0
    if IS_MAC:
        factor *= 0.85
    SCALE_FACTOR = factor

    CFG_WINDOW_W_BASE = S(400)
    CFG_WINDOW_H_BASE = S(740)
    SETTINGS_WINDOW_W = S(750)
    SETTINGS_WINDOW_H = S(580)
    SIDEBAR_WIDTH = S(50)
    BTN_HEIGHT = S(32)
    INPUT_HEIGHT = S(30)

    FONT_XS = FS(8)
    FONT_SM = FS(9)
    FONT_BASE = FS(10)
    FONT_MD = FS(11)
    FONT_LG = FS(13)
    FONT_XL = FS(15)
    FONT_TITLE = FS(18)
    FONT_DISPLAY = FS(36)

    import sys
    for mod_name in ('config', 'src.config', 'config.app_constants', 'src.config.app_constants', __name__):
        mod = sys.modules.get(mod_name)
        if mod:
            setattr(mod, 'SCALE_FACTOR', SCALE_FACTOR)
            setattr(mod, 'UI_SCALE_PERCENT', UI_SCALE_PERCENT)
            setattr(mod, 'CFG_WINDOW_W_BASE', CFG_WINDOW_W_BASE)
            setattr(mod, 'CFG_WINDOW_H_BASE', CFG_WINDOW_H_BASE)
            setattr(mod, 'SETTINGS_WINDOW_W', SETTINGS_WINDOW_W)
            setattr(mod, 'SETTINGS_WINDOW_H', SETTINGS_WINDOW_H)
            setattr(mod, 'SIDEBAR_WIDTH', SIDEBAR_WIDTH)
            setattr(mod, 'BTN_HEIGHT', BTN_HEIGHT)
            setattr(mod, 'INPUT_HEIGHT', INPUT_HEIGHT)
            setattr(mod, 'FONT_XS', FONT_XS)
            setattr(mod, 'FONT_SM', FONT_SM)
            setattr(mod, 'FONT_BASE', FONT_BASE)
            setattr(mod, 'FONT_MD', FONT_MD)
            setattr(mod, 'FONT_LG', FONT_LG)
            setattr(mod, 'FONT_XL', FONT_XL)
            setattr(mod, 'FONT_TITLE', FONT_TITLE)
            setattr(mod, 'FONT_DISPLAY', FONT_DISPLAY)

def init_ui_scaling(app=None, scale_pct=None):
    """
    Initializes or dynamically adjusts SCALE_FACTOR based on the primary screen's available height
    or a user-defined scaling percentage (75% to 150%).
    Ensures optimal proportions on macOS Retina, laptops (768p/900p), 1080p, and 4K displays.
    """
    if scale_pct is not None:
        set_ui_scale(scale_pct)
        return

    global SCALE_FACTOR, CFG_WINDOW_W_BASE, CFG_WINDOW_H_BASE, SETTINGS_WINDOW_W, SETTINGS_WINDOW_H
    global SIDEBAR_WIDTH, BTN_HEIGHT, INPUT_HEIGHT
    global FONT_XS, FONT_SM, FONT_BASE, FONT_MD, FONT_LG, FONT_XL, FONT_TITLE, FONT_DISPLAY
    try:
        from PySide6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen()
        if platform.system() == "Darwin":
            # On macOS Retina/MacBook screens, 0.85 gives compact, balanced layout
            SCALE_FACTOR = 0.85
        elif screen:
            avail_geo = screen.availableGeometry()
            avail_h = avail_geo.height()
            if avail_h < 850:
                # Small laptop screens (e.g. 1366x768 or 1080p at 150% scaling where available height is ~720)
                SCALE_FACTOR = 0.85
            elif avail_h < 1000:
                # Mid-sized screens (e.g. 1600x900 or 1080p at 125% scaling)
                SCALE_FACTOR = 0.90
            else:
                # Full HD 1080p (100%), 1440p, 4K (200%)
                SCALE_FACTOR = 1.0
        else:
            SCALE_FACTOR = 0.85 if platform.system() == "Darwin" else 1.0
    except Exception:
        SCALE_FACTOR = 0.85 if platform.system() == "Darwin" else 1.0

    CFG_WINDOW_W_BASE = S(400)
    CFG_WINDOW_H_BASE = S(740)
    SETTINGS_WINDOW_W = S(750)
    SETTINGS_WINDOW_H = S(580)
    SIDEBAR_WIDTH = S(50)
    BTN_HEIGHT = S(32)
    INPUT_HEIGHT = S(30)

    FONT_XS = FS(8)
    FONT_SM = FS(9)
    FONT_BASE = FS(10)
    FONT_MD = FS(11)
    FONT_LG = FS(13)
    FONT_XL = FS(15)
    FONT_TITLE = FS(18)
    FONT_DISPLAY = FS(36)

    import sys
    for mod_name in ('config', 'src.config', 'config.app_constants', 'src.config.app_constants', __name__):
        mod = sys.modules.get(mod_name)
        if mod:
            setattr(mod, 'SCALE_FACTOR', SCALE_FACTOR)
            setattr(mod, 'UI_SCALE_PERCENT', UI_SCALE_PERCENT)
            setattr(mod, 'CFG_WINDOW_W_BASE', CFG_WINDOW_W_BASE)
            setattr(mod, 'CFG_WINDOW_H_BASE', CFG_WINDOW_H_BASE)
            setattr(mod, 'SETTINGS_WINDOW_W', SETTINGS_WINDOW_W)
            setattr(mod, 'SETTINGS_WINDOW_H', SETTINGS_WINDOW_H)
            setattr(mod, 'SIDEBAR_WIDTH', SIDEBAR_WIDTH)
            setattr(mod, 'BTN_HEIGHT', BTN_HEIGHT)
            setattr(mod, 'INPUT_HEIGHT', INPUT_HEIGHT)
            setattr(mod, 'FONT_XS', FONT_XS)
            setattr(mod, 'FONT_SM', FONT_SM)
            setattr(mod, 'FONT_BASE', FONT_BASE)
            setattr(mod, 'FONT_MD', FONT_MD)
            setattr(mod, 'FONT_LG', FONT_LG)
            setattr(mod, 'FONT_XL', FONT_XL)
            setattr(mod, 'FONT_TITLE', FONT_TITLE)
            setattr(mod, 'FONT_DISPLAY', FONT_DISPLAY)

def S(px: int | float) -> int:
    """Scales pixel dimensions (widths, heights, margins, paddings, icon sizes, radiuses)."""
    return max(1, int(round(px * SCALE_FACTOR)))

def FS(pt: int | float) -> int:
    """Scales font point sizes smoothly (+1pt on macOS for enhanced legibility, standard on Windows/Linux)."""
    if IS_MAC:
        return int(pt) + 1
    return max(8, int(round(pt * SCALE_FACTOR)))

def SP(pt: int | float) -> int:
    """Alias for font scaling."""
    return FS(pt)

# Base dimensions scaled uniformly
CFG_WINDOW_W_BASE = S(400)
CFG_WINDOW_H_BASE = S(740)
SETTINGS_WINDOW_W = S(750)
SETTINGS_WINDOW_H = S(580)
SIDEBAR_WIDTH = S(50)
BTN_HEIGHT = S(32)
INPUT_HEIGHT = S(30)

# Fonts
UI_FONT_NAME = "Ubuntu Sans"
TITLE_FONT_NAME = "Ubuntu"
BASE_FONT_PT = 10

# Scaled typography tokens
FONT_XS = FS(8)
FONT_SM = FS(9)
FONT_BASE = FS(10)
FONT_MD = FS(11)
FONT_LG = FS(13)
FONT_XL = FS(15)
FONT_TITLE = FS(18)
FONT_DISPLAY = FS(36)

def get_system_font_name():
    """Returns the unified application font family."""
    return UI_FONT_NAME

# ==========================================
# ANALYSIS PARAMETERS
# ==========================================
