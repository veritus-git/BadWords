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

# Scale factor: 1.0 on standard 1080p/4K Windows/Linux, 0.82 on macOS Retina laptop displays
SCALE_FACTOR = 0.82 if IS_MAC else 1.0

def S(val: int | float) -> int:
    """Scales pixel dimension by SCALE_FACTOR and returns an integer."""
    return max(1, int(round(val * SCALE_FACTOR)))

def SP(val: int | float) -> int:
    """Scales font point size by SCALE_FACTOR and returns an integer."""
    return max(6, int(round(val * SCALE_FACTOR)))

# Base dimensions tailored per OS using token scaling
CFG_WINDOW_W_BASE = S(400)
CFG_WINDOW_H_BASE = S(740) - (28 if IS_MAC else 0)
SETTINGS_WINDOW_W = S(750)
SETTINGS_WINDOW_H = S(580) - (28 if IS_MAC else 0)
SIDEBAR_WIDTH = S(50)
BTN_HEIGHT = S(32)
INPUT_HEIGHT = S(30)

# Fonts
UI_FONT_NAME = "Ubuntu Sans"
TITLE_FONT_NAME = "Ubuntu"
BASE_FONT_PT = SP(10)

def get_system_font_name():
    """Returns the unified application font family."""
    return UI_FONT_NAME

def FS(size):
    """Returns normalized font sizes across all desktop platforms."""
    return SP(size)

# ==========================================
# ANALYSIS PARAMETERS
