#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: sliders.py
ROLE: GUI Widget
DESCRIPTION:
Custom slider widgets for configuration settings.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *

# Aliases for original standard classes we override
_QPushButton = QPushButton
_QLabel = QLabel
_QRadioButton = QRadioButton

class JumpSlider(QSlider):
    def mousePressEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.button() == Qt.LeftButton:
            w = max(1, self.width())
            ratio = max(0.0, min(1.0, ev.position().x() / float(w)))
            val = self.minimum() + ((self.maximum() - self.minimum()) * ratio)
            ival = int(round(val))
            self.setValue(ival)
            self.sliderPressed.emit()
            self.sliderMoved.emit(ival)
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.buttons() & Qt.LeftButton:
            w = max(1, self.width())
            ratio = max(0.0, min(1.0, ev.position().x() / float(w)))
            val = self.minimum() + ((self.maximum() - self.minimum()) * ratio)
            ival = int(round(val))
            self.setValue(ival)
            self.sliderMoved.emit(ival)
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.button() == Qt.LeftButton:
            self.sliderReleased.emit()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)


class SlimAudioSeekBar(QSlider):
    """
    Sleek, borderless seek slider drawn with pure anti-aliased vector geometry.
    Has zero extra background height, does not push elements apart, and renders
    the playhead as an unclipped, perfectly smooth circular dot.
    """
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        import config
        self.config = config
        self.setRange(0, 1000)
        self.setValue(0)
        self.setFixedHeight(config.S(14))
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setStyleSheet("background: transparent; border: none; margin: 0px; padding: 0px;")
        self._hovered = False
        self._dragging = False

    def enterEvent(self, ev):
        self._hovered = True
        self.update()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        self._hovered = False
        self.update()
        super().leaveEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._dragging = True
            w = max(1, self.width())
            pos_x = ev.position().x() if hasattr(ev, 'position') else ev.x()
            ratio = max(0.0, min(1.0, pos_x / float(w)))
            val = int(round(self.minimum() + ((self.maximum() - self.minimum()) * ratio)))
            self.setValue(val)
            self.sliderPressed.emit()
            self.sliderMoved.emit(val)
            self.update()
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            w = max(1, self.width())
            pos_x = ev.position().x() if hasattr(ev, 'position') else ev.x()
            ratio = max(0.0, min(1.0, pos_x / float(w)))
            val = int(round(self.minimum() + ((self.maximum() - self.minimum()) * ratio)))
            self.setValue(val)
            self.sliderMoved.emit(val)
            self.update()
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._dragging = False
            self.sliderReleased.emit()
            self.update()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w = float(self.width())
        h = float(self.height())
        cy = h / 2.0
        line_h = float(self.config.S(4.0))
        radius = float(self.config.S(2.0))

        # Progress ratio
        rng = self.maximum() - self.minimum()
        ratio = (self.value() - self.minimum()) / float(rng) if rng > 0 else 0.0
        ratio = max(0.0, min(1.0, ratio))

        # 1. Background unplayed track (solid opaque dark grey)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#383838"))
        painter.drawRoundedRect(QRectF(0.0, cy - line_h / 2.0, w, line_h), radius, radius)

        # 2. Played progress track (matching v3.2.4 exact: #1ed760)
        played_w = w * ratio
        if played_w > 0:
            painter.setBrush(QColor("#1ed760"))
            painter.drawRoundedRect(QRectF(0.0, cy - line_h / 2.0, played_w, line_h), radius, radius)

        # 3. Smooth white circle dot (kropka, diameter 10px idle / 12px hover)
        r = float(self.config.S(6.0 if (self._hovered or self._dragging) else 5.0))
        dot_x = max(r, min(w - r, played_w))
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(dot_x, cy), r, r)



