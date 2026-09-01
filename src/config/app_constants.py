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

# Global Scale Factor (1.0 on standard 1080p/4K Windows/Linux, 0.82 on macOS)
SCALE_FACTOR = 0.82 if IS_MAC else 1.0

def S(px: int | float) -> int:
    """Scales pixel dimensions (widths, heights, margins, paddings, radiuses)."""
    return max(1, int(round(px * SCALE_FACTOR)))

def FS(pt: int | float) -> int:
    """Scales font point sizes."""
    return max(6, int(round(pt * SCALE_FACTOR)))

def SP(pt: int | float) -> int:
    """Alias for font scaling."""
    return FS(pt)

# Base dimensions scaled uniformly
CFG_WINDOW_W_BASE = S(400)
CFG_WINDOW_H_BASE = S(740)
SETTINGS_WINDOW_W = S(750)
SETTINGS_WINDOW_H = S(580)
SIDEBAR_WIDTH = S(54)
BTN_HEIGHT = S(34)
INPUT_HEIGHT = S(32)

# Fonts
UI_FONT_NAME = "Ubuntu Sans"
TITLE_FONT_NAME = "Ubuntu"
BASE_FONT_PT = FS(10)

def get_system_font_name():
    """Returns the unified application font family."""
    return UI_FONT_NAME

# ==========================================
# ANALYSIS PARAMETERS
