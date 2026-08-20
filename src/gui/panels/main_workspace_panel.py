#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: main_workspace_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Primary sidebar workspace panel for markers, duration stats, favorites, and timeline assemble trigger.
"""

import os
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QIcon

from gui.widgets.layouts import MainPanelWidget
from gui.widgets.buttons import AssembleSplitButton
from gui.components.track_options_drawer import TrackOptionsDrawer
from .script_panel import wrap_activity_panel


def build_main_workspace_panel(win) -> QFrame:
    """Build the Main Workspace activity panel and bind widgets to main window."""
    p_main = MainPanelWidget()
    l_main = QVBoxLayout(p_main.layer1)
    l_main.setContentsMargins(15, 15, 15, 15)
    l_main.setSpacing(10)
    
    # Top Section (Markers)
    row_marking_title = QHBoxLayout()
    row_marking_title.addWidget(QLabel(win.txt("lbl_marking_mode")))
    row_marking_title.addStretch()
    win.btn_clear_transcript = QPushButton()
    win.btn_clear_transcript.setFixedSize(26, 26)
    win.btn_clear_transcript.setToolTip("")
    win.btn_clear_transcript.setCursor(Qt.CursorShape.PointingHandCursor)
    
    _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _prod_assets_dir = os.path.join(_src_dir, "layout")
    _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
    _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
    
    win.btn_clear_transcript.setIcon(QIcon(os.path.join(_assets_dir, "clean.png")))
    win.btn_clear_transcript.setIconSize(QSize(18, 18))
    win.btn_clear_transcript.setStyleSheet(
        "QPushButton { background: transparent; border: none; padding: 2px; } "
        "QPushButton:hover { background-color: rgba(255, 255, 255, 10%); border-radius: 4px; }"
    )
    win.btn_clear_transcript.clicked.connect(win._on_clear_transcript)
    row_marking_title.addWidget(win.btn_clear_transcript)
    l_main.addLayout(row_marking_title)
    
    win.markers_layout = QVBoxLayout()
    win.markers_layout.setSpacing(4)
    l_main.addLayout(win.markers_layout)
    
    win.btn_add_custom_marker = QPushButton(win.txt("lbl_add_custom_marker"))
    win.btn_add_custom_marker.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_add_custom_marker.setStyleSheet(
        "QPushButton { background: transparent; color: #808080; text-decoration: underline; border: none; text-align: left; padding: 5px; } "
        "QPushButton:hover { color: #ffffff; }"
    )
    win.btn_add_custom_marker.clicked.connect(win._on_add_custom_marker)
    l_main.addWidget(win.btn_add_custom_marker)
    
    l_main.addStretch(1)
    
    l_layer2 = QVBoxLayout(p_main.layer2)
    l_layer2.setContentsMargins(15, 10, 15, 15)
    l_layer2.setSpacing(10)
    l_layer2.setAlignment(Qt.AlignBottom)
    
    win.lbl_analysis_duration = QLabel("")
    win.lbl_analysis_duration.setStyleSheet("color: #a0a0a0; font-size: 9pt; font-style: italic;")
    win.lbl_analysis_duration.setAlignment(Qt.AlignCenter)
    win.lbl_analysis_duration.setVisible(False)
    l_layer2.addWidget(win.lbl_analysis_duration)
    
    win.lbl_pinned_favorites = QLabel(win.txt("lbl_pinned_favorites"))
    win.lbl_pinned_favorites.setStyleSheet("color: #888888; font-size: 8pt; font-weight: bold; text-transform: uppercase;")
    win.lbl_pinned_favorites.setVisible(False)
    l_layer2.addWidget(win.lbl_pinned_favorites)
    
    win.layout_favorites = QVBoxLayout()
    win.layout_favorites.setSpacing(10)
    l_layer2.addLayout(win.layout_favorites)
    
    layout_assemble_group = QVBoxLayout()
    layout_assemble_group.setContentsMargins(0, 0, 0, 0)
    layout_assemble_group.setSpacing(0)

    win.btn_assemble = AssembleSplitButton(win.txt("btn_assemble"), win)
    layout_assemble_group.addWidget(win.btn_assemble)

    win.w_track_options = TrackOptionsDrawer(win, win.engine)
    layout_assemble_group.addWidget(win.w_track_options)
    win.btn_assemble.toggleDrawerClicked.connect(lambda: [win.w_track_options.toggle_expand(), p_main.resizeEvent(None)])

    l_layer2.addLayout(layout_assemble_group)
    
    win._build_marker_radio_buttons()
    win.p_main = p_main
    
    return wrap_activity_panel(p_main)
