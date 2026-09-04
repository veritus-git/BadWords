#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: delegates.py
ROLE: GUI Widget
DESCRIPTION:
MVC delegates responsible for custom drawing of list items.
"""

from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config
from i18n import get_trans
from gui.vsync import get_refresh_interval_ms
import sys
import os
import time
import traceback
import ctypes
import threading
from PySide6.QtWidgets import QStyledItemDelegate, QStyle

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QCheckBox,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QAbstractItemView, QFrame, QScrollArea,
    QDockWidget, QToolBar, QStackedWidget, QFormLayout, QComboBox,
    QSpacerItem, QCompleter, QLineEdit, QWidgetAction, QToolTip,
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter, QSplitterHandle,
    QTabWidget, QSpinBox, QButtonGroup, QLayout
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation, Property, QThread
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter, QPen, QFontMetrics, QLinearGradient
)
from PySide6.QtCore import QMimeData

import config

# --- INJECTED WIDGET IMPORTS ---
from gui.widgets.buttons import QPushButton, MarqueeRadioButton, ToggleSwitch, ShortcutCaptureButton, MouseShortcutCaptureButton, AnimatedPlayerButton, AudioToggleTab, SidebarButton, CustomDropdown, TitleDropdown, SpeedDropdown, MultiSelectDropdown, SearchableDropdown, AssembleArrowButton, AssembleSplitButton
from gui.widgets.labels import QLabel, IDETooltip, MarqueeLabel
from gui.widgets.layouts import FlowLayout, MainPanelWidget
from gui.widgets.progress_bar import LiquidProgressBar
from gui.widgets.language_selector import _LangPickerDialog
from gui.widgets.splitters import GripHandle, GripSplitter
from gui.widgets.text_edits import WrappingPlaceholderTextEdit, SBSTextEdit
from gui.widgets.sliders import JumpSlider
# -------------------------------

class MarqueeItemDelegate(QStyledItemDelegate):
    """Delegate for QListWidget that draws item text with a smooth marquee
    animation on hover when the text is wider than the available column width.
    Completely replaces the default item renderer — no horizontal scrollbar needed.
    """
    _PADDING = 16  # default for main views and settings tabs

    def __init__(self, list_widget, padding=None):
        super().__init__(list_widget)
        self._lw = list_widget
        self._padding = self._PADDING if padding is None else padding
        # State per row index
        self._mq_pos   = {}   # float offset
        self._mq_alpha = {}   # 0.0–1.0 fade
        self._mq_state = {}   # str state machine
        self._mq_ticks = {}   # int tick counter
        self._hovered_row = -1

        self._timer = QTimer(self)
        self._timer.setInterval(get_refresh_interval_ms())
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
        """Pixel width available for text inside the list (minus padding and margins)."""
        vp_w = self._lw.viewport().width()
        padding = self._padding if self._padding is not None else 16
        border_pad = config.S(2) if hasattr(config, 'S') else 2
        buffer = config.S(6) if hasattr(config, 'S') else 6
        return max(10, vp_w - padding * 2 - border_pad - buffer)

    def _font_for_row(self, row):
        """Return the effective QFont for a specific row, falling back to list font."""
        from PySide6.QtWidgets import QStyleOptionViewItem
        opt = QStyleOptionViewItem()
        opt.font = self._lw.font()
        idx = self._lw.model().index(row, 0)
        self.initStyleOption(opt, idx)
        f = getattr(opt, 'font', None)
        if f is not None and hasattr(f, 'pointSize') and f.pointSize() > 0:
            return QFont(f)
        return QFont(self._lw.font())

    def _text_overflows(self, row):
        item = self._lw.item(row)
        if item is None:
            return False
        fm = QFontMetrics(self._font_for_row(row))
        return fm.horizontalAdvance(item.text()) > self._available_width()

    def eventFilter(self, obj, event):
        try:
            lw_vp = self._lw.viewport()
        except RuntimeError:
            return False
        if obj is lw_vp:
            if event.type() in (QEvent.Type.MouseMove, QEvent.Type.Enter):
                pos = event.position().toPoint() if hasattr(event, 'position') else (event.pos() if hasattr(event, 'pos') else self._lw.viewport().mapFromGlobal(QCursor.pos()))
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
        fm = QFontMetrics(self._font_for_row(row))
        avail = self._available_width()
        max_scroll = float(max(0, fm.horizontalAdvance(item.text()) - avail))

        state = self._row_state(row)
        iv = max(1, self._timer.interval())
        delay_threshold = int(round(640 / iv))
        scroll_step = 31.25 * (iv / 1000.0)
        fade_step = 0.05 * (iv / 16.0)

        if state == "START_DELAY":
            self._mq_ticks[row] += 1
            if self._mq_ticks[row] > delay_threshold:
                self._mq_state[row] = "SCROLL"
                self._mq_ticks[row] = 0
        elif state == "SCROLL":
            self._mq_pos[row] += scroll_step
            if self._mq_pos[row] >= max_scroll:
                self._mq_pos[row] = max_scroll
                self._mq_state[row] = "END_DELAY"
                self._mq_ticks[row] = 0
        elif state == "END_DELAY":
            self._mq_ticks[row] += 1
            if self._mq_ticks[row] > delay_threshold:
                self._mq_state[row] = "FADEOUT"
                self._mq_ticks[row] = 0
        elif state == "FADEOUT":
            self._mq_alpha[row] -= fade_step
            if self._mq_alpha[row] <= 0.0:
                self._mq_alpha[row] = 0.0
                self._mq_pos[row] = 0.0
                self._mq_state[row] = "FADEIN"
        elif state == "FADEIN":
            self._mq_alpha[row] += fade_step
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
        fm = QFontMetrics(option.font) if hasattr(option, 'font') else painter.fontMetrics()
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

        # Check alignment for RTL support
        align = item.textAlignment()
        is_rtl = bool(align & Qt.AlignRight)

        # Clip to the content rect to hide overflow, clamped to viewport width
        vp_w = self._lw.viewport().width()
        text_rect = option.rect.adjusted(self._padding, 0, -self._padding, 0)
        if text_rect.right() > vp_w - self._padding:
            text_rect.setRight(vp_w - self._padding)
        painter.setClipRect(text_rect)

        offset = int(self._mq_pos.get(row, 0.0)) if is_animating else 0

        # Show elided text with "…" when overflowing but not yet scrolling,
        # and draw full text once the marquee animation has started moving.
        scrolling = is_animating and (offset > 0 or self._mq_state.get(row) in ("SCROLL", "END_DELAY", "FADEOUT", "FADEIN"))
        if overflows and not scrolling:
            elide_mode = Qt.ElideLeft if is_rtl else Qt.ElideRight
            display_text = fm.elidedText(text, elide_mode, avail)
        else:
            display_text = text

        if is_rtl:
            # For RTL: right-aligned; marquee offset reveals hidden text on the left
            text_width = fm.horizontalAdvance(display_text)
            draw_rect = QRect(text_rect.right() - text_width + offset, text_rect.top(), text_width, text_rect.height())
            painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
        else:
            draw_rect = QRect(text_rect.left() - offset, text_rect.top(), 9999, text_rect.height())
            painter.drawText(draw_rect, Qt.AlignLeft | Qt.AlignVCenter, display_text)
        painter.restore()

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        # Prevent item width from exceeding viewport width so horizontal layout stays clean
        try:
            vp_w = self._lw.viewport().width()
            if vp_w > 0 and hint.width() > vp_w:
                hint.setWidth(vp_w)
        except Exception:
            pass
        return hint





# ==========================================
# PHASE 7 CLASSES: WORKER, PROGRESS BAR, CANVAS
