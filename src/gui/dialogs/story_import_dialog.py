#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: story_import_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Paste an AI answer that lists sentence IDs from the AI-ready transcript; preview the
resulting edit and hand it to the next Assemble (story mode, issue #8).
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QCheckBox, QWidget, QFrame,
    QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtGui import QColor

import config
import algorithms
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import _txt, _center_on_screen


def _mmss(seconds):
    seconds = int(round(max(0.0, seconds)))
    return f"{seconds // 60}:{seconds % 60:02d}"


class StoryImportDialog(FramelessWindowMixin, _BaseDialog):
    """
    Usage:
        dlg = StoryImportDialog(parent, lang, sentences, duration_fn, note='')
        if dlg.exec() == QDialog.Accepted:
            dlg.result_story  # {'clips': [...], 'keep_source_order': bool, 'duration': float}
    duration_fn(clips, keep_source_order) -> seconds the assembled edit would last.
    """
    MAX_PREVIEW_CLIPS = 8

    def __init__(self, parent, lang, sentences, duration_fn, note=""):
        super().__init__(parent)
        self._lang = lang
        self._sentences = sentences
        self._duration_fn = duration_fn
        self._clips = []
        self.result_story = None

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.ApplicationModal)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; border-radius: {config.S(6)}px; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; }}
            QLabel#lbl_title {{ font-size: {config.FS(13)}pt; font-weight: bold; color: #ffffff; }}
            QLabel#lbl_hint {{ color: #a0a0a0; font-size: {config.FS(9)}pt; }}
            QLabel#lbl_note {{ color: #e0b050; font-size: {config.FS(9)}pt; }}
            QLabel#lbl_preview {{ color: #ffffff; font-weight: bold; font-size: {config.FS(10)}pt; }}
            QLabel#lbl_clips {{ color: #b0b0b0; font-size: {config.FS(9)}pt; }}
            QPlainTextEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: {config.S(3)}px;
                padding: {config.S(5)}px {config.S(8)}px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
            }}
            QPlainTextEdit:focus {{ border-color: {config.BTN_BG}; }}
            QCheckBox {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9)}pt; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: {config.S(6)}px {config.S(16)}px;
                border-radius: {config.S(4)}px;
                min-width: {config.S(80)}px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_ok {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_ok:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_ok:disabled {{ background-color: #2a2a2a; color: #666666; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(30))
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
        title_text = _txt(lang, "story_dlg_title")
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(title_text)
        root_layout.addWidget(self._tb)

        content = QWidget(self.inner_frame)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(config.S(20), config.S(20), config.S(20), config.S(20))
        content_layout.setSpacing(config.S(10))
        root_layout.addWidget(content)

        lbl_title = QLabel(title_text, content)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)

        lbl_hint = QLabel(_txt(lang, "story_dlg_hint"), content)
        lbl_hint.setObjectName("lbl_hint")
        lbl_hint.setWordWrap(True)
        content_layout.addWidget(lbl_hint)

        if note:
            lbl_note = QLabel(note, content)
            lbl_note.setObjectName("lbl_note")
            lbl_note.setWordWrap(True)
            content_layout.addWidget(lbl_note)

        self._edit = QPlainTextEdit(content)
        self._edit.setPlaceholderText(_txt(lang, "story_dlg_placeholder"))
        self._edit.setFixedHeight(config.S(170))
        content_layout.addWidget(self._edit)

        self._lbl_preview = QLabel("", content)
        self._lbl_preview.setObjectName("lbl_preview")
        content_layout.addWidget(self._lbl_preview)

        self._lbl_clips = QLabel("", content)
        self._lbl_clips.setObjectName("lbl_clips")
        self._lbl_clips.setWordWrap(True)
        self._lbl_clips.setTextFormat(Qt.RichText)
        content_layout.addWidget(self._lbl_clips)

        self._chk_source_order = QCheckBox(_txt(lang, "story_keep_order"), content)
        self._chk_source_order.setToolTip(_txt(lang, "tt_story_keep_order"))
        self._chk_source_order.toggled.connect(self._refresh)
        content_layout.addWidget(self._chk_source_order)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(_txt(lang, "btn_close"), content)
        btn_cancel.clicked.connect(self.reject)
        self._btn_ok = QPushButton(_txt(lang, "btn_story_use"), content)
        self._btn_ok.setObjectName("btn_ok")
        self._btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(config.S(8))
        btn_row.addWidget(self._btn_ok)
        content_layout.addLayout(btn_row)

        # Most people copy the AI answer right before opening this
        clip_text = QApplication.clipboard().text() or ""
        if algorithms.parse_story_answer(clip_text, len(sentences))[0] and "# BadWords transcript" not in clip_text:
            self._edit.setPlainText(clip_text)
        self._edit.textChanged.connect(self._refresh)
        self._refresh()

        self.setFixedWidth(config.S(560))
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    def _refresh(self):
        picks, unknown = algorithms.parse_story_answer(self._edit.toPlainText(), len(self._sentences))
        self._clips = algorithms.story_clips(picks, self._sentences)
        if not self._clips:
            self._lbl_preview.setText(_txt(self._lang, "story_none"))
            self._lbl_clips.setText("")
            self._btn_ok.setEnabled(False)
            return

        keep = self._chk_source_order.isChecked()
        self._duration = self._duration_fn(self._clips, keep)
        self._lbl_preview.setText(_txt(self._lang, "story_preview").format(
            clips=len(self._clips), sentences=len(picks), duration=_mmss(self._duration)))

        shown = sorted(self._clips, key=lambda c: c["first"]) if keep else self._clips
        rows = []
        for c in shown[:self.MAX_PREVIEW_CLIPS]:
            ids = c["start_id"] if c["start_id"] == c["end_id"] else f'{c["start_id"]}–{c["end_id"]}'
            text = c["text"] if len(c["text"]) <= 70 else c["text"][:69] + "…"
            rows.append(f"<b>{ids}</b>&nbsp;&nbsp;{html.escape(text)}")
        if len(shown) > self.MAX_PREVIEW_CLIPS:
            rows.append(f"+ {len(shown) - self.MAX_PREVIEW_CLIPS}")
        if unknown:
            shown_ids = ", ".join(dict.fromkeys(unknown).keys())
            rows.append(f'<span style="color:#e0b050">'
                        f'{html.escape(_txt(self._lang, "story_unknown").format(ids=shown_ids))}</span>')
        self._lbl_clips.setText("<br>".join(rows))
        self._btn_ok.setEnabled(self._duration > 0)
        self.adjustSize()

    def _on_ok(self):
        if not self._clips:
            return
        self.result_story = {
            "clips": [{"cut_start": c["cut_start"], "cut_end": c["cut_end"],
                       "start_id": c["start_id"], "end_id": c["end_id"]} for c in self._clips],
            "keep_source_order": self._chk_source_order.isChecked(),
            "duration": self._duration,
        }
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
