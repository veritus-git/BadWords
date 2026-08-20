#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: update_dialog.py
ROLE: GUI Dialog & Background Worker
DESCRIPTION:
Update checker worker thread and notification dialog for new releases.
"""

import os
import sys
import threading
import subprocess
import tempfile
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect
)
from PySide6.QtGui import QColor

import config
from gui.components.mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.utils import _txt, _center_on_screen


class UpdateCheckThread(QThread):
    """
    Stdlib-only background worker that checks GitHub (with GitLab fallback)
    for a newer release of BadWords.

    Signals
    -------
    update_available(str, str, str)
        Emitted when a newer version is detected.
        Args: (latest_version, github_release_url, gitlab_release_url)
    """
    update_available = Signal(str, str, str)

    _cached_result: tuple | None = None
    _checked: bool = False
    _lock = None

    _GH_API  = "https://api.github.com/repos/veritus-git/BadWords/releases/latest"
    _GL_API  = "https://gitlab.com/api/v4/projects/78101072/releases"
    _GH_PAGE = "https://github.com/veritus-git/BadWords/releases/latest"
    _GL_PAGE = "https://gitlab.com/badwords/BadWords/-/releases"

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    @staticmethod
    def _parse_version(tag: str):
        tag = tag.strip().lstrip('v').lstrip('V')
        try:
            return tuple(int(x) for x in tag.split('.'))
        except ValueError:
            return (0,)

    @staticmethod
    def _fetch_json(url: str, timeout: int = 8):
        import urllib.request, json, ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers={"User-Agent": "BadWords-UpdateCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))

    def run(self):
        from osdoc import log_info, log_error

        if UpdateCheckThread._lock is None:
            UpdateCheckThread._lock = threading.Lock()

        current_tuple = self._parse_version(self._current)

        if UpdateCheckThread._checked:
            cached = UpdateCheckThread._cached_result
            if cached:
                latest_display, gh_page, gl_page = cached
                if self._parse_version(latest_display) > current_tuple:
                    log_info(f"[UpdateCheck] (cached) New version available: {latest_display}")
                    self.update_available.emit(latest_display, gh_page, gl_page)
                else:
                    log_info(f"[UpdateCheck] (cached) Already up-to-date ({self._current}).")
            else:
                log_info("[UpdateCheck] (cached) No version info available.")
            return

        with UpdateCheckThread._lock:
            if UpdateCheckThread._checked:
                cached = UpdateCheckThread._cached_result
                if cached:
                    latest_display, gh_page, gl_page = cached
                    if self._parse_version(latest_display) > current_tuple:
                        log_info(f"[UpdateCheck] (cached/lock) New version available: {latest_display}")
                        self.update_available.emit(latest_display, gh_page, gl_page)
                    else:
                        log_info(f"[UpdateCheck] (cached/lock) Already up-to-date ({self._current}).")
                return

            latest_tag = None
            try:
                data = self._fetch_json(self._GH_API)
                latest_tag = data.get("tag_name", "").strip()
                log_info(f"[UpdateCheck] GitHub latest tag: {latest_tag!r}")
            except Exception as e:
                log_error(f"[UpdateCheck] GitHub API failed: {e}")

            if not latest_tag:
                try:
                    data = self._fetch_json(self._GL_API)
                    if isinstance(data, list) and data:
                        latest_tag = data[0].get("tag_name", "").strip()
                    elif isinstance(data, dict):
                        latest_tag = data.get("tag_name", "").strip()
                    if latest_tag:
                        log_info(f"[UpdateCheck] GitLab latest tag: {latest_tag!r}")
                except Exception as e:
                    log_error(f"[UpdateCheck] GitLab API failed: {e}")

            UpdateCheckThread._checked = True

            if not latest_tag:
                log_error("[UpdateCheck] Could not retrieve latest version from any source.")
                UpdateCheckThread._cached_result = None
                return

            latest_tuple   = self._parse_version(latest_tag)
            latest_display = latest_tag.lstrip('vV')

            if latest_tuple > current_tuple:
                log_info(f"[UpdateCheck] New version available: {latest_display} (current: {self._current})")
                UpdateCheckThread._cached_result = (latest_display, self._GH_PAGE, self._GL_PAGE)
                self.update_available.emit(latest_display, self._GH_PAGE, self._GL_PAGE)
            else:
                log_info(f"[UpdateCheck] Already up-to-date ({self._current}).")
                UpdateCheckThread._cached_result = None


class UpdateNotifyDialog(FramelessWindowMixin, _BaseDialog):
    """Custom frameless update-notification dialog."""
    _UPDATE_SCRIPT    = 'https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/updater.py'
    _UPDATE_SCRIPT_GL = 'https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/updater.py'

    _update_done = Signal(bool, str)

    def __init__(self, parent, lang: str, current_ver: str, latest_ver: str,
                 gh_url: str, gl_url: str, is_win: bool, is_mac: bool,
                 install_dir: str):
        super().__init__(parent)
        self._lang    = lang
        self._engine  = getattr(parent, 'engine', None)
        self._is_mac  = is_mac
        self._is_win  = is_win
        self._gh_url  = gh_url
        self._install_dir = install_dir

        self._update_done.connect(self._on_update_done)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #111;
                border-radius: 8px;
            }}
            QLabel {{ color: {config.FG_COLOR}; background: transparent; }}
            QLabel#lbl_title  {{ font-size: 15pt; font-weight: bold; }}
            QLabel#lbl_sub    {{ font-size: 10pt; color: #999; }}
            QLabel#lbl_status {{ font-size: 10pt; color: #888; font-style: italic; }}
            #ver_frame {{
                background-color: #101010;
                border: 1px solid #1e1e1e;
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 7px 20px;
                border-radius: 5px;
                min-width: 90px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover    {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton:disabled {{ color: #444; background-color: #181818; }}
            QPushButton#btn_primary           {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_primary:hover     {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_primary:disabled  {{ background-color: #1a2e1a; color: #3a5a3a; }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        outer.addWidget(self.inner_frame)

        root = QVBoxLayout(self.inner_frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root.addWidget(self._tb)

        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 24)
        body.setSpacing(12)
        root.addLayout(body)

        lbl_title = QLabel(_txt(lang, 'update_notify_title'))
        lbl_title.setObjectName("lbl_title")
        body.addWidget(lbl_title)

        lbl_sub = QLabel(_txt(lang, 'update_notify_sub'))
        lbl_sub.setObjectName("lbl_sub")
        body.addWidget(lbl_sub)

        body.addSpacing(6)

        ver_frame = QFrame()
        ver_frame.setObjectName("ver_frame")
        ver_layout = QHBoxLayout(ver_frame)
        ver_layout.setContentsMargins(24, 16, 24, 16)
        ver_layout.setSpacing(0)

        def _ver_col(label_txt, ver_txt, ver_color):
            col = QVBoxLayout()
            col.setSpacing(3)
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color: #555; font-size: 9pt; letter-spacing: 1px;")
            val = QLabel(ver_txt)
            val.setStyleSheet(f"color: {ver_color}; font-size: 20pt; font-weight: bold;")
            col.addWidget(lbl)
            col.addWidget(val)
            return col

        body.addWidget(ver_frame)
        ver_layout.addLayout(_ver_col(
            _txt(lang, 'update_notify_lbl_current'), current_ver, "#555"
        ))

        lbl_arrow = QLabel("→")
        lbl_arrow.setStyleSheet("color: #333; font-size: 24pt; padding: 0 24px 0 20px;")
        lbl_arrow.setAlignment(Qt.AlignCenter)
        ver_layout.addWidget(lbl_arrow)

        ver_layout.addLayout(_ver_col(
            _txt(lang, 'update_notify_lbl_latest'), latest_ver, "#39ff7a"
        ))
        ver_layout.addStretch()

        self._lbl_status = QLabel("")
        self._lbl_status.setObjectName("lbl_status")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.hide()
        body.addWidget(self._lbl_status)

        body.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_dismiss = QPushButton(_txt(lang, 'update_notify_btn_dismiss'))
        self._btn_dismiss.setCursor(Qt.PointingHandCursor)
        self._btn_dismiss.clicked.connect(self._on_dismiss)
        btn_row.addWidget(self._btn_dismiss)

        btn_row.addSpacing(8)

        self._btn_primary = QPushButton(_txt(lang, 'update_notify_btn_update'))
        self._btn_primary.setObjectName("btn_primary")
        self._btn_primary.setCursor(Qt.PointingHandCursor)
        self._btn_primary.clicked.connect(self._on_update_now)

        btn_row.addWidget(self._btn_primary)
        body.addLayout(btn_row)

        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    def _on_update_now(self):
        self._btn_primary.setEnabled(False)
        self._btn_primary.setText(_txt(self._lang, 'update_notify_updating'))
        self._btn_dismiss.setEnabled(False)
        self._lbl_status.setText(_txt(self._lang, 'update_notify_wait'))
        self._lbl_status.setStyleSheet("color: #888; font-style: italic; font-size: 10pt;")
        self._lbl_status.show()
        self.adjustSize()

        url_primary  = self._UPDATE_SCRIPT
        url_fallback = self._UPDATE_SCRIPT_GL

        def _worker():
            tmp_script = None
            try:
                import urllib.request, ssl, certifi
                ctx = ssl.create_default_context(cafile=certifi.where())

                script_content = None
                for url in (url_primary, url_fallback):
                    try:
                        with urllib.request.urlopen(url, timeout=20, context=ctx) as resp:
                            script_content = resp.read()
                        break
                    except Exception:
                        continue

                if not script_content:
                    self._update_done.emit(False, "Could not download update script from GitHub or GitLab.")
                    return

                fd, tmp_script = tempfile.mkstemp(suffix='.py', prefix='bw_update_')
                with os.fdopen(fd, 'wb') as f:
                    f.write(script_content)

                cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

                if self._is_win:
                    venv_py = os.path.join(self._install_dir, 'venv', 'Scripts', 'python.exe')
                else:
                    venv_py = os.path.join(self._install_dir, 'venv', 'bin', 'python3')

                if not os.path.isfile(venv_py):
                    venv_py = sys.executable

                result = subprocess.run(
                    [venv_py, tmp_script, '--install-dir', self._install_dir],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8', errors='replace',
                    timeout=600,
                    creationflags=cf,
                )

                from osdoc import log_info
                for line in (result.stdout or '').splitlines():
                    log_info(f'[Updater] {line}')

                if result.returncode == 0:
                    self._update_done.emit(True, "")
                else:
                    self._update_done.emit(False, f"Exit code {result.returncode}")

            except subprocess.TimeoutExpired:
                self._update_done.emit(False, "Timeout (>10 min) — update may still be running.")
            except Exception as e:
                self._update_done.emit(False, str(e))
            finally:
                if tmp_script and os.path.exists(tmp_script):
                    try: os.remove(tmp_script)
                    except Exception: pass

        threading.Thread(target=_worker, daemon=True).start()

    def _on_update_done(self, success: bool, error_msg: str):
        from osdoc import log_info, log_error
        if success:
            log_info("[UpdateCheck] Auto-update completed successfully.")
            self._lbl_status.setText(_txt(self._lang, 'update_notify_success'))
            self._lbl_status.setStyleSheet("color: #39ff7a; font-size: 10pt; font-style: normal;")
            self._btn_primary.hide()
            self._btn_dismiss.setText(_txt(self._lang, 'btn_close'))
            self._btn_dismiss.clicked.disconnect()
            self._btn_dismiss.clicked.connect(self.accept)
            self._btn_dismiss.setEnabled(True)
        else:
            log_error(f"[UpdateCheck] Auto-update failed: {error_msg}")
            self._lbl_status.setText(_txt(self._lang, 'update_notify_failed'))
            self._lbl_status.setStyleSheet("color: #ed4245; font-size: 10pt; font-style: normal;")
            self._btn_primary.setText(_txt(self._lang, 'update_notify_win_btn'))
            self._btn_primary.clicked.disconnect()
            self._btn_primary.clicked.connect(lambda: self._open_url(self._gh_url))
            self._btn_primary.setEnabled(True)
            self._btn_dismiss.setEnabled(True)
        self.adjustSize()

    def _on_dismiss(self):
        self.reject()

    def closeEvent(self, event):
        event.accept()

    @staticmethod
    def _open_url(url: str):
        import webbrowser
        webbrowser.open(url)
