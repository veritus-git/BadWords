#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: gui.py
ROLE: Presentation Layer
DESCRIPTION:
Responsible solely for displaying the interface (PySide6).
Includes dark-theme styling via QSS based on config.py color palette.
Receives user actions and delegates them to Engine or ResolveHandler.
[PySide6 migration: Stage 2 — Main Window Shell & Dynamic Panels]
"""

from PySide6 import QtCore
import re
import math
import platform
import subprocess
import os
import time
import traceback
import ctypes
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QCheckBox,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QAbstractItemView, QFrame, QScrollArea,
    QDockWidget, QToolBar, QStackedWidget, QFormLayout, QComboBox,
    QSpacerItem, QCompleter, QLineEdit, QWidgetAction, QToolTip,
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter, QSplitterHandle,
    QTabWidget, QSpinBox, QButtonGroup
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation, Property
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter, QPen, QFontMetrics, QLinearGradient
)
from PySide6.QtCore import QMimeData

import config
import osdoc

# ==========================================
# CONSTANTS
# ==========================================
RTL_CODES = {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'}  # Right-To-Left Languages


# ==========================================
# HELPERS
# ==========================================

_QPushButton = QPushButton
class QPushButton(_QPushButton):
    """Patched QPushButton to support smooth marquee (scroll) effect on hover when text is squeezed."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mq_timer = QTimer(self)
        self._mq_timer.timeout.connect(self._mq_scroll)
        self._mq_timer.setInterval(16)  # ~60fps smooth scroll
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        self._mq_hovered = False
        self._mq_is_squeezed = False
        self._mq_state = "START_DELAY"
        self._mq_ticks = 0

    def setText(self, str_text):
        self.setProperty("_mq_original_text", str_text)
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        super().setText(str_text)

    def text(self):
        orig = self.property("_mq_original_text")
        if orig is not None:
            return orig
        return super().text()

    def _mq_text_area_width(self):
        """Returns the pixel width actually available for text rendering,
        derived from the widget's contentsRect (excludes QSS padding/margins)."""
        return self.contentsRect().width()

    def enterEvent(self, event):
        super().enterEvent(event)
        orig = self.property("_mq_original_text")
        if orig is None:
            orig = super().text()
            self.setProperty("_mq_original_text", orig)

        self._mq_hovered = True
        try:
            if not orig or len(orig.strip()) <= 3:
                self._mq_is_squeezed = False
                return
            fm = self.fontMetrics()
            if fm.horizontalAdvance(orig) > self._mq_text_area_width():
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
        orig = self.property("_mq_original_text")
        if not orig: return
        fm = self.fontMetrics()
        clip_w = self._mq_text_area_width()
        max_scroll = float(max(0, fm.horizontalAdvance(orig) - clip_w))

        if self._mq_state == "START_DELAY":
            self._mq_ticks += 1
            if self._mq_ticks > 40:  # ~640ms
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

        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        orig = self.property("_mq_original_text") or ""
        opt.text = ""  # Hide native text to draw our own
        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_PushButton, opt, painter, self)

        cr = self.contentsRect()
        painter.setClipRect(cr)
        color = opt.palette.buttonText().color()
        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))
        painter.setPen(color)
        draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, orig)


_QRadioButton = QRadioButton
class MarqueeRadioButton(_QRadioButton):
    """QRadioButton with smooth marquee (scroll) effect on hover when text is truncated.
    Uses QStyle.SE_RadioButtonContents to get the exact text rect Qt uses internally."""

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
        self._mq_original_text = None

    def setText(self, txt):
        self._mq_original_text = txt
        self._mq_pos = 0.0
        self._mq_alpha = 1.0
        super().setText(txt)

    def text(self):
        if self._mq_original_text is not None:
            return self._mq_original_text
        return super().text()

    def _mq_text_rect(self):
        """Returns the exact QRect where Qt would render the radio button text.
        Uses the style's SE_RadioButtonContents sub-element — 100% accurate,
        no magic offset constants, works with any style/DPI/font."""
        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        return self.style().subElementRect(QStyle.SE_RadioButtonContents, opt, self)

    def enterEvent(self, event):
        super().enterEvent(event)
        orig = self._mq_original_text
        if orig is None:
            orig = super().text()
            self._mq_original_text = orig

        self._mq_hovered = True
        try:
            if not orig or len(orig.strip()) <= 3:
                self._mq_is_squeezed = False
                return
            fm = self.fontMetrics()
            if fm.horizontalAdvance(orig) > self._mq_text_rect().width():
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
        orig = self._mq_original_text
        if not orig:
            return
        fm = self.fontMetrics()
        tr = self._mq_text_rect()
        max_scroll = float(max(0, fm.horizontalAdvance(orig) - tr.width()))

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

        from PySide6.QtWidgets import QStyleOptionButton, QStyle
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ""
        painter = QPainter(self)
        self.style().drawControl(QStyle.CE_RadioButton, opt, painter, self)

        tr = self._mq_text_rect()
        painter.setClipRect(tr)

        color = opt.palette.buttonText().color()
        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))
        painter.setPen(color)
        painter.setFont(self.font())
        draw_rect = QRect(tr.left() - int(self._mq_pos), tr.top(), 9999, tr.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, self._mq_original_text or "")


_QLabel = QLabel
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

        color = self.palette().windowText().color()
        if self._mq_alpha < 1.0:
            color.setAlphaF(max(0.0, min(1.0, self._mq_alpha)))
        painter.setPen(color)
        painter.setFont(self.font())

        text = self._mq_get_text()
        draw_rect = QRect(cr.left() - int(self._mq_pos), cr.top(), 9999, cr.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, text)




class GripHandle(QSplitterHandle):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width() # Expected to be 10
        h = self.height()
        half_w = w // 2  # Exactly 5
        
        # BULLETPROOF CHECK: handle(1) is always between LeftPanel and Stack.
        # If self is handle(1), it's the left sidebar grip. Else, it's the right one.
        is_left_handle = (self == self.splitter().handle(1))
        
        # 1. 50/50 Seamless Background Split
        if is_left_handle:
            painter.fillRect(0, 0, half_w, h, QColor("#212121")) # Left half touches panel
            painter.fillRect(half_w, 0, w - half_w, h, QColor("#1c1c1c")) # Right half touches workspace
        else:
            painter.fillRect(0, 0, half_w, h, QColor("#1c1c1c")) # Left half touches workspace
            painter.fillRect(half_w, 0, w - half_w, h, QColor("#212121")) # Right half touches panel
            
        # 2. Draw the Grip Pill (Centered, perfectly bisected by the background split)
        pill_width = 6
        pill_height = 36
        x = (w - pill_width) // 2
        y = (h - pill_height) // 2
        
        painter.setBrush(QColor("#555555"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, pill_width, pill_height, 3, 3)
        
        # 3. Draw 3 Centered Dots
        painter.setBrush(QColor("#aaaaaa"))
        dot_size = 2
        dot_x = x + (pill_width - dot_size) // 2
        
        painter.drawEllipse(dot_x, y + 8, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 17, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 26, dot_size, dot_size)

class GripSplitter(QSplitter):
    def createHandle(self):
        handle = GripHandle(self.orientation(), self)
        handle.setCursor(Qt.CursorShape.SplitHCursor)
        return handle


from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import QModelIndex

class MarqueeItemDelegate(QStyledItemDelegate):
    """Delegate for QListWidget that draws item text with a smooth marquee
    animation on hover when the text is wider than the available column width.
    Completely replaces the default item renderer — no horizontal scrollbar needed.
    """
    _PADDING = 16  # must match QSS padding: 10px 16px

    def __init__(self, list_widget):
        super().__init__(list_widget)
        self._lw = list_widget
        # State per row index
        self._mq_pos   = {}   # float offset
        self._mq_alpha = {}   # 0.0–1.0 fade
        self._mq_state = {}   # str state machine
        self._mq_ticks = {}   # int tick counter
        self._hovered_row = -1

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60fps
        self._timer.timeout.connect(self._tick)

        # Install event filter on the viewport to catch mouse moves
        self._lw.viewport().installEventFilter(self)
        self._lw.viewport().setMouseTracking(True)

    def _row_state(self, row):
        if row not in self._mq_state:
            self._mq_pos[row]   = 0.0
            self._mq_alpha[row] = 1.0
            self._mq_state[row] = "START_DELAY"
            self._mq_ticks[row] = 0
        return self._mq_state[row]

    def _reset_row(self, row):
        self._mq_pos[row]   = 0.0
        self._mq_alpha[row] = 1.0
        self._mq_state[row] = "START_DELAY"
        self._mq_ticks[row] = 0

    def _available_width(self):
        """Pixel width available for text inside the list (minus padding)."""
        return self._lw.viewport().width() - self._PADDING * 2

    def _text_overflows(self, row):
        item = self._lw.item(row)
        if item is None:
            return False
        fm = self._lw.fontMetrics()
        return fm.horizontalAdvance(item.text()) > self._available_width()

    def eventFilter(self, obj, event):
        if obj is self._lw.viewport():
            if event.type() == QEvent.Type.MouseMove:
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                idx = self._lw.indexAt(pos)
                new_row = idx.row() if idx.isValid() else -1
                if new_row != self._hovered_row:
                    old = self._hovered_row
                    self._hovered_row = new_row
                    # Reset old row animation
                    if old >= 0:
                        self._reset_row(old)
                        self._lw.update(self._lw.model().index(old, 0))
                    # Start new row animation if text overflows
                    if new_row >= 0 and self._text_overflows(new_row):
                        self._row_state(new_row)  # ensure initialised
                        if not self._timer.isActive():
                            self._timer.start()
                    elif not self._timer.isActive():
                        pass  # nothing to animate
            elif event.type() == QEvent.Type.Leave:
                old = self._hovered_row
                self._hovered_row = -1
                if old >= 0:
                    self._reset_row(old)
                    self._lw.update(self._lw.model().index(old, 0))
                self._timer.stop()
        return super().eventFilter(obj, event)

    def _tick(self):
        row = self._hovered_row
        if row < 0 or not self._text_overflows(row):
            self._timer.stop()
            return

        item = self._lw.item(row)
        fm = self._lw.fontMetrics()
        avail = self._available_width()
        max_scroll = float(max(0, fm.horizontalAdvance(item.text()) - avail))

        state = self._row_state(row)

        if state == "START_DELAY":
            self._mq_ticks[row] += 1
            if self._mq_ticks[row] > 40:
                self._mq_state[row] = "SCROLL"
                self._mq_ticks[row] = 0
        elif state == "SCROLL":
            self._mq_pos[row] += 0.5
            if self._mq_pos[row] >= max_scroll:
                self._mq_pos[row] = max_scroll
                self._mq_state[row] = "END_DELAY"
                self._mq_ticks[row] = 0
        elif state == "END_DELAY":
            self._mq_ticks[row] += 1
            if self._mq_ticks[row] > 40:
                self._mq_state[row] = "FADEOUT"
                self._mq_ticks[row] = 0
        elif state == "FADEOUT":
            self._mq_alpha[row] -= 0.05
            if self._mq_alpha[row] <= 0.0:
                self._mq_alpha[row] = 0.0
                self._mq_pos[row] = 0.0
                self._mq_state[row] = "FADEIN"
        elif state == "FADEIN":
            self._mq_alpha[row] += 0.05
            if self._mq_alpha[row] >= 1.0:
                self._mq_alpha[row] = 1.0
                self._mq_state[row] = "START_DELAY"
                self._mq_ticks[row] = 0

        self._lw.update(self._lw.model().index(row, 0))

    def paint(self, painter, option, index):
        # Draw selection/hover background using the standard style
        from PySide6.QtWidgets import QStyleOptionViewItem
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.text = ""  # suppress native text drawing
        self._lw.style().drawControl(QStyle.CE_ItemViewItem, opt, painter, self._lw)

        row = index.row()
        item = self._lw.item(row)
        if item is None:
            return

        text = item.text()
        fm = painter.fontMetrics()
        avail = self._available_width()
        overflows = fm.horizontalAdvance(text) > avail

        # Determine text colour based on selection state
        is_selected = bool(option.state & QStyle.State_Selected)
        palette = option.palette
        color = palette.highlightedText().color() if is_selected else palette.windowText().color()

        is_animating = overflows and row == self._hovered_row
        if is_animating:
            alpha = self._mq_alpha.get(row, 1.0)
            if alpha < 1.0:
                color.setAlphaF(max(0.0, min(1.0, alpha)))

        painter.save()
        painter.setPen(color)
        painter.setFont(option.font)

        # Clip to the content rect to hide overflow
        text_rect = option.rect.adjusted(self._PADDING, 0, -self._PADDING, 0)
        painter.setClipRect(text_rect)

        offset = int(self._mq_pos.get(row, 0.0)) if is_animating else 0

        # Show elided text with "…" when overflowing but not yet scrolling,
        # and draw full text once the marquee animation has started moving.
        scrolling = is_animating and offset > 0
        if overflows and not scrolling:
            # Use Qt's built-in elider to clip+append "…"
            display_text = fm.elidedText(text, Qt.ElideRight, avail)
        else:
            display_text = text

        draw_rect = QRect(text_rect.left() - offset, text_rect.top(), 9999, text_rect.height())
        painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        return hint

class ToggleSwitch(QWidget):
    """
    iOS-style animated toggle switch inheriting from QWidget.
    """
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_checked = False

        # Internal animation states
        self._thumb_x = 2
        self._bg_color = QColor("#555555")
        
        # Animators
        self._anim_group = QPropertyAnimation(self, b"thumb_x")
        self._anim_group.setDuration(150)
        
        self._color_anim = QPropertyAnimation(self, b"bg_color")
        self._color_anim.setDuration(150)

    @Property(float)
    def thumb_x(self):
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, value):
        self._thumb_x = value
        self.update()
        
    @Property(QColor)
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = value
        self.update()

    def isChecked(self) -> bool:
        return self._is_checked

    def setChecked(self, checked: bool, animated: bool = True):
        if self._is_checked == checked:
            return
        self._is_checked = checked

        if animated:
            self._update_animation()
        else:
            self._bg_color = QColor(config.BTN_BG) if checked else QColor("#555555")
            self._thumb_x = self.width() - 20 if checked else 4
            self.update()
        
        self.toggled.emit(self._is_checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_checked = not self._is_checked
            self._update_animation()
            self.toggled.emit(self._is_checked)
        super().mouseReleaseEvent(event)

    def _update_animation(self):
        self._anim_group.stop()
        self._color_anim.stop()
        
        end_x = 18 if self._is_checked else 2
        end_color = QColor(config.BTN_BG) if self._is_checked else QColor("#555555")
        
        self._anim_group.setEndValue(float(end_x))
        self._color_anim.setEndValue(end_color)
        
        self._anim_group.start()
        self._color_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Draw background capsule
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_color)
        rect = QRect(0, 0, self.width(), self.height())
        p.drawRoundedRect(rect, 10, 10)
        
        # Draw white thumb
        p.setBrush(QColor("white"))
        thumb_rect = QRect(int(self._thumb_x), 2, 16, 16)
        p.drawEllipse(thumb_rect)


def _app_icon() -> QIcon:
    try:
        import json
        install_dir = os.path.dirname(os.path.abspath(__file__))
        is_win = platform.system() == "Windows"
        ext = ".ico" if is_win else ".png"

        icon_name = "default"
        settings_file = os.path.join(install_dir, "settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                icon_name = data.get('app_icon', 'default')

        icon_path = os.path.join(install_dir, "icons", f"icon_{icon_name}{ext}")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(install_dir, f"icon{ext}")

        if os.path.exists(icon_path):
            return QIcon(icon_path)
    except Exception:
        pass
    return QIcon()


def apply_dark_title_bar(window: QWidget):
    """Forces the native Windows title bar to dark mode."""
    if platform.system() == "Windows":
        try:
            import ctypes
            # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE in Windows 10/11
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

def _center_on_screen(widget: QWidget, w: int, h: int):
    """Center *widget* on the primary screen (or active monitor if detectable)."""
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width()  - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        widget.setGeometry(x, y, w, h)


def _txt(lang: str, key: str, **kwargs) -> str:
    """Return translation string for *key* in *lang*, falling back to 'en'."""
    text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def _qwidget_txt(self, key: str, **kwargs) -> str:
    w = self.window()
    if hasattr(w, 'txt') and w != self:
        return w.txt(key, **kwargs)
    return _txt("en", key, **kwargs)

QWidget.txt = _qwidget_txt


# ==========================================
# PHASE 7 CLASSES: WORKER, PROGRESS BAR, CANVAS
# ==========================================

class ShortcutCaptureButton(QPushButton):
    """
    Key-capture widget that visually matches standard inputs.
    - Idle:      dark background (#1e1e1e), subtle border (#3a3a3a)
    - Listening: same background, green border (#23a559), text = "..."
    - Conflict:  red border (#ed4245) while another button has the same sequence
    - Uses native keyPressEvent to reliably capture single keys and combos.
    - Focus loss reverts to previous sequence without clearing.
    """
    sequence_changed = Signal(str)

    _BASE_SS = """
        QPushButton {{
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid {border};
            border-radius: 3px;
            padding: 0px 8px;
            min-width: 80px;
            min-height: 26px;
            max-height: 26px;
            text-align: center;
            font-family: monospace;
            font-size: 10pt;
        }}
        QPushButton:hover {{
            background-color: #252525;
        }}
    """

    def __init__(self, current_sequence, display_only=False, parent=None):
        super().__init__(parent)
        self.current_seq = current_sequence or ""
        self.capturing = False
        self.display_only = display_only
        self._conflict = False

        self.setCursor(Qt.PointingHandCursor if not display_only else Qt.ArrowCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_style()
        self._update_label()

        if not display_only:
            self.clicked.connect(self.start_capture)

    def _apply_style(self):
        if self._conflict:
            border = "#ed4245"
        elif self.capturing:
            border = "#23a559"
        else:
            border = "#3a3a3a"
        self.setStyleSheet(self._BASE_SS.format(border=border))

    def _update_label(self):
        if self.display_only:
            self.setText(self.current_seq if self.current_seq else "—")
        else:
            if self.capturing:
                self.setText("...")
            else:
                self.setText(self.current_seq if self.current_seq else "(none)")

    def start_capture(self):
        if self.display_only:
            return
        self.capturing = True
        self._conflict = False
        self._apply_style()
        self._update_label()
        self.setFocus()

    def keyPressEvent(self, event):
        if not self.capturing:
            super().keyPressEvent(event)
            return

        key = event.key()
        # Ignore modifiers if pressed alone
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_unknown):
            return

        from PySide6.QtGui import QKeySequence
        # Qt6-safe way to get the combination of modifiers and key
        combo = event.keyCombination()
        seq = QKeySequence(combo).toString(QKeySequence.PortableText)
        
        self.current_seq = seq
        self.capturing = False
        self._apply_style()
        self._update_label()
        self.clearFocus()
        self.sequence_changed.emit(seq)

    def focusOutEvent(self, event):
        if self.capturing:
            # Revert to old sequence on cancel
            self.capturing = False
            self._apply_style()
            self._update_label()
        super().focusOutEvent(event)

    def get_sequence(self) -> str:
        return self.current_seq

    def set_sequence(self, seq: str):
        self.current_seq = seq or ""
        self._update_label()

    def set_conflict(self, conflict: bool):
        if self._conflict != conflict:
            self._conflict = conflict
            if not self.capturing:
                self._apply_style()




class SearchOverlayWidget(QFrame):
    def __init__(self, parent_widget, main_window):
        super().__init__(parent_widget)
        self.main_window = main_window
        from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QLabel, QPushButton, QGraphicsDropShadowEffect, QWidget, QFrame
        from PySide6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QRect, QSize
        from PySide6.QtGui import QColor, QAction, QIcon, QPixmap
        import os
        
        self.setObjectName("SearchOverlay")
        self.setProperty("expanded", False)
        self.setFixedHeight(36)
        
        self.setStyleSheet("""
            QFrame#SearchOverlay {
                background-color: transparent;
                border: none;
            }
            QFrame#SearchContainer {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QLineEdit, QLabel, QPushButton {
                background: transparent;
                border: none;
                color: #dddddd;
            }
            QLineEdit {
                padding: 4px;
            }
            QLabel {
                padding-right: 8px;
            }
            QPushButton {
                font-weight: bold;
                padding: 4px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #333333;
                border-radius: 4px;
            }
            QPushButton#BtnOpenSearch {
                border-radius: 6px;
                background-color: transparent;
            }
            QPushButton#BtnOpenSearch:hover {
                background-color: #333333;
            }
        """)
        
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 150))
        self.shadow.setEnabled(True)
        self.setGraphicsEffect(self.shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        _src_dir = os.path.dirname(os.path.abspath(__file__))
        _icon_path = os.path.join(_src_dir, "layout", "search.png")
        
        self.btn_open_search = QPushButton()
        self.btn_open_search.setObjectName("BtnOpenSearch")
        self.btn_open_search.setFixedSize(36, 36)
        
        pix = QPixmap(_icon_path)
        if not pix.isNull():
            self.btn_open_search.setIcon(QIcon(pix))
            self.btn_open_search.setIconSize(QSize(18, 18))
        else:
            self.btn_open_search.setText("🔍")
            
        self.btn_open_search.setToolTip(self.main_window.txt("search_placeholder"))
        self.btn_open_search.clicked.connect(self.toggle_search)
        
        self.search_container = QFrame()
        self.search_container.setObjectName("SearchContainer")
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(8, 6, 8, 6)
        search_layout.setSpacing(4)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.main_window.txt("search_placeholder"))
        
        self.counter_label = QLabel(self.main_window.txt("search_results_counter_empty"))
        
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setToolTip(self.main_window.txt("search_tooltip_prev"))
        self.btn_prev.setFixedSize(24, 24)
        
        self.btn_next = QPushButton("▼")
        self.btn_next.setToolTip(self.main_window.txt("search_tooltip_next"))
        self.btn_next.setFixedSize(24, 24)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip(self.main_window.txt("search_tooltip_close"))
        self.btn_close.setFixedSize(24, 24)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.counter_label)
        search_layout.addWidget(self.btn_prev)
        search_layout.addWidget(self.btn_next)
        search_layout.addWidget(self.btn_close)
        
        layout.addWidget(self.btn_open_search)
        layout.addWidget(self.search_container)
        
        self.search_container.hide()
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self._perform_search)
        
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_enter_pressed)
        
        self.btn_prev.clicked.connect(self.prev_match)
        self.btn_next.clicked.connect(self.next_match)
        self.btn_close.clicked.connect(self.close_search)
        
        self.matches = []
        self.current_index = -1
        self._anim = None
        
        if parent_widget:
            parent_widget.installEventFilter(self)
            
        self.show()
        QTimer.singleShot(0, self._reposition)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj == self.parentWidget() and event.type() == QEvent.Resize:
            self._reposition()
        return super().eventFilter(obj, event)

    def _on_text_changed(self, text):
        self.search_timer.start()

    def _on_enter_pressed(self):
        from PySide6.QtGui import QGuiApplication
        mods = QGuiApplication.keyboardModifiers()
        from PySide6.QtCore import Qt
        if mods & Qt.ShiftModifier:
            self.prev_match()
        else:
            self.next_match()

    def _perform_search(self):
        query = self.search_input.text().strip()
        self.matches.clear()
        self.current_index = -1
        
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or getattr(canvas, 'words_data', None) is None:
            self._update_counter()
            return
            
        # Clean flags
        for w in canvas.words_data:
            w.pop('_search_match', None)
            w.pop('_search_active', None)
            
        if not query:
            canvas.update()
            self._update_counter()
            return
            
        import re
        q_lower = query.lower()
        # Break query into words removing special chars for matching
        q_words = [re.sub(r'[^\w\s]', '', q) for q in q_lower.split() if q]
        if not q_words:
            # If all were special chars, just use the raw query tokens
            q_words = [q for q in q_lower.split() if q]
            if not q_words:
                canvas.update()
                self._update_counter()
                return
        
        # Build searchable list
        searchable = []
        for idx, w in enumerate(canvas.words_data):
            if w.get('type') == 'silence' or w.get('_hidden'):
                continue
            d_text = w.get('_display_text', w.get('text', ''))
            if not d_text.strip():
                continue
            clean_text = re.sub(r'[^\w\s]', '', d_text).lower()
            raw_text = d_text.lower()
            searchable.append((idx, clean_text, raw_text))
            
        # Sliding window
        q_len = len(q_words)
        for i in range(len(searchable) - q_len + 1):
            match = True
            matched_indices = []
            
            for j in range(q_len):
                idx, clean_text, raw_text = searchable[i + j]
                q_word = q_words[j]
                
                # Full match required for all except the last word
                if j < q_len - 1:
                    # check exact match on clean text or raw text
                    if q_word != clean_text and q_word != raw_text:
                        match = False
                        break
                else:
                    # Last word can be a partial (contains) match
                    if q_word not in clean_text and q_word not in raw_text:
                        match = False
                        break
                        
                matched_indices.append(idx)
                
            if match:
                self.matches.append(matched_indices)
                for idx in matched_indices:
                    canvas.words_data[idx]['_search_match'] = True

        if self.matches:
            self.current_index = 0
            self._apply_active_highlight()
            
        self._update_counter()
        canvas.update()

    def _apply_active_highlight(self):
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or not getattr(canvas, 'words_data', None): return
        
        for matched_indices in self.matches:
            for idx in matched_indices:
                canvas.words_data[idx].pop('_search_active', None)
            
        if 0 <= self.current_index < len(self.matches):
            active_indices = self.matches[self.current_index]
            for idx in active_indices:
                canvas.words_data[idx]['_search_active'] = True
            
            w = canvas.words_data[active_indices[0]]
            if '_rect' in w:
                rect = w['_rect']
                if hasattr(self.main_window, 'scroll_area'):
                    self.main_window.scroll_area.ensureVisible(rect.x(), rect.y(), 0, 50)
                
        canvas.update()

    def _update_counter(self):
        if not self.matches:
            self.counter_label.setText(self.main_window.txt("search_results_counter_empty"))
        else:
            self.counter_label.setText(f"{self.current_index + 1}/{len(self.matches)}")

    def next_match(self):
        if not self.matches: return
        self.current_index = (self.current_index + 1) % len(self.matches)
        self._apply_active_highlight()
        self._update_counter()

    def prev_match(self):
        if not self.matches: return
        self.current_index = (self.current_index - 1) % len(self.matches)
        self._apply_active_highlight()
        self._update_counter()

    def toggle_search(self):
        if self.property("expanded"):
            self.close_search()
        else:
            self.open_search()

    def close_search(self):
        if not self.property("expanded"): return
        self.search_input.clear()
        
        canvas = getattr(self.main_window, 'text_canvas', None)
        if canvas and canvas.words_data:
            for w in canvas.words_data:
                w.pop('_search_match', None)
                w.pop('_search_active', None)
            canvas.update()
            
        self.setProperty("expanded", False)
        
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        start_geom = self.geometry()
        self._anim.setStartValue(start_geom)
        
        parent_w = self.parentWidget().width()
        target_w = 36
        target_x = parent_w - target_w - 20
        self._anim.setEndValue(QRect(target_x, start_geom.y(), target_w, 36))
        
        def on_finished():
            self.search_container.hide()
            self.btn_open_search.show()
            self._reposition()
            
        self._anim.finished.connect(on_finished)
        self._anim.start()

    def open_search(self):
        if self.property("expanded"):
            self.search_input.setFocus()
            self.search_input.selectAll()
            return
            
        self.show()
        self.raise_()
            
        self.btn_open_search.hide()
        self.search_container.show()
        
        self.setProperty("expanded", True)
        
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.OutBack)
        
        start_geom = self.geometry()
        self._anim.setStartValue(start_geom)
        
        parent_w = self.parentWidget().width()
        target_w = 300
        target_x = parent_w - target_w - 20
        
        self._anim.setEndValue(QRect(target_x, start_geom.y(), target_w, 36))
        
        def on_finished():
            self.search_input.setFocus()
            self.search_input.selectAll()
            
        self._anim.finished.connect(on_finished)
        self._anim.start()

    def _reposition(self):
        try:
            if not self.parentWidget(): return
            parent_w = self.parentWidget().width()
            if self.property("expanded"):
                target_w = self.sizeHint().width()
                if target_w < 300: target_w = 300
                self.setGeometry(parent_w - target_w - 20, 20, target_w, 36)
            else:
                self.setGeometry(parent_w - 36 - 20, 20, 36, 36)
        except Exception as e:
            import osdoc
            osdoc.log_error(f"Search positioning error: {str(e)}")


