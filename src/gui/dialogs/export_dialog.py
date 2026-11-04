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
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QFrame, QLineEdit, QFileDialog, QButtonGroup, QRadioButton
)
from PySide6.QtGui import QDesktopServices

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import CustomDropdown, ToggleSwitch
from gui.dialogs.msgbox import CustomMsgBox
from gui.utils import _app_icon, _txt
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

        self.setMinimumWidth(config.S(540))
        self.setFixedHeight(config.S(530))

        self._init_metadata()
        self._build_ui()

    def _t(self, key: str, default: str = "") -> str:
        if hasattr(self.parent_gui, "txt"):
            return self.parent_gui.txt(key, default)
        return _txt(self._lang, key, default)

    def _init_metadata(self):
        """Analyzes clips_info to determine default FPS, resolution, and hint text."""
        # Detect FPS
        video_fps_list = [c["fps"] for c in self.clips_info if c.get("has_video") and c.get("fps", 0) > 0]
        if video_fps_list:
            # Check if all same
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

        # Detect Resolution
        video_clips = [c for c in self.clips_info if c.get("has_video")]
        if video_clips:
            self.default_width = video_clips[0].get("width", 1920)
            self.default_height = video_clips[0].get("height", 1080)
        else:
            self.default_width = 1920
            self.default_height = 1080

        # Default destination folder
        first_path = self.clips_info[0]["path"] if self.clips_info else ""
        if first_path and os.path.isfile(first_path):
            self.default_dir = os.path.dirname(os.path.abspath(first_path))
            base_stem = os.path.splitext(os.path.basename(first_path))[0]
            self.default_seq_name = f"{base_stem}_BadWords_Cut"
        else:
            self.default_dir = os.path.expanduser("~")
            self.default_seq_name = f"BadWords_Timeline_{time.strftime('%Y%m%d_%H%M')}"

    def _build_ui(self):
        self.setStyleSheet(f"""
            QDialog, ExportDialog {{ background-color: transparent; }}
            QFrame#MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #333333;
                border-radius: {config.S(8)}px;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: {config.FS(13)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QLabel#lbl_sub {{
                color: #888888;
                font-size: {config.FS(8.5)}pt;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QLabel.section_lbl {{
                color: #d4d4d4;
                font-size: {config.FS(8.5)}pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
            }}
            QLineEdit {{
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
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
        outer_l.setContentsMargins(1, 1, 1, 1)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
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
        c_lay.setContentsMargins(config.S(20), config.S(14), config.S(20), config.S(16))
        c_lay.setSpacing(config.S(12))

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

        # ── 1. Format Selection Cards ─────────────────────────────────────────
        lbl_fmt = QLabel(self._t("lbl_export_format", "Format eksportu:"))
        lbl_fmt.setProperty("class", "section_lbl")
        c_lay.addWidget(lbl_fmt)

        self.btn_group_fmt = QButtonGroup(self)
        h_formats = QHBoxLayout()
        h_formats.setSpacing(config.S(8))

        self.formats = [
            ("fcp7_xml", "FCP 7 XML (.xml)", "DaVinci Resolve / Premiere"),
            ("otio", "OpenTimelineIO (.otio)", "Otwarty format (DaVinci/NLE)"),
            ("fcpxml", "FCPXML (.fcpxml)", "Final Cut Pro X / Resolve"),
            ("edl", "CMX 3600 (.edl)", "Lista cięć montażowych"),
        ]

        self.radio_buttons = {}
        for idx, (fmt_id, fmt_name, fmt_desc) in enumerate(self.formats):
            card = QFrame()
            card.setCursor(Qt.PointingHandCursor)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #1e1e1e;
                    border: 1px solid #333333;
                    border-radius: {config.S(5)}px;
                    padding: {config.S(4)}px;
                }}
                QFrame:hover {{
                    border-color: #38c172;
                    background-color: #242424;
                }}
            """)
            card_l = QVBoxLayout(card)
            card_l.setContentsMargins(config.S(6), config.S(6), config.S(6), config.S(6))
            card_l.setSpacing(config.S(2))

            rb = QRadioButton(fmt_name)
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: #ffffff; font-weight: bold; font-size: {config.FS(8.5)}pt;
                    font-family: "{config.UI_FONT_NAME}";
                }}
                QRadioButton::indicator {{
                    width: {config.S(13)}px; height: {config.S(13)}px;
                }}
            """)
            if idx == 0:
                rb.setChecked(True)
            self.btn_group_fmt.addButton(rb, idx)
            self.radio_buttons[fmt_id] = rb
            card_l.addWidget(rb)

            lbl_d = QLabel(fmt_desc)
            lbl_d.setStyleSheet(f"color: #888888; font-size: {config.FS(7.0)}pt; font-family: '{config.UI_FONT_NAME}'; padding-left: {config.S(18)}px;")
            card_l.addWidget(lbl_d)

            h_formats.addWidget(card, 1)

        c_lay.addLayout(h_formats)

        # ── 2. Sequence Parameters (Name, FPS, Resolution) ───────────────────
        params_box = QFrame()
        params_box.setStyleSheet(f"""
            QFrame {{
                background-color: #181818;
                border: 1px solid #282828;
                border-radius: {config.S(6)}px;
            }}
        """)
        p_lay = QVBoxLayout(params_box)
        p_lay.setContentsMargins(config.S(12), config.S(10), config.S(12), config.S(10))
        p_lay.setSpacing(config.S(8))

        # Row 1: Sequence Name
        r_name = QHBoxLayout()
        lbl_name = QLabel(self._t("lbl_export_seq_name", "Nazwa sekwencji:"))
        lbl_name.setFixedWidth(config.S(130))
        lbl_name.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_name.addWidget(lbl_name)

        self.txt_seq_name = QLineEdit(self.default_seq_name)
        r_name.addWidget(self.txt_seq_name, 1)
        p_lay.addLayout(r_name)

        # Row 2: FPS
        r_fps = QHBoxLayout()
        lbl_fps = QLabel(self._t("lbl_export_fps", "Klatkaż osi czasu:"))
        lbl_fps.setFixedWidth(config.S(130))
        lbl_fps.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_fps.addWidget(lbl_fps)

        self.fps_options = ["23.976", "24.0", "25.0", "29.97", "30.0", "50.0", "59.94", "60.0"]
        def_fps_str = f"{self.default_fps:g}"
        if def_fps_str not in self.fps_options:
            self.fps_options.append(def_fps_str)

        self.combo_fps = CustomDropdown(self.fps_options)
        self.combo_fps.setText(def_fps_str)
        self.combo_fps.setFixedHeight(config.S(26))
        r_fps.addWidget(self.combo_fps, 1)
        p_lay.addLayout(r_fps)

        if self.fps_hint:
            lbl_f_hint = QLabel(self.fps_hint)
            lbl_f_hint.setStyleSheet(f"color: #38c172; font-size: {config.FS(7.5)}pt; font-style: italic; margin-left: {config.S(135)}px;")
            p_lay.addWidget(lbl_f_hint)

        # Row 3: Resolution
        r_res = QHBoxLayout()
        lbl_res = QLabel(self._t("lbl_export_res", "Rozdzielczość osi:"))
        lbl_res.setFixedWidth(config.S(130))
        lbl_res.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_res.addWidget(lbl_res)

        self.res_options = [
            f"{self.default_width} x {self.default_height} (Oryginalna)",
            "1920 x 1080 (Full HD 16:9)",
            "3840 x 2160 (4K UHD 16:9)",
            "1080 x 1920 (Pionowe / Shorts 9:16)",
            "2560 x 1440 (2K QHD 16:9)",
            "1280 x 720 (HD 16:9)"
        ]
        self.combo_res = CustomDropdown(self.res_options)
        self.combo_res.setText(self.res_options[0])
        self.combo_res.setFixedHeight(config.S(26))
        r_res.addWidget(self.combo_res, 1)
        p_lay.addLayout(r_res)

        # Row 4: Preserve audio tracks switch
        r_audio = QHBoxLayout()
        lbl_aud = QLabel(self._t("lbl_export_preserve_audio", "Zachowaj oryginalne ścieżki audio (A1, A2...)"))
        lbl_aud.setStyleSheet(f"color: #bbbbbb; font-size: {config.FS(8.5)}pt; font-family: '{config.UI_FONT_NAME}';")
        r_audio.addWidget(lbl_aud, 1)

        self.tgl_audio = ToggleSwitch()
        self.tgl_audio.setChecked(True)
        r_audio.addWidget(self.tgl_audio)
        p_lay.addLayout(r_audio)

        c_lay.addWidget(params_box)

        # ── 3. Destination Folder ─────────────────────────────────────────────
        r_dest = QHBoxLayout()
        r_dest.setSpacing(config.S(6))

        lbl_dst = QLabel(self._t("lbl_export_dest", "Katalog zapisu:"))
        lbl_dst.setFixedWidth(config.S(110))
        lbl_dst.setStyleSheet(f"color: #d4d4d4; font-size: {config.FS(8.5)}pt; font-weight: bold; font-family: '{config.UI_FONT_NAME}';")
        r_dest.addWidget(lbl_dst)

        self.txt_dest_dir = QLineEdit(self.default_dir)
        r_dest.addWidget(self.txt_dest_dir, 1)

        btn_browse = QPushButton(self._t("btn_browse", "Przeglądaj..."))
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #ffffff; border: 1px solid #3a3a3a;
                border-radius: {config.S(4)}px; padding: {config.S(4)}px {config.S(10)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(8.5)}pt;
            }}
            QPushButton:hover {{ background-color: #333333; }}
        """)
        btn_browse.clicked.connect(self._on_browse_dest)
        r_dest.addWidget(btn_browse)

        c_lay.addLayout(r_dest)

        c_lay.addStretch(1)

        # ── Bottom Action Buttons ─────────────────────────────────────────────
        h_actions = QHBoxLayout()
        h_actions.setSpacing(config.S(10))
        h_actions.addStretch()

        btn_cancel = QPushButton(self._t("btn_cancel", "Anuluj"))
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #a0a0a0; border: 1px solid #3a3a3a;
                border-radius: {config.S(4)}px; padding: {config.S(6)}px {config.S(18)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9)}pt; font-weight: bold;
            }}
            QPushButton:hover {{ color: #ffffff; background-color: #2d2d2d; }}
        """)
        btn_cancel.clicked.connect(self.reject)
        h_actions.addWidget(btn_cancel)

        self.btn_export = QPushButton(self._t("btn_export", "Eksportuj"))
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setStyleSheet(f"""
            QPushButton {{
                background-color: #1a7a3e; color: #ffffff; border: none;
                border-radius: {config.S(4)}px; padding: {config.S(6)}px {config.S(24)}px;
                font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #219653; }}
        """)
        self.btn_export.clicked.connect(self._on_execute_export)
        h_actions.addWidget(self.btn_export)

        c_lay.addLayout(h_actions)
        root_l.addWidget(container)

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
        selected_idx = self.btn_group_fmt.checkedId()
        if selected_idx < 0 or selected_idx >= len(self.formats):
            selected_idx = 0

        fmt_id = self.formats[selected_idx][0]
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
        preserve_audio = self.tgl_audio.isChecked()

        # Recalculate or adapt ops for target_fps if needed
        ops = self.ops
        if hasattr(self.engine, 'calculate_timeline_structure') and self.words_data:
            prefs = self.engine.load_preferences() or {}
            ops = self.engine.calculate_timeline_structure(self.words_data, target_fps, prefs)

        self.btn_export.setEnabled(False)
        self.btn_export.setText("Eksportowanie...")

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
        self.btn_export.setText(self._t("btn_export", "Eksportuj"))

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
                self, "Błąd eksportu", f"Nie udało się wyeksportować osi czasu:\n{msg}", "OK"
            )
            err_dlg.exec()
