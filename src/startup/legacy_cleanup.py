#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/legacy_cleanup.py
ROLE: Legacy v3 File Cleaner
DESCRIPTION:
Removes leftover v3 root files and stale bytecode entries that would shadow
BadWords 4.x packages.
"""

import os

LEGACY_FILES = (
    "gui.py",
    "config.py",
    "transcribe.py",
    "timeline.py",
    "interface.py",
    "silence.py",
    "audio.py",
    "whisper_net.py",
    "BadWords_Launcher.py",
    "Badwords.py",
    "BadWords (Windows).py",
    "BadWords (Linux).py",
    "BadWords (Mac).py",
    "BadWords (macOS).py",
)


def run(src_dir):
    """Remove legacy v3 root scripts and their stale __pycache__ files."""
    cur_dir = os.path.abspath(src_dir)
    for lf in LEGACY_FILES:
        p = os.path.join(cur_dir, lf)
        if os.path.isfile(p):
            try:
                os.remove(p)
            except Exception:
                pass

    pycache = os.path.join(cur_dir, "__pycache__")
    if os.path.isdir(pycache):
        prefixes = tuple(x.replace(".py", "") for x in LEGACY_FILES)
        try:
            for f in os.listdir(pycache):
                if any(f.startswith(pref) for pref in prefixes):
                    try:
                        os.remove(os.path.join(pycache, f))
                    except Exception:
                        pass
        except Exception:
            pass