class WorkerSignals(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object, object)
    error = Signal(str)

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
        from PySide6.QtGui import QPainter, QColor, QLinearGradient
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2b2b2b"))
        p.drawRoundedRect(rect, 4, 4)
        
        if self._indeterminate:
            pill_width = rect.width() * 0.25
            x_pos = self._indet_offset * (rect.width() + pill_width) - pill_width
            
            grad = QLinearGradient(x_pos, 0, x_pos + pill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.setClipRect(rect)
            p.drawRoundedRect(QRectF(x_pos, 0, pill_width, rect.height()), 4, 4)
        elif self._value > 0:
            fill_width = (self._value / 100.0) * rect.width()
            fill_rect = QRectF(0, 0, fill_width, rect.height())
            
            grad = QLinearGradient(0, 0, fill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, 4, 4)


class UndoManager:
    def __init__(self, main_window, canvas):
        self.main_window = main_window
        self.canvas = canvas
        self.undo_stack = []
        self.redo_stack = []
        self.max_size = 50

    def push(self, action):
        if not action or not action.get('changes'):
            return
        self.undo_stack.append(action)
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: return
        action = self.undo_stack.pop()
        redo_action = self._apply_action(action)
        self.redo_stack.append(redo_action)
        self.canvas.update()

    def redo(self):
        if not self.redo_stack: return
        action = self.redo_stack.pop()
        undo_action = self._apply_action(action)
        self.undo_stack.append(undo_action)
        self.canvas.update()

    def _apply_action(self, action):
        reverse_changes = {}
        id_map = {wo['id']: wo for wo in self.canvas.words_data}
        layer_engine = getattr(self.main_window, '_calculate_visual_layer', None)

        for wid, state in action['changes'].items():
            word_obj = id_map.get(wid)
            if not word_obj: continue

            # Save current state for reverse action
            reverse_changes[wid] = {
                'status': word_obj.get('status'),
                'manual_status': word_obj.get('manual_status'),
                'algo_status': word_obj.get('algo_status'),
                'is_auto': word_obj.get('is_auto'),
                'selected': word_obj.get('selected')
            }

            # Apply restored state
            word_obj['status'] = state.get('status')
            word_obj['manual_status'] = state.get('manual_status')
            if 'algo_status' in state:
                word_obj['algo_status'] = state.get('algo_status')
            word_obj['is_auto'] = state.get('is_auto')
            word_obj['selected'] = state.get('selected')
            word_obj['overlay_suppressed'] = True

            if layer_engine:
                layer_engine(word_obj)

        return {"type": "paint", "changes": reverse_changes}

class TranscriptionCanvas(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.words_data = []
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        self._last_dragged_id = -1
        # --- VIEWPORT CULLING: cache visible_words so paintEvent never recomputes it ---
        self._cached_visible_words = []

    def load_data(self, words_data):
        self.words_data = words_data
        self._calculate_layout()
        self.update()

    def _get_visible_words(self):
        """Returns a filtered list of only the words that should physically render.
        STAGE 9: Consecutive inaudible tokens are deduplicated in the view layer —
        only the first (...) of a run is shown; data remains intact in memory.
        Result is cached in self._cached_visible_words — do NOT call this inside paintEvent.
        """
        if not self.words_data: return []
        
        vis = []
        previous_was_inaudible = False

        for w in self.words_data:
            if w.get('type') == 'silence':
                continue
                
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'

            if is_inaudible:
                # Hide if the user toggled inaudible off
                if hasattr(self.main_window, 'tgl_show_inaudible') and not self.main_window.tgl_show_inaudible.isChecked():
                    previous_was_inaudible = True
                    continue
                # STAGE 9: Skip consecutive (...) clutter — show only the first of a run
                if previous_was_inaudible:
                    continue
                previous_was_inaudible = True
            else:
                previous_was_inaudible = False

            vis.append(w)
        return vis

    def _get_clip_rect(self):
        """Returns the QRect of the currently visible viewport area in canvas coordinates,
        expanded by a generous vertical buffer so words near the edge are never clipped.
        Falls back to the full canvas rect when no parent scroll area is found."""
        try:
            scroll = getattr(self.main_window, 'scroll_area', None)
            if scroll is not None:
                vbar = scroll.verticalScrollBar()
                hbar = scroll.horizontalScrollBar()
                y_off = vbar.value()
                x_off = hbar.value()
                vp = scroll.viewport()
                vp_h = vp.height()
                vp_w = vp.width()
                # 400px vertical buffer — ensures words on partially-visible lines render correctly
                BUFFER = 400
                return QRect(x_off, max(0, y_off - BUFFER), vp_w, vp_h + BUFFER * 2)
        except Exception:
            pass
        return self.rect()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._calculate_layout()

    def _calculate_layout(self):
        if not self.words_data:
            self._cached_visible_words = []
            return
        from PySide6.QtGui import QFontMetrics, QFont
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        pref_lh = prefs.get('editor_line_height', 8)
        view_mode = prefs.get('view_mode', 'continuous')
        
        is_rtl = False
        lang_pref = prefs.get('lang', 'Auto')
        
        rtl_codes = getattr(config, 'RTL_LANGUAGES', {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'})
        # Whisper auto-detect outputs English names
        rtl_english_names = {'arabic', 'hebrew', 'persian', 'urdu', 'yiddish', 'pashto', 'sindhi'}
        rtl_native_names = {config.SUPPORTED_LANGUAGES.get(code, code) for code in rtl_codes}
        
        if isinstance(lang_pref, str) and lang_pref.lower() != 'auto':
            if lang_pref in rtl_native_names or lang_pref.lower() in rtl_codes or lang_pref.lower() in rtl_english_names:
                is_rtl = True
        elif self.words_data:
            meta_lang = self.words_data[0].get('meta_language')
            if isinstance(meta_lang, str) and (meta_lang.lower() in rtl_codes or meta_lang.lower() in rtl_english_names):
                is_rtl = True
                
        active_font = QFont(pref_family, pref_size)
        metrics = QFontMetrics(active_font)
        ts_font = QFont(config.UI_FONT_NAME, max(8, pref_size - 2))
        ts_metrics = QFontMetrics(ts_font)
        
        space_w = metrics.horizontalAdvance(" ") + 2
        line_height = metrics.height() + pref_lh
        
        max_w = self.width() - 40
        x = max_w if is_rtl else 20
        y = 20
        
        # Rebuild the cached list once — paintEvent reads it directly, never recomputes
        visible_words = self._get_visible_words()
        self._cached_visible_words = visible_words
        
        for w in visible_words:
            # Clean previous iteration markers
            w.pop('_ts_rect', None)
            w.pop('_ts_text', None)
            w.pop('_separator_y', None)
            
            # Paragraph formatting based on Engine's Chunking
            if view_mode == 'segmented' and w.get('is_segment_start'):
                has_advanced = (x < max_w) if is_rtl else (x > 20)
                if has_advanced: 
                    y += line_height
                if y > 20: 
                    w['_separator_y'] = y + 10 # Store Y coordinate for the line
                    y += 20 # Gap between paragraphs
                x = max_w if is_rtl else 20
                
                # Generate Timestamp — format depends on 'timestamp_precise' setting
                secs = w.get('start', 0)
                if prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']):
                    m = int(secs // 60)
                    s = int(secs % 60)
                    ms = int((secs - int(secs)) * 1000)
                    ts_text = f"[{m:02d}:{s:02d}.{ms:03d}]"
                else:
                    total_s = int(round(secs))
                    m = total_s // 60
                    s = total_s % 60
                    ts_text = f"[{m:02d}:{s:02d}]"
                
                # Ensure timestamps stay isolated as LTR natively, using LTR Embedding, if in RTL mode.
                w['_ts_text'] = f"\u202A\u2068{ts_text}\u2069\u202C" if is_rtl else ts_text
                ts_w = ts_metrics.horizontalAdvance(w['_ts_text'])
                
                if is_rtl:
                    x -= ts_w
                    w['_ts_rect'] = QRect(x, y, ts_w, metrics.height() + 4)
                    x -= (space_w + 5)
                else:
                    w['_ts_rect'] = QRect(x, y, ts_w, metrics.height() + 4)
                    x += ts_w + space_w + 5
            
            # Standard word layout
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            raw_text = "(...)" if is_inaudible else w.get('text', '')
            
            # Use BiDirectional formatting to perfectly resolve neutral chars (e.g. dots, numbers) in RTL.
            # \u202B (RLE) sets the base direction to RTL.
            # \u2068 (FSI) isolates the word so LTR chunks like "[x34]" keep their brackets unmirrored.
            display_text = f"\u202B\u2068{raw_text}\u2069\u202C" if is_rtl else raw_text
            
            w['_display_text'] = display_text  # Store visual text
            
            word_w = metrics.horizontalAdvance(display_text)
            
            if is_rtl:
                if x - word_w < 20 and x < max_w:
                    x = max_w
                    y += line_height
                x -= word_w
                w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                x -= space_w
            else:
                if x + word_w > max_w and x > 20:
                    x = 20
                    y += line_height
                w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                x += word_w + space_w
            
        self.setMinimumHeight(y + line_height + 40)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient
        from PySide6.QtCore import QRectF, Qt
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        active_font = QFont(pref_family, pref_size)
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        color_map = {
            'bad': (QColor(config.WORD_BAD_BG), QColor(config.WORD_BAD_FG)),
            'repeat': (QColor(config.WORD_REPEAT_BG), QColor(config.WORD_REPEAT_FG)),
            'typo': (QColor(config.WORD_TYPO_BG), QColor(config.WORD_TYPO_FG)),
            'inaudible': (QColor(config.WORD_INAUDIBLE_BG), QColor(config.WORD_INAUDIBLE_FG))
        }
        
        def get_status(w):
            s = w.get('status')
            if s == 'inaudible' and hasattr(self.main_window, 'tgl_mark_inaudible') and not self.main_window.tgl_mark_inaudible.isChecked():
                if w.get('manual_status') != 'inaudible' or w.get('is_auto', False):
                    return None
            if s == 'typo' and hasattr(self.main_window, 'tgl_show_typos') and not self.main_window.tgl_show_typos.isChecked():
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    return None
            return s

        def get_color_tuple(status_val):
            if status_val in color_map: return color_map[status_val]
            if status_val and str(status_val).startswith("custom_"):
                c_name = status_val.split("_")[1]
                return (QColor(config.RESOLVE_COLORS_HEX.get(c_name, "#ffffff")), QColor("#ffffff"))
            return None
            
        def get_base_bg_fg(w):
            status = get_status(w)
            c_res = get_color_tuple(status)
            if c_res:
                bg, fg = c_res[0], c_res[1]
                if w.get('is_assembled_cut'):
                    # Interpolate sharply towards dark gray background to dim seamlessly
                    r = int(bg.red() * 0.2 + 30 * 0.8)
                    g = int(bg.green() * 0.2 + 30 * 0.8)
                    b = int(bg.blue() * 0.2 + 30 * 0.8)
                    bg = QColor(r, g, b, 255)
                return bg, fg, False
            return None, QColor(config.WORD_NORMAL_FG), True

        p.setPen(Qt.NoPen)

        # ── VIEWPORT CULLING ─────────────────────────────────────────────────────
        # Use the pre-computed cached list — never call _get_visible_words() here.
        # Build a smaller list of only those words whose _rect overlaps the visible
        # viewport region. All rendering passes below use this culled list.
        # The full cached list is kept so bridge-detection can peek at neighbours.
        all_visible = self._cached_visible_words
        clip = self._get_clip_rect()
        visible_words = [w for w in all_visible if '_rect' not in w or clip.intersects(w['_rect'])]
        # ────────────────────────────────────────────────────────────────────────

        # Oś Y separatorów (only in visible range)
        p.setPen(QPen(QColor("#333333"), 1))
        for w in visible_words:
            if '_separator_y' in w:
                sep_y = w['_separator_y']
                p.drawLine(20, sep_y, self.width() - 20, sep_y)
        p.setPen(Qt.NoPen)
        
        # 1. CZYSZCZENIE ŚMIECI PO POPRZEDNICH ITERACJACH
        # Only clear per-frame keys on the culled (visible) set — no reason to touch off-screen words
        for w in visible_words:
            for key in ['_search_brush', '_search_fg', '_is_bold']:
                w.pop(key, None)
            
        groups = []
        curr_group = []
        curr_state = None # Teraz będzie przechowywać tuple: (search_state, bg_color)
        
        for w in visible_words:
            if '_rect' not in w: continue
            
            # Pobieramy stan wyszukiwania i kolor tła dla danego słowa
            search_state = 'active' if w.get('_search_active') else ('match' if w.get('_search_match') else None)
            bg_color, _, _ = get_base_bg_fg(w)
            
            # Nasz nowy klucz grupowania to kombinacja stanu i koloru
            state = (search_state, bg_color) if search_state else None
            
            if state:
                # Grupujemy tylko jeśli: ten sam stan, ten sam kolor i ta sama linia Y
                if curr_state == state and curr_group and w['_rect'].y() == curr_group[-1]['_rect'].y():
                    curr_group.append(w)
                else:
                    if curr_group: groups.append((curr_group, curr_state[0])) # Zapisujemy tylko search_state do grup
                    curr_group = [w]
                    curr_state = state
            else:
                if curr_group: groups.append((curr_group, curr_state[0]))
                curr_group = []
                curr_state = None
        if curr_group: groups.append((curr_group, curr_state[0]))

        # Uproszczone wygaszanie kolorów
        def get_dimmed_center(color):
            h, s, v, a = color.getHsv()
            if h == -1: h = 0
            return QColor.fromHsv(h, s, max(0, int(v * 0.90)), a)

        def get_dimmed_edge(color):
            h, s, v, a = color.getHsv()
            if h == -1: h = 0
            return QColor.fromHsv(h, s, max(0, int(v * 0.70)), a) 

        from PySide6.QtGui import QRadialGradient, QBrush, QTransform
        
        active_underlines = []
        active_line_rect = None
        active_line_color = None

        for grp_words, state in groups:
            is_active = (state == 'active')
            bg, fg, is_neutral = get_base_bg_fg(grp_words[0])
            
            min_x = min(w['_rect'].left() for w in grp_words)
            max_x = max(w['_rect'].right() for w in grp_words)
            r0 = grp_words[0]['_rect']
            
            if is_active:
                # Obliczamy prostokąt obejmujący całą szerokość płótna
                active_line_rect = QRectF(0, r0.top() - 4, self.width(), r0.height() + 8)
                # Dynamiczny kolor linii
                if is_neutral:
                    active_line_color = QColor(255, 200, 50, 15) # Domyślny, delikatny żółty
                else:
                    active_line_color = QColor(bg.red(), bg.green(), bg.blue(), 18) # 7% przezroczystości natywnego koloru markera
            
            if is_neutral:
                # KLON VS CODE: Jeden zbiorczy prostokąt dla całej frazy (Brak Alpha Stacking!)
                p.setBrush(QColor(255, 140, 0, 120) if is_active else QColor(255, 200, 50, 60))
                p.drawRoundedRect(QRectF(min_x - 2, r0.top() - 1, (max_x - min_x) + 4, r0.height() + 2), 3, 3)
                for w in grp_words:
                    w['_search_fg'] = fg 
                    w['_is_bold'] = False
            else:
                # KOLOROWE TAGI: Wygaszony gradient
                center_x = (min_x + max_x) / 2.0
                center_y = r0.center().y()
                half_w = max(1.0, (max_x - min_x) / 2.0 + 6)
                half_h = max(1.0, r0.height() / 2.0 + 1)
                
                grad = QRadialGradient(0, 0, 1.0)
                h, s, v, a = bg.getHsv()
                if h == -1: h = 0
                grad.setColorAt(0.0, get_dimmed_center(bg))
                grad.setColorAt(1.0, get_dimmed_edge(bg))
                    
                brush = QBrush(grad)
                brush.setTransform(QTransform().translate(center_x, center_y).scale(half_w, half_h))
                
                for w in grp_words:
                    w['_search_brush'] = brush
                    w['_search_fg'] = QColor("#ffffff") if is_active else fg
                    w['_is_bold'] = is_active
                    
                if is_active:
                    active_underlines.append(QRectF(min_x, r0.bottom() - 3, max_x - min_x, 2))

        # PASS 0: Podświetlenie aktywnej linii
        if active_line_rect and active_line_color:
            p.setPen(Qt.NoPen)
            p.setBrush(active_line_color)
            p.drawRect(active_line_rect)

        # PASS 1: Base Backgrounds
        for w in visible_words:
            if '_rect' not in w: continue
            bg, _, _ = get_base_bg_fg(w)
            brush = w.get('_search_brush', bg)
            if brush:
                p.setBrush(brush)
                expand = 6 if '_search_brush' in w else 3
                p.drawRoundedRect(w['_rect'].adjusted(-expand, -1, expand, 1), 5, 5)

        # PASS 2: Sharp Bridges
        # Iterate over the FULL cached list so bridges between an off-screen word and
        # an on-screen word are never orphaned. We skip pairs where neither is in the
        # visible set (fast path via a set of ids).
        p.setPen(Qt.NoPen)
        visible_ids = {id(w) for w in visible_words}
        for i in range(len(all_visible) - 1):
            w1 = all_visible[i]
            w2 = all_visible[i+1]
            # Skip pairs where neither word is on screen
            if id(w1) not in visible_ids and id(w2) not in visible_ids:
                continue
            
            if '_rect' not in w1 or '_rect' not in w2: continue
            if w1['_rect'].y() != w2['_rect'].y(): continue 
            
            bg1, _, _ = get_base_bg_fg(w1)
            bg2, _, _ = get_base_bg_fg(w2)
            
            brush1 = w1.get('_search_brush', bg1)
            brush2 = w2.get('_search_brush', bg2)
            
            if brush1 and brush2:
                expand1 = 6 if '_search_brush' in w1 else 3
                expand2 = 6 if '_search_brush' in w2 else 3
                
                r1 = w1['_rect'].adjusted(-expand1, -1, expand1, 1)
                r2 = w2['_rect'].adjusted(-expand2, -1, expand2, 1)
                
                left_rect = r1 if r1.left() <= r2.left() else r2
                right_rect = r2 if r1.left() <= r2.left() else r1
                brush_left = brush1 if r1.left() <= r2.left() else brush2
                brush_right = brush2 if r1.left() <= r2.left() else brush1
                
                if brush1 == brush2:
                    p.setBrush(brush1)
                    bridge_rect = QRectF(left_rect.right() - 5, left_rect.y(), right_rect.left() - left_rect.right() + 10, left_rect.height())
                    if bridge_rect.width() > 0:
                        p.drawRect(bridge_rect)
                else:
                    p.setRenderHint(QPainter.Antialiasing, False)
                    gap_mid = int(left_rect.right() + (right_rect.left() - left_rect.right()) / 2.0)
                    
                    if right_rect.left() - left_rect.right() > 0:
                        p.setBrush(brush_left)
                        p.drawRect(QRectF(left_rect.right() - 5, left_rect.y(), gap_mid - left_rect.right() + 6, left_rect.height()))
                        p.setBrush(brush_right)
                        p.drawRect(QRectF(gap_mid, right_rect.y(), right_rect.left() - gap_mid + 5, right_rect.height()))
                        
                    p.setRenderHint(QPainter.Antialiasing, True)
                    
        # PASS 3: Timestamps & Text
        ts_font = QFont(config.UI_FONT_NAME, 10)
        ts_color = QColor("#666666")
        
        for w in visible_words:
            if '_ts_rect' in w:
                p.setFont(ts_font)
                p.setPen(ts_color)
                p.drawText(w['_ts_rect'], Qt.AlignLeft | Qt.AlignVCenter, w.get('_ts_text', ''))
                
            if '_rect' not in w: continue
            
            _, fg, _ = get_base_bg_fg(w)
            final_fg = w.get('_search_fg', fg)
            
            font = QFont(active_font)
            if w.get('_is_bold'):
                font.setBold(True)
                
            if w.get('is_assembled_cut'):
                final_fg = QColor("#5a5a5a")
                
            p.setFont(font)
            p.setPen(final_fg)
            p.drawText(w['_rect'], Qt.AlignCenter, w.get('_display_text', w.get('text', '')))
            
            if w.get('is_assembled_cut'):
                p.setPen(QPen(final_fg, 1.5))
                mid_y = int(w['_rect'].center().y()) + 1
                p.drawLine(int(w['_rect'].left()) + 4, mid_y, int(w['_rect'].right()) - 4, mid_y)
            
        # PASS 4: Active Underlines
        if active_underlines:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffffff"))
            for rect in active_underlines:
                p.drawRoundedRect(rect, 1, 1)

    def _handle_mouse(self, pos):
        visible_words = self._cached_visible_words
        for w in visible_words:
            if '_rect' in w and w['_rect'].adjusted(-3, -1, 3, 1).contains(pos):
                if w['id'] != self._last_dragged_id:
                    self._last_dragged_id = w['id']
                    checked_btn = self.main_window.marker_btn_group.checkedButton()
                    status = checked_btn.property('status_id') if checked_btn else None
                    if status == 'eraser': status = None
                    # rb_eraser → status stays None → propagate_status_change clears

                    # UNDO SUPPORT: Save old state before algorithms modifies words_data
                    if getattr(self, '_current_undo_action', None) is not None:
                        ids_to_save = [w['id']]
                        if w.get('is_inaudible'):
                            start = w['id']
                            while start > 0 and (self.words_data[start-1].get('is_inaudible') or self.words_data[start-1].get('type') == 'silence'): start -= 1
                            end = w['id']
                            while end < len(self.words_data)-1 and (self.words_data[end+1].get('is_inaudible') or self.words_data[end+1].get('type') == 'silence'): end += 1
                            ids_to_save = range(start, end + 1)
                        
                        changes = self._current_undo_action['changes']
                        for wid in ids_to_save:
                            if wid not in changes: # Save only the first state observed during this drag session
                                old_w = self.words_data[wid]
                                changes[wid] = {
                                    'status': old_w.get('status'),
                                    'manual_status': old_w.get('manual_status'),
                                    'algo_status': old_w.get('algo_status'),
                                    'is_auto': old_w.get('is_auto'),
                                    'selected': old_w.get('selected')
                                }

                    import algorithms
                    updates = algorithms.propagate_status_change(self.words_data, w['id'], status)

                    if updates:
                        # Build a fast O(1) lookup: id → word_obj
                        id_map = {wo['id']: wo for wo in self.words_data}

                        layer_engine = getattr(self.main_window, '_calculate_visual_layer', None)
                        for wid, _raw in updates:
                            word_obj = id_map.get(wid)
                            if word_obj is None:
                                continue
                            # Stamp overlay_suppressed so the algo overlay sinks
                            # below the user's manual paint until the next reload.
                            word_obj['overlay_suppressed'] = True
                            word_obj.pop('is_assembled_cut', None)
                            # Route through the Layer Engine — this is what actually
                            # writes word_obj['status'] to the correct final value.
                            if layer_engine:
                                layer_engine(word_obj)

                        self.update()
                break


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_dragged_id = -1
            self._current_undo_action = {"type": "paint", "changes": {}}
            self._handle_mouse(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._handle_mouse(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            action = getattr(self, '_current_undo_action', None)
            if action and action.get('changes'):
                if hasattr(self.main_window, 'undo_manager'):
                    self.main_window.undo_manager.push(action)
            self._current_undo_action = None

# ==========================================
# CSD — CLIENT-SIDE DECORATION CLASSES
# ==========================================

class AnimatedTitleButton(QPushButton):
    """
    Title-bar control button with a 150ms QVariantAnimation colour transition
    on hover. The close button uses a red hover (#c42b1c) to match Discord/
    Spotify conventions; all other buttons use HOVER from config.
    """

    def __init__(self, icon_path: str, tooltip_key: str, lang: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBarBtn")
        self._bg    = config.COLOR_TITLEBAR_BG
        self._hover = config.COLOR_TITLEBAR_HOVER
        self._press = "#3a3a3d"
        self._cur   = self._bg

        self.setFixedSize(32, 32)
        self.setToolTip(_txt(lang, tooltip_key))
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAutoFillBackground(False)
        self.setFlat(True)

        pix = QPixmap(icon_path)
        if not pix.isNull():
            self.setIcon(QIcon(pix))
            self.setIconSize(QSize(12, 12))

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self._on_color_changed)
        self._icon_path = icon_path

        self._update_style()

    def change_base_icon(self, new_icon_path):
        self._icon_path = new_icon_path
        self.setIcon(QIcon(new_icon_path))
        self.update()

    # ── internal ─────────────────────────────────────────────────────────────
    def _on_color_changed(self, color):
        self._cur = color.name() if hasattr(color, 'name') else str(color)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton#TitleBarBtn {{
                background-color: {self._cur}; border: none; border-radius: 0px;
                min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;
                margin: 0px; padding: 0px;
            }}
            QPushButton#TitleBarBtn:pressed {{ background-color: {self._press}; }}
        """)

    # ── events ────────────────────────────────────────────────────────────────
    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._hover))
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._bg))
        self._anim.start()
        super().leaveEvent(event)


class CustomTitleBar(QWidget):
    """
    Cross-platform custom title bar.

    macOS / Linux
    -------------
    • Dragging  → QWindow.startSystemMove()  (native OS behaviour)
    • Dbl-click → toggle maximized             (native OS behaviour)

    Windows
    -------
    Dragging and maximise toggles are handled by FramelessWindowMixin via
    WM_NCHITTEST returning HTCAPTION, so mousePressEvent / mouseDoubleClick
    are NO-OPs on Windows (the mixin intercepts them at the native level).
    """

    def __init__(self, window: QWidget, lang: str, parent=None):
        super().__init__(parent)
        self._win  = window
        self._lang = lang
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(32)
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#CustomTitleBar {{ background-color: {config.COLOR_TITLEBAR_BG}; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(0)

        # Small app-icon
        icon_lbl = QLabel()
        icon_pix = _app_icon().pixmap(QSize(14, 14))
        if not icon_pix.isNull():
            icon_lbl.setPixmap(icon_pix)
        icon_lbl.setFixedSize(18, 32)
        icon_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(icon_lbl)
        lay.addSpacing(6)

        # Title text
        self._lbl_title = QLabel(config.APP_NAME)
        self._full_title = config.APP_NAME
        self._lbl_title.setTextFormat(Qt.RichText)
        self._lbl_title.setStyleSheet(
            f"color: #999999; font-family: \"{config.UI_FONT_NAME}\"; "
            f"font-size: 9pt; background: transparent;"
        )
        lay.addWidget(self._lbl_title)
        lay.addStretch()

        # Chapter Dropdown (absolutely centered via resizeEvent)
        self.chapter_dropdown = TitleDropdown(['Original'], parent=self)
        self.chapter_dropdown.setFixedHeight(24)
        self.chapter_dropdown.setMinimumWidth(100)
        self.chapter_dropdown.hide() # Hidden until at least one assembly happens
        
        # Resolve icon directory (assets/layout/ sibling to src/)
        _src_dir    = os.path.dirname(os.path.abspath(__file__))
        _assets_dir = os.path.join(_src_dir, "layout")

        self.btn_min = AnimatedTitleButton(
            os.path.join(_assets_dir, "minimize.png"),
            "btn_minimize", lang, parent=self)
        self.btn_max = AnimatedTitleButton(
            os.path.join(_assets_dir, "maximize.png"),
            "btn_maximize", lang, parent=self)
        self.btn_close    = AnimatedTitleButton(
            os.path.join(_assets_dir, "exit.png"),
            "btn_close",    lang, parent=self)

        self.btn_min.clicked.connect(lambda: self._win.showMinimized())
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self._win.close)

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(btn)

    def set_title(self, text):
        from PySide6.QtGui import QFontMetrics
        self._full_title = text
        self._lbl_title.setText(text)
        self.update_elision()

    def update_elision(self):
        from PySide6.QtGui import QFontMetrics
        if hasattr(self, 'chapter_dropdown') and self.chapter_dropdown.isVisible():
            dw = self.chapter_dropdown.sizeHint().width()
            dx = (self.width() - dw) // 2
            # Leave a 20px gap before dropdown
            max_w = max(10, dx - self._lbl_title.x() - 20)
        else:
            # Dropdown hidden, can use up to right buttons
            btn_area = self.btn_min.width() * 3 + 24
            max_w = max(10, self.width() - self._lbl_title.x() - btn_area - 20)
            
        fm = QFontMetrics(self._lbl_title.font())
        elided = fm.elidedText(self._full_title, Qt.ElideRight, max_w)
        self._lbl_title.setText(elided)

    def update_dropdown_placement(self):
        if hasattr(self, 'chapter_dropdown') and self.chapter_dropdown.isVisible():
            cw = self.chapter_dropdown.sizeHint().width()
            ch = self.chapter_dropdown.height()
            self.chapter_dropdown.setGeometry((self.width() - cw) // 2, (self.height() - ch) // 2, cw, ch)
        self.update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dropdown_placement()

    def update_maximize_icon(self, is_maximized):
        icon_name = 'windowed.png' if is_maximized else 'maximize.png'
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'layout', icon_name)

        # Używamy nowej metody, która zabezpiecza ikonę przed resetem przez animację hover!
        self.btn_max.change_base_icon(icon_path)
        self.btn_max.setIconSize(QSize(14, 14))

    # ── helpers ───────────────────────────────────────────────────────────────
    def _toggle_maximize(self):
        # Zapis/odczyt stanu przed maksymalizacją, aby przycisk "windowed"
        # przywracał dokładny poprzedni rozmiar i położenie.
        win = self._win
        if not getattr(win, '_is_root', False):
            return
        if win.isMaximized():
            win.showNormal()
            saved_geo = getattr(win, '_pre_max_geometry', None)
            if saved_geo and saved_geo.isValid():
                win.setGeometry(saved_geo)
        else:
            win._pre_max_geometry = win.geometry()  # zapamiętaj przed max
            win.showMaximized()

    def mousePressEvent(self, event):
        # Windows root window: OS handles dragging via HTCAPTION in nativeEvent.
        if getattr(self._win, '_is_win', False) and getattr(self._win, '_is_root', False):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._click_pos = event.position().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self._win, '_is_win', False) and getattr(self._win, '_is_root', False):
            event.ignore()
            return

        if not getattr(self, '_is_dragging', False):
            super().mouseMoveEvent(event)
            return

        win = self.window()
        gp = event.globalPosition().toPoint()
        frames = getattr(self, '_x11_detach_frames', 0)

        # Filtr drgań (tylko na start dragu)
        if frames == 0 and (event.position().toPoint() - self._click_pos).manhattanLength() < 5:
            return

        if win.isMaximized() and frames == 0:
            is_wayland = getattr(self._win, '_is_wayland', False)
            if is_wayland:
                self._is_dragging = False
                win.showNormal()
                win.resize(580, 670)
                if hasattr(win, 'windowHandle') and win.windowHandle():
                    win.windowHandle().startSystemMove()
                event.accept()
                return
            else:
                # X11 OUT OF THE BOX FIX:
                # Opóźniamy natywny drag o 5 ramek ruchu myszki (kilkadziesiąt milisekund).
                # Pozwala to serwerowi X11 na całkowite zastosowanie obkurczenia 
                # (showNormal + setGeometry), więc gdy w końcu wywołamy startSystemMove(), 
                # Menedżer Okien (KWin/Mutter) policzy offset chwycenia perfekcyjnie pod kursorem.
                
                ratio = self._click_pos.x() / max(1, self.width())
                saved_geo = getattr(win, '_pre_max_geometry', None)
                new_w = saved_geo.width() if saved_geo and saved_geo.isValid() else 580
                new_h = saved_geo.height() if saved_geo and saved_geo.isValid() else 670
                
                offset_x = int(new_w * ratio)
                offset_y = min(self._click_pos.y(), self.height())
                
                new_x = gp.x() - offset_x
                new_y = gp.y() - offset_y

                win.showNormal()
                win.setGeometry(new_x, new_y, new_w, new_h)

                self._x11_detach_frames = 5
                self._cached_offset_x = offset_x
                self._cached_offset_y = offset_y
                # Utrzymujemy _is_dragging = True aby wejść tu znowu jak ruszysz myszką po odpięciu
                event.accept()
                return

        if frames > 0:
            self._x11_detach_frames -= 1
            
            # W trakcie "kwarantanny" X11 prowadzimy okno ręcznie, 
            # by idealnie trzymało się i nie uciekło z dłoni
            new_x = gp.x() - self._cached_offset_x
            new_y = gp.y() - self._cached_offset_y
            win.move(new_x, new_y)

            if self._x11_detach_frames == 0:
                # Oczekiwany moment! Serwer X11 jest ostatecznie wyzerowany i świadomy rozmiaru 580px.
                # Odpalamy native Aero Snap Drag — Menadżer załapie okno perfekcyjnie tutaj.
                self._is_dragging = False
                if hasattr(win, 'windowHandle') and win.windowHandle():
                    win.windowHandle().startSystemMove()

            event.accept()
            return

        self._is_dragging = False
        if hasattr(win, 'windowHandle') and win.windowHandle():
            win.windowHandle().startSystemMove()

        event.accept()

    def mouseReleaseEvent(self, event):
        if getattr(self._win, '_is_win', False) and getattr(self._win, '_is_root', False):
            event.ignore()
            return
        self._is_dragging = False
        self._x11_detach_frames = 0
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # On Windows root it's handled by OS double-click on HTCAPTION.
            if getattr(self._win, '_is_win', False) and getattr(self._win, '_is_root', False):
                event.ignore()
                return
            self._toggle_maximize()
        super().mouseDoubleClickEvent(event)




class ResizeGrip(QWidget):
    def __init__(self, parent, edge):
        super().__init__(parent)
        self.edge = edge
        self.setStyleSheet("background: transparent;")
        
        if self.edge == Qt.TopEdge or self.edge == Qt.BottomEdge: 
            self.setCursor(Qt.SizeVerCursor)
        elif self.edge == Qt.LeftEdge or self.edge == Qt.RightEdge: 
            self.setCursor(Qt.SizeHorCursor)
        elif self.edge == (Qt.TopEdge | Qt.LeftEdge) or self.edge == (Qt.BottomEdge | Qt.RightEdge): 
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edge == (Qt.TopEdge | Qt.RightEdge) or self.edge == (Qt.BottomEdge | Qt.LeftEdge): 
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().windowHandle().startSystemResize(self.edge)
            event.accept()

class FramelessWindowMixin:
    """
    Mixin that turns any QMainWindow / QDialog into a frameless, CSD window.

    Usage
    -----
        class MyWindow(FramelessWindowMixin, QMainWindow):
            def __init__(self):
                super().__init__()
                self.frameless_init(is_popup=False)

    Provides
    --------
    • frameless_init()      — sets flags, creates shadow for popups
    • moveEvent / resizeEvent — Smart Corners (per-corner border-radius)
    • nativeEvent           — WM_NCHITTEST map (Windows only):
          resize borders → HT* constants
          title bar area → HTCAPTION  (enables Aero Snap, system animations)
          close/min/max buttons → HTCLIENT
          rest of window → HTCLIENT
    """

    _RESIZE_BORDER = 5   # px — hit-test sensitivity at window edges

    # ── public API ────────────────────────────────────────────────────────────
    def frameless_init(self, is_popup: bool = False):
        """Call once, right after super().__init__()."""
        import platform
        from PySide6.QtGui import QGuiApplication
        self._is_win = platform.system() == "Windows"
        self._is_mac = platform.system() == "Darwin"
        self._is_wayland = QGuiApplication.platformName() == 'wayland'
        # Sprawdzamy, czy to jest główne okno (root)
        self._is_root = self.__class__.__name__ == "BadWordsGUI"

        if self._is_win:
            if self._is_root:
                # Root window: uses a native HWND frame so DWM can handle Aero Snap,
                # shadows, and the snap-layout preview.
                self.setWindowFlags(
                    self.windowFlags()
                    | Qt.Window
                    | Qt.CustomizeWindowHint
                    | Qt.WindowMinMaxButtonsHint
                )
            else:
                # Popups are genuinely frameless — translucency is safe here.
                self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
                self.setAttribute(Qt.WA_TranslucentBackground, True)
        elif self._is_mac and self._is_root:
            # macOS root window: use native title bar with traffic lights.
            # This gives us the green fullscreen button which hides Dock + Menu Bar.
            # The custom CSD title bar widget is hidden in BadWordsGUI.__init__.
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinMaxButtonsHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowFullscreenButtonHint
            )
        else:
            # Linux and macOS popups: fully frameless + translucent (rounded corners via QSS).
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._is_popup = is_popup

        if not self._is_win and not (self._is_mac and self._is_root):
            self._setup_grips()

    def _get_root_frame(self):
        """Return the topmost styled QFrame to apply border-radius to."""
        return getattr(self, 'inner_frame', getattr(self, '_root_frame', None))

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            self._refresh_max_state()
            # Gdy okno zmienia stan (max ↔ normal), wymuszamy na DWM natychmiastowe
            # przeliczenie metryki NC przez SWP_FRAMECHANGED — eliminuje to białą ramkę
            # która mogłaby się pojawić w pierwszej klatce po zmianie stanu.
            if getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
                try:
                    import ctypes
                    hwnd = int(self.winId())
                    if hwnd:
                        # SWP_FRAMECHANGED(0x20)|SWP_NOZORDER(0x04)|SWP_NOMOVE(0x02)|SWP_NOSIZE(0x01)
                        ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0027)
                except Exception:
                    pass
        super().changeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        # Wynosimy gripy na wierzch dopiero po zbudowaniu i wyrenderowaniu całego UI (CentralWidget)
        if hasattr(self, '_grips'):
            for grip in self._grips:
                grip.raise_()

    def _refresh_max_state(self):
        is_max = self.isMaximized()

        # Szukamy paska pod obiema nazwami (główne okno: _title_bar, dialogi: _tb)
        title_bar = getattr(self, '_title_bar', getattr(self, '_tb', None))
        if title_bar and hasattr(title_bar, 'update_maximize_icon'):
            title_bar.update_maximize_icon(is_max)

        # Gdy okno pokrywa cały ekran, border-radius: 12px powoduje wizualne
        # "przycinanie" narożników. Zerujemy promień przy maksymalizacji i
        # przywracamy go przy powrocie do trybu okienkowego.
        # Dotyczy TYLKO głównego okna — popupy nie mogą być maksymalizowane.
        if getattr(self, '_is_root', False):
            root_frame = self._get_root_frame()
            if root_frame:
                radius = '0px' if is_max else '12px'
                root_frame.setStyleSheet(
                    f"QFrame#{root_frame.objectName()} {{"
                    f" background-color: {config.BG_COLOR};"
                    f" border-radius: {radius}; }}"
                )

    def _setup_grips(self):
        self._grips = []
        edges = [
            Qt.TopEdge, Qt.BottomEdge, Qt.LeftEdge, Qt.RightEdge, 
            Qt.TopEdge | Qt.LeftEdge, 
            Qt.TopEdge | Qt.RightEdge, 
            Qt.BottomEdge | Qt.LeftEdge, 
            Qt.BottomEdge | Qt.RightEdge
        ]
        for edge in edges:
            grip = ResizeGrip(self, edge)
            self._grips.append(grip)
            grip.raise_() # <-- ZMIANA: Podnosimy Z-index tylko raz przy tworzeniu

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_grips()

    def _update_grips(self):
        if not hasattr(self, '_grips'): return

        is_max = self.isMaximized()

        b = 6 
        w, h = self.width(), self.height()

        for grip in self._grips:
            if is_max:
                if not grip.isHidden(): grip.hide()
                continue
            else:
                if grip.isHidden(): grip.show()

            if grip.edge == Qt.TopEdge: grip.setGeometry(b, 0, w - 2*b, b)
            elif grip.edge == Qt.BottomEdge: grip.setGeometry(b, h - b, w - 2*b, b)
            elif grip.edge == Qt.LeftEdge: grip.setGeometry(0, b, b, h - 2*b)
            elif grip.edge == Qt.RightEdge: grip.setGeometry(w - b, b, b, h - 2*b)
            elif grip.edge == (Qt.TopEdge | Qt.LeftEdge): grip.setGeometry(0, 0, b, b)
            elif grip.edge == (Qt.TopEdge | Qt.RightEdge): grip.setGeometry(w - b, 0, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.LeftEdge): grip.setGeometry(0, h - b, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.RightEdge): grip.setGeometry(w - b, h - b, b, b)

    # ── Windows WM_NCHITTEST ──────────────────────────────────────────────────
    def nativeEvent(self, eventType, message):
        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False) or eventType != b"windows_generic_MSG":
            return super().nativeEvent(eventType, message)

        import ctypes
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))

        # ── WM_NCCALCSIZE (0x0083) ────────────────────────────────────────────
        # Returning 0 with wParam=True removes the entire native NC area so
        # Windows draws nothing there — our custom title bar owns that space.
        # When maximized, Windows adds a hidden "maximized border" (SM_CXFRAME +
        # SM_CXPADDEDBORDER) that would otherwise push the client area inward.
        # We compensate by shrinking the rect on all four sides. Left/right/bottom
        # corrections prevent edge clipping on multi-monitor setups.
        if msg.message == 0x0083:  # WM_NCCALCSIZE
            if msg.wParam and self.isMaximized():
                user32 = ctypes.windll.user32
                # SM_CXFRAME(32) + SM_CXPADDEDBORDER(92) = total hidden border
                border = user32.GetSystemMetrics(32) + user32.GetSystemMetrics(92)
                params = ctypes.cast(msg.lParam, ctypes.POINTER(wintypes.RECT))
                params[0].left   += border
                params[0].top    += border
                params[0].right  -= border
                params[0].bottom -= border
            return True, 0

        # ── WM_ENTERSIZEMOVE (0x0231) ─────────────────────────────────────────
        # Fires at the start of every drag or resize. Forces DWM to flush our
        # WM_NCCALCSIZE=0 result before NC repaint — eliminates white flash.
        if msg.message == 0x0231:  # WM_ENTERSIZEMOVE
            hwnd = int(self.winId())
            if hwnd:
                # SWP_FRAMECHANGED(0x20)|SWP_NOZORDER(0x04)|SWP_NOMOVE(0x02)|SWP_NOSIZE(0x01)
                ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0027)
            return super().nativeEvent(eventType, message)  # don't consume

        # ── WM_NCACTIVATE (0x0086) ────────────────────────────────────────────
        # The default handler repaints the NC area on activate/deactivate,
        # which produces a white flash at the top of the window.
        # Passing wParam=True and lParam=-1 tells Windows to suppress NC
        # repainting entirely and keeps our custom title bar pixel-perfect.
        if msg.message == 0x0086:  # WM_NCACTIVATE
            hwnd = int(self.winId())
            ctypes.windll.user32.DefWindowProcW(
                hwnd,
                0x0086,          # WM_NCACTIVATE
                msg.wParam,      # keep active/inactive state
                ctypes.c_long(-1)  # lParam = -1 → skip NC repaint
            )
            return True, 1

        # ── WM_NCHITTEST (0x0084) ─────────────────────────────────────────────
        # Map pixel positions to hit-test codes so Windows can drive:
        #   • resize (HTLEFT / HTRIGHT / …)
        #   • native drag + Aero Snap (HTCAPTION)
        #   • button clicks stay in client space (HTCLIENT)
        if msg.message == 0x0084:  # WM_NCHITTEST
            x = msg.lParam & 0xFFFF
            if x & 0x8000: x -= 0x10000
            y = (msg.lParam >> 16) & 0xFFFF
            if y & 0x8000: y -= 0x10000

            global_pos = QPoint(x, y)
            pos = self.mapFromGlobal(global_pos)
            w, h = self.width(), self.height()
            b = self._RESIZE_BORDER  # consistent with _update_grips

            # Resize border hit-tests (disabled when maximized)
            if not self.isMaximized():
                lx, rx = pos.x() < b, pos.x() > w - b
                ty, by = pos.y() < b, pos.y() > h - b
                if ty and lx: return True, 13  # HTTOPLEFT
                if ty and rx: return True, 14  # HTTOPRIGHT
                if by and lx: return True, 16  # HTBOTTOMLEFT
                if by and rx: return True, 17  # HTBOTTOMRIGHT
                if lx:        return True, 10  # HTLEFT
                if rx:        return True, 11  # HTRIGHT
                if ty:        return True, 12  # HTTOP
                if by:        return True, 15  # HTBOTTOM

            # Title-bar hit-test — HTCAPTION gives native drag + snap + animations.
            # Buttons stay as HTCLIENT so Qt can process their click events.
            _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
            if _tb:
                tb_pos = _tb.mapFromGlobal(global_pos)
                if _tb.rect().contains(tb_pos):
                    child = _tb.childAt(tb_pos)
                    if not child or not child.inherits("QPushButton"):
                        return True, 2  # HTCAPTION

            return True, 1  # HTCLIENT

        return super().nativeEvent(eventType, message)


# ==========================================
# CLASS 1: SPLASH SCREEN
# ==========================================

class SplashScreen(FramelessWindowMixin, QDialog):
    """
    Frameless, dark loading window displayed while engine/api are initializing.
    Shows an animated "loading…" label (0-3 cycling dots at 400 ms).
    Closed by main.py once InitThread emits `loaded`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        W, H = 300, 150
        self.setFixedSize(W + 30, H + 30)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        layout = QVBoxLayout(self.inner_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout = QVBoxLayout()
        layout.addLayout(content_layout)

        # --- QSS styling ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
            }}
            QLabel#title {{
                color: #ffffff;
                font-size: 18pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#loading {{
                color: {config.NOTE_COL};
                font-size: 12pt;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
        """)

        # --- Layout ---
        content_layout.setContentsMargins(20, 30, 20, 20)
        content_layout.setSpacing(8)
        content_layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel("BadWords", self.inner_frame)
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(lbl_title)

        self._lbl_loading = QLabel(self.txt("lbl_loading"), self.inner_frame)
        self._lbl_loading.setObjectName("loading")
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self._lbl_loading)

        # --- Icon ---
        self.setWindowIcon(_app_icon())

        # --- Center on screen ---
        _center_on_screen(self, W, H)

        # --- Dot animation ---
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self):
        """Cycle the trailing dots: loading → loading. → loading.. → loading..."""
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText(f"loading{dots}")
        self._dot_count += 1

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ==========================================
# CLASS 2: TELEMETRY POPUP
# ==========================================

class _LangPickerDialog(QDialog):
    """
    Lightweight language-selection popup (replaces the Tkinter ScrollableMenu).
    Shows all UI languages sorteed alphabetically; emits the selected code.
    Rebuilt as a proper PySide6 dialog — a full ScrollableMenu Port is Stage 2+.
    """
    lang_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFixedWidth(180)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.MENU_BG};
                border: 1px solid #1a1a1a;
            }}
            QListWidget {{
                background-color: {config.MENU_BG};
                color: {config.MENU_FG};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 11pt;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 5px 8px;
            }}
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover, QListWidget::item:selected {{
                background-color: #4a4e56;
                color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: {config.MENU_BG};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.SCROLL_FG};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.SCROLL_ACTIVE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._list)

        # Populate sorted language list
        entries = sorted(
            [(data.get("name", code.upper()), code) for code, data in config.TRANS.items()],
            key=lambda x: x[0]
        )
        for name, code in entries:
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.UserRole, code)
            self._list.addItem(item)

        visible_rows = min(len(entries), 6)
        row_h = 28
        self.setFixedHeight(visible_rows * row_h + 4)

        self._list.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem):
        code = item.data(Qt.UserRole)
        self.lang_selected.emit(code)
        self.close()


class TelemetryPopup(FramelessWindowMixin, QDialog):
    """
    Modal dialog asking the user for analytics consent.

    Skip condition: if engine.os_doc.get_telemetry_pref("telemetry_opt_in")
    is not None, caller should not show this dialog.

    On "I Agree":
        - Saves telemetry_opt_in = True
        - Saves telemetry_allow_geo = <checkbox state>
        - Calls engine.send_telemetry_ping("app_started")

    On "No thanks" (or Escape / close):
        - Saves telemetry_opt_in = False

    Language changes are persisted to pref.json in real time via
    engine.save_preferences({"gui_lang": code}).
    """

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._lang_picker = None

        # Load current language from preferences
        prefs = engine.load_preferences() or {}
        self._lang = prefs.get("gui_lang", "en")
        if self._lang not in config.TRANS:
            self._lang = "en"

        # --- Window setup ---
        self.frameless_init(is_popup=True)
        # WindowModal blocks only the parent — avoids ApplicationModal event-queue
        # pileup where pending main-window signals fire all at once after exec() returns.
        # WindowStaysOnTopHint is redundant with a modal dialog and can cause DWM issues.
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowIcon(_app_icon())

        # --- Root QSS (window is transparent; styling lives on inner_frame) ---
        self.setStyleSheet(f"""
            TelemetryPopup {{ background-color: transparent; }}
            QFrame#MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
                border-radius: 8px;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: 14pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_msg {{
                color: {config.FG_COLOR};
                font-size: 11pt;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 11pt;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 2px 4px;
            }}
            QPushButton#btn_lang:hover {{
                color: #ffffff;
            }}
            QPushButton#btn_yes {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                font-weight: bold;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }}
            QPushButton#btn_yes:hover {{
                background-color: {config.BTN_ACTIVE};
            }}
            QPushButton#btn_no {{
                background-color: {config.CANCEL_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                font-weight: bold;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }}
            QPushButton#btn_no:hover {{
                background-color: {config.CANCEL_ACTIVE};
            }}
            QCheckBox {{
                color: #aaaaaa;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #1a1a1a;
            }}
            QCheckBox::indicator:checked {{
                background-color: {config.BTN_BG};
                border-color: {config.BTN_BG};
            }}
        """)

        # --- Outer wrapper (transparent, holds shadow) ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.inner_frame.setGraphicsEffect(shadow)

        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Custom title bar ---
        self._tb = CustomTitleBar(self, self._lang, parent=self.inner_frame)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(self._t("title_telemetry"))
        root_layout.addWidget(self._tb)

        # --- Content area ---
        container = QWidget(self.inner_frame)
        container.setObjectName("container")
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(0)
        root_layout.addWidget(container)

        # Header row (title + language button)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._lbl_title = QLabel("", container)
        self._lbl_title.setObjectName("lbl_title")
        header.addWidget(self._lbl_title, 1)

        self._btn_lang = QPushButton("", container)
        self._btn_lang.setObjectName("btn_lang")
        self._btn_lang.setCursor(Qt.PointingHandCursor)
        self._btn_lang.setFocusPolicy(Qt.NoFocus)
        self._btn_lang.clicked.connect(self._show_lang_picker)
        header.addWidget(self._btn_lang)

        content_layout.addLayout(header)
        content_layout.addSpacing(15)

        # Message label
        self._lbl_msg = QLabel("", container)
        self._lbl_msg.setObjectName("lbl_msg")
        self._lbl_msg.setWordWrap(True)
        self._lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(self._lbl_msg)
        content_layout.addSpacing(10)

        # Geo checkbox
        self._chk_geo = QCheckBox("", container)
        self._chk_geo.setChecked(True)
        content_layout.addWidget(self._chk_geo)
        content_layout.addSpacing(20)

        # Buttons row (No | Yes)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        self._btn_no  = QPushButton("", container)
        self._btn_no.setObjectName("btn_no")
        self._btn_no.setCursor(Qt.PointingHandCursor)
        self._btn_no.clicked.connect(self._on_no)
        btn_row.addWidget(self._btn_no)
        btn_row.addSpacing(10)

        self._btn_yes = QPushButton("", container)
        self._btn_yes.setObjectName("btn_yes")
        self._btn_yes.setCursor(Qt.PointingHandCursor)
        self._btn_yes.clicked.connect(self._on_yes)
        btn_row.addWidget(self._btn_yes)
        btn_row.addStretch()

        content_layout.addLayout(btn_row)

        # --- Populate text and size ---
        self._refresh_texts()


    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _t(self, key: str, **kwargs) -> str:
        return _txt(self._lang, key, **kwargs)

    def _refresh_texts(self):
        """Update all translatable labels and re-size the dialog."""
        self.setWindowTitle(self._t("title_telemetry"))
        self._lbl_title.setText(self._t("title_telemetry"))
        self._lbl_msg.setText(self._t("msg_telemetry"))
        self._btn_yes.setText(self._t("btn_telemetry_yes"))
        self._btn_no.setText(self._t("btn_telemetry_no"))
        self._btn_lang.setText(self._lang.upper())
        self._chk_geo.setText(self._t("chk_telemetry_geo"))
        # Keep title bar in sync when language changes
        if hasattr(self, '_tb') and hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(self._t("title_telemetry"))

        # ── Size calculation ──────────────────────────────────────────────
        # The dialog uses a shadow outer wrapper (15px each side) and a content
        # area with 20px horizontal padding each side. Total horizontal overhead:
        # 15 + 15 + 20 + 20 = 70px.  We must tell the word-wrapped label its
        # exact available width BEFORE calling adjustSize(), otherwise Qt
        # computes height without accounting for wrapping and the bottom text
        # gets clipped.
        DIALOG_W      = 580
        HORIZ_MARGINS = 15 + 15 + 20 + 20   # shadow margins + content margins
        self._lbl_msg.setMaximumWidth(DIALOG_W - HORIZ_MARGINS)

        # Now constrain the dialog width and let height grow freely
        self.setFixedWidth(DIALOG_W)
        self.adjustSize()    # height is now computed correctly with wrapped text
        h = max(self.sizeHint().height(), self.height())
        _center_on_screen(self, DIALOG_W, h)


    def _show_lang_picker(self):
        """Open a floating language picker anchored below the lang button."""
        try:
            if self._lang_picker and self._lang_picker.isVisible():
                self._lang_picker.close()
                return
        except RuntimeError:
            self._lang_picker = None # Object was deleted by Qt

        self._lang_picker = _LangPickerDialog(self)
        self._lang_picker.lang_selected.connect(self._on_lang_selected)

        # Position: bottom-right of the language button
        btn_global = self._btn_lang.mapToGlobal(
            self._btn_lang.rect().bottomRight()
        )
        picker_w = self._lang_picker.width()
        self._lang_picker.move(btn_global.x() - picker_w, btn_global.y())
        self._lang_picker.show()

    def _on_lang_selected(self, code: str):
        """Handle language selection: persist and refresh UI."""
        if code == self._lang:
            return
        self._lang = code
        # Persist immediately so the main window picks it up
        self._engine.save_preferences({"gui_lang": code})
        self._refresh_texts()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_yes(self):
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in",   True)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", self._chk_geo.isChecked())
        self._engine.send_telemetry_ping("app_started")
        self.accept()

    def _on_no(self):
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in", False)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", False)
        self.accept()

    def keyPressEvent(self, event):
        """Escape → same as 'No thanks'."""
        if event.key() == Qt.Key_Escape:
            self._on_no()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Window closed without pressing a button → treat as 'No'."""
        self._on_no()
        super().closeEvent(event)


