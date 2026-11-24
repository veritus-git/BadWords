#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: msgbox.py
ROLE: GUI Dialog
DESCRIPTION:
Custom frameless message box dialog for alerts and confirmations.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import _center_on_screen
from gui.widgets.buttons import CustomCheckBox


class CustomMsgBox(FramelessWindowMixin, _BaseDialog):
    def __init__(self, parent, title: str, message: str, btn_yes_text: str, btn_no_text: str = None, btn_cancel_text: str = None, checkbox_text: str = None, checkbox_checked: bool = False):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {config.BG_COLOR}; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #2e2e2e; border-radius: 0px; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; }}
            QLabel#lbl_title {{ font-size: {config.FS(14)}pt; font-weight: bold; }}
            QLabel#lbl_msg {{ font-size: {config.FS(10.5)}pt; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: {config.S(6)}px {config.S(16)}px;
                border-radius: {config.S(4)}px;
                min-width: {config.S(80)}px;
                font-size: {config.FS(10)}pt;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_yes {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_yes:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        tb_lang = getattr(parent, 'lang', None) or getattr(parent, '_lang', None) or 'en'
        self._tb = CustomTitleBar(self, tb_lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(config.S(20), config.S(25), config.S(20), config.S(20))
        content_layout.setSpacing(config.S(15))
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("lbl_msg")
        lbl_msg.setWordWrap(True)
        lbl_msg.setFixedWidth(config.S(380))
        lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(lbl_msg)
        
        self.chk_box = None
        if checkbox_text:
            self.chk_box = CustomCheckBox(checkbox_text, checked=checkbox_checked, parent=self.inner_frame)
            content_layout.addWidget(self.chk_box)
            content_layout.addSpacing(config.S(5))

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        # With a Cancel button, Esc / window close must mean Cancel (2), not "No" (0)
        self._has_cancel = bool(btn_cancel_text)
        if btn_cancel_text:
            btn_cancel = QPushButton(btn_cancel_text)
            btn_cancel.clicked.connect(lambda: self.done(2))
            btn_layout.addWidget(btn_cancel)
            btn_layout.addSpacing(config.S(10))

        if btn_no_text:
            btn_no = QPushButton(btn_no_text)
            btn_no.clicked.connect(lambda: self.done(QDialog.Rejected))
            btn_layout.addWidget(btn_no)
            btn_layout.addSpacing(config.S(10))
            
        btn_yes = QPushButton(btn_yes_text)
        btn_yes.setObjectName("btn_yes")
        btn_yes.clicked.connect(self.accept)
        btn_layout.addWidget(btn_yes)
        
        content_layout.addLayout(btn_layout)
        
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height(), reference_window=parent)

    def reject(self):
        # Esc key and window close route through reject()
        if getattr(self, '_has_cancel', False):
            self.done(2)
        else:
            super().reject()

    def is_checkbox_checked(self) -> bool:
        return self.chk_box.isChecked() if getattr(self, 'chk_box', None) is not None else False

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
