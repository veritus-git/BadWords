#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: silence_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for audio silence detection parameters and toggles.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame
)
import config
from gui.widgets.buttons import ToggleSwitch
from .script_panel import wrap_activity_panel


def build_silence_panel(win) -> QFrame:
    """Build the Silence Detection activity panel and bind widgets to main window."""
    p_silence = QWidget()
    l_silence = QVBoxLayout(p_silence)
    l_silence.setContentsMargins(15, 15, 15, 15)
    l_silence.setSpacing(10)
    
    _sil_input_style = (
        "QLineEdit { background: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; "
        "border-radius: 3px; padding: 2px 6px; outline: none; } "
        "QLineEdit:focus { border: 1px solid #1a7a3e; outline: none; }"
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

    _sil_prefs = win.engine.load_preferences() or {}

    win.spin_thresh = QLineEdit()
    win.spin_thresh.setText(str(_sil_prefs.get('silence_threshold_db', _sil_prefs.get('ui_spin_thresh', -42.0))))
    win.spin_thresh.setFixedWidth(68)
    win.spin_thresh.setStyleSheet(_sil_input_style)
    _rst_thresh = QPushButton("↺")
    _rst_thresh.setFixedSize(22, 22)
    _rst_thresh.setCursor(Qt.PointingHandCursor)
    _rst_thresh.setStyleSheet(_sil_rst_style)
    _rst_thresh.clicked.connect(lambda: (
        win.spin_thresh.setText("-42.0"),
        win._save_single_pref('silence_threshold_db', -42.0)
    ))

    win.spin_pad = QLineEdit()
    win.spin_pad.setText(str(_sil_prefs.get('ui_spin_pad', 0.05)))
    win.spin_pad.setFixedWidth(68)
    win.spin_pad.setStyleSheet(_sil_input_style)
    _rst_pad = QPushButton("↺")
    _rst_pad.setFixedSize(22, 22)
    _rst_pad.setCursor(Qt.PointingHandCursor)
    _rst_pad.setStyleSheet(_sil_rst_style)
    _rst_pad.clicked.connect(lambda: (
        win.spin_pad.setText("0.05"),
        win._save_single_pref('ui_spin_pad', 0.05)
    ))

    win.spin_silence_min_dur = QLineEdit()
    win.spin_silence_min_dur.setText(str(_sil_prefs.get('silence_min_dur', 0.2)))
    win.spin_silence_min_dur.setFixedWidth(68)
    win.spin_silence_min_dur.setStyleSheet(_sil_input_style)
    win.spin_silence_min_dur.setToolTip(
        "Minimum duration (in seconds) for a gap to be classified as silence. "
        "Lower = more sensitive. Applies to both standalone and post-transcript modes."
    )
    _rst_min = QPushButton("↺")
    _rst_min.setFixedSize(22, 22)
    _rst_min.setCursor(Qt.PointingHandCursor)
    _rst_min.setStyleSheet(_sil_rst_style)
    _rst_min.clicked.connect(lambda: (
        win.spin_silence_min_dur.setText("0.2"),
        win._save_single_pref('silence_min_dur', 0.2)
    ))

    l_silence.addLayout(_sil_row(win.txt("lbl_threshold_db"), win.spin_thresh, _rst_thresh))
    l_silence.addLayout(_sil_row(win.txt("lbl_padding_s"), win.spin_pad, _rst_pad))
    l_silence.addLayout(_sil_row(win.txt("lbl_min_silence_dur"), win.spin_silence_min_dur, _rst_min))

    row_silence_cut = QHBoxLayout()
    lbl_cut = QLabel(win.txt("lbl_detect_and_cut_silence"))
    lbl_cut.setWordWrap(True)
    row_silence_cut.addWidget(lbl_cut)
    row_silence_cut.addStretch()
    info_silence_cut = win._create_info_icon("tt_detect_and_cut_silence")
    row_silence_cut.addWidget(info_silence_cut)
    row_silence_cut.addSpacing(6)
    win.tgl_silence_cut = ToggleSwitch()
    row_silence_cut.addWidget(win.tgl_silence_cut)
    l_silence.addLayout(row_silence_cut)
    
    row_silence_mark = QHBoxLayout()
    lbl_mark = QLabel(win.txt("lbl_detect_and_mark_silence"))
    lbl_mark.setWordWrap(True)
    row_silence_mark.addWidget(lbl_mark)
    row_silence_mark.addStretch()
    info_silence_mark = win._create_info_icon("tt_detect_and_mark_silence")
    row_silence_mark.addWidget(info_silence_mark)
    row_silence_mark.addSpacing(6)
    win.tgl_silence_mark = ToggleSwitch()
    row_silence_mark.addWidget(win.tgl_silence_mark)
    l_silence.addLayout(row_silence_mark)
    
    l_silence.addStretch(1)
    
    win.tgl_silence_cut.toggled.connect(lambda checked: win.tgl_silence_mark.setChecked(False) if checked else None)
    win.tgl_silence_mark.toggled.connect(lambda checked: win.tgl_silence_cut.setChecked(False) if checked else None)

    return wrap_activity_panel(p_silence)
