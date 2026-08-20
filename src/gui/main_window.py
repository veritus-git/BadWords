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

from PySide6 import QtCore
import re
import math
import platform
import subprocess
import os
import time
import traceback
import ctypes
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QCheckBox,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QAbstractItemView, QFrame, QScrollArea,
    QDockWidget, QToolBar, QStackedWidget, QFormLayout, QComboBox,
    QSpacerItem, QCompleter, QLineEdit, QWidgetAction, QToolTip,
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter, QSplitterHandle,
    QTabWidget, QSpinBox, QButtonGroup, QLayout
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation, Property, QThread
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter, QPen, QFontMetrics, QLinearGradient
)
from PySide6.QtCore import QMimeData

import config

# --- INJECTED WIDGET IMPORTS ---
from gui.widgets.buttons import QPushButton, MarqueeRadioButton, ToggleSwitch, ShortcutCaptureButton, MouseShortcutCaptureButton, AnimatedPlayerButton, AudioToggleTab, SidebarButton, CustomDropdown, TitleDropdown, SpeedDropdown, MultiSelectDropdown, SearchableDropdown, AssembleArrowButton, AssembleSplitButton
from gui.widgets.labels import QLabel, IDETooltip, MarqueeLabel
from gui.widgets.layouts import FlowLayout, MainPanelWidget
from gui.widgets.progress_bar import LiquidProgressBar
from gui.widgets.language_selector import _LangPickerDialog
from gui.widgets.splitters import GripHandle, GripSplitter
from gui.widgets.text_edits import WrappingPlaceholderTextEdit, SBSTextEdit
from gui.widgets.sliders import JumpSlider
# -------------------------------

import osdoc

# ==========================================
# QFRAMELESSWINDOW — NATIVE CSD LIBRARY
# ==========================================
# On Windows, use the battle-tested qframelesswindow library for proper
# Aero Snap, DWM shadows, resize, drag-detach, and snap layouts.
# Linux/macOS keep the existing manual code (it works fine there).
_HAS_QFRAMELESS = False
_BaseMainWindow = QMainWindow
_BaseDialog = QDialog

# ==========================================
# MACOS FONT SCALING MONKEY PATCH
# ==========================================
_orig_set_style_sheet = QWidget.setStyleSheet
def _scaled_set_style_sheet(self, qss):
    import platform, re
    if platform.system() == "Darwin" and qss and isinstance(qss, str):
        # Scale pt to px using 1.333 ratio
        qss = re.sub(r'font-size:\s*([\d\.]+)pt;', lambda m: f"font-size: {int(float(m.group(1)) * 1.333)}px;", qss)
    _orig_set_style_sheet(self, qss)
QWidget.setStyleSheet = _scaled_set_style_sheet

