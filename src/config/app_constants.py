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
# Base dimensions for 100% DPI (96 PPI)
CFG_WINDOW_W_BASE = 400
CFG_WINDOW_H_BASE = 740

def get_system_font_name():
    """
    Returns preferred font depending on the operating system.
    Does not require GUI library (tkinter).
    """
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    if system == "Darwin": # macOS
        return "Helvetica Neue"
    # Linux / Fallback
    return "Noto Sans"

UI_FONT_NAME = get_system_font_name()
BASE_FONT_PT = 12 if platform.system() == "Darwin" else 10

def FS(size):
    """Dynamically scales font sizes based on OS."""
    return size + 2 if platform.system() == "Darwin" else size

# ==========================================
# ANALYSIS PARAMETERS
