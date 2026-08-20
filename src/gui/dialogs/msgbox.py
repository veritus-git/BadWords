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
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import _center_on_screen


class CustomMsgBox(FramelessWindowMixin, _BaseDialog):
    def __init__(self, parent, title: str, message: str, btn_yes_text: str, btn_no_text: str = None, btn_cancel_text: str = None):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; }}
            QLabel {{ color: {config.FG_COLOR}; }}
            QLabel#lbl_title {{ font-size: 14pt; font-weight: bold; }}
            QLabel#lbl_msg {{ font-size: 11pt; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_yes {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_yes:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tb = CustomTitleBar(self, "en", parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(15)
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("lbl_msg")
        lbl_msg.setWordWrap(True)
        lbl_msg.setFixedWidth(380)
        lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if btn_cancel_text:
            btn_cancel = QPushButton(btn_cancel_text)
            btn_cancel.clicked.connect(lambda: self.done(2))
            btn_layout.addWidget(btn_cancel)
            btn_layout.addSpacing(10)
            
        if btn_no_text:
            btn_no = QPushButton(btn_no_text)
            btn_no.clicked.connect(self.reject)
            btn_layout.addWidget(btn_no)
            btn_layout.addSpacing(10)
            
        btn_yes = QPushButton(btn_yes_text)
        btn_yes.setObjectName("btn_yes")
        btn_yes.clicked.connect(self.accept)
        btn_layout.addWidget(btn_yes)
        
        content_layout.addLayout(btn_layout)
        
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())
