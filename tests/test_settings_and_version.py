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
        """Verify 9 tabs (restored Custom Markers tab) and AI Engine Basic vs Advanced visibility."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)

        # 9 tabs: Custom Markers = 5, AI Engine = 6, Support = 7, About = 8
        self.assertEqual(dialog.category_list.count(), 9)
        self.assertEqual(dialog.TAB_MARKERS, 5)
        self.assertEqual(dialog.TAB_AI_ENGINE, 6)
        self.assertEqual(dialog.TAB_SUPPORT, 7)
        self.assertEqual(dialog.TAB_ABOUT, 8)
        self.assertFalse(dialog.category_list.item(dialog.TAB_MARKERS).isHidden())
        self.assertTrue(dialog.category_list.item(dialog.TAB_AI_ENGINE).isHidden())

        # Support tab hides bottom Apply/Reset footer
        dialog.category_list.setCurrentRow(dialog.TAB_SUPPORT)
        app.processEvents()
        self.assertTrue(dialog.w_footer.isHidden())

        # Switch to advanced mode -> AI Engine tab visible, General App Folder card visible
        dialog.category_list.setCurrentRow(dialog.TAB_GENERAL)
        dialog._set_view_mode('advanced')
        app.processEvents()
        self.assertFalse(dialog.category_list.item(dialog.TAB_AI_ENGINE).isHidden())
        self.assertFalse(dialog.w_footer.isHidden())
        self.assertTrue(any(not w.isHidden() for w in dialog._advanced_widgets))

        # Switch back to basic -> AI Engine hidden again
        dialog._set_view_mode('basic')
        app.processEvents()
        self.assertTrue(dialog.category_list.item(dialog.TAB_AI_ENGINE).isHidden())
        dialog.close()

    def test_settings_dialog_lazy_page_building(self):
        """Verify all 9 tabs build cleanly via lazy loading."""
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)

        for i in range(9):
            dialog._ensure_page_built(i)
            page = dialog.stack.widget(i)
            self.assertIsNotNone(page)
            dialog.category_list.setCurrentRow(i)
            app.processEvents()
        dialog.close()

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
        """Verify debounced ranked Search, green highlight, PL+EN fallback, Basic->Advanced banner, and centered jump."""
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QLabel, QPushButton
        from gui.dialogs.settings_widgets import SearchResultCard
        engine = self._create_mock_engine()
        engine.load_preferences.return_value = {"gui_lang": "pl", "settings_view_mode": "basic"}
        dialog = SettingsDialog(engine)
        dialog.resize(920, 440)
        dialog.show()
        app.processEvents()

        # 1. Typing debounces via 180ms timer before switching to search view; Return runs immediately
        dialog.search_edit.setText("XML")
        app.processEvents()
        self.assertTrue(dialog._search_debounce_timer.isActive())
        self.assertNotEqual(dialog.stack.currentIndex(), dialog.STACK_SEARCH_IDX)

        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        self.assertEqual(dialog.stack.currentIndex(), dialog.STACK_SEARCH_IDX)
        self.assertEqual(dialog.category_list.currentRow(), 0)
        for idx in range(dialog.category_list.count()):
            if idx != dialog.TAB_AI_ENGINE:
                self.assertFalse(dialog.category_list.item(idx).isHidden())

        cards = dialog._search_results_container.findChildren(SearchResultCard)
        self.assertGreater(len(cards), 0)
        card0_txt = "".join(w.text() for w in cards[0].findChildren(QLabel))
        self.assertIn("#1f7a44", card0_txt)
        self.assertIn("XML", card0_txt)

        # 2. Live QTimer debounce executes automatically after ~210ms pause; PL+EN fallback (no 3rd lang)
        dialog.search_edit.setText("scaling")
        QTest.qWait(230)
        app.processEvents()
        en_cards = dialog._search_results_container.findChildren(SearchResultCard)
        self.assertTrue(any("Skalowanie" in "".join(w.text() for w in c.findChildren(QLabel)) or "UI" in "".join(w.text() for w in c.findChildren(QLabel)) for c in en_cards))

        dialog.search_edit.setText("skrot")
        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        pl_cards = dialog._search_results_container.findChildren(SearchResultCard)
        self.assertGreater(len(pl_cards), 0)

        dialog.search_edit.setText("Abbrechen")
        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        de_cards = dialog._search_results_container.findChildren(SearchResultCard)
        self.assertEqual(len(de_cards), 0)

        # 3. Basic View searching an Advanced-only setting -> shows hidden Advanced banner & button
        dialog.search_edit.setText("whisper")
        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        adv_buttons = [b for b in dialog._search_results_container.findChildren(QPushButton) if b.objectName() == "btn_apply"]
        self.assertGreater(len(adv_buttons), 0)
        adv_buttons[0].click()
        app.processEvents()
        self.assertFalse(dialog._is_basic_mode)
        self.assertGreater(len(dialog._search_results_container.findChildren(SearchResultCard)), 0)

        # 4. Clicking middle AI Engine result centers target widget vertically inside viewport!
        dialog.search_edit.setText("beam")
        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        beam_cards = dialog._search_results_container.findChildren(SearchResultCard)
        self.assertGreater(len(beam_cards), 0)
        beam_entry = next(e for e in dialog._search_entries if "beam" in (e.get("keywords_en", "") + " " + e.get("title_en", "")).lower())
        target_w = beam_entry["widget"]
        beam_cards[0].clicked.emit()
        app.processEvents()
        self.assertEqual(dialog.search_edit.text(), "")
        self.assertEqual(dialog.category_list.currentRow(), dialog.TAB_AI_ENGINE)
        self.assertEqual(dialog.stack.currentIndex(), dialog.TAB_AI_ENGINE)

        scroll_area = dialog.stack.widget(dialog.TAB_AI_ENGINE)
        vbar = scroll_area.verticalScrollBar()
        self.assertGreater(vbar.maximum(), 0)
        vp_h = scroll_area.viewport().height()
        target_mid_vp = target_w.mapTo(scroll_area.viewport(), QPoint(0, target_w.height() // 2)).y()
        # Vertically centered in viewport (or clamped at min/max scroll edge)
        if 0 < vbar.value() < vbar.maximum():
            self.assertLess(abs(target_mid_vp - (vp_h // 2)), 12)

        # 5. Clear returns to normal tab cleanly (immediately without waiting for debounce)
        dialog.search_edit.setText("zzzz_unlikely_query_xyz")
        dialog.search_edit.returnPressed.emit()
        app.processEvents()
        self.assertEqual(len(dialog._search_results_container.findChildren(SearchResultCard)), 0)
        dialog.search_edit.setText("")
        app.processEvents()
        self.assertEqual(dialog.stack.currentIndex(), dialog.category_list.currentRow())
        dialog._restore_state_dict(dialog._initial_state)
        dialog.close()

    def test_settings_dialog_support_send_and_render(self):
        """Verify Support/Feedback form UX: category prefix, validation, lightbox, mandatory sanitized logs, and relay send."""
        import io, tempfile, time, urllib.request, zipfile
        from PySide6.QtGui import QImage
        from PySide6.QtWidgets import QApplication
        from gui.dialogs.settings_widgets import AttachmentThumbCard, ScreenshotPreviewDialog

        engine = self._create_mock_engine()
        fake_user = os.path.basename(os.path.expanduser("~")) or "linux"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False, encoding="utf-8") as tf:
            tf.write(f"sample log entry in /home/{fake_user}/Videos/secret_media.mp4\n")
            tmp_log = tf.name
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as pf:
            tmp_png = pf.name
            img = QImage(320, 180, QImage.Format_RGB32)
            img.fill(0xFF238636)
            img.save(tmp_png, "PNG")
        try:
            engine.os_doc.log_file = tmp_log
            engine.os_doc.install_dir = os.path.dirname(tmp_log)
            engine.os_doc.user_file = ""
            engine.os_doc.settings_file = ""
            engine.os_doc.legacy_pref_file = ""

            dialog = SettingsDialog(engine)
            dialog.category_list.setCurrentRow(dialog.TAB_SUPPORT)
            dialog.show()
            QApplication.processEvents()

            # Mandatory logs: optional checkbox is gone; footer is hidden
            self.assertFalse(hasattr(dialog, "chk_support_attach_logs"))
            self.assertTrue(dialog.w_footer.isHidden())

            # Validation blocks empty submit and highlights missing title/body in red
            dialog.btn_send_report.click()
            QApplication.processEvents()
            self.assertTrue(dialog.lbl_support_status.property("is_err"))
            self.assertIn("#ed4245", dialog.input_support_title.styleSheet())
            self.assertIn("#ed4245", dialog.input_support_body.styleSheet())

            # Attach screenshot via live DropZone signal -> thumbnail card + lightbox preview
            dialog._support_dropzone.filesDropped.emit([tmp_png])
            QApplication.processEvents()
            thumbs = dialog.w_attachments_list.findChildren(AttachmentThumbCard)
            self.assertEqual(len(thumbs), 1)
            preview = ScreenshotPreviewDialog(tmp_png, "Preview", parent=dialog)
            preview.close()

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

            # Select Bug category, fill valid title & body
            dialog.combo_support_category.setText(dialog._support_cat_items[0][1])
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
            self.assertIn("**Tytuł:** [Bug] Contact test title".encode("utf-8"), captured["data"])
            self.assertIn("**Treść:**\nContact test body".encode("utf-8"), captured["data"])
            self.assertIn(b'filename="logs.zip"', captured["data"])

            # Verify logs.zip actually contains sanitized log text & screenshot
            zip_marker = b'Content-Disposition: form-data; name="file"; filename="logs.zip"\r\nContent-Type: application/zip\r\n\r\n'
            z_start = captured["data"].index(zip_marker) + len(zip_marker)
            z_end = captured["data"].index(b"\r\n------BadWordsBoundary", z_start)
            with zipfile.ZipFile(io.BytesIO(captured["data"][z_start:z_end]), "r") as zf:
                names = zf.namelist()
                self.assertIn("system_info.txt", names)
                self.assertIn("screenshot_1.jpg", names)
                log_members = [n for n in names if n.endswith(".log")]
                self.assertEqual(len(log_members), 1)
                sanitized_log = zf.read(log_members[0]).decode("utf-8")
                self.assertNotIn(f"/home/{fake_user}", sanitized_log)

            ua = captured["headers"].get("User-agent") or captured["headers"].get("User-Agent", "")
            self.assertTrue(ua.startswith("BadWords/"), f"Unexpected User-Agent: {ua}")
            dialog.close()
        finally:
            for p in (tmp_log, tmp_png):
                try:
                    os.remove(p)
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
        """Verify About & Privacy page exposes toggles, separate Coffee CTA card, no MIT badge, and renders cleanly."""
        from PySide6.QtWidgets import QFrame, QLabel
        engine = self._create_mock_engine()
        engine.os_doc.user_data = {
            "telemetry_opt_in": False,
            "telemetry_geo": True,
            "auto_crash_report": True,
        }
        dialog = SettingsDialog(engine)
        dialog.category_list.setCurrentRow(dialog.TAB_ABOUT)
        dialog.show()
        app.processEvents()

        self.assertTrue(hasattr(dialog, "chk_auto_crash_report"))
        self.assertTrue(dialog.chk_auto_crash_report.isChecked())
        # Geo toggle MUST be dimmed & mouse-transparent when telemetry_opt_in is False
        self.assertLess(dialog.chk_telemetry_geo._opacity, 0.5)
        self.assertTrue(dialog.chk_telemetry_geo.testAttribute(Qt.WA_TransparentForMouseEvents))

        # Coffee CTA is its own separate sibling card (never nested inside a SettingsCard) and MIT badge is removed
        from gui.dialogs.settings_widgets import SettingsCard
        coffee_cta = dialog.findChild(QFrame, "AboutCoffeeCta")
        self.assertIsNotNone(coffee_cta)
        page_about_scroll = dialog.stack.widget(dialog.TAB_ABOUT)
        anc = coffee_cta.parentWidget()
        while anc is not None and anc is not page_about_scroll:
            self.assertNotIsInstance(anc, SettingsCard)
            anc = anc.parentWidget()
        about_labels = [l.text() for l in page_about_scroll.findChildren(QLabel)]
        self.assertFalse(any("Open Source" in t for t in about_labels))

        # Turn telemetry ON -> geo animates/updates back toward 1.0
        dialog.chk_telemetry_opt_in.setChecked(True, animated=False)
        app.processEvents()
        dialog.chk_auto_crash_report.setChecked(False, animated=False)
        state = dialog._get_current_state_dict()
        self.assertFalse(state["auto_crash_report"])

        # Restore back for clean render
        dialog.chk_telemetry_opt_in.setChecked(False, animated=False)
        dialog.chk_auto_crash_report.setChecked(True, animated=False)
        app.processEvents()
        art_dir = os.path.join(os.path.dirname(__file__), "artifacts")
        os.makedirs(art_dir, exist_ok=True)
        self.assertTrue(dialog.grab().save(os.path.join(art_dir, "settings_dialog_about.png")))
        dialog._restore_state_dict(dialog._initial_state)
        dialog.close()

    def test_settings_markers_davinci_shortcut_sync_and_no_false_unsaved(self):
        """Verify restored Custom Markers tab, usage note, Shortcuts jump, MarkerDialog shortcut assignment, and no false Unsaved Changes."""
        from PySide6.QtWidgets import QLabel, QPushButton
        from gui.dialogs.marker_dialog import MarkerDialog
        engine = self._create_mock_engine()
        engine.load_preferences.return_value = {
            "gui_lang": "en",
            "custom_markers": [
                {"name": "B-Roll", "color": "Orange"}
            ],
            "shortcuts": {
                "custom_marker_B-Roll": "B",
                "shortcut_undo": "Ctrl+Z",
            },
        }
        dialog = SettingsDialog(engine)
        dialog._ensure_page_built(dialog.TAB_DAVINCI)
        dialog._ensure_page_built(dialog.TAB_MARKERS)
        dialog._ensure_page_built(dialog.TAB_SHORTCUTS)
        dialog.show()
        app.processEvents()

        # markers_card lives inside dedicated Custom Markers tab (NOT inside DaVinci tab)
        page_dav = dialog.stack.widget(dialog.TAB_DAVINCI)
        page_markers = dialog.stack.widget(dialog.TAB_MARKERS)
        self.assertFalse(page_dav.isAncestorOf(dialog.markers_card))
        self.assertTrue(page_markers.isAncestorOf(dialog.markers_card))

        # Custom Markers page includes File-mode vs DaVinci usage note + button jumping straight to Shortcuts
        marker_labels = [l.text() for l in page_markers.findChildren(QLabel)]
        self.assertTrue(any("file mode" in t.lower() and "davinci resolve" in t.lower() for t in marker_labels))
        jump_btns = [b for b in page_markers.findChildren(QPushButton) if dialog.txt("btn_manage_marker_shortcuts") in b.text()]
        self.assertEqual(len(jump_btns), 1)
        jump_btns[0].click()
        app.processEvents()
        self.assertEqual(dialog.category_list.currentRow(), dialog.TAB_SHORTCUTS)
        self.assertEqual(dialog.stack.currentIndex(), dialog.TAB_SHORTCUTS)

        # MarkerDialog supports optional shortcut capture prefilled & returned cleanly
        m_dlg = MarkerDialog(
            dialog, "en", "btn_edit_marker",
            prefill_name="B-Roll", prefill_color="Orange", prefill_shortcut="B",
        )
        self.assertEqual(m_dlg._shortcut_btn.get_sequence(), "B")
        m_dlg._shortcut_btn.set_sequence("M")
        m_dlg._on_ok()
        self.assertEqual(m_dlg.result_shortcut, "M")
        m_dlg.close()

        # Persisting marker add/edit syncs _initial_state['custom_markers'] + ['shortcuts'] -> no false Unsaved Changes
        m_key = "custom_marker_B-Roll"
        dialog._sync_shortcut_value(m_key, "M", source="")
        dialog.current_custom_markers.append({"name": "Extra", "color": "Red"})
        dialog._save_markers_and_refresh_main()
        self.assertEqual(dialog.custom_marker_shortcut_inputs[m_key].get_sequence(), "M")
        self.assertFalse(dialog.has_unsaved_changes())

        # Conflicting shortcut triggers conflict flag on Shortcuts page (collides with built-in play_stop='Space')
        dialog.custom_marker_shortcut_inputs[m_key].set_sequence("Space")
        dialog.custom_marker_shortcut_inputs[m_key].sequence_changed.emit("Space")
        app.processEvents()
        self.assertTrue(dialog.custom_marker_shortcut_inputs[m_key]._conflict)
        dialog._restore_state_dict(dialog._initial_state)
        dialog.close()

    def test_settings_general_advanced_paths_and_deferred_apply(self):
        """Verify General Advanced App Folder/Open Log card & Apply deferral + btn_apply [saved] property."""
        engine = self._create_mock_engine()
        engine.os_doc.install_dir = "/opt/badwords_app"
        engine.os_doc.log_file = "/opt/badwords_app/badwords_debug.log"
        engine.load_preferences.return_value = {
            "gui_lang": "en",
            "settings_view_mode": "basic",
            "always_on_top": True,
            "ui_scale_mode": config.UI_SCALE_MODE,
            "ui_scale_pct": config.UI_SCALE_PERCENT,
        }
        dialog = SettingsDialog(engine)
        dialog.show()
        app.processEvents()

        # Advanced paths hidden in basic mode
        self.assertTrue(all(w.isHidden() for w in dialog._advanced_widgets))
        dialog._set_view_mode("advanced")
        app.processEvents()
        self.assertTrue(any(not w.isHidden() for w in dialog._advanced_widgets))

        # Toggling settings must NOT write directly to save_preferences before Apply
        engine.save_preferences.reset_mock()
        dialog._ensure_page_built(dialog.TAB_APPEARANCE)
        dialog._ensure_page_built(dialog.TAB_DAVINCI)
        dialog.tgl_show_panel_headers.setChecked(False, animated=False)
        dialog.tgl_force_xml_assembly.setChecked(True, animated=False)
        app.processEvents()
        engine.save_preferences.assert_not_called()

        # Apply saves and sets [saved=True] cleanly
        dialog._apply_settings()
        engine.save_preferences.assert_called_once()
        self.assertTrue(dialog.btn_apply.property("saved"))

        # Basic mode _restore_state_dict must still restore chk_ontop
        dialog._set_view_mode("basic")
        dialog.chk_ontop.setChecked(False, animated=False)
        dialog._restore_state_dict({"always_on_top": True, "settings_view_mode": "advanced"})
        self.assertTrue(dialog.chk_ontop.isChecked())
        dialog._restore_state_dict(dialog._initial_state)
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

    def test_settings_uniform_control_widths_and_scale_slider(self):
        """Verify equal control column widths in Editor and compact responsive UI scale slider label without gap."""
        engine = self._create_mock_engine()
        engine.load_preferences.return_value = {
            "gui_lang": "pl",
            "ui_scale_mode": "manual",
            "ui_scale_pct": 130,
        }
        dialog = SettingsDialog(engine)
        dialog.show()
        dialog._ensure_page_built(dialog.TAB_APPEARANCE)
        dialog._ensure_page_built(dialog.TAB_EDITOR)
        app.processEvents()

        # Editor dropdowns share identical width (Display Mode == LMB == RMB)
        self.assertEqual(dialog.combo_view.width(), dialog.combo_mouse_lmb.width())
        self.assertEqual(dialog.combo_mouse_lmb.width(), dialog.combo_mouse_rmb.width())

        # Appearance UI scaling slider keeps fixed percentage column and puts green System text on the left
        dialog.category_list.setCurrentRow(dialog.TAB_APPEARANCE)
        dialog.slider_ui_scale.setValue(130)
        app.processEvents()
        scale_row = dialog.slider_ui_scale.parentWidget()
        self.assertEqual(dialog.lbl_ui_scale_val.text(), "130%")
        self.assertNotIn("System", dialog._lbl_ui_scale_title.text())
        self.assertEqual(scale_row.width(), config.S(220))
        self.assertLess(dialog.lbl_ui_scale_val.width(), config.S(68))
        manual_slider_w = dialog.slider_ui_scale.width()
        slider_right = dialog.slider_ui_scale.x() + dialog.slider_ui_scale.width()
        gap = dialog.lbl_ui_scale_val.x() - slider_right
        self.assertGreaterEqual(gap, 0)
        self.assertLessEqual(gap, config.S(14))

        # Switching to system auto shows emerald System label on the LEFT without shifting slider width!
        from gui.widgets.buttons import ReloadButton
        rev_btn = scale_row.parentWidget().findChild(ReloadButton)
        self.assertIsNotNone(rev_btn)
        rev_btn.click()
        app.processEvents()
        self.assertNotIn("(", dialog.lbl_ui_scale_val.text())
        self.assertIn("System", dialog._lbl_ui_scale_title.text())
        self.assertIn("#169c56", dialog._lbl_ui_scale_title.text())
        self.assertEqual(dialog.slider_ui_scale.width(), manual_slider_w)
        row_scale = scale_row.parentWidget().parentWidget()
        from PySide6.QtCore import QPoint
        title_right = dialog._lbl_ui_scale_title.mapTo(row_scale, QPoint(dialog._lbl_ui_scale_title.width(), 0)).x()
        scale_left = scale_row.mapTo(row_scale, QPoint(0, 0)).x()
        self.assertLess(title_right, scale_left)
        dialog._refresh_scale_label(200, True)
        app.processEvents()
        self.assertEqual(dialog.lbl_ui_scale_val.text(), "200%")
        self.assertGreaterEqual(
            dialog.lbl_ui_scale_val.width(),
            dialog.lbl_ui_scale_val.fontMetrics().horizontalAdvance("200%"),
        )
        dialog._restore_state_dict(dialog._initial_state)
        dialog.close()

    def test_unsaved_changes_dialog_modern_styling_and_compact_height(self):
        """Verify UnsavedChangesDialog matches new Settings card/footer aesthetics and avoids tall empty box."""
        from gui.dialogs.unsaved_changes_dialog import UnsavedChangesDialog
        from PySide6.QtWidgets import QFrame, QPushButton
        engine = self._create_mock_engine()
        dialog = SettingsDialog(engine)
        dialog.show()
        app.processEvents()

        # 1-item dialog should size compactly (not bloated 480px empty rectangle)
        u1 = UnsavedChangesDialog(
            dialog,
            {"ui_scale_pct": (100, 125)},
            {"ui_scale_pct": "Wygląd: Skalowanie interfejsu"},
        )
        u1.show()
        app.processEvents()
        self.assertIsNotNone(u1.findChild(QFrame, "UnsavedCard"))
        self.assertIsNotNone(u1.findChild(QFrame, "MainInnerFrame"))
        self.assertLess(u1.height(), config.S(330))
        apply_btns = [b for b in u1.findChildren(QPushButton) if b.objectName() == "btn_apply"]
        self.assertGreaterEqual(len(apply_btns), 2)
        self.assertTrue(all(b.height() >= config.S(26) for b in apply_btns))
        u1.close()

        # Decision recording remains intact
        u2 = UnsavedChangesDialog(
            dialog,
            {"ui_scale_pct": (100, 125), "always_on_top": (False, True)},
            {"ui_scale_pct": "Appearance: UI Scaling", "always_on_top": "Appearance: Always on Top"},
        )
        u2._make_decision("ui_scale_pct", "save")
        u2._discard_all()
        self.assertEqual(u2.decisions, {"ui_scale_pct": "save", "always_on_top": "discard"})
        u2.close()
        dialog.close()


if __name__ == "__main__":
    unittest.main()
