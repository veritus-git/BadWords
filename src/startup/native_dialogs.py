#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/native_dialogs.py
ROLE: Cross-Platform Startup Dialogs
DESCRIPTION:
Displays dark-themed choice/info/error dialogs via PySide6 when available,
or native OS dialogs (Win32 MessageBoxW, macOS osascript, Linux zenity/kdialog)
when Qt cannot be loaded. Never raises and always mirrors messages to stderr.
Must remain parseable by Python 3.8 grammar.
"""

import os
import shutil
import subprocess
import sys

from startup.i18n_lite import t

_QT_APP_REF = None


def _startup_scale_helpers():
    """Returns (S, FS_PX) scaling callables safely during early startup or fatal errors."""
    try:
        import config
        if hasattr(config, "S") and hasattr(config, "FS_PX"):
            return config.S, config.FS_PX
    except Exception:
        pass

    def _s(px):
        return max(1, int(round(float(px))))

    def _fs_px(pt):
        return max(8, int(round(float(pt) * (96.0 / 72.0))))

    return _s, _fs_px


def _build_dialog_qss():
    _S, _FS_PX = _startup_scale_helpers()
    return f"""
QDialog {{
    background-color: #161616;
    color: #e6e6e6;
}}
QLabel {{
    color: #e2e2e2;
    background: transparent;
}}
QLabel#StartupTitle {{
    color: #ffffff;
    font-size: {_FS_PX(13)}px;
    font-weight: 700;
}}
QLabel#StartupBody {{
    color: #d4d4d4;
    font-size: {_FS_PX(10)}px;
}}
QPlainTextEdit#StartupDetails {{
    background-color: #101010;
    color: #b8b8b8;
    border: 1px solid #2d2d2d;
    border-radius: {_S(6)}px;
    padding: {_S(8)}px;
    font-family: monospace;
    font-size: {_FS_PX(9)}px;
}}
QPushButton {{
    background-color: #262626;
    color: #e6e6e6;
    border: 1px solid #363636;
    border-radius: {_S(6)}px;
    padding: {_S(7)}px {_S(16)}px;
    font-size: {_FS_PX(10)}px;
    font-weight: 600;
    min-width: {_S(84)}px;
}}
QPushButton:hover {{
    background-color: #323232;
    border-color: #4a4a4a;
}}
QPushButton:pressed {{
    background-color: #202020;
}}
QPushButton#StartupPrimary {{
    background-color: #1f7a4c;
    color: #ffffff;
    border: 1px solid #28945e;
}}
QPushButton#StartupPrimary:hover {{
    background-color: #248f59;
}}
QPushButton#StartupDangerPrimary {{
    background-color: #b33939;
    color: #ffffff;
    border: 1px solid #cf4646;
}}
QPushButton#StartupDangerPrimary:hover {{
    background-color: #c94141;
}}
QPushButton#StartupDetailsBtn {{
    background-color: transparent;
    color: #9e9e9e;
    border: 1px solid #2e2e2e;
    min-width: 0px;
    padding: {_S(6)}px {_S(12)}px;
    font-size: {_FS_PX(9)}px;
}}
QPushButton#StartupDetailsBtn:hover {{
    color: #dcdcdc;
    border-color: #484848;
}}
"""


def _try_qt_widgets():
    try:
        from PySide6.QtWidgets import QApplication
        return QApplication
    except Exception:
        return None


def _ensure_qt_app(QApplication):
    global _QT_APP_REF
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv if sys.argv else ["BadWords"])
        _QT_APP_REF = app
    return app


def _apply_dark_titlebar_if_win(dialog):
    if sys.platform == "win32" or os.name == "nt":
        try:
            import ctypes
            hwnd = int(dialog.winId())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(ctypes.c_int(1)), 4
            )
        except Exception:
            pass


def _find_window_icon():
    try:
        from PySide6.QtGui import QIcon
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parent = os.path.dirname(here)
        ext = ".ico" if (sys.platform == "win32" or os.name == "nt") else ".png"
        for cand in (
            os.path.join(here, "assets", "icons", "icon_default" + ext),
            os.path.join(parent, "assets", "icons", "icon_default" + ext),
            os.path.join(here, "icons", "icon_default" + ext),
        ):
            if os.path.isfile(cand):
                return QIcon(cand)
    except Exception:
        pass
    return None


def _badge_svg(kind):
    if kind == "error":
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<circle cx="12" cy="12" r="10" fill="#c94141"/>'
            '<path d="M15 9l-6 6M9 9l6 6" stroke="#ffffff" stroke-width="2.2" '
            'stroke-linecap="round"/>'
            '</svg>'
        )
    if kind == "question":
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
            '<circle cx="12" cy="12" r="10" fill="#2374b5"/>'
            '<path d="M9.6 9.2a2.5 2.5 0 014.8.8c0 1.6-2.4 2.1-2.4 3.6" '
            'stroke="#ffffff" stroke-width="2" stroke-linecap="round" fill="none"/>'
            '<circle cx="12" cy="17" r="1.2" fill="#ffffff"/>'
            '</svg>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="12" cy="12" r="10" fill="#1f7a4c"/>'
        '<path d="M8 12.5l2.7 2.7L16.5 9.5" stroke="#ffffff" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        '</svg>'
    )


def _render_badge_pixmap(kind, size=34):
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(QByteArray(_badge_svg(kind).encode("utf-8")))
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(2.0)
    return pix


def build_dark_qt_dialog(title, text, buttons, default=0, details=None, kind="error", src_dir=None, lang=None):
    """Build a dark-themed Qt startup dialog matching BadWords aesthetics."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QPlainTextEdit,
        QPushButton,
        QVBoxLayout,
    )

    _S, _FS_PX = _startup_scale_helpers()
    dlg = QDialog()
    dlg.setWindowTitle(str(title))
    dlg.setStyleSheet(_build_dialog_qss())
    dlg.setMinimumWidth(_S(460))
    dlg.setMaximumWidth(_S(580))
    _apply_dark_titlebar_if_win(dlg)

    win_icon = _find_window_icon()
    if win_icon is not None:
        dlg.setWindowIcon(win_icon)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(_S(22), _S(20), _S(22), _S(18))
    root.setSpacing(_S(14))

    top_row = QHBoxLayout()
    top_row.setSpacing(_S(14))

    icon_lbl = QLabel(dlg)
    icon_lbl.setFixedSize(_S(36), _S(36))
    icon_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
    try:
        icon_lbl.setPixmap(_render_badge_pixmap(kind, size=_S(34)))
    except Exception:
        pass
    top_row.addWidget(icon_lbl, 0, Qt.AlignTop)

    text_col = QVBoxLayout()
    text_col.setSpacing(_S(8))

    title_lbl = QLabel(str(title), dlg)
    title_lbl.setObjectName("StartupTitle")
    title_lbl.setWordWrap(True)
    text_col.addWidget(title_lbl)

    body_lbl = QLabel(str(text), dlg)
    body_lbl.setObjectName("StartupBody")
    body_lbl.setWordWrap(True)
    body_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
    text_col.addWidget(body_lbl)

    top_row.addLayout(text_col, 1)
    root.addLayout(top_row)

    details_edit = None
    details_btn = None
    if details:
        show_lbl = t("startup_btn_show_details", src_dir=src_dir, lang=lang)
        hide_lbl = t("startup_btn_hide_details", src_dir=src_dir, lang=lang)

        details_edit = QPlainTextEdit(str(details), dlg)
        details_edit.setObjectName("StartupDetails")
        details_edit.setReadOnly(True)
        details_edit.setMaximumHeight(_S(160))
        details_edit.setVisible(False)
        root.addWidget(details_edit)

        details_btn = QPushButton(show_lbl, dlg)
        details_btn.setObjectName("StartupDetailsBtn")
        details_btn.setCursor(Qt.PointingHandCursor)

        def _toggle_details():
            now_vis = not details_edit.isVisible()
            details_edit.setVisible(now_vis)
            details_btn.setText(hide_lbl if now_vis else show_lbl)
            dlg.adjustSize()

        details_btn.clicked.connect(_toggle_details)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(_S(10))
    if details_btn is not None:
        btn_row.addWidget(details_btn)
    btn_row.addStretch(1)

    state = {"chosen": None}
    for idx, label in enumerate(buttons):
        btn = QPushButton(str(label), dlg)
        btn.setCursor(Qt.PointingHandCursor)
        if idx == 0 and kind == "question":
            btn.setObjectName("StartupPrimary")
        elif idx == 0 and kind == "error" and len(buttons) > 1:
            btn.setObjectName("StartupDangerPrimary")
        if idx == default:
            btn.setDefault(True)
            btn.setAutoDefault(True)

        def _make_handler(button_idx):
            def _on_click():
                state["chosen"] = button_idx
                dlg.accept()
            return _on_click

        btn.clicked.connect(_make_handler(idx))
        btn_row.addWidget(btn)

    root.addLayout(btn_row)
    dlg.adjustSize()
    return dlg, state


