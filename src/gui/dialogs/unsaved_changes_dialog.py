#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: unsaved_changes_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Confirmation dialog for review and save/discard of modified settings.
"""

import html

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QWidget, QSizePolicy
)

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.dialogs.settings_widgets import (
    SETTINGS_VIEWPORT_BG, SETTINGS_CARD_BG, SETTINGS_CARD_BORDER,
    SETTINGS_DIVIDER_COL, scope_transparent,
)
from gui.utils import _center_on_screen, _txt


class UnsavedChangesDialog(FramelessWindowMixin, _BaseDialog):
    def __init__(self, parent, diff_dict, key_name_map):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        tb_lang = getattr(parent, 'lang', None) or getattr(parent, '_lang', None)
        if not tb_lang and hasattr(parent, 'engine') and parent.engine:
            try:
                tb_lang = (parent.engine.load_preferences() or {}).get('gui_lang', 'en')
            except Exception:
                tb_lang = 'en'
        tb_lang = tb_lang or "en"

        def _tr(key: str, default: str = "") -> str:
            if parent is not None and hasattr(parent, 'txt') and callable(parent.txt):
                val = parent.txt(key)
                if val and val != key:
                    return val
            return _txt(tb_lang, key) or default or key

        self.setStyleSheet(f"""
            QDialog {{ background-color: {SETTINGS_VIEWPORT_BG}; }}
            #MainInnerFrame {{
                background-color: {SETTINGS_VIEWPORT_BG};
                border: 1px solid #2e2e2e;
                border-radius: 0px;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                font-size: {config.FS_PX(10)}px;
                background: transparent;
                border: none;
            }}
            QFrame#UnsavedCard {{
                background-color: {SETTINGS_CARD_BG};
                border: 1px solid {SETTINGS_CARD_BORDER};
                border-radius: {config.S(8)}px;
            }}
            QWidget#UnsavedFooterBar {{
                background-color: #202020;
            }}
            QPushButton {{
                outline: none;
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
            }}
            QPushButton#btn_apply {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                border: none;
                border-radius: {config.S(5)}px;
                font-weight: bold;
                font-size: {config.FS_PX(9.8)}px;
                padding: 0px {config.S(16)}px;
            }}
            QPushButton#btn_apply:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_apply:pressed {{ background-color: #125c2f; }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                color: #d4d4d4;
                border: 1px solid #484848;
                border-radius: {config.S(5)}px;
                font-size: {config.FS_PX(9.5)}px;
                padding: 0px {config.S(14)}px;
            }}
            QPushButton#btn_secondary:hover {{ background-color: #2c2f30; border-color: #777777; color: #ffffff; }}
            QPushButton#btn_ghost_sm {{
                background-color: transparent;
                color: #b0b0b0;
                border: 1px solid #3c3c3c;
                border-radius: {config.S(5)}px;
                font-size: {config.FS_PX(9)}px;
                padding: 0px {config.S(12)}px;
            }}
            QPushButton#btn_ghost_sm:hover {{ background-color: #303335; color: #ffffff; border-color: #666666; }}
            {config.scrollbar_qss(6, bg=SETTINGS_CARD_BG)}
        """)

        self.decisions = {}
        self.diff_dict = diff_dict
        self.rows = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        title_text = _tr('msg_unsaved_title', 'Unsaved Changes')
        self._tb = CustomTitleBar(self, tb_lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        self._tb.set_title(title_text)
        root_layout.addWidget(self._tb)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(config.S(22), config.S(18), config.S(22), config.S(18))
        content_layout.setSpacing(config.S(14))
        root_layout.addLayout(content_layout, 1)

        header_col = QVBoxLayout()
        header_col.setContentsMargins(0, 0, 0, 0)
        header_col.setSpacing(config.S(4))

        lbl_title = QLabel(title_text, self.inner_frame)
        lbl_title.setStyleSheet(
            f"font-size: {config.FS_PX(14.5)}px; font-weight: bold; color: #ffffff; background: transparent; border: none;"
        )
        header_col.addWidget(lbl_title)

        lbl_desc = QLabel(_tr('msg_unsaved_desc', 'You have unsaved changes. What would you like to do?'), self.inner_frame)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet(
            f"font-size: {config.FS_PX(9.5)}px; color: #969696; background: transparent; border: none;"
        )
        header_col.addWidget(lbl_desc)
        content_layout.addLayout(header_col)

        # Elevated Settings-style card wrapping diff rows (compact auto-height, no empty gray void)
        list_card = QFrame(self.inner_frame)
        list_card.setObjectName("UnsavedCard")
        lc_lay = QVBoxLayout(list_card)
        lc_lay.setContentsMargins(0, 0, 0, 0)
        lc_lay.setSpacing(0)

        scroll = QScrollArea(list_card)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; } "
            "QWidget#unsaved_scroll_content { background: transparent; border: none; }"
        )

        scroll_content = QWidget()
        scroll_content.setObjectName("unsaved_scroll_content")
        self.vbox = QVBoxLayout(scroll_content)
        self.vbox.setContentsMargins(config.S(4), config.S(2), config.S(4), config.S(2))
        self.vbox.setSpacing(0)

        total_items = len(diff_dict)
        row_h = config.S(56)

        for idx, (k, (old_v, new_v)) in enumerate(diff_dict.items()):
            is_last = (idx == total_items - 1)
            row_border = "border-bottom: none;" if is_last else f"border-bottom: 1px solid {SETTINGS_DIVIDER_COL};"
            row = QFrame(scroll_content)
            row.setObjectName("item_row")
            row.setFixedHeight(row_h)
            row.setStyleSheet(
                f"QFrame#item_row {{ background: transparent; {row_border} border-radius: {config.S(6) if is_last else 0}px; }} "
                f"QFrame#item_row:hover {{ background-color: #2b2b2b; border-radius: {config.S(6)}px; }}"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(config.S(14), config.S(8), config.S(12), config.S(8))
            rl.setSpacing(config.S(10))

            fname = key_name_map.get(k, k.replace('_', ' ').title())

            if isinstance(new_v, bool):
                display_val = _tr('btn_yes', 'Yes') if new_v else _tr('btn_no', 'No')
            elif isinstance(new_v, list):
                t_list = []
                for item in new_v:
                    t = _tr(str(item), str(item))
                    t_list.append(t if t != str(item) else str(item).replace('_', ' ').title())
                display_val = ", ".join(t_list) if t_list else "-"
            elif isinstance(new_v, str):
                t = _tr(new_v, new_v)
                display_val = t if t != new_v else new_v
            else:
                display_val = str(new_v)

            left_box = QWidget(row)
            scope_transparent(left_box)
            lb_lay = QVBoxLayout(left_box)
            lb_lay.setContentsMargins(0, 0, 0, 0)
            lb_lay.setSpacing(config.S(1))

            if ":" in fname:
                cat_part, opt_part = fname.split(":", 1)
                lbl_cat = QLabel(cat_part.strip(), left_box)
                lbl_cat.setStyleSheet(
                    f"color: #888888; font-size: {config.FS_PX(8.3)}px; background: transparent; border: none;"
                )
                lb_lay.addWidget(lbl_cat)
                title_str = opt_part.strip()
            else:
                title_str = fname

            lbl_name = QLabel(title_str, left_box)
            lbl_name.setStyleSheet(
                f"color: #efefef; font-size: {config.FS_PX(9.8)}px; font-weight: 600; background: transparent; border: none;"
            )
            lb_lay.addWidget(lbl_name)

            lbl_val = QLabel(display_val, row)
            lbl_val.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            lbl_val.setStyleSheet(
                f"color: #62e39a; background-color: #172e21; border: 1px solid #264f38; "
                f"border-radius: {config.S(4)}px; padding: {config.S(2)}px {config.S(8)}px; "
                f"font-size: {config.FS_PX(9)}px; font-weight: 600;"
            )

            btn_discard = QPushButton(_tr('btn_discard', 'Discard'), row)
            btn_discard.setObjectName("btn_ghost_sm")
            btn_discard.setFixedHeight(config.S(26))
            btn_discard.setCursor(Qt.PointingHandCursor)
            btn_discard.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'discard'))

            btn_save = QPushButton(_tr('btn_save', 'Save'), row)
            btn_save.setObjectName("btn_apply")
            btn_save.setFixedHeight(config.S(26))
            btn_save.setCursor(Qt.PointingHandCursor)
            btn_save.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'save'))

            rl.addWidget(left_box, 1)
            rl.addWidget(lbl_val, 0, Qt.AlignVCenter)
            rl.addWidget(btn_discard, 0, Qt.AlignVCenter)
            rl.addWidget(btn_save, 0, Qt.AlignVCenter)

            self.vbox.addWidget(row)
            self.rows[k] = row

        scroll.setWidget(scroll_content)
        scroll_h = min(config.S(290), max(config.S(64), total_items * row_h + config.S(6)))
        scroll.setFixedHeight(scroll_h)
        lc_lay.addWidget(scroll)
        content_layout.addWidget(list_card)

        # Settings-matched Footer Bar
        footer_bar = QWidget(self.inner_frame)
        footer_bar.setObjectName("UnsavedFooterBar")
        fb_outer = QVBoxLayout(footer_bar)
        fb_outer.setContentsMargins(0, 0, 0, 0)
        fb_outer.setSpacing(0)

        f_sep = QFrame(footer_bar)
        f_sep.setFrameShape(QFrame.HLine)
        f_sep.setStyleSheet("background: #323232; max-height: 1px; border: none;")
        fb_outer.addWidget(f_sep)

        bot_layout = QHBoxLayout()
        bot_layout.setContentsMargins(config.S(22), config.S(11), config.S(22), config.S(12))
        bot_layout.setSpacing(config.S(8))

        btn_cancel = QPushButton(_tr('btn_cancel', 'Cancel'), footer_bar)
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setMinimumWidth(config.S(84))
        btn_cancel.setFixedHeight(config.S(30))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_discard_all = QPushButton(_tr('btn_discard_all', 'Discard All'), footer_bar)
        btn_discard_all.setObjectName("btn_secondary")
        btn_discard_all.setMinimumWidth(config.S(92))
        btn_discard_all.setFixedHeight(config.S(30))
        btn_discard_all.setCursor(Qt.PointingHandCursor)
        btn_discard_all.clicked.connect(self._discard_all)

        btn_save_all = QPushButton(_tr('btn_save_all', 'Save All'), footer_bar)
        btn_save_all.setObjectName("btn_apply")
        btn_save_all.setMinimumWidth(config.S(92))
        btn_save_all.setFixedHeight(config.S(30))
        btn_save_all.setCursor(Qt.PointingHandCursor)
        btn_save_all.clicked.connect(self._save_all)

        bot_layout.addWidget(btn_cancel)
        bot_layout.addStretch()
        bot_layout.addWidget(btn_discard_all)
        bot_layout.addWidget(btn_save_all)
        fb_outer.addLayout(bot_layout)
        root_layout.addWidget(footer_bar)

        dlg_w = config.S(630)
        self.setFixedWidth(dlg_w)
        self.adjustSize()
        dlg_h = max(config.S(230), min(config.S(480), self.sizeHint().height()))
        self.resize(dlg_w, dlg_h)
        _center_on_screen(self, dlg_w, dlg_h, reference_window=parent)
        
    def _make_decision(self, key, decision):
        self.decisions[key] = decision
        self.rows[key].hide()
        if len(self.decisions) == len(self.diff_dict):
            self.accept()
            
    def _save_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'save'
        self.accept()
        
    def _discard_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'discard'
        self.accept()
