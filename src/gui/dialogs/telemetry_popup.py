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

from PySide6.QtCore import Qt, QTimer, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame
)
import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import ToggleSwitch, TrackSquareCheckbox
from gui.widgets.language_selector import _LangPickerDialog
from gui.utils import _app_icon, _txt, _center_on_screen, get_svg_icon


_CARD_BG_HEX = "#151515"


def _blend_hex(fg_hex: str, bg_hex: str, factor: float) -> str:
    """Blends fg_hex toward bg_hex by factor (0.0..1.0) into a #rrggbb string for QSS-proof fading."""
    t = max(0.0, min(1.0, float(factor)))
    fg = QColor(fg_hex)
    bg = QColor(bg_hex)
    r = int(round(bg.red() + (fg.red() - bg.red()) * t))
    g = int(round(bg.green() + (fg.green() - bg.green()) * t))
    b = int(round(bg.blue() + (fg.blue() - bg.blue()) * t))
    return f"#{r:02x}{g:02x}{b:02x}"


class _FadeIconLabel(QLabel):
    """Transparent SVG icon label with flicker-free QPainter opacity (no nested QGraphicsEffect)."""

    def __init__(self, svg_xml: str, size_px: int, parent=None):
        super().__init__(parent)
        self._opacity = 1.0
        self._size_px = config.S(size_px)
        self._pixmap = get_svg_icon(svg_xml, size=size_px).pixmap(self._size_px, self._size_px)
        self.setFixedSize(self._size_px, self._size_px)
        self.setStyleSheet("background: transparent; border: none;")
        self.setAttribute(Qt.WA_TranslucentBackground, True)

    def set_opacity(self, opacity: float):
        val = max(0.0, min(1.0, float(opacity)))
        if abs(self._opacity - val) > 1e-4:
            self._opacity = val
            self.update()

    def opacity(self) -> float:
        return self._opacity

    def paintEvent(self, event):
        if self._pixmap.isNull():
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setOpacity(self._opacity)
        x = (self.width() - self._pixmap.width()) // 2
        y = (self.height() - self._pixmap.height()) // 2
        p.drawPixmap(x, y, self._pixmap)
        p.end()


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
            QDialog, _PrivacyConsentDialogBase {{ background-color: {config.BG_COLOR}; }}
            QFrame#MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #2e2e2e;
                border-radius: 0px;
            }}
            QFrame#CardTelemetry, QFrame#CardCrashReport, QFrame#CrashInfoCard {{
                background-color: #151515;
                border: 1px solid #2b2b2b;
                border-radius: {config.S(6)}px;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: {config.FS_PX(13.5)}px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_intro {{
                color: #b4b4b4;
                font-size: {config.FS_PX(9.5)}px;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_subtitle {{
                color: #39d377;
                font-size: {config.FS_PX(9.5)}px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
            QLabel#lbl_card_title {{
                font-size: {config.FS_PX(10.5)}px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_card_body {{
                font-size: {config.FS_PX(9.5)}px;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_body {{
                color: #c8c8c8;
                font-size: {config.FS_PX(9.5)}px;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS_PX(10)}px;
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
                font-size: {config.FS_PX(10)}px;
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
                font-size: {config.FS_PX(10)}px;
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
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
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
        self._btn_no.clicked.connect(lambda: self._on_no())
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
        if hasattr(self, '_tb'):
            self._tb._lang = self._lang
            self._tb.set_title(title_txt)

        dialog_w = config.S(self._dialog_width)
        # Subtract inner_frame (2px) + container margins (40px) + card padding/borders (30px)
        text_max_w = dialog_w - config.S(20 + 20 + 28 + 6)
        for lbl in wrapped_labels:
            lbl.ensurePolished()
            lbl.setFixedWidth(text_max_w)
            lbl.setMinimumHeight(0)
            lbl.setMaximumHeight(16777215)
            lbl.updateGeometry()
            req_h = max(lbl.heightForWidth(text_max_w), lbl.sizeHint().height())
            if req_h > 0:
                lbl.setFixedHeight(req_h + config.S(6))

        if hasattr(self, '_chk_geo') and hasattr(self, '_geo_container'):
            self._chk_geo.lbl.setWordWrap(False)
            self._chk_geo.setText(self._chk_geo.text())
            self._geo_container.setMinimumHeight(self._chk_geo.minimumHeight() + config.S(4))

        total_w = dialog_w
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
        self._closing_anim_active = False
        self._label_color_cache = {}
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
        self._telem_icon = _FadeIconLabel(_SVG_ANALYTICS, size_px=18, parent=card_telem)
        telem_hdr.addWidget(self._telem_icon)

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
        self._geo_container.setStyleSheet("background: transparent; border: none;")
        geo_layout = QHBoxLayout(self._geo_container)
        geo_layout.setContentsMargins(0, config.S(2), 0, 0)
        self._chk_geo = TrackSquareCheckbox("", is_checked=True, font_size=config.FS_PX(9.5), parent=self._geo_container)
        geo_layout.addWidget(self._chk_geo)
        geo_layout.addStretch()
        telem_lay.addWidget(self._geo_container)

        # Smooth flicker-free fade for entire Telemetry card (NO nested QGraphicsOpacityEffect!)
        self._telem_dim_val = 1.0
        self._telem_anim = QVariantAnimation(self)
        self._telem_anim.setDuration(220)
        self._telem_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._telem_anim.valueChanged.connect(self._apply_telemetry_card_dim)
        self._apply_telemetry_card_dim(1.0)

        self._tgl_telemetry.toggled.connect(self._on_telemetry_toggled)
        content_layout.addWidget(card_telem)

        # --- Card 2: Automatic Crash & Error Reports (DEFAULT ON, no badge) ---
        card_crash = QFrame(container)
        card_crash.setObjectName("CardCrashReport")
        crash_lay = QVBoxLayout(card_crash)
        crash_lay.setContentsMargins(config.S(14), config.S(12), config.S(14), config.S(12))
        crash_lay.setSpacing(config.S(8))

        crash_hdr = QHBoxLayout()
        crash_hdr.setSpacing(config.S(8))
        self._crash_icon = _FadeIconLabel(_SVG_SHIELD, size_px=18, parent=card_crash)
        crash_hdr.addWidget(self._crash_icon)

        self._lbl_crash_title = QLabel("", card_crash)
        self._lbl_crash_title.setObjectName("lbl_card_title")
        crash_hdr.addWidget(self._lbl_crash_title, 1)

        self._tgl_crash_report = ToggleSwitch(card_crash)
        self._tgl_crash_report.setChecked(True, animated=False)
        crash_hdr.addWidget(self._tgl_crash_report)
        crash_lay.addLayout(crash_hdr)

        self._lbl_crash_msg = QLabel("", card_crash)
        self._lbl_crash_msg.setObjectName("lbl_card_body")
        self._lbl_crash_msg.setWordWrap(True)
        crash_lay.addWidget(self._lbl_crash_msg)

        # Smooth flicker-free fade for entire Crash Report card (NO nested QGraphicsOpacityEffect!)
        self._crash_dim_val = 1.0
        self._crash_anim = QVariantAnimation(self)
        self._crash_anim.setDuration(220)
        self._crash_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._crash_anim.valueChanged.connect(self._apply_crash_card_dim)
        self._apply_crash_card_dim(1.0)

        self._tgl_crash_report.toggled.connect(self._on_crash_toggled)
        content_layout.addWidget(card_crash)
        content_layout.addSpacing(config.S(4))
        content_layout.addLayout(self._build_footer_buttons(container))
        self._refresh_texts()

    def _set_label_hex_color(self, lbl: QLabel, hex_color: str, px_size: float, bold: bool = False):
        """Sets explicit per-label QSS color so global QApplication/MainWindow stylesheets cannot override dimming."""
        if self._label_color_cache.get(id(lbl)) == hex_color:
            return
        self._label_color_cache[id(lbl)] = hex_color
        weight = "bold" if bold else "normal"
        lbl.setStyleSheet(
            f"color: {hex_color}; font-size: {px_size}px; font-weight: {weight}; "
            f"font-family: '{config.UI_FONT_NAME}'; background: transparent; border: none;"
        )

    def _apply_telemetry_card_dim(self, val):
        factor = max(0.0, min(1.0, float(val)))
        self._telem_dim_val = factor
        self._telem_icon.set_opacity(factor)
        self._set_label_hex_color(self._lbl_telem_title, _blend_hex("#ffffff", _CARD_BG_HEX, factor), config.FS_PX(10.5), bold=True)
        self._set_label_hex_color(self._lbl_msg, _blend_hex("#c8c8c8", _CARD_BG_HEX, factor), config.FS_PX(9.5), bold=False)
        self._chk_geo.set_dim_opacity(factor, bg_hex=_CARD_BG_HEX)

    def _apply_crash_card_dim(self, val):
        factor = max(0.0, min(1.0, float(val)))
        self._crash_dim_val = factor
        self._crash_icon.set_opacity(factor)
        self._set_label_hex_color(self._lbl_crash_title, _blend_hex("#ffffff", _CARD_BG_HEX, factor), config.FS_PX(10.5), bold=True)
        self._set_label_hex_color(self._lbl_crash_msg, _blend_hex("#c8c8c8", _CARD_BG_HEX, factor), config.FS_PX(9.5), bold=False)

    def _on_telemetry_toggled(self, checked: bool):
        target = 1.0 if checked else 0.35
        self._geo_container.setAttribute(Qt.WA_TransparentForMouseEvents, not checked)
        self._chk_geo.setEnabled(checked)
        self._telem_anim.stop()
        self._telem_anim.setStartValue(self._telem_dim_val)
        self._telem_anim.setEndValue(target)
        self._telem_anim.start()

    def _on_crash_toggled(self, checked: bool):
        target = 1.0 if checked else 0.35
        self._crash_anim.stop()
        self._crash_anim.setStartValue(self._crash_dim_val)
        self._crash_anim.setEndValue(target)
        self._crash_anim.start()

    def _refresh_texts(self):
        title_txt = self._t("title_privacy_welcome")
        self._lbl_title.setText(title_txt)
        self._lbl_intro.setText(self._t("msg_privacy_welcome_intro"))
        self._lbl_telem_title.setText(self._t("title_telemetry"))
        self._lbl_msg.setText(self._t("msg_telemetry_card"))
        self._chk_geo.setText(self._t("chk_telemetry_geo"))
        self._lbl_crash_title.setText(self._t("title_crash_report_card"))
        self._lbl_crash_msg.setText(self._t("msg_crash_report_card"))
        self._finalize_geometry(
            title_txt,
            (self._lbl_intro, self._lbl_msg, self._lbl_crash_msg),
            btn_texts=(self._t("btn_consent_disable_all"), self._t("btn_consent_save")),
        )

    def _persist_disabled(self):
        if self._decision_saved:
            return
        self._decision_saved = True
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in", False)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", False)
        self._engine.os_doc.set_telemetry_pref("auto_crash_report", False)

    def _finish_disable_all(self):
        self._persist_disabled()
        try:
            self.accept()
        except RuntimeError:
            pass

    def _on_yes(self):
        if self._closing_anim_active:
            return
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

    def _on_no(self, immediate: bool = False):
        if self._closing_anim_active:
            return

        any_on = bool(self._tgl_telemetry.isChecked() or self._tgl_crash_report.isChecked())
        if not immediate and self.isVisible() and any_on:
            # Start switch slide & card fade INSTANTLY (0 ms) before any disk fsync I/O
            self._closing_anim_active = True
            self._btn_no.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._btn_yes.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._tgl_telemetry.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self._tgl_crash_report.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            if self._tgl_telemetry.isChecked():
                self._tgl_telemetry.setChecked(False, animated=True)
            if self._tgl_crash_report.isChecked():
                self._tgl_crash_report.setChecked(False, animated=True)
            QTimer.singleShot(420, self._finish_disable_all)
            return

        self._persist_disabled()
        self.accept()

    def closeEvent(self, event):
        if not getattr(self, "_decision_saved", False):
            self._persist_disabled()
        super().closeEvent(event)
