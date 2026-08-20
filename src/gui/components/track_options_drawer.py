#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: track_options_drawer.py
ROLE: Module
DESCRIPTION:
Provides core functionality for this component.
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

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import QModelIndex
from .mixins import FramelessWindowMixin, _BaseDialog
from ..utils import _app_icon, _txt


class TrackSquareCheckbox(QWidget):
    toggled = Signal(bool)

    def __init__(self, text, is_checked=True, parent=None):
        super().__init__(parent)
        self.is_checked = is_checked
        self.text_label = text
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(8)

        self.box = QLabel()
        self.box.setFixedSize(15, 15)
        self.box.setAlignment(Qt.AlignCenter)

        self.lbl = QLabel(text)
        self.lbl.setStyleSheet("color: #d4d4d4; font-size: 9.5pt; font-family: Inter, sans-serif; background: transparent; border: none;")

        lay.addWidget(self.box)
        lay.addWidget(self.lbl)
        lay.addStretch()

        self.update_ui()

    def update_ui(self):
        if self.is_checked:
            self.box.setText("✔")
            self.box.setStyleSheet("""
                background-color: #111111;
                border: 1px solid #1a7a3e;
                color: #1a7a3e;
                font-weight: bold;
                font-size: 11px;
                border-radius: 2px;
            """)
        else:
            self.box.setText("")
            self.box.setStyleSheet("""
                background-color: #111111;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
            """)

    def setChecked(self, checked):
        self.is_checked = bool(checked)
        self.update_ui()

    def isChecked(self):
        return self.is_checked

    def mousePressEvent(self, event):
        self.is_checked = not self.is_checked
        self.update_ui()
        self.toggled.emit(self.is_checked)
        super().mousePressEvent(event)









class _FlowListWidget(QWidget):
    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)
        if getattr(self, '_bypass_min_height', False):
            return
        if self.layout() and hasattr(self.layout(), 'heightForWidth'):
            h = self.layout().heightForWidth(self.width())
            if self.minimumHeight() != h:
                self.setMinimumHeight(h)


