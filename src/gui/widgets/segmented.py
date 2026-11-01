#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: segmented.py
ROLE: GUI Widget
DESCRIPTION:
Small segmented control (e.g. Keep | Mark | Cut): one exclusive choice shown as joined buttons.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup

import config


class SegmentedChoice(QWidget):
    """choices: [(value, label), ...]. Emits changed(value) on user clicks only."""
    changed = Signal(str)

    def __init__(self, choices, current=None, parent=None, compact=False):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons = {}
        pad = config.S(6) if compact else config.S(10)
        fs = config.FS(8.5) if compact else config.FS(9.5)
        h = config.S(20) if compact else config.INPUT_HEIGHT
        for i, (value, label) in enumerate(choices):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(h)
            r_l = config.S(4) if i == 0 else 0
            r_r = config.S(4) if i == len(choices) - 1 else 0
            btn.setStyleSheet(f"""
                QPushButton {{ background: #2a2a2a; color: #b0b0b0; border: 1px solid #3a3a3a;
                    border-top-left-radius: {r_l}px; border-bottom-left-radius: {r_l}px;
                    border-top-right-radius: {r_r}px; border-bottom-right-radius: {r_r}px;
                    padding: 0 {pad}px; font-family: '{config.UI_FONT_NAME}'; font-size: {fs}pt; }}
                QPushButton:hover {{ color: #ffffff; }}
                QPushButton:checked {{ background: {config.BTN_BG}; color: #ffffff; border-color: {config.BTN_BG}; font-weight: bold; }}
                QPushButton:disabled {{ color: #5a5a5a; }}
                QPushButton:checked:disabled {{ background: #34483b; color: #b0b0b0; border-color: #34483b; }}
            """)
            self._group.addButton(btn)
            self.buttons[value] = btn
            lay.addWidget(btn)
        if current in self.buttons:
            self.buttons[current].setChecked(True)
        self._group.buttonClicked.connect(self._on_clicked)

    def _on_clicked(self, btn):
        for value, b in self.buttons.items():
            if b is btn:
                self.changed.emit(value)
                return

    def value(self):
        for value, b in self.buttons.items():
            if b.isChecked():
                return value
        return None

    def set_value(self, value):
        if value in self.buttons and not self.buttons[value].isChecked():
            self.buttons[value].setChecked(True)
