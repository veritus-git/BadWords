#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/self_heal.py
ROLE: Consent-Based Component Repair
DESCRIPTION:
Verifies core BadWords components and, only with explicit user consent,
repairs missing packages strictly inside BadWords' own venv (never touching
system Python or killing a host DaVinci Resolve process).
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request

from startup import EXIT_FATAL_REPORTED
from startup.crash_report import primary_log_hint
from startup.env_guard import (
    HARD_REQUIRED,
    PIP_NAMES,
    SOFT_REQUIRED,
    find_venv_python,
    missing_packages,
)
from startup.fatal_dialog import show_fatal
from startup.i18n_lite import t
from startup.native_dialogs import ask_choice, show_message
from startup.runtime_mode import is_in_resolve_process


def _hidden_sp_kwargs():
    if sys.platform == "win32" or os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        si.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        return {
            "startupinfo": si,
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000),
            "stdin": subprocess.DEVNULL,
        }
    return {}


def nvidia_driver_major():
    """Return installed NVIDIA driver major version, or None if unavailable/macOS."""
    if sys.platform == "darwin":
        return None
    nvsmi = shutil.which("nvidia-smi")
    if not nvsmi and (sys.platform == "win32" or os.name == "nt"):
        for cand in (
            os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvidia-smi.exe"),
            r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe",
        ):
            if os.path.isfile(cand):
                nvsmi = cand
                break
    if not nvsmi:
        return None
    try:
        res = subprocess.run(
            [nvsmi, "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            **_hidden_sp_kwargs()
        )
        if res.returncode != 0 or not res.stdout:
            return None
        first_line = res.stdout.strip().splitlines()[0].strip()
        m = re.search(r"(\d+)(?:\.\d+)?", first_line)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def build_repair_command(venv_py, missing, driver_major=None):
    """Build pip command targeting only BadWords' venv. Never touches system Python."""
    if not venv_py:
        return None
    pkgs = []
    for name in missing:
        pip_name = PIP_NAMES.get(name, name)
        if pip_name not in pkgs:
            pkgs.append(pip_name)
    if (
        "faster_whisper" in missing
        and driver_major is not None
        and driver_major >= 525
        and sys.platform != "darwin"
    ):
        pkgs.extend(["nvidia-cublas-cu12", "nvidia-cudnn-cu12"])
    if not pkgs:
        return None
    return [venv_py, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check"] + pkgs


def has_internet(timeout=5):
    """Quick connectivity check to PyPI before attempting pip repair."""
    try:
        req = urllib.request.Request("https://pypi.org/simple/pip/", method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode() < 500
    except Exception:
        try:
            req = urllib.request.Request("https://pypi.org/simple/pip/")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.getcode() < 500
        except Exception:
            return False


def _is_dev_mode(src_dir):
    try:
        import osdoc
        return bool(osdoc.detect_dev_mode(src_dir)[0])
    except Exception:
        if os.environ.get("BADWORDS_FORCE_INSTALLED") == "1":
            return False
        if os.environ.get("BADWORDS_DEV") == "1":
            return True
        abs_src = os.path.abspath(src_dir)
        return (
            os.path.exists(os.path.join(abs_src, ".git"))
            or os.path.exists(os.path.join(os.path.dirname(abs_src), ".git"))
        )


def _append_log(log_path, text):
    try:
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        with open(log_path, "a", encoding="utf-8", errors="replace") as f:
            f.write(text)
    except Exception:
        pass


def _run_pip_with_qt_progress(cmd, title, label, log_path):
    from PySide6.QtCore import Qt, QThread, Signal
    from PySide6.QtWidgets import QApplication, QProgressDialog

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv if sys.argv else ["BadWords"])

    class _RepairWorker(QThread):
        finished_signal = Signal(int, str)

        def run(self):
            try:
                res = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    **_hidden_sp_kwargs()
                )
                self.finished_signal.emit(int(res.returncode), res.stdout or "")
            except Exception as exc:
                self.finished_signal.emit(1, str(exc))

    dlg = QProgressDialog(label, None, 0, 0)
    dlg.setWindowTitle(title)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.setCancelButton(None)
    dlg.setMinimumDuration(0)
    dlg.setAutoClose(False)
    dlg.setAutoReset(False)

    outcome = {"code": 1, "out": ""}
    worker = _RepairWorker()

    def _on_done(code, out):
        outcome["code"] = code
        outcome["out"] = out
        dlg.close()

    worker.finished_signal.connect(_on_done)
    worker.start()
    dlg.exec()
    worker.wait()

    if outcome["out"]:
        _append_log(log_path, "\n[SelfHeal]\n" + outcome["out"] + "\n")
    return outcome["code"], outcome["out"]


def _run_pip_repair(cmd, title, label, log_path):
    try:
        import PySide6.QtWidgets  # noqa: F401
        return _run_pip_with_qt_progress(cmd, title, label, log_path)
    except Exception:
        pass

    show_message(title, label, error=False)
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            **_hidden_sp_kwargs()
        )
        out = res.stdout or ""
        if out:
            _append_log(log_path, "\n[SelfHeal]\n" + out + "\n")
        return int(res.returncode), out
    except Exception as exc:
        err = str(exc)
        _append_log(log_path, "\n[SelfHeal ERROR] " + err + "\n")
        return 1, err


