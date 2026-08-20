#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: labels.py
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

class QLabel(_QLabel):
    """Patched QLabel — shows a smooth marquee on hover whenever its text is wider
    than the label's display area (single-line labels only; wordWrap ignored)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_scroll)
        self._mq_timer.setInterval(16)
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_state = "START_DELAY"
        self._mq_ticks = 0

    def _mq_get_text(self):
        t = super().text()
        # Strip HTML tags for advance measurement
        import re as _re
        return _re.sub(r'<[^>]+>', '', t)

    def _mq_active(self):
        """Only run marquee for single-line, non-wrapping labels with enough text."""
        if self.wordWrap():
            return False
        t = self._mq_get_text()
        return bool(t) and len(t.strip()) > 3

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self._mq_active():
            return
        self._mq_hovered = True
        try:
            fm = self.fontMetrics()
            avail = self.contentsRect().width()
            if fm.horizontalAdvance(self._mq_get_text()) > avail:
                self._mq_is_squeezed = True
                self._mq_pos = 0.0
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
                self._mq_timer.start()
            else:
                self._mq_is_squeezed = False
        except Exception:
            pass

    def leaveEvent(self, event):
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_timer.stop()
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self.update()
        super().leaveEvent(event)

    def _mq_scroll(self):
        fm = self.fontMetrics()
        avail = self.contentsRect().width()
        text = self._mq_get_text()
        max_scroll = float(max(0, fm.horizontalAdvance(text) - avail))

        if self._mq_state == "START_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:
                self._mq_state = "SCROLL"
                self._mq_ticks = 0
        elif self._mq_state == "SCROLL":
            self._mq_pos += 0.5
            if self._mq_pos >= max_scroll:
                self._mq_pos = max_scroll
                self._mq_state = "END_DELAY"
                self._mq_ticks = 0
        elif self._mq_state == "END_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:
                self._mq_state = "FADEOUT"
                self._mq_ticks = 0
        elif self._mq_state == "FADEOUT":
            self._mq_alpha -= 0.05
            if self._mq_alpha <= 0.0:
                self._mq_alpha = 0.0
                self._mq_pos = 0.0
                self._mq_state = "FADEIN"
        elif self._mq_state == "FADEIN":
            self._mq_alpha += 0.05
            if self._mq_alpha >= 1.0:
                self._mq_alpha = 1.0
                self._mq_state = "START_DELAY"
                self._mq_ticks = 0
        self.update()

    def paintEvent(self, event):
        if not self._mq_hovered or not self._mq_is_squeezed:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        cr = self.contentsRect()
        painter.setClipRect(cr)

        if self._mq_alpha < 1.0:
            painter.setOpacity(max(0.0, min(1.0, self._mq_alpha)))

        raw_text = super().text()
        if "<" in raw_text and ">" in raw_text:
            from PySide6.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setDefaultFont(self.font())
            color_name = self.palette().windowText().color().name()
            doc.setHtml(f"<div style='color: {color_name};'>{raw_text}</div>")
            doc.setDocumentMargin(0)
            
            y_pos = cr.top() + (cr.height() - doc.size().height()) / 2
            painter.translate(cr.left() - int(self._mq_pos), y_pos)
            doc.drawContents(painter)
        else:
            color = self.palette().windowText().color()
            painter.setPen(color)
            painter.setFont(self.font())
            text = self._mq_get_text()
            draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
            painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

class IDETooltip(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #454545;
                padding: 4px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 10pt;
            }
        """)
        self.hide()

    def show_at(self, widget, text, is_right_side):
        self.setText(text)
        self.adjustSize()

        rect = widget.rect()
        global_pos = widget.mapToGlobal(rect.topLeft())

        if not is_right_side:
            x = global_pos.x() + rect.width() + 5
        else:
            x = global_pos.x() - self.width() - 5

        y = global_pos.y() + (rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()

    def show_global(self, text, pos):
        self.setText(text)
        self.adjustSize()
        # Offset cursor by ~15px below it
        self.move(pos.x(), pos.y() + 15)
        self.show()

class MarqueeLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self._mq_timer = QTimer(self)
        self._mq_timer.setInterval(25)
        self._mq_timer.timeout.connect(self._scroll_step)
        self._mq_pos = 0.0
        self._hovered = False
        self.setMouseTracking(True)
        self.setStyleSheet("color: #d4d4d4; font-size: 9.5pt;")

    def setText(self, text):
        self._full_text = text
        self._mq_pos = 0.0
        super().setText(text)
        self.update()

    def text(self):
        return self._full_text

    def enterEvent(self, event):
        self._hovered = True
        if self._is_truncated():
            self._mq_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._mq_timer.stop()
        self._mq_pos = 0.0
        self.update()
        super().leaveEvent(event)

    def _is_truncated(self):
        fm = self.fontMetrics()
        return fm.horizontalAdvance(self._full_text) > self.width()

    def _scroll_step(self):
        fm = self.fontMetrics()
        txt_w = fm.horizontalAdvance(self._full_text)
        self._mq_pos += 1.2
        if self._mq_pos > txt_w + 20:
            self._mq_pos = -self.width()
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        from PySide6.QtCore import Qt

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fm = self.fontMetrics()

        if self._hovered and self._is_truncated() and self._mq_timer.isActive():
            p.setPen(QColor("#ffffff"))
            p.drawText(int(-self._mq_pos), fm.ascent() + (self.height() - fm.height()) // 2, self._full_text)
        else:
            elided = fm.elidedText(self._full_text, Qt.ElideRight, max(1, self.width()))
            p.setPen(QColor("#d4d4d4"))
            p.drawText(0, fm.ascent() + (self.height() - fm.height()) // 2, elided)

