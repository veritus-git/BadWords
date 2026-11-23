#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: vsync.py
ROLE: GUI VSync & High-Refresh Rate Engine
DESCRIPTION:
Synchronizes Qt internal animation pacing (QUnifiedTimer) and subscribed UI widget timers
with the active window monitor's refresh rate (30, 60, 75, 120, 144, 240Hz+).
Includes resource guardrails for ultra-high refresh rate displays (>144Hz).
"""

import os
import ctypes
import platform
import weakref
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen, QGuiApplication
import osdoc

# Current active interval in milliseconds (default 16ms = ~60 FPS)
_CURRENT_INTERVAL_MS = 16
_UNIFIED_TIMER_AVAILABLE = False
_SET_INTERVAL_FUNC = None
_TIMER_INSTANCE = None
_ACTIVE_SCREEN = None
_TRACKED_WINDOWS = weakref.WeakSet()
_SUBSCRIBED_TIMERS = weakref.WeakSet()
_SUBSCRIBED_CALLBACKS = []


def _find_qtcore_library() -> str | None:
    """Locates the active Qt6Core shared library / macOS framework for PySide6 across platforms."""
    try:
        import PySide6
        base_dir = os.path.dirname(PySide6.__file__)
        sys_plat = platform.system()

        if sys_plat == "Darwin":
            fw_candidates = [
                os.path.join(base_dir, "Qt", "lib", "QtCore.framework", "Versions", "A", "QtCore"),
                os.path.join(base_dir, "Qt", "lib", "QtCore.framework", "QtCore"),
            ]
            for fw in fw_candidates:
                if os.path.isfile(fw):
                    return fw

        for root, _, files in os.walk(base_dir):
            for f in files:
                if sys_plat == "Windows":
                    if f.lower() == "qt6core.dll":
                        return os.path.join(root, f)
                elif sys_plat == "Darwin":
                    if f == "QtCore" and "QtCore.framework" in root:
                        return os.path.join(root, f)
                    if f.startswith("libQt6Core") and (f.endswith(".dylib") or ".dylib." in f):
                        return os.path.join(root, f)
                else:
                    if f.startswith("libQt6Core.so"):
                        return os.path.join(root, f)
    except Exception as e:
        osdoc.log_error(f"vsync: failed locating Qt6Core library: {e}")
    return None


def _init_unified_timer_hooks():
    """Binds to QUnifiedTimer in QtCore via ctypes with exact ABI arity matching.
    # INVARIANT: Match QUnifiedTimer::instance 0-arg vs 1-bool-arg C++ ABI strictly and ignore idle secondary screens.
    """
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
        inst_takes_bool = False
        set_func = None

        if sys_plat in ("Linux", "Darwin"):
            for sym_inst, takes_bool in (
                ("_ZN13QUnifiedTimer8instanceEb", True),
                ("_ZN13QUnifiedTimer8instanceEv", False),
            ):
                if hasattr(lib, sym_inst):
                    inst_func = getattr(lib, sym_inst)
                    inst_takes_bool = takes_bool
                    break
            sym_set = "_ZN13QUnifiedTimer17setTimingIntervalEi"
            if hasattr(lib, sym_set):
                set_func = getattr(lib, sym_set)
        elif sys_plat == "Windows":
            # Pair MSVC symbols strictly with exact parameter arity
            candidates_inst = [
                ("?instance@QUnifiedTimer@@SAPEAV1@XZ", False),
                ("?instance@QUnifiedTimer@@SAPAV1@XZ", False),
                ("?instance@QUnifiedTimer@@SAPEAV1@_N@Z", True),
            ]
            candidates_set = [
                "?setTimingInterval@QUnifiedTimer@@QEAAXH@Z",
                "?setTimingInterval@QUnifiedTimer@@QAEXH@Z",
            ]
            for sym, takes_bool in candidates_inst:
                if hasattr(lib, sym):
                    inst_func = getattr(lib, sym)
                    inst_takes_bool = takes_bool
                    break
            for sym in candidates_set:
                if hasattr(lib, sym):
                    set_func = getattr(lib, sym)
                    break

        if inst_func and set_func:
            inst_func.restype = ctypes.c_void_p
            if inst_takes_bool:
                inst_func.argtypes = [ctypes.c_bool]
                instance_ptr = inst_func(True)
            else:
                inst_func.argtypes = []
                instance_ptr = inst_func()

            if instance_ptr:
                set_func.argtypes = [ctypes.c_void_p, ctypes.c_int]
                _TIMER_INSTANCE = instance_ptr
                _SET_INTERVAL_FUNC = set_func
                _UNIFIED_TIMER_AVAILABLE = True
                osdoc.log_info(
                    f"vsync: QUnifiedTimer hook bound successfully (handle: {hex(_TIMER_INSTANCE)})."
                )
            else:
                osdoc.log_info("vsync: QUnifiedTimer::instance returned null, using fallback timing.")
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
        return 16

    effective_rate = min(refresh_rate, 144.0)
    interval = round(1000.0 / effective_rate)
    return max(7, min(33, interval))


def get_refresh_interval_ms() -> int:
    """Returns the current VSync animation tick interval in milliseconds."""
    return _CURRENT_INTERVAL_MS


def _notify_subscribers(interval_ms: int):
    dead_timers = []
    for timer in list(_SUBSCRIBED_TIMERS):
        try:
            timer.setInterval(interval_ms)
        except RuntimeError:
            dead_timers.append(timer)
        except Exception:
            pass
    for t in dead_timers:
        try:
            _SUBSCRIBED_TIMERS.discard(t)
        except Exception:
            pass

    alive_cbs = []
    for cb in list(_SUBSCRIBED_CALLBACKS):
        try:
            cb(interval_ms)
            alive_cbs.append(cb)
        except RuntimeError:
            pass
        except Exception:
            alive_cbs.append(cb)
    _SUBSCRIBED_CALLBACKS[:] = alive_cbs


def subscribe_timer(timer) -> int:
    """Registers a QTimer so its interval updates dynamically when the active screen changes."""
    if timer is not None:
        try:
            _SUBSCRIBED_TIMERS.add(timer)
            timer.setInterval(_CURRENT_INTERVAL_MS)
        except Exception:
            pass
    return _CURRENT_INTERVAL_MS


def subscribe_refresh_callback(cb):
    """Registers a callback invoked with (interval_ms: int) whenever screen refresh rate changes."""
    if callable(cb) and cb not in _SUBSCRIBED_CALLBACKS:
        _SUBSCRIBED_CALLBACKS.append(cb)


def apply_screen_refresh_rate(screen: QScreen | None):
    """Applies the refresh rate of the specified screen to QUnifiedTimer and subscribed UI timers."""
    global _CURRENT_INTERVAL_MS, _ACTIVE_SCREEN
    if not screen:
        app = QGuiApplication.instance()
        screen = app.primaryScreen() if app else None

    _ACTIVE_SCREEN = screen
    rate = screen.refreshRate() if screen else 60.0
    target_interval = calculate_target_interval(rate)

    if target_interval != _CURRENT_INTERVAL_MS or not _UNIFIED_TIMER_AVAILABLE:
        changed = target_interval != _CURRENT_INTERVAL_MS
        _CURRENT_INTERVAL_MS = target_interval
        if _UNIFIED_TIMER_AVAILABLE and _SET_INTERVAL_FUNC and _TIMER_INSTANCE:
            try:
                _SET_INTERVAL_FUNC(_TIMER_INSTANCE, int(_CURRENT_INTERVAL_MS))
            except Exception as e:
                osdoc.log_error(f"vsync: failed updating timing interval: {e}")

        if changed:
            _notify_subscribers(_CURRENT_INTERVAL_MS)

        osdoc.log_info(
            f"vsync: Display '{screen.name() if screen else 'unknown'}' @ {rate:.1f}Hz -> "
            f"Paced at {_CURRENT_INTERVAL_MS}ms (~{round(1000.0 / _CURRENT_INTERVAL_MS)} FPS)"
        )


def _on_screen_rate_changed(screen: QScreen):
    # Only update when the active window's current screen changes its rate
    if _ACTIVE_SCREEN is None or screen is _ACTIVE_SCREEN:
        apply_screen_refresh_rate(screen)


def init_high_refresh_sync(app: QApplication):
    """
    Initializes dynamic VSync synchronization for the Qt application.
    """
    _init_unified_timer_hooks()

    primary = app.primaryScreen()
    if primary:
        apply_screen_refresh_rate(primary)

    def _on_screen_added(s: QScreen):
        try:
            s.refreshRateChanged.connect(lambda _, scr=s: _on_screen_rate_changed(scr))
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
        if window in _TRACKED_WINDOWS:
            handle = window.windowHandle() if hasattr(window, 'windowHandle') else None
            if handle and handle.screen():
                apply_screen_refresh_rate(handle.screen())
            return
        handle = window.windowHandle() if hasattr(window, 'windowHandle') else None
        if handle:
            _TRACKED_WINDOWS.add(window)
            handle.screenChanged.connect(apply_screen_refresh_rate)
            apply_screen_refresh_rate(handle.screen())
    except Exception:
        pass
