#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: progress_bar.py
ROLE: GUI Widget
DESCRIPTION:
Custom progress bars with animation support.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config

# Aliases for original standard classes we override
_QPushButton = QPushButton
_QLabel = QLabel
_QRadioButton = QRadioButton

class LiquidProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._indet_offset = 0.0
        self._indeterminate = False
        h = config.S(getattr(config, "PROGRESS_HEIGHT", 8))
        self.setFixedHeight(h)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self._loop_anim = QPropertyAnimation(self, b"indet_offset")
        self._loop_anim.setDuration(1500)
        self._loop_anim.setStartValue(0.0)
        self._loop_anim.setEndValue(1.0)
        self._loop_anim.setLoopCount(-1)

    def sizeHint(self):
        return QSize(config.S(400), max(self.height(), config.S(getattr(config, "PROGRESS_HEIGHT", 8))))

    def minimumSizeHint(self):
        return QSize(config.S(160), max(self.height(), config.S(getattr(config, "PROGRESS_HEIGHT", 8))))

    @Property(float)
    def value(self): return self._value

    @value.setter
    def value(self, val):
        self._value = max(0.0, min(100.0, float(val)))
        self.update()
        
    @Property(float)
    def indet_offset(self): return self._indet_offset

    @indet_offset.setter
    def indet_offset(self, val):
        self._indet_offset = val
        self.update()

    def set_value(self, val):
        if val < 0:
            if not self._indeterminate:
                self._indeterminate = True
                self._anim.stop()
                self._loop_anim.start()
        else:
            if self._indeterminate:
                self._indeterminate = False
                self._loop_anim.stop()
            target_val = max(0.0, min(100.0, float(val)))
            diff = abs(target_val - self._value)
            if diff < 0.05:
                return
            # Dynamic duration: rapid small updates finish quickly without stalling the easing curve
            duration = int(max(60, min(250, diff * 12)))
            self._anim.stop()
            self._anim.setDuration(duration)
            self._anim.setStartValue(self._value)
            self._anim.setEndValue(target_val)
            self._anim.start()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath
        from PySide6.QtCore import QRectF
        rect = self.rect()
        w = float(rect.width())
        h = float(rect.height())
        if w <= 2.0 or h <= 2.0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # INVARIANT: Inset track & clip path by 0.5px so rounded caps never clip or pinch at 1%-3% across DPI scales
        inset = 0.5
        tw = max(1.0, w - inset * 2.0)
        th = max(1.0, h - inset * 2.0)
        r = th / 2.0

        track_path = QPainterPath()
        track_path.addRoundedRect(QRectF(inset, inset, tw, th), r, r)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(getattr(config, "PROGRESS_TRACK_COLOR", "#2b2b2b")))
        p.drawPath(track_path)

        # Clip all inner fills to the inset rounded track path so ends are always smoothly rounded
        p.setClipPath(track_path)

        if self._indeterminate:
            pill_width = max(th, tw * 0.25)
            x_pos = inset + self._indet_offset * (tw + pill_width) - pill_width

            grad = QLinearGradient(x_pos, 0.0, x_pos + pill_width, 0.0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))

            p.setBrush(grad)
            p.drawRoundedRect(QRectF(x_pos, inset, pill_width, th), r, r)
        elif self._value > 0:
            fill_width = (self._value / 100.0) * tw
            if fill_width > 0.0:
                draw_x = inset + min(0.0, fill_width - th)
                draw_w = max(fill_width, th)
                fill_rect = QRectF(draw_x, inset, draw_w, th)

                grad = QLinearGradient(inset, 0.0, inset + max(fill_width, 1.0), 0.0)
                grad.setColorAt(0.0, QColor("#1a7a3e"))
                grad.setColorAt(1.0, QColor("#b8d035"))

                p.setBrush(grad)
                p.drawRoundedRect(fill_rect, r, r)


