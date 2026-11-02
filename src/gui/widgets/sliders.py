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

