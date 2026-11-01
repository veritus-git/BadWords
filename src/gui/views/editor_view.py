#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: editor_view.py
ROLE: GUI View
DESCRIPTION:
Primary transcript editing view with scrollable TranscriptionCanvas, side-by-side loading overlay, and audio preview scrubber.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QStackedWidget, QPushButton
)
import config
from gui.components.transcription_canvas import TranscriptionCanvas
from gui.components.audio_preview import AudioPreviewWidget
from gui.components.waveform_timeline import WaveformTimelineWidget
from gui.widgets.progress_bar import LiquidProgressBar


def _build_workflow_bar(win, parent) -> QWidget:
    """Clean up -> Compose -> Send to Resolve: the three steps of an edit, always in view."""
    bar = QFrame(parent)
    bar.setObjectName("WorkflowBar")
    grad = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22d3ee, stop:1 #a855f7)"  # the StoryCraft gradient (brand.CYAN -> brand.VIOLET)
    grad_hi = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #67e8f9, stop:1 #c084fc)"
    bar.setStyleSheet(f"""
        QFrame#WorkflowBar {{ background-color: {config.BG_COLOR}; border: none; }}
        QPushButton#WfStep {{ background: transparent; border: none; border-radius: {config.S(16)}px; }}
        QPushButton#WfStep:hover {{ background: #262626; }}
        QPushButton#WfStep[active="true"] {{ background: #262626; }}
        QLabel#WfBadge {{ background: #2e2e2e; color: #9a9a9a; border-radius: {config.S(11)}px;
            font-size: {config.FS(8.5)}pt; font-weight: bold; }}
        QLabel#WfBadge[active="true"] {{ background: {grad}; color: #0b0b14; }}
        QLabel#WfStepText {{ color: #8f8f8f; font-family: 'Outfit'; font-size: {config.FS(10.5)}pt; font-weight: 600;
            background: transparent; }}
        QLabel#WfStepText[active="true"] {{ color: #ffffff; }}
        QPushButton#WfSend {{ background: {grad}; color: #0b0b14; border: none;
            border-top-left-radius: {config.S(16)}px; border-bottom-left-radius: {config.S(16)}px;
            border-top-right-radius: 0px; border-bottom-right-radius: 0px;
            padding: {config.S(7)}px {config.S(18)}px; font-size: {config.FS(10)}pt; font-weight: bold; }}
        QPushButton#WfSend:hover {{ background: {grad_hi}; }}
        QPushButton#WfSend:disabled {{ background: #2a2a2a; color: #666666; }}
        QPushButton#WfSendMore {{ background: #a855f7; color: #0b0b14; border: none;
            border-left: 1px solid rgba(11, 11, 20, 0.35); border-top-left-radius: 0px; border-bottom-left-radius: 0px;
            border-top-right-radius: {config.S(16)}px; border-bottom-right-radius: {config.S(16)}px;
            padding: {config.S(7)}px 0; font-size: {config.FS(9)}pt; font-weight: bold; }}
        QPushButton#WfSendMore:hover {{ background: #c084fc; }}
        QPushButton#WfSendMore:disabled {{ background: #2a2a2a; color: #666666; }}
        QPushButton#WfGear {{ background: transparent; color: #9a9a9a; border: none; border-radius: {config.S(15)}px;
            font-size: {config.FS(13)}pt; }}
        QPushButton#WfGear:hover {{ color: #ffffff; background: #262626; }}
    """)
    h = QHBoxLayout(bar)
    h.setContentsMargins(config.S(20), config.S(10), config.S(16), config.S(8))
    h.setSpacing(config.S(8))
    win.workflow_steps = {}
    for num, (key, tt, step) in enumerate((("wf_cleanup", "tt_wf_cleanup", "cleanup"),
                                            ("wf_compose", "tt_wf_compose", "compose")), start=1):
        # A pill: numbered badge + step name; the current step is filled
        b = QPushButton(bar)
        b.setObjectName("WfStep")
        b.setCursor(Qt.PointingHandCursor)
        b.setToolTip(win.txt(tt))
        hb = QHBoxLayout(b)
        hb.setContentsMargins(config.S(5), config.S(5), config.S(14), config.S(5))
        hb.setSpacing(config.S(8))
        badge = QLabel(str(num), b)
        badge.setObjectName("WfBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(config.S(22), config.S(22))
        text = QLabel(win.txt(key).split("  ", 1)[-1], b)
        text.setObjectName("WfStepText")
        hb.addWidget(badge)
        hb.addWidget(text)
        b.setMinimumHeight(config.S(32))
        b.setMinimumWidth(hb.sizeHint().width())
        b.clicked.connect(lambda _=False, s=step: win._on_workflow_step(s))
        win.workflow_steps[step] = (b, badge, text)
        h.addWidget(b)
        if step == "cleanup":
            line = QFrame(bar)
            line.setFixedSize(config.S(24), 2)
            line.setStyleSheet(f"background: #333333; border: none; border-radius: 1px;")
            h.addWidget(line)
    h.addStretch(1)
    # Resolve connection chip (filled by win._update_resolve_chip)
    win.lbl_resolve_chip = QLabel("", bar)
    win.lbl_resolve_chip.hide()
    h.addWidget(win.lbl_resolve_chip)
    h.addSpacing(config.S(6))
    win.lbl_workflow_summary = QLabel("", bar)
    win.lbl_workflow_summary.setStyleSheet(f"color: #9a9a9a; font-size: {config.FS(9)}pt; background: transparent;")
    h.addWidget(win.lbl_workflow_summary)
    win.btn_send_resolve = QPushButton(win.txt("btn_assemble"), bar)
    win.btn_send_resolve.setObjectName("WfSend")
    win.btn_send_resolve.setCursor(Qt.PointingHandCursor)
    win.btn_send_resolve.setToolTip(win.txt("tt_send_resolve"))
    win.btn_send_resolve.clicked.connect(lambda: win._on_assemble())
    h.addWidget(win.btn_send_resolve)
    win.btn_send_options = QPushButton("▾", bar)
    win.btn_send_options.setObjectName("WfSendMore")
    win.btn_send_options.setCursor(Qt.PointingHandCursor)
    win.btn_send_options.setToolTip(win.txt("btn_track_options"))
    win.btn_send_options.setFixedWidth(config.S(28))
    win.btn_send_options.clicked.connect(lambda: win._show_track_options())
    send = QHBoxLayout()
    send.setSpacing(0)
    send.addWidget(win.btn_send_resolve)
    send.addWidget(win.btn_send_options)
    h.removeWidget(win.btn_send_resolve)
    h.addLayout(send)
    # Settings (the icon rails are gone): top right, next to Send
    gear = QPushButton("\u2699", bar)
    gear.setObjectName("WfGear")
    gear.setCursor(Qt.PointingHandCursor)
    gear.setToolTip(win.txt("tool_settings"))
    gear.setFixedSize(config.S(32), config.S(32))
    gear.clicked.connect(lambda: win._on_settings())
    h.addSpacing(config.S(4))
    h.addWidget(gear)
    win._set_workflow_step("cleanup")
    return bar


def _build_mark_strip(win, parent) -> QWidget:
    """Marker chips (keys 1-9), how marking works, and Restore AI marks."""
    strip = QFrame(parent)
    strip.setObjectName("MarkStrip")
    strip.setStyleSheet(f"""
        QFrame#MarkStrip {{ background-color: {config.BG_COLOR}; border: none; }}
        QPushButton#MarkChip {{ background: #232323; color: #b8b8b8; border: 1px solid transparent;
            border-radius: {config.S(13)}px; padding: {config.S(3)}px {config.S(11)}px; font-size: {config.FS(9)}pt; }}
        QPushButton#MarkChip:hover {{ color: #ffffff; background: #2b2b2b; }}
        QPushButton#MarkChip:checked {{ color: #ffffff; background: #2e2e2e; border-color: {config.BTN_BG}; font-weight: bold; }}
        QPushButton#MarkChip:disabled {{ color: #555555; }}
        QPushButton#RestoreAI {{ background: transparent; color: #a8a8a8; border: none;
            border-radius: {config.S(13)}px; padding: {config.S(3)}px {config.S(10)}px; font-size: {config.FS(9)}pt; }}
        QPushButton#RestoreAI:hover {{ color: #ffffff; background: #262626; }}
    """)
    h = QHBoxLayout(strip)
    h.setContentsMargins(config.S(20), config.S(2), config.S(16), config.S(10))
    h.setSpacing(config.S(6))
    lbl = QLabel(win.txt("mark_with"), strip)
    lbl.setStyleSheet(f"color: #8a8a8a; font-size: {config.FS(9)}pt; background: transparent;")
    h.addWidget(lbl)
    chips = QHBoxLayout()
    chips.setSpacing(config.S(6))
    win.mark_strip_chips = chips
    h.addLayout(chips)
    h.addStretch(1)
    hint = QLabel(win.txt("mark_hint"), strip)
    hint.setStyleSheet(f"color: #777777; font-size: {config.FS(8.5)}pt; background: transparent;")
    h.addWidget(hint)
    btn = QPushButton(win.txt("btn_restore_ai"), strip)
    btn.setObjectName("RestoreAI")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setToolTip(win.txt("tt_restore_ai"))
    btn.clicked.connect(lambda: win._restore_all_ai_marks())
    h.addWidget(btn)
    if hasattr(win, '_rebuild_mark_strip'):
        win._rebuild_mark_strip()
    return strip


def build_editor_view(win) -> QWidget:
    """Build Page 2 of the main stack: Interactive Transcript Editor screen."""
    page = QWidget()
    page.setObjectName("page_editor")
    page.setStyleSheet(f"QWidget#page_editor {{ background-color: {config.BG_COLOR}; }}")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    
    win.scroll_area = QScrollArea(page)
    win.scroll_area.setWidgetResizable(True)
    win.scroll_area.setFrameShape(QFrame.NoFrame)
    win.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    win.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {config.BG_COLOR}; border: none; }}")
    
    win.text_canvas = TranscriptionCanvas(main_window=win)
    win.scroll_area.setWidget(win.text_canvas)

    normal_editor_page = QWidget()
    normal_editor_layout = QVBoxLayout(normal_editor_page)
    normal_editor_layout.setContentsMargins(0, 0, 0, 0)
    normal_editor_layout.setSpacing(0)
    normal_editor_layout.addWidget(win.scroll_area)

    win.sbs_loading_page = QWidget()
    win.sbs_loading_page.setStyleSheet(f"background-color: {config.BG_COLOR};")
    ol_layout = QVBoxLayout(win.sbs_loading_page)
    ol_layout.setAlignment(Qt.AlignCenter)
    
    lbl = QLabel(win.txt("lbl_just_a_second"))
    lbl.setStyleSheet(f"color: {config.NOTE_COL}; font-size: {config.FS(13)}pt; font-family: '{config.UI_FONT_NAME}'; background: transparent;")
    lbl.setAlignment(Qt.AlignCenter)
    ol_layout.addWidget(lbl)
    
    ol_layout.addSpacing(config.S(15))
    
    win.sbs_loading_bar = LiquidProgressBar(win.sbs_loading_page)
    win.sbs_loading_bar.setFixedWidth(config.S(400))
    ol_layout.addWidget(win.sbs_loading_bar, 0, Qt.AlignCenter)

    win.editor_view_stack = QStackedWidget(page)
    win.editor_view_stack.setStyleSheet("background: transparent;")
    win.editor_view_stack.addWidget(normal_editor_page)
    win.editor_view_stack.addWidget(win.sbs_loading_page)
    layout.addWidget(_build_workflow_bar(win, page))
    layout.addWidget(_build_mark_strip(win, page))
    layout.addWidget(win.editor_view_stack)
    
    return page
