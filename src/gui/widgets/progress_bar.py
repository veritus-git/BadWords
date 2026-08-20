#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: progress_bar.py
ROLE: Module
DESCRIPTION:
Provides core functionality for this component.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config
from i18n import get_trans
import sys
import os

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
        self.setFixedHeight(8)
        
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self._loop_anim = QPropertyAnimation(self, b"indet_offset")
        self._loop_anim.setDuration(1500)
        self._loop_anim.setStartValue(0.0)
        self._loop_anim.setEndValue(1.0)
        self._loop_anim.setLoopCount(-1)

    @Property(float)
    def value(self): return self._value

    @value.setter
    def value(self, val):
        self._value = val
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
            self._anim.stop()
            self._anim.setEndValue(float(val))
            self._anim.start()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2b2b2b"))
        p.drawRoundedRect(rect, 4, 4)
        
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 4, 4)
        p.setClipPath(path)
        
        if self._indeterminate:
            pill_width = rect.width() * 0.25
            x_pos = self._indet_offset * (rect.width() + pill_width) - pill_width
            
            grad = QLinearGradient(x_pos, 0, x_pos + pill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(x_pos, 0, pill_width, rect.height()), 4, 4)
        elif self._value > 0:
            fill_width = (self._value / 100.0) * rect.width()
            fill_rect = QRectF(0, 0, fill_width, rect.height())
            
            grad = QLinearGradient(0, 0, fill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, 4, 4)

