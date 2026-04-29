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
        self.splash = gui.SplashScreen()
        self.splash.show()
        QApplication.processEvents()  # Paint splash before heavy loading starts

        self.init_thread = InitThread(self.os_doc)
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

def _run_auto_update_if_needed(os_doc, splash=None):
    """
    Called AFTER QApplication and SplashScreen exist.
    If auto_update_on_start is enabled and a newer version exists on GitHub/GitLab,
    download the update script, run it (blocking — splash stays visible),
    then re-exec this process so fresh files are loaded.
    """
    import json, urllib.request, ssl, subprocess, tempfile, os, sys

    def _set_splash(text):
        if splash is not None and hasattr(splash, 'set_status'):
            splash.set_status(text)
            QApplication.processEvents()

    # Read prefs without importing gui/Qt
    prefs_path = os.path.join(os_doc.install_dir, 'settings.json')
    try:
        with open(prefs_path, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
    except Exception:
        return

    if not prefs.get('auto_update_on_start', False):
        return

    _set_splash('Checking for updates…')
    osdoc.log_info("[AutoUpdate] auto_update_on_start is ON — checking for updates...")

    # ── 1. Fetch latest tag ─────────────────────────────────────────────
    GH_API = "https://api.github.com/repos/veritus-git/BadWords/releases/latest"
    GL_API = "https://gitlab.com/api/v4/projects/veritus-git%2FBadWords/releases/permalink/latest"
    GH_SCRIPT = "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/update-linux.sh"
    GL_SCRIPT = "https://gitlab.com/veritus-git/BadWords/-/raw/main/setupfiles/update-linux.sh"
    WIN_SCRIPT = "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/update-windows.bat"
    WIN_SCRIPT_GL = "https://gitlab.com/veritus-git/BadWords/-/raw/main/setupfiles/update-windows.bat"
    MAC_SCRIPT = "https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/update-mac.sh"
    MAC_SCRIPT_GL = "https://gitlab.com/veritus-git/BadWords/-/raw/main/setupfiles/update-mac.sh"

    def _fetch_json(url):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "BadWords-AutoUpdate/1.0"})
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            return json.loads(r.read().decode())

    def _parse_ver(tag):
        try:
            return tuple(int(x) for x in tag.strip().lstrip('vV').split('.'))
        except Exception:
            return (0,)

    import config as _cfg
    current = _parse_ver(_cfg.VERSION)
    latest_tag = None
    try:
        latest_tag = _fetch_json(GH_API).get("tag_name", "").strip()
    except Exception:
        pass
    if not latest_tag:
        try:
            latest_tag = _fetch_json(GL_API).get("tag_name", "").strip()
        except Exception:
            pass

    if not latest_tag or _parse_ver(latest_tag) <= current:
        osdoc.log_info(f"[AutoUpdate] Already up-to-date ({_cfg.VERSION}). Skipping.")
        return

    _set_splash(f'Updating to {latest_tag}…')
    osdoc.log_info(f"[AutoUpdate] New version {latest_tag} found — downloading update script...")

    # ── 2. Choose script URLs ────────────────────────────────────────────
    is_win = os_doc.is_win
    is_mac = getattr(os_doc, 'is_mac', False)
    if is_win:
        urls = [WIN_SCRIPT, WIN_SCRIPT_GL]
        suffix = '.bat'
    elif is_mac:
        urls = [MAC_SCRIPT, MAC_SCRIPT_GL]
        suffix = '.sh'
    else:
        urls = [GH_SCRIPT, GL_SCRIPT]
        suffix = '.sh'

    # ── 3. Download update script ───────────────────────────────────────────
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    content = None
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=20, context=ctx) as r:
                content = r.read()
            break
        except Exception:
            continue

    if not content:
        osdoc.log_info("[AutoUpdate] Could not download update script. Skipping.")
        return

    # ── 4. Run update script (blocking; splash stays visible) ────────────
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix='bw_autoupd_')
    try:
        with os.fdopen(fd, 'wb') as fh:
            fh.write(content)
        if not is_win:
            os.chmod(tmp_path, 0o755)
        cmd = ['cmd.exe', '/c', tmp_path] if is_win else ['/bin/bash', tmp_path]
        osdoc.log_info("[AutoUpdate] Running update script (blocking)...")
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600
        )
        if result.returncode == 0:
            osdoc.log_info("[AutoUpdate] Update script completed successfully.")
            _set_splash('Update complete — restarting…')
        else:
            osdoc.log_info(f"[AutoUpdate] Update script exited with code {result.returncode}.")
    except Exception as e:
        osdoc.log_info(f"[AutoUpdate] Update script failed: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    # ── 5. Re-exec this process to load fresh files ──────────────────────
    osdoc.log_info("[AutoUpdate] Re-launching BadWords with updated files...")
    try:
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        osdoc.log_info(f"[AutoUpdate] Re-exec failed: {e}. Continuing with current files.")


# ==========================================
# MODULE-LEVEL REFERENCE (prevents GC)
# ==========================================
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
        _controller.start()  # Shows splash, runs auto-update if needed, starts InitThread

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
