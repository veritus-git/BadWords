#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: splash_screen.py
ROLE: GUI Dialog
DESCRIPTION:
Splash screen loading window displayed during app initialization.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QFont

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog
from gui.utils import _app_icon, _center_on_screen, _txt


class SplashScreen(FramelessWindowMixin, _BaseDialog):
    """
    Frameless, dark loading window displayed while engine/api are initializing.
    Shows an animated "loading…" label (0-3 cycling dots at 400 ms).
    Closed by main.py once InitThread emits `loaded`.
    """

    def txt(self, key: str, **kwargs) -> str:
        return _txt("en", key, **kwargs)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        W, H = config.S(300), config.S(150)
        self.setFixedSize(W + config.S(30), H + config.S(30))
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("MainInnerFrame")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(30))
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        layout = QVBoxLayout(self.inner_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout = QVBoxLayout()
        layout.addLayout(content_layout)

        # --- QSS styling ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
            }}
            QLabel#title {{
                color: #ffffff;
                font-size: {config.SP(18)}pt;
                font-weight: bold;
                font-family: "{config.TITLE_FONT_NAME}", sans-serif;
                background: transparent;
            }}
            QLabel#loading {{
                color: {config.NOTE_COL};
                font-size: {config.SP(12)}pt;
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                background: transparent;
            }}
        """)

        # --- Layout ---
        content_layout.setContentsMargins(config.S(20), config.S(30), config.S(20), config.S(20))
        content_layout.setSpacing(config.S(8))
        content_layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel("BadWords", self.inner_frame)
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setFont(QFont(config.TITLE_FONT_NAME, config.SP(18), QFont.Weight.Bold))
        content_layout.addWidget(lbl_title)

        self._lbl_loading = QLabel(self.txt("lbl_loading"), self.inner_frame)
        self._lbl_loading.setObjectName("loading")
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self._lbl_loading)

        # --- Icon ---
        self.setWindowIcon(_app_icon())

        # --- Center on screen ---
        _center_on_screen(self, W, H)

        # --- Dot animation ---
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self):
        """Cycle the trailing dots: loading → loading. → loading.. → loading..."""
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText(f"loading{dots}")
        self._dot_count += 1

    def set_status(self, text: str):
        """Display a custom status text (stops the dot animation)."""
        self._timer.stop()
        self._lbl_loading.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
