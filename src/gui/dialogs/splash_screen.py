#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: splash_screen.py
ROLE: GUI Dialog (Re-export Facade)
DESCRIPTION:
Re-exports BootSplash as SplashScreen so existing callers keep working without
duplicating splash screen code or pulling heavy GUI modules during boot.
"""

from startup.boot_splash import (
    BootSplash as SplashScreen,
    SplashInnerFrame,
    find_splash_path as _find_splash_path,
)

__all__ = ["SplashScreen", "SplashInnerFrame", "_find_splash_path"]
