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
_DEFAULT_VERSION = "4.1.2"

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

UI_SCALE_MIN = 75
UI_SCALE_MAX = 200
UI_SCALE_STEP = 5

# Global Scale State
SCALE_FACTOR = 1.0
UI_SCALE_MODE = "auto"
UI_SCALE_PERCENT = 100
OS_SCALE_PERCENT = 100
QT_BASE_SCALE_PERCENT = 100

_SYNC_TOKEN_NAMES = (
    'SCALE_FACTOR',
    'UI_SCALE_MODE',
    'UI_SCALE_PERCENT',
    'OS_SCALE_PERCENT',
    'QT_BASE_SCALE_PERCENT',
    'UI_SCALE_MIN',
    'UI_SCALE_MAX',
    'UI_SCALE_STEP',
    'CFG_WINDOW_W_BASE',
    'CFG_WINDOW_H_BASE',
    'SETTINGS_WINDOW_W',
    'SETTINGS_WINDOW_H',
    'SIDEBAR_WIDTH',
    'BTN_HEIGHT',
    'INPUT_HEIGHT',
    'FONT_XS',
    'FONT_SM',
    'FONT_BASE',
    'FONT_MD',
    'FONT_LG',
    'FONT_XL',
    'FONT_TITLE',
    'FONT_DISPLAY',
)


def _get_active_screen(screen=None):
    """Returns explicit screen or QGuiApplication.primaryScreen() when Qt GUI is available."""
    if screen is not None:
        return screen
    try:
        from PySide6.QtGui import QGuiApplication
        return QGuiApplication.primaryScreen()
    except Exception:
        return None


def detect_os_scale_pct(screen=None) -> int:
    """
    Returns OS display scaling percentage for the given screen:
    - macOS: logical Cocoa points represent native 100% baseline (Retina dpr=2.0 is backing density).
    - Windows / Linux Wayland: devicePixelRatio() carries fractional/integer OS scale (125%, 150%, 200%).
    - Linux X11 (dpr=1.0 with Xft.dpi): logicalDotsPerInch() / 96.0 carries display scale.
    """
    if IS_MAC:
        return 100
    scr = _get_active_screen(screen)
    if scr is None:
        return 100
    try:
        dpr = float(scr.devicePixelRatio() or 1.0)
    except Exception:
        dpr = 1.0
    if abs(dpr - 1.0) > 0.02:
        return max(50, min(400, int(round(dpr * 100.0))))
    try:
        ldpi = float(scr.logicalDotsPerInch() or 96.0)
    except Exception:
        ldpi = 96.0
    if abs(ldpi - 96.0) > 2.0:
        return max(50, min(400, int(round((ldpi / 96.0) * 100.0))))
    return 100


def get_qt_base_scale_pct(screen=None) -> int:
    """
    Returns Qt's automatic DIP-to-physical scale percentage so BadWords never double-multiplies OS scaling.
    On macOS, CSS px and QFont pixelSize operate in logical points (base 100%).
    On Windows/Linux, Qt PassThrough multiplies DIPs by devicePixelRatio().
    """
    if IS_MAC:
        return 100
    scr = _get_active_screen(screen)
    if scr is None:
        return 100
    try:
        dpr = float(scr.devicePixelRatio() or 1.0)
    except Exception:
        dpr = 1.0
    return max(50, min(400, int(round(dpr * 100.0))))


def _recompute_and_sync_tokens():
    """Recomputes layout & typography tokens from SCALE_FACTOR and propagates across config aliases."""
    global CFG_WINDOW_W_BASE, CFG_WINDOW_H_BASE, SETTINGS_WINDOW_W, SETTINGS_WINDOW_H
    global SIDEBAR_WIDTH, BTN_HEIGHT, INPUT_HEIGHT
    global FONT_XS, FONT_SM, FONT_BASE, FONT_MD, FONT_LG, FONT_XL, FONT_TITLE, FONT_DISPLAY

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
    g = globals()
    for mod_name in ('config', 'src.config', 'config.app_constants', 'src.config.app_constants', __name__):
        mod = sys.modules.get(mod_name)
        if mod:
            for attr in _SYNC_TOKEN_NAMES:
                setattr(mod, attr, g[attr])


