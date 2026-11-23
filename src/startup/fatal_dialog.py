#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/fatal_dialog.py
ROLE: Fatal Startup Error Presentation
DESCRIPTION:
Unified cross-platform fatal startup error dialog with clear diagnostics,
log file path, and optional consent-based crash report submission.
"""

import os
import sys

from startup import RELEASES_URL
from startup.crash_report import primary_log_hint, send_report
from startup.i18n_lite import t
from startup.native_dialogs import ask_choice, show_message


def _default_src_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_dev_checkout(src_dir):
    if os.environ.get("BADWORDS_FORCE_INSTALLED") == "1":
        return False
    if os.environ.get("BADWORDS_DEV") == "1":
        return True
    base = os.path.abspath(src_dir)
    parent = os.path.dirname(base)
    return os.path.exists(os.path.join(base, ".git")) or os.path.exists(os.path.join(parent, ".git"))


def show_fatal(kind, error_text="", tb_text="", src_dir=None, allow_report=True):
    """Show a clear localized fatal startup error dialog and optionally send a report."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    title = t("startup_err_title", src_dir=base)
    log_path = primary_log_hint(base)
    ver = "{0}.{1}".format(sys.version_info[0], sys.version_info[1])

    if kind == "python_version":
        msg = t(
            "startup_err_python_version",
            src_dir=base,
            ver=ver,
            exe=sys.executable or "python",
            url=RELEASES_URL,
        )
    elif kind == "env_missing":
        msg = t("startup_err_env_missing", src_dir=base, url=RELEASES_URL)
        if error_text:
            msg = "{0}\n\n{1}\n\n{2}".format(msg, error_text, log_path)
    elif kind == "qt":
        msg = t(
            "startup_err_qt",
            src_dir=base,
            error=error_text or "Qt initialization failed",
            log=log_path,
        )
        if sys.platform == "win32" or os.name == "nt":
            msg = "{0}\n\n{1}".format(msg, t("startup_err_qt_win_hint", src_dir=base))
    elif kind == "heal_failed":
        msg = t(
            "heal_failed",
            src_dir=base,
            error=error_text or "Unknown error",
        )
        msg = "{0}\n\n{1}".format(msg, log_path)
    else:
        msg = t(
            "startup_err_generic",
            src_dir=base,
            error=error_text or "Unknown error",
            log=log_path,
        )

    try:
        sys.stderr.write("[BadWords] FATAL ({0}): {1}\n".format(kind, error_text or msg))
        sys.stderr.flush()
    except Exception:
        pass

    use_qt = (kind != "python_version")
    can_offer_report = bool(allow_report and not _is_dev_checkout(base))
    if not can_offer_report:
        show_message(title, msg, error=True, details=tb_text or None, prefer_qt=use_qt)
        return

    consent_text = t("startup_report_consent", src_dir=base)
    full_msg = "{0}\n\n{1}".format(msg, consent_text)
    send_label = t("startup_report_send", src_dir=base)
    close_label = t("startup_report_close", src_dir=base)
    win_map = t(
        "startup_win_button_map",
        src_dir=base,
        yes=send_label,
        no=close_label,
        cancel="",
    )

    choice = ask_choice(
        title,
        full_msg,
        [send_label, close_label],
        default=1,
        details=tb_text or None,
        error=True,
        win_button_map_text=win_map,
        prefer_qt=use_qt,
    )
    if choice == 0:
        ok = send_report(error_text or msg, tb_text=tb_text, src_dir=base)
        if ok:
            show_message(title, t("startup_report_sent", src_dir=base), error=False, prefer_qt=use_qt)
        else:
            show_message(
                title,
                t("startup_report_failed", src_dir=base, log=log_path),
                error=True,
                prefer_qt=use_qt,
            )