# ==========================================
# CLASS 3a: TOOLTIPS & SIDEBAR WIDGETS
# ==========================================

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

class GlobalAppFilter(QObject):
    """Intercepts native QEvent.ToolTip globally and handles global input focus management."""
    def __init__(self, shared_tooltip):
        super().__init__()
        self.shared_tooltip = shared_tooltip
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._do_show)
        self.current_text = ""
        self.current_pos = None
        self.active_widget = None

    def eventFilter(self, obj, event):
        # 1. Global Focus Management: clear focus from QLineEdit on click anywhere outside
        if event.type() == QEvent.MouseButtonPress:
            focused = QApplication.focusWidget()
            if isinstance(focused, QLineEdit):
                global_pos = QCursor.pos()
                focused_global_rect = QRect(focused.mapToGlobal(QPoint(0, 0)), focused.size())
                if not focused_global_rect.contains(global_pos):
                    focused.clearFocus()
                    
        # 2. Enter/Return removes focus from QLineEdit
        if event.type() == QEvent.KeyPress and isinstance(obj, QLineEdit) and obj.hasFocus():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                obj.clearFocus()

        # 3. Tooltip handling
        if event.type() == QEvent.ToolTip:
            if isinstance(obj, QWidget):
                text = obj.toolTip()
                if text:
                    self.current_text = text
                    self.current_pos = event.globalPos()
                    self.active_widget = obj
                    self.tooltip_timer.start(500)
                    return True # Stop native tooltip
        elif event.type() in (QEvent.Leave, QEvent.Hide, QEvent.MouseButtonPress, QEvent.WindowDeactivate):
            if obj == self.active_widget or self.active_widget is None:
                self.tooltip_timer.stop()
                if hasattr(self, 'shared_tooltip'):
                    self.shared_tooltip.hide()
                self.active_widget = None
        return False

    def _do_show(self):
        if self.current_text and self.active_widget:
            self.shared_tooltip.show_global(self.current_text, self.current_pos)

class SidebarButton(QPushButton):
    """
    Static sidebar item with a fixed 40x40 size and VS Code style static tooltip.
    Now draggable to allow panel repositioning.
    """
    def __init__(self, icon_text: str, label_text: str, activity_id: str, tooltip_widget=None, is_right_side: bool = False, is_draggable: bool = True, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setText(icon_text)
        self.activity_id = activity_id
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.custom_tooltip_text = label_text
        self.is_right_side = is_right_side
        self.is_draggable = is_draggable
        self.tooltip_widget = tooltip_widget
        self.drag_start_pos = None
        
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_tooltip)
        
        self.is_active = False
        self.set_active(False)

    def set_active(self, is_active: bool):
        self.is_active = is_active
        if is_active:
            border_css = "border-left" if self.is_right_side else "border-right"
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: 18pt; 
                    background-color: #333333; 
                    border-radius: 4px;
                    border: none;
                    {border_css}: 2px solid {config.BTN_BG};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: 18pt; 
                    background: transparent; 
                    border-radius: 4px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {config.BTN_GHOST_BG};
                }}
            """)

    def enterEvent(self, event):
        self.tooltip_timer.start(750)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.tooltip_timer.stop()
        if self.tooltip_widget:
            self.tooltip_widget.hide()
        super().leaveEvent(event)

    def _show_tooltip(self):
        if self.tooltip_widget:
            self.tooltip_widget.show_at(self, self.custom_tooltip_text, self.is_right_side)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.is_draggable: return
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QGuiApplication.styleHints().startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.activity_id)
        drag.setMimeData(mime)
        
        self._drag_was_active = self.is_active
        
        was_active = self.is_active
        if was_active:
            self.set_active(False)  # Temporarily remove active CSS (green border)
            self.style().polish(self) # Force CSS update
        
        btn_pixmap = self.grab() # Take the perfect 40x40 photo without border
        
        if was_active:
            self.set_active(True) # Restore state
            self.style().polish(self)
        
        if self.is_active:
            panel_widget = self.window().activities.get(self.activity_id)
            if panel_widget:
                panel_pixmap = panel_widget.grab()
                scaled_panel = panel_pixmap.scaledToWidth(160, Qt.SmoothTransformation)
                composite = QPixmap(scaled_panel.size())
                composite.fill(Qt.transparent)
                p = QPainter(composite)
                p.setOpacity(0.6)
                p.drawPixmap(0, 0, scaled_panel)
                p.setOpacity(1.0)
                p.drawPixmap(0, 0, btn_pixmap)
                p.end()
                drag.setPixmap(composite)
                drag.setHotSpot(event.position().toPoint())
            else:
                drag.setPixmap(btn_pixmap)
                drag.setHotSpot(event.position().toPoint())
        else:
            # Snapshot the button for the drag icon
            drag.setPixmap(btn_pixmap)
            drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        if self._drag_was_active and self.window() and hasattr(self.window(), "_toggle_activity"):
            self.window()._toggle_activity(self.activity_id)
            
        self.hide()
        drag.exec(Qt.MoveAction)
        self.show()


class SidebarDragZone(QFrame):
    """
    A drop-zone container for SidebarButtons
    """
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(6)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText():
            return
            
        layout = self.layout()
        source_btn = event.source()
        
        target_idx = layout.count()
        last_vis_widget = None
        drop_y = 0
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_btn:
                continue
            
            last_vis_widget = w
            
            # Hit-test: if mouse is above the vertical center of this widget, insert BEFORE it.
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            # If the loop completes without breaking, we are dropping at the VERY BOTTOM.
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
            else:
                layout_margins = self.layout().contentsMargins()
                drop_y = layout_margins.top() if layout_margins else 0
                
        self._drop_line_y = drop_y
        self.update()
            
        event.accept()

    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        
        activity_id = event.mimeData().text()
        source_btn = event.source()
        if isinstance(source_btn, SidebarButton) and source_btn.activity_id == activity_id:
            layout = self.layout()
            
            target_idx = layout.count()
            last_vis_widget = None
            drop_y = 0
            
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if not w or w.isHidden() or w == source_btn:
                    continue
                
                last_vis_widget = w
                
                # Hit-test: if mouse is above the vertical center of this widget, insert BEFORE it.
                if event.position().y() < w.geometry().center().y():
                    target_idx = i
                    drop_y = w.geometry().top()
                    break
            else:
                # If the loop completes without breaking, we are dropping at the VERY BOTTOM.
                if last_vis_widget:
                    drop_y = last_vis_widget.geometry().bottom()
                else:
                    layout_margins = self.layout().contentsMargins()
                    drop_y = layout_margins.top() if layout_margins else 0
                        
            layout.insertWidget(target_idx, source_btn)
            event.acceptProposedAction()
            
            main_window = self.window()
            is_right = (hasattr(main_window, "_sidebar_right") and self == main_window._drag_zone_right)
            source_btn.is_right_side = is_right
            source_btn.set_active(False)
            
            self._drop_line_y = -1
            self.update()

            main_window = self.window()
            if hasattr(main_window, '_save_sidebar_layout'):
                main_window._save_sidebar_layout()

            if getattr(source_btn, '_drag_was_active', False):
                source_btn.window()._toggle_activity(source_btn.activity_id)
                source_btn._drag_was_active = False


class MarkerDragZone(QFrame):
    """
    A drop-zone container for Custom Markers in the settings panel.
    """
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() == "m_drag":
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        layout = self.layout()
        source_widget = event.source()
        
        target_idx = layout.count() - 1 
        drop_y = 0
        last_vis_widget = None
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            
            if w.objectName() == "stretch_placeholder":
                continue
                
            last_vis_widget = w
            
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
                
        if drop_y != self._drop_line_y:
            self._drop_line_y = drop_y
            self.update()
            
        event.acceptProposedAction()
        
    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        self._drop_line_y = -1
        self.update()
        
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        source_widget = event.source()
        layout = self.layout()
        
        target_idx = layout.count() - 1
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            if w.objectName() == "stretch_placeholder":
                continue
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                break
                
        if hasattr(self.window(), "_on_markers_reordered"):
            self.window()._on_markers_reordered(source_widget.original_idx, target_idx)
            
        event.acceptProposedAction()


class MarkerRowWidget(QWidget):
    """
    Draggable marker row.
    """
    def __init__(self, marker_data, original_idx, parent=None):
        super().__init__(parent)
        self.marker_data = marker_data
        self.original_idx = original_idx
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        from PySide6.QtGui import QDrag
        from PySide6.QtCore import QMimeData
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText("m_drag")
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.MoveAction)
class CustomDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText(self.txt("txt_select"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.addItems(self.options_list)
        list_widget.setStyleSheet("""
            QListWidget { border: none; padding: 0px; margin: 0px; outline: none; background: transparent; color: #d4d4d4; }
            QListWidget::item { padding: 0px 5px; min-height: 26px; border: none; }
            QListWidget::item:selected { background-color: #2a5f8f; }
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover { background-color: #333333; }
        """)
        list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, popup))
        
        fake_header = QPushButton(self.text())
        fake_header.setCursor(Qt.PointingHandCursor)
        fake_header.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                border-radius: 0px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; background-color: #2a2d2e; }}
        """)
        fake_header.clicked.connect(popup.close)
        layout.addWidget(fake_header)
        
        layout.addWidget(list_widget)
        
        def _update_height():
            row_h = 26
            display_count = min(5, list_widget.count())
            list_height = display_count * row_h
            list_widget.setFixedHeight(list_height)
            
            header_height = fake_header.sizeHint().height()
            popup.setFixedHeight(list_height + header_height)
            
        _update_height()
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()
        
        popup._update_height = _update_height

    def setValue(self, text):
        self.setText(text)
        self.valueChanged.emit(text)

    def _on_item_clicked(self, item, popup):
        self.setValue(item.text())
        popup.close()

    def currentText(self):
        return self.text()

class TitleDropdown(CustomDropdown):
    def __init__(self, options_list, parent=None):
        super().__init__(options_list, parent)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #aaaaaa;
                text-align: center;
                border: none;
                font-size: 9pt;
                padding: 2px 6px;
            }
            QPushButton:hover { color: #ffffff; }
            QPushButton:pressed { background: transparent; color: #ffffff; }
        """)

    def setText(self, text):
        # Always append the down arrow for the title drop down
        clean_text = text.replace("  ▾", "")
        super().setText(f"{clean_text}  ▾")

    def currentText(self):
        return super().currentText().replace("  ▾", "")

    def mousePressEvent(self, event):
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("""
            QFrame {
                background-color: #383838;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.addItems(self.options_list)
        list_widget.setStyleSheet("""
            QListWidget { border: none; padding: 0px; margin: 0px; outline: none; background: transparent; color: #e6e6e6; }
            QListWidget::item { padding: 0px 5px; min-height: 26px; border: none; }
            QListWidget::item:selected { background-color: #555555; }
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover { background-color: #4a4a4a; }
        """)
        list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, popup))
        layout.addWidget(list_widget)
        
        row_h = 26
        display_count = list_widget.count()
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height)
        
        global_pos = self.mapToGlobal(QPoint(0, self.height() + 2))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()

class MultiSelectDropdown(QPushButton):
    valueChanged = Signal(list)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.selected_items = set()
        self.setText(self.txt("txt_all_tracks"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e; color: #d4d4d4; text-align: left;
                padding: 4px 8px; border: 1px solid #3a3a3a; border-radius: 3px; min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("QFrame { background-color: #1e1e1e; border: 1px solid #444; border-radius: 3px; padding: 0px; margin: 0px; }")

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setStyleSheet("""
            QListWidget { border: none; outline: none; background: transparent; }
            QListWidget::item { border: none; outline: none; }
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover { background-color: #2a2d2e; }
        """)


        class CustomCheckItemWidget(QWidget):
            def __init__(self, text, is_checked, parent=None):
                from PySide6.QtWidgets import QHBoxLayout, QLabel
                from PySide6.QtCore import Qt
                super().__init__(parent)
                self.is_checked = is_checked
                self.opt_text = text
                
                lay = QHBoxLayout(self)
                lay.setContentsMargins(8, 0, 8, 0)
                lay.setSpacing(8)
                
                self.tick_box = QLabel()
                self.tick_box.setFixedSize(14, 14)
                self.tick_box.setAlignment(Qt.AlignCenter)
                
                self.lbl = QLabel(text)
                self.lbl.setStyleSheet("border: none; outline: none; color: #d4d4d4; font-size: 10pt; background: transparent;")
                
                lay.addWidget(self.tick_box)
                lay.addWidget(self.lbl)
                lay.addStretch()
                self.update_ui()
                
            def update_ui(self):
                if self.is_checked:
                    self.tick_box.setText("✔")
                    self.tick_box.setStyleSheet("background: #111; border: 1px solid #1a7a3e; color: #1a7a3e; font-weight: bold; font-size: 11px;")
                else:
                    self.tick_box.setText("")
                    self.tick_box.setStyleSheet("background: #111; border: 1px solid #333;")
                    
            def toggle(self):
                self.is_checked = not self.is_checked
                self.update_ui()

        from PySide6.QtCore import QSize
        from PySide6.QtWidgets import QSizePolicy
        for opt in self.options_list:
            item = QListWidgetItem(list_widget)
            item.setSizeHint(QSize(0, 28))
            widget = CustomCheckItemWidget(opt, opt in self.selected_items)
            widget.setCursor(Qt.PointingHandCursor)
            list_widget.setItemWidget(item, widget)

        layout.addWidget(list_widget)
        
        # Enable clicking anywhere on the item to toggle the checkbox
        def _on_item_clicked(it):
            w = list_widget.itemWidget(it)
            if w:
                w.toggle()
                self._on_toggled(w.opt_text, w.is_checked)
        list_widget.itemClicked.connect(_on_item_clicked)
        # PERFEKCYJNA MATEMATYKA WYSOKOŚCI
        display_count = min(5, len(self.options_list))
        list_height = display_count * 28
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)

        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()

    def _on_toggled(self, text, checked):
        if checked: self.selected_items.add(text)
        else: self.selected_items.discard(text)

        if not self.selected_items or len(self.selected_items) == len(self.options_list):
            self.setText(self.txt("txt_all_tracks"))
        else:
            self.setText(", ".join(sorted(self.selected_items)))
        self.valueChanged.emit(list(self.selected_items))


class SearchableDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText(self.txt("txt_select"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        self.popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_DeleteOnClose)
        self.popup.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.addItems(self.options_list)
        
        rtl_names = [config.SUPPORTED_LANGUAGES.get(code, code) for code in getattr(config, 'RTL_LANGUAGES', set())]
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() in rtl_names:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.list_widget.setStyleSheet("""
            QListWidget { border: none; padding: 0px; margin: 0px; outline: none; background: transparent; color: #d4d4d4; }
            QListWidget::item { padding: 0px 5px; min-height: 26px; border: none; }
            QListWidget::item:selected { background-color: #2a5f8f; }
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover { background-color: #333333; }
        """)
        self.list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, self.popup))
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText(self.txt("ph_search"))
        self.line_edit.setFixedHeight(self.height())
        self.line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                border: none; border-bottom: 1px solid #3a3a3a; padding: 6px;
                color: #d4d4d4; background: transparent;
            }
        """)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(lambda: self._select_first_visible(self.popup))
        layout.addWidget(self.line_edit)
        
        layout.addWidget(self.list_widget)
        
        self._update_height(self.list_widget.count(), False)
        
        self.line_edit.setFocus()
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self.popup.move(global_pos)
        self.popup.show()

    def _on_text_changed(self, text):
        search_str = text.lower()
        visible_count = 0
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if search_str in item.text().lower():
                item.setHidden(False)
                visible_count += 1
            else:
                item.setHidden(True)
                
        self._update_height(visible_count, is_searching=bool(text.strip()))

    def _update_height(self, visible_count, is_searching):
        row_h = 26
        
        if is_searching:
            display_count = max(1, min(5, visible_count))
        else:
            display_count = min(5, self.list_widget.count())

        if display_count < 5:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
        list_height = display_count * row_h
        self.list_widget.setFixedHeight(list_height)
        
        total_popup_height = self.height() + list_height
        self.popup.setFixedSize(self.width(), total_popup_height)

    def _select_first_visible(self, popup):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.setText(item.text())
                self.valueChanged.emit(item.text())
                popup.close()
                return
        popup.close()

    def setValue(self, text):
        self.setText(text)
        self.valueChanged.emit(text)

    def _on_item_clicked(self, item, popup):
        self.setValue(item.text())
        popup.close()

    def currentText(self):
        return self.text()


class CustomMsgBox(FramelessWindowMixin, QDialog):
    def __init__(self, parent, title: str, message: str, btn_yes_text: str, btn_no_text: str = None):
        super().__init__(parent)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; }}
            QLabel {{ color: {config.FG_COLOR}; }}
            QLabel#lbl_title {{ font-size: 14pt; font-weight: bold; }}
            QLabel#lbl_msg {{ font-size: 11pt; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_yes {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_yes:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tb = CustomTitleBar(self, "en", parent=self.inner_frame)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(15)
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("lbl_msg")
        lbl_msg.setWordWrap(True)
        lbl_msg.setFixedWidth(380)
        lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if btn_no_text:
            btn_no = QPushButton(btn_no_text)
            btn_no.clicked.connect(self.reject)
            btn_layout.addWidget(btn_no)
            btn_layout.addSpacing(10)
            
        btn_yes = QPushButton(btn_yes_text)
        btn_yes.setObjectName("btn_yes")
        btn_yes.clicked.connect(self.accept)
        btn_layout.addWidget(btn_yes)
        
        content_layout.addLayout(btn_layout)
        
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())


class MarkerDialog(FramelessWindowMixin, QDialog):
    """
    Custom frameless dialog for adding or editing a custom marker.
    Usage:
        dlg = MarkerDialog(parent, lang, title_key, prefill_name='', prefill_color='Blue')
        if dlg.exec() == QDialog.Accepted:
            name, color = dlg.result_name, dlg.result_color
    """
    def __init__(self, parent, lang: str, title_key: str,
                 prefill_name: str = '', prefill_color: str = ''):
        super().__init__(parent)
        self._lang = lang
        self.result_name = ''
        self.result_color = ''

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.ApplicationModal)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; border-radius: 6px; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; }}
            QLabel#lbl_title {{ font-size: 13pt; font-weight: bold; color: #ffffff; }}
            QLineEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px 8px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
            }}
            QLineEdit:focus {{ border-color: {config.BTN_BG}; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_ok {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_ok:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.inner_frame.setGraphicsEffect(shadow)
        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        title_text = _txt(lang, title_key)
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(title_text)
        root_layout.addWidget(self._tb)

        content = QWidget(self.inner_frame)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(14)
        root_layout.addWidget(content)

        lbl_title = QLabel(title_text, content)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)

        # Name row
        name_row = QHBoxLayout()
        name_lbl = QLabel(_txt(lang, "lbl_marker_name"), content)
        name_lbl.setFixedWidth(100)
        self._name_edit = QLineEdit(content)
        self._name_edit.setText(prefill_name)
        self._name_edit.setPlaceholderText(_txt(lang, "placeholder_marker_name"))
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        content_layout.addLayout(name_row)

        # Color row — translated display names with a reverse map to English keys
        color_row = QHBoxLayout()
        color_lbl = QLabel(_txt(lang, "lbl_marker_color"), content)
        color_lbl.setFixedWidth(100)
        _blocked = getattr(config, 'RESOLVE_COLORS_BLOCKED', {"Olive", "Violet", "Chocolate", "Navy", "Tan"})
        # Build [(translated_label, english_key), ...]
        self._color_key_map: dict[str, str] = {}  # translated → english
        translated_options: list[str] = []
        for c in config.RESOLVE_COLORS:
            if c in _blocked:
                continue
            t = _txt(lang, f"resolve_color_{c.lower()}")
            self._color_key_map[t] = c
            translated_options.append(t)
        self._color_combo = CustomDropdown(translated_options)
        # CustomDropdown defaults to self.txt("txt_select") which resolves to English
        # at creation time (no parent window yet). Override with the correct lang immediately.
        if not (prefill_color and prefill_color in config.RESOLVE_COLORS):
            self._color_combo.setText(_txt(lang, "txt_select"))
        # Set prefill value — find its translated equivalent
        if prefill_color and prefill_color in config.RESOLVE_COLORS:
            prefill_t = _txt(lang, f"resolve_color_{prefill_color.lower()}")
            self._color_combo.setText(prefill_t)
        color_row.addWidget(color_lbl)
        color_row.addWidget(self._color_combo)
        content_layout.addLayout(color_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(_txt(lang, "btn_close"), content)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(_txt(lang, "btn_apply"), content)
        btn_ok.setObjectName("btn_ok")
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_ok)
        content_layout.addLayout(btn_row)

        self.adjustSize()
        self.setFixedWidth(380)
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    def _on_ok(self):
        name = self._name_edit.text().strip()
        translated = self._color_combo.currentText()
        color_key = self._color_key_map.get(translated, "")
        # Both name and a valid color must be provided
        if name and color_key:
            self.result_name = name
            self.result_color = color_key
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._on_ok()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)



class UnsavedChangesDialog(FramelessWindowMixin, QDialog):

    def __init__(self, parent, diff_dict, key_name_map):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(parent.styleSheet() + f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; }}
            QScrollArea {{ border: 1px solid #333; background-color: #1c1c1c; border-radius: 4px; }}
            QFrame#item_row {{ border-bottom: 1px solid #333; padding-bottom: 5px; }}
        """)
        
        self.decisions = {}
        self.diff_dict = diff_dict
        self.rows = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tb = CustomTitleBar(self, "en", parent=self.inner_frame)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(15)
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(parent.txt('msg_unsaved_title'))
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        content_layout.addWidget(lbl_title)
        content_layout.addWidget(QLabel(parent.txt('msg_unsaved_desc')))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.vbox = QVBoxLayout(scroll_content)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(10)
        
        for k, (old_v, new_v) in diff_dict.items():
            row = QFrame()
            row.setObjectName("item_row")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            
            fname = key_name_map.get(k, k.replace('_', ' ').title())
            lbl_name = QLabel(f"{fname}:")
            lbl_val = QLabel(f"<b>{new_v}</b>")
            lbl_val.setStyleSheet("color: #aaa;")
            
            btn_save = QPushButton(parent.txt('btn_save'))
            btn_save.setObjectName("btn_apply")
            btn_save.setCursor(Qt.PointingHandCursor)
            btn_save.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'save'))
            
            btn_discard = QPushButton(parent.txt('btn_discard'))
            btn_discard.setObjectName("btn_secondary")
            btn_discard.setCursor(Qt.PointingHandCursor)
            btn_discard.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'discard'))
            
            rl.addWidget(lbl_name)
            rl.addWidget(lbl_val)
            rl.addStretch()
            rl.addWidget(btn_discard)
            rl.addWidget(btn_save)
            
            self.vbox.addWidget(row)
            self.rows[k] = row
        
        self.vbox.addStretch()
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)
        
        bot_layout = QHBoxLayout()
        btn_cancel = QPushButton(parent.txt('btn_cancel'))
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_discard_all = QPushButton(parent.txt('btn_discard_all'))
        btn_discard_all.setObjectName("btn_secondary")
        btn_discard_all.setCursor(Qt.PointingHandCursor)
        btn_discard_all.clicked.connect(self._discard_all)
        
        btn_save_all = QPushButton(parent.txt('btn_save_all'))
        btn_save_all.setObjectName("btn_apply")
        btn_save_all.setCursor(Qt.PointingHandCursor)
        btn_save_all.clicked.connect(self._save_all)
        
        bot_layout.addWidget(btn_cancel)
        bot_layout.addStretch()
        bot_layout.addWidget(btn_discard_all)
        bot_layout.addWidget(btn_save_all)
        content_layout.addLayout(bot_layout)
        
        self.resize(630, 480)
        _center_on_screen(self, 630, 480)
        
    def _make_decision(self, key, decision):
        self.decisions[key] = decision
        self.rows[key].hide()
        if len(self.decisions) == len(self.diff_dict):
            self.accept()
            
    def _save_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'save'
        self.accept()
        
    def _discard_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'discard'
        self.accept()


