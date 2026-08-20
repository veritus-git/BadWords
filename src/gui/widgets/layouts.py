#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: layouts.py
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

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=-1, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        if margin != -1: self.setContentsMargins(margin, margin, margin, margin)
        self.m_hSpace = hSpacing
        self.m_vSpace = vSpacing
        self.itemList = []
    def addItem(self, item): self.itemList.append(item)
    def horizontalSpacing(self): return self.m_hSpace if self.m_hSpace >= 0 else self.spacing()
    def verticalSpacing(self): return self.m_vSpace if self.m_vSpace >= 0 else self.spacing()
    def count(self): return len(self.itemList)
    def itemAt(self, index): return self.itemList[index] if 0 <= index < len(self.itemList) else None
    def takeAt(self, index):
        if 0 <= index < len(self.itemList): return self.itemList.pop(index)
        return None
    def expandingDirections(self): return Qt.Orientations(0)
    def hasHeightForWidth(self): return True
    def heightForWidth(self, width): return self.doLayout(QRect(0, 0, width, 0), True)
    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)
    def sizeHint(self):
        w = self.parentWidget().width() if self.parentWidget() else 0
        if w > 0:
            return QSize(w, self.heightForWidth(w))
        return self.minimumSize()
    def minimumSize(self):
        size = QSize()
        for item in self.itemList: size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size
    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.horizontalSpacing()
            if spaceX == -1: spaceX = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = self.verticalSpacing()
            if spaceY == -1: spaceY = wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            if not testOnly: item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        return y + lineHeight - rect.y()

class MainPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layer1 = QWidget(self)
        self.layer2 = QWidget(self)
        self.layer2.setObjectName("Layer2Overlay")
        self.layer2.setStyleSheet("QWidget#Layer2Overlay { background-color: transparent; border: none; }")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        self._shadow = QGraphicsDropShadowEffect(self.layer2)
        self._shadow.setBlurRadius(15)
        self._shadow.setColor(QColor(0, 0, 0, 0))
        self._shadow.setOffset(0, -2)
        self.layer2.setGraphicsEffect(self._shadow)
        self._is_overlapping = False
        
    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)
        self.layer1.setGeometry(0, 0, self.width(), self.height())
        hint = self.layer2.sizeHint()
        if self.layer2.layout():
            hint = self.layer2.layout().sizeHint()
        self.layer2.setGeometry(0, self.height() - hint.height(), self.width(), hint.height())
        
        # Dynamic overlap check
        if event is None and hasattr(self, '_last_l1_hint'):
            l1_hint = self._last_l1_hint
        else:
            l1_hint = self.layer1.layout().sizeHint().height() if self.layer1.layout() else 0
            self._last_l1_hint = l1_hint
            
        overlap = (l1_hint + hint.height() + 20) > self.height()
        if overlap != getattr(self, '_is_overlapping', False):
            self._is_overlapping = overlap
            if overlap:
                self.layer2.setStyleSheet("QWidget#Layer2Overlay { background-color: #212121; border-top: 1px solid #2e2e2e; }")
                self._shadow.setColor(QColor(0, 0, 0, 90))
            else:
                self.layer2.setStyleSheet("QWidget#Layer2Overlay { background-color: transparent; border: none; }")
                self._shadow.setColor(QColor(0, 0, 0, 0))

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.resizeEvent(None))

