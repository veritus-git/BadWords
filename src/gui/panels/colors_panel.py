#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: colors_panel.py
ROLE: GUI Activity Panel
DESCRIPTION:
Dedicated sidebar activity panel for "Colors in this edit" (legend of colors present
in the current project/timeline, duration breakdown, and direct remove checkboxes).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame
)

import config
from gui.widgets.labels import QLabel
from .script_panel import wrap_activity_panel


def build_colors_panel(win) -> QFrame:
    """Build the dedicated Colors & Selection activity panel."""
    p_colors = QWidget()
    l_colors = QVBoxLayout(p_colors)
    l_colors.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))
    l_colors.setSpacing(config.S(10))

    header = QWidget()
    header.setObjectName("PanelHeaderWidget")
    win.header_legend = header
    h_layout = QVBoxLayout(header)
    h_layout.setContentsMargins(0, 0, 0, 0)
    h_layout.setSpacing(config.S(10))

    # Header title
    lbl_title = QLabel(win.txt("legend_title"))
    lbl_title.setStyleSheet(f"font-weight: bold; font-size: {config.FS(11)}pt; color: #ffffff;")
    win.lbl_legend_title = lbl_title
    h_layout.addWidget(lbl_title)

    # Subtitle / Hint
    win.lbl_legend_hint = QLabel(win.txt("legend_description", "Overview of colors and markers in this edit. Check 'Remove' to cut all segments of that color during Assemble."))
    win.lbl_legend_hint.setWordWrap(True)
    win.lbl_legend_hint.setStyleSheet(f"color: #888888; font-size: {config.FS(9.5)}pt; line-height: 1.35;")
    win.lbl_legend_hint.setVisible(False)
    h_layout.addWidget(win.lbl_legend_hint)

    # Divider
    win.div_legend = QFrame()
    win.div_legend.setFixedHeight(config.S(1))
    win.div_legend.setStyleSheet("background-color: #383838; margin-top: 6px; margin-bottom: 8px; border: none;")
    win.div_legend.setVisible(False)
    h_layout.addWidget(win.div_legend)

    l_colors.addWidget(header)

    # Initial visibility based on user setting
    prefs = getattr(win, 'prefs', {}) or {}
    show_headers = bool(prefs.get('show_panel_headers', True))
    header.setVisible(show_headers)
    lbl_title.setVisible(show_headers)

    # Legend list container (populated dynamically by win._render_color_legend())
    win.legend_layout = QVBoxLayout()
    win.legend_layout.setSpacing(config.S(10))
    l_colors.addLayout(win.legend_layout)

    # Reset signature and render initial empty state
    win._legend_signature = None
    win._render_color_legend({})

    l_colors.addStretch(1)

    return wrap_activity_panel(p_colors)
