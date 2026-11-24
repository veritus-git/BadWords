#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for settings refactor, version detection, UI scaling,
DaVinci assembly toggling, and telemetry drop shadow.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BADWORDS_DEV"] = "1"
app = QApplication.instance() or QApplication([])

import config
from config.app_constants import _detect_version, _DEFAULT_VERSION
from gui.widgets.buttons import AssemblyModeSelector
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.telemetry_popup import TelemetryPopup
from gui.dialogs.crash_report_dialog import CrashReportConsentDialog


class TestSettingsAndVersion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gui.dialogs.update_dialog import UpdateCheckThread
        UpdateCheckThread._checked = True
        UpdateCheckThread._cached_result = ("4.0.1", "https://github.com", "https://gitlab.com", "")

    def setUp(self):
        self._initial_scale = config.SCALE_FACTOR
        self._initial_pct = getattr(config, "UI_SCALE_PERCENT", 100)

    def tearDown(self):
        config.set_ui_scale(self._initial_pct)

    # -------------------------------------------------------------------------
    # 1. Version Detection Tests
    # -------------------------------------------------------------------------
    def test_version_detection_exact_tag(self):
        """Verify _detect_version extracts clean tag without leading 'v'."""
        with patch("subprocess.check_output") as mock_git:
            mock_git.return_value = b"v4.0.2\n"
            version = _detect_version()
            self.assertEqual(version, "4.0.2")

            mock_git.return_value = b"4.0.3\n"
            version = _detect_version()
            self.assertEqual(version, "4.0.3")

    def test_version_detection_tag_with_commits(self):
        """Verify _detect_version cleans commit offsets and hashes."""
        with patch("subprocess.check_output") as mock_git:
            mock_git.return_value = b"v4.0.2-3-gabcdef\n"
            version = _detect_version()
            self.assertEqual(version, "4.0.2")

    def test_version_detection_fallback(self):
        """Verify fallback to _DEFAULT_VERSION when git command fails."""
        with patch("subprocess.check_output", side_effect=Exception("git missing")):
            version = _detect_version()
            self.assertEqual(version, _DEFAULT_VERSION)

    # -------------------------------------------------------------------------
    # 2. Dynamic UI Scaling Tests
    # -------------------------------------------------------------------------
    def test_ui_scaling_ranges_and_clamping(self):
        """Verify UI scaling clamped between 75% and 200%."""
        config.set_ui_scale(100)
        self.assertEqual(config.UI_SCALE_PERCENT, 100)
        self.assertAlmostEqual(config.SCALE_FACTOR, 1.0, places=2)
        self.assertEqual(config.S(20), 20)

        config.set_ui_scale(75)
        self.assertEqual(config.UI_SCALE_PERCENT, 75)
        self.assertAlmostEqual(config.SCALE_FACTOR, 0.75, places=2)
        self.assertEqual(config.S(20), 15)

        config.set_ui_scale(150)
        self.assertEqual(config.UI_SCALE_PERCENT, 150)
        self.assertAlmostEqual(config.SCALE_FACTOR, 1.5, places=2)
        self.assertEqual(config.S(20), 30)

        config.set_ui_scale(200)
        self.assertEqual(config.UI_SCALE_PERCENT, 200)
        self.assertAlmostEqual(config.SCALE_FACTOR, 2.0, places=2)
        self.assertEqual(config.S(20), 40)

        # Underflow clamped to 75
        config.set_ui_scale(40)
        self.assertEqual(config.UI_SCALE_PERCENT, 75)
        self.assertAlmostEqual(config.SCALE_FACTOR, 0.75, places=2)

        # Overflow clamped to 200
        config.set_ui_scale(250)
        self.assertEqual(config.UI_SCALE_PERCENT, 200)
        self.assertAlmostEqual(config.SCALE_FACTOR, 2.0, places=2)

    # -------------------------------------------------------------------------
    # 3. AssemblyModeSelector Tests
    # -------------------------------------------------------------------------
    def test_assembly_mode_selector_toggling(self):
        """Verify AssemblyModeSelector switches modes and emits signals."""
        selector = AssemblyModeSelector(current_mode="xml")
        self.assertEqual(selector.mode(), "xml")
        self.assertEqual(selector.get_mode(), "xml")
        self.assertTrue(selector.isChecked())

        received = []
        selector.mode_changed.connect(lambda m: received.append(m))

        selector.btn_drt.click()
        self.assertEqual(selector.mode(), "drt")
        self.assertFalse(selector.isChecked())
        self.assertIn("drt", received)

        selector.btn_xml.click()
        self.assertEqual(selector.mode(), "xml")
        self.assertTrue(selector.isChecked())
        self.assertEqual(received[-1], "xml")

    def test_assembly_mode_selector_free_21_1_disabled(self):
        """Verify DRT mode is disabled and forced to XML on DaVinci Free 21.1+."""
        selector = AssemblyModeSelector(current_mode="drt", is_drt_disabled=True)
        # Should be forced to xml
        self.assertEqual(selector.mode(), "xml")
        self.assertFalse(selector.btn_drt.isEnabled())
        self.assertTrue(selector.btn_xml.isEnabled())

        # Clicking disabled DRT should not change mode
        selector.btn_drt.click()
        self.assertEqual(selector.mode(), "xml")

    # -------------------------------------------------------------------------
    # 4. SettingsDialog Structure and Search Tests
    # -------------------------------------------------------------------------
    def _create_mock_engine(self, is_free_21_1=False):
        engine = MagicMock()
        prefs = dict(config.DEFAULT_SETTINGS)
        prefs["gui_lang"] = "en"
        prefs["settings_view_mode"] = "basic"
        prefs["timeline_assembly_method"] = "xml"
        prefs["force_xml_assembly"] = True
        prefs["ui_scale_pct"] = 100

        engine.load_preferences.return_value = prefs
        engine.save_preferences = MagicMock()
        engine.current_lang = "en"

        mock_doc = MagicMock()
        mock_doc.get_resolve_edition_info.return_value = {
            "edition": "Free" if is_free_21_1 else "Studio",
            "is_21_1_or_newer": is_free_21_1
        }
        mock_doc.get_telemetry_pref.return_value = True
        engine.os_doc = mock_doc

        mock_resolve = MagicMock()
        mock_resolve.is_free_21_1_or_newer.return_value = is_free_21_1
        engine.resolve_handler = mock_resolve
        return engine

    def test_settings_dialog_tabs_basic_vs_advanced(self):
        """Verify AI Engine tab is hidden in basic mode and visible in advanced mode."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)

        # Tab index 6 is AI Engine
        self.assertEqual(dialog.category_list.count(), 9)
        self.assertTrue(dialog.category_list.item(6).isHidden())

        # Switch to advanced mode
        dialog._set_view_mode('advanced')
        self.assertFalse(dialog.category_list.item(6).isHidden())

        # Switch back to basic
        dialog._set_view_mode('basic')
        self.assertTrue(dialog.category_list.item(6).isHidden())

    def test_settings_dialog_lazy_page_building(self):
        """Verify all 9 tabs build cleanly via lazy loading."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)

        for i in range(9):
            dialog._ensure_page_built(i)
            page = dialog.stack.widget(i)
            self.assertIsNotNone(page)

    def test_settings_dialog_davinci_tab_xml_dimming(self):
        """Verify XML dependent settings dim and block when DRT is selected, even with a parent in file mode."""
        engine = self._create_mock_engine(is_free_21_1=False)
        from PySide6.QtWidgets import QWidget
        parent_mock = QWidget()
        parent_mock.current_source_type = "file"
        dialog = SettingsDialog(engine, parent=parent_mock)

        # Load DaVinci tab (index 3)
        dialog._ensure_page_built(3)

        self.assertIsNotNone(dialog.w_assembly_selector)
        # Select DRT
        dialog.w_assembly_selector.set_mode("drt")
        self.assertTrue(dialog.tgl_xml_preserve_track_order._blocked)
        self.assertTrue(dialog.tgl_link_av_clips._blocked)
        self.assertTrue(dialog.tgl_link_all_cut_tracks._blocked)
        self.assertAlmostEqual(dialog._curr_linking_op, 0.35, places=2)
        self.assertAlmostEqual(dialog.tgl_link_av_clips._opacity, 0.35, places=2)

        # Select XML
        dialog.w_assembly_selector.set_mode("xml")
        self.assertFalse(dialog.tgl_xml_preserve_track_order._blocked)
        self.assertFalse(dialog.tgl_link_av_clips._blocked)
        self.assertFalse(dialog.tgl_link_all_cut_tracks._blocked)
        self.assertAlmostEqual(dialog._curr_linking_op, 1.0, places=2)
        self.assertAlmostEqual(dialog.tgl_link_av_clips._opacity, 1.0, places=2)

    def test_settings_dialog_davinci_options_visible_in_basic_mode(self):
        """Verify primary XML linking options remain visible in basic mode."""
        engine = self._create_mock_engine(is_free_21_1=False)
        dialog = SettingsDialog(engine)
        dialog._ensure_page_built(3)

        # link_av_clips and link_all_cut_tracks should be visible (not hidden) in basic mode
        self.assertFalse(dialog._row_link_av.isHidden())
        self.assertFalse(dialog._row_link_all.isHidden())

        # xml_preserve_track_order should be hidden in basic mode
        self.assertTrue(dialog._row_xml_track.isHidden())

    def test_settings_dialog_collect_preferences_preserves_assembly_method(self):
        """Verify _collect_preferences captures both force_xml_assembly and timeline_assembly_method."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)
        dialog._ensure_page_built(3)

        dialog.w_assembly_selector.set_mode("drt")
        prefs = dialog._get_current_state_dict()
        self.assertFalse(prefs["force_xml_assembly"])
        self.assertEqual(prefs["timeline_assembly_method"], "drt")

        dialog.w_assembly_selector.set_mode("xml")
        prefs = dialog._get_current_state_dict()
        self.assertTrue(prefs["force_xml_assembly"])
        self.assertEqual(prefs["timeline_assembly_method"], "xml")

    def test_settings_dialog_search_filtering(self):
        """Verify search bar filters tabs dynamically."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)

        # Search for XML
        dialog.search_edit.setText("XML")
        # DaVinci Resolve tab (index 3) should be visible and selected
        self.assertFalse(dialog.category_list.item(3).isHidden())
        self.assertEqual(dialog.category_list.currentRow(), 3)

        # Clear search
        dialog.search_edit.setText("")
        # Tab 0 should be visible
        self.assertFalse(dialog.category_list.item(0).isHidden())

    def test_settings_dialog_support_send_and_render(self):
        """Verify Support/Contact tab renders cleanly and sends relay-compatible payload."""
        import tempfile, time, urllib.request
        from PySide6.QtWidgets import QApplication

        engine = self._create_mock_engine()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as tf:
            tf.write("sample log entry\n")
            tmp_log = tf.name
        try:
            engine.os_doc.log_file = tmp_log
            engine.os_doc.install_dir = os.path.dirname(tmp_log)
            engine.os_doc.user_file = ""
            engine.os_doc.settings_file = ""
            engine.os_doc.legacy_pref_file = ""

            dialog = SettingsDialog(engine)
            dialog.category_list.setCurrentRow(7)
            dialog.show()
            QApplication.processEvents()

            art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
            os.makedirs(art_dir, exist_ok=True)
            out_png = os.path.join(art_dir, "settings_dialog_support.png")
            self.assertTrue(dialog.grab().save(out_png))

            captured = {}

            class _Resp:
                def __enter__(self):
                    return self
                def __exit__(self, *a):
                    return False
                def getcode(self):
                    return 200
                def read(self):
                    return b'{"ok": true}'

            def _fake_urlopen(req, timeout=30, context=None):
                captured["data"] = req.data
                captured["headers"] = dict(req.header_items())
                return _Resp()

            dialog.input_support_title.setText("Contact test title")
            dialog.input_support_body.setPlainText("Contact test body")
            dialog.input_support_email.setText("user@example.com")

            with patch.object(config, "SUPPORT_WEBHOOK_URL", "https://example.invalid/", create=True):
                with patch.object(urllib.request, "urlopen", side_effect=_fake_urlopen):
                    dialog.btn_send_report.click()
                    deadline = time.time() + 3.0
                    while "data" not in captured and time.time() < deadline:
                        QApplication.processEvents()
                        time.sleep(0.01)

            self.assertIn("data", captured)
            self.assertIn("**Wersja:**".encode("utf-8"), captured["data"])
            self.assertIn("**Tytuł:** Contact test title".encode("utf-8"), captured["data"])
            self.assertIn("**Treść:**\nContact test body".encode("utf-8"), captured["data"])
            self.assertIn(b"filename=\"logs.zip\"", captured["data"])
            ua = captured["headers"].get("User-agent") or captured["headers"].get("User-Agent", "")
            self.assertTrue(ua.startswith("BadWords/"), f"Unexpected User-Agent: {ua}")
            dialog.close()
        finally:
            try:
                os.remove(tmp_log)
            except OSError:
                pass

    # -------------------------------------------------------------------------
    # 5. TelemetryPopup & CrashReportConsentDialog Tests + Visual Renders
    # -------------------------------------------------------------------------
    def test_telemetry_popup_drop_shadow_and_defaults(self):
        """Verify new-user popup defaults auto_crash_report=True, dims entire cards even under global QSS, and animates Disable All."""
        prev_qss = app.styleSheet()
        # Simulate live MainWindow/QApplication global dark QSS that overrides QPalette
        app.setStyleSheet("QWidget { color: #e0e0e0; } QLabel { color: #e0e0e0; }")
        try:
            engine = self._create_mock_engine()
            popup = TelemetryPopup(engine)

            self.assertIsNone(popup.inner_frame.graphicsEffect())
            self.assertFalse(popup.testAttribute(Qt.WA_TranslucentBackground))
            self.assertIn("1px solid #2e2e2e", popup.styleSheet())

            # Default state for new users: auto_crash_report MUST be ON, no default badge, no nested QGraphicsOpacityEffect
            self.assertTrue(popup._tgl_crash_report.isChecked())
            self.assertTrue(popup._tgl_telemetry.isChecked())
            self.assertFalse(hasattr(popup, "_lbl_default_badge"))
            self.assertIsNone(popup._geo_container.graphicsEffect())

            art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
            os.makedirs(art_dir, exist_ok=True)
            popup.show()
            app.processEvents()
            self.assertTrue(popup.grab().save(os.path.join(art_dir, "telemetry_popup.png")))

            # Verify Polish layout & entire Telemetry card (including title & body QSS) dims smoothly when OFF
            popup._on_lang_selected("pl")
            popup._tgl_telemetry.setChecked(False, animated=False)
            popup._telem_anim.stop()
            popup._apply_telemetry_card_dim(0.35)
            app.processEvents()
            self.assertFalse(popup._chk_geo.isEnabled())
            self.assertAlmostEqual(popup._telem_dim_val, 0.35, places=2)
            self.assertIn("color: #676767", popup._lbl_telem_title.styleSheet().lower())
            self.assertIn("color: #545454", popup._lbl_msg.styleSheet().lower())
            self.assertAlmostEqual(popup._crash_dim_val, 1.0, places=2)
            self.assertTrue(popup._tgl_crash_report.isChecked())
            self.assertTrue(popup.grab().save(os.path.join(art_dir, "telemetry_popup_pl.png")))

            # Verify Crash Report card also dims smoothly under global QSS when toggled OFF
            popup._tgl_crash_report.setChecked(False, animated=False)
            popup._crash_anim.stop()
            popup._apply_crash_card_dim(0.35)
            app.processEvents()
            self.assertAlmostEqual(popup._crash_dim_val, 0.35, places=2)
            self.assertIn("color: #676767", popup._lbl_crash_title.styleSheet().lower())
            self.assertIn("color: #545454", popup._lbl_crash_msg.styleSheet().lower())
            self.assertTrue(popup.grab().save(os.path.join(art_dir, "telemetry_popup_both_dimmed.png")))

            # Re-enable Crash Report before saving to test independent persistence
            popup._tgl_crash_report.setChecked(True, animated=False)
            popup._crash_anim.stop()
            popup._apply_crash_card_dim(1.0)
            app.processEvents()

            # Saving while telemetry is OFF and crash report is ON persists independently
            popup._on_yes()
            engine.os_doc.set_telemetry_pref.assert_any_call("telemetry_opt_in", False)
            engine.os_doc.set_telemetry_pref.assert_any_call("telemetry_allow_geo", False)
            engine.os_doc.set_telemetry_pref.assert_any_call("auto_crash_report", True)
            engine.send_telemetry_ping.assert_not_called()

            # Verify Disable All starts switch & fade animations INSTANTLY before any disk fsync, then persists on finish
            engine2 = self._create_mock_engine()
            popup2 = TelemetryPopup(engine2)
            popup2.show()
            app.processEvents()
            popup2._on_no()
            self.assertTrue(popup2._closing_anim_active)
            self.assertFalse(popup2._tgl_telemetry.isChecked())
            self.assertFalse(popup2._tgl_crash_report.isChecked())
            # Disk writes must NOT have blocked the animation start
            engine2.os_doc.set_telemetry_pref.assert_not_called()
            popup2._finish_disable_all()
            engine2.os_doc.set_telemetry_pref.assert_any_call("telemetry_opt_in", False)
            engine2.os_doc.set_telemetry_pref.assert_any_call("telemetry_allow_geo", False)
            engine2.os_doc.set_telemetry_pref.assert_any_call("auto_crash_report", False)
        finally:
            app.setStyleSheet(prev_qss)

    def test_existing_user_crash_report_consent_dialog(self):
        """Verify dedicated CrashReportConsentDialog shows for existing users regardless of telemetry choice."""
        for prior_telem in (True, False):
            engine = self._create_mock_engine()
            engine.os_doc.get_telemetry_pref.side_effect = (
                lambda k, pt=prior_telem: pt if k == "telemetry_opt_in" else None
            )
            dlg = CrashReportConsentDialog(engine)
            self.assertIsNone(dlg.inner_frame.graphicsEffect())
            self.assertFalse(dlg.testAttribute(Qt.WA_TranslucentBackground))

            if prior_telem is False:
                art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
                os.makedirs(art_dir, exist_ok=True)
                dlg.show()
                app.processEvents()
                self.assertTrue(dlg.grab().save(os.path.join(art_dir, "crash_report_dialog_en.png")))
                dlg._on_lang_selected("pl")
                app.processEvents()
                self.assertTrue(dlg.grab().save(os.path.join(art_dir, "crash_report_dialog_pl.png")))
                dlg._on_yes()
                engine.os_doc.set_telemetry_pref.assert_called_with("auto_crash_report", True)
            else:
                dlg._on_no()
                engine.os_doc.set_telemetry_pref.assert_called_with("auto_crash_report", False)

    def test_settings_about_page_crash_toggle_and_render(self):
        """Verify About & Privacy page exposes auto_crash_report toggle and zero emojis."""
        engine = self._create_mock_engine()
        engine.os_doc.user_data = {
            "telemetry_opt_in": False,
            "telemetry_geo": True,
            "auto_crash_report": True,
        }
        dialog = SettingsDialog(engine)
        dialog.category_list.setCurrentRow(8)
        dialog.show()
        app.processEvents()

        self.assertTrue(hasattr(dialog, "chk_auto_crash_report"))
        self.assertTrue(dialog.chk_auto_crash_report.isChecked())
        dialog.chk_auto_crash_report.setChecked(False, animated=False)
        state = dialog._get_current_state_dict()
        self.assertFalse(state["auto_crash_report"])

        # Restore back for clean render
        dialog.chk_auto_crash_report.setChecked(True, animated=False)
        app.processEvents()
        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        self.assertTrue(dialog.grab().save(os.path.join(art_dir, "settings_dialog_about.png")))
        dialog.close()

    def test_check_telemetry_routing_new_vs_existing_users(self):
        """Verify MainWindow.check_telemetry shows correct popup for new vs existing users."""
        from gui.main_window import BadWordsGUI

        class _DummyWin:
            def __init__(self, telem_val, crash_val):
                self.engine = MagicMock()
                self.engine.os_doc.get_telemetry_pref.side_effect = (
                    lambda k: telem_val if k == "telemetry_opt_in" else crash_val
                )
            def check_v4_migration_notice(self):
                pass

        # 1. Brand new user -> TelemetryPopup only
        w_new = _DummyWin(None, None)
        with patch("gui.main_window.TelemetryPopup") as mock_tp, patch("gui.main_window.CrashReportConsentDialog") as mock_cr:
            BadWordsGUI.check_telemetry(w_new)
            mock_tp.assert_called_once()
            mock_cr.assert_not_called()

        # 2. Existing user who REJECTED telemetry -> CrashReportConsentDialog MUST show
        w_old_no = _DummyWin(False, None)
        with patch("gui.main_window.TelemetryPopup") as mock_tp, patch("gui.main_window.CrashReportConsentDialog") as mock_cr:
            BadWordsGUI.check_telemetry(w_old_no)
            mock_tp.assert_not_called()
            mock_cr.assert_called_once()
            w_old_no.engine.send_telemetry_ping.assert_not_called()

        # 3. Existing user who ACCEPTED telemetry -> ping + CrashReportConsentDialog
        w_old_yes = _DummyWin(True, None)
        with patch("gui.main_window.TelemetryPopup") as mock_tp, patch("gui.main_window.CrashReportConsentDialog") as mock_cr:
            BadWordsGUI.check_telemetry(w_old_yes)
            mock_tp.assert_not_called()
            mock_cr.assert_called_once()
            w_old_yes.engine.send_telemetry_ping.assert_called_once_with("app_started")

        # 4. Existing user who already answered crash report -> neither popup shows
        w_done = _DummyWin(False, True)
        with patch("gui.main_window.TelemetryPopup") as mock_tp, patch("gui.main_window.CrashReportConsentDialog") as mock_cr:
            BadWordsGUI.check_telemetry(w_done)
            mock_tp.assert_not_called()
            mock_cr.assert_not_called()


if __name__ == "__main__":
    unittest.main()
