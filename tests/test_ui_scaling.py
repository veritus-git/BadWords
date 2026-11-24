#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for unified cross-platform UI scaling:
- Auto OS scale detection (Windows, Linux Wayland, Linux X11 Xft.dpi, macOS Retina) without double-multiplication
- Manual 75%-200% scaling & FS_PX typography parity
- Mixed-DPI multi-monitor recalculation
- Legacy settings.json one-time migration to ui_scale_mode="auto"
- Aspect-ratio responsive sidebar sizing (16:9 vs 16:10/3:2 narrow screens)
- SettingsDialog UI Scaling row range, info icon placement on right, and live rebuild state preservation
- Resolve-safe BadWordsGUI.rebuild_ui_for_scale() preserving Resolve connection, words_data, and waveform peaks
"""

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BADWORDS_DEV"] = "1"
app = QApplication.instance() or QApplication([])

import config
from config import app_constants
from gui.dialogs.settings_dialog import SettingsDialog
from gui.main_window import BadWordsGUI, compute_sidebar_panel_width


class _FakeScreen:
    def __init__(self, dpr=1.0, ldpi=96.0):
        self._dpr = dpr
        self._ldpi = ldpi

    def devicePixelRatio(self):
        return self._dpr

    def logicalDotsPerInch(self):
        return self._ldpi


class TestUIScalingUnified(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gui.dialogs.update_dialog import UpdateCheckThread
        UpdateCheckThread._checked = True
        UpdateCheckThread._cached_result = ("4.0.1", "https://github.com", "https://gitlab.com", "")

    def setUp(self):
        self._orig_mode = config.UI_SCALE_MODE
        self._orig_pct = config.UI_SCALE_PERCENT
        self._orig_is_mac = app_constants.IS_MAC

    def tearDown(self):
        app_constants.IS_MAC = self._orig_is_mac
        config.apply_ui_scaling(mode=self._orig_mode, pct=self._orig_pct)

    def test_auto_mode_never_double_multiplies_os_dpi(self):
        """Windows 11 / Linux Wayland fractional DPR scales cleanly with SCALE_FACTOR == 1.0 in Auto mode."""
        app_constants.IS_MAC = False
        for os_dpr, expected_pct in ((1.0, 100), (1.25, 125), (1.5, 150), (2.0, 200)):
            scr = _FakeScreen(dpr=os_dpr, ldpi=96.0)
            factor = config.apply_ui_scaling(mode="auto", screen=scr)
            self.assertEqual(config.OS_SCALE_PERCENT, expected_pct)
            self.assertEqual(config.UI_SCALE_PERCENT, expected_pct)
            self.assertAlmostEqual(factor, 1.0, places=3)
            self.assertEqual(config.FS_PX(10), 13)

    def test_linux_x11_xft_dpi_scales_uniformly_without_double_font_scale(self):
        """X11 with dpr=1.0 and Xft.dpi=120 (125%) sets SCALE_FACTOR=1.25 and scales fonts via FS_PX without double Xft boost."""
        app_constants.IS_MAC = False
        scr = _FakeScreen(dpr=1.0, ldpi=120.0)
        factor = config.apply_ui_scaling(mode="auto", screen=scr)
        self.assertEqual(config.OS_SCALE_PERCENT, 125)
        self.assertEqual(config.UI_SCALE_PERCENT, 125)
        self.assertAlmostEqual(factor, 1.25, places=3)
        self.assertEqual(config.S(20), 25)
        self.assertEqual(config.FS_PX(10), 17)

    def test_macos_retina_baseline_is_100_percent_with_exact_px_fonts(self):
        """macOS Retina keeps 100% OS baseline (no hidden 0.85 shrink) and matching 13px baseline font at 10pt."""
        app_constants.IS_MAC = True
        scr = _FakeScreen(dpr=2.0, ldpi=72.0)
        factor = config.apply_ui_scaling(mode="auto", screen=scr)
        self.assertEqual(config.OS_SCALE_PERCENT, 100)
        self.assertEqual(config.UI_SCALE_PERCENT, 100)
        self.assertAlmostEqual(factor, 1.0, places=3)
        self.assertEqual(config.S(20), 20)
        self.assertEqual(config.FS_PX(10), 13)

        # Manual 150% on macOS Retina scales uniformly to 1.5x
        factor_150 = config.apply_ui_scaling(mode="manual", pct=150, screen=scr)
        self.assertAlmostEqual(factor_150, 1.5, places=3)
        self.assertEqual(config.S(20), 30)
        self.assertEqual(config.FS_PX(10), 20)

    def test_manual_target_across_mixed_dpi_monitors(self):
        """Manual 125% target keeps identical physical scale when dragging between 100% and 150% monitors."""
        app_constants.IS_MAC = False
        scr_100 = _FakeScreen(dpr=1.0, ldpi=96.0)
        scr_150 = _FakeScreen(dpr=1.5, ldpi=96.0)

        f1 = config.apply_ui_scaling(mode="manual", pct=125, screen=scr_100)
        self.assertAlmostEqual(f1 * 1.0, 1.25, places=3)

        f2 = config.apply_ui_scaling(mode="manual", pct=125, screen=scr_150)
        self.assertAlmostEqual(f2 * 1.5, 1.25, places=3)
        self.assertAlmostEqual(f2, 125.0 / 150.0, places=3)

    def test_aspect_ratio_narrows_sidebar_on_16_10_macbook(self):
        """Narrower 16:10 and 3:2 screens narrow side panels instead of bloating them while protecting canvas width."""
        config.set_ui_scale(100)
        w_16_9 = compute_sidebar_panel_width(1440, 810, 16.0 / 9.0, content_min_w=240)
        w_16_10 = compute_sidebar_panel_width(1440, 900, 16.0 / 10.0, content_min_w=240)
        w_3_2 = compute_sidebar_panel_width(1440, 960, 1.5, content_min_w=240)
        self.assertGreaterEqual(w_16_9, w_16_10)
        self.assertGreaterEqual(w_16_10, w_3_2)
        # Even at 200% zoom on a 1440px laptop, one panel stays <= 29% width (center canvas >= 42%)
        config.set_ui_scale(200)
        w_200 = compute_sidebar_panel_width(1440, 900, 1.6, content_min_w=500)
        self.assertLessEqual(w_200, int(1440 * 0.29))

    def test_legacy_settings_migration_to_auto_mode(self):
        """Legacy settings.json without ui_scale_mode migrates once to 'auto'; explicit 'manual' is kept."""
        import osdoc

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = os.path.join(tmp, "settings.json")
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump({"settings_version": config.VERSION, "ui_scale_pct": 125}, f)

            fake_doc = SimpleNamespace(settings_file=settings_path, is_legacy_updater_migration=lambda: False)
            loaded = osdoc.OSDoctor.load_settings(fake_doc)
            self.assertEqual(loaded["ui_scale_mode"], "auto")

            # Explicit manual choice stays manual on next load
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump({"settings_version": config.VERSION, "ui_scale_mode": "manual", "ui_scale_pct": 140}, f)
            loaded2 = osdoc.OSDoctor.load_settings(fake_doc)
            self.assertEqual(loaded2["ui_scale_mode"], "manual")
            self.assertEqual(loaded2["ui_scale_pct"], 140)

    def _make_mock_engine(self, prefs_override=None):
        engine = MagicMock()
        prefs = dict(config.DEFAULT_SETTINGS)
        prefs["gui_lang"] = "pl"
        prefs["settings_view_mode"] = "basic"
        prefs["auto_check_updates"] = False
        if prefs_override:
            prefs.update(prefs_override)

        state = dict(prefs)
        engine.load_preferences.side_effect = lambda: dict(state)
        engine.calculate_timeline_structure_with_cuts.return_value = ([], [])

        def _save(new_p):
            if isinstance(new_p, dict):
                state.update(new_p)
            return True

        engine.save_preferences.side_effect = _save
        engine.current_lang = prefs["gui_lang"]

        mock_doc = MagicMock()
        mock_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
        mock_doc.get_telemetry_pref.side_effect = lambda k: bool(prefs.get(k, False))
        mock_doc.get_autosave_dir.return_value = tempfile.gettempdir()
        mock_doc.is_win = False
        mock_doc.is_mac = False
        mock_doc.install_dir = tempfile.gettempdir()
        engine.os_doc = mock_doc

        mock_resolve = MagicMock()
        mock_resolve.is_connected.return_value = True
        mock_resolve.is_bridge_connected.return_value = False
        mock_resolve.is_free_21_1_or_newer.return_value = False
        mock_resolve.get_project_name.return_value = "Test Project"
        mock_resolve.get_current_project_name.return_value = "Test Project"
        mock_resolve.get_all_timelines.return_value = ["Main Timeline"]
        mock_resolve.get_current_timeline_name.return_value = "Main Timeline"
        mock_resolve.get_audio_tracks.return_value = ["A1"]
        engine.resolve_handler = mock_resolve
        return engine, state

    def test_settings_slider_range_info_icon_on_right_and_live_rebuild(self):
        """Settings slider has 75-200 range, (i) icon next to right slider control, and live rebuild keeps active tab."""
        from gui.dialogs.update_dialog import UpdateCheckThread
        UpdateCheckThread._checked = True
        UpdateCheckThread._cached_result = ("4.0.1", "https://github.com", "https://gitlab.com", "")

        engine, _ = self._make_mock_engine({"ui_scale_mode": "auto", "ui_scale_pct": 100})
        dlg = SettingsDialog(engine)
        try:
            dlg.show()
            dlg._ensure_page_built(1)
            dlg.category_list.setCurrentRow(1)
            dlg.resize(config.SETTINGS_WINDOW_W, config.SETTINGS_WINDOW_H)
            app.processEvents()

            self.assertEqual(dlg.slider_ui_scale.minimum(), 75)
            self.assertEqual(dlg.slider_ui_scale.maximum(), 200)
            self.assertEqual(dlg.lbl_ui_scale_val.text(), f"{config.OS_SCALE_PERCENT}%")
            self.assertIn("System", dlg._lbl_ui_scale_title.text())
            self.assertIn("#169c56", dlg._lbl_ui_scale_title.text())
            auto_slider_w = dlg.slider_ui_scale.width()

            # Locate info icon on UI Scaling row and ensure it is right-aligned beside slider (not far left with label)
            scale_row_container = dlg.slider_ui_scale.parentWidget().parentWidget()
            icons = [
                w for w in scale_row_container.findChildren(type(dlg._get_info_icon("tt_ui_scaling")))
                if getattr(w, "custom_tooltip_text", None) or w.text() == "ⓘ"
            ]
            self.assertTrue(icons, "Expected info icon inside right-hand control container")
            self.assertLess(icons[0].x(), dlg.slider_ui_scale.parentWidget().x() + dlg.slider_ui_scale.parentWidget().width())

            # Explicit uniform category row height across Windows/Linux/macOS (35px at 100%)
            self.assertEqual(dlg.category_list.spacing(), 0)
            row_hint = dlg.category_list.itemDelegate().sizeHint(
                dlg.category_list.viewOptions() if hasattr(dlg.category_list, "viewOptions") else __import__("PySide6.QtWidgets", fromlist=["QStyleOptionViewItem"]).QStyleOptionViewItem(),
                dlg.category_list.model().index(0, 0),
            )
            self.assertEqual(row_hint.height(), config.S(35))

            # Moving slider hides left System badge without shifting or stretching slider width; only Apply rebuilds UI
            dlg.slider_ui_scale.setValue(150)
            app.processEvents()
            self.assertEqual(dlg.lbl_ui_scale_val.text(), "150%")
            self.assertNotIn("System", dlg._lbl_ui_scale_title.text())
            self.assertEqual(dlg.slider_ui_scale.width(), auto_slider_w)
            self.assertNotEqual(config.UI_SCALE_PERCENT, 150)
            self.assertIn("ui_scale_pct", dlg._compute_unsaved_diff()[0])

            # Clicking Apply saves and rebuilds to 150% live while keeping active tab
            dlg._apply_settings()
            app.processEvents()
            self.assertEqual(dlg.category_list.currentRow(), 1)
            self.assertEqual(config.UI_SCALE_PERCENT, 150)
            self.assertEqual(config.UI_SCALE_MODE, "manual")
            self.assertEqual(dlg._compute_unsaved_diff()[0], {})
        finally:
            dlg.close()
            dlg.deleteLater()

    def test_startup_finish_uses_load_preferences_so_saved_scale_persists(self):
        """Regression: AppController._finish_startup must read engine.load_preferences() (never missing .prefs) cleanly."""
        import main as app_main

        config.apply_ui_scaling(mode="auto")
        fake_engine = MagicMock(spec=["load_preferences", "os_doc"])
        fake_engine.load_preferences.return_value = {"ui_scale_mode": "manual", "ui_scale_pct": 150}
        fake_resolve = MagicMock()

        captured = {}

        class _DummyWin:
            def __init__(self, ae, rh):
                captured["ui_scale_pct"] = config.UI_SCALE_PERCENT
                captured["ui_scale_mode"] = config.UI_SCALE_MODE
                captured["factor"] = config.SCALE_FACTOR
                self.closeEvent_callback = None

            def showMaximized(self): pass
            def raise_(self): pass
            def activateWindow(self): pass
            def windowHandle(self): return None

        import gui
        orig_bw_gui = gui.BadWordsGUI
        gui.BadWordsGUI = _DummyWin
        try:
            ctrl = app_main.AppController(splash=None)
            ctrl._finish_startup(fake_resolve, fake_engine)
        finally:
            gui.BadWordsGUI = orig_bw_gui

        self.assertEqual(captured.get("ui_scale_mode"), "manual")
        self.assertEqual(captured.get("ui_scale_pct"), 150)

    def test_app_icon_requires_restart_and_never_calls_hot_swap_setwindowicon(self):
        """Regression: changing app_icon saves + flags restart_needed without calling apply_app_icon_everywhere live."""
        engine, _ = self._make_mock_engine({"app_icon": "default", "ui_scale_mode": "manual", "ui_scale_pct": 100})
        dlg = SettingsDialog(engine)
        try:
            dlg._ensure_page_built(0)
            for btn in dlg.icon_group.buttons():
                if btn.property("icon_name") == "white":
                    btn.setChecked(True)
                    break
            with patch("gui.dialogs.settings_dialog.CustomMsgBox") as mock_msg, \
                 patch("gui.utils.apply_app_icon_everywhere") as mock_hot_swap:
                mock_msg.return_value.exec.return_value = 0
                dlg._apply_settings()
                mock_hot_swap.assert_not_called()
                mock_msg.assert_called_once()
        finally:
            dlg.close()
            dlg.deleteLater()

    def test_mainwindow_live_rebuild_preserves_resolve_connection_and_editor_state(self):
        """BadWordsGUI.rebuild_ui_for_scale preserves Resolve object, words_data, waveform peaks, and active panels."""
        engine, _ = self._make_mock_engine({"ui_scale_mode": "manual", "ui_scale_pct": 100})
        orig_rh = engine.resolve_handler
        config.apply_ui_scaling(mode="manual", pct=100)

        orig_pop = BadWordsGUI._populate_timeline_track_combos
        orig_tel = BadWordsGUI.check_telemetry
        orig_upd = BadWordsGUI._start_update_check
        BadWordsGUI._populate_timeline_track_combos = lambda self: None
        BadWordsGUI.check_telemetry = lambda self: None
        BadWordsGUI._start_update_check = lambda self: None
        try:
            orig_preload = BadWordsGUI._preload_settings
            BadWordsGUI._preload_settings = lambda self: None
            try:
                win = BadWordsGUI(engine, orig_rh)
            finally:
                BadWordsGUI._preload_settings = orig_preload
        finally:
            BadWordsGUI._populate_timeline_track_combos = orig_pop
            BadWordsGUI.check_telemetry = orig_tel
            BadWordsGUI._start_update_check = orig_upd
        try:
            win.show()
            win.resize(1280, 800)
            win.combo_tl_0.options_list = ["Main Timeline", "Cut v2"]
            win.combo_tl_0.setText("Main Timeline")
            sample_words = [
                {"id": 0, "meta_lang": "pl", "text": "Cześć", "start": 0.0, "end": 0.4, "status": "normal", "is_segment_start": True},
                {"id": 1, "text": "tu", "start": 0.4, "end": 0.6, "status": "bad"},
                {"id": 2, "text": "test", "start": 0.6, "end": 1.0, "status": "repeat"},
            ]
            win.text_canvas.load_data(sample_words)
            import numpy as np
            from engine.waveform import WaveformPeaks
            n_pts = 400
            t_arr = np.linspace(0.0, 6.28, n_pts, dtype=np.float32)
            sentinel_peaks = WaveformPeaks(
                peaks_min=-np.abs(np.sin(t_arr)).astype(np.float32) * 0.6,
                peaks_max=np.abs(np.sin(t_arr)).astype(np.float32) * 0.6,
                peaks_rms=np.abs(np.sin(t_arr)).astype(np.float32) * 0.35,
                duration=2.0,
            )
            win.audio_preview.waveform_timeline._peaks = sentinel_peaks
            win.audio_preview.waveform_timeline._duration = 2.0
            win.go_to_page(2)
            win._toggle_activity("silence")
            app.processEvents()

            rh_calls_before = orig_rh.get_all_timelines.call_count

            # Live switch via SettingsDialog Apply 3 consecutive times without restarting
            # (tests deleted _panel_headers / deleted activities C++ object safety!)
            dlg = SettingsDialog(engine, parent=win)
            try:
                dlg.show()
                dlg._ensure_page_built(1)
                dlg.category_list.setCurrentRow(1)
                app.processEvents()

                for target_pct in (150, 125, 200, 100):
                    dlg.slider_ui_scale.setValue(target_pct)
                    app.processEvents()
                    dlg._apply_settings()
                    app.processEvents()
                    self.assertEqual(config.UI_SCALE_PERCENT, target_pct)
                    self.assertEqual(win._sidebar_left.width(), config.S(50))
                    win.set_panel_headers_visible(True)
                    win.set_panel_headers_visible(False)
                    win.set_panel_headers_visible(True)
            finally:
                dlg.close()
                dlg.deleteLater()

            # Switch back to 150% cleanly to verify preserved Resolve & waveform state
            config.apply_ui_scaling(mode="manual", pct=150)
            win.rebuild_ui_for_scale()
            app.processEvents()

            self.assertIs(win.resolve_handler, orig_rh)
            self.assertEqual(orig_rh.get_all_timelines.call_count, rh_calls_before)
            self.assertEqual(win._stack.currentIndex(), 2)
            self.assertEqual(len(win.text_canvas.words_data), 3)
            self.assertIs(win.audio_preview.waveform_timeline._peaks, sentinel_peaks)
            self.assertTrue(win._panel_left.isVisible())
            self.assertTrue(win.btn_nav_silence.is_active)
            self.assertEqual(win.combo_tl_0.currentText(), "Main Timeline")
            self.assertEqual(win._sidebar_left.width(), config.S(50))
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
