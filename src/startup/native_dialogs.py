#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/native_dialogs.py
ROLE: Cross-Platform Startup Dialogs
DESCRIPTION:
Displays choice and info/error dialogs via PySide6 when available, or native OS
dialogs (Win32 MessageBoxW, macOS osascript, Linux zenity/kdialog/notify-send)
when Qt cannot be loaded. Never raises and always mirrors messages to stderr.
"""

import os
import shutil
import subprocess
import sys


_QT_APP_REF = None


def _try_qt_widgets():
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        return QApplication, QMessageBox
    except Exception:
        return None, None


def _ensure_qt_app(QApplication):
    global _QT_APP_REF
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv if sys.argv else ["BadWords"])
        _QT_APP_REF = app
    return app


def _ask_choice_qt(title, text, buttons, default=0, details=None, error=False):
    QApplication, QMessageBox = _try_qt_widgets()
    if QApplication is None:
        return False, None
    try:
        _ensure_qt_app(QApplication)
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Critical if error else QMessageBox.Question)
        if details:
            box.setDetailedText(details)

        btn_objs = []
        for label in buttons:
            btn = box.addButton(str(label), QMessageBox.ActionRole)
            btn_objs.append(btn)
        if btn_objs and 0 <= default < len(btn_objs):
            box.setDefaultButton(btn_objs[default])

        box.exec()
        clicked = box.clickedButton()
        if clicked in btn_objs:
            return True, btn_objs.index(clicked)
        return True, None
    except Exception:
        return False, None


def _show_message_qt(title, text, error=True, details=None):
    QApplication, QMessageBox = _try_qt_widgets()
    if QApplication is None:
        return False
    try:
        _ensure_qt_app(QApplication)
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(QMessageBox.Critical if error else QMessageBox.Information)
        if details:
            box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()
        return True
    except Exception:
        return False


def _win32_message_box(title, text, flags):
    import ctypes
    return ctypes.windll.user32.MessageBoxW(None, str(text), str(title), flags)


def _macos_dialog(title, text, buttons, default=0):
    btn_items = []
    for idx, label in enumerate(buttons):
        btn_items.append("item {0} of argv".format(idx + 3))
    btn_list_expr = "{" + ", ".join(btn_items) + "}"
    default_expr = "item {0} of argv".format(default + 3) if 0 <= default < len(buttons) else "item 3 of argv"
    script_lines = [
        "on run argv",
        "display dialog (item 1 of argv) with title (item 2 of argv) buttons "
        + btn_list_expr
        + " default button "
        + default_expr,
        "end run",
    ]
    cmd = ["osascript"]
    for line in script_lines:
        cmd.extend(["-e", line])
    cmd.extend([str(text), str(title)])
    cmd.extend([str(b) for b in buttons])

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return None
    out = (res.stdout or "").strip()
    marker = "button returned:"
    if marker in out:
        chosen = out.split(marker, 1)[1].strip()
        for idx, b in enumerate(buttons):
            if chosen == str(b):
                return idx
    return None


def _linux_ask_choice(title, text, buttons, default=0, error=False):
    zenity = shutil.which("zenity")
    if zenity and len(buttons) >= 2:
        cmd = [
            zenity,
            "--question",
            "--title", str(title),
            "--text", str(text),
            "--ok-label", str(buttons[0]),
            "--cancel-label", str(buttons[1]),
            "--no-markup",
        ]
        if len(buttons) >= 3:
            cmd.extend(["--extra-button", str(buttons[2])])
        res = subprocess.run(cmd, capture_output=True, text=True)
        out = (res.stdout or "").strip()
        if len(buttons) >= 3 and out == str(buttons[2]):
            return 2
        if res.returncode == 0:
            return 0
        if res.returncode == 1:
            return 1
        return None

    kdialog = shutil.which("kdialog")
    if kdialog and len(buttons) >= 2:
        if len(buttons) >= 3:
            cmd = [
                kdialog,
                "--yesnocancel", str(text),
                "--title", str(title),
                "--yes-label", str(buttons[0]),
                "--no-label", str(buttons[1]),
                "--cancel-label", str(buttons[2]),
            ]
        else:
            cmd = [
                kdialog,
                "--yesno", str(text),
                "--title", str(title),
                "--yes-label", str(buttons[0]),
                "--no-label", str(buttons[1]),
            ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return 0
        if res.returncode == 1:
            return 1
        if res.returncode == 2 and len(buttons) >= 3:
            return 2
        return None

    notify = shutil.which("notify-send")
    if notify:
        try:
            subprocess.run([notify, str(title), str(text)], capture_output=True)
        except Exception:
            pass
    return None


def _linux_show_message(title, text, error=True):
    zenity = shutil.which("zenity")
    if zenity:
        flag = "--error" if error else "--info"
        subprocess.run([zenity, flag, "--title", str(title), "--text", str(text), "--no-markup"], capture_output=True)
        return True

    kdialog = shutil.which("kdialog")
    if kdialog:
        flag = "--error" if error else "--msgbox"
        subprocess.run([kdialog, flag, str(text), "--title", str(title)], capture_output=True)
        return True

    notify = shutil.which("notify-send")
    if notify:
        subprocess.run([notify, str(title), str(text)], capture_output=True)
        return True
    return False


def ask_choice(title, text, buttons, default=0, details=None, error=False, win_button_map_text="", prefer_qt=True):
    """Ask the user to pick one of *buttons*; returns 0-based index or None."""
    try:
        sys.stderr.write("[BadWords] {0}: {1}\n".format(title, text))
        sys.stderr.flush()
    except Exception:
        pass

    if not buttons:
        return None

    if prefer_qt:
        handled, idx = _ask_choice_qt(title, text, buttons, default=default, details=details, error=error)
        if handled:
            return idx

    try:
        if sys.platform == "win32" or os.name == "nt":
            full_text = str(text)
            if win_button_map_text:
                full_text = full_text + "\n\n" + win_button_map_text
            mb_icon = 0x10 if error else 0x30
            mb_top = 0x40000
            if len(buttons) == 1:
                mb_btns = 0x00
            elif len(buttons) == 2:
                mb_btns = 0x04  # MB_YESNO
            else:
                mb_btns = 0x03  # MB_YESNOCANCEL
            ret = _win32_message_box(title, full_text, mb_btns | mb_icon | mb_top)
            if ret == 6:  # IDYES
                return 0
            if ret == 7 and len(buttons) >= 2:  # IDNO
                return 1
            if ret == 2 and len(buttons) >= 3:  # IDCANCEL
                return 2
            if ret == 1 and len(buttons) == 1:  # IDOK
                return 0
            return None

        if sys.platform == "darwin":
            return _macos_dialog(title, text, buttons, default=default)

        return _linux_ask_choice(title, text, buttons, default=default, error=error)
    except Exception:
        return None


def show_message(title, text, error=True, details=None, prefer_qt=True):
    """Display an informational or error dialog without ever raising."""
    try:
        sys.stderr.write("[BadWords] {0}: {1}\n".format(title, text))
        sys.stderr.flush()
    except Exception:
        pass

    if prefer_qt and _show_message_qt(title, text, error=error, details=details):
        return

    try:
        if sys.platform == "win32" or os.name == "nt":
            mb_icon = 0x10 if error else 0x40
            _win32_message_box(title, text, 0x00 | mb_icon | 0x40000)
            return

        if sys.platform == "darwin":
            _macos_dialog(title, text, ["OK"], default=0)
            return

        _linux_show_message(title, text, error=error)
    except Exception:
        pass
