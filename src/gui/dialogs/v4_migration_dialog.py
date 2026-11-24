#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: v4_migration_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
One-time milestone notification displayed after upgrading from 3.x to 4.0.0,
informing the user about the standalone desktop app transformation and native launchers.
"""

import sys
import webbrowser
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QMouseEvent, QCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget, QScrollArea
)
import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog
from gui.utils import _app_icon, _txt, fit_dialog_to_screen, get_vector_icon


class V4MigrationDialog(FramelessWindowMixin, _BaseDialog):
    def __init__(self, lang: str = "en", parent=None):
        super().__init__(parent)
        self.user_choice = "close"
        self._drag_pos = None
        self._lang = lang if lang in config.TRANS else "en"

        def _t(suffix: str) -> str:
            return _txt(self._lang, f"v4_mig_{suffix}")

        self.setWindowTitle(_t("heading"))
        self.frameless_init(is_popup=True)
        self.setWindowIcon(_app_icon())

        self.setStyleSheet(f"""
            QDialog {{
                background-color: #181818;
                color: #e6e6e6;
                font-family: '{config.UI_FONT_NAME}', 'Segoe UI', 'Ubuntu', sans-serif;
            }}
            QFrame, QWidget {{
                background: transparent;
                background-color: transparent;
                color: #e6e6e6;
                font-family: '{config.UI_FONT_NAME}', 'Segoe UI', 'Ubuntu', sans-serif;
            }}
            #MainCard {{
                background-color: #181818;
                border: 1px solid #2e2e2e;
                border-radius: 0px;
            }}
            QLabel {{
                background: transparent;
                background-color: transparent;
            }}
            #BadgeLabel {{
                background-color: #0d2e18;
                color: #39ff7a;
                border: 1px solid #1a572d;
                border-radius: {config.S(4)}px;
                padding: {config.S(4)}px {config.S(10)}px;
                font-size: {config.FS_PX(9)}px;
                font-weight: bold;
            }}
            #HeadingLabel {{
                background: transparent;
                background-color: transparent;
                color: #ffffff;
                font-size: {config.FS_PX(13.5)}px;
                font-weight: bold;
            }}
            #BodyLabel {{
                background: transparent;
                background-color: transparent;
                color: #cccccc;
                font-size: {config.FS_PX(10)}px;
                line-height: 1.5;
            }}
            QPushButton {{
                border-radius: {config.S(6)}px;
                padding: {config.S(8)}px {config.S(16)}px;
                font-size: {config.FS_PX(9.5)}px;
                font-weight: bold;
            }}
            #PrimaryBtn {{
                background-color: #238636;
                color: #ffffff;
                border: 1px solid #2ea043;
            }}
            #PrimaryBtn:hover {{
                background-color: #2ea043;
            }}
            #SecondaryBtn {{
                background-color: #21262d;
                color: #c9d1d9;
                border: 1px solid #30363d;
            }}
            #SecondaryBtn:hover {{
                background-color: #30363d;
                color: #ffffff;
            }}
            #CloseBtn {{
                background-color: transparent;
                color: #8b949e;
                border: none;
                font-size: {config.FS_PX(11)}px;
                padding: {config.S(2)}px {config.S(6)}px;
            }}
            #CloseBtn:hover {{
                color: #ffffff;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame(self)
        card.setObjectName("MainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(config.S(24), config.S(24), config.S(24), config.S(24))
        card_layout.setSpacing(config.S(14))

        top_row = QHBoxLayout()
        badge = QLabel(_t("badge"))
        badge.setObjectName("BadgeLabel")
        top_row.addWidget(badge)
        top_row.addStretch()

        close_btn = QPushButton()
        close_btn.setObjectName("CloseBtn")
        close_btn.setFixedSize(config.S(26), config.S(26))
        close_btn.setIcon(get_vector_icon("close", config.S(12), "#8b949e"))
        close_btn.setIconSize(QSize(config.S(12), config.S(12)))
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.enterEvent = lambda e: close_btn.setIcon(get_vector_icon("close", config.S(12), "#ffffff"))
        close_btn.leaveEvent = lambda e: close_btn.setIcon(get_vector_icon("close", config.S(12), "#8b949e"))
        close_btn.clicked.connect(self._on_close)
        top_row.addWidget(close_btn)
        card_layout.addLayout(top_row)

        heading = QLabel(_t("heading"))
        heading.setObjectName("HeadingLabel")
        heading.setAttribute(Qt.WA_TranslucentBackground, True)
        heading.setWordWrap(True)
        card_layout.addWidget(heading)

        body = QLabel(_t("body"))
        body.setObjectName("BodyLabel")
        body.setAttribute(Qt.WA_TranslucentBackground, True)
        body.setWordWrap(True)
        card_layout.addWidget(body)

        card_layout.addSpacing(config.S(6))

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_close = QPushButton(_t("btn_close"))
        btn_close.setObjectName("SecondaryBtn")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self._on_close)
        btn_row.addWidget(btn_close)

        btn_gh = QPushButton(_t("btn_github"))
        btn_gh.setObjectName("PrimaryBtn")
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(self._on_github)
        btn_row.addWidget(btn_gh)
        card_layout.addLayout(btn_row)

        scroll = QScrollArea(self)
        scroll.setObjectName("V4MigScroll")
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea#V4MigScroll { background: transparent; border: none; }"
        )
        scroll.setWidget(card)
        outer.addWidget(scroll, 1)
        fit_dialog_to_screen(self, config.S(680), 0, reference_window=parent)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def _on_github(self):
        self.user_choice = "github"
        try:
            webbrowser.open("https://github.com/veritus-git/BadWords#-installation--setup")
        except Exception:
            pass
        self.accept()

    def _on_close(self):
        self.user_choice = "close"
        self.reject()
