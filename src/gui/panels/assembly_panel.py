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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QIcon

import config
from gui.widgets.buttons import ToggleSwitch
from .script_panel import wrap_activity_panel


def build_assembly_panel(win) -> QFrame:
    """Build the Assembly activity panel and bind widgets to main window."""
    p_assembly = QWidget()
    l_assembly = QVBoxLayout(p_assembly)
    l_assembly.setContentsMargins(15, 15, 15, 15)
    l_assembly.setSpacing(15)
    
    def _pin_btn(fav_id: str):
        btn = QPushButton("★")
        btn.setFixedSize(20, 20)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #555555; font-size: 11pt; padding: 0; } "
            "QPushButton:hover { color: #aaaaaa; }"
        )
        win._pin_buttons[fav_id] = btn
        return btn
    
    row_show_inaudible = QHBoxLayout()
    lbl_show_inaud = QLabel(win.txt("lbl_show_inaudible_fragments"))
    lbl_show_inaud.setWordWrap(True)
    row_show_inaudible.addWidget(lbl_show_inaud)
    row_show_inaudible.addStretch()
    win.tgl_show_inaudible = ToggleSwitch()
    win.tgl_show_inaudible.setChecked(True)
    win.tgl_show_inaudible.toggled.connect(lambda c: (win._on_inaudible_toggled(c), win._save_top_toggles_prefs()))
    row_show_inaudible.addWidget(win.tgl_show_inaudible)
    pin_show_inaud = _pin_btn('show_inaudible')
    row_show_inaudible.addWidget(pin_show_inaud)
    l_assembly.addLayout(row_show_inaudible)
    pin_show_inaud.clicked.connect(lambda checked=False, p=pin_show_inaud: win._toggle_favorite('show_inaudible', win.tgl_show_inaudible, win.txt("tool_show_inaudible"), p))
    
    row_mark_inaudible = QHBoxLayout()
    lbl_mark_inaud = QLabel(win.txt("lbl_mark_inaudible_fragments"))
    lbl_mark_inaud.setWordWrap(True)
    row_mark_inaudible.addWidget(lbl_mark_inaud)
    row_mark_inaudible.addStretch()
    win.tgl_mark_inaudible = ToggleSwitch()
    win.tgl_mark_inaudible.toggled.connect(lambda c: (win._on_mark_inaudible_toggled(c), win._save_top_toggles_prefs()))
    row_mark_inaudible.addWidget(win.tgl_mark_inaudible)
    pin_mark_inaud = _pin_btn('mark_inaudible')
    row_mark_inaudible.addWidget(pin_mark_inaud)
    l_assembly.addLayout(row_mark_inaudible)
    pin_mark_inaud.clicked.connect(lambda checked=False, p=pin_mark_inaud: win._toggle_favorite('mark_inaudible', win.tgl_mark_inaudible, win.txt("tool_mark_inaudible"), p))
    
    row_show_typos = QHBoxLayout()
    lbl_show_typos = QLabel(win.txt("lbl_show_detected_typos"))
    lbl_show_typos.setWordWrap(True)
    row_show_typos.addWidget(lbl_show_typos)
    row_show_typos.addStretch()
    win.tgl_show_typos = ToggleSwitch()
    win.tgl_show_typos.setChecked(True)
    win.tgl_show_typos.toggled.connect(lambda c: (win._on_typos_toggled(c), win._save_top_toggles_prefs()))
    row_show_typos.addWidget(win.tgl_show_typos)
    pin_show_typos = _pin_btn('show_typos')
    row_show_typos.addWidget(pin_show_typos)
    l_assembly.addLayout(row_show_typos)
    pin_show_typos.clicked.connect(lambda checked=False, p=pin_show_typos: win._toggle_favorite('show_typos', win.tgl_show_typos, win.txt("tool_show_typos"), p))
    
    win.color_cut_buttons = {}
    
    l_colors_container = QVBoxLayout()
    l_colors_container.setSpacing(10)
    
    div_top = QFrame()
    div_top.setFixedHeight(1)
    div_top.setStyleSheet("background-color: #383838; margin: 0px; border: none;")
    l_colors_container.addWidget(div_top)
    
    _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _prod_assets_dir = os.path.join(_src_dir, "layout")
    _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
    _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
    
    color_idx = 0
    for color_name, color_hex in config.RESOLVE_COLORS_HEX.items():
        row_color = QHBoxLayout()
        
        localized_color_name = win.txt(f"resolve_color_{color_name.lower()}")
        lbl_color = QLabel(win.txt("lbl_cut_color_fmt").format(hex=color_hex, color=localized_color_name))
        row_color.addWidget(lbl_color)
        row_color.addStretch()
        
        pin_c = _pin_btn(f'cut_{color_name.lower()}')
        
        is_unsupported = color_name.lower() in ["tan", "chocolate", "green", "blue"]
        btn_auto = None
        
        if not is_unsupported:
            btn_auto = QPushButton()
            btn_auto.setFixedSize(24, 24)
            btn_auto.setCursor(Qt.PointingHandCursor)
            btn_auto.setStyleSheet("background: transparent; border: none;")
            btn_auto.setCheckable(True)
            btn_auto.setToolTip(win.txt("tooltip_auto_cut"))
            
            prefs = win.engine.load_preferences() or {}
            auto_cut_colors = prefs.get('auto_cut_colors', [])
            is_checked = color_name in auto_cut_colors
            btn_auto.setChecked(is_checked)
            
            def _update_auto_icon(checked, b=btn_auto, ad=_assets_dir):
                icon_name = "auto-marked.png" if checked else "auto-unmarked.png"
                b.setIcon(QIcon(os.path.join(ad, icon_name)))
                b.setIconSize(QSize(20, 20))
                
            _update_auto_icon(is_checked)
            btn_auto.toggled.connect(lambda checked, b=btn_auto, fn=_update_auto_icon: (fn(checked, b), win._save_auto_cut_prefs()))
            win.color_cut_buttons[color_name] = btn_auto
        
        btn_cut_now = QPushButton()
        btn_cut_now.setFixedSize(24, 24)
        btn_cut_now.setCursor(Qt.PointingHandCursor)
        btn_cut_now.setStyleSheet("background: transparent; border: none;")
        btn_cut_now.setIcon(QIcon(os.path.join(_assets_dir, "cut.png")))
        btn_cut_now.setIconSize(QSize(20, 20))
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
        
    l_assembly.addLayout(l_colors_container)
    l_assembly.addStretch(1)
    
    return wrap_activity_panel(p_assembly)
