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
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QGraphicsOpacityEffect
)
import config
from gui.widgets.progress_bar import LiquidProgressBar


def build_processing_view(win) -> QWidget:
    """Build Page 1 of the main stack: Processing / Analysis Progress screen."""
    page = QWidget()
    page.setObjectName("page_processing")
    page.setStyleSheet(f"QWidget#page_processing {{ background-color: {config.BG_COLOR}; }}")
    
    layout = QVBoxLayout(page)
    layout.setContentsMargins(config.S(24), config.S(16), config.S(24), config.S(16))
    layout.setSpacing(0)
    layout.addStretch(1)
    
    win.lbl_processing_status = QLabel(win.txt("status_whisper_init", "Initializing transcription..."), page)
    win.lbl_processing_status.setAlignment(Qt.AlignCenter)
    win.lbl_processing_status.setWordWrap(True)
    win.lbl_processing_status.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    win.lbl_processing_status.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: {config.FS_PX(13)}px;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
    )
    layout.addWidget(win.lbl_processing_status)
    layout.addSpacing(config.S(15))
    
    win.bar_processing = LiquidProgressBar(page)
    win.bar_processing.setMinimumWidth(config.S(180))
    win.bar_processing.setMaximumWidth(config.S(420))
    bar_row = QHBoxLayout()
    bar_row.setContentsMargins(0, 0, 0, 0)
    bar_row.addStretch(1)
    bar_row.addWidget(win.bar_processing, 10)
    bar_row.addStretch(1)
    layout.addLayout(bar_row)

    layout.addSpacing(config.S(20))
    win.lbl_first_run_hint = QLabel("", page)
    win.lbl_first_run_hint.setAlignment(Qt.AlignCenter)
    win.lbl_first_run_hint.setWordWrap(True)
    win.lbl_first_run_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    win.lbl_first_run_hint.setStyleSheet(
        f"color: #666666; font-size: {config.FS_PX(10)}px; font-style: italic;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0 {config.S(20)}px;"
    )
    
    win._hint_opacity = QGraphicsOpacityEffect(win.lbl_first_run_hint)
    win._hint_opacity.setOpacity(0.0)
    win.lbl_first_run_hint.setGraphicsEffect(win._hint_opacity)
    win.lbl_first_run_hint.hide()
    layout.addWidget(win.lbl_first_run_hint)
    layout.addStretch(1)

    return page
