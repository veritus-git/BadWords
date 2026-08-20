#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: script_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Sidebar activity panel for pasting, importing, and comparing script text with audio transcription.
"""

from PySide6.QtCore import Qt, QVariantAnimation
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame
)
from PySide6.QtGui import QColor

import config


def wrap_activity_panel(widget: QWidget) -> QFrame:
    """Wrap any panel widget into a styled ActivityPanel frame container."""
    container = QFrame()
    container.setObjectName("ActivityPanel")
    container.setAttribute(Qt.WA_StyledBackground, True)

    container.setStyleSheet("""
        QFrame#ActivityPanel {
            background-color: #212121;
            border-radius: 0px;
            margin: 0px;
            border: none;
        }
        /* Force all generic children to be transparent so the grey shows through */
        QFrame#ActivityPanel QWidget {
            background-color: transparent;
        }
        /* Restore specific background for input fields so they don't blend in */
        QFrame#ActivityPanel QTextEdit,
        QFrame#ActivityPanel QDoubleSpinBox,
        QFrame#ActivityPanel QLineEdit {
            background-color: #1e1e1e;
            border: 1px solid #3a3a3a;
            color: #ffffff;
        }
        QFrame#ActivityPanel QPushButton {
            background-color: #333333;
            border: 1px solid #454545;
            border-radius: 4px;
            padding: 5px;
            color: #d9d9d9;
        }
        QFrame#ActivityPanel QPushButton:hover { background-color: #404040; border-color: #555555; }
        QFrame#ActivityPanel QPushButton:disabled { background-color: #2a2a2a; border-color: #222; color: #555555; }
    """)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(widget)
    return container


def build_script_panel(win) -> QFrame:
    """Build the Script Analysis activity panel and bind widgets to main window."""
    p_script_analysis = QWidget()
    l_script_analysis = QVBoxLayout(p_script_analysis)
    l_script_analysis.setContentsMargins(15, 15, 15, 15)
    l_script_analysis.setSpacing(10)
    
    win.text_script = QTextEdit()
    win.text_script.setAcceptRichText(False)
    win.text_script.setPlaceholderText(win.txt("ph_paste_script_here"))
    l_script_analysis.addWidget(win.text_script)
    
    btn_row_script = QHBoxLayout()
    win.btn_import_script = QPushButton(win.txt("btn_import_script"))
    win.btn_import_script.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_clear_script = QPushButton(win.txt("btn_clear"))
    win.btn_clear_script.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_row_script.addWidget(win.btn_import_script)
    btn_row_script.addWidget(win.btn_clear_script)
    l_script_analysis.addLayout(btn_row_script)
    
    win.btn_analyze_standalone = QPushButton(win.txt("btn_analyze_standalone"))
    win.btn_analyze_standalone.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_analyze_standalone.setFixedHeight(35)
    win.btn_analyze_standalone.setStyleSheet(
        f"QPushButton {{ background-color: {config.BTN_BG}; border: 1px solid #111; border-radius: 4px; color: #fff; font-weight: bold; padding: 8px; }} "
        f"QPushButton:hover {{ background-color: #1ed760; }}"
    )
    l_script_analysis.addWidget(win.btn_analyze_standalone)

    win.btn_analyze_compare = QPushButton(win.txt("btn_analyze_compare"))
    win.btn_analyze_compare.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_analyze_compare.setFixedHeight(35)
    win.btn_analyze_compare.setStyleSheet(
        f"QPushButton {{ background-color: {config.BTN_BG}; color: white; font-weight: bold; font-size: 12pt; border: none; border-radius: 4px; padding: 10px; }} "
        f"QPushButton:hover {{ background-color: #1ed760; }}"
    )
    l_script_analysis.addWidget(win.btn_analyze_compare)

    win.btn_side_by_side_compare = QPushButton(win.txt("btn_side_by_side_compare"))
    win.btn_side_by_side_compare.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_side_by_side_compare.setFixedHeight(32)
    win.btn_side_by_side_compare.setEnabled(False)
    win.btn_side_by_side_compare.setStyleSheet(
        "QPushButton { background-color: #2d3f35; color: #d9d9d9; "
        "font-weight: bold; border: 1px solid #3d5f4b; border-radius: 4px; padding: 7px; } "
        "QPushButton:hover { background-color: #36513f; } "
        "QPushButton:disabled { background-color: #2a2a2a; border-color: #222; color: #555555; }"
    )
    l_script_analysis.addWidget(win.btn_side_by_side_compare)
    
    win.btn_exit_sbs_text = QPushButton(win.txt("btn_return_normal"))
    win.btn_exit_sbs_text.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_exit_sbs_text.setStyleSheet("QPushButton { background: transparent; color: #888888; border: none; padding: 10px; font-size: 11pt; } QPushButton:hover { color: #ffffff; }")
    win.btn_exit_sbs_text.clicked.connect(win._exit_side_by_side)
    win.btn_exit_sbs_text.hide()
    l_script_analysis.addWidget(win.btn_exit_sbs_text)
    
    win._analyze_color_anim = QVariantAnimation(win)
    win._analyze_color_anim.setDuration(250)

    def update_btn_style(color):
        style = f"QPushButton {{ background-color: {color.name()}; border: 1px solid #111; border-radius: 4px; color: #fff; font-weight: bold; padding: 8px; }}"
        win.btn_analyze_compare.setStyleSheet(style)
        
    win._analyze_color_anim.valueChanged.connect(update_btn_style)
    
    def update_compare_btn():
        has_text = bool(win.text_script.toPlainText().strip())
        if getattr(win, '_analyze_last_state', None) == has_text:
            return 
        win._analyze_last_state = has_text
        
        win.btn_analyze_compare.setEnabled(has_text)
        win.btn_side_by_side_compare.setEnabled(has_text)
        
        start_color = QColor("#2a2a2a") if has_text else QColor(config.BTN_BG)
        end_color = QColor(config.BTN_BG) if has_text else QColor("#2a2a2a")

        win._analyze_color_anim.stop()
        win._analyze_color_anim.setStartValue(start_color)
        win._analyze_color_anim.setEndValue(end_color)
        win._analyze_color_anim.start()
        
    win._update_compare_btn = update_compare_btn
    win.text_script.textChanged.connect(win._update_compare_btn)
    win._update_compare_btn()

    return wrap_activity_panel(p_script_analysis)
