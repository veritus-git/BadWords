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

# Base dimensions tailored per OS for ideal screen proportions
CFG_WINDOW_W_BASE = 340 if IS_MAC else 400
CFG_WINDOW_H_BASE = 620 if IS_MAC else 740
SETTINGS_WINDOW_W = 640 if IS_MAC else 750
SETTINGS_WINDOW_H = 490 if IS_MAC else 580
SIDEBAR_WIDTH = 46 if IS_MAC else 54
BTN_HEIGHT = 28 if IS_MAC else 34
INPUT_HEIGHT = 28 if IS_MAC else 32

def get_system_font_name():
    """
    Returns the preferred font family depending on the OS:
    macOS uses native 'Helvetica Neue'.
    Windows & Linux use 'Ubuntu Sans' (modern Canonical font with native Medium 500 / SemiBold 600).
    """
    if IS_MAC:
        return "Helvetica Neue"
    return "Ubuntu Sans"

UI_FONT_NAME = get_system_font_name()
BASE_FONT_PT = 10

def FS(size):
    """Returns normalized font sizes across all desktop platforms."""
    return size

# ==========================================
# ANALYSIS PARAMETERS
