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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QScrollArea, QWidget, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import _center_on_screen


class UnsavedChangesDialog(FramelessWindowMixin, _BaseDialog):
    def __init__(self, parent, diff_dict, key_name_map):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(parent.styleSheet() + f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; }}
            QScrollArea {{ border: 1px solid #333; background-color: #1c1c1c; border-radius: 4px; }}
            QFrame#item_row {{ border-bottom: 1px solid #333; padding-bottom: 5px; }}
        """)
        
        self.decisions = {}
        self.diff_dict = diff_dict
        self.rows = {}
        
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
        
        lbl_title = QLabel(parent.txt('msg_unsaved_title'))
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        content_layout.addWidget(lbl_title)
        content_layout.addWidget(QLabel(parent.txt('msg_unsaved_desc')))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.vbox = QVBoxLayout(scroll_content)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(10)
        
        for k, (old_v, new_v) in diff_dict.items():
            row = QFrame()
            row.setObjectName("item_row")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            
            fname = key_name_map.get(k, k.replace('_', ' ').title())
            lbl_name = QLabel(f"{fname}:")
            
            if isinstance(new_v, bool):
                display_val = parent.txt('btn_yes') if new_v else parent.txt('btn_no')
            elif isinstance(new_v, list):
                t_list = []
                for item in new_v:
                    t = parent.txt(str(item))
                    t_list.append(t if t != str(item) else str(item).replace('_', ' ').title())
                display_val = ", ".join(t_list) if t_list else "—"
            elif isinstance(new_v, str):
                t = parent.txt(new_v)
                display_val = t if t != new_v else new_v
            else:
                display_val = str(new_v)
                
            lbl_val = QLabel(f"<b>{display_val}</b>")
            lbl_val.setStyleSheet("color: #aaa;")
            
            btn_save = QPushButton(parent.txt('btn_save'))
            btn_save.setObjectName("btn_apply")
            btn_save.setCursor(Qt.PointingHandCursor)
            btn_save.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'save'))
            
            btn_discard = QPushButton(parent.txt('btn_discard'))
            btn_discard.setObjectName("btn_secondary")
            btn_discard.setCursor(Qt.PointingHandCursor)
            btn_discard.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'discard'))
            
            rl.addWidget(lbl_name)
            rl.addWidget(lbl_val)
            rl.addStretch()
            rl.addWidget(btn_discard)
            rl.addWidget(btn_save)
            
            self.vbox.addWidget(row)
            self.rows[k] = row
        
        self.vbox.addStretch()
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)
        
        bot_layout = QHBoxLayout()
        btn_cancel = QPushButton(parent.txt('btn_cancel'))
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_discard_all = QPushButton(parent.txt('btn_discard_all'))
        btn_discard_all.setObjectName("btn_secondary")
        btn_discard_all.setCursor(Qt.PointingHandCursor)
        btn_discard_all.clicked.connect(self._discard_all)
        
        btn_save_all = QPushButton(parent.txt('btn_save_all'))
        btn_save_all.setObjectName("btn_apply")
        btn_save_all.setCursor(Qt.PointingHandCursor)
        btn_save_all.clicked.connect(self._save_all)
        
        bot_layout.addWidget(btn_cancel)
        bot_layout.addStretch()
        bot_layout.addWidget(btn_discard_all)
        bot_layout.addWidget(btn_save_all)
        content_layout.addLayout(bot_layout)
        
        self.resize(630, 480)
        _center_on_screen(self, 630, 480)
        
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
