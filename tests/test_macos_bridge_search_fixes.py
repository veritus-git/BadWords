#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""Regression tests for macOS UX, Resolve Bridge stability, search debouncing, chunked marks, and updater/crash fixes."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("_BW_AUTO_HEAL_ATTEMPTED", "1")
os.environ.setdefault("BADWORDS_DEV", "1")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
_SETUP_DIR = os.path.join(_REPO_ROOT, "setupfiles")
if _SETUP_DIR not in sys.path:
    sys.path.insert(0, _SETUP_DIR)

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QWidget, QDialog

_APP = QApplication.instance() or QApplication([])

import config
from gui import UpdateNotifyDialog
from gui.dialogs.update_dialog import UpdateNotifyDialog as _DirectUpdateDialog
from gui.dialogs.crash_report_dialog import CrashReportConsentDialog
from gui.dialogs.telemetry_popup import TelemetryPopup
from gui.dialogs.export_dialog import ExportDialog
from gui.dialogs.settings_widgets import score_search_entry, ScreenshotPreviewDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.components.search_overlay import SearchOverlayWidget
from gui.components.transcription_canvas import TranscriptionCanvas, merge_manual_marks_into_words
from gui.widgets.buttons import SearchableDropdown
from startup import crash_report


def _make_mock_engine():
    eng = MagicMock()
    eng.load_preferences.return_value = dict(config.DEFAULT_SETTINGS, gui_lang="en")
    eng.save_preferences.return_value = True
    eng.os_doc = MagicMock()
    eng.os_doc.is_win = False
    eng.os_doc.is_mac = False
    eng.os_doc.is_linux = True
    eng.os_doc.get_telemetry_pref.return_value = None
    eng.os_doc.set_telemetry_pref.return_value = True
    return eng


