#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: utils.py
ROLE: Core Module
DESCRIPTION:
Helper utilities for GUI (e.g., time formatting, icon loading).
"""

import os
import platform
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QIcon
import config

def get_icon_path(icon_name: str = "default") -> str:
    """Returns absolute path to an app icon (.ico on Windows, .png on Unix), checking all possible prod/dev locations."""
    try:
        install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        is_win = platform.system() == "Windows"
        ext = ".ico" if is_win else ".png"

        candidates = [
            os.path.join(install_dir, "icons", f"icon_{icon_name}{ext}"),
            os.path.join(install_dir, "assets", "icons", f"icon_{icon_name}{ext}"),
            os.path.join(os.path.dirname(install_dir), "assets", "icons", f"icon_{icon_name}{ext}"),
        ]

        if is_win:
            candidates.extend([
                os.path.join(install_dir, "icons", f"icon_{icon_name}.png"),
                os.path.join(install_dir, "assets", "icons", f"icon_{icon_name}.png"),
                os.path.join(os.path.dirname(install_dir), "assets", "icons", f"icon_{icon_name}.png"),
            ])

        for p in candidates:
            if os.path.isfile(p):
                return p

        if icon_name != "default":
            return get_icon_path("default")
    except Exception:
        pass
    return ""


def get_layout_dir() -> str:
    """Returns absolute path to layout icons folder, supporting both flat install, nested assets, and dev layout."""
    src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    prod_layout = os.path.join(src_dir, "layout")
    if os.path.isdir(prod_layout):
        return prod_layout
    prod_nested = os.path.join(src_dir, "assets", "layout")
    if os.path.isdir(prod_nested):
        return prod_nested
    dev_layout = os.path.join(os.path.dirname(src_dir), "assets", "layout")
    if os.path.isdir(dev_layout):
        return dev_layout
    return prod_layout


def get_layout_icon_path(icon_name: str) -> str:
    """Returns path to a specific layout image asset."""
    layout_dir = get_layout_dir()
    return os.path.join(layout_dir, icon_name)


def _app_icon() -> QIcon:
    try:
        import json
        install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        icon_name = "default"
        settings_file = os.path.join(install_dir, "settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                icon_name = data.get('app_icon', 'default')

        icon_path = get_icon_path(icon_name)
        if icon_path and os.path.exists(icon_path):
            return QIcon(icon_path)
    except Exception:
        pass
    return QIcon()


def apply_dark_title_bar(window: QWidget):
    """Forces the native Windows title bar to dark mode."""
    if platform.system() == "Windows":
        try:
            import ctypes
            # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE in Windows 10/11
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

def _center_on_screen(widget: QWidget, w: int, h: int):
    """Center *widget* on the primary screen (or active monitor if detectable)."""
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width()  - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        widget.setGeometry(x, y, w, h)


def _txt(lang: str, key: str, **kwargs) -> str:
    """Return translation string for *key* in *lang*, falling back to 'en'."""
    text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def _qwidget_txt(self, key: str, **kwargs) -> str:
    w = self.window()
    if hasattr(w, 'txt') and w != self:
        return w.txt(key, **kwargs)
    return _txt("en", key, **kwargs)

QWidget.txt = _qwidget_txt
