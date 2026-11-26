#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Helper script for .agents/skills/reddit-devlog to capture clean English-UI
screenshots of real BadWords widgets/windows under QT_QPA_PLATFORM=offscreen.
"""

import argparse
import os
import sys
import tempfile
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["BADWORDS_DEV"] = "1"
os.environ.setdefault("_BW_AUTO_HEAL_ATTEMPTED", "1")

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", "..", ".."))
_SRC_DIR = os.path.join(_REPO_ROOT, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from PySide6.QtWidgets import QApplication  # noqa: E402


def _make_mock_engine(tmp_dir: str):
    import config

    prefs = dict(config.DEFAULT_SETTINGS)
    prefs["gui_lang"] = "en"
    prefs["settings_view_mode"] = "basic"
    prefs["timeline_assembly_method"] = "xml"
    prefs["force_xml_assembly"] = True
    prefs["auto_check_updates"] = False
    prefs["ui_scale_mode"] = "manual"
    prefs["ui_scale_pct"] = 100
    saved = dict(prefs)

    engine = MagicMock()
    engine.load_preferences.side_effect = lambda: dict(saved)
    engine.save_preferences.side_effect = lambda d: saved.update(d)
    engine.current_lang = "en"

    os_doc = MagicMock()
    os_doc.is_win = False
    os_doc.is_mac = False
    os_doc.install_dir = tmp_dir
    os_doc.saves_dir = os.path.join(tmp_dir, "saves")
    os_doc.temp_dir = os.path.join(tmp_dir, "temp")
    os_doc.models_dir = os.path.join(tmp_dir, "models")
    os_doc.log_file = os.path.join(tmp_dir, "badwords_debug.log")
    os_doc.settings_file = os.path.join(tmp_dir, "settings.json")
    os_doc.user_data = {"telemetry_opt_in": False, "telemetry_geo": False, "auto_crash_report": True}
    os_doc.get_autosave_dir.return_value = os.path.join(tmp_dir, "autosave")
    os_doc.get_temp_folder.return_value = os.path.join(tmp_dir, "temp")
    os_doc.get_venv_python_path.return_value = sys.executable
    os_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
    os_doc.get_resolve_installation_info.return_value = {"installed": True, "edition": "Studio"}
    os_doc.get_telemetry_pref.return_value = True
    os_doc.get_subprocess_kwargs.return_value = {}
    os_doc.is_window_topmost.return_value = False
    os_doc.set_always_on_top.return_value = False
    engine.os_doc = os_doc

    rh = MagicMock()
    rh.is_connected.return_value = False
    rh.is_bridge_connected.return_value = False
    rh.is_free_21_1_or_newer.return_value = False
    rh.get_all_timelines.return_value = ["Main Edit Timeline"]
    engine.resolve_handler = rh
    engine.calculate_timeline_structure_with_cuts.return_value = (
        [{"start": 0.0, "end": 0.95}, {"start": 2.4, "end": 6.45}, {"start": 7.0, "end": 9.0}],
        [{"start": 0.95, "end": 2.4}, {"start": 6.45, "end": 7.0}],
    )
    engine.recalculate_silences_in_ram.return_value = ([], {})
    return engine


def _capture_main_window(app, engine, out_path: str, page: int = 0):
    from gui.main_window import BadWordsGUI

    orig = (
        BadWordsGUI._populate_timeline_track_combos,
        BadWordsGUI.check_telemetry,
        BadWordsGUI._start_update_check,
        BadWordsGUI._preload_settings,
    )
    BadWordsGUI._populate_timeline_track_combos = lambda self: None
    BadWordsGUI.check_telemetry = lambda self: None
    BadWordsGUI._start_update_check = lambda self: None
    BadWordsGUI._preload_settings = lambda self: None
    try:
        win = BadWordsGUI(engine, engine.resolve_handler)
    finally:
        (
            BadWordsGUI._populate_timeline_track_combos,
            BadWordsGUI.check_telemetry,
            BadWordsGUI._start_update_check,
            BadWordsGUI._preload_settings,
        ) = orig

    try:
        win.resize(1280, 780)
        win.show()
        win.go_to_page(page)
        if page == 1 and hasattr(win, "bar_processing"):
            win.bar_processing._value = 54.0
        app.processEvents()
        return win.grab().save(out_path)
    finally:
        app.removeEventFilter(win)
        if getattr(win, "_global_app_filter", None):
            app.removeEventFilter(win._global_app_filter)
        win.closeEvent = lambda e: e.accept()
        win.close()
        win.deleteLater()
        app.processEvents()


def _capture_editor(app, engine, out_path: str):
    from gui.main_window import BadWordsGUI

    orig = (
        BadWordsGUI._populate_timeline_track_combos,
        BadWordsGUI.check_telemetry,
        BadWordsGUI._start_update_check,
        BadWordsGUI._preload_settings,
    )
    BadWordsGUI._populate_timeline_track_combos = lambda self: None
    BadWordsGUI.check_telemetry = lambda self: None
    BadWordsGUI._start_update_check = lambda self: None
    BadWordsGUI._preload_settings = lambda self: None
    try:
        win = BadWordsGUI(engine, engine.resolve_handler)
    finally:
        (
            BadWordsGUI._populate_timeline_track_combos,
            BadWordsGUI.check_telemetry,
            BadWordsGUI._start_update_check,
            BadWordsGUI._preload_settings,
        ) = orig

    try:
        import numpy as np
        from engine.waveform import WaveformPeaks

        sample_words = [
            {"id": 0, "meta_lang": "en", "text": "Hey", "start": 0.2, "end": 0.45, "status": "normal", "is_segment_start": True},
            {"id": 1, "text": "everyone,", "start": 0.46, "end": 0.9, "status": "normal"},
            {"id": 2, "text": "um", "start": 0.95, "end": 1.2, "status": "bad"},
            {"id": 3, "text": "today", "start": 1.6, "end": 1.9, "status": "repeat"},
            {"id": 4, "text": "we", "start": 1.92, "end": 2.1, "status": "repeat"},
            {"id": 5, "text": "today", "start": 2.5, "end": 2.75, "status": "normal"},
            {"id": 6, "text": "we're", "start": 2.76, "end": 2.98, "status": "normal"},
            {"id": 7, "text": "cleaning", "start": 3.0, "end": 3.4, "status": "normal"},
            {"id": 8, "text": "up", "start": 3.42, "end": 3.6, "status": "normal"},
            {"id": 9, "text": "dead", "start": 3.65, "end": 3.95, "status": "normal"},
            {"id": 10, "text": "air", "start": 3.98, "end": 4.2, "status": "normal"},
            {"id": 11, "text": "fast.", "start": 4.25, "end": 4.6, "status": "normal"},
            {"id": 12, "text": "Let's", "start": 5.4, "end": 5.65, "status": "normal", "is_segment_start": True},
            {"id": 13, "text": "cut", "start": 5.66, "end": 5.95, "status": "normal"},
            {"id": 14, "text": "all", "start": 5.96, "end": 6.2, "status": "normal"},
            {"id": 15, "text": "those", "start": 6.22, "end": 6.45, "status": "normal"},
            {"id": 16, "text": "retakes", "start": 6.48, "end": 6.95, "status": "typo"},
            {"id": 17, "text": "and", "start": 7.0, "end": 7.2, "status": "normal"},
            {"id": 18, "text": "pauses", "start": 7.22, "end": 7.55, "status": "normal"},
            {"id": 19, "text": "automatically.", "start": 7.6, "end": 8.2, "status": "normal"},
            {"id": 20, "text": "Once", "start": 9.1, "end": 9.4, "status": "normal", "is_segment_start": True},
            {"id": 21, "text": "it", "start": 9.42, "end": 9.55, "status": "normal"},
            {"id": 22, "text": "looks", "start": 9.56, "end": 9.85, "status": "normal"},
            {"id": 23, "text": "good,", "start": 9.86, "end": 10.2, "status": "normal"},
            {"id": 24, "text": "uh", "start": 10.35, "end": 10.6, "status": "bad"},
            {"id": 25, "text": "just", "start": 10.75, "end": 11.0, "status": "normal"},
            {"id": 26, "text": "hit", "start": 11.02, "end": 11.2, "status": "normal"},
            {"id": 27, "text": "Assemble", "start": 11.22, "end": 11.75, "status": "normal"},
            {"id": 28, "text": "or", "start": 11.78, "end": 11.95, "status": "normal"},
            {"id": 29, "text": "export", "start": 11.98, "end": 12.35, "status": "normal"},
            {"id": 30, "text": "to", "start": 12.36, "end": 12.5, "status": "normal"},
            {"id": 31, "text": "Resolve.", "start": 12.52, "end": 13.1, "status": "normal"},
        ]
        win.resize(1280, 780)
        win.show()
        win.text_canvas.load_data(sample_words)
        n_pts = 480
        t_arr = np.linspace(0.0, 14.0, n_pts, dtype=np.float32)
        env = np.abs(np.sin(t_arr * 1.9)).astype(np.float32) * 0.65
        env[50:80] *= 0.04
        env[160:190] *= 0.04
        env[300:340] *= 0.04
        peaks = WaveformPeaks(
            peaks_min=-env,
            peaks_max=env,
            peaks_rms=env * 0.55,
            duration=14.0,
        )
        wt = win.audio_preview.waveform_timeline
        if hasattr(wt, "set_peaks"):
            wt.set_peaks(peaks)
        else:
            wt._peaks = peaks
            wt._duration = 14.0
        if hasattr(wt, "zoom_fit"):
            wt.zoom_fit()
        win.go_to_page(2)
        win._toggle_activity("silence")
        win._toggle_activity("main_panel")
        if hasattr(win, "tgl_cut_silence"):
            win.tgl_cut_silence.setChecked(True, animated=False)
        app.processEvents()
        return win.grab().save(out_path)
    finally:
        app.removeEventFilter(win)
        if getattr(win, "_global_app_filter", None):
            app.removeEventFilter(win._global_app_filter)
        win.closeEvent = lambda e: e.accept()
        win.close()
        win.deleteLater()
        app.processEvents()


def _capture_settings(app, engine, out_path: str, tab_idx: int, advanced: bool = False):
    from gui.dialogs.settings_dialog import SettingsDialog
    from gui.dialogs.update_dialog import UpdateCheckThread

    UpdateCheckThread._checked = True
    UpdateCheckThread._cached_result = None
    dlg = SettingsDialog(engine)
    try:
        if advanced and hasattr(dlg, "tgl_advanced_mode"):
            dlg.tgl_advanced_mode.setChecked(True)
        dlg.category_list.setCurrentRow(tab_idx)
        dlg.show()
        app.processEvents()
        return dlg.grab().save(out_path)
    finally:
        dlg.closeEvent = lambda e: e.accept()
        dlg.close()
        dlg.deleteLater()
        app.processEvents()


def main():
    parser = argparse.ArgumentParser(description="Capture English BadWords UI screenshots for Reddit devlogs.")
    parser.add_argument("--out", required=True, help="Output directory (e.g. devlogs/2026-11-26_feature)")
    parser.add_argument(
        "--views",
        nargs="+",
        default=["welcome"],
        choices=[
            "welcome",
            "processing",
            "editor",
            "settings_general",
            "settings_appearance",
            "settings_editor",
            "settings_davinci",
            "settings_markers",
            "settings_support",
            "settings_about",
            "telemetry",
        ],
        help="Preset views to render",
    )
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    app = QApplication.instance() or QApplication([])
    import config

    config.apply_ui_scaling(mode="manual", pct=100)
    config.apply_dark_app_theme(app)

    with tempfile.TemporaryDirectory() as tmp:
        engine = _make_mock_engine(tmp)
        saved_paths = []
        for idx, view in enumerate(args.views, start=1):
            out_file = os.path.join(args.out, f"screenshot_{idx}_{view}.png")
            ok = False
            if view == "welcome":
                ok = _capture_main_window(app, engine, out_file, page=0)
            elif view == "processing":
                ok = _capture_main_window(app, engine, out_file, page=1)
            elif view == "editor":
                ok = _capture_editor(app, engine, out_file)
            elif view == "settings_general":
                ok = _capture_settings(app, engine, out_file, 0, advanced=True)
            elif view == "settings_appearance":
                ok = _capture_settings(app, engine, out_file, 1)
            elif view == "settings_editor":
                ok = _capture_settings(app, engine, out_file, 2)
            elif view == "settings_davinci":
                ok = _capture_settings(app, engine, out_file, 3)
            elif view == "settings_markers":
                ok = _capture_settings(app, engine, out_file, 5)
            elif view == "settings_support":
                ok = _capture_settings(app, engine, out_file, 7)
            elif view == "settings_about":
                ok = _capture_settings(app, engine, out_file, 8)
            elif view == "telemetry":
                from gui.dialogs.telemetry_popup import TelemetryPopup

                pop = TelemetryPopup(lang="en")
                pop.show()
                app.processEvents()
                ok = pop.grab().save(out_file)
                pop.close()

            if not ok:
                raise RuntimeError(f"Failed to capture view: {view}")
            saved_paths.append(out_file)
            print("Saved:", out_file)


if __name__ == "__main__":
    main()
