#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: splash_screen.py
ROLE: GUI Dialog
DESCRIPTION:
Splash screen loading window displayed during app initialization.
Draws a themed card (mark, app name, tagline, accent glow, progress line) with a
"LOADING..." status; the app name comes from config.APP_NAME.
"""

from gui.theme import qc

import os
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QFrame, QLabel, QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QFont, QPixmap, QPainter, QImage

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog
from gui.utils import _app_icon, _center_on_screen, _txt, get_layout_icon_path, get_layout_dir


def _find_splash_path() -> str:
    """Find splashscreen.png in assets/layout across development and installed environments."""
    candidates = [
        get_layout_icon_path("splashscreen.png"),
        os.path.join(get_layout_dir(), "splashscreen.png"),
        # Dev repo layout: <repo_root>/assets/layout/splashscreen.png
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "assets", "layout", "splashscreen.png")),
        # Production install layout: <install_dir>/assets/layout/splashscreen.png
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "assets", "layout", "splashscreen.png")),
        # Legacy unpacked fallback
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "layout", "splashscreen.png")),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


class SplashInnerFrame(QFrame):
    """The splash card, drawn in code so it follows the colour theme: mark, name, tagline,
    a soft accent glow and an indeterminate progress line."""

    def __init__(self, splash_path: str, W: int, H: int, parent=None):
        super().__init__(parent)
        self.setObjectName("MainInnerFrame")
        self.setFixedSize(W, H)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._phase = 0.0  # progress line position, 0..1
        self._t = 0.0      # animated mark clock (s)

    def advance(self):
        self._phase = (self._phase + 0.012) % 1.0
        self._t += 0.016
        self.update()

    def paintEvent(self, event):
        from PySide6.QtCore import QRectF, QPointF
        from PySide6.QtGui import QRadialGradient, QLinearGradient, QPen, QPainterPath
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = config.S(14)
        accent = qc(config.BTN_BG)

        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.setClipPath(path)
        from gui import brand
        p.fillRect(r, QColor("#0b0b14"))
        # Brand light: cyan from the upper left, violet from the lower right
        for corner, col, alpha, reach in ((QPointF(r.left(), r.top()), brand.CYAN, 55, 0.65),
                                          (QPointF(r.right(), r.bottom()), brand.VIOLET, 95, 0.85)):
            glow = QRadialGradient(corner, r.width() * reach)
            c0 = QColor(col); c0.setAlpha(alpha)
            c1 = QColor(col); c1.setAlpha(0)
            glow.setColorAt(0.0, c0)
            glow.setColorAt(1.0, c1)
            p.fillRect(r, glow)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(r, radius, radius)

        # The mark and the wordmark (gui/brand.py)
        pad = config.S(28)
        tile = QRectF(pad, pad, config.S(52), config.S(52))
        brand.draw_mark_animated(p, tile, self._t)

        # Name and tagline
        name_px = config.S(34)
        name_rect = QRectF(pad, tile.bottom() + config.S(14), r.width() - 2 * pad, config.S(40))
        brand.draw_wordmark(p, pad, name_rect.top() + name_px * 0.92, name_px)
        tag_font = QFont(self.font())
        tag_font.setPointSizeF(config.FS(9.5))
        p.setFont(tag_font)
        p.setPen(QColor("#a1a3bd"))
        p.drawText(QRectF(pad, name_rect.bottom() + config.S(2), r.width() - 2 * pad, config.S(20)),
                   Qt.AlignLeft | Qt.AlignVCenter, _txt("en", "splash_tagline"))

        # Indeterminate progress line along the bottom
        track = QRectF(pad, r.bottom() - pad + config.S(2), r.width() - 2 * pad, config.S(3))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(track, track.height() / 2, track.height() / 2)
        seg_w = track.width() * 0.28
        x = track.left() - seg_w + (track.width() + seg_w) * self._phase
        seg = QRectF(max(track.left(), x), track.top(), min(track.right(), x + seg_w) - max(track.left(), x), track.height())
        if seg.width() > 0:
            p.setBrush(brand.gradient(seg.left(), seg.right()))
            p.drawRoundedRect(seg, track.height() / 2, track.height() / 2)

        # Version, bottom right above the line
        small = QFont(self.font())
        small.setPointSizeF(config.FS(8))
        p.setFont(small)
        p.setPen(QColor("#6b6e8a"))
        p.drawText(QRectF(pad, track.top() - config.S(22), track.width(), config.S(16)),
                   Qt.AlignRight | Qt.AlignVCenter, f"v{config.VERSION}")


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

        W, H = config.S(440), config.S(250)
        self.setFixedSize(W + config.S(24), H + config.S(24))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))

        splash_file = _find_splash_path()
        self.inner_frame = SplashInnerFrame(splash_file, W, H, self)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(24))
        shadow.setColor(qc(0, 0, 0, 190))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)

        main_layout.addWidget(self.inner_frame)

        content_layout = QVBoxLayout(self.inner_frame)
        # Status text sits bottom-left, just above the progress line
        content_layout.setContentsMargins(config.S(28), 0, config.S(28), config.S(30))
        content_layout.addStretch()

        self._lbl_loading = QLabel(self.txt("lbl_loading").upper(), self.inner_frame)
        self._lbl_loading.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._lbl_loading.setStyleSheet(f"""
            QLabel {{
                color: #a0a0a0;
                font-size: {config.FS(8)}pt;
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
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self.inner_frame.advance)
        self._progress_timer.start(16)

    def _animate(self):
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText(f"LOADING{dots}")
        self._dot_count += 1

    def set_status(self, text: str):
        self._timer.stop()
        # A sentence reads better without the wide spacing of the LOADING label
        self._lbl_loading.setStyleSheet(self._lbl_loading.styleSheet().replace("letter-spacing: 1.5px;", "letter-spacing: 0px;"))
        self._lbl_loading.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event):
        self._timer.stop()
        self._progress_timer.stop()
        super().closeEvent(event)
