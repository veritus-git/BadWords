#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: audio_preview.py
ROLE: GUI Component
DESCRIPTION:
GUI component for audio track preview and waveform visualization.
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
from .mixins import FramelessWindowMixin, _BaseDialog
from ..utils import _app_icon, _txt

class AudioPreviewWidget(QFrame):
    def __init__(self, parent_widget, main_window):
        super().__init__(parent_widget)
        self.main_window = main_window
        self.is_collapsed = False
        self._anim = None
        
        import os
        if os.name == 'posix':
            # Changing application.name forces PulseAudio/PipeWire to create a NEW volume profile
            # at 100%, completely bypassing the user's previously stuck 30% volume bug.
            os.environ["PULSE_PROP_application.name"] = "BadWordsApp"
            os.environ["PULSE_PROP_media.role"] = "production"
            os.environ["QT_MEDIA_BACKEND"] = "gstreamer"
        
        if self.main_window and hasattr(self.main_window, 'scroll_area'):
            vbar = self.main_window.scroll_area.verticalScrollBar()
            vbar.actionTriggered.connect(self._on_user_scroll)
            
        from PySide6.QtWidgets import QHBoxLayout, QPushButton, QComboBox, QSlider, QLabel, QWidget, QVBoxLayout
        from PySide6.QtCore import Qt, QUrl, QTimer, QEvent
        from PySide6.QtGui import QColor, QFont
        from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
        import os

        self.setObjectName("AudioPreview")
        self.setStyleSheet(f"""
            QFrame#AudioPreview {{
                background: transparent;
                border: none;
            }}
            QWidget#AudioContent {{
                background-color: #191919;
                border-top: 1px solid #2a2a2a;
            }}
            QWidget#TabContainer {{
                background: transparent;
                border: none;
            }}
            QWidget#AudioControls {{
                background: transparent;
            }}
            QWidget {{
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-weight: 600;
                font-size: 14px;
                padding: 6px 10px;
                border-radius: 8px;
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
                border-radius: 20px;
                font-size: 16px;
            }}
            QPushButton#PlayBtn:hover {{
                background-color: {config.BTN_ACTIVE};
            }}
            QLabel {{
                background: transparent;
                border: none;
                color: #b0b0b0;
                font-size: 13px;
            }}
            QComboBox {{
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #d0d0d0;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border: 1px solid rgba(255, 255, 255, 0.15);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.10);
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: #d0d0d0;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #ffffff;
            }}
            QSlider#SeekSlider::groove:horizontal {{
                height: 4px;
                background: rgba(255, 255, 255, 0.08);
                border-radius: 2px;
            }}
            QSlider#SeekSlider::sub-page:horizontal {{
                background: #1ed760;
                border-radius: 2px;
            }}
            QSlider#SeekSlider::handle:horizontal {{
                background: #ffffff;
                width: 8px;
                margin: -3px 0;
                border-radius: 4px;
            }}
            QLabel#TimeLabel {{
                font-family: 'JetBrains Mono', 'Consolas', 'Menlo', monospace;
                font-size: 11px;
                color: #707070;
                letter-spacing: 0.5px;
            }}
            QLabel#StatusLabel {{
                color: #666666;
                font-style: italic;
                font-size: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Content container (collapsible)
        self.content_widget = QWidget()
        self.content_widget.setObjectName("AudioContent")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        layout.addWidget(self.content_widget)

        # Floating toggle tab (wysepka parented to parent page for true zero-margin overlay)
        self.toggle_tab = AudioToggleTab(parent_widget)
        self.toggle_tab.setToolTip(self.main_window.txt("tooltip_toggle_audio_preview"))
        self.toggle_tab.clicked.connect(self.toggle_collapse)
        
        if parent_widget:
            parent_widget.installEventFilter(self)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("StatusLabel")
        self.lbl_status.setFixedHeight(70)
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setOpenExternalLinks(False)
        self.lbl_status.setTextFormat(Qt.RichText)
        self.lbl_status.setStyleSheet("""
            QLabel#StatusLabel {
                background-color: #1a1a1a;
                color: #d0d0d0;
                font-size: 13px;
                padding: 12px;
                border-top: 1px solid #2a2a2a;
                border-left: none;
                border-right: none;
                border-bottom: none;
            }
            QLabel#StatusLabel a {
                color: #1a7a45;
                font-weight: 600;
                text-decoration: underline;
                text-underline-offset: 3px;
            }
            QLabel#StatusLabel a:hover {
                color: #23a559;
            }
        """)
        self.lbl_status.linkActivated.connect(self._on_fetch_missing_audio)
        self.lbl_status.hide()
        content_layout.addWidget(self.lbl_status)

        self.controls_widget = QWidget()
        self.controls_widget.setObjectName("AudioControls")
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(16)
        
        # Left controls (Keep centered)
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        
        self.tgl_centered = ToggleSwitch(parent=self)
        self.tgl_centered.toggled.connect(self._on_tgl_centered_changed)
        
        self.lbl_centered = QLabel(self.main_window.txt("msg_keep_centered"))
        self.lbl_centered.setStyleSheet("color: #b0b0b0; font-size: 13px;")
        
        left_layout.addWidget(self.tgl_centered)
        left_layout.addSpacing(12)
        left_layout.addWidget(self.lbl_centered)
        left_layout.addStretch()
        
        self.lbl_vol_icon = QLabel()
        self.lbl_vol_icon.setFixedSize(20, 20)
        self.lbl_vol_icon.setAlignment(Qt.AlignCenter)
        
        self.slider_vol = JumpSlider(Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(100)
        self.slider_vol.setFixedWidth(60)
        
        self.cb_speed = SpeedDropdown()
        self.cb_speed.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x"])
        self.cb_speed.setCurrentText("1.0x")
        self.cb_speed.setFixedWidth(60)
        
        # Center controls (Playback + Seek slider)
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        
        play_layout = QHBoxLayout()
        play_layout.setAlignment(Qt.AlignCenter)
        
        self.btn_prev = AnimatedPlayerButton("player-backward.png", button_size=32, icon_size=16)
        self.btn_play = AnimatedPlayerButton("player-play.png", button_size=32, icon_size=16)
        self.btn_play.setObjectName("PlayBtn")
        self.btn_play.setStyleSheet(f"""
            QPushButton#PlayBtn {{
                background-color: #ffffff;
                border-radius: 16px;
            }}
            QPushButton#PlayBtn:hover {{
                background-color: #e0e0e0;
            }}
        """)
        self.btn_next = AnimatedPlayerButton("player-forward.png", button_size=32, icon_size=16)
        
        play_layout.addWidget(self.btn_prev)
        play_layout.addSpacing(8)
        play_layout.addWidget(self.btn_play)
        play_layout.addSpacing(8)
        play_layout.addWidget(self.btn_next)
        
        self.slider_seek = JumpSlider(Qt.Horizontal)
        self.slider_seek.setObjectName("SeekSlider")
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.setMinimumWidth(100)
        from PySide6.QtWidgets import QSizePolicy
        self.slider_seek.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._seek_dragging = False
        self.slider_seek.sliderPressed.connect(self._on_seek_pressed)
        self.slider_seek.sliderReleased.connect(self._on_seek_released)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        self.slider_seek.sliderMoved.connect(self._on_seek_moved)
        
        self.lbl_time_curr = QLabel("0:00")
        self.lbl_time_curr.setObjectName("TimeLabel")
        self.lbl_time_curr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_time_curr.setFixedWidth(40)
        
        self.lbl_time_total = QLabel("0:00")
        self.lbl_time_total.setObjectName("TimeLabel")
        self.lbl_time_total.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_time_total.setFixedWidth(40)
        
        seek_layout = QHBoxLayout()
        seek_layout.setAlignment(Qt.AlignCenter)
        seek_layout.addWidget(self.lbl_time_curr)
        seek_layout.addSpacing(8)
        seek_layout.addWidget(self.slider_seek, 1)
        seek_layout.addSpacing(8)
        seek_layout.addWidget(self.lbl_time_total)
        
        center_layout.addLayout(play_layout)
        center_layout.addLayout(seek_layout)
        
        # Right controls (Volume & Speed)
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        
        right_layout.addWidget(self.cb_speed)
        right_layout.addSpacing(4)
        right_layout.addWidget(self.lbl_vol_icon)
        right_layout.addWidget(self.slider_vol)
        
        controls_layout.addWidget(left_widget, 1, Qt.AlignLeft | Qt.AlignVCenter)
        controls_layout.addWidget(center_widget, 3, Qt.AlignVCenter)
        controls_layout.addWidget(right_widget, 1, Qt.AlignRight | Qt.AlignVCenter)

        content_layout.addWidget(self.controls_widget)
        layout.addWidget(self.content_widget)

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_prev.clicked.connect(self.skip_backward)
        self.btn_next.clicked.connect(self.skip_forward)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        self.cb_speed.currentTextChanged.connect(self.change_speed)
        
        self._on_volume_changed(100)

        self.update_timer = QTimer(self)
        self.update_timer.setInterval(16)
        self.update_timer.timeout.connect(self.sync_playback)

        self.player.playbackStateChanged.connect(self.on_state_changed)
        
        self.current_word_idx = -1
        self.last_jumped_ts = -1.0
        self.original_audio_path = None
        self._source_audio_path = None
        self.clean_ops = None
        
        self.hide()

    def update_tab_position(self):
        if not hasattr(self, 'toggle_tab') or not self.toggle_tab:
            return
        parent = self.parentWidget()
        if not parent or not self.isVisible():
            if hasattr(self, 'toggle_tab') and self.toggle_tab:
                self.toggle_tab.hide()
            return
        
        tw = self.toggle_tab.width()
        th = self.toggle_tab.height()
        
        if hasattr(self, 'btn_play') and self.btn_play.isVisible():
            center_pt = self.btn_play.mapTo(parent, self.btn_play.rect().center())
            target_x = center_pt.x() - (tw // 2)
        else:
            target_x = (parent.width() - tw) // 2
            
        target_y = self.y() - th
        
        self.toggle_tab.move(target_x, target_y)
        self.toggle_tab.raise_()
        self.toggle_tab.show()

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        if watched == self.parentWidget() and event.type() == QEvent.Resize:
            self.update_tab_position()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_tab_position()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_tab_position()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, 'toggle_tab') and self.toggle_tab:
            self.toggle_tab.hide()

    def is_preview_active(self):
        return self.isVisible() and not getattr(self, 'is_collapsed', False)

    def toggle_collapse(self):
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        from PySide6.QtMultimedia import QMediaPlayer
        
        if getattr(self, '_anim', None) and self._anim.state() == QPropertyAnimation.Running:
            self._anim.stop()
            
        target_collapsed = not self.is_collapsed
        self.is_collapsed = target_collapsed
        self.toggle_tab.set_collapsed(target_collapsed)
        
        target_h = self.controls_widget.sizeHint().height()
        if target_h < 50:
            target_h = 70
        self.controls_widget.setFixedHeight(target_h)

        if target_collapsed:
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
            self.update_timer.stop()
            self._clear_highlights()
            
            start_h = self.content_widget.height()
            if start_h <= 0:
                start_h = target_h
            self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight")
            self._anim.setDuration(320)
            self._anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim.setStartValue(start_h)
            self._anim.setEndValue(0)
            self._anim.valueChanged.connect(lambda _v: self.update_tab_position())
            
            def on_collapse_finished():
                if self.is_collapsed:
                    self.content_widget.hide()
                    self.controls_widget.setMaximumHeight(16777215)
                    self.controls_widget.setMinimumHeight(0)
                self.update_tab_position()
                    
            self._anim.finished.connect(on_collapse_finished)
            self._anim.start()
        else:
            self.content_widget.show()
            self.content_widget.setMaximumHeight(0)
            
            # Immediately restore highlight state for the currently active word
            self.current_word_idx = -1
            self.sync_playback()
            
            self._anim = QPropertyAnimation(self.content_widget, b"maximumHeight")
            self._anim.setDuration(320)
            self._anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim.setStartValue(0)
            self._anim.setEndValue(target_h)
            self._anim.valueChanged.connect(lambda _v: self.update_tab_position())
            
            def on_expand_finished():
                if not self.is_collapsed:
                    self.content_widget.setMaximumHeight(16777215)
                    self.controls_widget.setMaximumHeight(16777215)
                    self.controls_widget.setMinimumHeight(0)
                self.update_tab_position()
                    
            self._anim.finished.connect(on_expand_finished)
            self._anim.start()

    def _show_missing_audio_ui(self, is_loading=False, failed=False):
        if is_loading:
            loading_txt = self.main_window.txt("msg_audio_preview_preparing")
            self.lbl_status.setText(f"<span style='color: #b0b0b0;'>{loading_txt}</span>")
        elif failed:
            failed_txt = self.main_window.txt("msg_audio_preview_failed")
            html = f"<a href='fetch_audio' style='color: #e74c3c; text-decoration: none;'>{failed_txt}</a>"
            self.lbl_status.setText(html)
        else:
            prefix = self.main_window.txt("msg_audio_preview_missing")
            link_txt = self.main_window.txt("msg_audio_preview_get_now")
            html = f"{prefix} <a href='fetch_audio' style='color: #1a7a45; text-decoration: underline;'>{link_txt}</a>"
            self.lbl_status.setText(html)

        self.lbl_status.show()
        self.controls_widget.hide()
        if getattr(self, 'is_collapsed', False):
            self.content_widget.hide()
        else:
            self.content_widget.show()
        self.show()

    def _on_fetch_missing_audio(self, url=None):
        if getattr(self, '_fetching_audio', False):
            return
        self._fetching_audio = True
        self._show_missing_audio_ui(is_loading=True)

        from PySide6.QtCore import QThread, Signal
        import os

        class FetchAudioWorker(QThread):
            finished = Signal(str)

            def __init__(self, main_window):
                super().__init__()
                self.main_window = main_window

            def run(self):
                try:
                    settings = {}
                    snap = getattr(self.main_window, '_transcription_source', None) or {}
                    tl_name = snap.get('timeline_name')
                    if not tl_name and hasattr(self.main_window, 'combo_tl_0') and self.main_window.combo_tl_0:
                        tl_name = self.main_window.combo_tl_0.text()
                    if tl_name:
                        settings['timeline_name'] = tl_name

                    track_indices = snap.get('track_indices')
                    if not track_indices and hasattr(self.main_window, 'get_selected_track_indices'):
                        track_indices = self.main_window.get_selected_track_indices()
                    if track_indices:
                        settings['track_indices'] = track_indices

                    source_files = snap.get('source_files') or []
                    if not source_files:
                        canvas = getattr(self.main_window, 'text_canvas', None)
                        if canvas and getattr(canvas, 'words_data', None):
                            audio_p = canvas.words_data[0].get('meta_audio_path')
                            if audio_p:
                                source_files = [audio_p]
                    if source_files:
                        settings['source_files'] = source_files

                    wav_path = self.main_window.engine.prepare_preview_audio(settings)
                    self.finished.emit(wav_path or "")
                except Exception as e:
                    from osdoc import log_error
                    log_error(f"FetchAudioWorker error: {e}")
                    self.finished.emit("")

        self._fetch_thread = FetchAudioWorker(self.main_window)

        def _on_fetch_done(wav_path):
            self._fetching_audio = False
            if wav_path and os.path.exists(wav_path) and os.path.getsize(wav_path) > 0:
                canvas = getattr(self.main_window, 'text_canvas', None)
                if canvas and getattr(canvas, 'words_data', None):
                    for w in canvas.words_data:
                        w['meta_audio_path'] = wav_path
                self.check_audio_availability()
            else:
                self._show_missing_audio_ui(is_loading=False, failed=True)

        self._fetch_thread.finished.connect(_on_fetch_done)
        self._fetch_thread.start()

    def check_audio_availability(self):
        import os
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or not getattr(canvas, 'words_data', None):
            self.hide()
            return
            
        words = canvas.words_data
        audio_path = words[0].get('meta_audio_path') if words else None
        
        if not audio_path or not os.path.exists(audio_path):
            self._show_missing_audio_ui(is_loading=getattr(self, '_fetching_audio', False))
            return
        
        # If assembled audio is loaded for this same source, don't revert
        if audio_path == self._source_audio_path and self.clean_ops is not None:
            if self.original_audio_path and os.path.exists(self.original_audio_path):
                self.lbl_status.hide()
                self.controls_widget.show()
                if getattr(self, 'is_collapsed', False):
                    self.content_widget.hide()
                else:
                    self.content_widget.show()
                self.show()
                return
            
        self.lbl_status.hide()
        self.controls_widget.show()
        if getattr(self, 'is_collapsed', False):
            self.content_widget.hide()
        else:
            self.content_widget.show()
        self.show()
        
        if self._source_audio_path != audio_path:
            self._source_audio_path = audio_path
            self.original_audio_path = audio_path
            from PySide6.QtCore import QUrl
            self.player.setSource(QUrl.fromLocalFile(audio_path))
            self.clean_ops = None
            self.current_word_idx = -1
            self.last_jumped_ts = -1.0
            self.slider_seek.setValue(0)
            
    def load_assembled_audio(self, assembled_audio_path, clean_ops):
        import os
        from PySide6.QtCore import QUrl
        if os.path.exists(assembled_audio_path):
            self.original_audio_path = assembled_audio_path
            self.clean_ops = clean_ops
            self.player.setSource(QUrl.fromLocalFile(assembled_audio_path))
            self.lbl_status.hide()
            self.controls_widget.show()
            if getattr(self, 'is_collapsed', False):
                self.content_widget.hide()
            else:
                self.content_widget.show()
            self.slider_seek.setValue(0)
            self.current_word_idx = -1
            self.last_jumped_ts = -1.0
            self._clear_highlights()
            self.show()

    def set_position_ms(self, ms, force_word_idx=None):
        import time
        self.player.setPosition(ms)
        self._start_pos_s = ms / 1000.0
        self._real_start_time = time.time()
        
        if force_word_idx is not None and force_word_idx >= 0:
            self._force_highlight_idx = force_word_idx
            self._force_highlight_until = time.time() + 0.3
            
        self.sync_playback()

        
    def _get_audio_t(self):
        from PySide6.QtMultimedia import QMediaPlayer
        import time
        if self.player.playbackState() != QMediaPlayer.PlayingState:
            return self.player.position() / 1000.0
        return getattr(self, '_start_pos_s', 0.0) + (time.time() - getattr(self, '_real_start_time', 0.0)) * self.player.playbackRate()

    def toggle_play(self):
        from PySide6.QtMultimedia import QMediaPlayer
        import time
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self._start_pos_s = self.player.position() / 1000.0
            self._real_start_time = time.time()
            self.player.play()
            self.update_timer.start()
    def _force_system_volume(self, v):
        import os
        if os.name != 'posix': return
        import subprocess, sys, re, threading
        def _task():
            try:
                import time
                time.sleep(0.1) # Wait for QMediaPlayer to establish the sink-input
                script_name = os.path.basename(sys.argv[0])
                out = subprocess.check_output(['pactl', 'list', 'sink-inputs'], text=True)
                current_id = None
                for line in out.splitlines():
                    if 'Sink Input' in line or 'odpływ wejścia' in line:
                        m = re.search(r'(?:#|^)(\d+)\.?', line)
                        if m: current_id = m.group(1)
                    if script_name in line and current_id:
                        subprocess.call(['pactl', 'set-sink-input-volume', current_id, f"{v}%"])
            except Exception:
                pass
        threading.Thread(target=_task, daemon=True).start()

    def on_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
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

    def skip_forward(self):
        curr_t = self._get_audio_t()
        self.set_position_ms(int((curr_t + 3.0) * 1000))

    def skip_backward(self):
        curr_t = self._get_audio_t()
        self.set_position_ms(int(max(0.0, curr_t - 3.0) * 1000))

    def _on_volume_changed(self, v):
        self.audio_output.setVolume(v / 100.0)
        self._force_system_volume(v)
        import os
        from PySide6.QtGui import QPixmap
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        _prod_assets_dir = os.path.join(_src_dir, "layout")
        _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
        _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
        
        if v > 70:
            path = os.path.join(_assets_dir, "volume-max.png")
        elif v >= 40:
            path = os.path.join(_assets_dir, "volume-mid.png")
        else:
            path = os.path.join(_assets_dir, "volume-min.png")
            
        from PySide6.QtCore import Qt
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_vol_icon.setPixmap(pixmap)

    def change_speed(self, text):
        from PySide6.QtMultimedia import QMediaPlayer
        import time
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

    def _on_user_scroll(self, action):
        if not getattr(self, "tgl_centered", None): return
        if self.tgl_centered.isChecked():
            self.tgl_centered.setChecked(False)

    def _on_tgl_centered_changed(self, state):
        if state:
            self._center_current_word()

    def _center_current_word(self):
        if getattr(self, 'current_word_idx', -1) == -1: return
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or not getattr(canvas, 'words_data', None): return
        
        words = canvas.words_data
        if 0 <= self.current_word_idx < len(words):
            w = words[self.current_word_idx]
            if '_rect' in w:
                rect = w['_rect']
                scroll_area = getattr(self.main_window, 'scroll_area', None)
                if scroll_area:
                    scroll_area.ensureVisible(rect.x(), rect.y(), 50, 50)
                    vp_h = scroll_area.viewport().height()
                    vbar = scroll_area.verticalScrollBar()
                    target_y = rect.center().y()
                    new_val = int(target_y - vp_h / 2)
                    vbar.setValue(max(vbar.minimum(), min(new_val, vbar.maximum())))

    def _on_seek_pressed(self):
        self._seek_dragging = True

    def _on_seek_released(self):
        self._seek_dragging = False
        dur = self.player.duration()
        if dur > 0:
            ms = int(self.slider_seek.value() / 1000.0 * dur)
            self.set_position_ms(ms)

    def _on_seek_moved(self, value):
        dur = self.player.duration()
        if dur > 0:
            t = value / 1000.0 * dur / 1000.0
            cur_m, cur_s = divmod(int(t), 60)
            dur_m, dur_s = divmod(int(dur / 1000.0), 60)
            self.lbl_time_curr.setText(f"{cur_m}:{cur_s:02d}")
            self.lbl_time_total.setText(f"{dur_m}:{dur_s:02d}")

    def _audio_to_original_time(self, audio_t):
        if not self.clean_ops: return audio_t
        fps = getattr(self.main_window.resolve_handler, 'fps', 24.0)
        audio_frames = audio_t * fps
        current_audio_f = 0
        for op in self.clean_ops:
            dur = op['e'] - op['s']
            if current_audio_f <= audio_frames < current_audio_f + dur:
                return (op['s'] + (audio_frames - current_audio_f)) / fps
            current_audio_f += dur
        if self.clean_ops: return self.clean_ops[-1]['e'] / fps
        return audio_t

    def _original_to_audio_time(self, orig_t):
        if not self.clean_ops: return orig_t
        fps = getattr(self.main_window.resolve_handler, 'fps', 24.0)
        orig_frames = orig_t * fps
        current_audio_f = 0
        for op in self.clean_ops:
            if orig_frames < op['s']:
                break
            if op['s'] <= orig_frames <= op['e']:
                return (current_audio_f + (orig_frames - op['s'])) / fps
            current_audio_f += (op['e'] - op['s'])
        return current_audio_f / fps

    def sync_playback(self):
        if getattr(self, 'is_collapsed', False):
            self._clear_highlights()
            return
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or not getattr(canvas, 'words_data', None): return
        
        audio_t = max(0.0, self._get_audio_t())
        orig_t = self._audio_to_original_time(audio_t) if self.clean_ops else audio_t
        
        dur = self.player.duration() / 1000.0
        cur_m, cur_s = divmod(int(audio_t), 60)
        dur_m, dur_s = divmod(int(dur), 60)
        self.lbl_time_curr.setText(f"{cur_m}:{cur_s:02d}")
        self.lbl_time_total.setText(f"{dur_m}:{dur_s:02d}")
        
        # Update seek slider position (skip if user is dragging)
        if not self._seek_dragging and dur > 0:
            self.slider_seek.setValue(int(audio_t / dur * 1000))
            
        found_idx = -1
        
        import time
        if time.time() < getattr(self, '_force_highlight_until', 0.0):
            found_idx = getattr(self, '_force_highlight_idx', -1)
        else:
            offset_s = 0.0
            if self.clean_ops and hasattr(self.main_window, 'engine'):
                prefs = self.main_window.engine.load_preferences() or {}
                offset_s = prefs.get('offset', 0.133)
                
            # Lookahead compensates for audio pipeline output latency (~100-200ms)
            # We subtract offset_s because orig_t has offset_s baked into it (the cut point is offset)
            match_t = orig_t + 0.15 - offset_s
            for i in range(len(canvas.words_data)):
                start_t = canvas.words_data[i].get('start', 0)
                if start_t > match_t:
                    found_idx = i - 1
                    break
            else:
                if canvas.words_data:
                    found_idx = len(canvas.words_data) - 1
                
        if found_idx >= 0 and canvas.words_data[found_idx].get('type') == 'silence':
            pass
        elif found_idx != getattr(self, 'current_word_idx', -1):
            self._clear_highlights()
            self.current_word_idx = found_idx
            if found_idx >= 0:
                w = canvas.words_data[found_idx]
                w['_audio_active'] = True
                canvas.update()
                
                start_ts = w.get('start', 0)
                if abs(start_ts - getattr(self, 'last_jumped_ts', 0)) > 0.05:
                    self.last_jumped_ts = start_ts
                    # Playhead jump is purely manual via CTRL+LPM now.
                    
        if getattr(self, "tgl_centered", None) and self.tgl_centered.isChecked():
            self._center_current_word()
                        
    def _clear_highlights(self):
        canvas = getattr(self.main_window, 'text_canvas', None)
        if canvas and canvas.words_data:
            for w in canvas.words_data:
                w.pop('_audio_active', None)
            canvas.update()

# FIX KR-03: Zastąpiono WorkerSignals bezpieczną klasą dziedziczącą po QThread
