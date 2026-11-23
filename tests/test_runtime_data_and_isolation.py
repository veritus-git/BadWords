#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: tests/test_runtime_data_and_isolation.py
ROLE: Point 2 Regression & Live Empirical Test Suite
DESCRIPTION:
Verifies DEV vs Installed isolation, stray src/ cleanup, persistent user-profile fallback
on read-only install dirs, atomic JSON writes with .bak corruption recovery & key salvage,
single-write log deduplication under launcher stdout/stderr redirection, 5 MB startup log
trimming, session-protected 24h temp cleanup, Mac App Store DaVinci Resolve container paths,
Windows 8.3 short paths in BadWords Bridge.lua, and osdoc module-level helpers.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config
from config.runtime_data import (
    DEFAULT_TEMP_MAX_AGE_SECONDS,
    LOG_KEEP_BYTES,
    LOG_MAX_BYTES,
    SessionTempManager,
    atomic_write_json,
    detect_dev_mode,
    discover_sibling_installed_dir,
    get_macos_app_store_resolve_dirs,
    get_user_profile_data_dir,
    is_dir_writable,
    is_stream_redirected_to_file,
    load_json_with_recovery,
    migrate_stray_src_files_to_dev_workspace,
    trim_log_file_if_needed,
)
import osdoc
from api.resolve_bridge import ResolveBridgeClient


