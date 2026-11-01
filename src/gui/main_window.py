#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: main_window.py
ROLE: Core Module
DESCRIPTION:
Main application window managing the entire GUI composition.
"""

import platform
import os

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget, QRadioButton, QButtonGroup,
    QCheckBox
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QObject, QEvent, QVariantAnimation, QEasingCurve, QPropertyAnimation, QThread
)
from PySide6.QtGui import (
    QPixmap, QGuiApplication, 
    QCursor
)

import config

# --- INJECTED WIDGET IMPORTS ---
from gui.widgets.buttons import QPushButton, MarqueeRadioButton, ToggleSwitch, SidebarButton
from gui.widgets.labels import QLabel, IDETooltip
from gui.widgets.splitters import GripSplitter
# -------------------------------


# ===================================
# QFRAMELESSWINDOW — NATIVE CSD LIBRARY
# ===================================
# On Windows, use the battle-tested qframelesswindow library for proper
# Aero Snap, DWM shadows, resize, drag-detach, and snap layouts.
# Linux/macOS keep the existing manual code (it works fine there).
_HAS_QFRAMELESS = False
_BaseMainWindow = QMainWindow
_BaseDialog = QDialog



# ===================================
# CONSTANTS
# ===================================
RTL_CODES = {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'}  # Right-To-Left Languages


# ===================================
# HELPERS
# ===================================

_QPushButton = QPushButton




_QRadioButton = QRadioButton

from .utils import _app_icon, _txt, get_layout_icon_path
from .components.dialogs import TelemetryPopup, CustomMsgBox, UpdateNotifyDialog, SettingsDialog, GlobalAppFilter, SidebarDragZone, UpdateCheckThread
from .components.search_overlay import SearchOverlayWidget
from .components.mixins import FramelessWindowMixin, _HAS_QFRAMELESS, _BaseMainWindow
from .components.titlebar import CustomTitleBar
from .components.top_status_island import TopStatusIsland
from handlers.analysis_worker import AnalysisWorker
from handlers.autosave_manager import AutoSaveManager
from handlers.undo_manager import UndoManager

class _ProjectImportWorker(QThread):
    status_updated = Signal(str)
    finished_success = Signal(dict, dict)
    finished_error = Signal(str)

    def __init__(self, engine, file_path):
        super().__init__()
        self.engine = engine
        self.file_path = file_path

    def run(self):
        try:
            self.status_updated.emit("Loading project...")
            bws_extras = None
            if self.file_path.endswith('.bws'):
                state, _, bws_extras = self.engine.load_bws(self.file_path)
            else:
                state, _ = self.engine.load_project_state(self.file_path)

            missing_media = []
            if bws_extras and bws_extras.get("media_inventory"):
                self.status_updated.emit("Checking media...")
                missing_media, _ = self.engine.verify_media_inventory(bws_extras["media_inventory"])

            if bws_extras and bws_extras.get("assembly_recipe") and bws_extras.get("audio_path"):
                self.status_updated.emit("Preparing audio...")
                temp_dir = self.engine.os_doc.get_temp_folder()
                out_path = os.path.join(temp_dir, f"bws_assembled_{int(time.time())}.flac")
                self.engine.execute_assembly_recipe(bws_extras["assembly_recipe"], bws_extras["audio_path"], out_path)

            target_name = (state.get('transcription_source') or (state.get('settings') or {}).get('transcription_source') or {}).get("timeline_name", "")

            meta = {
                "bws_extras": bws_extras,
                "missing_media": missing_media,
                "target_name": target_name
            }
            self.finished_success.emit(state, meta)
        except Exception as e:
            self.finished_error.emit(str(e))


class WorkspaceWarningOverlay(QFrame):
    def __init__(self, parent_stack, title, description, btn_accept_text, btn_reject_text=None, btn_cancel_text=None):
        super().__init__()
        self._stack = parent_stack
        from PySide6.QtCore import QEventLoop, Qt
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFrame
        self._loop = QEventLoop()
        self._result = QDialog.Rejected
        
        import config
        self.setStyleSheet(f"background-color: {config.BG_COLOR};")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setFixedWidth(config.S(600))
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(config.S(20))
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: {config.FS(18)}pt; font-weight: bold; color: white; background: transparent; font-family: '{config.UI_FONT_NAME}';")
        lbl_title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"font-size: {config.FS(10.5)}pt; color: #cccccc; background: transparent; line-height: 1.5; font-family: '{config.UI_FONT_NAME}';")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lbl_desc)
        
        c_layout.addSpacing(config.S(10))
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(config.S(15))
        btn_layout.setAlignment(Qt.AlignCenter)
        
        if btn_reject_text:
            btn_reject = QPushButton(btn_reject_text)
            btn_reject.setCursor(Qt.PointingHandCursor)
            btn_reject.setStyleSheet(f"""
                QPushButton {{
                    background-color: #404040;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: {config.S(4)}px;
                    padding: {config.S(8)}px {config.S(16)}px;
                    font-size: {config.FS(10)}pt;
                    font-family: "{config.UI_FONT_NAME}";
                    font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #505050; border-color: #666666; }}
                QPushButton:pressed {{ background-color: #303030; }}
            """)
            btn_reject.clicked.connect(self._on_reject)
            btn_layout.addWidget(btn_reject)
            
        btn_accept = QPushButton(btn_accept_text)
        btn_accept.setCursor(Qt.PointingHandCursor)
        btn_accept.setStyleSheet(f"""
            QPushButton {{
                background-color: #23a559;
                color: white;
                border: none;
                border-radius: {config.S(4)}px;
                padding: {config.S(8)}px {config.S(16)}px;
                font-size: {config.FS(10)}pt;
                font-family: "{config.UI_FONT_NAME}";
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #26b361; }}
            QPushButton:pressed {{ background-color: #1e8e4c; }}
        """)
        btn_accept.clicked.connect(self._on_accept)
        btn_layout.addWidget(btn_accept)
        
        c_layout.addLayout(btn_layout)
        
        if btn_cancel_text:
            btn_cancel = QPushButton(btn_cancel_text)
            btn_cancel.setCursor(Qt.PointingHandCursor)
            btn_cancel.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: #a0a0a0;
                    border: none;
                    text-decoration: underline;
                    padding: {config.S(8)}px {config.S(16)}px;
                    font-size: {config.FS(10)}pt;
                    font-family: "{config.UI_FONT_NAME}";
                }}
                QPushButton:hover {{ color: white; }}
                QPushButton:pressed {{ color: #808080; }}
            """)
            btn_cancel.clicked.connect(self._on_cancel)
            c_layout.addWidget(btn_cancel, alignment=Qt.AlignCenter)
            
        layout.addWidget(container)

    def _on_accept(self):
        from PySide6.QtWidgets import QDialog
        self._result = QDialog.Accepted
        self._loop.quit()

    def _on_reject(self):
        from PySide6.QtWidgets import QDialog
        self._result = QDialog.Rejected
        self._loop.quit()

    def _on_cancel(self):
        self._result = -1  # custom code for Cancel
        self._loop.quit()

    def exec(self):
        prev_idx = self._stack.currentIndex()
        idx = self._stack.addWidget(self)
        self._stack.setCurrentIndex(idx)
        self._loop.exec()
        self._stack.setCurrentIndex(prev_idx)
        self._stack.removeWidget(self)
        self.deleteLater()
        return self._result

class _NeverShown(QFrame):
    """The old layout's left panel and icon rails: kept (code still reaches them and their buttons),
    never shown. Every panel opens in the inspector on the right."""
    def setVisible(self, visible):
        super().setVisible(False)


class BadWordsGUI(FramelessWindowMixin, _BaseMainWindow):
    """
    Stage 3 — QMainWindow implementing the "VS Code" unified workspace:
      - Opens maximized on the monitor under the cursor
      - NO top toolbar; left and right vertical activity bars instead
      - QStackedWidget as the central widget (3 pages)
        Page 0: Welcome / Config   (flat, borderless — default view)
        Page 1: Processing         (progress placeholder)
        Page 2: Editor             (editor placeholder)
      - Right dock starts hidden; revealed when analysis begins
      - CSD: frameless window with CustomTitleBar and native-feeling behaviour
    """

    def __init__(self, engine, resolve_handler, parent=None):
        super().__init__(parent)

        # ── CSD: remove native frame, enable translucency ──────────────────
        self.frameless_init(is_popup=False)

        self.engine              = engine
        self.resolve_handler     = resolve_handler
        self.autosave_manager    = AutoSaveManager(self.engine, self.engine.os_doc.get_autosave_dir())
        
        # This callback is injected by AppController in main.py
        self.closeEvent_callback = None
        self._chapters = []
        self._current_chapter_idx = -1

        self.shared_tooltip = IDETooltip()
        self.shared_tooltip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.shared_tooltip.setWindowFlag(Qt.WindowTransparentForInput, True)
        
        # Install global app filter to route all tooltips through IDETooltip and handle globals
        self._global_app_filter = GlobalAppFilter(self.shared_tooltip)
        QApplication.instance().installEventFilter(self._global_app_filter)
        
        # Declare panel containers early for Pyre inference
        self._sidebar_left: QFrame = None
        self._sidebar_right: QFrame = None
        self._panel_left: QFrame = None
        self._panel_right: QFrame = None

        # --- Language preference ---
        prefs     = engine.load_preferences() or {}
        self.lang = prefs.get("gui_lang", "en")
        if self.lang not in config.TRANS:
            self.lang = "en"

        # --- Window basics ---
        self.setWindowTitle(config.TRANS[self.lang].get("title", config.APP_NAME))
        self.setWindowIcon(_app_icon())
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            init_w = avail.width()
            init_h = avail.height()
        else:
            is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))
            init_w = config.S(780) if is_more_accurate else config.CFG_WINDOW_W_BASE
            init_h = config.CFG_WINDOW_H_BASE
        self.resize(init_w, init_h)
        self.setMinimumSize(config.S(330), config.S(400))
        from gui.views.welcome_view import is_embedded_in_resolve
        self.is_standalone = not is_embedded_in_resolve()

        # Once, when the StoryCraft theme arrives: it becomes the theme (the others stay in Settings)
        _p = self.engine.load_preferences() or {}
        if not _p.get('ui_theme_storycraft_set'):
            from gui import theme as _theme
            _p['ui_theme'], _p['ui_theme_storycraft_set'] = 'storycraft', True
            self.engine.save_preferences(_p)
            _theme.set_theme('storycraft')

        # --- Global QSS ---
        self.setStyleSheet(f"""
            * {{ outline: none; }}
            QMainWindow {{
                background-color: transparent;
            }}
            QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                font-size: {config.FS(10)}pt;
            }}
            {config.scrollbar_qss(8)}
        """)

        # ── CSD: root frame (wraps title bar + content, owns border-radius) ──
        self._root_frame = QFrame()
        self._root_frame.setObjectName("RootFrame")
        _is_mac_root = platform.system() == "Darwin"
        self._root_frame.setStyleSheet(f"""
            QFrame#RootFrame {{
                background-color: {config.BG_COLOR};
                border-radius: 0px;
            }}
        """)
        self._root_layout = QVBoxLayout(self._root_frame)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # ── CSD: custom title bar ───────────────────────────────────────
        self._title_bar = CustomTitleBar(self, self.lang, parent=self._root_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._title_bar)
        self._title_bar.chapter_dropdown.valueChanged.connect(self._switch_chapter)
        self._title_bar.projectExportRequested.connect(self._on_export_project)
        self._title_bar.projectImportRequested.connect(self._on_import_project)
        self._title_bar.transcriptExportTxtRequested.connect(self._on_export_transcript_txt)
        self._title_bar.transcriptCopyRequested.connect(self._on_copy_transcript_clipboard)
        self._title_bar.aiTranscriptCopyRequested.connect(self._on_copy_ai_transcript)
        self._title_bar.aiTranscriptExportRequested.connect(self._on_export_ai_transcript)
        self._title_bar.aiStoryImportRequested.connect(self._on_import_ai_story)
        self._root_layout.addWidget(self._title_bar)
        self.top_island = TopStatusIsland(parent_frame=self._root_frame, main_window=self)

        # On macOS: hide custom CSD title bar — native title bar handles close/min/max/fullscreen.
        # The native window title is set to show source timeline info (updated dynamically).
        if _is_mac_root:
            self._title_bar.setVisible(False)
            self._title_bar.setFixedHeight(0)
            from PySide6.QtWidgets import QMenuBar
            self._mac_menu_bar = QMenuBar(self)
            
            # Project Menu
            self._mac_menu_project = self._mac_menu_bar.addMenu(self.txt("titlebar_project"))
            self._mac_action_export_proj = self._mac_menu_project.addAction(self.txt("titlebar_export_project"))
            self._mac_action_export_proj.triggered.connect(self._on_export_project)
            self._mac_action_import_proj = self._mac_menu_project.addAction(self.txt("titlebar_import_project"))
            self._mac_action_import_proj.triggered.connect(self._on_import_project)
            self._mac_menu_project.menuAction().setVisible(False)

            # Transcript Menu
            self._mac_menu_transcript = self._mac_menu_bar.addMenu(self.txt("titlebar_transcript"))
            self._mac_action_export_txt = self._mac_menu_transcript.addAction(self.txt("titlebar_export_txt"))
            self._mac_action_export_txt.triggered.connect(self._on_export_transcript_txt)
            self._mac_action_copy = self._mac_menu_transcript.addAction(self.txt("titlebar_copy_clipboard"))
            self._mac_action_copy.triggered.connect(self._on_copy_transcript_clipboard)
            self._mac_menu_transcript.addSeparator()
            self._mac_action_copy_ai = self._mac_menu_transcript.addAction(self.txt("titlebar_copy_ai_transcript"))
            self._mac_action_copy_ai.triggered.connect(self._on_copy_ai_transcript)
            self._mac_action_export_ai = self._mac_menu_transcript.addAction(self.txt("titlebar_export_ai_transcript"))
            self._mac_action_export_ai.triggered.connect(self._on_export_ai_transcript)
            self._mac_action_import_story = self._mac_menu_transcript.addAction(self.txt("titlebar_import_ai_story"))
            self._mac_action_import_story.triggered.connect(self._on_import_ai_story)
            self._mac_menu_transcript.menuAction().setVisible(False)

            # Source Info Menu
            self._mac_menu_source = self._mac_menu_bar.addMenu("Source")
            self._mac_action_timeline = self._mac_menu_source.addAction("Timeline: None")
            self._mac_action_timeline.setEnabled(False)
            self._mac_action_track = self._mac_menu_source.addAction("Track: None")
            self._mac_action_track.setEnabled(False)
            self._mac_menu_source.menuAction().setVisible(False)
            
            # Edit Menu
            self._mac_menu_edits = self._mac_menu_bar.addMenu(self.txt("titlebar_edit"))
            self._mac_menu_edits.menuAction().setVisible(False)
            
            self._mac_menu_bar.setNativeMenuBar(True)
            try:
                import sys
                is_standalone = not (
                    hasattr(sys.modules.get('__main__'), 'resolve') or
                    hasattr(sys.modules.get('builtins'), 'resolve') or
                    hasattr(sys.modules.get('__main__'), 'bmd') or
                    hasattr(sys.modules.get('builtins'), 'bmd') or
                    'fscript' in sys.executable.lower() or
                    os.environ.get('RESOLVE_SCRIPT_API') is not None
                )
                if is_standalone:
                    from .utils import setup_macos_standalone_identity
                    setup_macos_standalone_identity(config.APP_NAME)
            except Exception:
                pass


        # --- Build UI --- (sidebars + central workspace sit below title bar)
        self._build_sidebars()         # left + right activity frames
        self._build_central_workspace() # QStackedWidget central area + panels


        self.search_overlay = SearchOverlayWidget(self.scroll_area, self)

        self.undo_manager = UndoManager(self, self.text_canvas)
        self._setup_hardcoded_shortcuts()
        
        # Install global app event filter for robust media shortcuts
        QApplication.instance().installEventFilter(self)

        self._active_shortcuts = []  # track dynamic QShortcuts for cleanup
        self._apply_dynamic_shortcuts()

        # --- Maximize on the monitor the cursor is on ---
        self._maximize_on_active_screen(show=False)

        prefs_init = self.engine.load_preferences() or {}
        if prefs_init.get('always_on_top'):
            self._apply_always_on_top(True)

        # --- Telemetry check fires 500 ms after first paint ---
        QTimer.singleShot(500, self.check_telemetry)

        # --- Auto-update check fires 1500 ms after first paint (after telemetry) ---
        QTimer.singleShot(1500, self._start_update_check)

        # --- Populate timeline/track dropdowns synchronously since Resolve API is fast ---
        self._populate_timeline_track_combos()
        
        self._bind_prefs()

    def _update_mac_chapter_menu(self):
        if not getattr(self, '_is_mac', False) or not hasattr(self, '_mac_menu_edits'):
            return
            
        from PySide6.QtGui import QActionGroup
        if not hasattr(self, '_mac_menu_edits_group'):
            self._mac_menu_edits_group = QActionGroup(self)
            self._mac_menu_edits_group.setExclusive(True)
            
        for act in self._mac_menu_edits_group.actions():
            self._mac_menu_edits_group.removeAction(act)
        self._mac_menu_edits.clear()
        
        if hasattr(self, '_title_bar') and hasattr(self._title_bar, 'chapter_dropdown'):
            for chap in self._title_bar.chapter_dropdown.options_list:
                action = self._mac_menu_edits.addAction(chap)
                action.setCheckable(True)
                self._mac_menu_edits_group.addAction(action)
                if chap == self._title_bar.chapter_dropdown.currentText():
                    action.setChecked(True)
                action.triggered.connect(lambda checked, c=chap: self._switch_chapter(c))

    def _save_single_pref(self, key: str, value):
        prefs = self.engine.load_preferences() or {}
        prefs[key] = value
        self.engine.save_preferences(prefs)

    def _bind_prefs(self):
        prefs = self.engine.load_preferences() or {}
        
        toggles = [
            ('ui_tgl_silence_cut', 'tgl_silence_cut'),
            ('ui_tgl_silence_mark', 'tgl_silence_mark'),
            ('ui_tgl_show_inaudible', 'tgl_show_inaudible'),
            ('ui_tgl_mark_inaudible', 'tgl_mark_inaudible'),
            ('ui_tgl_show_typos', 'tgl_show_typos'),
            ('ui_tgl_ripple_delete', 'tgl_ripple_delete')
        ]
        
        for key, attr_name in toggles:
            if hasattr(self, attr_name):
                toggle = getattr(self, attr_name)
                if key in prefs:
                    toggle.setChecked(prefs[key], animated=False)
                toggle.toggled.connect(lambda v, k=key: self._save_single_pref(k, v))
                
        if hasattr(self, 'spin_thresh'):
            if 'silence_threshold_db' in prefs:
                self.spin_thresh.setText(str(prefs['silence_threshold_db']))
            elif 'ui_spin_thresh' in prefs:
                self.spin_thresh.setText(str(prefs['ui_spin_thresh']))
            self.spin_thresh.editingFinished.connect(
                lambda: self._save_single_pref('silence_threshold_db',
                    float(self.spin_thresh.text().replace(',', '.') or -42.0))
            )

        if hasattr(self, 'spin_pad'):
            if 'ui_spin_pad' in prefs:
                self.spin_pad.setText(str(prefs['ui_spin_pad']))
            self.spin_pad.editingFinished.connect(
                lambda: self._save_single_pref('ui_spin_pad',
                    float(self.spin_pad.text().replace(',', '.') or 0.05))
            )

        if hasattr(self, 'spin_silence_min_dur'):
            if 'silence_min_dur' in prefs:
                self.spin_silence_min_dur.setText(str(prefs['silence_min_dur']))
            self.spin_silence_min_dur.editingFinished.connect(
                lambda: (self._save_single_pref('silence_min_dur',
                    float(self.spin_silence_min_dur.text().replace(',', '.') or 0.2)),
                    self._refresh_cut_preview())
            )

        
        # Restore pinned favorites
        for fav_id in prefs.get('favorites', []):
            if fav_id in self._pin_buttons:
                self._pin_buttons[fav_id].click()

        self._settings_dialog = None
        QTimer.singleShot(200, self._preload_settings)

    def _get_settings_dialog(self):
        if not hasattr(self, '_settings_dialog') or self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.engine, self)
        else:
            self._settings_dialog._reload_preferences()
        is_top = getattr(self, '_always_on_top_active', False) or bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        if bool(self._settings_dialog.windowFlags() & Qt.WindowStaysOnTopHint) != is_top:
            self._settings_dialog.setWindowFlag(Qt.WindowStaysOnTopHint, is_top)
        return self._settings_dialog

    def _preload_settings(self):
        try:
            if not hasattr(self, '_settings_dialog') or self._settings_dialog is None:
                self._settings_dialog = SettingsDialog(self.engine, self)
                # Pre-build all pages into RAM so open is 0ms
                for i in range(self._settings_dialog.category_list.count()):
                    self._settings_dialog._ensure_page_built(i)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._enforce_native_always_on_top()
        self._sync_script_edit_height(animated=False)

    def moveEvent(self, event):
        super().moveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_script_edit_height(animated=False)
        if hasattr(self, 'audio_preview') and self.audio_preview:
            self.audio_preview.update_seek_margins()

    def animate_script_edit_height(self, target_h: int, duration: int = 260):
        if not hasattr(self, 'welcome_script_edit'):
            return
        if getattr(self, '_script_h_anim', None) and self._script_h_anim.state() == QVariantAnimation.Running:
            self._script_h_anim.stop()

        start_h = self.welcome_script_edit.height()
        if start_h == target_h or duration <= 0:
            self.welcome_script_edit.setFixedHeight(target_h)
            return

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(start_h)
        anim.setEndValue(target_h)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.valueChanged.connect(lambda h: self.welcome_script_edit.setFixedHeight(int(h)))
        def _on_finish():
            self.welcome_script_edit.setFixedHeight(target_h)
        anim.finished.connect(_on_finish)
        self._script_h_anim = anim
        anim.start()

    def _sync_script_edit_height(self, animated: bool = False, duration: int = 0):
        if not hasattr(self, 'welcome_script_edit'):
            return
        try:
            from PySide6.QtCore import QPoint
            parent_ref = getattr(self, 'slider_widget', None)
            ref_widget = getattr(self, 'tgl_more_accurate', None) or getattr(self, 'w_row_acc', None)
            target_h = 0
            if ref_widget and parent_ref and self.welcome_script_edit.parentWidget():
                bottom_pt = ref_widget.mapTo(parent_ref, QPoint(0, ref_widget.height()))
                top_y = self.welcome_script_edit.mapTo(parent_ref, QPoint(0, 0)).y()
                if top_y <= 0:
                    top_y = config.S(18) + config.S(4)
                calc_h = bottom_pt.y() - top_y
                if calc_h > config.S(50):
                    target_h = calc_h

            if not target_h:
                is_standalone = getattr(self, 'is_standalone', True)
                target_h = config.S(333) if is_standalone else config.S(267)

            if target_h > config.S(50):
                if animated and duration > 0:
                    self.animate_script_edit_height(target_h, duration)
                else:
                    self.welcome_script_edit.setFixedHeight(target_h)
        except Exception as e:
            from osdoc import log_error
            log_error(f"_sync_script_edit_height error: {e}")

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.WindowStateChange, QEvent.ActivationChange):
            self._enforce_native_always_on_top()

    def _enforce_native_always_on_top(self):
        try:
            prefs = self.engine.load_preferences() or {}
            is_top = getattr(self, '_always_on_top_active', False) or prefs.get('always_on_top', False)
            if is_top and hasattr(self, 'engine') and hasattr(self.engine, 'os_doc'):
                self.engine.os_doc.set_always_on_top(int(self.winId()), True)
        except Exception:
            pass

    def _apply_always_on_top(self, enable: bool):
        self._always_on_top_active = bool(enable)
        native_ok = False
        try:
            win_id = int(self.winId())
            if win_id and hasattr(self, 'engine') and hasattr(self.engine, 'os_doc'):
                native_ok = self.engine.os_doc.set_always_on_top(win_id, enable)
        except Exception:
            native_ok = False

        # If native method was not supported (e.g. Wayland) or window isn't created/visible yet, use Qt window flags
        if not native_ok or not self.isVisible():
            self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
            if self.isVisible():
                if self.isMaximized():
                    self.showMaximized()
                elif self.isFullScreen():
                    self.showFullScreen()
                else:
                    self.show()


    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_sidebars(self):
        """
        Left and right vertical activity frames overlaying the main window.
        """
        self._sidebar_left = _NeverShown(self)
        self._sidebar_left.setFixedWidth(config.SIDEBAR_WIDTH)
        self._sidebar_left.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        left_layout = QVBoxLayout(self._sidebar_left)
        left_layout.setContentsMargins(0, config.S(6), 0, config.S(6))
        left_layout.setSpacing(config.S(6))
        left_layout.setAlignment(Qt.AlignHCenter)
        
        self._drag_zone_left = SidebarDragZone(self._sidebar_left)
        drag_layout_left = self._drag_zone_left.layout()
        drag_layout_left.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        left_layout.addWidget(self._drag_zone_left)
        
        self.btn_nav_script = SidebarButton("\U0001f4dd", self.txt("tool_script_analysis"), "script_analysis", tooltip_widget=self.shared_tooltip)
        self.btn_nav_script.clicked.connect(lambda: self._toggle_activity("script_analysis"))
        drag_layout_left.addWidget(self.btn_nav_script, 0, Qt.AlignHCenter)
        
        self.btn_nav_silence = SidebarButton("\U0001f507", self.txt("tool_silence"), "silence", tooltip_widget=self.shared_tooltip)
        self.btn_nav_silence.clicked.connect(lambda: self._toggle_activity("silence"))
        drag_layout_left.addWidget(self.btn_nav_silence, 0, Qt.AlignHCenter)

        self.btn_nav_fillers = SidebarButton("\U0001f4ac", self.txt("tool_filler_words"), "fillers", tooltip_widget=self.shared_tooltip)
        self.btn_nav_fillers.clicked.connect(lambda: self._toggle_activity("fillers"))
        drag_layout_left.addWidget(self.btn_nav_fillers, 0, Qt.AlignHCenter)
        
        self.btn_nav_settings = SidebarButton("\u2699", self.txt("tool_settings"), "settings", tooltip_widget=self.shared_tooltip, is_draggable=False)
        self.btn_nav_settings.clicked.connect(lambda: self._on_settings())
        left_layout.addWidget(self.btn_nav_settings, 0, Qt.AlignHCenter)
        
        self._sidebar_left.show()

        self._sidebar_right = _NeverShown(self)
        self._sidebar_right.setFixedWidth(config.SIDEBAR_WIDTH)
        self._sidebar_right.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        right_layout = QVBoxLayout(self._sidebar_right)
        right_layout.setContentsMargins(0, config.S(6), 0, config.S(6))
        right_layout.setSpacing(config.S(6))
        right_layout.setAlignment(Qt.AlignHCenter)
        
        self._drag_zone_right = SidebarDragZone(self._sidebar_right)
        drag_layout_right = self._drag_zone_right.layout()
        drag_layout_right.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        right_layout.addWidget(self._drag_zone_right)
        
        self.btn_nav_main = SidebarButton("\U0001f6e0\ufe0f", self.txt("tool_main_panel"), "main_panel", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_main.clicked.connect(lambda: self._toggle_activity("main_panel"))
        drag_layout_right.addWidget(self.btn_nav_main, 0, Qt.AlignHCenter)
        
        self.btn_nav_assembly = SidebarButton("\u2699\ufe0f", self.txt("tool_assembly"), "assembly", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_assembly.clicked.connect(lambda: self._toggle_activity("assembly"))
        drag_layout_right.addWidget(self.btn_nav_assembly, 0, Qt.AlignHCenter)

        self.btn_nav_story = SidebarButton("\U0001f3ac", self.txt("tool_story"), "story", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_story.clicked.connect(lambda: self._toggle_activity("story"))
        drag_layout_right.addWidget(self.btn_nav_story, 0, Qt.AlignHCenter)

        self._restore_sidebar_layout()
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, self._check_crash_recovery)
        QTimer.singleShot(1500, self._start_mcp_bridge)
        # Title bar chip: Resolve connected or not
        self._resolve_chip_timer = QTimer(self)
        self._resolve_chip_timer.setInterval(3000)
        self._resolve_chip_timer.timeout.connect(self._update_resolve_chip)
        self._resolve_chip_timer.start()
        QTimer.singleShot(600, self._update_resolve_chip)

        
    def _start_mcp_bridge(self):
        """Let AI assistants (Claude Desktop / Claude Code, via mcp_server/storycraft_mcp.py) work with this window."""
        if getattr(self, '_mcp_bridge', None) or not (self.engine.load_preferences() or {}).get('mcp_enabled', True):
            return
        try:
            from handlers.mcp_bridge import McpBridge
            from gui.mcp_tools import build_tools
            self._mcp_bridge = McpBridge(build_tools(self), self.engine.os_doc.install_dir, self)
        except Exception as e:
            from osdoc import log_error
            log_error(f"AI assistant bridge not started: {e}")

    def _check_crash_recovery(self):
        import os, json
        from PySide6.QtWidgets import QDialog
        self._crash_state = 'checking'

        flag_path = os.path.join(self.engine.os_doc.get_autosave_dir(), '.clean_exit')
        meta_path = os.path.join(self.engine.os_doc.get_autosave_dir(), 'recovery_meta.json')
        save_path = os.path.join(self.engine.os_doc.get_autosave_dir(), 'recovery.bws')
        
        crashed = False
        if not os.path.exists(flag_path) and os.path.exists(meta_path) and os.path.exists(save_path):
            crashed = True
        self._crash_state = 'crashed' if crashed else 'clean'

        if crashed:
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                
                proj_name = meta.get('project_name', 'Unknown')
                timestamp = meta.get('timestamp', 'Unknown time')
                
                msg_text = self.txt('msg_crash_desc').format(project=proj_name, time=timestamp)
                msg_box = WorkspaceWarningOverlay(
                    self._stack,
                    self.txt('msg_crash_title'),
                    msg_text,
                    self.txt('btn_restore'),
                    btn_cancel_text=self.txt('btn_discard')
                )
                if msg_box.exec() == QDialog.Accepted:
                    # Restore project
                    self._on_import_project(override_path=save_path)
            except Exception as e:
                from osdoc import log_error
                log_error(f"Failed to check crash recovery: {e}")
                
        # Now that we've checked, remove the flag if it exists, so next exit must be clean to rewrite it
        try:
            if os.path.exists(flag_path):
                os.remove(flag_path)
        except Exception:
            pass

    def _build_central_workspace(self):
        """
        Main container incorporating sidebars, panels, and central stack using QHBoxLayout.
        """
        main_container = QWidget()
        main_container.setObjectName("MainContainer")
        main_container.setAttribute(Qt.WA_StyledBackground, True)
        main_container.setStyleSheet(f"#MainContainer {{ background-color: {config.BG_COLOR}; }}")
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Build Panels
        self._panel_left = _NeverShown()
        self._panel_left.setMinimumWidth(config.S(150))
        self._panel_left.setObjectName("leftPanel")
        self._panel_left.setStyleSheet(f"QFrame#leftPanel {{ background-color: {config.BG_COLOR}; }} QFrame#ActivityPanel {{ background-color: #212121; border-radius: {config.S(6)}px; }}")
        QVBoxLayout(self._panel_left).setContentsMargins(0, 0, 0, 0)
        self._panel_left.hide()

        self._stack = QStackedWidget()
        self._stack.setObjectName("stack")
        self._stack.setStyleSheet(f"QStackedWidget#stack {{ background-color: {config.BG_COLOR}; }}")
        self._stack.addWidget(self._build_welcome_screen())   # index 0
        self._stack.addWidget(self._build_page_processing())  # index 1
        self._stack.addWidget(self._build_page_editor())      # index 2
        self._stack.setCurrentIndex(0)

        self._panel_right = QFrame()
        self._panel_right.setMinimumWidth(config.S(150))
        self._panel_right.setObjectName("rightPanel")
        self._panel_right.setStyleSheet(f"QFrame#rightPanel {{ background-color: {config.BG_COLOR}; }} QFrame#ActivityPanel {{ background-color: #212121; border-radius: {config.S(6)}px; }}")
        QVBoxLayout(self._panel_right).setContentsMargins(0, 0, 0, 0)
        self._build_inspector_tabs()
        self._panel_right.hide()
        
        self.activities = {}
        self.active_activity = None
        self._build_activities()
        
        if hasattr(self, 'welcome_script_edit') and hasattr(self, 'text_script'):
            def sync_scripts(source, target):
                if source.toPlainText() != target.toPlainText():
                    target.setText(source.toPlainText())
            
            self.welcome_script_edit.textChanged.connect(lambda: sync_scripts(self.welcome_script_edit, self.text_script))
            self.text_script.textChanged.connect(lambda: sync_scripts(self.text_script, self.welcome_script_edit))
            if self.text_script.toPlainText():
                self.welcome_script_edit.setText(self.text_script.toPlainText())


        # Splitter layout for panels and stack
        self._main_h_splitter = GripSplitter(Qt.Horizontal)
        self._main_h_splitter.setChildrenCollapsible(False)
        self._main_h_splitter.addWidget(self._panel_left)
        self._main_h_splitter.addWidget(self._stack)
        self._main_h_splitter.addWidget(self._panel_right)
        self._main_h_splitter.setStretchFactor(0, 0)
        self._main_h_splitter.setStretchFactor(1, 1)
        self._main_h_splitter.setStretchFactor(2, 0)

        self._main_h_splitter.setHandleWidth(config.S(6))
        self._main_h_splitter.setStyleSheet("QSplitter { border: none; background: transparent; }")

        # Add everything to main layout in exact order
        main_layout.addWidget(self._sidebar_left)
        main_layout.addWidget(self._main_h_splitter)
        main_layout.addWidget(self._sidebar_right)

        # ── CSD: add content area under the title bar in the root frame ───────
        self._root_layout.addWidget(main_container, 1)

        # ── Full-width Bottom Media Preview & Playback Dock ──────────────────
        from gui.components.audio_preview import AudioPreviewWidget
        self.audio_preview = AudioPreviewWidget(self._root_frame, self)
        self.waveform_timeline = getattr(self.audio_preview, 'waveform_timeline', None)
        self._root_layout.addWidget(self.audio_preview, 0)
        self._main_h_splitter.splitterMoved.connect(lambda *_: self.audio_preview.update_seek_margins())

        self.setCentralWidget(self._root_frame)


    # ── Inspector: every panel, one at a time, in the right-hand panel under a row of tabs ──
    _INSPECTOR_TABS = (("assembly", "insp_found"), ("story", "insp_story"), ("silence", "insp_pauses"),
                       ("fillers", "insp_fillers"), ("script_analysis", "insp_script"), ("main_panel", "insp_markers"))

    def _build_inspector_tabs(self):
        lay = self._panel_right.layout()
        lay.setContentsMargins(config.S(8), config.S(8), config.S(10), 0)
        lay.setSpacing(config.S(8))
        bar = QFrame(self._panel_right)
        bar.setObjectName("InspectorTabs")
        bar.setStyleSheet(f"""
            QFrame#InspectorTabs {{ background-color: #262626; border-radius: {config.S(10)}px; }}
            QPushButton#InspTab {{ background: transparent; color: #9a9a9a; border: none; border-radius: {config.S(7)}px;
                padding: {config.S(5)}px {config.S(3)}px; font-size: {config.FS(8.5)}pt; }}
            QPushButton#InspTab:hover {{ color: #ffffff; }}
            QPushButton#InspTab:checked {{ background: #383838; color: #ffffff; font-weight: bold; }}
            QPushButton#InspClose {{ background: transparent; color: #8a8a8a; border: none; font-size: {config.FS(11)}pt;
                padding: 0 {config.S(4)}px; }}
            QPushButton#InspClose:hover {{ color: #ffffff; }}
        """)
        row = QHBoxLayout(bar)
        row.setContentsMargins(config.S(3), config.S(3), config.S(3), config.S(3))
        row.setSpacing(config.S(2))
        self._inspector_tabs = {}
        for key, label in self._INSPECTOR_TABS:
            b = QPushButton(self.txt(label), bar)
            b.setObjectName("InspTab")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._open_activity(k))
            row.addWidget(b, 1)
            self._inspector_tabs[key] = b
        close = QPushButton("\u00d7", bar)
        close.setObjectName("InspClose")
        close.setCursor(Qt.PointingHandCursor)
        close.setToolTip(self.txt("insp_close"))
        close.clicked.connect(self._close_inspector)
        row.addWidget(close)
        lay.addWidget(bar)
        self._inspector_host = QWidget(self._panel_right)
        host = QVBoxLayout(self._inspector_host)
        host.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._inspector_host, 1)

    def _sync_inspector_tabs(self, activity_id):
        for key, b in getattr(self, '_inspector_tabs', {}).items():
            b.setChecked(key == activity_id)

    def _after_side_panel_change(self):
        current_page = self._stack.currentWidget()
        if current_page and hasattr(current_page, 'resizeEvent'):
            current_page.resizeEvent(None)
        if hasattr(self, 'audio_preview') and self.audio_preview:
            self.audio_preview.update_seek_margins()

    def _close_inspector(self):
        for widget in self.findChildren(SidebarButton):
            widget.set_active(False)
        self._sync_inspector_tabs(None)
        self._panel_right.hide()
        self._after_side_panel_change()

    def _toggle_activity(self, activity_id: str):
        """Open a panel in the inspector, or close the inspector if that panel is the one open."""
        target_btn = next((w for w in self.findChildren(SidebarButton) if w.activity_id == activity_id), None)
        if target_btn is None or activity_id not in self.activities:
            return
        panel = self._panel_right
        if target_btn.is_active and panel.isVisible():
            self._close_inspector()
            return
        for widget in self.findChildren(SidebarButton):
            widget.set_active(False)
        target_btn.set_active(True)
        self._sync_inspector_tabs(activity_id)
        activity_widget = self.activities[activity_id]
        layout = self._inspector_host.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        layout.addWidget(activity_widget)
        activity_widget.show()

        was_hidden = not panel.isVisible()
        panel.show()
        if was_hidden:
            sizes = self._main_h_splitter.sizes()
            win_w = max(800, self.width())
            # Wider than the old side panels: the inspector holds every tool (~340 px at 1920)
            target_w = max(config.S(360), int(win_w * (380.0 / 1920.0)))
            try:
                if activity_widget.layout():
                    target_w = max(target_w, activity_widget.layout().minimumSize().width() + config.S(18))
            except Exception:
                pass
            diff = target_w - sizes[2]
            sizes[2] = target_w
            sizes[1] = max(0, sizes[1] - diff)
            self._main_h_splitter.setSizes(sizes)
        self._after_side_panel_change()

    def _save_sidebar_layout(self):
        prefs = self.engine.load_preferences() or {}

        left_order = []
        for i in range(self._drag_zone_left.layout().count()):
            w = self._drag_zone_left.layout().itemAt(i).widget()
            if isinstance(w, SidebarButton): left_order.append(w.activity_id)

        right_order = []
        for i in range(self._drag_zone_right.layout().count()):
            w = self._drag_zone_right.layout().itemAt(i).widget()
            if isinstance(w, SidebarButton): right_order.append(w.activity_id)

        prefs['sidebar_left'] = left_order
        prefs['sidebar_right'] = right_order
        self.engine.save_preferences(prefs)

    def _restore_sidebar_layout(self):
        prefs = self.engine.load_preferences() or {}
        left_saved = prefs.get('sidebar_left', [])
        right_saved = prefs.get('sidebar_right', [])

        if not left_saved and not right_saved: return

        # Zmapuj i wyczyść obecne przyciski
        btns_map = {}
        home_right = {}
        for dz in [self._drag_zone_left, self._drag_zone_right]:
            layout = dz.layout()
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if isinstance(w, SidebarButton):
                    btns_map[w.activity_id] = w
                    home_right[w.activity_id] = dz is self._drag_zone_right
                    layout.removeWidget(w)

        # Odtwórz poprawną kolejność dla lewej strony
        for act_id in left_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = False
                self._drag_zone_left.layout().addWidget(btn, 0, Qt.AlignHCenter)

        # Odtwórz poprawną kolejność dla prawej strony
        for act_id in right_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = True
                self._drag_zone_right.layout().addWidget(btn, 0, Qt.AlignHCenter)

        # Resztki (nowe funkcje) lądują po stronie, na której zostały utworzone
        for act_id, btn in btns_map.items():
            btn.is_right_side = home_right.get(act_id, False)
            zone = self._drag_zone_right if btn.is_right_side else self._drag_zone_left
            zone.layout().addWidget(btn, 0, Qt.AlignHCenter)

    def _build_activities(self):
        from gui.panels import (
            build_script_panel, build_silence_panel, build_fillers_panel,
            build_main_workspace_panel, build_assembly_panel, build_story_panel
        )
        self._favorite_proxies = {}
        self._pin_buttons = {}

        self.activities["script_analysis"] = build_script_panel(self)
        self.activities["silence"] = build_silence_panel(self)
        self.activities["fillers"] = build_fillers_panel(self)
        self.activities["main_panel"] = build_main_workspace_panel(self)
        self.activities["assembly"] = build_assembly_panel(self)
        self.activities["story"] = build_story_panel(self)

        self.btn_analyze_standalone.installEventFilter(self)
        self.btn_clear_transcript.installEventFilter(self)

        # Signal Connections
        self.btn_import_script.clicked.connect(self._on_import_script)
        self.btn_clear_script.clicked.connect(self._on_clear_script)
        self.btn_analyze_compare.clicked.connect(self._on_analyze_compare)
        self.btn_side_by_side_compare.clicked.connect(self._on_side_by_side_compare)
        self.btn_analyze_standalone.clicked.connect(self._on_analyze_standalone)
        self.tgl_auto_filler.toggled.connect(self._on_auto_filler_toggled)
        self.btn_assemble.assembleClicked.connect(self._on_assemble)
        
    def _is_input_widget(self, w=None):
        if w is None:
            from PySide6.QtWidgets import QApplication
            w = QApplication.focusWidget()
        if w is None:
            return False
        from PySide6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox
        if isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox)):
            return True
        meta = w.metaObject()
        while meta:
            cname = meta.className()
            if any(k in cname for k in ('Edit', 'Input', 'Spin', 'Text', 'Search')):
                return True
            meta = meta.superClass()
        return False

    def _update_shortcut_enabled_states(self):
        from PySide6.QtWidgets import QApplication
        active = self.isActiveWindow() and QApplication.activeWindow() is not None
        in_input = self._is_input_widget()
        enable_shortcuts = active and not in_input

        for sc in getattr(self, '_active_shortcuts', []):
            try:
                sc.setEnabled(enable_shortcuts)
            except RuntimeError:
                pass

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QApplication
        
        if event.type() == QEvent.Type.KeyPress:
            if not self.isActiveWindow() or QApplication.activeWindow() is None:
                return super().eventFilter(watched, event)
            if self._is_input_widget():
                return super().eventFilter(watched, event)
            if hasattr(self, 'audio_preview') and getattr(self.audio_preview, 'is_preview_active', lambda: False)():
                try:
                    from PySide6.QtGui import QKeySequence
                    prefs = self.engine.load_preferences() or {}
                    scs = prefs.get('shortcuts', {}) if isinstance(prefs, dict) else {}
                    play_key = scs.get('play_stop', 'Space')
                    back_key = scs.get('skip_backward', 'Left')
                    fwd_key  = scs.get('skip_forward', 'Right')
                    
                    key_val = event.key()
                    mods = event.modifiers()
                    mod_val = mods.value if hasattr(mods, 'value') else int(mods)
                    combo = key_val | mod_val
                    seq_str = QKeySequence(combo).toString()
                    
                    if play_key and seq_str == play_key:
                        self.audio_preview.toggle_play()
                        return True
                    elif back_key and seq_str == back_key:
                        self.audio_preview.skip_backward()
                        return True
                    elif fwd_key and seq_str == fwd_key:
                        self.audio_preview.skip_forward()
                        return True
                except Exception:
                    pass
                        
        if event.type() == QEvent.Type.Enter:
            if watched == getattr(self, 'btn_analyze_standalone', None):
                self.shared_tooltip.show_at(watched, self.txt("tooltip_standalone"), is_right_side=False)
            elif watched == getattr(self, 'btn_clear_transcript', None):
                self.shared_tooltip.show_at(watched, self.txt("tooltip_clear_all_markings"), is_right_side=True)
        elif event.type() == QEvent.Type.Leave:
            if watched in (getattr(self, 'btn_analyze_standalone', None), getattr(self, 'btn_clear_transcript', None)):
                self.shared_tooltip.hide()
                
        return super().eventFilter(watched, event)


    # Removed deprecated _on_nav_script and _on_nav_analysis

    # ------------------------------------------------------------------
    # UI Logic Methods
    # ------------------------------------------------------------------

    def _jump_playhead(self, timestamp_s):
        rh = getattr(self.engine, 'resolve_handler', None) if self.engine else None
        if not rh: return
        
        tl_name = None
        if getattr(self, '_current_chapter_idx', -1) >= 0 and self._chapters:
            tl_name = self._chapters[self._current_chapter_idx].get("tl_name")
        elif getattr(self, '_transcription_source', None):
            tl_name = self._transcription_source.get("timeline_name")
        
        rh.jump_to_seconds(timestamp_s, timeline_name=tl_name, async_exec=True)

    def _on_waveform_seek_requested(self, timestamp_s: float, sync_resolve: bool = False):
        """
        Handles playhead seek / scrubbing from the WaveformTimelineWidget.
        Synchronizes the local BadWords audio player.
        Only syncs DaVinci Resolve playhead if explicitly requested (e.g. Ctrl + Click).
        """
        # 1. Update local audio preview playback position
        if hasattr(self, 'audio_preview') and self.audio_preview:
            self.audio_preview.seek_source_time(timestamp_s)

        # 2. Update DaVinci Resolve playhead ONLY when explicitly requested via shortcut (Ctrl + Click)
        if sync_resolve:
            self._jump_playhead(timestamp_s)

    def _on_import_script(self):
        from PySide6.QtWidgets import QFileDialog
        import algorithms
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Script", "", 
            "Text/Word/PDF Files (*.txt *.docx *.pdf);;All Files (*)"
        )
        if not file_path: return
        
        ext = file_path.split('.')[-1].lower()
        content = ""
        
        if ext == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == 'docx':
            if hasattr(algorithms, 'read_docx_text'):
                content = algorithms.read_docx_text(file_path)
        elif ext == 'pdf':
            if hasattr(algorithms, 'read_pdf_text'):
                content = algorithms.read_pdf_text(file_path)
            
        self.text_script.setText(content)

    def _on_clear_script(self):
        self.text_script.clear()

    def _on_analyze_compare(self):
        script_text = self.text_script.toPlainText().strip()
        if not script_text:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_please_import_or_paste_a"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        self.editor_view_stack.setCurrentIndex(1)
        if hasattr(self, 'sbs_loading_bar'):
            self.sbs_loading_bar.set_value(-1)
            
        def _finish_analyze(updated_words):
            self.text_canvas.load_data(updated_words)
            self._show_transcript_view()
            self._analyze_thread = None
            QTimer.singleShot(150, lambda: self.editor_view_stack.setCurrentIndex(0))
            
        from PySide6.QtCore import QThread, Signal as _Signal
        
        class _AnalyzeThread(QThread):
            finished_ok = _Signal(list)
            
            def __init__(self, engine, script_text, current_words):
                super().__init__()
                self.engine = engine
                self.script_text = script_text
                self.current_words = current_words
                
            def run(self):
                updated_words = self.engine.run_comparison_analysis(self.script_text, self.current_words)
                self.finished_ok.emit(updated_words)
                
        self._analyze_thread = _AnalyzeThread(self.engine, script_text, self.text_canvas.words_data)
        self._analyze_thread.finished_ok.connect(_finish_analyze)
        self._analyze_thread.start()

    def _on_side_by_side_compare(self):
        if getattr(self, '_is_sbs_active', False):
            self._exit_side_by_side()
            return

        script_text = self.text_script.toPlainText().strip()
        if not script_text:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_please_import_or_paste_a"), self.txt("btn_ok"))
            dlg.exec()
            return

        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return

        self._is_sbs_active = True

        self.text_script.hide()
        self.btn_import_script.hide()
        self.btn_clear_script.hide()
        self.btn_analyze_compare.hide()
        self.btn_analyze_standalone.hide()
        self.btn_side_by_side_compare.hide()
        if getattr(self, 'script_actions_card', None) is not None: self.script_actions_card.hide()

        self.btn_exit_sbs_text.show()

        for widget in self.findChildren(SidebarButton):
            if not widget.is_right_side and widget.is_active:
                widget.set_active(False)
        self._sbs_left_was_visible = self._panel_left.isVisible()
        self._sbs_left_sizes = self._main_h_splitter.sizes()
        self._panel_left.hide()

        self.editor_view_stack.setCurrentIndex(1)
        if hasattr(self, 'sbs_loading_bar'):
            self.sbs_loading_bar.set_value(-1)

        import algorithms
        curr_script_hash = " ".join(algorithms.super_clean(w) for w in script_text.split() if algorithms.super_clean(w))

        def _finish_sbs(rows, updated_words):
            self.text_canvas.words_data = updated_words
            self._sbs_last_script_hash = curr_script_hash
            
            self.text_canvas.is_sbs_mode = True
            self.text_canvas.sbs_rows = rows
            self.text_canvas._calculate_layout()
            self.text_canvas.update()
            
            self._sbs_thread = None
            if hasattr(self, 'sbs_loading_bar'):
                self.sbs_loading_bar.set_value(100)
            QTimer.singleShot(150, lambda: self.editor_view_stack.setCurrentIndex(0))

        if getattr(self, '_sbs_last_script_hash', None) == curr_script_hash:
            # Core script words haven't changed! Skip the heavy comparison analysis.
            self.text_canvas.is_sbs_mode = True
            self.text_canvas.sbs_rows = algorithms.build_side_by_side_alignment(script_text, self.text_canvas.words_data)
            self.text_canvas._calculate_layout()
            self.text_canvas.update()
            if hasattr(self, 'sbs_loading_bar'):
                self.sbs_loading_bar.set_value(100)
            QTimer.singleShot(150, lambda: self.editor_view_stack.setCurrentIndex(0))
        else:
            from PySide6.QtCore import QThread, Signal as _Signal
            
            class _SBSThread(QThread):
                finished_ok = _Signal(object, object)
                
                def __init__(self, engine, script_text, current_words):
                    super().__init__()
                    self.engine = engine
                    self.script_text = script_text
                    self.current_words = current_words
                    
                def run(self):
                    import algorithms
                    updated_words = self.engine.run_comparison_analysis(self.script_text, self.current_words)
                    rows = algorithms.build_side_by_side_alignment(self.script_text, updated_words)
                    self.finished_ok.emit(rows, updated_words)

            self._sbs_thread = _SBSThread(self.engine, script_text, self.text_canvas.words_data)
            self._sbs_thread.finished_ok.connect(_finish_sbs)
            self._sbs_thread.start()

    def _exit_side_by_side(self):
        self._is_sbs_active = False
        self.text_canvas.is_sbs_mode = False
        self.text_canvas._calculate_layout()
        self.text_canvas.update()
        
        self.btn_exit_sbs_text.hide()

        self.text_script.show()
        self.btn_import_script.show()
        self.btn_clear_script.show()
        self.btn_analyze_compare.show()
        self.btn_analyze_standalone.show()
        self.btn_side_by_side_compare.show()
        if getattr(self, 'script_actions_card', None) is not None: self.script_actions_card.show()

        # Restore left panel
        if getattr(self, '_sbs_left_was_visible', False):
            self._panel_left.show()
            if hasattr(self, '_sbs_left_sizes'):
                self._main_h_splitter.setSizes(self._sbs_left_sizes)

    def _on_cut_now_clicked(self, color_name):
        # Always fetch the currently active timeline from DaVinci before cutting
        rh = getattr(self.engine, 'resolve_handler', None)
        if rh:
            rh.get_current_timeline_name()
                
        localized_color_name = self.txt(f"resolve_color_{color_name.lower()}")
        title = self.txt("msg_cut_color_title").format(color=localized_color_name)
        desc = self.txt("msg_cut_color_desc")
        
        box = CustomMsgBox(self, title, desc, self.txt("btn_cut_new_timeline"), self.txt("btn_cut_current_timeline"), self.txt("btn_cancel"))
        ret = box.exec()
        if ret == 2: return
        new_timeline = (ret == 1)
        res = self.engine.api_delete_clips_by_color(color_name, new_timeline) or {}

        # Always report the outcome: a silent 0-clip cut looked like "delete does nothing"
        tl_name = res.get("timeline_name", "")
        if not res.get("ok"):
            msg_title = self.txt("msg_warning")
            msg = self.txt("msg_cut_result_failed").format(error=res.get("error") or "?")
        elif res.get("deleted", 0) == 0:
            if self._offer_assemble_without(color_name, localized_color_name, tl_name):
                return
            msg_title = self.txt("msg_warning")
            msg = self.txt("msg_cut_result_none").format(
                color=localized_color_name, tl=tl_name,
                assemble=self.txt("btn_assemble"), original=self.txt("titlebar_original"))
        else:
            msg_title = self.txt("msg_success")
            msg = self.txt("msg_cut_result_deleted").format(count=res["deleted"], color=localized_color_name, tl=tl_name)
        CustomMsgBox(self, msg_title, msg, self.txt("btn_ok")).exec()

    def _offer_assemble_without(self, color_name, localized_color_name, tl_name):
        """Nothing of this colour exists in Resolve yet (colours only reach Resolve via
        Assemble, the step people miss). If BadWords has parts of that colour marked, offer
        to assemble a new timeline without them in one step. Returns True if offered."""
        if getattr(self, '_is_live_transcribing', False):
            return False
        canvas = getattr(self, 'text_canvas', None)
        if not canvas or not canvas.words_data:
            return False
        is_silence = color_name.lower() == "tan"
        auto_btn = getattr(self, 'color_cut_buttons', {}).get(color_name)
        if not is_silence and auto_btn is None:
            return False

        # Count what an assembly would remove for this colour alone
        probe = dict(self.engine.load_preferences() or {})
        probe['auto_cut_colors'] = [] if is_silence else [color_name]
        probe['silence_cut'] = is_silence
        probe['silence_mark'] = False
        rh = getattr(self.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        try:
            _, cut_ops = self.engine.calculate_timeline_structure_with_cuts(
                [dict(w) for w in canvas.words_data], fps, probe)
        except Exception:
            return False
        if not cut_ops:
            return False

        if is_silence:
            note = self.txt("msg_cut_offer_note_silence").format(setting=self.txt("lbl_detect_and_cut_silence"))
        else:
            note = self.txt("msg_cut_offer_note_auto").format(color=localized_color_name)
        msg = self.txt("msg_cut_offer_assemble").format(
            color=localized_color_name, tl=tl_name, assemble=self.txt("btn_assemble"),
            count=len(cut_ops), note=note)
        box = CustomMsgBox(self, self.txt("msg_warning"), msg,
                           self.txt("btn_cut_assemble_without").format(color=localized_color_name),
                           self.txt("btn_cancel"))
        if box.exec() == 1:
            if is_silence:
                self.tgl_silence_cut.setChecked(True)
            else:
                auto_btn.setChecked(True)
            self._on_assemble()
        return True

    # ── Marking: passages and the AI layer ───────────────────────────────
    def _mark_words(self, ids, fn):
        """Apply fn to the words at these indices as one undo step, then refresh the views."""
        import algorithms
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return 0
        changes = {}
        for i in ids:
            if not (0 <= i < len(canvas.words_data)):
                continue
            w = canvas.words_data[i]
            if w.get('type') == 'silence':
                continue
            changes[w['id']] = {k: w.get(k) for k in algorithms.MARK_STATE_KEYS}
            fn(w)
        if changes and hasattr(self, 'undo_manager'):
            self.undo_manager.push({"type": "paint", "changes": changes})
        canvas.update()
        self._refresh_cut_preview()
        self._refresh_detection_counts()
        return len(changes)

    def _selection_mark(self, ids, status_id):
        def _mark(w):
            w['status'] = status_id
            w['manual_status'] = status_id
            w['is_auto'] = False
            w['selected'] = True
            w['overlay_suppressed'] = True
        self._mark_words(ids, _mark)

    def _selection_clear(self, ids):
        import algorithms
        self._mark_words(ids, algorithms.clear_mark)

    def _selection_restore_ai(self, ids):
        import algorithms

        def _restore(w):
            algorithms.restore_ai_mark(w)
            if w.get('ai_mark') == 'inaudible':
                self._calculate_visual_layer(w)
        n = self._mark_words(ids, _restore)
        self._show_temporary_status(self.txt("msg_ai_restored").format(count=n))

    def _restore_all_ai_marks(self):
        canvas = getattr(self, 'text_canvas', None)
        if canvas is not None and canvas.words_data:
            self._selection_restore_ai(range(len(canvas.words_data)))

    def _selection_detect_again(self, ids):
        """Run the detector again (fillers, stutters, retakes) on a copy of the transcript, so the
        passage keeps its context, then take the new verdicts for the passage only."""
        import copy
        import algorithms
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return
        ids = list(ids)
        work = copy.deepcopy(canvas.words_data)
        for i in ids:
            if 0 <= i < len(work):
                for k in ('manual_status', 'status', 'algo_status'):
                    work[i][k] = None
                work[i]['is_auto'] = False
        prefs = self.engine.load_preferences() or {}
        result, _ = self.engine.run_standalone_analysis(work, prefs.get('show_inaudible', True))
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        algorithms.apply_auto_filler_logic(result, fillers, True)
        by_id = {w.get('id'): w for w in result}
        for i in ids:
            if 0 <= i < len(canvas.words_data):
                w = canvas.words_data[i]
                fresh = by_id.get(w.get('id'))
                if fresh is not None:
                    w['ai_mark'] = algorithms.ai_verdict(fresh)

        def _restore(w):
            algorithms.restore_ai_mark(w)
            if w.get('ai_mark') == 'inaudible':
                self._calculate_visual_layer(w)
        self._mark_words(ids, _restore)
        marked = sum(1 for i in ids if 0 <= i < len(canvas.words_data) and canvas.words_data[i].get('ai_mark') in ('bad', 'repeat', 'typo'))
        self._show_temporary_status(self.txt("msg_detected_again").format(count=marked))

    def _selection_retranscribe(self, ids):
        """Transcribe a selected passage again (background), then put the new words in its place."""
        import copy, threading
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data or not ids or getattr(self, '_retranscribe_job', None):
            return
        words = canvas.words_data
        first, last = min(ids), max(ids)
        audio_path = words[0].get("meta_audio_path") or getattr(self.engine, 'last_audio_path', None)
        if not audio_path or not os.path.exists(audio_path):
            CustomMsgBox(self, config.APP_NAME, self.txt("msg_speaker_no_audio"), self.txt("btn_ok")).exec()
            return
        spoken = [w for w in words[first:last + 1] if w.get('type') != 'silence']
        if not spoken:
            return
        t0, t1 = float(spoken[0].get('start', 0.0)), float(spoken[-1].get('end', 0.0))
        raw_lang = self._combo_lang.text() if hasattr(self, '_combo_lang') else 'Auto'
        lang_code = next((c for c, n in config.SUPPORTED_LANGUAGES.items() if n.lower() == raw_lang.lower()), "auto")
        prefs = self.engine.load_preferences() or {}
        settings = {"lang": lang_code, "model": self._combo_model.text() if hasattr(self, '_combo_model') else prefs.get('model', 'Medium'),
                    "device": prefs.get('device', 'Auto')}
        rh = getattr(self.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        job = {"done": False, "words": None, "error": None}
        self._retranscribe_job = job
        self._show_temporary_status(self.txt("msg_retranscribe_running"), 120000)

        def _work():
            try:
                job["words"] = self.engine.transcribe_passage(audio_path, t0, t1, settings, fps)
            except Exception as e:
                job["error"] = str(e)
            job["done"] = True
        threading.Thread(target=_work, daemon=True).start()

        def _poll():
            if not job["done"]:
                QTimer.singleShot(300, _poll)
                return
            self._retranscribe_job = None
            if job["error"] or job["words"] is None:
                from osdoc import log_error
                log_error(f"Transcribe again failed: {job['error']}")
                self._show_temporary_status(self.txt("msg_retranscribe_failed"))
                return
            import algorithms
            old = copy.deepcopy(canvas.words_data)
            cur = canvas.words_data
            new_list = cur[:first] + job["words"] + cur[last + 1:]
            for k in ('meta_audio_path', 'meta_global_silence'):  # file-level info lives on the first word
                if k in cur[0] and k not in new_list[0]:
                    new_list[0][k] = cur[0][k]
            for i, w in enumerate(new_list):
                w['id'] = i
            for w in job["words"]:
                w.pop('ai_mark', None)
            canvas.load_data(new_list)  # snapshots the AI marks of the new words
            if hasattr(self, 'undo_manager'):
                self.undo_manager.push({"type": "words", "words": old, "changes": {"_": 1}})
            self._refresh_cut_preview()
            self._refresh_detection_counts()
            before = ' '.join(w.get('text', '') for w in spoken)
            after = ' '.join(w.get('text', '') for w in job["words"])
            self._show_temporary_status(self.txt("msg_retranscribe_done").format(
                before=len(spoken), after=len(job["words"])) if before != after else self.txt("msg_retranscribe_same"))
        QTimer.singleShot(300, _poll)

    def _selection_play(self, ids):
        canvas = getattr(self, 'text_canvas', None)
        ap = getattr(self, 'audio_preview', None)
        if canvas is None or ap is None or not ids:
            return
        w = canvas.words_data[min(ids)]
        ap.seek_source_time(float(w.get('start', 0.0)))
        if ap.player.playbackState() != ap.player.PlaybackState.PlayingState:
            ap.toggle_play()

    def _ai_kind_ids(self, kind):
        """Word indices the AI put in a kind: fillers / errors / typos / novoice."""
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return []
        fillers = {f.lower() for f in (self.engine.load_preferences() or {}).get('filler_words', config.DEFAULT_BAD_WORDS)}
        out = []
        for i, w in enumerate(canvas.words_data):
            a = w.get('ai_mark')
            if not a:
                continue
            is_filler = (w.get('text', '').strip(".,?!:;\"'()[]{}").lower() in fillers)
            if a.startswith('custom_'):
                k = 'speaker'
            elif w.get('is_stammer'):
                k = 'stammers'
            else:
                k = {'typo': 'typos', 'inaudible': 'novoice', 'repeat': 'errors'}.get(a) or ('fillers' if is_filler else 'errors')
            if k == kind:
                out.append(i)
        return out

    # ── Saved transcripts per timeline ──────────────────────────────────
    def _refresh_saved_transcript_offer(self, tl_name=None):
        """Show "Open saved transcript" when this timeline was transcribed before."""
        from handlers import timeline_store
        btn = getattr(self, 'btn_open_saved', None)
        if btn is None:
            return
        if tl_name is None and hasattr(self, 'combo_tl_0'):
            tl_name = self.combo_tl_0.text()
        found = timeline_store.find(self.engine.os_doc.get_saves_folder(), self.engine._get_resolve_project_name(), tl_name)
        self._saved_transcript_path = found[0] if found else None
        self._saved_transcript_current = bool(found) and self._saved_matches_timeline(found[0], tl_name)
        if found:
            btn.setText(self.txt("btn_open_saved").format(when=timeline_store.when_text(found[1]))
                        + ("" if self._saved_transcript_current else self.txt("saved_outdated")))
            btn.setToolTip(self.txt("tt_open_saved"))
        btn.setVisible(bool(found))

    def _saved_matches_timeline(self, path, tl_name):
        """False when the timeline's length in Resolve no longer fits the saved transcript (edited since)."""
        import json
        rh = getattr(self.engine, 'resolve_handler', None)
        try:
            tl_len = rh.get_timeline_length_s(tl_name) if rh else None
            if not tl_len:
                return True
            with open(path, encoding='utf-8') as f:
                words = json.load(f).get("words_data") or []
            end = max((float(w.get("end", 0.0)) for w in words), default=0.0)
            return end <= tl_len + 1.0 and end >= tl_len * 0.85 - 3.0
        except Exception:
            return True

    def _maybe_auto_open_saved(self, tries=0):
        """At launch: open the saved transcript of Resolve's current timeline instead of offering to
        transcribe it again. Skipped when a crash recovery is offered or something is already open."""
        state = getattr(self, '_crash_state', None)
        if state in (None, 'checking'):
            if tries < 20:
                QTimer.singleShot(250, lambda: self._maybe_auto_open_saved(tries + 1))
            return
        canvas = getattr(self, 'text_canvas', None)
        if (state == 'crashed' or self._stack.currentIndex() != 0
                or (canvas is not None and canvas.words_data) or not getattr(self, '_saved_transcript_path', None)):
            return
        if not getattr(self, '_saved_transcript_current', True):
            from osdoc import log_info
            log_info("Saved transcript not opened: the timeline has changed since it was saved")
            return
        from osdoc import log_info
        log_info(f"Opening the saved transcript of the current timeline: {os.path.basename(self._saved_transcript_path)}")
        self._open_saved_transcript()

    def _open_saved_transcript(self):
        path = getattr(self, '_saved_transcript_path', None)
        if path and os.path.exists(path):
            self._on_import_project(override_path=path)

    def _save_timeline_transcript_soon(self):
        """Keep this timeline's transcript (background), e.g. right after it was transcribed."""
        import threading
        from handlers import timeline_store
        packet = self._build_data_packet()
        if packet:
            threading.Thread(target=lambda: timeline_store.save(self.engine, packet, keep_previous=True), daemon=True).start()

    _AVOID_COLORS = ("Orange", "Brown", "Beige", "Pink", "Purple", "Teal", "Lime", "Yellow", "Apricot")

    def _avoid_names(self):
        import json
        names = {"avoid"}
        i18n_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "i18n")
        try:
            for f in os.listdir(i18n_dir):
                if f.endswith(".json"):
                    with open(os.path.join(i18n_dir, f), encoding="utf-8") as fh:
                        n = json.load(fh).get("marker_avoid")
                    if n:
                        names.add(n.lower())
        except Exception:
            pass
        return names

    def _avoid_marker(self):
        """The custom marker for parts not to use (noise, background voice, hesitation), or None."""
        markers = [m for m in (self.engine.load_preferences() or {}).get('custom_markers', []) or [] if m.get('name')]
        for m in markers:
            if m.get('role') == 'avoid':
                return m
        names = self._avoid_names()
        for m in markers:
            if m['name'].strip().lower() in names:
                return m
        return None

    def _avoid_status(self):
        m = self._avoid_marker()
        return f"custom_{m['color']}" if m else None

    def _ensure_avoid_marker(self):
        """Create the Avoid marker once, set to Keep: it never cuts or colours anything in Resolve,
        it only tells the AI and the story board not to use those parts. Deleting it in Settings is final."""
        prefs = self.engine.load_preferences() or {}
        if prefs.get('avoid_marker_added') or self._avoid_marker():
            return
        markers = list(prefs.get('custom_markers', []) or [])
        used = {m.get('color', '').lower() for m in markers}
        color = next((c for c in self._AVOID_COLORS if c.lower() not in used), None)
        if color is None:
            return
        markers.append({"name": self.txt("marker_avoid"), "color": color, "role": "avoid"})
        prefs['custom_markers'] = markers
        prefs['plain_colors'] = [c for c in (prefs.get('plain_colors', []) or []) if c.lower() != color.lower()] + [color]
        prefs['auto_cut_colors'] = [c for c in (prefs.get('auto_cut_colors', []) or []) if c.lower() != color.lower()]
        prefs['avoid_marker_added'] = True
        self.engine.save_preferences(prefs)
        btn = getattr(self, 'color_cut_buttons', {}).get(color)
        if btn is not None and btn.isChecked():
            btn.setChecked(False)

    def _apply_resolve_speakers(self, words):
        """Resolve named the speakers: whoever talks most is the main voice; the others get the Interviewer
        marker (created once, set to Keep), so the AI sees them as INTERVIEWER and nothing is cut by it."""
        import collections
        counts = collections.Counter(w.get('speaker') for w in words or [] if w.get('speaker'))
        if len(counts) < 2:
            return
        main = counts.most_common(1)[0][0]
        status = self._interviewer_status()
        if status is None:
            prefs = self.engine.load_preferences() or {}
            markers = list(prefs.get('custom_markers', []) or [])
            used = {m.get('color', '').lower() for m in markers}
            color = next((c for c in ("Teal", "Purple", "Pink", "Lime", "Yellow", "Apricot", "Beige", "Brown")
                          if c.lower() not in used), None)
            if color is None:
                return
            markers.append({"name": self.txt("marker_interviewer"), "color": color, "role": "speaker2"})
            prefs['custom_markers'] = markers
            prefs['plain_colors'] = [c for c in (prefs.get('plain_colors', []) or []) if c.lower() != color.lower()] + [color]
            prefs['auto_cut_colors'] = [c for c in (prefs.get('auto_cut_colors', []) or []) if c.lower() != color.lower()]
            self.engine.save_preferences(prefs)
            btn = getattr(self, 'color_cut_buttons', {}).get(color)
            if btn is not None and btn.isChecked():
                btn.setChecked(False)
            if hasattr(self, 'markers_layout'):
                self._build_marker_radio_buttons()
                self._rebuild_mark_strip()
            status = f"custom_{color}"
        n = 0
        for w in words:
            if w.get('speaker') and w['speaker'] != main and w.get('type') not in ('silence', 'inaudible') \
                    and not w.get('manual_status'):
                w['status'] = status
                w['ai_mark'] = status
                w['is_auto'] = False
                n += 1
        from osdoc import log_info
        log_info(f"Resolve speakers: {len(counts)} voices; {n} words of the other voice(s) marked Interviewer")

    def _speaker_marker(self):
        """The custom marker used for the second speaker: one named like "speaker", else the first one."""
        avoid = self._avoid_marker()
        markers = [m for m in (self.engine.load_preferences() or {}).get('custom_markers', []) or []
                   if m.get('name') and m.get('color', '').lower() not in ('green', 'blue') and m != avoid]
        for m in markers:
            if 'speaker' in m['name'].lower() or 'interview' in m['name'].lower():
                return m
        return markers[0] if markers else None

    def _detect_second_speaker(self):
        """Mark what the second speaker (usually the interviewer) says, in the background."""
        import threading
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data or getattr(self, '_speaker_job', None):
            return
        marker = self._speaker_marker()
        if marker is None:
            CustomMsgBox(self, config.APP_NAME, self.txt("msg_speaker_need_marker"), self.txt("btn_ok")).exec()
            return
        audio_path = canvas.words_data[0].get("meta_audio_path") or getattr(self.engine, 'last_audio_path', None)
        if not audio_path or not os.path.exists(audio_path):
            CustomMsgBox(self, config.APP_NAME, self.txt("msg_speaker_no_audio"), self.txt("btn_ok")).exec()
            return
        words = [dict(w) for w in canvas.words_data]
        job = {"done": False, "error": None, "picked": [], "progress": None}
        self._speaker_job = job
        self._show_temporary_status(self.txt("msg_speaker_running"), 60000)

        def _work():
            try:
                from engine import speakers
                mp = speakers.ensure_model(self.engine.models_dir, progress=lambda f: job.__setitem__("progress", f))
                audio = speakers.load_audio(getattr(self.engine, 'ffmpeg_cmd', 'ffmpeg'), audio_path)
                job["picked"], _ = speakers.find_second_speaker(audio, words, mp)
            except Exception as e:
                job["error"] = str(e)
            job["done"] = True

        threading.Thread(target=_work, daemon=True).start()

        def _poll():
            if not job["done"]:
                QTimer.singleShot(250, _poll)
                return
            self._speaker_job = None
            if job["error"]:
                from osdoc import log_error
                log_error(f"Speaker detection failed: {job['error']}")
                self._show_temporary_status(self.txt("msg_speaker_failed"))
                return
            status = f"custom_{marker['color']}"
            picked = set(job["picked"])
            for i, w in enumerate(canvas.words_data):
                if i in picked:
                    w['ai_mark'] = status
                elif w.get('ai_mark') == status:
                    w['ai_mark'] = algorithms_verdict(w)
            self._selection_restore_ai(sorted(picked))
            self._show_temporary_status(self.txt("msg_speaker_done").format(count=len(picked), marker=marker['name']))
            self._refresh_detection_counts()

        def algorithms_verdict(w):
            import algorithms
            return algorithms.ai_verdict(w)

        QTimer.singleShot(250, _poll)

    def _restore_ai_kind(self, kind):
        ids = self._ai_kind_ids(kind)
        if ids:
            self._selection_restore_ai(ids)
        self._refresh_detection_counts()

    def _detect_stammers(self):
        """Mark what is said again on the whole transcript: stammers, restarts and echoes."""
        import algorithms
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return
        ids = [i for i in algorithms.find_repeats(canvas.words_data) if not canvas.words_data[i].get('manual_status')]
        n = self._mark_words(ids, lambda w: algorithms.mark_stammers([w], [0]))
        algorithms.snapshot_ai_marks(canvas.words_data, overwrite=True, ids=set(ids))
        self._refresh_detection_counts()
        self._show_temporary_status(self.txt("msg_stammers_found").format(count=n))

    def _refresh_detection_counts(self):
        labels = getattr(self, 'det_counts', None)
        canvas = getattr(self, 'text_canvas', None)
        if not labels or canvas is None:
            return
        for kind, lbl in labels.items():
            ids = self._ai_kind_ids(kind)
            off = 0
            for i in ids:
                w = canvas.words_data[i]
                a = w.get('ai_mark')
                if a == 'inaudible':
                    off += 1 if w.get('manual_status') == 'normal' else 0
                elif w.get('status') != a:
                    off += 1
            text = self.txt("det_count").format(count=len(ids))
            if off:
                text += " · " + self.txt("det_cleared").format(count=off)
            if kind == 'novoice':
                loud = sum(1 for i in self._sound_ids() if self._sound_is_cut(canvas.words_data[i]))
                if loud:
                    text += " · " + self.txt("det_sounds_cut").format(count=loud)
            lbl.setText(text)

    # ── Sounds without words (cough, knock, a voice in the background) ──
    def _sound_ids(self):
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return []
        return [i for i, w in enumerate(canvas.words_data) if w.get('type') == 'inaudible' or w.get('is_inaudible')]

    def _sound_is_cut(self, w):
        """Cut by the user (Cut it), or much louder than the voice and not kept (as audio_engine cuts it)."""
        choice = w.get('sound_choice')
        if choice:
            return choice == 'cut'
        return bool(w.get('loud')) and (self.engine.load_preferences() or {}).get('cut_loud_sounds', True)

    def _measure_sounds_soon(self):
        """Measure, in the background, how loud the sounds without words are (older transcripts
        don't have it); loud ones are then cut and counted."""
        import algorithms
        from PySide6.QtCore import QThread, Signal
        canvas = getattr(self, 'text_canvas', None)
        words = canvas.words_data if canvas is not None else None
        if not words or not any((w.get('type') == 'inaudible' or w.get('is_inaudible')) and 'sound_db' not in w for w in words):
            return
        snapshot = [{k: w.get(k) for k in ('start', 'end', 'type', 'is_inaudible')} for w in words]
        win = self

        class _SoundWorker(QThread):
            done = Signal(list)

            def run(self):
                try:
                    algorithms.measure_sounds(snapshot, win._edit_audio())
                    self.done.emit([(i, w['sound_db'], w.get('loud')) for i, w in enumerate(snapshot) if 'sound_db' in w])
                except Exception:
                    self.done.emit([])

        def _apply(rows):
            if canvas.words_data is not words or not rows:
                return  # another transcript was opened meanwhile
            for i, db, loud in rows:
                words[i]['sound_db'], words[i]['loud'] = db, bool(loud)
            self._refresh_cut_preview()
            self._refresh_detection_counts()

        worker = _SoundWorker()
        worker.done.connect(_apply)
        worker.start()
        self._sound_worker = worker

    def _review_next_sound(self):
        """Play the next sound without words from a second before, and say how loud it is."""
        ids = self._sound_ids()
        if not ids:
            self._show_temporary_status(self.txt("msg_sounds_none"))
            return
        self._sound_review_k = (getattr(self, '_sound_review_k', -1) + 1) % len(ids)
        w = self.text_canvas.words_data[ids[self._sound_review_k]]
        ap = getattr(self, 'audio_preview', None)
        if ap is not None:
            from PySide6.QtMultimedia import QMediaPlayer
            ap.seek_source_time(max(0.0, float(w['start']) - 1.0))
            if ap.player.playbackState() != QMediaPlayer.PlayingState:
                ap.toggle_play()
        self._update_sound_review()

    def _toggle_sound_choice(self):
        ids = self._sound_ids()
        k = getattr(self, '_sound_review_k', -1)
        if not 0 <= k < len(ids):
            return
        w = self.text_canvas.words_data[ids[k]]
        w['sound_choice'] = 'keep' if self._sound_is_cut(w) else 'cut'
        self._refresh_cut_preview()
        self._refresh_detection_counts()
        self._update_sound_review()

    def _update_sound_review(self):
        ids = self._sound_ids()
        k = getattr(self, '_sound_review_k', -1)
        btn = getattr(self, 'btn_sound_choice', None)
        if not 0 <= k < len(ids):
            if btn is not None:
                btn.setEnabled(False)
            return
        w = self.text_canvas.words_data[ids[k]]
        cut = self._sound_is_cut(w)
        if btn is not None:
            btn.setEnabled(True)
            btn.setText(self.txt("btn_sound_keep" if cut else "btn_sound_cut"))
        s = int(float(w['start']))
        db = w.get('sound_db')
        self._show_temporary_status(self.txt("msg_sound_review").format(
            n=k + 1, total=len(ids), time=f"{s // 60}:{s % 60:02d}",
            level=f"{round(db):+d} dB" if db is not None else "?",
            state=self.txt("sound_state_cut" if cut else "sound_state_kept")), 8000)

    def _select_marker(self, index):
        """Keys 1-9: pick the n-th marker of the strip."""
        btns = [b for b in getattr(self, 'marker_btn_group', None).buttons()] if hasattr(self, 'marker_btn_group') else []
        if 0 <= index < len(btns) and btns[index].isEnabled():
            btns[index].setChecked(True)

    def _rebuild_mark_strip(self):
        """Marker chips above the transcript, mirroring the Marking Mode list (custom markers too)."""
        lay = getattr(self, 'mark_strip_chips', None)
        group = getattr(self, 'marker_btn_group', None)
        if lay is None or group is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        from PySide6.QtGui import QPixmap, QPainter, QIcon, QColor
        short = {"bad": "mark_chip_bad", "repeat": "mark_chip_repeat", "typo": "mark_chip_typo", "eraser": "mark_chip_clear"}
        colors = {"bad": config.WORD_BAD_BG, "repeat": config.WORD_REPEAT_BG, "typo": config.WORD_TYPO_BG, "eraser": "#9a9a9a"}
        self._mark_chips = []
        for n, rb in enumerate(group.buttons(), start=1):
            sid = rb.property("status_id") or ""
            if sid.startswith("custom_"):
                color = config.RESOLVE_COLORS_HEX.get(sid.split("_", 1)[1], "#ffffff")
                label = rb.text().split("(", 1)[-1].rstrip(")") if "(" in rb.text() else rb.text()
            else:
                color = colors.get(sid, "#ffffff")
                label = self.txt(short.get(sid, "")) if sid in short else rb.text()
            pm = QPixmap(config.S(10) * 2, config.S(10) * 2)
            pm.setDevicePixelRatio(2.0)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(color))
            if sid == "eraser":
                p.setBrush(Qt.NoBrush)
                p.setPen(QColor(color))
            p.drawEllipse(1, 1, config.S(10) - 2, config.S(10) - 2)
            p.end()
            chip = QPushButton(QIcon(pm), label)
            chip.setCheckable(True)
            chip.setChecked(rb.isChecked())
            chip.setEnabled(rb.isEnabled())
            chip.setCursor(Qt.PointingHandCursor)
            chip.setToolTip(self.txt("tt_mark_chip").format(key=n) if n <= 9 else "")
            chip.setObjectName("MarkChip")
            chip.clicked.connect(lambda _=False, b=rb: b.setChecked(True))
            rb.toggled.connect(lambda on, c=chip: c.setChecked(on))
            lay.addWidget(chip)
            self._mark_chips.append(chip)

    def _on_analyze_standalone(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        prefs = self.engine.load_preferences() or {}
        show_inaudible = prefs.get('show_inaudible', True)
        
        # Standalone analysis returns a tuple: (processed_words, count)
        updated_words, _ = self.engine.run_standalone_analysis(self.text_canvas.words_data, show_inaudible)
        import algorithms
        algorithms.snapshot_ai_marks(updated_words, overwrite=True)  # a fresh analysis: new AI layer
        self.text_canvas.load_data(updated_words)

    def _switch_chapter(self, chapter_name):
        if not self._chapters: return
        
        target_idx = -1
        for i, ch in enumerate(self._chapters):
            if ch.get("name") == chapter_name:
                target_idx = i
                break
                
        if target_idx == -1: return
        self._current_chapter_idx = target_idx
        
        import copy
        ch = self._chapters[target_idx]
        ch_words = copy.deepcopy(ch.get("words", []))
        self.text_canvas.load_data(ch_words)
        
        tl_name = ch.get("tl_name", "")
        track_label = f"A1: {tl_name}" if tl_name else "A1: Timeline Audio"
        if ch_words and ch_words[0].get("meta_audio_path") and hasattr(self, 'waveform_timeline') and self.waveform_timeline:
            self.waveform_timeline.load_from_audio(ch_words[0]["meta_audio_path"], track_name=track_label)
        elif hasattr(self, 'waveform_timeline') and self.waveform_timeline:
            self.waveform_timeline.set_track_info(track_label)
        
        # Sync DaVinci
        prefs = self.engine.load_preferences() or {}
        if prefs.get("sync_davinci_chapter", True):
            tl_name = ch.get("tl_name")
            if tl_name and self.resolve_handler:
                try:
                    self.resolve_handler.set_current_timeline(tl_name, async_exec=True)
                except Exception:
                    pass

    def _on_auto_filler_toggled(self, is_checked):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        import algorithms
        prefs = self.engine.load_preferences() or {}
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        
        # Apply filler logic directly to the current state
        if hasattr(algorithms, 'apply_auto_filler_logic'):
            updated_words = algorithms.apply_auto_filler_logic(self.text_canvas.words_data, fillers, is_checked)
            if is_checked:
                algorithms.snapshot_ai_marks(updated_words, overwrite=True)  # fillers are AI marks too
            self.text_canvas.words_data = updated_words
            self.text_canvas.update()

    def _on_save_inline_fillers(self):
        raw_text = self.txt_fillers.toPlainText()
        new_fillers = [w.strip() for w in raw_text.split(',') if w.strip()]
        
        prefs = self.engine.load_preferences() or {}
        prefs['filler_words'] = new_fillers
        self.engine.save_preferences(prefs)
        
        # Provide visual feedback on the button
        self.btn_save_fillers.setText(self.txt("txt_saved"))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_fillers.setText(self.txt("txt_save")))
        
        # Trigger real-time update if auto filler is currently active
        if hasattr(self, 'tgl_auto_filler') and self.tgl_auto_filler.isChecked() and hasattr(self, 'text_canvas') and self.text_canvas.words_data:
            import algorithms
            if hasattr(algorithms, 'apply_auto_filler_logic'):
                updated_words = algorithms.apply_auto_filler_logic(self.text_canvas.words_data, new_fillers, True)
                self.text_canvas.words_data = updated_words
                self.text_canvas.update()

    def _on_reset_inline_fillers(self):
        self.txt_fillers.setText(", ".join(config.DEFAULT_BAD_WORDS))
        self._on_save_inline_fillers()

    def _on_fillers_text_changed(self):
        # Auto-Resize: Document height + 1 line height
        doc_height = self.txt_fillers.document().size().height()
        from PySide6.QtGui import QFontMetrics
        line_height = QFontMetrics(self.txt_fillers.font()).lineSpacing()
        
        new_height = int(doc_height + line_height + 10) # 10px padding margin
        # Cap max height to avoid breaking the UI
        new_height = min(new_height, 250)
        self.txt_fillers.setFixedHeight(new_height)
        
        # Word count calculation
        raw_text = self.txt_fillers.toPlainText()
        words = [w.strip() for w in raw_text.split(',') if w.strip()]
        count = len(words)
        
        self.lbl_filler_count.setText(f"{count} / 150 {self.txt('lbl_words')}")
        
        if count > 150:
            self.lbl_filler_count.setStyleSheet("color: #ed4245; font-size: 9pt; font-weight: bold;")
            self.btn_save_fillers.setEnabled(False)
        else:
            self.lbl_filler_count.setStyleSheet("color: #888888; font-size: 9pt;")
            self.btn_save_fillers.setEnabled(True)

    def _get_clean_words_data(self):
        """Returns a deep-copy of words_data stripped of all PySide6 UI objects (keys starting with '_')."""
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return []
            
        clean_data = []
        for w in self.text_canvas.words_data:
            # Only keep native Python types, strip UI markers like _rect, _ts_rect, _display_text
            clean_w = {k: v for k, v in w.items() if not k.startswith('_')}
            clean_data.append(clean_w)
        return clean_data

    def _build_data_packet(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return None
        clean_words = self._get_clean_words_data()
        if getattr(self, '_current_chapter_idx', -1) >= 0 and getattr(self, '_chapters', []):
            self._chapters[self._current_chapter_idx]['words'] = clean_words
            
        analysis_time = ""
        if hasattr(self, 'lbl_analysis_duration') and self.lbl_analysis_duration.isVisible():
            analysis_time = getattr(self, '_last_analysis_time_raw', None)
            if not analysis_time:
                import re
                time_match = re.search(r'\d+:\d+', self.lbl_analysis_duration.text())
                analysis_time = time_match.group(0) if time_match else self.lbl_analysis_duration.text()
                
        return {
            "words_data":     clean_words,
            "chapters":       [
                {**ch, "words": [{k: v for k, v in w.items() if not k.startswith('_')} for w in ch.get("words", [])]}
                for ch in getattr(self, '_chapters', [])
            ],
            "current_chapter_idx": getattr(self, '_current_chapter_idx', -1),
            "script_content": getattr(self, 'text_script', None).toPlainText() if hasattr(self, 'text_script') else "",
            "transcription_source": getattr(self, '_transcription_source', None),
            "sbs_cache":      None,
            "analysis_time":  analysis_time
        }

    def _build_autosave_payload(self):
        packet = self._build_data_packet()
        bws_extras = {
            "drt_path": getattr(self, '_extracted_drt_path', None),
            "media_inventory": getattr(self, '_media_inventory', []),
            "assembly_recipe": getattr(self, '_assembly_recipe', None),
            # In autosave we skip exactly re-computing the fingerprint to avoid DaVinci lag, it will rely on timeline name during recovery
        }
        
        # Audio path is already embedded or resolved by save_worker, but we can also set it if known:
        audio_path = None
        if hasattr(self, '_current_audio_file'):
            audio_path = self._current_audio_file
        bws_extras["audio_path"] = audio_path
            
        return packet, bws_extras

    def _on_export_project(self):
        packet = self._build_data_packet()
        if not packet: return
        from PySide6.QtWidgets import QFileDialog
        import os
        
        saves_dir = self.engine.os_doc.get_saves_folder()
        os.makedirs(saves_dir, exist_ok=True)
        
        # SMART TIMELINE NAMING
        timeline_name = "Project"
        snap = packet.get("transcription_source") or {}
        if snap.get("timeline_name"):
            timeline_name = snap["timeline_name"]
            
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"{config.APP_NAME}_{safe_name}.bws"
        
        path, _ = QFileDialog.getSaveFileName(self, self.txt("btn_export_project"), os.path.join(saves_dir, default_filename), "StoryCraft Project (*.bws);;JSON Files (*.json)")
        if not path: return

        if path.endswith('.json'):
            self.engine.save_project_state(path, packet)
        else:
            # Gather .bws specific data
            audio_path = None
            words = packet.get("words_data", [])
            if words and words[0].get("meta_audio_path"):
                audio_path = words[0].get("meta_audio_path")
                
            drt_path = getattr(self, '_extracted_drt_path', None)
            if not drt_path and hasattr(self, 'engine') and hasattr(self, 'resolve_handler') and self.resolve_handler:
                # Try to export DRT from DaVinci Resolve right now if we don't have one
                drt_path = self.engine.export_source_drt(timeline_name)
                self._extracted_drt_path = drt_path

            # Re-compute fingerprint in case it changed since import/transcription
            timeline_fingerprint = None
            if hasattr(self, 'resolve_handler') and self.resolve_handler:
                timeline_fingerprint = self.resolve_handler.compute_timeline_fingerprint(timeline_name)
                
            # If we don't have media inventory, build it now
            media_inventory = getattr(self, '_media_inventory', [])
            if not media_inventory and hasattr(self, 'resolve_handler') and self.resolve_handler:
                source_files = snap.get("source_files")
                if not source_files:
                    try:
                        t_name = snap.get("timeline_name", "")
                        t_indices = snap.get("track_indices", [])
                        source_files = self.resolve_handler.get_timeline_source_files(t_name, t_indices)
                        if source_files:
                            snap["source_files"] = source_files
                    except Exception as e:
                        from osdoc import log_error as _le
                        _le(f"_on_export_project: get_timeline_source_files failed: {e}")
                if source_files:
                    media_inventory = self.engine.build_media_inventory(source_files)
                    self._media_inventory = media_inventory

            recipe = getattr(self, '_assembly_recipe', None)
            xml_path = None
            if not drt_path and getattr(self, 'resolve_handler', None) and getattr(self, '_transcription_source', None):
                tl_name = self._transcription_source.get("timeline_name")
                if tl_name:
                    try:
                        temp_dir = self.engine.os_doc.get_temp_folder()
                        safe_name = "".join(c for c in tl_name if c.isalnum() or c in '_- ')
                        cand_xml = os.path.join(temp_dir, f"bws_source_{safe_name.replace(' ', '_')}.xml")
                        if self.resolve_handler.export_timeline_xml(tl_name, cand_xml):
                            xml_path = cand_xml
                    except Exception as xe:
                        from osdoc import log_error as _le
                        _le(f"_on_export_project: xml fallback export failed: {xe}")

            self.engine.save_bws(
                path, packet, 
                audio_path=audio_path, 
                drt_path=drt_path, 
                assembly_recipe=recipe, 
                timeline_fingerprint=timeline_fingerprint,
                media_inventory=media_inventory,
                xml_path=xml_path
            )
            if xml_path and os.path.exists(xml_path):
                try: os.remove(xml_path)
                except Exception: pass
            
        self._show_temporary_status(self.txt("msg_transcript_exported"))

    def _build_transcript_plaintext(self):
        """Build a plain-text representation of the current transcript.
        Segmented view → one line per segment.
        Continuous view → one long paragraph.
        Returns str or None if no data."""
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return None

        prefs = self.engine.load_preferences() or {}
        view_mode = prefs.get('view_mode', 'segmented')
        is_segmented = (view_mode == 'segmented')

        lines = []
        current_line_words = []

        for w in self.text_canvas.words_data:
            # Skip silence tokens and inaudible markers
            if w.get('type') in ('silence', 'inaudible'):
                continue
            if w.get('is_inaudible'):
                continue
            # Skip hidden start words
            if w.get('is_hidden_start') and not getattr(self, 'show_hidden_start', False):
                continue

            if is_segmented and w.get('is_segment_start') and current_line_words:
                lines.append(' '.join(current_line_words))
                current_line_words = []

            text = w.get('text', '').strip()
            if text:
                current_line_words.append(text)

        if current_line_words:
            lines.append(' '.join(current_line_words))

        if is_segmented:
            return '\n'.join(lines)
        else:
            return ' '.join(lines)

    def _on_export_transcript_txt(self):
        """Export the transcript as a plain .txt file."""
        text = self._build_transcript_plaintext()
        if not text:
            return

        from PySide6.QtWidgets import QFileDialog
        import os

        saves_dir = self.engine.os_doc.get_saves_folder()
        os.makedirs(saves_dir, exist_ok=True)

        # Build default filename from source info
        timeline_name = "Transcript"
        snap = getattr(self, '_transcription_source', None)
        if snap and snap.get('timeline_name'):
            timeline_name = snap['timeline_name']
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"{config.APP_NAME}_{safe_name}_transcript.txt"

        path, _ = QFileDialog.getSaveFileName(
            self, self.txt("titlebar_export_txt"),
            os.path.join(saves_dir, default_filename),
            "Text Files (*.txt)"
        )
        if not path:
            return

        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)

        # Brief notification
        self._show_temporary_status(self.txt("msg_transcript_exported"))

    _AI_COLOR_NAMES = {"Violet": "red (errors/fillers)", "Navy": "blue (retakes)",
                       "Olive": "green (script differences)", "Tan": "silence", "Chocolate": "inaudible"}

    def _live_cut_prefs(self):
        """Prefs exactly as the next Assemble will use them (saved prefs + current panel toggles)."""
        prefs = dict(self.engine.load_preferences() or {})
        for attr, key in (('tgl_silence_cut', 'silence_cut'), ('tgl_silence_mark', 'silence_mark'),
                          ('tgl_show_inaudible', 'show_inaudible'), ('tgl_mark_inaudible', 'mark_inaudible'),
                          ('tgl_show_typos', 'show_typos')):
            if hasattr(self, attr):
                prefs[key] = getattr(self, attr).isChecked()
        if hasattr(self, 'color_cut_buttons'):
            prefs['auto_cut_colors'] = [c for c, b in self.color_cut_buttons.items() if b.isChecked()]
        story = getattr(self, '_story', None)
        if story and story.get("clips"):
            prefs['story_clips'] = story["clips"]  # pause budget counts only what the story uses
        return prefs

    def _build_ai_transcript(self):
        """Transcript of the edit after the current cuts, with sentence IDs and timecodes.
        Derived from the transcript and the same cut calculation as Assemble, so it needs
        no re-transcription and every sentence still points back to the source."""
        import algorithms
        canvas = getattr(self, 'text_canvas', None)
        if not canvas or not canvas.words_data:
            return None, []
        prefs = self._live_cut_prefs()
        rh = getattr(self.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        ops, _ = self.engine.calculate_timeline_structure_with_cuts(
            [dict(w) for w in canvas.words_data], fps, prefs)
        removed = [self._AI_COLOR_NAMES.get(c, c.lower()) for c in prefs.get('auto_cut_colors', [])]
        if prefs.get('silence_cut'):
            removed.append("silence")
        snap = getattr(self, '_transcription_source', None) or {}
        target = prefs.get('story_target_s') or None
        return algorithms.build_ai_transcript(
            canvas.words_data, ops, fps, title=snap.get('timeline_name', ''), removed=removed,
            offset=prefs.get('offset', 0.133), target_s=target, clarity_fn=self._clarity_scorer(),
            avoid_fn=(lambda w, s=self._avoid_status(): w.get('status') == s) if self._avoid_status() else None,
            speaker_fn=(lambda w, s=self._interviewer_status(): w.get('status') == s) if self._interviewer_status() else None)

    def _interviewer_status(self):
        """Status of the second-speaker marker, only when one is named like it (speaker / interview)."""
        for m in (self.engine.load_preferences() or {}).get('custom_markers', []) or []:
            n = (m.get('name') or '').lower()
            if m.get('color') and (m.get('role') == 'speaker2' or 'speaker' in n or 'interview' in n
                                   or n == self.txt("marker_interviewer").lower()):
                return f"custom_{m['color']}"
        return None

    def _edit_audio(self):
        """The transcript's recording as 16 kHz mono (numpy), loaded once per file; None if unavailable."""
        from engine import speakers
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return None
        audio_path = canvas.words_data[0].get("meta_audio_path")
        cache = getattr(self, '_clarity_audio', None)
        if not audio_path or not os.path.exists(audio_path):
            return None
        if cache and cache[0] == audio_path:
            return cache[1]
        try:
            audio = speakers.load_audio(getattr(self.engine, 'ffmpeg_cmd', 'ffmpeg'), audio_path)
            self._clarity_audio = (audio_path, audio)
            return audio
        except Exception:
            return None

    def _clarity_scorer(self):
        """Clarity 0-100 per stretch of the recording (Whisper confidence + speech level), cached per audio file."""
        from engine import clarity
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not canvas.words_data:
            return None
        return clarity.make_scorer(canvas.words_data, self._edit_audio())

    def _cut_review(self, edit=None):
        """Cut-by-cut review of the story (or of an edit given as text), for the AI or the user."""
        import algorithms
        from engine import clarity
        board = getattr(self, 'story_board', None)
        sentences = (board.sentences if board is not None and board.sentences else None) or self._load_ai_sentences()
        if not sentences:
            return None
        if edit:
            picks, _ = algorithms.parse_story_answer(edit, len(sentences), algorithms.moment_ranges(sentences))
            clips = algorithms.story_clips(picks, sentences)
        else:
            index = {s["id"]: i for i, s in enumerate(sentences)}
            clips = []
            for c in (getattr(self, '_story', None) or {}).get("clips") or []:
                f, l = index.get(c.get("start_id")), index.get(c.get("end_id"))
                if f is not None and l is not None:
                    clips.append({"first": f, "last": l, "start_id": c["start_id"], "end_id": c["end_id"],
                                  "cut_start": c["cut_start"], "cut_end": c["cut_end"],
                                  "text": " ".join(s["text"] for s in sentences[f:l + 1])})
        if not clips:
            return None
        audio = self._edit_audio()
        level = None
        if audio is not None:
            level = lambda t0, t1: clarity._speech_level(audio[int(max(0.0, t0) * 16000):int(t1 * 16000)])
        story = getattr(self, '_story', None) or {}
        target = (self.engine.load_preferences() or {}).get('story_target_s') or None
        return algorithms.cut_review_text(clips, sentences, story.get("duration") if not edit else None, target, level)

    def _on_review_cuts(self):
        text = self._cut_review()
        if not text:
            self._show_temporary_status(self.txt("msg_cut_review_empty"))
            return
        QApplication.clipboard().setText(text)
        n = text.count("\nCut ")
        self._show_temporary_status(self.txt("msg_cut_review_copied").format(cuts=n))

    def _on_copy_ai_transcript(self):
        text, sentences = self._build_ai_transcript()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self._remember_ai_sentences(sentences)
        self._show_temporary_status(self.txt("msg_ai_transcript_copied").format(count=len(sentences)))

    def _on_export_ai_transcript(self):
        text, sentences = self._build_ai_transcript()
        if not text:
            return
        self._remember_ai_sentences(sentences)
        from PySide6.QtWidgets import QFileDialog
        saves_dir = self.engine.os_doc.get_saves_folder()
        os.makedirs(saves_dir, exist_ok=True)
        snap = getattr(self, '_transcription_source', None) or {}
        timeline_name = snap.get('timeline_name') or "Transcript"
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        path, _ = QFileDialog.getSaveFileName(
            self, self.txt("titlebar_export_ai_transcript"),
            os.path.join(saves_dir, f"{config.APP_NAME}_{safe_name}_ai_transcript.txt"),
            "Text Files (*.txt)"
        )
        if not path:
            return
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        self._show_temporary_status(self.txt("msg_transcript_exported"))

    # ── Story mode (issue #8): import an AI edit and assemble it in its order ──
    def _ai_story_map_path(self):
        snap = getattr(self, '_transcription_source', None) or {}
        name = snap.get('timeline_name') or snap.get('source_file') or "Transcript"
        safe = "".join(c for c in os.path.basename(str(name)) if c.isalnum() or c in ' -_').strip() or "Transcript"
        return os.path.join(self.engine.os_doc.get_saves_folder(), "ai_story", f"{safe}.json")

    def _remember_ai_sentences(self, sentences):
        """The IDs the AI sees depend on the cut settings at export time, so keep that exact
        map: the import must resolve S012 to the same sentence even if settings change later."""
        import json
        self._ai_sentences = sentences
        try:
            path = self._ai_story_map_path()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({"version": 1, "sentences": sentences}, f)
        except Exception as e:
            from osdoc import log_error
            log_error(f"_remember_ai_sentences: {e}")

    def _load_ai_sentences(self):
        import json
        if getattr(self, '_ai_sentences', None):
            return self._ai_sentences
        try:
            with open(self._ai_story_map_path(), encoding='utf-8') as f:
                sentences = json.load(f).get("sentences") or []
            if sentences and all('cut_start' in s for s in sentences):
                self._ai_sentences = sentences
                return sentences
        except Exception:
            pass
        return None

    def _on_import_ai_story(self):
        import algorithms
        from gui.dialogs.story_import_dialog import StoryImportDialog
        canvas = getattr(self, 'text_canvas', None)
        if not canvas or not canvas.words_data:
            return
        note = ""
        sentences = self._load_ai_sentences()
        if not sentences:
            _, sentences = self._build_ai_transcript()
            note = self.txt("story_rebuilt_note")
        if not sentences:
            return

        prefs = self._live_cut_prefs()
        rh = getattr(self.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        ops, _ = self.engine.calculate_timeline_structure_with_cuts(
            [dict(w) for w in canvas.words_data], fps, prefs)
        offset = float(prefs.get('offset', 0.133))

        def _duration(clips, keep_source_order):
            story_ops = algorithms.apply_story_order(ops, clips, fps, offset, keep_source_order)
            return sum(o['e'] - o['s'] for o in story_ops) / fps

        dlg = StoryImportDialog(self, self.lang, sentences, _duration, note=note,
                                target_s=prefs.get('story_target_s') or None)
        if dlg.exec() and dlg.result_story:
            self._story = dlg.result_story
            if getattr(self, 'story_board', None) is not None:
                self.story_board.load_ai_story(sentences, dlg.result_story)  # also sets the story
            else:
                self._update_story_banner()
                self._refresh_cut_preview()
            self._show_temporary_status(self.txt("msg_story_loaded").format(
                clips=len(self._story["clips"]), assemble=self.txt("btn_assemble")))

    def _update_story_banner(self):
        story = getattr(self, '_story', None)
        if not hasattr(self, 'story_banner'):
            return
        if not story:
            self.story_banner.setVisible(False)
            return
        secs = int(round(story.get("duration", 0)))
        key = "story_banner_source" if story.get("keep_source_order") else "story_banner"
        self.lbl_story.setText(self.txt(key).format(
            clips=len(story["clips"]), duration=f"{secs // 60}:{secs % 60:02d}", assemble=self.txt("btn_assemble")))
        self.story_banner.setVisible(True)

    def _clear_story(self):
        board = getattr(self, 'story_board', None)
        if board is not None and board.list_edit.count():
            board.clear_edit()  # moves every block to Not used and clears the story
            return
        self._story = None
        self._update_story_banner()
        self._refresh_cut_preview()

    def _on_copy_transcript_clipboard(self):
        """Copy the transcript as plain text to the system clipboard."""
        text = self._build_transcript_plaintext()
        if not text:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        # Brief notification
        self._show_temporary_status(self.txt("msg_transcript_copied"))

    def _show_temporary_status(self, msg, duration_ms=5000):
        """Shows a temporary message on lbl_analysis_duration, restoring previous text after timeout."""
        if not hasattr(self, 'lbl_analysis_duration'):
            return
            
        self.lbl_analysis_duration.setText(msg)
        self.lbl_analysis_duration.setVisible(True)
        
        def _restore():
            if not hasattr(self, 'lbl_analysis_duration'): return
            raw_time = getattr(self, '_last_analysis_time_raw', None)
            if raw_time:
                if len(raw_time) > 0 and raw_time[0].isdigit():
                    self.lbl_analysis_duration.setText(self.txt("txt_analyzed_in").replace("{time}", raw_time))
                else:
                    self.lbl_analysis_duration.setText(raw_time)
                self.lbl_analysis_duration.setVisible(True)
            else:
                self.lbl_analysis_duration.setVisible(False)
                
        from PySide6.QtCore import QTimer
        if not hasattr(self, '_status_timer') or self._status_timer is None:
            self._status_timer = QTimer(self)
            self._status_timer.setSingleShot(True)
        else:
            self._status_timer.stop()
            try:
                self._status_timer.timeout.disconnect()
            except Exception:
                pass
        self._status_timer.timeout.connect(_restore)
        self._status_timer.start(duration_ms)

    def _on_import_project(self, override_path=None):
        try:
            from PySide6.QtWidgets import QFileDialog, QDialog
            from PySide6.QtCore import QThread, Signal
            import os, time
            
            path = override_path
            if not path:
                saves_dir = self.engine.os_doc.get_saves_folder()
                os.makedirs(saves_dir, exist_ok=True)
                
                path, _ = QFileDialog.getOpenFileName(
                    self, 
                    self.txt("btn_import_project"), 
                    saves_dir, 
                    "StoryCraft Project (*.bws);;JSON Files (*.json)"
                )
                
            if not path: return

            self._pre_import_stack_idx = self._stack.currentIndex() if hasattr(self, '_stack') else 0

            # Switch to processing page with indeterminate liquid progress bar (-1)
            import_txt = self.txt("status_importing_project") if hasattr(self, 'txt') else "Loading project..."
            if hasattr(self, 'lbl_processing_status'):
                self.lbl_processing_status.setText(import_txt)
            if hasattr(self, 'lbl_first_run_hint'):
                self.lbl_first_run_hint.hide()
            if hasattr(self, 'bar_processing'):
                self.bar_processing.set_value(-1)
            if hasattr(self, 'go_to_page'):
                self.go_to_page(1)
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()

            self._import_worker = _ProjectImportWorker(self.engine, path)
            def _on_import_status(s):
                if hasattr(self, 'lbl_processing_status'):
                    self.lbl_processing_status.setText(s)
                self._show_temporary_status(s)
            self._import_worker.status_updated.connect(_on_import_status)

            def _on_import_err(err):
                if hasattr(self, 'bar_processing'):
                    self.bar_processing.set_value(0)
                if hasattr(self, 'go_to_page'):
                    self.go_to_page(getattr(self, '_pre_import_stack_idx', 0))
                self._show_temporary_status(f"Import error: {err}")
                dlg = CustomMsgBox(self, self.txt("lbl_error"), f"{self.txt('msg_load_project_failed')}:\n{err}", self.txt("btn_ok"))
                dlg.exec()
            self._import_worker.finished_error.connect(_on_import_err)
            self._import_worker.finished_success.connect(self._apply_imported_project)
            self._import_worker.start()

        except Exception as e:
            from osdoc import log_error as _le
            _le(f"_on_import_project initialization error: {e}")

    def _apply_imported_project(self, state: dict, meta: dict):
        try:
            if hasattr(self, 'bar_processing'):
                self.bar_processing.set_value(0)
            if hasattr(self, '_import_worker') and self._import_worker:
                try:
                    self._import_worker.wait(1000)
                except Exception:
                    pass
                self._import_worker = None

            from PySide6.QtWidgets import QDialog
            bws_extras = meta.get("bws_extras")
            missing_media = meta.get("missing_media", [])
            target_name = meta.get("target_name", "")

            # Safe main-thread timeline fingerprint matching
            found_tl = None
            is_exact = False
            exists_by_name = False
            if bws_extras and bws_extras.get("timeline_fingerprint") and getattr(self, 'resolve_handler', None) and self.resolve_handler.is_connected():
                try:
                    found_tl, is_exact = self.resolve_handler.find_timeline_by_fingerprint(bws_extras["timeline_fingerprint"], preferred_name=target_name)
                    if not (found_tl and is_exact) and target_name:
                        exists_by_name = self.resolve_handler.timeline_exists(target_name)
                except Exception as _fe:
                    from osdoc import log_error as _le
                    _le(f"fingerprint matching error: {_fe}")

            from_main_window = getattr(self, '_pre_import_stack_idx', 0) != 2

            # --- Restore Source Snapshot ---
            imported_snapshot = state.get('transcription_source')
            if not imported_snapshot and 'settings' in state:
                imported_snapshot = (state.get('settings') or {}).get('transcription_source')
                
            if imported_snapshot:
                self._transcription_source = imported_snapshot
                track_names = imported_snapshot.get('track_names', [])
                all_tl_tracks = imported_snapshot.get('all_tracks', True)
                tracks_str = self.txt('txt_all') if (not track_names or all_tl_tracks) else ', '.join(sorted(track_names))
            else:
                tracks_str = self.txt('txt_all')

            # --- Restore Analysis Time ---
            analysis_time = state.get('analysis_time', "")
            if analysis_time and hasattr(self, 'lbl_analysis_duration'):
                import re
                time_match = re.search(r'\d+:\d+', analysis_time)
                if time_match:
                    raw_time = time_match.group(0)
                else:
                    raw_time = analysis_time
                self._last_analysis_time_raw = raw_time
                
                if len(raw_time) > 0 and raw_time[0].isdigit():
                    self.lbl_analysis_duration.setText(self.txt("txt_analyzed_in").replace("{time}", raw_time))
                else:
                    self.lbl_analysis_duration.setText(raw_time)
                self.lbl_analysis_duration.setVisible(True)
            elif hasattr(self, 'lbl_analysis_duration'):
                self.lbl_analysis_duration.setVisible(False)
                
            # --- BWS EXTRA HANDLING ---
            if bws_extras:
                self._assembly_recipe = bws_extras.get("assembly_recipe")
                self._media_inventory = bws_extras.get("media_inventory")
                self._extracted_drt_path = bws_extras.get("drt_path")
                self._extracted_xml_path = bws_extras.get("xml_path")
                
                # Check media inventory
                if missing_media:
                    files_str = ""
                    for m in missing_media[:5]:
                        files_str += f"- {m.get('basename', 'Unknown')}\n"
                    if len(missing_media) > 5:
                        files_str += f"... [+ {len(missing_media)-5}]\n"
                        
                    msg_text = self.txt("bws_media_missing_desc").replace("{files}", files_str.strip())
                    
                    msg_box = WorkspaceWarningOverlay(
                        self._stack,
                        self.txt("bws_media_missing_title"),
                        msg_text,
                        self.txt("bws_btn_continue"),
                        btn_cancel_text=self.txt("btn_cancel")
                    )
                    res = msg_box.exec()
                    if res != QDialog.Accepted:
                        self.go_to_page(getattr(self, '_pre_import_stack_idx', 0))
                        if hasattr(self, '_panel_left'): self._panel_left.hide()
                        if hasattr(self, '_panel_right'): self._panel_right.hide()
                        return
            
                # Check timeline fingerprint
                if bws_extras.get("timeline_fingerprint") and getattr(self, 'resolve_handler', None) and self.resolve_handler.is_connected():
                    if found_tl and is_exact:
                        if target_name and target_name != found_tl:
                            self._transcription_source["timeline_name"] = found_tl
                            if hasattr(self, '_title_bar'):
                                self._title_bar.set_source_info(found_tl, tracks_str)
                    else:
                        cand_import_path = self._extracted_drt_path or getattr(self, '_extracted_xml_path', None)
                        if exists_by_name:
                            msg_box = WorkspaceWarningOverlay(
                                self._stack,
                                self.txt("bws_timeline_changed_title"),
                                self.txt("bws_timeline_changed_desc").format(tl=target_name),
                                self.txt("bws_btn_continue"),
                                btn_reject_text=self.txt("bws_btn_import_drt") if cand_import_path else None,
                                btn_cancel_text=self.txt("btn_cancel")
                            )
                            res = msg_box.exec()
                            if res == -1:  # Cancel
                                self.go_to_page(getattr(self, '_pre_import_stack_idx', 0))
                                if hasattr(self, '_panel_left'): self._panel_left.hide()
                                if hasattr(self, '_panel_right'): self._panel_right.hide()
                                return
                            if res != QDialog.Accepted and cand_import_path:
                                new_name = f"imported '{target_name}'"
                                imp_ok = False
                                actual_name = None
                                if self._extracted_drt_path and not (self.resolve_handler and hasattr(self.resolve_handler, 'is_free_21_1_or_newer') and self.resolve_handler.is_free_21_1_or_newer()):
                                    imp_ok, actual_name = self.resolve_handler.import_timeline_drt(self._extracted_drt_path, new_name)
                                elif getattr(self, '_extracted_xml_path', None):
                                    imp_ok = self.resolve_handler.import_timeline_xml(self._extracted_xml_path, new_name)
                                    actual_name = new_name

                                if imp_ok:
                                    final_name = actual_name or new_name
                                    self._transcription_source["timeline_name"] = final_name
                                    if hasattr(self, '_title_bar'):
                                        self._title_bar.set_source_info(final_name, tracks_str)
                        else:
                            if cand_import_path:
                                msg_box = WorkspaceWarningOverlay(
                                    self._stack,
                                    self.txt("bws_missing_timeline_title"),
                                    self.txt("bws_missing_timeline_desc").format(tl=target_name),
                                    self.txt("bws_btn_import_drt"),
                                    btn_cancel_text=self.txt("btn_cancel")
                                )
                                res = msg_box.exec()
                                if res == -1:
                                    self.go_to_page(getattr(self, '_pre_import_stack_idx', 0))
                                    if hasattr(self, '_panel_left'): self._panel_left.hide()
                                    if hasattr(self, '_panel_right'): self._panel_right.hide()
                                    return
                                if res == QDialog.Accepted:
                                    new_name = f"imported '{target_name}'"
                                    imp_ok = False
                                    actual_name = None
                                    if self._extracted_drt_path and not (self.resolve_handler and hasattr(self.resolve_handler, 'is_free_21_1_or_newer') and self.resolve_handler.is_free_21_1_or_newer()):
                                        imp_ok, actual_name = self.resolve_handler.import_timeline_drt(self._extracted_drt_path, new_name)
                                    elif getattr(self, '_extracted_xml_path', None):
                                        imp_ok = self.resolve_handler.import_timeline_xml(self._extracted_xml_path, new_name)
                                        actual_name = new_name

                                    if imp_ok:
                                        final_name = actual_name or new_name
                                        self._transcription_source["timeline_name"] = final_name
                                        if hasattr(self, '_title_bar'):
                                            self._title_bar.set_source_info(final_name, tracks_str)
                    
            # --- Restore SBS Cache ---
            sbs_cache = state.get('sbs_cache')
            if sbs_cache:
                self._sbs_last_script_hash = sbs_cache.get('hash')
                if hasattr(self, 'text_canvas'):
                    self.text_canvas.sbs_rows = sbs_cache.get('rows', [])
            else:
                self._sbs_last_script_hash = None
                if hasattr(self, 'text_canvas'):
                    self.text_canvas.sbs_rows = []

            # Restore Script
            if hasattr(self, 'text_script') and 'script_content' in state:
                self.text_script.setText(state['script_content'])

            # Load Words Data
            if hasattr(self, 'text_canvas'):
                self.text_canvas.load_data(state.get('words_data', []))
                self._show_transcript_view()
                self._measure_sounds_soon()
                
            # Restore Chapters
            saved_chapters = state.get('chapters', [])
            saved_current_idx = state.get('current_chapter_idx', -1)
            if saved_chapters:
                self._chapters = saved_chapters
                self._current_chapter_idx = saved_current_idx
            else:
                import copy
                self._chapters = [{
                    "name": self.txt("titlebar_original"),
                    "tl_name": self._transcription_source.get("timeline_name", "") if getattr(self, '_transcription_source', None) else "",
                    "words": copy.deepcopy(state.get('words_data', []))
                }]
                self._current_chapter_idx = 0
                
            # Update Dropdown UI
            if self._chapters and hasattr(self, '_title_bar') and hasattr(self._title_bar, 'chapter_dropdown'):
                self._title_bar.chapter_dropdown.options_list = [ch['name'] for ch in self._chapters]
                if 0 <= self._current_chapter_idx < len(self._chapters):
                    self._title_bar.chapter_dropdown.setText(self._chapters[self._current_chapter_idx]['name'])
                self._title_bar.update_dropdown_placement()
                
            if hasattr(self, 'audio_preview') and not from_main_window:
                self.audio_preview.check_audio_availability()

            # Rebuild title from snapshot using new title bar mode
            if getattr(self, '_transcription_source', None):
                snap = self._transcription_source
                tl_name = snap.get('timeline_name', '')
                track_names = snap.get('track_names', [])
                all_tl_tracks = snap.get('all_tracks', True)
                tracks_str = self.txt('txt_all') if (not track_names or all_tl_tracks) else ', '.join(sorted(track_names))
                if hasattr(self, '_title_bar'):
                    self._title_bar.activate_transcription_mode()
                    self._title_bar.set_source_info(tl_name, tracks_str)

            # --- SWITCH TO EDITOR CONTEXT AND OPEN PANELS IF NEEDED ---
            if from_main_window:
                
                if hasattr(self, 'go_to_page'):
                    self.go_to_page(2)
                
                # Open script panel and main panel
                if hasattr(self, 'btn_nav_script'):
                    if not getattr(self.btn_nav_script, 'is_active', False):
                        self._toggle_activity('script_analysis')
                if hasattr(self, 'btn_nav_main'):
                    if not getattr(self.btn_nav_main, 'is_active', False):
                        self._toggle_activity('main_panel')

        except Exception as e:
            from osdoc import log_error
            import traceback
            log_error(f"Failed to load project: {e}\n{traceback.format_exc()}")
            dlg = CustomMsgBox(self, self.txt("lbl_error"), f"{self.txt('msg_load_project_failed')}:\n{e}", self.txt("btn_ok"))
            dlg.exec()

    def _refresh_canvas_view(self):
        if hasattr(self, 'text_canvas') and getattr(self.text_canvas, 'words_data', None):
            self.text_canvas._calculate_layout()
            self.text_canvas.update()

    def _calculate_visual_layer(self, word_obj: dict) -> str:
        """
        Non-Destructive Two-Layer Engine.

        BASE LAYER  — what the word 'is' permanently:
            manual_status (if set by user) > hard auto (hallucination/is_bad) >
            algo repeat > normal

        OVERLAY LAYER — a transient algo highlight that floats on top:
            active only when the matching toggle is ON and the user hasn't
            manually painted over it (overlay_suppressed == False).

        Manual painting sets overlay_suppressed=True so the user color shows.
        Toggle reload sets overlay_suppressed=False so the overlay resurfaces
        WITHOUT touching manual_status.
        """
        # --- BASE LAYER ---
        base = word_obj.get('manual_status')  # None means 'not set by user'
        if base is None:
            if word_obj.get('_is_hallucination') or word_obj.get('is_bad'):
                base = 'bad'
            elif word_obj.get('algo_status') in ('repeat', 'bad') or str(word_obj.get('algo_status') or '').startswith('custom_'):
                base = word_obj['algo_status']
            else:
                base = 'normal'

        # --- OVERLAY LAYER (toggle-gated, suppressed after manual paint) ---
        overlay = None
        if not word_obj.get('overlay_suppressed', False):
            show_typos = hasattr(self, 'tgl_show_typos') and self.tgl_show_typos.isChecked()
            mark_inaud = hasattr(self, 'tgl_mark_inaudible') and self.tgl_mark_inaudible.isChecked()
            if show_typos and word_obj.get('algo_status') == 'typo':
                overlay = 'typo'
            elif mark_inaud and (word_obj.get('is_inaudible') or word_obj.get('type') == 'inaudible'):
                overlay = 'inaudible'

        final = overlay if overlay is not None else base
        word_obj['status'] = final
        word_obj['selected'] = final in ('bad', 'inaudible', 'typo', 'repeat')
        return final

    def _on_inaudible_toggled(self, is_checked: bool):
        if hasattr(self, 'text_canvas') and getattr(self.text_canvas, 'words_data', None):
            self.text_canvas._calculate_layout()
            self.text_canvas.update()

    def _on_mark_inaudible_toggled(self, is_checked: bool):
        """
        Reload for 'Mark inaudible fragments with brown'.
        Turning ON: clears overlay_suppressed so the brown overlay resurfaces on top.
        manual_status is NEVER touched — base layer stays intact.
        """
        if not hasattr(self, 'text_canvas') or not getattr(self.text_canvas, 'words_data', None):
            return

        for word_obj in self.text_canvas.words_data:
            if not (word_obj.get('is_inaudible') or word_obj.get('type') == 'inaudible'):
                continue

            if is_checked:
                # Reload: allow the brown overlay to float back to the top
                word_obj['overlay_suppressed'] = False

            self._calculate_visual_layer(word_obj)

        self.text_canvas._calculate_layout()
        self.text_canvas.update()

    def _on_typos_toggled(self, is_checked: bool):
        """
        Reload for 'Show detected typos'.
        Turning ON: clears overlay_suppressed so the green overlay resurfaces on top.
        manual_status is NEVER touched — base layer stays intact.
        """
        if not hasattr(self, 'text_canvas') or not getattr(self.text_canvas, 'words_data', None):
            return

        for word_obj in self.text_canvas.words_data:
            if word_obj.get('algo_status') != 'typo':
                continue

            if is_checked:
                # Reload: allow the green overlay to float back to the top
                word_obj['overlay_suppressed'] = False

            self._calculate_visual_layer(word_obj)

        self.text_canvas._calculate_layout()
        self.text_canvas.update()
    # ------------------------------------------------------------------
    # Timeline / Track combo population & synchronisation
    # ------------------------------------------------------------------

    def _refresh_davinci_connection(self):
        """Attempts to reconnect to DaVinci Resolve asynchronously and update all badges/combos."""
        from PySide6.QtCore import QThread

        if getattr(self, '_refreshing_connection', False):
            return
        self._refreshing_connection = True

        for btn in (getattr(self, 'btn_ref_source_0', None), getattr(self, 'btn_ref_source_1', None)):
            if btn: btn.setEnabled(False)

        class _RefWorker(QThread):
            def __init__(self, engine):
                super().__init__()
                self._engine = engine

            def run(self):
                try:
                    rh = getattr(self._engine, 'resolve_handler', None)
                    if rh:
                        rh.refresh_context()
                except Exception:
                    pass

        self._ref_worker = _RefWorker(self.engine)

        def _on_done():
            self._refreshing_connection = False
            for btn in (getattr(self, 'btn_ref_source_0', None), getattr(self, 'btn_ref_source_1', None)):
                if btn: btn.setEnabled(True)
            self._populate_timeline_track_combos()
            if hasattr(self, 'header_source_0') and self.header_source_0:
                self.header_source_0.update_status()
            if hasattr(self, 'header_source_1') and self.header_source_1:
                self.header_source_1.update_status()
            if hasattr(self, 'badge_resolve_0') and self.badge_resolve_0:
                self.badge_resolve_0.update_status()
            if hasattr(self, 'badge_resolve_1') and self.badge_resolve_1:
                self.badge_resolve_1.update_status()
            rh = getattr(self.engine, 'resolve_handler', None)
            if rh and rh.is_connected() and getattr(self, 'current_source_type', 'file') == 'resolve':
                if hasattr(self, 'source_area_0'): self.source_area_0.set_mode("resolve")
                if hasattr(self, 'source_area_1'): self.source_area_1.set_mode("resolve")

        self._ref_worker.finished.connect(_on_done)
        self._ref_worker.start()

    def _populate_timeline_track_combos(self):
        """
        Queries the Resolve API for all timelines in the current project and
        populates both timeline dropdowns (combo_tl_0 / combo_tl_1) asynchronously.
        Guarantees zero UI lag / freezing on Windows.
        """
        from PySide6.QtCore import QThread, Signal

        if getattr(self, '_timeline_worker', None) and self._timeline_worker.isRunning():
            return

        for btn in (getattr(self, 'btn_ref_tl0', None), getattr(self, 'btn_ref_tl1', None)):
            if btn: btn.setEnabled(False)

        class _TimelineWorker(QThread):
            data_ready = Signal(list, str, dict)

            def __init__(self, engine):
                super().__init__()
                self._engine = engine

            def run(self):
                try:
                    rh = getattr(self._engine, 'resolve_handler', None)
                    os_doc = getattr(self._engine, 'os_doc', None)
                    if not rh:
                        self.data_ready.emit([], "", {})
                        return

                    if not rh.is_connected():
                        if os_doc and hasattr(os_doc, 'is_process_running'):
                            if not os_doc.is_process_running(["Resolve", "resolve", "fuscript"]):
                                self.data_ready.emit([], "", {})
                                return
                        rh.refresh_context(silent=True)

                    if not rh.is_connected():
                        self.data_ready.emit([], "", {})
                        return

                    tls = rh.get_all_timelines() or []
                    cur_tl = rh.get_current_timeline_name() or ""
                    tracks_map = {}
                    if tls:
                        init_tl = cur_tl if (cur_tl and cur_tl in tls) else tls[0]
                        tracks_map[init_tl] = rh.get_audio_tracks(init_tl) or []

                    self.data_ready.emit(tls, cur_tl, tracks_map)
                except Exception:
                    self.data_ready.emit([], "", {})

        self._timeline_worker = _TimelineWorker(self.engine)

        def _on_timelines_ready(timelines, current_tl_name, tracks_map):
            try:
                no_tl_label = self.txt("msg_no_timelines_detected")

                if not timelines:
                    for combo in (self.combo_tl_0, self.combo_tl_1):
                        combo.options_list = [no_tl_label]
                        combo.setText(no_tl_label)
                    for track_combo in (self.combo_tr_0, self.combo_tr_1):
                        track_combo.options_list = []
                        track_combo.selected_items = set()
                        track_combo.setText(self.txt("msg_no_audio_tracks_detected"))
                    if hasattr(self, 'header_source_0') and self.header_source_0:
                        self.header_source_0.update_status()
                    if hasattr(self, 'header_source_1') and self.header_source_1:
                        self.header_source_1.update_status()
                    if hasattr(self, 'badge_resolve_0') and self.badge_resolve_0:
                        self.badge_resolve_0.update_status()
                    if hasattr(self, 'badge_resolve_1') and self.badge_resolve_1:
                        self.badge_resolve_1.update_status()
                    return

                # Order timelines so that currently active timeline in DaVinci is FIRST
                if current_tl_name and current_tl_name in timelines:
                    ordered_timelines = [current_tl_name] + [t for t in timelines if t != current_tl_name]
                else:
                    ordered_timelines = list(timelines)

                # Populate timeline dropdowns, preserving existing selection if valid
                for combo in (self.combo_tl_0, self.combo_tl_1):
                    current_sel = combo.text() if hasattr(combo, 'text') else ""
                    combo.options_list = list(ordered_timelines)
                    if current_sel and current_sel in ordered_timelines:
                        display = current_sel
                    else:
                        display = ordered_timelines[0]
                    combo.setText(display)

                # Populate track dropdowns for the chosen timeline
                init_tl = self.combo_tl_0.text() if (hasattr(self, 'combo_tl_0') and self.combo_tl_0.text() in ordered_timelines) else ordered_timelines[0]
                init_tracks = tracks_map.get(init_tl)
                if init_tracks is None:
                    rh = getattr(self.engine, 'resolve_handler', None)
                    init_tracks = rh.get_audio_tracks(init_tl) if rh else []
                self._apply_audio_tracks_to_combo(init_tl, init_tracks, self.combo_tr_0)
                self._apply_audio_tracks_to_combo(init_tl, init_tracks, self.combo_tr_1)
                self._refresh_saved_transcript_offer(init_tl)
                if not getattr(self, '_auto_open_checked', False):
                    # First time the timelines arrive: Resolve's current timeline was transcribed before -> open it
                    self._auto_open_checked = True
                    if current_tl_name and init_tl == current_tl_name:
                        QTimer.singleShot(0, self._maybe_auto_open_saved)

                if hasattr(self, 'header_source_0') and self.header_source_0:
                    self.header_source_0.update_status()
                if hasattr(self, 'header_source_1') and self.header_source_1:
                    self.header_source_1.update_status()
                if hasattr(self, 'badge_resolve_0') and self.badge_resolve_0:
                    self.badge_resolve_0.update_status()
                if hasattr(self, 'badge_resolve_1') and self.badge_resolve_1:
                    self.badge_resolve_1.update_status()

            except Exception as e:
                from osdoc import log_error
                log_error(f"_populate_timeline_track_combos ready error: {e}")

        def _on_worker_finished():
            for btn in (getattr(self, 'btn_ref_tl0', None), getattr(self, 'btn_ref_tl1', None)):
                if btn: btn.setEnabled(True)

        self._timeline_worker.data_ready.connect(_on_timelines_ready)
        self._timeline_worker.finished.connect(_on_worker_finished)
        self._timeline_worker.start()

    def _apply_audio_tracks_to_combo(self, tl_name, tracks, track_combo):
        no_track_label = self.txt("msg_no_audio_tracks_detected")
        if not tracks:
            track_combo.options_list = []
            track_combo.selected_items = set()
            track_combo.setText(no_track_label)
        else:
            track_combo.options_list = list(tracks)
            track_combo.selected_items = set(tracks)
            track_combo.setText(self.txt("txt_all_tracks"))

    def _on_timeline_selected(self, tl_name, track_combo, mirror_tl_combo=None):
        """
        Updates *track_combo* with audio tracks for *tl_name* asynchronously, and optionally
        mirrors the selection to *mirror_tl_combo*.
        """
        try:
            if tl_name == self.txt("msg_no_timelines_detected"):
                return
            self._refresh_saved_transcript_offer(tl_name)

            rh = self.engine.resolve_handler
            # Check tracks cache first for instant update
            cached_tracks = getattr(rh, '_tracks_cache', {}).get(tl_name)
            other_track_combo = self.combo_tr_1 if track_combo is getattr(self, 'combo_tr_0', None) else getattr(self, 'combo_tr_0', None)

            if cached_tracks:
                self._apply_audio_tracks_to_combo(tl_name, cached_tracks, track_combo)
                if other_track_combo:
                    self._apply_audio_tracks_to_combo(tl_name, cached_tracks, other_track_combo)
            else:
                from PySide6.QtCore import QThread, Signal
                class _TrackWorker(QThread):
                    done = Signal(str, list)
                    def __init__(self, handler, name):
                        super().__init__()
                        self.h = handler
                        self.name = name
                    def run(self):
                        try:
                            res = self.h.get_audio_tracks(self.name) or []
                            self.done.emit(self.name, res)
                        except Exception:
                            self.done.emit(self.name, [])

                worker = _TrackWorker(rh, tl_name)
                def _on_track_done(name, tr):
                    self._apply_audio_tracks_to_combo(name, tr, track_combo)
                    if other_track_combo:
                        self._apply_audio_tracks_to_combo(name, tr, other_track_combo)
                worker.done.connect(_on_track_done)
                worker.start()
                self._track_query_worker = worker

            # Mirror the timeline selection to the other page's dropdown
            if mirror_tl_combo is not None:
                if tl_name in mirror_tl_combo.options_list and mirror_tl_combo.text() != tl_name:
                    try:
                        mirror_tl_combo.valueChanged.disconnect()
                    except Exception:
                        pass
                    mirror_tl_combo.setText(tl_name)
                    if mirror_tl_combo is self.combo_tl_1:
                        mirror_tl_combo.valueChanged.connect(
                            lambda t: self._on_timeline_selected(t, self.combo_tr_1, self.combo_tl_0)
                        )
                    else:
                        mirror_tl_combo.valueChanged.connect(
                            lambda t: self._on_timeline_selected(t, self.combo_tr_0, self.combo_tl_1)
                        )

        except Exception as e:
            from osdoc import log_error
            log_error(f"_on_timeline_selected error: {e}")

    def _track_names_to_indices(self, tl_name, track_names):
        """Converts track name labels (e.g. {'A1', 'A3', 'Audio 2', 'A2: Voice'}) to 1-based integer indices."""
        if not track_names:
            return []
        try:
            import re
            indices = []
            for name in track_names:
                # 1. Direct regex match on track numbers: A1, A2, A3, Audio 2, etc.
                m = re.search(r'(?:A|Audio\s*)(\d+)', str(name), re.IGNORECASE)
                if m:
                    indices.append(int(m.group(1)))
                else:
                    # 2. Check full timeline track metadata (index, name)
                    a_tracks, _ = self.engine.resolve_handler.get_timeline_tracks(tl_name)
                    matched = False
                    for idx, tname in a_tracks:
                        if name in (tname, f"A{idx}", f"Audio {idx}"):
                            indices.append(idx)
                            matched = True
                            break
                    if not matched:
                        m_any = re.search(r'\d+', str(name))
                        if m_any:
                            indices.append(int(m_any.group(0)))
            return sorted(list(set(indices)))
        except Exception as e:
            from osdoc import log_error
            log_error(f"_track_names_to_indices error: {e}")
            return []

    def _on_fast_silence(self):
        """Fast Silence Cut: runs FFmpeg pipeline then opens the Editor (Page 2) with silence cuts."""
        # ── Source validation ─────────────────────────────────────────────────
        is_file_source = getattr(self, 'current_source_type', 'resolve') == 'file'
        source_file_path = None
        if is_file_source:
            if hasattr(self, 'drop_zone_1'):
                source_file_path = self.drop_zone_1.get_file()
            if not source_file_path or not os.path.isfile(source_file_path):
                if hasattr(self, 'drop_zone_1'):
                    self.drop_zone_1.shake()
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_file_not_selected"), self.txt("btn_ok"))
                dlg.exec()
                return
            from gui.widgets.file_drop_zone import FileDropZone
            if not FileDropZone.is_supported_file(source_file_path):
                if hasattr(self, 'drop_zone_1'):
                    self.drop_zone_1.shake()
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_unsupported_file_format"), self.txt("btn_ok"))
                dlg.exec()
                return
        else:
            rh = getattr(self.engine, 'resolve_handler', None)
            if not rh or not rh.is_connected():
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_resolve_not_connected"), self.txt("btn_ok"))
                dlg.exec()
                return
            selected_tl = getattr(self, 'combo_tl_1', None)
            selected_tl_name = selected_tl.text() if selected_tl else ""
            no_tl = self.txt("msg_no_timelines_detected")
            if not selected_tl_name or selected_tl_name == no_tl:
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_no_timelines_detected"), self.txt("btn_ok"))
                dlg.exec()
                return

        # ── Read from line edits ──────────────────────────────────────────────
        try:
            thresh_val = float(self.input_fs_thresh.text().replace(',', '.'))
        except (ValueError, AttributeError):
            thresh_val = -42.0  # fallback
            
        try:
            pad_val = float(self.input_fs_pad.text().replace(',', '.'))
        except (ValueError, AttributeError):
            pad_val = 0.05  # fallback

        try:
            min_dur_val = float(self.input_fs_min_dur.text().replace(',', '.'))
            min_dur_val = max(0.05, min_dur_val)  # safety clamp
        except (ValueError, AttributeError):
            min_dur_val = 0.2  # fallback

        # Persist updated silence params so post-transcript path uses same values
        _p = self.engine.load_preferences() or {}
        _p['silence_threshold_db'] = thresh_val
        _p['silence_min_dur']      = min_dur_val
        self.engine.save_preferences(_p)

        # ── Switch to Processing Page ─────────────────────────────────────────
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()

        self.go_to_page(1)
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(-1)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("txt_initializing_fast_silence"))

        # Read selected timeline and tracks
        selected_tl = getattr(self, 'combo_tl_1', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        no_tl = self.txt("msg_no_timelines_detected")
        select_txt = self.txt("txt_select", "Wybierz...")
        valid_tls = getattr(selected_tl, 'options_list', []) if selected_tl else []

        if not is_file_source:
            rh = getattr(self.engine, 'resolve_handler', None)
            if not rh or not rh.is_connected():
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_resolve_not_connected"), self.txt("btn_ok"))
                dlg.exec()
                return
            if not selected_tl_name or selected_tl_name in (no_tl, select_txt, "Select...") or (valid_tls and selected_tl_name not in valid_tls):
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_no_timelines_detected"), self.txt("btn_ok"))
                dlg.exec()
                return

        if selected_tl_name == no_tl or selected_tl_name == select_txt:
            selected_tl_name = ""

        selected_tracks_combo = getattr(self, 'combo_tr_1', None)
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        # Update settings for the core
        settings = {
            'threshold_db':    thresh_val,
            'padding_s':       pad_val,
            'silence_min_dur': min_dur_val,
            'timeline_name':   selected_tl_name or None,
            'track_indices':   track_indices or None,
            'source_file':     source_file_path,
        }
        self._fs_settings = settings

        self._analysis_worker = AnalysisWorker(self.engine, 'run_fast_silence_pipeline', settings)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.status.connect(self._on_analysis_status)
        self._analysis_worker.finished_ok.connect(self._on_fs_finished)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.start()


    def _on_fs_finished(self, words_data, segments_data):
        """Called when run_fast_silence_pipeline completes."""
        from PySide6.QtWidgets import QApplication
        from gui.dialogs.msgbox import CustomMsgBox

        if not words_data:
            dlg = CustomMsgBox(self, self.txt("msg_fast_silence"), self.txt("msg_no_silence_segments_detec"), self.txt("btn_ok"))
            dlg.exec()
            self.go_to_page(0)
            if hasattr(self, 'welcome_stack'):
                self.welcome_stack.setCurrentIndex(1)
            return

        is_file_source = (getattr(self, 'current_source_type', 'resolve') == 'file')
        if is_file_source:
            # Standalone local file mode: open editor (Page 2) with silence data and review notice
            info_text = self.txt("msg_silence_detection_mode_active") if hasattr(self, 'txt') else "[Silence Detection: speech transcription was not performed]"
            if words_data and len(words_data) > 0 and words_data[0].get('text') == '[FAST_SILENCE_TRACK]':
                words_data[0]['text'] = info_text

            self._on_analysis_finished(words_data, segments_data)

            if hasattr(self, 'tgl_silence_cut'):
                self.tgl_silence_cut.setChecked(True)
            for widget in self.findChildren(SidebarButton):
                if getattr(widget, 'activity_id', None) == 'silence':
                    if not widget.is_active:
                        self._toggle_activity('silence')
                    break
            return

        # DaVinci Resolve mode: directly assemble the timeline!
        self.lbl_processing_status.setText(self.txt("txt_initializing_assembly") if hasattr(self, 'txt') else "Assembling Timeline...")
        self.bar_processing.set_value(-1)
        QApplication.processEvents()

        fs_prefs = self.engine.load_preferences() or {}
        fs_cut = getattr(self, 'tgl_fs_cut', None)
        fs_mark = getattr(self, 'tgl_fs_mark', None)
        fs_prefs['silence_cut']  = fs_cut.isChecked() if fs_cut else True
        fs_prefs['silence_mark'] = fs_mark.isChecked() if fs_mark else False

        selected_tl = getattr(self, 'combo_tl_1', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        if selected_tl_name == self.txt("msg_no_timelines_detected"):
            selected_tl_name = ""

        selected_tracks_combo = getattr(self, 'combo_tr_1', None)
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        curr_tl_name = selected_tl_name
        if not curr_tl_name:
            rh = getattr(self.engine, 'resolve_handler', None)
            if rh:
                curr_tl_name = rh.get_current_timeline_name()

        fs_prefs["source_snapshot"] = {
            "source_file": None,
            "timeline_name": curr_tl_name,
            "track_indices": track_indices,
            "track_names": selected_track_names
        }

        from PySide6.QtCore import QThread, Signal as _Signal, QObject as _QObject

        class _FsAssemblySignals(_QObject):
            status   = _Signal(str)
            finished = _Signal(object)

        sigs = _FsAssemblySignals()
        sigs.status.connect(self.lbl_processing_status.setText)

        def _on_fs_assemble_done(result):
            self.bar_processing.set_value(100)
            success, warning, new_tl_name, clean_ops = (
                result if (isinstance(result, tuple) and len(result) == 4)
                else (False, None, None, None)
            )
            if success:
                dlg = CustomMsgBox(self, self.txt("msg_fast_silence"), self.txt("msg_fast_silence_processing_c"), self.txt("btn_ok"))
                dlg.exec()
            else:
                dlg = CustomMsgBox(self, self.txt("msg_fast_silence"), f"{self.txt('msg_assembly_failed')}: {warning or ''}", self.txt("btn_ok"))
                dlg.exec()
            self.go_to_page(0)
            if hasattr(self, 'welcome_stack'):
                self.welcome_stack.setCurrentIndex(1)

        sigs.finished.connect(_on_fs_assemble_done)

        class _FsAssemblyThread(QThread):
            def __init__(self, engine, words_data, prefs, sigs):
                super().__init__()
                self._engine = engine
                self._data   = words_data
                self._prefs  = prefs
                self._sigs   = sigs

            def run(self):
                try:
                    result = self._engine.assemble_timeline(
                        self._data,
                        self._prefs,
                        callback_status   = self._sigs.status.emit,
                        callback_progress = lambda v: None,
                    )
                except Exception as _e:
                    import traceback as _tb
                    from osdoc import log_error as _le
                    _le(f"_FsAssemblyThread: {_e}\n{_tb.format_exc()}")
                    result = (False, None, None, None)
                self._sigs.finished.emit(result)

        self._fs_assembly_thread = _FsAssemblyThread(self.engine, words_data, fs_prefs, sigs)
        self._fs_assembly_sigs = sigs
        self._fs_assembly_thread.start()

    def _toggle_favorite(self, target_id: str, source_toggle, label_text: str, pin_btn):
        """Proxy Favorites system — creates or destroys a mirrored ToggleSwitch in layout_favorites."""
        if not hasattr(self, 'layout_favorites') or not hasattr(self, '_favorite_proxies'):
            return

        if target_id in self._favorite_proxies:
            # --- REMOVE favorite ---
            entry = self._favorite_proxies.pop(target_id)
            if entry.get('src_conn') and source_toggle:
                try: source_toggle.toggled.disconnect(entry['src_conn'])
                except Exception: pass
            if entry.get('prx_conn') and entry.get('proxy'):
                try: entry['proxy'].toggled.disconnect(entry['prx_conn'])
                except Exception: pass
            proxy_row = entry['row_widget']
            self.layout_favorites.removeWidget(proxy_row)
            proxy_row.deleteLater()
            if hasattr(pin_btn, 'setChecked'):
                pin_btn.setChecked(False)
            else:
                pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #555555; font-size: 11pt; padding: 0; } QPushButton:hover { color: #aaaaaa; }")
            # Persist removal
            prefs = self.engine.load_preferences() or {}
            favs = prefs.get('favorites', [])
            if target_id in favs: favs.remove(target_id)
            prefs['favorites'] = favs
            self.engine.save_preferences(prefs)
            # Hide label if no favorites left
            if hasattr(self, 'lbl_pinned_favorites'):
                self.lbl_pinned_favorites.setVisible(len(self._favorite_proxies) > 0)
            # Update layer2 size
            if hasattr(self, 'p_main'):
                self.p_main.resizeEvent(None)
        else:
            # --- Enforce max 10 favorites ---
            if len(self._favorite_proxies) >= 10:
                oldest_id = list(self._favorite_proxies.keys())[0]
                if oldest_id in self._pin_buttons:
                    self._pin_buttons[oldest_id].click()
                    
            # --- ADD favorite ---
            from PySide6.QtWidgets import QWidget as _QWidget
            row_widget = _QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            
            prx_conn, src_conn = None, None
            proxy_toggle = None

            if target_id.startswith('cut_'):
                from PySide6.QtGui import QIcon
                from PySide6.QtCore import QSize, Qt
                
                color_name_lower = target_id[4:]
                color_name_title = color_name_lower.capitalize()
                color_hex = "#FFFFFF"
                for c_n, c_h in config.RESOLVE_COLORS_HEX.items():
                    if c_n.lower() == color_name_lower:
                        color_hex = c_h
                        color_name_title = c_n
                        break
                        
                lbl_color = QLabel(self.txt("lbl_cut_color_fmt").format(hex=color_hex, color=label_text))
                row_layout.addWidget(lbl_color)
                row_layout.addStretch()

                # Cut Now Button (proxy)
                btn_cut_now_proxy = QPushButton()
                btn_cut_now_proxy.setFixedSize(24, 24)
                btn_cut_now_proxy.setCursor(Qt.PointingHandCursor)
                btn_cut_now_proxy.setStyleSheet("background: transparent; border: none;")
                btn_cut_now_proxy.setIcon(QIcon(get_layout_icon_path("cut.png")))
                btn_cut_now_proxy.setIconSize(QSize(20, 20))
                btn_cut_now_proxy.setToolTip(self.txt("tooltip_cut_now"))
                btn_cut_now_proxy.clicked.connect(lambda _, c=color_name_title: self._on_cut_now_clicked(c))
                row_layout.addWidget(btn_cut_now_proxy)

                if source_toggle: # Has auto button
                    proxy_auto = QPushButton()
                    proxy_auto.setFixedSize(24, 24)
                    proxy_auto.setCursor(Qt.PointingHandCursor)
                    proxy_auto.setStyleSheet("background: transparent; border: none;")
                    proxy_auto.setCheckable(True)
                    proxy_auto.setToolTip(self.txt("tooltip_auto_cut"))
                    proxy_auto.setChecked(source_toggle.isChecked())
                    
                    def _update_proxy_icon(checked, b=proxy_auto):
                        icon_name = "auto-marked.png" if checked else "auto-unmarked.png"
                        b.setIcon(QIcon(get_layout_icon_path(icon_name)))
                        b.setIconSize(QSize(20, 20))
                    
                    _update_proxy_icon(proxy_auto.isChecked())
                    proxy_auto.toggled.connect(lambda checked, b=proxy_auto, fn=_update_proxy_icon: (fn(checked, b), self._save_auto_cut_prefs()))
                    
                    row_layout.addWidget(proxy_auto)
                    
                    def prx_to_src(v, src=source_toggle, prx=proxy_auto):
                        if src.isChecked() != v: src.setChecked(v)
                    def src_to_prx(v, src=source_toggle, prx=proxy_auto):
                        if prx.isChecked() != v: prx.setChecked(v)

                    prx_conn = proxy_auto.toggled.connect(prx_to_src)
                    src_conn = source_toggle.toggled.connect(src_to_prx)
                    proxy_toggle = proxy_auto
                

                
            else:
                row_layout.addWidget(QLabel(label_text))
                row_layout.addStretch()

                proxy_toggle = ToggleSwitch()
                proxy_toggle.setChecked(source_toggle.isChecked(), animated=False)
                row_layout.addWidget(proxy_toggle)
                


                def prx_to_src(v, src=source_toggle, prx=proxy_toggle):
                    if src.isChecked() != v: src.setChecked(v)
                def src_to_prx(v, src=source_toggle, prx=proxy_toggle):
                    if prx.isChecked() != v: prx.setChecked(v)

                prx_conn = proxy_toggle.toggled.connect(prx_to_src)
                src_conn = source_toggle.toggled.connect(src_to_prx)

            if hasattr(pin_btn, 'setChecked'):
                pin_btn.setChecked(True)
            else:
                pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #f0b429; font-size: 11pt; padding: 0; } QPushButton:hover { color: #f5c842; }")
            
            self.layout_favorites.addWidget(row_widget)

            self._favorite_proxies[target_id] = {
                'row_widget': row_widget,
                'proxy': proxy_toggle,
                'prx_conn': prx_conn,
                'src_conn': src_conn,
            }
            # Persist addition
            prefs = self.engine.load_preferences() or {}
            favs = prefs.get('favorites', [])
            if target_id not in favs: favs.append(target_id)
            prefs['favorites'] = favs
            self.engine.save_preferences(prefs)
            # Show label when first favorite is added
            if hasattr(self, 'lbl_pinned_favorites'):
                self.lbl_pinned_favorites.setVisible(True)
            # Update layer2 size
            if hasattr(self, 'p_main'):
                self.p_main.resizeEvent(None)


    def _save_auto_cut_prefs(self):
        prefs = self.engine.load_preferences() or {}
        if hasattr(self, 'color_cut_buttons'):
            auto_cut = [c_name for c_name, btn in self.color_cut_buttons.items() if btn.isChecked()]
            prefs['auto_cut_colors'] = auto_cut
        self.engine.save_preferences(prefs)
        if hasattr(self, 'audio_preview') and hasattr(self.audio_preview, 'waveform_timeline'):
            canvas = getattr(self, 'text_canvas', None)
            words = canvas.words_data if canvas else []
            self.audio_preview.waveform_timeline.set_words_data(words)

    def _save_top_toggles_prefs(self):
        prefs = self.engine.load_preferences() or {}
        if hasattr(self, 'tgl_show_inaudible'): prefs['show_inaudible'] = self.tgl_show_inaudible.isChecked()
        if hasattr(self, 'tgl_show_typos'): prefs['show_typos'] = self.tgl_show_typos.isChecked()
        if hasattr(self, 'tgl_mark_inaudible'): prefs['mark_inaudible'] = self.tgl_mark_inaudible.isChecked()
        self.engine.save_preferences(prefs)
        if hasattr(self, 'audio_preview') and hasattr(self.audio_preview, 'waveform_timeline'):
            canvas = getattr(self, 'text_canvas', None)
            words = canvas.words_data if canvas else []
            self.audio_preview.waveform_timeline.set_words_data(words)

    def _save_silence_toggles_prefs(self):
        prefs = self.engine.load_preferences() or {}
        if hasattr(self, 'tgl_silence_cut'):
            v_cut = self.tgl_silence_cut.isChecked()
            prefs['silence_cut'] = v_cut
            prefs['ui_tgl_silence_cut'] = v_cut
        if hasattr(self, 'tgl_silence_mark'):
            v_mark = self.tgl_silence_mark.isChecked()
            prefs['silence_mark'] = v_mark
            prefs['ui_tgl_silence_mark'] = v_mark
        self.engine.save_preferences(prefs)
        self._refresh_cut_preview()

    def _refresh_cut_preview(self):
        """Recompute the waveform cut preview (and the silence readout) from current prefs."""
        if hasattr(self, 'audio_preview') and hasattr(self.audio_preview, 'waveform_timeline'):
            canvas = getattr(self, 'text_canvas', None)
            words = canvas.words_data if canvas else []
            self.audio_preview.waveform_timeline.set_words_data(words)

    def _update_silence_stats(self, surviving_ops, cut_ops, total_dur):
        """Show how many pauses the current silence settings cut or mark, and how much time."""
        lbl = getattr(self, 'lbl_silence_stats', None)
        if lbl is None:
            return
        cut = self.tgl_silence_cut.isChecked() if hasattr(self, 'tgl_silence_cut') else False
        mark = self.tgl_silence_mark.isChecked() if hasattr(self, 'tgl_silence_mark') else False
        if cut:
            spans = [(op['start_s'], op['end_s']) for op in cut_ops if op.get('cut_type') == 'silence_cut']
            key = "lbl_silence_stats_cut"
        elif mark:
            spans = [(op['start_s'], op['end_s']) for op in surviving_ops if op.get('type') == 'silence_mark']
            key = "lbl_silence_stats_mark"
        else:
            lbl.setText("")
            return
        secs = sum(max(0.0, e - s) for s, e in spans)
        pct = int(round(100.0 * secs / total_dur)) if total_dur > 0 else 0
        lbl.setText(self.txt(key).format(
            count=len(spans), removed=f"{int(secs // 60)}:{int(secs % 60):02d}", pct=pct))

    # ── Colour legend ───────────────────────────────────────────────────────
    _LEGEND_OP_KEYS = {"bad": "Violet", "repeat": "Navy", "typo": "Olive",
                       "inaudible": "Chocolate", "silence_mark": "Tan"}
    _LEGEND_CUT_KEYS = {"red_cut": "Violet", "blue_cut": "Navy", "green_cut": "Olive",
                        "inaudible_cut": "Chocolate", "silence_cut": "Tan"}
    _LEGEND_MEANINGS = {"Violet": "legend_meaning_bad", "Navy": "legend_meaning_repeat",
                        "Olive": "legend_meaning_typo", "Tan": "legend_meaning_silence",
                        "Chocolate": "legend_meaning_inaudible"}

    def _legend_key(self, type_name, is_cut):
        """Map an op type (kept) or cut_type (removed) to its Resolve colour name."""
        t = str(type_name or "")
        table = self._LEGEND_CUT_KEYS if is_cut else self._LEGEND_OP_KEYS
        if t in table:
            return table[t]
        if is_cut and t.endswith("_cut"):
            t = t[:-4]
        if t.startswith("custom_"):
            c = t.split("_", 1)[1].lower()
            for name in config.RESOLVE_COLORS_HEX:
                if name.lower() == c:
                    return name
        return None

    def _update_text_cut_preview(self, surviving_ops):
        """Show in the text view what the next Assemble removes: dropped words are struck
        through, and a mark sits where a pause between kept words is cut out.
        Fed by the waveform preview, so both views come from the same cut calculation."""
        import bisect
        canvas = getattr(self, 'text_canvas', None)
        if canvas is None or not hasattr(canvas, 'set_cut_preview'):
            return
        offset = float((self.engine.load_preferences() or {}).get('offset', 0.133))
        spans = sorted((op['start_s'], op['end_s']) for op in surviving_ops)
        starts = [s for s, _ in spans]
        preview, prev = {}, None
        for w in canvas.words_data or []:
            if w.get('type') in ('silence', 'inaudible') or w.get('is_inaudible') or 'id' not in w:
                continue
            # Same rule as Assemble: a word stays when its middle lands inside a kept clip
            t = (w.get('start', 0.0) + w.get('end', 0.0)) / 2.0 + offset
            i = bisect.bisect_right(starts, t) - 1
            if i < 0 or t >= spans[i][1]:
                preview[w['id']] = 'cut'
                prev = None
                continue
            if prev is not None and i != prev and any(
                    spans[k + 1][0] - spans[k][1] > 1e-3 for k in range(prev, i)):
                preview[w['id']] = 'jump'
            prev = i
        canvas.set_cut_preview(preview)

    def _open_activity(self, activity_id):
        """Show a sidebar panel (never closes it, unlike clicking its button)."""
        for widget in self.findChildren(SidebarButton):
            if widget.activity_id == activity_id:
                if not widget.is_active:
                    self._toggle_activity(activity_id)
                return

    def _show_track_options(self):
        """The ▾ next to Send to Resolve: open the panel with the track options, expanded."""
        self._open_activity("main_panel")
        drawer = getattr(self, 'w_track_options', None)
        if drawer is not None and not drawer.is_expanded and hasattr(self, '_toggle_track_options'):
            self._toggle_track_options()

    def _set_send_enabled(self, enabled, text=None):
        """Lock or unlock Send to Resolve (workflow bar) together with the old Assemble button."""
        if hasattr(self, 'btn_assemble'):
            if enabled:
                self.btn_assemble.set_assemble_enabled(True)
            else:
                self.btn_assemble.set_assemble_enabled(False, text)
        btn = getattr(self, 'btn_send_resolve', None)
        if btn is not None:
            btn.setEnabled(enabled)
            btn.setText(self.txt("btn_assemble") if enabled or not text else text)

    def _update_resolve_chip(self):
        """Title bar chip: is DaVinci Resolve connected (cheap check, no call into Resolve)."""
        rh = getattr(self.engine, 'resolve_handler', None) or getattr(self, 'resolve_handler', None)
        try:
            connected = bool(rh is not None and rh.is_connected())
        except Exception:
            connected = False
        text = self.txt("lbl_resolve_connected" if connected else "lbl_resolve_offline")
        if getattr(self, '_resolve_chip_state', None) == (connected, text):
            return
        self._resolve_chip_state = (connected, text)
        tb = getattr(self, '_title_bar', None)
        if tb is not None and hasattr(tb, 'set_resolve_status'):
            tb.set_resolve_status(connected, text)
        chip = getattr(self, 'lbl_resolve_chip', None)  # the workflow bar (the title bar is native on macOS)
        if chip is not None:
            from gui.theme import qc
            dot = qc("#23a559").name() if connected else "#777777"
            chip.setText(f"<span style='color:{dot}'>●</span>&nbsp; {text}")
            chip.setStyleSheet(f"color: #a0a0a0; font-size: {config.FS(8.5)}pt; background: #1e1e1e; border: 1px solid #333333;"
                               f" border-radius: {config.S(10)}px; padding: {config.S(2)}px {config.S(10)}px;")
            chip.show()

    def _set_workflow_step(self, step):
        """Fill the pill of the step the user is on."""
        for name, (btn, badge, text) in getattr(self, 'workflow_steps', {}).items():
            on = "true" if name == step else "false"
            for w in (btn, badge, text):
                w.setProperty("active", on)
                w.style().unpolish(w)
                w.style().polish(w)

    def _on_workflow_step(self, step):
        self._set_workflow_step(step)
        if step == "cleanup":
            # Pauses and colours: what gets removed. If both live on one side, the colours win.
            self._open_activity("silence")
            self._open_activity("assembly")
        elif step == "compose":
            self._open_activity("story")

    def _update_workflow_summary(self, total_s):
        lbl = getattr(self, 'lbl_workflow_summary', None)
        if lbl is None:
            return
        secs = int(round(max(0.0, total_s)))
        dur = f"{secs // 60}:{secs % 60:02d}"
        story = getattr(self, '_story', None)
        if story:
            lbl.setText(self.txt("wf_summary_story").format(blocks=len(story.get("clips", [])), duration=dur))
        else:
            lbl.setText(self.txt("wf_summary_all").format(duration=dur))

    def _story_ops_context(self):
        """(kept ops, fps, offset) exactly as the next Assemble computes them."""
        canvas = getattr(self, 'text_canvas', None)
        if not canvas or not canvas.words_data:
            return None
        prefs = self._live_cut_prefs()
        rh = getattr(self.engine, 'resolve_handler', None)
        fps = getattr(rh, 'fps', None) or 24.0
        ops, _ = self.engine.calculate_timeline_structure_with_cuts([dict(w) for w in canvas.words_data], fps, prefs)
        return ops, fps, float(prefs.get('offset', 0.133))

    def _set_story_from_board(self, clips):
        """The story board's Edit list became the story (None/empty = normal Assemble)."""
        if clips:
            import algorithms
            canvas = getattr(self, 'text_canvas', None)
            if canvas is not None and canvas.words_data and (self.engine.load_preferences() or {}).get('refine_cuts', True):
                # clean cut points: a little air before and after, on the quietest moment, never inside a word
                clips = algorithms.refine_clip_edges(clips, canvas.words_data, self._edit_audio())
            self._story = {"clips": clips, "keep_source_order": False, "duration": 0.0}
            ctx = self._story_ops_context()
            if ctx:
                ops, fps, offset = ctx
                self._story["duration"] = sum(o['e'] - o['s'] for o in algorithms.apply_story_order(ops, clips, fps, offset)) / fps
        else:
            self._story = None
        self._update_story_banner()
        self._refresh_cut_preview()

    def _update_edit_playlist(self, surviving_ops, fps):
        """Feed Play edit with the kept source ranges in the order the next Assemble plays them."""
        ap = getattr(self, 'audio_preview', None)
        if ap is None or not hasattr(ap, 'set_edit_segments'):
            return
        ops = [dict(op) for op in surviving_ops]
        story = getattr(self, '_story', None)
        offset = float((self.engine.load_preferences() or {}).get('offset', 0.133))
        board = getattr(self, 'story_board', None)
        if board is not None:
            board.refresh_lengths((surviving_ops, fps, offset))
            if surviving_ops:
                # The saved board for this timeline, once its transcript is in (deferred: we are inside
                # the waveform's recalculation, and restoring triggers another one)
                QTimer.singleShot(0, board.maybe_restore)
        if story and ops:
            import algorithms
            ops = algorithms.apply_story_order(ops, story["clips"], fps, offset=offset,
                                               keep_source_order=bool(story.get("keep_source_order")))
            # Cut settings changed the story's length: keep the banner and board header honest
            story["duration"] = sum(o['e'] - o['s'] for o in ops) / fps
            self._update_story_banner()
        else:
            ops.sort(key=lambda o: o['s'])
        self._update_workflow_summary(sum(o['e'] - o['s'] for o in ops) / fps if fps else 0.0)
        segments = []
        for op in ops:
            s, e = float(op['start_s']), float(op['end_s'])
            if e <= s:
                continue
            if segments and abs(s - segments[-1][1]) < 1e-3:
                segments[-1] = (segments[-1][0], e)  # touching clips play as one
            else:
                segments.append((s, e))
        ap.set_edit_segments(segments)

    def _update_color_legend(self, surviving_ops, cut_ops):
        """Summarise which colours the next Assemble keeps (as coloured clips) or leaves out.
        Fed by the waveform preview, which runs the same cut calculation as Assemble."""
        self._refresh_detection_counts()
        if not hasattr(self, 'legend_layout'):
            return
        stats = {}

        def _count(key, slot, seconds):
            st = stats.setdefault(key, [0, 0.0, 0, 0.0, 0, 0.0])
            st[slot] += 1
            st[slot + 1] += max(0.0, seconds)

        for ops, is_cut, field in ((surviving_ops, False, 'type'), (cut_ops, True, 'cut_type')):
            for op in ops:
                if not is_cut and op.get('plain_parts'):
                    # "Keep" parts sit inside ordinary clips; count each one under its colour
                    fps_op = (op['e'] - op['s']) / max(1e-9, float(op.get('end_s', 0.0)) - float(op.get('start_s', 0.0)))
                    for p_type, p_s, p_e in op['plain_parts']:
                        key = self._legend_key(p_type, False)
                        if key:
                            _count(key, 4, (p_e - p_s) / fps_op if fps_op > 0 else 0.0)
                    continue
                key = self._legend_key(op.get(field), is_cut)
                if not key:
                    continue
                _count(key, 2 if is_cut else 0, float(op.get('end_s', 0.0)) - float(op.get('start_s', 0.0)))
        modes = tuple(sorted((self._legend_mode(k) or "") for k in stats))
        sig = tuple(sorted((k, *(round(x, 1) for x in v)) for k, v in stats.items())) + modes
        if sig == getattr(self, '_legend_signature', None):
            return
        self._legend_signature = sig
        # Deferred: this can run inside a toggle handler of a row we are about to rebuild
        QTimer.singleShot(0, lambda s=stats: self._render_color_legend(s))

    def _render_color_legend(self, stats):
        import html
        lay = getattr(self, 'legend_layout', None)
        if lay is None:
            return
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not stats:
            empty = QLabel(self.txt("legend_empty"))
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color: #808080; font-size: {config.FS(9)}pt;")
            lay.addWidget(empty)
            return

        markers = {}
        for cm in (self.engine.load_preferences() or {}).get('custom_markers', []) or []:
            if cm.get('name') and cm.get('color'):
                markers.setdefault(cm['color'].lower(), []).append(cm['name'])
        cut_buttons = getattr(self, 'color_cut_buttons', {})

        def _dur(s):
            return f"{int(s // 60)}:{int(s % 60):02d}"

        for key, hex_col in config.RESOLVE_COLORS_HEX.items():
            if key not in stats:
                continue
            kept_n, kept_s, cut_n, cut_s, plain_n, plain_s = stats[key]
            name = self.txt(f"resolve_color_{key.lower()}")
            if key in self._LEGEND_MEANINGS:
                meaning = self.txt(self._LEGEND_MEANINGS[key])
            else:
                meaning = ", ".join(markers.get(key.lower(), [])) or self.txt("legend_meaning_custom")
            parts = []
            if kept_n:
                parts.append(self.txt("legend_kept").format(count=kept_n, dur=_dur(kept_s)))
            if plain_n:
                parts.append(self.txt("legend_kept_plain").format(count=plain_n, dur=_dur(plain_s)))
            if cut_n:
                parts.append(self.txt("legend_removed").format(count=cut_n, dur=_dur(cut_s)))
            if name.lower() != key.lower():
                parts.append(self.txt("legend_resolve_name").format(color=key))

            # Line 1: swatch, name, Keep / Mark / Cut. Line 2: what it means and how much of it there is.
            row = QWidget()
            v = QVBoxLayout(row)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(config.S(2))
            h = QHBoxLayout()
            h.setSpacing(config.S(8))
            swatch = QLabel()
            swatch.setFixedSize(config.S(12), config.S(12))
            swatch.setStyleSheet(f"background: {hex_col}; border-radius: {config.S(2)}px;")
            h.addWidget(swatch, 0, Qt.AlignVCenter)
            h.addWidget(QLabel(f"<b>{html.escape(name)}</b>"), 1)
            v.addLayout(h)
            text = QLabel(f"{html.escape(meaning)}<br><span style='color:#808080'>{html.escape(' · '.join(parts))}</span>")
            text.setWordWrap(True)
            text.setContentsMargins(config.S(20), 0, 0, 0)
            v.addWidget(text)

            from gui.widgets.segmented import SegmentedChoice
            mode = self._legend_mode(key)
            seg = SegmentedChoice([("keep", self.txt("btn_pause_keep")), ("mark", self.txt("btn_pause_mark")),
                                   ("cut", self.txt("btn_pause_cut"))], mode or "mark", compact=True)
            if mode is None:
                seg.setEnabled(False)
                seg.setToolTip(self.txt("tt_legend_not_removable"))
            else:
                seg.setToolTip(self.txt("tt_color_mode"))
            seg.changed.connect(lambda m, k=key: self._on_legend_mode(k, m))
            h.addWidget(seg, 0, Qt.AlignVCenter)
            lay.addWidget(row)

    def _legend_mode(self, key):
        """Keep / Mark / Cut for a colour, or None when it can't be changed here (inaudible)."""
        if key == "Tan":
            if not hasattr(self, 'tgl_silence_cut'):
                return None
            return "cut" if self.tgl_silence_cut.isChecked() else ("mark" if self.tgl_silence_mark.isChecked() else "keep")
        btn = getattr(self, 'color_cut_buttons', {}).get(key)
        if btn is None:
            return None
        if btn.isChecked():
            return "cut"
        plain = {c.lower() for c in (self.engine.load_preferences() or {}).get('plain_colors', []) or []}
        return "keep" if key.lower() in plain else "mark"

    def _on_legend_mode(self, key, mode):
        """Keep = stays in, without colour; Mark = stays as a coloured clip; Cut = removed."""
        if key == "Tan":
            if mode == "cut":
                self.tgl_silence_cut.setChecked(True)
            elif mode == "mark":
                self.tgl_silence_mark.setChecked(True)
            else:
                self.tgl_silence_cut.setChecked(False)
                self.tgl_silence_mark.setChecked(False)
            return
        prefs = self.engine.load_preferences() or {}
        plain = [c for c in (prefs.get('plain_colors', []) or []) if c.lower() != key.lower()]
        if mode == "keep":
            plain.append(key)
        prefs['plain_colors'] = plain
        self.engine.save_preferences(prefs)
        btn = getattr(self, 'color_cut_buttons', {}).get(key)
        if btn is not None and btn.isChecked() != (mode == "cut"):
            btn.setChecked(mode == "cut")  # saves auto-cut prefs and refreshes the preview
        else:
            self._refresh_cut_preview()

    def _on_legend_remove_toggled(self, key, checked):
        """Legend checkbox = the colour's auto-cut (A) button, or the silence cut/mark toggles."""
        if key == "Tan":
            if checked and hasattr(self, 'tgl_silence_cut'):
                self.tgl_silence_cut.setChecked(True)
            elif not checked and hasattr(self, 'tgl_silence_mark'):
                self.tgl_silence_mark.setChecked(True)
            return
        btn = getattr(self, 'color_cut_buttons', {}).get(key)
        if btn is not None and btn.isChecked() != checked:
            btn.setChecked(checked)

    def _on_assemble(self):
        if getattr(self, '_is_live_transcribing', False):
            return
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return

        from PySide6.QtWidgets import QApplication

        prefs = self.engine.load_preferences() or {}
        
        # INJECT SOURCE SNAPSHOT & TRACK SELECTION
        src = getattr(self, '_transcription_source', None)
        if not src:
            saved_src = (prefs or {}).get('transcription_source')
            if saved_src:
                src = saved_src
                self._transcription_source = src
                
        if src:
            track_config = src.get('assembly_track_config')
            if not track_config:
                track_config = {'audio_mode': 'all', 'video_mode': 'all'}
                src['assembly_track_config'] = track_config
                prefs['transcription_source'] = src
                self.engine.save_preferences(prefs)
            prefs["source_snapshot"] = src

        # GATHER UI STATES
        if hasattr(self, 'tgl_silence_cut'): prefs['silence_cut'] = self.tgl_silence_cut.isChecked()
        if hasattr(self, 'tgl_silence_mark'): prefs['silence_mark'] = self.tgl_silence_mark.isChecked()
        if hasattr(self, 'tgl_reviewer'): prefs['enable_reviewer'] = self.tgl_reviewer.isChecked()
        if hasattr(self, 'tgl_show_inaudible'): prefs['show_inaudible'] = self.tgl_show_inaudible.isChecked()
        if hasattr(self, 'tgl_show_typos'): prefs['show_typos'] = self.tgl_show_typos.isChecked()
        if hasattr(self, 'tgl_mark_inaudible'): prefs['mark_inaudible'] = self.tgl_mark_inaudible.isChecked()

        if hasattr(self, 'color_cut_buttons'):
            auto_cut = [c_name for c_name, btn in self.color_cut_buttons.items() if btn.isChecked()]
            prefs['auto_cut_colors'] = auto_cut

        checked_btn = getattr(self, 'marker_btn_group', None) and self.marker_btn_group.checkedButton()
        if checked_btn:
            prefs['mark_tool'] = checked_btn.property("status_id")

        self.engine.save_preferences(prefs)

        story = getattr(self, '_story', None)
        if story:
            prefs['story_clips'] = story["clips"]
            prefs['story_keep_source_order'] = story.get("keep_source_order", False)

        # SANITIZE EXPORT DATA (prevents C++ QRect deepcopy memory leaks)
        export_data    = self._get_clean_words_data()
        show_typos     = prefs.get('show_typos', True)
        mark_inaudible = prefs.get('mark_inaudible', False)
        for w in export_data:
            if w.get('status') == 'typo' and not show_typos:
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    w['status'] = None
            if w.get('status') == 'inaudible' and not mark_inaudible:
                w['status'] = None

        # UI PREP — infinite bar starts immediately so it animates during assembly
        self._panel_left.hide()
        self._panel_right.hide()
        self.go_to_page(1)
        self.lbl_processing_status.setText(self.txt("txt_initializing_assembly"))
        self.bar_processing.set_value(-1)   # infinite sweep animation
        QApplication.processEvents()

        # ── WORKER SIGNALS ────────────────────────────────────────────────────
        from PySide6.QtCore import QThread, Signal as _Signal, QObject as _QObject

        class _AssemblySignals(_QObject):
            status   = _Signal(str)
            finished = _Signal(object)   # carries result tuple

        _sigs = _AssemblySignals()
        _sigs.status.connect(self.lbl_processing_status.setText)
        _sigs.finished.connect(self._on_assemble_done)

        # ── WORKER THREAD ─────────────────────────────────────────────────────
        class _AssemblyThread(QThread):
            def __init__(self, engine, export_data, prefs, sigs):
                super().__init__()
                self._engine = engine
                self._data   = export_data
                self._prefs  = prefs
                self._sigs   = sigs

            def run(self):
                try:
                    result = self._engine.assemble_timeline(
                        self._data,
                        self._prefs,
                        callback_status   = self._sigs.status.emit,
                        callback_progress = lambda v: None,  # bar stays infinite
                    )
                except Exception as _e:
                    import traceback as _tb
                    from osdoc import log_error as _le
                    _le(f"_AssemblyThread: {_e}\n{_tb.format_exc()}")
                    result = (False, None, None, None)
                self._sigs.finished.emit(result)

        self._assembly_thread = _AssemblyThread(self.engine, export_data, prefs, _sigs)
        self._assembly_sigs   = _sigs   # keep alive until finished signal fires
        self._assembly_prefs  = prefs
        
        # Delay thread start to ensure loading UI transition finishes before GIL is locked
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, lambda: self._assembly_thread.start())

    def _on_assemble_done(self, result):
        """Called on main thread when assembly QThread finishes."""
        from PySide6.QtWidgets import QApplication

        self.bar_processing.set_value(100)

        success, warning, new_tl_name, clean_ops = (
            result if (isinstance(result, tuple) and len(result) == 4)
            else (False, None, None, None)
        )

        # Sync snapshot back (engine mutates prefs["source_snapshot"] in-place)
        prefs = getattr(self, '_assembly_prefs', {}) or {}
        updated_snapshot = prefs.get("source_snapshot")
        if updated_snapshot and hasattr(self, '_transcription_source'):
            new_filtered = updated_snapshot.get("filtered_tl_name")
            if new_filtered and self._transcription_source.get("filtered_tl_name") != new_filtered:
                self._transcription_source["filtered_tl_name"] = new_filtered
                try:
                    _p = self.engine.load_preferences() or {}
                    _p["transcription_source"] = self._transcription_source
                    self.engine.save_preferences(_p)
                except Exception:
                    pass

        if success:
            self.lbl_processing_status.setText(self.txt("txt_finishing"))
            QApplication.processEvents()
            self._on_assembly_success(new_tl_name, clean_ops)
        else:
            self._on_assembly_error(self.txt("msg_assembly_failed"))

        # RAM cleanup — MUST happen AFTER success/error handler so _assembly_prefs is available
        try:
            import gc
            self._assembly_thread = None
            self._assembly_sigs   = None
            self._assembly_prefs  = None
            gc.collect()
        except Exception:
            pass


    def _on_assembly_success(self, new_tl_name, clean_ops):
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        if getattr(self, 'resolve_handler', None) and new_tl_name:
            try:
                self.resolve_handler.set_current_timeline(new_tl_name)
            except Exception:
                pass
        
        # Audio preview mapping
        if hasattr(self, 'audio_preview') and getattr(self, '_assembly_prefs', None):
            words = self._get_clean_words_data()
            if words and words[0].get('meta_audio_path'):
                audio_path = words[0].get('meta_audio_path')
                import os
                if clean_ops:
                    fps = getattr(self.resolve_handler, 'fps', 24.0)
                    ffmpeg_cmd = self.engine.os_doc.get_ffmpeg_cmd()
                    if ffmpeg_cmd and os.path.exists(audio_path):
                        assembled_audio_path = audio_path.replace(".wav", "_assembled.wav")
                        from PySide6.QtCore import QThread, Signal
                        
                        class WavAssemblyThread(QThread):
                            finished = Signal(str, list)
                            def __init__(self, parent, in_path, out_path, ops, fps, ffmpeg_cmd, sp_kwargs):
                                super().__init__(parent)
                                self.in_path = in_path
                                self.out_path = out_path
                                self.ops = ops
                                self.fps = fps
                                self.ffmpeg_cmd = ffmpeg_cmd
                                self.sp_kwargs = sp_kwargs
                            def run(self):
                                import wave
                                import subprocess
                                import os
                                import tempfile
                                try:
                                    temp_wav_src = tempfile.mktemp(suffix=".wav")
                                    decode_cmd = [
                                        self.ffmpeg_cmd, "-y", "-i", self.in_path,
                                        "-acodec", "pcm_s16le", temp_wav_src
                                    ]
                                    subprocess.run(decode_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **self.sp_kwargs)
                                    
                                    if not os.path.exists(temp_wav_src):
                                        raise Exception("FFmpeg decode failed to produce WAV file.")
                                        
                                    with wave.open(temp_wav_src, 'rb') as w_in:
                                        params = w_in.getparams()
                                        nframes = w_in.getnframes()
                                        with wave.open(self.out_path, 'wb') as w_out:
                                            w_out.setparams(params)
                                            sr = params.framerate
                                            
                                            for op in self.ops:
                                                start_s = op['s'] / self.fps
                                                end_s = op['e'] / self.fps
                                                
                                                start_frame = int(start_s * sr)
                                                end_frame = int(end_s * sr)
                                                
                                                # Clamp to available frames to prevent wave.Error
                                                start_frame = max(0, min(start_frame, nframes))
                                                end_frame = max(0, min(end_frame, nframes))
                                                
                                                frames_to_read = max(0, end_frame - start_frame)
                                                
                                                if frames_to_read > 0:
                                                    w_in.setpos(start_frame)
                                                    data = w_in.readframes(frames_to_read)
                                                    w_out.writeframes(data)
                                                    
                                    try: os.remove(temp_wav_src)
                                    except: pass
                                    self.finished.emit(self.out_path, self.ops)
                                except Exception as e:
                                    from osdoc import log_error
                                    log_error(f"Wav assembly exception: {e}")
                                    
                        kwargs = self.engine.os_doc.get_subprocess_kwargs()
                        self._ffmpeg_thread = WavAssemblyThread(self, audio_path, assembled_audio_path, clean_ops, fps, ffmpeg_cmd, kwargs)
                        self._ffmpeg_thread.finished.connect(self.audio_preview.load_assembled_audio)
                        self._ffmpeg_thread.start()
                else:
                    self.audio_preview.check_audio_availability()
        
        is_sbs = getattr(self.text_canvas, 'is_sbs_mode', False)
        if hasattr(self, '_panel_left') and not is_sbs: self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        
        # --- CHAPTER REGISTRATION ---
        new_words = self._get_clean_words_data()
                
        chapter_name = f"Edit {len(self._chapters)}"
        new_chapter = {
            "name": chapter_name,
            "tl_name": new_tl_name or "",
            "words": new_words
        }
        self._chapters.append(new_chapter)
        self._current_chapter_idx = len(self._chapters) - 1
        
        # Update dropdown
        self._title_bar.chapter_dropdown.options_list = [ch['name'] for ch in self._chapters]
        self._title_bar.chapter_dropdown.setText(chapter_name)
        self._title_bar.update_dropdown_placement()
        
        # Load the new state
        self.text_canvas.load_data(new_words)
        self._show_transcript_view()
        
        dlg = CustomMsgBox(self, self.txt("msg_success"), self.txt("msg_timeline_assembled_succes"), self.txt("btn_ok"))
        dlg.exec()

    def _on_assembly_error(self, err_msg):
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        dlg = CustomMsgBox(self, self.txt("lbl_error"), err_msg, self.txt("btn_ok"))
        dlg.exec()

    def _build_welcome_screen(self) -> QWidget:
        """Page 0 of the main stack: Welcome / Config screen."""
        from gui.views import build_welcome_view
        view = build_welcome_view(self)
        if hasattr(view, 'preload'):
            sb_w = getattr(config, 'SIDEBAR_WIDTH', config.S(50))
            target_w = max(config.S(600), self.width() - 2 * sb_w)
            target_h = max(config.S(400), self.height() - config.S(36))
            view.preload(target_w, target_h)
        return view

    def _build_page_processing(self) -> QWidget:
        """Page 1 of the main stack: Processing / Progress screen."""
        from gui.views import build_processing_view
        return build_processing_view(self)

    def _update_processing_progress(self, val: int):
        if hasattr(self, 'bar_processing'):
            if val <= 0:
                self.bar_processing.set_value(-1)
            else:
                self.bar_processing.set_value(val)

    def _build_page_editor(self) -> QWidget:
        """Page 2 of the main stack: Interactive Transcript Editor screen."""
        from gui.views import build_editor_view
        return build_editor_view(self)

    def _show_transcript_view(self):
        if hasattr(self, 'editor_view_stack'):
            self.editor_view_stack.setCurrentIndex(0)

    def _create_info_icon(self, tooltip_key: str) -> QLabel:
        info = QLabel()
        info_icon_path = get_layout_icon_path("information.png")
        if os.path.exists(info_icon_path):
            pix = QPixmap(info_icon_path)
            dpr = self.devicePixelRatioF() if hasattr(self, 'devicePixelRatioF') else 1.0
            size = config.S(16)
            scaled_pix = pix.scaled(int(size * dpr), int(size * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled_pix.setDevicePixelRatio(dpr)
            info.setPixmap(scaled_pix)
        else:
            info.setText("🛈")
            info.setStyleSheet("color: #888888; font-size: 11pt;")
            
        tt_text = self.txt(tooltip_key) if hasattr(self, 'txt') else tooltip_key
        info.custom_tooltip_text = tt_text or ""
        info.setCursor(Qt.WhatsThisCursor)
        
        def instant_tooltip(event):
            if hasattr(self, 'shared_tooltip'):
                self.shared_tooltip.show_global(info.custom_tooltip_text, QCursor.pos())
        info.enterEvent = instant_tooltip
        info.leaveEvent = lambda e: self.shared_tooltip.hide() if hasattr(self, 'shared_tooltip') else None
        return info



    def _populate_editor(self, words_data, segments_data):
        import copy
        _orig_label = self.txt("titlebar_original")
        self._chapters = [{
            "name": _orig_label,
            "tl_name": self._transcription_source.get("timeline_name", "") if getattr(self, '_transcription_source', None) else "",
            "words": copy.deepcopy(words_data)
        }]
        self._current_chapter_idx = 0
        
        # Reset UI Dropdown
        self._title_bar.chapter_dropdown.options_list = [_orig_label]
        self._title_bar.chapter_dropdown.setText(_orig_label)
        self._title_bar.update_dropdown_placement()
        
        if hasattr(self, 'text_canvas'):
            self.show_hidden_start = True
            self.text_canvas.finalize_streaming(words_data)
            self._show_transcript_view()

        if words_data and words_data[0].get("meta_audio_path") and hasattr(self, 'waveform_timeline') and self.waveform_timeline:
            tl_name = self._transcription_source.get("timeline_name", "") if getattr(self, '_transcription_source', None) else ""
            track_label = f"A1: {tl_name}" if tl_name else "A1: Timeline Audio"
            self.waveform_timeline.load_from_audio(words_data[0]["meta_audio_path"], track_name=track_label)

    def _on_more_accurate_toggled(self, checked: bool):
        self.engine.save_preferences({"ai_more_accurate": checked})
        if not hasattr(self, 'script_container'):
            return

        if checked:
            self._sync_script_edit_height(animated=False)
            self.script_container.setVisible(True)

        has_btn = hasattr(self, 'btn_import_wrapper')
        if has_btn:
            self.btn_import_wrapper.setMaximumWidth(16777215)
            btn_full_w = self.btn_import_wrapper.sizeHint().width()
            start_btn_w = self.btn_import_wrapper.width() if self.btn_import_wrapper.isVisible() else 0
            end_btn_w = btn_full_w if checked else 0
            if checked:
                self.btn_import_wrapper.setMaximumWidth(start_btn_w)
                self.btn_import_wrapper.setVisible(True)

        if getattr(self, '_script_anim', None) and self._script_anim.state() == QVariantAnimation.Running:
            self._script_anim.stop()

        self._script_anim = QVariantAnimation(self)
        self._script_anim.setDuration(440)
        self._script_anim.setStartValue(0.0)
        self._script_anim.setEndValue(1.0)
        self._script_anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        start_w = self.script_container.width()
        pad = config.S(10)
        end_w = (config.S(16) + config.S(325) + pad) if checked else 0
        w_settings = self.settings_container.width()  # the settings card (fixed width)
        
        def _on_step(v):
            cur_script_w = int(start_w + (end_w - start_w) * v)
            self.script_container.setFixedWidth(cur_script_w)
            if hasattr(self, 'slider_widget'):
                self.slider_widget.setFixedWidth(w_settings + cur_script_w)
            if has_btn:
                self.btn_import_wrapper.setMaximumWidth(int(start_btn_w + (end_btn_w - start_btn_w) * v))
                
        def _on_finish():
            self.script_container.setFixedWidth(end_w)
            if hasattr(self, 'slider_widget'):
                self.slider_widget.setFixedWidth(w_settings + end_w)
            if checked:
                self._sync_script_edit_height(animated=False)
            else:
                self.script_container.setVisible(False)
            if has_btn:
                if not checked:
                    self.btn_import_wrapper.setVisible(False)
                self.btn_import_wrapper.setMaximumWidth(16777215)
                
        self._script_anim.valueChanged.connect(_on_step)
        self._script_anim.finished.connect(_on_finish)
        self._script_anim.start()

    def _on_start_analysis(self):
        # ── Language validation ─────────────────────────────────────────────────
        raw_lang_txt = self._combo_lang.text() if hasattr(self, '_combo_lang') else ''
        _lang_is_valid = raw_lang_txt.strip() and raw_lang_txt in set(config.SUPPORTED_LANGUAGES.values())

        if not _lang_is_valid:
            # Flash red border on the language dropdown
            if hasattr(self, '_combo_lang'):
                _err_ss = (
                    f"QPushButton {{"
                    f" background-color: #1e1e1e;"
                    f" color: #d4d4d4;"
                    f" text-align: left;"
                    f" padding: 0px {config.S(8)}px;"
                    f" border: 1px solid #ed4245;"
                    f" border-radius: {config.S(3)}px;"
                    f" min-height: {config.S(20)}px;"
                    f" max-height: {config.S(30)}px;"
                    f" height: {config.S(30)}px;"
                    f" font-family: '{config.UI_FONT_NAME}', sans-serif;"
                    f" font-size: {config.FS(9.5)}pt;"
                    f"}}"
                    f"QPushButton:hover {{ border-color: #ed4245; }}"
                )
                self._combo_lang.setStyleSheet(_err_ss)
                
                # Add a little shake animation
                from PySide6.QtCore import QPropertyAnimation as _QPA, QPoint as _QP
                if not hasattr(self._combo_lang, '_orig_pos') or self._combo_lang._orig_pos is None:
                    self._combo_lang._orig_pos = self._combo_lang.pos()
                pos = self._combo_lang._orig_pos
                delta = config.S(6)
                anim = _QPA(self._combo_lang, b"pos", self)
                anim.setDuration(300)
                anim.setKeyValueAt(0, pos)
                anim.setKeyValueAt(0.2, pos + _QP(delta, 0))
                anim.setKeyValueAt(0.4, pos - _QP(delta, 0))
                anim.setKeyValueAt(0.6, pos + _QP(delta, 0))
                anim.setKeyValueAt(0.8, pos - _QP(delta, 0))
                anim.setKeyValueAt(1, pos)
                def _on_lang_shake_done():
                    if hasattr(self._combo_lang, '_orig_pos') and self._combo_lang._orig_pos is not None:
                        self._combo_lang.move(self._combo_lang._orig_pos)
                        self._combo_lang._orig_pos = None
                anim.finished.connect(_on_lang_shake_done)
                anim.start()
                self._lang_shake_anim = anim # keep ref
                
                from PySide6.QtCore import QTimer as _QT
                _QT.singleShot(1250, lambda: self._combo_lang._update_text_alignment(self._combo_lang.text()))
            return  # Do NOT start analysis

        # ── Script / Scenario validation ────────────────────────────────────────
        _script_is_required = hasattr(self, 'tgl_more_accurate') and self.tgl_more_accurate.isChecked()
        _script_text = self.welcome_script_edit.toPlainText().strip() if hasattr(self, 'welcome_script_edit') else ''
        if _script_is_required and not _script_text:
            if hasattr(self, 'welcome_script_edit'):
                _orig_script_ss = f'''
                    QTextEdit {{
                        background-color: #1e1e1e; color: #d4d4d4; 
                        border: 1px solid #3a3a3a; border-radius: 3px; 
                        padding: 4px; outline: none; font-family: {config.UI_FONT_NAME};
                    }}
                    QTextEdit:focus {{ border: 1px solid #1a7a3e; }}
                '''
                _err_script_ss = f'''
                    QTextEdit {{
                        background-color: #1e1e1e; color: #d4d4d4; 
                        border: 1px solid #ed4245; border-radius: 3px; 
                        padding: 4px; outline: none; font-family: {config.UI_FONT_NAME};
                    }}
                    QTextEdit:focus {{ border: 1px solid #ed4245; }}
                '''
                self.welcome_script_edit.setStyleSheet(_err_script_ss)
                
                target_widget = self.script_content_widget if hasattr(self, 'script_content_widget') else self.welcome_script_edit
                parent_widget = self.script_container if hasattr(self, 'script_container') else self
                
                from PySide6.QtCore import QPropertyAnimation as _QPA, QPoint as _QP
                if not hasattr(target_widget, '_orig_pos') or target_widget._orig_pos is None:
                    target_widget._orig_pos = target_widget.pos()
                pos = target_widget._orig_pos
                delta = config.S(6)
                anim = _QPA(target_widget, b"pos", parent_widget)
                anim.setDuration(300)
                anim.setKeyValueAt(0, pos)
                anim.setKeyValueAt(0.2, pos + _QP(delta, 0))
                anim.setKeyValueAt(0.4, pos - _QP(delta, 0))
                anim.setKeyValueAt(0.6, pos + _QP(delta, 0))
                anim.setKeyValueAt(0.8, pos - _QP(delta, 0))
                anim.setKeyValueAt(1, pos)
                def _on_script_shake_done():
                    if hasattr(target_widget, '_orig_pos') and target_widget._orig_pos is not None:
                        target_widget.move(target_widget._orig_pos)
                        target_widget._orig_pos = None
                anim.finished.connect(_on_script_shake_done)
                anim.start()
                self._script_shake_anim = anim # keep ref
                
                from PySide6.QtCore import QTimer as _QT
                _QT.singleShot(1250, lambda: self.welcome_script_edit.setStyleSheet(_orig_script_ss))
            return  # Do NOT start analysis

        # ── Source validation ─────────────────────────────────────────────────
        is_file_source = getattr(self, 'current_source_type', 'resolve') == 'file'
        source_file_path = None
        if is_file_source:
            if hasattr(self, 'drop_zone_0'):
                source_file_path = self.drop_zone_0.get_file()
            if not source_file_path or not os.path.isfile(source_file_path):
                if hasattr(self, 'drop_zone_0'):
                    self.drop_zone_0.shake()
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_file_not_selected"), self.txt("btn_ok"))
                dlg.exec()
                return
            from gui.widgets.file_drop_zone import FileDropZone
            if not FileDropZone.is_supported_file(source_file_path):
                if hasattr(self, 'drop_zone_0'):
                    self.drop_zone_0.shake()
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_unsupported_file_format"), self.txt("btn_ok"))
                dlg.exec()
                return
        else:
            rh = getattr(self.engine, 'resolve_handler', None)
            if not rh or not rh.is_connected():
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_resolve_not_connected"), self.txt("btn_ok"))
                dlg.exec()
                return
            selected_tl = getattr(self, 'combo_tl_0', None)
            selected_tl_name = selected_tl.text() if selected_tl else ""
            no_tl = self.txt("msg_no_timelines_detected")
            select_txt = self.txt("txt_select", "Wybierz...")
            valid_tls = getattr(selected_tl, 'options_list', []) if selected_tl else []
            if not selected_tl_name or selected_tl_name in (no_tl, select_txt, "Select...") or (valid_tls and selected_tl_name not in valid_tls):
                dlg = CustomMsgBox(self, config.APP_NAME, self.txt("msg_no_timelines_detected"), self.txt("btn_ok"))
                dlg.exec()
                return
            # Transcribed before: open that instead, unless the user really wants a new transcription
            self._refresh_saved_transcript_offer(selected_tl_name)
            if getattr(self, '_saved_transcript_path', None):
                from handlers import timeline_store
                from PySide6.QtWidgets import QDialog
                when = timeline_store.when_text(os.path.getmtime(self._saved_transcript_path))
                choice = WorkspaceWarningOverlay(
                    self._stack, self.txt("msg_saved_exists_title"),
                    self.txt("msg_saved_exists_desc").format(timeline=selected_tl_name, when=when),
                    self.txt("btn_open_saved_short"), btn_reject_text=self.txt("btn_transcribe_again"),
                    btn_cancel_text=self.txt("btn_cancel")).exec()
                if choice == QDialog.Accepted:
                    self._open_saved_transcript()
                    return
                if choice != QDialog.Rejected:
                    return

        # 1. Hide side panels (saving pre-analysis state)
        self._pre_analysis_panels_state = (
            getattr(self, '_panel_left', None) is not None and self._panel_left.isVisible(),
            getattr(self, '_panel_right', None) is not None and self._panel_right.isVisible()
        )
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()
        
        # Un-toggle the sidebar buttons so they don't look active
        if hasattr(self, 'btn_nav_script'): self.btn_nav_script.set_active(False)
        if hasattr(self, 'btn_nav_main'): self.btn_nav_main.set_active(False)

        # 2. Switch stack to index 1 (Processing page with full-screen progress bar and hints)
        self.go_to_page(1)
        
        # Reset progress bar UI
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(-1)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("status_whisper_init", "Inicjalizowanie transkrypcji..."))

        # ── First-run hint: check if chosen model has been run before ────────────
        raw_model_for_check = self._combo_model.text() if hasattr(self, '_combo_model') else 'Medium'
        model_key = raw_model_for_check.split()[0].lower()
        if "Turbo" in raw_model_for_check: model_key = 'large-v3-turbo'
        if model_key == 'large': model_key = 'large-v3'

        # Check for marker file (MLX engine keeps its own model folder; Auto/GPU use it on Apple Silicon)
        _dev = (self.engine.load_preferences() or {}).get('device', 'auto').upper()
        _use_mlx = self.engine.use_mlx_for("GPU" if _dev in ("AUTO", "GPU") else "CPU")
        model_folder_name = self.engine.model_cache_folder(model_key, _use_mlx)
        marker_path = os.path.join(self.engine.models_dir, model_folder_name, ".badwords_initialized")
        _is_first_model_run = not os.path.exists(marker_path)

        # Stop any existing hint timer / animations
        if hasattr(self, '_hint_timer') and self._hint_timer is not None:
            self._hint_timer.stop()
            self._hint_timer = None
        for _aref in ('_hint_anim_out', '_hint_anim_in'):
            _a = getattr(self, _aref, None)
            if _a is not None:
                try: _a.stop()
                except Exception: pass
            setattr(self, _aref, None)

        if hasattr(self, 'lbl_first_run_hint'):
            import random as _random
            if _is_first_model_run:
                _hint_keys = [
                    'first_run_hint_1', 'first_run_hint_2', 'first_run_hint_3',
                    'first_run_hint_4', 'first_run_hint_5', 'first_run_hint_6',
                    'first_run_hint_7', 'first_run_hint_8', 'first_run_hint_9',
                    'first_run_hint_10',
                ]
            else:
                _hint_keys = [
                    'analysis_hint_1', 'analysis_hint_2', 'analysis_hint_3',
                    'analysis_hint_4', 'analysis_hint_5', 'analysis_hint_6',
                    'analysis_hint_7', 'analysis_hint_8', 'analysis_hint_9',
                    'analysis_hint_10',
                ]

            _shuffled = _hint_keys[:]
            _random.shuffle(_shuffled)
            self._hint_cycle_idx = 0
            self._hint_cycle_keys = _shuffled

            def _fade_to_next_hint():
                if not hasattr(self, 'lbl_first_run_hint'): return
                if not hasattr(self, '_hint_opacity'): return

                def _do_swap():
                    try:
                        key = self._hint_cycle_keys[
                            self._hint_cycle_idx % len(self._hint_cycle_keys)
                        ]
                        self.lbl_first_run_hint.setText(self.txt(key))
                        self._hint_cycle_idx += 1
                    except Exception: pass
                    # Fade in
                    anim_in = QPropertyAnimation(self._hint_opacity, b"opacity")
                    anim_in.setDuration(600)
                    anim_in.setStartValue(0.0)
                    anim_in.setEndValue(1.0)
                    anim_in.setEasingCurve(QEasingCurve.OutQuad)
                    anim_in.start()
                    self._hint_anim_in = anim_in

                anim_out = QPropertyAnimation(self._hint_opacity, b"opacity")
                anim_out.setDuration(500)
                anim_out.setStartValue(1.0)
                anim_out.setEndValue(0.0)
                anim_out.setEasingCurve(QEasingCurve.InQuad)
                anim_out.finished.connect(_do_swap)
                anim_out.start()
                self._hint_anim_out = anim_out

            # Show first hint immediately
            first_key = _shuffled[0]
            self.lbl_first_run_hint.setText(self.txt(first_key))
            self._hint_cycle_idx = 1
            self.lbl_first_run_hint.show()
            anim_first_in = QPropertyAnimation(self._hint_opacity, b"opacity")
            anim_first_in.setDuration(700)
            anim_first_in.setStartValue(0.0)
            anim_first_in.setEndValue(1.0)
            anim_first_in.setEasingCurve(QEasingCurve.OutQuad)
            anim_first_in.start()
            self._hint_anim_in = anim_first_in

            self._hint_timer = QTimer(self)
            self._hint_timer.timeout.connect(_fade_to_next_hint)
            self._hint_timer.start(10500)

        # 3. Gather settings
        raw_lang = self._combo_lang.text() if hasattr(self, '_combo_lang') else 'Auto'
        lang_code = "auto"
        
        if raw_lang != "Auto":
            for code, name in config.SUPPORTED_LANGUAGES.items():
                if name.lower() == raw_lang.lower():
                    lang_code = code
                    break
                    
        raw_model = self._combo_model.text() if hasattr(self, '_combo_model') else 'Medium'
        model = raw_model.split()[0].lower() # Fixes capital letter issue for Whisper

        # Read selected timeline and audio tracks
        selected_tl = getattr(self, 'combo_tl_0', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        no_tl = self.txt("msg_no_timelines_detected")
        if selected_tl_name == no_tl:
            selected_tl_name = ""

        selected_tracks_combo = getattr(self, 'combo_tr_0', None)
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        _current_prefs = self.engine.load_preferences() or {}
        _device_val = _current_prefs.get('device', 'auto').upper()
        if _device_val == 'AUTO': _device_val = 'Auto'
        
        settings = {
            "lang": lang_code,
            "model": model,
            "device": _device_val,
            "filler_words": config.DEFAULT_BAD_WORDS,
            "timeline_name": selected_tl_name or None,
            "track_indices": track_indices or None,
            "expected_script": self.text_script.toPlainText(),
            "source_file": source_file_path,
            "transcript_source": _current_prefs.get('transcript_source', 'whisper'),
            "resolve_speakers": True,
        }

        # 4. Start QThread targeting self.engine.run_analysis_pipeline()
        import time
        self._transcription_start_time = time.time()
        self._analysis_worker = AnalysisWorker(self.engine, 'run_analysis_pipeline', settings)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.status.connect(self._on_analysis_status)
        self._analysis_worker.chunk_ready.connect(self._on_analysis_chunk_ready)
        self._analysis_worker.finished_ok.connect(self._on_analysis_finished)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.start()

    def _set_live_transcription_lock(self, locked: bool):
        """Locks all actions that require a complete transcript while keeping marking mode and options functional."""
        self._is_live_transcribing = locked

        # 1. Assemble Button (with custom locked text when locked, and smooth fade-in unlock)
        if locked:
            self._set_send_enabled(False, self.txt("status_transcribing"))
        else:
            self._set_send_enabled(True)

        # 2. Titlebar Menus: Export/Import Project and Chapters locked; Export txt / copy kept enabled
        if hasattr(self, '_title_bar') and self._title_bar:
            if hasattr(self._title_bar, 'btn_menu_project'):
                self._title_bar.btn_menu_project.setEnabled(not locked)
            if hasattr(self._title_bar, 'btn_menu_edit'):
                self._title_bar.btn_menu_edit.setEnabled(not locked)

        # 3. Left Script Panel: Re-analysis, import, and clearing locked during stream
        if hasattr(self, 'btn_analyze_standalone'):
            self.btn_analyze_standalone.setEnabled(not locked)
        if hasattr(self, 'btn_analyze_compare'):
            if locked:
                self.btn_analyze_compare.setEnabled(False)
            else:
                has_text = bool(getattr(self, 'text_script', None) and self.text_script.toPlainText().strip())
                self.btn_analyze_compare.setEnabled(has_text)
        if hasattr(self, 'btn_side_by_side_compare'):
            if locked:
                self.btn_side_by_side_compare.setEnabled(False)
            else:
                has_text = bool(getattr(self, 'text_script', None) and self.text_script.toPlainText().strip())
                self.btn_side_by_side_compare.setEnabled(has_text)
        if hasattr(self, 'btn_import_script'):
            self.btn_import_script.setEnabled(not locked)
        if hasattr(self, 'btn_clear_script'):
            self.btn_clear_script.setEnabled(not locked)
        if hasattr(self, 'btn_clear_transcript'):
            self.btn_clear_transcript.setEnabled(not locked)
        if hasattr(self, 'text_script'):
            self.text_script.setReadOnly(locked)

    def _prepare_editor_for_live_transcription(self, pct=0):
        # Switch to Page 2 (Editor View) immediately when initialization completes!
        if self._stack.currentIndex() != 2:
            # Stop hint rotation on Page 1
            if hasattr(self, '_hint_timer') and self._hint_timer is not None:
                try: self._hint_timer.stop()
                except Exception: pass
                self._hint_timer = None
            for _aref in ('_hint_anim_out', '_hint_anim_in'):
                _a = getattr(self, _aref, None)
                if _a is not None:
                    try: _a.stop()
                    except Exception: pass
                setattr(self, _aref, None)
            if hasattr(self, 'lbl_first_run_hint'):
                self.lbl_first_run_hint.hide()
                if hasattr(self, '_hint_opacity'):
                    self._hint_opacity.setOpacity(0.0)

            # Switch stack to index 2 (Editor page)
            self.go_to_page(2)

            # Prepare canvas for streaming tokens
            if hasattr(self, 'text_canvas'):
                self.text_canvas.prepare_for_streaming()

            # Open left scenario panel and right main panel
            if not (hasattr(self, '_panel_left') and self._panel_left.isVisible()):
                self._toggle_activity("script_analysis")
            if not (hasattr(self, '_panel_right') and self._panel_right.isVisible()):
                self._toggle_activity("main_panel")

            # Activate transcription mode on title bar
            selected_tl = getattr(self, 'combo_tl_0', None)
            selected_tl_name = selected_tl.text() if selected_tl else ""
            selected_tracks_combo = getattr(self, 'combo_tr_0', None)
            if not selected_tracks_combo:
                tracks_str = self.txt("txt_all")
            else:
                tracks = list(selected_tracks_combo.selected_items)
                if not tracks or (len(tracks) == len(selected_tracks_combo.options_list)):
                    tracks_str = self.txt("txt_all")
                else:
                    tracks_str = ", ".join(sorted(tracks))
            self._title_bar.activate_transcription_mode()
            self._title_bar.set_source_info(selected_tl_name, tracks_str)

            # Lock actions requiring complete transcript during live streaming
            self._set_live_transcription_lock(True)

            # Ensure timeline preview ribbon is visible and loaded from the start
            active_wav = getattr(self.engine, 'current_analysis_audio_path', None) or getattr(self.engine, 'last_audio_path', None)
            if active_wav and os.path.exists(active_wav):
                if hasattr(self, 'audio_preview') and self.audio_preview:
                    self.audio_preview.show()
                    self.audio_preview.content_widget.show()
                    self.audio_preview.controls_widget.show()
                    self.audio_preview.slider_seek.show()
                    self.audio_preview._apply_modularity_state()
                    if hasattr(self.audio_preview, 'waveform_timeline'):
                        self.audio_preview.waveform_timeline.load_from_audio(
                            active_wav,
                            clip_name=f"A1: {selected_tl_name or 'Timeline Audio'}"
                        )

            # Launch Top Dynamic Island with initial status
            if hasattr(self, 'top_island'):
                self.top_island.show_progress(self.txt("status_transcribing", "Transkrybowanie..."), percent=pct)

    def _on_analysis_chunk_ready(self, chunk_info):
        pct = chunk_info.get("percent", -1)
        words = chunk_info.get("words", [])
        chunk_audio = chunk_info.get("audio_path")

        if pct >= 0 and self._stack.currentIndex() == 1:
            self._update_processing_progress(pct)

        # Ensure editor view is active only when actual words arrive
        if words and self._stack.currentIndex() != 2:
            self._prepare_editor_for_live_transcription(pct=pct)

        # Update top island percent
        if hasattr(self, 'top_island'):
            self.top_island.update_percent(pct)

        # Update words without scrolling viewport
        if hasattr(self, 'text_canvas') and words:
            self.text_canvas.load_streamed_words(words)

        # Update waveform timeline live as chunks arrive!
        wf_tl = getattr(self, 'waveform_timeline', None)
        if not wf_tl and hasattr(self, 'audio_preview') and hasattr(self.audio_preview, 'waveform_timeline'):
            wf_tl = self.audio_preview.waveform_timeline
        if wf_tl:
            if chunk_audio and not getattr(wf_tl, '_audio_path', None):
                wf_tl.load_from_audio(chunk_audio)
            if words:
                wf_tl.set_words_data(words)

    def _on_analysis_progress(self, val):
        self._update_processing_progress(val)
        if hasattr(self, 'top_island') and getattr(self.top_island, '_state', '') == 'working':
            self.top_island.update_percent(val)

    def _on_analysis_status(self, msg):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(msg)
        if hasattr(self, 'top_island') and getattr(self.top_island, '_state', '') == 'working':
            self.top_island.set_status(msg)

    def _on_analysis_error(self, err):
        # Stop hint rotation on Page 1
        if hasattr(self, '_hint_timer') and self._hint_timer is not None:
            try: self._hint_timer.stop()
            except Exception: pass
            self._hint_timer = None
        for _aref in ('_hint_anim_out', '_hint_anim_in'):
            _a = getattr(self, _aref, None)
            if _a is not None:
                try: _a.stop()
                except Exception: pass
            setattr(self, _aref, None)
        if hasattr(self, 'lbl_first_run_hint'):
            self.lbl_first_run_hint.hide()

        if hasattr(self, 'top_island'):
            self.top_island.set_error(str(err))
        self._set_live_transcription_lock(False)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(f"Error: {err}")

        from osdoc import log_error
        from gui.dialogs.msgbox import CustomMsgBox
        log_error(f"_on_analysis_error: {err}")

        # Restore Page 0 on error
        self.go_to_page(0)
        if hasattr(self, '_pre_analysis_panels_state'):
            l_vis, r_vis = self._pre_analysis_panels_state
            if hasattr(self, '_panel_left') and l_vis: self._panel_left.show()
            if hasattr(self, '_panel_right') and r_vis: self._panel_right.show()

        dlg = CustomMsgBox(self, self.txt("msg_analysis_failed", "Błąd analizy"), str(err), self.txt("btn_ok", "OK"))
        dlg.exec()

    def _on_analysis_finished(self, words_data, segments_data):
        # Keep this timeline's transcript as soon as the editor holds it
        QTimer.singleShot(2000, self._save_timeline_transcript_soon)
        # Stop hint rotation
        if hasattr(self, '_hint_timer') and self._hint_timer is not None:
            try: self._hint_timer.stop()
            except Exception: pass
            self._hint_timer = None
        for _aref in ('_hint_anim_out', '_hint_anim_in'):
            _a = getattr(self, _aref, None)
            if _a is not None:
                try: _a.stop()
                except Exception: pass
            setattr(self, _aref, None)
        if hasattr(self, 'lbl_first_run_hint'):
            self.lbl_first_run_hint.hide()
            if hasattr(self, '_hint_opacity'):
                self._hint_opacity.setOpacity(0.0)

        if not words_data:
            if hasattr(self, 'top_island'):
                self.top_island.set_error(self.txt("msg_analysis_failed"))
            self._set_send_enabled(True)
            dlg = CustomMsgBox(self, self.txt("msg_analysis_failed"), self.txt("msg_the_transcription_process"), self.txt("btn_ok"))
            dlg.exec()
            # Reset UI to Page 0 and restore previous panel state
            self.go_to_page(0)
            if hasattr(self, '_pre_analysis_panels_state'):
                l_vis, r_vis = self._pre_analysis_panels_state
                if hasattr(self, '_panel_left') and l_vis: self._panel_left.show()
                if hasattr(self, '_panel_right') and r_vis: self._panel_right.show()
            return
            
        self._apply_resolve_speakers(words_data)
        self.go_to_page(2)
        QTimer.singleShot(0, self._measure_sounds_soon)  # in case the engine couldn't (no audio then)

        if hasattr(self, 'top_island'):
            self.top_island.set_completed(self.txt("msg_transcription_complete", "Transkrypcja zakończona"))
            
        self._set_live_transcription_lock(False)
        
        if not (hasattr(self, '_panel_left') and self._panel_left.isVisible()):
            self._toggle_activity("script_analysis")
        if not (hasattr(self, '_panel_right') and self._panel_right.isVisible()):
            self._toggle_activity("main_panel")
        
        # Read selected timeline/tracks to format the new title
        selected_tl = getattr(self, 'combo_tl_0', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        selected_tracks_combo = getattr(self, 'combo_tr_0', None)
        
        if not selected_tracks_combo:
            tracks_str = self.txt("txt_all")
        else:
            tracks = list(selected_tracks_combo.selected_items)
            if not tracks or (len(tracks) == len(selected_tracks_combo.options_list)):
                tracks_str = self.txt("txt_all")
            else:
                tracks_str = ", ".join(sorted(tracks))

        # Activate the new title bar mode: [Project▾] [Transcript▾] [Edit▾] + centered source info
        self._title_bar.activate_transcription_mode()
        self._title_bar.set_source_info(selected_tl_name, tracks_str)
        
        # On macOS native title bar: update the OS window title too
        if platform.system() == "Darwin":
            self.setWindowTitle(config.TRANS[self.lang].get("title", config.APP_NAME))
            if hasattr(self, '_mac_action_timeline'):
                self._mac_menu_project.menuAction().setVisible(True)
                self._mac_menu_transcript.menuAction().setVisible(True)
                self._mac_menu_source.menuAction().setVisible(True)
                self._mac_menu_edits.menuAction().setVisible(True)
                self._mac_action_timeline.setText(f"Timeline: {selected_tl_name}")
                self._mac_action_track.setText(f"Track: {tracks_str}")

        # ── CAPTURE SOURCE SNAPSHOT ──────────────────────────────────────────
        # Compute track indices from names (needed for engine assembly)
        all_tracks_available = list(selected_tracks_combo.options_list) if selected_tracks_combo else []
        selected_track_names = list(selected_tracks_combo.selected_items) if selected_tracks_combo else []
        track_indices = self._track_names_to_indices(selected_tl_name, selected_track_names)

        source_files = []
        try:
            if self.resolve_handler:
                source_files = self.resolve_handler.get_timeline_source_files(selected_tl_name, track_indices)
        except Exception:
            pass

        self._transcription_source = {
            "timeline_name":  selected_tl_name,
            "track_names":    selected_track_names,
            "track_indices":  track_indices,
            "all_tracks":     (not selected_track_names) or (len(selected_track_names) >= len(all_tracks_available)),
            "source_files":   source_files,
        }
        # Persist snapshot so it survives project export/import
        try:
            prefs = self.engine.load_preferences() or {}
            prefs["transcription_source"] = self._transcription_source
            self.engine.save_preferences(prefs)
        except Exception as _e:
            from osdoc import log_error as _log_error
            _log_error(f"Could not persist transcription_source: {_e}")

        self._populate_editor(words_data, segments_data)
        
        if hasattr(self, 'w_track_options'):
            self.w_track_options.refresh_tracks()

        if hasattr(self, 'audio_preview'):
            self.audio_preview.check_audio_availability()
        
        # Load pre-calculated SBS cache if it exists (from initial transcript auto-compare)
        if getattr(self.engine, 'sbs_cache', None):
            self._sbs_last_script_hash = self.engine.sbs_cache.get('hash')
            if hasattr(self, 'text_canvas'):
                self.text_canvas.sbs_rows = self.engine.sbs_cache.get('rows', [])
            self.engine.sbs_cache = None
        
        if hasattr(self, '_transcription_start_time'):
            import time
            elapsed = int(time.time() - self._transcription_start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self._last_analysis_time_raw = f"{mins}:{secs:02d}"
            self.lbl_analysis_duration.setText(self.txt("txt_analyzed_in").replace("{time}", self._last_analysis_time_raw))
            self.lbl_analysis_duration.setVisible(True)
            if hasattr(self, 'p_main') and self.p_main:
                self.p_main.resizeEvent(None)


    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def _maximize_on_active_screen(self, show: bool = True):
        """
        Move the window to the monitor that currently has the cursor and maximize.
        """
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        w, h = config.S(580), config.S(670)
        if screen is None:
            self.resize(w, h)
            if show:
                if getattr(self, '_is_mac', False):
                    self.showFullScreen()
                else:
                    self.showMaximized()
            return
        sg = screen.availableGeometry()
        if not getattr(self, '_is_mac', False):
            self.setGeometry(sg)
            self.setWindowState(self.windowState() | Qt.WindowMaximized)
        else:
            self.setGeometry(
                sg.x() + (sg.width()  - w) // 2,
                sg.y() + (sg.height() - h) // 2,
                w, h
            )
        if show:
            if getattr(self, '_is_mac', False):
                self.showFullScreen()
            else:
                self.showMaximized()

    # ------------------------------------------------------------------
    # Action handlers (stubs — logic added in later stages)
    # ------------------------------------------------------------------

    def _on_clear_transcript(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return
            
        msg_box = CustomMsgBox(self, self.txt("msg_clear_title"), self.txt("msg_clear_desc"), self.txt("btn_yes"), self.txt("btn_no"))
        if msg_box.exec() == QDialog.Accepted:
            undo_action = {"type": "paint", "changes": {}}
            for w in self.text_canvas.words_data:
                has_inaud = (w.get('is_inaudible') or w.get('type') == 'inaudible')
                needs_suppress = has_inaud and not w.get('overlay_suppressed', False)
                
                if (w.get('status') or w.get('manual_status') or w.get('algo_status') or 
                    w.get('is_auto') or w.get('selected') or needs_suppress):
                    
                    undo_action["changes"][w['id']] = {
                        'status': w.get('status'),
                        'manual_status': w.get('manual_status'),
                        'algo_status': w.get('algo_status'),
                        'is_auto': w.get('is_auto'),
                        'selected': w.get('selected'),
                        'overlay_suppressed': w.get('overlay_suppressed', False)
                    }
                    w['status'] = None
                    w['manual_status'] = None
                    w['algo_status'] = None
                    w['is_auto'] = False
                    w['selected'] = False
                    if has_inaud:
                        w['overlay_suppressed'] = True
                        
                    self._calculate_visual_layer(w)

            if hasattr(self, 'undo_manager') and undo_action["changes"]:
                self.undo_manager.push(undo_action)
                
            self.text_canvas.update()
            if hasattr(self, 'waveform_timeline') and self.waveform_timeline:
                self.waveform_timeline.set_words_data(self.text_canvas.words_data)

    def _on_add_custom_marker(self):
        from PySide6.QtWidgets import QApplication
        dlg = self._get_settings_dialog()
        # Navigate to Custom Markers tab dynamically by matching the translated tab name
        custom_markers_label = dlg.txt("tab_custom_markers")
        for i in range(dlg.category_list.count()):
            if dlg.category_list.item(i).text() == custom_markers_label:
                dlg.stack.setCurrentIndex(i)
                dlg.category_list.setCurrentRow(i)
                break
        dlg.exec()
        
        # WORKAROUND: Restore main window icon after dialog closes
        from PySide6.QtWidgets import QApplication
        QApplication.setWindowIcon(_app_icon())
        self.setWindowIcon(_app_icon())
        self._build_marker_radio_buttons()
        self.text_canvas.update()

    def _build_marker_radio_buttons(self):
        self._ensure_avoid_marker()
        # Clear layout
        while self.markers_layout.count():
            item = self.markers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        def style_rb(rb, color):
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: {color};
                    font-size: 11pt;
                    font-weight: bold;
                    background: transparent;
                    padding: 2px 5px;
                }}
                QRadioButton::indicator {{
                    width: 15px; height: 15px;
                    border-radius: 8px;
                    border: 2px solid #555;
                    background: #1a1a1a;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #555;
                    background: qradialgradient(
                        cx:0.5, cy:0.5, radius:0.5,
                        fx:0.5, fy:0.5,
                        stop:0 {color},
                        stop:0.4 {color},
                        stop:0.5 #1a1a1a,
                        stop:1 #1a1a1a
                    );
                }}
            """)

        self.marker_btn_group = QButtonGroup(self)
        
        rb_red = MarqueeRadioButton(self.txt("rad_red_cut_filler"))
        rb_red.setProperty("status_id", "bad")
        style_rb(rb_red, config.WORD_BAD_BG)
        
        rb_blue = MarqueeRadioButton(self.txt("rad_blue_retake"))
        rb_blue.setProperty("status_id", "repeat")
        style_rb(rb_blue, config.WORD_REPEAT_BG)
        
        rb_green = MarqueeRadioButton(self.txt("rad_green_typo"))
        rb_green.setProperty("status_id", "typo")
        style_rb(rb_green, config.WORD_TYPO_BG)
        
        rb_eraser = MarqueeRadioButton(self.txt("rad_eraser_clear"))
        rb_eraser.setProperty("status_id", "eraser")
        rb_eraser.setStyleSheet("""
            QRadioButton {
                color: #aaaaaa; font-size: 11pt; font-weight: bold;
                background: transparent;
                padding: 2px 5px;
            }
            QRadioButton::indicator {
                width: 15px; height: 15px;
                border-radius: 8px;
                border: 2px solid #555;
                background: #1a1a1a;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #555;
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #aaaaaa,
                    stop:0.4 #aaaaaa,
                    stop:0.5 #1a1a1a,
                    stop:1 #1a1a1a
                );
            }
        """)
        
        for rb in (rb_red, rb_blue, rb_green):
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            self.markers_layout.addWidget(rb)
            self.marker_btn_group.addButton(rb)
            
        custom_markers = self.engine.load_preferences().get('custom_markers', [])
        for cm in custom_markers:
            name, color = cm.get("name", ""), cm.get("color", "")
            if not name: continue
            # Translate the color name for display; keep English key in status_id
            translated_color = self.txt(f"resolve_color_{color.lower()}")
            # Format: TranslatedColor (Name)
            rb = MarqueeRadioButton(f"{translated_color} ({name})")
            rb.setProperty("status_id", f"custom_{color}")
            style_rb(rb, config.RESOLVE_COLORS_HEX.get(color, '#ffffff'))
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            if color.lower() in ["green", "blue"]:
                rb.setEnabled(False)
                rb.setToolTip(self.txt("tooltip_disabled_davinci_colors"))
                style_rb(rb, '#666666')
            self.markers_layout.addWidget(rb)
            self.marker_btn_group.addButton(rb)

        rb_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        self.markers_layout.addWidget(rb_eraser)
        self.marker_btn_group.addButton(rb_eraser)
            
        self.rb_mark_bad       = rb_red
        self.rb_mark_repeat    = rb_blue
        self.rb_mark_typo      = rb_green
        self.rb_mark_inaudible = rb_eraser  # closest available; no dedicated inaudible radio
        rb_red.setChecked(True)
        self._rebuild_mark_strip()

    def _setup_hardcoded_shortcuts(self):
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Export
        self.sc_export = QShortcut(QKeySequence.Save, self, context=Qt.ApplicationShortcut)
        self.sc_export.activated.connect(self._on_export_project)
        
        # Undo
        self.sc_undo = QShortcut(QKeySequence.Undo, self, context=Qt.ApplicationShortcut)
        self.sc_undo.activated.connect(self.undo_manager.undo)
        
        # Redo (OS Default)
        self.sc_redo = QShortcut(QKeySequence.Redo, self, context=Qt.ApplicationShortcut)
        self.sc_redo.activated.connect(self.undo_manager.redo)
        
        # Redo Explicit Overrides (ensures Ctrl+Y natively works on Linux even if OS wants Ctrl+Shift+Z)
        self.sc_redo_y = QShortcut(QKeySequence("Ctrl+Y"), self, context=Qt.ApplicationShortcut)
        self.sc_redo_y.activated.connect(self.undo_manager.redo)
        
        self.sc_redo_shift_z = QShortcut(QKeySequence("Ctrl+Shift+Z"), self, context=Qt.ApplicationShortcut)
        self.sc_redo_shift_z.activated.connect(self.undo_manager.redo)

    def _apply_dynamic_shortcuts(self):
        """
        Build (or rebuilds) all dynamic QShortcuts from the saved preferences.
        Clears previously registered shortcuts first to avoid duplicates.
        'jump_to_word' and 'play_stop' are display-only and not registered.
        """
        from PySide6.QtGui import QShortcut, QKeySequence

        # Remove previously registered dynamic shortcuts
        for sc in getattr(self, '_active_shortcuts', []):
            try:
                sc.setEnabled(False)
                sc.setKey(QKeySequence())
                sc.setParent(None)
                sc.deleteLater()
            except RuntimeError:
                pass
        self._active_shortcuts = []

        prefs = self.engine.load_preferences() or {}
        shortcuts = {**config.DEFAULT_SETTINGS.get('shortcuts', {}), **prefs.get('shortcuts', {})}

        # Keys that are informational only — never register as QShortcut
        DISPLAY_ONLY_KEYS = {'jump_to_word'}

        def _make(seq, slot):
            """Helper: register one QShortcut with ApplicationShortcut context."""
            if not seq or seq in ('', 'Ctrl+RMB'):
                return
            try:
                sc = QShortcut(QKeySequence(seq), self, context=Qt.ApplicationShortcut)
                sc.activated.connect(slot)
                self._active_shortcuts.append(sc)
            except Exception:
                pass

        # search — open search overlay
        _make(shortcuts.get('search', 'Ctrl+F'), self.search_overlay.toggle_search)

        # open_settings — open settings dialog (default: Escape)
        # Note: Escape also closes search; handled by priority in event chain
        _make(shortcuts.get('open_settings', 'Escape'), self._on_settings)
        
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and not getattr(self, '_focus_signal_connected', False):
            def _on_focus_changed(_old_w, _new_w):
                try:
                    self._update_shortcut_enabled_states()
                except (RuntimeError, AttributeError):
                    pass
            app.focusChanged.connect(_on_focus_changed)
            self._focus_signal_connected = True

        def safe_toggle_play():
            if self._is_input_widget():
                return
            if hasattr(self, 'audio_preview') and self.audio_preview.is_preview_active():
                self.audio_preview.toggle_play()

        def safe_skip_backward():
            if self._is_input_widget():
                return
            if hasattr(self, 'audio_preview') and self.audio_preview.is_preview_active():
                self.audio_preview.skip_backward()

        def safe_skip_forward():
            if self._is_input_widget():
                return
            if hasattr(self, 'audio_preview') and self.audio_preview.is_preview_active():
                self.audio_preview.skip_forward()

        _make(shortcuts.get('play_stop', 'Space'), safe_toggle_play)
        _make(shortcuts.get('skip_backward', 'Left'), safe_skip_backward)
        _make(shortcuts.get('skip_forward', 'Right'), safe_skip_forward)

        # Marker shortcuts — click the corresponding radio button
        def _check_rb(rb):
            """Click (check) the given radio button if it exists."""
            def _do():
                if self._is_input_widget():
                    return
                try:
                    rb.setChecked(True)
                except RuntimeError:
                    pass
            return _do

        if hasattr(self, 'rb_mark_bad'):
            _make(shortcuts.get('mark_red', '1'),    _check_rb(self.rb_mark_bad))
        if hasattr(self, 'rb_mark_repeat'):
            _make(shortcuts.get('mark_blue', '2'),   _check_rb(self.rb_mark_repeat))
        if hasattr(self, 'rb_mark_typo'):
            _make(shortcuts.get('mark_green', '3'),  _check_rb(self.rb_mark_typo))
        if hasattr(self, 'rb_mark_inaudible'):
            _make(shortcuts.get('mark_eraser', '4'), _check_rb(self.rb_mark_inaudible))

        # Custom marker shortcuts — each registered key selects the matching radio button
        custom_markers = prefs.get('custom_markers', [])
        for cm in custom_markers:
            name  = cm.get('name', '')
            color = cm.get('color', '')
            if not name:
                continue
            s_key = f'custom_marker_{name}'
            seq   = shortcuts.get(s_key, '')
            if not seq:
                continue
            # Find the radio button with matching status_id
            target_status_id = f'custom_{color}'
            rb_target = None
            if hasattr(self, 'marker_btn_group'):
                for rb in self.marker_btn_group.buttons():
                    try:
                        if rb.property('status_id') == target_status_id \
                                and rb.text().endswith(f'({name})'):
                            rb_target = rb
                            break
                    except RuntimeError:
                        pass
            if rb_target is not None:
                _make(seq, _check_rb(rb_target))

        self._update_shortcut_enabled_states()


    def _on_settings(self):
        """Open settings panel."""
        dlg = self._get_settings_dialog()
        dlg.exec()
        
        # WORKAROUND: Restore main window icon after dialog closes
        from PySide6.QtWidgets import QApplication
        QApplication.setWindowIcon(_app_icon())
        self.setWindowIcon(_app_icon())
        
        self._build_marker_radio_buttons()
        self._apply_dynamic_shortcuts()
        self.text_canvas.update()
        
        # Explicitly reactivate the main window to ensure ApplicationShortcut context binds properly
        self.activateWindow()
        self.setFocus()




    # ------------------------------------------------------------------
    # Page navigation
    # ------------------------------------------------------------------

    def go_to_page(self, index: int):
        """
        Switch the central QStackedWidget to *index*.
        """
        self._stack.setCurrentIndex(index)
        if index == 0:
            QTimer.singleShot(0, self._refresh_saved_transcript_offer)
        if hasattr(self, 'top_island') and getattr(self.top_island, 'isVisible', lambda: False)():
            self.top_island._ensure_z_order()
        if index != 2:
            if hasattr(self, 'audio_preview') and self.audio_preview:
                self.audio_preview.hide()
            if hasattr(self, '_title_bar') and hasattr(self._title_bar, 'deactivate_transcription_mode'):
                self._title_bar.deactivate_transcription_mode()
            if getattr(self, '_is_mac', False):
                if hasattr(self, '_mac_menu_project'):
                    self._mac_menu_project.menuAction().setVisible(False)
                    self._mac_menu_transcript.menuAction().setVisible(False)
                    self._mac_menu_source.menuAction().setVisible(False)
                    self._mac_menu_edits.menuAction().setVisible(False)
        else:
            if hasattr(self, 'audio_preview') and self.audio_preview:
                self.audio_preview.check_audio_availability()
            if hasattr(self, '_title_bar') and hasattr(self._title_bar, 'activate_transcription_mode'):
                if getattr(self, '_transcription_source', None):
                    self._title_bar.activate_transcription_mode()
            if getattr(self, '_is_mac', False):
                if hasattr(self, '_mac_menu_project'):
                    self._mac_menu_project.menuAction().setVisible(True)
                    self._mac_menu_transcript.menuAction().setVisible(True)
                    self._mac_menu_source.menuAction().setVisible(True)
                    self._mac_menu_edits.menuAction().setVisible(True)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def check_telemetry(self):
        """Show TelemetryPopup if consent has never been recorded."""
        opt_in = self.engine.os_doc.get_telemetry_pref("telemetry_opt_in")
        if not getattr(config, "TELEMETRY_ENABLED", True):
            pass  # this fork sends nothing: no prompt, no ping
        elif opt_in is None:
            popup = TelemetryPopup(self.engine, parent=self)
            self.engine.os_doc.force_dark_titlebar(int(popup.winId()))
            popup.exec()  # ApplicationModal — blocks until user responds
        elif opt_in is True:
            self.engine.send_telemetry_ping("app_started")

        # Check if one-time milestone notice for 3.x -> 4.x migration is needed
        self.check_v4_migration_notice()

    def check_v4_migration_notice(self):
        """Show V4MigrationDialog once if upgrading from 3.x to 4.0.0 via legacy updater."""
        try:
            prefs = self.engine.load_preferences() or {}
            if prefs.get("v4_migration_notified", True):
                return

            dirs_to_check = [self.engine.os_doc.install_dir, os.path.dirname(self.engine.os_doc.install_dir)]
            for d in dirs_to_check:
                marker = os.path.join(d, ".v4_migration_notified")
                if os.path.isfile(marker):
                    self.engine.save_preferences({"v4_migration_notified": True})
                    return

            from gui.dialogs.v4_migration_dialog import V4MigrationDialog
            lang = prefs.get("gui_lang", "en")
            dlg = V4MigrationDialog(lang=lang, parent=self)
            dlg.exec()

            # Record that notice was shown and handled
            self.engine.save_preferences({"v4_migration_notified": True})
            for d in dirs_to_check:
                try:
                    with open(os.path.join(d, ".v4_migration_notified"), "w", encoding="utf-8") as f:
                        f.write("1\n")
                except Exception:
                    pass
        except Exception as e:
            from osdoc import log_error
            log_error(f"check_v4_migration_notice failed: {e}")

    def _open_update_dialog(self, latest_ver: str, gh_url: str, gl_url: str):
        """Open UpdateNotifyDialog manually (e.g. from settings version card)."""
        self._show_update_dialog(latest_ver, gh_url, gl_url)

    def _start_update_check(self):
        """Start background update-check thread.

        Always runs so the settings version card can display status.

        Behaviour based on prefs:
          auto_update_on_start=True  → silently download+apply update in background,
                                       then show a one-line restart notice.
                                       (NO os.execv, NO blocking, Resolve API intact)
          auto_check_updates=True    → show UpdateNotifyDialog popup.
          Both can be enabled simultaneously; auto-update fires first, popup is skipped.
        """
        try:
            prefs  = self.engine.load_preferences() or {}
            notify = prefs.get('auto_check_updates', True)
            auto   = prefs.get('auto_update_on_start', False) and __import__("gui.dialogs.update_dialog", fromlist=["x"]).update_install_supported(self.engine.os_doc.install_dir)

            self._update_thread = UpdateCheckThread(config.VERSION, parent=self)

            if auto:
                # Silent auto-update: no popup, no blocking, no os.execv
                self._update_thread.update_available.connect(self._do_silent_auto_update)
            elif notify:
                self._update_thread.update_available.connect(self._show_update_dialog)

            self._update_thread.start()
        except Exception as e:
            from osdoc import log_error
            log_error(f"[UpdateCheck] Failed to start check thread: {e}")

    def _do_silent_auto_update(self, latest_ver: str, gh_url: str, gl_url: str):
        """
        Run update script in a background daemon thread.
        No blocking on main thread → Resolve API connection stays alive.
        No os.execv → process is never replaced.
        On success: show a small non-modal notice asking user to restart.
        On failure: log only (no popup spam).
        """
        import threading, subprocess, tempfile, urllib.request, ssl
        from osdoc import log_info, log_error

        log_info(f"[AutoUpdate] Silent auto-update to {latest_ver} starting in background...")

        is_win = self.engine.os_doc.is_win
        urls   = [UpdateNotifyDialog._UPDATE_SCRIPT, UpdateNotifyDialog._UPDATE_SCRIPT_GL]

        # Signal bridge — safe cross-thread UI callback
        class _Bridge(QObject):
            done = Signal(bool, str)
        _bridge = _Bridge(self)

        def _on_done(success, err):
            if success:
                log_info(f"[AutoUpdate] Update to {latest_ver} applied silently. Restart to load new version.")
                # Store flag — settings card will show "restart to apply" when opened
                self._pending_update_ver = latest_ver
            else:
                log_error(f"[AutoUpdate] Silent update failed: {err}")

        _bridge.done.connect(_on_done)

        def _worker():
            tmp = None
            try:
                import sys, os
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
                content = None
                for url in urls:
                    try:
                        with urllib.request.urlopen(url, timeout=20, context=ctx) as r:
                            content = r.read()
                        break
                    except Exception:
                        continue
                if not content:
                    _bridge.done.emit(False, "Could not download update script.")
                    return
                import sys
                fd, tmp = tempfile.mkstemp(suffix='.py', prefix='bw_autoupd_')
                with os.fdopen(fd, 'wb') as fh:
                    fh.write(content)
                install_dir = getattr(self.engine.os_doc, 'install_dir', '')
                if hasattr(self.engine.os_doc, 'get_venv_python_path'):
                    venv_py = self.engine.os_doc.get_venv_python_path()
                elif is_win:
                    venv_py = os.path.join(install_dir, 'venv', 'Scripts', 'pythonw.exe')
                    if not os.path.isfile(venv_py):
                        venv_py = os.path.join(install_dir, 'venv', 'Scripts', 'python.exe')
                else:
                    venv_py = os.path.join(install_dir, 'venv', 'bin', 'python3')
                    
                if not os.path.isfile(venv_py):
                    venv_py = sys.executable

                cmd = [venv_py, tmp]
                if install_dir:
                    cmd.extend(['--install-dir', install_dir])

                sp_kwargs = self.engine.os_doc.get_subprocess_kwargs() if hasattr(self.engine, 'os_doc') else {}
                if not sp_kwargs and is_win:
                    sp_kwargs['creationflags'] = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= getattr(subprocess, 'STARTF_USESHOWWINDOW', 1)
                    si.wShowWindow = getattr(subprocess, 'SW_HIDE', 0)
                    sp_kwargs['startupinfo'] = si

                result = subprocess.run(
                    cmd, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    encoding='utf-8', errors='replace', timeout=600, **sp_kwargs
                )
                for line in (result.stdout or '').splitlines():
                    log_info(f'[AutoUpdate] {line}')
                _bridge.done.emit(result.returncode == 0,
                                  f"Exit code {result.returncode}" if result.returncode != 0 else "")
            except subprocess.TimeoutExpired:
                _bridge.done.emit(False, "Timeout (>10 min)")
            except Exception as e:
                _bridge.done.emit(False, str(e))
            finally:
                if tmp:
                    try: os.remove(tmp)
                    except Exception: pass

        threading.Thread(target=_worker, daemon=True).start()

    def _show_auto_update_done(self, latest_ver: str):
        """Show a simple non-blocking message: update applied, please restart."""
        try:
            title = self.txt('update_notify_title')
            msg   = self.txt('update_notify_success')
            ok    = self.txt('btn_ok')
            CustomMsgBox(self, title, msg, ok).exec()
        except Exception as e:
            from osdoc import log_error
            log_error(f"[AutoUpdate] Could not show restart notice: {e}")

    def _show_update_dialog(self, latest_ver: str, gh_url: str, gl_url: str):

        """Show the UpdateNotifyDialog on the main (GUI) thread."""
        if not __import__("gui.dialogs.update_dialog", fromlist=["x"]).update_install_supported(self.engine.os_doc.install_dir):
            # StoryCraft: point to the release page; nothing is downloaded or run from here
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            dlg = CustomMsgBox(self, self.txt("update_fork_title"),
                               self.txt("update_fork_desc").format(latest=latest_ver, current=config.VERSION),
                               self.txt("btn_open_download"), self.txt("btn_later"))
            if dlg.exec():
                QDesktopServices.openUrl(QUrl(gh_url))
            return
        try:
            is_win = self.engine.os_doc.is_win
            is_mac = getattr(self.engine.os_doc, 'is_mac', False)
            install_dir = self.engine.os_doc.install_dir
            dlg = UpdateNotifyDialog(
                parent=self,
                lang=self.lang,
                current_ver=config.VERSION,
                latest_ver=latest_ver,
                gh_url=gh_url,
                gl_url=gl_url,
                is_win=is_win,
                is_mac=is_mac,
                install_dir=install_dir,
            )
            self.engine.os_doc.force_dark_titlebar(int(dlg.winId()))
            dlg.exec()
        except Exception as e:
            from osdoc import log_error
            log_error(f"[UpdateCheck] Failed to show update dialog: {e}")

    # ------------------------------------------------------------------
    # Translation helper
    # ------------------------------------------------------------------

    def txt(self, key: str, default: str = None, **kwargs) -> str:
        return _txt(self.lang, key, default=default, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        msg_box = CustomMsgBox(self, self.txt('msg_quit_title'), self.txt('msg_quit_desc'), self.txt('btn_yes'), self.txt('btn_no'))
        if msg_box.exec() == QDialog.Accepted:
            if getattr(self, '_mcp_bridge', None):
                self._mcp_bridge.stop()
                self._mcp_bridge = None
            # Prevent crashes by unhooking global signals during teardown
            try:
                QApplication.instance().focusChanged.disconnect(self._on_app_focus_changed)
            except Exception:
                pass

            if hasattr(self, '_global_app_filter') and self._global_app_filter:
                QApplication.instance().removeEventFilter(self._global_app_filter)
                self._global_app_filter = None

            # Write clean exit flag
            try:
                import os
                flag_path = os.path.join(self.engine.os_doc.get_autosave_dir(), '.clean_exit')
                with open(flag_path, 'w') as f:
                    f.write('ok')
            except Exception:
                pass
                
            event.accept()
            if self.closeEvent_callback:
                self.closeEvent_callback()
        else:
            event.ignore()
