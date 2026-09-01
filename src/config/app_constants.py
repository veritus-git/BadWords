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

# Reference resolution: Full HD 1920x1080 (16:9)
CFG_WINDOW_W_BASE = 400
CFG_WINDOW_H_BASE = 740
SETTINGS_WINDOW_W = 750
SETTINGS_WINDOW_H = 580
SIDEBAR_WIDTH = 50

def get_responsive_window_size(screen=None):
    """
    Computes optimal window dimensions relative to the available screen workspace,
    calibrated against a 1920x1080 Full HD baseline with safe clamping bounds.
    """
    try:
        from PySide6.QtGui import QGuiApplication
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            sw, sh = avail.width(), avail.height()
            # Proportional height (calibrated to ~68.5% of workspace)
            target_h = int(sh * 0.685)
            if IS_MAC:
                target_h -= 28  # Compensate for macOS system title bar
            # Proportional width based on vertical screen proportion
            height_scale = max(0.6, min(sh / 1080.0, 1.8))
            target_w = int(400 * height_scale)

            w = max(340, min(target_w, 500))
            h = max(420, min(target_h, 920))
            return w, h
    except Exception:
        pass
    return (360, 640) if IS_MAC else (400, 740)

def get_responsive_settings_size(screen=None):
    """
    Computes optimal settings dialog dimensions relative to the available screen workspace.
    """
    try:
        from PySide6.QtGui import QGuiApplication
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            sw, sh = avail.width(), avail.height()
            height_scale = max(0.6, min(sh / 1080.0, 1.8))
            target_w = int(750 * height_scale)
            target_h = int(580 * height_scale)
            if IS_MAC:
                target_h -= 28

            w = max(620, min(target_w, 850))
            h = max(460, min(target_h, 680))
            return w, h
    except Exception:
        pass
    return (650, 500) if IS_MAC else (750, 580)

def get_system_font_name():
    """
    Returns the unified application font family:
    Ubuntu Sans across all platforms (macOS, Windows, Linux).
    """
    return "Ubuntu Sans"

UI_FONT_NAME = get_system_font_name()
BASE_FONT_PT = 10

def FS(size):
    """Returns normalized font sizes across all desktop platforms."""
    return size

# ==========================================
# ANALYSIS PARAMETERS