def _ask_choice_qt(title, text, buttons, default=0, details=None, error=False, src_dir=None):
    QApplication = _try_qt_widgets()
    if QApplication is None:
        return False, None
    try:
        _ensure_qt_app(QApplication)
        kind = "error" if error else "question"
        dlg, state = build_dark_qt_dialog(
            title, text, buttons, default=default, details=details, kind=kind, src_dir=src_dir
        )
        dlg.exec()
        return True, state["chosen"]
    except Exception:
        return False, None


def _show_message_qt(title, text, error=True, details=None, src_dir=None):
    QApplication = _try_qt_widgets()
    if QApplication is None:
        return False
    try:
        _ensure_qt_app(QApplication)
        kind = "error" if error else "info"
        dlg, _ = build_dark_qt_dialog(
            title, text, ["OK"], default=0, details=details, kind=kind, src_dir=src_dir
        )
        dlg.exec()
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


def ask_choice(title, text, buttons, default=0, details=None, error=False, win_button_map_text="", prefer_qt=True, src_dir=None):
    """Ask the user to pick one of *buttons*; returns 0-based index or None."""
    try:
        sys.stderr.write("[BadWords] {0}: {1}\n".format(title, text))
        sys.stderr.flush()
    except Exception:
        pass

    if not buttons:
        return None

    if prefer_qt:
        handled, idx = _ask_choice_qt(
            title, text, buttons, default=default, details=details, error=error, src_dir=src_dir
        )
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


def show_message(title, text, error=True, details=None, prefer_qt=True, src_dir=None):
    """Display an informational or error dialog without ever raising."""
    try:
        sys.stderr.write("[BadWords] {0}: {1}\n".format(title, text))
        sys.stderr.flush()
    except Exception:
        pass

    if prefer_qt and _show_message_qt(title, text, error=error, details=details, src_dir=src_dir):
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
