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
            return _FakeResp()

        with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
            ok = crash_report.send_report("Boom\ndetails", tb_text="Trace", src_dir=SRC_DIR)
        self.assertTrue(ok)
        self.assertIn(b'name="content"', captured["data"])
        self.assertIn("**Wersja:**".encode("utf-8"), captured["data"])
        self.assertIn("**Tytuł:**".encode("utf-8"), captured["data"])
        self.assertIn("**Treść:**".encode("utf-8"), captured["data"])

        with patch.dict(os.environ, {"BADWORDS_FORCE_INSTALLED": "1"}, clear=False):
            with patch.object(fatal_dialog, "ask_choice", return_value=1):
                with patch.object(fatal_dialog, "send_report") as mock_send:
                    fatal_dialog.show_fatal("generic", error_text="err", src_dir=SRC_DIR, allow_report=True)
                    mock_send.assert_not_called()

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
        self.assertEqual(splash.width(), config.S(345) + config.S(24))
        self.assertEqual(splash.height(), config.S(194) + config.S(24))
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


if __name__ == "__main__":
    unittest.main()
