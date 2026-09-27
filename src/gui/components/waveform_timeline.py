#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: waveform_timeline.py
ROLE: GUI Component
DESCRIPTION:
Interactive waveform timeline preview ribbon widget with real-time playhead.
Inspired by DaVinci Resolve / Fairlight interface aesthetics.
Features pre-rendered QPixmap waveform caching for stable 60 FPS scrubbing,
cut range hatching (solid vs hatched), High-DPI scaling, and bidirectional playhead synchronization.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
from PySide6.QtCore import Qt, QRectF, QPointF, QLineF, Signal, QThread
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QPixmap,
    QFont,
    QLinearGradient,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget, QSizePolicy

import config
from engine.waveform import WaveformPeaks, WaveformExtractor
from osdoc import log_info, log_error


# DaVinci Resolve solid timeline clip colors (matching DaVinci Edit / Fairlight page)
RESOLVE_CLIP_COLORS = {
    "normal": QColor("#2f614d"),       # DaVinci Fairlight Green
    "bad": QColor("#8c3450"),          # DaVinci Violet / Pink (Errors / Bad Takes)
    "red": QColor("#8c3450"),
    "violet": QColor("#8c3450"),
    "repeat": QColor("#2b5278"),       # DaVinci Navy / Blue (Retakes)
    "blue": QColor("#2b5278"),
    "navy": QColor("#2b5278"),
    "typo": QColor("#356844"),         # DaVinci Olive (Typo)
    "green": QColor("#356844"),
    "olive": QColor("#356844"),
    "silence_mark": QColor("#8a7154"), # DaVinci Tan (Silence marked)
    "tan": QColor("#8a7154"),
    "silence": QColor("#8a7154"),
    "inaudible": QColor("#5e3518"),    # DaVinci Chocolate (Inaudible)
    "chocolate": QColor("#5e3518"),
}
CUT_VOID_COLOR = QColor("#0e0e0e")


