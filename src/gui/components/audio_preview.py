#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: audio_preview.py
ROLE: GUI Component
DESCRIPTION:
Unified Media Preview & Playback Dock for BadWords v4.0.
Integrates:
- Control Bar (Timecode, Playhead centering, Playback controls, Speed, Volume, Collapse tab)
- Video Preview Widget (16:9 QVideoWidget for talking-head footage)
- Timeline Preview Widget (Fairlight green clip ribbon with waveform, hatched cuts, and playhead)
- Full modularity: toggle video preview, toggle timeline preview, compact audio-only bar, or collapse all.
"""

from __future__ import annotations

import os
import time
import subprocess
import sys
import re
import threading
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QTimer, QUrl, QRectF, QPointF, Signal, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPolygonF,
    QPixmap,
    QFont,
)
from PySide6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

import config
from gui.widgets.buttons import ToggleSwitch, AnimatedPlayerButton, AudioToggleTab, SpeedDropdown
from gui.widgets.sliders import JumpSlider
from gui.components.video_preview import VideoPreviewWidget
from gui.components.waveform_timeline import WaveformTimelineWidget
from osdoc import log_info, log_error


class PreviewToggleBtn(QPushButton):
    """Clean minimalist toggle icon button for Timeline and Video preview modes."""
    def __init__(self, mode: str = "timeline", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode = mode
        self.setCheckable(True)
        self.setChecked(True)
        self.setFixedSize(config.S(24), config.S(24))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: {config.S(4)}px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
        """)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor("#2ecc71") if self.isChecked() else QColor("#707070")
        w = float(self.width())
        h = float(self.height())

        if self.mode == "timeline":
            # Waveform bars icon
            painter.setPen(QPen(color, float(config.S(1.8)), Qt.SolidLine, Qt.RoundCap))
            xs = [w * 0.26, w * 0.42, w * 0.58, w * 0.74]
            heights = [h * 0.30, h * 0.60, h * 0.42, h * 0.65]
            for x, bar_h in zip(xs, heights):
                painter.drawLine(QPointF(x, (h - bar_h) / 2.0), QPointF(x, (h + bar_h) / 2.0))
        elif self.mode == "video":
            # Filmstrip / 16:9 frame with center play triangle
            painter.setPen(QPen(color, float(config.S(1.4)), Qt.SolidLine, Qt.RoundCap))
            rect = QRectF(w * 0.18, h * 0.25, w * 0.64, h * 0.50)
            painter.drawRoundedRect(rect, config.S(2), config.S(2))
            # Center play triangle
            tri = QPolygonF([
                QPointF(w * 0.43, h * 0.36),
                QPointF(w * 0.43, h * 0.64),
                QPointF(w * 0.63, h * 0.50),
            ])
            painter.setBrush(QBrush(color))
            painter.drawPolygon(tri)


