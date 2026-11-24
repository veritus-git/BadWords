#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/boot_splash.py
ROLE: Instant Startup Splash Screen
DESCRIPTION:
Lightweight frameless splash window displayed immediately on startup while
heavy backend modules (osdoc, api, engine, gui.main_window) initialize.
Must NEVER import gui.main_window, gui.components.*, or gui.dialogs.*.
"""

import os
import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget

import config
from gui.utils import _app_icon, _center_on_screen, _txt, get_layout_dir, get_layout_icon_path


def find_splash_path():
    """Find splashscreen.png in assets/layout across development and installed environments."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        get_layout_icon_path("splashscreen.png"),
        os.path.join(get_layout_dir(), "splashscreen.png"),
        # Dev repo layout: <repo_root>/assets/layout/splashscreen.png
        os.path.abspath(os.path.join(here, "..", "..", "assets", "layout", "splashscreen.png")),
        # Production install layout: <install_dir>/assets/layout/splashscreen.png
        os.path.abspath(os.path.join(here, "..", "assets", "layout", "splashscreen.png")),
        # Legacy unpacked fallback
        os.path.abspath(os.path.join(here, "..", "layout", "splashscreen.png")),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


class SplashInnerFrame(QFrame):
    """Inner container frame that paints the splash image directly with high-quality antialiased scaling."""

    def __init__(self, splash_path, w, h, parent=None):
        super().__init__(parent)
        self.setObjectName("MainInnerFrame")
        self.setFixedSize(w, h)
        self.setAttribute(Qt.WA_StyledBackground, False)

        if splash_path and os.path.isfile(splash_path):
            orig_img = QImage(splash_path)
            dpr = self.devicePixelRatioF()
            scaled_img = orig_img.scaled(
                int(w * dpr),
                int(h * dpr),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            self._pix = QPixmap.fromImage(scaled_img)
            self._pix.setDevicePixelRatio(dpr)
        else:
            self._pix = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._pix and not self._pix.isNull():
            p.drawPixmap(0, 0, self._pix)
        else:
            p.fillRect(self.rect(), QColor("#121212"))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#2e2e2e"), 1))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)


class BootSplash(QWidget):
    """Frameless dark loading window displayed immediately on boot before heavy imports."""

    def txt(self, key, **kwargs):
        return _txt("en", key, **kwargs)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Window
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        w, h = config.S(345), config.S(194)
        self.setFixedSize(w, h)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splash_file = find_splash_path()
        self.inner_frame = SplashInnerFrame(splash_file, w, h, self)
        main_layout.addWidget(self.inner_frame)

        content_layout = QVBoxLayout(self.inner_frame)
        content_layout.setContentsMargins(0, 0, 0, config.S(40))
        content_layout.addStretch()

        self._lbl_loading = QLabel(self.txt("lbl_loading").upper(), self.inner_frame)
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        self._lbl_loading.setStyleSheet(
            """
            QLabel {{
                color: #a0a0a0;
                font-family: "{font}", "Ubuntu", sans-serif;
                font-size: {size}px;
                font-weight: 500;
                letter-spacing: {lsp}px;
                background: transparent;
            }}
            """.format(font=config.UI_FONT_NAME, size=config.FS_PX(7.5), lsp=max(1, config.S(1.5)))
        )
        content_layout.addWidget(self._lbl_loading)

        self.setStyleSheet("QWidget#BootSplashRoot { background-color: #121212; }")
        self.setObjectName("BootSplashRoot")

        self.setWindowIcon(_app_icon())
        _center_on_screen(self, w, h)

        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(300)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                import ctypes
                from ctypes import wintypes
                hwnd = int(self.winId())
                if hwnd:
                    dwmapi = ctypes.windll.dwmapi
                    dwmapi.DwmSetWindowAttribute.argtypes = [
                        wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD
                    ]
                    dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.c_void_p]
                    nc_policy = ctypes.c_int(2)
                    dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(nc_policy), 4)
                    corner_pref = ctypes.c_int(1)
                    dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), 4)
                    border_color = ctypes.c_uint(0xFFFFFFFE)
                    dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), 4)

                    class MARGINS(ctypes.Structure):
                        _fields_ = [
                            ("left", ctypes.c_int),
                            ("right", ctypes.c_int),
                            ("top", ctypes.c_int),
                            ("bottom", ctypes.c_int),
                        ]
                    m = MARGINS(0, 0, 0, 1)
                    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))
            except Exception:
                pass

    def _animate(self):
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText("LOADING{0}".format(dots))
        self._dot_count += 1

    def set_status(self, text):
        self._timer.stop()
        self._lbl_loading.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
