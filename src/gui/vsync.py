#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: vsync.py
ROLE: GUI VSync & High-Refresh Rate Engine
DESCRIPTION:
Synchronizes Qt internal animation pacing (QUnifiedTimer) and UI widget timers
with the active monitor's refresh rate (30, 60, 75, 120, 144, 240Hz+).
Includes resource guardrails for ultra-high refresh rate displays (>144Hz).
"""

import sys
import os
import ctypes
import platform
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen, QGuiApplication
import osdoc

# Current active interval in milliseconds (default 16ms = ~60 FPS)
_CURRENT_INTERVAL_MS = 16
_UNIFIED_TIMER_AVAILABLE = False
_SET_INTERVAL_FUNC = None
_TIMER_INSTANCE = None


def _find_qtcore_library() -> str | None:
    """Locates the active Qt6Core shared library for PySide6 across platforms."""
    try:
        import PySide6
        base_dir = os.path.dirname(PySide6.__file__)
        sys_plat = platform.system()

        for root, _, files in os.walk(base_dir):
            for f in files:
                if sys_plat == "Windows":
                    if f.lower() == "qt6core.dll":
                        return os.path.join(root, f)
                elif sys_plat == "Darwin":
                    if f.startswith("libQt6Core") and (f.endswith(".dylib") or ".dylib." in f):
                        return os.path.join(root, f)
                else:
                    if f.startswith("libQt6Core.so"):
                        return os.path.join(root, f)
    except Exception as e:
        osdoc.log_error(f"vsync: failed locating Qt6Core library: {e}")
    return None


def _init_unified_timer_hooks():
    """Binds to QUnifiedTimer in QtCore via ctypes."""
    global _UNIFIED_TIMER_AVAILABLE, _SET_INTERVAL_FUNC, _TIMER_INSTANCE
    if _UNIFIED_TIMER_AVAILABLE:
        return

    lib_path = _find_qtcore_library()
    if not lib_path:
        osdoc.log_info("vsync: Qt6Core library path not found, using software timer fallback.")
        return

    try:
        lib = ctypes.CDLL(lib_path)
        sys_plat = platform.system()

        inst_func = None
        set_func = None

        if sys_plat in ("Linux", "Darwin"):
            # Itanium C++ ABI mangling (GCC / Clang)
            sym_inst = "_ZN13QUnifiedTimer8instanceEv"
            sym_set = "_ZN13QUnifiedTimer17setTimingIntervalEi"
            if hasattr(lib, sym_inst) and hasattr(lib, sym_set):
                inst_func = getattr(lib, sym_inst)
                set_func = getattr(lib, sym_set)
        elif sys_plat == "Windows":
            # MSVC C++ ABI mangling
            # 64-bit MSVC symbols
            candidates_inst = [
                "?instance@QUnifiedTimer@@SAPEAV1@XZ",
                "?instance@QUnifiedTimer@@SAPEAV1@_N@Z",
                "?instance@QUnifiedTimer@@SAPAV1@XZ"
            ]
            candidates_set = [
                "?setTimingInterval@QUnifiedTimer@@QEAAXH@Z",
                "?setTimingInterval@QUnifiedTimer@@QAEXH@Z"
            ]
            for sym in candidates_inst:
                if hasattr(lib, sym):
                    inst_func = getattr(lib, sym)
                    break
            for sym in candidates_set:
                if hasattr(lib, sym):
                    set_func = getattr(lib, sym)
                    break

        if inst_func and set_func:
            inst_func.restype = ctypes.c_void_p
            set_func.argtypes = [ctypes.c_void_p, ctypes.c_int]

            _TIMER_INSTANCE = inst_func()
            _SET_INTERVAL_FUNC = set_func
            _UNIFIED_TIMER_AVAILABLE = True
            osdoc.log_info(f"vsync: QUnifiedTimer hook bound successfully (handle: {hex(_TIMER_INSTANCE) if _TIMER_INSTANCE else 'null'}).")
        else:
            osdoc.log_info("vsync: QUnifiedTimer symbols not found in QtCore, using fallback timing.")
    except Exception as e:
        osdoc.log_error(f"vsync: failed binding QUnifiedTimer hooks: {e}")


def calculate_target_interval(refresh_rate: float) -> int:
    """
    Computes optimal animation frame interval in ms for any refresh rate.
    Includes smart GPU/CPU resource guardrail for ultra-high refresh displays (>144Hz).
    """
    if refresh_rate <= 0:
        return 16  # fallback to 60Hz

    # Resource Guardrail: For displays > 144Hz (e.g. 240Hz, 360Hz), cap animation
    # tick interval to 7ms (~143 FPS) to prevent excessive CPU/GPU usage on 2D desktop UI.
    effective_rate = min(refresh_rate, 144.0)

    interval = round(1000.0 / effective_rate)
    # Clamp interval between 7ms (~143 FPS) and 33ms (~30 FPS)
    return max(7, min(33, interval))


def get_refresh_interval_ms() -> int:
    """Returns the current VSync animation tick interval in milliseconds."""
    return _CURRENT_INTERVAL_MS


def apply_screen_refresh_rate(screen: QScreen | None):
    """Applies the refresh rate of the specified screen to the application."""
    global _CURRENT_INTERVAL_MS
    if not screen:
        app = QGuiApplication.instance()
        screen = app.primaryScreen() if app else None

    rate = screen.refreshRate() if screen else 60.0
    target_interval = calculate_target_interval(rate)

    if target_interval != _CURRENT_INTERVAL_MS or not _UNIFIED_TIMER_AVAILABLE:
        _CURRENT_INTERVAL_MS = target_interval
        if _UNIFIED_TIMER_AVAILABLE and _SET_INTERVAL_FUNC and _TIMER_INSTANCE:
            try:
                _SET_INTERVAL_FUNC(_TIMER_INSTANCE, int(_CURRENT_INTERVAL_MS))
            except Exception as e:
                osdoc.log_error(f"vsync: failed updating timing interval: {e}")

        osdoc.log_info(
            f"vsync: Display '{screen.name() if screen else 'unknown'}' @ {rate:.1f}Hz -> "
            f"Paced at {_CURRENT_INTERVAL_MS}ms (~{round(1000.0 / _CURRENT_INTERVAL_MS)} FPS)"
        )


def init_high_refresh_sync(app: QApplication):
    """
    Initializes dynamic VSync synchronization for the whole Qt application.
    Listens to screen changes and monitor refresh rate changes in real time.
    """
    _init_unified_timer_hooks()

    # Initial apply on primary screen
    primary = app.primaryScreen()
    if primary:
        apply_screen_refresh_rate(primary)
        try:
            primary.refreshRateChanged.connect(lambda _: apply_screen_refresh_rate(primary))
        except Exception:
            pass

    # Monitor all connected screens
    def _on_screen_added(s: QScreen):
        try:
            s.refreshRateChanged.connect(lambda _: apply_screen_refresh_rate(s))
        except Exception:
            pass

    try:
        app.screenAdded.connect(_on_screen_added)
        for s in app.screens():
            _on_screen_added(s)
    except Exception:
        pass


def track_window_screen(window):
    """Hooks a top-level window so moving it across monitors updates VSync interval."""
    try:
        handle = window.windowHandle() if hasattr(window, 'windowHandle') else None
        if handle:
            handle.screenChanged.connect(apply_screen_refresh_rate)
            apply_screen_refresh_rate(handle.screen())
    except Exception:
        pass
