#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: marker_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Dialog for creating and editing custom timeline markers.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QWidget, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import CustomDropdown
from gui.utils import _txt, _center_on_screen


class MarkerDialog(FramelessWindowMixin, _BaseDialog):
    """
    Custom frameless dialog for adding or editing a custom marker.
    Usage:
        dlg = MarkerDialog(parent, lang, title_key, prefill_name='', prefill_color='Blue')
        if dlg.exec() == QDialog.Accepted:
            name, color = dlg.result_name, dlg.result_color
    """
    def __init__(self, parent, lang: str, title_key: str,
                 prefill_name: str = '', prefill_color: str = ''):
        super().__init__(parent)
        self._lang = lang
        self.result_name = ''
        self.result_color = ''

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.ApplicationModal)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; border-radius: 6px; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: {config.UI_FONT_NAME}; }}
            QLabel#lbl_title {{ font-size: 13pt; font-weight: bold; color: #ffffff; }}
            QLineEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px 8px;
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
            }}
            QLineEdit:focus {{ border-color: {config.BTN_BG}; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
                font-family: {config.UI_FONT_NAME};
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_ok {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_ok:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.inner_frame.setGraphicsEffect(shadow)
        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        title_text = _txt(lang, title_key)
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(title_text)
        root_layout.addWidget(self._tb)

        content = QWidget(self.inner_frame)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(14)
        root_layout.addWidget(content)

        lbl_title = QLabel(title_text, content)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)

        # Name row
        name_row = QHBoxLayout()
        name_lbl = QLabel(_txt(lang, "lbl_marker_name"), content)
        name_lbl.setFixedWidth(100)
        self._name_edit = QLineEdit(content)
        self._name_edit.setText(prefill_name)
        self._name_edit.setPlaceholderText(_txt(lang, "placeholder_marker_name"))
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        content_layout.addLayout(name_row)

        # Color row
        color_row = QHBoxLayout()
        color_lbl = QLabel(_txt(lang, "lbl_marker_color"), content)
        color_lbl.setFixedWidth(100)
        _blocked = getattr(config, 'RESOLVE_COLORS_BLOCKED', {"Olive", "Violet", "Chocolate", "Navy", "Tan"})
        self._color_key_map: dict[str, str] = {}
        translated_options: list[str] = []
        for c in config.RESOLVE_COLORS:
            if c in _blocked:
                continue
            t = _txt(lang, f"resolve_color_{c.lower()}")
            self._color_key_map[t] = c
            translated_options.append(t)
        self._color_combo = CustomDropdown(translated_options)
        if not (prefill_color and prefill_color in config.RESOLVE_COLORS):
            self._color_combo.setText(_txt(lang, "txt_select"))
        if prefill_color and prefill_color in config.RESOLVE_COLORS:
            prefill_t = _txt(lang, f"resolve_color_{prefill_color.lower()}")
            self._color_combo.setText(prefill_t)
        color_row.addWidget(color_lbl)
        color_row.addWidget(self._color_combo)
        content_layout.addLayout(color_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(_txt(lang, "btn_close"), content)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(_txt(lang, "btn_apply"), content)
        btn_ok.setObjectName("btn_ok")
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_ok)
        content_layout.addLayout(btn_row)

        self.adjustSize()
        self.setFixedWidth(380)
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    def _on_ok(self):
        name = self._name_edit.text().strip()
        translated = self._color_combo.currentText()
        color_key = self._color_key_map.get(translated, "")
        if name and color_key:
            self.result_name = name
            self.result_color = color_key
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._on_ok()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
