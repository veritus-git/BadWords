#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: silence_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for audio silence detection live editing parameters,
real-time interactive sliders, animated fade states, and assemble toggles.
"""

from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QFrame, QGraphicsOpacityEffect
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

    def _create_separator():
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #383838; margin: 0px; border: none;")
        return div

    _sil_prefs = win.engine.load_preferences() or {}

    # ── 1. Top Section: Switches ─────────────────────────────────────────────
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

    l_silence.addSpacing(config.S(6))

    # ── 2. Parameters Container (fades / grays out when both toggles OFF) ─────
    w_params = QWidget()
    w_params.setStyleSheet("background: transparent;")
    l_params = QVBoxLayout(w_params)
    l_params.setContentsMargins(0, 0, 0, 0)
    l_params.setSpacing(config.S(6))
    win.w_silence_params_container = w_params

    opacity_effect = QGraphicsOpacityEffect(w_params)
    w_params.setGraphicsEffect(opacity_effect)

    win._silence_fade_anim = QVariantAnimation(w_params)
    win._silence_fade_anim.setDuration(250)
    win._silence_fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
    win._silence_fade_anim.valueChanged.connect(lambda val: opacity_effect.setOpacity(val))

    def _param_block(label_text, key, default, lo, hi, scale, decimals, on_change_callback, tooltip_text=""):
        v_box = QVBoxLayout()
        v_box.setContentsMargins(0, 0, 0, 0)
        v_box.setSpacing(config.S(2))

        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: #e0e0e0; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; font-weight: 500;")
        lbl.setWordWrap(True)
        v_box.addWidget(lbl)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(config.S(8))

        saved_val = float(_sil_prefs.get(key, default))
        saved_val = min(hi, max(lo, saved_val))

        edit = QLineEdit()
        edit.setText(f"{saved_val:.{decimals}f}" if decimals > 0 else str(int(round(saved_val))))
        edit.setFixedWidth(config.S(58))
        edit.setFixedHeight(config.INPUT_HEIGHT)
        edit.setStyleSheet(_sil_input_style)
        if tooltip_text:
            edit.setToolTip(tooltip_text)

        slider = JumpSlider(Qt.Horizontal)
        slider.setRange(int(round(lo * scale)), int(round(hi * scale)))
        slider.setValue(int(round(saved_val * scale)))
        slider.setFixedHeight(config.S(16))
        if tooltip_text:
            slider.setToolTip(tooltip_text)

        _is_syncing = [False]

        def _on_slider(v):
            if _is_syncing[0]:
                return
            _is_syncing[0] = True
            real_val = round(v / float(scale), decimals)
            real_val = min(hi, max(lo, real_val))
            edit.setText(f"{real_val:.{decimals}f}" if decimals > 0 else str(int(round(real_val))))
            win._save_single_pref(key, real_val)
            if on_change_callback:
                on_change_callback()
            _is_syncing[0] = False

        slider.valueChanged.connect(_on_slider)
        if on_change_callback:
            slider.sliderReleased.connect(on_change_callback)

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
            edit.setText(f"{val:.{decimals}f}" if decimals > 0 else str(int(round(val))))
            slider.setValue(int(round(val * scale)))
            win._save_single_pref(key, val)
            if on_change_callback:
                on_change_callback()
            _is_syncing[0] = False

        edit.editingFinished.connect(lambda: _on_edit())
        rst = ReloadButton(size=28)
        rst.clicked.connect(lambda: _on_edit(default))

        row.addWidget(slider, 1)
        row.addWidget(edit, 0)
        row.addWidget(rst, 0)
        v_box.addLayout(row)

        return v_box, edit, slider, rst

    # Callback helpers
    def _on_preview_change():
        if hasattr(win, '_refresh_cut_preview'):
            win._refresh_cut_preview()

    # 1. Próg ciszy (dB): -80.0 to -10.0 dB, default -42.0 dB
    # Decoupled from pre-transcription baseline silence_threshold_db.
    vb_thresh, win.spin_thresh, win.slider_thresh, _rst_thresh = _param_block(
        win.txt("lbl_silence_threshold_db"), 'panel_silence_threshold_db', -42.0, -80.0, -10.0, 1.0, 1,
        _on_preview_change,
        win.txt("tt_silence_threshold_db")
    )
    l_params.addLayout(vb_thresh)
    l_params.addSpacing(config.S(2))
    l_params.addWidget(_create_separator())
    l_params.addSpacing(config.S(8))

    # 2. Zostaw przerwę (s): 0.00 to 1.50 s, default 0.20 s
    vb_keep, win.spin_silence_keep, win.slider_silence_keep, _rst_keep = _param_block(
        win.txt("lbl_silence_keep"), 'silence_keep', 0.20, 0.00, 1.50, 100.0, 2,
        _on_preview_change,
        win.txt("tt_silence_keep")
    )
    l_params.addLayout(vb_keep)
    l_params.addSpacing(config.S(2))
    l_params.addWidget(_create_separator())
    l_params.addSpacing(config.S(8))

    # 2. Pauzy do usunięcia (%): 0 to 100%, default 100%
    vb_pct, win.spin_silence_cut_pct, win.slider_silence_cut_pct, _rst_pct = _param_block(
        win.txt("lbl_silence_cut_pct"), 'silence_cut_pct', 100.0, 0.0, 100.0, 1.0, 0,
        _on_preview_change,
        win.txt("tt_silence_cut_pct")
    )
    l_params.addLayout(vb_pct)
    l_params.addSpacing(config.S(2))
    l_params.addWidget(_create_separator())
    l_params.addSpacing(config.S(8))

    # 3. Min. czas trwania ciszy (s): 0.05 to 3.00 s, default 0.20 s
    # Works 100% live in-memory via _on_preview_change on pre-detected silences!
    # Decoupled from pre-transcription baseline silence_min_dur to prevent false inaudibles.
    vb_min_dur, win.spin_silence_min_dur, win.slider_silence_min_dur, _rst_min_dur = _param_block(
        win.txt("lbl_min_silence_dur"), 'panel_silence_min_dur', 0.20, 0.05, 3.00, 100.0, 2,
        _on_preview_change,
        win.txt("tt_min_silence_dur")
    )
    l_params.addLayout(vb_min_dur)
    l_params.addSpacing(config.S(2))
    l_params.addWidget(_create_separator())
    l_params.addSpacing(config.S(8))

    # 4. Min. klip między cięciami (s): 0.00 to 5.00 s, default 0.00 s
    vb_min_clip, win.spin_silence_min_clip, win.slider_silence_min_clip, _rst_min_clip = _param_block(
        win.txt("lbl_silence_min_clip"), 'silence_min_clip', 0.00, 0.00, 5.00, 10.0, 2,
        _on_preview_change,
        win.txt("tt_silence_min_clip")
    )
    l_params.addLayout(vb_min_clip)

    l_silence.addWidget(w_params, 0)

    # 5. Live stats label outside w_params (no nested graphics effect!) with 0.0 <-> 1.0 opacity
    l_silence.addSpacing(config.S(10))
    win.lbl_silence_stats = QLabel("")
    win.lbl_silence_stats.setWordWrap(True)
    win.lbl_silence_stats.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt;")
    l_silence.addWidget(win.lbl_silence_stats)

    stats_opacity = QGraphicsOpacityEffect(win.lbl_silence_stats)
    win.lbl_silence_stats.setGraphicsEffect(stats_opacity)
    win._silence_stats_opacity_effect = stats_opacity

    win._silence_stats_fade_anim = QVariantAnimation(win.lbl_silence_stats)
    win._silence_stats_fade_anim.setDuration(250)
    win._silence_stats_fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
    win._silence_stats_fade_anim.valueChanged.connect(
        lambda val: (stats_opacity.setOpacity(val), win.lbl_silence_stats.repaint())
    )
    win._silence_stats_fade_anim.finished.connect(
        lambda: win.lbl_silence_stats.repaint()
    )

    l_silence.addStretch(1)

    # ── State toggle & fade logic ─────────────────────────────────────────────
    def _update_container_state(animate=True):
        cut_on = win.tgl_silence_cut.isChecked()
        mark_on = win.tgl_silence_mark.isChecked()
        is_active = cut_on or mark_on

        target_params_opacity = 1.0 if is_active else 0.35
        target_stats_opacity = 1.0 if is_active else 0.0
        w_params.setEnabled(is_active)

        if animate:
            win._silence_fade_anim.stop()
            win._silence_fade_anim.setStartValue(opacity_effect.opacity())
            win._silence_fade_anim.setEndValue(target_params_opacity)
            win._silence_fade_anim.start()

            win._silence_stats_fade_anim.stop()
            win._silence_stats_fade_anim.setStartValue(stats_opacity.opacity())
            win._silence_stats_fade_anim.setEndValue(target_stats_opacity)
            win._silence_stats_fade_anim.start()
        else:
            win._silence_fade_anim.stop()
            opacity_effect.setOpacity(target_params_opacity)
            win._silence_stats_fade_anim.stop()
            stats_opacity.setOpacity(target_stats_opacity)
            win.lbl_silence_stats.repaint()

    def _on_sil_cut_toggled(checked):
        if checked:
            win.tgl_silence_mark.setChecked(False)
        if hasattr(win, '_save_silence_toggles_prefs'):
            win._save_silence_toggles_prefs()
        _update_container_state(animate=True)

    def _on_sil_mark_toggled(checked):
        if checked:
            win.tgl_silence_cut.setChecked(False)
        if hasattr(win, '_save_silence_toggles_prefs'):
            win._save_silence_toggles_prefs()
        _update_container_state(animate=True)

    win.tgl_silence_cut.toggled.connect(_on_sil_cut_toggled)
    win.tgl_silence_mark.toggled.connect(_on_sil_mark_toggled)

    # Set initial state without animation
    _update_container_state(animate=False)

    return wrap_activity_panel(p_silence)
