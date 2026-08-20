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

class WrappingPlaceholderTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_placeholder = ""

    def setPlaceholderText(self, text):
        self._custom_placeholder = text
        self.viewport().update()

    def placeholderText(self):
        return self._custom_placeholder

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.toPlainText() and self._custom_placeholder:
            p = QPainter(self.viewport())
            p.setPen(QColor("#777777"))
            rect = self.viewport().rect().adjusted(5, 5, -5, -5)
            p.drawText(rect, Qt.AlignTop | Qt.TextWordWrap, self._custom_placeholder)
            p.end()

class SBSTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def setCustomPlaceholderText(self, text):
        # We use native placeholder instead of custom paint to prevent QPainter lag storms
        self.setPlaceholderText(text)

