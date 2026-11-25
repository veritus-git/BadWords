#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Regression suite for BadWords v4.1.1 fixes:
- SettingsDialog closes/reopens genuinely maximized (PO Decision 1B) with hidden state reset
- SettingsDialog & MainWindow Always-On-Top Z-order state & Win32 handle sync
- 64-bit Win32 ctypes argtypes/restype guards across osdoc, runtime_data, resolve_bridge, mixins, native_dialogs, utils
- Win11 DWM dark border COLORREF (0x00101010 / 0x002e2e2e, never 0xFFFFFFFE) & cloak-before-hide/paint-uncloak
- Lazy DaVinciResolveScript load on ResolveHandler init
- Windows HuggingFace symlink bypass & incomplete snapshot cache verification
- AnalysisWorker opt-in auto-crash-reporting for technical errors only (PO Decision 2A)
- launcher.c /SUBSYSTEM:WINDOWS diagnostic logging, SEH handler, and safe-boot fallback
- Defensive QMediaPlayer / QVideoWidget fallback for headless / GPU-less Windows PCs
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("BADWORDS_DEV", "1")
os.environ.setdefault("_BW_AUTO_HEAL_ATTEMPTED", "1")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import QApplication, QMainWindow

_app = QApplication.instance() or QApplication([])

import config
from engine.transcription import ModelDownloadError, TranscriptionMixin
from handlers.analysis_worker import AnalysisWorker, is_technical_analysis_error
from gui.dialogs.settings_dialog import SettingsDialog


def _make_mock_engine():
    engine = MagicMock()
    prefs = dict(config.DEFAULT_SETTINGS)
    prefs["gui_lang"] = "en"
    prefs["settings_view_mode"] = "basic"
    prefs["always_on_top"] = False
    prefs["app_icon"] = "default"
    engine.load_preferences.return_value = prefs
    engine.save_preferences = MagicMock()
    engine.current_lang = "en"
    mock_doc = MagicMock()
    mock_doc.is_win = False
    mock_doc.is_mac = False
    mock_doc.is_linux = True
    mock_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
    mock_doc.get_telemetry_pref.return_value = True
    mock_doc.set_always_on_top.return_value = False
    mock_doc.is_window_topmost.return_value = False
    mock_doc.app_data_dir = config.get_app_data_dir() if hasattr(config, "get_app_data_dir") else tempfile.gettempdir()
    engine.os_doc = mock_doc
    mock_resolve = MagicMock()
    mock_resolve.is_free_21_1_or_newer.return_value = False
    engine.resolve_handler = mock_resolve
    return engine


