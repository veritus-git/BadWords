#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: welcome_view.py
ROLE: GUI View
DESCRIPTION:
Welcome screen with transcription settings, model chooser, more accurate slide-out, and standalone fast silence mode.
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QLineEdit, QTextEdit, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QCursor

import config
from gui.widgets.buttons import CustomDropdown, SearchableDropdown, MultiSelectDropdown, ToggleSwitch


def build_welcome_view(win) -> QWidget:
    """Build Page 0 of the main stack: Welcome / Configuration screen."""
    prefs = win.engine.load_preferences() or {}
    page = QWidget()
    page.setObjectName("page_welcome")
    page.setStyleSheet(f"QWidget#page_welcome {{ background-color: {config.BG_COLOR}; }}")

    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    inner = QWidget()
    inner.setObjectName("welcome_inner")
    inner.setStyleSheet("QWidget#welcome_inner { background: transparent; }")

    inner_layout = QVBoxLayout(inner)
    inner_layout.setContentsMargins(0, 0, 0, 0)
    inner_layout.setSpacing(0)
    inner_layout.setAlignment(Qt.AlignTop)

    # ── Shared Title ─────────────────────────────────────────────────
    lbl_title = QLabel("BadWords", inner)
    lbl_title.setObjectName("welcome_title")
    lbl_title.setAlignment(Qt.AlignCenter)
    lbl_title.setStyleSheet(f"""
        QLabel#welcome_title {{
            color: #ffffff;
            font-size: 34pt;
            font-weight: 900;
            font-family: {config.UI_FONT_NAME};
            background: transparent;
            letter-spacing: -2px;
        }}
    """)
    inner_layout.addWidget(lbl_title)
    inner_layout.addSpacing(10)

    # ── Local stacked widget ──────────────────────────────────────────
    win.welcome_stack = QStackedWidget()
    win.welcome_stack.setStyleSheet("background: transparent;")
    inner_layout.addWidget(win.welcome_stack)

    def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(3)
        lbl = QLabel(label_text)
        lbl.setFixedHeight(16)
        lbl.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 9pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
        )
        row.addWidget(lbl)
        row.addWidget(widget)
        return row

    p_transcription = QWidget()
    p_transcription.setStyleSheet("background: transparent;")
    l_trans = QVBoxLayout(p_transcription)
    l_trans.setContentsMargins(0, 0, 0, 0)
    l_trans.setSpacing(0)
    l_trans.setAlignment(Qt.AlignTop)

    lbl_sub = QLabel(win.txt("lbl_transcription_workspace"))
    lbl_sub.setAlignment(Qt.AlignCenter)
    lbl_sub.setFixedHeight(20)
    lbl_sub.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 10pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
    )
    l_trans.addWidget(lbl_sub)
    l_trans.addSpacing(20)

    win.slider_widget = QWidget()
    win.slider_widget.setStyleSheet("background: transparent;")
    win.slider_layout = QHBoxLayout(win.slider_widget)
    win.slider_layout.setContentsMargins(0, 0, 0, 0)
    win.slider_layout.setSpacing(0)
    win.slider_layout.setAlignment(Qt.AlignTop)
    
    win.settings_container = QWidget()
    win.settings_container.setFixedWidth(310)
    win.settings_container.setStyleSheet("background: transparent;")
    win.settings_layout = QVBoxLayout(win.settings_container)
    win.settings_layout.setContentsMargins(0, 0, 0, 0)
    win.settings_layout.setSpacing(0)
    win.settings_layout.setAlignment(Qt.AlignTop)
    win.slider_layout.addWidget(win.settings_container)

    win.combo_tl_0 = CustomDropdown([])
    win.combo_tl_0.setFixedHeight(30)
    win.combo_tl_0.valueChanged.connect(
        lambda tl: win._on_timeline_selected(tl, win.combo_tr_0, win.combo_tl_1)
    )
    _vbox_tl0 = QVBoxLayout()
    _vbox_tl0.setContentsMargins(0, 0, 0, 0)
    _vbox_tl0.setSpacing(3)
    _lbl_tl0 = QLabel(win.txt("lbl_timeline_selection"))
    _lbl_tl0.setFixedHeight(16)
    _lbl_tl0.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 9pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    _hbox_tl0 = QHBoxLayout()
    _hbox_tl0.setContentsMargins(0, 0, 0, 0)
    _hbox_tl0.setSpacing(4)
    _hbox_tl0.addWidget(win.combo_tl_0, 1)
    _btn_ref_tl0 = QPushButton("↺")
    _btn_ref_tl0.setFixedSize(30, 30)
    _btn_ref_tl0.setCursor(Qt.PointingHandCursor)
    _btn_ref_tl0.setToolTip(win.txt("tt_refresh_timelines"))
    _btn_ref_tl0.setStyleSheet(
        "QPushButton { background: transparent; border: 1px solid #444; "
        "border-radius: 3px; color: #777; font-size: 11pt; } "
        "QPushButton:hover { color: #ccc; border-color: #666; }"
    )
    _btn_ref_tl0.clicked.connect(win._populate_timeline_track_combos)
    _hbox_tl0.addWidget(_btn_ref_tl0)
    _vbox_tl0.addWidget(_lbl_tl0)
    _vbox_tl0.addLayout(_hbox_tl0)
    win.settings_layout.addLayout(_vbox_tl0)
    win.settings_layout.addSpacing(10)

    win.combo_tr_0 = MultiSelectDropdown([])
    win.combo_tr_0.setFixedHeight(30)
    win.settings_layout.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_0))
    win.settings_layout.addSpacing(10)

    # Language
    lang_items = list(config.SUPPORTED_LANGUAGES.values())
    win._combo_lang = SearchableDropdown(lang_items)
    win._combo_lang.setFixedHeight(30)
    saved_lang = prefs.get('lang', '')
    display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
    placeholder = win.txt("lbl_choose_recording_language") if hasattr(win, 'txt') else "Choose recording language"
    win._combo_lang.setText(display_name if display_name in lang_items else placeholder)
    win._combo_lang.valueChanged.connect(lambda v: win.engine.save_preferences({"lang": v}))
    win.settings_layout.addLayout(_row(win.txt("lbl_lang"), win._combo_lang))
    win.settings_layout.addSpacing(10)

    # Model
    model_items = [
        "Tiny (I wouldn't, ~0.3GB)",
        "Base (Dogsh!t, ~0.5GB)",
        "Small (Bearable, ~1.0GB)",
        "Medium (Okayish, ~2.5GB)",
        "Large Turbo (Best Balance, ~2.5GB)",
        "Large (Recommended, ~3.5GB)",
    ]
    win._combo_model = CustomDropdown(model_items)
    win._combo_model.max_visible_items = 6
    win._combo_model.setFixedHeight(30)
    
    saved_model = prefs.get("model", "")
    if saved_model in model_items:
        win._combo_model.setText(saved_model)
    else:
        win._combo_model.setText(model_items[4])
        win.engine.save_preferences({"model": model_items[4]})
        
    win._combo_model.valueChanged.connect(lambda v: win.engine.save_preferences({"model": v}))
    
    info_model = QLabel()
    _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    _prod_assets_dir = os.path.join(_src_dir, "layout")
    _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
    _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
    info_icon_path = os.path.join(_assets_dir, "information.png")
    if os.path.exists(info_icon_path):
        info_model.setPixmap(QPixmap(info_icon_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        info_model.setText("🛈")
        info_model.setStyleSheet("color: #888888; font-size: 11pt;")
        
    info_model.custom_tooltip_text = f"<div style='max-width: 320px; white-space: pre-wrap;'>{win.txt('tt_model_size_info')}</div>"
    info_model.setCursor(Qt.WhatsThisCursor)
    
    def instant_tooltip_model(event):
        if hasattr(win, 'shared_tooltip'):
            win.shared_tooltip.show_global(info_model.custom_tooltip_text, QCursor.pos())
    info_model.enterEvent = instant_tooltip_model
    info_model.leaveEvent = lambda e: win.shared_tooltip.hide() if hasattr(win, 'shared_tooltip') else None
    info_model.installEventFilter(win)
    
    row_model_lbl = QHBoxLayout()
    row_model_lbl.setContentsMargins(0, 0, 0, 0)
    row_model_lbl.setSpacing(5)
    lbl_model = QLabel(win.txt("lbl_model"))
    lbl_model.setFixedHeight(16)
    lbl_model.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 9pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    row_model_lbl.addWidget(lbl_model)
    row_model_lbl.addWidget(info_model)
    row_model_lbl.addStretch()
    
    vbox_model = QVBoxLayout()
    vbox_model.setContentsMargins(0, 0, 0, 0)
    vbox_model.setSpacing(3)
    vbox_model.addLayout(row_model_lbl)
    vbox_model.addWidget(win._combo_model)
    
    win.settings_layout.addLayout(vbox_model)
    win.settings_layout.addSpacing(15)

    # More Accurate Mode
    win.tgl_more_accurate = ToggleSwitch()
    is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))
    win.tgl_more_accurate.setChecked(is_more_accurate)
    win.tgl_more_accurate.toggled.connect(win._on_more_accurate_toggled)
    
    lbl_acc = QLabel(win.txt("lbl_more_accurate"))
    lbl_acc.setStyleSheet(f"color: {config.FG_COLOR}; font-family: {config.UI_FONT_NAME}; font-size: 10pt;")
    
    info_acc = QLabel()
    if os.path.exists(info_icon_path):
        info_acc.setPixmap(QPixmap(info_icon_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    else:
        info_acc.setText("🛈")
        info_acc.setStyleSheet("color: #888888; font-size: 11pt;")
    tt_acc_text = win.txt("tt_more_accurate")
    info_acc.custom_tooltip_text = f"<div style='max-width: 350px; white-space: pre-wrap;'>{tt_acc_text}</div>"
    info_acc.setCursor(Qt.WhatsThisCursor)
    
    def instant_tooltip_acc(event):
        if hasattr(win, 'shared_tooltip'):
            win.shared_tooltip.show_global(info_acc.custom_tooltip_text, QCursor.pos())
    info_acc.enterEvent = instant_tooltip_acc
    info_acc.leaveEvent = lambda e: win.shared_tooltip.hide() if hasattr(win, 'shared_tooltip') else None
    
    row_acc = QHBoxLayout()
    row_acc.setSpacing(0)
    row_acc.addWidget(lbl_acc)
    row_acc.addStretch()
    row_acc.addWidget(info_acc)
    row_acc.addSpacing(6)
    row_acc.addWidget(win.tgl_more_accurate)
    
    win.settings_layout.addLayout(row_acc)
    win.settings_layout.addSpacing(24)

    # Script Container
    win.script_container = QWidget()
    win.script_container.setFixedWidth(350 if is_more_accurate else 0)
    win.script_container.setStyleSheet("background: transparent;")
    
    win.script_container_layout = QHBoxLayout(win.script_container)
    win.script_container_layout.setContentsMargins(15, 0, 15, 0)
    win.script_container_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
    
    win.script_content_widget = QWidget()
    win.script_content_widget.setFixedWidth(320)
    win.script_layout = QVBoxLayout(win.script_content_widget)
    win.script_layout.setContentsMargins(0, 0, 0, 0)
    win.script_layout.setSpacing(0)
    win.script_layout.setAlignment(Qt.AlignTop)
    
    _lbl_script = QLabel(win.txt("lbl_script"))
    _lbl_script.setFixedHeight(16)
    _lbl_script.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 9pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    win.script_layout.addWidget(_lbl_script)
    win.script_layout.addSpacing(3)
    
    win.welcome_script_edit = QTextEdit()
    win.welcome_script_edit.setFixedHeight(247)
    win.welcome_script_edit.setAcceptRichText(False)
    win.welcome_script_edit.setStyleSheet(f'''
        QTextEdit {{
            background-color: #1e1e1e; color: #d4d4d4; 
            border: 1px solid #3a3a3a; border-radius: 3px; 
            padding: 4px; outline: none; font-family: {config.UI_FONT_NAME};
        }}
        QTextEdit:focus {{ border: 1px solid #1a7a3e; }}
    ''')
    win.script_layout.addWidget(win.welcome_script_edit)
    
    win.btn_import_welcome_script = QPushButton(win.txt("btn_import_script"))
    win.btn_import_welcome_script.setObjectName("btn_ghost")
    win.btn_import_welcome_script.setCursor(Qt.PointingHandCursor)
    win.btn_import_welcome_script.setFixedHeight(30)
    win.btn_import_welcome_script.setStyleSheet(f"""
        QPushButton#btn_ghost {{
            background-color: #1e1e1e; color: {config.FG_COLOR};
            font-family: {config.UI_FONT_NAME}; font-size: 10pt;
            border: 1px solid #3a3a3a; border-radius: 3px; padding: 0 12px;
        }}
        QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
        QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
    """)
    win.btn_import_welcome_script.clicked.connect(win._on_import_script)
    win.script_container_layout.addWidget(win.script_content_widget)
    
    win.slider_layout.addWidget(win.script_container)
    
    h_slider = QHBoxLayout()
    h_slider.setContentsMargins(0, 0, 0, 0)
    h_slider.addStretch()
    h_slider.addWidget(win.slider_widget)
    h_slider.addStretch()
    l_trans.addLayout(h_slider)
    
    win.settings_container.raise_()

    # Action buttons
    btn_row_t = QHBoxLayout()
    btn_row_t.setContentsMargins(0, 0, 0, 0)
    btn_row_t.setSpacing(0)

    btn_import = QPushButton(win.txt("btn_import_project"))
    btn_import.setObjectName("btn_ghost")
    btn_import.setCursor(Qt.PointingHandCursor)
    btn_import.setFixedHeight(30)
    btn_import.setStyleSheet(f"""
        QPushButton#btn_ghost {{
            background-color: #1e1e1e; color: {config.FG_COLOR};
            font-family: {config.UI_FONT_NAME}; font-size: 10pt;
            border: 1px solid #3a3a3a; border-radius: 3px; padding: 0 12px;
        }}
        QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
        QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
    """)
    btn_import.clicked.connect(win._on_import_project)
    btn_row_t.addWidget(btn_import)

    btn_analyze = QPushButton("▶ " + win.txt("btn_analyze"))
    btn_analyze.setObjectName("btn_primary")
    btn_analyze.setCursor(Qt.PointingHandCursor)
    btn_analyze.setFixedHeight(30)
    btn_analyze.setStyleSheet(f"""
        QPushButton#btn_primary {{
            background-color: {config.BTN_BG}; color: #ffffff;
            font-family: {config.UI_FONT_NAME}; font-size: 10pt; font-weight: bold;
            border: none; border-radius: 3px; padding: 0 18px;
        }}
        QPushButton#btn_primary:hover {{ background-color: {config.BTN_ACTIVE}; }}
        QPushButton#btn_primary:pressed {{ background-color: #176e38; }}
    """)
    btn_analyze.clicked.connect(win._on_start_analysis)
    btn_row_t.addSpacing(8)
    btn_row_t.addWidget(btn_analyze)
    
    win.btn_import_wrapper = QWidget()
    wrapper_l = QHBoxLayout(win.btn_import_wrapper)
    wrapper_l.setContentsMargins(8, 0, 0, 0)
    wrapper_l.setSpacing(0)
    wrapper_l.addWidget(win.btn_import_welcome_script)
    btn_row_t.addWidget(win.btn_import_wrapper)
    
    win.btn_import_wrapper.setVisible(prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False)))
    
    btn_row_t_centered = QHBoxLayout()
    btn_row_t_centered.setContentsMargins(0, 0, 0, 0)
    btn_row_t_centered.addStretch()
    btn_row_t_centered.addLayout(btn_row_t)
    btn_row_t_centered.addStretch()
    
    l_trans.addLayout(btn_row_t_centered)
    l_trans.addSpacing(14)

    btn_switch_fast = QPushButton(win.txt("btn_standalone_silence_detection"))
    btn_switch_fast.setCursor(Qt.PointingHandCursor)
    btn_switch_fast.setStyleSheet(
        f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
        " font-size: 9pt; text-decoration: underline; border: none; padding: 0;"
    )
    btn_switch_fast.clicked.connect(lambda: win.welcome_stack.setCurrentIndex(1))
    l_trans.addWidget(btn_switch_fast, 0, Qt.AlignCenter)
    l_trans.addStretch()
    
    win.welcome_stack.addWidget(p_transcription)

    # ═══════════════════════════════════════════════════════════════
    # SUB-PAGE 1: FAST SILENCE
    # ═══════════════════════════════════════════════════════════════
    p_fast_outer = QWidget()
    p_fast_outer.setStyleSheet("background: transparent;")
    p_fast_layout = QHBoxLayout(p_fast_outer)
    p_fast_layout.setContentsMargins(0, 0, 0, 0)
    p_fast_layout.setSpacing(0)
    
    p_fast = QWidget()
    p_fast.setFixedWidth(310)
    p_fast.setStyleSheet("background: transparent;")
    l_fast = QVBoxLayout(p_fast)
    l_fast.setContentsMargins(0, 0, 0, 0)
    l_fast.setSpacing(0)
    l_fast.setAlignment(Qt.AlignTop)
    
    p_fast_layout.addStretch()
    p_fast_layout.addWidget(p_fast)
    p_fast_layout.addStretch()

    lbl_fs_title = QLabel(win.txt("lbl_standalone_silence_workspace"))
    lbl_fs_title.setAlignment(Qt.AlignCenter)
    lbl_fs_title.setFixedHeight(20)
    lbl_fs_title.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 10pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
    )
    l_fast.addWidget(lbl_fs_title)
    l_fast.addSpacing(20)

    win.combo_tl_1 = CustomDropdown([])
    win.combo_tl_1.setFixedHeight(30)
    win.combo_tl_1.valueChanged.connect(
        lambda tl: win._on_timeline_selected(tl, win.combo_tr_1, win.combo_tl_0)
    )
    _vbox_tl1 = QVBoxLayout()
    _vbox_tl1.setContentsMargins(0, 0, 0, 0)
    _vbox_tl1.setSpacing(3)
    _lbl_tl1 = QLabel(win.txt("lbl_timeline_selection"))
    _lbl_tl1.setStyleSheet(
        f"color: {config.NOTE_COL}; font-size: 9pt;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
    )
    _hbox_tl1 = QHBoxLayout()
    _hbox_tl1.setContentsMargins(0, 0, 0, 0)
    _hbox_tl1.setSpacing(4)
    _hbox_tl1.addWidget(win.combo_tl_1, 1)
    _btn_ref_tl1 = QPushButton("↺")
    _btn_ref_tl1.setFixedSize(30, 30)
    _btn_ref_tl1.setCursor(Qt.PointingHandCursor)
    _btn_ref_tl1.setToolTip(win.txt("tt_refresh_timelines"))
    _btn_ref_tl1.setStyleSheet(
        "QPushButton { background: transparent; border: 1px solid #444; "
        "border-radius: 3px; color: #777; font-size: 11pt; } "
        "QPushButton:hover { color: #ccc; border-color: #666; }"
    )
    _btn_ref_tl1.clicked.connect(win._populate_timeline_track_combos)
    _hbox_tl1.addWidget(_btn_ref_tl1)
    _vbox_tl1.addWidget(_lbl_tl1)
    _vbox_tl1.addLayout(_hbox_tl1)
    l_fast.addLayout(_vbox_tl1)
    l_fast.addSpacing(10)

    win.combo_tr_1 = MultiSelectDropdown([])
    win.combo_tr_1.setFixedHeight(30)
    l_fast.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_1))
    l_fast.addSpacing(10)

    input_style = '''
        QLineEdit {
            background-color: #1e1e1e; color: #d4d4d4; 
            border: 1px solid #3a3a3a; border-radius: 3px; 
            padding: 4px 8px;
            outline: none;
        }
        QLineEdit:focus { border: 1px solid #1a7a3e; outline: none; }
    '''

    def _row_rst(label_text, widget, reset_val_str):
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(3)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 9pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        vbox.addWidget(lbl)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(4)
        hbox.addWidget(widget, 1)

        rst = QPushButton("↺")
        rst.setFixedSize(22, 22)
        rst.setCursor(Qt.PointingHandCursor)
        rst.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid #444; "
            "border-radius: 3px; color: #777; font-size: 10pt; } "
            "QPushButton:hover { color: #ccc; border-color: #666; }"
        )
        rst.clicked.connect(lambda: widget.setText(reset_val_str))
        rst.setToolTip(win.txt("tt_reset_to_default"))
        hbox.addWidget(rst)
        vbox.addLayout(hbox)
        return vbox

    win.input_fs_thresh = QLineEdit()
    win.input_fs_thresh.setText(str(prefs.get('silence_threshold_db', prefs.get('ui_spin_thresh', -42.0))))
    win.input_fs_thresh.setStyleSheet(input_style)
    win.input_fs_thresh.setFixedHeight(30)
    l_fast.addLayout(_row_rst(win.txt("lbl_silence_threshold_db"), win.input_fs_thresh, "-42.0"))
    l_fast.addSpacing(10)

    win.input_fs_pad = QLineEdit()
    win.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.05)))
    win.input_fs_pad.setStyleSheet(input_style)
    win.input_fs_pad.setFixedHeight(30)
    l_fast.addLayout(_row_rst(win.txt("lbl_padding_s"), win.input_fs_pad, "0.05"))
    l_fast.addSpacing(10)

    win.input_fs_min_dur = QLineEdit()
    win.input_fs_min_dur.setText(str(prefs.get('silence_min_dur', 0.2)))
    win.input_fs_min_dur.setStyleSheet(input_style)
    win.input_fs_min_dur.setFixedHeight(30)
    win.input_fs_min_dur.setToolTip(
        "Minimum gap duration (s) to classify as silence. "
        "Lower = more gaps detected. Shared with post-transcript mode."
    )
    l_fast.addLayout(_row_rst(win.txt("lbl_min_silence_dur"), win.input_fs_min_dur, "0.2"))
    l_fast.addSpacing(16)

    # MODE TOGGLES
    row_fs_cut = QHBoxLayout()
    lbl_fs_cut = QLabel(win.txt("lbl_cut_silence_directly"))
    lbl_fs_cut.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
    row_fs_cut.addWidget(lbl_fs_cut)
    row_fs_cut.addStretch()
    info_fs_cut = win._create_info_icon("tt_cut_silence_directly")
    row_fs_cut.addWidget(info_fs_cut)
    row_fs_cut.addSpacing(6)
    win.tgl_fs_cut = ToggleSwitch()
    win.tgl_fs_cut.setChecked(prefs.get('fs_cut_mode', True), animated=False)
    row_fs_cut.addWidget(win.tgl_fs_cut)
    l_fast.addLayout(row_fs_cut)
    l_fast.addSpacing(10)

    row_fs_mark = QHBoxLayout()
    lbl_fs_mark = QLabel(win.txt("lbl_mark_silence_with_color"))
    lbl_fs_mark.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
    row_fs_mark.addWidget(lbl_fs_mark)
    row_fs_mark.addStretch()
    info_fs_mark = win._create_info_icon("tt_mark_silence_with_color")
    row_fs_mark.addWidget(info_fs_mark)
    row_fs_mark.addSpacing(6)
    win.tgl_fs_mark = ToggleSwitch()
    win.tgl_fs_mark.setChecked(prefs.get('fs_mark_mode', False), animated=False)
    row_fs_mark.addWidget(win.tgl_fs_mark)
    l_fast.addLayout(row_fs_mark)
    l_fast.addSpacing(24)

    win.tgl_fs_cut.toggled.connect(lambda c: win.tgl_fs_mark.setChecked(False) if c else None)
    win.tgl_fs_mark.toggled.connect(lambda c: win.tgl_fs_cut.setChecked(False) if c else None)
    win.tgl_fs_cut.toggled.connect(lambda v: win._save_single_pref('fs_cut_mode', v))
    win.tgl_fs_mark.toggled.connect(lambda v: win._save_single_pref('fs_mark_mode', v))

    btn_row_fs = QHBoxLayout()
    btn_row_fs.setContentsMargins(0, 0, 0, 0)

    btn_back = QPushButton(f"← {win.txt('btn_back_to_transcription')}")
    btn_back.setCursor(Qt.PointingHandCursor)
    btn_back.setStyleSheet(
        f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
        " font-size: 9pt; text-decoration: underline; border: none; padding: 0; text-align: left;"
    )
    btn_back.clicked.connect(lambda: win.welcome_stack.setCurrentIndex(0))
    btn_row_fs.addWidget(btn_back)
    btn_row_fs.addStretch()

    win.btn_run_fs = QPushButton(win.txt("btn_run_standalone_silence"))
    win.btn_run_fs.setCursor(Qt.PointingHandCursor)
    win.btn_run_fs.setFixedHeight(30)
    win.btn_run_fs.setStyleSheet(f'''
        QPushButton {{
            background-color: {config.BTN_BG}; color: #ffffff;
            font-family: {config.UI_FONT_NAME}; font-size: 10pt; font-weight: bold;
            border: none; border-radius: 3px; padding: 0 18px;
        }}
        QPushButton:hover {{ background-color: {config.BTN_ACTIVE}; }}
        QPushButton:pressed {{ background-color: #176e38; }}
    ''')
    win.btn_run_fs.clicked.connect(win._on_fast_silence)
    btn_row_fs.addWidget(win.btn_run_fs)
    
    l_fast.addLayout(btn_row_fs)
    l_fast.addStretch()

    win.welcome_stack.addWidget(p_fast_outer)

    # Centre horizontally
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    h.addStretch()
    h.addWidget(inner)
    h.addStretch()
    outer.addLayout(h)

    outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
    return page
