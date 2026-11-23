#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: crash_report_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Dedicated one-time consent dialog shown to existing users after updating when
automatic error & crash reporting has not been configured yet (independent of
telemetry consent).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QFrame
import config
from gui.dialogs.telemetry_popup import _PrivacyConsentDialogBase, _SVG_SHIELD, _FadeIconLabel


class CrashReportConsentDialog(_PrivacyConsentDialogBase):
    """
    Modal dialog asking existing users whether to enable automatic crash
    and error reporting, independent of their previous telemetry choice.
    """

    def __init__(self, engine, parent=None):
        super().__init__(engine, parent=parent, dialog_width=580)
        container = self._container
        content_layout = self._content_layout

        # Header row: shield SVG icon + Title + subtitle + Language switcher
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(config.S(12))

        icon_lbl = _FadeIconLabel(_SVG_SHIELD, size_px=30, parent=container)
        header.addWidget(icon_lbl, 0, Qt.AlignTop)

        title_col = QVBoxLayout()
        title_col.setSpacing(config.S(2))
        self._lbl_title = QLabel("", container)
        self._lbl_title.setObjectName("lbl_title")
        title_col.addWidget(self._lbl_title)

        self._lbl_subtitle = QLabel("", container)
        self._lbl_subtitle.setObjectName("lbl_subtitle")
        self._lbl_subtitle.setWordWrap(True)
        title_col.addWidget(self._lbl_subtitle)
        header.addLayout(title_col, 1)

        self._btn_lang = self._build_lang_button(container)
        header.addWidget(self._btn_lang, 0, Qt.AlignTop)
        content_layout.addLayout(header)

        # Details card
        card = QFrame(container)
        card.setObjectName("CrashInfoCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(config.S(14), config.S(12), config.S(14), config.S(12))
        card_lay.setSpacing(0)

        self._lbl_body = QLabel("", card)
        self._lbl_body.setObjectName("lbl_body")
        self._lbl_body.setWordWrap(True)
        self._lbl_body.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        card_lay.addWidget(self._lbl_body)

        content_layout.addWidget(card)
        content_layout.addSpacing(config.S(4))
        content_layout.addLayout(self._build_footer_buttons(container))
        self._refresh_texts()

    def _refresh_texts(self):
        title_txt = self._t("title_crash_consent")
        self._lbl_title.setText(title_txt)
        self._lbl_subtitle.setText(self._t("subtitle_crash_consent"))
        self._lbl_body.setText(self._t("msg_crash_consent_body"))
        self._finalize_geometry(
            title_txt,
            (self._lbl_body,),
            btn_texts=(self._t("btn_crash_consent_later"), self._t("btn_enable_crash_reports")),
        )

    def _on_yes(self):
        self._decision_saved = True
        self._engine.os_doc.set_telemetry_pref("auto_crash_report", True)
        self.accept()

    def _on_no(self):
        self._decision_saved = True
        self._engine.os_doc.set_telemetry_pref("auto_crash_report", False)
        self.accept()
