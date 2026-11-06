#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: dialogs.py
ROLE: GUI Component (Facade)
DESCRIPTION:
Forwarding facade to gui.dialogs package for full backward compatibility.
"""

from gui.dialogs import (
    SplashScreen,
    TelemetryPopup,
    CustomMsgBox,
    UpdateCheckThread,
    UpdateNotifyDialog,
    MarkerDialog,
    UnsavedChangesDialog,
    SettingsDialog,
    GlobalAppFilter,
    SidebarDragZone,
    MarkerDragZone,
    MarkerRowWidget,
    AnimatedDimOverlay,
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
