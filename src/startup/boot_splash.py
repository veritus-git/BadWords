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
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QFrame, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget

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
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self._pix and not self._pix.isNull():
            p.drawPixmap(0, 0, self._pix)
        else:
            p.fillRect(self.rect(), QColor("#121212"))


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
            | Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        w, h = config.S(345), config.S(194)
        self.setFixedSize(w + config.S(24), h + config.S(24))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))

        splash_file = find_splash_path()
        self.inner_frame = SplashInnerFrame(splash_file, w, h, self)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(24))
        shadow.setColor(QColor(0, 0, 0, 190))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)

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
                font-size: {size}pt;
                font-weight: 500;
                letter-spacing: 1.5px;
                background: transparent;
            }}
            """.format(font=config.UI_FONT_NAME, size=config.FS(7.5))
        )
        content_layout.addWidget(self._lbl_loading)

        self.setStyleSheet("QWidget#BootSplashRoot { background-color: transparent; }")
        self.setObjectName("BootSplashRoot")

        self.setWindowIcon(_app_icon())
        _center_on_screen(self, w + config.S(24), h + config.S(24))

        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(300)

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
