#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: telemetry_popup.py
ROLE: GUI Dialog
DESCRIPTION:
Shared consent-dialog base and first-launch privacy & diagnostics dialog for
new users, covering anonymous telemetry and automatic error reporting.
"""

from PySide6.QtCore import Qt, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import ToggleSwitch, TrackSquareCheckbox
from gui.widgets.language_selector import _LangPickerDialog
from gui.utils import _app_icon, _txt, _center_on_screen, get_svg_icon


_SVG_ANALYTICS = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <rect x="3" y="13" width="4" height="8" rx="1.2" fill="#23a559"/>
  <rect x="10" y="8" width="4" height="13" rx="1.2" fill="#23a559"/>
  <rect x="17" y="3" width="4" height="18" rx="1.2" fill="#39d377"/>
</svg>"""

_SVG_SHIELD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
  <path d="M12 2.5L4.5 5.8v5.7c0 4.9 3.2 9.4 7.5 10.5 4.3-1.1 7.5-5.6 7.5-10.5V5.8L12 2.5z" fill="#173d27" stroke="#23a559" stroke-width="1.8"/>
  <path d="M9 12.2l2.1 2.1 4.2-4.3" stroke="#39d377" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


class _PrivacyConsentDialogBase(FramelessWindowMixin, _BaseDialog):
    """Shared frameless dark shell, shadow, titlebar, and live language switcher for consent dialogs."""

    def __init__(self, engine, parent=None, dialog_width: int = 580):
        super().__init__(parent)
        self._engine = engine
        self._lang_picker = None
        self._decision_saved = False
        self._dialog_width = dialog_width

        prefs = engine.load_preferences() or {}
        self._lang = prefs.get("gui_lang", "en")
        if self._lang not in config.TRANS:
            self._lang = "en"

        self.frameless_init(is_popup=True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowIcon(_app_icon())

        self.setStyleSheet(f"""
            QDialog, _PrivacyConsentDialogBase {{ background-color: transparent; }}
            QFrame#MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: none;
                border-radius: {config.S(8)}px;
            }}
            QFrame#CardTelemetry, QFrame#CardCrashReport, QFrame#CrashInfoCard {{
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: {config.S(6)}px;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: {config.FS(13.5)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_intro {{
                color: #b4b4b4;
                font-size: {config.FS(9.5)}pt;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_subtitle {{
                color: #39d377;
                font-size: {config.FS(9.5)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_card_title {{
                color: #ffffff;
                font-size: {config.FS(10.5)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_card_body, QLabel#lbl_body {{
                color: #c8c8c8;
                font-size: {config.FS(9.5)}pt;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_default_badge {{
                background-color: #0f301d;
                color: #39d377;
                border: 1px solid #1d5c37;
                border-radius: {config.S(3)}px;
                padding: {config.S(2)}px {config.S(7)}px;
                font-size: {config.FS(8)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
                font-weight: bold;
                background: transparent;
                border: 1px solid #303030;
                border-radius: {config.S(4)}px;
                padding: {config.S(2)}px {config.S(8)}px;
            }}
            QPushButton#btn_lang:hover {{
                color: #ffffff;
                border-color: #555555;
            }}
            QPushButton#btn_yes {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
                font-weight: bold;
                border: none;
                padding: {config.S(7)}px {config.S(18)}px;
                border-radius: {config.S(4)}px;
            }}
            QPushButton#btn_yes:hover {{
                background-color: {config.BTN_ACTIVE};
            }}
            QPushButton#btn_no {{
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(10)}pt;
                font-weight: bold;
                border: 1px solid #404040;
                padding: {config.S(7)}px {config.S(16)}px;
                border-radius: {config.S(4)}px;
            }}
            QPushButton#btn_no:hover {{
                background-color: #383838;
                border-color: #5a5a5a;
                color: #ffffff;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(config.S(15), config.S(15), config.S(15), config.S(15))

        class SolidFrame(QFrame):
            def paintEvent(self, e):
                p = QPainter(self)
                p.fillRect(self.rect(), QColor(config.BG_COLOR))
                super().paintEvent(e)

        self.inner_frame = SolidFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(config.S(30))
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tb = CustomTitleBar(self, self._lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)

        self._container = QWidget(self.inner_frame)
        self._container.setObjectName("container")
        self._content_layout = QVBoxLayout(self._container)
        self._content_layout.setContentsMargins(config.S(20), config.S(14), config.S(20), config.S(18))
        self._content_layout.setSpacing(config.S(12))
        root_layout.addWidget(self._container)

    def _build_lang_button(self, parent) -> QPushButton:
        btn = QPushButton("", parent)
        btn.setObjectName("btn_lang")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(self._show_lang_picker)
        return btn

    def _build_footer_buttons(self, parent) -> QHBoxLayout:
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(config.S(10))
        btn_row.addStretch()

        self._btn_no = QPushButton("", parent)
        self._btn_no.setObjectName("btn_no")
        self._btn_no.setCursor(Qt.PointingHandCursor)
        self._btn_no.clicked.connect(self._on_no)
        btn_row.addWidget(self._btn_no)

        self._btn_yes = QPushButton("", parent)
        self._btn_yes.setObjectName("btn_yes")
        self._btn_yes.setCursor(Qt.PointingHandCursor)
        self._btn_yes.clicked.connect(self._on_yes)
        btn_row.addWidget(self._btn_yes)
        btn_row.addStretch()
        return btn_row

    def _t(self, key: str, **kwargs) -> str:
        return _txt(self._lang, key, **kwargs)

    def _set_btn_text(self, btn: QPushButton, text: str):
        btn.setText(str(text).replace("&", "&&"))

    def _finalize_geometry(self, title_txt: str, wrapped_labels: tuple, btn_texts: tuple = None):
        self.setWindowTitle(title_txt)
        if btn_texts and len(btn_texts) == 2:
            self._set_btn_text(self._btn_no, btn_texts[0])
            self._set_btn_text(self._btn_yes, btn_texts[1])
        self._btn_lang.setText(self._lang.upper())
        if hasattr(self, '_tb') and hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(title_txt)
            self._tb._lang = self._lang

        dialog_w = config.S(self._dialog_width)
        text_max_w = dialog_w - config.S(15 + 15 + 20 + 20 + 28)
        for lbl in wrapped_labels:
            lbl.setFixedWidth(text_max_w)
            lbl.setMinimumHeight(0)
            lbl.setMaximumHeight(16777215)
            lbl.updateGeometry()
            req_h = lbl.heightForWidth(text_max_w)
            if req_h > 0:
                lbl.setFixedHeight(req_h + config.S(2))

        if hasattr(self, '_chk_geo') and hasattr(self, '_geo_container'):
            self._chk_geo.lbl.setWordWrap(False)
            self._chk_geo.setText(self._chk_geo.text())
            self._geo_container.setMinimumHeight(self._chk_geo.minimumHeight() + config.S(4))

        total_w = dialog_w + config.S(30)
        self.setMinimumWidth(total_w)
        self.setMaximumWidth(total_w)
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        if self._container.layout():
            self._container.layout().invalidate()
            self._container.layout().activate()
        if self.inner_frame.layout():
            self.inner_frame.layout().invalidate()
            self.inner_frame.layout().activate()
        if self.layout():
            self.layout().invalidate()
            self.layout().activate()
        self.adjustSize()
        h = max(self.sizeHint().height(), self.layout().totalHeightForWidth(total_w) if self.layout() else self.height())
        self.setFixedSize(total_w, h)
        _center_on_screen(self, total_w, h)

    def _show_lang_picker(self):
        try:
            if self._lang_picker and self._lang_picker.isVisible():
                self._lang_picker.close()
                return
        except RuntimeError:
            self._lang_picker = None

        self._lang_picker = _LangPickerDialog(self)
        self._lang_picker.lang_selected.connect(self._on_lang_selected)

        btn_global = self._btn_lang.mapToGlobal(self._btn_lang.rect().bottomRight())
        picker_w = self._lang_picker.width()
        self._lang_picker.move(btn_global.x() - picker_w, btn_global.y())
        self._lang_picker.show()

    def _on_lang_selected(self, code: str):
        if code == self._lang:
            return
        self._lang = code
        self._engine.save_preferences({"gui_lang": code})
        self._refresh_texts()

    def _refresh_texts(self):
        raise NotImplementedError

    def _on_yes(self):
        raise NotImplementedError

    def _on_no(self):
        raise NotImplementedError

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._on_no()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if not getattr(self, "_decision_saved", False):
            self._on_no()
        super().closeEvent(event)


class TelemetryPopup(_PrivacyConsentDialogBase):
    """
    Modal welcome consent dialog for new users covering:
    1) Anonymous Telemetry (with optional geo sub-checkbox that dims when off)
    2) Automatic Error & Crash Reports (enabled by default for new users)
    """

    def __init__(self, engine, parent=None):
        super().__init__(engine, parent=parent, dialog_width=600)
        container = self._container
        content_layout = self._content_layout

        # Header row (title + language button)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(config.S(8))

        self._lbl_title = QLabel("", container)
        self._lbl_title.setObjectName("lbl_title")
        header.addWidget(self._lbl_title, 1)

        self._btn_lang = self._build_lang_button(container)
        header.addWidget(self._btn_lang)
        content_layout.addLayout(header)

        self._lbl_intro = QLabel("", container)
        self._lbl_intro.setObjectName("lbl_intro")
        self._lbl_intro.setWordWrap(True)
        content_layout.addWidget(self._lbl_intro)

        # --- Card 1: Anonymous Telemetry ---
        card_telem = QFrame(container)
        card_telem.setObjectName("CardTelemetry")
        telem_lay = QVBoxLayout(card_telem)
        telem_lay.setContentsMargins(config.S(14), config.S(12), config.S(14), config.S(12))
        telem_lay.setSpacing(config.S(8))

        telem_hdr = QHBoxLayout()
        telem_hdr.setSpacing(config.S(8))
        telem_icon = QLabel(card_telem)
        telem_icon.setFixedSize(config.S(18), config.S(18))
        telem_icon.setPixmap(get_svg_icon(_SVG_ANALYTICS, size=18).pixmap(config.S(18), config.S(18)))
        telem_hdr.addWidget(telem_icon)

        self._lbl_telem_title = QLabel("", card_telem)
        self._lbl_telem_title.setObjectName("lbl_card_title")
        telem_hdr.addWidget(self._lbl_telem_title, 1)

        self._tgl_telemetry = ToggleSwitch(card_telem)
        self._tgl_telemetry.setChecked(True, animated=False)
        telem_hdr.addWidget(self._tgl_telemetry)
        telem_lay.addLayout(telem_hdr)

        self._lbl_msg = QLabel("", card_telem)
        self._lbl_msg.setObjectName("lbl_card_body")
        self._lbl_msg.setWordWrap(True)
        telem_lay.addWidget(self._lbl_msg)

        self._geo_container = QWidget(card_telem)
        self._geo_container.setStyleSheet("background: transparent;")
        geo_layout = QHBoxLayout(self._geo_container)
        geo_layout.setContentsMargins(0, config.S(2), 0, 0)
        self._chk_geo = TrackSquareCheckbox("", is_checked=True, font_size=config.FS(9.5), parent=self._geo_container)
        geo_layout.addWidget(self._chk_geo)
        geo_layout.addStretch()

        self._geo_opacity = QGraphicsOpacityEffect(self._geo_container)
        self._geo_opacity.setOpacity(1.0)
        self._geo_opacity.setEnabled(False)
        self._geo_container.setGraphicsEffect(self._geo_opacity)
        self._geo_anim = QVariantAnimation(self)
        self._geo_anim.setDuration(220)
        self._geo_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._geo_anim.valueChanged.connect(lambda v: self._geo_opacity.setOpacity(float(v)))
        self._geo_anim.finished.connect(self._on_geo_anim_finished)
        telem_lay.addWidget(self._geo_container)

        self._tgl_telemetry.toggled.connect(self._on_telemetry_toggled)
        content_layout.addWidget(card_telem)

        # --- Card 2: Automatic Crash & Error Reports (DEFAULT ON) ---
        card_crash = QFrame(container)
        card_crash.setObjectName("CardCrashReport")
        crash_lay = QVBoxLayout(card_crash)
        crash_lay.setContentsMargins(config.S(14), config.S(12), config.S(14), config.S(12))
        crash_lay.setSpacing(config.S(8))

        crash_hdr = QHBoxLayout()
        crash_hdr.setSpacing(config.S(8))
        crash_icon = QLabel(card_crash)
        crash_icon.setFixedSize(config.S(18), config.S(18))
        crash_icon.setPixmap(get_svg_icon(_SVG_SHIELD, size=18).pixmap(config.S(18), config.S(18)))
        crash_hdr.addWidget(crash_icon)

        self._lbl_crash_title = QLabel("", card_crash)
        self._lbl_crash_title.setObjectName("lbl_card_title")
        crash_hdr.addWidget(self._lbl_crash_title)

        self._lbl_default_badge = QLabel("", card_crash)
        self._lbl_default_badge.setObjectName("lbl_default_badge")
        crash_hdr.addWidget(self._lbl_default_badge)
        crash_hdr.addStretch(1)

        self._tgl_crash_report = ToggleSwitch(card_crash)
        self._tgl_crash_report.setChecked(True, animated=False)
        crash_hdr.addWidget(self._tgl_crash_report)
        crash_lay.addLayout(crash_hdr)

        self._lbl_crash_msg = QLabel("", card_crash)
        self._lbl_crash_msg.setObjectName("lbl_card_body")
        self._lbl_crash_msg.setWordWrap(True)
        crash_lay.addWidget(self._lbl_crash_msg)

        content_layout.addWidget(card_crash)
        content_layout.addSpacing(config.S(4))
        content_layout.addLayout(self._build_footer_buttons(container))
        self._refresh_texts()

    def _on_geo_anim_finished(self):
        if self._tgl_telemetry.isChecked():
            self._geo_opacity.setEnabled(False)

    def _on_telemetry_toggled(self, checked: bool):
        target = 1.0 if checked else 0.35
        self._geo_container.setAttribute(Qt.WA_TransparentForMouseEvents, not checked)
        self._chk_geo.setEnabled(checked)
        self._geo_opacity.setEnabled(True)
        self._geo_anim.stop()
        self._geo_anim.setStartValue(self._geo_opacity.opacity())
        self._geo_anim.setEndValue(target)
        self._geo_anim.start()

    def _refresh_texts(self):
        title_txt = self._t("title_privacy_welcome")
        self._lbl_title.setText(title_txt)
        self._lbl_intro.setText(self._t("msg_privacy_welcome_intro"))
        self._lbl_telem_title.setText(self._t("title_telemetry"))
        self._lbl_msg.setText(self._t("msg_telemetry_card"))
        self._chk_geo.setText(self._t("chk_telemetry_geo"))
        self._lbl_crash_title.setText(self._t("title_crash_report_card"))
        self._lbl_default_badge.setText(self._t("badge_default_on"))
        self._lbl_crash_msg.setText(self._t("msg_crash_report_card"))
        self._finalize_geometry(
            title_txt,
            (self._lbl_intro, self._lbl_msg, self._lbl_crash_msg),
            btn_texts=(self._t("btn_consent_disable_all"), self._t("btn_consent_save")),
        )

    def _on_yes(self):
        self._decision_saved = True
        telem_on = bool(self._tgl_telemetry.isChecked())
        geo_on = bool(telem_on and self._chk_geo.isChecked())
        crash_on = bool(self._tgl_crash_report.isChecked())

        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in", telem_on)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", geo_on)
        self._engine.os_doc.set_telemetry_pref("auto_crash_report", crash_on)
        if telem_on:
            self._engine.send_telemetry_ping("app_started")
        self.accept()

    def _on_no(self):
        self._decision_saved = True
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in", False)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", False)
        self._engine.os_doc.set_telemetry_pref("auto_crash_report", False)
        self.accept()