def apply_ui_scaling(mode: str = "auto", pct: int | float | None = None, screen=None) -> float:
    """
    Computes unified SCALE_FACTOR cleanly without double-multiplying native OS DPI scaling.
    In 'auto' mode, BadWords matches native OS display scaling 1:1 (target == OS_SCALE_PERCENT).
    In 'manual' mode, BadWords targets pct% (75%-200%) relative to 100% physical baseline,
    dividing out Qt's automatic devicePixelRatio() so moving across mixed-DPI monitors keeps true target size.
    # INVARIANT: SCALE_FACTOR = target_pct / qt_base_pct prevents double OS+app scaling on Win11, Wayland, X11, and macOS.
    """
    global SCALE_FACTOR, UI_SCALE_MODE, UI_SCALE_PERCENT, OS_SCALE_PERCENT, QT_BASE_SCALE_PERCENT

    scr = _get_active_screen(screen)
    OS_SCALE_PERCENT = detect_os_scale_pct(scr)
    QT_BASE_SCALE_PERCENT = get_qt_base_scale_pct(scr)

    norm_mode = "manual" if str(mode or "auto").strip().lower() == "manual" else "auto"
    if norm_mode == "auto":
        target_pct = max(50, min(400, int(OS_SCALE_PERCENT)))
    else:
        raw_pct = OS_SCALE_PERCENT if pct is None else int(round(float(pct)))
        target_pct = max(UI_SCALE_MIN, min(UI_SCALE_MAX, raw_pct))

    UI_SCALE_MODE = norm_mode
    UI_SCALE_PERCENT = target_pct
    SCALE_FACTOR = float(target_pct) / float(max(50, QT_BASE_SCALE_PERCENT))
    _recompute_and_sync_tokens()
    return SCALE_FACTOR


def set_ui_scale(pct: int | float, screen=None):
    """Sets manual UI scaling factor from a percentage (75% to 200%) and recomputes layout tokens."""
    return apply_ui_scaling(mode="manual", pct=pct, screen=screen)


def init_ui_scaling(app=None, scale_pct=None, scale_mode=None, screen=None):
    """
    Initializes global SCALE_FACTOR from the active screen and saved scaling preference ('auto' or 'manual').
    Defaults to 'auto' (native OS display scaling) unless manual scale_pct / scale_mode='manual' is requested.
    """
    scr = screen
    if scr is None and app is not None:
        try:
            scr = app.primaryScreen()
        except Exception:
            scr = None

    if scale_mode is None:
        mode = "manual" if scale_pct is not None else "auto"
    else:
        mode = str(scale_mode).strip().lower()
    return apply_ui_scaling(mode=mode, pct=scale_pct, screen=scr)


def S(px: int | float) -> int:
    """Scales pixel dimensions (widths, heights, margins, paddings, icon sizes, radiuses)."""
    return max(1, int(round(px * SCALE_FACTOR)))


def FS_PX(pt: int | float) -> int:
    """
    Converts typographic points cleanly to scaled Qt DIP pixels (96/72 * SCALE_FACTOR).
    Eliminates 1pt quantization steps at fractional scales (125%, 150%, 175%) and
    equalizes font proportions across macOS (72 DPI), Windows (96 DPI), and Linux X11/Wayland.
    """
    return max(8, int(round(float(pt) * (96.0 / 72.0) * SCALE_FACTOR)))


def FS(pt: int | float) -> int:
    """Scales font point sizes uniformly across platforms."""
    return max(7, int(round(float(pt) * SCALE_FACTOR)))


def SP(pt: int | float) -> int:
    """Alias for pixel font scaling helper."""
    return FS_PX(pt)


def make_font(family: str | None = None, pt: int | float = 10, bold: bool = False, italic: bool = False, weight=None):
    """Creates a QFont sized in exact scaled pixels (FS_PX) with clean antialiasing and hinting."""
    from PySide6.QtGui import QFont
    f = QFont(family or UI_FONT_NAME)
    f.setPixelSize(FS_PX(pt))
    if italic:
        f.setItalic(True)
    if weight is not None:
        f.setWeight(weight)
    elif bold:
        f.setBold(True)
    f.setStyleStrategy(QFont.PreferAntialias)
    f.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return f

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
