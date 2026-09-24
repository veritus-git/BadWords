#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: file_drop_zone.py
ROLE: GUI Widget
DESCRIPTION:
Modern, responsive Drag & Drop and File Picker widget for standalone media import (video/audio).
Adheres strictly to the BadWords design system: dark aesthetics, zero emojis, vector SVG icons,
and embedded Ubuntu font consistency across all platforms.
"""

import os
import subprocess
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSizePolicy
)
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QCursor

import config
from gui.utils import get_svg_icon


class FileDropZone(QWidget):
    """
    Modern Drag & Drop + Browse box for importing local media files (.mp4, .mov, etc.).
    Supports visual drag-over feedback, file metadata inspection, and clean clear/reset.
    """
    file_selected = Signal(str)

    SUPPORTED_AUDIO_EXTENSIONS = (
        ".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".aiff", ".wma", ".opus"
    )
    SUPPORTED_VIDEO_EXTENSIONS = (
        ".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".ts", ".mts", ".wmv", ".flv"
    )
    SUPPORTED_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS

    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        if not file_path:
            return False
        ext = os.path.splitext(file_path)[1].lower()
        return ext in cls.SUPPORTED_EXTENSIONS

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("file_drop_zone")
        self.setFixedHeight(config.S(90))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._current_file = ""
        self._is_drag_active = False

        self._build_ui()
        self._update_state()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(config.S(12), config.S(10), config.S(12), config.S(10))
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # ── State 1: Empty / Prompt Container ────────────────────────────────
        self.empty_container = QWidget(self)
        self.empty_container.setStyleSheet("background: transparent;")
        empty_l = QVBoxLayout(self.empty_container)
        empty_l.setContentsMargins(0, 0, 0, 0)
        empty_l.setSpacing(config.S(4))
        empty_l.setAlignment(Qt.AlignCenter)

        # Vector upload icon (clean minimal arrow & tray)
        self.lbl_icon = QLabel()
        self.lbl_icon.setAlignment(Qt.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self._update_empty_icon(is_hover=False)
        empty_l.addWidget(self.lbl_icon)

        self.lbl_prompt = QLabel()
        self.lbl_prompt.setAlignment(Qt.AlignCenter)
        self.lbl_prompt.setStyleSheet(
            f"color: #a0a0a0; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(8.5)}pt; font-weight: 500; background: transparent; border: none;"
        )
        empty_l.addWidget(self.lbl_prompt)

        self.lbl_subprompt = QLabel()
        self.lbl_subprompt.setAlignment(Qt.AlignCenter)
        self.lbl_subprompt.setStyleSheet(
            f"color: #1a7a3e; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(8.0)}pt; font-weight: bold; background: transparent; border: none;"
        )
        empty_l.addWidget(self.lbl_subprompt)

        self.main_layout.addWidget(self.empty_container)

        # ── State 2: File Selected Container ─────────────────────────────────
        self.selected_container = QWidget(self)
        self.selected_container.setStyleSheet("background: transparent;")
        sel_l = QHBoxLayout(self.selected_container)
        sel_l.setContentsMargins(0, 0, 0, 0)
        sel_l.setSpacing(config.S(10))
        sel_l.setAlignment(Qt.AlignVCenter)

        # File type icon
        self.lbl_file_icon = QLabel()
        self.lbl_file_icon.setFixedSize(config.S(32), config.S(32))
        self.lbl_file_icon.setAlignment(Qt.AlignCenter)
        self.lbl_file_icon.setStyleSheet("background: transparent; border: none;")
        sel_l.addWidget(self.lbl_file_icon)

        # Text details (Filename + metadata)
        v_details = QVBoxLayout()
        v_details.setContentsMargins(0, 0, 0, 0)
        v_details.setSpacing(config.S(2))
        v_details.setAlignment(Qt.AlignVCenter)

        h_title_row = QHBoxLayout()
        h_title_row.setContentsMargins(0, 0, 0, 0)
        h_title_row.setSpacing(config.S(6))

        self.lbl_badge = QLabel()
        self.lbl_badge.setFixedHeight(config.S(16))
        self.lbl_badge.setStyleSheet(
            f"background-color: #1a3a24; color: #38c172; border: 1px solid #1a7a3e; "
            f"border-radius: {config.S(3)}px; padding: 0 {config.S(4)}px; "
            f"font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(7.5)}pt; font-weight: bold;"
        )
        h_title_row.addWidget(self.lbl_badge)

        self.lbl_filename = QLabel()
        self.lbl_filename.setStyleSheet(
            f"color: #ffffff; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(9.0)}pt; font-weight: bold; background: transparent; border: none;"
        )
        h_title_row.addWidget(self.lbl_filename, 1)
        v_details.addLayout(h_title_row)

        self.lbl_file_info = QLabel()
        self.lbl_file_info.setStyleSheet(
            f"color: #888888; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(8.0)}pt; background: transparent; border: none;"
        )
        v_details.addWidget(self.lbl_file_info)

        sel_l.addLayout(v_details, 1)

        # Clear button
        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedSize(config.S(24), config.S(24))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setToolTip("Usuń plik / Wybierz inny")
        self.btn_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #888888;
                border: 1px solid #3a3a3a; border-radius: {config.S(12)}px;
                font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(8.5)}pt; font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: #381e1e; color: #ff5555; border-color: #ff5555;
            }}
        """)
        self.btn_clear.clicked.connect(self.clear_file)
        sel_l.addWidget(self.btn_clear)

        self.main_layout.addWidget(self.selected_container)

    def set_texts(self, prompt: str, subprompt: str):
        """Sets localized prompt texts."""
        self.lbl_prompt.setText(prompt)
        self.lbl_subprompt.setText(subprompt)

    def _update_empty_icon(self, is_hover: bool = False):
        color = "#1a7a3e" if is_hover else "#707070"
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
          <path d="M12 15V3m0 0l-4 4m4-4l4 4" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
        icon = get_svg_icon(svg, config.S(20))
        self.lbl_icon.setPixmap(icon.pixmap(config.S(20), config.S(20)))

    def _update_file_icon(self, ext: str):
        ext_lower = ext.lower()
        is_audio = ext_lower in (".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".aiff")
        color = "#38c172"
        if is_audio:
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
              <path d="M9 18V5l12-2v13" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
              <circle cx="6" cy="18" r="3" stroke="{color}" stroke-width="1.8"/>
              <circle cx="18" cy="16" r="3" stroke="{color}" stroke-width="1.8"/>
            </svg>'''
        else:
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="4" width="20" height="16" rx="2" stroke="{color}" stroke-width="1.8"/>
              <path d="M7 4v16M17 4v16M2 12h20M2 8h5M2 16h5M17 8h5M17 16h5" stroke="{color}" stroke-width="1.5"/>
            </svg>'''
        icon = get_svg_icon(svg, config.S(24))
        self.lbl_file_icon.setPixmap(icon.pixmap(config.S(24), config.S(24)))

    def _update_state(self):
        if self._current_file and os.path.isfile(self._current_file):
            self.empty_container.hide()
            self.selected_container.show()
            self.setCursor(Qt.ArrowCursor)

            filename = os.path.basename(self._current_file)
            ext = os.path.splitext(filename)[1].lstrip('.').upper() or "FILE"

            self.lbl_badge.setText(ext)
            # Truncate filename if too long
            display_name = filename if len(filename) <= 32 else filename[:16] + "..." + filename[-12:]
            self.lbl_filename.setText(display_name)
            self.lbl_filename.setToolTip(self._current_file)

            self._update_file_icon("." + ext)

            # File size info
            try:
                sz_bytes = os.path.getsize(self._current_file)
                if sz_bytes >= 1024 * 1024 * 1024:
                    sz_str = f"{sz_bytes / (1024**3):.2f} GB"
                elif sz_bytes >= 1024 * 1024:
                    sz_str = f"{sz_bytes / (1024**2):.1f} MB"
                else:
                    sz_str = f"{sz_bytes / 1024:.0f} KB"
            except Exception:
                sz_str = "Unknown size"

            # Optional duration lookup
            dur_str = self._probe_duration_str(self._current_file)
            if dur_str:
                self.lbl_file_info.setText(f"{dur_str} • {sz_str}")
            else:
                self.lbl_file_info.setText(sz_str)
        else:
            self.selected_container.hide()
            self.empty_container.show()
            self.setCursor(Qt.PointingHandCursor)

    def _probe_duration_str(self, file_path: str) -> str:
        """Quick ffprobe duration lookup (non-blocking / fast timeout)."""
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=2)
            if res.returncode == 0 and res.stdout.strip():
                dur_s = float(res.stdout.strip())
                m = int(dur_s // 60)
                s = int(dur_s % 60)
                h = int(m // 60)
                m = m % 60
                if h > 0:
                    return f"{h:02d}:{m:02d}:{s:02d}"
                return f"{m:02d}:{s:02d}"
        except Exception:
            pass
        return ""

    def get_file(self) -> str:
        return self._current_file

    def set_file(self, file_path: str):
        if file_path and os.path.isfile(file_path):
            if not self.is_supported_file(file_path):
                self.shake()
                return
            self._current_file = os.path.abspath(file_path)
            self._update_state()
            self.file_selected.emit(self._current_file)
            self.update()
        elif not file_path:
            self.clear_file()
        else:
            self.shake()

    def clear_file(self):
        if not self._current_file:
            return
        self._current_file = ""
        self._update_state()
        self.file_selected.emit("")
        self.update()

    # ── Mouse Interaction ────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._current_file:
            self.browse_file()
        super().mousePressEvent(event)

    def browse_file(self):
        video_patterns = " ".join(f"*{ext}" for ext in self.SUPPORTED_VIDEO_EXTENSIONS)
        audio_patterns = " ".join(f"*{ext}" for ext in self.SUPPORTED_AUDIO_EXTENSIONS)
        all_patterns = f"{video_patterns} {audio_patterns}"
        filters = (
            f"Pliki multimedialne ({all_patterns});;"
            f"Pliki wideo ({video_patterns});;"
            f"Pliki audio ({audio_patterns})"
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik wideo lub audio", "", filters
        )
        if path:
            if self.is_supported_file(path):
                self.set_file(path)
            else:
                self.shake()

    # ── Drag and Drop Handlers ───────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                fp = urls[0].toLocalFile()
                if fp and self.is_supported_file(fp):
                    event.acceptProposedAction()
                    self._is_drag_active = True
                    self._update_empty_icon(is_hover=True)
                    self.update()
                    return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                fp = urls[0].toLocalFile()
                if fp and self.is_supported_file(fp):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._is_drag_active = False
        self._update_empty_icon(is_hover=False)
        self.update()
        event.accept()

    def dropEvent(self, event):
        self._is_drag_active = False
        self._update_empty_icon(is_hover=False)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                fp = urls[0].toLocalFile()
                if fp and os.path.isfile(fp) and self.is_supported_file(fp):
                    self.set_file(fp)
                    event.acceptProposedAction()
                    self.update()
                    return
                else:
                    self.shake()
        event.ignore()

    def shake(self):
        """Triggers horizontal shake animation and red border flash on validation failure."""
        from PySide6.QtCore import QPropertyAnimation, QPoint, QTimer
        self._shake_err_border = True
        self.update()

        if not hasattr(self, '_orig_pos') or self._orig_pos is None:
            self._orig_pos = self.pos()
        pos = self._orig_pos
        delta = config.S(6)
        anim = QPropertyAnimation(self, b"pos", self.parent())
        anim.setDuration(300)
        anim.setKeyValueAt(0, pos)
        anim.setKeyValueAt(0.2, pos + QPoint(delta, 0))
        anim.setKeyValueAt(0.4, pos - QPoint(delta, 0))
        anim.setKeyValueAt(0.6, pos + QPoint(delta, 0))
        anim.setKeyValueAt(0.8, pos - QPoint(delta, 0))
        anim.setKeyValueAt(1, pos)

        def _on_done():
            if hasattr(self, '_orig_pos') and self._orig_pos is not None:
                self.move(self._orig_pos)
                self._orig_pos = None
            QTimer.singleShot(900, self._clear_shake_err)

        anim.finished.connect(_on_done)
        anim.start()
        self._shake_anim = anim

    def _clear_shake_err(self):
        self._shake_err_border = False
        self.update()

    # ── Custom Painting (Standalone Rounded Card) ───────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = float(rect.width())
        h = float(rect.height())
        r = float(config.S(4))

        # Background - dark graphite blending harmoniously with #1c1c1c UI
        if getattr(self, '_shake_err_border', False):
            bg_color = QColor("#221414")
            border_color = QColor("#ed4245")
            pen_style = Qt.SolidLine
            pen_w = 1.5
        elif self._is_drag_active:
            bg_color = QColor("#142d1e")
            border_color = QColor("#1a7a3e")
            pen_style = Qt.SolidLine
            pen_w = 2.0
        elif self._current_file:
            bg_color = QColor("#1a1a1a")
            border_color = QColor("#3a3a3a")
            pen_style = Qt.SolidLine
            pen_w = 1.0
        else:
            bg_color = QColor("#1a1a1a")
            border_color = QColor("#3a3a3a")
            pen_style = Qt.DashLine
            pen_w = 1.2

        # 1. Fill background with rounded corners on all 4 sides
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, w, h, r, r)
        p.fillPath(path, bg_color)

        # 2. Draw border along all 4 sides with rounded corners
        pen = QPen(border_color, pen_w, pen_style)
        if pen_style == Qt.DashLine:
            pen.setDashPattern([4, 4])
        p.setPen(pen)

        half_w = pen_w / 2.0
        outline = QPainterPath()
        outline.addRoundedRect(half_w, half_w, w - pen_w, h - pen_w, r, r)
        p.drawPath(outline)

        p.end()
