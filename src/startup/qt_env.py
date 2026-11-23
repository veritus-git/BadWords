#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: startup/qt_env.py
ROLE: Linux Qt6 Environment Isolation
DESCRIPTION:
Isolates bundled PySide6 Qt6 shared libraries and plugins from host KDE/GTK
Qt themes and libraries on Linux before PySide6 is imported.
"""

import os
import sys


def isolate_linux_qt_env(src_dir):
    """Isolate Qt6 plugin/library paths on Linux.

    # INVARIANT: must run before any PySide6 import.
    """
    if not sys.platform.startswith("linux"):
        return

    if "QT_QPA_PLATFORMTHEME" in os.environ:
        del os.environ["QT_QPA_PLATFORMTHEME"]
    os.environ.pop("QT_STYLE_OVERRIDE", None)

    try:
        import ctypes

        abs_src = os.path.abspath(src_dir)
        cand_dirs = [abs_src, os.path.dirname(abs_src)] + list(sys.path)

        qt_lib_dir = None
        qt_plugins_dir = None
        for d in cand_dirs:
            if not d or not os.path.isdir(d):
                continue
            lib_check = os.path.join(d, "PySide6", "Qt", "lib")
            if os.path.isdir(lib_check):
                qt_lib_dir = lib_check
                plugins_check = os.path.join(d, "PySide6", "Qt", "plugins")
                if os.path.isdir(plugins_check):
                    qt_plugins_dir = plugins_check
                break
            vlib = os.path.join(d, "venv", "lib")
            if os.path.isdir(vlib):
                try:
                    for sub in os.listdir(vlib):
                        sp_lib = os.path.join(vlib, sub, "site-packages", "PySide6", "Qt", "lib")
                        if os.path.isdir(sp_lib):
                            qt_lib_dir = sp_lib
                            sp_plugins = os.path.join(vlib, sub, "site-packages", "PySide6", "Qt", "plugins")
                            if os.path.isdir(sp_plugins):
                                qt_plugins_dir = sp_plugins
                            break
                except Exception:
                    pass
                if qt_lib_dir:
                    break

        if qt_plugins_dir:
            os.environ["QT_PLUGIN_PATH"] = qt_plugins_dir

        if qt_lib_dir:
            cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if cur_ld:
                os.environ["LD_LIBRARY_PATH"] = "{0}:{1}".format(qt_lib_dir, cur_ld)
            else:
                os.environ["LD_LIBRARY_PATH"] = qt_lib_dir

            qt_preload = (
                "libQt6Core.so.6",
                "libQt6Network.so.6",
                "libQt6DBus.so.6",
                "libQt6Gui.so.6",
                "libQt6Widgets.so.6",
                "libQt6OpenGL.so.6",
                "libQt6WaylandClient.so.6",
                "libQt6XcbQpa.so.6",
            )
            for lib_name in qt_preload:
                p = os.path.join(qt_lib_dir, lib_name)
                if os.path.isfile(p):
                    try:
                        ctypes.CDLL(p, mode=ctypes.RTLD_GLOBAL)
                    except Exception:
                        pass
    except Exception:
        pass
