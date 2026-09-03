#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: splash_screen.py
ROLE: GUI Dialog
DESCRIPTION:
Splash screen loading window displayed during app initialization.
Renders assets/layout/splashscreen.png with animated "LOADING..." indicator.
"""

import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QImage

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog
from gui.utils import _app_icon, _center_on_screen, _txt, get_layout_icon_path, get_layout_dir


def _find_splash_path() -> str:
    """Find splashscreen.png across development repository and installed environments."""
    candidates = [
        get_layout_icon_path("splashscreen.png"),
        os.path.join(get_layout_dir(), "splashscreen.png"),
        # Dev repo layout
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "layout", "splashscreen.png")),
        # Unpacked flat install layout
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "layout", "splashscreen.png")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "layout", "splashscreen.png")),
        "/mnt/dump/BadWords/assets/layout/splashscreen.png",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


class SplashInnerFrame(QFrame):
    """Inner container frame that paints the splash image directly with high-quality antialiased scaling."""
    def __init__(self, splash_path: str, W: int, H: int, parent=None):
        super().__init__(parent)
        self.setObjectName("MainInnerFrame")
        self.setFixedSize(W, H)
        self.setAttribute(Qt.WA_StyledBackground, False)

        if splash_path and os.path.isfile(splash_path):
            orig_img = QImage(splash_path)
            dpr = self.devicePixelRatioF()
            # Area-averaging smooth downscale to native physical pixels to eliminate jagged edges
            scaled_img = orig_img.scaled(int(W * dpr), int(H * dpr), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
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


class SplashScreen(FramelessWindowMixin, _BaseDialog):
    """
    Frameless, dark loading window displayed while engine/api are initializing.
    Shows animated "LOADING..." label (0-3 cycling dots at 300 ms).
    Closed by main.py once initialization completes and the main window is rendered.
    """

    def txt(self, key: str, **kwargs) -> str:
        return _txt("en", key, **kwargs)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 15% larger than original 300x150, keeping 16:9 ratio
        W, H = config.S(345), config.S(194)
        self.setFixedSize(W + config.S(24), H + config.S(24))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))

        splash_file = _find_splash_path()
        self.inner_frame = SplashInnerFrame(splash_file, W, H, self)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(24))
        shadow.setColor(QColor(0, 0, 0, 190))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)

        main_layout.addWidget(self.inner_frame)

        content_layout = QVBoxLayout(self.inner_frame)
        # Position loading higher up, closer to BadWords text
        content_layout.setContentsMargins(0, 0, 0, config.S(40))
        content_layout.addStretch()

        self._lbl_loading = QLabel(self.txt("lbl_loading").upper(), self.inner_frame)
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        self._lbl_loading.setStyleSheet(f"""
            QLabel {{
                color: #a0a0a0;
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                font-size: {config.FS(7.5)}pt;
                font-weight: 500;
                letter-spacing: 1.5px;
                background: transparent;
            }}
        """)
        content_layout.addWidget(self._lbl_loading)

        self.setStyleSheet("QDialog { background-color: transparent; }")

        # Icon & centering
        self.setWindowIcon(_app_icon())
        _center_on_screen(self, W, H)

        # Dot animation (calm rhythm: 300ms cycle)
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(300)

    def _animate(self):
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText(f"LOADING{dots}")
        self._dot_count += 1

    def set_status(self, text: str):
        self._timer.stop()
        self._lbl_loading.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
