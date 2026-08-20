#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

class JumpSlider(QSlider):
    def mousePressEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.button() == Qt.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * ev.position().x()) / self.width()
            self.setValue(int(val))
            ev.accept()
            self.sliderPressed.emit()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        from PySide6.QtCore import Qt
        if ev.buttons() & Qt.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * ev.position().x()) / self.width()
            self.setValue(int(val))
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