class SettingsDialog(FramelessWindowMixin, QDialog):
    """Settings Dialog — left category menu + right stacked pages.
    All I/O goes through engine.load_preferences / engine.save_preferences
    which delegate to osdoc's smart router.
    """

    # Fallback defaults (for revert buttons)
    DEFAULTS = {
        'view_mode':          'continuous',
        'offset':             -0.05,
        'pad':                0.05,
        'snap_max':           0.25,
        'editor_font_family': config.UI_FONT_NAME,
        'editor_font_size':   12,
        'editor_line_height': 12,
        'theme':              'dark',
        'always_on_top':      False,
        'hidden_panels':      [],
    }

    def txt(self, key: str, **kwargs) -> str:
        prefs = self.engine.load_preferences() or {}
        lang = prefs.get("gui_lang", "en")
        text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle(self.txt("tool_settings"))
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.Dialog)
        self.setMinimumSize(710, 550)
        self.resize(750, 580)

        prefs = self.engine.load_preferences() or {}

        # ── Global stylesheet ─────────────────────────────────────────────
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #1a1a1a;
            }}
            QPushButton {{
                padding: 6px 16px;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                background: transparent;
            }}
            QListWidget {{
                background-color: {config.SIDEBAR_BG};
                border: none;
                border-right: 1px solid {config.SEPARATOR_COL};
                outline: none;
                padding: 6px 0;
            }}
            QListWidget::item {{
                color: {config.NOTE_COL};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 10px 16px;
                border-radius: 0px;
            }}
            QListWidget::item:selected {{
                background-color: #2a2d2e;
                color: {config.FG_COLOR};
                border-left: 2px solid {config.BTN_BG};
            }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover:!selected {{
                background-color: #222222;
                color: {config.FG_COLOR};
            }}
            QStackedWidget {{
                background-color: {config.BG_COLOR};
            }}
            QDoubleSpinBox, QSpinBox, QComboBox {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                padding: 4px 8px;
                border-radius: 3px;
                min-height: 26px;
            }}
            QCheckBox {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {config.BTN_BG};
                border-color: {config.BTN_BG};
            }}
            QPushButton#btn_apply {{
                background-color: {config.BTN_BG};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 0 18px;
            }}
            QPushButton#btn_apply:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_apply:pressed {{ background-color: #125c2f; }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 0 12px;
            }}
            QPushButton#btn_secondary:hover {{ background-color: #2a2d2e; border-color: #888; }}
            QPushButton#btn_ghost_sm {{
                background-color: transparent;
                color: #888;
                border: 1px solid #444;
                border-radius: 4px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 9pt;
                padding: 0px;
                text-align: center;
            }}
            QPushButton#btn_ghost_sm:hover {{ background-color: #222; color: #bbb; border-color: #666; }}
            QPushButton[class="revert-btn"] {{
                padding: 0px;
                text-align: center;
                background: transparent;
                border: 1px solid #444;
                border-radius: 3px;
                color: #888;
                font-size: 12pt;
                font-weight: bold;
            }}
        """)

        # ─────────────────────────────────────────────────────────────────
        # Root layout: [LEFT menu | RIGHT content]
        # ─────────────────────────────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        outer_layout = QVBoxLayout(self.inner_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        self._tb = CustomTitleBar(self, prefs.get("gui_lang", "en"), parent=self.inner_frame)
        # Manually force the title into toolbars that normally get theirs from windowTitle()
        if hasattr(self._tb, "_lbl_title"):
            self._tb._lbl_title.setText(self.txt("tool_settings"))
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        outer_layout.addWidget(self._tb)
        
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer_layout.addLayout(root)

        # ── LEFT: Category list ───────────────────────────────────────────
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(155)
        self.category_list.setFocusPolicy(Qt.NoFocus)
        # Disable horizontal scrollbar — marquee handles overflow instead
        self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._marquee_delegate = MarqueeItemDelegate(self.category_list)
        self.category_list.setItemDelegate(self._marquee_delegate)
        root.addWidget(self.category_list)

        # ── RIGHT: stacked pages + bottom bar ────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        root.addLayout(right_layout)


        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        # Connect list → stack
        self.category_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        self._build_ui()

        # ─────────────────────────────────────────────────────────────────
        # BOTTOM BUTTON BAR (separator + row)
        # ─────────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {config.SEPARATOR_COL}; max-height: 1px; border: none;")
        right_layout.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(16, 10, 16, 12)
        btn_bar.setSpacing(8)

        btn_bar.addStretch()

        # Right: Restore / Close / Apply
        self.btn_restore = QPushButton(self.txt("btn_restore_defaults"))
        self.btn_restore.setObjectName("btn_secondary")
        self.btn_restore.setMinimumWidth(120)
        self.btn_restore.setFixedHeight(30)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self._restore_all_defaults)
        btn_bar.addWidget(self.btn_restore)

        self.btn_close = QPushButton(self.txt("btn_close"))
        self.btn_close.setObjectName("btn_secondary")
        self.btn_close.setMinimumWidth(120)
        self.btn_close.setFixedHeight(30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_close)

        self.btn_apply = QPushButton(self.txt("btn_apply"))
        self.btn_apply.setObjectName("btn_apply")
        self.btn_apply.setMinimumWidth(120)
        self.btn_apply.setFixedHeight(30)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_bar.addWidget(self.btn_apply)

        right_layout.addLayout(btn_bar)

    # ── Helpers ───────────────────────────────────────────────────────────


    def _set_view_mode(self, mode):
        self.engine.save_preferences({'settings_view_mode': mode})
        self._build_ui()

    def _build_ui(self):
        self._advanced_widgets = []
        self.category_list.clear()
        while self.stack.count() > 0:
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        prefs = self.engine.load_preferences() or {}
        view_mode = prefs.get('settings_view_mode', 'basic')
        is_basic = (view_mode == 'basic')

        if is_basic:
            self.category_list.addItem(self.txt("tab_general"))
            self.category_list.addItem(self.txt("tab_shortcuts"))
            self.category_list.addItem(self.txt("tab_custom_markers"))
            self.category_list.addItem(self.txt("tab_transcript"))
            self.category_list.addItem(self.txt("tab_telemetry"))
        else:
            self.category_list.addItem(self.txt("tab_general"))
            self.category_list.addItem(self.txt("tab_shortcuts"))
            self.category_list.addItem(self.txt("tab_custom_markers"))
            self.category_list.addItem(self.txt("tab_transcript"))
            self.category_list.addItem(self.txt("tab_interface"))
            self.category_list.addItem(self.txt("tab_ai_engine"))
            self.category_list.addItem(self.txt("tab_algorithms"))
            self.category_list.addItem(self.txt("tab_audio_sync"))
            self.category_list.addItem(self.txt("tab_telemetry"))

        self.category_list.setCurrentRow(0)

        # ── Revert helper ─────────────────────────────────────────────────
        self.revert_funcs = []

        def _add_row(form, label_text, widget, default_val, setter_func):
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(widget)
            btn_rev = QPushButton("↺")
            btn_rev.setFixedSize(26, 26)
            btn_rev.setCursor(Qt.PointingHandCursor)
            btn_rev.setObjectName("btn_ghost_sm")
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            def create_reset_handler(s_func, d_val):
                return lambda checked=False: s_func(d_val)
            btn_rev.clicked.connect(create_reset_handler(setter_func, default_val))
            row.addWidget(btn_rev)
            lbl = QLabel(label_text)
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(200)
            form.addRow(lbl, container)
            self.revert_funcs.append(lambda d=default_val, s=setter_func: s(d))
            return lbl, container

        def _add_page_to_stack(page_widget):
            scroll = QScrollArea()
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
            scroll.setWidget(page_widget)
            self.stack.addWidget(scroll)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 0 — GENERAL
        # ─────────────────────────────────────────────────────────────────
        page_gen = QWidget()
        page_gen.setStyleSheet("background: transparent;")
        l_gen = QVBoxLayout(page_gen)
        l_gen.setContentsMargins(24, 20, 24, 16)
        l_gen.setSpacing(0)
        form_gen = QFormLayout()
        form_gen.setSpacing(14)
        form_gen.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Basic/Advanced view switch
        view_btn_row = QHBoxLayout()
        view_btn_row.setContentsMargins(0, 0, 0, 16)
        view_btn_row.setSpacing(10)
        
        btn_view_basic = QPushButton(self.txt("btn_view_basic"))
        btn_view_basic.setFixedHeight(30)
        btn_view_basic.setCursor(Qt.PointingHandCursor)
        active_btn_style = "background-color: #1b8745; color: white; border: 1px solid #125c2f; border-radius: 4px; font-weight: bold;"
        inactive_btn_style = "background-color: #1a1a1a; color: #777777; border-top: 1px solid #0d0d0d; border-bottom: 1px solid #2e2e2e; border-left: 1px solid #141414; border-right: 1px solid #141414; border-radius: 4px; font-weight: normal;"
        
        if is_basic:
            btn_view_basic.setStyleSheet(active_btn_style)
        else:
            btn_view_basic.setStyleSheet(inactive_btn_style)
        btn_view_basic.clicked.connect(lambda: self._set_view_mode('basic'))
        
        btn_view_advanced = QPushButton(self.txt("btn_view_advanced"))
        btn_view_advanced.setFixedHeight(30)
        btn_view_advanced.setCursor(Qt.PointingHandCursor)
        
        import os
        has_dev = os.path.exists(os.path.join(self.engine.os_doc.install_dir, "dev.json"))
        
        if view_mode == 'advanced':
            btn_view_advanced.setStyleSheet(active_btn_style)
        else:
            btn_view_advanced.setStyleSheet(inactive_btn_style)
            
        if not has_dev:
            btn_view_advanced.setEnabled(False)
            btn_view_advanced.setToolTip(self.txt("tt_advanced_locked"))
            
        btn_view_advanced.clicked.connect(lambda: self._set_view_mode('advanced'))

        view_btn_row.addWidget(btn_view_basic)
        view_btn_row.addWidget(btn_view_advanced)
        l_gen.addLayout(view_btn_row)


        # Language
        self.dropdown_lang = CustomDropdown(list(config.SUPPORTED_LANGS.values()))
        current_lang_code = prefs.get('gui_lang', 'en')
        self.dropdown_lang.setText(config.SUPPORTED_LANGS.get(current_lang_code, 'English'))

        def _on_lang_changed(val):
            code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), 'en')
            prefs = self.engine.load_preferences() or {}
            if code == prefs.get('gui_lang'):
                return

            current_state = self._get_current_state_dict()
            current_state['gui_lang'] = code
            
            prefs['gui_lang'] = code
            self.engine.save_preferences(prefs)

            self._build_ui()
            self._restore_state_dict(current_state)

            target = config.TRANS.get(code, config.TRANS['en'])
            title   = target.get('msg_title_language_changed', 'Language Changed')
            message = target.get('msg_restart_lang_pending', 'Language changed. Full changes will apply on restart.')
            ok_text = target.get('btn_ok', 'OK')
            
            CustomMsgBox(self, title, message, ok_text).exec()
            
            self.btn_apply.setText(self.txt("btn_apply"))
            self.btn_close.setText(self.txt("btn_close"))
            self.btn_restore.setText(self.txt("btn_restore_defaults"))

        self.dropdown_lang.valueChanged.connect(_on_lang_changed)
        def _reset_lang(val):
            self.dropdown_lang.setText(val)
            _on_lang_changed(val)
        _add_row(form_gen, self.txt("lbl_language"), self.dropdown_lang, 'English', _reset_lang)

        # App Icon (Visual Selector)
        icon_row = QHBoxLayout()
        icon_row.setSpacing(10)
        self.icon_group = QButtonGroup(self)
        self.icon_group.setExclusive(True)
        
        icon_names = ["default", "monochrome", "whiteb", "white"]
        saved_icon = prefs.get('app_icon', 'default')
        
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        import os
        
        for i, name in enumerate(icon_names):
            btn = QPushButton()
            ext = ".ico" if self.engine.os_doc.is_win else ".png"
            icon_path = os.path.join(self.engine.os_doc.install_dir, "icons", f"icon_{name}{ext}")
            
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(48, 48))
            btn.setCheckable(True)
            if name == saved_icon:
                btn.setChecked(True)
                
            btn.setProperty("icon_name", name)
            
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px; }
                QPushButton:checked { background: #262626; border: 1px solid #404040; }
                QPushButton:hover { background: #333333; }
            """)
            self.icon_group.addButton(btn, i)
            icon_row.addWidget(btn)
            
        icon_row.addStretch()
        
        icon_container = QWidget()
        icon_container.setLayout(icon_row)
        icon_container.layout().setContentsMargins(0, 0, 0, 0)
        
        lbl_icon, container_icon = _add_row(form_gen, self.txt("lbl_app_icon"), icon_container, 'default', lambda: None)
        btn_rev_icon = container_icon.findChild(QPushButton, "btn_ghost_sm")
        if btn_rev_icon:
            btn_rev_icon.clicked.disconnect()
            def set_icon_default(val="default"):
                for btn in self.icon_group.buttons():
                    if btn.property("icon_name") == val:
                        btn.setChecked(True)
                        break
            btn_rev_icon.clicked.connect(lambda *args: set_icon_default("default"))

        l_gen.addLayout(form_gen)

        sep_io = QFrame()
        sep_io.setFrameShape(QFrame.Shape.HLine)
        sep_io.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
        l_gen.addSpacing(12)
        l_gen.addWidget(sep_io)
        l_gen.addSpacing(10)

        # Import/Export settings
        io_row = QHBoxLayout()
        io_row.setContentsMargins(0, 0, 0, 16)
        io_row.setSpacing(8)

        btn_import_s = QPushButton(self.txt("btn_import_settings"))
        btn_import_s.setObjectName("btn_ghost_sm")
        btn_import_s.setStyleSheet("padding: 4px 12px;")
        btn_import_s.setCursor(Qt.PointingHandCursor)
        btn_import_s.clicked.connect(self._on_import_settings)
        io_row.addWidget(btn_import_s)

        btn_export_s = QPushButton(self.txt("btn_export_settings"))
        btn_export_s.setObjectName("btn_ghost_sm")
        btn_export_s.setStyleSheet("padding: 4px 12px;")
        btn_export_s.setCursor(Qt.PointingHandCursor)
        btn_export_s.clicked.connect(self._on_export_settings)
        io_row.addWidget(btn_export_s)
        io_row.addStretch()
        l_gen.addLayout(io_row)

        l_gen.addStretch()
        _add_page_to_stack(page_gen)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 1 — SHORTCUTS
        # ─────────────────────────────────────────────────────────────────
        page_shorts = QWidget()
        page_shorts.setStyleSheet("background: transparent;")
        l_shorts = QVBoxLayout(page_shorts)
        l_shorts.setContentsMargins(24, 20, 24, 16)
        l_shorts.setSpacing(0)


        default_shortcuts = getattr(config, 'DEFAULT_SETTINGS', {}).get('shortcuts', {})
        # Merge defaults with saved prefs, keeping only keys present in DEFAULT_SETTINGS
        saved_shortcuts = prefs.get('shortcuts', {})
        current_shortcuts = {k: saved_shortcuts.get(k, v) for k, v in default_shortcuts.items()}

        self.shortcut_inputs = {}

        def _check_shortcut_conflicts():
            """Scan all capturable inputs; set red border on any with a duplicate sequence."""
            # Gather sequences from capturable inputs only (built-in + custom marker)
            all_inputs = dict(self.shortcut_inputs)
            all_inputs.update(getattr(self, 'custom_marker_shortcut_inputs', {}))
            seq_to_keys = {}
            for k, w in all_inputs.items():
                if w.display_only:
                    continue
                seq = w.get_sequence()
                if seq:
                    seq_to_keys.setdefault(seq, []).append(k)
            # Apply conflict styling
            for k, w in all_inputs.items():
                if w.display_only:
                    continue
                seq = w.get_sequence()
                is_conflict = seq and len(seq_to_keys.get(seq, [])) > 1
                w.set_conflict(bool(is_conflict))


        # Builds label + field container for one shortcut row (used for addRow and insertRow)
        def _make_shortcut_widgets(label_text, widget, default_val, setter_func, is_display=False):
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(widget)

            if not is_display:
                btn_clear = QPushButton("✕")
                btn_clear.setFixedSize(26, 26)
                btn_clear.setCursor(Qt.PointingHandCursor)
                btn_clear.setObjectName("btn_ghost_sm")
                btn_clear.setToolTip(self.txt("tt_clear_shortcut") if self.txt("tt_clear_shortcut") != "tt_clear_shortcut" else "Clear shortcut")
                btn_clear.clicked.connect(lambda: setter_func(""))
                row.addWidget(btn_clear)

            btn_rev = QPushButton("↺")
            btn_rev.setFixedSize(26, 26)
            btn_rev.setCursor(Qt.PointingHandCursor)
            btn_rev.setObjectName("btn_ghost_sm")
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            def create_reset_handler(s_func, d_val):
                return lambda checked=False: s_func(d_val)
            btn_rev.clicked.connect(create_reset_handler(setter_func, default_val))
            row.addWidget(btn_rev)

            lbl = QLabel(label_text)
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(200)
            return lbl, container

        def _add_shortcut_row(form, label_text, widget, default_val, setter_func, is_display=False):
            lbl, container = _make_shortcut_widgets(label_text, widget, default_val, setter_func, is_display)
            form.addRow(lbl, container)

        # Keys and their ordering in the final form
        MARKER_KEYS  = {'mark_red', 'mark_blue', 'mark_green', 'mark_eraser',
                        'jump_to_word', 'play_stop'}
        NAV_KEYS     = {'search', 'open_settings'}
        DISPLAY_ONLY = {'jump_to_word', 'play_stop'}
        KEY_ORDER    = ['mark_red', 'mark_blue', 'mark_green', 'mark_eraser',
                        'jump_to_word', 'play_stop', 'search', 'open_settings']

        def make_setter(w, check_fn):
            def _setter(v):
                w.set_sequence(str(v))
                check_fn()
            return _setter

        # ── ONE unified QFormLayout ───────────────────────────────────────────
        # Custom markers inserted via insertRow() at _custom_sc_insert_pos so
        # spacing is always identical (14px) between EVERY row.
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Marker shortcuts (red … eraser)
        for key in KEY_ORDER:
            if key not in MARKER_KEYS or key not in current_shortcuts:
                continue
            is_disp = key in DISPLAY_ONLY
            if is_basic and is_disp:
                continue
            value      = current_shortcuts[key]
            i18n_key   = f'shortcut_{key}'
            label_text = self.txt(i18n_key) if self.txt(i18n_key) != i18n_key else key.replace('_', ' ').title()
            widget = ShortcutCaptureButton(str(value), display_only=is_disp)
            widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
            lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, ''),
                                                     make_setter(widget, _check_shortcut_conflicts),
                                                     is_display=is_disp)
            form.addRow(lbl, container)
            self.shortcut_inputs[key] = widget

        # Position where custom marker rows will be inserted (after last marker row)
        self._custom_sc_insert_pos       = form.rowCount()
        self._custom_sc_unified          = form
        self._make_shortcut_widgets_fn   = _make_shortcut_widgets
        self._check_shortcut_conflicts_fn = _check_shortcut_conflicts
        self._add_shortcut_row_fn         = _add_shortcut_row
        self.custom_marker_shortcut_inputs = {}

        # Nav shortcuts (search, open_settings)
        for key in KEY_ORDER:
            if key not in NAV_KEYS or key not in current_shortcuts:
                continue
            value      = current_shortcuts[key]
            i18n_key   = f'shortcut_{key}'
            label_text = self.txt(i18n_key) if self.txt(i18n_key) != i18n_key else key.replace('_', ' ').title()
            widget = ShortcutCaptureButton(str(value), display_only=False)
            widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
            lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, ''),
                                                     make_setter(widget, _check_shortcut_conflicts),
                                                     is_display=False)
            form.addRow(lbl, container)
            self.shortcut_inputs[key] = widget

        l_shorts.addLayout(form)
        l_shorts.addStretch()

        _check_shortcut_conflicts()
        _add_page_to_stack(page_shorts)


        # ─────────────────────────────────────────────────────────────────
        # PAGE 2 — CUSTOM MARKERS
        # ─────────────────────────────────────────────────────────────────
        page_markers = QWidget()
        page_markers.setStyleSheet("background: transparent;")
        l_markers = QVBoxLayout(page_markers)
        l_markers.setContentsMargins(24, 20, 24, 16)
        l_markers.setSpacing(10)

        self.current_custom_markers = list(prefs.get('custom_markers', []))

        # Scroll area to hold the dynamic marker rows
        markers_scroll = QScrollArea()
        markers_scroll.setWidgetResizable(True)
        markers_scroll.setFrameShape(QFrame.NoFrame)
        markers_scroll.setMinimumHeight(120)
        markers_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
            }}
            QWidget#markers_inner {{
                background-color: #1e1e1e;
            }}
        """)
        self._markers_inner = MarkerDragZone()
        self._markers_inner.setObjectName("markers_inner")
        self._markers_layout = self._markers_inner.layout()
        self._markers_layout.setContentsMargins(4, 4, 4, 4)
        self._markers_layout.setSpacing(2)
        self._markers_layout.addStretch()
        markers_scroll.setWidget(self._markers_inner)
        self._refresh_markers_list()
        # Also refresh Shortcuts tab now that current_custom_markers is populated
        self._refresh_custom_marker_shortcuts()
        l_markers.addWidget(markers_scroll)


        marker_btn_row = QHBoxLayout()
        marker_btn_row.setSpacing(8)
        btn_add_m = QPushButton(self.txt("btn_add_marker"))
        btn_add_m.setObjectName("btn_secondary")
        btn_add_m.setFixedHeight(30)
        btn_add_m.setCursor(Qt.PointingHandCursor)
        btn_add_m.clicked.connect(self._on_add_marker)
        marker_btn_row.addWidget(btn_add_m)

        btn_export_m = QPushButton(self.txt("btn_export_markers"))
        btn_export_m.setObjectName("btn_ghost_sm")
        btn_export_m.setStyleSheet("padding: 0 14px;")
        btn_export_m.setFixedHeight(30)
        btn_export_m.setCursor(Qt.PointingHandCursor)
        btn_export_m.clicked.connect(self._on_export_markers)
        marker_btn_row.addWidget(btn_export_m)

        btn_import_m = QPushButton(self.txt("btn_import_markers"))
        btn_import_m.setObjectName("btn_ghost_sm")
        btn_import_m.setStyleSheet("padding: 0 14px;")
        btn_import_m.setFixedHeight(30)
        btn_import_m.setCursor(Qt.PointingHandCursor)
        btn_import_m.clicked.connect(self._on_import_markers)
        marker_btn_row.addWidget(btn_import_m)

        marker_btn_row.addStretch()
        l_markers.addLayout(marker_btn_row)


        _add_page_to_stack(page_markers)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 3 — TRANSCRIPT
        # ─────────────────────────────────────────────────────────────────
        page_transcript = QWidget()
        page_transcript.setStyleSheet("background: transparent;")
        l_transcript = QVBoxLayout(page_transcript)
        l_transcript.setContentsMargins(24, 20, 24, 16)
        l_transcript.setSpacing(0)
        form_transcript = QFormLayout()
        form_transcript.setSpacing(14)
        form_transcript.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Display Mode (moved from General)
        view_items = [self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")]
        self.combo_view = CustomDropdown(view_items)
        is_seg = prefs.get('view_mode', 'segmented') == 'segmented'
        self.combo_view.setText(self.txt("opt_segmented_blocks") if is_seg else self.txt("opt_continuous_flow"))
        _add_row(form_transcript, self.txt("lbl_display_mode"), self.combo_view,
                 self.txt("opt_segmented_blocks"), self.combo_view.setValue)

        # Font family, size, line height
        from PySide6.QtGui import QFontDatabase
        self.combo_font = CustomDropdown(QFontDatabase.families())
        self.combo_font.setText(prefs.get('editor_font_family', self.DEFAULTS['editor_font_family']))

        self.spin_fsize = QSpinBox()
        self.spin_fsize.setRange(8, 48)
        self.spin_fsize.setValue(int(prefs.get('editor_font_size', self.DEFAULTS['editor_font_size'])))

        self.spin_lheight = QSpinBox()
        self.spin_lheight.setRange(0, 40)
        self.spin_lheight.setValue(int(prefs.get('editor_line_height', self.DEFAULTS['editor_line_height'])))

        _add_row(form_transcript, self.txt("lbl_transcript_font"), self.combo_font,
                 self.DEFAULTS['editor_font_family'], self.combo_font.setValue)
        _add_row(form_transcript, self.txt("lbl_font_size_pt"),    self.spin_fsize,
                 self.DEFAULTS['editor_font_size'],   self.spin_fsize.setValue)
        _add_row(form_transcript, self.txt("lbl_line_spacing_px"), self.spin_lheight,
                 self.DEFAULTS['editor_line_height'], self.spin_lheight.setValue)
        l_transcript.addLayout(form_transcript)

        # Font preview
        self.lbl_preview = QLabel()
        self.lbl_preview.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_preview.setWordWrap(True)
        self.lbl_preview.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_preview.setMinimumHeight(90)
        self.lbl_preview.setStyleSheet(f"background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px; color: {config.FG_COLOR}; padding: 12px 14px;")
        l_transcript.addSpacing(10)
        l_transcript.addWidget(self.lbl_preview)


        if not is_basic:
            # Separator before chunking settings
            sep_chunk = QFrame()
            sep_chunk.setFrameShape(QFrame.Shape.HLine)
            sep_chunk.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
            l_transcript.addSpacing(12)
            l_transcript.addWidget(sep_chunk)
            l_transcript.addSpacing(10)

        # Chunking spinboxes — Advanced view only
        if not is_basic:
            form_chunk = QFormLayout()
            form_chunk.setSpacing(14)
            form_chunk.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.spin_chunk_max = QSpinBox()
            self.spin_chunk_max.setRange(5, 200)
            self.spin_chunk_max.setValue(int(prefs.get('chunk_max_words', 30)))
            _add_row(form_chunk, self.txt("lbl_chunk_max_words"), self.spin_chunk_max, 30, self.spin_chunk_max.setValue)

            self.spin_chunk_look = QSpinBox()
            self.spin_chunk_look.setRange(0, 20)
            self.spin_chunk_look.setValue(int(prefs.get('chunk_lookahead', 3)))
            _add_row(form_chunk, self.txt("lbl_chunk_lookahead"), self.spin_chunk_look, 3, self.spin_chunk_look.setValue)

            self.spin_chunk_min = QSpinBox()
            self.spin_chunk_min.setRange(1, 50)
            self.spin_chunk_min.setValue(int(prefs.get('chunk_min_chars', 7)))
            _add_row(form_chunk, self.txt("lbl_chunk_min_chars"), self.spin_chunk_min, 7, self.spin_chunk_min.setValue)

            l_transcript.addLayout(form_chunk)

            # Enable/disable chunk spinboxes based on view mode
            def _update_chunk_state(idx):
                enabled = (idx == 1)  # 1 = Segmented
                self.spin_chunk_max.setEnabled(enabled)
                self.spin_chunk_look.setEnabled(enabled)
                self.spin_chunk_min.setEnabled(enabled)
            self.combo_view.valueChanged.connect(lambda v: _update_chunk_state(1 if v == self.txt("opt_segmented_blocks") else 0))
            _update_chunk_state(1 if self.combo_view.currentText() == self.txt("opt_segmented_blocks") else 0)

        # ── Sync DaVinci timeline on chapter switch ─ BOTTOM of Transcript tab
        # (below font preview and chunking settings, applies to both basic/advanced)
        l_transcript.addSpacing(12)
        sep_sync = QFrame()
        sep_sync.setFrameShape(QFrame.Shape.HLine)
        sep_sync.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
        l_transcript.addWidget(sep_sync)
        l_transcript.addSpacing(10)

        form_bottom = QFormLayout()
        form_bottom.setSpacing(14)
        form_bottom.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.chk_sync_davinci = ToggleSwitch()
        self.chk_sync_davinci.setChecked(bool(prefs.get('sync_davinci_chapter', True)), animated=False)
        w_sync = QWidget()
        l_sync = QHBoxLayout(w_sync)
        l_sync.setContentsMargins(0, 0, 0, 0)
        l_sync.addStretch()
        l_sync.addWidget(self.chk_sync_davinci)
        _add_row(form_bottom, self.txt("chk_sync_davinci"), w_sync,
                 True, lambda v: self.chk_sync_davinci.setChecked(v, animated=False))

        # Track order toggle — directly below sync davinci
        import config as _cfg_bot
        _bot_prefs = self.engine.load_preferences() or {}
        self.tgl_xml_preserve_track_order = ToggleSwitch()
        self.tgl_xml_preserve_track_order.setChecked(
            bool(_bot_prefs.get("xml_preserve_track_order",
                                _cfg_bot.DEFAULT_SETTINGS["xml_preserve_track_order"])),
            animated=False
        )
        self.tgl_xml_preserve_track_order.setToolTip(self.txt("tt_xml_preserve_track_order"))
        self.tgl_xml_preserve_track_order.toggled.connect(
            lambda checked: self.engine.save_preferences({"xml_preserve_track_order": checked})
        )
        w_xml_track = QWidget()
        l_xml_track = QHBoxLayout(w_xml_track)
        l_xml_track.setContentsMargins(0, 0, 0, 0)
        l_xml_track.addStretch()
        l_xml_track.addWidget(self.tgl_xml_preserve_track_order)
        _add_row(form_bottom, self.txt("lbl_xml_preserve_track_order"), w_xml_track,
                 False, lambda v: self.tgl_xml_preserve_track_order.setChecked(v, animated=False))

        # ── Precise timestamps toggle — bottom of Transcript tab (basic + advanced) ──
        self.tgl_timestamp_precise = ToggleSwitch()
        self.tgl_timestamp_precise.setChecked(
            bool(prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise'])),
            animated=False
        )
        self.tgl_timestamp_precise.setToolTip(self.txt("tt_timestamp_precise"))
        w_ts_precise = QWidget()
        l_ts_precise = QHBoxLayout(w_ts_precise)
        l_ts_precise.setContentsMargins(0, 0, 0, 0)
        l_ts_precise.addStretch()
        l_ts_precise.addWidget(self.tgl_timestamp_precise)
        _add_row(form_bottom, self.txt("lbl_timestamp_precise"), w_ts_precise,
                 False, lambda v: self.tgl_timestamp_precise.setChecked(v, animated=False))

        l_transcript.addLayout(form_bottom)
        l_transcript.addStretch()

        self.combo_font.valueChanged.connect(self._update_preview)
        self.spin_fsize.valueChanged.connect(self._update_preview)
        self.spin_lheight.valueChanged.connect(self._update_preview)
        self._update_preview()
        _add_page_to_stack(page_transcript)

        # ─────────────────────────────────────────────────────────────────
        if not is_basic:
            # PAGE 4 — INTERFACE
        # ─────────────────────────────────────────────────────────────────
            page_iface = QWidget()
            page_iface.setStyleSheet("background: transparent;")
            l_iface = QVBoxLayout(page_iface)
            l_iface.setContentsMargins(24, 20, 24, 16)
            l_iface.setSpacing(0)
            form_iface = QFormLayout()
            form_iface.setSpacing(14)
            form_iface.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Always on top
            self.chk_ontop = ToggleSwitch()
            self.chk_ontop.setChecked(bool(prefs.get('always_on_top', True)), animated=False)
            _add_row(form_iface, self.txt("lbl_always_on_top"), self.chk_ontop,
                     False, lambda v: self.chk_ontop.setChecked(v, animated=False))

            # Hidden panels (multi-select)
            _panel_options = ["Script Analysis", "Silence", "Filler Words", "Assembly"]
            self.dropdown_hidden = MultiSelectDropdown(_panel_options)
            self.dropdown_hidden.setFixedHeight(30)
            saved_hidden = prefs.get('hidden_panels', [])
            if isinstance(saved_hidden, list) and saved_hidden:
                self.dropdown_hidden.selected_items = set(saved_hidden)
                self.dropdown_hidden.setText(", ".join(sorted(saved_hidden)))
            else:
                self.dropdown_hidden.setText(self.txt("txt_select"))
            _add_row(form_iface, self.txt("lbl_hidden_panels"), self.dropdown_hidden,
                     [], lambda v: None)  # revert placeholder — clear handled by Restore Defaults

            # Accent Color
            _accent_items = ["green", "blue", "purple", "orange"]
            self.dropdown_accent = CustomDropdown(_accent_items)
            self.dropdown_accent.setFixedHeight(30)
            saved_accent = prefs.get('accent_color', 'green')
            self.dropdown_accent.setText(saved_accent if saved_accent in _accent_items else 'green')
            _add_row(form_iface, self.txt("lbl_accent_color"), self.dropdown_accent, 'green', self.dropdown_accent.setValue)

            l_iface.addLayout(form_iface)
            l_iface.addStretch()
            _add_page_to_stack(page_iface)

        
        

        # ─────────────────────────────────────────────────────────────────
        if not is_basic:
            # PAGE 5 — AI ENGINE
        # ─────────────────────────────────────────────────────────────────
            page_ai = QWidget()
            page_ai.setStyleSheet("background: transparent;")
            l_ai = QVBoxLayout(page_ai)
            l_ai.setContentsMargins(24, 20, 24, 16)
            l_ai.setSpacing(0)
            form_ai = QFormLayout()
            form_ai.setSpacing(14)
            form_ai.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # Device
            _device_items = ["Auto", "CPU", "GPU"]
            self.dropdown_device = CustomDropdown(_device_items)
            self.dropdown_device.setFixedHeight(30)
            saved_device = prefs.get('device', 'auto').capitalize()
            if saved_device.upper() == 'AUTO': saved_device = 'Auto'
            self.dropdown_device.setText(saved_device if saved_device in _device_items else 'Auto')
            _add_row(form_ai, self.txt("lbl_device"), self.dropdown_device, 'Auto', self.dropdown_device.setValue)

            # Compute type
            _compute_items = ["Auto", "float16", "int8", "float32", "int8_float16", "int8_float32"]
            self.dropdown_compute = CustomDropdown(_compute_items)
            self.dropdown_compute.setFixedHeight(30)
            saved_compute = prefs.get('ai_compute_type', 'Auto')
            self.dropdown_compute.setText(saved_compute if saved_compute in _compute_items else 'Auto')
            _add_row(form_ai, self.txt("lbl_compute_type"), self.dropdown_compute, 'Auto', self.dropdown_compute.setValue)

            l_ai.addLayout(form_ai)
            l_ai.addSpacing(14)

            # Initial prompt label + QTextEdit
            lbl_prompt = QLabel(self.txt("lbl_initial_prompt"))
            lbl_prompt.setStyleSheet(f"color: {config.NOTE_COL}; font-size: 9pt; background: transparent;")
            l_ai.addWidget(lbl_prompt)
            l_ai.addSpacing(4)

            self.textedit_prompt = QTextEdit()
            self.textedit_prompt.setMaximumHeight(80)
            self.textedit_prompt.setPlaceholderText("e.g. Transcribe film dialogue with punctuation.")
            self.textedit_prompt.setPlainText(prefs.get('ai_initial_prompt', config.DEFAULT_WHISPER_PROMPT))
            self.textedit_prompt.setStyleSheet(f"""
                QTextEdit {{
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 6px 8px;
                    font-family: "{config.UI_FONT_NAME}";
                    font-size: 10pt;
                }}
            """)
            l_ai.addWidget(self.textedit_prompt)

            # ── Advanced Whisper Parameters ─────────────────────────
            sep_whisper = QFrame()
            sep_whisper.setFrameShape(QFrame.Shape.HLine)
            sep_whisper.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
            l_ai.addSpacing(14)
            l_ai.addWidget(sep_whisper)
            l_ai.addSpacing(10)
            self._advanced_widgets.append(sep_whisper)

            form_whisper = QFormLayout()
            form_whisper.setSpacing(14)
            form_whisper.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.chk_vad_filter = ToggleSwitch()
            self.chk_vad_filter.setChecked(bool(prefs.get('ai_vad_filter', False)), animated=False)
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_vad_filter"), self.chk_vad_filter,
                     False, lambda v: self.chk_vad_filter.setChecked(v, animated=False)))

            self.chk_condition_prev = ToggleSwitch()
            self.chk_condition_prev.setChecked(bool(prefs.get('ai_condition_on_prev', False)), animated=False)
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_condition_prev"), self.chk_condition_prev,
                     False, lambda v: self.chk_condition_prev.setChecked(v, animated=False)))

            self.spin_beam_size = QSpinBox()
            self.spin_beam_size.setRange(1, 10)
            self.spin_beam_size.setValue(int(prefs.get('ai_beam_size', 1)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_beam_size"), self.spin_beam_size, 1, self.spin_beam_size.setValue))

            self.spin_temperature = QDoubleSpinBox()
            self.spin_temperature.setRange(0.0, 1.0)
            self.spin_temperature.setSingleStep(0.1)
            self.spin_temperature.setDecimals(2)
            self.spin_temperature.setValue(float(prefs.get('ai_temperature', 0.0)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_temperature"), self.spin_temperature, 0.0, self.spin_temperature.setValue))

            self.spin_logprob = QDoubleSpinBox()
            self.spin_logprob.setRange(-3.0, 0.0)
            self.spin_logprob.setSingleStep(0.1)
            self.spin_logprob.setDecimals(2)
            self.spin_logprob.setValue(float(prefs.get('ai_logprob_threshold', -1.0)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_logprob"), self.spin_logprob, -1.0, self.spin_logprob.setValue))

            self.spin_no_speech = QDoubleSpinBox()
            self.spin_no_speech.setRange(0.0, 1.0)
            self.spin_no_speech.setSingleStep(0.1)
            self.spin_no_speech.setDecimals(2)
            self.spin_no_speech.setValue(float(prefs.get('ai_no_speech_threshold', 0.2)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_no_speech"), self.spin_no_speech, 0.2, self.spin_no_speech.setValue))

            self.spin_patience = QDoubleSpinBox()
            self.spin_patience.setRange(0.0, 10.0)
            self.spin_patience.setSingleStep(0.1)
            self.spin_patience.setDecimals(2)
            self.spin_patience.setValue(float(prefs.get('ai_patience', 1.0)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_patience"), self.spin_patience, 1.0, self.spin_patience.setValue))

            self.spin_compression = QDoubleSpinBox()
            self.spin_compression.setRange(0.0, 100.0)
            self.spin_compression.setSingleStep(0.1)
            self.spin_compression.setDecimals(2)
            self.spin_compression.setValue(float(prefs.get('ai_compression_ratio_threshold', 10.0)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_compression_ratio"), self.spin_compression, 10.0, self.spin_compression.setValue))

            self.spin_no_repeat = QSpinBox()
            self.spin_no_repeat.setRange(0, 100)
            self.spin_no_repeat.setValue(int(prefs.get('ai_no_repeat_ngram_size', 0)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_no_repeat_ngram"), self.spin_no_repeat, 0, self.spin_no_repeat.setValue))

            self.chk_regroup = ToggleSwitch()
            self.chk_regroup.setChecked(bool(prefs.get('ai_regroup', False)), animated=False)
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_regroup"), self.chk_regroup,
                     False, lambda v: self.chk_regroup.setChecked(v, animated=False)))

            self.chk_suppress_silence = ToggleSwitch()
            self.chk_suppress_silence.setChecked(bool(prefs.get('ai_suppress_silence', False)), animated=False)
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_suppress_silence"), self.chk_suppress_silence,
                     False, lambda v: self.chk_suppress_silence.setChecked(v, animated=False)))

            self.spin_q_levels = QSpinBox()
            self.spin_q_levels.setRange(0, 100)
            self.spin_q_levels.setValue(int(prefs.get('ai_q_levels', 20)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_q_levels"), self.spin_q_levels, 20, self.spin_q_levels.setValue))

            self.spin_k_size = QSpinBox()
            self.spin_k_size.setRange(0, 100)
            self.spin_k_size.setValue(int(prefs.get('ai_k_size', 5)))
            self._advanced_widgets.extend(_add_row(form_whisper, self.txt("lbl_k_size"), self.spin_k_size, 5, self.spin_k_size.setValue))

            l_ai.addLayout(form_whisper)
            l_ai.addStretch()
            _add_page_to_stack(page_ai)

            

            # ─────────────────────────────────────────────────────────────────
        if not is_basic:
                # PAGE 5 — ALGORITHMS
            # ─────────────────────────────────────────────────────────────────
            page_algo = QWidget()
            page_algo.setStyleSheet("background: transparent;")
            l_algo = QVBoxLayout(page_algo)
            l_algo.setContentsMargins(24, 20, 24, 16)
            l_algo.setSpacing(0)
            form_algo = QFormLayout()
            form_algo.setSpacing(14)
            form_algo.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.spin_fuzzy = QSpinBox()
            self.spin_fuzzy.setRange(0, 100)
            self.spin_fuzzy.setSuffix(" %")
            self.spin_fuzzy.setValue(int(prefs.get('algo_fuzzy_threshold', 80)))
            self._advanced_widgets.extend(_add_row(form_algo, self.txt("lbl_algo_fuzzy"), self.spin_fuzzy, 80, self.spin_fuzzy.setValue))

            self.spin_lookahead = QSpinBox()
            self.spin_lookahead.setRange(1, 300)
            self.spin_lookahead.setValue(int(prefs.get('algo_retake_lookahead', 80)))
            self._advanced_widgets.extend(_add_row(form_algo, self.txt("lbl_algo_lookahead"), self.spin_lookahead, 15, self.spin_lookahead.setValue))

            self.spin_penalty = QDoubleSpinBox()
            self.spin_penalty.setRange(0.0, 10.0)
            self.spin_penalty.setSingleStep(0.1)
            self.spin_penalty.setDecimals(1)
            self.spin_penalty.setValue(float(prefs.get('algo_distance_penalty', 2.0)))
            self._advanced_widgets.extend(_add_row(form_algo, self.txt("lbl_algo_penalty"), self.spin_penalty, 2.0, self.spin_penalty.setValue))

            self.spin_anchor = QSpinBox()
            self.spin_anchor.setRange(1, 10)
            self.spin_anchor.setValue(int(prefs.get('algo_anchor_depth', 3)))
            self._advanced_widgets.extend(_add_row(form_algo, self.txt("lbl_algo_anchor"), self.spin_anchor, 3, self.spin_anchor.setValue))

            l_algo.addLayout(form_algo)
            l_algo.addStretch()
            _add_page_to_stack(page_algo)


        # ─────────────────────────────────────────────────────────────────
        if not is_basic:
            # PAGE 1 — AUDIO SYNC
            # ─────────────────────────────────────────────────────────────────
            page_sync = QWidget()
            page_sync.setStyleSheet("background: transparent;")
            l_sync = QVBoxLayout(page_sync)
            l_sync.setContentsMargins(24, 20, 24, 16)
            l_sync.setSpacing(0)
            form_sync = QFormLayout()
            form_sync.setSpacing(14)
            form_sync.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.spin_offset = QDoubleSpinBox()
            self.spin_offset.setRange(-10, 10)
            self.spin_offset.setSingleStep(0.1)
            self.spin_offset.setValue(float(prefs.get('offset', self.DEFAULTS['offset'])))

            self.spin_pad = QDoubleSpinBox()
            self.spin_pad.setRange(0, 5)
            self.spin_pad.setSingleStep(0.1)
            self.spin_pad.setValue(float(prefs.get('pad', self.DEFAULTS['pad'])))

            self.spin_snap = QDoubleSpinBox()
            self.spin_snap.setRange(0, 5)
            self.spin_snap.setSingleStep(0.1)
            self.spin_snap.setValue(float(prefs.get('snap_max', prefs.get('snap_margin', self.DEFAULTS['snap_max']))))

            _add_row(form_sync, self.txt("lbl_offset_s"),   self.spin_offset, self.DEFAULTS['offset'],   self.spin_offset.setValue)
            _add_row(form_sync, self.txt("lbl_padding_s"),  self.spin_pad,    self.DEFAULTS['pad'],       self.spin_pad.setValue)
            _add_row(form_sync, self.txt("lbl_snap_max_s"), self.spin_snap,   self.DEFAULTS['snap_max'],  self.spin_snap.setValue)

            l_sync.addLayout(form_sync)
            l_sync.addStretch()
            _add_page_to_stack(page_sync)



        # ─────────────────────────────────────────────────────────────────
        # PAGE 8 — TELEMETRY
        # ─────────────────────────────────────────────────────────────────
        page_telem = QWidget()
        page_telem.setStyleSheet("background: transparent;")
        l_telem = QVBoxLayout(page_telem)
        l_telem.setContentsMargins(24, 20, 24, 16)
        l_telem.setSpacing(12)

        # Info label
        lbl_telem_info = QLabel(self.txt("msg_telemetry_settings"))
        lbl_telem_info.setWordWrap(True)
        lbl_telem_info.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        l_telem.addWidget(lbl_telem_info)

        form_telem = QFormLayout()
        form_telem.setSpacing(14)
        form_telem.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        user_data = getattr(self.engine.os_doc, 'user_data', {})

        self.chk_telemetry_opt_in = ToggleSwitch()
        self.chk_telemetry_opt_in.setChecked(bool(user_data.get('telemetry_opt_in', False)), animated=False)
        w1 = QWidget()
        l1 = QHBoxLayout(w1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addStretch()
        l1.addWidget(self.chk_telemetry_opt_in)
        _add_row(form_telem, self.txt("chk_telemetry_opt_in"), w1,
                 False, lambda v: self.chk_telemetry_opt_in.setChecked(v, animated=False))

        self.chk_telemetry_geo = ToggleSwitch()
        self.chk_telemetry_geo.setChecked(bool(user_data.get('telemetry_geo', True)), animated=False)
        w2 = QWidget()
        l2 = QHBoxLayout(w2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addStretch()
        l2.addWidget(self.chk_telemetry_geo)
        _add_row(form_telem, self.txt("chk_telemetry_geo"), w2,
                 True, lambda v: self.chk_telemetry_geo.setChecked(v, animated=False))

        l_telem.addLayout(form_telem)
        l_telem.addStretch()
        _add_page_to_stack(page_telem)

        # FIX: Capture the exact UI state right after full construction
        # This prevents false-positive unsaved changes warnings when disk JSON
        # lacks keys that are correctly populated with defaults by the UI.
        self._initial_state = self._get_current_state_dict()

    def _restore_all_defaults(self):
        msg_box = CustomMsgBox(
            self, 
            self.txt('msg_restore_title'), 
            self.txt('msg_restore_desc'), 
            self.txt('btn_yes'), 
            self.txt('btn_no')
        )
        if msg_box.exec() == QDialog.Accepted:
            import config
            old_prefs = self.engine.load_preferences() or {}
            # Build a full default state — start with DEFAULT_SETTINGS then keep
            # lang and settings_view_mode so the UI doesn't switch language/mode.
            default_state = config.DEFAULT_SETTINGS.copy()
            default_state['gui_lang'] = old_prefs.get('gui_lang', 'en')
            default_state['settings_view_mode'] = old_prefs.get('settings_view_mode', 'basic')
            # Save to disk first so subsequent load_preferences() returns defaults
            self.engine.save_preferences(default_state)
            self.initial_prefs = self.engine.load_preferences() or {}
            # Reset all visible widgets to their default values
            self._restore_state_dict(default_state)
            # Clear custom markers
            self.current_custom_markers = []
            CustomMsgBox(self, self.txt('msg_title_settings'), self.txt('msg_restart_required'), self.txt('btn_ok')).exec()
            try:
                self._refresh_markers_list()
            except Exception:
                pass

    # ── Custom Markers helpers ─────────────────────────────────────────────

    def _refresh_markers_list(self):
        """Rebuild the custom marker list widget with inline Edit/Delete buttons."""
        # Clear existing rows (keep the trailing stretch)
        layout = self._markers_layout
        while layout.count() > 1:  # keep the stretch at the end
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_ss = f"""
            QWidget#marker_row {{
                background-color: #1e1e1e;
                border-bottom: 1px solid #2a2a2a;
            }}
            QWidget#marker_row:hover {{
                background-color: #252525;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                background: transparent;
            }}
            QPushButton {{
                background-color: #2d2d2d;
                color: #aaaaaa;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 9pt;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background-color: #383838;
                color: #ffffff;
            }}
            QPushButton#btn_del:hover {{
                background-color: #7a2020;
                border-color: #ed4245;
                color: #ed4245;
            }}
        """

        for idx, m in enumerate(self.current_custom_markers):
            name  = m.get('name', '?')
            color = m.get('color', '')
            hex_col = config.RESOLVE_COLORS_HEX.get(color, '#FFFFFF')

            row_widget = MarkerRowWidget(m, idx)
            row_widget.setObjectName("marker_row")
            row_widget.setStyleSheet(row_ss)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)

            # Color dot indicator
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {hex_col}; font-size: 14pt; background: transparent;")
            dot.setFixedWidth(20)
            row_layout.addWidget(dot)

            # Name + color label
            lbl_name = QLabel(f"{name}")
            lbl_name.setStyleSheet(f"color: {hex_col}; font-weight: bold; background: transparent;")
            row_layout.addWidget(lbl_name, 1)

            lbl_color = QLabel(f"[{self.txt(f'resolve_color_{color.lower()}')}]")
            lbl_color.setStyleSheet(f"color: #666666; font-size: 9pt; background: transparent;")
            row_layout.addWidget(lbl_color)

            # Edit button
            def make_edit(i):
                return lambda checked=False: self._on_edit_marker(i)
            btn_edit = QPushButton(self.txt("btn_edit_marker"))
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(make_edit(idx))
            row_layout.addWidget(btn_edit)

            # Delete button
            def make_del(i):
                return lambda checked=False: self._on_remove_marker_inline(i)
            btn_del = QPushButton("✕")
            btn_del.setObjectName("btn_del")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedWidth(28)
            btn_del.clicked.connect(make_del(idx))
            row_layout.addWidget(btn_del)

            # Insert before stretch
            layout.insertWidget(layout.count() - 1, row_widget)

    def _on_markers_reordered(self, source_idx, target_idx):
        if source_idx == target_idx:
            return
        m = self.current_custom_markers.pop(source_idx)
        # if source_idx < target_idx, target_idx shifted down by 1 due to pop
        if source_idx < target_idx:
            target_idx -= 1
        self.current_custom_markers.insert(target_idx, m)
        self._refresh_markers_list()
        self._save_markers_and_refresh_main()

    def _save_markers_and_refresh_main(self):
        """
        Persist custom_markers immediately (bypassing the Apply button),
        then rebuild the main window's marker sidebar and dynamic shortcuts.
        Markers work like a live database, not a pending settings value.
        """
        prefs = self.engine.load_preferences() or {}
        prefs['custom_markers'] = list(self.current_custom_markers)
        self.engine.save_preferences(prefs)

        # Walk the widget parent hierarchy to find BadWordsGUI
        # (self.parent() alone is not reliable when SettingsDialog is modal)
        w = self
        main_win = None
        while w is not None:
            try:
                if hasattr(w, '_build_marker_radio_buttons') \
                        and hasattr(w, '_apply_dynamic_shortcuts'):
                    main_win = w
                    break
                w = w.parent()
            except RuntimeError:
                break

        if main_win is not None:
            try:
                main_win._build_marker_radio_buttons()
            except Exception:
                pass
            try:
                main_win._apply_dynamic_shortcuts()
            except Exception:
                pass


    def _on_add_marker(self):
        lang = self.engine.load_preferences().get('gui_lang', 'en')
        dlg = MarkerDialog(self, lang, "btn_add_marker")
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            self.current_custom_markers.append({
                "name":  dlg.result_name,
                "color": dlg.result_color,
            })
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()

    def _on_edit_marker(self, idx: int):
        if not (0 <= idx < len(self.current_custom_markers)):
            return
        m = self.current_custom_markers[idx]
        lang = self.engine.load_preferences().get('gui_lang', 'en')
        dlg = MarkerDialog(self, lang, "btn_edit_marker",
                           prefill_name=m.get('name', ''),
                           prefill_color=m.get('color', ''))
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            self.current_custom_markers[idx] = {
                "name":  dlg.result_name,
                "color": dlg.result_color,
            }
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()

    def _on_remove_marker_inline(self, idx: int):
        if 0 <= idx < len(self.current_custom_markers):
            self.current_custom_markers.pop(idx)
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()


    def _on_remove_marker(self):
        """Legacy method — kept for safety but no longer wired to any button."""
        pass

    def _on_export_markers(self):
        """Export custom markers to a JSON file."""
        from PySide6.QtWidgets import QFileDialog
        import json, os

        if not self.current_custom_markers:
            lang = self.engine.load_preferences().get('gui_lang', 'en')
            CustomMsgBox(
                self,
                _txt(lang, 'btn_export_markers'),
                _txt(lang, 'msg_no_markers_to_export'),
                _txt(lang, 'btn_ok'),
            ).exec()
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.txt('btn_export_markers'),
            os.path.expanduser('~/badwords_markers.json'),
            'JSON Files (*.json)',
        )
        if not path:
            return

        data = {
            'version': 1,
            'app': 'BadWords',
            'custom_markers': list(self.current_custom_markers),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            lang = self.engine.load_preferences().get('gui_lang', 'en')
            CustomMsgBox(self, 'Error', str(e), _txt(lang, 'btn_ok')).exec()

    def _on_import_markers(self):
        """Import custom markers from a JSON file (replaces current list)."""
        from PySide6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.txt('btn_import_markers'),
            '',
            'JSON Files (*.json)',
        )
        if not path:
            return

        lang = self.engine.load_preferences().get('gui_lang', 'en')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            CustomMsgBox(self, 'Error', str(e), _txt(lang, 'btn_ok')).exec()
            return

        # Accept both {"custom_markers": [...]} and plain lists
        if isinstance(data, list):
            imported = data
        elif isinstance(data, dict):
            imported = data.get('custom_markers', [])
        else:
            CustomMsgBox(
                self, 'Error', _txt(lang, 'msg_import_invalid_format'), _txt(lang, 'btn_ok')
            ).exec()
            return

        # Validate: each entry must have at least a non-empty 'name'
        valid = []
        for entry in imported:
            if isinstance(entry, dict) and entry.get('name', '').strip():
                valid.append({
                    'name':  entry['name'].strip(),
                    'color': entry.get('color', 'Blue'),
                })

        if not valid:
            CustomMsgBox(
                self, 'Error', _txt(lang, 'msg_import_no_valid_markers'), _txt(lang, 'btn_ok')
            ).exec()
            return

        self.current_custom_markers = valid
        self._refresh_markers_list()
        self._refresh_custom_marker_shortcuts()
        self._save_markers_and_refresh_main()


    def _refresh_custom_marker_shortcuts(self):
        """
        Rebuilds the custom-marker shortcut rows in the unified Shortcuts form.
        Uses insertRow(pos) / removeRow(pos) on the single QFormLayout so all
        rows always have identical 14px spacing — no separate widget needed.
        """
        form       = getattr(self, '_custom_sc_unified', None)
        make_fn    = getattr(self, '_make_shortcut_widgets_fn', None)
        check_fn   = getattr(self, '_check_shortcut_conflicts_fn', None)
        insert_pos = getattr(self, '_custom_sc_insert_pos', None)

        if form is None or make_fn is None or check_fn is None or insert_pos is None:
            return

        # ── Remove previous custom rows ─────────────────────────────────────
        old_count = len(getattr(self, 'custom_marker_shortcut_inputs', {}))
        for _ in range(old_count):
            # Always remove at the same index; rows shift up after each removal
            try:
                form.removeRow(insert_pos)
            except Exception:
                break

        self.custom_marker_shortcut_inputs = {}

        # ── Insert new custom rows at insert_pos ────────────────────────────
        prefs = self.engine.load_preferences() or {}
        saved_shortcuts = prefs.get('shortcuts', {})
        markers = getattr(self, 'current_custom_markers', [])

        for i, m in enumerate(markers):
            name = m.get('name', '')
            if not name:
                continue
            s_key = f'custom_marker_{name}'

            fmt = self.txt('shortcut_custom_marker_fmt')
            label_text = fmt.format(name=name) if fmt != 'shortcut_custom_marker_fmt' \
                         else f'Switch to "{name}" Marker'

            current_seq = saved_shortcuts.get(s_key, '')
            widget = ShortcutCaptureButton(str(current_seq), display_only=False)
            widget.sequence_changed.connect(lambda _seq, _w=widget: check_fn())

            def make_setter(w, check):
                def _setter(v):
                    w.set_sequence(str(v))
                    check()
                return _setter

            lbl, container = make_fn(label_text, widget, '',
                                     make_setter(widget, check_fn),
                                     is_display=False)
            form.insertRow(insert_pos + i, lbl, container)
            self.custom_marker_shortcut_inputs[s_key] = widget

        check_fn()


    def _update_preview(self):

        ff = self.combo_font.currentText()
        fs = self.spin_fsize.value()
        lh = self.spin_lheight.value()
        self.lbl_preview.setStyleSheet(f"""
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: {config.FG_COLOR};
            font-family: "{ff}";
            font-size: {fs}pt;
            padding: 12px 14px;
        """)
        px_size = int(fs * 1.33)
        total_lh = px_size + lh
        preview_text = self.txt("lbl_font_preview")
        self.lbl_preview.setText(
            f'<div style="line-height: {total_lh}px; text-align: left;">{preview_text}</div>'
        )

    # ── Export / Import ───────────────────────────────────────────────────

    def _on_export_settings(self):
        import shutil
        from PySide6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(
            self, self.txt("btn_export_settings"), "badwords_settings.json",
            "JSON files (*.json)"
        )
        if dest:
            try:
                shutil.copy2(self.engine.os_doc.settings_file, dest)
            except Exception as e:
                from osdoc import log_error
                log_error(f"Export settings failed: {e}")

    def _on_import_settings(self):
        import shutil
        from PySide6.QtWidgets import QFileDialog
        src, _ = QFileDialog.getOpenFileName(
            self, self.txt("btn_import_settings"), "",
            "JSON files (*.json)"
        )
        if not src:
            return
        try:
            shutil.copy2(src, self.engine.os_doc.settings_file)
            self.engine.os_doc.settings = self.engine.os_doc.load_settings()
        except Exception as e:
            from osdoc import log_error
            log_error(f"Import settings failed: {e}")
            return

        target = config.TRANS.get('en', config.TRANS['en'])
        CustomMsgBox(
            self,
            target.get('msg_title_language_changed', 'Restart Required'),
            target.get('msg_restart_lang', 'Settings imported. Please restart BadWords to apply all changes.'),
            target.get('btn_ok', 'OK')
        ).exec()
        self.reject()


    # ── Smart Apply ───────────────────────────────────────────────────────

    def _safe_get(self, attr_name, default_val, method_name="value"):
        """Safely extracts a value from a widget, avoiding PySide6 dead C++ object errors."""
        try:
            widget = getattr(self, attr_name)
            return getattr(widget, method_name)()
        except (RuntimeError, AttributeError):
            return default_val

    def _get_current_state_dict(self):
        old_prefs = self.engine.load_preferences() or {}
        is_basic = old_prefs.get('settings_view_mode', 'basic') == 'basic'
        
        try:
            checked_btn = self.icon_group.checkedButton()
            icon_val = checked_btn.property("icon_name") if checked_btn else "default"
        except (RuntimeError, AttributeError):
            icon_val = old_prefs.get('app_icon', 'default')

        try:
            val = self.dropdown_lang.text()
            lang_code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), old_prefs.get('gui_lang', 'en'))
        except (RuntimeError, AttributeError):
            lang_code = old_prefs.get('gui_lang', 'en')
            
        view_mode_val = self._safe_get('combo_view', '', 'currentText')
        view_mode = 'segmented' if view_mode_val == self.txt("opt_segmented_blocks") else ('continuous' if view_mode_val else old_prefs.get('view_mode', 'segmented'))

        try:
            shortcuts_dict = {k: v.get_sequence() for k, v in self.shortcut_inputs.items()}
            # Merge in custom marker shortcuts
            for k, v in getattr(self, 'custom_marker_shortcut_inputs', {}).items():
                shortcuts_dict[k] = v.get_sequence()
        except (RuntimeError, AttributeError):
            shortcuts_dict = old_prefs.get('shortcuts', {})


        try:
            hidden_panels_val = sorted(self.dropdown_hidden.selected_items)
        except (RuntimeError, AttributeError):
            hidden_panels_val = old_prefs.get('hidden_panels', [])

        state = {
            'gui_lang':           lang_code,
            'settings_view_mode': old_prefs.get('settings_view_mode', 'basic'),
            'offset':             self._safe_get('spin_offset', old_prefs.get('offset', 0.0), 'value'),
            'pad':                self._safe_get('spin_pad', old_prefs.get('pad', 0.0), 'value'),
            'snap_max':           self._safe_get('spin_snap', old_prefs.get('snap_max', 0.0), 'value'),
            'app_icon':           icon_val,
            'shortcuts':          shortcuts_dict,
            'custom_markers':     getattr(self, 'current_custom_markers', old_prefs.get('custom_markers', [])),
            'telemetry_opt_in':   self._safe_get('chk_telemetry_opt_in', old_prefs.get('telemetry_opt_in', False), 'isChecked'),
            'telemetry_geo':      self._safe_get('chk_telemetry_geo', old_prefs.get('telemetry_geo', False), 'isChecked'),
            'view_mode':          view_mode,
            'editor_font_family': self._safe_get('combo_font', old_prefs.get('editor_font_family', 'Segoe UI'), 'currentText'),
            'editor_font_size':   self._safe_get('spin_fsize', old_prefs.get('editor_font_size', 12), 'value'),
            'editor_line_height': self._safe_get('spin_lheight', old_prefs.get('editor_line_height', 12), 'value'),
            'sync_davinci_chapter': self._safe_get('chk_sync_davinci', old_prefs.get('sync_davinci_chapter', True), 'isChecked'),
            'timestamp_precise':    self._safe_get('tgl_timestamp_precise', old_prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'isChecked'),
        }
        
        if not is_basic:
            state.update({
                'always_on_top':      self._safe_get('chk_ontop', old_prefs.get('always_on_top', False), 'isChecked'),
                'hidden_panels':      hidden_panels_val,
                'accent_color':       self._safe_get('dropdown_accent', old_prefs.get('accent_color', 'green'), 'currentText'),
                'device':             self._safe_get('dropdown_device', old_prefs.get('device', 'auto').capitalize(), 'currentText').lower(),
                'ai_compute_type':    self._safe_get('dropdown_compute', old_prefs.get('ai_compute_type', 'Auto'), 'currentText'),
                'ai_initial_prompt':  self._safe_get('textedit_prompt', old_prefs.get('ai_initial_prompt', ''), 'toPlainText'),
                'chunk_max_words':    self._safe_get('spin_chunk_max', old_prefs.get('chunk_max_words', 30), 'value'),
                'chunk_lookahead':    self._safe_get('spin_chunk_look', old_prefs.get('chunk_lookahead', 3), 'value'),
                'chunk_min_chars':    self._safe_get('spin_chunk_min', old_prefs.get('chunk_min_chars', 7), 'value'),
                'algo_fuzzy_threshold':  self._safe_get('spin_fuzzy', old_prefs.get('algo_fuzzy_threshold', 80), 'value'),
                'algo_retake_lookahead': self._safe_get('spin_lookahead', old_prefs.get('algo_retake_lookahead', 80), 'value'),
                'algo_distance_penalty': self._safe_get('spin_penalty', old_prefs.get('algo_distance_penalty', 2.0), 'value'),
                'algo_anchor_depth':     self._safe_get('spin_anchor', old_prefs.get('algo_anchor_depth', 3), 'value'),
                'ai_vad_filter':            self._safe_get('chk_vad_filter', old_prefs.get('ai_vad_filter', False), 'isChecked'),
                'ai_beam_size':             self._safe_get('spin_beam_size', old_prefs.get('ai_beam_size', 1), 'value'),
                'ai_temperature':           self._safe_get('spin_temperature', old_prefs.get('ai_temperature', 0.0), 'value'),
                'ai_condition_on_prev':     self._safe_get('chk_condition_prev', old_prefs.get('ai_condition_on_prev', False), 'isChecked'),
                'ai_logprob_threshold':     self._safe_get('spin_logprob', old_prefs.get('ai_logprob_threshold', -1.0), 'value'),
                'ai_no_speech_threshold':   self._safe_get('spin_no_speech', old_prefs.get('ai_no_speech_threshold', 0.2), 'value'),
                'ai_patience':              self._safe_get('spin_patience', old_prefs.get('ai_patience', 1.0), 'value'),
                'ai_compression_ratio_threshold': self._safe_get('spin_compression', old_prefs.get('ai_compression_ratio_threshold', 10.0), 'value'),
                'ai_no_repeat_ngram_size':  self._safe_get('spin_no_repeat', old_prefs.get('ai_no_repeat_ngram_size', 0), 'value'),
                'ai_regroup':               self._safe_get('chk_regroup', old_prefs.get('ai_regroup', False), 'isChecked'),
                'ai_suppress_silence':      self._safe_get('chk_suppress_silence', old_prefs.get('ai_suppress_silence', False), 'isChecked'),
                'ai_q_levels':              self._safe_get('spin_q_levels', old_prefs.get('ai_q_levels', 20), 'value'),
                'ai_k_size':                self._safe_get('spin_k_size', old_prefs.get('ai_k_size', 5), 'value'),
            })
        else:
            advanced_keys = ["always_on_top", "hidden_panels", "accent_color", "device", "ai_compute_type", "ai_initial_prompt", "chunk_max_words", "chunk_lookahead", "chunk_min_chars", "algo_fuzzy_threshold", "algo_retake_lookahead", "algo_distance_penalty", "algo_anchor_depth", "ai_vad_filter", "ai_beam_size", "ai_temperature", "ai_condition_on_prev", "ai_logprob_threshold", "ai_no_speech_threshold", "ai_patience", "ai_compression_ratio_threshold", "ai_no_repeat_ngram_size", "ai_regroup", "ai_suppress_silence", "ai_q_levels", "ai_k_size"]
            for key in advanced_keys:
                if key in old_prefs:
                    state[key] = old_prefs[key]
        return state

    def _safe_set(self, attr_name, value, method_name="setValue"):
        """Safely sets a value on a widget, avoiding dead objects or missing attributes."""
        try:
            if hasattr(self, attr_name):
                widget = getattr(self, attr_name)
                getattr(widget, method_name)(value)
        except (RuntimeError, AttributeError):
            pass

    def _restore_state_dict(self, state):
        is_basic = state.get('settings_view_mode', 'basic') == 'basic'
        
        self._safe_set('spin_offset', state.get('offset', 0.0), 'setValue')
        self._safe_set('spin_pad', state.get('pad', 0.0), 'setValue')
        self._safe_set('spin_snap', state.get('snap_max', 0.0), 'setValue')
        self._safe_set('chk_telemetry_opt_in', state.get('telemetry_opt_in', False), 'setChecked')
        self._safe_set('chk_telemetry_geo', state.get('telemetry_geo', False), 'setChecked')
        
        try:
            if hasattr(self, 'icon_group'):
                icon_name = state.get('app_icon', 'default')
                for btn in self.icon_group.buttons():
                    if btn.property("icon_name") == icon_name:
                        btn.setChecked(True)
                        break
        except RuntimeError:
            pass
                
        try:
            lang_code = state.get('gui_lang', 'en')
            self._safe_set('dropdown_lang', config.SUPPORTED_LANGS.get(lang_code, 'English'), 'setText')
        except Exception:
            pass
        
        view_mode = state.get('view_mode', 'segmented')
        self._safe_set('combo_view', self.txt("opt_segmented_blocks") if view_mode == 'segmented' else self.txt("opt_continuous_flow"), 'setText')
        self._safe_set('combo_font', state.get('editor_font_family', 'Segoe UI'), 'setText')
        self._safe_set('spin_fsize', state.get('editor_font_size', 12), 'setValue')
        self._safe_set('spin_lheight', state.get('editor_line_height', 12), 'setValue')
        
        self.current_custom_markers = state.get('custom_markers', [])
        try:
            if hasattr(self, '_refresh_markers_list'):
                self._refresh_markers_list()
        except RuntimeError:
            pass
        
        try:
            from PySide6.QtGui import QKeySequence
            if hasattr(self, 'shortcut_inputs'):
                for k, v in state.get('shortcuts', {}).items():
                    if k in self.shortcut_inputs:
                        self.shortcut_inputs[k].set_sequence(v)
        except RuntimeError:
            pass
                
        self._safe_set('chk_sync_davinci', state.get('sync_davinci_chapter', True), 'setChecked')
        self._safe_set('tgl_timestamp_precise', state.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'setChecked')
        
        if not is_basic:
            self._safe_set('chk_ontop', state.get('always_on_top', False), 'setChecked')
            try:
                if hasattr(self, 'dropdown_hidden'):
                    self.dropdown_hidden.selected_items = set(state.get('hidden_panels', []))
                    self.dropdown_hidden.setText(", ".join(sorted(state.get('hidden_panels', []))) if state.get('hidden_panels') else self.txt("txt_select"))
            except RuntimeError:
                pass
            
            self._safe_set('dropdown_accent', state.get('accent_color', 'green'), 'setText')
            self._safe_set('dropdown_device', state.get('device', 'Auto').capitalize(), 'setText')
            self._safe_set('dropdown_compute', state.get('ai_compute_type', 'Auto'), 'setText')
            self._safe_set('textedit_prompt', state.get('ai_initial_prompt', ''), 'setPlainText')
            self._safe_set('spin_chunk_max', state.get('chunk_max_words', 30), 'setValue')
            self._safe_set('spin_chunk_look', state.get('chunk_lookahead', 3), 'setValue')
            self._safe_set('spin_chunk_min', state.get('chunk_min_chars', 7), 'setValue')
            self._safe_set('chk_vad_filter', state.get('ai_vad_filter', False), 'setChecked')
            self._safe_set('spin_beam_size', state.get('ai_beam_size', 1), 'setValue')
            self._safe_set('spin_temperature', state.get('ai_temperature', 0.0), 'setValue')
            self._safe_set('chk_condition_prev', state.get('ai_condition_on_prev', False), 'setChecked')
            self._safe_set('spin_logprob', state.get('ai_logprob_threshold', -1.0), 'setValue')
            self._safe_set('spin_no_speech', state.get('ai_no_speech_threshold', 0.2), 'setValue')
            self._safe_set('spin_patience', state.get('ai_patience', 1.0), 'setValue')
            self._safe_set('spin_compression', state.get('ai_compression_ratio_threshold', 10.0), 'setValue')
            self._safe_set('spin_no_repeat', state.get('ai_no_repeat_ngram_size', 0), 'setValue')
            self._safe_set('chk_regroup', state.get('ai_regroup', False), 'setChecked')
            self._safe_set('chk_suppress_silence', state.get('ai_suppress_silence', False), 'setChecked')
            self._safe_set('spin_q_levels', state.get('ai_q_levels', 20), 'setValue')
            self._safe_set('spin_k_size', state.get('ai_k_size', 5), 'setValue')
            self._safe_set('spin_fuzzy', state.get('algo_fuzzy_threshold', 80), 'setValue')
            self._safe_set('spin_lookahead', state.get('algo_retake_lookahead', 80), 'setValue')
            self._safe_set('spin_penalty', state.get('algo_distance_penalty', 2.0), 'setValue')
            self._safe_set('spin_anchor', state.get('algo_anchor_depth', 3), 'setValue')

    def _apply_settings(self):
        old_prefs = self.engine.load_preferences() or {}
        new_prefs = self._get_current_state_dict()
        
        selected_device  = new_prefs.get('device', 'auto')
        selected_compute = new_prefs.get('ai_compute_type', 'Auto')
        old_compute      = old_prefs.get('ai_compute_type', 'Auto')
        old_device       = old_prefs.get('device', 'auto')

        compute_changed = (selected_compute != old_compute) or (selected_device != old_device)
        if selected_compute.lower() != 'auto' and compute_changed:
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                is_supported = self.engine.verify_hardware_compute(selected_device, selected_compute)
            finally:
                QApplication.restoreOverrideCursor()

            if not is_supported:
                CustomMsgBox(self, self.txt('msg_compute_fail_title'), self.txt('msg_compute_fail_desc'), self.txt('btn_close')).exec()
                return

        restart_needed = any(
            new_prefs.get(k) != old_prefs.get(k)
            for k in config.RESTART_REQUIRED_KEYS
            if k in new_prefs
        )

        self.engine.save_preferences(new_prefs)
        self.initial_prefs = self.engine.load_preferences() or {}
        self._initial_state = self._get_current_state_dict()
        self.btn_apply.setText(self.txt("txt_saved"))
        self.btn_apply.setStyleSheet(f"background-color: #1a7a3e; color: white;")
        from PySide6.QtCore import QTimer
        def restore_btn():
            self.btn_apply.setText(self.txt("btn_apply"))
            self.btn_apply.setStyleSheet("") # Przywraca domyślny arkusz CSS
        QTimer.singleShot(1500, restore_btn)

        main_win = self.parent()
        if hasattr(main_win, 'text_canvas'):
            main_win.text_canvas._calculate_layout()
            main_win.text_canvas.update()

        aot_changed = new_prefs.get('always_on_top', False) != bool(old_prefs.get('always_on_top', False))
        if aot_changed and main_win:
            if new_prefs.get('always_on_top'):
                main_win.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            else:
                main_win.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            main_win.show()

        if restart_needed:
            lang = old_prefs.get('gui_lang', 'en')
            target = config.TRANS.get(lang, config.TRANS['en'])
            CustomMsgBox(
                self,
                target.get('tool_settings', 'Settings'),
                target.get('msg_restart_required', 'Changes applied. Full effect will be visible on next launch.'),
                target.get('btn_ok', 'OK')
            ).exec()

    def reject(self):
        # FIX: Validate against the exact snapshot of how the UI was built
        # rather than the raw preferences file which may be missing keys.
        old_prefs = getattr(self, '_initial_state', self.engine.load_preferences() or {})
        new_prefs = self._get_current_state_dict()
        diff = {}
        for k, new_val in new_prefs.items():
            old_val = old_prefs.get(k)
            if old_val is None:
                if k == 'app_icon': old_val = 'default'
                elif k == 'gui_lang': old_val = 'en'
                elif k == 'hidden_panels': old_val = []
                elif k == 'custom_markers': old_val = []
            
            if k == 'shortcuts':
                old_dict = old_val if old_val is not None else {}
                for sub_k, sub_new in new_val.items():
                    sub_old = old_dict.get(sub_k, '')
                    if sub_old != sub_new:
                        diff[f"shortcuts.{sub_k}"] = (sub_old, sub_new)
            else:
                if str(new_val) != str(old_val) and new_val != old_val:
                    diff[k] = (old_val, new_val)
                
        if diff:
            key_name_map = {
                'shortcuts': f"{self.txt('tab_shortcuts')}",
                'gui_lang': f"{self.txt('tab_general')}: {self.txt('lbl_language')}",
                'app_icon': f"{self.txt('tab_general')}: {self.txt('lbl_app_icon')}",
                'offset': f"{self.txt('tab_audio_sync')}: {self.txt('lbl_offset_s')}",
                'pad': f"{self.txt('tab_audio_sync')}: {self.txt('lbl_padding_s')}",
                'snap_max': f"{self.txt('tab_audio_sync')}: {self.txt('lbl_snap_max_s')}",
                'view_mode': f"{self.txt('tab_transcript')}: {self.txt('lbl_display_mode')}",
                'editor_font_family': f"{self.txt('tab_transcript')}: {self.txt('lbl_transcript_font')}",
                'editor_font_size': f"{self.txt('tab_transcript')}: {self.txt('lbl_font_size_pt')}",
                'editor_line_height': f"{self.txt('tab_transcript')}: {self.txt('lbl_line_spacing_px')}",
                'chunk_max_words': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_max_words')}",
                'chunk_lookahead': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_lookahead')}",
                'chunk_min_chars': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_min_chars')}",
                'always_on_top': f"{self.txt('tab_interface')}: {self.txt('lbl_always_on_top')}",
                'hidden_panels': f"{self.txt('tab_interface')}: {self.txt('lbl_hidden_panels')}",
                'accent_color': f"{self.txt('tab_interface')}: {self.txt('lbl_accent_color')}",
                'sync_davinci_chapter': f"{self.txt('tab_transcript')}: {self.txt('chk_sync_davinci')}",
                'timestamp_precise':    f"{self.txt('tab_transcript')}: {self.txt('lbl_timestamp_precise')}",
                'device': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_device')}",
                'ai_compute_type': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_compute_type')}",
                'ai_initial_prompt': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_initial_prompt')}",
                'algo_fuzzy_threshold': f"{self.txt('tab_algorithms')}: {self.txt('lbl_algo_fuzzy')}",
                'algo_retake_lookahead': f"{self.txt('tab_algorithms')}: {self.txt('lbl_algo_lookahead')}",
                'algo_distance_penalty': f"{self.txt('tab_algorithms')}: {self.txt('lbl_algo_penalty')}",
                'algo_anchor_depth': f"{self.txt('tab_algorithms')}: {self.txt('lbl_algo_anchor')}",
                'telemetry_opt_in': f"{self.txt('tab_telemetry')}: {self.txt('chk_telemetry_opt_in')}",
                'telemetry_geo': f"{self.txt('tab_telemetry')}: {self.txt('chk_telemetry_geo')}",
                'custom_markers': self.txt('tab_custom_markers')
            }
            
            # Map dynamic shortcut composite keys
            for diff_k in diff.keys():
                if diff_k.startswith('shortcuts.'):
                    sub_k = diff_k.split('.', 1)[1]
                    sub_name = self.txt(f"shortcut_{sub_k}")
                    if sub_name == f"shortcut_{sub_k}": # Fallback if not translated
                        sub_name = sub_k.replace('_', ' ').title()
                    key_name_map[diff_k] = f"{self.txt('tab_shortcuts')}: {sub_name}"
            
            dlg = UnsavedChangesDialog(self, diff, key_name_map)
            if dlg.exec() == QDialog.Accepted:
                save_needed = False
                for k, action in dlg.decisions.items():
                    if action == 'discard':
                        if k.startswith('shortcuts.'):
                            sub_k = k.split('.', 1)[1]
                            new_prefs['shortcuts'][sub_k] = diff[k][0]
                        else:
                            new_prefs[k] = diff[k][0] 
                    else:
                        save_needed = True
                
                self._restore_state_dict(new_prefs)
                
                if save_needed:
                    self._apply_settings()
                super().reject()
            else:
                return 
        else:
            super().reject()


# ==========================================
# CLASS 3: MAIN APPLICATION WINDOW
# ==========================================

class BadWordsGUI(FramelessWindowMixin, QMainWindow):
    """
    Stage 3 — QMainWindow implementing the "VS Code" unified workspace:
      - Opens maximized on the monitor under the cursor
      - NO top toolbar; left and right vertical activity bars instead
      - QStackedWidget as the central widget (3 pages)
        Page 0: Welcome / Config   (flat, borderless — default view)
        Page 1: Processing         (progress placeholder)
        Page 2: Editor             (editor placeholder)
      - Right dock starts hidden; revealed when analysis begins
      - CSD: frameless window with CustomTitleBar and native-feeling behaviour
    """

    def __init__(self, engine, resolve_handler, parent=None):
        super().__init__(parent)

        # ── CSD: remove native frame, enable translucency ──────────────────
        self.frameless_init(is_popup=False)

        self.engine              = engine
        self.resolve_handler     = resolve_handler
        # This callback is injected by AppController in main.py
        self.closeEvent_callback = None
        self._chapters = []
        self._current_chapter_idx = -1
        self.shared_tooltip = IDETooltip()
        self.shared_tooltip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.shared_tooltip.setWindowFlag(Qt.WindowTransparentForInput, True)
        
        # Install global app filter to route all tooltips through IDETooltip and handle globals
        self._global_app_filter = GlobalAppFilter(self.shared_tooltip)
        QApplication.instance().installEventFilter(self._global_app_filter)
        
        # Declare panel containers early for Pyre inference
        self._sidebar_right: SidebarFrame = None
        self._panel_left: QFrame = None
        self._panel_right: QFrame = None

        # --- Language preference ---
        prefs     = engine.load_preferences() or {}
        self.lang = prefs.get("gui_lang", "en")
        if self.lang not in config.TRANS:
            self.lang = "en"

        # --- Window basics ---
        self.setWindowTitle(config.TRANS[self.lang].get("title", config.APP_NAME))
        self.setWindowIcon(_app_icon())
        self.resize(config.CFG_WINDOW_W_BASE, config.CFG_WINDOW_H_BASE)
        self.setMinimumSize(config.CFG_WINDOW_W_BASE, 400)
        # NOTE: force_dark_titlebar removed — CSD owns the title bar.

        # --- Global QSS ---
        self.setStyleSheet(f"""
            * {{ outline: none; }}
            QMainWindow {{
                background-color: transparent;
            }}
            QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
            }}
            /* ---- Scrollbars (global) ---- */
            QScrollBar:vertical {{
                background: {config.SCROLL_BG};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.SCROLL_FG};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.SCROLL_ACTIVE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        # ── CSD: root frame (wraps title bar + content, owns border-radius) ──
        self._root_frame = QFrame()
        self._root_frame.setObjectName("RootFrame")
        _is_mac_root = platform.system() == "Darwin"
        _root_radius = "0px" if _is_mac_root else "12px"
        self._root_frame.setStyleSheet(f"""
            QFrame#RootFrame {{
                background-color: {config.BG_COLOR};
                border-radius: {_root_radius};
            }}
        """)
        self._root_layout = QVBoxLayout(self._root_frame)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # ── CSD: custom title bar ───────────────────────────────────────
        self._title_bar = CustomTitleBar(self, self.lang, parent=self._root_frame)
        self._title_bar.chapter_dropdown.valueChanged.connect(self._switch_chapter)
        self._root_layout.addWidget(self._title_bar)

        # On macOS: hide custom CSD title bar — native title bar handles close/min/max/fullscreen.
        # The native window title is set to show source timeline info (updated dynamically).
        if _is_mac_root:
            self._title_bar.setVisible(False)
            self._title_bar.setFixedHeight(0)

        # --- Build UI --- (sidebars + central workspace sit below title bar)
        self._build_sidebars()         # left + right activity frames
        self._build_central_workspace() # QStackedWidget central area + panels


        self.search_overlay = SearchOverlayWidget(self.scroll_area, self)

        self.undo_manager = UndoManager(self, self.text_canvas)
        self._setup_hardcoded_shortcuts()

        self._active_shortcuts = []  # track dynamic QShortcuts for cleanup
        self._apply_dynamic_shortcuts()

        # --- Maximize on the monitor the cursor is on ---
        self._maximize_on_active_screen()

        # --- Telemetry check fires 500 ms after first paint ---
        QTimer.singleShot(500, self.check_telemetry)

        # --- Populate timeline/track dropdowns synchronously since Resolve API is fast ---
        self._populate_timeline_track_combos()
        
        self._bind_prefs()

    def _save_single_pref(self, key: str, value):
        prefs = self.engine.load_preferences() or {}
        prefs[key] = value
        self.engine.save_preferences(prefs)

    def _bind_prefs(self):
        prefs = self.engine.load_preferences() or {}
        
        toggles = [
            ('ui_tgl_silence_cut', 'tgl_silence_cut'),
            ('ui_tgl_silence_mark', 'tgl_silence_mark'),
            ('ui_tgl_show_inaudible', 'tgl_show_inaudible'),
            ('ui_tgl_mark_inaudible', 'tgl_mark_inaudible'),
            ('ui_tgl_show_typos', 'tgl_show_typos'),
            ('ui_tgl_ripple_delete', 'tgl_ripple_delete')
        ]
        
        for key, attr_name in toggles:
            if hasattr(self, attr_name):
                toggle = getattr(self, attr_name)
                if key in prefs:
                    toggle.setChecked(prefs[key], animated=False)
                toggle.toggled.connect(lambda v, k=key: self._save_single_pref(k, v))
                
        if hasattr(self, 'spin_thresh'):
            if 'silence_threshold_db' in prefs:
                self.spin_thresh.setText(str(prefs['silence_threshold_db']))
            elif 'ui_spin_thresh' in prefs:
                self.spin_thresh.setText(str(prefs['ui_spin_thresh']))
            self.spin_thresh.editingFinished.connect(
                lambda: self._save_single_pref('silence_threshold_db',
                    float(self.spin_thresh.text().replace(',', '.') or -42.0))
            )

        if hasattr(self, 'spin_pad'):
            if 'ui_spin_pad' in prefs:
                self.spin_pad.setText(str(prefs['ui_spin_pad']))
            self.spin_pad.editingFinished.connect(
                lambda: self._save_single_pref('ui_spin_pad',
                    float(self.spin_pad.text().replace(',', '.') or 0.05))
            )

        if hasattr(self, 'spin_silence_min_dur'):
            if 'silence_min_dur' in prefs:
                self.spin_silence_min_dur.setText(str(prefs['silence_min_dur']))
            self.spin_silence_min_dur.editingFinished.connect(
                lambda: self._save_single_pref('silence_min_dur',
                    float(self.spin_silence_min_dur.text().replace(',', '.') or 0.2))
            )

        
        # Restore pinned favorites
        for fav_id in prefs.get('favorites', []):
            if fav_id in self._pin_buttons:
                self._pin_buttons[fav_id].setStyleSheet("QPushButton { background: transparent; border: none; color: #eebb00; font-size: 11pt; padding: 0; } QPushButton:hover { color: #ffcc00; }")
                self._pin_buttons[fav_id].click()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_sidebars(self):
        """
        Left and right vertical activity frames overlaying the main window.
        """
        self._sidebar_left = QFrame(self)
        self._sidebar_left.setFixedWidth(50)
        self._sidebar_left.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        left_layout = QVBoxLayout(self._sidebar_left)
        left_layout.setContentsMargins(5, 6, 5, 6)
        left_layout.setSpacing(6)
        
        self._drag_zone_left = SidebarDragZone(self._sidebar_left)
        drag_layout_left = self._drag_zone_left.layout()
        left_layout.addWidget(self._drag_zone_left)
        
        self.btn_nav_script = SidebarButton("\U0001f4dd", self.txt("tool_script_analysis"), "script_analysis", tooltip_widget=self.shared_tooltip)
        self.btn_nav_script.clicked.connect(lambda: self._toggle_activity("script_analysis"))
        drag_layout_left.addWidget(self.btn_nav_script)
        
        self.btn_nav_silence = SidebarButton("\U0001f507", self.txt("tool_silence"), "silence", tooltip_widget=self.shared_tooltip)
        self.btn_nav_silence.clicked.connect(lambda: self._toggle_activity("silence"))
        drag_layout_left.addWidget(self.btn_nav_silence)

        self.btn_nav_fillers = SidebarButton("\U0001f4ac", self.txt("tool_filler_words"), "fillers", tooltip_widget=self.shared_tooltip)
        self.btn_nav_fillers.clicked.connect(lambda: self._toggle_activity("fillers"))
        drag_layout_left.addWidget(self.btn_nav_fillers)
        
        self.btn_nav_settings = SidebarButton("\u2699", self.txt("tool_settings"), "settings", tooltip_widget=self.shared_tooltip, is_draggable=False)
        self.btn_nav_settings.clicked.connect(self._on_settings)
        left_layout.addWidget(self.btn_nav_settings)
        
        self._sidebar_left.show()

        self._sidebar_right = QFrame(self)
        self._sidebar_right.setFixedWidth(50)
        self._sidebar_right.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        right_layout = QVBoxLayout(self._sidebar_right)
        right_layout.setContentsMargins(5, 6, 5, 6)
        right_layout.setSpacing(6)
        
        self._drag_zone_right = SidebarDragZone(self._sidebar_right)
        drag_layout_right = self._drag_zone_right.layout()
        right_layout.addWidget(self._drag_zone_right)
        
        self.btn_nav_main = SidebarButton("\U0001f6e0\ufe0f", self.txt("tool_main_panel"), "main_panel", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_main.clicked.connect(lambda: self._toggle_activity("main_panel"))
        drag_layout_right.addWidget(self.btn_nav_main)
        
        self.btn_nav_assembly = SidebarButton("\u2699\ufe0f", self.txt("tool_assembly"), "assembly", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_assembly.clicked.connect(lambda: self._toggle_activity("assembly"))
        drag_layout_right.addWidget(self.btn_nav_assembly)

        self._restore_sidebar_layout()
        
    def _build_central_workspace(self):
        """
        Main container incorporating sidebars, panels, and central stack using QHBoxLayout.
        """
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Build Panels
        self._panel_left = QFrame()
        self._panel_left.setMinimumWidth(150)
        self._panel_left.setObjectName("leftPanel")
        self._panel_left.setStyleSheet("QFrame#leftPanel { background: transparent; } QFrame#ActivityPanel { background-color: #212121; border-radius: 6px; }")
        QVBoxLayout(self._panel_left).setContentsMargins(0, 0, 0, 0)
        self._panel_left.hide()

        self._stack = QStackedWidget()
        self._stack.setObjectName("stack")
        self._stack.setStyleSheet(f"QStackedWidget#stack {{ background-color: {config.BG_COLOR}; }}")
        self._stack.addWidget(self._build_welcome_screen())   # index 0
        self._stack.addWidget(self._build_page_processing())  # index 1
        self._stack.addWidget(self._build_page_editor())      # index 2
        self._stack.setCurrentIndex(0)

        self._panel_right = QFrame()
        self._panel_right.setMinimumWidth(150)
        self._panel_right.setObjectName("rightPanel")
        self._panel_right.setStyleSheet("QFrame#rightPanel { background: transparent; } QFrame#ActivityPanel { background-color: #212121; border-radius: 6px; }")
        QVBoxLayout(self._panel_right).setContentsMargins(0, 0, 0, 0)
        self._panel_right.hide()
        
        self.activities = {}
        self.active_activity = None
        self._build_activities()

        # Splitter layout for panels and stack
        self._main_h_splitter = GripSplitter(Qt.Horizontal)
        self._main_h_splitter.setChildrenCollapsible(False)
        self._main_h_splitter.addWidget(self._panel_left)
        self._main_h_splitter.addWidget(self._stack)
        self._main_h_splitter.addWidget(self._panel_right)
        self._main_h_splitter.setStretchFactor(0, 0)
        self._main_h_splitter.setStretchFactor(1, 1)
        self._main_h_splitter.setStretchFactor(2, 0)
        self._main_h_splitter.setHandleWidth(10)
        self._main_h_splitter.setStyleSheet("QSplitter { border: none; background: transparent; }")

        # Add everything to main layout in exact order
        main_layout.addWidget(self._sidebar_left)
        main_layout.addWidget(self._main_h_splitter)
        main_layout.addWidget(self._sidebar_right)

        # ── CSD: add content area under the title bar in the root frame ───────
        self._root_layout.addWidget(main_container)
        self.setCentralWidget(self._root_frame)


    def _toggle_activity(self, activity_id: str):
        target_btn = None
        target_splitter = None
        
        for widget in self.findChildren(SidebarButton):
            if widget.activity_id == activity_id:
                target_btn = widget
                target_splitter = self._panel_right if widget.is_right_side else self._panel_left
                break
                    
        if not target_btn or not target_splitter:
            return  # Activity button not found in sidebars

        assert target_btn is not None
        assert target_splitter is not None

        activity_widget = self.activities[activity_id]
        sidebar = self._sidebar_left if not target_btn.is_right_side else self._sidebar_right
        
        is_already_active = target_btn.is_active
        
        if is_already_active:
            target_splitter.hide()
            target_btn.set_active(False)
        else:
            for widget in self.findChildren(SidebarButton):
                if widget.is_right_side == target_btn.is_right_side:
                    widget.set_active(False)
                    
            target_btn.set_active(True)
            layout = target_splitter.layout()
            
            # Clear existing items safely
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    
            layout.addWidget(activity_widget)
            activity_widget.show()
            
            was_hidden = not target_splitter.isVisible()
            target_splitter.show()
            if was_hidden:
                sizes = self._main_h_splitter.sizes()
                target_w = 280
                if target_splitter == self._panel_left:
                    diff = target_w - sizes[0]
                    sizes[0] = target_w
                    sizes[1] = max(0, sizes[1] - diff)
                elif target_splitter == self._panel_right:
                    diff = target_w - sizes[2]
                    sizes[2] = target_w
                    sizes[1] = max(0, sizes[1] - diff)
                self._main_h_splitter.setSizes(sizes)

    def _save_sidebar_layout(self):
        prefs = self.engine.load_preferences() or {}

        left_order = []
        for i in range(self._drag_zone_left.layout().count()):
            w = self._drag_zone_left.layout().itemAt(i).widget()
            if isinstance(w, SidebarButton): left_order.append(w.activity_id)

        right_order = []
        for i in range(self._drag_zone_right.layout().count()):
            w = self._drag_zone_right.layout().itemAt(i).widget()
            if isinstance(w, SidebarButton): right_order.append(w.activity_id)

        prefs['sidebar_left'] = left_order
        prefs['sidebar_right'] = right_order
        self.engine.save_preferences(prefs)

    def _restore_sidebar_layout(self):
        prefs = self.engine.load_preferences() or {}
        left_saved = prefs.get('sidebar_left', [])
        right_saved = prefs.get('sidebar_right', [])

        if not left_saved and not right_saved: return

        # Zmapuj i wyczyść obecne przyciski
        btns_map = {}
        for dz in [self._drag_zone_left, self._drag_zone_right]:
            layout = dz.layout()
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if isinstance(w, SidebarButton):
                    btns_map[w.activity_id] = w
                    layout.removeWidget(w)

        # Odtwórz poprawną kolejność dla lewej strony
        for act_id in left_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = False
                self._drag_zone_left.layout().addWidget(btn)

        # Odtwórz poprawną kolejność dla prawej strony
        for act_id in right_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = True
                self._drag_zone_right.layout().addWidget(btn)

        # Resztki (nowe funkcje) lądują domyślnie na lewo
        for btn in btns_map.values():
            btn.is_right_side = False
            self._drag_zone_left.layout().addWidget(btn)

    def _build_activities(self):
        def _wrap_activity(widget: QWidget) -> QFrame:
            container = QFrame()
            container.setObjectName("ActivityPanel")
            container.setAttribute(Qt.WA_StyledBackground, True)

            container.setStyleSheet("""
                QFrame#ActivityPanel {
                    background-color: #212121;
                    border-radius: 0px;
                    margin: 0px;
                    border: none;
                }
                /* Force all generic children to be transparent so the grey shows through */
                QFrame#ActivityPanel QWidget {
                    background-color: transparent;
                }
                /* Restore specific background for input fields so they don't blend in */
                QFrame#ActivityPanel QTextEdit,
                QFrame#ActivityPanel QDoubleSpinBox,
                QFrame#ActivityPanel QLineEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #3a3a3a;
                    color: #ffffff;
                }
                QFrame#ActivityPanel QPushButton {
                    background-color: #333333;
                    border: 1px solid #454545;
                    border-radius: 4px;
                    padding: 5px;
                    color: #d9d9d9;
                }
                QFrame#ActivityPanel QPushButton:hover { background-color: #404040; border-color: #555555; }
                QFrame#ActivityPanel QPushButton:disabled { background-color: #2a2a2a; border-color: #222; color: #555555; }
            """)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget)
            return container

        def style_rb(rb, color):
            rb.setStyleSheet(f"""
                QRadioButton {{ color: {color}; font-weight: bold; }}
                QRadioButton::indicator {{
                    width: 12px; height: 12px;
                    border-radius: 7px;
                    border: 2px solid #555555;
                    background: transparent;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #555555;
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.45, fx:0.5, fy:0.5, stop:0 {color}, stop:0.8 {color}, stop:1 transparent);
                }}
            """)

        # A. script_analysis
        p_script_analysis = QWidget()
        l_script_analysis = QVBoxLayout(p_script_analysis)
        l_script_analysis.setContentsMargins(15, 15, 15, 15)
        l_script_analysis.setSpacing(10)
        
        self.text_script = QTextEdit()
        self.text_script.setAcceptRichText(False)
        self.text_script.setPlaceholderText(self.txt("ph_paste_script_here"))
        l_script_analysis.addWidget(self.text_script)
        
        btn_row_script = QHBoxLayout()
        self.btn_import_script = QPushButton(self.txt("btn_import_script"))
        self.btn_import_script.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_script = QPushButton(self.txt("btn_clear"))
        self.btn_clear_script.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row_script.addWidget(self.btn_import_script)
        btn_row_script.addWidget(self.btn_clear_script)
        l_script_analysis.addLayout(btn_row_script)
        
        self.btn_analyze_compare = QPushButton(self.txt("btn_analyze_compare"))
        self.btn_analyze_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_compare.setFixedHeight(35)
        self.btn_analyze_compare.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; font-weight: bold; font-size: 12pt; border: none; border-radius: 4px; padding: 10px;")
        l_script_analysis.addWidget(self.btn_analyze_compare)
        
        self._analyze_color_anim = QVariantAnimation(self)
        self._analyze_color_anim.setDuration(250)

        def update_btn_style(color):
            self.btn_analyze_compare.setStyleSheet(f"QPushButton {{ background-color: {color.name()}; border: 1px solid #111; border-radius: 4px; color: #fff; font-weight: bold; padding: 8px; }}")
        self._analyze_color_anim.valueChanged.connect(update_btn_style)
        
        self.btn_analyze_standalone = QPushButton(self.txt("btn_analyze_standalone"))
        self.btn_analyze_standalone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_standalone.setFixedHeight(35)
        self.btn_analyze_standalone.setEnabled(False)
        l_script_analysis.addWidget(self.btn_analyze_standalone)
        
        self.activities["script_analysis"] = _wrap_activity(p_script_analysis)
        
        # Connect text change logic
        def update_compare_btn():
            has_text = bool(self.text_script.toPlainText().strip())
            
            # Check if state actually changed to prevent animation loop on every keystroke
            if getattr(self, '_analyze_last_state', None) == has_text:
                return 
            self._analyze_last_state = has_text
            
            self.btn_analyze_compare.setEnabled(has_text)
            
            start_color = QColor("#2a2a2a") if has_text else QColor(config.BTN_BG)
            end_color = QColor(config.BTN_BG) if has_text else QColor("#2a2a2a")

            self._analyze_color_anim.stop()
            self._analyze_color_anim.setStartValue(start_color)
            self._analyze_color_anim.setEndValue(end_color)
            self._analyze_color_anim.start()
            
        self.text_script.textChanged.connect(update_compare_btn)
        update_compare_btn()

        # B. silence
        p_silence = QWidget()
        l_silence = QVBoxLayout(p_silence)
        l_silence.setContentsMargins(15, 15, 15, 15)
        l_silence.setSpacing(10)
        
        # Reusable style for compact silence param inputs
        _sil_input_style = (
            "QLineEdit { background: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; "
            "border-radius: 3px; padding: 2px 6px; } "
            "QLineEdit:focus { border: 1px solid #1a7a3e; }"
        )
        _sil_rst_style = (
            "QPushButton { background: transparent; border: 1px solid #444; "
            "border-radius: 3px; color: #777; font-size: 10pt; } "
            "QPushButton:hover { color: #ccc; border-color: #666; }"
        )

        def _sil_row(label_text, widget, rst_btn):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            row.addWidget(lbl, 1)
            row.addWidget(widget)
            row.addSpacing(4)
            row.addWidget(rst_btn)
            return row

        _sil_prefs = self.engine.load_preferences() or {}

        self.spin_thresh = QLineEdit()
        self.spin_thresh.setText(str(_sil_prefs.get('silence_threshold_db', _sil_prefs.get('ui_spin_thresh', -42.0))))
        self.spin_thresh.setFixedWidth(68)
        self.spin_thresh.setStyleSheet(_sil_input_style)
        _rst_thresh = QPushButton("↺")
        _rst_thresh.setFixedSize(22, 22)
        _rst_thresh.setCursor(Qt.PointingHandCursor)
        _rst_thresh.setStyleSheet(_sil_rst_style)
        _rst_thresh.clicked.connect(lambda: (
            self.spin_thresh.setText("-42.0"),
            self._save_single_pref('silence_threshold_db', -42.0)
        ))

        self.spin_pad = QLineEdit()
        self.spin_pad.setText(str(_sil_prefs.get('ui_spin_pad', 0.05)))
        self.spin_pad.setFixedWidth(68)
        self.spin_pad.setStyleSheet(_sil_input_style)
        _rst_pad = QPushButton("↺")
        _rst_pad.setFixedSize(22, 22)
        _rst_pad.setCursor(Qt.PointingHandCursor)
        _rst_pad.setStyleSheet(_sil_rst_style)
        _rst_pad.clicked.connect(lambda: (
            self.spin_pad.setText("0.05"),
            self._save_single_pref('ui_spin_pad', 0.05)
        ))

        self.spin_silence_min_dur = QLineEdit()
        self.spin_silence_min_dur.setText(str(_sil_prefs.get('silence_min_dur', 0.2)))
        self.spin_silence_min_dur.setFixedWidth(68)
        self.spin_silence_min_dur.setStyleSheet(_sil_input_style)
        self.spin_silence_min_dur.setToolTip(
            "Minimum duration (in seconds) for a gap to be classified as silence. "
            "Lower = more sensitive. Applies to both standalone and post-transcript modes."
        )
        _rst_min = QPushButton("↺")
        _rst_min.setFixedSize(22, 22)
        _rst_min.setCursor(Qt.PointingHandCursor)
        _rst_min.setStyleSheet(_sil_rst_style)
        _rst_min.clicked.connect(lambda: (
            self.spin_silence_min_dur.setText("0.2"),
            self._save_single_pref('silence_min_dur', 0.2)
        ))

        l_silence.addLayout(_sil_row(self.txt("lbl_threshold_db"), self.spin_thresh, _rst_thresh))
        l_silence.addLayout(_sil_row(self.txt("lbl_padding_s"), self.spin_pad, _rst_pad))
        l_silence.addLayout(_sil_row(self.txt("lbl_min_silence_dur"), self.spin_silence_min_dur, _rst_min))

        
        row_silence_cut = QHBoxLayout()
        lbl_cut = QLabel(self.txt("lbl_detect_and_cut_silence"))
        lbl_cut.setWordWrap(True)
        row_silence_cut.addWidget(lbl_cut)
        row_silence_cut.addStretch()
        self.tgl_silence_cut = ToggleSwitch()
        row_silence_cut.addWidget(self.tgl_silence_cut)
        l_silence.addLayout(row_silence_cut)
        
        row_silence_mark = QHBoxLayout()
        lbl_mark = QLabel(self.txt("lbl_detect_and_mark_silence"))
        lbl_mark.setWordWrap(True)
        row_silence_mark.addWidget(lbl_mark)
        row_silence_mark.addStretch()
        self.tgl_silence_mark = ToggleSwitch()
        row_silence_mark.addWidget(self.tgl_silence_mark)
        l_silence.addLayout(row_silence_mark)
        
        l_silence.addStretch(1)
        self.activities["silence"] = _wrap_activity(p_silence)
        
        self.tgl_silence_cut.toggled.connect(lambda checked: self.tgl_silence_mark.setChecked(False) if checked else None)
        self.tgl_silence_mark.toggled.connect(lambda checked: self.tgl_silence_cut.setChecked(False) if checked else None)

        # C. fillers
        p_fillers = QWidget()
        l_fillers = QVBoxLayout(p_fillers)
        l_fillers.setContentsMargins(15, 15, 15, 15)
        l_fillers.setSpacing(10)
        # Inline Filler Words Editor
        prefs = self.engine.load_preferences() or {}
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        
        self.txt_fillers = QTextEdit()
        self.txt_fillers.setAcceptRichText(False)
        self.txt_fillers.setStyleSheet(f"background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; border-radius: 4px; padding: 4px;")
        self.txt_fillers.setText(", ".join(fillers))
        l_fillers.addWidget(self.txt_fillers)
        
        # Bottom tools for fillers (Counter, Reset, Save)
        filler_tools_layout = QHBoxLayout()
        filler_tools_layout.setContentsMargins(0, 2, 0, 0)
        
        self.lbl_filler_count = QLabel(self.txt("lbl_words"))
        self.lbl_filler_count.setStyleSheet("color: #888888; font-size: 9pt;")
        filler_tools_layout.addWidget(self.lbl_filler_count)
        
        filler_tools_layout.addStretch()
        
        self.btn_reset_fillers = QPushButton("↺")
        self.btn_reset_fillers.setFixedSize(24, 24)
        self.btn_reset_fillers.setCursor(Qt.PointingHandCursor)
        self.btn_reset_fillers.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 3px; color: #888;")
        self.btn_reset_fillers.clicked.connect(self._on_reset_inline_fillers)
        filler_tools_layout.addWidget(self.btn_reset_fillers)
        
        self.btn_save_fillers = QPushButton(self.txt("btn_save"))
        self.btn_save_fillers.setCursor(Qt.PointingHandCursor)
        self.btn_save_fillers.setStyleSheet(f"background-color: {config.BTN_GHOST_BG}; color: {config.FG_COLOR}; border-radius: 4px; font-weight: bold; padding: 4px 10px;")
        self.btn_save_fillers.clicked.connect(self._on_save_inline_fillers)
        filler_tools_layout.addWidget(self.btn_save_fillers)
        l_fillers.addLayout(filler_tools_layout)
        
        # Connect text changed signal for auto-resize and counting
        self.txt_fillers.textChanged.connect(self._on_fillers_text_changed)
        
        # Force initial calculation
        self._on_fillers_text_changed()
        
        row_auto_filler = QHBoxLayout()
        row_auto_filler.addWidget(QLabel(self.txt("lbl_mark_filler_words_automat")))
        row_auto_filler.addStretch()
        self.tgl_auto_filler = ToggleSwitch()
        self.tgl_auto_filler.setChecked(True)
        row_auto_filler.addWidget(self.tgl_auto_filler)
        l_fillers.addLayout(row_auto_filler)
        
        l_fillers.addStretch(1)
        self.activities["fillers"] = _wrap_activity(p_fillers)

        # D. main_panel
        p_main = QWidget()
        l_main = QVBoxLayout(p_main)
        l_main.setContentsMargins(15, 15, 15, 15)
        l_main.setSpacing(10)
        
        # Top Section (Markers)
        row_marking_title = QHBoxLayout()
        row_marking_title.addWidget(QLabel(self.txt("lbl_marking_mode")))
        row_marking_title.addStretch()
        self.btn_clear_transcript = QPushButton("🧹")
        self.btn_clear_transcript.setFixedSize(26, 26)
        self.btn_clear_transcript.setToolTip("") # Force remove native tooltip
        self.btn_clear_transcript.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_transcript.setStyleSheet("background: transparent; border: none; font-size: 12pt; padding: 2px;")
        self.btn_clear_transcript.clicked.connect(self._on_clear_transcript)
        row_marking_title.addWidget(self.btn_clear_transcript)
        l_main.addLayout(row_marking_title)
        
        self.markers_layout = QVBoxLayout()
        self.markers_layout.setSpacing(4)
        l_main.addLayout(self.markers_layout)
        
        self.btn_add_custom_marker = QPushButton(self.txt("lbl_add_custom_marker"))
        self.btn_add_custom_marker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_custom_marker.setStyleSheet("QPushButton { background: transparent; color: #808080; text-decoration: underline; border: none; text-align: left; padding: 5px; } QPushButton:hover { color: #ffffff; }")
        self.btn_add_custom_marker.clicked.connect(self._on_add_custom_marker)
        l_main.addWidget(self.btn_add_custom_marker)
        
        # Middle
        l_main.addStretch(1)
        
        # Favorites section
        self.lbl_pinned_favorites = QLabel(self.txt("lbl_pinned_favorites"))
        self.lbl_pinned_favorites.setStyleSheet("color: #888888; font-size: 8pt; font-weight: bold; text-transform: uppercase;")
        self.lbl_pinned_favorites.setVisible(False)  # Hidden until at least one favorite is pinned
        l_main.addWidget(self.lbl_pinned_favorites)
        
        self.layout_favorites = QVBoxLayout()
        self.layout_favorites.setSpacing(10)
        l_main.addLayout(self.layout_favorites)
        
        # Bottom Section removed!
        
        row_proj = QHBoxLayout()
        self.btn_import_proj = QPushButton(self.txt("btn_import_project"))
        self.btn_import_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_proj = QPushButton(self.txt("btn_export_project"))
        self.btn_export_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        row_proj.addWidget(self.btn_import_proj)
        row_proj.addWidget(self.btn_export_proj)
        l_main.addLayout(row_proj)
        
        self.btn_assemble = QPushButton(self.txt("btn_assemble"))
        self.btn_assemble.setFixedHeight(35)
        self.btn_assemble.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_assemble.setStyleSheet("QPushButton { background-color: #11703c; color: white; font-weight: bold; border-radius: 4px; border: 1px solid #0a4d28; } QPushButton:hover { background-color: #168f4d; } QPushButton:pressed { background-color: #0d5c31; }")
        l_main.addWidget(self.btn_assemble)
        
        self._build_marker_radio_buttons()
        self.activities["main_panel"] = _wrap_activity(p_main)
        
        self._favorite_proxies = {}
        self._pin_buttons = {}
        
        # E. assembly
        p_assembly = QWidget()
        l_assembly = QVBoxLayout(p_assembly)
        l_assembly.setContentsMargins(15, 15, 15, 15)
        l_assembly.setSpacing(15)
        
        def _pin_btn(fav_id: str):
            btn = QPushButton("★")
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #555555; font-size: 11pt; padding: 0; } QPushButton:hover { color: #aaaaaa; }")
            self._pin_buttons[fav_id] = btn
            return btn
        
        row_show_inaudible = QHBoxLayout()
        lbl_show_inaud = QLabel(self.txt("lbl_show_inaudible_fragments"))
        lbl_show_inaud.setWordWrap(True)
        row_show_inaudible.addWidget(lbl_show_inaud)
        row_show_inaudible.addStretch()
        self.tgl_show_inaudible = ToggleSwitch()
        self.tgl_show_inaudible.setChecked(True)
        self.tgl_show_inaudible.toggled.connect(self._on_inaudible_toggled)
        row_show_inaudible.addWidget(self.tgl_show_inaudible)
        pin_show_inaud = _pin_btn('show_inaudible')
        row_show_inaudible.addWidget(pin_show_inaud)
        l_assembly.addLayout(row_show_inaudible)
        pin_show_inaud.clicked.connect(lambda: self._toggle_favorite('show_inaudible', self.tgl_show_inaudible, self.txt("tool_show_inaudible"), pin_show_inaud))
        
        row_mark_inaudible = QHBoxLayout()
        lbl_mark_inaud = QLabel(self.txt("lbl_mark_inaudible_fragments"))
        lbl_mark_inaud.setWordWrap(True)
        row_mark_inaudible.addWidget(lbl_mark_inaud)
        row_mark_inaudible.addStretch()
        self.tgl_mark_inaudible = ToggleSwitch()
        self.tgl_mark_inaudible.toggled.connect(self._on_mark_inaudible_toggled)
        row_mark_inaudible.addWidget(self.tgl_mark_inaudible)
        pin_mark_inaud = _pin_btn('mark_inaudible')
        row_mark_inaudible.addWidget(pin_mark_inaud)
        l_assembly.addLayout(row_mark_inaudible)
        pin_mark_inaud.clicked.connect(lambda: self._toggle_favorite('mark_inaudible', self.tgl_mark_inaudible, self.txt("tool_mark_inaudible"), pin_mark_inaud))
        
        row_show_typos = QHBoxLayout()
        lbl_show_typos = QLabel(self.txt("lbl_show_detected_typos"))
        lbl_show_typos.setWordWrap(True)
        row_show_typos.addWidget(lbl_show_typos)
        row_show_typos.addStretch()
        self.tgl_show_typos = ToggleSwitch()
        self.tgl_show_typos.setChecked(True)
        self.tgl_show_typos.toggled.connect(self._on_typos_toggled)
        row_show_typos.addWidget(self.tgl_show_typos)
        pin_show_typos = _pin_btn('show_typos')
        row_show_typos.addWidget(pin_show_typos)
        l_assembly.addLayout(row_show_typos)
        pin_show_typos.clicked.connect(lambda: self._toggle_favorite('show_typos', self.tgl_show_typos, self.txt("tool_show_typos"), pin_show_typos))
        
        row_ripple_delete = QHBoxLayout()
        lbl_ripple = QLabel(self.txt("lbl_ripple_delete_red_clips"))
        lbl_ripple.setWordWrap(True)
        row_ripple_delete.addWidget(lbl_ripple)
        row_ripple_delete.addStretch()
        self.tgl_ripple_delete = ToggleSwitch()
        row_ripple_delete.addWidget(self.tgl_ripple_delete)
        pin_ripple = _pin_btn('ripple_delete')
        row_ripple_delete.addWidget(pin_ripple)
        l_assembly.addLayout(row_ripple_delete)
        pin_ripple.clicked.connect(lambda: self._toggle_favorite('ripple_delete', self.tgl_ripple_delete, self.txt("tool_ripple_delete"), pin_ripple))

        l_assembly.addStretch(1)
        self.activities["assembly"] = _wrap_activity(p_assembly)

        
        self.btn_analyze_standalone.installEventFilter(self)
        self.btn_clear_transcript.installEventFilter(self)

        # Signal Connections
        self.btn_import_script.clicked.connect(self._on_import_script)
        self.btn_clear_script.clicked.connect(self._on_clear_script)
        self.btn_analyze_compare.clicked.connect(self._on_analyze_compare)
        self.btn_analyze_standalone.clicked.connect(self._on_analyze_standalone)
        self.tgl_auto_filler.toggled.connect(self._on_auto_filler_toggled)
        
        # Right Panel Signals
        self.btn_assemble.clicked.connect(self._on_assemble)
        self.btn_import_proj.clicked.connect(self._on_import_project)
        self.btn_export_proj.clicked.connect(self._on_export_project)
        
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            if watched == getattr(self, 'btn_analyze_standalone', None):
                self.shared_tooltip.show_at(watched, self.txt("tooltip_dev"), is_right_side=False)
            elif watched == getattr(self, 'btn_clear_transcript', None):
                # CRITICAL: is_right_side=True forces it to render to the left of the button!
                self.shared_tooltip.show_at(watched, self.txt("tooltip_clear_all_markings"), is_right_side=True)
        elif event.type() == QEvent.Type.Leave:
            if watched in (getattr(self, 'btn_analyze_standalone', None), getattr(self, 'btn_clear_transcript', None)):
                self.shared_tooltip.hide()
                
        return super().eventFilter(watched, event)


    # Removed deprecated _on_nav_script and _on_nav_analysis

    # ------------------------------------------------------------------
    # UI Logic Methods
    # ------------------------------------------------------------------

    def _on_import_script(self):
        from PySide6.QtWidgets import QFileDialog
        import algorithms
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Script", "", 
            "Text/Word/PDF Files (*.txt *.docx *.pdf);;All Files (*)"
        )
        if not file_path: return
        
        ext = file_path.split('.')[-1].lower()
        content = ""
        
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == 'docx':
            if hasattr(algorithms, 'read_docx_text'):
                content = algorithms.read_docx_text(file_path)
        elif ext == 'pdf':
            if hasattr(algorithms, 'read_pdf_text'):
                content = algorithms.read_pdf_text(file_path)
            
        self.text_script.setText(content)

    def _on_clear_script(self):
        self.text_script.clear()

    def _on_analyze_compare(self):
        script_text = self.text_script.toPlainText().strip()
        if not script_text:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_please_import_or_paste_a"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        # Run comparison via engine and overwrite canvas data
        updated_words = self.engine.run_comparison_analysis(script_text, self.text_canvas.words_data)
        self.text_canvas.load_data(updated_words)

    def _on_analyze_standalone(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        prefs = self.engine.load_preferences() or {}
        show_inaudible = prefs.get('show_inaudible', True)
        
        # Standalone analysis returns a tuple: (processed_words, count)
        updated_words, _ = self.engine.run_standalone_analysis(self.text_canvas.words_data, show_inaudible)
        self.text_canvas.load_data(updated_words)

    def _switch_chapter(self, chapter_name):
        if not self._chapters: return
        
        target_idx = -1
        for i, ch in enumerate(self._chapters):
            if ch.get("name") == chapter_name:
                target_idx = i
                break
                
        if target_idx == -1: return
        self._current_chapter_idx = target_idx
        
        import copy
        ch = self._chapters[target_idx]
        self.text_canvas.load_data(copy.deepcopy(ch.get("words", [])))
        
        # Sync DaVinci
        prefs = self.engine.load_preferences() or {}
        if prefs.get("sync_davinci_chapter", True):
            tl_name = ch.get("tl_name")
            if tl_name and self.resolve_handler and getattr(self.resolve_handler, 'project', None):
                try:
                    count = self.resolve_handler.project.GetTimelineCount()
                    for i in range(1, count + 1):
                        tl = self.resolve_handler.project.GetTimelineByIndex(i)
                        if tl and tl.GetName() == tl_name:
                            self.resolve_handler.project.SetCurrentTimeline(tl)
                            break
                except Exception:
                    pass

    def _on_auto_filler_toggled(self, is_checked):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        import algorithms
        prefs = self.engine.load_preferences() or {}
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        
        # Apply filler logic directly to the current state
        if hasattr(algorithms, 'apply_auto_filler_logic'):
            updated_words = algorithms.apply_auto_filler_logic(self.text_canvas.words_data, fillers, is_checked)
            self.text_canvas.words_data = updated_words
            self.text_canvas.update()

    def _on_save_inline_fillers(self):
        raw_text = self.txt_fillers.toPlainText()
        new_fillers = [w.strip() for w in raw_text.split(',') if w.strip()]
        
        prefs = self.engine.load_preferences() or {}
        prefs['filler_words'] = new_fillers
        self.engine.save_preferences(prefs)
        
        # Provide visual feedback on the button
        self.btn_save_fillers.setText(self.txt("txt_saved"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_fillers.setText(self.txt("txt_save")))
        
        # Trigger real-time update if auto filler is currently active
        if hasattr(self, 'tgl_auto_filler') and self.tgl_auto_filler.isChecked() and hasattr(self, 'text_canvas') and self.text_canvas.words_data:
            import algorithms
            if hasattr(algorithms, 'apply_auto_filler_logic'):
                updated_words = algorithms.apply_auto_filler_logic(self.text_canvas.words_data, new_fillers, True)
                self.text_canvas.words_data = updated_words
                self.text_canvas.update()

    def _on_reset_inline_fillers(self):
        self.txt_fillers.setText(", ".join(config.DEFAULT_BAD_WORDS))
        self._on_save_inline_fillers()

    def _on_fillers_text_changed(self):
        # Auto-Resize: Document height + 1 line height
        doc_height = self.txt_fillers.document().size().height()
        from PySide6.QtGui import QFontMetrics
        line_height = QFontMetrics(self.txt_fillers.font()).lineSpacing()
        
        new_height = int(doc_height + line_height + 10) # 10px padding margin
        # Cap max height to avoid breaking the UI
        new_height = min(new_height, 250)
        self.txt_fillers.setFixedHeight(new_height)
        
        # Word count calculation
        raw_text = self.txt_fillers.toPlainText()
        words = [w.strip() for w in raw_text.split(',') if w.strip()]
        count = len(words)
        
        self.lbl_filler_count.setText(f"{count} / 150 {self.txt('lbl_words')}")
        
        if count > 150:
            self.lbl_filler_count.setStyleSheet("color: #ed4245; font-size: 9pt; font-weight: bold;")
            self.btn_save_fillers.setEnabled(False)
        else:
            self.lbl_filler_count.setStyleSheet("color: #888888; font-size: 9pt;")
            self.btn_save_fillers.setEnabled(True)

    def _get_clean_words_data(self):
        """Returns a deep-copy of words_data stripped of all PySide6 UI objects (keys starting with '_')."""
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return []
            
        clean_data = []
        for w in self.text_canvas.words_data:
            # Only keep native Python types, strip UI markers like _rect, _ts_rect, _display_text
            clean_w = {k: v for k, v in w.items() if not k.startswith('_')}
            clean_data.append(clean_w)
        return clean_data

    def _on_export_project(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        from PySide6.QtWidgets import QFileDialog
        import time, os
        
        saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
        os.makedirs(saves_dir, exist_ok=True)
        
        # SMART TIMELINE NAMING
        timeline_name = "Project"
        try:
            if hasattr(self, 'resolve_handler') and self.resolve_handler:
                project = self.resolve_handler.project_manager.GetCurrentProject()
                if project:
                    timeline_name = project.GetName()
                    tl = project.GetCurrentTimeline()
                    if tl:
                        timeline_name = tl.GetName()
        except Exception:
            pass
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"BadWords_{safe_name}.json"
        
        path, _ = QFileDialog.getSaveFileName(self, self.txt("btn_export_project"), os.path.join(saves_dir, default_filename), "JSON Files (*.json)")
        if not path: return
        
        prefs = self.engine.load_preferences() or {}

        # GATHER ACTIVE PANELS (Using correct attribute names)
        active_panels = []
        nav_btns = [
            getattr(self, 'btn_nav_script',   None), getattr(self, 'btn_nav_silence', None),
            getattr(self, 'btn_nav_fillers',  None), getattr(self, 'btn_nav_main',    None),
            getattr(self, 'btn_nav_assembly', None)
        ]
        for btn in nav_btns:
            if btn and getattr(btn, 'is_active', False):
                active_panels.append(btn.activity_id)

        # SMUGGLE LAYOUT DATA INTO PREFS TO BYPASS ENGINE RESTRICTIONS
        prefs['ui_active_panels']  = active_panels
        prefs['ui_splitter_sizes'] = self._main_h_splitter.sizes() if hasattr(self, '_main_h_splitter') else []

        clean_words = self._get_clean_words_data()

        # Update current chapter with latest canvas data before saving
        if getattr(self, '_current_chapter_idx', -1) >= 0 and self._chapters:
            self._chapters[self._current_chapter_idx]['words'] = clean_words
            
        data_packet = {
            "lang_code":      prefs.get('lang', 'Auto'),
            "settings":       prefs,
            "title_bar_text": getattr(self, '_title_bar', None)._lbl_title.text() if hasattr(self, '_title_bar') else "BadWords",
            "filler_words":   prefs.get('filler_words', config.DEFAULT_BAD_WORDS),
            "words_data":     clean_words,
            "chapters":       getattr(self, '_chapters', []),
            "current_chapter_idx": getattr(self, '_current_chapter_idx', -1),
            "script_content": getattr(self, 'text_script', None).toPlainText() if hasattr(self, 'text_script') else ""
        }
        # Note: layout state is inside 'settings', not at the root level
        self.engine.save_project_state(path, data_packet)

    def _on_import_project(self):
        try:
            from PySide6.QtWidgets import QFileDialog, QApplication
            import os
            
            saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
            os.makedirs(saves_dir, exist_ok=True)
            
            path, _ = QFileDialog.getOpenFileName(self, self.txt("btn_import_project"), saves_dir, "JSON Files (*.json)")
            if not path: return
            
            state, _ = self.engine.load_project_state(path)

            from PySide6.QtCore import QTimer

            # --- 1. SYNC UI PREFERENCES ---
            imported_prefs = state.get('settings', {})
            
            # --- Restore Source Snapshot ---
            imported_snapshot = (state.get('settings') or {}).get('transcription_source')
            if imported_snapshot:
                self._transcription_source = imported_snapshot

            # --- Restore Title Bar ---
            title_text = state.get('title_bar_text', '')
            if title_text and title_text != "BadWords":
                if hasattr(self, '_title_bar'):
                    self._title_bar.set_title(title_text)
            elif self._transcription_source:
                # Rebuild title from snapshot
                snap = self._transcription_source
                tl_name = snap.get('timeline_name', '')
                track_names = snap.get('track_names', [])
                all_tl_tracks = snap.get('all_tracks', True)
                tracks_str = self.txt('txt_all') if (not track_names or all_tl_tracks) else ', '.join(sorted(track_names))
                msg = self.txt('msg_transcription_source')
                if msg and '{tl}' in msg:
                    rebuilt_title = msg.replace('{tl}', tl_name).replace('{tr}', tracks_str)
                    if hasattr(self, '_title_bar'):
                        self._title_bar.set_title(rebuilt_title)

            if imported_prefs:
                self.engine.save_preferences(imported_prefs)

                # Update Toggle Switches
                toggles = [
                    ('ui_tgl_silence_cut',    getattr(self, 'tgl_silence_cut',    None)),
                    ('ui_tgl_silence_mark',   getattr(self, 'tgl_silence_mark',   None)),
                    ('ui_tgl_show_inaudible', getattr(self, 'tgl_show_inaudible', None)),
                    ('ui_tgl_mark_inaudible', getattr(self, 'tgl_mark_inaudible', None)),
                    ('ui_tgl_show_typos',     getattr(self, 'tgl_show_typos',     None)),
                    ('ui_tgl_ripple_delete',  getattr(self, 'tgl_ripple_delete',  None)),
                    ('ui_tgl_auto_filler',    getattr(self, 'tgl_auto_filler',    None)),
                ]
                for key, widget in toggles:
                    if widget and key in imported_prefs:
                        widget.setChecked(imported_prefs[key], animated=False)

                # Restore Standalone Silence Detection inputs (QLineEdit-based)
                if hasattr(self, 'input_fs_thresh') and 'silence_threshold_db' in imported_prefs:
                    self.input_fs_thresh.setText(str(imported_prefs['silence_threshold_db']))
                if hasattr(self, 'input_fs_pad') and 'ui_spin_pad' in imported_prefs:
                    self.input_fs_pad.setText(str(imported_prefs['ui_spin_pad']))
                if hasattr(self, 'input_fs_min_dur') and 'silence_min_dur' in imported_prefs:
                    self.input_fs_min_dur.setText(str(imported_prefs['silence_min_dur']))

                # Restore pinned favorites visually
                for fav_id in imported_prefs.get('favorites', []):
                    if hasattr(self, '_pin_buttons') and fav_id in self._pin_buttons:
                        if not hasattr(self, '_favorite_proxies') or fav_id not in self._favorite_proxies:
                            self._pin_buttons[fav_id].click()
                # Update pinned favorites label visibility
                if hasattr(self, 'lbl_pinned_favorites') and hasattr(self, '_favorite_proxies'):
                    self.lbl_pinned_favorites.setVisible(len(self._favorite_proxies) > 0)

            # Restore Script
            if hasattr(self, 'text_script') and 'script_content' in state:
                self.text_script.setText(state['script_content'])

            # --- 2. SWITCH TO EDITOR CONTEXT ---
            if hasattr(self, 'go_to_page'):
                self.go_to_page(2)

            # EXTRACT SMUGGLED UI STATE FROM PREFS
            saved_panels = imported_prefs.get('ui_active_panels', [])
            saved_sizes  = imported_prefs.get('ui_splitter_sizes', [])

            # --- 3. BULLETPROOF PANEL RESTORATION ---
            if hasattr(self, '_panel_left'):  self._panel_left.hide()
            if hasattr(self, '_panel_right'): self._panel_right.hide()

            # STRICT MAPPING: exact activity_id string -> actual button instance
            nav_map = {
                'script_analysis': getattr(self, 'btn_nav_script',   None),
                'silence':         getattr(self, 'btn_nav_silence',  None),
                'fillers':         getattr(self, 'btn_nav_fillers',  None),
                'main_panel':      getattr(self, 'btn_nav_main',     None),
                'assembly':        getattr(self, 'btn_nav_assembly', None),
            }

            # Force all buttons off safely
            for act_id, btn in nav_map.items():
                if btn:
                    btn.is_active = False
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)

            QApplication.processEvents()

            # Forcefully trigger saved panels
            for act_id in saved_panels:
                if act_id in nav_map and nav_map[act_id] is not None:
                    self._toggle_activity(act_id)

            QApplication.processEvents()

            # Load Words Data
            if hasattr(self, 'text_canvas'):
                self.text_canvas.load_data(state.get('words_data', []))
                
            # Restore Chapters
            saved_chapters = state.get('chapters', [])
            saved_current_idx = state.get('current_chapter_idx', -1)
            if saved_chapters:
                self._chapters = saved_chapters
                self._current_chapter_idx = saved_current_idx
            else:
                import copy
                self._chapters = [{
                    "name": "Original",
                    "tl_name": self._transcription_source.get("timeline_name", "") if self._transcription_source else "",
                    "words": copy.deepcopy(state.get('words_data', []))
                }]
                self._current_chapter_idx = 0
                
            # Update Dropdown UI
            if self._chapters and hasattr(self, '_title_bar') and hasattr(self._title_bar, 'chapter_dropdown'):
                self._title_bar.chapter_dropdown.options_list = [ch['name'] for ch in self._chapters]
                # Try to select current chapter name, otherwise default to first
                if 0 <= self._current_chapter_idx < len(self._chapters):
                    self._title_bar.chapter_dropdown.setText(self._chapters[self._current_chapter_idx]['name'])
                if len(self._chapters) > 1:
                    self._title_bar.chapter_dropdown.show()
                else:
                    self._title_bar.chapter_dropdown.hide()
                self._title_bar.update_dropdown_placement()

            # Apply splitter sizes
            if saved_sizes and hasattr(self, '_main_h_splitter'):
                QTimer.singleShot(150, lambda: self._main_h_splitter.setSizes(saved_sizes))
        except Exception as e:
            from osdoc import log_error
            log_error(f"Failed to load project: {e}")
            dlg = CustomMsgBox(self, self.txt("lbl_error"), f"{self.txt('msg_load_project_failed')}:\n{e}", self.txt("btn_ok"))
            dlg.exec()

    def _refresh_canvas_view(self):
        if hasattr(self, 'text_canvas') and getattr(self.text_canvas, 'words_data', None):
            self.text_canvas._calculate_layout()
            self.text_canvas.update()

    def _calculate_visual_layer(self, word_obj: dict) -> str:
        """
        Non-Destructive Two-Layer Engine.

        BASE LAYER  — what the word 'is' permanently:
            manual_status (if set by user) > hard auto (hallucination/is_bad) >
            algo repeat > normal

        OVERLAY LAYER — a transient algo highlight that floats on top:
            active only when the matching toggle is ON and the user hasn't
            manually painted over it (overlay_suppressed == False).

        Manual painting sets overlay_suppressed=True so the user color shows.
        Toggle reload sets overlay_suppressed=False so the overlay resurfaces
        WITHOUT touching manual_status.
        """
        # --- BASE LAYER ---
        base = word_obj.get('manual_status')  # None means 'not set by user'
        if base is None:
            if word_obj.get('_is_hallucination') or word_obj.get('is_bad'):
                base = 'bad'
            elif word_obj.get('algo_status') == 'repeat':
                base = 'repeat'
            else:
                base = 'normal'

        # --- OVERLAY LAYER (toggle-gated, suppressed after manual paint) ---
        overlay = None
        if not word_obj.get('overlay_suppressed', False):
            show_typos = hasattr(self, 'tgl_show_typos') and self.tgl_show_typos.isChecked()
            mark_inaud = hasattr(self, 'tgl_mark_inaudible') and self.tgl_mark_inaudible.isChecked()
            if show_typos and word_obj.get('algo_status') == 'typo':
                overlay = 'typo'
            elif mark_inaud and (word_obj.get('is_inaudible') or word_obj.get('type') == 'inaudible'):
                overlay = 'inaudible'

        final = overlay if overlay is not None else base
        word_obj['status'] = final
        word_obj['selected'] = final in ('bad', 'inaudible', 'typo', 'repeat')
        return final

    def _on_inaudible_toggled(self, is_checked: bool):
        if hasattr(self, 'text_canvas') and getattr(self.text_canvas, 'words_data', None):
            self.text_canvas._calculate_layout()
            self.text_canvas.update()

    def _on_mark_inaudible_toggled(self, is_checked: bool):
        """
        Reload for 'Mark inaudible fragments with brown'.
        Turning ON: clears overlay_suppressed so the brown overlay resurfaces on top.
        manual_status is NEVER touched — base layer stays intact.
        """
        if not hasattr(self, 'text_canvas') or not getattr(self.text_canvas, 'words_data', None):
            return

        for word_obj in self.text_canvas.words_data:
            if not (word_obj.get('is_inaudible') or word_obj.get('type') == 'inaudible'):
                continue

            if is_checked:
                # Reload: allow the brown overlay to float back to the top
                word_obj['overlay_suppressed'] = False

            self._calculate_visual_layer(word_obj)

        self.text_canvas._calculate_layout()
        self.text_canvas.update()

    def _on_typos_toggled(self, is_checked: bool):
        """
        Reload for 'Show detected typos'.
        Turning ON: clears overlay_suppressed so the green overlay resurfaces on top.
        manual_status is NEVER touched — base layer stays intact.
        """
        if not hasattr(self, 'text_canvas') or not getattr(self.text_canvas, 'words_data', None):
            return

        for word_obj in self.text_canvas.words_data:
            if word_obj.get('algo_status') != 'typo':
                continue

            if is_checked:
                # Reload: allow the green overlay to float back to the top
                word_obj['overlay_suppressed'] = False

            self._calculate_visual_layer(word_obj)

        self.text_canvas._calculate_layout()
        self.text_canvas.update()
    # ------------------------------------------------------------------
    # Timeline / Track combo population & synchronisation
    # ------------------------------------------------------------------

    def _populate_timeline_track_combos(self):
        """
        Queries the Resolve API for all timelines in the current project and
        populates both timeline dropdowns (combo_tl_0 / combo_tl_1).
        Called via QTimer.singleShot(800, ...) after __init__.
        """
        try:
            rh = self.engine.resolve_handler
            timelines = rh.get_all_timelines()

            current_tl_name = ""
            if rh.timeline:
                try:
                    current_tl_name = rh.timeline.GetName()
                except Exception:
                    pass

            no_tl_label = self.txt("msg_no_timelines_detected")

            if not timelines:
                for combo in (self.combo_tl_0, self.combo_tl_1):
                    combo.options_list = [no_tl_label]
                    combo.setText(no_tl_label)
                for track_combo in (self.combo_tr_0, self.combo_tr_1):
                    track_combo.options_list = []
                    track_combo.selected_items = set()
                    track_combo.setText(self.txt("msg_no_audio_tracks_detected"))
                return

            # Populate timeline dropdowns
            for combo in (self.combo_tl_0, self.combo_tl_1):
                combo.options_list = list(timelines)
                display = current_tl_name if current_tl_name in timelines else timelines[0]
                combo.setText(display)

            # Populate track dropdowns for the default timeline
            init_tl = current_tl_name if current_tl_name in timelines else timelines[0]
            self._on_timeline_selected(init_tl, self.combo_tr_0)
            self._on_timeline_selected(init_tl, self.combo_tr_1)

        except Exception as e:
            from osdoc import log_error
            log_error(f"_populate_timeline_track_combos error: {e}")

    def _on_timeline_selected(self, tl_name, track_combo, mirror_tl_combo=None):
        """
        Updates *track_combo* with audio tracks for *tl_name*, and optionally
        mirrors the selection to *mirror_tl_combo*.
        """
        try:
            if tl_name == self.txt("msg_no_timelines_detected"):
                return

            rh = self.engine.resolve_handler
            tracks = rh.get_audio_tracks(tl_name)

            no_track_label = self.txt("msg_no_audio_tracks_detected")

            if not tracks:
                track_combo.options_list = []
                track_combo.selected_items = set()
                track_combo.setText(no_track_label)
            else:
                track_combo.options_list = list(tracks)
                track_combo.selected_items = set()
                track_combo.setText(self.txt("txt_all_tracks"))

            # Mirror the timeline selection to the other page's dropdown
            if mirror_tl_combo is not None:
                if tl_name in mirror_tl_combo.options_list and mirror_tl_combo.text() != tl_name:
                    try:
                        mirror_tl_combo.valueChanged.disconnect()
                    except Exception:
                        pass
                    mirror_tl_combo.setText(tl_name)
                    if mirror_tl_combo is self.combo_tl_1:
                        mirror_tl_combo.valueChanged.connect(
                            lambda t: self._on_timeline_selected(t, self.combo_tr_1, self.combo_tl_0)
                        )
                    else:
                        mirror_tl_combo.valueChanged.connect(
                            lambda t: self._on_timeline_selected(t, self.combo_tr_0, self.combo_tl_1)
                        )

        except Exception as e:
            from osdoc import log_error
            log_error(f"_on_timeline_selected error: {e}")

    def _track_names_to_indices(self, tl_name, track_names):
        """Converts track name labels (e.g. {'A1', 'A3'}) to 1-based integer indices."""
        if not track_names:
            return []
        try:
            all_tracks = self.engine.resolve_handler.get_audio_tracks(tl_name)
            indices = []
            for name in track_names:
                if name in all_tracks:
                    indices.append(all_tracks.index(name) + 1)
            return sorted(indices)
        except Exception as e:
            from osdoc import log_error
            log_error(f"_track_names_to_indices error: {e}")
            return []

    def _on_fast_silence(self):
        """Fast Silence Cut: runs FFmpeg pipeline then directly assembles the timeline."""
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()

        self.go_to_page(1)
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(0)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("txt_initializing_fast_silence"))

        # Read from line edits
        try:
            thresh_val = float(self.input_fs_thresh.text().replace(',', '.'))
        except (ValueError, AttributeError):
            thresh_val = -42.0  # fallback
            
        try:
            pad_val = float(self.input_fs_pad.text().replace(',', '.'))
        except (ValueError, AttributeError):
            pad_val = 0.05  # fallback

        try:
            min_dur_val = float(self.input_fs_min_dur.text().replace(',', '.'))
            min_dur_val = max(0.05, min_dur_val)  # safety clamp
        except (ValueError, AttributeError):
            min_dur_val = 0.2  # fallback

        # Persist updated silence params so post-transcript path uses same values
        _p = self.engine.load_preferences() or {}
        _p['silence_threshold_db'] = thresh_val
        _p['silence_min_dur']      = min_dur_val
        self.engine.save_preferences(_p)

        # Read selected timeline and tracks
        selected_tl = getattr(self, 'combo_tl_1', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        no_tl = self.txt("msg_no_timelines_detected")
        if selected_tl_name == no_tl:
            selected_tl_name = ""

        selected_tracks_combo = getattr(self, 'combo_tr_1', None)
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        # Update settings for the core
        settings = {
            'threshold_db':    thresh_val,
            'padding_s':       pad_val,
            'silence_min_dur': min_dur_val,
            'timeline_name':   selected_tl_name or None,
            'track_indices':   track_indices or None,
        }
        self._fs_settings = settings

        self._worker_signals = WorkerSignals()
        self._worker_signals.progress.connect(self._on_analysis_progress)
        self._worker_signals.status.connect(self._on_analysis_status)
        # Route to fast-silence-specific finished handler
        self._worker_signals.finished.connect(self._on_fs_finished)
        self._worker_signals.error.connect(self._on_analysis_error)

        def worker_func():
            try:
                words_data, segments_data = self.engine.run_fast_silence_pipeline(
                    settings,
                    callback_status=self._worker_signals.status.emit,
                    callback_progress=self._worker_signals.progress.emit
                )
                self._worker_signals.finished.emit(words_data, segments_data)
            except Exception as e:
                self._worker_signals.error.emit(str(e))

        self._analysis_thread = threading.Thread(target=worker_func, daemon=True)
        self._analysis_thread.start()


    def _on_fs_finished(self, words_data, segments_data):
        """Called when run_fast_silence_pipeline completes. Directly assembles the timeline."""
        from PySide6.QtWidgets import QApplication

        if not words_data:
            dlg = CustomMsgBox(self, self.txt("msg_standalone_silence"), self.txt("msg_no_silence_segments_detec"), self.txt("btn_ok"))
            dlg.exec()
            self.go_to_page(0)
            if hasattr(self, 'welcome_stack'): self.welcome_stack.setCurrentIndex(0)
            return

        self.lbl_processing_status.setText(self.txt("txt_assembling_timeline"))
        QApplication.processEvents()

        fs_prefs = self.engine.load_preferences() or {}
        fs_prefs['silence_cut']  = getattr(self, 'tgl_fs_cut',  None) and self.tgl_fs_cut.isChecked()
        fs_prefs['silence_mark'] = getattr(self, 'tgl_fs_mark', None) and self.tgl_fs_mark.isChecked()
        if hasattr(self, '_fs_settings'):
            fs_prefs['source_snapshot'] = self._fs_settings

        success, warning, new_tl_name, clean_ops = self.engine.assemble_timeline(
            words_data, fs_prefs,
            callback_status=self.lbl_processing_status.setText,
            callback_progress=self.bar_processing.set_value
        )

        if success:
            dlg = CustomMsgBox(self, self.txt("msg_standalone_silence"), self.txt("msg_standalone_silence_processing_c"), self.txt("btn_ok"))
            dlg.exec()
        else:
            dlg = CustomMsgBox(self, self.txt("msg_fs_error"), f"{self.txt('msg_assembly_failed')}:\n{warning}", self.txt("btn_ok"))
            dlg.exec()

        self.go_to_page(0)
        if hasattr(self, 'welcome_stack'):
            self.welcome_stack.setCurrentIndex(1)

    def _toggle_favorite(self, target_id: str, source_toggle, label_text: str, pin_btn):
        """Proxy Favorites system — creates or destroys a mirrored ToggleSwitch in layout_favorites."""
        if not hasattr(self, 'layout_favorites') or not hasattr(self, '_favorite_proxies'):
            return

        if target_id in self._favorite_proxies:
            # --- REMOVE favorite ---
            entry = self._favorite_proxies.pop(target_id)
            try: source_toggle.toggled.disconnect(entry['src_conn'])
            except: pass
            try: entry['proxy'].toggled.disconnect(entry['prx_conn'])
            except: pass
            proxy_row = entry['row_widget']
            self.layout_favorites.removeWidget(proxy_row)
            proxy_row.deleteLater()
            pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #555555; font-size: 11pt; padding: 0; } QPushButton:hover { color: #aaaaaa; }")
            # Persist removal
            prefs = self.engine.load_preferences() or {}
            favs = prefs.get('favorites', [])
            if target_id in favs: favs.remove(target_id)
            prefs['favorites'] = favs
            self.engine.save_preferences(prefs)
            # Hide label if no favorites left
            if hasattr(self, 'lbl_pinned_favorites'):
                self.lbl_pinned_favorites.setVisible(len(self._favorite_proxies) > 0)
        else:
            # --- ADD favorite ---
            from PySide6.QtWidgets import QWidget as _QWidget
            row_widget = _QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            row_layout.addWidget(QLabel(label_text))
            row_layout.addStretch()

            proxy_toggle = ToggleSwitch()
            pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #eebb00; font-size: 11pt; padding: 0; } QPushButton:hover { color: #ffcc00; }")
            proxy_toggle.setChecked(source_toggle.isChecked(), animated=False)
            row_layout.addWidget(proxy_toggle)

            self.layout_favorites.addWidget(row_widget)

            # Two-way binding (loop-safe)
            def prx_to_src(v, src=source_toggle, prx=proxy_toggle):
                if src.isChecked() != v: src.setChecked(v)
            def src_to_prx(v, src=source_toggle, prx=proxy_toggle):
                if prx.isChecked() != v: prx.setChecked(v)

            prx_conn = proxy_toggle.toggled.connect(prx_to_src)
            src_conn = source_toggle.toggled.connect(src_to_prx)

            self._favorite_proxies[target_id] = {
                'row_widget': row_widget,
                'proxy': proxy_toggle,
                'prx_conn': prx_conn,
                'src_conn': src_conn,
            }
            pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #f0b429; font-size: 11pt; padding: 0; } QPushButton:hover { color: #f5c842; }")
            # Persist addition
            prefs = self.engine.load_preferences() or {}
            favs = prefs.get('favorites', [])
            if target_id not in favs: favs.append(target_id)
            prefs['favorites'] = favs
            self.engine.save_preferences(prefs)
            # Show label when first favorite is added
            if hasattr(self, 'lbl_pinned_favorites'):
                self.lbl_pinned_favorites.setVisible(True)

    def _on_assemble(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return

        from PySide6.QtWidgets import QApplication

        prefs = self.engine.load_preferences() or {}

        # GATHER UI STATES
        if hasattr(self, 'tgl_silence_cut'): prefs['silence_cut'] = self.tgl_silence_cut.isChecked()
        if hasattr(self, 'tgl_silence_mark'): prefs['silence_mark'] = self.tgl_silence_mark.isChecked()
        if hasattr(self, 'tgl_reviewer'): prefs['enable_reviewer'] = self.tgl_reviewer.isChecked()
        if hasattr(self, 'tgl_ripple_delete'): prefs['auto_del'] = self.tgl_ripple_delete.isChecked()
        if hasattr(self, 'tgl_show_typos'): prefs['show_typos'] = self.tgl_show_typos.isChecked()
        if hasattr(self, 'tgl_mark_inaudible'): prefs['mark_inaudible'] = self.tgl_mark_inaudible.isChecked()
        if hasattr(self, 'tgl_show_inaudible'): prefs['show_inaudible'] = self.tgl_show_inaudible.isChecked()

        checked_btn = getattr(self, 'marker_btn_group', None) and self.marker_btn_group.checkedButton()
        if checked_btn:
            prefs['mark_tool'] = checked_btn.property("status_id")

        self.engine.save_preferences(prefs)

        # SANITIZE EXPORT DATA (prevents C++ QRect deepcopy memory leaks)
        export_data    = self._get_clean_words_data()
        show_typos     = prefs.get('show_typos', True)
        mark_inaudible = prefs.get('mark_inaudible', True)
        for w in export_data:
            if w.get('status') == 'typo' and not show_typos:
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    w['status'] = None
            if w.get('status') == 'inaudible' and not mark_inaudible:
                w['status'] = None

        # INJECT SOURCE SNAPSHOT
        src = getattr(self, '_transcription_source', None)
        if not src:
            saved_src = (self.engine.load_preferences() or {}).get('transcription_source')
            if saved_src:
                src = saved_src
                self._transcription_source = src
        if src:
            prefs["source_snapshot"] = src

        # UI PREP — infinite bar starts immediately so it animates during assembly
        self._panel_left.hide()
        self._panel_right.hide()
        self.go_to_page(1)
        self.lbl_processing_status.setText(self.txt("txt_initializing_assembly"))
        self.bar_processing.set_value(-1)   # infinite sweep animation
        QApplication.processEvents()

        # ── WORKER SIGNALS ────────────────────────────────────────────────────
        from PySide6.QtCore import QThread, Signal as _Signal, QObject as _QObject

        class _AssemblySignals(_QObject):
            status   = _Signal(str)
            finished = _Signal(object)   # carries result tuple

        _sigs = _AssemblySignals()
        _sigs.status.connect(self.lbl_processing_status.setText)
        _sigs.finished.connect(self._on_assemble_done)

        # ── WORKER THREAD ─────────────────────────────────────────────────────
        class _AssemblyThread(QThread):
            def __init__(self, engine, export_data, prefs, sigs):
                super().__init__()
                self._engine = engine
                self._data   = export_data
                self._prefs  = prefs
                self._sigs   = sigs

            def run(self):
                try:
                    result = self._engine.assemble_timeline(
                        self._data,
                        self._prefs,
                        callback_status   = self._sigs.status.emit,
                        callback_progress = lambda v: None,  # bar stays infinite
                    )
                except Exception as _e:
                    import traceback as _tb
                    from badwords_log import log_error as _le
                    _le(f"_AssemblyThread: {_e}\n{_tb.format_exc()}")
                    result = (False, None, None, None)
                self._sigs.finished.emit(result)

        self._assembly_thread = _AssemblyThread(self.engine, export_data, prefs, _sigs)
        self._assembly_sigs   = _sigs   # keep alive until finished signal fires
        self._assembly_prefs  = prefs
        self._assembly_thread.start()

    def _on_assemble_done(self, result):
        """Called on main thread when assembly QThread finishes."""
        from PySide6.QtWidgets import QApplication

        self.bar_processing.set_value(100)

        success, warning, new_tl_name, clean_ops = (
            result if (isinstance(result, tuple) and len(result) == 4)
            else (False, None, None, None)
        )

        # Sync snapshot back (engine mutates prefs["source_snapshot"] in-place)
        prefs = getattr(self, '_assembly_prefs', {}) or {}
        updated_snapshot = prefs.get("source_snapshot")
        if updated_snapshot and hasattr(self, '_transcription_source'):
            new_filtered = updated_snapshot.get("filtered_tl_name")
            if new_filtered and self._transcription_source.get("filtered_tl_name") != new_filtered:
                self._transcription_source["filtered_tl_name"] = new_filtered
                try:
                    _p = self.engine.load_preferences() or {}
                    _p["transcription_source"] = self._transcription_source
                    self.engine.save_preferences(_p)
                except Exception:
                    pass

        # RAM cleanup
        try:
            import gc
            self._assembly_thread = None
            self._assembly_sigs   = None
            self._assembly_prefs  = None
            gc.collect()
        except Exception:
            pass

        if success:
            self.lbl_processing_status.setText(self.txt("txt_finishing"))
            QApplication.processEvents()
            self._on_assembly_success(new_tl_name, clean_ops)
        else:
            self._on_assembly_error(self.txt("msg_assembly_failed"))


    def _on_assembly_success(self, new_tl_name, clean_ops):
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        if hasattr(self, '_panel_left'): self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        
        # --- CHAPTER REGISTRATION ---
        new_words = self._get_clean_words_data()
                
        chapter_name = f"Edit {len(self._chapters)}"
        new_chapter = {
            "name": chapter_name,
            "tl_name": new_tl_name or "",
            "words": new_words
        }
        self._chapters.append(new_chapter)
        self._current_chapter_idx = len(self._chapters) - 1
        
        # Update dropdown
        self._title_bar.chapter_dropdown.options_list = [ch['name'] for ch in self._chapters]
        self._title_bar.chapter_dropdown.setText(chapter_name)
        self._title_bar.chapter_dropdown.show()
        self._title_bar.update_dropdown_placement()
        
        # Load the new state
        self.text_canvas.load_data(new_words)
        
        dlg = CustomMsgBox(self, self.txt("msg_success"), self.txt("msg_timeline_assembled_succes"), self.txt("btn_ok"))
        dlg.exec()

    def _on_assembly_error(self, err_msg):
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        if hasattr(self, '_panel_left'): self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        dlg = CustomMsgBox(self, self.txt("lbl_error"), err_msg, self.txt("btn_ok"))
        dlg.exec()

    def _build_welcome_screen(self) -> QWidget:
        """
        Page 0 of the main stack: Welcome / Config screen.
        Contains a local QStackedWidget (self.welcome_stack):
          - sub-page 0: Transcription workflow (existing dropdowns + Analyze button)
          - sub-page 1: Fast Silence settings + Run button
        """
        page = QWidget()
        page.setObjectName("page_welcome")
        page.setStyleSheet(f"QWidget#page_welcome {{ background-color: {config.BG_COLOR}; }}")

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        inner = QWidget()
        inner.setObjectName("welcome_inner")
        inner.setFixedWidth(320)
        inner.setStyleSheet("QWidget#welcome_inner { background: transparent; }")

        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)
        inner_layout.setAlignment(Qt.AlignTop)

        # ── Shared Title ─────────────────────────────────────────────────
        lbl_title = QLabel("BadWords", inner)
        lbl_title.setObjectName("welcome_title")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"""
            QLabel#welcome_title {{
                color: #ffffff;
                font-size: 34pt;
                font-weight: 900;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
                letter-spacing: -2px;
            }}
        """)
        inner_layout.addWidget(lbl_title)
        inner_layout.addSpacing(10)

        # ── Local stacked widget ──────────────────────────────────────────
        self.welcome_stack = QStackedWidget()
        self.welcome_stack.setStyleSheet("background: transparent;")
        inner_layout.addWidget(self.welcome_stack)

        prefs = self.engine.load_preferences() or {}

        def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
            """Label directly above the input."""
            row = QVBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {config.NOTE_COL}; font-size: 9pt;"
                f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
            )
            row.addWidget(lbl)
            row.addWidget(widget)
            return row

        p_transcription = QWidget()
        p_transcription.setStyleSheet("background: transparent;")
        l_trans = QVBoxLayout(p_transcription)
        l_trans.setContentsMargins(0, 0, 0, 0)
        l_trans.setSpacing(0)
        l_trans.setAlignment(Qt.AlignTop)

        lbl_sub = QLabel(self.txt("lbl_transcription_workspace"))
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setFixedHeight(20)
        lbl_sub.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 10pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        l_trans.addWidget(lbl_sub)
        l_trans.addSpacing(20)

        self.combo_tl_0 = CustomDropdown([])
        self.combo_tl_0.setFixedHeight(30)
        self.combo_tl_0.valueChanged.connect(
            lambda tl: self._on_timeline_selected(tl, self.combo_tr_0, self.combo_tl_1)
        )
        _vbox_tl0 = QVBoxLayout()
        _vbox_tl0.setContentsMargins(0, 0, 0, 0)
        _vbox_tl0.setSpacing(3)
        _lbl_tl0 = QLabel(self.txt("lbl_timeline_selection"))
        _lbl_tl0.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 9pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        _hbox_tl0 = QHBoxLayout()
        _hbox_tl0.setContentsMargins(0, 0, 0, 0)
        _hbox_tl0.setSpacing(4)
        _hbox_tl0.addWidget(self.combo_tl_0, 1)
        _btn_ref_tl0 = QPushButton("↺")
        _btn_ref_tl0.setFixedSize(30, 30)
        _btn_ref_tl0.setCursor(Qt.PointingHandCursor)
        _btn_ref_tl0.setToolTip(self.txt("tt_refresh_timelines"))
        _btn_ref_tl0.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #444; "
            "border-radius: 3px; color: #777; font-size: 11pt; } "
            "QPushButton:hover { color: #ccc; border-color: #666; }"
        )
        _btn_ref_tl0.clicked.connect(self._populate_timeline_track_combos)
        _hbox_tl0.addWidget(_btn_ref_tl0)
        _vbox_tl0.addWidget(_lbl_tl0)
        _vbox_tl0.addLayout(_hbox_tl0)
        l_trans.addLayout(_vbox_tl0)
        l_trans.addSpacing(10)

        self.combo_tr_0 = MultiSelectDropdown([])
        self.combo_tr_0.setFixedHeight(30)
        l_trans.addLayout(_row(self.txt("lbl_tracks_selection"), self.combo_tr_0))
        l_trans.addSpacing(10)

        # ── Language
        lang_items = list(config.SUPPORTED_LANGUAGES.values())
        self._combo_lang = SearchableDropdown(lang_items)
        self._combo_lang.setFixedHeight(30)
        saved_lang = prefs.get('lang', 'Auto')
        display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
        self._combo_lang.setText(display_name if (display_name in lang_items or display_name == 'Auto') else "Auto")
        self._combo_lang.valueChanged.connect(lambda v: self.engine.save_preferences({"lang": v}))
        l_trans.addLayout(_row(self.txt("lbl_lang"), self._combo_lang))
        l_trans.addSpacing(10)

        # ── Model
        model_items = [
            "Tiny  (Fast, <1 GB)",
            "Base  (Balanced, 1 GB)",
            "Small  (Good, 2 GB)",
            "Medium  (5 GB)",
            "Large Turbo  (Fast & Precise, 6 GB)",
            "Large  (Accurate, 10 GB)",
        ]
        self._combo_model = CustomDropdown(model_items)
        self._combo_model.setFixedHeight(30)
        self._combo_model.setText(prefs["model"] if "model" in prefs and prefs["model"] in model_items else model_items[4])
        self._combo_model.valueChanged.connect(lambda v: self.engine.save_preferences({"model": v}))
        l_trans.addLayout(_row(self.txt("lbl_model"), self._combo_model))
        l_trans.addSpacing(24)

        # ── Action buttons
        btn_row_t = QHBoxLayout()
        btn_row_t.setSpacing(8)

        btn_import = QPushButton(self.txt("btn_import_project"))
        btn_import.setObjectName("btn_ghost")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.setFixedHeight(30)
        btn_import.setStyleSheet(f"""
            QPushButton#btn_ghost {{
                background-color: #1e1e1e; color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt;
                border: 1px solid #3a3a3a; border-radius: 3px; padding: 0 12px;
            }}
            QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
            QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
        """)
        btn_import.clicked.connect(self._on_import_project)
        btn_row_t.addWidget(btn_import)

        btn_analyze = QPushButton("▶ " + self.txt("btn_analyze"))
        btn_analyze.setObjectName("btn_primary")
        btn_analyze.setCursor(Qt.PointingHandCursor)
        btn_analyze.setFixedHeight(30)
        btn_analyze.setStyleSheet(f"""
            QPushButton#btn_primary {{
                background-color: {config.BTN_BG}; color: #ffffff;
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt; font-weight: bold;
                border: none; border-radius: 3px; padding: 0 18px;
            }}
            QPushButton#btn_primary:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_primary:pressed {{ background-color: #176e38; }}
        """)
        btn_analyze.clicked.connect(self._on_start_analysis)
        btn_row_t.addWidget(btn_analyze)
        l_trans.addLayout(btn_row_t)
        l_trans.addSpacing(14)

        # ── Link to fast silence sub-page
        btn_switch_fast = QPushButton(self.txt("btn_standalone_silence_detection"))
        btn_switch_fast.setCursor(Qt.PointingHandCursor)
        btn_switch_fast.setStyleSheet(
            f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
            " font-size: 9pt; text-decoration: underline; border: none; padding: 0;"
        )
        btn_switch_fast.clicked.connect(lambda: self.welcome_stack.setCurrentIndex(1))
        l_trans.addWidget(btn_switch_fast, 0, Qt.AlignCenter)

        self.welcome_stack.addWidget(p_transcription)  # index 0

        # ═══════════════════════════════════════════════════════════════
        # SUB-PAGE 1: FAST SILENCE (clean layout, mirrors main page)
        # ═══════════════════════════════════════════════════════════════
        p_fast = QWidget()
        p_fast.setStyleSheet("background: transparent;")
        l_fast = QVBoxLayout(p_fast)
        l_fast.setContentsMargins(0, 0, 0, 0)
        l_fast.setSpacing(0)
        l_fast.setAlignment(Qt.AlignTop)

        # TITLE
        lbl_fs_title = QLabel(self.txt("lbl_standalone_silence_workspace"))
        lbl_fs_title.setAlignment(Qt.AlignCenter)
        lbl_fs_title.setFixedHeight(20)
        lbl_fs_title.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 10pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        l_fast.addWidget(lbl_fs_title)
        l_fast.addSpacing(20)

        self.combo_tl_1 = CustomDropdown([])
        self.combo_tl_1.setFixedHeight(30)
        self.combo_tl_1.valueChanged.connect(
            lambda tl: self._on_timeline_selected(tl, self.combo_tr_1, self.combo_tl_0)
        )
        _vbox_tl1 = QVBoxLayout()
        _vbox_tl1.setContentsMargins(0, 0, 0, 0)
        _vbox_tl1.setSpacing(3)
        _lbl_tl1 = QLabel(self.txt("lbl_timeline_selection"))
        _lbl_tl1.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 9pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        _hbox_tl1 = QHBoxLayout()
        _hbox_tl1.setContentsMargins(0, 0, 0, 0)
        _hbox_tl1.setSpacing(4)
        _hbox_tl1.addWidget(self.combo_tl_1, 1)
        _btn_ref_tl1 = QPushButton("↺")
        _btn_ref_tl1.setFixedSize(30, 30)
        _btn_ref_tl1.setCursor(Qt.PointingHandCursor)
        _btn_ref_tl1.setToolTip(self.txt("tt_refresh_timelines"))
        _btn_ref_tl1.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #444; "
            "border-radius: 3px; color: #777; font-size: 11pt; } "
            "QPushButton:hover { color: #ccc; border-color: #666; }"
        )
        _btn_ref_tl1.clicked.connect(self._populate_timeline_track_combos)
        _hbox_tl1.addWidget(_btn_ref_tl1)
        _vbox_tl1.addWidget(_lbl_tl1)
        _vbox_tl1.addLayout(_hbox_tl1)
        l_fast.addLayout(_vbox_tl1)
        l_fast.addSpacing(10)

        self.combo_tr_1 = MultiSelectDropdown([])
        self.combo_tr_1.setFixedHeight(30)
        l_fast.addLayout(_row(self.txt("lbl_tracks_selection"), self.combo_tr_1))
        l_fast.addSpacing(10)

        # SETTINGS ROWS
        input_style = '''
            QLineEdit {
                background-color: #1e1e1e; color: #d4d4d4; 
                border: 1px solid #3a3a3a; border-radius: 3px; 
                padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #1a7a3e; }
        '''

        # Helper: label above input + reset button on the right in one combined layout
        def _row_rst(label_text, widget, reset_val_str):
            """Label above, then a horizontal row: [input, stretch-none, reset_btn]."""
            vbox = QVBoxLayout()
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {config.NOTE_COL}; font-size: 9pt;"
                f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
            )
            vbox.addWidget(lbl)

            hbox = QHBoxLayout()
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(4)
            hbox.addWidget(widget, 1)

            rst = QPushButton("↺")
            rst.setFixedSize(22, 22)
            rst.setCursor(Qt.PointingHandCursor)
            rst.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid #444; "
                "border-radius: 3px; color: #777; font-size: 10pt; } "
                "QPushButton:hover { color: #ccc; border-color: #666; }"
            )
            rst.clicked.connect(lambda: widget.setText(reset_val_str))
            # Optional: Add tooltip to generic reset button
            rst.setToolTip(self.txt("tt_reset_to_default"))
            hbox.addWidget(rst)
            vbox.addLayout(hbox)
            return vbox

        self.input_fs_thresh = QLineEdit()
        self.input_fs_thresh.setText(str(prefs.get('silence_threshold_db', prefs.get('ui_spin_thresh', -42.0))))
        self.input_fs_thresh.setStyleSheet(input_style)
        self.input_fs_thresh.setFixedHeight(30)
        l_fast.addLayout(_row_rst(self.txt("lbl_silence_threshold_db"), self.input_fs_thresh, "-42.0"))
        l_fast.addSpacing(10)

        self.input_fs_pad = QLineEdit()
        self.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.05)))
        self.input_fs_pad.setStyleSheet(input_style)
        self.input_fs_pad.setFixedHeight(30)
        l_fast.addLayout(_row_rst(self.txt("lbl_padding_s"), self.input_fs_pad, "0.05"))
        l_fast.addSpacing(10)

        self.input_fs_min_dur = QLineEdit()
        self.input_fs_min_dur.setText(str(prefs.get('silence_min_dur', 0.2)))
        self.input_fs_min_dur.setStyleSheet(input_style)
        self.input_fs_min_dur.setFixedHeight(30)
        self.input_fs_min_dur.setToolTip(
            "Minimum gap duration (s) to classify as silence. "
            "Lower = more gaps detected. Shared with post-transcript mode."
        )
        l_fast.addLayout(_row_rst(self.txt("lbl_min_silence_dur"), self.input_fs_min_dur, "0.2"))
        l_fast.addSpacing(16)


        # MODE TOGGLES (Mutually Exclusive)
        row_fs_cut = QHBoxLayout()
        lbl_fs_cut = QLabel(self.txt("lbl_cut_silence_directly"))
        lbl_fs_cut.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
        row_fs_cut.addWidget(lbl_fs_cut)
        row_fs_cut.addStretch()
        self.tgl_fs_cut = ToggleSwitch()
        self.tgl_fs_cut.setChecked(prefs.get('fs_cut_mode', True), animated=False)
        row_fs_cut.addWidget(self.tgl_fs_cut)
        l_fast.addLayout(row_fs_cut)
        l_fast.addSpacing(10)

        row_fs_mark = QHBoxLayout()
        lbl_fs_mark = QLabel(self.txt("lbl_mark_silence_with_color"))
        lbl_fs_mark.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
        row_fs_mark.addWidget(lbl_fs_mark)
        row_fs_mark.addStretch()
        self.tgl_fs_mark = ToggleSwitch()
        self.tgl_fs_mark.setChecked(prefs.get('fs_mark_mode', False), animated=False)
        row_fs_mark.addWidget(self.tgl_fs_mark)
        l_fast.addLayout(row_fs_mark)
        l_fast.addSpacing(24)

        # Connect mutual exclusion & auto-saving
        self.tgl_fs_cut.toggled.connect(lambda c: self.tgl_fs_mark.setChecked(False) if c else None)
        self.tgl_fs_mark.toggled.connect(lambda c: self.tgl_fs_cut.setChecked(False) if c else None)
        self.tgl_fs_cut.toggled.connect(lambda v: self._save_single_pref('fs_cut_mode', v))
        self.tgl_fs_mark.toggled.connect(lambda v: self._save_single_pref('fs_mark_mode', v))

        # RUN & BACK BUTTONS
        btn_row_fs = QHBoxLayout()

        # BACK BUTTON
        btn_back = QPushButton(f"← {self.txt('btn_back_to_transcription')}")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(
            f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
            " font-size: 9pt; text-decoration: underline; border: none; padding: 0; text-align: left;"
        )
        btn_back.clicked.connect(lambda: self.welcome_stack.setCurrentIndex(0))
        btn_row_fs.addWidget(btn_back)

        btn_row_fs.addStretch()

        self.btn_run_fs = QPushButton(self.txt("btn_run_standalone_silence"))
        self.btn_run_fs.setCursor(Qt.PointingHandCursor)
        self.btn_run_fs.setFixedHeight(30)
        self.btn_run_fs.setStyleSheet(f'''
            QPushButton {{
                background-color: {config.BTN_BG}; color: #ffffff;
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt; font-weight: bold;
                border: none; border-radius: 3px; padding: 0 18px;
            }}
            QPushButton:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton:pressed {{ background-color: #176e38; }}
        ''')
        self.btn_run_fs.clicked.connect(self._on_fast_silence)
        btn_row_fs.addWidget(self.btn_run_fs)
        
        l_fast.addLayout(btn_row_fs)
        l_fast.addStretch()

        self.welcome_stack.addWidget(p_fast)   # index 1

        # ── Centre horizontally ──────────────────────────────────────────
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch()
        h.addWidget(inner)
        h.addStretch()
        outer.addLayout(h)

        outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        return page

    def _build_page_processing(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page_processing")
        page.setStyleSheet(f"QWidget#page_processing {{ background-color: {config.BG_COLOR}; }}")
        
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_processing_status = QLabel(self.txt("lbl_initializing"), page)
        self.lbl_processing_status.setAlignment(Qt.AlignCenter)
        self.lbl_processing_status.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 13pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        layout.addWidget(self.lbl_processing_status)
        layout.addSpacing(15)
        
        self.bar_processing = LiquidProgressBar(page)
        self.bar_processing.setFixedWidth(400)
        layout.addWidget(self.bar_processing, 0, Qt.AlignCenter)
        return page

    def _update_processing_progress(self, val: int):
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(val)

    def _build_page_editor(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page_editor")
        page.setStyleSheet(f"QWidget#page_editor {{ background-color: {config.BG_COLOR}; }}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.scroll_area = QScrollArea(page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {config.BG_COLOR}; border: none; }}")
        
        self.text_canvas = TranscriptionCanvas(main_window=self)
        self.scroll_area.setWidget(self.text_canvas)
        layout.addWidget(self.scroll_area)
        
        return page

    def _populate_editor(self, words_data, segments_data):
        import copy
        self._chapters = [{
            "name": "Original",
            "tl_name": getattr(self, '_original_timeline_name', ""),
            "words": copy.deepcopy(words_data)
        }]
        self._current_chapter_idx = 0
        
        # Reset UI Dropdown
        self._title_bar.chapter_dropdown.hide()
        self._title_bar.chapter_dropdown.options_list = ["Original"]
        self._title_bar.chapter_dropdown.setText("Original")
        self._title_bar.update_dropdown_placement()
        
        if hasattr(self, 'text_canvas'):
            self.text_canvas.load_data(words_data)

    # ------------------------------------------------------------------
    # Sidebar navigation stubs
    # ------------------------------------------------------------------

    def _on_nav_script(self):
        """Navigate to the Script / Welcome page."""
        self.go_to_page(0)

    def _on_nav_analysis(self):
        """Navigate to the Analysis / Processing page."""
        self.go_to_page(1)

    def _on_start_analysis(self):
        # 1. Hide side panels
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()
        
        # Un-toggle the sidebar buttons so they don't look active
        if hasattr(self, 'btn_nav_script'): self.btn_nav_script.set_active(False)
        if hasattr(self, 'btn_nav_main'): self.btn_nav_main.set_active(False)

        # 2. Switch stack to index 1 (Processing page)
        self.go_to_page(1)
        
        # Reset progress bar UI
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(0)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("txt_initializing_analysis"))

        # 3. Gather settings
        raw_lang = self._combo_lang.text() if hasattr(self, '_combo_lang') else 'Auto'
        lang_code = "auto"
        
        if raw_lang != "Auto":
            for code, name in config.SUPPORTED_LANGUAGES.items():
                if name.lower() == raw_lang.lower():
                    lang_code = code
                    break
                    
        raw_model = self._combo_model.text() if hasattr(self, '_combo_model') else 'Medium'
        model = raw_model.split()[0].lower() # Fixes capital letter issue for Whisper

        # Read selected timeline and audio tracks
        selected_tl = getattr(self, 'combo_tl_0', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        no_tl = self.txt("msg_no_timelines_detected")
        if selected_tl_name == no_tl:
            selected_tl_name = ""

        selected_tracks_combo = getattr(self, 'combo_tr_0', None)
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        settings = {
            "lang": lang_code,
            "model": model,
            "device": "Auto",
            "filler_words": config.DEFAULT_BAD_WORDS,
            "timeline_name": selected_tl_name or None,
            "track_indices": track_indices or None,
        }

        
        # 4. Start thread targeting self.engine.run_analysis_pipeline()
        self._worker_signals = WorkerSignals()
        self._worker_signals.progress.connect(self._on_analysis_progress)
        self._worker_signals.status.connect(self._on_analysis_status)
        self._worker_signals.finished.connect(self._on_analysis_finished)
        self._worker_signals.error.connect(self._on_analysis_error)
        
        def worker_func():
            try:
                words_data, segments_data = self.engine.run_analysis_pipeline(
                    settings, 
                    callback_status=self._worker_signals.status.emit, 
                    callback_progress=self._worker_signals.progress.emit
                )
                self._worker_signals.finished.emit(words_data, segments_data)
            except Exception as e:
                self._worker_signals.error.emit(str(e))
                
        self._analysis_thread = threading.Thread(target=worker_func, daemon=True)
        self._analysis_thread.start()

    def _on_analysis_progress(self, val):
        self._update_processing_progress(val)

    def _on_analysis_status(self, msg):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(msg)

    def _on_analysis_error(self, err):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(f"Error: {err}")

    def _on_analysis_finished(self, words_data, segments_data):
        if not words_data:
            dlg = CustomMsgBox(self, self.txt("msg_analysis_failed"), self.txt("msg_the_transcription_process"), self.txt("btn_ok"))
            dlg.exec()
            # Reset UI to Page 0 and show panels again
            self.go_to_page(0)
            self._panel_left.show()
            self._panel_right.show()
            return
            
        self.go_to_page(2)
        
        self._toggle_activity("script_analysis")
        self._toggle_activity("main_panel")
        
        # Read selected timeline/tracks to format the new title
        selected_tl = getattr(self, 'combo_tl_0', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        selected_tracks_combo = getattr(self, 'combo_tr_0', None)
        
        if not selected_tracks_combo:
            tracks_str = self.txt("txt_all")
        else:
            tracks = list(selected_tracks_combo.selected_items)
            if not tracks or (len(tracks) == len(selected_tracks_combo.options_list)):
                tracks_str = self.txt("txt_all")
            else:
                tracks_str = ", ".join(sorted(tracks))

        msg = self.txt("msg_transcription_source")
        if msg and "{tl}" in msg:
            new_title = msg.replace("{tl}", selected_tl_name).replace("{tr}", tracks_str)
            self._title_bar.set_title(new_title)
            # On macOS native title bar: update the OS window title too
            if platform.system() == "Darwin":
                self.setWindowTitle(new_title)

        # ── CAPTURE SOURCE SNAPSHOT ──────────────────────────────────────────
        # Compute track indices from names (needed for engine assembly)
        all_tracks_available = list(selected_tracks_combo.options_list) if selected_tracks_combo else []
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        self._transcription_source = {
            "timeline_name":  selected_tl_name,
            "track_names":    selected_track_names,
            "track_indices":  track_indices,
            "all_tracks":     (not selected_track_names) or (len(selected_track_names) >= len(all_tracks_available)),
        }
        # Persist snapshot so it survives project export/import
        try:
            prefs = self.engine.load_preferences() or {}
            prefs["transcription_source"] = self._transcription_source
            self.engine.save_preferences(prefs)
        except Exception as _e:
            from osdoc import log_error as _log_error
            _log_error(f"Could not persist transcription_source: {_e}")

        self._populate_editor(words_data, segments_data)


    def _on_nav_markers(self):
        """Toggle the right panel (placeholder)."""
        print("[BadWordsGUI] Tools toggled (Stage 4 TODO)")

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def _maximize_on_active_screen(self):
        """
        Move the window to the monitor that currently has the cursor and maximize.
        DWM / the WM remembers the geometry that was set IMMEDIATELY before
        showMaximized() as the "restore" size used when drag-to-unmaximizing.
        We position 580x670 centered on the target screen first, THEN maximize,
        so the restore size is always 580x670 regardless of previous session state.
        """
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(580, 670)
            self.showMaximized()
            return
        sg = screen.availableGeometry()
        # Center 580x670 on the target screen — this becomes the restore geometry
        self.setGeometry(
            sg.x() + (sg.width()  - 580) // 2,
            sg.y() + (sg.height() - 670) // 2,
            580, 670
        )
        self.showMaximized()

    # ------------------------------------------------------------------
    # Action handlers (stubs — logic added in later stages)
    # ------------------------------------------------------------------

    def _on_clear_transcript(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return
            
        msg_box = CustomMsgBox(self, self.txt("msg_clear_title"), self.txt("msg_clear_desc"), self.txt("btn_yes"), self.txt("btn_no"))
        if msg_box.exec() == QDialog.Accepted:
            undo_action = {"type": "paint", "changes": {}}
            for w in self.text_canvas.words_data:
                has_inaud = (w.get('is_inaudible') or w.get('type') == 'inaudible')
                needs_suppress = has_inaud and not w.get('overlay_suppressed', False)
                
                if (w.get('status') or w.get('manual_status') or w.get('algo_status') or 
                    w.get('is_auto') or w.get('selected') or needs_suppress):
                    
                    undo_action["changes"][w['id']] = {
                        'status': w.get('status'),
                        'manual_status': w.get('manual_status'),
                        'algo_status': w.get('algo_status'),
                        'is_auto': w.get('is_auto'),
                        'selected': w.get('selected'),
                        'overlay_suppressed': w.get('overlay_suppressed', False)
                    }
                    w['status'] = None
                    w['manual_status'] = None
                    w['algo_status'] = None
                    w['is_auto'] = False
                    w['selected'] = False
                    if has_inaud:
                        w['overlay_suppressed'] = True
                        
                    self._calculate_visual_layer(w)

            if hasattr(self, 'undo_manager') and undo_action["changes"]:
                self.undo_manager.push(undo_action)
                
            self.text_canvas.update()

    def _on_add_custom_marker(self):
        from PySide6.QtWidgets import QApplication
        dlg = SettingsDialog(self.engine, self)
        # Navigate to Custom Markers tab dynamically by matching the translated tab name
        custom_markers_label = dlg.txt("tab_custom_markers")
        for i in range(dlg.category_list.count()):
            if dlg.category_list.item(i).text() == custom_markers_label:
                dlg.stack.setCurrentIndex(i)
                dlg.category_list.setCurrentRow(i)
                break
        dlg.exec()
        self._build_marker_radio_buttons()
        self.text_canvas.update()

    def _build_marker_radio_buttons(self):
        # Clear layout
        while self.markers_layout.count():
            item = self.markers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        def style_rb(rb, color):
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: {color};
                    font-size: 11pt;
                    font-weight: bold;
                    background: transparent;
                    padding: 2px 5px;
                }}
                QRadioButton::indicator {{
                    width: 15px; height: 15px;
                    border-radius: 8px;
                    border: 2px solid #555;
                    background: #1a1a1a;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #555;
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 {color},
                        stop:0.4 {color},
                        stop:0.5 #1a1a1a,
                        stop:1 #1a1a1a
                    );
                }}
            """)

        self.marker_btn_group = QButtonGroup(self)
        
        rb_red = MarqueeRadioButton(self.txt("rad_red_cut_filler"))
        rb_red.setProperty("status_id", "bad")
        style_rb(rb_red, config.WORD_BAD_BG)
        
        rb_blue = MarqueeRadioButton(self.txt("rad_blue_retake"))
        rb_blue.setProperty("status_id", "repeat")
        style_rb(rb_blue, config.WORD_REPEAT_BG)
        
        rb_green = MarqueeRadioButton(self.txt("rad_green_typo"))
        rb_green.setProperty("status_id", "typo")
        style_rb(rb_green, config.WORD_TYPO_BG)
        
        rb_eraser = MarqueeRadioButton(self.txt("rad_eraser_clear"))
        rb_eraser.setProperty("status_id", "eraser")
        rb_eraser.setStyleSheet("""
            QRadioButton {
                color: #aaaaaa; font-size: 11pt; font-weight: bold;
                background: transparent;
                padding: 2px 5px;
            }
            QRadioButton::indicator {
                width: 15px; height: 15px;
                border-radius: 8px;
                border: 2px solid #555;
                background: #1a1a1a;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #555;
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #aaaaaa,
                    stop:0.4 #aaaaaa,
                    stop:0.5 #1a1a1a,
                    stop:1 #1a1a1a
                );
            }
        """)
        
        for rb in (rb_red, rb_blue, rb_green):
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            self.markers_layout.addWidget(rb)
            self.marker_btn_group.addButton(rb)
            
        custom_markers = self.engine.load_preferences().get('custom_markers', [])
        for cm in custom_markers:
            name, color = cm.get("name", ""), cm.get("color", "")
            if not name: continue
            # Translate the color name for display; keep English key in status_id
            translated_color = self.txt(f"resolve_color_{color.lower()}")
            # Format: TranslatedColor (Name)
            rb = MarqueeRadioButton(f"{translated_color} ({name})")
            rb.setProperty("status_id", f"custom_{color}")
            style_rb(rb, config.RESOLVE_COLORS_HEX.get(color, '#ffffff'))
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            self.markers_layout.addWidget(rb)
            self.marker_btn_group.addButton(rb)

        rb_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.markers_layout.addWidget(rb_eraser)
        self.marker_btn_group.addButton(rb_eraser)
            
        self.rb_mark_bad       = rb_red
        self.rb_mark_repeat    = rb_blue
        self.rb_mark_typo      = rb_green
        self.rb_mark_inaudible = rb_eraser  # closest available; no dedicated inaudible radio
        rb_red.setChecked(True)

    def _setup_hardcoded_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Export
        self.sc_export = QShortcut(QKeySequence.Save, self, context=Qt.ApplicationShortcut)
        self.sc_export.activated.connect(self._on_export_project)
        
        # Undo
        self.sc_undo = QShortcut(QKeySequence.Undo, self, context=Qt.ApplicationShortcut)
        self.sc_undo.activated.connect(self.undo_manager.undo)
        
        # Redo (OS Default)
        self.sc_redo = QShortcut(QKeySequence.Redo, self, context=Qt.ApplicationShortcut)
        self.sc_redo.activated.connect(self.undo_manager.redo)
        
        # Redo Explicit Overrides (ensures Ctrl+Y natively works on Linux even if OS wants Ctrl+Shift+Z)
        self.sc_redo_y = QShortcut(QKeySequence("Ctrl+Y"), self, context=Qt.ApplicationShortcut)
        self.sc_redo_y.activated.connect(self.undo_manager.redo)
        
        self.sc_redo_shift_z = QShortcut(QKeySequence("Ctrl+Shift+Z"), self, context=Qt.ApplicationShortcut)
        self.sc_redo_shift_z.activated.connect(self.undo_manager.redo)

    def _apply_dynamic_shortcuts(self):
        """
        Build (or rebuilds) all dynamic QShortcuts from the saved preferences.
        Clears previously registered shortcuts first to avoid duplicates.
        'jump_to_word' and 'play_stop' are display-only and not registered.
        """
        from PySide6.QtGui import QShortcut, QKeySequence

        # Remove previously registered dynamic shortcuts
        for sc in getattr(self, '_active_shortcuts', []):
            try:
                sc.setEnabled(False)
                sc.setKey(QKeySequence())
                sc.setParent(None)
                sc.deleteLater()
            except RuntimeError:
                pass
        self._active_shortcuts = []

        prefs = self.engine.load_preferences() or {}
        shortcuts = {**config.DEFAULT_SETTINGS.get('shortcuts', {}), **prefs.get('shortcuts', {})}

        # Keys that are informational only — never register as QShortcut
        DISPLAY_ONLY_KEYS = {'jump_to_word', 'play_stop'}

        def _make(seq, slot):
            """Helper: register one QShortcut with ApplicationShortcut context."""
            if not seq or seq in ('', 'Ctrl+RMB', 'Space'):
                return
            try:
                sc = QShortcut(QKeySequence(seq), self, context=Qt.ApplicationShortcut)
                sc.activated.connect(slot)
                self._active_shortcuts.append(sc)
            except Exception:
                pass

        # search — open search overlay
        _make(shortcuts.get('search', 'Ctrl+F'), self.search_overlay.toggle_search)

        # open_settings — open settings dialog (default: Escape)
        # Note: Escape also closes search; handled by priority in event chain
        _make(shortcuts.get('open_settings', 'Escape'), self._on_settings)

        # Marker shortcuts — click the corresponding radio button
        def _check_rb(rb):
            """Click (check) the given radio button if it exists."""
            def _do():
                try:
                    rb.setChecked(True)
                except RuntimeError:
                    pass
            return _do

        if hasattr(self, 'rb_mark_bad'):
            _make(shortcuts.get('mark_red', '1'),    _check_rb(self.rb_mark_bad))
        if hasattr(self, 'rb_mark_repeat'):
            _make(shortcuts.get('mark_blue', '2'),   _check_rb(self.rb_mark_repeat))
        if hasattr(self, 'rb_mark_typo'):
            _make(shortcuts.get('mark_green', '3'),  _check_rb(self.rb_mark_typo))
        if hasattr(self, 'rb_mark_inaudible'):
            _make(shortcuts.get('mark_eraser', '4'), _check_rb(self.rb_mark_inaudible))

        # Custom marker shortcuts — each registered key selects the matching radio button
        custom_markers = prefs.get('custom_markers', [])
        for cm in custom_markers:
            name  = cm.get('name', '')
            color = cm.get('color', '')
            if not name:
                continue
            s_key = f'custom_marker_{name}'
            seq   = shortcuts.get(s_key, '')
            if not seq:
                continue
            # Find the radio button with matching status_id
            target_status_id = f'custom_{color}'
            rb_target = None
            if hasattr(self, 'marker_btn_group'):
                for rb in self.marker_btn_group.buttons():
                    try:
                        if rb.property('status_id') == target_status_id \
                                and rb.text().endswith(f'({name})'):
                            rb_target = rb
                            break
                    except RuntimeError:
                        pass
            if rb_target is not None:
                _make(seq, _check_rb(rb_target))


    def _on_settings(self):
        """Open settings panel."""
        dlg = SettingsDialog(self.engine, self)
        dlg.exec()
        self._build_marker_radio_buttons()
        self._apply_dynamic_shortcuts()
        self.text_canvas.update()
        
        # Explicitly reactivate the main window to ensure ApplicationShortcut context binds properly
        self.activateWindow()
        self.setFocus()




    # ------------------------------------------------------------------
    # Page navigation
    # ------------------------------------------------------------------

    def go_to_page(self, index: int):
        """
        Switch the central QStackedWidget to *index*.
        """
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def check_telemetry(self):
        """Show TelemetryPopup if consent has never been recorded."""
        opt_in = self.engine.os_doc.get_telemetry_pref("telemetry_opt_in")
        if opt_in is None:
            popup = TelemetryPopup(self.engine, parent=self)
            self.engine.os_doc.force_dark_titlebar(int(popup.winId()))
            popup.exec()  # ApplicationModal — blocks until user responds
        elif opt_in is True:
            self.engine.send_telemetry_ping("app_started")

    # ------------------------------------------------------------------
    # Translation helper
    # ------------------------------------------------------------------

    def txt(self, key: str, **kwargs) -> str:
        return _txt(self.lang, key, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        msg_box = CustomMsgBox(self, self.txt('msg_quit_title'), self.txt('msg_quit_desc'), self.txt('btn_yes'), self.txt('btn_no'))
        if msg_box.exec() == QDialog.Accepted:
            event.accept()
            if self.closeEvent_callback:
                self.closeEvent_callback()
        else:
            event.ignore()
