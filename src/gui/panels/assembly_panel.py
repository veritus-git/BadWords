#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: assembly_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for timeline assembly options, inaudible/typo toggles, cut color dynamic list, and auto-cut presets.
"""

import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame
)
from PySide6.QtGui import QIcon

import config
from gui.widgets.labels import QLabel
from gui.widgets.buttons import QPushButton, ToggleSwitch, StarFavoriteButton
from .script_panel import wrap_activity_panel


def build_assembly_panel(win) -> QFrame:
    """Build the Assembly activity panel and bind widgets to main window."""
    p_assembly = QWidget()
    l_assembly = QVBoxLayout(p_assembly)
    l_assembly.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_assembly.setSpacing(config.S(15))
    
    def _pin_btn(fav_id: str):
        btn = StarFavoriteButton(size=18)
        win._pin_buttons[fav_id] = btn
        return btn
    
    # Colours in this edit: what each colour means, how much of it there is, and
    # whether the next Assemble leaves it out. Rows are filled by win._render_color_legend().
    def _card():
        card = QFrame()
        card.setObjectName("PanelCard")
        card.setStyleSheet(f"""QFrame#PanelCard {{ background: #1e1e1e; border: 1px solid #2e2e2e;
                               border-radius: {config.S(6)}px; }}""")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))
        lay.setSpacing(config.S(10))
        return card, lay

    lbl_legend = QLabel(win.txt("legend_title"))
    lbl_legend.setStyleSheet(f"font-size: {config.FS(12)}pt; font-weight: bold; background: transparent;")
    l_assembly.addWidget(lbl_legend)
    card_legend, l_card_legend = _card()
    win.legend_layout = QVBoxLayout()
    win.legend_layout.setSpacing(config.S(10))
    l_card_legend.addLayout(win.legend_layout)
    l_assembly.addWidget(card_legend)
    win._legend_signature = None
    win._render_color_legend({})
    # What the AI found: one row per kind, with its count, its switches and Restore.
    # Placed above the colours: first what was detected, then what happens to each colour.
    lbl_det = QLabel(win.txt("det_title"))
    lbl_det.setStyleSheet(f"font-size: {config.FS(12)}pt; font-weight: bold; background: transparent;")
    card_det, l_card_det = _card()
    l_assembly.insertWidget(0, lbl_det)
    l_assembly.insertWidget(1, card_det)
    win.det_counts = {}
    _small_btn = f"""
        QPushButton {{ background: #2a2a2a; color: #d0d0d0; border: 1px solid #3a3a3a; border-radius: {config.S(4)}px;
                       padding: {config.S(2)}px {config.S(8)}px; font-size: {config.FS(8.5)}pt; }}
        QPushButton:hover {{ color: #ffffff; border-color: #555; }}"""

    def _det_row(kind, title_key):
        box = QVBoxLayout()
        box.setSpacing(config.S(2))
        top = QHBoxLayout()
        top.setSpacing(config.S(6))
        title = QLabel(win.txt(title_key))
        title.setStyleSheet("font-weight: bold; background: transparent;")
        top.addWidget(title)
        top.addStretch()
        count = QLabel("")
        count.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(8.5)}pt; background: transparent;")
        win.det_counts[kind] = count
        box.addLayout(top)
        bottom = QHBoxLayout()
        bottom.setSpacing(config.S(6))
        bottom.addWidget(count)
        bottom.addStretch()
        restore = QPushButton(win.txt("btn_det_restore"))
        restore.setCursor(Qt.PointingHandCursor)
        restore.setToolTip(win.txt("tt_det_restore"))
        restore.setStyleSheet(_small_btn)
        restore.clicked.connect(lambda: win._restore_ai_kind(kind))
        bottom.addWidget(restore)
        box.addLayout(bottom)
        return box, top, bottom

    # Fillers: the auto-filler switch (mirrors the Filler Words panel) and a link to the list
    box, top, bottom = _det_row("fillers", "det_fillers")
    tgl_fill = ToggleSwitch()
    src = getattr(win, 'tgl_auto_filler', None)
    if src is not None:
        tgl_fill.setChecked(src.isChecked())
        tgl_fill.toggled.connect(lambda c: src.setChecked(c) if src.isChecked() != c else None)
        src.toggled.connect(lambda c: tgl_fill.setChecked(c) if tgl_fill.isChecked() != c else None)
    tgl_fill.setToolTip(win.txt("tt_det_fillers"))
    top.addWidget(tgl_fill)
    edit_list = QPushButton(win.txt("btn_det_edit_list"))
    edit_list.setCursor(Qt.PointingHandCursor)
    edit_list.setStyleSheet(_small_btn)
    edit_list.clicked.connect(lambda: win._open_activity("fillers"))
    bottom.insertWidget(2, edit_list)
    l_card_det.addLayout(box)

    # Errors & retakes: run the detector, or restore what it found
    box, top, bottom = _det_row("errors", "det_errors")
    detect = QPushButton(win.txt("btn_det_detect"))
    detect.setCursor(Qt.PointingHandCursor)
    detect.setToolTip(win.txt("tt_det_detect"))
    detect.setStyleSheet(_small_btn)
    detect.clicked.connect(lambda: win._on_analyze_standalone())
    top.addWidget(detect)
    l_card_det.addLayout(box)

    # Repeated words ("I think I think") and restarts: every abandoned copy, as Retake
    box, top, bottom = _det_row("stammers", "det_stammers")
    det_st = QPushButton(win.txt("btn_det_detect"))
    det_st.setCursor(Qt.PointingHandCursor)
    det_st.setToolTip(win.txt("tt_det_stammers"))
    det_st.setStyleSheet(_small_btn)
    det_st.clicked.connect(lambda: win._detect_stammers())
    top.addWidget(det_st)
    l_card_det.addLayout(box)

    # Second speaker: quiet, different voice (usually the interviewer); marked with a custom marker
    box, top, bottom = _det_row("speaker", "det_speaker")
    det_spk = QPushButton(win.txt("btn_det_detect"))
    det_spk.setCursor(Qt.PointingHandCursor)
    det_spk.setToolTip(win.txt("tt_det_speaker"))
    det_spk.setStyleSheet(_small_btn)
    det_spk.clicked.connect(lambda: win._detect_second_speaker())
    top.addWidget(det_spk)
    l_card_det.addLayout(box)

    # Script differences (typos): show or hide
    box, top, bottom = _det_row("typos", "det_typos")
    win.tgl_show_typos = ToggleSwitch()
    win.tgl_show_typos.setChecked(True)
    win.tgl_show_typos.setToolTip(win.txt("lbl_show_detected_typos"))
    win.tgl_show_typos.toggled.connect(lambda c: (win._on_typos_toggled(c), win._save_top_toggles_prefs()))
    top.addWidget(win.tgl_show_typos)
    pin_show_typos = _pin_btn('show_typos')
    top.addWidget(pin_show_typos)
    pin_show_typos.clicked.connect(lambda checked=False, p=pin_show_typos: win._toggle_favorite('show_typos', win.tgl_show_typos, win.txt("tool_show_typos"), p))
    l_card_det.addLayout(box)

    # No voice (inaudible): mark it (brown clips), and whether (...) shows in the text
    box, top, bottom = _det_row("novoice", "det_novoice")
    win.tgl_mark_inaudible = ToggleSwitch()
    win.tgl_mark_inaudible.setToolTip(win.txt("lbl_mark_inaudible_fragments"))
    win.tgl_mark_inaudible.toggled.connect(lambda c: (win._on_mark_inaudible_toggled(c), win._save_top_toggles_prefs()))
    top.addWidget(win.tgl_mark_inaudible)
    pin_mark_inaud = _pin_btn('mark_inaudible')
    top.addWidget(pin_mark_inaud)
    pin_mark_inaud.clicked.connect(lambda checked=False, p=pin_mark_inaud: win._toggle_favorite('mark_inaudible', win.tgl_mark_inaudible, win.txt("tool_mark_inaudible"), p))
    show_row = QHBoxLayout()
    show_row.setSpacing(config.S(6))
    lbl_show = QLabel(win.txt("lbl_show_inaudible_fragments"))
    lbl_show.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(8.5)}pt; background: transparent;")
    show_row.addWidget(lbl_show)
    show_row.addStretch()
    win.tgl_show_inaudible = ToggleSwitch()
    win.tgl_show_inaudible.setChecked(True)
    win.tgl_show_inaudible.toggled.connect(lambda c: (win._on_inaudible_toggled(c), win._save_top_toggles_prefs()))
    show_row.addWidget(win.tgl_show_inaudible)
    pin_show_inaud = _pin_btn('show_inaudible')
    show_row.addWidget(pin_show_inaud)
    pin_show_inaud.clicked.connect(lambda checked=False, p=pin_show_inaud: win._toggle_favorite('show_inaudible', win.tgl_show_inaudible, win.txt("tool_show_inaudible"), p))
    box.addLayout(show_row)
    # Sounds without words: listen to each one, keep or cut it (loud ones are cut by themselves)
    sound_row = QHBoxLayout()
    sound_row.setSpacing(config.S(6))
    review = QPushButton(win.txt("btn_review_sounds"))
    review.setCursor(Qt.PointingHandCursor)
    review.setToolTip(win.txt("tt_review_sounds"))
    review.setStyleSheet(_small_btn)
    review.clicked.connect(lambda: win._review_next_sound())
    sound_row.addWidget(review)
    win.btn_sound_choice = QPushButton(win.txt("btn_sound_cut"))
    win.btn_sound_choice.setCursor(Qt.PointingHandCursor)
    win.btn_sound_choice.setStyleSheet(_small_btn)
    win.btn_sound_choice.setEnabled(False)
    win.btn_sound_choice.clicked.connect(lambda: win._toggle_sound_choice())
    sound_row.addWidget(win.btn_sound_choice)
    sound_row.addStretch()
    box.addLayout(sound_row)
    l_card_det.addLayout(box)

    win.color_cut_buttons = {}
    
    l_colors_container = QVBoxLayout()
    l_colors_container.setSpacing(config.S(10))
    
    div_top = QFrame()
    div_top.setFixedHeight(config.S(1))
    div_top.setStyleSheet("background-color: #383838; margin: 0px; border: none;")
    l_colors_container.addWidget(div_top)
    
    from gui.utils import get_layout_icon_path

    color_idx = 0
    for color_name, color_hex in config.RESOLVE_COLORS_HEX.items():
        row_color = QHBoxLayout()
        row_color.setSpacing(config.S(8))
        
        localized_color_name = win.txt(f"resolve_color_{color_name.lower()}")
        lbl_color = QLabel(win.txt("lbl_cut_color_fmt").format(hex=color_hex, color=localized_color_name))
        row_color.addWidget(lbl_color)
        row_color.addStretch()
        
        pin_c = _pin_btn(f'cut_{color_name.lower()}')
        
        is_unsupported = color_name.lower() in ["tan", "chocolate", "green", "blue"]
        btn_auto = None
        
        if not is_unsupported:
            btn_auto = QPushButton()
            btn_auto.setFixedSize(config.S(24), config.S(24))
            btn_auto.setCursor(Qt.PointingHandCursor)
            btn_auto.setStyleSheet("background: transparent; border: none;")
            btn_auto.setCheckable(True)
            btn_auto.setToolTip(win.txt("tooltip_auto_cut"))
            
            prefs = win.engine.load_preferences() or {}
            auto_cut_colors = prefs.get('auto_cut_colors', [])
            is_checked = color_name in auto_cut_colors
            btn_auto.setChecked(is_checked)
            
            def _update_auto_icon(checked, b=btn_auto):
                icon_name = "auto-marked.png" if checked else "auto-unmarked.png"
                b.setIcon(QIcon(get_layout_icon_path(icon_name)))
                b.setIconSize(QSize(config.S(20), config.S(20)))
                
            _update_auto_icon(is_checked)
            btn_auto.toggled.connect(lambda checked, b=btn_auto, fn=_update_auto_icon: (fn(checked, b), win._save_auto_cut_prefs()))
            win.color_cut_buttons[color_name] = btn_auto
        
        btn_cut_now = QPushButton()
        btn_cut_now.setFixedSize(config.S(24), config.S(24))
        btn_cut_now.setCursor(Qt.PointingHandCursor)
        btn_cut_now.setStyleSheet("background: transparent; border: none;")
        btn_cut_now.setIcon(QIcon(get_layout_icon_path("cut.png")))
        btn_cut_now.setIconSize(QSize(config.S(20), config.S(20)))
        btn_cut_now.setToolTip(win.txt("tooltip_cut_now"))
        btn_cut_now.clicked.connect(lambda _, c=color_name: win._on_cut_now_clicked(c))
        
        row_color.addWidget(btn_cut_now)
        if btn_auto:
            row_color.addWidget(btn_auto)
        row_color.addWidget(pin_c)
        
        l_colors_container.addLayout(row_color)
        
        clean_label = win.txt(f"resolve_color_{color_name.lower()}").replace("<br>", " ")
        pin_c.clicked.connect(lambda _, c=color_name, b=btn_auto, p=pin_c, l=clean_label: win._toggle_favorite(
            f'cut_{c.lower()}', b, l, p
        ))
        
        color_idx += 1
        if color_idx == 3:
            div = QFrame()
            div.setFixedHeight(1)
            div.setStyleSheet("background-color: #383838; margin: 0px; border: none;")
            l_colors_container.addWidget(div)
        
    btn_tools = QPushButton("▸  " + win.txt("lbl_resolve_tools"))
    btn_tools.setCheckable(True)
    btn_tools.setCursor(Qt.PointingHandCursor)
    btn_tools.setToolTip(win.txt("tt_resolve_tools"))
    btn_tools.setStyleSheet(f"""
        QPushButton {{ background: transparent; border: none; color: #9a9a9a; text-align: left;
            padding: {config.S(2)}px 0; font-size: {config.FS(9)}pt; font-weight: bold; }}
        QPushButton:hover {{ color: #ffffff; }}
    """)
    tools_box = QWidget()
    tools_box.setLayout(l_colors_container)
    tools_box.setVisible(False)
    btn_tools.toggled.connect(lambda c: (tools_box.setVisible(c),
                                         btn_tools.setText(("▾  " if c else "▸  ") + win.txt("lbl_resolve_tools"))))
    l_assembly.addWidget(btn_tools)
    l_assembly.addWidget(tools_box)
    l_assembly.addStretch(1)
    
    return wrap_activity_panel(p_assembly, scroll=True)
