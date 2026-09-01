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
VERSION = "4.0.0"
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

def init_ui_scaling(app=None):
    """
    Initializes or dynamically adjusts SCALE_FACTOR based on the primary screen's available height.
    Ensures optimal proportions on macOS Retina, laptops (768p/900p), 1080p, and 4K displays.
    """
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
    """Scales font point sizes smoothly while preserving full readability."""
    if IS_MAC:
        return int(pt)
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
