#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: main.py
ROLE: Core Module
DESCRIPTION:
Main entry point for the BadWords application.
# INVARIANT: The guard section at the top of this file must remain parseable by
# Python 3.8 so incompatible host interpreters display a clear dialog.
# INVARIANT: The version gate runs before any third-party imports.
# INVARIANT: No network calls, pip installs, or browser launches occur without consent.
# INVARIANT: BootSplash is displayed before heavy OSDoctor/api/engine/main_window loading.
"""

import builtins
import importlib
import os
import sys
import time
import traceback

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# Propagate DaVinci Resolve embedded globals to builtins so all worker threads can access them
for _k in ("resolve", "bmd", "fusion", "fu"):
    if _k in globals() and not hasattr(builtins, _k):
        setattr(builtins, _k, globals()[_k])

# --- Cross-platform OpenMP / BLAS threading caps (Windows, macOS, Linux) ---
# Prevents worker threads from spin-waiting in while(true) loops and starving OS/UI
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OMP_WAIT_POLICY", "PASSIVE")
os.environ.setdefault("KMP_BLOCKTIME", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "2")

# Safe-boot software rendering fallback (triggered automatically on Windows retry)
if os.environ.get("BADWORDS_SAFE_BOOT") == "1":
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    os.environ.setdefault("QT_FFMPEG_ENCODING_HW_DEVICE_TYPES", "")

# --- Early startup guard (stdlib-only, Python 3.8+ parseable) ---
from startup import EXIT_FATAL_REPORTED, crash_report, env_guard, fatal_dialog

env_guard.prune_mismatched_version_paths()
if not env_guard.check_python_version():
    fatal_dialog.show_fatal("python_version", src_dir=_SRC)
    sys.exit(EXIT_FATAL_REPORTED)

# Importing osdoc installs the single Windows hidden-subprocess Popen hook.
import osdoc

from startup import legacy_cleanup, qt_env, runtime_mode, self_heal

legacy_cleanup.run(_SRC)
crash_report.install_runtime_crash_hooks(src_dir=_SRC)
qt_env.isolate_linux_qt_env(_SRC)
self_heal.ensure_components(_SRC)

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QSurfaceFormat
    from PySide6.QtCore import QLoggingCategory, QThread, QTimer, Signal
except Exception as _early_err:
    _tb = traceback.format_exc()
    fatal_dialog.show_fatal("qt", error_text=str(_early_err), tb_text=_tb, src_dir=_SRC)
    sys.exit(EXIT_FATAL_REPORTED)


# ==========================================
# BACKGROUND INITIALIZATION THREAD
# ==========================================

class InitThread(QThread):
    """
    Runs heavyweight initialization (hardware probes, Resolve script sync,
    ResolveHandler, AudioEngine) off the main thread while BootSplash is visible.
    """
    loaded = Signal(object, object)
    error = Signal(str)

    def __init__(self, os_doc, api_mod, engine_mod, parent=None):
        super().__init__(parent)
        self.os_doc = os_doc
        self.api_mod = api_mod
        self.engine_mod = engine_mod

    def run(self):
        try:
            osdoc.log_info("[BOOT] Probing hardware topology...")
            try:
                self.os_doc.log_hardware_info()
            except Exception as he:
                osdoc.log_warn(f"log_hardware_info error during startup: {he}")

            osdoc.log_info("[BOOT] Syncing DaVinci Resolve scripts...")
            try:
                self.os_doc.sync_resolve_scripts()
            except Exception as se:
                osdoc.log_warn(f"sync_resolve_scripts error during startup: {se}")

            osdoc.log_info("[BOOT] Initializing ResolveHandler...")
            resolve = self.api_mod.ResolveHandler(self.os_doc)
            osdoc.log_info("[BOOT] Initializing AudioEngine...")
            audio_engine = self.engine_mod.AudioEngine(self.os_doc, resolve)
            osdoc.log_info("[BOOT] Background initialization finished.")
            self.loaded.emit(resolve, audio_engine)
        except Exception as e:
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


# ==========================================
# APPLICATION CONTROLLER
# ==========================================

class AppController:
    """
    Owns every long-lived object in the application so Python's garbage
    collector never destroys a window simply because a helper function returned.
    """

    def __init__(self, splash):
        self.os_doc = None
        self.splash = splash
        self.main_win = None
        self.init_thread = None

    def start(self):
        """Initialize OSDoctor, import backend packages, and start InitThread while splash is visible."""
        try:
            self._splash_start_time = time.time()
            self.os_doc = osdoc.OSDoctor()
            try:
                import faulthandler
                lf = getattr(self.os_doc, "log_file", None)
                if lf is not None and hasattr(lf, "fileno"):
                    lf.fileno()
                    faulthandler.enable(file=lf, all_threads=True)
            except Exception:
                pass
            if os.environ.get("BADWORDS_SAFE_BOOT") == "1":
                osdoc.log_warn("[BOOT] Safe-boot mode active (software OpenGL/RHI fallback).")
            osdoc.log_info("Event loop started.")
            QApplication.processEvents()

            import api
            QApplication.processEvents()
            import engine
            QApplication.processEvents()

            self.init_thread = InitThread(self.os_doc, api, engine)
            self.init_thread.loaded.connect(self.on_loaded)
            self.init_thread.error.connect(self.on_error)
            self.init_thread.start()

            # Pre-import main window on main thread in next event-loop tick while InitThread works
            QTimer.singleShot(0, self._preimport_main_window)
        except Exception as e:
            self.on_error(f"{e}\n\n{traceback.format_exc()}")

    def _preimport_main_window(self):
        try:
            importlib.import_module("gui.main_window")
        except Exception as e:
            osdoc.log_warn(f"Main window pre-import warning: {e}")

    def on_loaded(self, resolve, audio_engine):
        """Called on the main thread when InitThread finishes successfully."""
        self._finish_startup(resolve, audio_engine)

    def _finish_startup(self, resolve, audio_engine):
        try:
            import gui
            import config

            prefs = {}
            if hasattr(audio_engine, "load_preferences"):
                prefs = audio_engine.load_preferences() or {}
            elif hasattr(audio_engine, "os_doc") and isinstance(getattr(audio_engine.os_doc, "settings", None), dict):
                prefs = audio_engine.os_doc.settings
            app = QApplication.instance()
            config.init_ui_scaling(
                app,
                scale_pct=prefs.get("ui_scale_pct"),
                scale_mode=prefs.get("ui_scale_mode", "auto"),
            )
            if app is not None:
                app.setFont(
                    config.make_font(
                        config.UI_FONT_NAME,
                        config.BASE_FONT_PT,
                        weight=QFont.Weight.Normal,
                    )
                )

            osdoc.log_info(
                f"Loading complete. Building main window (scale_mode={config.UI_SCALE_MODE}, "
                f"ui_scale={config.UI_SCALE_PERCENT}%, os_scale={config.OS_SCALE_PERCENT}%, "
                f"factor={config.SCALE_FACTOR:.3f})."
            )
            self.main_win = gui.BadWordsGUI(audio_engine, resolve)
            self.main_win.closeEvent_callback = self._on_close
            osdoc.log_info("Main window constructed. Showing window.")

            self.main_win.showMaximized()
            self.main_win.raise_()
            self.main_win.activateWindow()

            gui.track_window_screen(self.main_win)

            if self.splash:
                self.splash.close()
                self.splash = None
            osdoc.log_info("Main window displayed.")
        except Exception as e:
            self.on_error(f"{e}\n\n{traceback.format_exc()}")

    def on_error(self, message: str):
        """Called on the main thread when InitThread or startup fails."""
        osdoc.log_error(f"CRITICAL ERROR during init:\n{message}")
        if self.splash:
            self.splash.close()
            self.splash = None
        first_line = message.split("\n")[0] if message else "Startup initialization failed"
        fatal_dialog.show_fatal("generic", error_text=first_line, tb_text=message, src_dir=_SRC)
        app = QApplication.instance()
        if app is not None:
            app.exit(EXIT_FATAL_REPORTED)
        else:
            sys.exit(EXIT_FATAL_REPORTED)

    def _on_close(self):
        """Called when the user closes the main window."""
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        if self.os_doc:
            self.os_doc.cleanup_temp(close_session=True)
        crash_report.wait_for_pending_reports(timeout=2.0)
        app = QApplication.instance()
        if app is not None:
            app.quit()


# ==========================================
# MODULE-LEVEL REFERENCE (prevents GC)
# ==========================================
_controller: AppController = None


# ==========================================
# ENTRY POINT
# ==========================================

def main():
    global _controller

    try:
        try:
            import faulthandler
            if sys.stderr is not None and hasattr(sys.stderr, "fileno"):
                sys.stderr.fileno()
                faulthandler.enable(file=sys.stderr, all_threads=True)
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("veritus.badwords.editor.v4")
                ctypes.windll.winmm.timeBeginPeriod(1)
            except Exception:
                pass

        if os.environ.get("BADWORDS_SAFE_BOOT") != "1":
            try:
                fmt = QSurfaceFormat()
                fmt.setSwapInterval(1)
                QSurfaceFormat.setDefaultFormat(fmt)
            except Exception:
                pass

        QLoggingCategory.setFilterRules("qt.text.font.db.warning=false\nqt.text.font.db.debug=false")

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        import config
        from gui.utils import _app_icon, init_embedded_fonts, setup_macos_standalone_identity
        from gui.vsync import init_high_refresh_sync
        from startup.boot_splash import BootSplash

        app.setApplicationName(config.APP_NAME)
        app.setApplicationDisplayName(config.APP_NAME)
        app.setOrganizationName("Veritus")
        app.setOrganizationDomain("veritus.badwords")
        if sys.platform.startswith("linux"):
            app.setDesktopFileName("badwords")

        init_high_refresh_sync(app)
        config.apply_dark_app_theme(app)
        saved_scale_mode, saved_scale_pct = config.runtime_data.read_startup_ui_scale_prefs()
        config.init_ui_scaling(app, scale_pct=saved_scale_pct, scale_mode=saved_scale_mode)

        init_embedded_fonts()
        default_font = config.make_font(
            config.UI_FONT_NAME,
            config.BASE_FONT_PT,
            weight=QFont.Weight.Normal,
        )
        app.setFont(default_font)

        if sys.platform == "darwin":
            try:
                if not runtime_mode.is_embedded_in_resolve():
                    setup_macos_standalone_identity(config.APP_NAME)
            except Exception:
                pass
        elif sys.platform.startswith("linux"):
            try:
                import ctypes
                import ctypes.util
                libc_name = ctypes.util.find_library("c") or "libc.so.6"
                libc = ctypes.CDLL(libc_name)
                libc.prctl(15, b"BadWords\0", 0, 0, 0)
            except Exception:
                pass

        app_icon = _app_icon()
        if not app_icon.isNull():
            app.setWindowIcon(app_icon)

        app.setStyleSheet(config.scrollbar_qss(8))

        # Show BootSplash immediately BEFORE OSDoctor / api / engine / main_window load
        splash = BootSplash()
        splash.show()
        app.processEvents()

        _controller = AppController(splash)
        QTimer.singleShot(0, _controller.start)

        sys.exit(app.exec())

    except Exception as e:
        error_trace = traceback.format_exc()
        error_msg = f"CRITICAL ERROR: {e}\n{error_trace}"

        try:
            osdoc.log_error(error_msg)
        except Exception:
            print(error_msg, file=sys.stderr)

        fatal_dialog.show_fatal("generic", error_text=str(e), tb_text=error_trace, src_dir=_SRC)
        sys.exit(EXIT_FATAL_REPORTED)


if __name__ == "__main__":
    main()
