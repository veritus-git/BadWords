#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: main.py
ROLE: Manager / Entry Point
DESCRIPTION:
Main execution file. Checks dependencies, imports configuration,
initializes the OS layer (osdoc), Resolve API, Engine, and starts the GUI.
Connects all components into a working application.
[PySide6 migration: Stage 1 — fixed GC & thread-affinity issues via AppController]
"""

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QThread, Signal

# Application module imports
import osdoc
import api
import engine
import gui


# ==========================================
# BACKGROUND INITIALIZATION THREAD
# ==========================================

class InitThread(QThread):
    """
    Runs heavyweight initialization (ResolveHandler, AudioEngine) off the
    main thread so the splash screen stays responsive.

    Signals are delivered to slots on the MAIN thread automatically by Qt's
    queued-connection mechanism, so all GUI work in the slots is thread-safe.

    Signals
    -------
    loaded(resolve, audio_engine)
        Emitted when both objects are ready.
    error(message)
        Emitted if an exception is raised during initialization.
    """
    loaded = Signal(object, object)
    error  = Signal(str)

    def __init__(self, os_doc, parent=None):
        super().__init__(parent)
        self.os_doc = os_doc

    def run(self):
        try:
            resolve      = api.ResolveHandler(self.os_doc)
            audio_engine = engine.AudioEngine(self.os_doc, resolve)
            self.loaded.emit(resolve, audio_engine)
        except Exception as e:
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


# ==========================================
# APPLICATION CONTROLLER
# ==========================================

class AppController:
    """
    Owns every long-lived object in the application so Python's garbage
    collector never destroys a window simply because a helper function
    returned.

    Lifetime: one instance is created in main() and stored in the module-
    level ``_controller`` variable, keeping it alive for the duration of
    the Qt event loop.
    """

    def __init__(self, os_doc: osdoc.OSDoctor):
        self.os_doc      = os_doc

        # These attributes MUST be kept as instance variables.
        # If they were local variables inside on_loaded(), the GC would
        # destroy the QWidgets the moment that function returned.
        self.splash      = None   # gui.SplashScreen
        self.main_win    = None   # gui.BadWordsGUI
        self.init_thread = None   # InitThread

    # ------------------------------------------------------------------
    # Start-up sequence
    # ------------------------------------------------------------------

    def start(self):
        """Create the splash and kick off background initialization."""
        # Splash is stored on self → GC-safe for the entire loading phase
        self.splash = gui.SplashScreen()
        self.splash.show()
        QApplication.processEvents()  # Paint splash before heavy loading starts

        self.init_thread = InitThread(self.os_doc)
        # Qt delivers cross-thread signals via the event loop on the main
        # thread, so on_loaded / on_error are always called from main thread.
        self.init_thread.loaded.connect(self.on_loaded)
        self.init_thread.error.connect(self.on_error)
        self.init_thread.start()

    # ------------------------------------------------------------------
    # Signal handlers (always called on the MAIN THREAD by Qt)
    # ------------------------------------------------------------------

    def on_loaded(self, resolve, audio_engine):
        """
        Called on the main thread when InitThread finishes successfully.
        Build the main window and store it on self so GC cannot destroy it.
        """
        self.splash.close()
        self.splash = None  # Allow GC to clean up the splash widget properly

        osdoc.log_info("Loading complete. Building main window.")

        # IMPORTANT: store on self, NOT as a local variable.
        self.main_win = gui.BadWordsGUI(audio_engine, resolve)

        # Wire clean-shutdown callback
        self.main_win.closeEvent_callback = self._on_close

        self.main_win.show()
        self.main_win.raise_()
        self.main_win.activateWindow()
        osdoc.log_info("Main window displayed.")

    def on_error(self, message: str):
        """Called on the main thread when InitThread raises an exception."""
        osdoc.log_error(f"CRITICAL ERROR during init:\n{message}")
        if self.splash:
            self.splash.close()
            self.splash = None
        QMessageBox.critical(
            None,
            "Critical Application Error",
            f"An unexpected error occurred during startup:\n\n"
            f"{message.split(chr(10))[0]}"
            f"\n\nDetails saved to log file."
        )
        QApplication.instance().quit()

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def _on_close(self):
        """Called when the user closes the main window."""
        if self.os_doc:
            self.os_doc.cleanup_temp()
        QApplication.instance().quit()


# ==========================================
# MODULE-LEVEL REFERENCE (prevents GC)
# ==========================================
# Storing the controller at module level ensures Python will NEVER garbage-
# collect it (and therefore the windows it owns) while the event loop runs.
_controller: AppController = None


# ==========================================
# ENTRY POINT
# ==========================================

def main():
    global _controller

    os_doc = None

    try:
        # 1. System layer — fast, safe on main thread
        os_doc = osdoc.OSDoctor()
        osdoc.log_info("=== Starting BadWords ===")

        if not os_doc.is_mac:
            import os
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

        # 2. QApplication must exist before any QWidget
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)  # We control shutdown via closeEvent

        # 3. Create controller (holds all GUI references → GC-safe)
        _controller = AppController(os_doc)
        _controller.start()  # Shows splash, starts InitThread

        # 4. Hand control to Qt — app.exec() blocks here until app.quit() is called
        osdoc.log_info("Event loop started.")
        sys.exit(app.exec())

    except Exception as e:
        error_trace = traceback.format_exc()
        error_msg   = f"CRITICAL ERROR: {e}\n{error_trace}"

        if os_doc:
            osdoc.log_error(error_msg)
        else:
            print(error_msg, file=sys.stderr)

        # Attempt to show a Qt error dialog even if early init failed
        try:
            _app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Critical Application Error",
                f"An unexpected error occurred:\n{e}\n\nDetails saved to log file."
            )
        except Exception:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()