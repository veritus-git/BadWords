#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: processing_view.py
ROLE: GUI View
DESCRIPTION:
Processing progress screen with status updates, liquid progress bar, and first-run model download hint.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSizePolicy, QGraphicsOpacityEffect
)
import config
from gui.widgets.progress_bar import LiquidProgressBar


def build_processing_view(win) -> QWidget:
    """Build Page 1 of the main stack: Processing / Analysis Progress screen."""
    page = QWidget()
    page.setObjectName("page_processing")
    page.setStyleSheet(f"QWidget#page_processing {{ background-color: {config.BG_COLOR}; }}")
    
    layout = QVBoxLayout(page)
    layout.setAlignment(Qt.AlignCenter)
    
    win.lbl_processing_status = QLabel(win.txt("lbl_initializing"), page)
    win.lbl_processing_status.setAlignment(Qt.AlignCenter)
    win.lbl_processing_status.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 13pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
    )
    layout.addWidget(win.lbl_processing_status)
    layout.addSpacing(15)
    
    win.bar_processing = LiquidProgressBar(page)
    win.bar_processing.setFixedWidth(400)
    layout.addWidget(win.bar_processing, 0, Qt.AlignCenter)

    layout.addSpacing(20)
    win.lbl_first_run_hint = QLabel("", page)
    win.lbl_first_run_hint.setAlignment(Qt.AlignCenter)
    win.lbl_first_run_hint.setWordWrap(False)
    win.lbl_first_run_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    win.lbl_first_run_hint.setStyleSheet(
        f"color: #666666; font-size: 10pt; font-style: italic;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0 20px;"
    )
    
    win._hint_opacity = QGraphicsOpacityEffect(win.lbl_first_run_hint)
    win._hint_opacity.setOpacity(0.0)
    win.lbl_first_run_hint.setGraphicsEffect(win._hint_opacity)
    win.lbl_first_run_hint.hide()
    layout.addWidget(win.lbl_first_run_hint, 0, Qt.AlignCenter)

    return page
