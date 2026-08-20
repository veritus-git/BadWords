#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: __init__.py
ROLE: GUI Dialogs Package
DESCRIPTION:
Package initialization for all dialog components.
"""

from .splash_screen import SplashScreen
from .telemetry_popup import TelemetryPopup
from .msgbox import CustomMsgBox
from .update_dialog import UpdateCheckThread, UpdateNotifyDialog
from .marker_dialog import MarkerDialog
from .unsaved_changes_dialog import UnsavedChangesDialog
from .settings_dialog import SettingsDialog
from .overlay import (
    GlobalAppFilter, SidebarDragZone, MarkerDragZone, MarkerRowWidget, AnimatedDimOverlay
)

__all__ = [
    "SplashScreen",
    "TelemetryPopup",
    "CustomMsgBox",
    "UpdateCheckThread",
    "UpdateNotifyDialog",
    "MarkerDialog",
    "UnsavedChangesDialog",
    "SettingsDialog",
    "GlobalAppFilter",
    "SidebarDragZone",
    "MarkerDragZone",
    "MarkerRowWidget",
    "AnimatedDimOverlay",
]
