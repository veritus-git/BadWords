#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: export_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Modern, frameless modal dialog for exporting standalone timeline edits to industry-standard
timeline formats (Final Cut Pro 7 XML, OpenTimelineIO .otio, Apple FCPXML, CMX 3600 EDL).
Allows frame rate and resolution overrides, audio track preservation, and folder destination selection.
All generated XML/OTIO files strictly reference original media files on disk (never proxies).
"""

import os
import time
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QFrame, QLineEdit, QFileDialog, QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QDesktopServices, QCursor, QPixmap, QPainter, QColor

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import CustomDropdown, ToggleSwitch
from gui.dialogs.msgbox import CustomMsgBox
from gui.utils import _app_icon, _txt, get_export_icon, get_export_pixmap, get_layout_icon_path
import assembler


class ExportDialog(FramelessWindowMixin, _BaseDialog):
    """
    Modal export dialog for Standalone (File) Mode in BadWords.
    """
    def __init__(self, parent_gui, engine, clips_info: list, ops: list, words_data: list = None, parent=None):
        super().__init__(parent or parent_gui)
        self.parent_gui = parent_gui
        self.engine = engine
        self.clips_info = clips_info or []
        self.ops = ops or []
        self.words_data = words_data or []

        prefs = engine.load_preferences() if engine else {}
        self._lang = prefs.get("gui_lang", "en") if prefs else "en"
        if self._lang not in config.TRANS:
            self._lang = "en"

        self.frameless_init(is_popup=True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowIcon(_app_icon())

        win_w = config.S(560)
        win_h = config.S(415)
        self.setFixedSize(win_w, win_h)

        # Center over active main window or active screen
        parent_w = parent or parent_gui
        if parent_w:
            geo = parent_w.geometry()
            x = geo.x() + (geo.width() - win_w) // 2
            y = geo.y() + (geo.height() - win_h) // 2
            self.move(max(0, x), max(0, y))
        else:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                sg = screen.availableGeometry()
                self.move(sg.x() + (sg.width() - win_w) // 2,
                          sg.y() + (sg.height() - win_h) // 2)

        self._init_metadata()
        self._build_ui()

    def _t(self, key: str, default: str = "") -> str:
        if hasattr(self.parent_gui, "txt"):
            return self.parent_gui.txt(key, default)
        return _txt(self._lang, key, default)

    def _init_metadata(self):
        """Analyzes clips_info to determine default FPS, resolution, and hint text."""
        video_fps_list = [c["fps"] for c in self.clips_info if c.get("has_video") and c.get("fps", 0) > 0]
        if video_fps_list:
            first_fps = video_fps_list[0]
            if all(abs(f - first_fps) < 0.05 for f in video_fps_list):
                self.default_fps = round(first_fps, 3)
                self.fps_hint = self._t("hint_fps_uniform", f"Wszystkie klipy wideo mają {self.default_fps:g} FPS").replace("{fps}", f"{self.default_fps:g}")
            else:
                self.default_fps = round(first_fps, 3)
                details = ", ".join(f"{f:g} FPS" for f in video_fps_list[:3])
                self.fps_hint = self._t("hint_fps_mixed", f"Wykryto różne klatkaże: {details}").replace("{details}", details)
        else:
            self.default_fps = 24.0
            self.fps_hint = ""

        video_clips = [c for c in self.clips_info if c.get("has_video")]
        if video_clips:
            self.default_width = video_clips[0].get("width", 1920)
            self.default_height = video_clips[0].get("height", 1080)
        else:
            self.default_width = 1920
            self.default_height = 1080

        first_path = self.clips_info[0]["path"] if self.clips_info else ""
        if first_path and os.path.isfile(first_path):
            self.default_dir = os.path.dirname(os.path.abspath(first_path))
            base_stem = os.path.splitext(os.path.basename(first_path))[0]
            self.default_seq_name = f"{base_stem}_BadWords_Cut"
        else:
            self.default_dir = os.path.expanduser("~")
            self.default_seq_name = f"BadWords_Timeline_{time.strftime('%Y%m%d_%H%M')}"

    def _create_info_icon(self, tooltip_key: str) -> QLabel:
        """Creates an (i) info icon that opens the tooltip with explanation, with dimming support."""
        info = QLabel()
        info_icon_path = get_layout_icon_path("information.png")
        if os.path.exists(info_icon_path):
            pix = QPixmap(info_icon_path)
            dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            size = config.S(16)
            scaled_pix = pix.scaled(int(size * dpr), int(size * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_pix.setDevicePixelRatio(dpr)

            dimmed_pix = QPixmap(scaled_pix.size())
            dimmed_pix.fill(Qt.transparent)
            painter = QPainter(dimmed_pix)
            painter.setOpacity(0.35)
            painter.drawPixmap(0, 0, scaled_pix)
            painter.end()
            dimmed_pix.setDevicePixelRatio(dpr)

            info._normal_pix = scaled_pix
            info._dimmed_pix = dimmed_pix
            info.setPixmap(scaled_pix)
        else:
            info.setText("🛈")
            info.setStyleSheet("color: #888888; font-size: 11pt;")
            info._normal_pix = None
            info._dimmed_pix = None

        tt_text = self._t(tooltip_key, tooltip_key)
        info.custom_tooltip_text = tt_text
        info.setToolTip(tt_text)
        info.setCursor(Qt.WhatsThisCursor)

        def _on_enter(e):
            if not info.isEnabled():
                return
            if hasattr(self.parent_gui, 'shared_tooltip'):
                self.parent_gui.shared_tooltip.show_global(info.custom_tooltip_text, QCursor.pos())
        info.enterEvent = _on_enter
        info.leaveEvent = lambda e: self.parent_gui.shared_tooltip.hide() if hasattr(self.parent_gui, 'shared_tooltip') else None
        return info

    def _build_ui(self):
        self.setStyleSheet(f"""
            QDialog, ExportDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #1a1a1a;
                border-radius: 0px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: {config.FS(12.5)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QLabel#lbl_sub {{
                color: #888888;
                font-size: {config.FS(8.5)}pt;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QLineEdit {{
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: {config.S(4)}px;
                padding: {config.S(4)}px {config.S(8)}px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(9)}pt;
            }}
            QLineEdit:focus {{
                border-color: #38c172;
            }}
        """)

        outer_l = QVBoxLayout(self)
        outer_l.setContentsMargins(15, 15, 15, 15)

        class SolidFrame(QFrame):
            def paintEvent(self, e):
                from PySide6.QtGui import QPainter, QColor
                p = QPainter(self)
                p.fillRect(self.rect(), QColor(config.BG_COLOR))
                super().paintEvent(e)

        self.inner_frame = SolidFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)

        outer_l.addWidget(self.inner_frame)

        root_l = QVBoxLayout(self.inner_frame)
        root_l.setContentsMargins(0, 0, 0, 0)
        root_l.setSpacing(0)

        # Title bar
        self._tb = CustomTitleBar(self, self._lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(self._t("dlg_export_title", "Eksportuj oś czasu"))
        root_l.addWidget(self._tb)

        # Body container
        container = QWidget(self.inner_frame)
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(config.S(22), config.S(12), config.S(22), config.S(14))
        c_lay.setSpacing(config.S(9))

        # Header titles
        h_row = QVBoxLayout()
        h_row.setSpacing(config.S(2))
        lbl_h = QLabel(self._t("dlg_export_title", "Eksportuj oś czasu"))
        lbl_h.setObjectName("lbl_title")
        h_row.addWidget(lbl_h)
        lbl_sub = QLabel(self._t("dlg_export_desc", "Wybierz format eksportu i parametry sekwencji montażowej"))
        lbl_sub.setObjectName("lbl_sub")
        h_row.addWidget(lbl_sub)
        c_lay.addLayout(h_row)

        c_lay.addSpacing(config.S(3))

        label_w = config.S(145)

        # ── 1. Export Format (Dropdown) ───────────────────────────────────────
        r_fmt = QHBoxLayout()
        r_fmt.setSpacing(config.S(8))
        lbl_fmt = QLabel(self._t("lbl_export_format", "Format eksportu:"))
        lbl_fmt.setFixedWidth(label_w)
        lbl_fmt.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_fmt.addWidget(lbl_fmt)

        self.format_items = [
            ("fcp7_xml", "Final Cut Pro 7 XML (.xml)"),
            ("otio",     "OpenTimelineIO (.otio)"),
            ("fcpxml",   "Apple FCPXML (.fcpxml)"),
            ("edl",      "CMX 3600 EDL (.edl)"),
        ]
        self.format_labels = [name for _, name in self.format_items]
        self.combo_fmt = CustomDropdown(self.format_labels)
        self.combo_fmt.setText(self.format_labels[0])
        self.combo_fmt.setFixedHeight(config.S(28))
        self.combo_fmt.valueChanged.connect(self._on_format_changed)
        r_fmt.addWidget(self.combo_fmt, 1)
        c_lay.addLayout(r_fmt)

        # ── 2. Sequence Name ──────────────────────────────────────────────────
        r_name = QHBoxLayout()
        r_name.setSpacing(config.S(8))
        lbl_name = QLabel(self._t("lbl_export_seq_name", "Nazwa sekwencji:"))
        lbl_name.setFixedWidth(label_w)
        lbl_name.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_name.addWidget(lbl_name)

        self.txt_seq_name = QLineEdit(self.default_seq_name)
        self.txt_seq_name.setFixedHeight(config.S(28))
        r_name.addWidget(self.txt_seq_name, 1)
        c_lay.addLayout(r_name)

        # ── 3. Timeline Frame Rate ────────────────────────────────────────────
        r_fps = QHBoxLayout()
        r_fps.setSpacing(config.S(8))
        lbl_fps = QLabel(self._t("lbl_export_fps", "Klatkaż osi czasu:"))
        lbl_fps.setFixedWidth(label_w)
        lbl_fps.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_fps.addWidget(lbl_fps)

        self.fps_options = ["23.976", "24.0", "25.0", "29.97", "30.0", "50.0", "59.94", "60.0"]
        def_fps_str = f"{self.default_fps:g}"
        if def_fps_str not in self.fps_options:
            self.fps_options.append(def_fps_str)

        self.combo_fps = CustomDropdown(self.fps_options)
        self.combo_fps.setText(def_fps_str)
        self.combo_fps.setFixedHeight(config.S(28))
        r_fps.addWidget(self.combo_fps, 1)
        c_lay.addLayout(r_fps)

        if self.fps_hint:
            lbl_f_hint = QLabel(self.fps_hint)
            lbl_f_hint.setStyleSheet(f"color: #38c172; font-size: {config.FS(7.5)}pt; font-style: italic; margin-left: {label_w + config.S(8)}px;")
            c_lay.addWidget(lbl_f_hint)

        # ── 4. Timeline Resolution ────────────────────────────────────────────
        r_res = QHBoxLayout()
        r_res.setSpacing(config.S(8))
        lbl_res = QLabel(self._t("lbl_export_res", "Rozdzielczość osi:"))
        lbl_res.setFixedWidth(label_w)
        lbl_res.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_res.addWidget(lbl_res)

        self.res_options = [
            f"{self.default_width} x {self.default_height} ({self._t('lbl_res_original', 'Oryginalna')})",
            "1920 x 1080 (Full HD 16:9)",
            "3840 x 2160 (4K UHD 16:9)",
            "1080 x 1920 (Pionowe / Shorts 9:16)",
            "2560 x 1440 (2K QHD 16:9)",
            "1280 x 720 (HD 16:9)"
        ]
        self.combo_res = CustomDropdown(self.res_options)
        self.combo_res.setText(self.res_options[0])
        self.combo_res.setFixedHeight(config.S(28))
        r_res.addWidget(self.combo_res, 1)
        c_lay.addLayout(r_res)

        # ── 5. Audio Track Preservation (with Info Icon) ──────────────────────
        self.w_audio_container = QWidget()
        self.w_audio_container.setStyleSheet("background: transparent;")
        r_audio = QHBoxLayout(self.w_audio_container)
        r_audio.setContentsMargins(0, 0, 0, 0)
        r_audio.setSpacing(config.S(6))

        self.lbl_aud = QLabel(self._t("lbl_export_preserve_audio", "Zachowaj oryginalne ścieżki audio (A1, A2...)"))
        self.lbl_aud.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_audio.addWidget(self.lbl_aud)

        # (i) Information icon with comprehensive explanation tooltip
        self.info_aud = self._create_info_icon("tt_export_preserve_audio")
        r_audio.addWidget(self.info_aud)
        r_audio.addStretch(1)

        self.tgl_audio = ToggleSwitch()
        self.tgl_audio.setChecked(True)
        r_audio.addWidget(self.tgl_audio)
        c_lay.addWidget(self.w_audio_container)

        self._audio_pref = True
        self.tgl_audio.toggled.connect(self._on_audio_toggled)

        # ── 6. Destination Folder ─────────────────────────────────────────────
        r_dest = QHBoxLayout()
        r_dest.setSpacing(config.S(8))

        lbl_dst = QLabel(self._t("lbl_export_dest", "Katalog zapisu:"))
        lbl_dst.setFixedWidth(label_w)
        lbl_dst.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_dest.addWidget(lbl_dst)

        self.txt_dest_dir = QLineEdit(self.default_dir)
        self.txt_dest_dir.setFixedHeight(config.S(28))
        r_dest.addWidget(self.txt_dest_dir, 1)

        btn_browse = QPushButton(self._t("btn_browse", "Przeglądaj..."))
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setFixedHeight(config.S(28))
        btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #ffffff; border: 1px solid #3a3a3a;
                border-radius: {config.S(4)}px; padding: 0px {config.S(12)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(8.5)}pt;
            }}
            QPushButton:hover {{ background-color: #333333; }}
        """)
        btn_browse.clicked.connect(self._on_browse_dest)
        r_dest.addWidget(btn_browse)
        c_lay.addLayout(r_dest)

        c_lay.addSpacing(config.S(8))

        # ── Bottom Action Buttons ─────────────────────────────────────────────
        h_actions = QHBoxLayout()
        h_actions.setSpacing(config.S(10))
        h_actions.addStretch()

        btn_cancel = QPushButton(self._t("btn_cancel", "Anuluj"))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setFixedHeight(config.S(32))
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #a0a0a0; border: 1px solid #3a3a3a;
                border-radius: {config.S(4)}px; padding: 0px {config.S(18)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9)}pt; font-weight: bold;
            }}
            QPushButton:hover {{ color: #ffffff; background-color: #2d2d2d; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        h_actions.addWidget(btn_cancel)

        self.btn_export = QPushButton()
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedHeight(config.S(32))
        self.btn_export.setMinimumWidth(config.S(110))
        self.btn_export.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: #1a7a3e; color: #ffffff; border: none;
                border-radius: {config.S(4)}px; padding: 0px {config.S(16)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #219653; }}
        """)

        btn_exp_lay = QHBoxLayout(self.btn_export)
        btn_exp_lay.setContentsMargins(config.S(14), 0, config.S(14), 0)
        btn_exp_lay.setSpacing(config.S(8))
        btn_exp_lay.addStretch(1)

        self.lbl_btn_export_text = QLabel(self._t("btn_export", "Eksportuj"))
        self.lbl_btn_export_text.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_btn_export_text.setStyleSheet(f"color: #ffffff; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; font-weight: bold; background: transparent; border: none;")
        btn_exp_lay.addWidget(self.lbl_btn_export_text)

        self.lbl_btn_export_icon = QLabel()
        self.lbl_btn_export_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_btn_export_icon.setStyleSheet("background: transparent; border: none;")
        self.lbl_btn_export_icon.setPixmap(get_export_pixmap(config.S(11), "#ffffff"))
        btn_exp_lay.addWidget(self.lbl_btn_export_icon)
        btn_exp_lay.addStretch(1)

        self.btn_export.clicked.connect(self._on_execute_export)
        h_actions.addWidget(self.btn_export)

        c_lay.addLayout(h_actions)
        root_l.addWidget(container)

        self._update_audio_toggle_state(animate=False)

    def _get_selected_format_id(self) -> str:
        selected_text = self.combo_fmt.text() if hasattr(self, 'combo_fmt') else ""
        for fid, fname in self.format_items:
            if fname == selected_text:
                return fid
        return "fcp7_xml"

    def _on_format_changed(self, text: str):
        self._update_audio_toggle_state(animate=True)

    def _on_audio_toggled(self, checked: bool):
        if self._get_selected_format_id() == "fcp7_xml":
            self._audio_pref = checked

    def _update_audio_toggle_state(self, animate: bool = True):
        fmt_id = self._get_selected_format_id()
        is_supported = (fmt_id == "fcp7_xml")

        self.w_audio_container.setEnabled(is_supported)
        self.w_audio_container.setAttribute(Qt.WA_TransparentForMouseEvents, not is_supported)

        # Update label color (full opacity #bbbbbb vs 35% dimmed #555555)
        lbl_color = "#bbbbbb" if is_supported else "#555555"
        self.lbl_aud.setStyleSheet(
            f"color: {lbl_color}; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';"
        )

        # Update info icon dimming
        if hasattr(self, 'info_aud'):
            if hasattr(self.info_aud, '_normal_pix') and self.info_aud._normal_pix:
                self.info_aud.setPixmap(self.info_aud._normal_pix if is_supported else self.info_aud._dimmed_pix)
            else:
                self.info_aud.setStyleSheet(f"color: {'#888888' if is_supported else '#444444'}; font-size: 11pt;")
            self.info_aud.setEnabled(is_supported)

        # Update toggle switch
        self.tgl_audio.setEnabled(is_supported)
        self.tgl_audio.blockSignals(True)
        if is_supported:
            self.tgl_audio.setChecked(self._audio_pref, animated=animate)
        else:
            self.tgl_audio.setChecked(False, animated=animate)
        self.tgl_audio.blockSignals(False)
        self.tgl_audio.update()

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(self, self._t("lbl_export_dest", "Katalog zapisu"), self.txt_dest_dir.text())
        if folder:
            self.txt_dest_dir.setText(folder)

    def _parse_resolution(self) -> tuple[int, int]:
        txt = self.combo_res.text()
        try:
            part = txt.split('(')[0].strip()
            w_str, h_str = part.split('x')
            return int(w_str.strip()), int(h_str.strip())
        except Exception:
            return self.default_width, self.default_height

    def _on_execute_export(self):
        """Builds and writes the selected timeline file."""
        selected_text = self.combo_fmt.text()
        fmt_id = "fcp7_xml"
        for fid, fname in self.format_items:
            if fname == selected_text:
                fmt_id = fid
                break

        ext_map = {
            "fcp7_xml": ".xml",
            "otio":     ".otio",
            "fcpxml":   ".fcpxml",
            "edl":      ".edl",
        }
        ext = ext_map.get(fmt_id, ".xml")

        seq_name = self.txt_seq_name.text().strip() or "BadWords_Sequence"
        dest_dir = self.txt_dest_dir.text().strip()
        if not dest_dir or not os.path.isdir(dest_dir):
            dest_dir = os.path.expanduser("~")

        out_filename = f"{seq_name}{ext}"
        out_path = os.path.join(dest_dir, out_filename)

        try:
            target_fps = float(self.combo_fps.text())
        except Exception:
            target_fps = self.default_fps

        width, height = self._parse_resolution()
        preserve_audio = self.tgl_audio.isChecked() and (fmt_id == "fcp7_xml")

        # Recalculate or adapt ops for target_fps if needed
        ops = self.ops
        if hasattr(self.engine, 'calculate_timeline_structure') and self.words_data:
            prefs = self.engine.load_preferences() or {}
            ops = self.engine.calculate_timeline_structure(self.words_data, target_fps, prefs)

        self.btn_export.setEnabled(False)
        self.lbl_btn_export_text.setText(self._t("btn_exporting", "Eksportowanie..."))
        self.lbl_btn_export_icon.hide()

        ok = False
        msg = ""

        if fmt_id == "fcp7_xml":
            ok, msg = assembler.build_standalone_fcp7_xml(
                self.clips_info, ops, out_path,
                fps=target_fps, width=width, height=height,
                preserve_audio_tracks=preserve_audio, timeline_name=seq_name
            )
        elif fmt_id == "otio":
            ok, msg = assembler.build_standalone_otio(
                self.clips_info, ops, out_path,
                fps=target_fps, width=width, height=height,
                preserve_audio_tracks=preserve_audio, timeline_name=seq_name
            )
        elif fmt_id == "fcpxml":
            ok, msg = assembler.build_standalone_fcpxml(
                self.clips_info, ops, out_path,
                fps=target_fps, width=width, height=height,
                preserve_audio_tracks=preserve_audio, timeline_name=seq_name
            )
        elif fmt_id == "edl":
            ok, msg = assembler.build_standalone_edl(
                self.clips_info, ops, out_path,
                fps=target_fps, preserve_audio_tracks=preserve_audio, timeline_name=seq_name
            )

        self.btn_export.setEnabled(True)
        self.lbl_btn_export_text.setText(self._t("btn_export", "Eksportuj"))
        self.lbl_btn_export_icon.show()

        if ok:
            succ_dlg = CustomMsgBox(
                self,
                self._t("dlg_export_title", "Eksport zakończony"),
                f"{self._t('msg_export_success', 'Oś czasu została pomyślnie wyeksportowana!')}\n\n{out_path}",
                self._t("btn_open_folder", "Otwórz folder"),
                btn_no_text=self._t("btn_close", "Zamknij")
            )
            if succ_dlg.exec():
                QDesktopServices.openUrl(QUrl.fromLocalFile(dest_dir))
            self.accept()
        else:
            err_dlg = CustomMsgBox(
                self,
                self._t("dlg_export_error", "Błąd eksportu"),
                f"{self._t('msg_export_failed', 'Nie udało się wyeksportować osi czasu:')}\n{msg}",
                "OK"
            )
            err_dlg.exec()