class TestMacosBridgeSearchFixes(unittest.TestCase):
    def test_gui_lazy_update_dialog_and_qfont_import(self):
        self.assertIs(UpdateNotifyDialog, _DirectUpdateDialog)
        import gui.main_window as mw_mod
        self.assertIs(mw_mod.QFont, QFont)

    def test_updater_detect_installed_version_ignores_dynamic_call(self):
        import updater
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, "config")
            os.makedirs(cfg_dir, exist_ok=True)
            with open(os.path.join(cfg_dir, "app_constants.py"), "w", encoding="utf-8") as f:
                f.write('_DEFAULT_VERSION = "4.1.1"\nVERSION = _detect_version()\n')
            self.assertEqual(updater.detect_installed_version(tmp), "4.1.1")

            with open(os.path.join(tmp, ".version"), "w", encoding="utf-8") as f:
                f.write("4.1.2\n")
            self.assertEqual(updater.detect_installed_version(tmp), "4.1.2")

    def test_crash_report_version_scoped_dedup_and_filters(self):
        limiter = crash_report._CrashRateLimiter()
        with tempfile.TemporaryDirectory() as tmp:
            ok1, r1 = limiter.try_acquire("abc12345", app_data_dir=tmp, app_version="4.1.1")
            self.assertTrue(ok1, r1)
            ok2, r2 = limiter.try_acquire("abc12345", app_data_dir=tmp, app_version="4.1.1")
            self.assertFalse(ok2)
            self.assertEqual(r2, "session_duplicate")
            ok3, r3 = limiter.try_acquire("abc12345", app_data_dir=tmp, app_version="4.1.2")
            self.assertTrue(ok3, r3)

        self.assertFalse(crash_report.is_technical_update_error("Could not download update script from GitHub"))
        self.assertFalse(crash_report.is_technical_update_error("Timeout (>10 min)"))
        self.assertTrue(crash_report.is_technical_update_error("Exit code 1"))
        self.assertTrue(crash_report.is_technical_update_error("ImportError: cannot import name UpdateNotifyDialog"))

        self.assertFalse(crash_report.is_technical_bridge_error("DaVinci Resolve is not running"))
        self.assertTrue(crash_report.is_technical_bridge_error("Handler error: attempt to index nil value"))
        self.assertTrue(crash_report.is_technical_bridge_error("Failed to parse bridge response"))

    def test_search_overlay_and_dropdown_debouncing_and_cache(self):
        # 1. Settings score_search_entry folded cache
        entry = {
            "title_loc": "Ścieżki dźwiękowe",
            "category_loc": "Ogólne",
            "desc_loc": "Opis testowy",
            "options_loc": ["Włączone"],
            "title_en": "Audio Tracks",
            "category_en": "General",
            "desc_en": "Test desc",
            "options_en": ["Enabled"],
            "keywords_en": "audio tracks",
        }
        sc, via_en, _ = score_search_entry("sciezki", entry, "pl")
        self.assertGreater(sc, 0)
        self.assertFalse(via_en)
        self.assertIn("_folded_cache", entry)
        self.assertEqual(entry["_folded_cache"]["_lang"], "pl")

        # 2. SearchOverlayWidget debounce, clear, Enter flush, word cache
        host = QWidget()
        host.resize(800, 600)
        mw = MagicMock()
        mw.txt = lambda k, default="": default or k
        canvas = MagicMock()
        canvas.words_data = [
            {"text": "Alpha,", "start": 0.0, "end": 0.5},
            {"text": "Beta!", "start": 0.5, "end": 1.0},
            {"text": "Gamma", "start": 1.0, "end": 1.5},
        ]
        mw.text_canvas = canvas
        overlay = SearchOverlayWidget(host, mw)
        overlay.open_search()
        overlay.search_input.setText("beta")
        _APP.processEvents()
        self.assertTrue(overlay.search_timer.isActive())
        overlay._on_enter_pressed()
        self.assertFalse(overlay.search_timer.isActive())
        self.assertEqual(len(overlay.matches), 1)
        self.assertEqual(canvas.words_data[1].get("_search_clean"), "beta")

        overlay.search_input.setText("")
        _APP.processEvents()
        self.assertFalse(overlay.search_timer.isActive())
        self.assertEqual(len(overlay.matches), 0)
        host.close()

        # 3. SearchableDropdown debounce + Enter flush
        from PySide6.QtTest import QTest
        dd = SearchableDropdown(["Alpha", "Beta", "Gamma"])
        dd.show()
        QTest.mouseClick(dd, Qt.LeftButton)
        _APP.processEvents()
        dd.line_edit.setText("bet")
        _APP.processEvents()
        self.assertTrue(dd._filter_timer.isActive())
        dd._apply_filter()
        self.assertFalse(dd.list_widget.item(1).isHidden())
        self.assertTrue(dd.list_widget.item(0).isHidden())
        dd.popup.close()
        dd.close()

    def test_chunked_streaming_preserves_manual_marks(self):
        streamed = [
            {"id": 0, "text": "hello", "start": 0.0, "end": 0.4, "status": "bad", "manual_status": "bad", "overlay_suppressed": True, "selected": False},
            {"id": 1, "text": "badword", "start": 0.45, "end": 0.9, "status": None, "manual_status": None, "overlay_suppressed": True, "selected": False},
            {"id": 2, "text": "cutme", "start": 1.0, "end": 1.3, "status": "cut", "manual_status": None, "selected": True},
        ]
        final = [
            {"id": 0, "text": "hello", "start": 0.0, "end": 0.4, "status": None, "manual_status": None},
            {"id": 1, "text": "[pause]", "type": "silence", "start": 0.4, "end": 0.45},
            {"id": 2, "text": "badword", "start": 0.45, "end": 0.9, "status": "bad", "manual_status": "bad"},
            {"id": 3, "text": "cutme", "start": 1.0, "end": 1.3, "status": None, "manual_status": None},
        ]
        merged = merge_manual_marks_into_words(streamed, final)
        self.assertEqual(merged, 3)
        self.assertEqual(final[0]["manual_status"], "bad")
        self.assertTrue(final[0].get("overlay_suppressed"))
        self.assertIsNone(final[2]["manual_status"])
        self.assertIsNone(final[2]["status"])
        self.assertTrue(final[2].get("overlay_suppressed"))
        self.assertTrue(final[3].get("selected"))

        # Streaming tick does not rewind user-edited tail status
        mw = MagicMock()
        mw.engine = _make_mock_engine()
        canvas = TranscriptionCanvas(mw)
        canvas.resize(600, 400)
        canvas.words_data = [
            {"id": 0, "text": "one", "start": 0.0, "end": 0.2, "status": "bad", "manual_status": "bad", "overlay_suppressed": True},
        ]
        canvas._target_streamed_words = [
            {"id": 0, "text": "one", "start": 0.0, "end": 0.2, "status": None, "manual_status": None},
            {"id": 1, "text": "two", "start": 0.2, "end": 0.5, "status": None, "manual_status": None},
        ]
        canvas._process_streaming_tick()
        self.assertEqual(len(canvas.words_data), 2)
        self.assertEqual(canvas.words_data[0]["manual_status"], "bad")

    def test_resolve_bridge_fingerprint_parity_and_transition_guard(self):
        from api.resolve_handler import ResolveHandler
        handler = ResolveHandler(_make_mock_engine().os_doc)

        # Transition callable guard when GetLeftTransition attribute is None
        item_ok = MagicMock()
        item_ok.GetStart.return_value = 100
        item_ok.GetDuration.return_value = 50
        item_ok.GetLeftOffset.return_value = 0
        item_ok.GetMediaPoolItem.return_value = MagicMock()
        item_ok.GetLeftTransition = None
        item_ok.GetRightTransition = None
        tl_mock = MagicMock()
        tl_mock.GetTrackCount.return_value = 1
        tl_mock.GetItemListInTrack.return_value = [item_ok]
        handler.project = MagicMock()
        handler._resolve_target_timeline = MagicMock(return_value=tl_mock)
        self.assertFalse(handler.has_complex_timeline_video("Timeline 1"))

        # Native vs Bridge fingerprint parity even when Lua includes clip 'name'
        tl_mock.GetSetting.return_value = "24"
        tl_mock.GetStartFrame.return_value = 86400
        item_fp = MagicMock()
        item_fp.GetStart.return_value = 86500
        item_fp.GetDuration.return_value = 120
        item_fp.GetLeftOffset.return_value = 15
        item_fp.GetMediaPoolItem.return_value = MagicMock()
        def _track_items(tt, idx):
            return [item_fp] if (tt == "audio" and idx == 1) else []
        tl_mock.GetItemListInTrack.side_effect = _track_items
        handler.backend = "native"
        native_fp = handler.compute_timeline_fingerprint("Timeline 1")

        handler.backend = "bridge"
        handler.bridge_client = MagicMock()
        handler.bridge_client.call.return_value = {
            "ok": True,
            "fps": 24.0,
            "start_frame": 86400,
            "tracks": [
                {"type": "audio", "index": 1, "clips": [{"start": 100, "duration": 120, "left_offset": 15, "name": "clip.mov"}]}
            ],
        }
        bridge_fp = handler.compute_timeline_fingerprint("Timeline 1")
        self.assertEqual(native_fp, bridge_fp)

        with open(os.path.join(_REPO_ROOT, "setupfiles", "BadWords Bridge.lua"), "r", encoding="utf-8") as f:
            lua_src = f.read()
        self.assertIn("find_timeline_by_name", lua_src)
        self.assertIn("bridge_ack(req.id)", lua_src)

    def test_macos_popups_scaling_and_settings_fullscreen_close(self):
        eng = _make_mock_engine()
        cr_dlg = CrashReportConsentDialog(eng)
        self.assertEqual(cr_dlg.windowModality(), Qt.ApplicationModal)
        tel_dlg = TelemetryPopup(eng)
        self.assertEqual(tel_dlg.windowModality(), Qt.ApplicationModal)

        out_dir = os.path.join(_REPO_ROOT, "tests", "artifacts", "macos_popups_audit")
        os.makedirs(out_dir, exist_ok=True)
        cr_dlg.show()
        _APP.processEvents()
        cr_dlg.grab().save(os.path.join(out_dir, "crash_consent_en.png"))
        tel_dlg.show()
        _APP.processEvents()
        tel_dlg.grab().save(os.path.join(out_dir, "telemetry_en.png"))
        cr_dlg.close()
        tel_dlg.close()

        # Verify macOS popup CustomTitleBar drag moves manually without NameError or size stretch
        from PySide6.QtCore import QPointF, QEvent
        from PySide6.QtGui import QMouseEvent
        drag_dlg = CrashReportConsentDialog(eng)
        drag_dlg._is_mac = True
        drag_dlg.show()
        _APP.processEvents()
        orig_sz = drag_dlg.size()
        tb = drag_dlg._tb
        press_ev = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(80, 12),
            QPointF(300, 200),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        tb.mousePressEvent(press_ev)
        self.assertIsNotNone(getattr(tb, "_manual_drag_offset", None))
        move_ev = QMouseEvent(
            QEvent.Type.MouseMove,
            QPointF(110, 32),
            QPointF(330, 220),
            Qt.NoButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )
        tb.mouseMoveEvent(move_ev)
        self.assertTrue(getattr(tb, "_manual_drag_active", False))
        self.assertEqual(drag_dlg.size(), orig_sz)
        rel_ev = QMouseEvent(
            QEvent.Type.MouseButtonRelease,
            QPointF(110, 32),
            QPointF(330, 220),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )
        tb.mouseReleaseEvent(rel_ev)
        drag_dlg.close()

        # Verify macOS Settings Close button & closeEvent close native NSWindow cleanly and detach
        fake_mw = MagicMock()
        dlg = SettingsDialog(eng)
        dlg._main_window = fake_mw
        fake_mw._settings_dialog = dlg
        dlg._is_mac = True
        dlg._macos_close_native_window = MagicMock()
        finished_results = []
        dlg.finished.connect(finished_results.append)
        dlg.show()
        _APP.processEvents()
        dlg.btn_close.click()
        _APP.processEvents()
        dlg._macos_close_native_window.assert_called_once()
        self.assertIsNone(fake_mw._settings_dialog)
        try:
            self.assertFalse(dlg.isVisible())
        except RuntimeError:
            pass  # C++ QMainWindow already deleted cleanly via deleteLater()
        self.assertEqual(finished_results, [0])

        # Verify macOS Fullscreen Settings defers off-Space MainWindow scale rebuild (no Space kick)
        fs_mw = MagicMock()
        fs_mw.rebuild_ui_for_scale = MagicMock()
        fs_mw._pending_scale_rebuild = False
        fs_dlg = SettingsDialog(eng)
        fs_dlg._main_window = fs_mw
        fs_dlg._is_mac = True
        fs_dlg.isFullScreen = MagicMock(return_value=True)
        fs_dlg._apply_live_ui_scale("manual", 110)
        fs_mw.rebuild_ui_for_scale.assert_not_called()
        self.assertTrue(fs_mw._pending_scale_rebuild)
        fs_dlg._macos_close_native_window = MagicMock()
        fs_dlg.close()
        _APP.processEvents()
        config.apply_ui_scaling(mode="auto", pct=None)

        # Verify macOS default startup maximizes on desktop (without forcing Fullscreen Space)
        self.assertTrue(config.DEFAULT_SETTINGS.get("mac_window_maximized"))
        self.assertFalse(config.DEFAULT_SETTINGS.get("mac_window_fullscreen"))

        # Verify macOS osdoc behavior restores FullScreenPrimary (1 << 7)
        with open(os.path.join(_REPO_ROOT, "src", "osdoc.py"), "r", encoding="utf-8") as f:
            osdoc_src = f.read()
        self.assertIn("if top else (1 << 7)", osdoc_src)


if __name__ == "__main__":
    unittest.main()
