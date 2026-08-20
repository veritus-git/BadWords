#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: engine/__init__.py
ROLE: Module
DESCRIPTION:
Package initializer for the engine module.
"""

from .audio_engine import AudioEngine

__all__ = ["AudioEngine"]
