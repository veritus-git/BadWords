#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: file_drop_zone.py
ROLE: GUI Widget
DESCRIPTION:
Modern, responsive Drag & Drop and Multi-File Queue widget for standalone media import (video/audio).
Maintains strict fixed height (118px) to guarantee pixel-perfect stability of the welcome view layout.
Supports single-file and multi-file sequential queues, reordering, deletion, and fast duration probing.
"""

import os
import subprocess
from PySide6.QtCore import Qt, Signal, QSize, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSizePolicy, QScrollArea, QFrame
)
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QCursor

import config
from gui.utils import _txt, get_svg_icon


class FileDropZone(QWidget):
    """
    Modern Drag & Drop + Browse box supporting single and multiple files.
    Always maintains a fixed height of config.S(118) to preserve Welcome Screen geometry.
    """
    file_selected = Signal(str)
    files_changed = Signal(list)

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

    def __init__(self, parent=None, lang: str = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("file_drop_zone")
        self.setFixedHeight(config.S(118))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if lang:
            self._lang = lang
        elif parent and hasattr(parent, 'current_lang'):
            self._lang = parent.current_lang
        elif parent and hasattr(parent, '_lang'):
            self._lang = parent._lang
        else:
            try:
                import osdoc
                prefs = osdoc.load_preferences() or {}
                self._lang = prefs.get("gui_lang", "en")
            except Exception:
                self._lang = "en"

        self._files: list[str] = []
        self._current_file: str = ""
        self._is_drag_active: bool = False
        self._durations_cache: dict[str, str] = {}
        self._durations_sec_cache: dict[str, float] = {}
        self.setCursor(Qt.ArrowCursor)

        self._build_ui()
        self._update_state()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(config.S(10), config.S(8), config.S(10), config.S(8))
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignCenter)

        # ── State 1: Empty Container (0 files) ───────────────────────────────
        self.empty_container = QWidget(self)
        self.empty_container.setStyleSheet("background: transparent;")
        empty_l = QVBoxLayout(self.empty_container)
        empty_l.setContentsMargins(0, 0, 0, 0)
        empty_l.setSpacing(config.S(4))
        empty_l.setAlignment(Qt.AlignCenter)

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
        self.lbl_subprompt.setCursor(Qt.PointingHandCursor)
        self.lbl_subprompt.setStyleSheet(
            f"color: #1a7a3e; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(8.0)}pt; font-weight: bold; background: transparent; border: none;"
        )
        empty_l.addWidget(self.lbl_subprompt)

        self.main_layout.addWidget(self.empty_container)

        # ── State 2: Single File Container (1 file) ───────────────────────────
        self.selected_container = QWidget(self)
        self.selected_container.setStyleSheet("background: transparent;")
        sel_l = QHBoxLayout(self.selected_container)
        sel_l.setContentsMargins(0, 0, 0, 0)
        sel_l.setSpacing(config.S(10))
        sel_l.setAlignment(Qt.AlignVCenter)

        self.lbl_file_icon = QLabel()
        self.lbl_file_icon.setFixedSize(config.S(32), config.S(32))
        self.lbl_file_icon.setAlignment(Qt.AlignCenter)
        self.lbl_file_icon.setStyleSheet("background: transparent; border: none;")
        sel_l.addWidget(self.lbl_file_icon)

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

        # Actions in single-file mode (+ Add more and Clear)
        h_single_actions = QHBoxLayout()
        h_single_actions.setContentsMargins(0, 0, 0, 0)
        h_single_actions.setSpacing(config.S(6))

        self.btn_add_more_single = QPushButton("+")
        self.btn_add_more_single.setFixedSize(config.S(24), config.S(24))
        self.btn_add_more_single.setCursor(Qt.PointingHandCursor)
        self.btn_add_more_single.setToolTip(_txt(self._lang, "tt_add_more_files", "Add more files to sequence"))
        self.btn_add_more_single.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #38c172;
                border: 1px solid #3a3a3a; border-radius: {config.S(12)}px;
                font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(10)}pt; font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: #1a3a24; border-color: #38c172; color: #ffffff;
            }}
        """)
        self.btn_add_more_single.clicked.connect(lambda: self.browse_files(append=True))
        h_single_actions.addWidget(self.btn_add_more_single)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedSize(config.S(24), config.S(24))
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setToolTip(_txt(self._lang, "tt_clear_file", "Clear file"))
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
        self.btn_clear.clicked.connect(self.clear_files)
        h_single_actions.addWidget(self.btn_clear)

        sel_l.addLayout(h_single_actions)
        self.main_layout.addWidget(self.selected_container)

        # ── State 3: Multi-File Queue Container (>1 files) ───────────────────
        self.multi_container = QWidget(self)
        self.multi_container.setStyleSheet("background: transparent;")
        multi_l = QVBoxLayout(self.multi_container)
        multi_l.setContentsMargins(0, 0, 0, 0)
        multi_l.setSpacing(config.S(4))

        # Top summary bar
        h_multi_top = QHBoxLayout()
        h_multi_top.setContentsMargins(0, 0, 0, 0)
        h_multi_top.setSpacing(config.S(6))

        self.lbl_multi_summary = QLabel()
        self.lbl_multi_summary.setStyleSheet(
            f"color: #a0a0a0; font-family: '{config.UI_FONT_NAME}'; "
            f"font-size: {config.FS(8.0)}pt; font-weight: bold; background: transparent;"
        )
        h_multi_top.addWidget(self.lbl_multi_summary, 1)

        self.btn_multi_add = QPushButton(f"+ {_txt(self._lang, 'btn_add', 'Add')}")
        self.btn_multi_add.setCursor(Qt.PointingHandCursor)
        self.btn_multi_add.setStyleSheet(f"""
            QPushButton {{
                background-color: #1a3a24; color: #38c172; border: 1px solid #1a7a3e;
                border-radius: {config.S(3)}px; padding: {config.S(2)}px {config.S(6)}px;
                font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(7.5)}pt; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #214a2f; color: #ffffff; }}
        """)
        self.btn_multi_add.clicked.connect(lambda: self.browse_files(append=True))
        h_multi_top.addWidget(self.btn_multi_add)

        self.btn_multi_clear = QPushButton(_txt(self._lang, "btn_clear", "Clear"))
        self.btn_multi_clear.setCursor(Qt.PointingHandCursor)
        self.btn_multi_clear.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #888888; border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px; padding: {config.S(2)}px {config.S(6)}px;
                font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(7.5)}pt;
            }}
            QPushButton:hover {{ background-color: #381e1e; color: #ff5555; border-color: #ff5555; }}
        """)
        self.btn_multi_clear.clicked.connect(self.clear_files)
        h_multi_top.addWidget(self.btn_multi_clear)

        multi_l.addLayout(h_multi_top)

        # Scrollable items area
        self.scroll_area = QScrollArea(self.multi_container)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFixedHeight(config.S(74))
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent; border: none;
            }}
            QScrollBar:vertical {{
                background: transparent; width: {config.S(5)}px; margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: #3a3a3a; border-radius: {config.S(2)}px; min-height: {config.S(16)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #505050;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px; background: transparent;
            }}
        """)

        self.scroll_widget = QWidget()
        self.scroll_widget.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.scroll_widget)
        self.items_layout.setContentsMargins(0, 0, config.S(2), 0)
        self.items_layout.setSpacing(config.S(3))
        self.scroll_area.setWidget(self.scroll_widget)

        multi_l.addWidget(self.scroll_area)
        self.main_layout.addWidget(self.multi_container)

    def set_texts(self, prompt: str = None, subprompt: str = None, add_txt: str = None, clear_txt: str = None, queue_txt: str = None, lang: str = None):
        """Sets localized prompt and control texts."""
        if lang:
            self._lang = lang
        if prompt: self.lbl_prompt.setText(prompt)
        if subprompt: self.lbl_subprompt.setText(subprompt)
        if add_txt and hasattr(self, 'btn_multi_add'):
            self.btn_multi_add.setText(f"+ {add_txt}" if not add_txt.startswith("+") else add_txt)
        if clear_txt and hasattr(self, 'btn_multi_clear'):
            self.btn_multi_clear.setText(clear_txt)
        if hasattr(self, 'btn_clear') and hasattr(self, '_lang'):
            self.btn_clear.setToolTip(_txt(self._lang, "tt_clear_file", "Clear file"))
        if queue_txt:
            self._queue_prefix = queue_txt

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
        is_audio = ext_lower in self.SUPPORTED_AUDIO_EXTENSIONS
        color = "#38c172" if not is_audio else "#4a9eff"
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

    def _probe_duration_sec(self, file_path: str) -> float:
        """Fast cached ffprobe duration lookup in seconds."""
        if file_path in self._durations_sec_cache:
            return self._durations_sec_cache[file_path]
        try:
            from osdoc import get_subprocess_kwargs
            cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", file_path
            ]
            res = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=2, **get_subprocess_kwargs()
            )
            if res.returncode == 0 and res.stdout.strip():
                dur = float(res.stdout.strip())
                self._durations_sec_cache[file_path] = dur
                return dur
        except Exception:
            pass
        self._durations_sec_cache[file_path] = 0.0
        return 0.0

    def _probe_duration_str(self, file_path: str) -> str:
        """Quick ffprobe duration string lookup (e.g. 04:12)."""
        if file_path in self._durations_cache:
            return self._durations_cache[file_path]
        dur_s = self._probe_duration_sec(file_path)
        if dur_s > 0:
            m = int(dur_s // 60)
            s = int(dur_s % 60)
            h = int(m // 60)
            m = m % 60
            formatted = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"
            self._durations_cache[file_path] = formatted
            return formatted
        self._durations_cache[file_path] = ""
        return ""

    def _update_state(self):
        """Switches between Empty (0), Single File (1), and Multi Queue (2+) containers."""
        # Sanitize files: retain only existing files
        valid_files = [f for f in self._files if os.path.isfile(f)]
        if len(valid_files) != len(self._files):
            self._files = valid_files

        count = len(self._files)
        self._current_file = self._files[0] if count > 0 else ""

        if count == 0:
            self.selected_container.hide()
            self.multi_container.hide()
            self.empty_container.show()
            self.setCursor(Qt.ArrowCursor)

        elif count == 1:
            self.empty_container.hide()
            self.multi_container.hide()
            self.selected_container.show()
            self.setCursor(Qt.ArrowCursor)

            filename = os.path.basename(self._current_file)
            ext = os.path.splitext(filename)[1].lstrip('.').upper() or "FILE"

            is_audio = ("." + ext.lower()) in self.SUPPORTED_AUDIO_EXTENSIONS
            badge_color = "#4a9eff" if is_audio else "#38c172"
            badge_bg = "#14253a" if is_audio else "#1a3a24"
            badge_border = "#1a4a7e" if is_audio else "#1a7a3e"

            self.lbl_badge.setText(ext)
            self.lbl_badge.setStyleSheet(
                f"background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_border}; "
                f"border-radius: {config.S(3)}px; padding: 0 {config.S(4)}px; "
                f"font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(7.5)}pt; font-weight: bold;"
            )

            display_name = filename if len(filename) <= 32 else filename[:16] + "..." + filename[-12:]
            self.lbl_filename.setText(display_name)
            self.lbl_filename.setToolTip(self._current_file)

            self._update_file_icon("." + ext)

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

            dur_str = self._probe_duration_str(self._current_file)
            self.lbl_file_info.setText(f"{dur_str} • {sz_str}" if dur_str else sz_str)

        else:
            # Multi-file queue mode
            self.empty_container.hide()
            self.selected_container.hide()
            self.multi_container.show()
            self.setCursor(Qt.ArrowCursor)

            # Rebuild queue list
            while self.items_layout.count():
                it = self.items_layout.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()

            total_sec = sum(self._probe_duration_sec(fp) for fp in self._files)
            tm = int(total_sec // 60)
            ts = int(total_sec % 60)
            th = int(tm // 60)
            tm = tm % 60
            tot_str = f"{th:02d}:{tm:02d}:{ts:02d}" if th > 0 else f"{tm:02d}:{ts:02d}"

            q_lbl = getattr(self, '_queue_prefix', 'Kolejka')
            self.lbl_multi_summary.setText(f"{q_lbl}: {count} • {tot_str}")

            for idx, fp in enumerate(self._files):
                row = self._create_queue_row(idx, fp, count)
                self.items_layout.addWidget(row)

            self.items_layout.addStretch(1)

        self.update()

    def _create_queue_row(self, idx: int, file_path: str, total_count: int) -> QWidget:
        """Builds a single compact row inside the multi-file scroll queue."""
        row_widget = QFrame()
        row_widget.setFixedHeight(config.S(22))
        row_widget.setStyleSheet(f"""
            QFrame {{
                background-color: #212121;
                border: 1px solid #2e2e2e;
                border-radius: {config.S(3)}px;
            }}
            QFrame:hover {{
                border-color: #3e3e3e;
                background-color: #262626;
            }}
        """)

        r_lay = QHBoxLayout(row_widget)
        r_lay.setContentsMargins(config.S(4), 0, config.S(4), 0)
        r_lay.setSpacing(config.S(4))

        # Reorder buttons: Up and Down
        btn_up = QPushButton("▲")
        btn_up.setFixedSize(config.S(14), config.S(14))
        btn_up.setCursor(Qt.PointingHandCursor if idx > 0 else Qt.ArrowCursor)
        btn_up.setEnabled(idx > 0)
        btn_up.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {'#888888' if idx > 0 else '#3a3a3a'};
                font-size: {config.FS(6.5)}pt; padding: 0;
            }}
            QPushButton:hover {{ color: {'#38c172' if idx > 0 else '#3a3a3a'}; }}
        """)
        btn_up.clicked.connect(lambda _, i=idx: self.move_file(i, i - 1))
        r_lay.addWidget(btn_up)

        btn_down = QPushButton("▼")
        btn_down.setFixedSize(config.S(14), config.S(14))
        btn_down.setCursor(Qt.PointingHandCursor if idx < total_count - 1 else Qt.ArrowCursor)
        btn_down.setEnabled(idx < total_count - 1)
        btn_down.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; color: {'#888888' if idx < total_count - 1 else '#3a3a3a'};
                font-size: {config.FS(6.5)}pt; padding: 0;
            }}
            QPushButton:hover {{ color: {'#38c172' if idx < total_count - 1 else '#3a3a3a'}; }}
        """)
        btn_down.clicked.connect(lambda _, i=idx: self.move_file(i, i + 1))
        r_lay.addWidget(btn_down)

        # Extension badge
        ext = os.path.splitext(file_path)[1].lstrip('.').upper() or "FILE"
        is_audio = ("." + ext.lower()) in self.SUPPORTED_AUDIO_EXTENSIONS
        b_col = "#4a9eff" if is_audio else "#38c172"
        b_bg = "#14253a" if is_audio else "#1a3a24"

        badge = QLabel(ext)
        badge.setFixedHeight(config.S(14))
        badge.setStyleSheet(f"""
            background-color: {b_bg}; color: {b_col};
            border-radius: {config.S(2)}px; padding: 0 {config.S(3)}px;
            font-size: {config.FS(6.5)}pt; font-weight: bold; font-family: '{config.UI_FONT_NAME}';
            border: none;
        """)
        r_lay.addWidget(badge)

        # Filename
        fname = os.path.basename(file_path)
        lbl_name = QLabel(fname)
        lbl_name.setToolTip(file_path)
        lbl_name.setStyleSheet(f"""
            color: #d4d4d4; font-size: {config.FS(7.5)}pt;
            font-family: '{config.UI_FONT_NAME}'; background: transparent; border: none;
        """)
        r_lay.addWidget(lbl_name, 1)

        # Duration
        dur_str = self._probe_duration_str(file_path)
        if dur_str:
            lbl_dur = QLabel(dur_str)
            lbl_dur.setStyleSheet(f"""
                color: #888888; font-size: {config.FS(7.0)}pt;
                font-family: '{config.UI_FONT_NAME}'; background: transparent; border: none;
            """)
            r_lay.addWidget(lbl_dur)

        # Remove single clip button
        btn_del = QPushButton("✕")
        btn_del.setFixedSize(config.S(14), config.S(14))
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setToolTip(_txt(self._lang, "tt_remove_clip_from_queue", "Remove this clip from queue"))
        btn_del.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: #707070; border: none;
                font-size: {config.FS(7.5)}pt; font-weight: bold; padding: 0;
            }}
            QPushButton:hover {{ color: #ff5555; }}
        """)
        btn_del.clicked.connect(lambda _, i=idx: self.remove_file(i))
        r_lay.addWidget(btn_del)

        return row_widget

    # ── Queue Modification APIs ───────────────────────────────────────────────
    def get_file(self) -> str:
        """Returns the first file path (for backward compatibility)."""
        return self._files[0] if self._files else ""

    def get_files(self) -> list[str]:
        """Returns the complete ordered list of media files in the queue."""
        return list(self._files)

    def set_file(self, file_path: str):
        """Sets a single file, replacing the existing queue."""
        if file_path:
            self.set_files([file_path])
        else:
            self.clear_files()

    def set_files(self, file_paths: list[str]):
        """Replaces the queue with the provided list of files."""
        valid = []
        for fp in file_paths:
            if fp and os.path.isfile(fp) and self.is_supported_file(fp):
                abs_p = os.path.abspath(fp)
                if abs_p not in valid:
                    valid.append(abs_p)

        if not valid and file_paths:
            self.shake()
            return

        self._files = valid
        self._update_state()
        self.file_selected.emit(self.get_file())
        self.files_changed.emit(self.get_files())

    def add_files(self, file_paths: list[str]):
        """Appends new files to the existing queue."""
        added = False
        for fp in file_paths:
            if fp and os.path.isfile(fp) and self.is_supported_file(fp):
                abs_p = os.path.abspath(fp)
                if abs_p not in self._files:
                    self._files.append(abs_p)
                    added = True

        if added:
            self._update_state()
            self.file_selected.emit(self.get_file())
            self.files_changed.emit(self.get_files())
        elif file_paths:
            self.shake()

    def remove_file(self, index: int):
        """Removes a file at the specified index."""
        if 0 <= index < len(self._files):
            self._files.pop(index)
            self._update_state()
            self.file_selected.emit(self.get_file())
            self.files_changed.emit(self.get_files())

    def move_file(self, from_idx: int, to_idx: int):
        """Reorders a file in the queue."""
        if 0 <= from_idx < len(self._files) and 0 <= to_idx < len(self._files):
            item = self._files.pop(from_idx)
            self._files.insert(to_idx, item)
            self._update_state()
            self.files_changed.emit(self.get_files())

    def clear_file(self):
        self.clear_files()

    def clear_files(self):
        """Empties the queue."""
        if not self._files:
            return
        self._files.clear()
        self._update_state()
        self.file_selected.emit("")
        self.files_changed.emit([])

    # ── Mouse & Drag-Drop Interaction ─────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._files:
            self.browse_files(append=False)
        super().mousePressEvent(event)

    def browse_files(self, append: bool = False):
        video_patterns = " ".join(f"*{ext}" for ext in self.SUPPORTED_VIDEO_EXTENSIONS)
        audio_patterns = " ".join(f"*{ext}" for ext in self.SUPPORTED_AUDIO_EXTENSIONS)
        all_patterns = f"{video_patterns} {audio_patterns}"
        media_txt = _txt(self._lang, "lbl_media_files", "Media files")
        video_txt = _txt(self._lang, "lbl_video_files", "Video files")
        audio_txt = _txt(self._lang, "lbl_audio_files", "Audio files")
        dialog_title = _txt(self._lang, "dlg_choose_media_files", "Select video or audio files")
        filters = (
            f"{media_txt} ({all_patterns});;"
            f"{video_txt} ({video_patterns});;"
            f"{audio_txt} ({audio_patterns})"
        )
        paths, _ = QFileDialog.getOpenFileNames(
            self, dialog_title, "", filters
        )
        if paths:
            if append:
                self.add_files(paths)
            else:
                self.set_files(paths)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for u in urls:
                fp = u.toLocalFile()
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
            for u in urls:
                fp = u.toLocalFile()
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
            collected = []
            for u in urls:
                fp = u.toLocalFile()
                if fp and os.path.isfile(fp) and self.is_supported_file(fp):
                    collected.append(fp)

            if collected:
                if self._files:
                    self.add_files(collected)
                else:
                    self.set_files(collected)
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

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        w = float(rect.width())
        h = float(rect.height())
        r = float(config.S(4))

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
        elif self._files:
            bg_color = QColor("#1a1a1a")
            border_color = QColor("#3a3a3a")
            pen_style = Qt.SolidLine
            pen_w = 1.0
        else:
            bg_color = QColor("#1a1a1a")
            border_color = QColor("#3a3a3a")
            pen_style = Qt.DashLine
            pen_w = 1.2

        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, w, h, r, r)
        p.fillPath(path, bg_color)

        pen = QPen(border_color, pen_w, pen_style)
        if pen_style == Qt.DashLine:
            pen.setDashPattern([4, 4])
        p.setPen(pen)

        half_w = pen_w / 2.0
        outline = QPainterPath()
        outline.addRoundedRect(half_w, half_w, w - pen_w, h - pen_w, r, r)
        p.drawPath(outline)

        p.end()
