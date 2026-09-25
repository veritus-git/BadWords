#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: top_status_island.py
ROLE: GUI Component
DESCRIPTION:
Dynamic top island status widget displayed under the title bar.
Shapes 1:1 identically to AudioToggleTab (inverted trapezoid with curved bezier shoulders),
providing minimalist feedback during transcription with pure vector graphics (zero emojis).
"""

import re
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QVariantAnimation, QEasingCurve,
    Property, QEvent
)
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QFontMetrics
)
import config
from gui.vsync import get_refresh_interval_ms


class TopStatusIsland(QWidget):
    """
    A dynamic island widget attached to the bottom edge of the title bar.
    Shaped 1:1 like AudioToggleTab with smooth bezier shoulders, centered horizontally,
    with automatic width adjustment, animated slide-in/out, and minimalist vector rendering.
    """

    def __init__(self, parent_frame, main_window):
        super().__init__(parent_frame)
        self.main_window = main_window
        self.parent_frame = parent_frame

        self.setObjectName("TopStatusIsland")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("background: transparent; border: none;")

        # State
        self._state = "idle"  # "idle", "working", "completed", "error"
        self._title_text = ""
        self._percent_text = ""
        
        # Dimensions matching AudioToggleTab proportions
        self._c1 = float(config.S(12.0))
        self._c2 = float(config.S(15.0))
        self._c3 = float(config.S(25.0))
        self._island_height = float(config.S(24.0))

        self._current_width = float(config.S(190))
        self._target_width = float(config.S(190))
        self._pos_y = -self._island_height
        self._spinner_angle = 0

        # Vsync timer for smooth vector spinner animation
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(get_refresh_interval_ms())
        self._spinner_timer.timeout.connect(self._on_spinner_tick)

        # Width morphing animation
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(220)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.valueChanged.connect(self._on_width_anim_step)

        # Y position slide animation
        self._pos_anim = QVariantAnimation(self)
        self._pos_anim.setDuration(300)
        self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._pos_anim.valueChanged.connect(self._on_pos_anim_step)

        # Auto-dismiss timer for completion state
        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.slide_out)

        # Parent event filter for window resize
        if parent_frame:
            parent_frame.installEventFilter(self)

        self.setFixedHeight(int(self._island_height))
        self.setFixedWidth(int(self._current_width))
        self.hide()

    def _get_titlebar_bottom_y(self) -> float:
        """Returns the bottom Y coordinate of the title bar."""
        tb = getattr(self.main_window, '_title_bar', None)
        if tb and tb.isVisible():
            return float(tb.y() + tb.height())
        return 0.0

    def _on_pos_anim_step(self, val):
        self._pos_y = float(val)
        self._reposition()

    def _on_width_anim_step(self, val):
        self._current_width = float(val)
        self.setFixedWidth(int(self._current_width))
        self._reposition()
        self.update()

    def _on_spinner_tick(self):
        if self._state == "working":
            self._spinner_angle = (self._spinner_angle + 6) % 360
            self.update()

    def _ensure_z_order(self):
        """Ensures the island stays above content views but strictly behind/under the title bar."""
        self.raise_()
        tb = getattr(self.main_window, '_title_bar', None)
        if tb and tb.parent() == self.parent():
            self.stackUnder(tb)

    def _reposition(self):
        """Always centers horizontally inside the parent frame at the current Y."""
        if not self.parent_frame:
            return
        pw = float(self.parent_frame.width())
        x = (pw - self._current_width) / 2.0
        self.move(int(x), int(self._pos_y))
        self._ensure_z_order()

    def eventFilter(self, watched, event):
        if watched == self.parent_frame and event.type() == QEvent.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def _calculate_target_width(self) -> float:
        """Calculates optimal tab width based on text and shoulder curves (no dot)."""
        font_name = config.UI_FONT_NAME
        f_lbl = QFont(font_name, config.FS(8.5))
        f_bold = QFont(font_name, config.FS(8.5), QFont.Bold)
        fm_lbl = QFontMetrics(f_lbl)
        fm_bold = QFontMetrics(f_bold)

        icon_w = float(config.S(14.0))
        icon_gap = float(config.S(8.0))
        title_w = fm_lbl.horizontalAdvance(self._title_text) if self._title_text else 0
        pct_w = (float(config.S(8.0)) + fm_bold.horizontalAdvance(self._percent_text)) if self._percent_text else 0
        pad_x = float(config.S(18.0))

        content_w = icon_w + icon_gap + title_w + pct_w + pad_x
        # Total width = content + both curved shoulders (2 * c3)
        total_w = content_w + (self._c3 * 2.0)
        return max(float(config.S(160)), total_w)

    def _animate_to_target_width(self):
        new_target = self._calculate_target_width()
        if abs(new_target - self._target_width) > 2.0:
            self._target_width = new_target
            if self._width_anim.state() == QVariantAnimation.Running:
                self._width_anim.stop()
            self._width_anim.setStartValue(self._current_width)
            self._width_anim.setEndValue(self._target_width)
            self._width_anim.start()

    # --- Public Control API ---

    def show_progress(self, title: str, percent: int = -1):
        """Display the island with active spinning indicator and percentage."""
        self._state = "working"
        cleaned_title = re.sub(r'[\s:•–-]*\d+%\s*$', '', title).strip()
        self._title_text = cleaned_title
        self._percent_text = f"{percent}%" if percent >= 0 else ""

        if not self._spinner_timer.isActive():
            self._spinner_timer.start()

        self._animate_to_target_width()
        self.show()
        self._ensure_z_order()

        target_y = self._get_titlebar_bottom_y()
        if self._pos_y < target_y:
            if self._pos_anim.state() == QVariantAnimation.Running:
                self._pos_anim.stop()
            self._pos_anim.setStartValue(target_y - self._island_height)
            self._pos_anim.setEndValue(target_y)
            self._pos_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._pos_anim.start()
        else:
            self._pos_y = target_y
            self._reposition()

        self.update()

    def update_percent(self, percent: int):
        """Minimalist progress update: updates the percentage badge."""
        self._percent_text = f"{percent}%" if percent >= 0 else ""
        self._animate_to_target_width()
        self.update()

    def update_chunk_info(self, c_idx: int = 0, tot: int = -1, pct: int = -1):
        """Compatibility method for chunk stream updates; minimalist: shows percent only."""
        self.update_percent(pct)

    def set_status(self, text: str):
        """Update the main title text, stripping any redundant trailing percentage."""
        cleaned = re.sub(r'[\s:•–-]*\d+%\s*$', '', text).strip()
        self._title_text = cleaned
        self._animate_to_target_width()
        self.update()

    def set_completed(self, message: str = ""):
        """Switch to completion state with green vector checkmark and auto-dismiss."""
        self._state = "completed"
        if self._spinner_timer.isActive():
            self._spinner_timer.stop()

        self._title_text = message if message else (
            self.main_window.txt("msg_transcription_complete") if hasattr(self.main_window, 'txt') else "Complete"
        )
        self._percent_text = ""

        self._animate_to_target_width()
        self.update()

        # Auto-slide out after 2.5 seconds
        self._dismiss_timer.start(2500)

    def set_error(self, err_msg: str):
        """Switch to error state with warning icon."""
        self._state = "error"
        if self._spinner_timer.isActive():
            self._spinner_timer.stop()

        self._title_text = f"Error: {err_msg}"
        self._percent_text = ""

        self._animate_to_target_width()
        self.update()
        self._dismiss_timer.start(4000)

    def slide_out(self):
        """Smoothly slide the island back up behind the title bar."""
        self._ensure_z_order()
        target_y = self._get_titlebar_bottom_y() - self._island_height
        if self._pos_anim.state() == QVariantAnimation.Running:
            self._pos_anim.stop()
        self._pos_anim.setStartValue(self._pos_y)
        self._pos_anim.setEndValue(target_y)
        self._pos_anim.setEasingCurve(QEasingCurve.InCubic)

        def on_finished():
            self.hide()
            self._state = "idle"
            if self._spinner_timer.isActive():
                self._spinner_timer.stop()

        self._pos_anim.finished.connect(on_finished)
        self._pos_anim.start()

    # --- Vector Rendering (QPainter) ---
    # Shaped 1:1 like AudioToggleTab (inverted trapezoid with curved shoulders)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        c1 = self._c1
        c2 = self._c2
        c3 = self._c3

        # 1. Inverted Trapezoid Path with curved shoulders (1:1 mirror of AudioToggleTab)
        path = QPainterPath()
        # Top-left corner attached flush to title bar
        path.moveTo(0.0, 0.0)
        # Left shoulder curves down to bottom edge
        path.cubicTo(c1, 0.0, c2, h, c3, h)
        # Flat bottom edge
        path.lineTo(w - c3, h)
        # Right shoulder curves back up to top edge
        path.cubicTo(w - c2, h, w - c1, 0.0, w, 0.0)
        path.closeSubpath()

        # Fill background - subtly darker than the title bar (#191919) to cut cleanly
        bg_col = QColor("#111113")
        p.fillPath(path, QBrush(bg_col))

        # Border outline along shoulders and bottom edge
        if self._state == "completed":
            border_col = QColor("#23a559")
        elif self._state == "error":
            border_col = QColor("#e74c3c")
        else:
            border_col = QColor("#222225")
        border_path = QPainterPath()
        border_path.moveTo(0.5, 0.0)
        border_path.cubicTo(c1, 0.5, c2, h - 0.5, c3, h - 0.5)
        border_path.lineTo(w - c3, h - 0.5)
        border_path.cubicTo(w - c2, h - 0.5, w - c1, 0.5, w - 0.5, 0.0)
        p.setPen(QPen(border_col, 1.0))
        p.drawPath(border_path)

        # 2. Typography & Text metrics
        font_name = config.UI_FONT_NAME
        f_lbl = QFont(font_name, config.FS(8.5))
        f_bold = QFont(font_name, config.FS(8.5), QFont.Bold)
        fm_lbl = QFontMetrics(f_lbl)
        fm_bold = QFontMetrics(f_bold)

        icon_w = float(config.S(14.0))
        icon_gap = float(config.S(8.0))
        title_w = fm_lbl.horizontalAdvance(self._title_text) if self._title_text else 0
        pct_w = (float(config.S(8.0)) + fm_bold.horizontalAdvance(self._percent_text)) if self._percent_text else 0
        total_content_w = icon_w + icon_gap + title_w + pct_w

        # Center inside flat bottom area [c3, w - c3]
        flat_w = w - 2.0 * c3
        start_x = c3 + max(0.0, (flat_w - total_content_w) / 2.0)

        # 3. Vector Status Indicator (Zero emojis)
        icon_cx = start_x + icon_w / 2.0
        icon_cy = h / 2.0
        icon_r = float(config.S(5.0))

        if self._state == "working":
            p.save()
            p.translate(icon_cx, icon_cy)
            p.rotate(self._spinner_angle)

            arc_rect = QRectF(-icon_r, -icon_r, icon_r * 2.0, icon_r * 2.0)
            spinner_pen = QPen(QColor("#23a559"), config.S(1.6), Qt.SolidLine, Qt.RoundCap)
            p.setPen(spinner_pen)
            p.drawArc(arc_rect, 0, 270 * 16)
            p.restore()

        elif self._state == "completed":
            check_pen = QPen(QColor("#2ecc71"), config.S(1.6), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(check_pen)
            check_path = QPainterPath()
            check_path.moveTo(icon_cx - config.S(4.0), icon_cy)
            check_path.lineTo(icon_cx - config.S(1.0), icon_cy + config.S(3.0))
            check_path.lineTo(icon_cx + config.S(4.5), icon_cy - config.S(3.0))
            p.drawPath(check_path)

        elif self._state == "error":
            err_pen = QPen(QColor("#e74c3c"), config.S(1.6), Qt.SolidLine, Qt.RoundCap)
            p.setPen(err_pen)
            p.drawEllipse(QPointF(icon_cx, icon_cy), icon_r, icon_r)
            p.drawLine(QPointF(icon_cx, icon_cy - icon_r + 2.5), QPointF(icon_cx, icon_cy + 0.5))
            p.drawPoint(QPointF(icon_cx, icon_cy + icon_r - 2.0))

        # 4. Text layout (minimalist: text + green % only, NO bullet dot)
        cur_x = start_x + icon_w + icon_gap
        text_y = (h + fm_lbl.ascent() - fm_lbl.descent()) / 2.0

        # Title (e.g. Transkrybowanie...)
        if self._title_text:
            p.setFont(f_lbl)
            p.setPen(QColor("#a2a2a8"))
            p.drawText(QPointF(cur_x, text_y), self._title_text)
            cur_x += title_w

        # Percent badge (e.g. 25% directly, NO bullet dot)
        if self._percent_text:
            cur_x += float(config.S(8))
            p.setFont(f_bold)
            p.setPen(QColor("#23a559"))
            p.drawText(QPointF(cur_x, text_y), self._percent_text)
