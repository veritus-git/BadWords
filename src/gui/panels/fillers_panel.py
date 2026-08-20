#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: fillers_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for inline filler words editing, word count, and automatic marking.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFrame
)
import config
from gui.widgets.buttons import ToggleSwitch
from .script_panel import wrap_activity_panel


def build_fillers_panel(win) -> QFrame:
    """Build the Filler Words activity panel and bind widgets to main window."""
    p_fillers = QWidget()
    l_fillers = QVBoxLayout(p_fillers)
    l_fillers.setContentsMargins(15, 15, 15, 15)
    l_fillers.setSpacing(10)

    prefs = win.engine.load_preferences() or {}
    fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
    
    win.txt_fillers = QTextEdit()
    win.txt_fillers.setAcceptRichText(False)
    win.txt_fillers.setStyleSheet(
        "background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; border-radius: 4px; padding: 4px;"
    )
    win.txt_fillers.setText(", ".join(fillers))
    l_fillers.addWidget(win.txt_fillers)
    
    filler_tools_layout = QHBoxLayout()
    filler_tools_layout.setContentsMargins(0, 2, 0, 0)
    
    win.lbl_filler_count = QLabel(win.txt("lbl_words"))
    win.lbl_filler_count.setStyleSheet("color: #888888; font-size: 9pt;")
    filler_tools_layout.addWidget(win.lbl_filler_count)
    filler_tools_layout.addStretch()
    
    win.btn_reset_fillers = QPushButton("↺")
    win.btn_reset_fillers.setFixedSize(24, 24)
    win.btn_reset_fillers.setCursor(Qt.PointingHandCursor)
    win.btn_reset_fillers.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 3px; color: #888;")
    win.btn_reset_fillers.clicked.connect(win._on_reset_inline_fillers)
    filler_tools_layout.addWidget(win.btn_reset_fillers)
    
    win.btn_save_fillers = QPushButton(win.txt("btn_save"))
    win.btn_save_fillers.setCursor(Qt.PointingHandCursor)
    win.btn_save_fillers.setStyleSheet(
        f"background-color: {config.BTN_GHOST_BG}; color: {config.FG_COLOR}; border-radius: 4px; font-weight: bold; padding: 4px 10px;"
    )
    win.btn_save_fillers.clicked.connect(win._on_save_inline_fillers)
    filler_tools_layout.addWidget(win.btn_save_fillers)
    l_fillers.addLayout(filler_tools_layout)
    
    win.txt_fillers.textChanged.connect(win._on_fillers_text_changed)
    win._on_fillers_text_changed()
    
    row_auto_filler = QHBoxLayout()
    row_auto_filler.addWidget(QLabel(win.txt("lbl_mark_filler_words_automat")))
    row_auto_filler.addStretch()
    info_auto_filler = win._create_info_icon("tt_mark_filler_words")
    row_auto_filler.addWidget(info_auto_filler)
    row_auto_filler.addSpacing(6)
    win.tgl_auto_filler = ToggleSwitch()
    win.tgl_auto_filler.setChecked(True)
    row_auto_filler.addWidget(win.tgl_auto_filler)
    l_fillers.addLayout(row_auto_filler)
    
    l_fillers.addStretch(1)
    
    return wrap_activity_panel(p_fillers)
