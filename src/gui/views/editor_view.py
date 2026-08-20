#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: editor_view.py
ROLE: GUI View
DESCRIPTION:
Primary transcript editing view with scrollable TranscriptionCanvas, side-by-side loading overlay, and audio preview scrubber.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame, QStackedWidget
)
import config
from gui.components.transcription_canvas import TranscriptionCanvas
from gui.components.audio_preview import AudioPreviewWidget
from gui.widgets.progress_bar import LiquidProgressBar


def build_editor_view(win) -> QWidget:
    """Build Page 2 of the main stack: Interactive Transcript Editor screen."""
    page = QWidget()
    page.setObjectName("page_editor")
    page.setStyleSheet(f"QWidget#page_editor {{ background-color: {config.BG_COLOR}; }}")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    win.scroll_area = QScrollArea(page)
    win.scroll_area.setWidgetResizable(True)
    win.scroll_area.setFrameShape(QFrame.NoFrame)
    win.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
    win.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {config.BG_COLOR}; border: none; }}")
    
    win.text_canvas = TranscriptionCanvas(main_window=win)
    win.scroll_area.setWidget(win.text_canvas)

    normal_editor_page = QWidget()
    normal_editor_layout = QVBoxLayout(normal_editor_page)
    normal_editor_layout.setContentsMargins(0, 0, 0, 0)
    normal_editor_layout.setSpacing(0)
    normal_editor_layout.addWidget(win.scroll_area)

    win.sbs_loading_page = QWidget()
    win.sbs_loading_page.setStyleSheet(f"background-color: {config.BG_COLOR};")
    ol_layout = QVBoxLayout(win.sbs_loading_page)
    ol_layout.setAlignment(Qt.AlignCenter)
    
    lbl = QLabel(win.txt("lbl_just_a_second"))
    lbl.setStyleSheet(f"color: {config.NOTE_COL}; font-size: 13pt; font-family: '{config.UI_FONT_NAME}'; background: transparent;")
    lbl.setAlignment(Qt.AlignCenter)
    ol_layout.addWidget(lbl)
    
    ol_layout.addSpacing(15)
    
    win.sbs_loading_bar = LiquidProgressBar(win.sbs_loading_page)
    win.sbs_loading_bar.setFixedWidth(400)
    ol_layout.addWidget(win.sbs_loading_bar, 0, Qt.AlignCenter)

    win.editor_view_stack = QStackedWidget(page)
    win.editor_view_stack.setStyleSheet("background: transparent;")
    win.editor_view_stack.addWidget(normal_editor_page)
    win.editor_view_stack.addWidget(win.sbs_loading_page)
    layout.addWidget(win.editor_view_stack)
    
    win.audio_preview = AudioPreviewWidget(page, win)
    layout.addWidget(win.audio_preview)
    
    return page
