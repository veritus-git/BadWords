#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: Core Module
DESCRIPTION:
Python package initialization file.
"""

from .main_window import BadWordsGUI
from .components.dialogs import SplashScreen
from .utils import _app_icon, init_embedded_fonts, get_play_icon, get_svg_icon, setup_macos_standalone_identity, set_macos_runtime_icon
from .vsync import init_high_refresh_sync, get_refresh_interval_ms, track_window_screen

