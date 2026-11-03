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
from .script_panel import wrap_activity_panel, create_panel_header


class DynamicAssemblyWidget(QWidget):
    """Activity panel container for Assembly that dynamically reduces spacings when compressed vertically."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.l_assembly = None
        self.l_switches = None
        self.l_colors = None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_spacings()

    def adjust_spacings(self):
        h = self.height()
        if h <= 0:
            return
        # If plenty of vertical space (>= 740px), keep generous original spacing (15px / 14px / 8px).
        # When compressed / smaller window, dynamically reduce spacing down to 3px so items don't overflow.
        if h >= 740:
            s_main = config.S(15)
            s_switch = config.S(14)
            s_color = config.S(8)
        elif h >= 600:
            ratio = (h - 600) / 140.0
            s_main = int(config.S(8) + ratio * (config.S(15) - config.S(8)))
            s_switch = int(config.S(6) + ratio * (config.S(14) - config.S(6)))
            s_color = int(config.S(5) + ratio * (config.S(8) - config.S(5)))
        else:
            ratio = max(0.0, (h - 400) / 200.0)
            s_main = int(config.S(4) + ratio * (config.S(8) - config.S(4)))
            s_switch = int(config.S(3) + ratio * (config.S(6) - config.S(3)))
            s_color = int(config.S(3) + ratio * (config.S(5) - config.S(3)))

        if self.l_assembly:
            self.l_assembly.setSpacing(s_main)
        if self.l_switches:
            self.l_switches.setSpacing(s_switch)
        if self.l_colors:
            self.l_colors.setSpacing(s_color)


def build_assembly_panel(win) -> QFrame:
    """Build the Assembly activity panel and bind widgets to main window."""
    p_assembly = DynamicAssemblyWidget()
    l_assembly = QVBoxLayout(p_assembly)
    l_assembly.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_assembly.setSpacing(config.S(15))
    p_assembly.l_assembly = l_assembly

    header = create_panel_header(
        win,
        "panel_assembly_title",
        "panel_assembly_desc",
        "Assembly Options",
        "Configure ripple-cut rules, inaudible speech handling, color cut presets, and timeline creation."
    )
    l_assembly.addWidget(header)
    
    def _pin_btn(fav_id: str):
        btn = StarFavoriteButton(size=18)
        win._pin_buttons[fav_id] = btn
        return btn
    
    # ── Top Toggles Container (Dynamic Spacing) ──
    l_switches = QVBoxLayout()
    l_switches.setContentsMargins(0, 0, 0, 0)
    l_switches.setSpacing(config.S(14))
    p_assembly.l_switches = l_switches

    row_show_inaudible = QHBoxLayout()
    row_show_inaudible.setSpacing(config.S(8))
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
    l_switches.addLayout(row_show_inaudible)
    pin_show_inaud.clicked.connect(lambda checked=False, p=pin_show_inaud: win._toggle_favorite('show_inaudible', win.tgl_show_inaudible, win.txt("tool_show_inaudible"), p))
    
    row_mark_inaudible = QHBoxLayout()
    row_mark_inaudible.setSpacing(config.S(8))
    lbl_mark_inaud = QLabel(win.txt("lbl_mark_inaudible_fragments"))
    lbl_mark_inaud.setWordWrap(True)
    row_mark_inaudible.addWidget(lbl_mark_inaud)
    row_mark_inaudible.addStretch()
    win.tgl_mark_inaudible = ToggleSwitch()
    win.tgl_mark_inaudible.toggled.connect(lambda c: (win._on_mark_inaudible_toggled(c), win._save_top_toggles_prefs()))
    row_mark_inaudible.addWidget(win.tgl_mark_inaudible)
    pin_mark_inaud = _pin_btn('mark_inaudible')
    row_mark_inaudible.addWidget(pin_mark_inaud)
    l_switches.addLayout(row_mark_inaudible)
    pin_mark_inaud.clicked.connect(lambda checked=False, p=pin_mark_inaud: win._toggle_favorite('mark_inaudible', win.tgl_mark_inaudible, win.txt("tool_mark_inaudible"), p))
    
    row_show_typos = QHBoxLayout()
    row_show_typos.setSpacing(config.S(8))
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
    l_switches.addLayout(row_show_typos)
    pin_show_typos.clicked.connect(lambda checked=False, p=pin_show_typos: win._toggle_favorite('show_typos', win.tgl_show_typos, win.txt("tool_show_typos"), p))

    l_assembly.addLayout(l_switches)
    
    win.color_cut_buttons = {}
    
    l_colors_container = QVBoxLayout()
    l_colors_container.setSpacing(config.S(8))
    p_assembly.l_colors = l_colors_container
    
    div_top = QFrame()
    div_top.setFixedHeight(config.S(1))
    div_top.setStyleSheet("background-color: #383838; margin-top: 4px; margin-bottom: 2px; border: none;")
    l_colors_container.addWidget(div_top)
    
    from gui.utils import get_layout_icon_path

    # Reserved colors: Chocolate, Tan, Green, Blue are reserved by BadWords/Resolve defaults.
    # They ONLY have the scissors icon (no auto-cut assemble toggle) and must be at the very bottom.
    RESERVED_COLORS = ["Chocolate", "Tan", "Green", "Blue"]
    reserved_set = {c.lower() for c in RESERVED_COLORS}

    all_colors = list(config.RESOLVE_COLORS_HEX.items())
    standard_colors = [(name, hex_val) for name, hex_val in all_colors if name.lower() not in reserved_set]
    reserved_colors = []
    for r_name in RESERVED_COLORS:
        for name, hex_val in all_colors:
            if name.lower() == r_name.lower():
                reserved_colors.append((name, hex_val))
                break

    def _render_color_item(color_name: str, color_hex: str, is_scissors_only: bool):
        row_color = QHBoxLayout()
        row_color.setSpacing(config.S(8))
        
        localized_color_name = win.txt(f"resolve_color_{color_name.lower()}")
        lbl_color = QLabel(win.txt("lbl_cut_color_fmt").format(hex=color_hex, color=localized_color_name))
        row_color.addWidget(lbl_color)
        row_color.addStretch()
        
        pin_c = _pin_btn(f'cut_{color_name.lower()}')
        btn_auto = None
        
        if not is_scissors_only:
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
        
        target_fav = btn_auto if btn_auto is not None else btn_cut_now
        clean_label = win.txt(f"resolve_color_{color_name.lower()}").replace("<br>", " ")
        pin_c.clicked.connect(lambda _, c=color_name, b=target_fav, p=pin_c, l=clean_label: win._toggle_favorite(
            f'cut_{c.lower()}', b, l, p
        ))

    # 1. Standard editable colors (Violet, Navy, Olive first with divider, then others)
    for idx, (color_name, color_hex) in enumerate(standard_colors):
        _render_color_item(color_name, color_hex, is_scissors_only=False)
        if idx == 2:
            div = QFrame()
            div.setFixedHeight(config.S(1))
            div.setStyleSheet("background-color: #383838; margin: 2px 0px; border: none;")
            l_colors_container.addWidget(div)

    # 2. Divider before reserved colors at the bottom
    div_reserved = QFrame()
    div_reserved.setFixedHeight(config.S(1))
    div_reserved.setStyleSheet("background-color: #383838; margin-top: 4px; margin-bottom: 2px; border: none;")
    l_colors_container.addWidget(div_reserved)

    # 3. Reserved colors at the very bottom (Chocolate, Tan, Green, Blue) — scissors only!
    for color_name, color_hex in reserved_colors:
        _render_color_item(color_name, color_hex, is_scissors_only=True)
        
    l_assembly.addLayout(l_colors_container)
    l_assembly.addStretch(1)
    
    p_assembly.adjust_spacings()

    return wrap_activity_panel(p_assembly)
