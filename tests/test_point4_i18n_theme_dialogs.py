#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Point 4 regression & visual test suite:
- 11-language i18n parity, zero emojis, zero long dashes, English fallbacks
- Localized BootSplash via i18n_lite
- Global OS light-theme immunity (Fusion + complete dark QPalette + MarqueeLabel guard)
- Vector icons across dropdowns, search overlay, drop zone, info icons, dialogs
- Responsive scaling (75%-200%), height-clamped dialogs, Processing/Heal progress bars
- Settings Export/Import (atomic + user.json isolation), Reset Defaults, Update toggle coupling
"""

import glob
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BADWORDS_DEV"] = "1"
app = QApplication.instance() or QApplication([])

import config
from gui.dialogs.export_dialog import ExportDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.update_dialog import UpdateCheckThread, UpdateNotifyDialog
from gui.dialogs.v4_migration_dialog import V4MigrationDialog
from gui.main_window import BadWordsGUI
from gui.utils import _txt, create_info_icon, get_vector_icon, get_vector_pixmap
from gui.widgets.buttons import CustomCheckBox, CustomDropdown, TitleDropdown, TrackSquareCheckbox
from gui.widgets.file_drop_zone import FileDropZone
from gui.widgets.labels import QLabel as MarqueeLabel
from gui.widgets.progress_bar import LiquidProgressBar
from i18n import get_trans
from startup.boot_splash import BootSplash
from startup.i18n_lite import detect_language, t as lite_txt
from startup.self_heal import build_dark_progress_dialog


class TestPoint4I18nThemeDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(cls.artifacts_dir, exist_ok=True)
        cls._orig_checked = UpdateCheckThread._checked
        cls._orig_cached = UpdateCheckThread._cached_result

    @classmethod
    def tearDownClass(cls):
        UpdateCheckThread._checked = cls._orig_checked
        UpdateCheckThread._cached_result = cls._orig_cached

    def setUp(self):
        self._orig_mode = getattr(config, "UI_SCALE_MODE", "auto")
        self._orig_pct = getattr(config, "UI_SCALE_PERCENT", 100)
        self._orig_palette = QApplication.palette()
        UpdateCheckThread._checked = True
        UpdateCheckThread._cached_result = None

    def tearDown(self):
        config.apply_ui_scaling(mode=self._orig_mode, pct=self._orig_pct)
        config.apply_dark_app_theme(app)

    def _make_engine(self, prefs_override=None, tmp_dir=None):
        prefs = dict(config.DEFAULT_SETTINGS)
        prefs["gui_lang"] = "en"
        prefs["settings_view_mode"] = "basic"
        prefs["timeline_assembly_method"] = "xml"
        prefs["force_xml_assembly"] = True
        prefs["ui_scale_mode"] = "manual"
        prefs["ui_scale_pct"] = 100
        if prefs_override:
            prefs.update(prefs_override)

        saved_store = dict(prefs)

        def _load():
            return dict(saved_store)

        def _save(new_d):
            saved_store.update(new_d)

        engine = MagicMock()
        engine.load_preferences.side_effect = _load
        engine.save_preferences.side_effect = _save
        engine.saved_store = saved_store
        engine.current_lang = saved_store.get("gui_lang", "en")

        mock_doc = MagicMock()
        mock_doc.is_win = False
        mock_doc.is_mac = False
        mock_doc.install_dir = tmp_dir or "/opt/badwords_test"
        mock_doc.log_file = os.path.join(tmp_dir or "/opt/badwords_test", "badwords_debug.log")
        mock_doc.settings_file = os.path.join(tmp_dir or "/opt/badwords_test", "settings.json")
        mock_doc.user_data = {"telemetry_opt_in": False, "telemetry_geo": True, "auto_crash_report": True}
        mock_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
        mock_doc.get_resolve_installation_info.return_value = {"installed": True, "edition": "Studio"}
        mock_doc.get_telemetry_pref.return_value = True
        mock_doc.get_subprocess_kwargs.return_value = {}
        engine.os_doc = mock_doc

        mock_rh = MagicMock()
        mock_rh.is_connected.return_value = False
        mock_rh.is_bridge_connected.return_value = False
        mock_rh.is_free_21_1_or_newer.return_value = False
        mock_rh.get_all_timelines.return_value = ["Timeline 1"]
        engine.resolve_handler = mock_rh
        return engine

    def test_11_language_parity_fallbacks_and_bootsplash_localization(self):
        """All 11 locale files stay key-identical, emoji-free, and BootSplash obeys settings gui_lang."""
        en = json.load(open(os.path.join(config.ROOT_DIR if hasattr(config, "ROOT_DIR") else os.path.dirname(os.path.dirname(__file__)), "src", "i18n", "en.json"), encoding="utf-8"))
        en_keys = set(en.keys())
        i18n_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "i18n")

        for path in sorted(glob.glob(os.path.join(i18n_dir, "*.json"))):
            data = json.load(open(path, encoding="utf-8"))
            self.assertEqual(set(data.keys()), en_keys, f"Key mismatch in {os.path.basename(path)}")
            for k, v in data.items():
                self.assertIsInstance(v, str)
                self.assertTrue(v.strip(), f"Empty translation {path}:{k}")
                self.assertNotIn("\u2013", v, f"En-dash found in {path}:{k}")
                self.assertNotIn("\u2014", v, f"Em-dash found in {path}:{k}")
                self.assertNotIn("3.0", v, f"Obsolete BadWords 3.0 in {path}:{k}")
                for g in "🛈🔍⏳⌛✔✓✕🚀💡🔥":
                    self.assertNotIn(g, v, f"UI emoji {g!r} found in {path}:{k}")

        # ZH must have real Chinese translations for updated core keys
        zh = json.load(open(os.path.join(i18n_dir, "zh.json"), encoding="utf-8"))
        self.assertNotEqual(zh["v4_mig_heading"], en["v4_mig_heading"])
        self.assertNotEqual(zh["msg_settings_export_ok"], en["msg_settings_export_ok"])

        # Fallback to English on empty string or missing key
        self.assertEqual(_txt("en", "btn_ok", "Fallback"), en["btn_ok"])
        with patch.dict(config.TRANS["pl"], {"btn_ok": ""}):
            self.assertEqual(_txt("pl", "btn_ok", "Fallback"), en["btn_ok"])
            self.assertEqual(get_trans("btn_ok", "pl"), en["btn_ok"])

        # BootSplash localizes strictly from detect_language() (DEV/installed setting)
        expected_zh_loading = lite_txt("lbl_loading", lang="zh").rstrip(".… ").upper()
        expected_pl_loading = lite_txt("lbl_loading", lang="pl").rstrip(".… ").upper()
        with tempfile.TemporaryDirectory() as td:
            fake_src = os.path.join(td, "src")
            fake_dev = os.path.join(td, ".dev_workspace")
            os.makedirs(fake_src, exist_ok=True)
            os.makedirs(fake_dev, exist_ok=True)
            sp = os.path.join(fake_dev, "settings.json")
            with open(sp, "w", encoding="utf-8") as f:
                json.dump({"gui_lang": "zh"}, f)
            with patch("startup.i18n_lite._default_src_dir", return_value=fake_src):
                self.assertEqual(detect_language(), "zh")
                splash_zh = BootSplash()
                self.assertEqual(splash_zh._lang, "zh")
                self.assertEqual(splash_zh._loading_base, expected_zh_loading)
                self.assertNotIn("LOADING", splash_zh._lbl_loading.text())
                splash_zh.show()
                app.processEvents()
                out_zh = os.path.join(self.artifacts_dir, "point4_bootsplash_zh.png")
                self.assertTrue(splash_zh.grab().save(out_zh))
                splash_zh.close()

            with open(sp, "w", encoding="utf-8") as f:
                json.dump({"gui_lang": "pl"}, f)
            with patch("startup.i18n_lite._default_src_dir", return_value=fake_src):
                splash_pl = BootSplash()
                self.assertEqual(splash_pl._lang, "pl")
                self.assertEqual(splash_pl._loading_base, expected_pl_loading)
                splash_pl.show()
                app.processEvents()
                out_pl = os.path.join(self.artifacts_dir, "point4_bootsplash_pl.png")
                self.assertTrue(splash_pl.grab().save(out_pl))
                splash_pl.close()

    def test_os_light_theme_immunity_and_marquee_contrast(self):
        """Fusion + dark QPalette defeats OS light mode; MarqueeLabel never paints black-on-black text."""
        light_pal = QPalette()
        light_pal.setColor(QPalette.Window, QColor("#f5f5f5"))
        light_pal.setColor(QPalette.Base, QColor("#ffffff"))
        light_pal.setColor(QPalette.WindowText, QColor("#000000"))
        light_pal.setColor(QPalette.Text, QColor("#000000"))
        light_pal.setColor(QPalette.ButtonText, QColor("#000000"))
        app.setPalette(light_pal)

        config.apply_dark_app_theme(app)
        self.assertEqual(app.style().objectName().lower(), "fusion")
        dark_pal = app.palette()
        self.assertGreater(dark_pal.color(QPalette.WindowText).lightness(), 180)
        self.assertLess(dark_pal.color(QPalette.Window).lightness(), 50)
        self.assertGreater(dark_pal.color(QPalette.ButtonText).lightness(), 180)

        # Simulate hostile widget-level black WindowText palette on MarqueeLabel
        lbl = MarqueeLabel("Sample scrolling label text")
        lbl.setPalette(light_pal)
        lbl.setStyleSheet("")
        resolved = lbl._get_text_color()
        self.assertGreater(resolved.lightness(), 170)

        lbl_colored = MarqueeLabel("Explicit cyan label")
        lbl_colored.setStyleSheet("color: #2ecc71; background: transparent;")
        self.assertEqual(lbl_colored._get_text_color().name().lower(), "#2ecc71")

        # TitleDropdown strips any legacy arrow text and renders vector chevron cleanly
        td = TitleDropdown(["Chapter 1", "Chapter 2"])
        td.setText("Chapter 1  ▾")
        self.assertEqual(td.currentText(), "Chapter 1")
        td.setFixedSize(180, 32)
        td.show()
        cd = CustomDropdown(["Final Cut Pro 7 XML (.xml)", "OpenTimelineIO (.otio)"])
        cd.setFixedSize(220, 30)
        cd.show()
        app.processEvents()
        self.assertTrue(td.grab().save(os.path.join(self.artifacts_dir, "point4_title_dropdown.png")))
        self.assertTrue(cd.grab().save(os.path.join(self.artifacts_dir, "point4_custom_dropdown.png")))
        td.close()
        cd.close()

    def test_vector_icons_and_dropzone_zero_emojis(self):
        """All vector helpers produce non-null HiDPI pixmaps and FileDropZone/Checkboxes use zero emojis."""
        for kind in ("info", "question", "warning", "search", "close", "check", "chevron_up", "chevron_down", "arrow_right", "plus", "minus"):
            pm = get_vector_pixmap(kind, size=16, color="#d4d4d4")
            self.assertFalse(pm.isNull(), f"Vector pixmap {kind} is null")
            self.assertFalse(get_vector_icon(kind, size=16).isNull(), f"Vector icon {kind} is null")

        chk = CustomCheckBox("Auto check")
        sq = TrackSquareCheckbox("A1", "#39ff7a")
        sq.setChecked(True)
        chk.setChecked(True)
        self.assertEqual(chk.lbl.text(), "Auto check")

        dz = FileDropZone()
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf1, \
             tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf2:
            tmp_mp4, tmp_wav = tf1.name, tf2.name
            tf1.write(b"\x00\x00\x00\x20ftypmp42")
            tf2.write(b"RIFF\x24\x00\x00\x00WAVE")
        try:
            dz.add_files([tmp_mp4, tmp_wav])
            dz.set_texts(lang="en", queue_txt=_txt("en", "lbl_queue"))
            dz.resize(420, 180)
            dz.show()
            app.processEvents()
            self.assertTrue(dz.grab().save(os.path.join(self.artifacts_dir, "point4_dropzone_en.png")))
            self.assertIn(_txt("en", "lbl_queue"), dz.lbl_multi_summary.text())
            self.assertNotIn("Kolejka", dz.lbl_multi_summary.text())
        finally:
            dz.close()
            for p in (tmp_mp4, tmp_wav):
                try:
                    os.remove(p)
                except OSError:
                    pass

        info = create_info_icon("tt_ui_scaling", txt_fn=lambda k: _txt("en", k))
        self.assertNotIn("🛈", info.text())
        self.assertTrue(bool(info.custom_tooltip_text))
        self.assertFalse(info.pixmap().isNull())

    def test_responsive_dialogs_scaled_75_to_200_and_artifacts(self):
        """Scaled Export/Update/Migration/Heal/Processing windows fit without clipping and render cleanly."""
        engine = self._make_engine()
        parent = QWidget()
        parent.lang = "en"
        parent.engine = engine

        # 1. ExportDialog at 150% scale in English
        config.apply_ui_scaling(mode="manual", pct=150)
        exp = ExportDialog(
            parent,
            engine,
            [{"path": "/tmp/demo_clip.mp4", "has_video": True, "fps": 23.976, "width": 1920, "height": 1080}],
            [],
        )
        exp.show()
        app.processEvents()
        self.assertNotEqual(exp.info_aud.text(), "🛈")
        exp_scroll = exp.findChild(QWidget, "ExportScroll")
        if exp_scroll is not None:
            self.assertFalse(exp_scroll.verticalScrollBar().isVisible())
        self.assertTrue(exp.grab().save(os.path.join(self.artifacts_dir, "point4_export_150_en.png")))
        exp.close()

        # 2. UpdateNotifyDialog at 100% scale in Polish
        config.apply_ui_scaling(mode="manual", pct=100)
        upd = UpdateNotifyDialog(
            parent=parent,
            lang="pl",
            current_ver="4.0.1",
            latest_ver="4.0.2",
            gh_url="https://github.com/veritus-git/BadWords/releases",
            gl_url="https://gitlab.com/badwords/BadWords/-/releases",
            is_win=False,
            is_mac=False,
            install_dir=".",
            release_notes="- Improved localization across all 11 languages\n- Vector SVG UI icons",
        )
        upd.show()
        app.processEvents()
        # Arrow label uses crisp vector pixmap, not literal "→"; primary button keeps themed style
        arrow_labels = [l for l in upd.findChildren(QLabel) if l.text() == "→"]
        self.assertEqual(arrow_labels, [])
        self.assertNotIn("background: transparent", upd._btn_primary.styleSheet())
        self.assertTrue(upd.grab().save(os.path.join(self.artifacts_dir, "point4_update_pl.png")))
        upd.close()

        # 3. V4MigrationDialog in Chinese (centralized i18n JSON + vector close + full button visibility)
        mig = V4MigrationDialog(lang="zh", parent=parent)
        mig.show()
        app.processEvents()
        btn_gh = mig.findChild(QWidget, "PrimaryBtn")
        self.assertIsNotNone(btn_gh)
        self.assertTrue(btn_gh.isVisible())
        self.assertLessEqual(btn_gh.mapTo(mig, btn_gh.rect().bottomLeft()).y(), mig.height())
        self.assertTrue(mig.grab().save(os.path.join(self.artifacts_dir, "point4_migration_zh.png")))
        mig.close()

        from PySide6.QtCore import QRect
        tight_screen = MagicMock()
        tight_screen.availableGeometry.return_value = QRect(0, 0, 1280, 720)
        config.apply_ui_scaling(mode="manual", pct=200)
        with patch("PySide6.QtGui.QGuiApplication.primaryScreen", return_value=tight_screen), \
             patch("PySide6.QtGui.QGuiApplication.screenAt", return_value=tight_screen):
            exp_200 = ExportDialog(parent, engine, [], [])
            self.assertLessEqual(exp_200.width(), 1280)
            self.assertLessEqual(exp_200.height(), 720)
            exp_200.close()
            upd_200 = UpdateNotifyDialog(parent, "en", "4.0.1", "4.0.2", "https://gh", "https://gl", False, False, ".", "- Fix")
            self.assertLessEqual(upd_200.width(), 1280)
            self.assertLessEqual(upd_200.height(), 720)
            upd_200.close()
            mig_200 = V4MigrationDialog(lang="en", parent=parent)
            self.assertLessEqual(mig_200.width(), 1280)
            self.assertLessEqual(mig_200.height(), 720)
            mig_200.close()

        config.apply_ui_scaling(mode="manual", pct=75)
        exp_75 = ExportDialog(parent, engine, [], [])
        self.assertGreater(exp_75.width(), 300)
        exp_75.close()
        config.apply_ui_scaling(mode="manual", pct=100)

        # 4. Self-heal progress dialog uses LiquidProgressBar indeterminate
        heal = build_dark_progress_dialog("Self-Check", _txt("pl", "lbl_loading"))
        bars = heal.findChildren(LiquidProgressBar)
        self.assertEqual(len(bars), 1)
        bars[0]._indet_offset = 0.45
        heal.show()
        app.processEvents()
        self.assertTrue(heal.grab().save(os.path.join(self.artifacts_dir, "point4_heal_liquid.png")))
        heal.close()
        parent.close()

    def test_settings_update_coupling_export_import_and_reset(self):
        """Settings update toggles dim & obey disable, Export/Import validates cleanly, Reset cleans user/settings."""
        with tempfile.TemporaryDirectory() as td:
            engine = self._make_engine(
                prefs_override={
                    "auto_check_updates": False,
                    "auto_update_on_start": True,
                    "custom_markers": [{"name": "Note", "color": "Blue"}],
                    "shortcuts": {"custom_marker_Note": "N", "shortcut_undo": "Ctrl+Shift+Z"},
                },
                tmp_dir=td,
            )
            UpdateCheckThread._checked = False
            dlg = SettingsDialog(engine)
            dlg.show()
            app.processEvents()

            # Auto-check OFF at open -> disabled status + Check Now button visible, auto-update toggle dimmed & blocked
            self.assertEqual(dlg._lbl_ver_status.text(), dlg.txt("msg_updates_disabled"))
            self.assertFalse(dlg._btn_ver_check.isHidden())
            self.assertTrue(dlg.tgl_auto_update_on_start._blocked)
            self.assertFalse(dlg.tgl_auto_update_on_start.isChecked())
            self.assertTrue(dlg.grab().save(os.path.join(self.artifacts_dir, "point4_settings_updates_disabled.png")))

            # Toggling ON directly from Auto-check disabled MUST clear msg_updates_disabled immediately!
            with patch.object(UpdateCheckThread, "_fetch_json", return_value={"tag_name": f"v{config.VERSION}", "body": ""}):
                dlg.tgl_auto_check_updates.setChecked(True, animated=False)
                app.processEvents()
                dlg._settings_ver_thread.wait(2000)
                app.processEvents()
            self.assertFalse(dlg.tgl_auto_update_on_start._blocked)
            self.assertTrue(dlg._btn_ver_check.isHidden())
            self.assertEqual(dlg._lbl_ver_status.text(), dlg.txt("lbl_ver_up_to_date"))
            self.assertFalse(dlg._lbl_ver_icon.isHidden())

            # Toggle OFF -> shows msg_updates_disabled & Check now; manual Check now works offline too
            dlg.tgl_auto_check_updates.setChecked(False, animated=False)
            app.processEvents()
            self.assertEqual(dlg._lbl_ver_status.text(), dlg.txt("msg_updates_disabled"))
            self.assertFalse(dlg._btn_ver_check.isHidden())
            with patch.object(UpdateCheckThread, "_fetch_json", return_value={"tag_name": f"v{config.VERSION}", "body": ""}):
                dlg._btn_ver_check.click()
                dlg._settings_ver_thread.wait(2000)
                app.processEvents()
            self.assertNotIn("✓", dlg._lbl_ver_status.text())
            self.assertFalse(dlg._lbl_ver_icon.isHidden())

            # Simulate _reload_preferences() restoring saved True after being disabled -> must NOT stick disabled
            dlg.tgl_auto_check_updates.setChecked(True, animated=False)
            app.processEvents()
            dlg.tgl_auto_check_updates.setChecked(False, animated=False)
            app.processEvents()
            self.assertEqual(dlg._lbl_ver_status.text(), dlg.txt("msg_updates_disabled"))
            engine.saved_store["auto_check_updates"] = True
            with patch.object(UpdateCheckThread, "_fetch_json", return_value={"tag_name": f"v{config.VERSION}", "body": ""}):
                dlg._reload_preferences()
                dlg._settings_ver_thread.wait(2000)
                app.processEvents()
            self.assertEqual(dlg._lbl_ver_status.text(), dlg.txt("lbl_ver_up_to_date"))
            self.assertTrue(dlg._btn_ver_check.isHidden())
            self.assertTrue(dlg.grab().save(os.path.join(self.artifacts_dir, "point4_settings_updates_uptodate.png")))

            # Export settings excludes DEFAULT_USER_DATA consent keys and preserves current changes
            exp_path = os.path.join(td, "exported_settings.json")
            dlg._ensure_page_built(dlg.TAB_EDITOR)
            dlg.spin_fsize.setValue(16)
            with patch("PySide6.QtWidgets.QFileDialog.getSaveFileName", return_value=(exp_path, "JSON files (*.json)")), \
                 patch("gui.dialogs.settings_dialog.CustomMsgBox") as mock_mb:
                mock_mb.return_value.exec.return_value = True
                dlg._on_export_settings()
                mock_mb.assert_called_once()
                self.assertIn(exp_path, str(mock_mb.call_args))
                self.assertNotIn("{path}", str(mock_mb.call_args))
            self.assertTrue(os.path.isfile(exp_path))
            exported = json.load(open(exp_path, encoding="utf-8"))
            self.assertEqual(exported["editor_font_size"], 16)
            self.assertNotIn("telemetry_opt_in", exported)
            self.assertNotIn("auto_crash_report", exported)

            # Import corrupt JSON shows formatted error without overwriting active preferences
            bad_path = os.path.join(td, "corrupt.json")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("{invalid json")
            before_saved = dict(engine.saved_store)
            with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=(bad_path, "JSON files (*.json)")), \
                 patch("gui.dialogs.settings_dialog.CustomMsgBox") as mock_mb:
                mock_mb.return_value.exec.return_value = True
                dlg._on_import_settings()
                err_prefix = dlg.txt("msg_settings_import_err", error="X").splitlines()[0]
                self.assertIn(err_prefix, str(mock_mb.call_args))
                self.assertNotIn("{error}", str(mock_mb.call_args))
            self.assertEqual(engine.saved_store, before_saved)

            # Import valid file updates settings and strips user consent keys
            imp_path = os.path.join(td, "valid_import.json")
            with open(imp_path, "w", encoding="utf-8") as f:
                json.dump({"editor_font_size": 18, "telemetry_opt_in": True, "gui_lang": "pl"}, f)
            with patch("PySide6.QtWidgets.QFileDialog.getOpenFileName", return_value=(imp_path, "JSON files (*.json)")), \
                 patch("gui.dialogs.settings_dialog.CustomMsgBox") as mock_mb, \
                 patch.object(dlg, "reject"):
                mock_mb.return_value.exec.return_value = True
                dlg._on_import_settings()
            self.assertEqual(engine.saved_store["editor_font_size"], 18)
            self.assertNotIn("telemetry_opt_in", engine.saved_store)
            self.assertEqual(dlg.spin_fsize.value(), 18)

            # Restore All Defaults keeping markers vs deleting markers
            dlg._ensure_all_pages_built()
            dlg.spin_beam_size.setValue(4)
            with patch("gui.dialogs.settings_dialog.CustomMsgBox") as mock_mb, \
                 patch.object(dlg, "_apply_live_ui_scale"):
                inst = mock_mb.return_value
                inst.exec.return_value = 1  # QDialog.Accepted
                inst.is_checkbox_checked.return_value = True
                dlg._restore_all_defaults()
            self.assertEqual(engine.saved_store["custom_markers"], [])
            self.assertNotIn("custom_marker_Note", engine.saved_store["shortcuts"])
            self.assertNotIn("telemetry_opt_in", engine.saved_store)
            engine.os_doc.set_telemetry_pref.assert_any_call("auto_crash_report", True)
            engine.os_doc.set_telemetry_pref.assert_any_call("telemetry_opt_in", False)
            self.assertEqual(dlg.spin_beam_size.value(), config.DEFAULT_SETTINGS["ai_beam_size"])

            dlg.close()

    def test_mainwindow_live_language_and_update_guard(self):
        """MainWindow respects auto_check_updates=False, shows silent update notice, and switches scale/lang live."""
        engine = self._make_engine({"gui_lang": "en", "auto_check_updates": False, "auto_update_on_start": True})
        orig_pop = BadWordsGUI._populate_timeline_track_combos
        orig_tel = BadWordsGUI.check_telemetry
        orig_upd = BadWordsGUI._start_update_check
        orig_pre = BadWordsGUI._preload_settings
        BadWordsGUI._populate_timeline_track_combos = lambda self: None
        BadWordsGUI.check_telemetry = lambda self: None
        BadWordsGUI._start_update_check = lambda self: None
        BadWordsGUI._preload_settings = lambda self: None
        try:
            win = BadWordsGUI(engine, engine.resolve_handler)
        finally:
            BadWordsGUI._populate_timeline_track_combos = orig_pop
            BadWordsGUI.check_telemetry = orig_tel
            BadWordsGUI._start_update_check = orig_upd
            BadWordsGUI._preload_settings = orig_pre

        try:
            # Verify auto_check_updates=False prevents _start_update_check from launching UpdateCheckThread
            win._update_thread = None
            win._start_update_check()
            self.assertIsNone(win._update_thread)

            # Verify Processing page at 125% scale renders English text & rounded LiquidProgressBar cleanly
            config.apply_ui_scaling(mode="manual", pct=125)
            win.rebuild_ui_for_scale()
            win.resize(1280, 760)
            win.show()
            win.go_to_page(1)
            win.bar_processing._value = 42.0
            win.lbl_first_run_hint.setText(win.txt("first_run_hint_1"))
            win.lbl_first_run_hint.show()
            win._hint_opacity.setOpacity(1.0)
            app.processEvents()
            self.assertNotIn("Inicjalizowanie", win.lbl_processing_status.text())
            self.assertTrue(win.lbl_first_run_hint.wordWrap())
            self.assertTrue(win.grab().save(os.path.join(self.artifacts_dir, "point4_processing_125_en.png")))

            # Switch to Polish live via engine prefs + rebuild -> Polish UI active immediately
            engine.saved_store["gui_lang"] = "pl"
            win.rebuild_ui_for_scale()
            app.processEvents()
            self.assertEqual(win.lang, "pl")
            self.assertEqual(win.lbl_processing_status.text(), _txt("pl", "status_whisper_init"))
        finally:
            try:
                app.removeEventFilter(win)
                if getattr(win, "_global_app_filter", None):
                    app.removeEventFilter(win._global_app_filter)
            except Exception:
                pass
            win.closeEvent = lambda e: e.accept()
            win.close()
            win.deleteLater()


if __name__ == "__main__":
    unittest.main()
