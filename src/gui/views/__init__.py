#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: GUI Views Package
DESCRIPTION:
Package initialization for primary stacked views.
"""

from .welcome_view import build_welcome_view
from .processing_view import build_processing_view
from .editor_view import build_editor_view

__all__ = [
    "build_welcome_view",
    "build_processing_view",
    "build_editor_view",
]
