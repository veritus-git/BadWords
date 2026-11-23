#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: Core Module
DESCRIPTION:
Python package initialization file with PEP 562 lazy attribute loading so
importing gui or lightweight helpers (e.g. gui.utils) does not eagerly load
gui.main_window before the boot splash screen is displayed.
"""

import importlib

_LAZY = {
    "BadWordsGUI": ("gui.main_window", "BadWordsGUI"),
    "SplashScreen": ("gui.components.dialogs", "SplashScreen"),
    "CustomMsgBox": ("gui.components.dialogs", "CustomMsgBox"),
    "_app_icon": ("gui.utils", "_app_icon"),
    "init_embedded_fonts": ("gui.utils", "init_embedded_fonts"),
    "get_play_icon": ("gui.utils", "get_play_icon"),
    "get_svg_icon": ("gui.utils", "get_svg_icon"),
    "setup_macos_standalone_identity": ("gui.utils", "setup_macos_standalone_identity"),
    "set_macos_runtime_icon": ("gui.utils", "set_macos_runtime_icon"),
    "init_high_refresh_sync": ("gui.vsync", "init_high_refresh_sync"),
    "get_refresh_interval_ms": ("gui.vsync", "get_refresh_interval_ms"),
    "track_window_screen": ("gui.vsync", "track_window_screen"),
}

__all__ = list(_LAZY)


def __getattr__(name):
    target = _LAZY.get(name)
    if target is None:
        raise AttributeError("module 'gui' has no attribute {0!r}".format(name))
    mod_name, attr_name = target
    mod = importlib.import_module(mod_name)
    val = getattr(mod, attr_name)
    globals()[name] = val
    return val


def __dir__():
    return sorted(list(globals().keys()) + list(_LAZY.keys()))