# ==========================================
# CONSTANTS
# ==========================================
RTL_CODES = {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'}  # Right-To-Left Languages


# ==========================================
# HELPERS
# ==========================================

_QPushButton = QPushButton




_QRadioButton = QRadioButton

from .utils import _app_icon, apply_dark_title_bar, _center_on_screen, _txt, _qwidget_txt
from .components.dialogs import SplashScreen, TelemetryPopup, MarkerDragZone, MarkerRowWidget, CustomMsgBox, UpdateNotifyDialog, MarkerDialog, UnsavedChangesDialog, SettingsDialog, GlobalAppFilter, SidebarDragZone, UpdateCheckThread
from .components.audio_preview import AudioPreviewWidget
from .components.transcription_canvas import TranscriptionCanvas
from .components.search_overlay import SearchOverlayWidget
from .components.mixins import FramelessWindowMixin, ResizeGrip, _HAS_QFRAMELESS, _BaseMainWindow, _BaseDialog
from .components.titlebar import CustomTitleBar, AnimatedTitleButton
from .components.track_options_drawer import TrackOptionsDrawer
from .widgets.delegates import MarqueeItemDelegate
from handlers.analysis_worker import AnalysisWorker
from handlers.autosave_manager import AutoSaveManager
from handlers.undo_manager import UndoManager

_QLabel = QLabel







class WorkspaceWarningOverlay(QFrame):
    def __init__(self, parent_stack, title, description, btn_accept_text, btn_reject_text=None, btn_cancel_text=None):
        super().__init__()
        self._stack = parent_stack
        from PySide6.QtCore import QEventLoop, Qt
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
        self._loop = QEventLoop()
        self._result = QDialog.Rejected
        
        import config
        self.setStyleSheet(f"background-color: {config.BG_COLOR};")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        container = QFrame()
        container.setFixedWidth(600)
        c_layout = QVBoxLayout(container)
        c_layout.setSpacing(20)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet("font-size: 14px; color: #cccccc; background: transparent; line-height: 1.5;")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(lbl_desc)
        
        c_layout.addSpacing(10)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        if btn_reject_text:
            btn_reject = QPushButton(btn_reject_text)
            btn_reject.setCursor(Qt.PointingHandCursor)
            btn_reject.setStyleSheet(f"""
                QPushButton {{
                    background-color: #404040;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-size: 13px;
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
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
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
                    padding: 8px 16px;
                    font-size: 13px;
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
        self.resize(config.CFG_WINDOW_W_BASE, config.CFG_WINDOW_H_BASE)
        self.setMinimumSize(config.CFG_WINDOW_W_BASE, 400)
        # NOTE: force_dark_titlebar removed — CSD owns the title bar.

        # --- Global QSS ---
        self.setStyleSheet(f"""
            * {{ outline: none; }}
            QMainWindow {{
                background-color: transparent;
            }}
            QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.FG_COLOR};
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
            }}
            /* ---- Scrollbars (global) ---- */
            QScrollBar:vertical {{
                background: {config.SCROLL_BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {config.SCROLL_FG};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {config.SCROLL_ACTIVE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
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
        self._root_layout.addWidget(self._title_bar)

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
        self._maximize_on_active_screen()

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
                lambda: self._save_single_pref('silence_min_dur',
                    float(self.spin_silence_min_dur.text().replace(',', '.') or 0.2))
            )

        
        # Restore pinned favorites
        for fav_id in prefs.get('favorites', []):
            if fav_id in self._pin_buttons:
                self._pin_buttons[fav_id].setStyleSheet("QPushButton { background: transparent; border: none; color: #eebb00; font-size: 11pt; padding: 0; } QPushButton:hover { color: #ffcc00; }")
                self._pin_buttons[fav_id].click()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._enforce_native_always_on_top()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._enforce_native_always_on_top()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._enforce_native_always_on_top()

    def _enforce_native_always_on_top(self):
        try:
            prefs = self.engine.load_preferences() or {}
            if prefs.get('always_on_top') and hasattr(self, 'engine') and hasattr(self.engine, 'os_doc'):
                self.engine.os_doc.set_always_on_top(int(self.winId()), True)
        except Exception:
            pass

    def _apply_always_on_top(self, enable: bool):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
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
        self._sidebar_left = QFrame(self)
        self._sidebar_left.setFixedWidth(50)
        self._sidebar_left.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        left_layout = QVBoxLayout(self._sidebar_left)
        left_layout.setContentsMargins(5, 6, 5, 6)
        left_layout.setSpacing(6)
        
        self._drag_zone_left = SidebarDragZone(self._sidebar_left)
        drag_layout_left = self._drag_zone_left.layout()
        left_layout.addWidget(self._drag_zone_left)
        
        self.btn_nav_script = SidebarButton("\U0001f4dd", self.txt("tool_script_analysis"), "script_analysis", tooltip_widget=self.shared_tooltip)
        self.btn_nav_script.clicked.connect(lambda: self._toggle_activity("script_analysis"))
        drag_layout_left.addWidget(self.btn_nav_script)
        
        self.btn_nav_silence = SidebarButton("\U0001f507", self.txt("tool_silence"), "silence", tooltip_widget=self.shared_tooltip)
        self.btn_nav_silence.clicked.connect(lambda: self._toggle_activity("silence"))
        drag_layout_left.addWidget(self.btn_nav_silence)

        self.btn_nav_fillers = SidebarButton("\U0001f4ac", self.txt("tool_filler_words"), "fillers", tooltip_widget=self.shared_tooltip)
        self.btn_nav_fillers.clicked.connect(lambda: self._toggle_activity("fillers"))
        drag_layout_left.addWidget(self.btn_nav_fillers)
        
        self.btn_nav_settings = SidebarButton("\u2699", self.txt("tool_settings"), "settings", tooltip_widget=self.shared_tooltip, is_draggable=False)
        self.btn_nav_settings.clicked.connect(lambda: self._on_settings())
        left_layout.addWidget(self.btn_nav_settings)
        
        self._sidebar_left.show()

        self._sidebar_right = QFrame(self)
        self._sidebar_right.setFixedWidth(50)
        self._sidebar_right.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        right_layout = QVBoxLayout(self._sidebar_right)
        right_layout.setContentsMargins(5, 6, 5, 6)
        right_layout.setSpacing(6)
        
        self._drag_zone_right = SidebarDragZone(self._sidebar_right)
        drag_layout_right = self._drag_zone_right.layout()
        right_layout.addWidget(self._drag_zone_right)
        
        self.btn_nav_main = SidebarButton("\U0001f6e0\ufe0f", self.txt("tool_main_panel"), "main_panel", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_main.clicked.connect(lambda: self._toggle_activity("main_panel"))
        drag_layout_right.addWidget(self.btn_nav_main)
        
        self.btn_nav_assembly = SidebarButton("\u2699\ufe0f", self.txt("tool_assembly"), "assembly", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_assembly.clicked.connect(lambda: self._toggle_activity("assembly"))
        drag_layout_right.addWidget(self.btn_nav_assembly)

        self._restore_sidebar_layout()
        
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1000, self._check_crash_recovery)

        
    def _check_crash_recovery(self):
        import os, json
        from PySide6.QtWidgets import QDialog
        
        flag_path = os.path.join(self.engine.os_doc.get_autosave_dir(), '.clean_exit')
        meta_path = os.path.join(self.engine.os_doc.get_autosave_dir(), 'recovery_meta.json')
        save_path = os.path.join(self.engine.os_doc.get_autosave_dir(), 'recovery.bws')
        
        crashed = False
        if not os.path.exists(flag_path) and os.path.exists(meta_path) and os.path.exists(save_path):
            crashed = True
            
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
        self._panel_left = QFrame()
        self._panel_left.setMinimumWidth(150)
        self._panel_left.setObjectName("leftPanel")
        self._panel_left.setStyleSheet(f"QFrame#leftPanel {{ background-color: {config.BG_COLOR}; }} QFrame#ActivityPanel {{ background-color: #212121; border-radius: 6px; }}")
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
        self._panel_right.setMinimumWidth(150)
        self._panel_right.setObjectName("rightPanel")
        self._panel_right.setStyleSheet(f"QFrame#rightPanel {{ background-color: {config.BG_COLOR}; }} QFrame#ActivityPanel {{ background-color: #212121; border-radius: 6px; }}")
        QVBoxLayout(self._panel_right).setContentsMargins(0, 0, 0, 0)
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

        self._main_h_splitter.setHandleWidth(6)
        self._main_h_splitter.setStyleSheet("QSplitter { border: none; background: transparent; }")

        # Add everything to main layout in exact order
        main_layout.addWidget(self._sidebar_left)
        main_layout.addWidget(self._main_h_splitter)
        main_layout.addWidget(self._sidebar_right)

        # ── CSD: add content area under the title bar in the root frame ───────
        self._root_layout.addWidget(main_container)
        self.setCentralWidget(self._root_frame)


    def _toggle_activity(self, activity_id: str):
        target_btn = None
        target_splitter = None
        
        for widget in self.findChildren(SidebarButton):
            if widget.activity_id == activity_id:
                target_btn = widget
                target_splitter = self._panel_right if widget.is_right_side else self._panel_left
                break
                    
        if not target_btn or not target_splitter:
            return  # Activity button not found in sidebars

        assert target_btn is not None
        assert target_splitter is not None

        activity_widget = self.activities[activity_id]
        sidebar = self._sidebar_left if not target_btn.is_right_side else self._sidebar_right
        
        is_already_active = target_btn.is_active
        
        if is_already_active:
            target_splitter.hide()
            target_btn.set_active(False)
        else:
            for widget in self.findChildren(SidebarButton):
                if widget.is_right_side == target_btn.is_right_side:
                    widget.set_active(False)
                    
            target_btn.set_active(True)
            layout = target_splitter.layout()
            
            # Clear existing items safely
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    
            layout.addWidget(activity_widget)
            activity_widget.show()
            
            was_hidden = not target_splitter.isVisible()
            target_splitter.show()
            if was_hidden:
                sizes = self._main_h_splitter.sizes()
                # 14.58% perfectly matches 280px on a 1920px display
                target_w = max(180, min(300, int(self.width() * (280.0 / 1920.0))))
                if target_splitter == self._panel_left:
                    diff = target_w - sizes[0]
                    sizes[0] = target_w
                    sizes[1] = max(0, sizes[1] - diff)
                elif target_splitter == self._panel_right:
                    diff = target_w - sizes[2]
                    sizes[2] = target_w
                    sizes[1] = max(0, sizes[1] - diff)
                self._main_h_splitter.setSizes(sizes)

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
        for dz in [self._drag_zone_left, self._drag_zone_right]:
            layout = dz.layout()
            for i in reversed(range(layout.count())):
                w = layout.itemAt(i).widget()
                if isinstance(w, SidebarButton):
                    btns_map[w.activity_id] = w
                    layout.removeWidget(w)

        # Odtwórz poprawną kolejność dla lewej strony
        for act_id in left_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = False
                self._drag_zone_left.layout().addWidget(btn)

        # Odtwórz poprawną kolejność dla prawej strony
        for act_id in right_saved:
            if act_id in btns_map:
                btn = btns_map.pop(act_id)
                btn.is_right_side = True
                self._drag_zone_right.layout().addWidget(btn)

        # Resztki (nowe funkcje) lądują domyślnie na lewo
        for btn in btns_map.values():
            btn.is_right_side = False
            self._drag_zone_left.layout().addWidget(btn)

    def _build_activities(self):
        from gui.panels import (
            build_script_panel, build_silence_panel, build_fillers_panel,
            build_main_workspace_panel, build_assembly_panel
        )
        self._favorite_proxies = {}
        self._pin_buttons = {}

        self.activities["script_analysis"] = build_script_panel(self)
        self.activities["silence"] = build_silence_panel(self)
        self.activities["fillers"] = build_fillers_panel(self)
        self.activities["main_panel"] = build_main_workspace_panel(self)
        self.activities["assembly"] = build_assembly_panel(self)

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
        from PySide6.QtCore import QEvent, Qt
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
        if not self.engine.resolve_handler or not getattr(self.engine.resolve_handler, 'project', None): return
        
        tl_name = None
        if getattr(self, '_current_chapter_idx', -1) >= 0 and self._chapters:
            tl_name = self._chapters[self._current_chapter_idx].get("tl_name")
        elif getattr(self, '_transcription_source', None):
            tl_name = self._transcription_source.get("timeline_name")
            
        if tl_name:
            curr_tl = self.engine.resolve_handler.project.GetCurrentTimeline()
            if curr_tl and curr_tl.GetName() == tl_name:
                self.engine.resolve_handler.timeline = curr_tl
            else:
                count = self.engine.resolve_handler.project.GetTimelineCount()
                for i in range(1, count + 1):
                    tl = self.engine.resolve_handler.project.GetTimelineByIndex(i)
                    if tl and tl.GetName() == tl_name:
                        self.engine.resolve_handler.project.SetCurrentTimeline(tl)
                        self.engine.resolve_handler.timeline = tl
                        break
        
        self.engine.resolve_handler.jump_to_seconds(timestamp_s)

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

        # Restore left panel
        if getattr(self, '_sbs_left_was_visible', False):
            self._panel_left.show()
            if hasattr(self, '_sbs_left_sizes'):
                self._main_h_splitter.setSizes(self._sbs_left_sizes)

    def _on_cut_now_clicked(self, color_name):
        from gui import CustomMsgBox
        
        # Always fetch the currently active timeline from DaVinci before cutting
        rh = getattr(self.engine, 'resolve_handler', None)
        if rh and rh.project:
            current_tl = rh.project.GetCurrentTimeline()
            if current_tl:
                rh.timeline = current_tl
                
        localized_color_name = self.txt(f"resolve_color_{color_name.lower()}")
        title = self.txt("msg_cut_color_title").format(color=localized_color_name)
        desc = self.txt("msg_cut_color_desc")
        
        box = CustomMsgBox(self, title, desc, self.txt("btn_cut_new_timeline"), self.txt("btn_cut_current_timeline"), self.txt("btn_cancel"))
        ret = box.exec()
        if ret == 2: return
        new_timeline = (ret == 1)
        self.engine.api_delete_clips_by_color(color_name, new_timeline)

    def _on_analyze_standalone(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            dlg = CustomMsgBox(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"), self.txt("btn_ok"))
            dlg.exec()
            return
            
        prefs = self.engine.load_preferences() or {}
        show_inaudible = prefs.get('show_inaudible', True)
        
        # Standalone analysis returns a tuple: (processed_words, count)
        updated_words, _ = self.engine.run_standalone_analysis(self.text_canvas.words_data, show_inaudible)
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
        self.text_canvas.load_data(copy.deepcopy(ch.get("words", [])))
        
        # Sync DaVinci
        prefs = self.engine.load_preferences() or {}
        if prefs.get("sync_davinci_chapter", True):
            tl_name = ch.get("tl_name")
            if tl_name and self.resolve_handler and getattr(self.resolve_handler, 'project', None):
                try:
                    count = self.resolve_handler.project.GetTimelineCount()
                    for i in range(1, count + 1):
                        tl = self.resolve_handler.project.GetTimelineByIndex(i)
                        if tl and tl.GetName() == tl_name:
                            self.resolve_handler.project.SetCurrentTimeline(tl)
                            break
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
        import time, os
        
        saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
        os.makedirs(saves_dir, exist_ok=True)
        
        # SMART TIMELINE NAMING
        timeline_name = "Project"
        snap = packet.get("transcription_source") or {}
        if snap.get("timeline_name"):
            timeline_name = snap["timeline_name"]
            
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"BadWords_{safe_name}.bws"
        
        path, _ = QFileDialog.getSaveFileName(self, self.txt("btn_export_project"), os.path.join(saves_dir, default_filename), "BadWords Save (*.bws);;JSON Files (*.json)")
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

            self.engine.save_bws(
                path, packet, 
                audio_path=audio_path, 
                drt_path=drt_path, 
                assembly_recipe=recipe, 
                timeline_fingerprint=timeline_fingerprint,
                media_inventory=media_inventory
            )
            
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

        saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
        os.makedirs(saves_dir, exist_ok=True)

        # Build default filename from source info
        timeline_name = "Transcript"
        snap = getattr(self, '_transcription_source', None)
        if snap and snap.get('timeline_name'):
            timeline_name = snap['timeline_name']
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"BadWords_{safe_name}_transcript.txt"

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
            from PySide6.QtWidgets import QFileDialog, QApplication, QDialog
            import os, time
            
            path = override_path
            if not path:
                saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
                os.makedirs(saves_dir, exist_ok=True)
                
                path, _ = QFileDialog.getOpenFileName(
                    self, 
                    self.txt("btn_import_project"), 
                    saves_dir, 
                    "BadWords Save (*.bws);;JSON Files (*.json)"
                )
                
            if not path: return
            
            bws_extras = None
            if path.endswith('.bws'):
                state, _, bws_extras = self.engine.load_bws(path)
            else:
                state, _ = self.engine.load_project_state(path)

            from PySide6.QtCore import QTimer

            from_main_window = False
            if hasattr(self, '_stack') and self._stack.currentIndex() != 2:
                from_main_window = True

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
                
            # (Title bar update moved below popups)

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
                
                # Check media inventory
                if self._media_inventory:
                    missing, _ = self.engine.verify_media_inventory(self._media_inventory)
                    if missing:
                        # Convert to markdown bullet list for a scrollable CustomMsgBox (using QLabel properties)
                        # We just show a summary
                        files_str = ""
                        for m in missing[:5]:
                            files_str += f"- {m.get('basename', 'Unknown')}\n"
                        if len(missing) > 5:
                            files_str += f"... [+ {len(missing)-5}]\n"
                            
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
                            self.go_to_page(0)
                            if hasattr(self, '_panel_left'): self._panel_left.hide()
                            if hasattr(self, '_panel_right'): self._panel_right.hide()
                            return
                
                # Check timeline fingerprint
                if bws_extras.get("timeline_fingerprint") and getattr(self, 'resolve_handler', None) and self.resolve_handler.project:
                    found_tl, is_exact = self.resolve_handler.find_timeline_by_fingerprint(bws_extras["timeline_fingerprint"])
                    
                    # Target name from snapshot
                    target_name = (self._transcription_source or {}).get("timeline_name", "")
                    
                    if found_tl and is_exact:
                        if target_name and target_name != found_tl:
                            # Automatically update the name to match the new exact fingerprint match
                            self._transcription_source["timeline_name"] = found_tl
                            if hasattr(self, '_title_bar'):
                                self._title_bar.set_source_info(found_tl, tracks_str)
                    else:
                        # No exact match. Does it exist by name?
                        exists_by_name = self.resolve_handler.timeline_exists(target_name)
                        if exists_by_name:
                            # It exists but fingerprint differs
                            msg_box = WorkspaceWarningOverlay(
                                self._stack,
                                self.txt("bws_timeline_changed_title"),
                                self.txt("bws_timeline_changed_desc").format(tl=target_name),
                                self.txt("bws_btn_continue"),
                                btn_reject_text=self.txt("bws_btn_import_drt") if self._extracted_drt_path else None,
                                btn_cancel_text=self.txt("btn_cancel")
                            )
                            res = msg_box.exec()
                            if res == -1:  # Cancel
                                self.go_to_page(0)
                                if hasattr(self, '_panel_left'): self._panel_left.hide()
                                if hasattr(self, '_panel_right'): self._panel_right.hide()
                                return
                            if res != QDialog.Accepted:
                                if self._extracted_drt_path:
                                    new_tl = self.resolve_handler.media_pool.ImportTimelineFromFile(self._extracted_drt_path)
                                    if new_tl:
                                        new_name = f"imported '{target_name}'"
                                        new_tl.SetName(new_name)
                                        self._transcription_source["timeline_name"] = new_name
                                        if hasattr(self, '_title_bar'):
                                            self._title_bar.set_source_info(new_name, tracks_str)
                                else:
                                    return
                        else:
                            # Doesn't exist at all
                            if self._extracted_drt_path:
                                msg_box = WorkspaceWarningOverlay(
                                    self._stack,
                                    self.txt("bws_missing_timeline_title"),
                                    self.txt("bws_missing_timeline_desc").format(tl=target_name),
                                    self.txt("bws_btn_import_drt"),
                                    btn_cancel_text=self.txt("btn_cancel")
                                )
                                res = msg_box.exec()
                                if res == -1:
                                    self.go_to_page(0)
                                    if hasattr(self, '_panel_left'): self._panel_left.hide()
                                    if hasattr(self, '_panel_right'): self._panel_right.hide()
                                    return
                                if res == QDialog.Accepted:
                                    new_tl = self.resolve_handler.media_pool.ImportTimelineFromFile(self._extracted_drt_path)
                                    if new_tl:
                                        new_name = f"imported '{target_name}'"
                                        new_tl.SetName(new_name)
                                        self._transcription_source["timeline_name"] = new_name
                                        if hasattr(self, '_title_bar'):
                                            self._title_bar.set_source_info(new_name, tracks_str)

                # Recreate assembled audio if needed
                if self._assembly_recipe and bws_extras.get("audio_path"):
                    temp_dir = self.engine.os_doc.get_temp_folder()
                    out_path = os.path.join(temp_dir, f"bws_assembled_{int(time.time())}.flac")
                    self.engine.execute_assembly_recipe(self._assembly_recipe, bws_extras["audio_path"], out_path)
                    
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
                
            if hasattr(self, 'audio_preview'):
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
            elif word_obj.get('algo_status') == 'repeat':
                base = 'repeat'
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

    def _populate_timeline_track_combos(self):
        """
        Queries the Resolve API for all timelines in the current project and
        populates both timeline dropdowns (combo_tl_0 / combo_tl_1).
        Called via QTimer.singleShot(800, ...) after __init__.
        """
        try:
            rh = self.engine.resolve_handler
            timelines = rh.get_all_timelines()

            current_tl_name = ""
            if rh.timeline:
                try:
                    current_tl_name = rh.timeline.GetName()
                except Exception:
                    pass

            no_tl_label = self.txt("msg_no_timelines_detected")

            if not timelines:
                for combo in (self.combo_tl_0, self.combo_tl_1):
                    combo.options_list = [no_tl_label]
                    combo.setText(no_tl_label)
                for track_combo in (self.combo_tr_0, self.combo_tr_1):
                    track_combo.options_list = []
                    track_combo.selected_items = set()
                    track_combo.setText(self.txt("msg_no_audio_tracks_detected"))
                return

            # Populate timeline dropdowns
            for combo in (self.combo_tl_0, self.combo_tl_1):
                combo.options_list = list(timelines)
                display = current_tl_name if current_tl_name in timelines else timelines[0]
                combo.setText(display)

            # Populate track dropdowns for the default timeline
            init_tl = current_tl_name if current_tl_name in timelines else timelines[0]
            self._on_timeline_selected(init_tl, self.combo_tr_0)
            self._on_timeline_selected(init_tl, self.combo_tr_1)

        except Exception as e:
            from osdoc import log_error
            log_error(f"_populate_timeline_track_combos error: {e}")

    def _on_timeline_selected(self, tl_name, track_combo, mirror_tl_combo=None):
        """
        Updates *track_combo* with audio tracks for *tl_name*, and optionally
        mirrors the selection to *mirror_tl_combo*.
        """
        try:
            if tl_name == self.txt("msg_no_timelines_detected"):
                return

            rh = self.engine.resolve_handler
            tracks = rh.get_audio_tracks(tl_name)

            no_track_label = self.txt("msg_no_audio_tracks_detected")

            if not tracks:
                track_combo.options_list = []
                track_combo.selected_items = set()
                track_combo.setText(no_track_label)
            else:
                track_combo.options_list = list(tracks)
                track_combo.selected_items = set()
                track_combo.setText(self.txt("txt_all_tracks"))

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
        """Converts track name labels (e.g. {'A1', 'A3'}) to 1-based integer indices."""
        if not track_names:
            return []
        try:
            all_tracks = self.engine.resolve_handler.get_audio_tracks(tl_name)
            indices = []
            for name in track_names:
                if name in all_tracks:
                    indices.append(all_tracks.index(name) + 1)
            return sorted(indices)
        except Exception as e:
            from osdoc import log_error
            log_error(f"_track_names_to_indices error: {e}")
            return []

    def _on_fast_silence(self):
        """Fast Silence Cut: runs FFmpeg pipeline then directly assembles the timeline."""
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()

        self.go_to_page(1)
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(0)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("txt_initializing_fast_silence"))

        # Read from line edits
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

        # Read selected timeline and tracks
        selected_tl = getattr(self, 'combo_tl_1', None)
        selected_tl_name = selected_tl.text() if selected_tl else ""
        no_tl = self.txt("msg_no_timelines_detected")
        if selected_tl_name == no_tl:
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
        }
        self._fs_settings = settings

        self._analysis_worker = AnalysisWorker(self.engine, 'run_fast_silence_pipeline', settings)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.status.connect(self._on_analysis_status)
        self._analysis_worker.finished_ok.connect(self._on_fs_finished)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.start()


    def _on_fs_finished(self, words_data, segments_data):
        """Called when run_fast_silence_pipeline completes. Directly assembles the timeline."""
        from PySide6.QtWidgets import QApplication

        if not words_data:
            dlg = CustomMsgBox(self, self.txt("msg_standalone_silence"), self.txt("msg_no_silence_segments_detec"), self.txt("btn_ok"))
            dlg.exec()
            self.go_to_page(0)
            if hasattr(self, 'welcome_stack'): self.welcome_stack.setCurrentIndex(0)
            return

        self.lbl_processing_status.setText(self.txt("txt_assembling_timeline"))

        fs_prefs = self.engine.load_preferences() or {}
        fs_prefs['silence_cut']  = getattr(self, 'tgl_fs_cut',  None) and self.tgl_fs_cut.isChecked()
        fs_prefs['silence_mark'] = getattr(self, 'tgl_fs_mark', None) and self.tgl_fs_mark.isChecked()
        if hasattr(self, '_fs_settings'):
            fs_prefs['source_snapshot'] = self._fs_settings

        # FIX KR-03: Asynchroniczny montaż osi czasu (Fast Silence) aby uniknąć GUI freeze
        from PySide6.QtCore import QThread, Signal as _Signal, QObject

        class _FSAssemblySignals(QObject):
            status = _Signal(str)
            progress = _Signal(int)
            finished = _Signal(object)

        class _FSAssemblyThread(QThread):
            def __init__(self, engine, words_data, prefs, sigs):
                super().__init__()
                self._engine = engine
                self._data = words_data
                self._prefs = prefs
                self._sigs = sigs

            def run(self):
                try:
                    result = self._engine.assemble_timeline(
                        self._data,
                        self._prefs,
                        callback_status=self._sigs.status.emit,
                        callback_progress=self._sigs.progress.emit
                    )
                except Exception as e:
                    import osdoc
                    osdoc.log_error(f"_FSAssemblyThread Error: {e}")
                    result = (False, str(e), None, None)
                self._sigs.finished.emit(result)

        self._fs_sigs = _FSAssemblySignals()
        self._fs_sigs.status.connect(self.lbl_processing_status.setText)
        self._fs_sigs.progress.connect(self.bar_processing.set_value)

        def on_fs_assembly_done(result):
            success, warning, new_tl_name, clean_ops = result
            if success:
                dlg = CustomMsgBox(self, self.txt("msg_standalone_silence"), self.txt("msg_standalone_silence_processing_c"), self.txt("btn_ok"))
                dlg.exec()
            else:
                dlg = CustomMsgBox(self, self.txt("msg_fs_error"), f"{self.txt('msg_assembly_failed')}:\n{warning}", self.txt("btn_ok"))
                dlg.exec()

        self._fs_sigs.finished.connect(on_fs_assembly_done)
        self._fs_assembly_thread = _FSAssemblyThread(self.engine, words_data, fs_prefs, self._fs_sigs)
        self._fs_assembly_thread.start()

        self.go_to_page(0)
        if hasattr(self, 'welcome_stack'):
            self.welcome_stack.setCurrentIndex(1)

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
                import os
                from PySide6.QtGui import QIcon, QCursor
                from PySide6.QtCore import QSize, Qt
                
                color_name_lower = target_id[4:]
                color_name_title = color_name_lower.capitalize()
                color_hex = "#FFFFFF"
                for c_n, c_h in config.RESOLVE_COLORS_HEX.items():
                    if c_n.lower() == color_name_lower:
                        color_hex = c_h
                        color_name_title = c_n
                        break
                        
                _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                _assets_dir = os.path.join(_src_dir, "layout") if os.path.exists(os.path.join(_src_dir, "layout")) else os.path.join(os.path.dirname(_src_dir), "assets", "layout")

                lbl_color = QLabel(self.txt("lbl_cut_color_fmt").format(hex=color_hex, color=label_text))
                row_layout.addWidget(lbl_color)
                row_layout.addStretch()

                # Cut Now Button (proxy)
                btn_cut_now_proxy = QPushButton()
                btn_cut_now_proxy.setFixedSize(24, 24)
                btn_cut_now_proxy.setCursor(Qt.PointingHandCursor)
                btn_cut_now_proxy.setStyleSheet("background: transparent; border: none;")
                btn_cut_now_proxy.setIcon(QIcon(os.path.join(_assets_dir, "cut.png")))
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
                    
                    def _update_proxy_icon(checked, b=proxy_auto, ad=_assets_dir):
                        icon_name = "auto-marked.png" if checked else "auto-unmarked.png"
                        b.setIcon(QIcon(os.path.join(ad, icon_name)))
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

    def _save_top_toggles_prefs(self):
        prefs = self.engine.load_preferences() or {}
        if hasattr(self, 'tgl_show_inaudible'): prefs['show_inaudible'] = self.tgl_show_inaudible.isChecked()
        if hasattr(self, 'tgl_show_typos'): prefs['show_typos'] = self.tgl_show_typos.isChecked()
        if hasattr(self, 'tgl_mark_inaudible'): prefs['mark_inaudible'] = self.tgl_mark_inaudible.isChecked()
        self.engine.save_preferences(prefs)
    def _on_assemble(self):
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

        # SANITIZE EXPORT DATA (prevents C++ QRect deepcopy memory leaks)
        export_data    = self._get_clean_words_data()
        show_typos     = prefs.get('show_typos', True)
        mark_inaudible = prefs.get('mark_inaudible', True)
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
                        import tempfile
                        
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
        
        is_sbs = getattr(self.text_canvas, 'is_sbs_mode', False)
        if hasattr(self, '_panel_left') and not is_sbs: self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        dlg = CustomMsgBox(self, self.txt("lbl_error"), err_msg, self.txt("btn_ok"))
        dlg.exec()

    def _build_welcome_screen(self) -> QWidget:
        """Page 0 of the main stack: Welcome / Config screen."""
        from gui.views import build_welcome_view
        return build_welcome_view(self)

    def _build_page_processing(self) -> QWidget:
        """Page 1 of the main stack: Processing / Progress screen."""
        from gui.views import build_processing_view
        return build_processing_view(self)

    def _update_processing_progress(self, val: int):
        if hasattr(self, 'bar_processing'):
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
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        _prod_assets_dir = os.path.join(_src_dir, "layout")
        _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
        _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
        info_icon_path = os.path.join(_assets_dir, "information.png")
        if os.path.exists(info_icon_path):
            info.setPixmap(QPixmap(info_icon_path).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            info.setText("🛈")
            info.setStyleSheet("color: #888888; font-size: 11pt;")
            
        tt_text = self.txt(tooltip_key) if hasattr(self, 'txt') else tooltip_key
        info.custom_tooltip_text = f"<div style='max-width: 300px; white-space: pre-wrap;'>{tt_text}</div>"
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
            self.text_canvas.load_data(words_data)
            self._show_transcript_view()

    # ------------------------------------------------------------------
    # Sidebar navigation stubs
    # ------------------------------------------------------------------

    def _on_nav_script(self):
        """Navigate to the Script / Welcome page."""
        self.go_to_page(0)

    def _on_nav_analysis(self):
        """Navigate to the Analysis / Processing page."""
        self.go_to_page(1)

    def _on_more_accurate_toggled(self, checked):
        self.engine.save_preferences({"ai_more_accurate": checked})
        if not hasattr(self, 'script_container'): return
        
        from PySide6.QtCore import QVariantAnimation, QEasingCurve
        
        has_btn = hasattr(self, 'btn_import_wrapper')
        if has_btn:
            # Temporarily un-restrict to measure natural width
            self.btn_import_wrapper.setMaximumWidth(16777215)
            btn_full_w = self.btn_import_wrapper.sizeHint().width()
            start_btn_w = self.btn_import_wrapper.width() if self.btn_import_wrapper.isVisible() else 0
            end_btn_w = btn_full_w if checked else 0
            
            if checked:
                self.btn_import_wrapper.setMaximumWidth(start_btn_w)
                self.btn_import_wrapper.setVisible(True)

        self._script_anim = QVariantAnimation(self)
        self._script_anim.setDuration(500)
        self._script_anim.setStartValue(0.0)
        self._script_anim.setEndValue(1.0)
        self._script_anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        start_w = self.script_container.width()
        end_w = 350 if checked else 0
        
        def _on_step(v):
            self.script_container.setFixedWidth(int(start_w + (end_w - start_w) * v))
            if has_btn:
                self.btn_import_wrapper.setMaximumWidth(int(start_btn_w + (end_btn_w - start_btn_w) * v))
                
        def _on_finish():
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
                _orig_ss = (
                    f"QPushButton {{"
                    f" background-color: #1e1e1e;"
                    f" color: #d4d4d4;"
                    f" text-align: left;"
                    f" padding: 4px 8px;"
                    f" border: 1px solid #3a3a3a;"
                    f" border-radius: 3px;"
                    f" min-height: 20px;"
                    f"}}"
                    f"QPushButton:hover {{ border-color: {config.BTN_BG}; }}"
                )
                _err_ss = (
                    "QPushButton {"
                    " background-color: #1e1e1e;"
                    " color: #d4d4d4;"
                    " text-align: left;"
                    " padding: 4px 8px;"
                    " border: 1px solid #ed4245;"
                    " border-radius: 3px;"
                    " min-height: 20px;"
                    "}"
                    "QPushButton:hover { border-color: #ed4245; }"
                )
                self._combo_lang.setStyleSheet(_err_ss)
                
                # Add a little shake animation
                from PySide6.QtCore import QPropertyAnimation as _QPA, QPoint as _QP
                anim = _QPA(self._combo_lang, b"pos", self)
                anim.setDuration(300)
                pos = self._combo_lang.pos()
                anim.setKeyValueAt(0, pos)
                anim.setKeyValueAt(0.2, pos + _QP(5, 0))
                anim.setKeyValueAt(0.4, pos - _QP(5, 0))
                anim.setKeyValueAt(0.6, pos + _QP(5, 0))
                anim.setKeyValueAt(0.8, pos - _QP(5, 0))
                anim.setKeyValueAt(1, pos)
                anim.start()
                self._lang_shake_anim = anim # keep ref
                
                from PySide6.QtCore import QTimer as _QT
                _QT.singleShot(1250, lambda: self._combo_lang.setStyleSheet(_orig_ss))
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
                anim = _QPA(target_widget, b"pos", parent_widget)
                anim.setDuration(300)
                pos = target_widget.pos()
                anim.setKeyValueAt(0, pos)
                anim.setKeyValueAt(0.2, pos + _QP(5, 0))
                anim.setKeyValueAt(0.4, pos - _QP(5, 0))
                anim.setKeyValueAt(0.6, pos + _QP(5, 0))
                anim.setKeyValueAt(0.8, pos - _QP(5, 0))
                anim.setKeyValueAt(1, pos)
                anim.start()
                self._script_shake_anim = anim # keep ref
                
                from PySide6.QtCore import QTimer as _QT
                _QT.singleShot(1250, lambda: self.welcome_script_edit.setStyleSheet(_orig_script_ss))
            return  # Do NOT start analysis

        # 1. Hide side panels
        if hasattr(self, '_panel_left'): self._panel_left.hide()
        if hasattr(self, '_panel_right'): self._panel_right.hide()
        
        # Un-toggle the sidebar buttons so they don't look active
        if hasattr(self, 'btn_nav_script'): self.btn_nav_script.set_active(False)
        if hasattr(self, 'btn_nav_main'): self.btn_nav_main.set_active(False)

        # 2. Switch stack to index 1 (Processing page)
        self.go_to_page(1)
        
        # Reset progress bar UI
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(0)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(self.txt("txt_initializing_analysis"))

        # ── First-run hint: check if chosen model has been run before ────────────
        raw_model_for_check = self._combo_model.text() if hasattr(self, '_combo_model') else 'Medium'
        model_key = raw_model_for_check.split()[0].lower()
        if model_key == 'large': model_key = 'large-v3'
        
        # Check for marker file instead of settings.json
        model_folder_name = f"models--Systran--faster-whisper-{model_key}"
        import os
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
                except: pass
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
                """Fade out current hint, swap text, fade back in."""
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

            # Show first hint immediately (fade in from scratch)
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
            self._hint_timer.start(10500)  # rotate hint every 10.5 seconds


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
        }

        
        # 4. Start QThread targeting self.engine.run_analysis_pipeline()
        import time
        self._transcription_start_time = time.time()
        self._analysis_worker = AnalysisWorker(self.engine, 'run_analysis_pipeline', settings)
        self._analysis_worker.progress.connect(self._on_analysis_progress)
        self._analysis_worker.status.connect(self._on_analysis_status)
        self._analysis_worker.finished_ok.connect(self._on_analysis_finished)
        self._analysis_worker.error.connect(self._on_analysis_error)
        self._analysis_worker.start()

    def _on_analysis_progress(self, val):
        self._update_processing_progress(val)

    def _on_analysis_status(self, msg):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(msg)

    def _on_analysis_error(self, err):
        # Stop hint rotation and animations
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
            self.lbl_first_run_hint.hide()
            if hasattr(self, '_hint_opacity'):
                self._hint_opacity.setOpacity(0.0)
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(f"Error: {err}")

    def _on_analysis_finished(self, words_data, segments_data):
        # Stop hint rotation and animations on finish
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
            self.lbl_first_run_hint.hide()
            if hasattr(self, '_hint_opacity'):
                self._hint_opacity.setOpacity(0.0)


        if not words_data:
            dlg = CustomMsgBox(self, self.txt("msg_analysis_failed"), self.txt("msg_the_transcription_process"), self.txt("btn_ok"))
            dlg.exec()
            # Reset UI to Page 0 and show panels again
            self.go_to_page(0)
            self._panel_left.show()
            self._panel_right.show()
            return
            
        self.go_to_page(2)
        
        self._toggle_activity("script_analysis")
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


    def _on_nav_markers(self):
        """Toggle the right panel (placeholder)."""
        print("[BadWordsGUI] Tools toggled (Stage 4 TODO)")

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def _maximize_on_active_screen(self):
        """
        Move the window to the monitor that currently has the cursor and maximize.
        DWM / the WM remembers the geometry that was set IMMEDIATELY before
        showMaximized() as the "restore" size used when drag-to-unmaximizing.
        We position 580x670 centered on the target screen first, THEN maximize,
        so the restore size is always 580x670 regardless of previous session state.
        """
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(580, 670)
            if getattr(self, '_is_mac', False):
                self.showFullScreen()
            else:
                self.showMaximized()
            return
        sg = screen.availableGeometry()
        # Center 580x670 on the target screen — this becomes the restore geometry
        self.setGeometry(
            sg.x() + (sg.width()  - 580) // 2,
            sg.y() + (sg.height() - 670) // 2,
            580, 670
        )
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

    def _on_add_custom_marker(self):
        from PySide6.QtWidgets import QApplication
        dlg = SettingsDialog(self.engine, self)
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
            app.focusChanged.connect(lambda old_w, new_w: self._update_shortcut_enabled_states())
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
        dlg = SettingsDialog(self.engine, self)
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
        if index != 2:
            if hasattr(self, '_title_bar') and hasattr(self._title_bar, 'deactivate_transcription_mode'):
                self._title_bar.deactivate_transcription_mode()
            if getattr(self, '_is_mac', False):
                if hasattr(self, '_mac_menu_project'):
                    self._mac_menu_project.menuAction().setVisible(False)
                    self._mac_menu_transcript.menuAction().setVisible(False)
                    self._mac_menu_source.menuAction().setVisible(False)
                    self._mac_menu_edits.menuAction().setVisible(False)
        else:
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
        if opt_in is None:
            popup = TelemetryPopup(self.engine, parent=self)
            self.engine.os_doc.force_dark_titlebar(int(popup.winId()))
            popup.exec()  # ApplicationModal — blocks until user responds
        elif opt_in is True:
            self.engine.send_telemetry_ping("app_started")

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
            auto   = prefs.get('auto_update_on_start', False)

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
        import threading, subprocess, tempfile, os, urllib.request, ssl
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
                cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                
                install_dir = getattr(self.engine.os_doc, 'install_dir', '')
                if is_win:
                    venv_py = os.path.join(install_dir, 'venv', 'Scripts', 'python.exe')
                else:
                    venv_py = os.path.join(install_dir, 'venv', 'bin', 'python3')
                    
                if not os.path.isfile(venv_py):
                    venv_py = sys.executable

                cmd = [venv_py, tmp]
                if install_dir:
                    cmd.extend(['--install-dir', install_dir])

                result = subprocess.run(
                    cmd, stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    encoding='utf-8', errors='replace', timeout=600, creationflags=cf
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

    def txt(self, key: str, **kwargs) -> str:
        return _txt(self.lang, key, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        msg_box = CustomMsgBox(self, self.txt('msg_quit_title'), self.txt('msg_quit_desc'), self.txt('btn_yes'), self.txt('btn_no'))
        if msg_box.exec() == QDialog.Accepted:
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
