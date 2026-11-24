#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
Regression tests for Point 1: Startup pipeline, runtime isolation,
consent-based self-healing, crash reporting, Resolve wrappers, and BootSplash.
"""

import ast
import inspect
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import osdoc
from startup import EXIT_FATAL_REPORTED, crash_report, env_guard, fatal_dialog, runtime_mode, self_heal


class TestStartupGuard(unittest.TestCase):
    def test_python_version_gate(self):
        self.assertFalse(env_guard.check_python_version((3, 9, 18)))
        self.assertTrue(env_guard.check_python_version((3, 10, 0)))
        self.assertTrue(env_guard.check_python_version((3, 12, 9)))
        self.assertFalse(env_guard.check_python_version((3, 13, 0)))

    def test_startup_modules_parse_with_python_38_grammar(self):
        startup_dir = os.path.join(SRC_DIR, "startup")
        py_files = [
            os.path.join(startup_dir, f)
            for f in sorted(os.listdir(startup_dir))
            if f.endswith(".py")
        ]
        self.assertGreaterEqual(len(py_files), 10)
        for path in py_files:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
            ast.parse(src, filename=path, feature_version=(3, 8))

    def test_main_and_src_invariants(self):
        with open(os.path.join(SRC_DIR, "main.py"), "r", encoding="utf-8") as f:
            main_src = f.read()
        self.assertNotIn("-> list:", main_src)
        self.assertNotIn("_run_auto_update_if_needed", main_src)
        self.assertNotIn("webbrowser", main_src)

        for root, _, files in os.walk(SRC_DIR):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(root, fn)
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.assertNotIn("--break-system-packages", content, f"Forbidden flag in {p}")
                if p == os.path.join(SRC_DIR, "main.py") or os.path.join(SRC_DIR, "startup") in root:
                    self.assertNotIn("webbrowser.open", content, f"Browser auto-open forbidden in {p}")

    def test_prune_mismatched_version_paths(self):
        sample = [
            "/home/x/miniconda3/lib/python3.13/site-packages",
            r"C:\Python313\Lib\site-packages",
            "/opt/bw/venv/lib/python3.12/site-packages",
            "/opt/bw/src",
        ]
        removed = env_guard.prune_mismatched_version_paths(sample, current=(3, 12))
        self.assertEqual(
            removed,
            [
                "/home/x/miniconda3/lib/python3.13/site-packages",
                r"C:\Python313\Lib\site-packages",
            ],
        )
        self.assertEqual(
            sample,
            [
                "/opt/bw/venv/lib/python3.12/site-packages",
                "/opt/bw/src",
            ],
        )

    def test_build_repair_command_rules(self):
        self.assertIsNone(self_heal.build_repair_command(None, ["PySide6"], 550))

        cmd_470 = self_heal.build_repair_command("/opt/bw/venv/bin/python3", ["faster_whisper"], 470)
        self.assertNotIn("--break-system-packages", cmd_470)
        self.assertNotIn("nvidia-cublas-cu12", cmd_470)
        self.assertIn("faster-whisper", cmd_470)

        with patch.object(sys, "platform", "linux"):
            cmd_535 = self_heal.build_repair_command("/opt/bw/venv/bin/python3", ["faster_whisper"], 535)
            self.assertIn("nvidia-cublas-cu12", cmd_535)
            self.assertIn("nvidia-cudnn-cu12", cmd_535)

        with patch.object(sys, "platform", "darwin"):
            cmd_mac = self_heal.build_repair_command("/opt/bw/venv/bin/python3", ["faster_whisper"], 550)
            self.assertNotIn("nvidia-cublas-cu12", cmd_mac)

    def test_ensure_components_consent_and_resolve_safety(self):
        with patch.dict(os.environ, {"BADWORDS_FORCE_INSTALLED": "1", "BADWORDS_DEV": ""}, clear=False):
            os.environ.pop("_BW_AUTO_HEAL_ATTEMPTED", None)

            # 1. Hard missing + Close -> exits with 3, never calls subprocess.run
            with patch.object(self_heal, "nvidia_driver_major", return_value=None):
                with patch.object(self_heal, "missing_packages", side_effect=[["PySide6"], []]):
                    with patch.object(self_heal, "ask_choice", return_value=1):
                        with patch("subprocess.run") as mock_run:
                            with self.assertRaises(SystemExit) as cm:
                                self_heal.ensure_components(SRC_DIR)
                            self.assertEqual(cm.exception.code, EXIT_FATAL_REPORTED)
                            mock_run.assert_not_called()

            # 2. Soft only + Continue -> returns without pip
            with patch.object(self_heal, "nvidia_driver_major", return_value=None):
                with patch.object(self_heal, "missing_packages", side_effect=[[], ["faster_whisper"]]):
                    with patch.object(self_heal, "ask_choice", return_value=1):
                        with patch("subprocess.run") as mock_run:
                            self_heal.ensure_components(SRC_DIR)
                            mock_run.assert_not_called()

            # 3. In-Resolve repair success -> exits 3 WITHOUT os.execve
            with patch.object(self_heal, "nvidia_driver_major", return_value=None):
                with patch.object(self_heal, "missing_packages", side_effect=[[], ["faster_whisper"]]):
                    with patch.object(self_heal, "ask_choice", return_value=0):
                        with patch.object(self_heal, "find_venv_python", return_value="/tmp/venv/bin/python3"):
                            with patch.object(self_heal, "has_internet", return_value=True):
                                with patch.object(self_heal, "_run_pip_repair", return_value=(0, "OK")):
                                    with patch.object(self_heal, "is_in_resolve_process", return_value=True):
                                        with patch.object(self_heal, "show_message"):
                                            with patch("os.execve") as mock_exec:
                                                with self.assertRaises(SystemExit) as cm:
                                                    self_heal.ensure_components(SRC_DIR)
                                                self.assertEqual(cm.exception.code, EXIT_FATAL_REPORTED)
                                                mock_exec.assert_not_called()

    def test_crash_report_multipart_and_opt_out(self):
        fields = {
            "title": "[Startup crash] Boom",
            "body": "traceback here",
            "email": "",
            "version": "4.0.1",
            "content": "hello",
        }
        payload, ctype = crash_report.build_multipart(fields, b"PK\x03\x04dummy")
        self.assertIn("multipart/form-data; boundary=", ctype)
        for marker in (b'name="title"', b'name="body"', b'name="version"', b'name="content"', b'filename="logs.zip"'):
            self.assertIn(marker, payload)

        captured = {}

        class _FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def getcode(self):
                return 204

        def _fake_urlopen(req, timeout=20, context=None):
            captured["data"] = req.data
            captured["headers"] = dict(req.header_items())
            return _FakeResp()

        with tempfile.TemporaryDirectory() as tmp_data:
            with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                ok = crash_report.send_report("Boom\ndetails", tb_text="Trace", src_dir=SRC_DIR, app_data_dir=tmp_data)
            self.assertTrue(ok)
        self.assertIn(b'name="content"', captured["data"])
        self.assertIn("**Wersja:**".encode("utf-8"), captured["data"])
        self.assertIn("**Tytuł:**".encode("utf-8"), captured["data"])
        self.assertIn("**Treść:**".encode("utf-8"), captured["data"])
        ua = captured["headers"].get("User-agent") or captured["headers"].get("User-Agent", "")
        self.assertTrue(ua.startswith("BadWords/"), f"Unexpected User-Agent: {ua}")

        # Verify shared uploader handles empty email, custom email, >1900 char truncation, and SettingsDialog parity
        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            ok2, _ = crash_report.post_support_report(
                "https://example.invalid/",
                version="4.0.1",
                title="Test Title",
                body="X" * 3000,
                email="user@example.com",
                zip_bytes=b"PK\x03\x04dummy",
            )
        self.assertTrue(ok2)
        self.assertIn(b"**Email:** user@example.com", captured["data"])
        content_part = captured["data"].split(b'name="content"\r\n\r\n', 1)[1].split(b"\r\n--", 1)[0]
        self.assertLessEqual(len(content_part.decode("utf-8")), 1900)

        with open(os.path.join(SRC_DIR, "gui", "dialogs", "settings_dialog.py"), "r", encoding="utf-8") as f:
            sd_src = f.read()
        self.assertIn("post_support_report", sd_src)
        self.assertNotIn("**Version:**", sd_src)

        with patch.dict(os.environ, {"BADWORDS_FORCE_INSTALLED": "1"}, clear=False):
            with patch.object(fatal_dialog, "get_auto_crash_report_pref", return_value=None):
                with patch.object(fatal_dialog, "ask_choice", return_value=1):
                    with patch.object(fatal_dialog, "send_report") as mock_send:
                        fatal_dialog.show_fatal("generic", error_text="err", src_dir=SRC_DIR, allow_report=True)
                        mock_send.assert_not_called()

    def test_privacy_scrubbing_rate_limit_and_live_http_relay(self):
        import io, json, socketserver, threading, urllib.request, zipfile
        from http.server import BaseHTTPRequestHandler, HTTPServer

        crash_report.reset_rate_limiter_for_tests()
        sample_err = (
            r'File "C:\Users\SecretClientUser\Videos\Confidential_Launch.mp4" failed; '
            r'log at /home/secret_linux_user/docs/raw_take.mov user=secret_linux_user'
        )
        scrubbed = crash_report.sanitize_crash_text(sample_err, src_dir=SRC_DIR)
        self.assertNotIn("SecretClientUser", scrubbed)
        self.assertNotIn("Confidential_Launch", scrubbed)
        self.assertNotIn("secret_linux_user", scrubbed)
        self.assertNotIn("raw_take", scrubbed)
        self.assertIn(".mp4", scrubbed)
        self.assertIn(".mov", scrubbed)

        with tempfile.TemporaryDirectory() as tmp:
            user_json = os.path.join(tmp, "user.json")
            with open(user_json, "w", encoding="utf-8") as f:
                json.dump({"telemetry_opt_in": False, "auto_crash_report": True}, f)
            with open(os.path.join(tmp, "settings.json"), "w", encoding="utf-8") as f:
                json.dump({"gui_lang": "pl"}, f)
            log_path = os.path.join(tmp, "badwords_debug.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("[INFO] Extracting /Users/alice/Movies/TopSecretAd.mov\n")

            self.assertIs(crash_report.get_auto_crash_report_pref(src_dir=SRC_DIR, app_data_dir=tmp), True)

            received = []

            class _Handler(BaseHTTPRequestHandler):
                def do_POST(self):
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length)
                    received.append((dict(self.headers), body))
                    self.send_response(204)
                    self.end_headers()

                def log_message(self, *args):
                    pass

            srv = HTTPServer(("127.0.0.1", 0), _Handler)
            srv_thread = threading.Thread(target=srv.serve_forever, daemon=True)
            srv_thread.start()
            relay_url = f"http://127.0.0.1:{srv.server_port}/"
            try:
                with patch.object(crash_report, "_read_app_constants", return_value=(relay_url, "4.0.1")):
                    # Same crash repeated 4 times -> anti-spam sends only 1
                    for _ in range(4):
                        try:
                            raise ValueError("Cannot open /home/bob/client_video.mp4")
                        except ValueError:
                            et, ev, tb = sys.exc_info()
                            th = crash_report.send_runtime_crash_async(
                                et, ev, tb, context_label="TestThread",
                                src_dir=SRC_DIR, app_data_dir=tmp, allow_dev=True
                            )
                            if th is not None:
                                th.join(timeout=3.0)

                    self.assertEqual(len(received), 1)
                    hdrs, raw = received[0]
                    self.assertTrue((hdrs.get("User-Agent") or "").startswith("BadWords/"))
                    self.assertIn("**Wersja:**".encode("utf-8"), raw)
                    self.assertNotIn(b"client_video", raw)
                    self.assertNotIn(b"/home/bob", raw)

                    # Extract attached zip from multipart body and verify log scrubbing & no user.json/settings.json leak
                    ct_header = hdrs.get("Content-Type") or hdrs.get("Content-type") or ""
                    boundary_bytes = ct_header.split("boundary=", 1)[1].strip().encode("ascii")
                    zip_start = raw.index(b"PK\x03\x04")
                    zip_end = raw.index(b"\r\n--" + boundary_bytes, zip_start)
                    zf = zipfile.ZipFile(io.BytesIO(raw[zip_start:zip_end]))
                    names = zf.namelist()
                    self.assertIn("system_info.txt", names)
                    self.assertIn("badwords_debug.log", names)
                    self.assertNotIn("user.json", names)
                    self.assertNotIn("settings.json", names)
                    log_content = zf.read("badwords_debug.log").decode("utf-8")
                    self.assertNotIn("TopSecretAd", log_content)
                    self.assertNotIn("/Users/alice", log_content)

                    # Simulate app restart (clear in-memory cache) -> SAME error is STILL permanently blocked!
                    crash_report.reset_rate_limiter_for_tests()
                    def _same_crash():
                        raise ValueError("Cannot open /home/bob/client_video.mp4")

                    for _restart in range(2):
                        try:
                            _same_crash()
                        except ValueError:
                            et, ev, tb = sys.exc_info()
                            th2 = crash_report.send_runtime_crash_async(
                                et, ev, tb, context_label="TestThread",
                                src_dir=SRC_DIR, app_data_dir=tmp, allow_dev=True
                            )
                            if th2 is not None:
                                th2.join(timeout=3.0)
                        crash_report.reset_rate_limiter_for_tests()
                    # First _same_crash call has a new stack site (total 2), second restart hit is blocked (still 2)
                    self.assertEqual(len(received), 2)

                    # Distinct exceptions capped at _MAX_PER_SESSION (3 total per session)
                    for idx in range(5):
                        ok = crash_report.send_report(
                            f"UniqueError_{idx}", tb_text=f'File "x.py", line {10 + idx}, in fn',
                            src_dir=SRC_DIR, app_data_dir=tmp, allow_dev=True, suppress_in_dev=True, category="Auto crash"
                        )
                        if idx < 3:
                            self.assertTrue(ok)
                        else:
                            self.assertFalse(ok)
                    self.assertEqual(len(received), 5)
            finally:
                srv.shutdown()
                srv.server_close()

        # Verify Decision 5A in fatal_dialog when auto_crash_report=True
        with patch.dict(os.environ, {"BADWORDS_FORCE_INSTALLED": "1"}, clear=False):
            with patch.object(fatal_dialog, "get_auto_crash_report_pref", return_value=True):
                with patch.object(fatal_dialog, "send_report_async") as mock_auto_send:
                    mock_th = MagicMock()
                    mock_th.is_alive.return_value = False
                    mock_auto_send.return_value = (mock_th, {"done": True, "ok": True})
                    with patch.object(fatal_dialog, "show_message") as mock_msg:
                        fatal_dialog.show_fatal("generic", error_text="boom", src_dir=SRC_DIR, allow_report=True)
                        mock_auto_send.assert_called_once()
                        mock_msg.assert_called_once()
                        self.assertIn("automat", mock_msg.call_args[0][1].lower())

        # Verify live sys.excepthook + threading.excepthook installation & capture in subprocess
        hook_script = (
            "import json, os, sys, tempfile, threading, time\n"
            "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
            "from unittest.mock import patch\n"
            f"sys.path.insert(0, {SRC_DIR!r})\n"
            "from startup import crash_report\n"
            "with tempfile.TemporaryDirectory() as tmp:\n"
            "    with open(os.path.join(tmp, 'user.json'), 'w') as f:\n"
            "        json.dump({'auto_crash_report': True}, f)\n"
            "    hits = []\n"
            "    class H(BaseHTTPRequestHandler):\n"
            "        def do_POST(self):\n"
            "            hits.append(self.rfile.read(int(self.headers.get('Content-Length', 0))))\n"
            "            self.send_response(204); self.end_headers()\n"
            "        def log_message(self, *a): pass\n"
            "    srv = HTTPServer(('127.0.0.1', 0), H)\n"
            "    threading.Thread(target=srv.serve_forever, daemon=True).start()\n"
            "    url = f'http://127.0.0.1:{srv.server_port}/'\n"
            "    with patch.object(crash_report, '_read_app_constants', return_value=(url, '4.0.1')):\n"
            "        crash_report.install_runtime_crash_hooks(src_dir=sys.path[0], app_data_dir=tmp, allow_dev=True)\n"
            "        def boom_thread():\n"
            "            raise RuntimeError('bg_thread_failure')\n"
            "        t = threading.Thread(target=boom_thread, name='WorkerBG')\n"
            "        t.start(); t.join(timeout=2.0)\n"
            "        try:\n"
            "            raise KeyError('main_slot_failure')\n"
            "        except KeyError:\n"
            "            sys.excepthook(*sys.exc_info())\n"
            "        crash_report.wait_for_pending_reports(timeout=3.0)\n"
            "    srv.shutdown(); srv.server_close()\n"
            "    assert len(hits) == 2, f'Expected 2 hits, got {len(hits)}'\n"
            "    print('HOOKS_OK')\n"
        )
        res = subprocess.run([sys.executable, "-c", hook_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr + res.stdout)
        self.assertIn("HOOKS_OK", res.stdout)

        crash_report.reset_rate_limiter_for_tests()

    def test_resolve_wrapper_template_and_generators(self):
        doc = osdoc.OSDoctor()
        wrapper = doc.generate_davinci_wrapper_content()
        self.assertTrue(wrapper)
        compile(wrapper, "BadWords.py", "exec")
        self.assertNotIn("__BADWORDS_INSTALL_DIR__", wrapper)
        self.assertIn(doc.install_dir.replace("\\", "/"), wrapper)
        self.assertNotIn("ctypes.CDLL(os.path.join(_bin_p", wrapper)
        self.assertNotIn("ctypes.CDLL(os.path.join(_d", wrapper)
        self.assertNotIn("--resolve-attached", wrapper)
        self.assertIn("PYTHONNOUSERSITE", wrapper)
        self.assertIn("PYTHONHOME", wrapper)
        self.assertNotIn("shutil.which(", wrapper)

        with open(os.path.join(REPO_ROOT, "setupfiles", "updater.py"), "r", encoding="utf-8") as f:
            self.assertNotIn("--resolve-attached", f.read())

        for rel in ("setupfiles/setup.py", "installer/src/engine.rs"):
            with open(os.path.join(REPO_ROOT, rel), "r", encoding="utf-8") as f:
                self.assertNotIn("ctypes.CDLL(os.path.join(_bin_p, _f))", f.read())

    def test_sync_resolve_scripts_dev_and_free_21_1_preservation(self):
        doc = osdoc.OSDoctor()
        with tempfile.TemporaryDirectory() as tmp:
            d1 = os.path.join(tmp, "dir1")
            d2 = os.path.join(tmp, "dir2")
            os.makedirs(d1)
            os.makedirs(d2)

            # In DEV mode nothing is written
            with patch.object(doc, "is_dev", True):
                with patch.dict(os.environ, {}, clear=False):
                    os.environ.pop("BADWORDS_DEV_SYNC_RESOLVE", None)
                    with patch.object(doc, "get_resolve_script_utility_dirs", return_value=[d1, d2]):
                        doc.sync_resolve_scripts()
                        self.assertFalse(os.path.exists(os.path.join(d1, "BadWords.py")))

            # Non-dev Free 21.1+: BadWords.py IS deployed in primary dir and cleaned from secondary
            with open(os.path.join(d2, "BadWords.py"), "w", encoding="utf-8") as f:
                f.write("old")
            with patch.object(doc, "is_dev", False):
                with patch.object(
                    doc,
                    "get_resolve_installation_info",
                    return_value={"installed": True, "edition": "Free", "version": "21.1.0", "is_21_1_or_newer": True},
                ):
                    with patch.object(doc, "get_resolve_script_utility_dirs", return_value=[d1, d2]):
                        doc.sync_resolve_scripts()
            self.assertTrue(os.path.isfile(os.path.join(d1, "BadWords.py")))
            self.assertFalse(os.path.exists(os.path.join(d2, "BadWords.py")))

    def test_get_venv_python_path_cleaned(self):
        src = inspect.getsource(osdoc.OSDoctor.get_venv_python_path)
        self.assertNotIn("/mnt/dump", src)
        self.assertNotIn("BadWords.exe", src)

        doc = osdoc.OSDoctor()
        with tempfile.TemporaryDirectory() as tmp:
            py3 = os.path.join(tmp, "venv", "bin", "python3")
            os.makedirs(os.path.dirname(py3))
            with open(py3, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n")
            with patch.object(doc, "is_win", False):
                with patch.object(doc, "install_dir", tmp):
                    self.assertEqual(doc.get_venv_python_path(), py3)

    def test_osdoctor_init_skips_hardware_probes(self):
        with patch.object(osdoc.OSDoctor, "has_nvidia_support", return_value=False) as mock_nv:
            doc = osdoc.OSDoctor()
            mock_nv.assert_not_called()
            doc.log_hardware_info()
            mock_nv.assert_called_once()

    def test_boot_splash_lazy_gui_subprocess(self):
        code = (
            "import sys; "
            "from startup.boot_splash import BootSplash; "
            "assert 'gui.main_window' not in sys.modules; "
            "import gui; "
            "assert 'gui.main_window' not in sys.modules; "
            "assert callable(gui.BadWordsGUI)"
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = SRC_DIR
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["BADWORDS_DEV"] = "1"
        res = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_runtime_mode_ignores_resolve_script_api_env(self):
        with patch.dict(os.environ, {"RESOLVE_SCRIPT_API": "/opt/resolve/Developer/Scripting"}, clear=True):
            with patch.object(sys, "argv", ["main.py"]):
                with patch.object(runtime_mode, "is_in_resolve_process", return_value=False):
                    self.assertFalse(runtime_mode.is_embedded_in_resolve())
        with patch.dict(os.environ, {"BADWORDS_EMBEDDED": "1"}, clear=True):
            self.assertTrue(runtime_mode.is_embedded_in_resolve())

    def test_boot_splash_visual_render(self):
        from PySide6.QtWidgets import QApplication
        import config
        from startup.boot_splash import BootSplash

        app = QApplication.instance() or QApplication(sys.argv)
        config.init_ui_scaling(app)
        splash = BootSplash()
        splash.show()
        app.processEvents()
        out_path = os.path.join(REPO_ROOT, "tests", "artifacts", "boot_splash.png")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        pix = splash.grab()
        self.assertFalse(pix.isNull())
        self.assertTrue(pix.save(out_path))
        from PySide6.QtCore import Qt
        self.assertEqual(splash.width(), config.S(345))
        self.assertEqual(splash.height(), config.S(194))
        self.assertFalse(splash.testAttribute(Qt.WA_TranslucentBackground))
        self.assertIsNone(splash.inner_frame.graphicsEffect())
        splash.close()

    def test_dark_startup_dialogs_visual_render(self):
        from PySide6.QtWidgets import QApplication
        from startup.i18n_lite import t
        from startup.native_dialogs import build_dark_qt_dialog
        from startup.self_heal import build_dark_progress_dialog

        app = QApplication.instance() or QApplication(sys.argv)
        artifacts_dir = os.path.join(REPO_ROOT, "tests", "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)

        # 1. Fatal error dialog with consent & details (PL)
        msg_fatal = (
            t("startup_err_generic", src_dir=SRC_DIR, lang="pl", error="RuntimeError: Przykładowy błąd testowy przy starcie", log="/home/user/BadWords/badwords_debug.log")
            + "\n\n"
            + t("startup_report_consent", src_dir=SRC_DIR, lang="pl")
        )
        dlg1, _ = build_dark_qt_dialog(
            t("startup_err_title", src_dir=SRC_DIR, lang="pl"),
            msg_fatal,
            [t("startup_report_send", src_dir=SRC_DIR, lang="pl"), t("startup_report_close", src_dir=SRC_DIR, lang="pl")],
            default=1,
            details='Traceback (most recent call last):\n  File "main.py", line 123, in main\nRuntimeError: Example',
            kind="error",
            src_dir=SRC_DIR,
            lang="pl",
        )
        dlg1.show()
        app.processEvents()
        p1 = os.path.join(artifacts_dir, "dialog_fatal_pl.png")
        self.assertTrue(dlg1.grab().save(p1))
        dlg1.close()

        # 2. Component repair consent dialog (PL)
        msg_heal = t("heal_prompt", src_dir=SRC_DIR, lang="pl", packages="PySide6, faster-whisper, av<19, pypdf", size="~400 MB + ~1200 MB (NVIDIA CUDA)")
        dlg2, _ = build_dark_qt_dialog(
            t("heal_title", src_dir=SRC_DIR, lang="pl"),
            msg_heal,
            [
                t("heal_btn_repair", src_dir=SRC_DIR, lang="pl"),
                t("heal_btn_skip", src_dir=SRC_DIR, lang="pl"),
                t("heal_btn_close", src_dir=SRC_DIR, lang="pl"),
            ],
            default=0,
            kind="question",
            src_dir=SRC_DIR,
        )
        dlg2.show()
        app.processEvents()
        p2 = os.path.join(artifacts_dir, "dialog_heal_pl.png")
        self.assertTrue(dlg2.grab().save(p2))
        dlg2.close()

        # 3. Repair progress dialog (PL)
        dlg3 = build_dark_progress_dialog(
            t("heal_title", src_dir=SRC_DIR, lang="pl"),
            t("heal_progress", src_dir=SRC_DIR, lang="pl"),
        )
        dlg3.show()
        app.processEvents()
        p3 = os.path.join(artifacts_dir, "dialog_heal_progress_pl.png")
        self.assertTrue(dlg3.grab().save(p3))
        dlg3.close()

        # 4. Auto-sent fatal startup crash dialog (PL)
        msg_auto = (
            t("startup_err_generic", src_dir=SRC_DIR, lang="pl", error="RuntimeError: Krytyczny błąd startu", log="/home/<USER>/BadWords/badwords_debug.log")
            + "\n\n"
            + t("startup_report_auto_sent", src_dir=SRC_DIR, lang="pl")
        )
        dlg4, _ = build_dark_qt_dialog(
            t("startup_err_title", src_dir=SRC_DIR, lang="pl"),
            msg_auto,
            ["OK"],
            default=0,
            details='Traceback (most recent call last):\n  File "main.py", line 123, in main\nRuntimeError: Example',
            kind="error",
            src_dir=SRC_DIR,
            lang="pl",
        )
        dlg4.show()
        app.processEvents()
        p4 = os.path.join(artifacts_dir, "dialog_fatal_auto_pl.png")
        self.assertTrue(dlg4.grab().save(p4))
        dlg4.close()


if __name__ == "__main__":
    unittest.main()
