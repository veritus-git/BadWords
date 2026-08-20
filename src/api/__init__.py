#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: api/__init__.py
DESCRIPTION:
    Package initializer for the api module.
    Re-exports ResolveHandler for backward compatibility
    so that ``import api; api.ResolveHandler(...)`` keeps working.
"""

from .resolve_handler import ResolveHandler

__all__ = ["ResolveHandler"]
