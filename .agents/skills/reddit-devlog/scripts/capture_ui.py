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
    os_doc.log_file = os.path.join(tmp_dir, "badwords_debug.log")
    os_doc.settings_file = os.path.join(tmp_dir, "settings.json")
    os_doc.user_data = {"telemetry_opt_in": False, "telemetry_geo": False, "auto_crash_report": True}
    os_doc.get_resolve_edition_info.return_value = {"edition": "Studio", "is_21_1_or_newer": False}
    os_doc.get_resolve_installation_info.return_value = {"installed": True, "edition": "Studio"}
    os_doc.get_telemetry_pref.return_value = True
    os_doc.get_subprocess_kwargs.return_value = {}
    engine.os_doc = os_doc

    rh = MagicMock()
    rh.is_connected.return_value = False
    rh.is_bridge_connected.return_value = False
    rh.is_free_21_1_or_newer.return_value = False
    rh.get_all_timelines.return_value = ["Main Edit Timeline"]
    engine.resolve_handler = rh
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