class TestRuntimeDataAndIsolation(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.mkdtemp(prefix="bw_test_pt2_")

    def tearDown(self):
        # Restore write permissions on any read-only test directories before removal
        for root, dirs, _ in os.walk(self.sandbox):
            for d in dirs:
                try:
                    os.chmod(os.path.join(root, d), 0o755)
                except Exception:
                    pass
        try:
            os.chmod(self.sandbox, 0o755)
        except Exception:
            pass
        shutil.rmtree(self.sandbox, ignore_errors=True)

    # ── 1. DEV vs Installed Detection & Stray src/ Migration ─────────────────

    def test_detect_dev_mode_and_stray_src_migration(self):
        fake_repo = os.path.join(self.sandbox, "BadWordsRepo")
        fake_src = os.path.join(fake_repo, "src")
        fake_git = os.path.join(fake_repo, ".git")
        os.makedirs(fake_src, exist_ok=True)
        os.makedirs(fake_git, exist_ok=True)

        with patch.dict(os.environ, {"BADWORDS_DEV": "", "BADWORDS_FORCE_INSTALLED": ""}, clear=False):
            os.environ.pop("BADWORDS_DEV", None)
            os.environ.pop("BADWORDS_FORCE_INSTALLED", None)
            is_dev, root = detect_dev_mode(fake_src)
            self.assertTrue(is_dev)
            self.assertEqual(root, fake_repo)

        with patch.dict(os.environ, {"BADWORDS_FORCE_INSTALLED": "1"}, clear=False):
            is_dev, root = detect_dev_mode(fake_src)
            self.assertFalse(is_dev)
            self.assertEqual(root, "")

        # Populate stray runtime files in fake_src
        with open(os.path.join(fake_src, "settings.json"), "w", encoding="utf-8") as f:
            json.dump({"gui_lang": "pl"}, f)
        with open(os.path.join(fake_src, "user.json"), "w", encoding="utf-8") as f:
            json.dump({"uuid": "test-uuid-1"}, f)
        os.makedirs(os.path.join(fake_src, "saves"), exist_ok=True)
        with open(os.path.join(fake_src, "saves", "my_edit.bws"), "w", encoding="utf-8") as f:
            f.write("bws_content")
        os.makedirs(os.path.join(fake_src, "temp"), exist_ok=True)
        with open(os.path.join(fake_src, "temp", "stale.wav"), "w", encoding="utf-8") as f:
            f.write("wav")
        os.makedirs(os.path.join(fake_src, "models"), exist_ok=True)

        dev_ws = os.path.join(fake_repo, ".dev_workspace")
        migrate_stray_src_files_to_dev_workspace(fake_src, dev_ws)

        # Verify src/ is completely clean
        self.assertFalse(os.path.exists(os.path.join(fake_src, "settings.json")))
        self.assertFalse(os.path.exists(os.path.join(fake_src, "user.json")))
        self.assertFalse(os.path.exists(os.path.join(fake_src, "saves")))
        self.assertFalse(os.path.exists(os.path.join(fake_src, "temp")))
        self.assertFalse(os.path.exists(os.path.join(fake_src, "models")))

        # Verify .dev_workspace/ received config and saves
        self.assertTrue(os.path.isfile(os.path.join(dev_ws, "settings.json")))
        self.assertTrue(os.path.isfile(os.path.join(dev_ws, "user.json")))
        self.assertTrue(os.path.isfile(os.path.join(dev_ws, "saves", "my_edit.bws")))

    # ── 2. Atomic JSON Writes, Corrupt .bak Backup & Key Salvage ─────────────

    def test_atomic_write_json_concurrent_and_corrupt_recovery(self):
        cfg_file = os.path.join(self.sandbox, "Polish_Łukasz_Żółć", "settings.json")
        errors = []

        def _writer(tid: int):
            try:
                for i in range(10):
                    atomic_write_json(cfg_file, {"thread": tid, "iter": i, "gui_lang": "pl"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_writer, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertTrue(os.path.isfile(cfg_file))
        with open(cfg_file, "r", encoding="utf-8") as f:
            final_data = json.load(f)
        self.assertEqual(final_data.get("gui_lang"), "pl")
        # Ensure no leftover .tmp files remain
        parent_files = os.listdir(os.path.dirname(cfg_file))
        self.assertEqual([fn for fn in parent_files if fn.endswith(".tmp")], [])

        # Now simulate a power-loss truncated JSON file
        corrupt_user_file = os.path.join(self.sandbox, "user.json")
        truncated_content = '{\n    "uuid": "salvaged-uuid-999",\n    "telemetry_opt_in": false,\n    "auto_crash_report": true,\n    "broken_key": '
        with open(corrupt_user_file, "w", encoding="utf-8") as f:
            f.write(truncated_content)

        salvaged, was_corrupt = load_json_with_recovery(
            corrupt_user_file, config.DEFAULT_USER_DATA
        )
        self.assertTrue(was_corrupt)
        self.assertTrue(os.path.isfile(corrupt_user_file + ".bak"))
        with open(corrupt_user_file + ".bak", "r", encoding="utf-8") as bf:
            self.assertEqual(bf.read(), truncated_content)

        # Verify valid keys were salvaged instead of being wiped
        self.assertEqual(salvaged.get("uuid"), "salvaged-uuid-999")
        self.assertIs(salvaged.get("telemetry_opt_in"), False)
        self.assertIs(salvaged.get("auto_crash_report"), True)

    # ── 3. Persistent User-Profile Fallback When Install Dir Is Read-Only ────

    def test_persistent_user_profile_fallback_on_readonly_install_dir(self):
        fake_home = os.path.join(self.sandbox, "Home_Łukasz")
        os.makedirs(fake_home, exist_ok=True)

        win_dir = get_user_profile_data_dir("Windows", home_dir=fake_home)
        self.assertTrue(win_dir.endswith(os.path.join("BadWords")))
        mac_dir = get_user_profile_data_dir("Darwin", home_dir=fake_home)
        self.assertEqual(mac_dir, os.path.join(fake_home, "Library", "Application Support", "BadWords"))
        with patch.dict(os.environ, {"XDG_DATA_HOME": ""}, clear=False):
            os.environ.pop("XDG_DATA_HOME", None)
            lin_dir = get_user_profile_data_dir("Linux", home_dir=fake_home)
            self.assertEqual(lin_dir, os.path.join(fake_home, ".local", "share", "BadWords"))

        # Test empirical write probe on a read-only directory (skip root user if running as uid 0)
        ro_dir = os.path.join(self.sandbox, "ReadOnlyProgramFiles")
        os.makedirs(ro_dir, exist_ok=True)
        os.chmod(ro_dir, stat.S_IRUSR | stat.S_IXUSR)
        if os.geteuid() != 0:
            self.assertFalse(is_dir_writable(ro_dir))

    # ── 4. Single-Write Logging (Zero Duplication) & 5 MB Startup Trimming ───

    def test_5mb_log_trimming_on_startup(self):
        log_path = os.path.join(self.sandbox, "badwords_debug.log")
        # Create a 5.6 MB log file with identifiable numbered lines
        line_template = "2026-11-23 12:00:00 [INFO] Diagnostic log entry line number {:08d} with padding text.\n"
        sample_len = len(line_template.format(1))
        total_lines = (LOG_MAX_BYTES // sample_len) + 8000
        with open(log_path, "w", encoding="utf-8") as f:
            for i in range(total_lines):
                f.write(line_template.format(i))

        initial_size = os.path.getsize(log_path)
        self.assertGreater(initial_size, LOG_MAX_BYTES)

        trimmed = trim_log_file_if_needed(log_path)
        self.assertTrue(trimmed)
        final_size = os.path.getsize(log_path)
        self.assertLessEqual(final_size, LOG_KEEP_BYTES + 512)

        with open(log_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
            tail_content = f.read()
        self.assertIn("LOG TRIMMED ON STARTUP", first_line)
        # Last line must still be present
        self.assertIn(f"line number {total_lines - 1:08d}", tail_content)

    def test_live_launcher_redirected_logging_writes_each_line_once(self):
        """
        Empirically simulates the native C launcher (macos/linux/windows launcher.c)
        redirecting stdout and stderr to badwords_debug.log before Python starts,
        and verifies that log_info, log_warn, log_error, and raw print() each appear
        EXACTLY ONCE in badwords_debug.log.
        """
        log_path = os.path.join(self.sandbox, "badwords_debug.log")
        script = f"""
import sys, os
sys.path.insert(0, {SRC_DIR!r})
import osdoc
doc = osdoc.OSDoctor.__new__(osdoc.OSDoctor)
doc.log_file = {log_path!r}
doc._setup_logging()
osdoc.log_info("UNIQUE_INFO_MARKER_101")
osdoc.log_warn("UNIQUE_WARN_MARKER_202")
osdoc.log_warning("UNIQUE_WARNING_ALIAS_303")
osdoc.log_error("UNIQUE_ERROR_MARKER_404\\nTraceback line 1\\nFileNotFoundError: ffmpeg")
print("UNIQUE_RAW_PRINT_MARKER_505")
sys.stdout.flush()
sys.stderr.flush()
"""
        with open(log_path, "a", encoding="utf-8") as log_fp:
            res = subprocess.run(
                [sys.executable, "-c", script],
                stdout=log_fp,
                stderr=log_fp,
                text=True,
                timeout=10,
            )
        self.assertEqual(res.returncode, 0)

        with open(log_path, "r", encoding="utf-8") as f:
            log_text = f.read()

        self.assertEqual(log_text.count("UNIQUE_INFO_MARKER_101"), 1, f"Duplicate INFO in log:\n{log_text}")
        self.assertEqual(log_text.count("UNIQUE_WARN_MARKER_202"), 1, f"Duplicate WARN in log:\n{log_text}")
        self.assertEqual(log_text.count("UNIQUE_WARNING_ALIAS_303"), 1, f"Duplicate WARNING alias in log:\n{log_text}")
        self.assertEqual(log_text.count("UNIQUE_ERROR_MARKER_404"), 1, f"Duplicate ERROR in log:\n{log_text}")
        self.assertEqual(log_text.count("FileNotFoundError: ffmpeg"), 1, f"Duplicate traceback in log:\n{log_text}")
        self.assertEqual(log_text.count("UNIQUE_RAW_PRINT_MARKER_505"), 1, f"Duplicate raw print in log:\n{log_text}")

    # ── 5. Session-Protected Temp Directory & 24h Stale Cleanup ──────────────

    def test_session_temp_manager_protects_active_project_and_cleans_24h_stale(self):
        temp_dir = os.path.join(self.sandbox, "temp")
        os.makedirs(temp_dir, exist_ok=True)
        mgr = SessionTempManager(temp_dir)

        now = time.time()
        three_hours_ago = now - (3 * 3600)
        two_hours_ago = now - (2 * 3600)
        twenty_six_hours_ago = now - (26 * 3600)

        # 1. Active .bws extract folder and active audio WAV (backdated to 3 hours ago: long editing session)
        active_bws_dir = os.path.join(temp_dir, "bws_import_active")
        os.makedirs(active_bws_dir, exist_ok=True)
        active_flac = os.path.join(active_bws_dir, "source.flac")
        with open(active_flac, "w", encoding="utf-8") as f:
            f.write("active_flac_audio")
        os.utime(active_flac, (three_hours_ago, three_hours_ago))

        active_wav = os.path.join(temp_dir, "BW_123_source.wav")
        with open(active_wav, "w", encoding="utf-8") as f:
            f.write("active_wav_audio")
        os.utime(active_wav, (three_hours_ago, three_hours_ago))

        mgr.register_path(active_bws_dir)
        mgr.register_path(active_wav)

        # 2. Recent unregistered file (2 hours old -> must survive 24h threshold)
        recent_unregistered = os.path.join(temp_dir, "recent_2h.wav")
        with open(recent_unregistered, "w", encoding="utf-8") as f:
            f.write("recent")
        os.utime(recent_unregistered, (two_hours_ago, two_hours_ago))

        # 3. Stale unregistered file (26 hours old -> must be deleted)
        stale_26h = os.path.join(temp_dir, "stale_26h.wav")
        with open(stale_26h, "w", encoding="utf-8") as f:
            f.write("stale")
        os.utime(stale_26h, (twenty_six_hours_ago, twenty_six_hours_ago))

        # 4. Dead PID session lock file (must be cleaned up)
        dead_lock = os.path.join(temp_dir, ".bw_session_999998.json")
        with open(dead_lock, "w", encoding="utf-8") as f:
            json.dump({"pid": 999998, "protected_paths": []}, f)

        # 5. Transient one-shot helper script
        helper_py = os.path.join(temp_dir, "fw_downloader.py")
        with open(helper_py, "w", encoding="utf-8") as f:
            f.write("# downloader")

        # Run mid-session cleanup (default 24h = 86400s, close_session=False)
        mgr.cleanup(max_age_seconds=DEFAULT_TEMP_MAX_AGE_SECONDS, close_session=False)

        self.assertTrue(os.path.isfile(active_flac), "Active .bws FLAC must never be deleted during long session")
        self.assertTrue(os.path.isfile(active_wav), "Active WAV must never be deleted during long session")
        self.assertTrue(os.path.isfile(recent_unregistered), "2-hour-old file must survive 24h cleanup")
        self.assertFalse(os.path.exists(stale_26h), "26-hour-old stale file must be deleted")
        self.assertFalse(os.path.exists(dead_lock), "Dead PID lock file must be removed")

        # Even if someone forces a short max_age_seconds (e.g. 60s) mid-session, active registered paths stay protected!
        mgr.cleanup(max_age_seconds=60, close_session=False)
        self.assertTrue(os.path.isfile(active_flac), "Active .bws FLAC must remain protected even with short max_age")
        self.assertTrue(os.path.isfile(active_wav), "Active WAV must remain protected even with short max_age")

        # Now close session: transient helper script and session lock file must be removed immediately
        mgr.cleanup(max_age_seconds=DEFAULT_TEMP_MAX_AGE_SECONDS, close_session=True)
        self.assertFalse(os.path.exists(helper_py), "Transient fw_downloader.py must be removed on session close")
        self.assertFalse(os.path.exists(mgr._session_file), "Session lock file must be removed on session close")

    # ── 6. Mac App Store Resolve Containers & Windows 8.3 Bridge Paths ───────

    def test_macos_app_store_resolve_container_discovery(self):
        fake_home = os.path.join(self.sandbox, "MacUser")
        mas_container = os.path.join(
            fake_home,
            "Library",
            "Containers",
            "com.blackmagic-design.DaVinciResolveLite",
        )
        mas_resolve_dir = os.path.join(
            mas_container,
            "Data",
            "Library",
            "Application Support",
            "Blackmagic Design",
            "DaVinci Resolve",
        )
        mas_profile_dir = os.path.join(mas_resolve_dir, "Fusion", "Profiles", "Default")
        os.makedirs(mas_profile_dir, exist_ok=True)
        mas_prefs = os.path.join(mas_profile_dir, "Fusion.prefs")
        with open(mas_prefs, "w", encoding="utf-8") as f:
            f.write('Global.BadWordsBridge.Response = "1:e30="\n')

        discovered = get_macos_app_store_resolve_dirs(home_dir=fake_home)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(os.path.abspath(discovered[0]), os.path.abspath(mas_resolve_dir))

        # Verify OSDoctor.get_resolve_script_utility_dirs includes the Mac App Store Utility dir
        doc = osdoc.OSDoctor.__new__(osdoc.OSDoctor)
        doc.is_mac = True
        doc.is_win = False
        doc.is_linux = False
        doc.home_dir = fake_home
        util_dirs = doc.get_resolve_script_utility_dirs()
        expected_mas_util = os.path.join(mas_resolve_dir, "Fusion", "Scripts", "Utility")
        self.assertIn(expected_mas_util, util_dirs)

        # Verify ResolveBridgeClient.find_fusion_prefs_path finds the MAS container Fusion.prefs
        with patch.object(sys, "platform", "darwin"):
            client = ResolveBridgeClient(install_dir=self.sandbox)
            found_prefs = client.find_fusion_prefs_path(home_dir=fake_home)
            self.assertIsNotNone(found_prefs)
            self.assertEqual(os.path.abspath(str(found_prefs)), os.path.abspath(mas_prefs))

    def test_no_hardcoded_mnt_dump_and_osdoc_helpers_work(self):
        # 1. Verify no hardcoded /mnt/dump paths remain in runtime files
        for rel_path in (
            os.path.join("src", "engine", "audio_engine.py"),
            os.path.join("src", "api", "resolve_bridge.py"),
            os.path.join("setupfiles", "BadWords Bridge.lua"),
        ):
            full_p = os.path.join(REPO_ROOT, rel_path)
            with open(full_p, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("/mnt/dump", content, f"Hardcoded /mnt/dump path found in {rel_path}")
            self.assertIn("__BADWORDS_SHORT_INSTALL_DIR__", open(os.path.join(REPO_ROOT, "setupfiles", "BadWords Bridge.lua"), encoding="utf-8").read())

        # 2. Verify osdoc.log_warning and osdoc.load_preferences exist and work cleanly
        self.assertTrue(callable(getattr(osdoc, "log_warning", None)))
        self.assertTrue(callable(getattr(osdoc, "load_preferences", None)))
        prefs = osdoc.load_preferences()
        self.assertIsInstance(prefs, dict)
        self.assertIn("gui_lang", prefs)
        self.assertEqual(prefs.get("offset"), 0.133)
        self.assertEqual(prefs.get("snap_max"), 0.25)


if __name__ == "__main__":
    unittest.main()