class AudioPreviewWidget(QFrame):
    """
    Unified bottom media dock in BadWords v4.0.
    Houses the control bar, video monitor, and waveform preview ribbon.
    """
    def __init__(self, parent_widget: Optional[QWidget], main_window: Optional[QWidget]):
        super().__init__(parent_widget)
        self.main_window = main_window
        self.is_collapsed = False
        self._anim = None

        # Modularity flags with preference persistence
        prefs = {}
        if self.main_window and hasattr(self.main_window, "engine"):
            prefs = self.main_window.engine.load_preferences() or {}
        self.show_timeline = bool(prefs.get("show_timeline_preview", True))
        self.show_video = bool(prefs.get("show_video_preview", True))

        if os.name == "posix":
            os.environ["PULSE_PROP_application.name"] = "BadWordsApp"
            os.environ["PULSE_PROP_media.role"] = "production"

        if self.main_window and hasattr(self.main_window, "scroll_area"):
            vbar = self.main_window.scroll_area.verticalScrollBar()
            vbar.actionTriggered.connect(self._on_user_scroll)

        self.setObjectName("AudioPreview")
        self.setStyleSheet(f"""
            QFrame#AudioPreview {{
                background: transparent;
                border: none;
            }}
            QWidget#AudioContent {{
                background: transparent;
                border: none;
            }}
            QWidget#TabContainer {{
                background: transparent;
                border: none;
            }}
            QWidget#AudioControls {{
                background-color: #191919;
            }}
            QWidget#MediaContainer {{
                background-color: #191919;
            }}
            QWidget {{
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-weight: 600;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
                padding: {config.S(6)}px {config.S(10)}px;
                border-radius: {config.S(6)}px;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.06);
            }}
            QPushButton#PlayBtn {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                border-radius: {config.S(16)}px;
                font-size: {config.FS(11)}pt;
            }}
            QPushButton#PlayBtn:hover {{
                background-color: {config.BTN_ACTIVE};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(9.5)}pt;
            }}
            QComboBox {{
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: {config.S(6)}px;
                color: #d0d0d0;
                padding: {config.S(4)}px {config.S(10)}px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(9)}pt;
            }}
            QComboBox:hover {{
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QSlider::groove:horizontal {{
                height: {config.S(4)}px;
                background: rgba(255, 255, 255, 0.10);
                border-radius: {config.S(2)}px;
            }}
            QSlider::handle:horizontal {{
                background: #d0d0d0;
                width: {config.S(10)}px;
                margin: -{config.S(3)}px 0px;
                border-radius: {config.S(5)}px;
                border: 0px solid transparent;
            }}
            QSlider::handle:horizontal:hover {{
                background: #ffffff;
            }}
            QWidget#SeekBarContainer {{
                background: transparent;
                border: none;
            }}
            QSlider#SeekSlider {{
                margin: 0px;
                padding: 0px;
                border: none;
                background: transparent;
            }}
            QSlider#SeekSlider::groove:horizontal {{
                height: {config.S(3)}px;
                background: rgba(255, 255, 255, 0.10);
                border-radius: 0px;
                margin: 0px;
            }}
            QSlider#SeekSlider::sub-page:horizontal {{
                background: #1ed760;
                border-radius: 0px;
                margin: 0px;
            }}
            QSlider#SeekSlider::handle:horizontal {{
                background: #ffffff;
                width: {config.S(10)}px;
                height: {config.S(10)}px;
                margin: -{config.S(3)}px 0px;
                border-radius: {config.S(5)}px;
                border: 0px solid transparent;
            }}
            QSlider#SeekSlider::handle:horizontal:hover {{
                background: #ffffff;
                border: 1px solid #1ed760;
            }}
            QLabel#TimecodeLabel {{
                font-family: 'JetBrains Mono', 'Consolas', 'Menlo', monospace;
                font-size: {config.FS(9.5)}pt;
                font-weight: bold;
                color: #ffffff;
                letter-spacing: 0.5px;
            }}
            QLabel#StatusLabel {{
                color: #666666;
                font-style: italic;
                font-size: {config.FS(9)}pt;
            }}
        """)

        dock_layout = QVBoxLayout(self)
        dock_layout.setContentsMargins(0, 0, 0, 0)
        dock_layout.setSpacing(0)

        # 1. Main Collapsible Content Container
        self.content_widget = QWidget()
        self.content_widget.setObjectName("AudioContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        dock_layout.addWidget(self.content_widget)

        # 2. Floating Toggle Tab (wysepka)
        self.toggle_tab = AudioToggleTab(parent_widget)
        self.toggle_tab.setToolTip(self.main_window.txt("tooltip_toggle_audio_preview") if self.main_window else "Toggle Preview")
        self.toggle_tab.clicked.connect(self.toggle_collapse)

        if parent_widget:
            parent_widget.installEventFilter(self)

        # 3. Status Label (for fetching / missing audio)
        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("StatusLabel")
        self.lbl_status.setFixedHeight(config.S(60))
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setOpenExternalLinks(False)
        self.lbl_status.setTextFormat(Qt.RichText)
        self.lbl_status.linkActivated.connect(self._on_fetch_missing_audio)
        self.lbl_status.hide()
        self.content_layout.addWidget(self.lbl_status)

        # 4. Top Seek Progress Slider (spans between left and right side panels)
        self.seek_bar_container = QWidget()
        self.seek_bar_container.setObjectName("SeekBarContainer")
        self.seek_bar_container.setFixedHeight(config.S(6))
        seek_h_layout = QHBoxLayout(self.seek_bar_container)
        seek_h_layout.setContentsMargins(0, 0, 0, 0)
        seek_h_layout.setSpacing(0)

        self.seek_spacer_left = QWidget()
        self.seek_spacer_left.setStyleSheet("background: transparent;")
        self.seek_spacer_right = QWidget()
        self.seek_spacer_right.setStyleSheet("background: transparent;")

        self.slider_seek = JumpSlider(Qt.Horizontal)
        self.slider_seek.setObjectName("SeekSlider")
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.setFixedHeight(config.S(6))
        self.slider_seek.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._seek_dragging = False
        self.slider_seek.sliderPressed.connect(self._on_seek_pressed)
        self.slider_seek.sliderReleased.connect(self._on_seek_released)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)

        seek_h_layout.addWidget(self.seek_spacer_left)
        seek_h_layout.addWidget(self.slider_seek, 1)
        seek_h_layout.addWidget(self.seek_spacer_right)

        self.content_layout.addWidget(self.seek_bar_container)

        # 5. Controls Row (Timecode | Buttons | Playback | Volume)
        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("AudioControls")
        self.controls_widget.setFixedHeight(config.S(48))
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(config.S(16), 0, config.S(16), 0)
        controls_layout.setSpacing(config.S(16))

        # --- Left Section: Timecode + Centered + Modularity Toggles ---
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(config.S(10))

        self.lbl_timecode = QLabel("01:00:00:00")
        self.lbl_timecode.setObjectName("TimecodeLabel")
        self.lbl_timecode.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        left_layout.addWidget(self.lbl_timecode)
        left_layout.addSpacing(config.S(4))

        self.tgl_centered = ToggleSwitch(parent=self)
        self.tgl_centered.toggled.connect(self._on_tgl_centered_changed)
        left_layout.addWidget(self.tgl_centered)

        self.lbl_centered = QLabel(self.main_window.txt("msg_keep_centered") if self.main_window else "Keep centered")
        self.lbl_centered.setStyleSheet(f"color: #b0b0b0; font-size: {config.FS(9)}pt;")
        left_layout.addWidget(self.lbl_centered)
        left_layout.addSpacing(config.S(6))

        # Modularity Buttons: Waveform Timeline & Video Preview Toggles
        self.btn_toggle_timeline = PreviewToggleBtn("timeline", parent=self)
        self.btn_toggle_timeline.setChecked(self.show_timeline)
        self.btn_toggle_timeline.setToolTip(self.main_window.txt("tt_toggle_timeline", "Toggle Timeline Preview") if self.main_window else "Toggle Timeline")
        self.btn_toggle_timeline.clicked.connect(self.toggle_timeline_preview)
        left_layout.addWidget(self.btn_toggle_timeline)

        self.btn_toggle_video = PreviewToggleBtn("video", parent=self)
        self.btn_toggle_video.setChecked(self.show_video)
        self.btn_toggle_video.setToolTip(self.main_window.txt("tt_toggle_video", "Toggle Video Preview") if self.main_window else "Toggle Video Preview")
        self.btn_toggle_video.clicked.connect(self.toggle_video_preview)
        left_layout.addWidget(self.btn_toggle_video)

        left_layout.addStretch()

        # --- Center Section: Playback Controls ---
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(config.S(8))
        center_layout.setAlignment(Qt.AlignCenter)

        self.btn_prev = AnimatedPlayerButton("player-backward.png", button_size=config.S(30), icon_size=config.S(14))
        play_size = max(32, config.S(34))
        play_icon = max(16, config.S(16))
        self.btn_play = AnimatedPlayerButton("player-play.png", button_size=play_size, icon_size=play_icon, is_circle=True)
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.setStyleSheet("QPushButton#PlayBtn { background: transparent; border: none; outline: none; }")
        self.btn_next = AnimatedPlayerButton("player-forward.png", button_size=config.S(30), icon_size=config.S(14))

        center_layout.addWidget(self.btn_prev)
        center_layout.addWidget(self.btn_play)
        center_layout.addWidget(self.btn_next)

        # --- Right Section: Speed + Volume ---
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(config.S(8))
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.cb_speed = SpeedDropdown()
        self.cb_speed.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x"])
        self.cb_speed.setCurrentText("1.0x")
        self.cb_speed.setFixedWidth(config.S(58))
        right_layout.addWidget(self.cb_speed)

        self.lbl_vol_icon = QLabel()
        self.lbl_vol_icon.setFixedSize(config.S(18), config.S(18))
        self.lbl_vol_icon.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.lbl_vol_icon)

        self.slider_vol = JumpSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        self.slider_vol.setFixedWidth(config.S(64))
        right_layout.addWidget(self.slider_vol)

        controls_layout.addWidget(left_widget, 2, Qt.AlignLeft | Qt.AlignVCenter)
        controls_layout.addWidget(center_widget, 1, Qt.AlignCenter)
        controls_layout.addWidget(right_widget, 2, Qt.AlignRight | Qt.AlignVCenter)

        self.content_layout.addWidget(self.controls_widget)

        # 6. Bottom Media Container: Video Preview + Timeline Preview (matching Screenshot 1!)
        self.media_container = QWidget()
        self.media_container.setObjectName("MediaContainer")
        self.media_layout = QHBoxLayout(self.media_container)
        self.media_layout.setContentsMargins(config.S(16), 0, config.S(16), config.S(10))
        self.media_layout.setSpacing(config.S(12))

        # Left: 16:9 Video Monitor
        self.video_preview_widget = VideoPreviewWidget(self.media_container)
        self.media_layout.addWidget(self.video_preview_widget, 0)

        # Right: Waveform Timeline Preview Ribbon
        self.waveform_timeline = WaveformTimelineWidget(self.media_container, main_window)
        self.waveform_timeline.seek_requested.connect(self._on_waveform_seek_requested)
        self.media_layout.addWidget(self.waveform_timeline, 1)

        self.content_layout.addWidget(self.media_container)

        # 7. Media Player Engine
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.setVideoOutput(self.video_preview_widget.video_widget)

        # Signal Connections
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_prev.clicked.connect(self.skip_backward)
        self.btn_next.clicked.connect(self.skip_forward)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        self.cb_speed.currentTextChanged.connect(self.change_speed)
        self._on_volume_changed(100)

        from gui.vsync import get_refresh_interval_ms
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(get_refresh_interval_ms())
        self.update_timer.timeout.connect(self.sync_playback)

        self.player.playbackStateChanged.connect(self.on_state_changed)

        # State Variables
        self.current_word_idx = -1
        self.last_jumped_ts = -1.0
        self.original_audio_path = None
        self._source_audio_path = None
        self._source_video_path = None
        self.clean_ops = None

        self.hide()

    # -------------------------------------------------------------------------
    # Modularity & Toggles (Timeline, Video, Controls, Collapse)
    # -------------------------------------------------------------------------

    def toggle_timeline_preview(self) -> None:
        """Toggles visibility of the Waveform Timeline ribbon."""
        self.show_timeline = self.btn_toggle_timeline.isChecked()
        self._apply_modularity_state()
        self._save_modularity_prefs()

    def toggle_video_preview(self) -> None:
        """Toggles visibility of the 16:9 Video Monitor."""
        self.show_video = self.btn_toggle_video.isChecked()
        self._apply_modularity_state()
        self._save_modularity_prefs()

    def _save_modularity_prefs(self) -> None:
        if self.main_window and hasattr(self.main_window, "engine"):
            prefs = self.main_window.engine.load_preferences() or {}
            prefs["show_timeline_preview"] = self.show_timeline
            prefs["show_video_preview"] = self.show_video
            self.main_window.engine.save_preferences(prefs)

    def _apply_modularity_state(self) -> None:
        """Updates visibility of video, timeline, and media container based on toggle states."""
        self.waveform_timeline.setVisible(self.show_timeline)
        self.video_preview_widget.setVisible(self.show_video)

        has_media = self.show_timeline or self.show_video
        self.media_container.setVisible(has_media)

        # Resize video preview to maintain 16:9 aspect ratio relative to container
        target_h = config.S(235)
        self.video_preview_widget.setFixedHeight(target_h)
        self.video_preview_widget.setFixedWidth(int(target_h * 16.0 / 9.0))
        self.waveform_timeline.setFixedHeight(target_h)

        if not getattr(self, "is_collapsed", False):
            self.content_widget.setMaximumHeight(16777215)
            self.content_widget.setMinimumHeight(0)
            self.updateGeometry()

        self.update_tab_position()

    def update_tab_position(self) -> None:
        """Centers the floating toggle tab directly above the Play button."""
        if not hasattr(self, "toggle_tab") or not self.toggle_tab:
            return
        parent = self.parentWidget()
        if not parent or not self.isVisible():
            if hasattr(self, "toggle_tab") and self.toggle_tab:
                self.toggle_tab.hide()
            return

        tw = self.toggle_tab.width()
        th = self.toggle_tab.height()

        if hasattr(self, "btn_play") and self.btn_play.isVisible():
            center_pt = self.btn_play.mapTo(parent, self.btn_play.rect().center())
            target_x = center_pt.x() - (tw // 2)
        else:
            target_x = (parent.width() - tw) // 2

        target_y = self.y() - th
        self.toggle_tab.move(target_x, target_y)
        if not self.toggle_tab.isVisible():
            self.toggle_tab.show()
            self.toggle_tab.raise_()

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() == QEvent.Resize:
            self.update_tab_position()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_tab_position()
        self.update_seek_margins()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_tab_position()
        self.update_seek_margins()

    def update_seek_margins(self) -> None:
        """
        Dynamically adjusts left and right spacers so that slider_seek aligns
        between the left activity panel and right activity panel (matching the central editor width).
        """
        if not self.main_window or not hasattr(self, 'seek_spacer_left') or not hasattr(self, 'seek_spacer_right'):
            return
        try:
            stack = getattr(self.main_window, "_stack", None)
            if stack and stack.isVisible() and self.isVisible():
                p_tl = stack.mapToGlobal(QPointF(0, 0).toPoint())
                p_tr = stack.mapToGlobal(QPointF(stack.width(), 0).toPoint())

                self_tl = self.mapFromGlobal(p_tl)
                self_tr = self.mapFromGlobal(p_tr)

                w_left = max(0, int(self_tl.x()))
                w_right = max(0, int(self.width() - self_tr.x()))

                if self.seek_spacer_left.width() != w_left:
                    self.seek_spacer_left.setFixedWidth(w_left)
                if self.seek_spacer_right.width() != w_right:
                    self.seek_spacer_right.setFixedWidth(w_right)
            else:
                sb_l = getattr(self.main_window, "_sidebar_left", None)
                p_l = getattr(self.main_window, "_panel_left", None)
                sb_r = getattr(self.main_window, "_sidebar_right", None)
                p_r = getattr(self.main_window, "_panel_right", None)

                w_left = (sb_l.width() if sb_l and sb_l.isVisible() else 0) + (p_l.width() if p_l and p_l.isVisible() else 0)
                w_right = (sb_r.width() if sb_r and sb_r.isVisible() else 0) + (p_r.width() if p_r and p_r.isVisible() else 0)

                self.seek_spacer_left.setFixedWidth(max(0, w_left))
                self.seek_spacer_right.setFixedWidth(max(0, w_right))
        except Exception:
            pass

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "toggle_tab") and self.toggle_tab:
            self.toggle_tab.hide()

    def is_preview_active(self) -> bool:
        return self.isVisible() and not getattr(self, "is_collapsed", False)

    def _get_expanded_target_height(self) -> int:
        h = self.controls_widget.sizeHint().height() + self.slider_seek.height()
        if self.show_timeline or self.show_video:
            h += config.S(235) + config.S(14)
        return max(50, h)

    def toggle_collapse(self) -> None:
        """Smoothly collapses or expands the entire preview dock."""
        if getattr(self, "_anim", None) and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()

        target_collapsed = not self.is_collapsed
        self.is_collapsed = target_collapsed
        self.toggle_tab.set_collapsed(target_collapsed)

        target_h = self._get_expanded_target_height()

        if target_collapsed:
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
            self.update_timer.stop()
            self._clear_highlights()

            start_h = self.content_widget.height()
            if start_h <= 0:
                start_h = target_h
            self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight")
            self._anim.setDuration(300)
            self._anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim.setStartValue(start_h)
            self._anim.setEndValue(0)
            self._anim.valueChanged.connect(lambda _v: self.update_tab_position())

            def on_collapse_finished():
                if self.is_collapsed:
                    self.content_widget.hide()
                    self.content_widget.setMaximumHeight(16777215)
                self.update_tab_position()

            self._anim.finished.connect(on_collapse_finished)
            self._anim.start()
        else:
            self.content_widget.show()
            self.content_widget.setMaximumHeight(0)
            self.current_word_idx = -1
            self.sync_playback()

            self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight")
            self._anim.setDuration(300)
            self._anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim.setStartValue(0)
            self._anim.setEndValue(target_h)
            self._anim.valueChanged.connect(lambda _v: self.update_tab_position())

            def on_expand_finished():
                if not self.is_collapsed:
                    self.content_widget.setMaximumHeight(16777215)
                    self.content_widget.setMinimumHeight(0)
                self.update_tab_position()

            self._anim.finished.connect(on_expand_finished)
            self._anim.start()

    # -------------------------------------------------------------------------
    # Audio & Video Availability
    # -------------------------------------------------------------------------

    def _show_missing_audio_ui(self, is_loading=False, failed=False):
        if is_loading:
            loading_txt = self.main_window.txt("msg_audio_preview_preparing") if self.main_window else "Preparing preview..."
            self.lbl_status.setText(f"<span style='color: #b0b0b0;'>{loading_txt}</span>")
        elif failed:
            failed_txt = self.main_window.txt("msg_audio_preview_failed") if self.main_window else "Failed to get audio. Click to retry."
            html = f"<a href='fetch_audio' style='color: #e74c3c; text-decoration: none;'>{failed_txt}</a>"
            self.lbl_status.setText(html)
        else:
            prefix = self.main_window.txt("msg_audio_preview_missing") if self.main_window else "Audio not found."
            link_txt = self.main_window.txt("msg_audio_preview_get_now") if self.main_window else "Get preview audio"
            html = f"{prefix} <a href='fetch_audio' style='color: #1a7a45; text-decoration: underline;'>{link_txt}</a>"
            self.lbl_status.setText(html)

        self.lbl_status.show()
        self.controls_widget.hide()
        self.slider_seek.hide()
        self.media_container.hide()
        if getattr(self, "is_collapsed", False):
            self.content_widget.hide()
        else:
            self.content_widget.show()
        self.show()

    def _on_fetch_missing_audio(self, url=None):
        if getattr(self, "_fetching_audio", False):
            return
        self._fetching_audio = True
        self._show_missing_audio_ui(is_loading=True)

        from PySide6.QtCore import QThread, Signal

        class FetchAudioWorker(QThread):
            finished = Signal(str)
            def __init__(self, main_win):
                super().__init__()
                self.main_win = main_win
            def run(self):
                try:
                    settings = {}
                    snap = getattr(self.main_win, "_transcription_source", None) or {}
                    tl_name = snap.get("timeline_name")
                    if not tl_name and hasattr(self.main_win, "combo_tl_0") and self.main_win.combo_tl_0:
                        tl_name = self.main_win.combo_tl_0.text()
                    if tl_name:
                        settings["timeline_name"] = tl_name

                    track_indices = snap.get("track_indices")
                    if not track_indices and hasattr(self.main_win, "get_selected_track_indices"):
                        track_indices = self.main_win.get_selected_track_indices()
                    if track_indices:
                        settings["track_indices"] = track_indices

                    source_files = snap.get("source_files") or []
                    if not source_files:
                        canvas = getattr(self.main_win, "text_canvas", None)
                        if canvas and getattr(canvas, "words_data", None):
                            audio_p = canvas.words_data[0].get("meta_audio_path")
                            if audio_p:
                                source_files = [audio_p]
                    if source_files:
                        settings["source_files"] = source_files

                    wav_path = self.main_win.engine.prepare_preview_audio(settings)
                    self.finished.emit(wav_path or "")
                except Exception as e:
                    log_error(f"FetchAudioWorker error: {e}")
                    self.finished.emit("")

        self._fetch_thread = FetchAudioWorker(self.main_window)

        def _on_fetch_done(wav_path):
            self._fetching_audio = False
            if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                canvas = getattr(self.main_window, "text_canvas", None)
                if canvas and getattr(canvas, "words_data", None):
                    for w in canvas.words_data:
                        w["meta_audio_path"] = wav_path
                self.check_audio_availability()
            else:
                self._show_missing_audio_ui(is_loading=False, failed=True)

        self._fetch_thread.finished.connect(_on_fetch_done)
        self._fetch_thread.start()

    def check_audio_availability(self) -> None:
        """Discovers audio & video media and configures the player and timeline ribbon."""
        canvas = getattr(self.main_window, "text_canvas", None)
        words = getattr(canvas, "words_data", None) if canvas else None
        audio_path = words[0].get("meta_audio_path") if (words and len(words) > 0) else None

        if not audio_path and self.main_window and hasattr(self.main_window, "engine"):
            audio_path = getattr(self.main_window.engine, "current_analysis_audio_path", None) or getattr(self.main_window.engine, "last_audio_path", None)

        if not audio_path or not os.path.exists(audio_path):
            if not words:
                self.hide()
                return
            self._show_missing_audio_ui(is_loading=getattr(self, "_fetching_audio", False))
            return

        # Restore UI controls
        self.lbl_status.hide()
        self.controls_widget.show()
        self.slider_seek.show()
        self._apply_modularity_state()

        if getattr(self, "is_collapsed", False):
            self.content_widget.hide()
        else:
            self.content_widget.show()
        self.show()

        # Discover source video file (e.g. from DaVinci timeline or project snapshot)
        snap = getattr(self.main_window, "_transcription_source", None) or {}
        source_files = list(snap.get("source_files") or [])
        video_file = None

        for sf in source_files:
            if sf and os.path.isfile(sf):
                ext = os.path.splitext(sf)[1].lower()
                if ext in (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".webm"):
                    video_file = sf
                    break

        # Fallback 1: Query resolve_handler for timeline source files if snap was empty or missing video
        if not video_file and self.main_window and getattr(self.main_window, "resolve_handler", None):
            tl_name = snap.get("timeline_name")
            try:
                resolved_files = self.main_window.resolve_handler.get_timeline_source_files(tl_name)
                for sf in (resolved_files or []):
                    if sf and os.path.isfile(sf):
                        ext = os.path.splitext(sf)[1].lower()
                        if ext in (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".webm"):
                            video_file = sf
                            source_files.append(sf)
                            break
                if source_files:
                    snap["source_files"] = source_files
                    self.main_window._transcription_source = snap
            except Exception as _e:
                pass

        # Fallback 2: Check adjacent directory of audio_path for matching video footage
        if not video_file and audio_path:
            audio_dir = os.path.dirname(audio_path)
            if os.path.isdir(audio_dir):
                try:
                    for fname in os.listdir(audio_dir):
                        ext = os.path.splitext(fname)[1].lower()
                        if ext in (".mov", ".mp4", ".m4v", ".mkv", ".webm"):
                            cand = os.path.join(audio_dir, fname)
                            if os.path.isfile(cand) and os.path.getsize(cand) > 1024 * 1024:
                                video_file = cand
                                break
                except Exception:
                    pass

        clip_name = os.path.basename(video_file) if video_file else (
            f"A1: {snap.get('timeline_name', 'Timeline Audio')}" if snap.get("timeline_name") else os.path.basename(audio_path)
        )

        # Set media player source
        target_source = video_file if (video_file and self.clean_ops is None) else audio_path
        if self._source_audio_path != target_source:
            self._source_audio_path = target_source
            self.original_audio_path = target_source
            self.player.setSource(QUrl.fromLocalFile(target_source))
            self.clean_ops = None
            self.current_word_idx = -1
            self.last_jumped_ts = -1.0
        if video_file:
            self.video_preview_widget.show_placeholder(False)
        else:
            self.video_preview_widget.show_placeholder(True, "Audio Only")

        # Configure Waveform Timeline Ribbon
        self.waveform_timeline.load_from_audio(audio_path, clip_name=clip_name)
        self.waveform_timeline.set_words_data(words)

    def load_assembled_audio(self, assembled_audio_path: str, clean_ops: List[Dict[str, Any]]) -> None:
        """Switches playback to the newly assembled timeline audio."""
        if os.path.exists(assembled_audio_path):
            self.original_audio_path = assembled_audio_path
            self.clean_ops = clean_ops
            self.player.setSource(QUrl.fromLocalFile(assembled_audio_path))
            self.lbl_status.hide()
            self.controls_widget.show()
            self.slider_seek.show()
            self._apply_modularity_state()

            if getattr(self, "is_collapsed", False):
                self.content_widget.hide()
            else:
                self.content_widget.show()

            self.slider_seek.setValue(0)
            self.current_word_idx = -1
            self.last_jumped_ts = -1.0
            self._clear_highlights()
            self.show()

            self.waveform_timeline.load_from_audio(assembled_audio_path, clip_name="A1: Assembled Timeline")
            self.waveform_timeline.set_words_data([])

    # -------------------------------------------------------------------------
    # Playback Controls & Sync
    # -------------------------------------------------------------------------

    def set_position_ms(self, ms: int, force_word_idx: Optional[int] = None) -> None:
        self.player.setPosition(ms)
        self._start_pos_s = ms / 1000.0
        self._real_start_time = time.time()

        if force_word_idx is not None and force_word_idx >= 0:
            self._force_highlight_idx = force_word_idx
            self._force_highlight_until = time.time() + 0.3

        self.waveform_timeline.set_playhead_time(self._start_pos_s)
        self.sync_playback()

    def _get_audio_t(self) -> float:
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            return self.player.position() / 1000.0
        return getattr(self, "_start_pos_s", 0.0) + (time.time() - getattr(self, "_real_start_time", 0.0)) * self.player.playbackRate()

    def toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self._start_pos_s = self.player.position() / 1000.0
            self._real_start_time = time.time()
            self.player.play()
            self.update_timer.start()

    def on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlayingState:
            self.btn_play.update_icon("player-stop.png")
            self.update_timer.start()
            vol = self.slider_vol.value()
            self.audio_output.setVolume(vol / 100.0)
            self._force_system_volume(vol)
        else:
            self.btn_play.update_icon("player-play.png")
            self.update_timer.stop()
            if state == QMediaPlayer.StoppedState:
                self._clear_highlights()
                self.waveform_timeline.set_playhead_time(0.0)

    def skip_forward(self) -> None:
        curr_t = self._get_audio_t()
        self.set_position_ms(int((curr_t + 3.0) * 1000))

    def skip_backward(self) -> None:
        curr_t = self._get_audio_t()
        self.set_position_ms(int(max(0.0, curr_t - 3.0) * 1000))

    def _on_volume_changed(self, v: int) -> None:
        self.audio_output.setVolume(v / 100.0)
        self._force_system_volume(v)
        from gui.utils import get_layout_icon_path

        if v > 70:
            path = get_layout_icon_path("volume-max.png")
        elif v >= 40:
            path = get_layout_icon_path("volume-mid.png")
        else:
            path = get_layout_icon_path("volume-min.png")

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
            s = config.S(18)
            pixmap = pixmap.scaled(int(s * dpr), int(s * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            pixmap.setDevicePixelRatio(dpr)
        self.lbl_vol_icon.setPixmap(pixmap)

    def change_speed(self, text: str) -> None:
        if not text.endswith("x"):
            return
        try:
            new_rate = float(text[:-1])
        except ValueError:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self._start_pos_s = self._get_audio_t()
            self._real_start_time = time.time()
        self.player.setPlaybackRate(new_rate)

    def _on_user_scroll(self, action: int) -> None:
        if getattr(self, "tgl_centered", None) and self.tgl_centered.isChecked():
            self.tgl_centered.setChecked(False)

    def _on_tgl_centered_changed(self, state: bool) -> None:
        if state:
            self._center_current_word()

    def _center_current_word(self) -> None:
        if getattr(self, "current_word_idx", -1) == -1:
            return
        canvas = getattr(self.main_window, "text_canvas", None)
        if not canvas or not getattr(canvas, "words_data", None):
            return

        words = canvas.words_data
        if 0 <= self.current_word_idx < len(words):
            w = words[self.current_word_idx]
            if "_rect" in w:
                rect = w["_rect"]
                scroll_area = getattr(self.main_window, "scroll_area", None)
                if scroll_area:
                    scroll_area.ensureVisible(rect.x(), rect.y(), 50, 50)
                    vp_h = scroll_area.viewport().height()
                    vbar = scroll_area.verticalScrollBar()
                    target_y = rect.center().y()
                    new_val = int(target_y - vp_h / 2)
                    vbar.setValue(max(vbar.minimum(), min(new_val, vbar.maximum())))

    def _on_seek_pressed(self) -> None:
        self._seek_dragging = True

    def _on_seek_released(self) -> None:
        from PySide6.QtGui import QGuiApplication
        self._seek_dragging = False
        dur = self.player.duration()
        if dur > 0:
            ms = int(self.slider_seek.value() / 1000.0 * dur)
            self.set_position_ms(ms)
            mods = QGuiApplication.queryKeyboardModifiers()
            if mods & (Qt.ControlModifier | Qt.AltModifier):
                t_s = ms / 1000.0
                if self.main_window and hasattr(self.main_window, "_jump_playhead"):
                    self.main_window._jump_playhead(t_s)

    def _on_seek_moved(self, value: int) -> None:
        dur = self.player.duration()
        if dur > 0:
            t = (value / 1000.0) * (dur / 1000.0)
            self.lbl_timecode.setText(self._format_timecode(t))

    def _on_waveform_seek_requested(self, timestamp_s: float, sync_resolve: bool = False) -> None:
        """Receives playhead click/scrub from WaveformTimelineWidget for 60 FPS local playback and video sync."""
        audio_pos_s = timestamp_s
        if self.clean_ops:
            audio_pos_s = self._original_to_audio_time(timestamp_s)
        self.set_position_ms(int(audio_pos_s * 1000))
        if sync_resolve and self.main_window and hasattr(self.main_window, "_jump_playhead"):
            self.main_window._jump_playhead(timestamp_s)

    def _format_timecode(self, seconds: float) -> str:
        """Formats seconds to SMPTE timecode (HH:MM:SS:FF) matching DaVinci Resolve."""
        fps = 24.0
        start_frame = 0
        if self.main_window and hasattr(self.main_window, "resolve_handler") and self.main_window.resolve_handler:
            fps = float(self.main_window.resolve_handler.fps or 24.0)
            try:
                start_frame = int(self.main_window.resolve_handler.get_timeline_start_frame() or 0)
            except Exception:
                start_frame = 0

        # Fallback start frame 01:00:00:00 (standard DaVinci Resolve timeline start)
        if start_frame <= 0 and fps > 0:
            start_frame = int(3600 * fps)

        curr_frame = start_frame + int(round(seconds * fps))
        int_fps = max(1, int(round(fps)))
        ff = curr_frame % int_fps
        total_s = curr_frame // int_fps
        ss = total_s % 60
        mm = (total_s // 60) % 60
        hh = total_s // 3600
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"

    def _audio_to_original_time(self, audio_t: float) -> float:
        if not self.clean_ops:
            return audio_t
        fps = getattr(self.main_window.resolve_handler, "fps", 24.0) if self.main_window else 24.0
        audio_frames = audio_t * fps
        current_audio_f = 0
        for op in self.clean_ops:
            dur = op["e"] - op["s"]
            if current_audio_f <= audio_frames < current_audio_f + dur:
                return (op["s"] + (audio_frames - current_audio_f)) / fps
            current_audio_f += dur
        if self.clean_ops:
            return self.clean_ops[-1]["e"] / fps
        return audio_t

    def _original_to_audio_time(self, orig_t: float) -> float:
        if not self.clean_ops:
            return orig_t
        fps = getattr(self.main_window.resolve_handler, "fps", 24.0) if self.main_window else 24.0
        orig_frames = orig_t * fps
        current_audio_f = 0
        for op in self.clean_ops:
            if orig_frames < op["s"]:
                break
            if op["s"] <= orig_frames <= op["e"]:
                return (current_audio_f + (orig_frames - op["s"])) / fps
            current_audio_f += (op["e"] - op["s"])
        return current_audio_f / fps

    def sync_playback(self) -> None:
        """60 FPS synchronization tick for playhead, waveform, video, and words."""
        if getattr(self, "is_collapsed", False):
            self._clear_highlights()
            return
        canvas = getattr(self.main_window, "text_canvas", None)
        if not canvas or not getattr(canvas, "words_data", None):
            return

        audio_t = max(0.0, self._get_audio_t())
        orig_t = self._audio_to_original_time(audio_t) if self.clean_ops else audio_t

        dur = self.player.duration() / 1000.0
        self.lbl_timecode.setText(self._format_timecode(orig_t))

        # Update seek slider position
        if not self._seek_dragging and dur > 0:
            self.slider_seek.setValue(int(audio_t / dur * 1000))

        # Synchronize Waveform Timeline playhead
        self.waveform_timeline.set_playhead_time(audio_t)

        # Word highlighting
        found_idx = -1
        if time.time() < getattr(self, "_force_highlight_until", 0.0):
            found_idx = getattr(self, "_force_highlight_idx", -1)
        else:
            offset_s = 0.0
            if self.clean_ops and hasattr(self.main_window, "engine"):
                prefs = self.main_window.engine.load_preferences() or {}
                offset_s = prefs.get("offset", 0.133)

            match_t = orig_t + 0.15 - offset_s
            for i, w_item in enumerate(canvas.words_data):
                start_t = w_item.get("start", 0)
                if start_t > match_t:
                    found_idx = i - 1
                    break
            else:
                if canvas.words_data:
                    found_idx = len(canvas.words_data) - 1

        if found_idx >= 0 and canvas.words_data[found_idx].get("type") == "silence":
            pass
        elif found_idx != getattr(self, "current_word_idx", -1):
            self._clear_highlights()
            self.current_word_idx = found_idx
            if found_idx >= 0:
                w = canvas.words_data[found_idx]
                w["_audio_active"] = True
                canvas.update()

        if getattr(self, "tgl_centered", None) and self.tgl_centered.isChecked():
            self._center_current_word()

    def _clear_highlights(self) -> None:
        canvas = getattr(self.main_window, "text_canvas", None)
        if canvas and canvas.words_data:
            for w in canvas.words_data:
                w.pop("_audio_active", None)
            canvas.update()

    def _force_system_volume(self, v: int) -> None:
        if os.name != "posix":
            return
        def _task():
            try:
                time.sleep(0.1)
                script_name = os.path.basename(sys.argv[0])
                out = subprocess.check_output(["pactl", "list", "sink-inputs"], text=True)
                current_id = None
                for line in out.splitlines():
                    if "Sink Input" in line or "odpływ wejścia" in line:
                        m = re.search(r"(?:#|^)(\d+)\.?", line)
                        if m:
                            current_id = m.group(1)
                    if script_name in line and current_id:
                        subprocess.call(["pactl", "set-sink-input-volume", current_id, f"{v}%"])
            except Exception:
                pass
        threading.Thread(target=_task, daemon=True).start()
