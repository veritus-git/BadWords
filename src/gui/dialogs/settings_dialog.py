#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: settings_dialog.py
ROLE: GUI Dialog
DESCRIPTION:
Modern card-based Settings window with 9 categories (including dedicated Custom
Markers tab with File vs DaVinci guide + Shortcuts jump and MarkerDialog shortcut assignment),
Brave-style ranked search with green highlights and English fallback, mandatory sanitized
Support diagnostics with thumbnail/lightbox image attachments, and an engaging About & Privacy section.
"""

import os
import sys

from PySide6.QtCore import (
    Qt, QPoint, QRect, QSize, QTimer, Signal, QObject, QVariantAnimation, QEasingCurve, QUrl, QEvent
)
from PySide6.QtGui import (
    QFont, QFontMetrics, QGuiApplication, QDesktopServices, QColor, QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QLabel, QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QSizePolicy, QFrame, QScrollArea, QStackedWidget, QLineEdit,
    QButtonGroup, QTextEdit
)

import config
from gui.components.mixins import FramelessWindowMixin, _BaseMainWindow, _HAS_QFRAMELESS
from gui.components.titlebar import CustomTitleBar
from gui.widgets.buttons import (
    QPushButton, ToggleSwitch, ShortcutCaptureButton,
    MouseShortcutCaptureButton, CustomDropdown, SearchableDropdown,
    ReloadButton, CloseIconButton, SquareIconButton, CustomNumberInput,
    AssemblyModeSelector
)
from gui.widgets.layouts import FlowLayout
from gui.widgets.sliders import JumpSlider
from gui.widgets.labels import QLabel
from gui.widgets.text_edits import WrappingPlaceholderTextEdit
from gui.widgets.delegates import MarqueeItemDelegate
from gui.utils import _txt, _app_icon, _center_on_screen, get_svg_icon, create_info_icon, get_vector_pixmap
from gui.vsync import track_window_screen

from gui.dialogs.msgbox import CustomMsgBox
from gui.dialogs.update_dialog import UpdateCheckThread
from gui.dialogs.marker_dialog import MarkerDialog
from gui.dialogs.unsaved_changes_dialog import UnsavedChangesDialog
from gui.dialogs.overlay import MarkerDragZone, MarkerRowWidget
from gui.dialogs.settings_widgets import (
    SETTINGS_VIEWPORT_BG, SETTINGS_CARD_BG, SETTINGS_CARD_BORDER,
    SETTINGS_DIVIDER_COL, SETTINGS_INPUT_BG, SETTINGS_INPUT_BORDER,
    SVG_SHIELD, SVG_COFFEE, SVG_GRIP_DOTS, SVG_SEARCH_EMPTY, SVG_TRASH, SVG_CHEVRON_RIGHT,
    SettingsPageHeader, SettingsSectionLabel, SettingsRowWidget, SettingsCard,
    SettingsSearchBar, SearchResultCard, AttachmentThumbCard, SupportDropZone,
    ScreenshotPreviewDialog, save_clipboard_image_temp, scope_transparent,
    fold_accents, highlight_text_html, score_search_entry,
)


_CACHED_FONT_FAMILIES = None
_MAX_SUPPORT_SCREENSHOTS = 5


def _get_system_font_families():
    global _CACHED_FONT_FAMILIES
    if _CACHED_FONT_FAMILIES is None:
        try:
            from PySide6.QtGui import QFontDatabase
            _CACHED_FONT_FAMILIES = sorted(list(set(QFontDatabase.families())))
        except Exception:
            _CACHED_FONT_FAMILIES = [config.UI_FONT_NAME, "Ubuntu", "Arial", "Helvetica", "sans-serif"]
    return _CACHED_FONT_FAMILIES


def _is_segmented_text(text: str) -> bool:
    if not text:
        return False
    seg_texts = {
        trans.get('opt_segmented_blocks')
        for trans in getattr(config, 'TRANS', {}).values()
        if 'opt_segmented_blocks' in trans
    } | {
        'Segmented blocks', 'Segmentowane bloki', 'Segmentierte Blöcke',
        'Bloques segmentados', 'Blocs segmentés', 'Blocchi segmentati',
        'Blocos segmentados', 'Сегментированные блоки', 'Сегментовані блоки',
        'Gesegmenteerde blokken', '分段块'
    }
    return text in seg_texts


def _is_continuous_text(text: str) -> bool:
    if not text:
        return False
    cont_texts = {
        trans.get('opt_continuous_flow')
        for trans in getattr(config, 'TRANS', {}).values()
        if 'opt_continuous_flow' in trans
    } | {
        'Continuous flow', 'Continuous Flow', 'Ciągły przepływ',
        'Kontinuierlicher Fluss', 'Fluxo Contínuo', 'Flusso Continuo',
        'Непрерывный поток', 'Continue Stroom', 'Flujo Continuo',
        'Безперервний потік', 'Flux continu', '连续流式', '连续流'
    }
    return text in cont_texts


def _get_mouse_mode_from_text(text: str, default: str = 'box') -> str:
    if not text:
        return default
    box_texts = {trans.get('opt_mouse_box') for trans in getattr(config, 'TRANS', {}).values() if 'opt_mouse_box' in trans} | {'Box selection', 'Zaznaczanie obszarem', 'Marquee Box Selection'}
    text_texts = {trans.get('opt_mouse_text') for trans in getattr(config, 'TRANS', {}).values() if 'opt_mouse_text' in trans} | {'Text Selection (Notepad)', 'Text selection', 'Zaznaczanie tekstu (Notatnik)', 'Zaznaczanie tekstu'}
    brush_texts = {trans.get('opt_mouse_brush') for trans in getattr(config, 'TRANS', {}).values() if 'opt_mouse_brush' in trans} | {'Brush selection', 'Pędzel / malowanie', 'Brush Painting'}
    none_texts = {trans.get('opt_mouse_none') for trans in getattr(config, 'TRANS', {}).values() if 'opt_mouse_none' in trans} | {'None', 'Brak', 'Disabled'}
    if text in box_texts:
        return 'box'
    if text in text_texts:
        return 'text'
    if text in brush_texts:
        return 'brush'
    if text in none_texts:
        return 'none'
    return default


def _blend_hex(fg_hex: str, bg_hex: str, factor: float) -> str:
    t = max(0.0, min(1.0, float(factor)))
    fg = QColor(fg_hex)
    bg = QColor(bg_hex)
    r = int(round(bg.red() + (fg.red() - bg.red()) * t))
    g = int(round(bg.green() + (fg.green() - bg.green()) * t))
    b = int(round(bg.blue() + (fg.blue() - bg.blue()) * t))
    return f"#{r:02x}{g:02x}{b:02x}"


class _CenteredPageHost(QWidget):
    """Centers settings page content up to max_width when widened/maximized without latching minimumWidth."""

    def __init__(self, content: QWidget, max_width: int, parent=None):
        super().__init__(parent)
        self._content = content
        self._max_width = max(1, int(max_width))
        scope_transparent(self, border_none=False)
        self.setMinimumWidth(0)
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(0)
        content.setParent(self)
        content.setMinimumWidth(0)
        content.setMaximumWidth(self._max_width)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._lay.addWidget(content)

    def _sync_margins(self):
        avail_w = self.width()
        side_pad = max(0, (avail_w - self._max_width) // 2)
        cur = self._lay.contentsMargins()
        if cur.left() != side_pad or cur.right() != side_pad:
            self._lay.setContentsMargins(side_pad, 0, side_pad, 0)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_margins()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_margins()


class SettingsDialog(FramelessWindowMixin, _BaseMainWindow):
    """Settings Window - 1:1 top-level QMainWindow matching BadWordsGUI framing & titlebar.
    All I/O goes through engine.load_preferences / engine.save_preferences
    which delegate to osdoc's smart router.
    """

    finished = Signal(int)

    # Category tab indices (9 tabs; index 9 on stack is Search Results)
    TAB_GENERAL = 0
    TAB_APPEARANCE = 1
    TAB_EDITOR = 2
    TAB_DAVINCI = 3
    TAB_SHORTCUTS = 4
    TAB_MARKERS = 5
    TAB_AI_ENGINE = 6
    TAB_SUPPORT = 7
    TAB_ABOUT = 8
    STACK_SEARCH_IDX = 9

    # Fallback defaults (for revert buttons)
    DEFAULTS = {
        'view_mode':          'segmented',
        'offset':             0.133,
        'pad':                0.0,
        'snap_max':           0.25,
        'editor_font_family': config.UI_FONT_NAME,
        'editor_font_size':   12,
        'editor_line_height': 7,
        'theme':              'dark',
        'always_on_top':      False,
        'hidden_panels':      [],
    }

    def txt(self, key: str, default: str = None, **kwargs) -> str:
        prefs = self.engine.load_preferences() or {}
        lang = prefs.get("gui_lang", "en")
        return _txt(lang, key, default=default, **kwargs)

    def _en(self, key: str, default: str = None, **kwargs) -> str:
        return _txt("en", key, default=default, **kwargs)

    def _active_lang(self) -> str:
        prefs = self.engine.load_preferences() or {}
        return str(prefs.get("gui_lang", "en") or "en")

    def _get_main_window(self):
        return getattr(self, '_main_window', None) or self.parent()

    def _sync_native_always_on_top(self):
        """Ensures Win32 WS_EX_TOPMOST matches _always_on_top_active on open/show."""
        enable = bool(getattr(self, '_always_on_top_active', False))
        if not self.testAttribute(Qt.WA_WState_Created):
            return
        os_doc = getattr(getattr(self, 'engine', None), 'os_doc', None)
        if not os_doc:
            return
        try:
            win_id = int(self.winId())
            if not win_id:
                return
            if getattr(os_doc, 'is_win', False) and hasattr(os_doc, 'is_window_topmost'):
                if os_doc.is_window_topmost(win_id) != enable:
                    os_doc.set_always_on_top(win_id, enable)
            elif enable:
                os_doc.set_always_on_top(win_id, True)
        except Exception:
            pass

    def set_always_on_top_state(self, enable: bool):
        enable = bool(enable)
        self._always_on_top_active = enable
        native_ok = False
        os_doc = getattr(getattr(self, 'engine', None), 'os_doc', None)
        if not self.isVisible() and bool(self.windowFlags() & Qt.WindowStaysOnTopHint) != enable:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
        try:
            if self.testAttribute(Qt.WA_WState_Created) and os_doc:
                win_id = int(self.winId())
                if win_id:
                    native_ok = bool(os_doc.set_always_on_top(win_id, enable))
        except Exception:
            native_ok = False
        if (not native_ok or not self.isVisible()):
            if bool(self.windowFlags() & Qt.WindowStaysOnTopHint) != enable:
                was_visible = self.isVisible()
                reopen_max = was_visible and self._is_effectively_maximized()
                self.setWindowFlag(Qt.WindowStaysOnTopHint, enable)
                if was_visible:
                    if reopen_max:
                        self.showMaximized()
                    else:
                        self.show()
                if self.testAttribute(Qt.WA_WState_Created) and os_doc:
                    try:
                        os_doc.set_always_on_top(int(self.winId()), enable)
                    except Exception:
                        pass

    def __init__(self, engine, parent=None):
        # Independent top-level window (same Python process) for Alt+Tab & maximize/minimize support
        # INVARIANT: Never set Qt.Tool or call winId() in __init__ (prevents hidden Win11 startup micro-window flashes).
        super().__init__(None)
        self._main_window = parent
        self.engine = engine
        self._reopen_maximized = False
        self.setWindowTitle(self.txt("tool_settings"))
        self.frameless_init(is_popup=False, use_linux_csd_shadow=False)
        self.setWindowIcon(_app_icon())
        self.setMinimumSize(config.S(640), config.S(460))

        # Inherit always on top from main window using authoritative _always_on_top_active
        is_top = bool(
            parent and getattr(
                parent,
                '_always_on_top_active',
                bool(parent.windowFlags() & Qt.WindowStaysOnTopHint),
            )
        )
        self.set_always_on_top_state(is_top)

        self._search_entries = []
        self._temp_clipboard_images = []
        self._pending_shortcuts = {}
        prefs = self.engine.load_preferences() or {}

        self._build_dialog_chrome(prefs)

        init_w = config.SETTINGS_WINDOW_W
        init_h = config.SETTINGS_WINDOW_H
        _center_on_screen(self, init_w, init_h, reference_window=self._main_window)
        self.init_normal_geometry(
            saved_w=init_w,
            saved_h=init_h,
            screen=self.screen() or QGuiApplication.primaryScreen(),
            ratio=0.70,
            min_w=config.S(640),
            min_h=config.S(460),
            apply_geometry=False,
            always_restore_default=True,
        )

    def _build_dialog_chrome(self, prefs: dict):
        """Constructs or rebuilds the Settings dialog stylesheet, chrome, sidebar, and pages."""
        self.setMinimumSize(config.S(640), config.S(460))

        # ── Global stylesheet (Option 1: Darker Margins + Elevated Cards) ─
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {SETTINGS_VIEWPORT_BG}; }}
            #MainInnerFrame {{
                background-color: {SETTINGS_VIEWPORT_BG};
                border: none;
            }}
            QPushButton {{
                padding: {config.S(6)}px {config.S(16)}px;
                outline: none;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                font-size: {config.FS_PX(10)}px;
                background: transparent;
            }}
            QListWidget {{
                background-color: {config.SIDEBAR_BG};
                border: none;
                border-right: 1px solid {config.SEPARATOR_COL};
                outline: none;
                padding: {config.S(4)}px 0;
            }}
            QListWidget::item {{
                color: #b4b4b4;
                font-family: "{config.UI_FONT_NAME}", "Ubuntu", sans-serif;
                font-size: {config.FS_PX(10)}px;
                height: {config.S(35)}px;
                padding: 0px {config.S(16)}px;
                border-radius: 0px;
            }}
            QListWidget::item:selected,
            QListWidget::item:selected:active,
            QListWidget::item:selected:!active {{
                background-color: #2f3335;
                color: #ffffff;
                border-left: 2px solid {config.BTN_BG};
            }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover:!selected {{
                background-color: #2c2c2c;
                color: #f0f0f0;
            }}
            QStackedWidget {{
                background-color: {SETTINGS_VIEWPORT_BG};
            }}
            QLineEdit, QTextEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
                background-color: {SETTINGS_INPUT_BG};
                color: {config.INPUT_FG};
                border: 1px solid {SETTINGS_INPUT_BORDER};
                padding: {config.S(4)}px {config.S(8)}px;
                border-radius: {config.S(4)}px;
                outline: none;
            }}
            QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {config.BTN_BG};
                outline: none;
            }}
            QCheckBox {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS_PX(10)}px;
                spacing: {config.S(8)}px;
            }}
            QPushButton#btn_apply {{
                background-color: {config.BTN_BG};
                color: white;
                border: none;
                border-radius: {config.S(4)}px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS_PX(10)}px;
                padding: 0 {config.S(18)}px;
            }}
            QPushButton#btn_apply:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_apply:pressed {{ background-color: #125c2f; }}
            QPushButton#btn_apply[saved="true"] {{
                background-color: #1a7a3e;
                color: #ffffff;
            }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                color: #d4d4d4;
                border: 1px solid #4a4a4a;
                border-radius: {config.S(4)}px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS_PX(9.5)}px;
                padding: 0 {config.S(12)}px;
            }}
            QPushButton#btn_secondary:hover {{ background-color: #2c2f30; border-color: #777777; color: #ffffff; }}
            QPushButton#btn_ghost_sm {{
                background-color: transparent;
                color: #a8a8a8;
                border: 1px solid #3f3f3f;
                border-radius: {config.S(4)}px;
                font-family: "{config.UI_FONT_NAME}", sans-serif;
                font-size: {config.FS_PX(9.2)}px;
                padding: {config.S(4)}px {config.S(12)}px;
                text-align: center;
            }}
            QPushButton#btn_ghost_sm:hover {{ background-color: #2a2d2e; color: #ffffff; border-color: #666666; }}
            QPushButton#btn_ghost_sm:pressed {{ background-color: #1a1a1a; color: #aaaaaa; border-color: #444444; }}
            {config.scrollbar_qss(8, bg=SETTINGS_VIEWPORT_BG)}
        """)

        # ─────────────────────────────────────────────────────────────────
        # Root layout: 1:1 central QFrame matching BadWordsGUI (no CSD shadow)
        # ─────────────────────────────────────────────────────────────────
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        self._root_frame = self.inner_frame
        self.setCentralWidget(self.inner_frame)

        outer_layout = QVBoxLayout(self.inner_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self._tb = CustomTitleBar(self, prefs.get("gui_lang", "en"), parent=self.inner_frame)
        self._title_bar = self._tb
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.set_title(self.txt("tool_settings"))
        if getattr(self, '_is_mac', False):
            self._tb.setVisible(False)
            self._tb.setFixedHeight(0)
        outer_layout.addWidget(self._tb)

        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer_layout.addLayout(root)

        # ── LEFT: Search bar + Category list ─────────────────────────────
        self.left_panel = QWidget()
        left_panel = self.left_panel
        left_panel.setObjectName("SettingsLeftPanel")
        left_panel.setFixedWidth(config.S(212))
        left_panel.setStyleSheet(f"""
            QWidget#SettingsLeftPanel {{
                background-color: {config.SIDEBAR_BG};
                border-right: 1px solid #353535;
            }}
            QListWidget {{
                border-right: none;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(config.S(10), config.S(10), config.S(10), config.S(10))
        left_layout.setSpacing(config.S(8))

        # Modern custom search bar (zero ugly system clear icon) + 180ms input debounce
        self._search_debounce_timer = QTimer(self)
        self._search_debounce_timer.setSingleShot(True)
        self._search_debounce_timer.setInterval(180)
        self._search_debounce_timer.timeout.connect(self._execute_pending_search)

        self.search_edit = SettingsSearchBar(self.txt("search_settings_placeholder"), parent=left_panel)
        self.search_edit.textChanged.connect(self._on_search_query_changed)
        self.search_edit.returnPressed.connect(self._execute_pending_search)
        left_layout.addWidget(self.search_edit)

        self.category_list = QListWidget()
        self.category_list.setFocusPolicy(Qt.NoFocus)
        self.category_list.setSpacing(0)
        self.category_list.setFont(config.make_font(config.UI_FONT_NAME, 10))
        self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._marquee_delegate = MarqueeItemDelegate(self.category_list, padding=config.S(14), row_height=config.S(35))
        self.category_list.setItemDelegate(self._marquee_delegate)
        left_layout.addWidget(self.category_list, 1)

        root.addWidget(left_panel)

        # ── RIGHT: stacked pages + bottom bar ────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        root.addLayout(right_layout, 1)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack, 1)

        self.w_footer = QWidget()
        self.w_footer.setObjectName("SettingsFooterBar")
        self.w_footer.setStyleSheet("QWidget#SettingsFooterBar { background-color: #202020; }")
        l_footer = QVBoxLayout(self.w_footer)
        l_footer.setContentsMargins(0, 0, 0, 0)
        l_footer.setSpacing(0)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #323232; max-height: 1px; border: none;")
        l_footer.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(config.S(16), config.S(10), config.S(16), config.S(12))
        btn_bar.setSpacing(config.S(8))

        btn_bar.addStretch()

        self.btn_restore = QPushButton(self.txt("btn_restore_defaults"))
        self.btn_restore.setObjectName("btn_secondary")
        self.btn_restore.setMinimumWidth(config.S(90))
        self.btn_restore.setFixedHeight(config.S(30))
        self.btn_restore.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self._restore_all_defaults)
        btn_bar.addWidget(self.btn_restore)

        self.btn_close = QPushButton(self.txt("btn_close"))
        self.btn_close.setObjectName("btn_secondary")
        self.btn_close.setMinimumWidth(config.S(84))
        self.btn_close.setFixedHeight(config.S(30))
        self.btn_close.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.close)
        btn_bar.addWidget(self.btn_close)

        self.btn_apply = QPushButton(self.txt("btn_apply"))
        self.btn_apply.setObjectName("btn_apply")
        self.btn_apply.setMinimumWidth(config.S(84))
        self.btn_apply.setFixedHeight(config.S(30))
        self.btn_apply.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_bar.addWidget(self.btn_apply)

        l_footer.addLayout(btn_bar)
        right_layout.addWidget(self.w_footer)

        self._build_ui()

    def _schedule_live_ui_scale(self, mode: str, pct: int | None):
        """Schedules live UI rescale on next tick so active slider mouse handlers unwind cleanly."""
        QTimer.singleShot(0, lambda m=mode, p=pct: self._apply_live_ui_scale(m, p))

    def _apply_live_ui_scale(self, mode: str, pct: int | None):
        """Applies new UI scaling factor immediately without restarting process or dropping Resolve IPC."""
        if getattr(self, '_rebuilding_scale', False):
            return
        main_win = self._get_main_window()
        scr = self.screen() or (main_win.screen() if main_win else None) or QGuiApplication.primaryScreen()
        config.apply_ui_scaling(mode=mode, pct=pct, screen=scr)

        app = QApplication.instance()
        if app is not None:
            app.setFont(
                config.make_font(
                    config.UI_FONT_NAME,
                    config.BASE_FONT_PT,
                    weight=QFont.Weight.Normal,
                )
            )

        if getattr(self, '_is_mac', False):
            # Rebuild active Settings window first so macOS Fullscreen Space keeps focus cleanly
            was_fs = bool(self.isFullScreen())
            self.rebuild_ui_for_scale()
            if main_win is not None and hasattr(main_win, 'rebuild_ui_for_scale'):
                main_win.rebuild_ui_for_scale()
            def _keep_mac_settings_focus():
                try:
                    if not self.isVisible():
                        return
                    if was_fs and not self.isFullScreen():
                        self.showFullScreen()
                    self.raise_()
                    self.activateWindow()
                except RuntimeError:
                    pass
            QTimer.singleShot(0, _keep_mac_settings_focus)
            return

        if main_win is not None and hasattr(main_win, 'rebuild_ui_for_scale'):
            main_win.rebuild_ui_for_scale()

        self.rebuild_ui_for_scale()

    def sync_auto_os_scale_display(self, os_pct: int):
        """Refreshes the live Auto-mode scale indicator when moving across mixed-DPI screens."""
        if getattr(self, '_ui_scale_mode', 'auto') != 'auto':
            return
        self._updating_scale_slider = True
        try:
            if hasattr(self, 'slider_ui_scale') and self.slider_ui_scale is not None:
                self.slider_ui_scale.setValue(max(config.UI_SCALE_MIN, min(config.UI_SCALE_MAX, int(os_pct))))
            if hasattr(self, '_refresh_scale_label') and callable(self._refresh_scale_label):
                self._refresh_scale_label(int(os_pct), True)
        except RuntimeError:
            pass
        finally:
            self._updating_scale_slider = False

    def rebuild_ui_for_scale(self):
        """Cleanly rebuilds all Settings widgets/fonts at current SCALE_FACTOR preserving state & active tab."""
        if getattr(self, '_rebuilding_scale', False):
            return
        self._rebuilding_scale = True
        was_visible = self.isVisible()
        self.setUpdatesEnabled(False)
        try:
            saved_state = self._get_current_state_dict()
            saved_initial = dict(getattr(self, '_initial_state', {}) or {})
            saved_initial['ui_scale_mode'] = saved_state.get('ui_scale_mode', 'auto')
            saved_initial['ui_scale_pct'] = saved_state.get('ui_scale_pct', config.UI_SCALE_PERCENT)

            saved_tab = self.category_list.currentRow() if hasattr(self, 'category_list') else 0
            saved_search = self.search_edit.text() if hasattr(self, 'search_edit') else ''
            saved_basic = getattr(self, '_is_basic_mode', True)
            saved_support = {
                'email': self._safe_get('input_support_email', '', 'text'),
                'title': self._safe_get('input_support_title', '', 'text'),
                'body': self._safe_get('input_support_body', '', 'toPlainText'),
                'category': self._safe_get('combo_support_category', '', 'currentText'),
                'attachments': list(getattr(self, 'support_attachments', [])),
            }

            old_central = self.takeCentralWidget()

            build_prefs = dict(self.engine.load_preferences() or {})
            build_prefs['settings_view_mode'] = 'basic' if saved_basic else 'advanced'
            self._build_dialog_chrome(build_prefs)

            if old_central is not None:
                old_central.hide()
                old_central.setParent(None)
                old_central.deleteLater()

            if hasattr(self, 'category_list'):
                for i in range(self.category_list.count()):
                    self._ensure_page_built(i)

            self._restore_state_dict(saved_state)
            self._set_view_mode('basic' if saved_basic else 'advanced')

            if hasattr(self, 'category_list') and 0 <= saved_tab < self.category_list.count():
                self.category_list.setCurrentRow(saved_tab)
            if saved_search and hasattr(self, 'search_edit'):
                self.search_edit.setText(saved_search)
                self._execute_pending_search()

            try:
                if hasattr(self, 'input_support_email'):
                    self.input_support_email.setText(saved_support['email'])
                if hasattr(self, 'input_support_title'):
                    self.input_support_title.setText(saved_support['title'])
                if hasattr(self, 'input_support_body'):
                    self.input_support_body.setPlainText(saved_support['body'])
                if hasattr(self, 'combo_support_category') and saved_support['category']:
                    self.combo_support_category.setText(saved_support['category'])
                self.support_attachments = list(saved_support['attachments'])
                if hasattr(self, '_render_attachments_fn') and callable(self._render_attachments_fn):
                    self._render_attachments_fn()
            except Exception:
                pass

            self._initial_state = saved_initial
            self._default_normal_size = QSize(config.SETTINGS_WINDOW_W, config.SETTINGS_WINDOW_H)

            if not self._is_effectively_maximized():
                scr = self.screen() or QGuiApplication.primaryScreen()
                avail = scr.availableGeometry() if scr else QRect(0, 0, 1280, 800)
                new_w = max(config.S(640), min(config.SETTINGS_WINDOW_W, avail.width() - 16))
                new_h = max(config.S(460), min(config.SETTINGS_WINDOW_H, avail.height() - 16))
                cx, cy = self.geometry().center().x(), self.geometry().center().y()
                nx = max(avail.left(), min(cx - new_w // 2, avail.right() - new_w + 1))
                ny = max(avail.top(), min(cy - new_h // 2, avail.bottom() - new_h + 1))
                self.setGeometry(nx, ny, new_w, new_h)

            if hasattr(self, '_ensure_border_overlay'):
                self._ensure_border_overlay()
            self._update_responsive_layout()
        finally:
            self.setUpdatesEnabled(True)
            if was_visible:
                self.update()
            self._rebuilding_scale = False

    def _compute_ideal_sidebar_width(self) -> int:
        min_w = config.S(212)
        max_w = config.S(320)
        if not hasattr(self, 'category_list'):
            return min_w
        fm = QFontMetrics(self.category_list.font())
        longest = 0
        for i in range(self.category_list.count()):
            it = self.category_list.item(i)
            if it is not None and not it.isHidden():
                longest = max(longest, fm.horizontalAdvance(it.text()))
        if longest <= 0:
            return min_w
        return max(min_w, min(max_w, longest + config.S(64)))

    def _update_responsive_layout(self):
        if not hasattr(self, 'left_panel') or self.left_panel is None:
            return
        min_w = config.S(212)
        ideal_w = self._compute_ideal_sidebar_width()
        if self.isMaximized() or self.isFullScreen() or self.width() >= config.S(960):
            target_w = ideal_w
        elif self.width() <= config.SETTINGS_WINDOW_W:
            target_w = min_w
        else:
            span = max(1, config.S(960) - config.SETTINGS_WINDOW_W)
            t = min(1.0, max(0.0, (self.width() - config.SETTINGS_WINDOW_W) / float(span)))
            target_w = int(round(min_w + (ideal_w - min_w) * t))
        if self.left_panel.width() != target_w:
            self.left_panel.setFixedWidth(target_w)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get_info_icon(self, info_key):
        main_win = self._get_main_window()
        tip_widget = getattr(main_win, 'shared_tooltip', None) if main_win else None
        return create_info_icon(
            info_key,
            txt_fn=self.txt if hasattr(self, 'txt') else None,
            tooltip_widget=tip_widget,
            parent=self,
        )

    def _open_external_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _open_local_path(self, path: str):
        if not path:
            return
        try:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
                if getattr(self.engine.os_doc, 'is_win', False):
                    os.startfile(path)
                elif getattr(self.engine.os_doc, 'is_mac', False):
                    import subprocess
                    subprocess.Popen(['open', path])
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', path])
        except Exception:
            pass

    def _register_search_entry(
        self,
        page_idx: int,
        widget: QWidget,
        title_key: str = "",
        desc_key: str = "",
        section_key: str = "",
        tab_key: str = "",
        is_advanced: bool = False,
        title_override: tuple[str, str] = None,
        desc_override: tuple[str, str] = None,
        options_keys: list[str] = None,
        options_static: list[str] = None,
        keywords_en: str = "",
    ):
        """Registers an option/section in the unified search index (active lang + English only)."""
        if title_override:
            title_loc, title_en = title_override
        else:
            title_loc = self.txt(title_key) if title_key else ""
            title_en = self._en(title_key) if title_key else ""

        if desc_override:
            desc_loc, desc_en = desc_override
        elif desc_key:
            desc_loc = self.txt(desc_key)
            desc_en = self._en(desc_key)
        else:
            desc_loc, desc_en = "", ""

        tab_loc = self.txt(tab_key) if tab_key else ""
        tab_en = self._en(tab_key) if tab_key else ""
        sec_loc = self.txt(section_key) if section_key else ""
        sec_en = self._en(section_key) if section_key else ""

        cat_loc = f"{tab_loc} › {sec_loc}" if (tab_loc and sec_loc) else (tab_loc or sec_loc)
        cat_en = f"{tab_en} › {sec_en}" if (tab_en and sec_en) else (tab_en or sec_en)

        opts_loc = [self.txt(ok) for ok in (options_keys or [])] + list(options_static or [])
        opts_en = [self._en(ok) for ok in (options_keys or [])] + list(options_static or [])

        self._search_entries.append({
            "page_idx": page_idx,
            "widget": widget,
            "is_advanced": bool(is_advanced),
            "title_loc": title_loc,
            "title_en": title_en,
            "desc_loc": desc_loc,
            "desc_en": desc_en,
            "category_loc": cat_loc,
            "category_en": cat_en,
            "options_loc": opts_loc,
            "options_en": opts_en,
            "keywords_en": keywords_en,
        })

    # ── Brave-Style Ranked Search & Navigation ────────────────────────────

    def open_section(self, section_id: str):
        """Navigates cleanly to a named section (e.g. 'custom_markers', 'shortcuts', 'support') and highlights it."""
        if hasattr(self, "search_edit") and self.search_edit.text().strip():
            self.search_edit.clear()
        self._ensure_all_pages_built()
        if section_id == "custom_markers":
            self.category_list.setCurrentRow(self.TAB_MARKERS)
            self.stack.setCurrentIndex(self.TAB_MARKERS)
            self.w_footer.show()
            if getattr(self, "markers_card", None) is not None:
                self._navigate_to_target(self.TAB_MARKERS, self.markers_card)
        elif section_id == "shortcuts":
            self._navigate_to_target(self.TAB_SHORTCUTS, getattr(self, "_sc_markers_card", None))
        elif section_id == "support":
            self.category_list.setCurrentRow(self.TAB_SUPPORT)
            self.stack.setCurrentIndex(self.TAB_SUPPORT)
            self.w_footer.hide()
        elif section_id == "about":
            self.category_list.setCurrentRow(self.TAB_ABOUT)
            self.stack.setCurrentIndex(self.TAB_ABOUT)
            self.w_footer.show()

    def _navigate_to_target(self, page_idx: int, target_widget: QWidget = None):
        """Clears search if needed, switches to page_idx, centers target_widget vertically, and flashes green."""
        if getattr(self, "_is_basic_mode", True) and page_idx == self.TAB_AI_ENGINE:
            self._set_view_mode("advanced")

        if hasattr(self, "_search_debounce_timer"):
            self._search_debounce_timer.stop()

        if hasattr(self, "search_edit") and self.search_edit.text():
            self.search_edit.line_edit.blockSignals(True)
            self.search_edit.line_edit.clear()
            self.search_edit.btn_clear.hide()
            self.search_edit.line_edit.blockSignals(False)

        self._ensure_page_built(page_idx)
        self.category_list.setCurrentRow(page_idx)
        self.stack.setCurrentIndex(page_idx)
        self._sync_footer_for_page(page_idx)

        scroll = self.stack.widget(page_idx)
        if target_widget is not None and isinstance(scroll, QScrollArea):
            def _scroll_and_flash():
                try:
                    content_w = scroll.widget()
                    vp = scroll.viewport()
                    sb = scroll.verticalScrollBar()
                    if content_w is not None and content_w.layout():
                        content_w.layout().activate()
                    if content_w is not None and vp is not None and sb is not None:
                        pos_in_content = target_widget.mapTo(content_w, QPoint(0, 0))
                        center_y = pos_in_content.y() + (target_widget.height() // 2)
                        target_y = max(0, min(sb.maximum(), center_y - (vp.height() // 2)))
                        sb.setValue(target_y)
                    else:
                        scroll.ensureWidgetVisible(target_widget, 0, config.S(60))
                    if hasattr(target_widget, "flash_highlight"):
                        target_widget.flash_highlight()
                    else:
                        p = target_widget.parentWidget()
                        while p is not None and p is not scroll:
                            if hasattr(p, "flash_highlight"):
                                p.flash_highlight()
                                break
                            p = p.parentWidget()
                except RuntimeError:
                    pass
            QTimer.singleShot(0, _scroll_and_flash)

    def _sync_footer_for_page(self, idx: int):
        if not hasattr(self, "w_footer"):
            return
        if idx == self.TAB_SUPPORT:
            self.w_footer.hide()
        else:
            self.w_footer.show()

    def _on_search_query_changed(self, text: str):
        query = text.strip()
        if not query:
            if hasattr(self, "_search_debounce_timer"):
                self._search_debounce_timer.stop()
            # Return cleanly to currently selected category without hiding anything
            curr = self.category_list.currentRow()
            if curr < 0 or curr >= self.TAB_ABOUT + 1:
                curr = 0
                self.category_list.setCurrentRow(0)
            self._ensure_page_built(curr)
            self.stack.setCurrentIndex(curr)
            self._sync_footer_for_page(curr)
            return

        if hasattr(self, "_search_debounce_timer"):
            self._search_debounce_timer.start()
        else:
            self._execute_pending_search()

    def _execute_pending_search(self):
        if hasattr(self, "_search_debounce_timer"):
            self._search_debounce_timer.stop()
        query = self.search_edit.text().strip() if hasattr(self, "search_edit") else ""
        if not query:
            return
        self._ensure_all_pages_built()
        self.stack.setCurrentIndex(self.STACK_SEARCH_IDX)
        self.w_footer.show()
        self._render_search_results(query)

    def _render_search_results(self, query: str):
        container = getattr(self, "_search_results_container", None)
        lay = getattr(self, "_search_results_layout", None)
        if container is None or lay is None:
            return

        container.setUpdatesEnabled(False)
        try:
            self._render_search_results_inner(query, container, lay)
        finally:
            container.setUpdatesEnabled(True)

    def _render_search_results_inner(self, query: str, container, lay):
        while lay.count() > 0:
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        gui_lang = self._active_lang()
        visible_hits = []
        hidden_adv_hits = []

        for entry in self._search_entries:
            score, via_en, en_snip = score_search_entry(query, entry, gui_lang)
            if score <= 0:
                continue
            item_tuple = (score, via_en, en_snip, entry)
            if entry["is_advanced"] and self._is_basic_mode:
                hidden_adv_hits.append(item_tuple)
            else:
                visible_hits.append(item_tuple)

        # Also search dynamic custom markers by name & shortcut!
        for idx, m in enumerate(getattr(self, "current_custom_markers", [])):
            name = m.get("name", "")
            color = m.get("color", "")
            color_loc = self.txt(f"resolve_color_{color.lower()}") if color else ""
            s_key = f"custom_marker_{name}"
            sc_seq = self._pending_shortcuts.get(s_key, "")
            dyn_entry = {
                "page_idx": self.TAB_MARKERS,
                "widget": getattr(self, "markers_card", None),
                "is_advanced": False,
                "title_loc": name,
                "title_en": name,
                "desc_loc": f"{self.txt('search_marker_label')} · {color_loc}" + (f" · {sc_seq}" if sc_seq else ""),
                "desc_en": f"Custom Marker · {color}" + (f" · {sc_seq}" if sc_seq else ""),
                "category_loc": self.txt('tab_custom_markers'),
                "category_en": "Custom Markers",
                "options_loc": [color_loc, sc_seq],
                "options_en": [color, sc_seq],
                "keywords_en": "custom marker color tag",
            }
            sc, via_en, en_snip = score_search_entry(query, dyn_entry, gui_lang)
            if sc > 0:
                visible_hits.append((sc, via_en, en_snip, dyn_entry))

        visible_hits.sort(key=lambda x: (-x[0], x[3].get("page_idx", 0), x[3].get("title_loc", "")))
        hidden_adv_hits.sort(key=lambda x: (-x[0], x[3].get("page_idx", 0), x[3].get("title_loc", "")))

        # Page header
        count_n = len(visible_hits)
        if count_n == 1:
            sub_txt = self.txt("search_results_count_one")
        elif count_n > 1:
            sub_txt = self.txt("search_results_count", count=count_n)
        else:
            sub_txt = ""
        lay.addWidget(SettingsPageHeader(self.txt("search_results_title"), sub_txt, parent=container))
        lay.addSpacing(config.S(6))

        if not visible_hits:
            empty_card = SettingsCard(parent=container)
            empty_w = QWidget(empty_card)
            scope_transparent(empty_w)
            el = QVBoxLayout(empty_w)
            el.setContentsMargins(config.S(24), config.S(28), config.S(24), config.S(28))
            el.setSpacing(config.S(10))

            ic = QLabel(empty_w)
            ic.setFixedSize(config.S(36), config.S(36))
            ic.setAlignment(Qt.AlignCenter)
            ic.setPixmap(get_svg_icon(SVG_SEARCH_EMPTY, size=32).pixmap(config.S(32), config.S(32)))
            scope_transparent(ic)
            el.addWidget(ic, 0, Qt.AlignCenter)

            lbl_empty_title = QLabel(self.txt("search_no_results_title", query=query), empty_w)
            lbl_empty_title.setWordWrap(True)
            lbl_empty_title.setAlignment(Qt.AlignCenter)
            lbl_empty_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            lbl_empty_title.setStyleSheet(
                f"color: #ffffff; font-size: {config.FS_PX(11.5)}px; font-weight: bold; background: transparent; padding: {config.S(2)}px 0px;"
            )
            el.addWidget(lbl_empty_title)

            lbl_empty_hint = QLabel(self.txt("search_no_results_hint"), empty_w)
            lbl_empty_hint.setWordWrap(True)
            lbl_empty_hint.setAlignment(Qt.AlignCenter)
            lbl_empty_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
            lbl_empty_hint.setStyleSheet(
                f"color: #8f8f8f; font-size: {config.FS_PX(9.5)}px; background: transparent; padding-bottom: {config.S(4)}px;"
            )
            el.addWidget(lbl_empty_hint)

            btn_row = QHBoxLayout()
            btn_row.setSpacing(config.S(8))
            btn_row.setAlignment(Qt.AlignCenter)

            btn_clr = QPushButton(self.txt("btn_clear_search"), empty_w)
            btn_clr.setObjectName("btn_secondary")
            btn_clr.setFixedHeight(config.S(30))
            btn_clr.setCursor(Qt.PointingHandCursor)
            btn_clr.clicked.connect(self.search_edit.clear)
            btn_row.addWidget(btn_clr)

            if hidden_adv_hits:
                btn_adv = QPushButton(self.txt("btn_switch_advanced_results"), empty_w)
                btn_adv.setObjectName("btn_apply")
                btn_adv.setFixedHeight(config.S(30))
                btn_adv.setCursor(Qt.PointingHandCursor)
                btn_adv.clicked.connect(self._switch_to_advanced_and_refresh_search)
                btn_row.addWidget(btn_adv)

            el.addSpacing(config.S(4))
            el.addLayout(btn_row)
            empty_card.add_content_widget(empty_w, margins=(0, 0, 0, 0))
            lay.addWidget(empty_card)
            empty_w.updateGeometry()
            empty_card.updateGeometry()

        for _score, via_en, en_snip, entry in visible_hits:
            t_html = highlight_text_html(entry["title_loc"], query, fg_color="#f2f2f2")
            d_txt = entry.get("desc_loc", "")
            d_html = highlight_text_html(d_txt, query, fg_color="#a0a0a0") if d_txt else ""
            en_hint_html = ""
            if via_en and en_snip:
                en_pfx = self.txt("search_en_match_prefix")
                en_hint_html = f'<span style="color: #777777;">{en_pfx} </span>' + highlight_text_html(en_snip, query, fg_color="#a8a8a8")
            else:
                q_fold = fold_accents(query)
                title_desc_fold = fold_accents(entry.get("title_loc", "") + " " + entry.get("desc_loc", ""))
                if q_fold and q_fold not in title_desc_fold:
                    matched_opt = next((o for o in entry.get("options_loc", []) if q_fold in fold_accents(o)), "")
                    if matched_opt:
                        en_hint_html = highlight_text_html(matched_opt, query, fg_color="#a8a8a8")
                    elif en_snip:
                        en_pfx = self.txt("search_en_match_prefix")
                        en_hint_html = f'<span style="color: #777777;">{en_pfx} </span>' + highlight_text_html(en_snip, query, fg_color="#a8a8a8")

            badge = self.txt("btn_view_advanced") if entry.get("is_advanced") else ""
            card = SearchResultCard(
                title_html=t_html,
                category_text=entry.get("category_loc", ""),
                desc_html=d_html,
                en_hint_html=en_hint_html,
                badge_text=badge,
                parent=container,
            )
            p_idx = entry["page_idx"]
            target_w = entry["widget"]
            card.clicked.connect(lambda pi=p_idx, tw=target_w: self._navigate_to_target(pi, tw))
            lay.addWidget(card)

        if visible_hits and hidden_adv_hits:
            adv_banner = QFrame(container)
            adv_banner.setStyleSheet(
                f"QFrame {{ background-color: #1c2420; border: 1px solid #2b4536; border-radius: {config.S(8)}px; }}"
            )
            bl = QHBoxLayout(adv_banner)
            bl.setContentsMargins(config.S(14), config.S(10), config.S(14), config.S(10))
            bl.setSpacing(config.S(10))
            lbl_adv = QLabel(self.txt("search_hidden_advanced_notice", count=len(hidden_adv_hits)), adv_banner)
            lbl_adv.setWordWrap(True)
            lbl_adv.setStyleSheet(f"color: #b7dfc6; font-size: {config.FS_PX(9.3)}px; background: transparent; border: none;")
            bl.addWidget(lbl_adv, 1)

            btn_sw = QPushButton(self.txt("btn_switch_advanced_results"), adv_banner)
            btn_sw.setObjectName("btn_apply")
            btn_sw.setFixedHeight(config.S(28))
            btn_sw.setCursor(Qt.PointingHandCursor)
            btn_sw.clicked.connect(self._switch_to_advanced_and_refresh_search)
            bl.addWidget(btn_sw)
            lay.addSpacing(config.S(6))
            lay.addWidget(adv_banner)

        lay.addStretch(1)
        if hasattr(self, "_search_scroll") and self._search_scroll is not None:
            self._search_scroll.verticalScrollBar().setValue(0)

    def _switch_to_advanced_and_refresh_search(self):
        self._set_view_mode("advanced")
        if hasattr(self, "search_edit") and self.search_edit.text().strip():
            self._render_search_results(self.search_edit.text().strip())

    # ── View Mode (Basic vs Advanced) ─────────────────────────────────────

    def _set_view_mode(self, mode):
        self.setUpdatesEnabled(False)
        try:
            self.engine.save_preferences({'settings_view_mode': mode})
            if hasattr(self, '_initial_state'):
                self._initial_state['settings_view_mode'] = mode
                for k, def_v in config.DEFAULT_SETTINGS.items():
                    if k not in self._initial_state:
                        self._initial_state[k] = def_v

            self._is_basic_mode = (mode == 'basic')

            if hasattr(self, 'category_list') and self.category_list.count() > self.TAB_AI_ENGINE:
                item = self.category_list.item(self.TAB_AI_ENGINE)
                if item:
                    item.setHidden(self._is_basic_mode)
                if self._is_basic_mode and self.category_list.currentRow() == self.TAB_AI_ENGINE:
                    self.category_list.setCurrentRow(0)

            if hasattr(self, 'btn_view_basic') and hasattr(self, 'btn_view_advanced'):
                if self._is_basic_mode:
                    self.btn_view_basic.setStyleSheet(self.active_btn_style)
                    self.btn_view_advanced.setStyleSheet(self.inactive_btn_style)
                else:
                    self.btn_view_basic.setStyleSheet(self.inactive_btn_style)
                    self.btn_view_advanced.setStyleSheet(self.active_btn_style)

            if hasattr(self, '_advanced_widgets'):
                for w in self._advanced_widgets:
                    if w:
                        w.setVisible(not self._is_basic_mode)
            self._update_responsive_layout()
        finally:
            self.setUpdatesEnabled(True)

    def setVisible(self, visible: bool):
        if visible and getattr(self, '_reopen_maximized', False):
            self._reopen_maximized = False
            self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowMaximized)
        super().setVisible(visible)

    def present(self):
        """Shows SettingsDialog cleanly, preserving maximized/fullscreen state across platforms."""
        if getattr(self, '_is_mac', False):
            main_is_fs = bool(self._main_window and getattr(self._main_window, 'isFullScreen', lambda: False)())
            is_top = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
            if main_is_fs and not is_top:
                self._reopen_maximized = False
                self.show()
                if not self.isFullScreen():
                    self.showFullScreen()
            else:
                if getattr(self, '_reopen_maximized', False) or self.isMaximized():
                    self._reopen_maximized = False
                    self.showMaximized()
                else:
                    if self.isFullScreen():
                        self.showNormal()
                    self.show()
                    if self.isMinimized():
                        self.showNormal()
            self.raise_()
            self.activateWindow()
            return

        if getattr(self, '_reopen_maximized', False) or self.isMaximized():
            self._reopen_maximized = False
            self.showMaximized()
        else:
            self.show()
            if self.isMinimized():
                self.showNormal()
        self.raise_()
        self.activateWindow()

    def _reset_hidden_maximized_state(self):
        """Clears cached Qt/Win32 maximized state while hidden so next maximized open recomputes clean client bounds."""
        if self.isVisible() or getattr(self, '_is_mac', False):
            return
        try:
            if self.windowState() & Qt.WindowMaximized:
                self.setWindowState(self.windowState() & ~Qt.WindowMaximized)
        except Exception:
            pass
        if getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
            try:
                from gui.components.mixins import _get_win32_apis
                user32, _, _ = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd:
                    GWL_STYLE = -16
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    if style & 0x01000000:  # WS_MAXIMIZE
                        user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~0x01000000)
                    target_size = getattr(self, '_default_normal_size', None) or QSize(config.SETTINGS_WINDOW_W, config.SETTINGS_WINDOW_H)
                    w = max(config.S(640), int(target_size.width()))
                    h = max(config.S(460), int(target_size.height()))
                    scr = self.screen() or QApplication.primaryScreen()
                    if scr:
                        avail = scr.availableGeometry()
                        x = avail.x() + max(0, (avail.width() - w) // 2)
                        y = avail.y() + max(0, (avail.height() - h) // 2)
                    else:
                        x, y = 100, 100
                    user32.SetWindowPos(hwnd, None, x, y, w, h, 0x0004 | 0x0010 | 0x0020)
            except Exception:
                pass

    def _post_show_layout_sync(self):
        if not self.isVisible():
            return
        self._update_responsive_layout()
        self._update_border_overlay()
        self._update_grips()
        self._refresh_max_state()
        if getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
            try:
                hwnd = int(self.winId())
                if hwnd:
                    self._enforce_win_dwm_attributes(hwnd, include_extend=True)
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_native_always_on_top()
        track_window_screen(self)
        self._ensure_screen_scale_tracking()
        if hasattr(self, '_ensure_page_built') and hasattr(self, 'category_list'):
            for i in range(self.category_list.count()):
                self._ensure_page_built(i)
        self._update_responsive_layout()
        self._refresh_max_state()
        tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
        if tb:
            for btn_name in ('btn_close', 'btn_max', 'btn_min'):
                btn = getattr(tb, btn_name, None)
                if btn and hasattr(btn, 'reset_state'):
                    btn.reset_state()

        self._initial_state = self._get_current_state_dict()
        QTimer.singleShot(0, self._post_show_layout_sync)
        self.raise_()
        self.activateWindow()

    def _ensure_screen_scale_tracking(self):
        """Hooks windowHandle().screenChanged on SettingsDialog for multi-DPI screen transitions."""
        if getattr(self, '_scale_screen_tracked', False):
            return
        handle = self.windowHandle() if hasattr(self, 'windowHandle') else None
        if not handle:
            return
        self._scale_screen_tracked = True
        if not hasattr(self, '_screen_scale_timer') or self._screen_scale_timer is None:
            self._screen_scale_timer = QTimer(self)
            self._screen_scale_timer.setSingleShot(True)
            self._screen_scale_timer.setInterval(120)
            self._screen_scale_timer.timeout.connect(self._on_settings_screen_settled)

        def _schedule(_=None):
            if hasattr(self, '_screen_scale_timer') and self._screen_scale_timer is not None:
                self._screen_scale_timer.start()

        handle.screenChanged.connect(lambda _s: _schedule())

    def _on_settings_screen_settled(self):
        main_win = self._get_main_window()
        if main_win is not None and hasattr(main_win, '_on_screen_scale_settled'):
            main_win._on_screen_scale_settled()
            return
        scr = (self.windowHandle().screen() if self.windowHandle() else None) or self.screen()
        if scr is None:
            return
        mode = getattr(self, '_ui_scale_mode', 'auto')
        old_factor = config.SCALE_FACTOR
        old_os = config.OS_SCALE_PERCENT
        new_os = config.detect_os_scale_pct(scr)
        pct = self._safe_get('slider_ui_scale', new_os, 'value')
        config.apply_ui_scaling(mode=mode, pct=(None if mode == 'auto' else pct), screen=scr)
        if abs(config.SCALE_FACTOR - old_factor) >= 0.01:
            self.rebuild_ui_for_scale()
        elif mode == 'auto' and new_os != old_os:
            self.sync_auto_os_scale_display(new_os)

    # ── UI / Pages Bootstrap ──────────────────────────────────────────────

    def _build_ui(self):
        self.setUpdatesEnabled(False)
        try:
            self._advanced_widgets = []
            self._search_entries = []
            self.category_list.clear()
            while self.stack.count() > 0:
                w = self.stack.widget(0)
                self.stack.removeWidget(w)
                w.deleteLater()

            prefs = self.engine.load_preferences() or {}
            view_mode = prefs.get('settings_view_mode', 'basic')
            self._is_basic_mode = (view_mode == 'basic')

            self.current_custom_markers = list(prefs.get('custom_markers', []))
            default_sc = dict(getattr(config, 'DEFAULT_SETTINGS', {}).get('shortcuts', {}))
            saved_sc = prefs.get('shortcuts', {}) or {}
            self._pending_shortcuts = {k: saved_sc.get(k, v) for k, v in default_sc.items()}
            for m in self.current_custom_markers:
                m_name = m.get('name', '')
                if m_name:
                    sk = f'custom_marker_{m_name}'
                    self._pending_shortcuts[sk] = saved_sc.get(sk, '')

            self.category_list.addItem(self.txt("tab_general"))         # 0
            self.category_list.addItem(self.txt("tab_appearance"))      # 1
            self.category_list.addItem(self.txt("tab_editor"))          # 2
            self.category_list.addItem(self.txt("tab_davinci"))         # 3
            self.category_list.addItem(self.txt("tab_shortcuts"))       # 4
            self.category_list.addItem(self.txt("tab_custom_markers"))  # 5
            self.category_list.addItem(self.txt("tab_ai_engine"))       # 6
            self.category_list.addItem(self.txt("tab_support"))         # 7
            self.category_list.addItem(self.txt("tab_about"))           # 8

            if self._is_basic_mode:
                item = self.category_list.item(self.TAB_AI_ENGINE)
                if item:
                    item.setHidden(True)

            self.revert_funcs = []

            for _ in range(self.category_list.count()):
                scroll = QScrollArea()
                scroll.setObjectName("SettingsTabScroll")
                scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.NoFrame)
                scroll.setStyleSheet(f"QScrollArea#SettingsTabScroll {{ background-color: {SETTINGS_VIEWPORT_BG}; border: none; }}")
                if scroll.viewport():
                    scroll.viewport().setObjectName("SettingsScrollViewport")
                    scroll.viewport().setStyleSheet(f"#SettingsScrollViewport {{ background-color: {SETTINGS_VIEWPORT_BG}; }}")
                self.stack.addWidget(scroll)

            # Dedicated Search Results page at stack index STACK_SEARCH_IDX (8)
            self._search_scroll = QScrollArea()
            self._search_scroll.setObjectName("SettingsSearchScroll")
            self._search_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self._search_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self._search_scroll.setWidgetResizable(True)
            self._search_scroll.setFrameShape(QFrame.NoFrame)
            self._search_scroll.setStyleSheet(f"QScrollArea#SettingsSearchScroll {{ background-color: {SETTINGS_VIEWPORT_BG}; border: none; }}")
            if self._search_scroll.viewport():
                self._search_scroll.viewport().setObjectName("SettingsSearchViewport")
                self._search_scroll.viewport().setStyleSheet(f"#SettingsSearchViewport {{ background-color: {SETTINGS_VIEWPORT_BG}; }}")

            self._search_results_container = QWidget()
            scope_transparent(self._search_results_container, border_none=False)
            self._search_results_layout = QVBoxLayout(self._search_results_container)
            self._search_results_layout.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
            self._search_results_layout.setSpacing(config.S(8))
            self._search_scroll.setWidget(_CenteredPageHost(self._search_results_container, config.S(660), parent=self._search_scroll))
            self.stack.addWidget(self._search_scroll)

            self._built_pages = set()

            def _ensure_page_built(idx):
                if idx not in self._built_pages and 0 <= idx < self.category_list.count():
                    self._build_page(idx)
                    self._built_pages.add(idx)

            self._ensure_page_built = _ensure_page_built

            def _ensure_all_pages_built():
                for i in range(self.category_list.count()):
                    self._ensure_page_built(i)

            self._ensure_all_pages_built = _ensure_all_pages_built

            # Lazy-load: build page 0 immediately so dialog opens in < 3ms
            self._ensure_page_built(0)

            def _build_remaining():
                for i in range(1, self.category_list.count()):
                    self._ensure_page_built(i)
            QTimer.singleShot(10, _build_remaining)

            if hasattr(self, '_advanced_widgets'):
                for w in self._advanced_widgets:
                    if w:
                        w.setVisible(not self._is_basic_mode)

            def _on_tab_changed(idx):
                if hasattr(self, 'search_edit') and self.search_edit.text().strip():
                    self.search_edit.clear()
                self._ensure_page_built(idx)
                self.stack.setCurrentIndex(idx)
                self._sync_footer_for_page(idx)

            def _on_cat_clicked(item):
                if hasattr(self, 'search_edit') and self.search_edit.text().strip():
                    row = self.category_list.row(item)
                    self.search_edit.clear()
                    if 0 <= row < self.category_list.count():
                        self._ensure_page_built(row)
                        self.stack.setCurrentIndex(row)
                        self._sync_footer_for_page(row)

            self.category_list.currentRowChanged.connect(_on_tab_changed)
            self.category_list.itemClicked.connect(_on_cat_clicked)

            self.category_list.setCurrentRow(0)
            self._initial_state = self._get_current_state_dict()
        finally:
            self.setUpdatesEnabled(True)

    # ── Unified Card Row Builder ──────────────────────────────────────────

    def _add_card_row(
        self,
        card: SettingsCard,
        label_key: str,
        widget: QWidget,
        default_val,
        setter_func,
        info_key: str = None,
        is_advanced: bool = False,
        add_divider_above: bool = True,
        min_widget_w: int = None,
        max_widget_w: int = None,
        section_key: str = "",
        tab_key: str = "",
        options_keys: list[str] = None,
        options_static: list[str] = None,
        keywords_en: str = "",
        show_revert: bool = True,
    ) -> SettingsRowWidget:
        """
        Adds a uniform option row inside *card* with left label, consistent right-aligned
        control + optional (i) info icon immediately left of control + optional revert button,
        optional hairline divider above, and search registration.
        """
        divider = None
        if add_divider_above and card._lay.count() > 0:
            divider = card.add_divider()

        row_frame = SettingsRowWidget(card)
        hl = QHBoxLayout(row_frame)
        hl.setContentsMargins(config.S(16), config.S(11), config.S(14), config.S(11))
        hl.setSpacing(config.S(12))

        label_text = self.txt(label_key)
        lbl = QLabel(label_text, row_frame)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: #e4e4e4; font-size: {config.FS_PX(10)}px; background: transparent; border: none;")
        hl.addWidget(lbl, 1)

        container = QWidget(row_frame)
        scope_transparent(container)
        ctrl_lay = QHBoxLayout(container)
        ctrl_lay.setContentsMargins(0, 0, 0, 0)
        has_toggle = (
            isinstance(widget, ToggleSwitch)
            or widget.findChild(ToggleSwitch) is not None
            or isinstance(widget, AssemblyModeSelector)
            or widget.findChild(AssemblyModeSelector) is not None
        )
        ctrl_lay.setSpacing(config.S(8) if has_toggle else config.S(6))
        ctrl_lay.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        if info_key:
            ctrl_lay.addWidget(self._get_info_icon(info_key))

        if not has_toggle:
            if min_widget_w is None and max_widget_w is None:
                fixed_ctrl_w = config.S(220)
                widget.setFixedWidth(fixed_ctrl_w)
                widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            else:
                widget.setMinimumWidth(min_widget_w if min_widget_w is not None else config.S(160))
                widget.setMaximumWidth(max_widget_w if max_widget_w is not None else config.S(220))
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        ctrl_lay.addWidget(widget)

        if show_revert:
            btn_rev = ReloadButton(size=28, parent=container)
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            btn_rev.clicked.connect(lambda _c=False, s=setter_func, d=default_val: s(d))
            ctrl_lay.addWidget(btn_rev)
            self.revert_funcs.append(lambda d=default_val, s=setter_func: s(d))

        hl.addWidget(container, 0)
        card._lay.addWidget(row_frame)

        curr_page_idx = getattr(self, '_current_building_page_idx', 0)
        self._register_search_entry(
            page_idx=curr_page_idx,
            widget=row_frame,
            title_key=label_key,
            desc_key=info_key or "",
            section_key=section_key,
            tab_key=tab_key,
            is_advanced=is_advanced,
            options_keys=options_keys,
            options_static=options_static,
            keywords_en=keywords_en,
        )

        if is_advanced:
            self._advanced_widgets.append(row_frame)
            if divider is not None:
                self._advanced_widgets.append(divider)
            if getattr(self, '_is_basic_mode', True):
                row_frame.setVisible(False)
                if divider is not None:
                    divider.setVisible(False)

        row_frame._label_widget = lbl
        row_frame._ctrl_container = container
        row_frame._divider_widget = divider
        return row_frame

    def _build_page(self, idx):
        if idx < 0 or idx >= self.category_list.count():
            return
        scroll = self.stack.widget(idx)
        prefs = self.engine.load_preferences() or {}

        mapping = {
            self.TAB_GENERAL: 'general',
            self.TAB_APPEARANCE: 'appearance',
            self.TAB_EDITOR: 'editor',
            self.TAB_DAVINCI: 'davinci',
            self.TAB_SHORTCUTS: 'shortcuts',
            self.TAB_MARKERS: 'custom_markers',
            self.TAB_AI_ENGINE: 'ai_engine',
            self.TAB_SUPPORT: 'support',
            self.TAB_ABOUT: 'about',
        }
        page_name = mapping.get(idx)
        if not page_name:
            return
        method = getattr(self, f"_build_page_{page_name}", None)
        if method:
            page_widget = method(prefs)
            if page_widget:
                max_content_w = config.S(660)
                scroll.setWidget(_CenteredPageHost(page_widget, max_content_w, parent=scroll))

    # ── PAGE 0: GENERAL ───────────────────────────────────────────────────

    def _build_page_general(self, prefs):
        self._current_building_page_idx = self.TAB_GENERAL
        page_gen = QWidget()
        scope_transparent(page_gen, border_none=False)
        l_gen = QVBoxLayout(page_gen)
        l_gen.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_gen.setSpacing(config.S(14))

        # Basic / Advanced view switch (preserved cleanly at top as liked by PO)
        view_btn_row = QHBoxLayout()
        view_btn_row.setContentsMargins(0, 0, 0, config.S(2))
        view_btn_row.setSpacing(config.S(10))

        self.btn_view_basic = QPushButton(self.txt("btn_view_basic"))
        self.btn_view_basic.setFixedHeight(config.S(30))
        self.btn_view_basic.setCursor(Qt.PointingHandCursor)
        self.active_btn_style = (
            f"background-color: #1b8745; color: white; border: 1px solid #125c2f; "
            f"border-radius: {config.S(5)}px; font-weight: bold; font-size: {config.FS_PX(10)}px;"
        )
        self.inactive_btn_style = (
            f"background-color: {SETTINGS_CARD_BG}; color: #8c8c8c; border: 1px solid {SETTINGS_CARD_BORDER}; "
            f"border-radius: {config.S(5)}px; font-weight: normal; font-size: {config.FS_PX(10)}px;"
        )
        self.btn_view_basic.setStyleSheet(self.active_btn_style if self._is_basic_mode else self.inactive_btn_style)
        self.btn_view_basic.clicked.connect(lambda: self._set_view_mode('basic'))

        self.btn_view_advanced = QPushButton(self.txt("btn_view_advanced"))
        self.btn_view_advanced.setFixedHeight(config.S(30))
        self.btn_view_advanced.setCursor(Qt.PointingHandCursor)
        self.btn_view_advanced.setStyleSheet(self.active_btn_style if not self._is_basic_mode else self.inactive_btn_style)
        self.btn_view_advanced.clicked.connect(lambda: self._set_view_mode('advanced'))

        view_btn_row.addWidget(self.btn_view_basic)
        view_btn_row.addWidget(self.btn_view_advanced)
        l_gen.addLayout(view_btn_row)

        self._register_search_entry(
            self.TAB_GENERAL, self.btn_view_advanced,
            title_key="lbl_view_mode", tab_key="tab_general",
            options_keys=["btn_view_basic", "btn_view_advanced"],
            keywords_en="basic advanced view mode settings",
        )

        # ── Version / Update card ─────────────────────────────────────────
        ver_card = SettingsCard(parent=page_gen)
        ver_top = QWidget(ver_card)
        scope_transparent(ver_top)
        ver_row = QHBoxLayout(ver_top)
        ver_row.setContentsMargins(config.S(16), config.S(12), config.S(16), config.S(12))
        ver_row.setSpacing(config.S(8))

        lbl_ver_key = QLabel(self.txt("lbl_ver_installed") + ":", ver_top)
        lbl_ver_key.setStyleSheet(f"color: #909090; font-size: {config.FS_PX(9.5)}px; background: transparent;")
        lbl_ver_val = QLabel(config.VERSION, ver_top)
        lbl_ver_val.setStyleSheet(f"color: #ffffff; font-size: {config.FS_PX(11)}px; font-weight: bold; background: transparent;")
        self._lbl_ver_icon = QLabel(ver_top)
        self._lbl_ver_icon.setFixedSize(config.S(14), config.S(14))
        self._lbl_ver_icon.setAlignment(Qt.AlignCenter)
        self._lbl_ver_icon.setPixmap(get_vector_pixmap("check", size=config.S(12), color="#39ff7a"))
        scope_transparent(self._lbl_ver_icon)
        self._lbl_ver_icon.hide()

        self._lbl_ver_status = QLabel("...", ver_top)
        self._lbl_ver_status.setStyleSheet(f"color: #777777; font-size: {config.FS_PX(9)}px; background: transparent;")
        self._btn_ver_check = QPushButton(self.txt("btn_check_updates_now"), ver_top)
        self._btn_ver_check.setObjectName("btn_ghost_sm")
        self._btn_ver_check.setStyleSheet(f"padding: {config.S(3)}px {config.S(10)}px; font-size: {config.FS_PX(9)}px;")
        self._btn_ver_check.setCursor(Qt.PointingHandCursor)
        self._btn_ver_check.hide()

        self._btn_ver_update = QPushButton(self.txt("btn_settings_update_now"), ver_top)
        self._btn_ver_update.setObjectName("btn_ghost_sm")
        self._btn_ver_update.setStyleSheet(f"padding: {config.S(3)}px {config.S(10)}px; font-size: {config.FS_PX(9)}px;")
        self._btn_ver_update.setCursor(Qt.PointingHandCursor)
        self._btn_ver_update.hide()

        ver_row.addWidget(lbl_ver_key)
        ver_row.addWidget(lbl_ver_val)
        ver_row.addSpacing(config.S(10))
        ver_row.addWidget(self._lbl_ver_icon)
        ver_row.addWidget(self._lbl_ver_status)
        ver_row.addStretch()
        ver_row.addWidget(self._btn_ver_check)
        ver_row.addWidget(self._btn_ver_update)
        ver_card._lay.addWidget(ver_top)

        auto_check_on = bool(prefs.get('auto_check_updates', True))
        self.tgl_auto_check_updates = ToggleSwitch()
        self.tgl_auto_check_updates.setChecked(auto_check_on, animated=False)
        self._add_card_row(
            ver_card, "lbl_auto_check_updates", self.tgl_auto_check_updates,
            True, lambda v: self.tgl_auto_check_updates.setChecked(v, animated=True),
            info_key="tt_auto_check_updates", tab_key="tab_general",
            keywords_en="update version check notify", show_revert=False,
        )

        self.tgl_auto_update_on_start = ToggleSwitch()
        self.tgl_auto_update_on_start.setChecked(
            bool(prefs.get('auto_update_on_start', False)) if auto_check_on else False,
            animated=False,
        )
        self._row_auto_update_on_start = self._add_card_row(
            ver_card, "lbl_auto_update_on_start", self.tgl_auto_update_on_start,
            False, lambda v: self.tgl_auto_update_on_start.setChecked(v, animated=True),
            info_key="tt_auto_update_on_start", is_advanced=True, tab_key="tab_general",
            keywords_en="auto update startup silent", show_revert=False,
        )

        self._upd_dim_anim = QVariantAnimation(self)
        self._upd_dim_anim.setDuration(220)
        self._upd_dim_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._upd_dim_anim.valueChanged.connect(self._apply_auto_update_dim_opacity)
        self._curr_upd_op = 1.0

        def _on_auto_check_toggled(checked: bool):
            enabled = bool(checked)
            if not enabled:
                if self.tgl_auto_update_on_start.isChecked():
                    self.tgl_auto_update_on_start.setChecked(False, animated=True)
                self._update_auto_update_availability(False, animated=True)
                if not getattr(self._get_main_window(), '_pending_update_ver', None) and self._btn_ver_update.isHidden():
                    self._lbl_ver_icon.hide()
                    self._lbl_ver_status.setText(self.txt("msg_updates_disabled"))
                    self._lbl_ver_status.setStyleSheet(f"color: #888888; font-size: {config.FS_PX(9)}px; background: transparent;")
                    self._btn_ver_check.show()
            else:
                self._update_auto_update_availability(True, animated=True)
                self._btn_ver_check.hide()
                if self._lbl_ver_status.text() in (self.txt("msg_updates_disabled"), "..."):
                    self._run_ver_check(force_refresh=False)

        self.tgl_auto_check_updates.toggled.connect(_on_auto_check_toggled)
        self._update_auto_update_availability(auto_check_on, animated=False)

        l_gen.addWidget(ver_card)

        # Async update check wiring
        _card_engine = self.engine

        def _card_lang():
            p = _card_engine.load_preferences() or {}
            return p.get('gui_lang', 'en')

        def _on_update_known_for_card(latest_ver, gh_url, gl_url, release_notes=""):
            try:
                self._lbl_ver_icon.hide()
                self._btn_ver_check.hide()
                self._btn_ver_check.setEnabled(True)
                main_win = self._get_main_window()
                pending = getattr(main_win, '_pending_update_ver', None)
                if pending and pending == latest_ver:
                    self._lbl_ver_status.setText(self.txt('lbl_ver_pending_restart'))
                    self._lbl_ver_status.setStyleSheet(
                        f"color: #f4a641; font-size: {config.FS_PX(9)}px; font-weight: bold; background: transparent;"
                    )
                    self._btn_ver_update.hide()
                    return

                self._lbl_ver_status.setText(f"{self.txt('lbl_ver_update_avail')} {latest_ver}")
                self._lbl_ver_status.setStyleSheet(f"color: #f4a641; font-size: {config.FS_PX(9)}px; background: transparent;")
                self._btn_ver_update.show()
            except RuntimeError:
                return

            def _do_inline_update():
                import threading, subprocess, tempfile, urllib.request, ssl
                from osdoc import log_info, log_error
                is_win = _card_engine.os_doc.is_win
                from gui import UpdateNotifyDialog as _UND
                urls = [_UND._UPDATE_SCRIPT, _UND._UPDATE_SCRIPT_GL]

                self._btn_ver_update.setEnabled(False)
                self._btn_ver_update.setText(_txt(_card_lang(), 'update_notify_updating'))
                self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_wait'))
                self._lbl_ver_status.setStyleSheet(
                    f"color: #888; font-size: {config.FS_PX(9)}px; font-style: italic; background: transparent;"
                )

                class _Bridge(QObject):
                    done = Signal(bool, str)
                _bridge = _Bridge(self)

                def _on_done(success, err):
                    if success:
                        log_info("[Updater] Card update succeeded.")
                        self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_success'))
                        self._lbl_ver_status.setStyleSheet(f"color: #39ff7a; font-size: {config.FS_PX(9)}px; background: transparent;")
                        self._btn_ver_update.hide()
                    else:
                        log_error(f"[Updater] Card update failed: {err}")
                        try:
                            from startup.crash_report import is_technical_update_error, send_nonfatal_technical_report
                            if is_technical_update_error(err):
                                send_nonfatal_technical_report(
                                    "Updater failure (settings)",
                                    err,
                                    extra_context={"target_version": latest_ver},
                                )
                        except Exception:
                            pass
                        self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_failed'))
                        self._lbl_ver_status.setStyleSheet(f"color: #ed4245; font-size: {config.FS_PX(9)}px; background: transparent;")
                        self._btn_ver_update.setText(_txt(_card_lang(), 'update_notify_win_btn'))
                        self._btn_ver_update.setEnabled(True)
                        try:
                            self._btn_ver_update.clicked.disconnect()
                        except Exception:
                            pass
                        from gui import UpdateNotifyDialog as _UND2
                        self._btn_ver_update.clicked.connect(lambda: _UND2._open_url(gh_url))
                        self._btn_ver_update.show()

                _bridge.done.connect(_on_done)

                def _worker():
                    tmp = None
                    try:
                        try:
                            import certifi
                            ctx = ssl.create_default_context(cafile=certifi.where())
                        except Exception:
                            ctx = ssl.create_default_context()
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
                        fd, tmp = tempfile.mkstemp(suffix='.py', prefix='bw_upd_')
                        with os.fdopen(fd, 'wb') as fh:
                            fh.write(content)
                        install_dir = getattr(_card_engine.os_doc, 'install_dir', '')
                        if hasattr(_card_engine.os_doc, 'get_venv_python_path'):
                            venv_py = _card_engine.os_doc.get_venv_python_path()
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
                        sp_kwargs = _card_engine.os_doc.get_subprocess_kwargs() if hasattr(_card_engine, 'os_doc') else {}
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
                            log_info(f'[Updater] {line}')
                        if result.returncode == 0:
                            _bridge.done.emit(True, "")
                        else:
                            _bridge.done.emit(False, f"Exit code {result.returncode}")
                    except subprocess.TimeoutExpired:
                        _bridge.done.emit(False, "Timeout (>10 min)")
                    except Exception as e:
                        _bridge.done.emit(False, str(e))
                    finally:
                        if tmp:
                            try: os.remove(tmp)
                            except Exception: pass

                threading.Thread(target=_worker, daemon=True).start()

            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    self._btn_ver_update.clicked.disconnect()
                except Exception:
                    pass
            self._btn_ver_update.clicked.connect(_do_inline_update)

        def _on_check_done_for_card():
            try:
                self._btn_ver_check.setEnabled(True)
                if self._lbl_ver_status.text() in ("...", self.txt("lbl_ver_checking")):
                    self._lbl_ver_status.setText(self.txt("lbl_ver_up_to_date"))
                    self._lbl_ver_status.setStyleSheet(f"color: #39ff7a; font-size: {config.FS_PX(9)}px; background: transparent;")
                    self._lbl_ver_icon.show()
                    if not self.tgl_auto_check_updates.isChecked():
                        self._btn_ver_check.show()
            except RuntimeError:
                pass

        def _run_ver_check(force_refresh: bool = False):
            if force_refresh:
                UpdateCheckThread._checked = False
            self._lbl_ver_icon.hide()
            self._btn_ver_update.hide()
            self._btn_ver_check.setEnabled(False)
            self._lbl_ver_status.setText(self.txt("lbl_ver_checking"))
            self._lbl_ver_status.setStyleSheet(f"color: #888888; font-size: {config.FS_PX(9)}px; background: transparent;")
            _thr = UpdateCheckThread(config.VERSION, parent=None)
            _thr.update_available.connect(_on_update_known_for_card)
            _thr.finished.connect(_on_check_done_for_card)
            _thr.finished.connect(_thr.deleteLater)
            self._settings_ver_thread = _thr
            _thr.start()

        self._run_ver_check = _run_ver_check
        self._btn_ver_check.clicked.connect(lambda _c=False: _run_ver_check(force_refresh=True))

        def _sync_ver_card_state(auto_enabled: bool):
            mw = self._get_main_window()
            p_ver = getattr(mw, '_pending_update_ver', None)
            if p_ver:
                self._lbl_ver_status.setText(self.txt('lbl_ver_pending_restart'))
                self._lbl_ver_status.setStyleSheet(
                    f"color: #f4a641; font-size: {config.FS_PX(9)}px; font-weight: bold; background: transparent;"
                )
                self._lbl_ver_icon.hide()
                self._btn_ver_check.hide()
                self._btn_ver_update.hide()
            elif not auto_enabled:
                self._lbl_ver_icon.hide()
                self._btn_ver_update.hide()
                self._lbl_ver_status.setText(self.txt("msg_updates_disabled"))
                self._lbl_ver_status.setStyleSheet(f"color: #888888; font-size: {config.FS_PX(9)}px; background: transparent;")
                self._btn_ver_check.setEnabled(True)
                self._btn_ver_check.show()
            else:
                self._btn_ver_check.hide()
                _run_ver_check(force_refresh=False)

        self._sync_ver_card_state = _sync_ver_card_state
        _sync_ver_card_state(auto_check_on)

        # ── Main General Preferences Card ─────────────────────────────────
        gen_card = SettingsCard(parent=page_gen)

        self.dropdown_lang = CustomDropdown(list(config.SUPPORTED_LANGS.values()))
        current_lang_code = prefs.get('gui_lang', 'en')
        self.dropdown_lang.setText(config.SUPPORTED_LANGS.get(current_lang_code, 'English'))

        def _on_lang_changed(val):
            code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), 'en')
            cur_prefs = self.engine.load_preferences() or {}
            if code == cur_prefs.get('gui_lang'):
                return

            cur_prefs['gui_lang'] = code
            self.engine.save_preferences(cur_prefs)
            if hasattr(self, '_initial_state') and isinstance(self._initial_state, dict):
                self._initial_state['gui_lang'] = code

            target = config.TRANS.get(code, config.TRANS['en'])
            if hasattr(self, 'combo_view') and self.combo_view is not None:
                cur_mode = self.combo_view.property("view_mode_key")
                if not cur_mode or cur_mode not in ('segmented', 'continuous'):
                    cur_txt = self.combo_view.currentText()
                    cur_mode = 'segmented' if _is_segmented_text(cur_txt) else ('continuous' if _is_continuous_text(cur_txt) else cur_prefs.get('view_mode', 'segmented'))
                self.combo_view.setProperty("view_mode_key", cur_mode)
                self.combo_view.options_list = [target.get("opt_continuous_flow", "Continuous flow"), target.get("opt_segmented_blocks", "Segmented blocks")]
                self.combo_view.blockSignals(True)
                self.combo_view.setText(target.get("opt_segmented_blocks" if cur_mode == "segmented" else "opt_continuous_flow"))
                self.combo_view.blockSignals(False)

            if hasattr(self, 'combo_mouse_lmb') and self.combo_mouse_lmb is not None:
                cur_lmb = self.combo_mouse_lmb.property("mouse_mode_key") or _get_mouse_mode_from_text(self.combo_mouse_lmb.currentText(), cur_prefs.get('mouse_lmb_mode', 'text'))
                self.combo_mouse_lmb.setProperty("mouse_mode_key", cur_lmb)
                self.combo_mouse_lmb.options_list = [target.get("opt_mouse_text", "Text selection"), target.get("opt_mouse_box", "Box selection"), target.get("opt_mouse_brush", "Brush selection"), target.get("opt_mouse_none", "None")]
                lmb_map = {'text': target.get("opt_mouse_text", "Text selection"), 'box': target.get("opt_mouse_box", "Box selection"), 'brush': target.get("opt_mouse_brush", "Brush selection"), 'none': target.get("opt_mouse_none", "None")}
                self.combo_mouse_lmb.blockSignals(True)
                self.combo_mouse_lmb.setText(lmb_map.get(cur_lmb, target.get("opt_mouse_text", "Text selection")))
                self.combo_mouse_lmb.blockSignals(False)

            if hasattr(self, 'combo_mouse_rmb') and self.combo_mouse_rmb is not None:
                cur_rmb = self.combo_mouse_rmb.property("mouse_mode_key") or _get_mouse_mode_from_text(self.combo_mouse_rmb.currentText(), cur_prefs.get('mouse_rmb_mode', 'box'))
                self.combo_mouse_rmb.setProperty("mouse_mode_key", cur_rmb)
                self.combo_mouse_rmb.options_list = [target.get("opt_mouse_box", "Box selection"), target.get("opt_mouse_text", "Text selection"), target.get("opt_mouse_brush", "Brush selection"), target.get("opt_mouse_none", "None")]
                rmb_map = {'box': target.get("opt_mouse_box", "Box selection"), 'text': target.get("opt_mouse_text", "Text selection"), 'brush': target.get("opt_mouse_brush", "Brush selection"), 'none': target.get("opt_mouse_none", "None")}
                self.combo_mouse_rmb.blockSignals(True)
                self.combo_mouse_rmb.setText(rmb_map.get(cur_rmb, target.get("opt_mouse_box", "Box selection")))
                self.combo_mouse_rmb.blockSignals(False)

            if hasattr(self, 'textedit_prompt') and self.textedit_prompt:
                new_auto = config.get_whisper_prompt_for_lang(cur_prefs.get('lang', 'Auto'), gui_lang=code)
                self.textedit_prompt.setPlaceholderText(new_auto)
                cur_text = self.textedit_prompt.toPlainText().strip()
                if not cur_text or config.is_default_whisper_prompt(cur_text):
                    self.textedit_prompt.setPlainText("")

            title = target.get('msg_title_language_changed', 'Language Changed')
            message = target.get('msg_restart_lang_pending', target.get('msg_restart_lang', 'Language changed. Full changes will apply on restart.'))
            ok_text = target.get('btn_ok', 'OK')
            CustomMsgBox(self, title, message, ok_text).exec()

        self.dropdown_lang.valueChanged.connect(_on_lang_changed)

        def _reset_lang(val):
            self.dropdown_lang.setText(val)
            _on_lang_changed(val)

        self._add_card_row(
            gen_card, "lbl_language", self.dropdown_lang, 'English', _reset_lang,
            add_divider_above=False, tab_key="tab_general",
            options_static=list(config.SUPPORTED_LANGS.values()),
            keywords_en="language translation locale polish english",
        )

        # App Icon visual selector
        icon_row = QHBoxLayout()
        icon_row.setSpacing(config.S(6))
        icon_row.setContentsMargins(0, 0, 0, 0)
        self.icon_group = QButtonGroup(self)
        self.icon_group.setExclusive(True)

        icon_names = ["default", "monochrome", "whiteb", "white"]
        saved_icon = prefs.get('app_icon', 'default')
        for i, name in enumerate(icon_names):
            btn = SquareIconButton(name)
            if name == saved_icon:
                btn.setChecked(True)
            self.icon_group.addButton(btn, i)
            icon_row.addWidget(btn, 1)

        icon_container = QWidget()
        icon_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        icon_container.setLayout(icon_row)

        def _reset_icon(_val="default"):
            for btn in self.icon_group.buttons():
                if btn.property("icon_name") == "default":
                    btn.setChecked(True)
                    break

        self._add_card_row(
            gen_card, "lbl_app_icon", icon_container, 'default', _reset_icon,
            tab_key="tab_general", min_widget_w=config.S(220), max_widget_w=config.S(220),
            keywords_en="app icon logo monochrome white",
        )

        # Show panel headers [Advanced] - saved consistently on Apply
        self.tgl_show_panel_headers = ToggleSwitch()
        self.tgl_show_panel_headers.setChecked(bool(prefs.get("show_panel_headers", True)), animated=False)
        self._add_card_row(
            gen_card, "lbl_show_panel_headers", self.tgl_show_panel_headers,
            True, lambda v: self.tgl_show_panel_headers.setChecked(v, animated=True),
            info_key="tt_show_panel_headers", is_advanced=True, tab_key="tab_general",
            keywords_en="panel headers titles descriptions",
        )

        l_gen.addWidget(gen_card)

        # ── Application Folder & Direct Log File Opener [Advanced Only] ───
        w_paths_sec = QWidget(page_gen)
        scope_transparent(w_paths_sec, border_none=False)
        lp_sec = QVBoxLayout(w_paths_sec)
        lp_sec.setContentsMargins(0, 0, 0, 0)
        lp_sec.setSpacing(config.S(6))

        lp_sec.addWidget(SettingsSectionLabel(self.txt("sec_general_paths"), w_paths_sec))

        paths_card = SettingsCard(parent=w_paths_sec)
        paths_inner = QWidget(paths_card)
        scope_transparent(paths_inner)
        pi_lay = QVBoxLayout(paths_inner)
        pi_lay.setContentsMargins(config.S(14), config.S(12), config.S(14), config.S(12))
        pi_lay.setSpacing(config.S(8))

        raw_inst = getattr(getattr(self.engine, 'os_doc', None), 'install_dir', '')
        install_dir = os.fspath(raw_inst) if isinstance(raw_inst, (str, os.PathLike)) else ''
        raw_log = getattr(getattr(self.engine, 'os_doc', None), 'log_file', '')
        log_file_path = (
            os.fspath(raw_log)
            if isinstance(raw_log, (str, os.PathLike)) and raw_log
            else (os.path.join(install_dir, 'badwords_debug.log') if install_dir else '')
        )

        lbl_app_dir = QLabel(self.txt("lbl_app_folder"), paths_inner)
        lbl_app_dir.setStyleSheet(f"color: #d8d8d8; font-size: {config.FS_PX(9.5)}px; background: transparent;")
        pi_lay.addWidget(lbl_app_dir)

        val_app_dir = QLineEdit(str(install_dir), paths_inner)
        val_app_dir.setReadOnly(True)
        val_app_dir.setCursorPosition(0)
        val_app_dir.setToolTip(str(install_dir))
        val_app_dir.setFixedHeight(config.S(30))
        val_app_dir.setStyleSheet(
            f"color: #b4b4b4; font-family: monospace; font-size: {config.FS_PX(9)}px; "
            f"background: {SETTINGS_INPUT_BG}; border: 1px solid {SETTINGS_INPUT_BORDER}; "
            f"border-radius: {config.S(4)}px; padding: 0 {config.S(10)}px;"
        )
        pi_lay.addWidget(val_app_dir)

        path_btns = QHBoxLayout()
        path_btns.setSpacing(config.S(8))

        btn_copy_app = QPushButton(self.txt("btn_copy_path"), paths_inner)
        btn_copy_app.setObjectName("btn_ghost_sm")
        btn_copy_app.setFixedHeight(config.S(28))
        btn_copy_app.setCursor(Qt.PointingHandCursor)

        def _copy_app_dir():
            QGuiApplication.clipboard().setText(str(install_dir))
            orig = self.txt("btn_copy_path")
            btn_copy_app.setText(self.txt("btn_copied"))
            QTimer.singleShot(1400, lambda: btn_copy_app.setText(orig))

        btn_copy_app.clicked.connect(_copy_app_dir)
        path_btns.addWidget(btn_copy_app)

        btn_open_app = QPushButton(self.txt("btn_open_logs_dir"), paths_inner)
        btn_open_app.setObjectName("btn_ghost_sm")
        btn_open_app.setFixedHeight(config.S(28))
        btn_open_app.setCursor(Qt.PointingHandCursor)
        btn_open_app.clicked.connect(lambda: self._open_local_path(install_dir))
        path_btns.addWidget(btn_open_app)

        path_btns.addStretch()

        btn_open_log = QPushButton(self.txt("btn_open_log_file"), paths_inner)
        btn_open_log.setObjectName("btn_secondary")
        btn_open_log.setFixedHeight(config.S(28))
        btn_open_log.setCursor(Qt.PointingHandCursor)
        btn_open_log.setToolTip(self.txt("tt_open_log_file", path=log_file_path))
        btn_open_log.clicked.connect(lambda: self._open_local_path(log_file_path))
        path_btns.addWidget(btn_open_log)

        pi_lay.addLayout(path_btns)
        paths_card._lay.addWidget(paths_inner)
        lp_sec.addWidget(paths_card)

        self._advanced_widgets.append(w_paths_sec)
        if self._is_basic_mode:
            w_paths_sec.setVisible(False)
        l_gen.addWidget(w_paths_sec)

        self._register_search_entry(
            self.TAB_GENERAL, paths_card,
            title_key="sec_general_paths",
            desc_override=(f"{self.txt('lbl_app_folder')} · {self.txt('btn_open_log_file')}", "Application folder & open diagnostic log file"),
            tab_key="tab_general", is_advanced=True,
            keywords_en="install folder path diagnostics log file open directory",
        )

        l_gen.addStretch(1)

        # ── Import / Export settings (bottom) ─────────────────────────────
        io_row = QHBoxLayout()
        io_row.setContentsMargins(0, config.S(4), 0, 0)
        io_row.setSpacing(config.S(8))

        btn_import_s = QPushButton(self.txt("btn_import_settings"))
        btn_import_s.setObjectName("btn_ghost_sm")
        btn_import_s.setFixedHeight(config.S(28))
        btn_import_s.setCursor(Qt.PointingHandCursor)
        btn_import_s.clicked.connect(self._on_import_settings)
        io_row.addWidget(btn_import_s)

        btn_export_s = QPushButton(self.txt("btn_export_settings"))
        btn_export_s.setObjectName("btn_ghost_sm")
        btn_export_s.setFixedHeight(config.S(28))
        btn_export_s.setCursor(Qt.PointingHandCursor)
        btn_export_s.clicked.connect(self._on_export_settings)
        io_row.addWidget(btn_export_s)
        io_row.addStretch()
        l_gen.addLayout(io_row)

        self._register_search_entry(
            self.TAB_GENERAL, btn_import_s,
            title_key="btn_import_settings", tab_key="tab_general",
            keywords_en="import settings json config backup",
        )
        self._register_search_entry(
            self.TAB_GENERAL, btn_export_s,
            title_key="btn_export_settings", tab_key="tab_general",
            keywords_en="export settings json config backup",
        )

        return page_gen

    # ── PAGE 1: APPEARANCE & SCALING ──────────────────────────────────────

    def _build_page_appearance(self, prefs):
        self._current_building_page_idx = self.TAB_APPEARANCE
        page_app = QWidget()
        scope_transparent(page_app, border_none=False)
        l_app = QVBoxLayout(page_app)
        l_app.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_app.setSpacing(config.S(12))

        l_app.addWidget(SettingsPageHeader(self.txt("tab_appearance"), self.txt("hdr_appearance_sub"), parent=page_app))

        # Section 1: Interface & Window
        l_app.addWidget(SettingsSectionLabel(self.txt("sec_app_interface"), page_app))
        card_ui = SettingsCard(parent=page_app)

        scale_mode = str(prefs.get('ui_scale_mode', 'auto')).strip().lower()
        if scale_mode not in ('auto', 'manual'):
            scale_mode = 'auto'
        self._ui_scale_mode = scale_mode
        self._updating_scale_slider = False

        os_pct = int(getattr(config, 'OS_SCALE_PERCENT', config.detect_os_scale_pct(self.screen())))
        raw_saved = int(prefs.get('ui_scale_pct', os_pct))
        effective_scale = os_pct if scale_mode == 'auto' else max(config.UI_SCALE_MIN, min(config.UI_SCALE_MAX, raw_saved))

        self.slider_ui_scale = JumpSlider(Qt.Horizontal, snap_step=config.UI_SCALE_STEP)
        self.slider_ui_scale.setRange(config.UI_SCALE_MIN, config.UI_SCALE_MAX)
        self.slider_ui_scale.setSingleStep(config.UI_SCALE_STEP)
        self.slider_ui_scale.setPageStep(25)
        self.slider_ui_scale.setMinimumWidth(config.S(85))
        self.slider_ui_scale.setValue(max(config.UI_SCALE_MIN, min(config.UI_SCALE_MAX, effective_scale)))
        self.slider_ui_scale.setFixedHeight(config.S(20))

        self.lbl_ui_scale_val = QLabel()
        scale_lbl_font = config.make_font(config.UI_FONT_NAME, 9.5)
        scale_lbl_fm = QFontMetrics(scale_lbl_font)
        self.lbl_ui_scale_val.setFont(scale_lbl_font)
        self.lbl_ui_scale_val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_ui_scale_val.setFixedWidth(max(config.S(38), scale_lbl_fm.horizontalAdvance("200%") + config.S(4)))
        self.lbl_ui_scale_val.setStyleSheet(f"font-size: {config.FS_PX(9.5)}px; color: #c4c4c4; background: transparent;")

        sys_badge_txt = self.txt('ui_scale_system_badge')
        if sys_badge_txt == 'ui_scale_system_badge':
            sys_badge_txt = 'System'
        base_scale_title = self.txt('lbl_ui_scaling')

        def _refresh_scale_label(pct_val: int, is_auto: bool):
            if hasattr(self, 'lbl_ui_scale_val') and self.lbl_ui_scale_val is not None:
                self.lbl_ui_scale_val.setText(f"{pct_val}%")
            t_lbl = getattr(self, '_lbl_ui_scale_title', None)
            if t_lbl is not None:
                import html as _html
                esc_base = _html.escape(base_scale_title)
                if is_auto:
                    esc_sys = _html.escape(sys_badge_txt)
                    t_lbl.setTextFormat(Qt.RichText)
                    t_lbl.setText(
                        f"{esc_base}&nbsp;&nbsp;"
                        f"<span style='color: #169c56; font-weight: 600;'>{esc_sys}</span>"
                    )
                else:
                    t_lbl.setTextFormat(Qt.PlainText)
                    t_lbl.setText(base_scale_title)

        self._refresh_scale_label = _refresh_scale_label

        scale_row = QWidget()
        scope_transparent(scale_row)
        scale_lay = QHBoxLayout(scale_row)
        scale_lay.setContentsMargins(0, 0, 0, 0)
        scale_lay.setSpacing(config.S(8))
        scale_lay.addWidget(self.slider_ui_scale, 1)
        scale_lay.addWidget(self.lbl_ui_scale_val, 0)

        def _on_scale_val(v):
            if getattr(self, '_updating_scale_slider', False):
                return
            self._ui_scale_mode = 'manual'
            _refresh_scale_label(int(v), False)

        def _reset_scale(_val):
            cur_os = int(config.detect_os_scale_pct(self.screen()))
            self._ui_scale_mode = 'auto'
            self._updating_scale_slider = True
            try:
                self.slider_ui_scale.setValue(max(config.UI_SCALE_MIN, min(config.UI_SCALE_MAX, cur_os)))
            finally:
                self._updating_scale_slider = False
            _refresh_scale_label(cur_os, True)

        self.slider_ui_scale.valueChanged.connect(_on_scale_val)

        ctrl_scale_w = config.S(220)
        row_scale = self._add_card_row(
            card_ui, "lbl_ui_scaling", scale_row, "auto", _reset_scale,
            info_key="tt_ui_scaling", add_divider_above=False,
            min_widget_w=ctrl_scale_w, max_widget_w=ctrl_scale_w,
            section_key="sec_app_interface", tab_key="tab_appearance",
            keywords_en="dpi scaling zoom size factor percentage",
        )
        # Show deep emerald system-mode text inline right beside the left-side label
        # so the right-side percentage stays fixed-width and never resizes the slider.
        self._lbl_ui_scale_title = getattr(row_scale, '_label_widget', None)
        _refresh_scale_label(effective_scale, scale_mode == 'auto')

        self.chk_ontop = ToggleSwitch()
        self.chk_ontop.setChecked(bool(prefs.get('always_on_top', False)), animated=False)
        self._add_card_row(
            card_ui, "lbl_always_on_top", self.chk_ontop, False,
            lambda v: self.chk_ontop.setChecked(v, animated=True),
            info_key="tt_always_on_top",
            section_key="sec_app_interface", tab_key="tab_appearance",
            keywords_en="always on top pin window float",
        )

        is_wayland = getattr(self, '_is_wayland', False) or (os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland')
        if is_wayland:
            self.lbl_always_on_top_wayland_hint = QLabel(
                self.txt(
                    "lbl_always_on_top_wayland_hint",
                    "* Note: On Linux Wayland, the system may ignore application-requested Always on Top. "
                    "If needed, right-click the window taskbar icon and enable 'Keep Above Others'."
                )
            )
            self.lbl_always_on_top_wayland_hint.setWordWrap(True)
            self.lbl_always_on_top_wayland_hint.setStyleSheet(
                f"color: #d4a64a; font-size: {config.FS_PX(8.5)}px; background: transparent;"
            )
            card_ui.add_content_widget(
                self.lbl_always_on_top_wayland_hint,
                margins=(config.S(16), 0, config.S(16), config.S(10)),
            )

        l_app.addWidget(card_ui)

        # Section 2: Transcript Typography
        l_app.addSpacing(config.S(4))
        l_app.addWidget(SettingsSectionLabel(self.txt("sec_app_typography"), page_app))
        card_typo = SettingsCard(parent=page_app)

        self.combo_font = SearchableDropdown(_get_system_font_families)
        self.combo_font.setText(prefs.get('editor_font_family', self.DEFAULTS['editor_font_family']))
        self.spin_fsize = CustomNumberInput(int(prefs.get('editor_font_size', self.DEFAULTS['editor_font_size'])), 8, 48)
        self.spin_lheight = CustomNumberInput(int(prefs.get('editor_line_height', self.DEFAULTS['editor_line_height'])), 0, 40)

        self._add_card_row(
            card_typo, "lbl_transcript_font", self.combo_font,
            self.DEFAULTS['editor_font_family'], self.combo_font.setValue,
            add_divider_above=False, section_key="sec_app_typography", tab_key="tab_appearance",
            keywords_en="font family typography transcript",
        )
        self._add_card_row(
            card_typo, "lbl_font_size_pt", self.spin_fsize,
            self.DEFAULTS['editor_font_size'], self.spin_fsize.setValue,
            section_key="sec_app_typography", tab_key="tab_appearance",
            keywords_en="font size pt typography",
        )
        self._add_card_row(
            card_typo, "lbl_line_spacing_px", self.spin_lheight,
            self.DEFAULTS['editor_line_height'], self.spin_lheight.setValue,
            is_advanced=True, section_key="sec_app_typography", tab_key="tab_appearance",
            keywords_en="line spacing height px typography",
        )

        card_typo.add_divider()
        self.lbl_preview = QTextEdit()
        self.lbl_preview.setReadOnly(True)
        self.lbl_preview.setFocusPolicy(Qt.NoFocus)
        self.lbl_preview.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lbl_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lbl_preview.setFrameShape(QFrame.NoFrame)
        self.lbl_preview.document().setDocumentMargin(0)
        self.lbl_preview.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        def _update_preview_height(_=None):
            try:
                lh = config.S(self.spin_lheight.value())
                new_h = int(self.lbl_preview.document().size().height()) - lh + config.S(24)
                new_h = max(config.S(34), new_h)
                if self.lbl_preview.height() != new_h:
                    self.lbl_preview.setFixedHeight(new_h)
            except Exception:
                pass

        self.lbl_preview.document().documentLayout().documentSizeChanged.connect(_update_preview_height)
        card_typo.add_content_widget(
            self.lbl_preview,
            margins=(config.S(14), config.S(12), config.S(14), config.S(14)),
        )

        self.combo_font.valueChanged.connect(self._update_preview)
        self.spin_fsize.valueChanged.connect(self._update_preview)
        self.spin_lheight.valueChanged.connect(self._update_preview)
        self._update_preview()

        l_app.addWidget(card_typo)
        l_app.addStretch(1)
        return page_app

    # ── PAGE 2: EDITOR & CANVAS ───────────────────────────────────────────

    def _build_page_editor(self, prefs):
        self._current_building_page_idx = self.TAB_EDITOR
        page_ed = QWidget()
        scope_transparent(page_ed, border_none=False)
        l_ed = QVBoxLayout(page_ed)
        l_ed.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_ed.setSpacing(config.S(12))

        l_ed.addWidget(SettingsPageHeader(self.txt("tab_editor"), self.txt("hdr_editor_sub"), parent=page_ed))

        # Section 1: Canvas & Mouse Controls
        l_ed.addWidget(SettingsSectionLabel(self.txt("sec_ed_canvas"), page_ed))
        card_canvas = SettingsCard(parent=page_ed)

        view_items = [self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")]
        self.combo_view = CustomDropdown(
            view_items,
            options_getter=lambda: [self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")]
        )
        is_seg = prefs.get('view_mode', 'segmented') == 'segmented'
        self.combo_view.setProperty("view_mode_key", "segmented" if is_seg else "continuous")
        self.combo_view.setText(self.txt("opt_segmented_blocks") if is_seg else self.txt("opt_continuous_flow"))
        self.combo_view.valueChanged.connect(
            lambda v: self.combo_view.setProperty(
                "view_mode_key",
                "segmented" if _is_segmented_text(v) else ("continuous" if _is_continuous_text(v) else self.combo_view.property("view_mode_key"))
            )
        )
        self._add_card_row(
            card_canvas, "lbl_display_mode", self.combo_view,
            self.txt("opt_segmented_blocks"), lambda v: self.combo_view.setValue(self.txt("opt_segmented_blocks")),
            add_divider_above=False, section_key="sec_ed_canvas", tab_key="tab_editor",
            options_keys=["opt_continuous_flow", "opt_segmented_blocks"],
            keywords_en="display view mode segmented blocks continuous flow",
        )

        mouse_lmb_items = [self.txt("opt_mouse_box"), self.txt("opt_mouse_text"), self.txt("opt_mouse_brush"), self.txt("opt_mouse_none")]
        self.combo_mouse_lmb = CustomDropdown(mouse_lmb_items, options_getter=lambda: [self.txt("opt_mouse_box"), self.txt("opt_mouse_text"), self.txt("opt_mouse_brush"), self.txt("opt_mouse_none")])
        curr_lmb = prefs.get('mouse_lmb_mode', 'text')
        self.combo_mouse_lmb.setProperty("mouse_mode_key", curr_lmb)
        lmb_text_map = {'text': self.txt("opt_mouse_text"), 'box': self.txt("opt_mouse_box"), 'brush': self.txt("opt_mouse_brush"), 'none': self.txt("opt_mouse_none")}
        self.combo_mouse_lmb.setText(lmb_text_map.get(curr_lmb, self.txt("opt_mouse_text")))
        self.combo_mouse_lmb.valueChanged.connect(lambda v: self.combo_mouse_lmb.setProperty("mouse_mode_key", _get_mouse_mode_from_text(v, self.combo_mouse_lmb.property("mouse_mode_key") or "text")))
        self._add_card_row(
            card_canvas, "lbl_mouse_lmb_mode", self.combo_mouse_lmb,
            self.txt("opt_mouse_text"), lambda v: self.combo_mouse_lmb.setValue(self.txt("opt_mouse_text")),
            info_key="tt_mouse_lmb_mode", section_key="sec_ed_canvas", tab_key="tab_editor",
            options_keys=["opt_mouse_box", "opt_mouse_text", "opt_mouse_brush", "opt_mouse_none"],
            keywords_en="left mouse button click marquee box brush text selection",
        )

        mouse_rmb_items = [self.txt("opt_mouse_box"), self.txt("opt_mouse_text"), self.txt("opt_mouse_brush"), self.txt("opt_mouse_none")]
        self.combo_mouse_rmb = CustomDropdown(mouse_rmb_items, options_getter=lambda: [self.txt("opt_mouse_box"), self.txt("opt_mouse_text"), self.txt("opt_mouse_brush"), self.txt("opt_mouse_none")])
        curr_rmb = prefs.get('mouse_rmb_mode', 'box')
        self.combo_mouse_rmb.setProperty("mouse_mode_key", curr_rmb)
        rmb_text_map = {'box': self.txt("opt_mouse_box"), 'text': self.txt("opt_mouse_text"), 'brush': self.txt("opt_mouse_brush"), 'none': self.txt("opt_mouse_none")}
        self.combo_mouse_rmb.setText(rmb_text_map.get(curr_rmb, self.txt("opt_mouse_box")))
        self.combo_mouse_rmb.valueChanged.connect(lambda v: self.combo_mouse_rmb.setProperty("mouse_mode_key", _get_mouse_mode_from_text(v, self.combo_mouse_rmb.property("mouse_mode_key") or "box")))
        self._add_card_row(
            card_canvas, "lbl_mouse_rmb_mode", self.combo_mouse_rmb,
            self.txt("opt_mouse_box"), lambda v: self.combo_mouse_rmb.setValue(self.txt("opt_mouse_box")),
            info_key="tt_mouse_rmb_mode", is_advanced=True, section_key="sec_ed_canvas", tab_key="tab_editor",
            options_keys=["opt_mouse_box", "opt_mouse_text", "opt_mouse_brush", "opt_mouse_none"],
            keywords_en="right mouse button click marquee box brush text selection",
        )

        l_ed.addWidget(card_canvas)

        # Section 2: Chunking & Timestamps [Advanced Only]
        w_ed_adv = QWidget(page_ed)
        scope_transparent(w_ed_adv, border_none=False)
        l_ed_adv = QVBoxLayout(w_ed_adv)
        l_ed_adv.setContentsMargins(0, config.S(4), 0, 0)
        l_ed_adv.setSpacing(config.S(6))

        l_ed_adv.addWidget(SettingsSectionLabel(self.txt("sec_ed_chunking"), w_ed_adv))
        card_chunk = SettingsCard(parent=w_ed_adv)

        self.spin_chunk_max = CustomNumberInput(int(prefs.get('chunk_max_words', 15)), 5, 200)
        self._add_card_row(
            card_chunk, "lbl_chunk_max_words", self.spin_chunk_max, 15, self.spin_chunk_max.setValue,
            info_key="tt_chunk_max_words", is_advanced=True, add_divider_above=False,
            section_key="sec_ed_chunking", tab_key="tab_editor",
            keywords_en="chunk max words transcript line",
        )

        self.spin_chunk_look = CustomNumberInput(int(prefs.get('chunk_lookahead', 3)), 0, 20)
        self._add_card_row(
            card_chunk, "lbl_chunk_lookahead", self.spin_chunk_look, 3, self.spin_chunk_look.setValue,
            info_key="tt_chunk_lookahead", is_advanced=True,
            section_key="sec_ed_chunking", tab_key="tab_editor",
            keywords_en="chunk lookahead punctuation words",
        )

        self.spin_chunk_min = CustomNumberInput(int(prefs.get('chunk_min_chars', 7)), 1, 50)
        self._add_card_row(
            card_chunk, "lbl_chunk_min_chars", self.spin_chunk_min, 7, self.spin_chunk_min.setValue,
            info_key="tt_chunk_min_chars", is_advanced=True,
            section_key="sec_ed_chunking", tab_key="tab_editor",
            keywords_en="chunk min chars line",
        )

        self.tgl_timestamp_precise = ToggleSwitch()
        self.tgl_timestamp_precise.setChecked(bool(prefs.get("timestamp_precise", config.DEFAULT_SETTINGS["timestamp_precise"])), animated=False)
        self._add_card_row(
            card_chunk, "lbl_timestamp_precise", self.tgl_timestamp_precise, False,
            lambda v: self.tgl_timestamp_precise.setChecked(v, animated=True),
            info_key="tt_timestamp_precise", is_advanced=True,
            section_key="sec_ed_chunking", tab_key="tab_editor",
            keywords_en="timestamps milliseconds precise ms",
        )

        l_ed_adv.addWidget(card_chunk)
        self._advanced_widgets.append(w_ed_adv)
        if self._is_basic_mode:
            w_ed_adv.setVisible(False)
        l_ed.addWidget(w_ed_adv)

        l_ed.addStretch(1)
        return page_ed

    # ── PAGE 3: DAVINCI RESOLVE & CUSTOM MARKERS ──────────────────────────

    def _build_page_davinci(self, prefs):
        self._current_building_page_idx = self.TAB_DAVINCI
        page_dav = QWidget()
        scope_transparent(page_dav, border_none=False)
        l_dav = QVBoxLayout(page_dav)
        l_dav.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_dav.setSpacing(config.S(12))

        l_dav.addWidget(SettingsPageHeader(self.txt("tab_davinci"), self.txt("hdr_davinci_sub"), parent=page_dav))

        is_free_21_1 = False
        if hasattr(self.engine, 'resolve_handler') and self.engine.resolve_handler and hasattr(self.engine.resolve_handler, 'is_free_21_1_or_newer'):
            is_free_21_1 = self.engine.resolve_handler.is_free_21_1_or_newer()
        elif hasattr(self.engine, 'os_doc') and self.engine.os_doc:
            ed_info = self.engine.os_doc.get_resolve_edition_info()
            is_free_21_1 = (ed_info.get("edition") == "Free" and ed_info.get("is_21_1_or_newer", False))

        # Section 1: Assembly & Linking
        l_dav.addWidget(SettingsSectionLabel(self.txt("sec_dav_assembly"), page_dav))
        card_asm = SettingsCard(parent=page_dav)

        force_xml_init = bool(prefs.get("force_xml_assembly", config.DEFAULT_SETTINGS["force_xml_assembly"]))
        if is_free_21_1:
            force_xml_init = True

        self.w_assembly_selector = AssemblyModeSelector(
            current_mode="xml" if force_xml_init else "drt",
            is_drt_disabled=is_free_21_1,
            parent=card_asm
        )
        if is_free_21_1:
            self.w_assembly_selector.set_drt_disabled(True, self.txt("tt_assembly_drt_disabled_free"))
        else:
            self.w_assembly_selector.btn_xml.setToolTip(self.txt("tt_assembly_xml"))
            self.w_assembly_selector.btn_drt.setToolTip(self.txt("tt_assembly_drt"))
        self.tgl_force_xml_assembly = self.w_assembly_selector

        self._add_card_row(
            card_asm, "lbl_assembly_method", self.w_assembly_selector, True,
            lambda v: self.w_assembly_selector.setChecked(v),
            info_key="tt_assembly_method", add_divider_above=False,
            section_key="sec_dav_assembly", tab_key="tab_davinci",
            options_static=["XML", "DRT"],
            keywords_en="timeline assembly method fcp7 xml drt resolve",
        )

        self.tgl_xml_preserve_track_order = ToggleSwitch()
        self.tgl_xml_preserve_track_order.setChecked(bool(prefs.get("xml_preserve_track_order", config.DEFAULT_SETTINGS["xml_preserve_track_order"])), animated=False)
        self._row_xml_track = self._add_card_row(
            card_asm, "lbl_xml_preserve_track_order", self.tgl_xml_preserve_track_order, False,
            lambda v: self.tgl_xml_preserve_track_order.setChecked(v, animated=True),
            info_key="tt_xml_preserve_track_order", is_advanced=True,
            section_key="sec_dav_assembly", tab_key="tab_davinci",
            keywords_en="preserve original track order xml audio video",
        )
        self.lbl_xml_track = self._row_xml_track._label_widget

        self.tgl_link_av_clips = ToggleSwitch()
        self.tgl_link_av_clips.setChecked(bool(prefs.get("link_av_clips", config.DEFAULT_SETTINGS["link_av_clips"])), animated=False)
        self._row_link_av = self._add_card_row(
            card_asm, "lbl_link_av_clips", self.tgl_link_av_clips, False,
            lambda v: self.tgl_link_av_clips.setChecked(v, animated=True),
            info_key="tt_link_av_clips",
            section_key="sec_dav_assembly", tab_key="tab_davinci",
            keywords_en="link matching audio video clips xml",
        )
        self.lbl_link_av = self._row_link_av._label_widget

        self.tgl_link_all_cut_tracks = ToggleSwitch()
        self.tgl_link_all_cut_tracks.setChecked(bool(prefs.get("link_all_cut_tracks", config.DEFAULT_SETTINGS["link_all_cut_tracks"])), animated=False)
        self._row_link_all = self._add_card_row(
            card_asm, "lbl_link_all_cut_tracks", self.tgl_link_all_cut_tracks, False,
            lambda v: self.tgl_link_all_cut_tracks.setChecked(v, animated=True),
            info_key="tt_link_all_cut_tracks",
            section_key="sec_dav_assembly", tab_key="tab_davinci",
            keywords_en="link all cut tracks xml",
        )
        self.lbl_link_all = self._row_link_all._label_widget

        # Animated linking dimming (no immediate disk write - waits for Apply)
        self._linking_anim = QVariantAnimation(self)
        self._linking_anim.setDuration(250)
        self._linking_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._linking_anim.valueChanged.connect(self._apply_linking_opacity)
        self._curr_linking_op = 1.0

        self.w_assembly_selector.mode_changed.connect(
            lambda mode: self._update_linking_availability(mode == "xml", animated=True)
        )
        self._update_linking_availability(self.w_assembly_selector.isChecked(), animated=False)

        l_dav.addWidget(card_asm)

        # Section 2: Playback & Preview
        l_dav.addSpacing(config.S(4))
        l_dav.addWidget(SettingsSectionLabel(self.txt("sec_dav_playback"), page_dav))
        card_play = SettingsCard(parent=page_dav)

        self.chk_sync_davinci = ToggleSwitch()
        self.chk_sync_davinci.setChecked(bool(prefs.get('sync_davinci_chapter', True)), animated=False)
        self._add_card_row(
            card_play, "chk_sync_davinci", self.chk_sync_davinci, True,
            lambda v: self.chk_sync_davinci.setChecked(v, animated=True),
            info_key="tt_sync_davinci_chapter", add_divider_above=False,
            section_key="sec_dav_playback", tab_key="tab_davinci",
            keywords_en="sync davinci timeline chapter switch",
        )

        self.tgl_resolve_render_timeline_proxy = ToggleSwitch()
        self.tgl_resolve_render_timeline_proxy.setChecked(bool(prefs.get("resolve_render_timeline_proxy", config.DEFAULT_SETTINGS["resolve_render_timeline_proxy"])), animated=False)
        self._add_card_row(
            card_play, "lbl_resolve_render_timeline_proxy", self.tgl_resolve_render_timeline_proxy, True,
            lambda v: self.tgl_resolve_render_timeline_proxy.setChecked(v, animated=True),
            info_key="tt_resolve_render_timeline_proxy", is_advanced=True,
            section_key="sec_dav_playback", tab_key="tab_davinci",
            keywords_en="render davinci timeline preview proxy 360p",
        )

        l_dav.addWidget(card_play)
        l_dav.addStretch(1)
        return page_dav

    def _apply_linking_opacity(self, val: float):
        self._curr_linking_op = float(val)
        is_translucent = (val < 0.9)

        for row_attr, lbl_attr, tgl_attr in (
            ('_row_link_av', 'lbl_link_av', 'tgl_link_av_clips'),
            ('_row_link_all', 'lbl_link_all', 'tgl_link_all_cut_tracks'),
            ('_row_xml_track', 'lbl_xml_track', 'tgl_xml_preserve_track_order'),
        ):
            row_w = getattr(self, row_attr, None)
            if row_w is not None:
                ctrl_c = getattr(row_w, '_ctrl_container', row_w)
                ctrl_c.setAttribute(Qt.WA_TransparentForMouseEvents, is_translucent)
            lbl_w = getattr(self, lbl_attr, None)
            if lbl_w is not None:
                lbl_w.setStyleSheet(
                    f"font-size: {config.FS_PX(10)}px; color: {_blend_hex('#e4e4e4', SETTINGS_CARD_BG, val)}; background: transparent;"
                )
                lbl_w.setAttribute(Qt.WA_TransparentForMouseEvents, is_translucent)
            tgl_w = getattr(self, tgl_attr, None)
            if tgl_w is not None and hasattr(tgl_w, 'set_opacity'):
                tgl_w.set_opacity(val)

    def _update_linking_availability(self, is_xml_on: bool, animated: bool = False):
        enabled = bool(is_xml_on)
        for tgl_attr in ('tgl_link_av_clips', 'tgl_link_all_cut_tracks', 'tgl_xml_preserve_track_order'):
            tgl = getattr(self, tgl_attr, None)
            if tgl is not None:
                tgl.set_blocked(not enabled)

        tt = "" if enabled else self.txt("tt_linking_requires_xml")
        for row_attr in ('_row_link_av', '_row_link_all', '_row_xml_track'):
            rw = getattr(self, row_attr, None)
            if rw is not None:
                rw.setToolTip(tt)

        target_op = 1.0 if enabled else 0.35
        if animated and self.isVisible():
            if hasattr(self, '_linking_anim'):
                self._linking_anim.stop()
                self._linking_anim.setStartValue(self._curr_linking_op)
                self._linking_anim.setEndValue(target_op)
                self._curr_linking_op = target_op
                self._linking_anim.start()
        else:
            if hasattr(self, '_linking_anim'):
                self._linking_anim.stop()
            self._curr_linking_op = target_op
            self._apply_linking_opacity(target_op)

    # ── PAGE 4: SHORTCUTS ─────────────────────────────────────────────────

    def _check_shortcut_conflicts(self):
        """Scan all capturable shortcuts across built-in and Shortcuts custom marker rows."""
        all_inputs = {}
        all_inputs.update(getattr(self, 'shortcut_inputs', {}))
        all_inputs.update(getattr(self, 'custom_marker_shortcut_inputs', {}))

        seq_to_keys = {}
        for k, w in all_inputs.items():
            if getattr(w, 'display_only', False):
                continue
            seq = w.get_sequence()
            if seq:
                seq_to_keys.setdefault(seq, []).append(k)

        for k, w in all_inputs.items():
            if getattr(w, 'display_only', False):
                continue
            seq = w.get_sequence()
            is_conflict = bool(seq and len(seq_to_keys.get(seq, [])) > 1)
            w.set_conflict(is_conflict)

    def _sync_shortcut_value(self, key: str, seq: str, source: str = ""):
        """Synchronizes a shortcut sequence across _pending_shortcuts and the Shortcuts tab."""
        seq = str(seq or "")
        self._pending_shortcuts[key] = seq

        if source != "shortcuts":
            sc_w = getattr(self, 'shortcut_inputs', {}).get(key) or getattr(self, 'custom_marker_shortcut_inputs', {}).get(key)
            if sc_w is not None:
                try:
                    sc_w.set_sequence(seq)
                except RuntimeError:
                    pass

        self._check_shortcut_conflicts()

    def _build_page_shortcuts(self, prefs):
        self._current_building_page_idx = self.TAB_SHORTCUTS
        page_shorts = QWidget()
        scope_transparent(page_shorts, border_none=False)
        l_shorts = QVBoxLayout(page_shorts)
        l_shorts.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_shorts.setSpacing(config.S(12))

        l_shorts.addWidget(SettingsPageHeader(self.txt("tab_shortcuts"), self.txt("hdr_shortcuts_sub"), parent=page_shorts))

        default_shortcuts = getattr(config, 'DEFAULT_SETTINGS', {}).get('shortcuts', {})
        self.shortcut_inputs = {}
        self.custom_marker_shortcut_inputs = {}

        # Card 1: Marker Shortcuts (Red, Blue, Green, Eraser + dynamic Custom Markers)
        l_shorts.addWidget(SettingsSectionLabel(self.txt("sec_sc_markers"), page_shorts))
        self._sc_markers_card = SettingsCard(parent=page_shorts)

        # Card 2: Playback & Navigation
        l_shorts.addWidget(SettingsSectionLabel(self.txt("sec_sc_navigation"), page_shorts))
        card_nav = SettingsCard(parent=page_shorts)

        MARKER_KEYS = ['mark_red', 'mark_blue', 'mark_green', 'mark_eraser']
        NAV_KEYS = ['play_stop', 'skip_backward', 'skip_forward', 'jump_to_word', 'search', 'open_settings']

        none_lbl = self.txt("shortcut_none")

        def _make_shortcut_row(card: SettingsCard, key: str, label_key: str, default_val: str, info_key: str = None, add_divider: bool = True, sec_key: str = ""):
            cur_val = self._pending_shortcuts.get(key, default_val)
            if key == 'jump_to_word':
                opts_keys = ['opt_ctrl_lmb', 'opt_ctrl_rmb', 'opt_alt_lmb', 'opt_alt_rmb', 'opt_shift_lmb', 'opt_shift_rmb']
                key_map = {k: self.txt(k) for k in opts_keys}
                widget = MouseShortcutCaptureButton(str(cur_val), key_map, display_only=False, none_label=none_lbl)
            else:
                widget = ShortcutCaptureButton(str(cur_val), display_only=False, none_label=none_lbl)

            widget.sequence_changed.connect(lambda seq, k=key: self._sync_shortcut_value(k, seq, source="shortcuts"))

            # Combine [CaptureButton, Clear X, Revert] cleanly
            holder = QWidget()
            scope_transparent(holder)
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(config.S(4))

            is_mouse_key = (key == 'jump_to_word')
            btn_w = config.S(225) if is_mouse_key else config.S(165)
            widget.set_uniform_width(btn_w)
            hl.addWidget(widget)

            btn_clear = CloseIconButton(size=28, parent=holder)
            btn_clear.setToolTip(self.txt("tt_clear_shortcut"))
            btn_clear.clicked.connect(lambda _c=False, k=key: self._sync_shortcut_value(k, "", source=""))
            hl.addWidget(btn_clear)

            row_w = self._add_card_row(
                card, label_key, holder, default_val,
                lambda d_val, k=key: self._sync_shortcut_value(k, d_val, source=""),
                info_key=info_key, add_divider_above=add_divider,
                min_widget_w=btn_w + config.S(34),
                max_widget_w=btn_w + config.S(34),
                section_key=sec_key, tab_key="tab_shortcuts",
                options_static=[str(cur_val)],
                keywords_en=f"shortcut hotkey keybind {key.replace('_', ' ')}",
            )
            self.shortcut_inputs[key] = widget
            return row_w

        for i, key in enumerate(MARKER_KEYS):
            if key not in default_shortcuts:
                continue
            _make_shortcut_row(
                self._sc_markers_card, key, f"shortcut_{key}",
                default_shortcuts.get(key, ""), add_divider=(i > 0), sec_key="sec_sc_markers",
            )

        self._sc_custom_marker_rows = []
        l_shorts.insertWidget(2, self._sc_markers_card)

        for i, key in enumerate(NAV_KEYS):
            if key not in default_shortcuts:
                continue
            _make_shortcut_row(
                card_nav, key, f"shortcut_{key}",
                default_shortcuts.get(key, "opt_ctrl_lmb" if key == "jump_to_word" else ""),
                info_key="tt_jump_to_word_info" if key == "jump_to_word" else None,
                add_divider=(i > 0), sec_key="sec_sc_navigation",
            )

        l_shorts.addWidget(card_nav)
        l_shorts.addStretch(1)

        self._refresh_custom_marker_shortcuts()
        self._check_shortcut_conflicts()
        return page_shorts

    # ── PAGE 5: CUSTOM MARKERS ────────────────────────────────────────────

    def _build_page_custom_markers(self, prefs):
        self._current_building_page_idx = self.TAB_MARKERS
        page_markers = QWidget()
        scope_transparent(page_markers, border_none=False)
        l_m = QVBoxLayout(page_markers)
        l_m.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_m.setSpacing(config.S(12))

        l_m.addWidget(SettingsPageHeader(self.txt("tab_custom_markers"), self.txt("hdr_custom_markers_sub"), parent=page_markers))

        self.markers_card = SettingsCard(parent=page_markers)
        if not hasattr(self, 'current_custom_markers'):
            self.current_custom_markers = list(prefs.get('custom_markers', []))

        self._markers_scroll = QScrollArea(self.markers_card)
        self._markers_scroll.setWidgetResizable(True)
        self._markers_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._markers_scroll.setFrameShape(QFrame.NoFrame)
        self._markers_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget#markers_inner {{
                background: transparent;
                border: none;
            }}
            {config.scrollbar_qss(6, bg=SETTINGS_CARD_BG)}
        """)
        self._markers_inner = MarkerDragZone()
        self._markers_inner.setObjectName("markers_inner")
        self._markers_layout = self._markers_inner.layout()
        self._markers_layout.setContentsMargins(config.S(6), config.S(4), config.S(6), config.S(4))
        self._markers_layout.setSpacing(0)
        self._markers_scroll.setWidget(self._markers_inner)
        self.markers_card._lay.addWidget(self._markers_scroll)

        self.markers_card.add_divider()

        footer_wrap = QWidget(self.markers_card)
        scope_transparent(footer_wrap)
        fw_lay = QHBoxLayout(footer_wrap)
        fw_lay.setContentsMargins(config.S(14), config.S(10), config.S(14), config.S(10))
        fw_lay.setSpacing(config.S(8))

        btn_add_m = QPushButton("+ " + self.txt("btn_add_marker"), footer_wrap)
        btn_add_m.setObjectName("btn_apply")
        btn_add_m.setFixedHeight(config.S(28))
        btn_add_m.setCursor(Qt.PointingHandCursor)
        btn_add_m.clicked.connect(self._on_add_marker)
        fw_lay.addWidget(btn_add_m)

        fw_lay.addStretch()

        btn_export_m = QPushButton(self.txt("btn_export_markers"), footer_wrap)
        btn_export_m.setObjectName("btn_ghost_sm")
        btn_export_m.setFixedHeight(config.S(28))
        btn_export_m.setCursor(Qt.PointingHandCursor)
        btn_export_m.clicked.connect(self._on_export_markers)
        fw_lay.addWidget(btn_export_m)

        btn_import_m = QPushButton(self.txt("btn_import_markers"), footer_wrap)
        btn_import_m.setObjectName("btn_ghost_sm")
        btn_import_m.setFixedHeight(config.S(28))
        btn_import_m.setCursor(Qt.PointingHandCursor)
        btn_import_m.clicked.connect(self._on_import_markers)
        fw_lay.addWidget(btn_import_m)

        self.markers_card._lay.addWidget(footer_wrap)
        l_m.addWidget(self.markers_card)

        self._refresh_markers_list()

        self._register_search_entry(
            self.TAB_MARKERS, self.markers_card,
            title_key="tab_custom_markers", desc_key="hdr_custom_markers_sub",
            tab_key="tab_custom_markers",
            keywords_en="custom markers davinci color tag export import add marker",
        )

        # Compact bottom note + shortcut link bar
        card_m_info = SettingsCard(parent=page_markers)
        jump_wrap = QWidget(card_m_info)
        scope_transparent(jump_wrap)
        jw_lay = QHBoxLayout(jump_wrap)
        jw_lay.setContentsMargins(config.S(16), config.S(10), config.S(14), config.S(10))
        jw_lay.setSpacing(config.S(12))

        lbl_usage = QLabel(self.txt("desc_custom_markers_usage"), jump_wrap)
        lbl_usage.setWordWrap(True)
        lbl_usage.setStyleSheet(f"color: #969696; font-size: {config.FS_PX(9)}px; background: transparent; border: none;")
        jw_lay.addWidget(lbl_usage, 1)

        btn_sc_jump = QPushButton(self.txt("btn_manage_marker_shortcuts"), jump_wrap)
        btn_sc_jump.setObjectName("btn_ghost_sm")
        btn_sc_jump.setIcon(get_svg_icon(SVG_CHEVRON_RIGHT, size=12))
        btn_sc_jump.setIconSize(QSize(config.S(12), config.S(12)))
        btn_sc_jump.setFixedHeight(config.S(28))
        btn_sc_jump.setCursor(Qt.PointingHandCursor)
        btn_sc_jump.clicked.connect(lambda: self.open_section("shortcuts"))
        jw_lay.addWidget(btn_sc_jump, 0)
        card_m_info._lay.addWidget(jump_wrap)

        l_m.addWidget(card_m_info)

        self._register_search_entry(
            self.TAB_MARKERS, card_m_info,
            title_key="btn_manage_marker_shortcuts", desc_key="desc_custom_markers_usage",
            tab_key="tab_custom_markers",
            keywords_en="marker shortcut hotkey keybind file mode davinci resolve",
        )

        l_m.addStretch(1)
        return page_markers

    # ── PAGE 6: AI ENGINE ─────────────────────────────────────────────────

    def _build_page_ai_engine(self, prefs):
        self._current_building_page_idx = self.TAB_AI_ENGINE
        page_ai = QWidget()
        scope_transparent(page_ai, border_none=False)
        l_ai = QVBoxLayout(page_ai)
        l_ai.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_ai.setSpacing(config.S(12))

        l_ai.addWidget(SettingsPageHeader(self.txt("tab_ai_engine"), self.txt("hdr_ai_engine_sub"), parent=page_ai))

        # Card 1: Hardware & Compute
        l_ai.addWidget(SettingsSectionLabel(self.txt("sec_ai_hardware"), page_ai))
        card_hw = SettingsCard(parent=page_ai)

        _device_items = ["Auto", "CPU", "GPU"]
        self.dropdown_device = CustomDropdown(_device_items, parent=card_hw)
        self.dropdown_device.setFixedHeight(config.S(30))
        saved_device = prefs.get('device', 'auto').upper()
        if saved_device == 'AUTO':
            saved_device = 'Auto'
        self.dropdown_device.setText(saved_device if saved_device in _device_items else 'Auto')
        self._add_card_row(
            card_hw, "lbl_device", self.dropdown_device, 'Auto', self.dropdown_device.setValue,
            info_key="tt_ai_device", is_advanced=True, add_divider_above=False,
            section_key="sec_ai_hardware", tab_key="tab_ai_engine",
            options_static=_device_items, keywords_en="device cpu gpu cuda mlx hardware",
        )

        _compute_items = ["Auto", "float16", "int8", "float32", "int8_float16", "int8_float32"]
        self.dropdown_compute = CustomDropdown(_compute_items, parent=card_hw)
        self.dropdown_compute.setFixedHeight(config.S(30))
        saved_compute = prefs.get('ai_compute_type', 'Auto')
        self.dropdown_compute.setText(saved_compute if saved_compute in _compute_items else 'Auto')
        self._add_card_row(
            card_hw, "lbl_compute_type", self.dropdown_compute, 'Auto', self.dropdown_compute.setValue,
            info_key="tt_ai_compute_type", is_advanced=True,
            section_key="sec_ai_hardware", tab_key="tab_ai_engine",
            options_static=_compute_items, keywords_en="compute type precision float16 int8 float32",
        )

        l_ai.addWidget(card_hw)

        # Card 2: Audio Pre-Processing & Silence VAD (FFmpeg)
        l_ai.addSpacing(config.S(4))
        l_ai.addWidget(SettingsSectionLabel(self.txt("hdr_audio_preprocessing"), page_ai))
        card_audio = SettingsCard(parent=page_ai)

        def_thresh = config.DEFAULT_SETTINGS.get('silence_threshold_db', -42.0)
        self.spin_silence_thresh = CustomNumberInput(float(prefs.get('silence_threshold_db', def_thresh)), -80.0, -10.0, step=1.0, decimals=1, parent=card_audio)
        self._add_card_row(
            card_audio, "lbl_silence_threshold_db", self.spin_silence_thresh, def_thresh, self.spin_silence_thresh.setValue,
            info_key="tt_silence_threshold_db", is_advanced=True, add_divider_above=False,
            section_key="hdr_audio_preprocessing", tab_key="tab_ai_engine",
            keywords_en="silence threshold db ffmpeg audio",
        )

        def_pad = config.DEFAULT_SETTINGS.get('ui_spin_pad', 0.1)
        self.spin_silence_pad = CustomNumberInput(float(prefs.get('ui_spin_pad', def_pad)), 0.0, 2.0, step=0.05, decimals=2, parent=card_audio)
        self._add_card_row(
            card_audio, "lbl_padding_s", self.spin_silence_pad, def_pad, self.spin_silence_pad.setValue,
            info_key="tt_silence_keep", is_advanced=True,
            section_key="hdr_audio_preprocessing", tab_key="tab_ai_engine",
            keywords_en="silence padding keep buffer seconds",
        )

        def_min_dur = config.DEFAULT_SETTINGS.get('silence_min_dur', 0.2)
        self.spin_silence_min_dur = CustomNumberInput(float(prefs.get('silence_min_dur', def_min_dur)), 0.05, 5.0, step=0.05, decimals=2, parent=card_audio)
        self._add_card_row(
            card_audio, "lbl_min_silence_dur", self.spin_silence_min_dur, def_min_dur, self.spin_silence_min_dur.setValue,
            info_key="tt_min_silence_dur", is_advanced=True,
            section_key="hdr_audio_preprocessing", tab_key="tab_ai_engine",
            keywords_en="min silence duration seconds",
        )

        l_ai.addWidget(card_audio)

        # Card 3: Whisper Decoding Parameters
        l_ai.addSpacing(config.S(4))
        l_ai.addWidget(SettingsSectionLabel(self.txt("sec_ai_whisper"), page_ai))
        card_wh = SettingsCard(parent=page_ai)

        prompt_wrap = QWidget(card_wh)
        scope_transparent(prompt_wrap)
        pl_w = QVBoxLayout(prompt_wrap)
        pl_w.setContentsMargins(config.S(16), config.S(12), config.S(16), config.S(12))
        pl_w.setSpacing(config.S(6))

        lbl_prompt = QLabel(self.txt("lbl_initial_prompt"), prompt_wrap)
        lbl_prompt.setStyleSheet(f"color: #d8d8d8; font-size: {config.FS_PX(9.5)}px; background: transparent;")
        pl_w.addWidget(lbl_prompt)

        self.textedit_prompt = WrappingPlaceholderTextEdit()
        self.textedit_prompt.setMaximumHeight(config.S(78))
        saved_prompt = prefs.get('ai_initial_prompt', '').strip()
        auto_prompt = config.get_whisper_prompt_for_lang(prefs.get('lang', 'Auto'), gui_lang=prefs.get('gui_lang', 'en'))
        self.textedit_prompt.setPlaceholderText(auto_prompt)
        if saved_prompt and not config.is_default_whisper_prompt(saved_prompt):
            self.textedit_prompt.setPlainText(saved_prompt)
        else:
            self.textedit_prompt.setPlainText("")
        self.textedit_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: {SETTINGS_INPUT_BG};
                color: #e0e0e0;
                border: 1px solid {SETTINGS_INPUT_BORDER};
                border-radius: {config.S(4)}px;
                padding: {config.S(6)}px {config.S(8)}px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS_PX(9.5)}px;
            }}
        """)
        pl_w.addWidget(self.textedit_prompt)
        card_wh._lay.addWidget(prompt_wrap)

        self._register_search_entry(
            self.TAB_AI_ENGINE, prompt_wrap,
            title_key="lbl_initial_prompt", section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            is_advanced=True, keywords_en="whisper initial prompt verbatim fillers",
        )

        self.chk_vad_filter = ToggleSwitch(parent=card_wh)
        self.chk_vad_filter.setChecked(bool(prefs.get('ai_vad_filter', False)), animated=False)
        self._add_card_row(
            card_wh, "lbl_vad_filter", self.chk_vad_filter, False,
            lambda v: self.chk_vad_filter.setChecked(v, animated=True),
            info_key="tt_ai_vad_filter", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="vad voice activity detection silero",
        )

        self.chk_condition_prev = ToggleSwitch(parent=card_wh)
        self.chk_condition_prev.setChecked(bool(prefs.get('ai_condition_on_prev', False)), animated=False)
        self._add_card_row(
            card_wh, "lbl_condition_prev", self.chk_condition_prev, False,
            lambda v: self.chk_condition_prev.setChecked(v, animated=True),
            info_key="tt_ai_condition_prev", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="condition previous text context loop",
        )

        def_beam = config.DEFAULT_SETTINGS.get('ai_beam_size', 1)
        self.spin_beam_size = CustomNumberInput(int(prefs.get('ai_beam_size', def_beam)), 1, 10, step=1, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_beam_size", self.spin_beam_size, def_beam, self.spin_beam_size.setValue,
            info_key="tt_ai_beam_size", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="beam size search whisper",
        )

        def_temp = config.DEFAULT_SETTINGS.get('ai_temperature', 0.0)
        self.spin_temperature = CustomNumberInput(float(prefs.get('ai_temperature', def_temp)), 0.0, 1.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_temperature", self.spin_temperature, def_temp, self.spin_temperature.setValue,
            info_key="tt_ai_temperature", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="temperature sampling whisper",
        )

        def_logprob = config.DEFAULT_SETTINGS.get('ai_logprob_threshold', -0.8)
        self.spin_logprob = CustomNumberInput(float(prefs.get('ai_logprob_threshold', def_logprob)), -3.0, 0.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_logprob", self.spin_logprob, def_logprob, self.spin_logprob.setValue,
            info_key="tt_ai_logprob", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="logprob threshold whisper",
        )

        def_nospeech = config.DEFAULT_SETTINGS.get('ai_no_speech_threshold', 0.7)
        self.spin_no_speech = CustomNumberInput(float(prefs.get('ai_no_speech_threshold', def_nospeech)), 0.0, 1.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_no_speech", self.spin_no_speech, def_nospeech, self.spin_no_speech.setValue,
            info_key="tt_ai_no_speech", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="no speech threshold whisper",
        )

        def_patience = config.DEFAULT_SETTINGS.get('ai_patience', 1.0)
        self.spin_patience = CustomNumberInput(float(prefs.get('ai_patience', def_patience)), 0.0, 10.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_patience", self.spin_patience, def_patience, self.spin_patience.setValue,
            info_key="tt_ai_patience", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="patience beam search whisper",
        )

        def_comp = config.DEFAULT_SETTINGS.get('ai_compression_ratio_threshold', 2.4)
        self.spin_compression = CustomNumberInput(float(prefs.get('ai_compression_ratio_threshold', def_comp)), 0.0, 100.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_compression_ratio", self.spin_compression, def_comp, self.spin_compression.setValue,
            info_key="tt_ai_compression_ratio", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="compression ratio hallucination whisper",
        )

        def_no_rep = config.DEFAULT_SETTINGS.get('ai_no_repeat_ngram_size', 0)
        self.spin_no_repeat = CustomNumberInput(int(prefs.get('ai_no_repeat_ngram_size', def_no_rep)), 0, 100, step=1, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_no_repeat_ngram", self.spin_no_repeat, def_no_rep, self.spin_no_repeat.setValue,
            info_key="tt_ai_no_repeat_ngram", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="no repeat ngram whisper",
        )

        self.spin_length_penalty = CustomNumberInput(float(prefs.get('ai_length_penalty', 1.0)), 0.0, 10.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_length_penalty", self.spin_length_penalty, 1.0, self.spin_length_penalty.setValue,
            info_key="tt_ai_length_penalty", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="length penalty whisper",
        )

        self.spin_repetition_penalty = CustomNumberInput(float(prefs.get('ai_repetition_penalty', 1.0)), 1.0, 10.0, step=0.1, decimals=2, parent=card_wh)
        self._add_card_row(
            card_wh, "lbl_repetition_penalty", self.spin_repetition_penalty, 1.0, self.spin_repetition_penalty.setValue,
            info_key="tt_ai_repetition_penalty", is_advanced=True,
            section_key="sec_ai_whisper", tab_key="tab_ai_engine",
            keywords_en="repetition penalty whisper",
        )

        l_ai.addWidget(card_wh)
        l_ai.addStretch(1)
        return page_ai

    # ── PAGE 6: SUPPORT & FEEDBACK ────────────────────────────────────────

    def _build_page_support(self, prefs):
        self._current_building_page_idx = self.TAB_SUPPORT
        page_support = QWidget()
        scope_transparent(page_support, border_none=False)
        l_support = QVBoxLayout(page_support)
        l_support.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        l_support.setSpacing(config.S(12))

        l_support.addWidget(SettingsPageHeader(self.txt("tab_support"), self.txt("hdr_support_sub"), parent=page_support))

        form_card = SettingsCard(parent=page_support)
        form_inner = QWidget(form_card)
        scope_transparent(form_inner)
        fl = QVBoxLayout(form_inner)
        fl.setContentsMargins(config.S(18), config.S(16), config.S(18), config.S(16))
        fl.setSpacing(config.S(12))

        def _field_lbl(text: str, required: bool = False) -> QLabel:
            lbl = QLabel(f"{text} <span style='color: #23a559;'>*</span>" if required else text, form_inner)
            lbl.setTextFormat(Qt.RichText)
            lbl.setStyleSheet(
                f"color: #d8d8d8; font-size: {config.FS_PX(9.5)}px; font-weight: 600; "
                f"background: transparent; border: none;"
            )
            return lbl

        # Row 1: Category + Email side by side
        top_grid = QHBoxLayout()
        top_grid.setSpacing(config.S(12))

        col_cat = QVBoxLayout()
        col_cat.setSpacing(config.S(5))
        col_cat.addWidget(_field_lbl(self.txt("lbl_support_category")))
        self._support_cat_items = [
            ("Bug", self.txt("cat_support_bug")),
            ("Feature", self.txt("cat_support_feature")),
            ("Question", self.txt("cat_support_question")),
        ]
        self.combo_support_category = CustomDropdown([lbl for _, lbl in self._support_cat_items], parent=form_inner)
        self.combo_support_category.setText(self._support_cat_items[0][1])
        self.combo_support_category.setFixedHeight(config.S(32))
        col_cat.addWidget(self.combo_support_category)
        top_grid.addLayout(col_cat, 1)

        col_email = QVBoxLayout()
        col_email.setSpacing(config.S(5))
        col_email.addWidget(_field_lbl(self.txt("lbl_support_email_field")))
        self.input_support_email = QLineEdit(form_inner)
        self.input_support_email.setPlaceholderText(self.txt("ph_support_email"))
        self.input_support_email.setFixedHeight(config.S(32))
        col_email.addWidget(self.input_support_email)
        top_grid.addLayout(col_email, 1)

        fl.addLayout(top_grid)

        # Subject
        col_title = QVBoxLayout()
        col_title.setSpacing(config.S(5))
        col_title.addWidget(_field_lbl(self.txt("lbl_support_title_field"), required=True))
        self.input_support_title = QLineEdit(form_inner)
        self.input_support_title.setPlaceholderText(self.txt("lbl_support_title"))
        self.input_support_title.setFixedHeight(config.S(32))
        col_title.addWidget(self.input_support_title)
        fl.addLayout(col_title)

        # Description
        col_body = QVBoxLayout()
        col_body.setSpacing(config.S(5))
        col_body.addWidget(_field_lbl(self.txt("lbl_support_body_field"), required=True))
        self.input_support_body = WrappingPlaceholderTextEdit(form_inner)
        self.input_support_body.setPlaceholderText(self.txt("lbl_support_body"))
        self.input_support_body.setMinimumHeight(config.S(96))
        col_body.addWidget(self.input_support_body)
        fl.addLayout(col_body)

        # Screenshots Drop/Paste + Thumbnail Gallery
        col_imgs = QVBoxLayout()
        col_imgs.setSpacing(config.S(6))
        col_imgs.addWidget(_field_lbl(self.txt("lbl_support_screenshots")))

        self.support_attachments = []
        self._support_dropzone = SupportDropZone(
            hint_text=self.txt("hint_support_drop_paste"),
            btn_text=self.txt("btn_add_screenshots"),
            parent=form_inner,
        )
        col_imgs.addWidget(self._support_dropzone)

        self.w_attachments_list = QWidget(form_inner)
        scope_transparent(self.w_attachments_list)
        self.l_attachments_list = FlowLayout(self.w_attachments_list, margin=0, hSpacing=config.S(8), vSpacing=config.S(8))
        col_imgs.addWidget(self.w_attachments_list)
        self.w_attachments_list.hide()

        fl.addLayout(col_imgs)

        # Validation border reset on typing
        _normal_title_ss = (
            f"background-color: {SETTINGS_INPUT_BG}; color: {config.INPUT_FG}; "
            f"border: 1px solid {SETTINGS_INPUT_BORDER}; border-radius: {config.S(4)}px; padding: {config.S(4)}px {config.S(8)}px;"
        )
        _err_ss = (
            f"background-color: {SETTINGS_INPUT_BG}; color: {config.INPUT_FG}; "
            f"border: 1px solid #ed4245; border-radius: {config.S(4)}px; padding: {config.S(4)}px {config.S(8)}px;"
        )

        self.lbl_support_status = QLabel("", form_inner)
        self.lbl_support_status.setWordWrap(True)
        self.lbl_support_status.setStyleSheet(f"color: #9a9a9a; font-size: {config.FS_PX(9)}px; background: transparent;")
        self.lbl_support_status.hide()

        def _clear_title_err(_=None):
            self.input_support_title.setStyleSheet("")
            if self.lbl_support_status.property("is_err"):
                self.lbl_support_status.hide()

        def _clear_body_err():
            self.input_support_body.setStyleSheet("")
            if self.lbl_support_status.property("is_err"):
                self.lbl_support_status.hide()

        self.input_support_title.textChanged.connect(_clear_title_err)
        self.input_support_body.textChanged.connect(_clear_body_err)

        def _render_attachments():
            while self.l_attachments_list.count():
                child = self.l_attachments_list.takeAt(0)
                if child and child.widget():
                    child.widget().deleteLater()

            if not self.support_attachments:
                self.w_attachments_list.hide()
                return

            self.w_attachments_list.show()
            for p in list(self.support_attachments):
                card_t = AttachmentThumbCard(
                    p,
                    preview_tooltip=self.txt("tt_support_preview_image"),
                    parent=self.w_attachments_list,
                )
                card_t.removeRequested.connect(lambda path_rem: _remove_attachment(path_rem))
                card_t.previewRequested.connect(lambda path_prev: _preview_attachment(path_prev))
                self.l_attachments_list.addWidget(card_t)
            self.w_attachments_list.updateGeometry()

        self._render_attachments_fn = _render_attachments

        def _remove_attachment(path_rem: str):
            if path_rem in self.support_attachments:
                self.support_attachments.remove(path_rem)
                _render_attachments()

        def _preview_attachment(path_prev: str):
            dlg_prev = ScreenshotPreviewDialog(path_prev, self.txt("lbl_support_preview_title"), parent=self)
            dlg_prev.exec()

        def _add_image_paths(paths: list[str]):
            added = False
            for f in paths:
                if len(self.support_attachments) >= _MAX_SUPPORT_SCREENSHOTS:
                    self.lbl_support_status.setProperty("is_err", True)
                    self.lbl_support_status.setText(self.txt("msg_support_max_images", max=_MAX_SUPPORT_SCREENSHOTS))
                    self.lbl_support_status.setStyleSheet(f"color: #f4a641; font-size: {config.FS_PX(9)}px; background: transparent;")
                    self.lbl_support_status.show()
                    break
                if f and f not in self.support_attachments:
                    self.support_attachments.append(f)
                    added = True
            if added:
                _render_attachments()

        def _browse_images():
            from PySide6.QtWidgets import QFileDialog
            files, _ = QFileDialog.getOpenFileNames(
                self, self.txt("btn_add_screenshots"), "", "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if files:
                _add_image_paths(files)

        self._support_dropzone.browseClicked.connect(_browse_images)
        self._support_dropzone.filesDropped.connect(_add_image_paths)

        # Ctrl+V clipboard screenshot paste handler on Support page
        class _PasteFilter(QObject):
            def eventFilter(self_f, obj, ev):
                if ev.type() == QEvent.KeyPress and (ev.modifiers() & Qt.ControlModifier) and ev.key() == Qt.Key_V:
                    cb = QGuiApplication.clipboard()
                    if cb and cb.mimeData() and cb.mimeData().hasImage():
                        img = cb.image()
                        saved = save_clipboard_image_temp(img)
                        if saved:
                            self._temp_clipboard_images.append(saved)
                            _add_image_paths([saved])
                            return True
                return False

        self._support_paste_filter = _PasteFilter(page_support)
        page_support.installEventFilter(self._support_paste_filter)
        self.input_support_body.installEventFilter(self._support_paste_filter)
        self.input_support_title.installEventFilter(self._support_paste_filter)

        # Mandatory sanitized logs notice banner (replaces old optional checkbox)
        notice_box = QFrame(form_inner)
        notice_box.setObjectName("SupportNoticeBox")
        notice_box.setStyleSheet(
            f"QFrame#SupportNoticeBox {{ background-color: #18231d; border: 1px solid #274032; border-radius: {config.S(6)}px; }}"
        )
        nl = QHBoxLayout(notice_box)
        nl.setContentsMargins(config.S(12), config.S(10), config.S(12), config.S(10))
        nl.setSpacing(config.S(10))

        lbl_shield = QLabel(notice_box)
        lbl_shield.setFixedSize(config.S(18), config.S(18))
        lbl_shield.setPixmap(get_svg_icon(SVG_SHIELD, size=18).pixmap(config.S(18), config.S(18)))
        lbl_shield.setStyleSheet("background: transparent; border: none;")
        nl.addWidget(lbl_shield, 0, Qt.AlignTop)

        lbl_logs_note = QLabel(self.txt("msg_support_logs_mandatory"), notice_box)
        lbl_logs_note.setWordWrap(True)
        lbl_logs_note.setStyleSheet(
            f"color: #b7d7c2; font-size: {config.FS_PX(8.8)}px; background: transparent; border: none;"
        )
        nl.addWidget(lbl_logs_note, 1)
        fl.addWidget(notice_box)

        fl.addWidget(self.lbl_support_status)

        # Submit row inside form card
        w_send = QWidget(form_inner)
        scope_transparent(w_send)
        l_send = QHBoxLayout(w_send)
        l_send.setContentsMargins(0, config.S(4), 0, 0)
        l_send.addStretch()

        btn_send = QPushButton(self.txt("btn_send_report"), w_send)
        self.btn_send_report = btn_send
        btn_send.setObjectName("btn_apply")
        btn_send.setFixedHeight(config.S(34))
        btn_send.setMinimumWidth(config.S(140))
        btn_send.setCursor(Qt.PointingHandCursor)

        def _send_report():
            raw_title = self.input_support_title.text().strip()
            body = self.input_support_body.toPlainText().strip()
            email = self.input_support_email.text().strip()

            missing = False
            if not raw_title:
                self.input_support_title.setStyleSheet(_err_ss)
                missing = True
            if not body:
                self.input_support_body.setStyleSheet(_err_ss)
                missing = True
            if missing:
                self.lbl_support_status.setProperty("is_err", True)
                self.lbl_support_status.setText(self.txt("msg_support_validation_required"))
                self.lbl_support_status.setStyleSheet(f"color: #ff6b6b; font-size: {config.FS_PX(9)}px; background: transparent;")
                self.lbl_support_status.show()
                return

            sel_cat_label = self.combo_support_category.currentText()
            cat_tag = next((tag for tag, lbl in self._support_cat_items if lbl == sel_cat_label), "Bug")
            tagged_title = f"[{cat_tag}] {raw_title}"

            btn_send.setEnabled(False)
            btn_send.setText(self.txt("msg_support_sending"))
            self.lbl_support_status.setProperty("is_err", False)
            self.lbl_support_status.setText(self.txt("msg_support_sending"))
            self.lbl_support_status.setStyleSheet(f"color: #aaaaaa; font-size: {config.FS_PX(9)}px; background: transparent;")
            self.lbl_support_status.show()

            attachments = list(self.support_attachments)

            class SendSignals(QObject):
                finished = Signal(bool, str)

            signals = SendSignals(self)

            def _worker():
                import zipfile, tempfile, platform
                from osdoc import log_info, log_error
                from startup.crash_report import post_support_report, sanitize_crash_text, _MAX_LOG_BYTES

                tmp_logs = ""
                src_dir = getattr(self.engine.os_doc, 'install_dir', None)
                try:
                    fd, tmp_logs = tempfile.mkstemp(suffix='.zip', prefix='bw_logs_')
                    os.close(fd)
                    with zipfile.ZipFile(tmp_logs, 'w', zipfile.ZIP_DEFLATED) as zf:
                        # Sanitized system metadata
                        try:
                            os_sum = f"{platform.system()} {platform.release()} ({platform.machine()})".strip()
                            res_info = {}
                            if hasattr(self.engine, 'os_doc') and hasattr(self.engine.os_doc, 'get_resolve_edition_info'):
                                res_info = self.engine.os_doc.get_resolve_edition_info() or {}
                            sys_lines = [
                                f"Category: {cat_tag}",
                                f"AppVersion: {getattr(config, 'VERSION', 'Unknown')}",
                                f"OS: {os_sum}",
                                f"Python: {sys.version.split()[0]}",
                                f"UI Scale: {getattr(config, 'UI_SCALE_PERCENT', 100)}% ({getattr(config, 'UI_SCALE_MODE', 'auto')})",
                                f"Resolve: {res_info.get('edition', 'Unknown')} {res_info.get('version', '')}".strip(),
                            ]
                            zf.writestr("system_info.txt", sanitize_crash_text("\n".join(sys_lines), src_dir=src_dir).encode("utf-8"))
                        except Exception:
                            pass

                        # Mandatory sanitized diagnostic log (tail 256 KB, matching crash_report)
                        l_file = getattr(self.engine.os_doc, 'log_file', '')
                        if l_file and os.path.isfile(l_file):
                            try:
                                sz = os.path.getsize(l_file)
                                with open(l_file, "rb") as lf:
                                    if sz > _MAX_LOG_BYTES:
                                        lf.seek(sz - _MAX_LOG_BYTES)
                                    raw_log = lf.read().decode("utf-8", errors="replace")
                                clean_log = sanitize_crash_text(raw_log, src_dir=src_dir)
                                zf.writestr(os.path.basename(l_file), clean_log.encode("utf-8", errors="replace"))
                            except Exception:
                                pass

                        # Mandatory sanitized configuration files
                        inst_dir = getattr(self.engine.os_doc, 'install_dir', '')
                        u_file = getattr(self.engine.os_doc, 'user_file', os.path.join(inst_dir, 'user.json'))
                        s_file = getattr(self.engine.os_doc, 'settings_file', os.path.join(inst_dir, 'settings.json'))
                        p_file = getattr(self.engine.os_doc, 'legacy_pref_file', os.path.join(inst_dir, 'pref.json'))
                        for cfile, p in [('user.json', u_file), ('settings.json', s_file), ('pref.json', p_file)]:
                            if p and os.path.isfile(p):
                                try:
                                    with open(p, "r", encoding="utf-8", errors="replace") as cf:
                                        clean_cfg = sanitize_crash_text(cf.read(), src_dir=src_dir)
                                    zf.writestr(cfile, clean_cfg.encode("utf-8", errors="replace"))
                                except Exception:
                                    pass

                        # Resized JPEG screenshots
                        from PySide6.QtGui import QImage
                        for i, p in enumerate(attachments):
                            if os.path.exists(p):
                                img = QImage(p)
                                if not img.isNull():
                                    if img.width() > 1920 or img.height() > 1080:
                                        img = img.scaled(1920, 1080, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                    fd_img, tmp_img = tempfile.mkstemp(suffix='.jpg')
                                    os.close(fd_img)
                                    img.save(tmp_img, "JPG", 75)
                                    zf.write(tmp_img, f"screenshot_{i+1}.jpg")
                                    try:
                                        os.remove(tmp_img)
                                    except Exception:
                                        pass
                                else:
                                    zf.write(p, f"screenshot_{i+1}{os.path.splitext(p)[1]}")

                    webhook_url = getattr(config, 'SUPPORT_WEBHOOK_URL', '')
                    if not webhook_url:
                        import time
                        time.sleep(0.3)
                        log_info("Webhook URL not defined in config.py, skipping actual HTTP POST.")
                        return True, ""

                    zip_bytes = None
                    if os.path.exists(tmp_logs):
                        with open(tmp_logs, "rb") as f_zip:
                            zip_bytes = f_zip.read()

                    clean_body = body
                    success, detail = post_support_report(
                        webhook_url,
                        version=getattr(config, 'VERSION', 'Unknown'),
                        title=tagged_title,
                        body=clean_body,
                        email=email,
                        zip_bytes=zip_bytes,
                        timeout=30,
                    )
                    if not success:
                        log_error(f"Support report send failed: {detail}")
                    return success, detail
                except Exception as e:
                    log_error(f"Support report exception: {e}")
                    return False, str(e)
                finally:
                    if tmp_logs and os.path.exists(tmp_logs):
                        try:
                            os.remove(tmp_logs)
                        except Exception:
                            pass

            def _thread_target():
                success, msg = _worker()
                signals.finished.emit(success, msg)

            def _on_finished(success, msg):
                btn_send.setEnabled(True)
                btn_send.setText(self.txt("btn_send_report"))
                if success:
                    self.lbl_support_status.setProperty("is_err", False)
                    self.lbl_support_status.setText(self.txt("msg_support_sent_ok"))
                    self.lbl_support_status.setStyleSheet(f"color: #39d377; font-size: {config.FS_PX(9.2)}px; font-weight: bold; background: transparent;")
                    self.lbl_support_status.show()

                    self.input_support_title.clear()
                    self.input_support_body.clear()
                    self.input_support_email.clear()
                    self.support_attachments.clear()
                    _render_attachments()
                    QTimer.singleShot(4500, lambda: self.lbl_support_status.hide() if not self.lbl_support_status.property("is_err") else None)
                else:
                    self.lbl_support_status.setProperty("is_err", True)
                    self.lbl_support_status.setText(self.txt("msg_support_send_error", error=msg[:120]))
                    self.lbl_support_status.setStyleSheet(f"color: #ff6b6b; font-size: {config.FS_PX(9)}px; background: transparent;")
                    self.lbl_support_status.show()
                    CustomMsgBox(
                        self,
                        self.txt("tab_support"),
                        self.txt("msg_support_send_error", error=msg[:120]),
                        self.txt("btn_ok")
                    ).exec()

            signals.finished.connect(_on_finished)
            import threading
            threading.Thread(target=_thread_target, daemon=True).start()

        btn_send.clicked.connect(_send_report)
        l_send.addWidget(btn_send)
        fl.addWidget(w_send)

        form_card._lay.addWidget(form_inner)
        l_support.addWidget(form_card)

        self._register_search_entry(
            self.TAB_SUPPORT, form_card,
            title_key="tab_support", desc_key="hdr_support_sub",
            tab_key="tab_support",
            options_keys=["cat_support_bug", "cat_support_feature", "cat_support_question"],
            keywords_en="support feedback bug report crash contact logs email screenshot",
        )

        l_support.addStretch(1)
        return page_support

    # ── PAGE 7: ABOUT & PRIVACY ───────────────────────────────────────────

    def _build_page_about(self, prefs):
        self._current_building_page_idx = self.TAB_ABOUT
        page_about = QWidget()
        scope_transparent(page_about, border_none=False)
        layout = QVBoxLayout(page_about)
        layout.setContentsMargins(config.S(24), config.S(20), config.S(24), config.S(24))
        layout.setSpacing(config.S(12))

        layout.addWidget(SettingsPageHeader(self.txt("tab_about"), self.txt("hdr_about_sub"), parent=page_about))

        # Card 1: Clean App Identity & Short About + Links (no cluttered badge or nested CTA)
        hero_card = SettingsCard(parent=page_about)

        hero_top = QWidget(hero_card)
        scope_transparent(hero_top)
        ht_lay = QHBoxLayout(hero_top)
        ht_lay.setContentsMargins(config.S(18), config.S(16), config.S(18), config.S(14))
        ht_lay.setSpacing(config.S(14))

        lbl_logo = QLabel(hero_top)
        lbl_logo.setFixedSize(config.S(42), config.S(42))
        app_ico = _app_icon(prefs.get("app_icon"))
        if not app_ico.isNull():
            lbl_logo.setPixmap(app_ico.pixmap(config.S(42), config.S(42)))
        lbl_logo.setStyleSheet("background: transparent; border: none;")
        ht_lay.addWidget(lbl_logo, 0, Qt.AlignVCenter)

        hero_txt = QVBoxLayout()
        hero_txt.setSpacing(config.S(3))

        lbl_app = QLabel(f"BadWords v{config.VERSION}", hero_top)
        lbl_app.setStyleSheet(f"font-size: {config.FS_PX(13.5)}px; font-weight: bold; color: #ffffff; background: transparent;")
        hero_txt.addWidget(lbl_app)

        lbl_tagline = QLabel(self.txt("about_tagline"), hero_top)
        lbl_tagline.setWordWrap(True)
        lbl_tagline.setStyleSheet(f"font-size: {config.FS_PX(9.5)}px; color: #b5b5b5; background: transparent;")
        hero_txt.addWidget(lbl_tagline)

        ht_lay.addLayout(hero_txt, 1)
        hero_card._lay.addWidget(hero_top)
        hero_card.add_divider()

        # Short developer note + quick links
        story_box = QWidget(hero_card)
        scope_transparent(story_box)
        sb_lay = QVBoxLayout(story_box)
        sb_lay.setContentsMargins(config.S(18), config.S(14), config.S(18), config.S(16))
        sb_lay.setSpacing(config.S(12))

        lbl_st_title = QLabel(self.txt("about_story_title"), story_box)
        lbl_st_title.setStyleSheet(f"font-size: {config.FS_PX(10.5)}px; font-weight: bold; color: #ffffff; background: transparent;")
        sb_lay.addWidget(lbl_st_title)

        lbl_st_body = QLabel(self.txt("about_story_body"), story_box)
        lbl_st_body.setWordWrap(True)
        lbl_st_body.setStyleSheet(f"font-size: {config.FS_PX(9.8)}px; color: #bbbbbb; line-height: 1.35; background: transparent;")
        sb_lay.addWidget(lbl_st_body)

        links_row = QHBoxLayout()
        links_row.setSpacing(config.S(8))

        btn_gh = QPushButton(self.txt("btn_about_github"), story_box)
        btn_gh.setObjectName("btn_ghost_sm")
        btn_gh.setFixedHeight(config.S(28))
        btn_gh.setCursor(Qt.PointingHandCursor)
        btn_gh.clicked.connect(lambda: self._open_external_url("https://github.com/veritus-git/BadWords"))
        links_row.addWidget(btn_gh)

        btn_rep = QPushButton(self.txt("btn_about_report"), story_box)
        btn_rep.setObjectName("btn_ghost_sm")
        btn_rep.setFixedHeight(config.S(28))
        btn_rep.setCursor(Qt.PointingHandCursor)
        btn_rep.clicked.connect(lambda: self.open_section("support"))
        links_row.addWidget(btn_rep)

        btn_em = QPushButton(self.txt("btn_about_email"), story_box)
        btn_em.setObjectName("btn_ghost_sm")
        btn_em.setFixedHeight(config.S(28))
        btn_em.setCursor(Qt.PointingHandCursor)
        btn_em.clicked.connect(lambda: self._open_external_url("mailto:badwords.git@gmail.com"))
        links_row.addWidget(btn_em)

        btn_lic = QPushButton(self.txt("btn_about_license"), story_box)
        btn_lic.setObjectName("btn_ghost_sm")
        btn_lic.setFixedHeight(config.S(28))
        btn_lic.setCursor(Qt.PointingHandCursor)
        btn_lic.clicked.connect(lambda: self._open_external_url("https://github.com/veritus-git/BadWords/blob/main/LICENSE"))
        links_row.addWidget(btn_lic)

        links_row.addStretch()
        sb_lay.addLayout(links_row)
        hero_card._lay.addWidget(story_box)
        layout.addWidget(hero_card)

        # Card 2: Dedicated Separate Support / Buy Me a Coffee Card
        coffee_cta = QFrame(page_about)
        coffee_cta.setObjectName("AboutCoffeeCta")
        coffee_cta.setStyleSheet(
            f"QFrame#AboutCoffeeCta {{ background-color: #192920; border: 1px solid #29523b; border-radius: {config.S(8)}px; }}"
        )
        cc_lay = QHBoxLayout(coffee_cta)
        cc_lay.setContentsMargins(config.S(18), config.S(14), config.S(18), config.S(14))
        cc_lay.setSpacing(config.S(14))

        cc_txt = QVBoxLayout()
        cc_txt.setSpacing(config.S(3))
        lbl_cf_t = QLabel(self.txt("about_coffee_title"), coffee_cta)
        lbl_cf_t.setStyleSheet(f"color: #ffffff; font-size: {config.FS_PX(10.5)}px; font-weight: bold; background: transparent; border: none;")
        lbl_cf_d = QLabel(self.txt("about_coffee_desc"), coffee_cta)
        lbl_cf_d.setWordWrap(True)
        lbl_cf_d.setStyleSheet(f"color: #a9d6bc; font-size: {config.FS_PX(9.5)}px; background: transparent; border: none;")
        cc_txt.addWidget(lbl_cf_t)
        cc_txt.addWidget(lbl_cf_d)
        cc_lay.addLayout(cc_txt, 1)

        btn_coffee = QPushButton(self.txt("link_coffee_label"), coffee_cta)
        btn_coffee.setObjectName("btn_apply")
        btn_coffee.setIcon(get_svg_icon(SVG_COFFEE, size=15))
        btn_coffee.setIconSize(QSize(config.S(15), config.S(15)))
        btn_coffee.setFixedHeight(config.S(34))
        btn_coffee.setCursor(Qt.PointingHandCursor)
        btn_coffee.clicked.connect(lambda: self._open_external_url("https://buymeacoffee.com/badwords"))
        cc_lay.addWidget(btn_coffee, 0, Qt.AlignVCenter)
        layout.addWidget(coffee_cta)

        self._register_search_entry(
            self.TAB_ABOUT, coffee_cta,
            title_key="link_coffee_label", desc_key="about_coffee_desc",
            tab_key="tab_about", keywords_en="donate coffee support developer author github license",
        )

        # Card 2: Privacy & Telemetry (with live animated dimming on geo when telemetry is OFF)
        layout.addSpacing(config.S(4))
        layout.addWidget(SettingsSectionLabel(self.txt("header_privacy_telemetry"), page_about))
        card_priv = SettingsCard(parent=page_about)

        raw_user_data = getattr(self.engine.os_doc, 'user_data', {})
        user_data = raw_user_data if isinstance(raw_user_data, dict) else {}

        self.chk_telemetry_opt_in = ToggleSwitch()
        telem_on = bool(user_data.get('telemetry_opt_in', False))
        self.chk_telemetry_opt_in.setChecked(telem_on, animated=False)
        self._add_card_row(
            card_priv, "chk_telemetry_opt_in", self.chk_telemetry_opt_in, False,
            lambda v: self.chk_telemetry_opt_in.setChecked(v, animated=True),
            info_key="tt_telemetry_opt_in", add_divider_above=False,
            section_key="header_privacy_telemetry", tab_key="tab_about",
            keywords_en="telemetry anonymous analytics privacy ping",
        )

        self.chk_telemetry_geo = ToggleSwitch()
        geo_val = user_data.get('telemetry_geo')
        self.chk_telemetry_geo.setChecked(True if geo_val is None else bool(geo_val), animated=False)
        self._row_telemetry_geo = self._add_card_row(
            card_priv, "chk_telemetry_geo", self.chk_telemetry_geo, True,
            lambda v: self.chk_telemetry_geo.setChecked(v, animated=True),
            info_key="tt_telemetry_geo",
            section_key="header_privacy_telemetry", tab_key="tab_about",
            keywords_en="geolocation location country city telemetry",
        )

        # Live smooth dimming animation for telemetry geo row when telemetry is OFF
        self._geo_dim_anim = QVariantAnimation(self)
        self._geo_dim_anim.setDuration(220)
        self._geo_dim_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._geo_dim_anim.valueChanged.connect(self._apply_geo_dim_opacity)
        self._curr_geo_op = 1.0

        def _on_telem_opt_changed(checked: bool):
            self._update_geo_availability(bool(checked), animated=True)

        self.chk_telemetry_opt_in.toggled.connect(_on_telem_opt_changed)
        self._update_geo_availability(telem_on, animated=False)

        raw_crash = user_data.get('auto_crash_report', prefs.get('auto_crash_report'))
        crash_checked = True if raw_crash is None else bool(raw_crash)
        self.chk_auto_crash_report = ToggleSwitch()
        self.chk_auto_crash_report.setChecked(crash_checked, animated=False)
        self._add_card_row(
            card_priv, "chk_auto_crash_report", self.chk_auto_crash_report, True,
            lambda v: self.chk_auto_crash_report.setChecked(v, animated=True),
            info_key="tt_auto_crash_report",
            section_key="header_privacy_telemetry", tab_key="tab_about",
            keywords_en="automatic crash error reports privacy logs",
        )

        layout.addWidget(card_priv)
        layout.addStretch(1)
        return page_about

    def _apply_auto_update_dim_opacity(self, val: float):
        self._curr_upd_op = float(val)
        is_translucent = (val < 0.9)
        row_w = getattr(self, "_row_auto_update_on_start", None)
        if row_w is not None:
            lbl_w = getattr(row_w, "_label_widget", None)
            if lbl_w is not None:
                lbl_w.setStyleSheet(
                    f"color: {_blend_hex('#e4e4e4', SETTINGS_CARD_BG, val)}; "
                    f"font-size: {config.FS_PX(10)}px; background: transparent; border: none;"
                )
        if hasattr(self, "tgl_auto_update_on_start"):
            self.tgl_auto_update_on_start.setAttribute(Qt.WA_TransparentForMouseEvents, is_translucent)
            if hasattr(self.tgl_auto_update_on_start, "set_opacity"):
                self.tgl_auto_update_on_start.set_opacity(val)

    def _update_auto_update_availability(self, enabled: bool, animated: bool = False):
        if hasattr(self, "tgl_auto_update_on_start"):
            self.tgl_auto_update_on_start.set_blocked(not enabled)
        target_op = 1.0 if enabled else 0.35
        if animated and self.isVisible():
            self._upd_dim_anim.stop()
            self._upd_dim_anim.setStartValue(self._curr_upd_op)
            self._upd_dim_anim.setEndValue(target_op)
            self._curr_upd_op = target_op
            self._upd_dim_anim.start()
        else:
            if hasattr(self, "_upd_dim_anim"):
                self._upd_dim_anim.stop()
            self._curr_upd_op = target_op
            self._apply_auto_update_dim_opacity(target_op)

    def _apply_geo_dim_opacity(self, val: float):
        self._curr_geo_op = float(val)
        is_translucent = (val < 0.9)
        row_w = getattr(self, "_row_telemetry_geo", None)
        if row_w is not None:
            lbl_w = getattr(row_w, "_label_widget", None)
            if lbl_w is not None:
                lbl_w.setStyleSheet(
                    f"color: {_blend_hex('#e4e4e4', SETTINGS_CARD_BG, val)}; "
                    f"font-size: {config.FS_PX(10)}px; background: transparent; border: none;"
                )
        if hasattr(self, "chk_telemetry_geo"):
            self.chk_telemetry_geo.setAttribute(Qt.WA_TransparentForMouseEvents, is_translucent)
            if hasattr(self.chk_telemetry_geo, "set_opacity"):
                self.chk_telemetry_geo.set_opacity(val)

    def _update_geo_availability(self, enabled: bool, animated: bool = False):
        if hasattr(self, "chk_telemetry_geo"):
            self.chk_telemetry_geo.set_blocked(not enabled)
        target_op = 1.0 if enabled else 0.35
        if animated and self.isVisible():
            self._geo_dim_anim.stop()
            self._geo_dim_anim.setStartValue(self._curr_geo_op)
            self._geo_dim_anim.setEndValue(target_op)
            self._curr_geo_op = target_op
            self._geo_dim_anim.start()
        else:
            if hasattr(self, "_geo_dim_anim"):
                self._geo_dim_anim.stop()
            self._curr_geo_op = target_op
            self._apply_geo_dim_opacity(target_op)

    # ── Reset All Defaults ────────────────────────────────────────────────

    def _restore_all_defaults(self):
        msg_box = CustomMsgBox(
            self,
            self.txt('msg_restore_title'),
            self.txt('msg_restore_desc'),
            self.txt('btn_yes'),
            self.txt('btn_no'),
            checkbox_text=self.txt('chk_delete_custom_markers'),
            checkbox_checked=False
        )
        if msg_box.exec() == QDialog.Accepted:
            self._ensure_all_pages_built()
            old_prefs = self.engine.load_preferences() or {}
            delete_markers = msg_box.is_checkbox_checked()
            default_state = dict(config.DEFAULT_SETTINGS)
            default_state['gui_lang'] = old_prefs.get('gui_lang', 'en')
            default_state['settings_view_mode'] = old_prefs.get('settings_view_mode', 'basic')
            default_state['shortcuts'] = dict(config.DEFAULT_SETTINGS.get('shortcuts', {}))

            if not delete_markers:
                kept_markers = list(old_prefs.get('custom_markers', []))
                default_state['custom_markers'] = kept_markers
                old_sc = old_prefs.get('shortcuts', {}) or {}
                for m in kept_markers:
                    mk = f"custom_marker_{m.get('name', '')}"
                    if mk in old_sc:
                        default_state['shortcuts'][mk] = old_sc[mk]
            else:
                default_state['custom_markers'] = []
                self.current_custom_markers = []

            self.engine.save_preferences(default_state)

            # Reset user-privacy toggles in user.json without leaking DEFAULT_USER_DATA keys into settings.json
            os_doc = getattr(self.engine, 'os_doc', None)
            if os_doc is not None and hasattr(os_doc, 'set_telemetry_pref'):
                try:
                    os_doc.set_telemetry_pref("telemetry_opt_in", False)
                    os_doc.set_telemetry_pref("telemetry_geo", True)
                    os_doc.set_telemetry_pref("auto_crash_report", True)
                except Exception:
                    pass

            restore_payload = dict(default_state)
            restore_payload['telemetry_opt_in'] = False
            restore_payload['telemetry_geo'] = True
            restore_payload['auto_crash_report'] = True

            self.initial_prefs = self.engine.load_preferences() or {}
            self._restore_state_dict(restore_payload, include_advanced=True)
            if delete_markers:
                self._save_markers_and_refresh_main()
            if hasattr(self, '_initial_state') and isinstance(self._initial_state, dict):
                self._initial_state = self._get_current_state_dict()
            self._apply_live_ui_scale('auto', None)
            CustomMsgBox(self, self.txt('msg_title_settings'), self.txt('msg_restart_required'), self.txt('btn_ok')).exec()
            try:
                self._refresh_markers_list()
            except Exception:
                pass

    # ── Custom Markers Helpers (Dedicated Tab + Shortcut Dialog Support) ────

    def _refresh_markers_list(self):
        """Rebuild minimalist flush marker rows with vector color swatches, muted color labels, and clean hover controls."""
        if not hasattr(self, '_markers_layout') or self._markers_layout is None:
            return
        layout = self._markers_layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        if hasattr(self, '_markers_inner') and self._markers_inner:
            for child in self._markers_inner.findChildren(MarkerRowWidget):
                child.hide()
                child.setParent(None)
                child.deleteLater()

        row_h = config.S(46)
        count = len(self.current_custom_markers or [])
        if hasattr(self, '_markers_scroll') and self._markers_scroll is not None:
            if count == 0:
                self._markers_scroll.setFixedHeight(config.S(68))
            else:
                target_h = min(config.S(310), count * row_h + config.S(8))
                self._markers_scroll.setFixedHeight(target_h)

        if not self.current_custom_markers:
            empty_box = QWidget(self._markers_inner)
            scope_transparent(empty_box)
            el = QVBoxLayout(empty_box)
            el.setContentsMargins(config.S(16), config.S(18), config.S(16), config.S(18))
            el.setSpacing(0)
            lbl_empty = QLabel(self.txt("empty_custom_markers"), empty_box)
            lbl_empty.setWordWrap(True)
            lbl_empty.setAlignment(Qt.AlignCenter)
            lbl_empty.setStyleSheet(f"color: #7d7d7d; font-size: {config.FS_PX(9.2)}px; background: transparent;")
            el.addWidget(lbl_empty)
            layout.addWidget(empty_box)
            if hasattr(self, '_refresh_custom_marker_shortcuts'):
                self._refresh_custom_marker_shortcuts()
            return

        total = len(self.current_custom_markers)
        for idx, m in enumerate(self.current_custom_markers):
            name = m.get('name', '?')
            color = m.get('color', '')
            hex_col = config.RESOLVE_COLORS_HEX.get(color, '#FFFFFF')
            is_builtin = color.lower() in ["green", "blue"]
            is_last = (idx == total - 1)
            row_border = "border-bottom: none;" if is_last else f"border-bottom: 1px solid {SETTINGS_DIVIDER_COL};"

            row_ss = f"""
                QWidget#marker_row {{
                    background-color: transparent;
                    {row_border}
                    border-radius: {config.S(6) if is_last else 0}px;
                }}
                QWidget#marker_row:hover {{
                    background-color: #2b2b2b;
                    border-radius: {config.S(6)}px;
                }}
                QLabel {{
                    color: {config.FG_COLOR};
                    font-family: "{config.UI_FONT_NAME}";
                    font-size: {config.FS_PX(10)}px;
                    background: transparent;
                }}
            """

            row_widget = MarkerRowWidget(m, idx)
            row_widget.setObjectName("marker_row")
            row_widget.setFixedHeight(row_h)
            row_widget.setStyleSheet(row_ss)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(config.S(12), config.S(4), config.S(10), config.S(4))
            row_layout.setSpacing(config.S(10))

            # Subtle drag grip
            lbl_grip = QLabel(row_widget)
            lbl_grip.setFixedSize(config.S(12), config.S(18))
            lbl_grip.setPixmap(get_svg_icon(SVG_GRIP_DOTS, size=12).pixmap(config.S(12), config.S(18)))
            lbl_grip.setStyleSheet("background: transparent; border: none;")
            lbl_grip.setCursor(Qt.OpenHandCursor)
            row_layout.addWidget(lbl_grip)

            # Crisp vector circle swatch (no Unicode dot, no chunky gray box)
            swatch = QFrame(row_widget)
            sw_sz = config.S(11)
            swatch.setFixedSize(sw_sz, sw_sz)
            sw_fill = "#5e5e5e" if is_builtin else hex_col
            swatch.setStyleSheet(
                f"QFrame {{ background-color: {sw_fill}; border: 1px solid rgba(255, 255, 255, 0.16); "
                f"border-radius: {sw_sz // 2}px; }}"
            )
            row_layout.addWidget(swatch)

            # Clean primary label + calm hue-tinted color name (no boxy gray badge)
            lbl_name = QLabel(f"{name}", row_widget)
            name_col = "#7a7a7a" if is_builtin else "#efefef"
            lbl_name.setStyleSheet(
                f"color: {name_col}; font-weight: 600; font-size: {config.FS_PX(10)}px; background: transparent; border: none;"
            )
            row_layout.addWidget(lbl_name, 1)

            color_txt = self.txt(f'resolve_color_{color.lower()}')
            color_tint = "#6e6e6e" if is_builtin else _blend_hex("#8d8d8d", hex_col, 0.42)
            lbl_color = QLabel(color_txt, row_widget)
            lbl_color.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_color.setStyleSheet(
                f"color: {color_tint}; font-size: {config.FS_PX(9.2)}px; "
                f"background: transparent; border: none; padding-right: {config.S(6)}px;"
            )
            row_layout.addWidget(lbl_color)

            # Quiet borderless-until-hover actions
            btn_edit = QPushButton(self.txt("btn_edit_marker"), row_widget)
            btn_edit.setObjectName("btn_edit")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setFixedHeight(config.S(26))
            btn_edit.setStyleSheet(f"""
                QPushButton#btn_edit {{
                    background-color: transparent;
                    color: #9e9e9e;
                    border: 1px solid transparent;
                    border-radius: {config.S(5)}px;
                    padding: 0px {config.S(10)}px;
                    font-size: {config.FS_PX(9)}px;
                }}
                QPushButton#btn_edit:hover {{
                    background-color: #343434;
                    border-color: #454545;
                    color: #ffffff;
                }}
                QPushButton#btn_edit:disabled {{
                    color: #555555;
                }}
            """)
            btn_edit.clicked.connect(lambda _c=False, i=idx: self._on_edit_marker(i))
            if is_builtin:
                btn_edit.setEnabled(False)
                btn_edit.setToolTip(self.txt("tooltip_disabled_davinci_colors"))
            row_layout.addWidget(btn_edit)

            btn_del = QPushButton(row_widget)
            btn_del.setObjectName("btn_del_marker")
            btn_del.setIcon(get_svg_icon(SVG_TRASH, size=14))
            btn_del.setIconSize(QSize(config.S(14), config.S(14)))
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedSize(config.S(26), config.S(26))
            btn_del.setStyleSheet(f"""
                QPushButton#btn_del_marker {{
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: {config.S(5)}px;
                    padding: 0px;
                }}
                QPushButton#btn_del_marker:hover {{
                    background-color: #7a2020;
                    border-color: #ed4245;
                }}
            """)
            btn_del.clicked.connect(lambda _c=False, i=idx: self._on_remove_marker_inline(i))
            row_layout.addWidget(btn_del)

            layout.addWidget(row_widget)

        if hasattr(self, '_refresh_custom_marker_shortcuts'):
            self._refresh_custom_marker_shortcuts()
        self._check_shortcut_conflicts()

    def _on_markers_reordered(self, source_idx, target_idx):
        if not self.current_custom_markers:
            return
        target_idx = max(0, min(target_idx, len(self.current_custom_markers) - 1))
        if source_idx == target_idx:
            return
        m = self.current_custom_markers.pop(source_idx)
        self.current_custom_markers.insert(target_idx, m)
        self._refresh_markers_list()
        self._save_markers_and_refresh_main()

    def _save_markers_and_refresh_main(self):
        """
        Persist custom_markers (and any custom marker shortcuts assigned via MarkerDialog)
        immediately, sync _initial_state so closing Settings never triggers false Unsaved Changes,
        and rebuild the main window's marker sidebar and dynamic shortcuts.
        """
        prefs = self.engine.load_preferences() or {}
        prefs['custom_markers'] = list(self.current_custom_markers)

        sc_prefs = dict(prefs.get('shortcuts', {}) or {})
        valid_marker_keys = {f"custom_marker_{m.get('name', '')}" for m in self.current_custom_markers if m.get('name')}
        for k in list(sc_prefs.keys()):
            if k.startswith('custom_marker_') and k not in valid_marker_keys:
                sc_prefs.pop(k, None)
        for mk in valid_marker_keys:
            if mk in self._pending_shortcuts:
                sc_prefs[mk] = self._pending_shortcuts[mk]
        prefs['shortcuts'] = sc_prefs
        self.engine.save_preferences(prefs)

        if hasattr(self, '_initial_state') and isinstance(self._initial_state, dict):
            self._initial_state['custom_markers'] = [dict(m) for m in self.current_custom_markers]
            init_sc = dict(self._initial_state.get('shortcuts', {}) or {})
            for k in list(init_sc.keys()):
                if k.startswith('custom_marker_') and k not in valid_marker_keys:
                    init_sc.pop(k, None)
            for mk in valid_marker_keys:
                if mk in self._pending_shortcuts:
                    init_sc[mk] = self._pending_shortcuts[mk]
            self._initial_state['shortcuts'] = init_sc

        main_win = self._get_main_window()
        if not (main_win and hasattr(main_win, '_build_marker_radio_buttons')):
            w = self
            main_win = None
            while w is not None:
                try:
                    if hasattr(w, '_build_marker_radio_buttons') and hasattr(w, '_apply_dynamic_shortcuts'):
                        main_win = w
                        break
                    w = w.parent()
                except RuntimeError:
                    break

        if main_win is not None:
            try:
                main_win._build_marker_radio_buttons()
            except Exception:
                pass
            try:
                main_win._apply_dynamic_shortcuts()
            except Exception:
                pass

    def _on_add_marker(self):
        lang = (self.engine.load_preferences() or {}).get('gui_lang', 'en')
        dlg = MarkerDialog(self, lang, "btn_add_marker")
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            self.current_custom_markers.append({
                "name": dlg.result_name,
                "color": dlg.result_color,
            })
            self._pending_shortcuts[f"custom_marker_{dlg.result_name}"] = getattr(dlg, 'result_shortcut', '') or ''
            self._refresh_markers_list()
            self._save_markers_and_refresh_main()

    def _on_edit_marker(self, idx: int):
        if not (0 <= idx < len(self.current_custom_markers)):
            return
        m = self.current_custom_markers[idx]
        old_name = m.get('name', '')
        old_sk = f"custom_marker_{old_name}" if old_name else ""
        prefill_sc = self._pending_shortcuts.get(old_sk, '') if old_sk else ''
        lang = (self.engine.load_preferences() or {}).get('gui_lang', 'en')
        dlg = MarkerDialog(
            self, lang, "btn_edit_marker",
            prefill_name=old_name, prefill_color=m.get('color', ''), prefill_shortcut=prefill_sc
        )
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            if old_name and dlg.result_name != old_name:
                self._pending_shortcuts.pop(old_sk, None)
            self._pending_shortcuts[f"custom_marker_{dlg.result_name}"] = getattr(dlg, 'result_shortcut', '') or ''
            self.current_custom_markers[idx] = {
                "name": dlg.result_name,
                "color": dlg.result_color,
            }
            self._refresh_markers_list()
            self._save_markers_and_refresh_main()

    def _on_remove_marker_inline(self, idx: int):
        if 0 <= idx < len(self.current_custom_markers):
            removed = self.current_custom_markers.pop(idx)
            r_name = removed.get('name', '')
            if r_name:
                self._pending_shortcuts.pop(f"custom_marker_{r_name}", None)
            self._refresh_markers_list()
            self._save_markers_and_refresh_main()

    def _on_export_markers(self):
        from PySide6.QtWidgets import QFileDialog
        import json

        if not self.current_custom_markers:
            lang = (self.engine.load_preferences() or {}).get('gui_lang', 'en')
            CustomMsgBox(self, _txt(lang, 'btn_export_markers'), _txt(lang, 'msg_no_markers_to_export'), _txt(lang, 'btn_ok')).exec()
            return

        path, _ = QFileDialog.getSaveFileName(self, self.txt('btn_export_markers'), os.path.expanduser('~/badwords_markers.json'), 'JSON Files (*.json)')
        if not path:
            return
        data = {'version': 1, 'app': 'BadWords', 'custom_markers': list(self.current_custom_markers)}
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            lang = (self.engine.load_preferences() or {}).get('gui_lang', 'en')
            CustomMsgBox(self, self.txt('lbl_error'), str(e), _txt(lang, 'btn_ok')).exec()

    def _on_import_markers(self):
        from PySide6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getOpenFileName(self, self.txt('btn_import_markers'), '', 'JSON Files (*.json)')
        if not path:
            return
        lang = (self.engine.load_preferences() or {}).get('gui_lang', 'en')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            CustomMsgBox(self, self.txt('lbl_error'), str(e), _txt(lang, 'btn_ok')).exec()
            return

        if isinstance(data, list):
            imported = data
        elif isinstance(data, dict):
            imported = data.get('custom_markers', [])
        else:
            CustomMsgBox(self, self.txt('lbl_error'), _txt(lang, 'msg_import_invalid_format'), _txt(lang, 'btn_ok')).exec()
            return

        blocked_colors = {c.lower() for c in getattr(config, 'RESOLVE_COLORS_BLOCKED', {"Olive", "Violet", "Chocolate", "Navy", "Tan", "Green", "Blue"})}
        valid = []
        for entry in imported:
            if isinstance(entry, dict) and entry.get('name', '').strip():
                c_name = entry.get('color', 'Orange').strip()
                if c_name.lower() in blocked_colors:
                    continue
                valid.append({'name': entry['name'].strip(), 'color': c_name})

        if not valid:
            CustomMsgBox(self, self.txt('lbl_error'), _txt(lang, 'msg_import_no_valid_markers'), _txt(lang, 'btn_ok')).exec()
            return

        self.current_custom_markers = valid
        for m in valid:
            self._pending_shortcuts.setdefault(f"custom_marker_{m['name']}", "")
        self._refresh_markers_list()
        self._save_markers_and_refresh_main()

    def _refresh_custom_marker_shortcuts(self):
        """Rebuilds dynamic custom-marker shortcut rows inside the Shortcuts Marker card."""
        card = getattr(self, '_sc_markers_card', None)
        if card is None:
            return

        for row_w, div_w in getattr(self, '_sc_custom_marker_rows', []):
            for w in (div_w, row_w):
                if w is not None:
                    card._lay.removeWidget(w)
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
        self._sc_custom_marker_rows = []
        self.custom_marker_shortcut_inputs = {}

        # Remove old custom marker shortcut search entries before re-adding
        self._search_entries = [e for e in self._search_entries if not e.get("_is_dyn_marker_sc")]

        none_lbl = self.txt("shortcut_none")
        markers = getattr(self, 'current_custom_markers', [])

        for m in markers:
            name = m.get('name', '')
            if not name:
                continue
            s_key = f'custom_marker_{name}'
            fmt = self.txt('shortcut_custom_marker_fmt')
            label_text = fmt.format(name=name) if fmt != 'shortcut_custom_marker_fmt' else f'Switch to "{name}" Marker'
            en_fmt = self._en('shortcut_custom_marker_fmt')
            en_text = en_fmt.format(name=name) if en_fmt != 'shortcut_custom_marker_fmt' else f'Switch to "{name}" Marker'

            cur_seq = self._pending_shortcuts.get(s_key, '')
            widget = ShortcutCaptureButton(str(cur_seq), display_only=False, none_label=none_lbl)
            widget.sequence_changed.connect(lambda seq, k=s_key: self._sync_shortcut_value(k, seq, source="shortcuts"))

            div_w = card.add_divider()
            row_frame = SettingsRowWidget(card)
            hl = QHBoxLayout(row_frame)
            hl.setContentsMargins(config.S(16), config.S(11), config.S(14), config.S(11))
            hl.setSpacing(config.S(12))

            lbl = QLabel(label_text, row_frame)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color: #e4e4e4; font-size: {config.FS_PX(10)}px; background: transparent; border: none;")
            hl.addWidget(lbl, 1)

            holder = QWidget(row_frame)
            scope_transparent(holder)
            c_lay = QHBoxLayout(holder)
            c_lay.setContentsMargins(0, 0, 0, 0)
            c_lay.setSpacing(config.S(4))

            widget.set_uniform_width(config.S(165))
            c_lay.addWidget(widget)

            btn_clear = CloseIconButton(size=28, parent=holder)
            btn_clear.setToolTip(self.txt("tt_clear_shortcut"))
            btn_clear.clicked.connect(lambda _c=False, k=s_key: self._sync_shortcut_value(k, "", source=""))
            c_lay.addWidget(btn_clear)

            btn_rev = ReloadButton(size=28, parent=holder)
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            btn_rev.clicked.connect(lambda _c=False, k=s_key: self._sync_shortcut_value(k, "", source=""))
            c_lay.addWidget(btn_rev)

            hl.addWidget(holder, 0)
            card._lay.addWidget(row_frame)

            self.custom_marker_shortcut_inputs[s_key] = widget
            self._sc_custom_marker_rows.append((row_frame, div_w))

            self._search_entries.append({
                "page_idx": self.TAB_SHORTCUTS,
                "widget": row_frame,
                "is_advanced": False,
                "title_loc": label_text,
                "title_en": en_text,
                "desc_loc": "",
                "desc_en": "",
                "category_loc": f"{self.txt('tab_shortcuts')} › {self.txt('sec_sc_markers')}",
                "category_en": "Shortcuts › Marker Shortcuts",
                "options_loc": [str(cur_seq)],
                "options_en": [str(cur_seq)],
                "keywords_en": f"shortcut marker hotkey {name}",
                "_is_dyn_marker_sc": True,
            })

        self._check_shortcut_conflicts()

    # ── Font Preview ──────────────────────────────────────────────────────

    def _update_preview(self):
        ff = self.combo_font.currentText()
        fs = self.spin_fsize.value()
        lh = self.spin_lheight.value()
        self.lbl_preview.setStyleSheet(f"""
            background-color: {SETTINGS_INPUT_BG};
            border: 1px solid #303030;
            border-radius: {config.S(6)}px;
            color: {config.FG_COLOR};
            font-family: "{ff}";
            font-size: {config.FS_PX(fs)}px;
            padding: {config.S(12)}px {config.S(14)}px;
        """)
        self.lbl_preview.setPlainText(self.txt("lbl_font_preview"))
        from PySide6.QtGui import QTextCursor, QTextBlockFormat
        cursor = self.lbl_preview.textCursor()
        cursor.select(QTextCursor.Document)
        fmt = QTextBlockFormat()
        fmt.setLineHeight(float(config.S(lh)), 4)
        cursor.setBlockFormat(fmt)
        cursor.setPosition(0)
        self.lbl_preview.setTextCursor(cursor)
        self.lbl_preview.verticalScrollBar().setValue(0)

    # ── Export / Import ───────────────────────────────────────────────────

    def _on_export_settings(self):
        import json
        from PySide6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(self, self.txt("btn_export_settings"), "badwords_settings.json", "JSON files (*.json)")
        if not dest:
            return
        try:
            self._ensure_all_pages_built()
            user_keys = set(getattr(config, 'DEFAULT_USER_DATA', {}).keys()) | {'telemetry_opt_in', 'telemetry_geo', 'auto_crash_report'}
            merged = dict(config.DEFAULT_SETTINGS)
            disk_prefs = self.engine.load_preferences() or {}
            for k, v in disk_prefs.items():
                if k not in user_keys:
                    merged[k] = v
            cur_state = self._get_current_state_dict()
            for k, v in cur_state.items():
                if k not in user_keys:
                    merged[k] = v

            atomic_write = getattr(getattr(config, 'runtime_data', None), 'atomic_write_json', None)
            if callable(atomic_write):
                atomic_write(dest, merged)
            else:
                with open(dest, 'w', encoding='utf-8') as f:
                    json.dump(merged, f, indent=4, ensure_ascii=False)
            CustomMsgBox(
                self,
                self.txt("msg_settings_export_title"),
                self.txt("msg_settings_export_ok", path=dest),
                self.txt("btn_ok"),
            ).exec()
        except Exception as e:
            from osdoc import log_error
            log_error(f"Export settings failed: {e}")
            CustomMsgBox(
                self,
                self.txt("msg_settings_export_title"),
                self.txt("msg_settings_export_err", error=str(e)),
                self.txt("btn_ok"),
            ).exec()

    def _on_import_settings(self):
        import json
        from PySide6.QtWidgets import QFileDialog
        src, _ = QFileDialog.getOpenFileName(self, self.txt("btn_import_settings"), "", "JSON files (*.json)")
        if not src:
            return
        try:
            with open(src, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception as e:
            from osdoc import log_error
            log_error(f"Import settings failed: {e}")
            CustomMsgBox(
                self,
                self.txt("msg_settings_import_title"),
                self.txt("msg_settings_import_err", error=str(e)),
                self.txt("btn_ok"),
            ).exec()
            return

        valid_keys = set(getattr(config, 'DEFAULT_SETTINGS', {}).keys()) | {'gui_lang', 'custom_markers', 'shortcuts', 'app_icon'}
        if not isinstance(raw, dict) or not (set(raw.keys()) & valid_keys):
            CustomMsgBox(self, self.txt("msg_settings_import_title"), self.txt("msg_settings_import_invalid"), self.txt("btn_ok")).exec()
            return

        # INVARIANT: Never import DEFAULT_USER_DATA consent keys into settings.json; telemetry flags belong strictly to user.json.
        user_keys = set(getattr(config, 'DEFAULT_USER_DATA', {}).keys()) | {'telemetry_opt_in', 'telemetry_geo', 'auto_crash_report'}
        clean_cfg = dict(getattr(config, 'DEFAULT_SETTINGS', {}))
        for k, v in raw.items():
            if k not in user_keys:
                clean_cfg[k] = v

        try:
            self.engine.save_preferences(clean_cfg)
            os_doc = getattr(self.engine, 'os_doc', None)
            if os_doc is not None:
                os_doc.settings = dict(clean_cfg)
            self._ensure_all_pages_built()
            self._restore_state_dict(clean_cfg, include_advanced=True)
            self._save_markers_and_refresh_main()
            self._initial_state = self._get_current_state_dict()
        except Exception as e:
            from osdoc import log_error
            log_error(f"Apply imported settings failed: {e}")
            CustomMsgBox(
                self,
                self.txt("msg_settings_import_title"),
                self.txt("msg_settings_import_err", error=str(e)),
                self.txt("btn_ok"),
            ).exec()
            return

        lang = (self.engine.load_preferences() or {}).get('gui_lang', clean_cfg.get('gui_lang', 'en'))
        target = config.TRANS.get(lang, config.TRANS['en'])
        CustomMsgBox(
            self,
            target.get('msg_settings_import_title', target.get('msg_title_language_changed', 'Import Settings')),
            target.get('msg_settings_import_ok', target.get('msg_restart_lang', 'Settings imported. Please restart BadWords to apply all changes.')),
            target.get('btn_ok', 'OK')
        ).exec()
        self.reject()

    # ── State Collection, Restoration & Smart Apply ───────────────────────

    def _safe_get(self, attr_name, default_val, method_name="value"):
        try:
            widget = getattr(self, attr_name)
            return getattr(widget, method_name)()
        except (RuntimeError, AttributeError):
            return default_val

    def _get_current_state_dict(self):
        old_prefs = self.engine.load_preferences() or {}
        is_basic = getattr(self, '_is_basic_mode', old_prefs.get('settings_view_mode', 'basic') == 'basic')

        try:
            checked_btn = self.icon_group.checkedButton()
            icon_val = checked_btn.property("icon_name") if checked_btn else "default"
        except (RuntimeError, AttributeError):
            icon_val = old_prefs.get('app_icon', 'default')

        try:
            val = self.dropdown_lang.text()
            lang_code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), old_prefs.get('gui_lang', 'en'))
        except (RuntimeError, AttributeError):
            lang_code = old_prefs.get('gui_lang', 'en')

        view_mode_val = self._safe_get('combo_view', '', 'currentText')
        prop_mode = self.combo_view.property("view_mode_key") if hasattr(self, 'combo_view') and self.combo_view else None
        if prop_mode in ('segmented', 'continuous'):
            view_mode = prop_mode
        elif _is_segmented_text(view_mode_val):
            view_mode = 'segmented'
        elif _is_continuous_text(view_mode_val):
            view_mode = 'continuous'
        else:
            view_mode = old_prefs.get('view_mode', 'segmented')

        lmb_text = self._safe_get('combo_mouse_lmb', '', 'currentText')
        prop_lmb = self.combo_mouse_lmb.property("mouse_mode_key") if hasattr(self, 'combo_mouse_lmb') and self.combo_mouse_lmb else None
        lmb_mode = prop_lmb if prop_lmb in ('text', 'box', 'brush', 'none') else _get_mouse_mode_from_text(lmb_text, old_prefs.get('mouse_lmb_mode', 'text'))

        rmb_text = self._safe_get('combo_mouse_rmb', '', 'currentText')
        prop_rmb = self.combo_mouse_rmb.property("mouse_mode_key") if hasattr(self, 'combo_mouse_rmb') and self.combo_mouse_rmb else None
        rmb_mode = prop_rmb if prop_rmb in ('box', 'text', 'brush', 'none') else _get_mouse_mode_from_text(rmb_text, old_prefs.get('mouse_rmb_mode', 'box'))

        # Merge shortcuts across _pending_shortcuts and Shortcuts tab
        shortcuts_dict = dict(old_prefs.get('shortcuts', {}))
        shortcuts_dict.update(getattr(self, '_pending_shortcuts', {}))
        try:
            for k, v in getattr(self, 'shortcut_inputs', {}).items():
                shortcuts_dict[k] = v.get_sequence()
            for k, v in getattr(self, 'custom_marker_shortcut_inputs', {}).items():
                shortcuts_dict[k] = v.get_sequence()
        except (RuntimeError, AttributeError):
            pass

        raw_geo = old_prefs.get('telemetry_geo')
        geo_fallback = True if raw_geo is None else bool(raw_geo)
        raw_crash = old_prefs.get('auto_crash_report')
        crash_fallback = True if raw_crash is None else bool(raw_crash)

        state = {
            'gui_lang':           lang_code,
            'settings_view_mode': 'basic' if is_basic else 'advanced',
            'app_icon':           icon_val,
            'shortcuts':          shortcuts_dict,
            'custom_markers':     list(getattr(self, 'current_custom_markers', old_prefs.get('custom_markers', []))),
            'telemetry_opt_in':   self._safe_get('chk_telemetry_opt_in', bool(old_prefs.get('telemetry_opt_in', False)), 'isChecked'),
            'telemetry_geo':      self._safe_get('chk_telemetry_geo', geo_fallback, 'isChecked'),
            'auto_crash_report':  self._safe_get('chk_auto_crash_report', crash_fallback, 'isChecked'),
            'view_mode':          view_mode,
            'mouse_lmb_mode':     lmb_mode,
            'mouse_rmb_mode':     rmb_mode,
            'editor_font_family': self._safe_get('combo_font', old_prefs.get('editor_font_family', config.UI_FONT_NAME), 'currentText'),
            'editor_font_size':   self._safe_get('spin_fsize', old_prefs.get('editor_font_size', 12), 'value'),
            'editor_line_height': self._safe_get('spin_lheight', old_prefs.get('editor_line_height', 7), 'value'),
            'ui_scale_mode':      getattr(self, '_ui_scale_mode', old_prefs.get('ui_scale_mode', 'auto')),
            'ui_scale_pct':       self._safe_get('slider_ui_scale', old_prefs.get('ui_scale_pct', 100), 'value'),
            'sync_davinci_chapter': self._safe_get('chk_sync_davinci', old_prefs.get('sync_davinci_chapter', True), 'isChecked'),
            'xml_preserve_track_order': self._safe_get('tgl_xml_preserve_track_order', old_prefs.get('xml_preserve_track_order', config.DEFAULT_SETTINGS['xml_preserve_track_order']), 'isChecked'),
            'force_xml_assembly':   self._safe_get('tgl_force_xml_assembly', old_prefs.get('force_xml_assembly', config.DEFAULT_SETTINGS['force_xml_assembly']), 'isChecked'),
            'timeline_assembly_method': "xml" if self._safe_get('tgl_force_xml_assembly', old_prefs.get('force_xml_assembly', config.DEFAULT_SETTINGS['force_xml_assembly']), 'isChecked') else "drt",
            'link_av_clips':        self._safe_get('tgl_link_av_clips', old_prefs.get('link_av_clips', config.DEFAULT_SETTINGS['link_av_clips']), 'isChecked'),
            'link_all_cut_tracks':  self._safe_get('tgl_link_all_cut_tracks', old_prefs.get('link_all_cut_tracks', config.DEFAULT_SETTINGS['link_all_cut_tracks']), 'isChecked'),
            'resolve_render_timeline_proxy': self._safe_get('tgl_resolve_render_timeline_proxy', old_prefs.get('resolve_render_timeline_proxy', config.DEFAULT_SETTINGS['resolve_render_timeline_proxy']), 'isChecked'),
            'timestamp_precise':    self._safe_get('tgl_timestamp_precise', old_prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'isChecked'),
            'show_panel_headers':   self._safe_get('tgl_show_panel_headers', old_prefs.get('show_panel_headers', True), 'isChecked'),
            'auto_check_updates':      self._safe_get('tgl_auto_check_updates', old_prefs.get('auto_check_updates', True), 'isChecked'),
            'auto_update_on_start':   self._safe_get('tgl_auto_update_on_start', old_prefs.get('auto_update_on_start', False), 'isChecked'),
            'always_on_top':          self._safe_get('chk_ontop', old_prefs.get('always_on_top', False), 'isChecked'),
        }

        if not is_basic:
            state.update({
                'device':             self._safe_get('dropdown_device', old_prefs.get('device', 'auto'), 'currentText').lower(),
                'ai_compute_type':    self._safe_get('dropdown_compute', old_prefs.get('ai_compute_type', 'Auto'), 'currentText'),
                'ai_initial_prompt':  self._safe_get('textedit_prompt', old_prefs.get('ai_initial_prompt', ''), 'toPlainText'),
                'chunk_max_words':    self._safe_get('spin_chunk_max', old_prefs.get('chunk_max_words', 15), 'value'),
                'chunk_lookahead':    self._safe_get('spin_chunk_look', old_prefs.get('chunk_lookahead', 3), 'value'),
                'chunk_min_chars':    self._safe_get('spin_chunk_min', old_prefs.get('chunk_min_chars', 7), 'value'),
                'algo_fuzzy_threshold':  self._safe_get('spin_fuzzy', old_prefs.get('algo_fuzzy_threshold', config.DEFAULT_SETTINGS.get('algo_fuzzy_threshold', 75)), 'value'),
                'algo_retake_lookahead': self._safe_get('spin_lookahead', old_prefs.get('algo_retake_lookahead', 80), 'value'),
                'algo_distance_penalty': self._safe_get('spin_penalty', old_prefs.get('algo_distance_penalty', 2.0), 'value'),
                'algo_anchor_depth':     self._safe_get('spin_anchor', old_prefs.get('algo_anchor_depth', 3), 'value'),
                'ai_vad_filter':            self._safe_get('chk_vad_filter', old_prefs.get('ai_vad_filter', False), 'isChecked'),
                'ai_beam_size':             self._safe_get('spin_beam_size', old_prefs.get('ai_beam_size', 1), 'value'),
                'ai_temperature':           self._safe_get('spin_temperature', old_prefs.get('ai_temperature', 0.0), 'value'),
                'ai_condition_on_prev':     self._safe_get('chk_condition_prev', old_prefs.get('ai_condition_on_prev', False), 'isChecked'),
                'ai_logprob_threshold':     self._safe_get('spin_logprob', old_prefs.get('ai_logprob_threshold', -0.8), 'value'),
                'ai_no_speech_threshold':   self._safe_get('spin_no_speech', old_prefs.get('ai_no_speech_threshold', 0.7), 'value'),
                'ai_patience':              self._safe_get('spin_patience', old_prefs.get('ai_patience', 1.0), 'value'),
                'ai_compression_ratio_threshold': self._safe_get('spin_compression', old_prefs.get('ai_compression_ratio_threshold', 2.4), 'value'),
                'ai_no_repeat_ngram_size':  self._safe_get('spin_no_repeat', old_prefs.get('ai_no_repeat_ngram_size', 0), 'value'),
                'ai_length_penalty':        self._safe_get('spin_length_penalty', old_prefs.get('ai_length_penalty', config.DEFAULT_SETTINGS.get('ai_length_penalty', 1.0)), 'value'),
                'ai_repetition_penalty':    self._safe_get('spin_repetition_penalty', old_prefs.get('ai_repetition_penalty', config.DEFAULT_SETTINGS.get('ai_repetition_penalty', 1.0)), 'value'),
                'silence_threshold_db':     self._safe_get('spin_silence_thresh', old_prefs.get('silence_threshold_db', -42.0), 'value'),
                'ui_spin_pad':              self._safe_get('spin_silence_pad', old_prefs.get('ui_spin_pad', 0.1), 'value'),
                'silence_min_dur':          self._safe_get('spin_silence_min_dur', old_prefs.get('silence_min_dur', 0.2), 'value'),
            })
        else:
            advanced_keys = [
                "device", "ai_compute_type", "ai_initial_prompt", "chunk_max_words", "chunk_lookahead",
                "chunk_min_chars", "algo_fuzzy_threshold", "algo_retake_lookahead", "algo_distance_penalty",
                "algo_anchor_depth", "ai_vad_filter", "ai_beam_size", "ai_temperature",
                "ai_condition_on_prev", "ai_logprob_threshold", "ai_no_speech_threshold", "ai_patience",
                "ai_compression_ratio_threshold", "ai_no_repeat_ngram_size", "ai_length_penalty",
                "ai_repetition_penalty", "silence_threshold_db", "ui_spin_pad", "silence_min_dur"
            ]
            for key in advanced_keys:
                state[key] = old_prefs.get(key, config.DEFAULT_SETTINGS.get(key))
        return state

    def _safe_set(self, attr_name, value, method_name="setValue"):
        try:
            if hasattr(self, attr_name):
                widget = getattr(self, attr_name)
                getattr(widget, method_name)(value)
        except (RuntimeError, AttributeError):
            pass

    def _reload_preferences(self):
        try:
            prefs = self.engine.load_preferences() or {}
            self._restore_state_dict(prefs)
            self._initial_state = self._get_current_state_dict()
        except Exception:
            pass

    def _restore_state_dict(self, state, include_advanced: bool = None):
        def _g(k, d):
            v = state.get(k)
            return v if v is not None else d

        is_basic = _g('settings_view_mode', 'basic') == 'basic'
        telem_on = bool(_g('telemetry_opt_in', False))
        self._safe_set('chk_telemetry_opt_in', telem_on, 'setChecked')
        self._safe_set('chk_telemetry_geo', bool(_g('telemetry_geo', True)), 'setChecked')
        if hasattr(self, '_update_geo_availability'):
            self._update_geo_availability(telem_on, animated=False)
        self._safe_set('chk_auto_crash_report', bool(_g('auto_crash_report', True)), 'setChecked')

        try:
            if hasattr(self, 'icon_group'):
                icon_name = _g('app_icon', 'default')
                for btn in self.icon_group.buttons():
                    if btn.property("icon_name") == icon_name:
                        btn.setChecked(True)
                        break
        except RuntimeError:
            pass

        try:
            lang_code = _g('gui_lang', 'en')
            self._safe_set('dropdown_lang', config.SUPPORTED_LANGS.get(lang_code, 'English'), 'setText')
        except Exception:
            pass

        view_mode = _g('view_mode', 'segmented')
        if hasattr(self, 'combo_view') and self.combo_view is not None:
            self.combo_view.options_list = [self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")]
            self.combo_view.setProperty("view_mode_key", view_mode)
        self._safe_set('combo_view', self.txt("opt_segmented_blocks") if view_mode == 'segmented' else self.txt("opt_continuous_flow"), 'setText')

        lmb_mode = _g('mouse_lmb_mode', 'text')
        if hasattr(self, 'combo_mouse_lmb') and self.combo_mouse_lmb is not None:
            self.combo_mouse_lmb.setProperty("mouse_mode_key", lmb_mode)
            lmb_map = {'text': self.txt("opt_mouse_text"), 'box': self.txt("opt_mouse_box"), 'brush': self.txt("opt_mouse_brush"), 'none': self.txt("opt_mouse_none")}
            self._safe_set('combo_mouse_lmb', lmb_map.get(lmb_mode, self.txt("opt_mouse_text")), 'setText')

        rmb_mode = _g('mouse_rmb_mode', 'box')
        if hasattr(self, 'combo_mouse_rmb') and self.combo_mouse_rmb is not None:
            self.combo_mouse_rmb.setProperty("mouse_mode_key", rmb_mode)
            rmb_map = {'box': self.txt("opt_mouse_box"), 'text': self.txt("opt_mouse_text"), 'brush': self.txt("opt_mouse_brush"), 'none': self.txt("opt_mouse_none")}
            self._safe_set('combo_mouse_rmb', rmb_map.get(rmb_mode, self.txt("opt_mouse_box")), 'setText')

        self._safe_set('combo_font', _g('editor_font_family', config.UI_FONT_NAME), 'setText')
        self._safe_set('spin_fsize', _g('editor_font_size', 12), 'setValue')
        self._safe_set('spin_lheight', _g('editor_line_height', 7), 'setValue')

        # Fixed: Always on top belongs to Basic mode too, so restore regardless of is_basic!
        self._safe_set('chk_ontop', bool(_g('always_on_top', False)), 'setChecked')

        restored_mode = str(_g('ui_scale_mode', 'auto')).strip().lower()
        self._ui_scale_mode = restored_mode if restored_mode in ('auto', 'manual') else 'auto'
        restored_os = int(config.detect_os_scale_pct(self.screen()))
        restored_pct = restored_os if self._ui_scale_mode == 'auto' else int(_g('ui_scale_pct', restored_os))
        self._updating_scale_slider = True
        try:
            self._safe_set('slider_ui_scale', max(config.UI_SCALE_MIN, min(config.UI_SCALE_MAX, restored_pct)), 'setValue')
        finally:
            self._updating_scale_slider = False
        if hasattr(self, '_refresh_scale_label') and callable(self._refresh_scale_label):
            self._refresh_scale_label(restored_pct, self._ui_scale_mode == 'auto')

        self.current_custom_markers = _g('custom_markers', [])
        sc_state = dict(_g('shortcuts', {}) or {})
        self._pending_shortcuts = dict(sc_state)

        try:
            for k, v in sc_state.items():
                if k in getattr(self, 'shortcut_inputs', {}):
                    self.shortcut_inputs[k].set_sequence(v)
        except RuntimeError:
            pass

        try:
            if hasattr(self, '_markers_layout') and self._markers_layout is not None:
                self._refresh_markers_list()
        except Exception:
            pass

        try:
            for k, v in sc_state.items():
                if k in getattr(self, 'custom_marker_shortcut_inputs', {}):
                    self.custom_marker_shortcut_inputs[k].set_sequence(v)
        except RuntimeError:
            pass

        self._check_shortcut_conflicts()

        self._safe_set('chk_sync_davinci', _g('sync_davinci_chapter', True), 'setChecked')
        self._safe_set('tgl_xml_preserve_track_order', _g('xml_preserve_track_order', config.DEFAULT_SETTINGS['xml_preserve_track_order']), 'setChecked')
        asm_method = str(_g('timeline_assembly_method', '')).strip().lower()
        force_xml = (asm_method == 'xml') if asm_method in ('xml', 'drt') else bool(_g('force_xml_assembly', config.DEFAULT_SETTINGS['force_xml_assembly']))
        self._safe_set('tgl_force_xml_assembly', force_xml, 'setChecked')
        self._safe_set('tgl_link_av_clips', _g('link_av_clips', config.DEFAULT_SETTINGS['link_av_clips']), 'setChecked')
        self._safe_set('tgl_link_all_cut_tracks', _g('link_all_cut_tracks', config.DEFAULT_SETTINGS['link_all_cut_tracks']), 'setChecked')
        self._safe_set('tgl_resolve_render_timeline_proxy', _g('resolve_render_timeline_proxy', config.DEFAULT_SETTINGS['resolve_render_timeline_proxy']), 'setChecked')
        self._safe_set('tgl_timestamp_precise', _g('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'setChecked')
        self._safe_set('tgl_show_panel_headers', _g('show_panel_headers', True), 'setChecked')
        auto_chk = bool(_g('auto_check_updates', True))
        self._safe_set('tgl_auto_check_updates', auto_chk, 'setChecked')
        self._safe_set('tgl_auto_update_on_start', bool(_g('auto_update_on_start', False)) if auto_chk else False, 'setChecked')
        if hasattr(self, '_update_auto_update_availability'):
            self._update_auto_update_availability(auto_chk, animated=False)
        if hasattr(self, '_sync_ver_card_state') and callable(self._sync_ver_card_state):
            cur_st = self._lbl_ver_status.text() if hasattr(self, '_lbl_ver_status') else ""
            if (not auto_chk) or (cur_st in (self.txt("msg_updates_disabled"), "...")):
                self._sync_ver_card_state(auto_chk)

        if include_advanced or (include_advanced is None and not is_basic):
            dev_val = _g('device', 'Auto').upper()
            if dev_val == 'AUTO':
                dev_val = 'Auto'
            self._safe_set('dropdown_device', dev_val, 'setText')
            self._safe_set('dropdown_compute', _g('ai_compute_type', 'Auto'), 'setText')
            self._safe_set('textedit_prompt', _g('ai_initial_prompt', ''), 'setPlainText')
            self._safe_set('spin_chunk_max', _g('chunk_max_words', 15), 'setValue')
            self._safe_set('spin_chunk_look', _g('chunk_lookahead', 3), 'setValue')
            self._safe_set('spin_chunk_min', _g('chunk_min_chars', 7), 'setValue')
            self._safe_set('chk_vad_filter', _g('ai_vad_filter', False), 'setChecked')
            self._safe_set('spin_beam_size', _g('ai_beam_size', 1), 'setValue')
            self._safe_set('spin_temperature', _g('ai_temperature', 0.0), 'setValue')
            self._safe_set('chk_condition_prev', _g('ai_condition_on_prev', False), 'setChecked')
            self._safe_set('spin_logprob', _g('ai_logprob_threshold', -0.8), 'setValue')
            self._safe_set('spin_no_speech', _g('ai_no_speech_threshold', 0.7), 'setValue')
            self._safe_set('spin_patience', _g('ai_patience', 1.0), 'setValue')
            self._safe_set('spin_compression', _g('ai_compression_ratio_threshold', 2.4), 'setValue')
            self._safe_set('spin_no_repeat', _g('ai_no_repeat_ngram_size', 0), 'setValue')
            self._safe_set('spin_length_penalty', _g('ai_length_penalty', 1.0), 'setValue')
            self._safe_set('spin_repetition_penalty', _g('ai_repetition_penalty', 1.0), 'setValue')
            self._safe_set('spin_fuzzy', _g('algo_fuzzy_threshold', config.DEFAULT_SETTINGS.get('algo_fuzzy_threshold', 75)), 'setValue')
            self._safe_set('spin_lookahead', _g('algo_retake_lookahead', 80), 'setValue')
            self._safe_set('spin_penalty', _g('algo_distance_penalty', 2.0), 'setValue')
            self._safe_set('spin_anchor', _g('algo_anchor_depth', 3), 'setValue')
            self._safe_set('spin_silence_thresh', _g('silence_threshold_db', -42.0), 'setValue')
            self._safe_set('spin_silence_pad', _g('ui_spin_pad', 0.1), 'setValue')
            self._safe_set('spin_silence_min_dur', _g('silence_min_dur', 0.2), 'setValue')

    def _apply_settings(self):
        old_prefs = self.engine.load_preferences() or {}
        new_prefs = self._get_current_state_dict()

        selected_device = new_prefs.get('device', 'auto')
        selected_compute = new_prefs.get('ai_compute_type', 'Auto')
        old_compute = old_prefs.get('ai_compute_type', 'Auto')
        old_device = old_prefs.get('device', 'auto')

        compute_changed = (selected_compute != old_compute) or (selected_device != old_device)
        if selected_compute.lower() != 'auto' and compute_changed:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                is_supported = self.engine.verify_hardware_compute(selected_device, selected_compute)
            finally:
                QApplication.restoreOverrideCursor()

            if not is_supported:
                CustomMsgBox(self, self.txt('msg_compute_fail_title'), self.txt('msg_compute_fail_desc'), self.txt('btn_close')).exec()
                return

        _defs = dict(getattr(config, 'DEFAULT_USER_DATA', {}))
        _defs.update(getattr(config, 'DEFAULT_SETTINGS', {}))
        restart_needed = any(
            new_prefs.get(k) != old_prefs.get(k, _defs.get(k))
            for k in config.RESTART_REQUIRED_KEYS
            if k in new_prefs
        )

        self.engine.save_preferences(new_prefs)
        self.initial_prefs = self.engine.load_preferences() or {}
        self._initial_state = self._get_current_state_dict()

        main_win = self._get_main_window()

        if main_win and hasattr(main_win, 'text_canvas'):
            main_win.text_canvas.invalidate_font_cache()
            main_win.text_canvas._calculate_layout()
            main_win.text_canvas.update()

        if main_win and hasattr(main_win, 'update_silence_panel_ranges'):
            main_win.update_silence_panel_ranges()

        if main_win and hasattr(main_win, 'set_panel_headers_visible'):
            main_win.set_panel_headers_visible(new_prefs.get('show_panel_headers', True))

        if main_win and hasattr(main_win, 'w_track_options'):
            try:
                main_win.w_track_options.load_config()
            except Exception:
                pass

        if main_win and hasattr(main_win, '_apply_dynamic_shortcuts'):
            try:
                main_win._apply_dynamic_shortcuts()
            except Exception:
                pass

        aot_changed = new_prefs.get('always_on_top', False) != bool(old_prefs.get('always_on_top', False))
        if aot_changed:
            is_top = bool(new_prefs.get('always_on_top'))
            if main_win:
                if hasattr(main_win, '_apply_always_on_top'):
                    main_win._apply_always_on_top(is_top)
                else:
                    main_win.setWindowFlag(Qt.WindowStaysOnTopHint, is_top)
                    main_win.show()
            self.set_always_on_top_state(is_top)

        new_mode = str(new_prefs.get('ui_scale_mode', 'auto')).strip().lower()
        if new_mode not in ('auto', 'manual'):
            new_mode = 'auto'
        new_pct = int(new_prefs.get('ui_scale_pct', 100))
        old_mode = str(old_prefs.get('ui_scale_mode', 'auto')).strip().lower()
        old_pct = int(old_prefs.get('ui_scale_pct', 100))
        scale_changed = (
            (new_mode != old_mode)
            or (new_mode == 'manual' and new_pct != old_pct)
            or (new_mode != getattr(config, 'UI_SCALE_MODE', 'auto'))
            or (new_mode == 'manual' and new_pct != int(getattr(config, 'UI_SCALE_PERCENT', 100)))
        )
        if scale_changed:
            self._apply_live_ui_scale(new_mode, None if new_mode == 'auto' else new_pct)

        # Clean property-based Saved! feedback (keeps rounded corners & bold font!)
        if hasattr(self, 'btn_apply') and self.btn_apply is not None:
            btn_ref = self.btn_apply
            btn_ref.setText(self.txt("txt_saved"))
            btn_ref.setProperty("saved", True)
            btn_ref.style().unpolish(btn_ref)
            btn_ref.style().polish(btn_ref)

            def restore_btn(b=btn_ref):
                try:
                    if getattr(self, 'btn_apply', None) is b:
                        b.setText(self.txt("btn_apply"))
                        b.setProperty("saved", False)
                        b.style().unpolish(b)
                        b.style().polish(b)
                except RuntimeError:
                    pass
            QTimer.singleShot(1500, restore_btn)

        if restart_needed:
            lang = old_prefs.get('gui_lang', 'en')
            target = config.TRANS.get(lang, config.TRANS['en'])
            CustomMsgBox(
                self,
                target.get('tool_settings', 'Settings'),
                target.get('msg_restart_required', 'Changes applied. Full effect will be visible on next launch.'),
                target.get('btn_ok', 'OK')
            ).exec()

    def _compute_unsaved_diff(self):
        """Returns (diff_dict, new_prefs) comparing current UI state against initial snapshot."""
        old_prefs = getattr(self, '_initial_state', self.engine.load_preferences() or {})
        new_prefs = self._get_current_state_dict()
        diff = {}
        for k, new_val in new_prefs.items():
            if k in ('ui_scale_mode', 'ui_scale_pct'):
                continue
            old_val = old_prefs.get(k)
            if old_val is None:
                old_val = config.DEFAULT_SETTINGS.get(k)
                if old_val is None:
                    if k == 'app_icon': old_val = 'default'
                    elif k == 'gui_lang': old_val = 'en'
                    elif k == 'hidden_panels': old_val = []
                    elif k == 'custom_markers': old_val = []

            if k == 'shortcuts':
                old_dict = old_val if isinstance(old_val, dict) else {}
                for sub_k, sub_new in new_val.items():
                    sub_old = old_dict.get(sub_k, '')
                    if sub_old != sub_new:
                        diff[f"shortcuts.{sub_k}"] = (sub_old, sub_new)
            else:
                is_different = False
                if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
                    if abs(float(old_val) - float(new_val)) > 1e-5:
                        is_different = True
                elif str(new_val) != str(old_val) and new_val != old_val:
                    try:
                        if abs(float(old_val) - float(new_val)) < 1e-5:
                            is_different = False
                        else:
                            is_different = True
                    except (ValueError, TypeError):
                        is_different = True
                if is_different:
                    diff[k] = (old_val, new_val)

        old_mode = str(old_prefs.get('ui_scale_mode', 'auto')).strip().lower()
        new_mode = str(new_prefs.get('ui_scale_mode', 'auto')).strip().lower()
        old_pct = int(old_prefs.get('ui_scale_pct', 100))
        new_pct = int(new_prefs.get('ui_scale_pct', 100))
        if new_mode == 'auto':
            if old_mode != 'auto':
                badge = self.txt('ui_scale_system_badge')
                if badge == 'ui_scale_system_badge':
                    badge = 'System'
                cur_os = int(config.detect_os_scale_pct(self.screen()))
                diff['ui_scale_mode'] = (f"{old_pct}%", f"{cur_os}% ({badge})")
        elif old_mode != 'manual' or new_pct != old_pct:
            diff['ui_scale_pct'] = (old_pct, f"{new_pct}%")

        return diff, new_prefs

    def has_unsaved_changes(self) -> bool:
        try:
            diff, _ = self._compute_unsaved_diff()
            return bool(diff)
        except Exception:
            return False

    def reject(self):
        diff, new_prefs = self._compute_unsaved_diff()
        if diff:
            key_name_map = {
                'shortcuts': f"{self.txt('tab_shortcuts')}",
                'gui_lang': f"{self.txt('tab_general')}: {self.txt('lbl_language')}",
                'app_icon': f"{self.txt('tab_general')}: {self.txt('lbl_app_icon')}",
                'settings_view_mode': f"{self.txt('tab_general')}: {self.txt('lbl_view_mode')}",
                'show_panel_headers': f"{self.txt('tab_general')}: {self.txt('lbl_show_panel_headers')}",
                'auto_check_updates': f"{self.txt('tab_general')}: {self.txt('lbl_auto_check_updates')}",
                'auto_update_on_start': f"{self.txt('tab_general')}: {self.txt('lbl_auto_update_on_start')}",

                'ui_scale_mode': f"{self.txt('tab_appearance')}: {self.txt('lbl_ui_scaling')}",
                'ui_scale_pct': f"{self.txt('tab_appearance')}: {self.txt('lbl_ui_scaling')}",
                'always_on_top': f"{self.txt('tab_appearance')}: {self.txt('lbl_always_on_top')}",
                'editor_font_family': f"{self.txt('tab_appearance')}: {self.txt('lbl_transcript_font')}",
                'editor_font_size': f"{self.txt('tab_appearance')}: {self.txt('lbl_font_size_pt')}",
                'editor_line_height': f"{self.txt('tab_appearance')}: {self.txt('lbl_line_spacing_px')}",

                'view_mode': f"{self.txt('tab_editor')}: {self.txt('lbl_display_mode')}",
                'mouse_lmb_mode': f"{self.txt('tab_editor')}: {self.txt('lbl_mouse_lmb_mode')}",
                'mouse_rmb_mode': f"{self.txt('tab_editor')}: {self.txt('lbl_mouse_rmb_mode')}",
                'chunk_max_words': f"{self.txt('tab_editor')}: {self.txt('lbl_chunk_max_words')}",
                'chunk_lookahead': f"{self.txt('tab_editor')}: {self.txt('lbl_chunk_lookahead')}",
                'chunk_min_chars': f"{self.txt('tab_editor')}: {self.txt('lbl_chunk_min_chars')}",
                'timestamp_precise': f"{self.txt('tab_editor')}: {self.txt('lbl_timestamp_precise')}",

                'force_xml_assembly': f"{self.txt('tab_davinci')}: {self.txt('lbl_assembly_method')}",
                'timeline_assembly_method': f"{self.txt('tab_davinci')}: {self.txt('lbl_assembly_method')}",
                'xml_preserve_track_order': f"{self.txt('tab_davinci')}: {self.txt('lbl_xml_preserve_track_order')}",
                'link_av_clips': f"{self.txt('tab_davinci')}: {self.txt('lbl_link_av_clips')}",
                'link_all_cut_tracks': f"{self.txt('tab_davinci')}: {self.txt('lbl_link_all_cut_tracks')}",
                'sync_davinci_chapter': f"{self.txt('tab_davinci')}: {self.txt('chk_sync_davinci')}",
                'resolve_render_timeline_proxy': f"{self.txt('tab_davinci')}: {self.txt('lbl_resolve_render_timeline_proxy')}",
                'custom_markers': f"{self.txt('tab_custom_markers')}: {self.txt('sec_dav_markers')}",

                'device': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_device')}",
                'ai_compute_type': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_compute_type')}",
                'silence_threshold_db': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_silence_threshold_db')}",
                'ui_spin_pad': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_padding_s')}",
                'silence_min_dur': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_min_silence_dur')}",
                'ai_initial_prompt': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_initial_prompt')}",
                'ai_vad_filter': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_vad_filter')}",
                'ai_condition_on_prev': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_condition_prev')}",
                'ai_beam_size': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_beam_size')}",
                'ai_temperature': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_temperature')}",
                'ai_logprob_threshold': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_logprob')}",
                'ai_no_speech_threshold': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_no_speech')}",
                'ai_patience': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_patience')}",
                'ai_compression_ratio_threshold': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_compression_ratio')}",
                'ai_no_repeat_ngram_size': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_no_repeat_ngram')}",
                'ai_length_penalty': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_length_penalty')}",
                'ai_repetition_penalty': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_repetition_penalty')}",

                'telemetry_opt_in': f"{self.txt('tab_about')}: {self.txt('chk_telemetry_opt_in')}",
                'telemetry_geo': f"{self.txt('tab_about')}: {self.txt('chk_telemetry_geo')}",
                'auto_crash_report': f"{self.txt('tab_about')}: {self.txt('chk_auto_crash_report')}",
            }

            for diff_k in diff.keys():
                if diff_k.startswith('shortcuts.'):
                    sub_k = diff_k.split('.', 1)[1]
                    if sub_k.startswith('custom_marker_'):
                        m_name = sub_k[len('custom_marker_'):]
                        fmt = self.txt('shortcut_custom_marker_fmt')
                        sub_name = fmt.format(name=m_name) if fmt != 'shortcut_custom_marker_fmt' else f'Switch to "{m_name}" Marker'
                    else:
                        sub_name = self.txt(f"shortcut_{sub_k}")
                        if sub_name == f"shortcut_{sub_k}":
                            sub_name = sub_k.replace('_', ' ').title()
                    key_name_map[diff_k] = f"{self.txt('tab_shortcuts')}: {sub_name}"

            dlg = UnsavedChangesDialog(self, diff, key_name_map)
            if dlg.exec() == QDialog.Accepted:
                save_needed = False
                for k, action in dlg.decisions.items():
                    if action == 'discard':
                        if k.startswith('shortcuts.'):
                            sub_k = k.split('.', 1)[1]
                            new_prefs['shortcuts'][sub_k] = diff[k][0]
                        elif k in ('ui_scale_mode', 'ui_scale_pct'):
                            snap = getattr(self, '_initial_state', self.engine.load_preferences() or {})
                            new_prefs['ui_scale_mode'] = snap.get('ui_scale_mode', 'auto')
                            new_prefs['ui_scale_pct'] = snap.get('ui_scale_pct', 100)
                        else:
                            new_prefs[k] = diff[k][0]
                    else:
                        save_needed = True

                self._restore_state_dict(new_prefs)
                if save_needed:
                    self._apply_settings()
                self._finish_close(0)
            else:
                return
        else:
            self._finish_close(0)

    def _macos_close_native_window(self):
        """Closes the underlying Cocoa NSWindow natively so Fullscreen/Stage Manager never leaves a ghost or black Space."""
        if not getattr(self, '_is_mac', False):
            return
        if not self.testAttribute(Qt.WA_WState_Created):
            return
        try:
            import ctypes
            import ctypes.util
            objc_path = ctypes.util.find_library('objc')
            if not objc_path:
                return
            objc = ctypes.cdll.LoadLibrary(objc_path)
            objc.sel_registerName.restype = ctypes.c_void_p
            objc.sel_registerName.argtypes = [ctypes.c_char_p]

            win_id = int(self.winId())
            if not win_id:
                return
            view = ctypes.c_void_p(win_id)
            sel_window = objc.sel_registerName(b"window")
            msg_window = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
            nswindow = msg_window(view, sel_window) or view
            if not nswindow:
                return

            sel_set_rel = objc.sel_registerName(b"setReleasedWhenClosed:")
            msg_set_rel = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool))
            msg_set_rel(nswindow, sel_set_rel, False)

            sel_close = objc.sel_registerName(b"close")
            msg_close = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p))
            msg_close(nswindow, sel_close)
        except Exception:
            pass

    def _finish_close(self, result: int = 0):
        # On macOS, calling hide() + setWindowState() or mid-animation showNormal() on a reused
        # QMainWindow leaves an empty gray NSWindow or strands Cocoa on a black Fullscreen Space.
        # Close the native NSWindow cleanly and recreate a fresh SettingsDialog on next open.
        if getattr(self, '_is_mac', False):
            if getattr(self, '_mac_closed', False):
                return
            self._mac_closed = True
            mw = getattr(self, '_main_window', None)
            if mw is not None and getattr(mw, '_settings_dialog', None) is self:
                mw._settings_dialog = None
            self.finished.emit(result)
            self._macos_close_native_window()
            self.hide()
            self.deleteLater()
            if mw is not None:
                def _refocus_main(target=mw):
                    try:
                        target.raise_()
                        target.activateWindow()
                    except RuntimeError:
                        pass
                QTimer.singleShot(60, _refocus_main)
            return

        was_max = bool(self._is_effectively_maximized())
        self._reopen_maximized = was_max
        if hasattr(self, '_dwm_cloak'):
            self._dwm_cloak(True)
        self.hide()
        if was_max:
            self._reset_hidden_maximized_state()
        self.finished.emit(result)

    def accept(self):
        self._finish_close(1)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if hasattr(self, 'search_edit') and self.search_edit.text().strip():
                self.search_edit.clear()
                return
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        if getattr(self, '_mac_closed', False):
            event.accept()
            return
        self.reject()
        if getattr(self, '_mac_closed', False) or not self.isVisible():
            event.accept()
        else:
            event.ignore()

    def mousePressEvent(self, event):
        focused = QApplication.focusWidget()
        if focused and focused is not self:
            focused.clearFocus()
        super().mousePressEvent(event)