class WaveformWorker(QThread):
    """Background worker thread to extract waveform peaks without freezing the Qt UI."""
    peaks_ready = Signal(object, str)  # WaveformPeaks, audio_path
    error = Signal(str)

    def __init__(
        self,
        audio_path: str,
        points_per_second: int = 400,
        cache_dir: Optional[str] = None,
        ffmpeg_cmd: str = "ffmpeg",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.audio_path = audio_path
        self.points_per_second = points_per_second
        self.cache_dir = cache_dir
        self.ffmpeg_cmd = ffmpeg_cmd

    def run(self):
        try:
            peaks = WaveformExtractor.extract_from_file(
                self.audio_path,
                points_per_second=self.points_per_second,
                cache_dir=self.cache_dir,
                ffmpeg_cmd=self.ffmpeg_cmd,
            )
            if peaks is not None and peaks.num_points > 0:
                self.peaks_ready.emit(peaks, self.audio_path)
            else:
                self.error.emit(f"Failed to generate waveform for {self.audio_path}")
        except Exception as e:
            log_error(f"WaveformWorker error: {e}")
            self.error.emit(str(e))


class WaveformTimelineWidget(QWidget):
    """
    DaVinci Resolve / Fairlight styled timeline waveform preview ribbon.
    Pre-renders the waveform and cut regions to QPixmap for zero-latency 60 FPS playhead movement.
    """
    seek_requested = Signal(float, bool)  # Emits (target_timestamp_s, sync_resolve)
    scrub_started = Signal()
    scrub_finished = Signal()

    def __init__(self, parent: Optional[QWidget] = None, main_window: Optional[QWidget] = None):
        super().__init__(parent)
        self.main_window = main_window

        # State
        self._peaks: Optional[WaveformPeaks] = None
        self._audio_path: Optional[str] = None
        self._clip_name: str = "A1: Timeline Audio"
        self._duration: float = 0.0
        self._playhead_time: float = 0.0
        self._is_scrubbing: bool = False
        self._hover_x: Optional[float] = None
        self._worker: Optional[WaveformWorker] = None

        # Zoom & Viewport Pan State
        self._zoom_level: float = 1.0  # 1.0 = Fit all, up to 120.0 = deep zoom
        self._view_start_time: float = 0.0

        # Cuts & Marking Ranges for Visual Design System (Solid vs Hatched)
        self._words_data: Optional[List[Dict[str, Any]]] = None
        self._cut_ranges: List[Tuple[float, float, str]] = []  # (start_s, end_s, type)
        self._timeline_segments: List[Dict[str, Any]] = []

        # Pre-rendered cache
        self._waveform_pixmap: Optional[QPixmap] = None
        self._needs_pixmap_rebuild: bool = True

        # Horizontal ScrollBar for panning when zoomed in
        from PySide6.QtWidgets import QScrollBar, QPushButton, QHBoxLayout
        self.scrollbar = QScrollBar(Qt.Horizontal, self)
        self.scrollbar.setObjectName("TimelineScrollBar")
        self.scrollbar.setStyleSheet(f"""
            QScrollBar:horizontal {{
                height: {config.S(7)}px;
                background: #141414;
                margin: 0px;
                border: none;
                border-radius: {config.S(3)}px;
            }}
            QScrollBar::handle:horizontal {{
                background: #2f2f2f;
                min-width: {config.S(24)}px;
                border-radius: {config.S(3)}px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: #444444;
            }}
            QScrollBar::handle:horizontal:pressed {{
                background: #2ecc71;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                height: 0px;
                background: transparent;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)
        self.scrollbar.setRange(0, 1000)
        self.scrollbar.setValue(0)
        self.scrollbar.hide()
        self.scrollbar.valueChanged.connect(self._on_scrollbar_changed)

        # Zoom Controls Widget ([-] [Fit] [+]) at top-right corner of track lane
        self.zoom_ctrl_widget = QWidget(self)
        self.zoom_ctrl_widget.setObjectName("ZoomCtrlWidget")
        zoom_layout = QHBoxLayout(self.zoom_ctrl_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(config.S(3))

        btn_style = f"""
            QPushButton {{
                background-color: rgba(22, 22, 22, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: {config.S(3)}px;
                color: #b0b0b0;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(8)}pt;
                font-weight: bold;
                padding: 0px {config.S(5)}px;
            }}
            QPushButton:hover {{
                background-color: rgba(45, 45, 45, 0.95);
                border-color: rgba(46, 204, 113, 0.7);
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: rgba(46, 204, 113, 0.25);
            }}
        """
        self.btn_zoom_out = QPushButton("−", self.zoom_ctrl_widget)
        self.btn_zoom_out.setToolTip(self.main_window.txt("tt_zoom_out", "Zoom Out") if self.main_window else "Zoom Out")
        self.btn_zoom_out.setStyleSheet(btn_style)
        self.btn_zoom_out.clicked.connect(self.zoom_out)
        self.btn_zoom_out.setFixedSize(config.S(22), config.S(18))

        self.btn_zoom_fit = QPushButton("Fit", self.zoom_ctrl_widget)
        self.btn_zoom_fit.setToolTip(self.main_window.txt("tt_zoom_fit", "Fit Timeline") if self.main_window else "Fit Timeline")
        self.btn_zoom_fit.setStyleSheet(btn_style)
        self.btn_zoom_fit.clicked.connect(self.zoom_fit)
        self.btn_zoom_fit.setFixedSize(config.S(28), config.S(18))

        self.btn_zoom_in = QPushButton("+", self.zoom_ctrl_widget)
        self.btn_zoom_in.setToolTip(self.main_window.txt("tt_zoom_in", "Zoom In (or Ctrl + Wheel)") if self.main_window else "Zoom In")
        self.btn_zoom_in.setStyleSheet(btn_style)
        self.btn_zoom_in.clicked.connect(self.zoom_in)
        self.btn_zoom_in.setFixedSize(config.S(22), config.S(18))

        zoom_layout.addWidget(self.btn_zoom_out)
        zoom_layout.addWidget(self.btn_zoom_fit)
        zoom_layout.addWidget(self.btn_zoom_in)

        # Widget styling & sizing
        self.setObjectName("WaveformTimelineWidget")
        self.setMinimumHeight(config.S(105))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def set_waveform_data(
        self,
        peaks: Optional[WaveformPeaks],
        clip_name: Optional[str] = None,
        audio_path: Optional[str] = None,
    ) -> None:
        """Sets pre-computed waveform peak data and refreshes the display."""
        self._peaks = peaks
        if audio_path is not None:
            self._audio_path = audio_path
        if clip_name:
            self._clip_name = clip_name
        if peaks is not None:
            self._duration = peaks.duration
        self._zoom_level = 1.0
        self._view_start_time = 0.0
        self._sync_scrollbar()
        self._needs_pixmap_rebuild = True
        self.update()

    def load_from_audio(
        self,
        audio_path: str,
        clip_name: Optional[str] = None,
        duration: Optional[float] = None,
        track_name: Optional[str] = None,
    ) -> None:
        """
        Loads waveform from audio file in background without blocking the UI.
        If the file has already been loaded, avoids duplicate processing.
        """
        if not audio_path or not os.path.isfile(audio_path):
            return

        effective_name = clip_name or track_name
        if effective_name:
            self._clip_name = effective_name
        if duration and duration > 0:
            self._duration = duration

        if self._audio_path == audio_path and self._peaks is not None and self._peaks.num_points > 0:
            return  # Already loaded

        self._audio_path = audio_path

        # Determine temp cache folder
        cache_dir = None
        if self.main_window and hasattr(self.main_window, "engine") and hasattr(self.main_window.engine, "os_doc"):
            cache_dir = self.main_window.engine.os_doc.get_temp_folder()

        ffmpeg_cmd = "ffmpeg"
        if self.main_window and hasattr(self.main_window, "engine"):
            ffmpeg_cmd = getattr(self.main_window.engine, "ffmpeg_cmd", "ffmpeg")

        # Terminate any previous background worker
        if self._worker is not None and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(100)

        self._worker = WaveformWorker(
            audio_path=audio_path,
            points_per_second=400,
            cache_dir=cache_dir,
            ffmpeg_cmd=ffmpeg_cmd,
            parent=self,
        )
        self._worker.peaks_ready.connect(self._on_peaks_ready)
        self._worker.error.connect(self._on_peaks_error)
        self._worker.start()

    def set_words_data(self, words_data: Optional[List[Dict[str, Any]]]) -> None:
        """
        Passes transcript words to calculate visual cut ranges (Solid vs Hatched).
        """
        self._words_data = words_data or []
        self._recalculate_cut_ranges()
        self._needs_pixmap_rebuild = True
        self.update()

    def _recalculate_cut_ranges(self) -> None:
        """Extracts solid clip segments and cut ranges directly from engine calculation."""
        self._cut_ranges.clear()
        self._timeline_segments = []

        total_dur = self._duration if self._duration > 0 else 0.0

        if not self._words_data or not self.main_window or not hasattr(self.main_window, "engine"):
            if total_dur > 0:
                self._timeline_segments = [{
                    "start_s": 0.0,
                    "end_s": total_dur,
                    "type": "normal",
                    "is_cut": False,
                    "color": RESOLVE_CLIP_COLORS["normal"],
                }]
            return

        prefs = self.main_window.engine.load_preferences() or {}
        if hasattr(self.main_window, 'tgl_silence_cut'):
            prefs['silence_cut'] = self.main_window.tgl_silence_cut.isChecked()
        if hasattr(self.main_window, 'tgl_silence_mark'):
            prefs['silence_mark'] = self.main_window.tgl_silence_mark.isChecked()
        if hasattr(self.main_window, 'tgl_show_inaudible'):
            prefs['show_inaudible'] = self.main_window.tgl_show_inaudible.isChecked()
        if hasattr(self.main_window, 'tgl_mark_inaudible'):
            prefs['mark_inaudible'] = self.main_window.tgl_mark_inaudible.isChecked()
        if hasattr(self.main_window, 'tgl_show_typos'):
            prefs['show_typos'] = self.main_window.tgl_show_typos.isChecked()
        if hasattr(self.main_window, 'color_cut_buttons'):
            auto_cut = [c_name for c_name, btn in self.main_window.color_cut_buttons.items() if btn.isChecked()]
            prefs['auto_cut_colors'] = auto_cut

        fps = 60.0
        if hasattr(self.main_window.engine, 'resolve_handler') and self.main_window.engine.resolve_handler:
            fps = getattr(self.main_window.engine.resolve_handler, 'fps', 60.0) or 60.0

        surviving_ops, cut_ops = self.main_window.engine.calculate_timeline_structure_with_cuts(
            self._words_data, fps, prefs
        )

        raw_segments = []
        for op in surviving_ops:
            s_s = max(0.0, float(op.get('start_s', 0.0)))
            e_s = float(op.get('end_s', 0.0))
            if total_dur > 0:
                e_s = min(total_dur, e_s)
            if e_s <= s_s:
                continue
            op_type = (op.get('type') or 'normal').lower()
            col = RESOLVE_CLIP_COLORS.get(op_type, RESOLVE_CLIP_COLORS["normal"])
            raw_segments.append({
                "start_s": s_s,
                "end_s": e_s,
                "type": op_type,
                "is_cut": False,
                "color": col,
            })
            self._cut_ranges.append((s_s, e_s, f"{op_type}_solid"))

        for op in cut_ops:
            s_s = max(0.0, float(op.get('start_s', 0.0)))
            e_s = float(op.get('end_s', 0.0))
            if total_dur > 0:
                e_s = min(total_dur, e_s)
            if e_s <= s_s:
                continue
            cut_type = str(op.get('cut_type', 'silence_cut')).lower()
            raw_segments.append({
                "start_s": s_s,
                "end_s": e_s,
                "type": cut_type,
                "is_cut": True,
                "color": CUT_VOID_COLOR,
            })
            self._cut_ranges.append((s_s, e_s, cut_type))

        raw_segments.sort(key=lambda s: s["start_s"])

        # Fill any gaps with 'normal' clips so the entire timeline has a solid continuous base
        cur_pos = 0.0
        filled = []
        for seg in raw_segments:
            if seg["start_s"] > cur_pos + 0.001:
                filled.append({
                    "start_s": cur_pos,
                    "end_s": seg["start_s"],
                    "type": "normal",
                    "is_cut": False,
                    "color": RESOLVE_CLIP_COLORS["normal"],
                })
            filled.append(seg)
            cur_pos = max(cur_pos, seg["end_s"])

        if total_dur > cur_pos + 0.001:
            filled.append({
                "start_s": cur_pos,
                "end_s": total_dur,
                "type": "normal",
                "is_cut": False,
                "color": RESOLVE_CLIP_COLORS["normal"],
            })

        self._timeline_segments = filled

    def set_playhead_time(self, seconds: float) -> None:
        """
        Updates the playhead position in seconds and requests an ultra-fast repaint.
        Called on playback tick (60 FPS) without rebuilding the waveform pixmap!
        """
        seconds = max(0.0, seconds)
        if self._duration > 0:
            seconds = min(self._duration, seconds)

        if abs(self._playhead_time - seconds) > 0.001:
            self._playhead_time = seconds

            # Auto-scroll if keep centered is checked or playhead leaves viewport during playback
            if self._duration > 0 and self._zoom_level > 1.01:
                vis_dur = self.visible_duration()
                t0 = self._view_start_time
                t1 = t0 + vis_dur

                keep_centered = False
                if self.main_window and hasattr(self.main_window, 'audio_preview') and self.main_window.audio_preview:
                    keep_centered = getattr(self.main_window.audio_preview.tgl_centered, 'isChecked', lambda: False)()

                if keep_centered:
                    if seconds < t0 + vis_dur * 0.2 or seconds > t0 + vis_dur * 0.8:
                        self.scroll_to_time(seconds - vis_dur * 0.5)
                else:
                    if seconds > t1 or seconds < t0:
                        self.scroll_to_time(seconds - vis_dur * 0.1)

            self.update()

    def set_clip_info(self, clip_name: str, duration: Optional[float] = None) -> None:
        """Updates clip label or duration badge."""
        self._clip_name = clip_name
        if duration is not None and duration > 0:
            self._duration = duration
        self._needs_pixmap_rebuild = True
        self.update()

    # Alias for backward compatibility
    set_track_info = set_clip_info

    def clear(self) -> None:
        """Resets waveform data and playhead state."""
        self._peaks = None
        self._audio_path = None
        self._duration = 0.0
        self._playhead_time = 0.0
        self._words_data = None
        self._cut_ranges.clear()
        self._zoom_level = 1.0
        self._view_start_time = 0.0
        self._sync_scrollbar()
        self._needs_pixmap_rebuild = True
        self.update()

    # -------------------------------------------------------------------------
    # Zoom & Viewport Pan API
    # -------------------------------------------------------------------------

    def visible_duration(self) -> float:
        """Returns the time duration currently visible in the timeline viewport."""
        if self._duration <= 0.0:
            return 1.0
        return max(0.2, self._duration / max(1.0, self._zoom_level))

    def set_zoom(self, zoom: float, center_time: Optional[float] = None) -> None:
        """
        Sets zoom level and maintains relative cursor position in viewport.
        Allows zooming in so deeply that individual peaks/nodes can be seen (down to 0.2s visible).
        """
        if self._duration <= 0:
            self._zoom_level = 1.0
            self._view_start_time = 0.0
            self._sync_scrollbar()
            self._needs_pixmap_rebuild = True
            self.update()
            return

        max_zoom = max(1.0, self._duration / 0.2)
        new_zoom = max(1.0, min(max_zoom, zoom))

        old_vis_dur = self.visible_duration()
        new_vis_dur = max(0.2, self._duration / new_zoom)

        if center_time is None:
            center_time = self._playhead_time

        ratio = (center_time - self._view_start_time) / max(0.001, old_vis_dur)
        ratio = max(0.0, min(1.0, ratio))
        self._view_start_time = center_time - ratio * new_vis_dur

        max_start = max(0.0, self._duration - new_vis_dur)
        self._view_start_time = max(0.0, min(max_start, self._view_start_time))
        self._zoom_level = new_zoom

        self._sync_scrollbar()
        self._needs_pixmap_rebuild = True
        self.update()

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom_level * 1.5, center_time=self._playhead_time)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom_level / 1.5, center_time=self._playhead_time)

    def zoom_fit(self) -> None:
        self.set_zoom(1.0, center_time=0.0)

    def scroll_to_time(self, t: float) -> None:
        vis_dur = self.visible_duration()
        max_start = max(0.0, self._duration - vis_dur)
        self._view_start_time = max(0.0, min(max_start, t))
        self._sync_scrollbar()
        self._needs_pixmap_rebuild = True
        self.update()

    def _sync_scrollbar(self) -> None:
        if not hasattr(self, 'scrollbar'):
            return
        vis_dur = self.visible_duration()
        max_start = max(0.0, self._duration - vis_dur)
        if max_start <= 0.001 or self._zoom_level <= 1.01:
            self.scrollbar.setEnabled(False)
            self.scrollbar.blockSignals(True)
            self.scrollbar.setPageStep(1000)
            self.scrollbar.setValue(0)
            self.scrollbar.blockSignals(False)
            self.scrollbar.hide()
        else:
            self.scrollbar.setEnabled(True)
            self.scrollbar.show()
            page_ratio = min(1.0, vis_dur / max(0.001, self._duration))
            page_step = int(page_ratio * 1000)
            val = int((self._view_start_time / max_start) * (1000 - page_step))
            self.scrollbar.blockSignals(True)
            self.scrollbar.setPageStep(page_step)
            self.scrollbar.setValue(max(0, min(1000 - page_step, val)))
            self.scrollbar.blockSignals(False)

    def _on_scrollbar_changed(self, value: int) -> None:
        vis_dur = self.visible_duration()
        max_start = max(0.0, self._duration - vis_dur)
        if max_start > 0:
            max_val = max(1, 1000 - self.scrollbar.pageStep())
            pct = max(0.0, min(1.0, value / float(max_val)))
            self._view_start_time = pct * max_start
            self._needs_pixmap_rebuild = True
            self.update()

    # -------------------------------------------------------------------------
    # Worker callbacks
    # -------------------------------------------------------------------------

    def _on_peaks_ready(self, peaks: WaveformPeaks, audio_path: str) -> None:
        if self._audio_path == audio_path:
            self._peaks = peaks
            self._duration = peaks.duration
            self._recalculate_cut_ranges()
            self._zoom_level = 1.0
            self._view_start_time = 0.0
            self._sync_scrollbar()
            self._needs_pixmap_rebuild = True
            self.update()

    def _on_peaks_error(self, err_msg: str) -> None:
        log_info(f"WaveformTimelineWidget: peak extraction notice: {err_msg}")
        self._needs_pixmap_rebuild = True
        self.update()

    # -------------------------------------------------------------------------
    # Pre-rendered Waveform Cache (QPixmap)
    # -------------------------------------------------------------------------

    def _get_clip_rect(self) -> QRectF:
        """Calculates the Fairlight clip ribbon rectangle inside the widget with breathing room."""
        m_x = float(config.S(8))
        m_y_top = float(config.S(22))   # Top space for breathing room + zoom controls
        m_y_bot = float(config.S(16))   # Bottom space for breathing room + scrollbar
        sb_h = float(config.S(7)) if (hasattr(self, 'scrollbar') and self.scrollbar.isVisible()) else 0.0

        w = max(10.0, self.width() - 2 * m_x)
        h = max(10.0, self.height() - m_y_top - m_y_bot - sb_h)
        return QRectF(m_x, m_y_top, w, h)

    def _rebuild_waveform_pixmap(self) -> None:
        """
        Pre-renders the Fairlight clip background, waveform geometry, cut hatching,
        and bottom clip badge into a QPixmap.
        Executes only on resize or data changes, keeping paintEvent < 0.2ms!
        """
        w = max(1, self.width())
        h = max(1, self.height())
        dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0

        pixmap = QPixmap(int(w * dpr), int(h * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        clip_rect = self._get_clip_rect()
        rx = clip_rect.x()
        ry = clip_rect.y()
        rw = clip_rect.width()
        rh = clip_rect.height()
        radius = float(config.S(6))

        # 1. Dark container background
        bg_container = QRectF(0, 0, w, h)
        painter.fillRect(bg_container, QColor("#141414"))

        # 2. Fairlight Audio Clip Ribbon
        clip_path = QPainterPath()
        clip_path.addRoundedRect(clip_rect, radius, radius)

        painter.save()
        painter.setClipPath(clip_path)

        vis_dur = self.visible_duration()
        t_start = self._view_start_time
        t_end = t_start + vis_dur

        # 3. Draw Solid Timeline Segments (DaVinci Resolve Style Solid Colors)
        segments = self._timeline_segments
        if not segments:
            # Default normal Fairlight clip
            painter.fillRect(clip_rect, RESOLVE_CLIP_COLORS["normal"])
        else:
            for seg in segments:
                if seg["end_s"] <= t_start or seg["start_s"] >= t_end:
                    continue
                s0 = max(t_start, seg["start_s"])
                s1 = min(t_end, seg["end_s"])
                x0 = rx + ((s0 - t_start) / vis_dur) * rw
                x1 = rx + ((s1 - t_start) / vis_dur) * rw
                seg_w = max(1.0, x1 - x0)
                seg_rect = QRectF(x0, ry, seg_w, rh)

                if seg["is_cut"]:
                    painter.fillRect(seg_rect, CUT_VOID_COLOR)
                    painter.fillRect(seg_rect, QBrush(QColor(22, 22, 22), Qt.BDiagPattern))
                else:
                    painter.fillRect(seg_rect, seg["color"])
                    # Subtle top highlight
                    painter.setPen(QPen(seg["color"].lighter(112), 1.0))
                    painter.drawLine(QPointF(x0, ry), QPointF(x1, ry))
                    # Subtle bottom shadow
                    painter.setPen(QPen(seg["color"].darker(118), 1.0))
                    painter.drawLine(QPointF(x0, ry + rh), QPointF(x1, ry + rh))

                # Vertical divider seam at cut point
                painter.setPen(QPen(QColor(16, 16, 16), 1.0))
                painter.drawLine(QPointF(x0, ry), QPointF(x0, ry + rh))
                painter.drawLine(QPointF(x1, ry), QPointF(x1, ry + rh))

        # 4. Subtle horizontal audio midline and dB guide lines
        mid_y = ry + rh / 2.0
        half_h = (rh / 2.0) * 0.88

        # 0dB midline (subtle dark line matching DaVinci Fairlight Screenshot 3)
        midline_pen = QPen(QColor(15, 35, 25, 120), 1.0, Qt.SolidLine)
        painter.setPen(midline_pen)
        painter.drawLine(QPointF(rx, mid_y), QPointF(rx + rw, mid_y))

        # 5. Draw Waveform Silhouette (1:1 with DaVinci Resolve Screenshot 3)
        if self._peaks is not None and self._peaks.num_points > 0 and self._duration > 0:
            num_cols = max(1, int(rw))

            # Smooth power scaling preserving quiet speech while preventing clipping
            def scale_amp(v: float) -> float:
                if abs(v) < 1e-4:
                    return 0.0
                return float(np.sign(v) * (abs(v) ** 0.62))

            top_pts = []
            bot_pts = []

            for col in range(num_cols):
                t0 = t_start + (col / float(num_cols)) * vis_dur
                t1 = t_start + ((col + 1) / float(num_cols)) * vis_dur

                p_min, p_max, _, _ = self._peaks.get_visible_peaks(t0, t1)
                if len(p_max) > 0:
                    v_max = float(np.max(p_max))
                    v_min = float(np.min(p_min))
                else:
                    v_max = 0.0
                    v_min = 0.0

                if abs(v_max) < 0.002 and abs(v_min) < 0.002:
                    s_max = 0.003
                    s_min = -0.003
                else:
                    s_max = scale_amp(v_max)
                    s_min = scale_amp(v_min)

                x_val = rx + col + 0.5
                y_top = mid_y - (s_max * half_h)
                y_bot = mid_y - (s_min * half_h)

                if y_bot - y_top < 1.0:
                    y_top = mid_y - 0.5
                    y_bot = mid_y + 0.5

                top_pts.append(QPointF(x_val, y_top))
                bot_pts.append(QPointF(x_val, y_bot))

            if top_pts:
                wf_poly = QPolygonF()
                for pt in top_pts:
                    wf_poly.append(pt)
                for pt in reversed(bot_pts):
                    wf_poly.append(pt)

                # Solid filled continuous silhouette in crisp off-white / pale mint (#f0fcf6)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor("#f0fcf6")))
                painter.drawPolygon(wf_poly)

                # Clean razor center trace across silence/quiet portions
                painter.setPen(QPen(QColor("#f0fcf6"), 1.0))
                painter.drawLine(QPointF(rx, mid_y), QPointF(rx + rw, mid_y))

            # Mask cut voids & diagonal hatching over the waveform in cut segments
            for seg in segments:
                if not seg["is_cut"]:
                    continue
                if seg["end_s"] <= t_start or seg["start_s"] >= t_end:
                    continue
                s0 = max(t_start, seg["start_s"])
                s1 = min(t_end, seg["end_s"])
                x0 = rx + ((s0 - t_start) / vis_dur) * rw
                x1 = rx + ((s1 - t_start) / vis_dur) * rw
                seg_w = max(1.0, x1 - x0)
                seg_rect = QRectF(x0, ry, seg_w, rh)

                painter.fillRect(seg_rect, QColor(14, 14, 14, 235))
                painter.fillRect(seg_rect, QBrush(QColor(0, 0, 0, 210), Qt.BDiagPattern))
                painter.setPen(QPen(QColor(10, 10, 10, 255), 1.0))
                painter.drawLine(QPointF(x0, ry), QPointF(x0, ry + rh))
                painter.drawLine(QPointF(x1, ry), QPointF(x1, ry + rh))

            painter.restore()
        else:
            # Subtle waiting text
            painter.setPen(QColor("#4e735b"))
            placeholder_font = QFont(config.UI_FONT_NAME, config.FS(9))
            placeholder_font.setItalic(True)
            painter.setFont(placeholder_font)
            txt = self.main_window.txt("lbl_timeline_ready", "A1: Ready for timeline audio") if self.main_window and hasattr(self.main_window, "txt") else "A1: Ready for timeline audio"
            painter.drawText(clip_rect, Qt.AlignCenter, txt)
            painter.restore()

        # Ribbon outer border
        border_pen = QPen(QColor("#1b3b2c"), 1.0)
        painter.setPen(border_pen)
        painter.drawPath(clip_path)

        # 6. Clip Name Label Badge (at bottom-left corner of the clip, matching Screenshot 1!)
        badge_font = QFont(config.UI_FONT_NAME, config.FS(8))
        badge_font.setBold(False)
        painter.setFont(badge_font)

        clip_label = self._clip_name
        fm = painter.fontMetrics()
        txt_w = fm.horizontalAdvance(clip_label)
        txt_h = fm.height()

        badge_pad_x = float(config.S(6))
        badge_pad_y = float(config.S(2))
        badge_rect = QRectF(
            rx + float(config.S(8)),
            ry + rh - float(config.S(6)) - txt_h - 2 * badge_pad_y,
            txt_w + 2 * badge_pad_x,
            txt_h + 2 * badge_pad_y,
        )

        badge_path = QPainterPath()
        badge_path.addRoundedRect(badge_rect, config.S(3), config.S(3))
        painter.fillPath(badge_path, QColor(10, 22, 15, 210))
        painter.setPen(QPen(QColor("#245437"), 1.0))
        painter.drawPath(badge_path)

        painter.setPen(QColor("#c8e6d2"))
        painter.drawText(badge_rect, Qt.AlignCenter, clip_label)

        painter.end()

        self._waveform_pixmap = pixmap
        self._needs_pixmap_rebuild = False

    # -------------------------------------------------------------------------
    # Qt Event Handlers
    # -------------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        sb_h = config.S(7)
        m_x = config.S(8)
        if hasattr(self, 'scrollbar'):
            self.scrollbar.setGeometry(
                m_x,
                self.height() - sb_h - config.S(3),
                max(10, self.width() - 2 * m_x),
                sb_h,
            )
            self._sync_scrollbar()
        if hasattr(self, 'zoom_ctrl_widget'):
            ctrl_w = config.S(80)
            ctrl_h = config.S(18)
            self.zoom_ctrl_widget.setGeometry(
                self.width() - ctrl_w - config.S(12),
                config.S(2),
                ctrl_w,
                ctrl_h,
            )
        self._needs_pixmap_rebuild = True

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if abs(delta) < 1:
            delta = event.angleDelta().x()
        if delta == 0 or self._duration <= 0:
            return

        clip_rect = self._get_clip_rect()
        pos_x = event.position().x()

        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            # Zoom centered at cursor position
            rx = clip_rect.x()
            rw = clip_rect.width()
            vis_dur = self.visible_duration()
            cursor_ratio = max(0.0, min(1.0, (pos_x - rx) / max(1.0, rw)))
            t_cursor = self._view_start_time + cursor_ratio * vis_dur

            factor = 1.3 if delta > 0 else (1.0 / 1.3)
            self.set_zoom(self._zoom_level * factor, center_time=t_cursor)
        else:
            # Horizontal Pan
            vis_dur = self.visible_duration()
            pan_s = (vis_dur * 0.15) * (-1 if delta > 0 else 1)
            self.scroll_to_time(self._view_start_time + pan_s)

    def paintEvent(self, event) -> None:
        if self._needs_pixmap_rebuild or self._waveform_pixmap is None:
            self._rebuild_waveform_pixmap()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Blit pre-rendered waveform pixmap (ultra-fast, ~0.05ms)
        if self._waveform_pixmap is not None:
            painter.drawPixmap(0, 0, self._waveform_pixmap)

        clip_rect = self._get_clip_rect()
        rx = clip_rect.x()
        ry = clip_rect.y()
        rw = clip_rect.width()
        rh = clip_rect.height()

        # 2. Draw Red Playhead (matching Screenshot 1: vertical red line + top red circular pin marker)
        if self._duration > 0:
            vis_dur = self.visible_duration()
            t_start = self._view_start_time
            t_end = t_start + vis_dur

            if t_start <= self._playhead_time <= t_end:
                pct = (self._playhead_time - t_start) / vis_dur
                playhead_x = rx + (pct * rw)

                # Vertical red line through the clip
                line_pen = QPen(QColor("#ff3b30"), config.S(1.8))
                painter.setPen(line_pen)
                painter.drawLine(QPointF(playhead_x, ry), QPointF(playhead_x, ry + rh))

                # Top red circular marker (radius ~4.5px, matching Screenshot 1!)
                marker_radius = float(config.S(4.5))
                painter.setPen(QPen(QColor("#c0392b"), 1.0))
                painter.setBrush(QBrush(QColor("#ff3b30")))
                painter.drawEllipse(QPointF(playhead_x, ry + marker_radius), marker_radius, marker_radius)

            # Optional scrubbing time tooltip
            if self._is_scrubbing or self._hover_x is not None:
                hover_t = self._playhead_time if self._is_scrubbing else (
                    max(0.0, min(self._duration, t_start + ((self._hover_x - rx) / rw) * vis_dur))
                    if self._hover_x is not None else self._playhead_time
                )
                hm, hs = divmod(int(hover_t), 60)
                hms = int((hover_t - int(hover_t)) * 100)
                tc_str = f"{hm:02d}:{hs:02d}.{hms:02d}"

                tc_font = QFont("JetBrains Mono", config.FS(7.5))
                if not tc_font.exactMatch():
                    tc_font = QFont("Consolas", config.FS(7.5))
                painter.setFont(tc_font)
                fm = painter.fontMetrics()
                box_w = fm.horizontalAdvance(tc_str) + config.S(8)
                box_h = fm.height() + config.S(2)

                tip_pct = (hover_t - t_start) / vis_dur
                tip_center_x = rx + (tip_pct * rw)
                tip_x = max(rx, min(rx + rw - box_w, tip_center_x - box_w / 2.0))
                tip_y = max(ry + 2, ry + rh - box_h - float(config.S(4)))
                tip_rect = QRectF(tip_x, tip_y, box_w, box_h)

                tip_path = QPainterPath()
                tip_path.addRoundedRect(tip_rect, config.S(3), config.S(3))
                painter.fillPath(tip_path, QColor(0, 0, 0, 210))
                painter.setPen(QPen(QColor("#ff3b30"), 1.0))
                painter.drawPath(tip_path)

                painter.setPen(QColor("#ffffff"))
                painter.drawText(tip_rect, Qt.AlignCenter, tc_str)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            clip_rect = self._get_clip_rect()
            if clip_rect.contains(event.position()) and self._duration > 0:
                self._is_scrubbing = True
                self.scrub_started.emit()
                is_jump = bool(event.modifiers() & (Qt.ControlModifier | Qt.AltModifier))
                self._update_from_mouse_x(event.position().x(), sync_resolve=is_jump)

    def mouseMoveEvent(self, event) -> None:
        clip_rect = self._get_clip_rect()
        if clip_rect.contains(event.position()):
            self._hover_x = event.position().x()
            if self._is_scrubbing and self._duration > 0:
                self._update_from_mouse_x(event.position().x(), sync_resolve=False)
            else:
                self.update()
        else:
            if self._hover_x is not None:
                self._hover_x = None
                self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._is_scrubbing:
            self._is_scrubbing = False
            self.scrub_finished.emit()
            clip_rect = self._get_clip_rect()
            if self._duration > 0:
                is_jump = bool(event.modifiers() & (Qt.ControlModifier | Qt.AltModifier))
                self._update_from_mouse_x(event.position().x(), sync_resolve=is_jump)
            self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        if self._hover_x is not None:
            self._hover_x = None
            self.update()

    def _update_from_mouse_x(self, mouse_x: float, sync_resolve: bool = False) -> None:
        clip_rect = self._get_clip_rect()
        rx = clip_rect.x()
        rw = clip_rect.width()
        if rw <= 0 or self._duration <= 0:
            return

        vis_dur = self.visible_duration()
        pct = max(0.0, min(1.0, (mouse_x - rx) / rw))
        target_t = self._view_start_time + (pct * vis_dur)
        target_t = max(0.0, min(self._duration, target_t))
        self._playhead_time = target_t
        self.update()

        # Local immediate seek (60 FPS playback / video frame update)
        self.seek_requested.emit(target_t, sync_resolve)

        # DaVinci Resolve seek: ONLY when explicit shortcut (Ctrl + click) was triggered!
        if sync_resolve and self.main_window and hasattr(self.main_window, "_jump_playhead"):
            self.main_window._jump_playhead(target_t)

