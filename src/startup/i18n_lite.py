#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/i18n_lite.py
ROLE: Lightweight Startup Localization
DESCRIPTION:
Stdlib-only translation lookup for early startup dialogs before config/GUI load.
Includes a built-in English fallback dictionary so fatal error messages still
render coherently even if src/i18n JSON files are missing or damaged.
"""

import json
import os

_BUILTIN_EN = {
    "startup_err_title": "BadWords - Startup Error",
    "startup_err_python_version": (
        "BadWords 4.x requires Python 3.10 - 3.12.\n"
        "Detected: Python {ver} ({exe})\n\n"
        "Please download and run the official BadWords Setup Installer, "
        "which installs the compatible Python environment automatically:\n{url}"
    ),
    "startup_err_env_missing": (
        "BadWords could not find its isolated Python environment or required components.\n\n"
        "Please run the official BadWords Setup Installer to repair the installation:\n{url}"
    ),
    "startup_err_generic": (
        "An unexpected error occurred during startup:\n\n{error}\n\n"
        "Diagnostic log file:\n{log}"
    ),
    "startup_err_qt": (
        "Failed to initialize the application graphics interface (PySide6/Qt):\n\n{error}\n\n"
        "Diagnostic log file:\n{log}"
    ),
    "startup_err_qt_win_hint": (
        "On a fresh Windows installation, installing Microsoft Visual C++ 2015-2022 "
        "Redistributable (x64) may also be required."
    ),
    "startup_report_consent": (
        "Optional: send an anonymous diagnostic report to the developer?\n"
        "What will be sent: the error description, OS and Python version, and the BadWords log file "
        "(no media files or projects are included)."
    ),
    "startup_report_send": "Send Report",
    "startup_report_close": "Close",
    "startup_report_sent": "Thank you. The diagnostic report has been sent to the developer.",
    "startup_report_failed": (
        "Could not send the diagnostic report automatically.\n"
        "You can attach the log file manually:\n{log}"
    ),
    "startup_win_button_map": "Buttons: Yes = {yes}, No = {no}{cancel}",
    "heal_title": "BadWords - Component Repair",
    "heal_prompt": (
        "Some required BadWords components are missing (for example after an update from 3.x to 4.x):\n"
        "{packages}\n\n"
        "Estimated download size: {size}.\n"
        "BadWords can download and install them now into its own private environment "
        "(your system Python will not be modified). An internet connection is required."
    ),
    "heal_btn_repair": "Repair Now",
    "heal_btn_skip": "Continue Without Repair",
    "heal_btn_close": "Close",
    "heal_progress": "Downloading and repairing BadWords components inside private environment...",
    "heal_done": "Components repaired successfully. Restarting BadWords...",
    "heal_done_resolve": (
        "Components repaired successfully.\n"
        "Please launch BadWords again from DaVinci Resolve (Workspace -> Scripts -> BadWords)."
    ),
    "heal_failed": (
        "Component repair failed:\n\n{error}\n\n"
        "Please run the official BadWords Setup Installer to repair the installation."
    ),
    "heal_offline": (
        "Cannot repair missing components because no internet connection was detected.\n"
        "Please connect to the internet and try again, or use the official Setup Installer."
    ),
}

_CACHE = {}


def _default_src_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def detect_language(src_dir=None):
    """Read gui_lang from settings.json without importing config or osdoc."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    parent = os.path.dirname(base)
    candidates = [
        os.path.join(parent, ".dev_workspace", "settings.json"),
        os.path.join(base, "settings.json"),
        os.path.join(parent, "settings.json"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                lang = str(data.get("gui_lang", "")).strip().lower()
                if lang:
                    return lang
            except Exception:
                pass
    return "en"


def _load_lang_dict(lang, src_dir):
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    cache_key = (base, lang)
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    path = os.path.join(base, "i18n", "{0}.json".format(lang))
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                data = loaded
        except Exception:
            data = {}
    _CACHE[cache_key] = data
    return data


def t(key, src_dir=None, lang=None, **kwargs):
    """Return translated startup text for *key*, falling back cleanly to English."""
    base = os.path.abspath(src_dir) if src_dir else _default_src_dir()
    chosen_lang = lang or detect_language(base)

    lang_dict = _load_lang_dict(chosen_lang, base)
    en_dict = _load_lang_dict("en", base) if chosen_lang != "en" else lang_dict

    text = lang_dict.get(key)
    if text is None:
        text = en_dict.get(key)
    if text is None:
        text = _BUILTIN_EN.get(key, key)

    if kwargs and isinstance(text, str):
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
