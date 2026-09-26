#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: video_preview.py
ROLE: GUI Component
DESCRIPTION:
16:9 Video playback preview container utilizing QVideoWidget.
Features rounded corners, aspect-ratio preservation, and sleek DaVinci Resolve styling.
"""

from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtMultimediaWidgets import QVideoWidget

import config


class VideoPreviewWidget(QFrame):
    """
    Video playback monitor container for talking-head and timeline footage.
    Embedded in the bottom dock alongside the Timeline Preview ribbon.
    """
    def __init__(self, parent: Optional[QFrame] = None):
        super().__init__(parent)
        self.setObjectName("VideoPreviewWidget")
        self.setStyleSheet(f"""
            QFrame#VideoPreviewWidget {{
                background-color: #0c0c0c;
                border: 1px solid #242424;
                border-radius: {config.S(6)}px;
            }}
        """)
        self.setMinimumHeight(config.S(90))
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_widget = QVideoWidget(self)
        self.video_widget.setStyleSheet(f"background-color: #000000; border-radius: {config.S(6)}px;")
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        layout.addWidget(self.video_widget)

        self.lbl_placeholder = QLabel(self)
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder.setStyleSheet(f"color: #4a4a4a; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(8.5)}pt; font-style: italic;")
        self.lbl_placeholder.setText("Video Preview")
        self.lbl_placeholder.hide()
        layout.addWidget(self.lbl_placeholder)

    def sizeHint(self) -> QSize:
        h = max(config.S(90), self.height() if self.height() > 0 else config.S(145))
        w = int(h * 16.0 / 9.0)
        return QSize(w, h)

    def show_placeholder(self, show: bool = True, text: str = "Video Preview") -> None:
        if show:
            self.lbl_placeholder.setText(text)
            self.lbl_placeholder.show()
            self.video_widget.hide()
        else:
            self.lbl_placeholder.hide()
            self.video_widget.show()
