#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: labels.py
ROLE: GUI Widget
DESCRIPTION:
Custom text label widgets.
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
        self.setMouseTracking(True)

    def _get_text_color(self):
        if hasattr(self, '_custom_color') and self._custom_color:
            return QColor(self._custom_color)
        ss = self.styleSheet()
        if 'color:' in ss:
            import re
            m = re.search(r'color:\s*([^;]+);', ss)
            if m:
                c = QColor(m.group(1).strip())
                if c.isValid() and c != QColor("#000000"):
                    return c
        return QColor("#ffffff")

    def _mq_get_text(self):
        t = super().text()
        # Strip HTML tags for advance measurement
        import re as _re
        return _re.sub(r'<[^>]+>', '', t)

    def _is_physically_truncated(self):
        """
        Determines whether the text is physically truncated or obscured on screen.
        Checks:
        1. Whether sizeHint (with full QSS styles/fonts) or fontMetrics exceeds allocated space.
        2. Whether the widget is physically clipped or obscured by parent bounds or visibleRegion.
        3. For word-wrapped labels: only True if height is insufficient to show all lines.
        """
        if self.wordWrap():
            sh = self.sizeHint()
            h = self.height()
            if h <= 0:
                return False
            return sh.height() > h + 2

        t = self._mq_get_text()
        if not t or len(t.strip()) <= 1 or '\n' in t:
            return False

        cr = self.contentsRect()
        avail = cr.width()
        if avail <= 0:
            return False

        # Physical on-screen visibility check:
        # If the widget is clipped by a parent widget, layout or scroll viewport,
        # visibleRegion().boundingRect() gives the exact visible pixel rectangle.
        try:
            vis = self.visibleRegion().boundingRect()
            if vis.isValid() and 0 < vis.width() < self.width():
                avail = min(avail, vis.width())
        except Exception:
            pass

        p = self.parentWidget()
        if p and 0 < p.width() < self.width():
            avail = min(avail, p.width())

        sh_w = self.sizeHint().width()
        fm_w = self.fontMetrics().horizontalAdvance(t)
        needed = max(sh_w, fm_w)

        return needed > avail + 2

    def enterEvent(self, event):
        super().enterEvent(event)
        self._mq_hovered = True
        try:
            if self._is_physically_truncated():
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
        cr = self.contentsRect()
        avail = cr.width()
        try:
            vis = self.visibleRegion().boundingRect()
            if vis.isValid() and 0 < vis.width() < self.width():
                avail = min(avail, vis.width())
        except Exception:
            pass
        p = self.parentWidget()
        if p and 0 < p.width() < self.width():
            avail = min(avail, p.width())

        text = self._mq_get_text()
        fm = self.fontMetrics()
        text_w = max(self.sizeHint().width(), fm.horizontalAdvance(text))
        max_scroll = float(max(0, text_w - avail))

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

        color = self._get_text_color()
        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))

        raw_text = super().text()
        if "<" in raw_text and ">" in raw_text:
            from PySide6.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setDefaultFont(self.font())
            doc.setHtml(f"<div style='color: {color.name()};'>{raw_text}</div>")
            doc.setDocumentMargin(0)
            
            y_pos = cr.top() + (cr.height() - doc.size().height()) / 2
            painter.translate(cr.left() - int(self._mq_pos), y_pos)
            doc.drawContents(painter)
        else:
            painter.setPen(color)
            painter.setFont(self.font())
            text = self._mq_get_text()
            draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
            painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

class IDETooltip(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #454545;
                padding: 4px 8px;
                font-family: '{config.UI_FONT_NAME}', sans-serif;
                font-size: 9pt;
            }}
        """)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def show_beside(self, widget, is_right_side=False):
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
    """Convenience subclass of QLabel with marquee enabled."""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("color: #d4d4d4; font-size: 9.5pt;")
