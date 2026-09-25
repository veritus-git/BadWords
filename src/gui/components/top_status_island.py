#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: top_status_island.py
ROLE: GUI Component
DESCRIPTION:
Dynamic top island status widget displayed under the title bar.
Provides real-time, non-blocking feedback during transcription with smooth micro-animations.
"""

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
    A dynamic island widget floating right beneath the title bar.
    Centered horizontally with automatic width adjustment based on content,
    animated slide-in/slide-out, smooth width morphing, and pure vector rendering (zero emojis).
    """

    def __init__(self, parent_frame, main_window):
        super().__init__(parent_frame)
        self.main_window = main_window
        self.parent_frame = parent_frame

        self.setObjectName("TopStatusIsland")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFocusPolicy(Qt.NoFocus)

        # State
        self._state = "idle"  # "idle", "working", "completed", "error"
        self._title_text = ""
        self._subtitle_text = ""
        self._percent_text = ""
        
        # Dimensions & animation values
        self._current_width = float(config.S(220))
        self._target_width = float(config.S(220))
        self._island_height = float(config.S(30))
        self._pos_y = -self._island_height
        self._opacity = 1.0
        self._spinner_angle = 0

        # High-performance vsync timer for vector spinner animation
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
        self._pos_anim.setDuration(320)
        self._pos_anim.setEasingCurve(QEasingCurve.OutBack)
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

    # --- Property Getters/Setters for Animations ---

    def _get_pos_y(self) -> float:
        return self._pos_y

    def _set_pos_y(self, val: float):
        self._pos_y = float(val)
        self._reposition()

    pos_y = Property(float, _get_pos_y, _set_pos_y)

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

    def _get_target_y(self) -> float:
        """Target Y position directly under the title bar."""
        tb = getattr(self.main_window, '_title_bar', None)
        if tb and tb.isVisible():
            return float(tb.height() + config.S(6))
        return float(config.S(6))

    def _reposition(self):
        """Always centers horizontally inside the parent frame."""
        if not self.parent_frame:
            return
        pw = float(self.parent_frame.width())
        x = (pw - self._current_width) / 2.0
        self.move(int(x), int(self._pos_y))

    def eventFilter(self, watched, event):
        if watched == self.parent_frame and event.type() == QEvent.Resize:
            self._reposition()
        return super().eventFilter(watched, event)

    def _calculate_target_width(self) -> float:
        """Calculates optimal capsule width based on current text tokens and font metrics."""
        font_name = config.UI_FONT_NAME
        f_lbl = QFont(font_name, config.FS(9))
        f_bold = QFont(font_name, config.FS(9), QFont.Bold)
        fm_lbl = QFontMetrics(f_lbl)
        fm_bold = QFontMetrics(f_bold)

        # Base padding: icon (20px) + margins (32px) + gaps (16px)
        w = float(config.S(68))

        if self._title_text:
            w += fm_lbl.horizontalAdvance(self._title_text)
        if self._subtitle_text:
            w += fm_bold.horizontalAdvance(self._subtitle_text) + float(config.S(16))  # Include bullet
        if self._percent_text:
            w += fm_bold.horizontalAdvance(self._percent_text) + float(config.S(16))   # Include bullet

        return max(float(config.S(200)), w)

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

    def show_progress(self, title: str, subtitle: str = "", percent: int = -1):
        """Display the island with active spinning indicator and progress."""
        self._state = "working"
        self._title_text = title
        self._subtitle_text = subtitle
        self._percent_text = f"{percent}%" if percent >= 0 else ""

        if not self._spinner_timer.isActive():
            self._spinner_timer.start()

        self._animate_to_target_width()
        self.show()
        self.raise_()

        # Slide down animation if not already visible
        target_y = self._get_target_y()
        if self._pos_y < 0:
            if self._pos_anim.state() == QVariantAnimation.Running:
                self._pos_anim.stop()
            self._pos_anim.setStartValue(-self._island_height)
            self._pos_anim.setEndValue(target_y)
            self._pos_anim.setEasingCurve(QEasingCurve.OutBack)
            self._pos_anim.start()
        else:
            self._pos_y = target_y
            self._reposition()

        self.update()

    def update_chunk_info(self, current_chunk: int, total_chunks: int, percent: int = -1):
        """Update progress for chunked transcription."""
        lang_code = getattr(self.main_window, 'lang', 'en')
        from gui.utils import _txt
        chunk_word = _txt(lang_code, "lbl_island") if hasattr(self.main_window, 'txt') else "Island"
        if not chunk_word or chunk_word.startswith("!"):
            chunk_word = "Island"

        title = self.main_window.txt("status_transcribing") if hasattr(self.main_window, 'txt') else "Transcribing..."
        subtitle = f"{chunk_word} {current_chunk}/{total_chunks}"
        self.show_progress(title, subtitle, percent)

    def set_status(self, text: str):
        """Update the main title text."""
        self._title_text = text
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
        self._subtitle_text = ""
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
        self._subtitle_text = ""
        self._percent_text = ""

        self._animate_to_target_width()
        self.update()
        self._dismiss_timer.start(4000)

    def slide_out(self):
        """Smoothly slide the island back up under the title bar."""
        if self._pos_anim.state() == QVariantAnimation.Running:
            self._pos_anim.stop()
        self._pos_anim.setStartValue(self._pos_y)
        self._pos_anim.setEndValue(-self._island_height - 10)
        self._pos_anim.setEasingCurve(QEasingCurve.InQuad)

        def on_finished():
            self.hide()
            self._state = "idle"
            if self._spinner_timer.isActive():
                self._spinner_timer.stop()

        self._pos_anim.finished.connect(on_finished)
        self._pos_anim.start()

    # --- Vector Rendering (QPainter) ---

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        w = float(self.width())
        h = float(self.height())
        r = h / 2.0

        # 1. Background Pill: Dark glass (#18181a) with subtle translucent border
        capsule_path = QPainterPath()
        capsule_path.addRoundedRect(0.5, 0.5, w - 1.0, h - 1.0, r, r)

        bg_brush = QBrush(QColor(24, 24, 26, 245))
        p.fillPath(capsule_path, bg_brush)

        # Border
        border_col = QColor(255, 255, 255, 25) if self._state != "completed" else QColor(35, 165, 89, 80)
        p.setPen(QPen(border_col, 1.0))
        p.drawPath(capsule_path)

        # Subtle top inner highlight
        highlight_path = QPainterPath()
        highlight_path.moveTo(r, 1.5)
        highlight_path.lineTo(w - r, 1.5)
        p.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
        p.drawPath(highlight_path)

        # 2. Vector Status Indicator (Zero emojis)
        icon_cx = float(config.S(20))
        icon_cy = h / 2.0
        icon_r = float(config.S(6.5))

        if self._state == "working":
            # Animated vector spinner arc
            p.save()
            p.translate(icon_cx, icon_cy)
            p.rotate(self._spinner_angle)

            arc_rect = QRectF(-icon_r, -icon_r, icon_r * 2.0, icon_r * 2.0)
            spinner_pen = QPen(QColor("#23a559"), config.S(1.8), Qt.SolidLine, Qt.RoundCap)
            p.setPen(spinner_pen)
            # 270 degrees arc
            p.drawArc(arc_rect, 0, 270 * 16)
            p.restore()

        elif self._state == "completed":
            # Crisp green checkmark
            check_pen = QPen(QColor("#2ecc71"), config.S(1.8), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            p.setPen(check_pen)
            check_path = QPainterPath()
            check_path.moveTo(icon_cx - config.S(4.5), icon_cy)
            check_path.lineTo(icon_cx - config.S(1.5), icon_cy + config.S(3.5))
            check_path.lineTo(icon_cx + config.S(5.0), icon_cy - config.S(3.5))
            p.drawPath(check_path)

        elif self._state == "error":
            # Red warning circle with exclamation
            err_pen = QPen(QColor("#e74c3c"), config.S(1.8), Qt.SolidLine, Qt.RoundCap)
            p.setPen(err_pen)
            p.drawEllipse(QPointF(icon_cx, icon_cy), icon_r, icon_r)
            p.drawLine(QPointF(icon_cx, icon_cy - icon_r + 3), QPointF(icon_cx, icon_cy + 1))
            p.drawPoint(QPointF(icon_cx, icon_cy + icon_r - 2.5))

        # 3. Typography & Text layout
        font_name = config.UI_FONT_NAME
        f_lbl = QFont(font_name, config.FS(9))
        f_bold = QFont(font_name, config.FS(9), QFont.Bold)
        fm_lbl = QFontMetrics(f_lbl)
        fm_bold = QFontMetrics(f_bold)

        cur_x = float(config.S(34))
        text_y = (h + fm_lbl.ascent() - fm_lbl.descent()) / 2.0

        # Title (Status label)
        if self._title_text:
            p.setFont(f_lbl)
            p.setPen(QColor("#a2a2a8"))
            p.drawText(QPointF(cur_x, text_y), self._title_text)
            cur_x += fm_lbl.horizontalAdvance(self._title_text)

        # Bullet separator
        if self._subtitle_text or self._percent_text:
            cur_x += float(config.S(6))
            p.setFont(f_lbl)
            p.setPen(QColor("#55555c"))
            p.drawText(QPointF(cur_x, text_y), "•")
            cur_x += float(config.S(10))

        # Subtitle (Island 3/12)
        if self._subtitle_text:
            p.setFont(f_bold)
            p.setPen(QColor("#ffffff"))
            p.drawText(QPointF(cur_x, text_y), self._subtitle_text)
            cur_x += fm_bold.horizontalAdvance(self._subtitle_text)

        # Percent badge
        if self._percent_text:
            cur_x += float(config.S(6))
            p.setFont(f_lbl)
            p.setPen(QColor("#55555c"))
            p.drawText(QPointF(cur_x, text_y), "•")
            cur_x += float(config.S(10))

            p.setFont(f_bold)
            p.setPen(QColor("#23a559"))
            p.drawText(QPointF(cur_x, text_y), self._percent_text)
