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
        """Verify UI scaling clamped between 75% and 150%."""
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

        # Underflow clamped to 75
        config.set_ui_scale(40)
        self.assertEqual(config.UI_SCALE_PERCENT, 75)
        self.assertAlmostEqual(config.SCALE_FACTOR, 0.75, places=2)

        # Overflow clamped to 150
        config.set_ui_scale(220)
        self.assertEqual(config.UI_SCALE_PERCENT, 150)
        self.assertAlmostEqual(config.SCALE_FACTOR, 1.5, places=2)

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

    # -------------------------------------------------------------------------
    # 5. TelemetryPopup Drop Shadow Test
    # -------------------------------------------------------------------------
    def test_telemetry_popup_drop_shadow(self):
        """Verify TelemetryPopup uses drop shadow effect on inner frame without outer border."""
        engine = self._create_mock_engine()
        popup = TelemetryPopup(engine)

        # Verify inner frame has QGraphicsDropShadowEffect
        shadow = popup.inner_frame.graphicsEffect()
        self.assertIsInstance(shadow, QGraphicsDropShadowEffect)
        self.assertGreaterEqual(shadow.blurRadius(), 20)


if __name__ == "__main__":
    unittest.main()
