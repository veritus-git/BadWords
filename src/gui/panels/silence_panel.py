#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: silence_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for audio silence detection live editing parameters,
real-time interactive sliders (Keep Pause, Cut %), and assemble toggles.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame
)
import config
from gui.widgets.labels import QLabel
from gui.widgets.buttons import QPushButton, ToggleSwitch, ReloadButton
from gui.widgets.sliders import JumpSlider
from .script_panel import wrap_activity_panel


def build_silence_panel(win) -> QFrame:
    """Build the Silence Detection activity panel and bind widgets to main window."""
    p_silence = QWidget()
    l_silence = QVBoxLayout(p_silence)
    l_silence.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_silence.setSpacing(config.S(8))
    
    _sil_input_style = f"""
        QLineEdit {{ background: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a;
        border-radius: {config.S(3)}px; padding: {config.S(2)}px {config.S(6)}px; outline: none;
        font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; }}
        QLineEdit:focus {{ border: 1px solid #1a7a3e; outline: none; }}
    """
    _sil_slider_style = f"""
        QSlider::groove:horizontal {{
            height: {config.S(4)}px;
            background: #383838;
            border-radius: {config.S(2)}px;
        }}
        QSlider::sub-page:horizontal {{
            background: #1ed760;
            border-radius: {config.S(2)}px;
        }}
        QSlider::handle:horizontal {{
            background: #ffffff;
            width: {config.S(12)}px;
            margin-top: -{config.S(4)}px;
            margin-bottom: -{config.S(4)}px;
            border-radius: {config.S(6)}px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #1ed760;
            border: 2px solid #ffffff;
        }}
    """

    def _sil_row(label_text, widget, rst_btn):
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        row.addWidget(lbl, 1)
        row.addWidget(widget)
        row.addWidget(rst_btn)
        return row

    _sil_prefs = win.engine.load_preferences() or {}

    def _slider_tuning_field(key, default, lo, hi, scale, decimals, tooltip_key):
        saved_val = float(_sil_prefs.get(key, default))
        saved_val = min(hi, max(lo, saved_val))

        edit = QLineEdit()
        edit.setText(f"{saved_val:.{decimals}f}")
        edit.setFixedWidth(config.S(68))
        edit.setFixedHeight(config.INPUT_HEIGHT)
        edit.setStyleSheet(_sil_input_style)
        edit.setToolTip(win.txt(tooltip_key))

        slider = JumpSlider(Qt.Horizontal)
        slider.setRange(int(round(lo * scale)), int(round(hi * scale)))
        slider.setValue(int(round(saved_val * scale)))
        slider.setStyleSheet(_sil_slider_style)
        slider.setFixedHeight(config.S(18))
        slider.setToolTip(win.txt(tooltip_key))

        _is_syncing = [False]

        def _on_slider(v):
            if _is_syncing[0]:
                return
            _is_syncing[0] = True
            real_val = round(v / float(scale), decimals)
            real_val = min(hi, max(lo, real_val))
            edit.setText(f"{real_val:.{decimals}f}")
            win._save_single_pref(key, real_val)
            if hasattr(win, '_refresh_cut_preview'):
                win._refresh_cut_preview()
            _is_syncing[0] = False

        slider.valueChanged.connect(_on_slider)

        def _on_edit(val=None):
            if _is_syncing[0]:
                return
            _is_syncing[0] = True
            if val is None:
                try:
                    val = float(edit.text().replace(',', '.').strip())
                except ValueError:
                    val = default
            val = min(hi, max(lo, val))
            val = round(val, decimals)
            edit.setText(f"{val:.{decimals}f}")
            slider.setValue(int(round(val * scale)))
            win._save_single_pref(key, val)
            if hasattr(win, '_refresh_cut_preview'):
                win._refresh_cut_preview()
            _is_syncing[0] = False

        edit.editingFinished.connect(lambda: _on_edit())
        rst = ReloadButton(size=30)
        rst.clicked.connect(lambda: _on_edit(default))

        return edit, slider, rst

    def _simple_tuning_field(key, default, lo, hi, decimals, tooltip_text):
        saved_val = float(_sil_prefs.get(key, default))
        saved_val = min(hi, max(lo, saved_val))

        edit = QLineEdit()
        edit.setText(f"{saved_val:.{decimals}f}")
        edit.setFixedWidth(config.S(68))
        edit.setFixedHeight(config.INPUT_HEIGHT)
        edit.setStyleSheet(_sil_input_style)
        edit.setToolTip(tooltip_text)

        def _commit(value=None):
            if value is None:
                try:
                    value = float(edit.text().replace(',', '.').strip())
                except ValueError:
                    value = default
            value = min(hi, max(lo, value))
            value = round(value, decimals)
            edit.setText(f"{value:.{decimals}f}")
            win._save_single_pref(key, value)
            if hasattr(win, '_refresh_cut_preview'):
                win._refresh_cut_preview()

        edit.editingFinished.connect(lambda: _commit())
        rst = ReloadButton(size=30)
        rst.clicked.connect(lambda: _commit(default))
        return edit, rst

    # 1. Keep Pause (silence_keep): default 0.2s with live JumpSlider
    win.spin_silence_keep, win.slider_silence_keep, _rst_keep = _slider_tuning_field(
        'silence_keep', 0.2, 0.0, 1.5, 100, 2, "tt_silence_keep"
    )
    l_silence.addLayout(_sil_row(win.txt("lbl_silence_keep"), win.spin_silence_keep, _rst_keep))
    l_silence.addWidget(win.slider_silence_keep)
    l_silence.addSpacing(config.S(6))

    # 2. Cut Percentage (silence_cut_pct): default 100% with live JumpSlider
    win.spin_silence_cut_pct, win.slider_silence_cut_pct, _rst_pct = _slider_tuning_field(
        'silence_cut_pct', 100.0, 0.0, 100.0, 1, 0, "tt_silence_cut_pct"
    )
    l_silence.addLayout(_sil_row(win.txt("lbl_silence_cut_pct"), win.spin_silence_cut_pct, _rst_pct))
    l_silence.addWidget(win.slider_silence_cut_pct)
    l_silence.addSpacing(config.S(6))

    # 3. Min Silence Duration (silence_min_dur): default 0.2s
    win.spin_silence_min_dur, _rst_min = _simple_tuning_field(
        'silence_min_dur', 0.2, 0.05, 5.0, 2,
        win.txt("tt_min_silence_dur") if hasattr(win, 'txt') else
        "Minimum duration (in seconds) for a gap to be classified as silence."
    )
    l_silence.addLayout(_sil_row(win.txt("lbl_min_silence_dur"), win.spin_silence_min_dur, _rst_min))
    l_silence.addSpacing(config.S(4))

    # 4. Min Kept Clip (silence_min_clip): default 0.0s
    win.spin_silence_min_clip, _rst_clip = _simple_tuning_field(
        'silence_min_clip', 0.0, 0.0, 30.0, 2,
        win.txt("tt_silence_min_clip")
    )
    l_silence.addLayout(_sil_row(win.txt("lbl_silence_min_clip"), win.spin_silence_min_clip, _rst_clip))
    l_silence.addSpacing(config.S(8))

    # 5. Toggles
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
    
    # 6. Live readout of what current settings do (updated dynamically by waveform timeline)
    win.lbl_silence_stats = QLabel("")
    win.lbl_silence_stats.setWordWrap(True)
    win.lbl_silence_stats.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt;")
    l_silence.addWidget(win.lbl_silence_stats)
    
    l_silence.addStretch(1)
    
    def _on_sil_cut_toggled(checked):
        if checked:
            win.tgl_silence_mark.setChecked(False)
        if hasattr(win, '_save_silence_toggles_prefs'):
            win._save_silence_toggles_prefs()

    def _on_sil_mark_toggled(checked):
        if checked:
            win.tgl_silence_cut.setChecked(False)
        if hasattr(win, '_save_silence_toggles_prefs'):
            win._save_silence_toggles_prefs()

    win.tgl_silence_cut.toggled.connect(_on_sil_cut_toggled)
    win.tgl_silence_mark.toggled.connect(_on_sil_mark_toggled)

    return wrap_activity_panel(p_silence)
