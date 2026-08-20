#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: GUI Panels Package
DESCRIPTION:
Package initialization for sidebar activity panels.
"""

from .script_panel import build_script_panel, wrap_activity_panel
from .silence_panel import build_silence_panel
from .fillers_panel import build_fillers_panel
from .main_workspace_panel import build_main_workspace_panel
from .assembly_panel import build_assembly_panel

__all__ = [
    "build_script_panel",
    "build_silence_panel",
    "build_fillers_panel",
    "build_main_workspace_panel",
    "build_assembly_panel",
    "wrap_activity_panel",
]