class TestV411Fixes(unittest.TestCase):
    def setUp(self):
        self._repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_settings_reopen_maximized_cycle(self):
        engine = _make_mock_engine()
        main_win = QMainWindow()
        main_win._always_on_top_active = False

        dlg = SettingsDialog(engine, main_win)
        dlg.show()
        _app.processEvents()

        # Simulate user closing while maximized
        with patch.object(dlg, "_is_effectively_maximized", return_value=True):
            dlg._finish_close(0)
        _app.processEvents()

        self.assertTrue(dlg._reopen_maximized)
        self.assertFalse(dlg.isVisible())
        self.assertFalse(bool(dlg.windowState() & Qt.WindowMaximized))

        # Reopen via present() or show(): must consume flag and enter WindowMaximized
        dlg.show()
        _app.processEvents()
        self.assertFalse(dlg._reopen_maximized)
        self.assertTrue(bool(dlg.windowState() & Qt.WindowMaximized))

        # Closing while windowed resets _reopen_maximized to False
        with patch.object(dlg, "_is_effectively_maximized", return_value=False):
            dlg._finish_close(0)
        self.assertFalse(dlg._reopen_maximized)
        dlg.close()

    def test_settings_always_on_top_sync_hidden_and_visible(self):
        engine = _make_mock_engine()
        main_win = QMainWindow()
        main_win._always_on_top_active = False
        # Even if Qt WindowStaysOnTopHint was stale, _always_on_top_active is authoritative
        main_win.setWindowFlag(Qt.WindowStaysOnTopHint, True)

        dlg = SettingsDialog(engine, main_win)
        self.assertFalse(dlg._always_on_top_active)
        self.assertFalse(bool(dlg.windowFlags() & Qt.WindowStaysOnTopHint))

        # Enable then disable while already having a window handle (WA_WState_Created)
        dlg.show()
        _app.processEvents()
        engine.os_doc.set_always_on_top.return_value = True

        dlg.set_always_on_top_state(True)
        self.assertTrue(dlg._always_on_top_active)
        dlg._finish_close(0)

        # Disabled while hidden must still push HWND_NOTOPMOST to native OS handle and clear flag
        engine.os_doc.set_always_on_top.reset_mock()
        dlg.set_always_on_top_state(False)
        self.assertFalse(dlg._always_on_top_active)
        self.assertFalse(bool(dlg.windowFlags() & Qt.WindowStaysOnTopHint))
        engine.os_doc.set_always_on_top.assert_called_with(int(dlg.winId()), False)
        dlg.close()

    def test_win32_ctypes_64bit_signatures_and_dark_dwm_colors(self):
        with open(os.path.join(self._repo_root, "src", "osdoc.py"), "r", encoding="utf-8") as f:
            osdoc_src = f.read()
        for sym in (
            "CreateToolhelp32Snapshot.argtypes",
            "CreateToolhelp32Snapshot.restype = wintypes.HANDLE",
            "GetFileVersionInfoSizeW.argtypes",
            "GetFileVersionInfoW.argtypes",
            "VerQueryValueW.argtypes",
            "SetWindowPos.argtypes",
            "DwmSetWindowAttribute.argtypes",
            "GetWindowLongPtrW.restype = ctypes.c_ssize_t",
        ):
            self.assertIn(sym, osdoc_src, f"Missing 64-bit ctypes annotation {sym} in osdoc.py")

        with open(os.path.join(self._repo_root, "src", "config", "runtime_data.py"), "r", encoding="utf-8") as f:
            rd_src = f.read()
        self.assertIn("OpenProcess.restype = wintypes.HANDLE", rd_src)
        self.assertIn("GetExitCodeProcess.argtypes", rd_src)

        with open(os.path.join(self._repo_root, "src", "api", "resolve_bridge.py"), "r", encoding="utf-8") as f:
            rb_src = f.read()
        self.assertIn("CreateFileW.restype = wintypes.HANDLE", rb_src)
        self.assertIn("ReadFile.argtypes", rb_src)

        with open(os.path.join(self._repo_root, "src", "gui", "components", "mixins.py"), "r", encoding="utf-8") as f:
            mix_src = f.read()
        with open(os.path.join(self._repo_root, "src", "startup", "boot_splash.py"), "r", encoding="utf-8") as f:
            splash_src = f.read()

        # Never leave Win11 taskbar preview outline at DWMWA_COLOR_NONE (0xFFFFFFFE)
        self.assertNotIn("0xFFFFFFFE", mix_src)
        self.assertNotIn("0xFFFFFFFE", splash_src)
        self.assertIn("0x00101010", mix_src)
        self.assertIn("0x002e2e2e", mix_src)
        self.assertIn("0x002e2e2e", splash_src)
        self.assertIn("SetClassLongPtrW", mix_src)
        self.assertIn("SetClassLongPtrW", splash_src)
        self.assertIn("_dwm_cloak", mix_src)

    def test_resolve_handler_defers_native_module_import(self):
        from api.resolve_handler import ResolveHandler
        mock_doc = MagicMock()
        mock_doc.get_resolve_installation_info.return_value = {"installed": True, "edition": "Unknown"}
        mock_doc.is_process_running.return_value = False
        with patch.object(ResolveHandler, "_load_resolve_script_module") as loader:
            rh = ResolveHandler(mock_doc)
            loader.assert_not_called()
            self.assertIsNone(rh.resolve)

    def test_hf_symlink_bypass_classification_and_cache_integrity(self):
        class _DummyEngine(TranscriptionMixin):
            def __init__(self, models_dir):
                self.models_dir = models_dir
                self.os_doc = MagicMock()
                self.os_doc.get_temp_folder.return_value = tempfile.gettempdir()
                self.os_doc.get_short_path.side_effect = lambda p: p
                self.libs_dir = os.path.join(models_dir, "libs")
                self.last_download_error = ""
                self.last_download_error_kind = None

            def _get_python_executable(self):
                return sys.executable

            def txt(self, key, **kw):
                return key

        with tempfile.TemporaryDirectory() as tmp:
            eng = _DummyEngine(tmp)
            # Partial snapshot missing model.bin (like interrupted WinError 1314 run) must be False
            snap_dir = os.path.join(tmp, eng.model_cache_folder("tiny"), "snapshots", "rev1")
            os.makedirs(snap_dir, exist_ok=True)
            with open(os.path.join(snap_dir, "config.json"), "w", encoding="utf-8") as f:
                f.write("{}")
            self.assertFalse(eng.check_model_exists("tiny"))

            # Complete non-empty snapshot returns True
            with open(os.path.join(snap_dir, "model.bin"), "wb") as f:
                f.write(b"123456")
            self.assertTrue(eng.check_model_exists("tiny"))

            # Simulate Windows HF symlink error vs offline error classification
            detail_sym, kind_sym = TranscriptionMixin._classify_download_failure(
                ["Error: [WinError 1314] A required privilege is not held by the client"], 1
            )
            self.assertEqual(kind_sym, "technical")
            self.assertIn("1314", detail_sym)

            _, kind_net = TranscriptionMixin._classify_download_failure(
                ["Error: MaxRetryError: Failed to resolve 'huggingface.co' (getaddrinfo failed)"], 1
            )
            self.assertEqual(kind_net, "network")

        # Verify actual downloader script embeds Windows are_symlinks_supported patch
        with open(os.path.join(self._repo_root, "src", "engine", "transcription.py"), "r", encoding="utf-8") as f:
            tr_src = f.read()
        self.assertIn("are_symlinks_supported = lambda *a, **kw: False", tr_src)

    def test_analysis_worker_crash_report_filtering(self):
        self.assertFalse(is_technical_analysis_error(ModelDownloadError("offline", technical=False)))
        self.assertTrue(is_technical_analysis_error(ModelDownloadError("symlink", technical=True, detail="WinError 1314")))
        self.assertFalse(is_technical_analysis_error(OSError("Errno 28: No space left on device")))
        self.assertFalse(is_technical_analysis_error(RuntimeError("Cancelled by user")))
        self.assertTrue(is_technical_analysis_error(RuntimeError("FFmpeg crashed with code -11")))

        mock_engine = MagicMock()
        mock_engine.os_doc.app_data_dir = tempfile.gettempdir()
        mock_engine.last_pipeline_error = None

        # Technical error (including wrapped pipeline failure) triggers opt-in crash report
        def _fake_pipeline_fail(_settings, **_kwargs):
            mock_engine.last_pipeline_error = (
                RuntimeError("Boom internal bug"),
                "Traceback...\nRuntimeError: Boom internal bug",
            )
            return None, None

        mock_engine.run_analysis_pipeline.side_effect = _fake_pipeline_fail

        emitted_errors = []
        worker = AnalysisWorker(mock_engine, "run_analysis_pipeline", {})
        worker.error.connect(emitted_errors.append)

        with patch("startup.crash_report.get_auto_crash_report_pref", return_value=True), \
             patch("startup.crash_report.send_report_async") as send_mock:
            worker.run()
            send_mock.assert_called_once()
            self.assertIn("Boom internal bug", emitted_errors[-1])

        # Offline ModelDownloadError does NOT trigger telemetry crash report
        emitted_errors.clear()
        mock_engine.last_pipeline_error = None
        mock_engine.run_analysis_pipeline.side_effect = ModelDownloadError("Network down", technical=False)
        with patch("startup.crash_report.get_auto_crash_report_pref", return_value=True), \
             patch("startup.crash_report.send_report_async") as send_mock:
            worker.run()
            send_mock.assert_not_called()
            self.assertIn("Network down", emitted_errors[-1])

    def test_launcher_c_and_main_safe_boot_diagnostics(self):
        import re
        with open(os.path.join(self._repo_root, "setupfiles", "windows", "launcher.c"), "r", encoding="utf-8") as f:
            lc_src = f.read()
        self.assertIsNone(re.search(r"(?<!v)fwprintf\(stderr", lc_src))
        self.assertIn("SetUnhandledExceptionFilter(badwords_seh_handler)", lc_src)
        self.assertIn("relaunch_safe_boot", lc_src)
        self.assertIn("BADWORDS_SAFE_BOOT", lc_src)

        with open(os.path.join(self._repo_root, "src", "main.py"), "r", encoding="utf-8") as f:
            main_src = f.read()
        self.assertIn("all_threads=True", main_src)
        self.assertIn('BADWORDS_SAFE_BOOT', main_src)

    def test_audio_video_preview_survives_missing_multimedia_backend(self):
        from PySide6.QtWidgets import QWidget
        from gui.components.audio_preview import AudioPreviewWidget
        from gui.components.video_preview import VideoPreviewWidget

        parent = QWidget()
        mw = MagicMock()
        mw.engine = _make_mock_engine()
        mw.txt = lambda k, default="": default or k
        mw.prefs = dict(config.DEFAULT_SETTINGS)

        with patch("gui.components.video_preview.QVideoWidget", side_effect=RuntimeError("No video surface")), \
             patch("gui.components.audio_preview.QMediaPlayer", side_effect=RuntimeError("No MF audio")):
            vp = VideoPreviewWidget()
            self.assertIsNone(vp.video_widget)
            ap = AudioPreviewWidget(parent, mw)
            self.assertIsNone(ap.player)
            ap.toggle_play()
            ap._on_volume_changed(50)
            ap.change_speed("1.5x")
            ap.close()
            vp.close()
            parent.close()


if __name__ == "__main__":
    unittest.main()
