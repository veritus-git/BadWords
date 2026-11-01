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
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame, QButtonGroup
)
import config
from gui.widgets.labels import QLabel
from gui.widgets.buttons import QPushButton, ToggleSwitch, ReloadButton
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
        # Name above, field and reset below: fits a narrow panel (like the sliders above)
        col = QVBoxLayout()
        col.setSpacing(config.S(4))
        lbl = QLabel(label_text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: #a0a0a0; font-size: {config.FS(9)}pt; background: transparent;")
        col.addWidget(lbl)
        row = QHBoxLayout()
        row.addWidget(widget, 1)
        row.addWidget(rst_btn)
        col.addLayout(row)
        return col

    _sil_prefs = win.engine.load_preferences() or {}

    win.spin_thresh = QLineEdit()
    win.spin_thresh.setText(str(_sil_prefs.get('silence_threshold_db', _sil_prefs.get('ui_spin_thresh', -42.0))))
    win.spin_thresh.setMinimumWidth(config.S(60))
    win.spin_thresh.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_thresh.setStyleSheet(_sil_input_style)
    _rst_thresh = ReloadButton(size=30)
    _rst_thresh.clicked.connect(lambda: (
        win.spin_thresh.setText("-42.0"),
        win._save_single_pref('silence_threshold_db', -42.0)
    ))

    win.spin_pad = QLineEdit()
    win.spin_pad.setText(str(_sil_prefs.get('ui_spin_pad', 0.1)))
    win.spin_pad.setMinimumWidth(config.S(60))
    win.spin_pad.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_pad.setStyleSheet(_sil_input_style)
    _rst_pad = ReloadButton(size=30)
    _rst_pad.clicked.connect(lambda: (
        win.spin_pad.setText("0.1"),
        win._save_single_pref('ui_spin_pad', 0.1)
    ))

    win.spin_silence_min_dur = QLineEdit()
    win.spin_silence_min_dur.setText(str(_sil_prefs.get('silence_min_dur', 0.2)))
    win.spin_silence_min_dur.setMinimumWidth(config.S(60))
    win.spin_silence_min_dur.setFixedHeight(config.INPUT_HEIGHT)
    win.spin_silence_min_dur.setStyleSheet(_sil_input_style)
    win.spin_silence_min_dur.setToolTip(
        "Minimum duration (in seconds) for a gap to be classified as silence. "
        "Lower = more sensitive. Applies to both standalone and post-transcript modes. "
        "Raising it updates the cuts immediately; lowering it below the value used "
        "during analysis needs a new analysis."
    )
    _rst_min = ReloadButton(size=30)
    _rst_min.clicked.connect(lambda: (
        win.spin_silence_min_dur.setText("0.2"),
        win._save_single_pref('silence_min_dur', 0.2),
        win._refresh_cut_preview()
    ))

    # Live tuning of what Cut does: sliders (double-click the value to reset)
    import re
    from gui.widgets.slider_field import SliderField

    def _tuning_slider(key, label_key, default, lo, hi, step, unit, decimals, tooltip_key):
        try:
            value = float(_sil_prefs.get(key, default))
        except (TypeError, ValueError):
            value = default
        label = re.sub(r"\s*\((%|s)\)\s*$", "", win.txt(label_key))
        s = SliderField(label, min(hi, max(lo, value)), lo, hi, step, default, unit, decimals, win.txt(tooltip_key))
        s.committed.connect(lambda v, k=key: (win._save_single_pref(k, v), win._refresh_cut_preview()))
        return s

    win.spin_silence_cut_pct = _tuning_slider('silence_cut_pct', "lbl_silence_cut_pct", 100.0, 0.0, 100.0, 1.0, "%", 0, "tt_silence_cut_pct")
    win.spin_silence_min_clip = _tuning_slider('silence_min_clip', "lbl_silence_min_clip", 0.0, 0.0, 5.0, 0.1, " s", 1, "tt_silence_min_clip")
    win.spin_silence_keep = _tuning_slider('silence_keep', "lbl_silence_keep", 0.0, 0.0, 1.0, 0.05, " s", 2, "tt_silence_keep")

    def _card():
        card = QFrame()
        card.setObjectName("PanelCard")
        card.setStyleSheet(f"""QFrame#PanelCard {{ background: #1e1e1e; border: 1px solid #2e2e2e;
                               border-radius: {config.S(6)}px; }}""")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))
        lay.setSpacing(config.S(10))
        return card, lay

    # Title, then one card for what happens to pauses, one for how they are detected
    lbl_title = QLabel(win.txt("lbl_pauses"))
    lbl_title.setStyleSheet(f"font-size: {config.FS(12)}pt; font-weight: bold; background: transparent;")
    l_silence.addWidget(lbl_title)
    lbl_sub = QLabel(win.txt("sub_pauses"))
    lbl_sub.setWordWrap(True)
    lbl_sub.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt; background: transparent;")
    l_silence.addWidget(lbl_sub)
    card_mode, l_card_mode = _card()
    l_silence.addWidget(card_mode)

    # One choice for what happens to pauses: Keep / Mark / Cut
    row_pause_mode = QHBoxLayout()
    seg = QHBoxLayout()
    seg.setSpacing(0)
    win.pause_mode_group = QButtonGroup(p_silence)
    win.pause_mode_group.setExclusive(True)
    win.pause_mode_buttons = {}
    _modes = (("keep", "btn_pause_keep"), ("mark", "btn_pause_mark"), ("cut", "btn_pause_cut"))
    for i, (mode, key) in enumerate(_modes):
        btn = QPushButton(win.txt(key))
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(config.INPUT_HEIGHT)
        r_l = config.S(4) if i == 0 else 0
        r_r = config.S(4) if i == len(_modes) - 1 else 0
        btn.setStyleSheet(f"""
            QPushButton {{ background: #2a2a2a; color: #b0b0b0; border: 1px solid #3a3a3a;
                border-top-left-radius: {r_l}px; border-bottom-left-radius: {r_l}px;
                border-top-right-radius: {r_r}px; border-bottom-right-radius: {r_r}px;
                padding: 0 {config.S(10)}px; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; }}
            QPushButton:hover {{ color: #ffffff; }}
            QPushButton:checked {{ background: {config.BTN_BG}; color: #ffffff; border-color: {config.BTN_BG}; font-weight: bold; }}
        """)
        win.pause_mode_group.addButton(btn)
        win.pause_mode_buttons[mode] = btn
        seg.addWidget(btn)
    row_pause_mode.addLayout(seg)
    row_pause_mode.addStretch()
    row_pause_mode.addWidget(win._create_info_icon("tt_pause_mode"))
    l_card_mode.addLayout(row_pause_mode)

    # Live readout of what the current settings do (filled by the waveform preview)
    win.lbl_silence_stats = QLabel("")
    win.lbl_silence_stats.setWordWrap(True)
    win.lbl_silence_stats.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt; background: transparent;")
    l_card_mode.addWidget(win.lbl_silence_stats)
    l_card_mode.addWidget(win.spin_silence_cut_pct)
    l_card_mode.addWidget(win.spin_silence_min_clip)
    l_card_mode.addWidget(win.spin_silence_keep)

    card_detect, l_card_detect = _card()
    lbl_detect = QLabel(win.txt("lbl_pause_detection"))
    lbl_detect.setStyleSheet(f"color: #888888; font-size: {config.FS(8)}pt; font-weight: bold; text-transform: uppercase; background: transparent;")
    l_card_detect.addWidget(lbl_detect)
    l_card_detect.addLayout(_sil_row(win.txt("lbl_threshold_db"), win.spin_thresh, _rst_thresh))
    l_card_detect.addLayout(_sil_row(win.txt("lbl_padding_s"), win.spin_pad, _rst_pad))
    l_card_detect.addLayout(_sil_row(win.txt("lbl_min_silence_dur"), win.spin_silence_min_dur, _rst_min))
    l_silence.addWidget(card_detect)

    switches = QWidget()
    l_switches = QHBoxLayout(switches)
    l_switches.setContentsMargins(0, 0, 0, 0)
    win.tgl_silence_cut = ToggleSwitch()
    win.tgl_silence_mark = ToggleSwitch()
    l_switches.addWidget(win.tgl_silence_cut)
    l_switches.addWidget(win.tgl_silence_mark)
    switches.setVisible(False)
    l_silence.addWidget(switches)
    
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

    def _sync_pause_mode(*_):
        mode = "cut" if win.tgl_silence_cut.isChecked() else ("mark" if win.tgl_silence_mark.isChecked() else "keep")
        btn = win.pause_mode_buttons[mode]
        if not btn.isChecked():
            btn.setChecked(True)

    def _on_pause_mode_clicked(btn):
        mode = next(m for m, b in win.pause_mode_buttons.items() if b is btn)
        if mode == "keep":
            win.tgl_silence_cut.setChecked(False)
            win.tgl_silence_mark.setChecked(False)
        elif mode == "mark":
            win.tgl_silence_mark.setChecked(True)
        else:
            win.tgl_silence_cut.setChecked(True)

    win.tgl_silence_cut.toggled.connect(_on_sil_cut_toggled)
    win.tgl_silence_mark.toggled.connect(_on_sil_mark_toggled)
    win.tgl_silence_cut.toggled.connect(_sync_pause_mode)
    win.tgl_silence_mark.toggled.connect(_sync_pause_mode)
    win.pause_mode_group.buttonClicked.connect(_on_pause_mode_clicked)
    _sync_pause_mode()

    return wrap_activity_panel(p_silence, scroll=True)
