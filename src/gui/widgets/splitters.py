#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: splitters.py
ROLE: GUI Widget
DESCRIPTION:
Custom splitters for resizable GUI panels.
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

class GripHandle(QSplitterHandle):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        from PySide6.QtCore import QVariantAnimation
        self.setAttribute(Qt.WA_Hover)
        self._pressed = False
        self._anim_val = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.valueChanged.connect(self._on_anim_value)
        
    def _on_anim_value(self, val):
        self._anim_val = val
        self.update()

    def mousePressEvent(self, event):
        self._pressed = True
        self._anim.stop()
        self._anim.setStartValue(self._anim_val)
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        self._pressed = False
        self._anim.stop()
        self._anim.setStartValue(self._anim_val)
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        
        w = self.width() 
        h = self.height()
        is_left_handle = (self == self.splitter().handle(1))
        
        painter.fillRect(0, 0, w, h, QColor("#212121"))
        
        line_w = 1 + int(self._anim_val * 2)
        x = (w - line_w) if is_left_handle else 0
        
        r = int(42 + (30 - 42) * self._anim_val)
        g = int(42 + (215 - 42) * self._anim_val)
        b = int(42 + (96 - 42) * self._anim_val)
        
        painter.fillRect(x, 0, line_w, h, QColor(r, g, b))

class GripSplitter(QSplitter):
    def createHandle(self):
        handle = GripHandle(self.orientation(), self)
        handle.setCursor(Qt.CursorShape.SplitHCursor)
        return handle

