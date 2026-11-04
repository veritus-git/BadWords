#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: video_preview.py
ROLE: GUI Component
DESCRIPTION:
16:9 Video playback preview container utilizing QVideoWidget.
Features rounded corners, aspect-ratio preservation, and sleek DaVinci Resolve styling.
Supports background proxy generation status with a smooth vector spinner and instant playback.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QSize, QTimer, QRectF, QPointF
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy, QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from PySide6.QtMultimediaWidgets import QVideoWidget

import config


class VideoLoadingWidget(QWidget):
    """
    Subtle loading widget with a smooth vector spinner and gray status text,
    matching TopStatusIsland style.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._spinner_angle = 0
        self._text = ""

        # Gentle 30 FPS timer for vector spinner animation
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)

        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_text(self, text: str):
        # Strip any emojis from text to guarantee zero emojis
        cleaned = text.replace("⏳", "").replace("⌛", "").strip()
        self._text = cleaned
        self.update()

    def start(self, text: str = ""):
        self.set_text(text)
        self._spinner_angle = 0
        if not self._timer.isActive():
            self._timer.start()
        self.show()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()
        self.hide()

    def _on_tick(self):
        if self.isVisible():
            self._spinner_angle = (self._spinner_angle + 12) % 360
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())

        f = QFont(config.UI_FONT_NAME, config.FS(8.5))
        p.setFont(f)
        fm = QFontMetrics(f)

        spinner_size = float(config.S(12.0))
        gap = float(config.S(8.0))

        # Compute text and handle eliding if space is tight
        max_text_w = max(10.0, w - spinner_size - gap - float(config.S(16.0)))
        elided_text = fm.elidedText(self._text, Qt.ElideRight, int(max_text_w)) if self._text else ""
        text_w = fm.horizontalAdvance(elided_text) if elided_text else 0

        total_w = spinner_size + (gap + text_w if elided_text else 0)
        start_x = (w - total_w) / 2.0
        cy = h / 2.0

        # Draw rotating vector spinner (exact same arc style as TopStatusIsland)
        spinner_cx = start_x + spinner_size / 2.0
        r = spinner_size / 2.0

        p.save()
        p.translate(spinner_cx, cy)
        p.rotate(self._spinner_angle)
        arc_rect = QRectF(-r, -r, r * 2.0, r * 2.0)
        spinner_pen = QPen(QColor("#23a559"), config.S(1.6), Qt.SolidLine, Qt.RoundCap)
        p.setPen(spinner_pen)
        p.drawArc(arc_rect, 0, 270 * 16)
        p.restore()

        # Draw subtle gray text (zero emojis, non-intrusive)
        if elided_text:
            text_x = start_x + spinner_size + gap
            text_y = (h + fm.ascent() - fm.descent()) / 2.0
            p.setPen(QColor("#888888"))
            p.drawText(QPointF(text_x, text_y), elided_text)


class VideoPreviewWidget(QFrame):
    """
    Video playback monitor container for talking-head and timeline footage.
    Embedded in the bottom dock alongside the Timeline Preview ribbon.
    """
    def __init__(self, parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.setObjectName("VideoPreviewWidget")
        self.setStyleSheet(f"""
            QFrame#VideoPreviewWidget {{
                background-color: #0c0c0c;
                border: 1px solid #242424;
                border-radius: {config.S(6)}px;
            }}
        """)
        self.setMinimumHeight(config.S(90))
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet(f"background-color: #000000; border-radius: {config.S(6)}px;")
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        layout.addWidget(self.video_widget)

        self.loading_widget = VideoLoadingWidget(self)
        self.loading_widget.hide()
        layout.addWidget(self.loading_widget)

        self.lbl_placeholder = QLabel(self)
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder.setStyleSheet(f"color: #4a4a4a; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(8.5)}pt; font-style: italic;")
        self.lbl_placeholder.setText("Video Preview")
        self.lbl_placeholder.hide()
        layout.addWidget(self.lbl_placeholder)

    def sizeHint(self) -> QSize:
        h = max(config.S(90), self.height() if self.height() > 0 else config.S(145))
        w = int(h * 16.0 / 9.0)
        return QSize(w, h)

    def show_placeholder(self, show: bool = True, text: str = "Video Preview") -> None:
        if show:
            self.loading_widget.stop()
            self.lbl_placeholder.setStyleSheet(f"color: #4a4a4a; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(8.5)}pt; font-style: italic;")
            self.lbl_placeholder.setText(text)
            self.lbl_placeholder.show()
            self.video_widget.hide()
        else:
            self.lbl_placeholder.hide()
            if not self.loading_widget.isVisible():
                self.video_widget.show()

    def show_loading(self, show: bool = True, text: str = "Generating preview...") -> None:
        if show:
            self.lbl_placeholder.hide()
            self.video_widget.hide()
            self.loading_widget.start(text)
        else:
            self.loading_widget.stop()
            if not self.lbl_placeholder.isVisible():
                self.video_widget.show()
