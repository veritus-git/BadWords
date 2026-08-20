#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: engine/__init__.py
DESCRIPTION:
    Package initializer for the engine module.
    Re-exports AudioEngine and FakeTTY for backward compatibility
    so that ``import engine; engine.AudioEngine(...)`` keeps working.
"""

from .audio_engine import AudioEngine

__all__ = ["AudioEngine"]
