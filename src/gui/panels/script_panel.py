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

from gui.theme import qc

from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFrame, QScrollArea, QLabel
)
from PySide6.QtGui import QColor

import config


def panel_header(layout, title, subtitle=None):
    """Panel title (and a one-line explanation under it), the same in every side panel."""
    lbl = QLabel(title)
    lbl.setStyleSheet(f"font-size: {config.FS(12)}pt; font-weight: bold; background: transparent;")
    layout.addWidget(lbl)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt; background: transparent;")
        layout.addWidget(sub)
    return lbl


def panel_card(spacing=10):
    """A rounded card grouping related controls; returns (frame, its layout)."""
    card = QFrame()
    card.setObjectName("PanelCard")
    card.setStyleSheet(f"""QFrame#PanelCard {{ background: #1e1e1e; border: 1px solid #2e2e2e;
                           border-radius: {config.S(6)}px; }}""")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(config.S(12), config.S(12), config.S(12), config.S(12))
    lay.setSpacing(config.S(spacing))
    return card, lay


def wrap_activity_panel(widget: QWidget, scroll: bool = False) -> QFrame:
    """Wrap any panel widget into a styled ActivityPanel frame container.
    scroll: the content keeps its natural size and scrolls when the window is short
    (instead of being squeezed until labels overlap)."""
    container = QFrame()
    container.setObjectName("ActivityPanel")
    container.setAttribute(Qt.WA_StyledBackground, True)

    container.setStyleSheet(f"""
        QFrame#ActivityPanel {{
            background-color: #212121;
            border-radius: 0px;
            margin: 0px;
            border: none;
        }}
        /* Force all generic children to be transparent so the grey shows through */
        QFrame#ActivityPanel QWidget {{
            background-color: transparent;
        }}
        /* Restore specific background for input fields so they don't blend in */
        QFrame#ActivityPanel QTextEdit,
        QFrame#ActivityPanel QDoubleSpinBox,
        QFrame#ActivityPanel QLineEdit {{
            background-color: #1e1e1e;
            border: 1px solid #3a3a3a;
            color: #ffffff;
            font-family: "{config.UI_FONT_NAME}";
            font-size: {config.FS(9.5)}pt;
        }}
        QFrame#ActivityPanel QPushButton {{
            background-color: #333333;
            border: 1px solid #454545;
            border-radius: {config.S(4)}px;
            padding: {config.S(5)}px;
            color: #d9d9d9;
            font-family: "{config.UI_FONT_NAME}";
            font-size: {config.FS(9.5)}pt;
        }}
        QFrame#ActivityPanel QPushButton:hover {{ background-color: #404040; border-color: #555555; }}
        QFrame#ActivityPanel QPushButton:disabled {{ background-color: #2a2a2a; border-color: #222; color: #555555; }}
    """)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    if scroll:
        area = QScrollArea()
        area.setObjectName("ActivityScroll")
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setStyleSheet("QScrollArea#ActivityScroll { background: transparent; border: none; }")
        area.setWidget(widget)
        layout.addWidget(area)
    else:
        layout.addWidget(widget)
    return container


