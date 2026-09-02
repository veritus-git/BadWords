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
from gui.widgets.buttons import ToggleSwitch, ReloadButton
from .script_panel import wrap_activity_panel


def build_silence_panel(win) -> QFrame:
    """Build the Silence Detection activity panel and bind widgets to main window."""
    p_silence = QWidget()
    l_silence = QVBoxLayout(p_silence)
    l_silence.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_silence.setSpacing(config.S(10))
    
    _sil_input_style = f"""
        QLineEdit {{ background: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a;
        border-radius: {config.S(3)}px; padding: {config.S(2)}px {config.S(6)}px; outline: none;
        font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; }}
        QLineEdit:focus {{ border: 1px solid #1a7a3e; outline: none; }}
    """
    _sil_rst_style = f"""
        QPushButton {{ background: transparent; border: 1px solid #444;
        border-radius: {config.S(3)}px; color: #777; font-size: {config.FS(11)}pt; }}
        QPushButton:hover {{ color: #ccc; border-color: #666; }}
    """

    def _sil_row(label_text, widget, rst_btn):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        row.addWidget(lbl, 1)
        row.addWidget(widget)
        row.addWidget(rst_btn)
        return row

    _sil_prefs = win.engine.load_preferences() or {}

    win.spin_thresh = QLineEdit()
    win.spin_thresh.setText(str(_sil_prefs.get('silence_threshold_db', _sil_prefs.get('ui_spin_thresh', -42.0))))
    win.spin_thresh.setFixedWidth(config.S(68))
    win.spin_thresh.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_thresh.setStyleSheet(_sil_input_style)
    _rst_thresh = ReloadButton(size=30)
    _rst_thresh.clicked.connect(lambda: (
        win.spin_thresh.setText("-42.0"),
        win._save_single_pref('silence_threshold_db', -42.0)
    ))

    win.spin_pad = QLineEdit()
    win.spin_pad.setText(str(_sil_prefs.get('ui_spin_pad', 0.1)))
    win.spin_pad.setFixedWidth(config.S(68))
    win.spin_pad.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_pad.setStyleSheet(_sil_input_style)
    _rst_pad = ReloadButton(size=30)
    _rst_pad.clicked.connect(lambda: (
        win.spin_pad.setText("0.1"),
        win._save_single_pref('ui_spin_pad', 0.1)
    ))

    win.spin_silence_min_dur = QLineEdit()
    win.spin_silence_min_dur.setText(str(_sil_prefs.get('silence_min_dur', 0.2)))
    win.spin_silence_min_dur.setFixedWidth(config.S(68))
    win.spin_silence_min_dur.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_silence_min_dur.setStyleSheet(_sil_input_style)
    win.spin_silence_min_dur.setToolTip(
        "Minimum duration (in seconds) for a gap to be classified as silence. "
        "Lower = more sensitive. Applies to both standalone and post-transcript modes."
    )
    _rst_min = ReloadButton(size=30)
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
    row_silence_cut.addSpacing(config.S(6))
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
    row_silence_mark.addSpacing(config.S(6))
    win.tgl_silence_mark = ToggleSwitch()
    row_silence_mark.addWidget(win.tgl_silence_mark)
    l_silence.addLayout(row_silence_mark)
    
    l_silence.addStretch(1)
    
    win.tgl_silence_cut.toggled.connect(lambda checked: win.tgl_silence_mark.setChecked(False) if checked else None)
    win.tgl_silence_mark.toggled.connect(lambda checked: win.tgl_silence_cut.setChecked(False) if checked else None)

    return wrap_activity_panel(p_silence)