class TrackOptionsDrawer(QWidget):
    def __init__(self, parent_gui, engine, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFrame, QGridLayout
        from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve

        self.parent_gui = parent_gui
        self.engine = engine
        self.is_expanded = False
        self._anim = None
        self._block_signals = False

        self.setMaximumHeight(0)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("TrackOptionsScroll")
        self.scroll_area.setStyleSheet("""
            QScrollArea#TrackOptionsScroll {
                background-color: #0f2d1e;
                border: 1px solid #11703c;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QScrollArea#TrackOptionsScroll > QWidget > QWidget {
                background: transparent;
            }
        """)
        main_layout.addWidget(self.scroll_area, 1)

        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("TrackOptionsInnerFrame")
        self.inner_frame.setStyleSheet("""
            QFrame#TrackOptionsInnerFrame {
                background: transparent;
                border: none;
            }
            QFrame#TrackOptionsInnerFrame QWidget {
                border: none;
                background: transparent;
            }
            QFrame#TrackOptionsInnerFrame QLabel {
                border: none;
                background: transparent;
            }
        """)
        self.scroll_area.setWidget(self.inner_frame)
        self.scroll_area.setAlignment(Qt.AlignBottom)

        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setSizeConstraint(QVBoxLayout.SetMinAndMaxSize)
        inner_layout.setAlignment(Qt.AlignBottom)
        inner_layout.setContentsMargins(10, 6, 10, 8)
        inner_layout.setSpacing(4)

        def make_section_header(title_text):
            w = QWidget()
            lay = QHBoxLayout(w)
            lay.setContentsMargins(0, 4, 0, 2)
            lay.setSpacing(6)
            lbl = QLabel(title_text)
            lbl.setStyleSheet("font-size: 8.5pt; color: #288a50; font-weight: bold; text-transform: uppercase; border: none; background: transparent;")
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("background-color: #1a5433; max-height: 1px; border: none;")
            lay.addWidget(lbl)
            lay.addWidget(line, 1)
            return w

        # Audio section header
        inner_layout.addWidget(make_section_header(self.parent_gui.txt('dlg_audio_tracks')))

        self.tgl_a_all = ToggleSwitch()
        self.tgl_a_tr = ToggleSwitch()
        self.tgl_a_cust = ToggleSwitch()

        def make_toggle_row(lbl_text, tgl):
            w = QWidget()
            w.setFixedHeight(26)
            l = QHBoxLayout(w)
            l.setContentsMargins(2, 0, 2, 0)
            lbl = MarqueeLabel(lbl_text)
            l.addWidget(lbl, 1)
            l.addWidget(tgl)
            return w

        inner_layout.addWidget(make_toggle_row(self.parent_gui.txt("dlg_all_tracks"), self.tgl_a_all))

        src = getattr(self.parent_gui, '_transcription_source', None) or {}
        tr_indices = src.get('track_indices', [])
        tr_label_text = self.parent_gui.txt("dlg_transcription_tracks")
        if tr_indices:
            tr_label_text += f" (A{', A'.join(str(i) for i in tr_indices)})"
        self.w_a_tr = make_toggle_row(tr_label_text, self.tgl_a_tr)
        inner_layout.addWidget(self.w_a_tr)

        inner_layout.addWidget(make_toggle_row(self.parent_gui.txt("dlg_custom_selection"), self.tgl_a_cust))

        # Query project audio & video tracks
        audio_tracks, video_tracks = self._get_project_tracks()

        self.w_a_cust_list = _FlowListWidget()
        self.w_a_cust_list.setMaximumHeight(0)
        self.w_a_cust_list.setStyleSheet("background: transparent; border: none;")
        
        grid_a = FlowLayout(self.w_a_cust_list, margin=4, hSpacing=14, vSpacing=4)
        self.a_track_checkboxes = {}

        for i, (idx, tname) in enumerate(audio_tracks):
            cb = TrackSquareCheckbox(f"A{idx}", is_checked=True)
            cb.toggled.connect(lambda chk, item_idx=idx: self._on_a_cb_toggled(item_idx, chk))
            grid_a.addWidget(cb)
            self.a_track_checkboxes[idx] = cb
        inner_layout.addWidget(self.w_a_cust_list)

        inner_layout.addSpacing(2)

        # Video section header
        inner_layout.addWidget(make_section_header(self.parent_gui.txt('dlg_video_tracks')))

        self.tgl_v_all = ToggleSwitch()
        self.tgl_v_none = ToggleSwitch()
        self.tgl_v_cust = ToggleSwitch()

        inner_layout.addWidget(make_toggle_row(self.parent_gui.txt("dlg_all_tracks"), self.tgl_v_all))
        inner_layout.addWidget(make_toggle_row("No tracks", self.tgl_v_none))
        inner_layout.addWidget(make_toggle_row(self.parent_gui.txt("dlg_custom_selection"), self.tgl_v_cust))

        self.w_v_cust_list = _FlowListWidget()
        self.w_v_cust_list.setMaximumHeight(0)
        self.w_v_cust_list.setStyleSheet("background: transparent; border: none;")
        
        grid_v = FlowLayout(self.w_v_cust_list, margin=4, hSpacing=14, vSpacing=4)
        self.v_track_checkboxes = {}

        for i, (idx, tname) in enumerate(video_tracks):
            cb = TrackSquareCheckbox(f"V{idx}", is_checked=True)
            cb.toggled.connect(lambda chk, item_idx=idx: self._on_v_cb_toggled(item_idx, chk))
            grid_v.addWidget(cb)
            self.v_track_checkboxes[idx] = cb
        inner_layout.addWidget(self.w_v_cust_list)

        self.tgl_a_all.toggled.connect(lambda c: self._update_a_radios('all', c))
        self.tgl_a_tr.toggled.connect(lambda c: self._update_a_radios('tr', c))
        self.tgl_a_cust.toggled.connect(lambda c: self._update_a_radios('cust', c))

        self.tgl_v_all.toggled.connect(lambda c: self._update_v_radios('all', c))
        self.tgl_v_none.toggled.connect(lambda c: self._update_v_radios('none', c))
        self.tgl_v_cust.toggled.connect(lambda c: self._update_v_radios('cust', c))

        self.load_config()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        if not self.is_expanded:
            return QSize(self.width(), 0)
        if getattr(self, '_is_animating', False):
            return QSize(self.width(), self.maximumHeight())
        return QSize(self.width(), self.inner_frame.sizeHint().height() + 2)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.load_config()
        self._animate_to_size()

    def _animate_to_size(self):
        if getattr(self, '_block_signals', False):
            return
            
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup

        a_cust_visible = self.tgl_a_cust.isChecked()
        v_cust_visible = self.tgl_v_cust.isChecked()

        a_cust_start = self.w_a_cust_list.height()
        v_cust_start = self.w_v_cust_list.height()
        drawer_start = self.height()

        a_cust_target = self.w_a_cust_list.layout().sizeHint().height() if a_cust_visible else 0
        v_cust_target = self.w_v_cust_list.layout().sizeHint().height() if v_cust_visible else 0

        # Temporarily apply target heights to measure drawer target
        self.w_a_cust_list._bypass_min_height = True
        self.w_v_cust_list._bypass_min_height = True
        self.w_a_cust_list.setMinimumHeight(0)
        self.w_v_cust_list.setMinimumHeight(0)
        
        self.w_a_cust_list.setMaximumHeight(a_cust_target)
        self.w_v_cust_list.setMaximumHeight(v_cust_target)
        self.inner_frame.layout().activate()
        drawer_target = self.inner_frame.sizeHint().height() + 2 if self.is_expanded else 0
        
        # Restore starting heights
        self.w_a_cust_list.setMaximumHeight(a_cust_start)
        self.w_v_cust_list.setMaximumHeight(v_cust_start)

        if getattr(self, '_anim_group', None) and self._anim_group.state() == QPropertyAnimation.Running:
            self._anim_group.stop()

        self._anim_group = QParallelAnimationGroup(self)
        
        def _update_overlay():
            if hasattr(self.parent_gui, 'p_main'):
                self.parent_gui.p_main.resizeEvent(None)

        if drawer_start != drawer_target:
            anim_drawer_max = QPropertyAnimation(self, b"maximumHeight", self)
            anim_drawer_max.setDuration(350)
            anim_drawer_max.setStartValue(drawer_start)
            anim_drawer_max.setEndValue(drawer_target)
            anim_drawer_max.setEasingCurve(QEasingCurve.InOutCubic)
            anim_drawer_max.valueChanged.connect(lambda _: _update_overlay())
            self._anim_group.addAnimation(anim_drawer_max)

            anim_drawer_min = QPropertyAnimation(self, b"minimumHeight", self)
            anim_drawer_min.setDuration(350)
            anim_drawer_min.setStartValue(drawer_start)
            anim_drawer_min.setEndValue(drawer_target)
            anim_drawer_min.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim_group.addAnimation(anim_drawer_min)

        if a_cust_start != a_cust_target:
            anim_a_max = QPropertyAnimation(self.w_a_cust_list, b"maximumHeight", self)
            anim_a_max.setDuration(350)
            anim_a_max.setStartValue(a_cust_start)
            anim_a_max.setEndValue(a_cust_target)
            anim_a_max.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim_group.addAnimation(anim_a_max)

        if v_cust_start != v_cust_target:
            anim_v_max = QPropertyAnimation(self.w_v_cust_list, b"maximumHeight", self)
            anim_v_max.setDuration(350)
            anim_v_max.setStartValue(v_cust_start)
            anim_v_max.setEndValue(v_cust_target)
            anim_v_max.setEasingCurve(QEasingCurve.InOutCubic)
            self._anim_group.addAnimation(anim_v_max)

        self._is_animating = True
        self._anim_group.start()
        
        def _on_finish():
            self._is_animating = False
            if self.is_expanded:
                self.setMaximumHeight(16777215)
                self.setMinimumHeight(0)
            if a_cust_visible:
                self.w_a_cust_list._bypass_min_height = False
                self.w_a_cust_list.setMaximumHeight(16777215)
                self.w_a_cust_list.resizeEvent(None)
            if v_cust_visible:
                self.w_v_cust_list._bypass_min_height = False
                self.w_v_cust_list.setMaximumHeight(16777215)
                self.w_v_cust_list.resizeEvent(None)
            _update_overlay()
            
        self._anim_group.finished.connect(_on_finish)

    def load_config(self):
        self._block_signals = True
        try:
            src = getattr(self.parent_gui, '_transcription_source', None) or {}
            conf = src.get('assembly_track_config') or {}
            amode = conf.get('audio_mode', 'all')
            vmode = conf.get('video_mode', 'all')

            self.tgl_a_all.setChecked(amode == 'all', animated=False)
            self.tgl_a_tr.setChecked(amode == 'tr', animated=False)
            self.tgl_a_cust.setChecked(amode == 'cust', animated=False)

            self.tgl_v_all.setChecked(vmode == 'all', animated=False)
            self.tgl_v_cust.setChecked(vmode == 'cust', animated=False)

            saved_a_custom = conf.get('audio_custom', [])
            for i, cb in self.a_track_checkboxes.items():
                if saved_a_custom:
                    cb.setChecked(i in saved_a_custom)
                else:
                    cb.setChecked(True)

            saved_v_custom = conf.get('video_custom', [])
            for i, cb in self.v_track_checkboxes.items():
                if saved_v_custom:
                    cb.setChecked(i in saved_v_custom)
                else:
                    cb.setChecked(True)

            if amode == 'cust':
                self.w_a_cust_list.setMaximumHeight(16777215)
            else:
                self.w_a_cust_list.setMaximumHeight(0)
                
            if vmode == 'cust':
                self.w_v_cust_list.setMaximumHeight(16777215)
            else:
                self.w_v_cust_list.setMaximumHeight(0)
        finally:
            self._block_signals = False

    def save_config(self):
        if getattr(self, '_block_signals', False):
            return
        amode = 'all'
        if self.tgl_a_tr.isChecked(): amode = 'tr'
        elif self.tgl_a_cust.isChecked(): amode = 'cust'

        vmode = 'all'
        if self.tgl_v_none.isChecked(): vmode = 'none'
        elif self.tgl_v_cust.isChecked(): vmode = 'cust'

        a_custom = [i for i, cb in getattr(self, 'a_track_checkboxes', {}).items() if cb.isChecked()]
        v_custom = [i for i, cb in getattr(self, 'v_track_checkboxes', {}).items() if cb.isChecked()]

        res = {
            'audio_mode': amode,
            'audio_custom': a_custom,
            'video_mode': vmode,
            'video_custom': v_custom
        }
        src = getattr(self.parent_gui, '_transcription_source', None)
        if isinstance(src, dict):
            src['assembly_track_config'] = res

    def _get_project_tracks(self):
        audio_tracks = []
        video_tracks = []

        rh = getattr(self.engine, 'resolve_handler', None)
        target_tl = None
        if rh and rh.project:
            src = getattr(self.parent_gui, '_transcription_source', None) or {}
            tl_name = src.get('timeline_name')
            if tl_name:
                try:
                    cnt = rh.project.GetTimelineCount()
                    for i in range(1, cnt + 1):
                        tl = rh.project.GetTimelineByIndex(i)
                        if tl and tl.GetName() == tl_name:
                            target_tl = tl
                            break
                except Exception:
                    pass
            if not target_tl and rh.timeline:
                target_tl = rh.timeline

        if target_tl:
            try:
                ac = target_tl.GetTrackCount("audio")
                _get_a_name = getattr(target_tl, "GetTrackName", None)
                for i in range(1, ac + 1):
                    tname = ""
                    if callable(_get_a_name):
                        try: tname = _get_a_name("audio", i)
                        except Exception: pass
                    if not tname: tname = f"Audio {i}"
                    audio_tracks.append((i, tname))
            except Exception: pass

            try:
                vc = target_tl.GetTrackCount("video")
                _get_v_name = getattr(target_tl, "GetTrackName", None)
                for i in range(1, vc + 1):
                    tname = ""
                    if callable(_get_v_name):
                        try: tname = _get_v_name("video", i)
                        except Exception: pass
                    if not tname: tname = f"Video {i}"
                    video_tracks.append((i, tname))
            except Exception: pass

        if not audio_tracks:
            max_a = 4
            src = getattr(self.parent_gui, '_transcription_source', None) or {}
            tr_indices = src.get('track_indices', [])
            if tr_indices:
                max_a = max(max_a, max(tr_indices))
            for i in range(1, max_a + 1):
                audio_tracks.append((i, f"Audio {i}"))

        if not video_tracks:
            for i in range(1, 5):
                video_tracks.append((i, f"Video {i}"))

        return audio_tracks, video_tracks

    def _update_a_radios(self, src, checked):
        if getattr(self, '_block_signals', False):
            return
        if not checked:
            if not (self.tgl_a_all.isChecked() or self.tgl_a_tr.isChecked() or self.tgl_a_cust.isChecked()):
                self.tgl_a_all.setChecked(True)
                return
        else:
            self._block_signals = True
            try:
                if src != 'all': self.tgl_a_all.setChecked(False)
                if src != 'tr': self.tgl_a_tr.setChecked(False)
                if src != 'cust': self.tgl_a_cust.setChecked(False)
            finally:
                self._block_signals = False

        self._animate_to_size()
        self.save_config()

    def _update_v_radios(self, src, checked):
        if getattr(self, '_block_signals', False):
            return
        if not checked:
            if not (self.tgl_v_all.isChecked() or self.tgl_v_none.isChecked() or self.tgl_v_cust.isChecked()):
                self.tgl_v_all.setChecked(True)
                return
        else:
            self._block_signals = True
            try:
                if src != 'all': self.tgl_v_all.setChecked(False)
                if src != 'none': self.tgl_v_none.setChecked(False)
                if src != 'cust': self.tgl_v_cust.setChecked(False)
            finally:
                self._block_signals = False

        self._animate_to_size()
        self.save_config()

    def _on_a_cb_toggled(self, idx, checked):
        if getattr(self, '_block_signals', False):
            return
        if not checked:
            any_checked = any(cb.isChecked() for cb in self.a_track_checkboxes.values())
            if not any_checked:
                self.a_track_checkboxes[idx].setChecked(True)
                return
        self.save_config()

    def _on_v_cb_toggled(self, idx, checked):
        if getattr(self, '_block_signals', False):
            return
        if not checked:
            any_checked = any(cb.isChecked() for cb in self.v_track_checkboxes.values())
            if not any_checked:
                self.v_track_checkboxes[idx].setChecked(True)
                return
        self.save_config()