def _relaunch_in_venv(venv_py, src_dir):
    new_env = os.environ.copy()
    new_env["_BW_AUTO_HEAL_ATTEMPTED"] = "1"
    main_py = os.path.join(os.path.abspath(src_dir), "main.py")
    args = [main_py] + list(sys.argv[1:])

    if sys.platform == "win32" or os.name == "nt":
        pyw = os.path.join(os.path.dirname(venv_py), "pythonw.exe")
        target_py = pyw if os.path.isfile(pyw) else venv_py
        subprocess.Popen([target_py] + args, env=new_env, **_hidden_sp_kwargs())
        sys.exit(0)
    else:
        os.execve(venv_py, [venv_py] + args, new_env)


def ensure_components(src_dir):
    """Check core packages and repair missing ones only with explicit user consent."""
    abs_src = os.path.abspath(src_dir)
    hard_missing = missing_packages(HARD_REQUIRED)
    soft_missing = missing_packages(SOFT_REQUIRED)
    all_missing = hard_missing + soft_missing

    if not all_missing:
        return

    if _is_dev_mode(abs_src):
        if not hard_missing:
            sys.stderr.write(
                "[BadWords DEV] Optional runtime packages missing ({0}); skipping self-heal.\n".format(
                    ", ".join(soft_missing)
                )
            )
            sys.stderr.flush()
            return
        show_fatal(
            "env_missing",
            error_text="Missing required packages: " + ", ".join(hard_missing),
            src_dir=abs_src,
            allow_report=False,
        )
        sys.exit(EXIT_FATAL_REPORTED)

    if os.environ.get("_BW_AUTO_HEAL_ATTEMPTED") == "1":
        if hard_missing:
            show_fatal(
                "heal_failed",
                error_text="Missing packages after repair attempt: " + ", ".join(hard_missing),
                src_dir=abs_src,
            )
            sys.exit(EXIT_FATAL_REPORTED)
        return

    title = t("heal_title", src_dir=abs_src)
    pkg_list = ", ".join(PIP_NAMES.get(m, m) for m in all_missing)
    drv_major = nvidia_driver_major() if "faster_whisper" in all_missing else None
    include_cuda = bool(
        "faster_whisper" in all_missing
        and drv_major is not None
        and drv_major >= 525
        and sys.platform != "darwin"
    )
    size_hint = "~400 MB + ~1200 MB (NVIDIA CUDA)" if include_cuda else "~400 MB"

    prompt = t("heal_prompt", src_dir=abs_src, packages=pkg_list, size=size_hint)
    btn_repair = t("heal_btn_repair", src_dir=abs_src)
    btn_skip = t("heal_btn_skip", src_dir=abs_src)
    btn_close = t("heal_btn_close", src_dir=abs_src)

    if hard_missing:
        buttons = [btn_repair, btn_close]
        win_map = t("startup_win_button_map", src_dir=abs_src, yes=btn_repair, no=btn_close, cancel="")
        choice = ask_choice(title, prompt, buttons, default=0, error=False, win_button_map_text=win_map)
        if choice != 0:
            sys.exit(EXIT_FATAL_REPORTED)
    else:
        buttons = [btn_repair, btn_skip, btn_close]
        win_map = t(
            "startup_win_button_map",
            src_dir=abs_src,
            yes=btn_repair,
            no=btn_skip,
            cancel=", Cancel = {0}".format(btn_close),
        )
        choice = ask_choice(title, prompt, buttons, default=0, error=False, win_button_map_text=win_map)
        if choice == 1:
            return
        if choice != 0:
            sys.exit(EXIT_FATAL_REPORTED)

    venv_py = find_venv_python(abs_src)
    if not venv_py:
        show_fatal(
            "env_missing",
            error_text="Private BadWords virtual environment was not found.",
            src_dir=abs_src,
        )
        sys.exit(EXIT_FATAL_REPORTED)

    if not has_internet():
        show_message(title, t("heal_offline", src_dir=abs_src), error=True)
        if hard_missing:
            sys.exit(EXIT_FATAL_REPORTED)
        return

    cmd = build_repair_command(venv_py, all_missing, driver_major=drv_major)
    if not cmd:
        return

    log_path = primary_log_hint(abs_src)
    progress_label = t("heal_progress", src_dir=abs_src)
    code, out = _run_pip_repair(cmd, title, progress_label, log_path)
    if code != 0:
        tail = "\n".join((out or "").strip().splitlines()[-8:])
        show_fatal("heal_failed", error_text=tail or "pip exited with code {0}".format(code), src_dir=abs_src)
        sys.exit(EXIT_FATAL_REPORTED)

    if is_in_resolve_process():
        show_message(title, t("heal_done_resolve", src_dir=abs_src), error=False)
        sys.exit(EXIT_FATAL_REPORTED)

    _relaunch_in_venv(venv_py, abs_src)
