#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: language_selector.py
ROLE: GUI Widget
DESCRIPTION:
Widget for selecting application and transcription language.
"""

from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtMultimedia import *
import config
from i18n import get_trans
import sys
import os

# Aliases for original standard classes we override
_QPushButton = QPushButton
_QLabel = QLabel
_QRadioButton = QRadioButton

class _LangPickerDialog(QDialog):
    """
    Lightweight language-selection popup (replaces the Tkinter ScrollableMenu).
    Shows all UI languages sorteed alphabetically; emits the selected code.
    Rebuilt as a proper PySide6 dialog — a full ScrollableMenu Port is Stage 2+.
    """
    lang_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFixedWidth(180)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.MENU_BG};
                border: 1px solid #1a1a1a;
            }}
            QListWidget {{
                background-color: {config.MENU_BG};
                color: {config.MENU_FG};
                font-family: {config.UI_FONT_NAME};
                font-size: 11pt;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 5px 8px;
            }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover, QListWidget::item:selected {{
                background-color: #4a4e56;
                color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: {config.MENU_BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {config.SCROLL_FG};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.SCROLL_ACTIVE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._list)

        # Populate sorted language list
        entries = sorted(
            [(data.get("name", code.upper()), code) for code, data in config.TRANS.items()],
            key=lambda x: x[0]
        )
        for name, code in entries:
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.UserRole, code)
            self._list.addItem(item)

        visible_rows = min(len(entries), 6)
        row_h = 28
        self.setFixedHeight(visible_rows * row_h + 4)

        self._list.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem):
        code = item.data(Qt.UserRole)
        self.lang_selected.emit(code)
        self.close()

