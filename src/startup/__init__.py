#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/__init__.py
ROLE: Startup Guard Package
DESCRIPTION:
Lightweight, stdlib-only startup guards, environment isolation, crash reporting,
consent-based self-healing, and instant boot splash screen.
All guard modules stay compatible with Python 3.8 syntax so version-mismatch
dialogs can still render on older host interpreters.
"""

EXIT_FATAL_REPORTED = 3
RELEASES_URL = "https://github.com/veritus-git/BadWords/releases/latest"
SUPPORTED_MIN = (3, 10)
SUPPORTED_MAX_EXCL = (3, 13)