def build_script_panel(win) -> QFrame:
    """Build the Script Analysis activity panel and bind widgets to main window."""
    p_script_analysis = QWidget()
    l_script_analysis = QVBoxLayout(p_script_analysis)
    l_script_analysis.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_script_analysis.setSpacing(config.S(10))
    panel_header(l_script_analysis, win.txt("lbl_script_title"), win.txt("sub_script"))

    card_script, l_card_script = panel_card(8)
    win.text_script = QTextEdit()
    win.text_script.setAcceptRichText(False)
    win.text_script.setPlaceholderText(win.txt("ph_paste_script_here"))
    win.text_script.setMinimumHeight(config.S(90))
    win.text_script.setStyleSheet(f"""QTextEdit {{ background: #171717; border: 1px solid #333; border-radius: {config.S(4)}px;
        padding: {config.S(4)}px; color: #e0e0e0; font-size: {config.FS(9.5)}pt; }}""")
    l_card_script.addWidget(win.text_script, 1)
    l_script_analysis.addWidget(card_script, 1)

    btn_row_script = QHBoxLayout()
    win.btn_import_script = QPushButton(win.txt("btn_import_script"))
    win.btn_import_script.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_clear_script = QPushButton(win.txt("btn_clear"))
    win.btn_clear_script.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_row_script.addWidget(win.btn_import_script)
    btn_row_script.addWidget(win.btn_clear_script)
    l_card_script.addLayout(btn_row_script)

    # What to do with it: compare (primary), side by side, or find errors without a script
    win.script_actions_card, l_actions = panel_card(8)
    l_script_analysis.addWidget(win.script_actions_card)

    win.btn_analyze_standalone = QPushButton(win.txt("btn_script_errors"))
    win.btn_analyze_standalone.setToolTip(win.txt("tt_script_errors"))
    win.btn_analyze_standalone.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_analyze_standalone.setStyleSheet(f"""
        QPushButton {{ background: transparent; border: none; color: #9a9a9a; text-decoration: underline;
            padding: {config.S(2)}px; font-size: {config.FS(9)}pt; }}
        QPushButton:hover {{ color: #ffffff; }}
    """)

    win.btn_analyze_compare = QPushButton(win.txt("btn_script_compare"))
    win.btn_analyze_compare.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_analyze_compare.setFixedHeight(config.S(35))
    win.btn_analyze_compare.setStyleSheet(f"""
        QPushButton {{ background-color: {config.BTN_BG}; color: white; font-weight: bold; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(10.5)}pt; border: none; border-radius: {config.S(4)}px; padding: {config.S(8)}px; }}
        QPushButton:hover {{ background-color: #1ed760; }}
    """)
    l_actions.addWidget(win.btn_analyze_compare)

    win.btn_side_by_side_compare = QPushButton(win.txt("btn_script_sbs"))
    win.btn_side_by_side_compare.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_side_by_side_compare.setFixedHeight(config.S(32))
    win.btn_side_by_side_compare.setEnabled(False)
    win.btn_side_by_side_compare.setStyleSheet(f"""
        QPushButton {{ background-color: #2d3f35; color: #d9d9d9;
        font-weight: bold; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; border: 1px solid #3d5f4b; border-radius: {config.S(4)}px; padding: {config.S(6)}px; }}
        QPushButton:hover {{ background-color: #36513f; }}
        QPushButton:disabled {{ background-color: #2a2a2a; border-color: #222; color: #555555; }}
    """)
    l_actions.addWidget(win.btn_side_by_side_compare)
    l_actions.addWidget(win.btn_analyze_standalone, 0, Qt.AlignHCenter)
    
    win.btn_exit_sbs_text = QPushButton(win.txt("btn_return_normal"))
    win.btn_exit_sbs_text.setCursor(Qt.CursorShape.PointingHandCursor)
    win.btn_exit_sbs_text.setStyleSheet(f"QPushButton {{ background: transparent; color: #888888; border: none; padding: {config.S(8)}px; font-size: {config.FS(10)}pt; }} QPushButton:hover {{ color: #ffffff; }}")
    win.btn_exit_sbs_text.clicked.connect(win._exit_side_by_side)
    win.btn_exit_sbs_text.hide()
    l_script_analysis.addWidget(win.btn_exit_sbs_text)
    
    win._analyze_color_anim = QVariantAnimation(win)
    win._analyze_color_anim.setDuration(250)
    win._analyze_color_anim.setEasingCurve(QEasingCurve.InOutQuad)

    def update_btn_style(color):
        style = (f"QPushButton {{ background-color: {color.name()}; border: 1px solid #111; border-radius: {config.S(4)}px;"
                 f" color: #fff; font-weight: bold; padding: {config.S(8)}px; }}"
                 f" QPushButton:disabled {{ color: #6a6a6a; }}")
        win.btn_analyze_compare.setStyleSheet(style)
        
    win._analyze_color_anim.valueChanged.connect(update_btn_style)
    
    def update_compare_btn():
        has_text = bool(win.text_script.toPlainText().strip())
        if getattr(win, '_analyze_last_state', None) == has_text:
            return 
        win._analyze_last_state = has_text
        
        win.btn_analyze_compare.setEnabled(has_text)
        win.btn_side_by_side_compare.setEnabled(has_text)
        
        start_color = qc("#2a2a2a") if has_text else qc(config.BTN_BG)
        end_color = qc(config.BTN_BG) if has_text else qc("#2a2a2a")

        win._analyze_color_anim.stop()
        win._analyze_color_anim.setStartValue(start_color)
        win._analyze_color_anim.setEndValue(end_color)
        win._analyze_color_anim.start()
        
    win._update_compare_btn = update_compare_btn
    win.text_script.textChanged.connect(win._update_compare_btn)
    win._update_compare_btn()

    return wrap_activity_panel(p_script_analysis)
