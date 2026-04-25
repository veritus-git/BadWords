from PySide6 import QtCore
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: gui.py
ROLE: Presentation Layer
DESCRIPTION:
Responsible solely for displaying the interface (PySide6).
Includes dark-theme styling via QSS based on config.py color palette.
Receives user actions and delegates them to Engine or ResolveHandler.
[PySide6 migration: Stage 2 — Main Window Shell & Dynamic Panels]
"""

import re
import math
import platform
import subprocess
import os
import time
import traceback

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QCheckBox,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QAbstractItemView, QFrame, QScrollArea,
    QDockWidget, QToolBar, QStackedWidget, QFormLayout, QComboBox,
    QSpacerItem, QCompleter, QLineEdit, QWidgetAction, QToolTip,
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation,
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter
)
from PySide6.QtCore import QMimeData

import config
import osdoc

# ==========================================
# CONSTANTS
# ==========================================
RTL_CODES = {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'}  # Right-To-Left Languages


# ==========================================
# HELPERS
# ==========================================

def _app_icon() -> QIcon:
    """Load application icon from the install directory (icon.ico on Windows, icon.png elsewhere)."""
    try:
        install_dir = os.path.dirname(os.path.abspath(__file__))
        is_win = platform.system() == "Windows"
        icon_file = "icon.ico" if is_win else "icon.png"
        icon_path = os.path.join(install_dir, icon_file)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
    except Exception:
        pass
    return QIcon()


def _center_on_screen(widget: QWidget, w: int, h: int):
    """Center *widget* on the primary screen (or active monitor if detectable)."""
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width()  - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        widget.setGeometry(x, y, w, h)


def _txt(lang: str, key: str, **kwargs) -> str:
    """Return translation string for *key* in *lang*, falling back to 'en'."""
    text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


# ==========================================
# CLASS 1: SPLASH SCREEN
# ==========================================

class SplashScreen(QDialog):
    """
    Frameless, dark loading window displayed while engine/api are initializing.
    Shows an animated "loading…" label (0-3 cycling dots at 400 ms).
    Closed by main.py once InitThread emits `loaded`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Window flags: frameless, always on top during splash ---
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Dialog
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        W, H = 300, 150
        self.setFixedSize(W, H)

        # --- QSS styling ---
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
            }}
            QLabel#title {{
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#loading {{
                color: {config.NOTE_COL};
                font-size: 12px;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
        """)

        # --- Layout ---
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 30, 20, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel("BadWords", self)
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)

        self._lbl_loading = QLabel("loading", self)
        self._lbl_loading.setObjectName("loading")
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._lbl_loading)

        # --- Icon ---
        self.setWindowIcon(_app_icon())

        # --- Center on screen ---
        _center_on_screen(self, W, H)

        # --- Dot animation ---
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(400)

    def _animate(self):
        """Cycle the trailing dots: loading → loading. → loading.. → loading..."""
        dots = "." * (self._dot_count % 4)
        self._lbl_loading.setText(f"loading{dots}")
        self._dot_count += 1

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ==========================================
# CLASS 2: TELEMETRY POPUP
# ==========================================

class _LangPickerDialog(QDialog):
    """
    Lightweight language-selection popup (replaces the Tkinter ScrollableMenu).
    Shows all UI languages sorteed alphabetically; emits the selected code.
    Rebuilt as a proper PySide6 dialog — a full ScrollableMenu Port is Stage 2+.
    """
    lang_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFixedWidth(180)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.MENU_BG};
                border: 1px solid #1a1a1a;
            }}
            QListWidget {{
                background-color: {config.MENU_BG};
                color: {config.MENU_FG};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10px;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 5px 8px;
            }}
            QListWidget::item:hover, QListWidget::item:selected {{
                background-color: #4a4e56;
                color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: {config.MENU_BG};
                width: 8px;
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
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self._list)

        # Populate sorted language list
        entries = sorted(
            [(data.get("name", code.upper()), code) for code, data in config.TRANS.items()],
            key=lambda x: x[0]
        )
        for name, code in entries:
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.UserRole, code)
            self._list.addItem(item)

        visible_rows = min(len(entries), 6)
        row_h = 28
        self.setFixedHeight(visible_rows * row_h + 4)

        self._list.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item: QListWidgetItem):
        code = item.data(Qt.UserRole)
        self.lang_selected.emit(code)
        self.close()


class TelemetryPopup(QDialog):
    """
    Modal dialog asking the user for analytics consent.

    Skip condition: if engine.os_doc.get_telemetry_pref("telemetry_opt_in")
    is not None, caller should not show this dialog.

    On "I Agree":
        - Saves telemetry_opt_in = True
        - Saves telemetry_allow_geo = <checkbox state>
        - Calls engine.send_telemetry_ping("app_started")

    On "No thanks" (or Escape / close):
        - Saves telemetry_opt_in = False

    Language changes are persisted to pref.json in real time via
    engine.save_preferences({"gui_lang": code}).
    """

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._lang_picker = None

        # Load current language from preferences
        prefs = engine.load_preferences() or {}
        self._lang = prefs.get("gui_lang", "en")
        if self._lang not in config.TRANS:
            self._lang = "en"

        # --- Window setup ---
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowIcon(_app_icon())

        # --- Root QSS ---
        self.setStyleSheet(f"""
            TelemetryPopup {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
            }}
            QWidget#container {{
                background-color: {config.BG_COLOR};
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_msg {{
                color: {config.FG_COLOR};
                font-size: 10px;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 11px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 2px 4px;
            }}
            QPushButton#btn_lang:hover {{
                color: #ffffff;
            }}
            QPushButton#btn_yes {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 9px;
                font-weight: bold;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }}
            QPushButton#btn_yes:hover {{
                background-color: {config.BTN_ACTIVE};
            }}
            QPushButton#btn_no {{
                background-color: {config.CANCEL_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 9px;
                font-weight: bold;
                border: none;
                padding: 6px 16px;
                border-radius: 3px;
            }}
            QPushButton#btn_no:hover {{
                background-color: {config.CANCEL_ACTIVE};
            }}
            QCheckBox {{
                color: #aaaaaa;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 9px;
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                border: 1px solid #555555;
                border-radius: 2px;
                background: #1a1a1a;
            }}
            QCheckBox::indicator:checked {{
                background-color: {config.BTN_BG};
                border-color: {config.BTN_BG};
            }}
        """)

        # --- Build layout ---
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        container = QWidget(self)
        container.setObjectName("container")
        outer.addWidget(container)

        root_layout = QVBoxLayout(container)
        root_layout.setContentsMargins(20, 25, 20, 20)
        root_layout.setSpacing(0)

        # Header row (title + language button)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self._lbl_title = QLabel("", container)
        self._lbl_title.setObjectName("lbl_title")
        header.addWidget(self._lbl_title, 1)

        self._btn_lang = QPushButton("", container)
        self._btn_lang.setObjectName("btn_lang")
        self._btn_lang.setCursor(Qt.PointingHandCursor)
        self._btn_lang.setFocusPolicy(Qt.NoFocus)
        self._btn_lang.clicked.connect(self._show_lang_picker)
        header.addWidget(self._btn_lang)

        root_layout.addLayout(header)
        root_layout.addSpacing(15)

        # Message label
        self._lbl_msg = QLabel("", container)
        self._lbl_msg.setObjectName("lbl_msg")
        self._lbl_msg.setWordWrap(True)
        self._lbl_msg.setFixedWidth(400)
        self._lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        root_layout.addWidget(self._lbl_msg)
        root_layout.addSpacing(10)

        # Geo checkbox
        self._chk_geo = QCheckBox("", container)
        self._chk_geo.setChecked(True)
        root_layout.addWidget(self._chk_geo)
        root_layout.addSpacing(20)

        # Buttons row (No | Yes)
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        self._btn_no  = QPushButton("", container)
        self._btn_no.setObjectName("btn_no")
        self._btn_no.setCursor(Qt.PointingHandCursor)
        self._btn_no.clicked.connect(self._on_no)
        btn_row.addWidget(self._btn_no)
        btn_row.addSpacing(10)

        self._btn_yes = QPushButton("", container)
        self._btn_yes.setObjectName("btn_yes")
        self._btn_yes.setCursor(Qt.PointingHandCursor)
        self._btn_yes.clicked.connect(self._on_yes)
        btn_row.addWidget(self._btn_yes)
        btn_row.addStretch()

        root_layout.addLayout(btn_row)

        # --- Populate text and size ---
        self._refresh_texts()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _t(self, key: str, **kwargs) -> str:
        return _txt(self._lang, key, **kwargs)

    def _refresh_texts(self):
        """Update all translatable labels and re-size the dialog."""
        self.setWindowTitle(self._t("title_telemetry"))
        self._lbl_title.setText(self._t("title_telemetry"))
        self._lbl_msg.setText(self._t("msg_telemetry"))
        self._btn_yes.setText(self._t("btn_telemetry_yes"))
        self._btn_no.setText(self._t("btn_telemetry_no"))
        self._btn_lang.setText(self._lang.upper())
        self._chk_geo.setText(self._t("chk_telemetry_geo"))

        # Adjust height to fit content and re-center
        self.adjustSize()
        # Fix width so word-wrap calculations are stable
        w = 450
        self.setFixedWidth(w)
        self.adjustSize()
        h = self.sizeHint().height()
        _center_on_screen(self, w, h)

    def _show_lang_picker(self):
        """Open a floating language picker anchored below the lang button."""
        if self._lang_picker and self._lang_picker.isVisible():
            self._lang_picker.close()
            return

        self._lang_picker = _LangPickerDialog(self)
        self._lang_picker.lang_selected.connect(self._on_lang_selected)

        # Position: bottom-right of the language button
        btn_global = self._btn_lang.mapToGlobal(
            self._btn_lang.rect().bottomRight()
        )
        picker_w = self._lang_picker.width()
        self._lang_picker.move(btn_global.x() - picker_w, btn_global.y())
        self._lang_picker.show()

    def _on_lang_selected(self, code: str):
        """Handle language selection: persist and refresh UI."""
        if code == self._lang:
            return
        self._lang = code
        # Persist immediately so the main window picks it up
        self._engine.save_preferences({"gui_lang": code})
        self._refresh_texts()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_yes(self):
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in",   True)
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", self._chk_geo.isChecked())
        self._engine.send_telemetry_ping("app_started")
        self.accept()

    def _on_no(self):
        self._engine.os_doc.set_telemetry_pref("telemetry_opt_in", False)
        self.accept()

    def keyPressEvent(self, event):
        """Escape → same as 'No thanks'."""
        if event.key() == Qt.Key_Escape:
            self._on_no()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Window closed without pressing a button → treat as 'No'."""
        self._on_no()
        super().closeEvent(event)


# ==========================================
# CLASS 3a: TOOLTIPS & SIDEBAR WIDGETS
# ==========================================

class IDETooltip(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #454545;
                padding: 4px 8px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
            }
        """)
        self.hide()

    def show_at(self, widget, text, is_right_side):
        self.setText(text)
        self.adjustSize()

        rect = widget.rect()
        global_pos = widget.mapToGlobal(rect.topLeft())

        if not is_right_side:
            x = global_pos.x() + rect.width() + 5
        else:
            x = global_pos.x() - self.width() - 5

        y = global_pos.y() + (rect.height() - self.height()) // 2
        self.move(x, y)
        self.show()

class SidebarButton(QPushButton):
    """
    Static sidebar item with a fixed 40x40 size and VS Code style static tooltip.
    Now draggable to allow panel repositioning.
    """
    def __init__(self, icon_text: str, label_text: str, activity_id: str, tooltip_widget=None, is_right_side: bool = False, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setText(icon_text)
        self.activity_id = activity_id
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.custom_tooltip_text = label_text
        self.is_right_side = is_right_side
        self.tooltip_widget = tooltip_widget
        self.drag_start_pos = None
        
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_tooltip)
        
        self.is_active = False
        self.set_active(False)

    def set_active(self, is_active: bool):
        self.is_active = is_active
        if is_active:
            border_css = "border-left" if self.is_right_side else "border-right"
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: 24px; 
                    background-color: #333333; 
                    border-radius: 4px;
                    border: none;
                    {border_css}: 2px solid {config.BTN_BG};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    color: white; 
                    font-size: 24px; 
                    background: transparent; 
                    border-radius: 4px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {config.BTN_GHOST_BG};
                }}
            """)

    def enterEvent(self, event):
        self.tooltip_timer.start(750)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.tooltip_timer.stop()
        if self.tooltip_widget:
            self.tooltip_widget.hide()
        super().leaveEvent(event)

    def _show_tooltip(self):
        if self.tooltip_widget:
            self.tooltip_widget.show_at(self, self.custom_tooltip_text, self.is_right_side)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QGuiApplication.styleHints().startDragDistance():
            return
            
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.activity_id)
        drag.setMimeData(mime)
        
        # Snapshot the button for the drag icon
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        drag.exec(Qt.MoveAction)


class SidebarFrame(QFrame):
    """
    A drop-zone container for SidebarButtons
    """
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.drop_indicator = QFrame()
        self.drop_indicator.setStyleSheet("background-color: transparent; border: 1px dashed #555; border-radius: 4px;")
        self.drop_indicator.setMinimumHeight(0)
        self.drop_indicator.hide()
        self.anim = QPropertyAnimation(self.drop_indicator, b"minimumHeight")
        self.anim.setDuration(150)
        self.current_drop_idx = -1
        self._last_drop_index = -1
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.drop_indicator.show()
            self.anim.stop()
            self.anim.setStartValue(self.drop_indicator.minimumHeight())
            self.anim.setEndValue(40)
            self.anim.start()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText():
            return
            
        layout = self.layout()
        drop_y = event.position().y()
        target_idx = 0
        
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if widget is None or widget == self.drop_indicator:
                    continue
                if drop_y < widget.geometry().center().y():
                    break
                else:
                    target_idx += 1
                    
        max_idx = layout.count() - 2
        target_idx = min(target_idx, max_idx)
                    
        if target_idx != self._last_drop_index:
            self._last_drop_index = target_idx
            layout.insertWidget(target_idx, self.drop_indicator)
            self.anim.stop()
            self.anim.setStartValue(self.drop_indicator.minimumHeight())
            self.anim.setEndValue(40)
            self.anim.start()
            
        event.accept()

    def dragLeaveEvent(self, event):
        self.anim.stop()
        self.anim.setStartValue(self.drop_indicator.minimumHeight())
        self.anim.setEndValue(0)
        try:
            self.anim.finished.disconnect()
        except RuntimeError:
            pass
        self.anim.finished.connect(self.drop_indicator.hide)
        self.anim.start()

    def dropEvent(self, event):
        self.anim.stop()
        self.drop_indicator.hide()
        self.drop_indicator.setMinimumHeight(0)
        self.drop_indicator.setParent(None)
        self.current_drop_idx = -1
        self._last_drop_index = -1
        
        activity_id = event.mimeData().text()
        source_btn = event.source()
        if isinstance(source_btn, SidebarButton) and source_btn.activity_id == activity_id:
            layout = self.layout()
            drop_y = event.position().y()
            
            target_idx = layout.count() - 1
            for i in range(layout.count() - 1):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if drop_y < widget.geometry().center().y():
                        target_idx = i
                        break
                        
            max_idx = layout.count() - 2
            target_idx = min(target_idx, max_idx)
                        
            layout.insertWidget(target_idx, source_btn)
            event.acceptProposedAction()
            
            main_window = self.window()
            is_right = (hasattr(main_window, "_sidebar_right") and self == main_window._sidebar_right)
            source_btn.is_right_side = is_right
            if getattr(source_btn, "is_active", False):
                source_btn.set_active(True)


class CustomDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText("Select...")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.addItems(self.options_list)
        list_widget.setStyleSheet("""
            QListWidget { border: none; padding: 0px; margin: 0px; outline: none; background: transparent; color: #d4d4d4; }
            QListWidget::item { padding: 0px 5px; min-height: 26px; border: none; }
            QListWidget::item:selected { background-color: #2a5f8f; }
            QListWidget::item:hover { background-color: #333333; }
        """)
        list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, popup))
        
        fake_header = QPushButton(self.text())
        fake_header.setCursor(Qt.PointingHandCursor)
        fake_header.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: none;
                border-bottom: 1px solid #3a3a3a;
                border-radius: 0px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; background-color: #2a2d2e; }}
        """)
        fake_header.clicked.connect(popup.close)
        layout.addWidget(fake_header)
        
        layout.addWidget(list_widget)
        
        def _update_height():
            row_h = 26
            display_count = min(5, list_widget.count())
            list_height = display_count * row_h
            list_widget.setFixedHeight(list_height)
            
            header_height = fake_header.sizeHint().height()
            popup.setFixedHeight(list_height + header_height)
            
        _update_height()
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()
        
        popup._update_height = _update_height

    def _on_item_clicked(self, item, popup):
        self.setText(item.text())
        self.valueChanged.emit(item.text())
        popup.close()

class SearchableDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText("Select...")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                text-align: left;
                padding: 4px 8px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        self.popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_DeleteOnClose)
        self.popup.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 0px;
                margin: 0px;
            }
        """)
        
        layout = QVBoxLayout(self.popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.list_widget = QListWidget()
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.addItems(self.options_list)
        self.list_widget.setStyleSheet("""
            QListWidget { border: none; padding: 0px; margin: 0px; outline: none; background: transparent; color: #d4d4d4; }
            QListWidget::item { padding: 0px 5px; min-height: 26px; border: none; }
            QListWidget::item:selected { background-color: #2a5f8f; }
            QListWidget::item:hover { background-color: #333333; }
        """)
        self.list_widget.itemClicked.connect(lambda item: self._on_item_clicked(item, self.popup))
        
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Search...")
        self.line_edit.setFixedHeight(self.height())
        self.line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                border: none; border-bottom: 1px solid #3a3a3a; padding: 6px;
                color: #d4d4d4; background: transparent;
            }
        """)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.returnPressed.connect(lambda: self._select_first_visible(self.popup))
        layout.addWidget(self.line_edit)
        
        layout.addWidget(self.list_widget)
        
        self._update_height(self.list_widget.count(), False)
        
        self.line_edit.setFocus()
        
        global_pos = self.mapToGlobal(QPoint(0, 0))
        self.popup.move(global_pos)
        self.popup.show()

    def _on_text_changed(self, text):
        search_str = text.lower()
        visible_count = 0
        
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if search_str in item.text().lower():
                item.setHidden(False)
                visible_count += 1
            else:
                item.setHidden(True)
                
        self._update_height(visible_count, is_searching=bool(text.strip()))

    def _update_height(self, visible_count, is_searching):
        row_h = 26
        
        if is_searching:
            display_count = max(1, min(5, visible_count))
        else:
            display_count = min(5, self.list_widget.count())

        if display_count < 5:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
        list_height = display_count * row_h
        self.list_widget.setFixedHeight(list_height)
        
        total_popup_height = self.height() + list_height
        self.popup.setFixedSize(self.width(), total_popup_height)

    def _select_first_visible(self, popup):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                self.setText(item.text())
                self.valueChanged.emit(item.text())
                popup.close()
                return
        popup.close()

    def _on_item_clicked(self, item, popup):
        self.setText(item.text())
        self.valueChanged.emit(item.text())
        popup.close()


class SettingsDialog(QDialog):
    """
    Stage 5: Audio Sync and Options Dialog
    """
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("Settings")
        self.setWindowFlags(Qt.Tool | Qt.Dialog)
        self.setFixedSize(300, 250)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {config.BG_COLOR}; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; font-size: 11px; }}
            QCheckBox {{ color: {config.FG_COLOR}; font-family: "{config.UI_FONT_NAME}"; font-size: 11px; }}
            QDoubleSpinBox {{ background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; padding: 3px; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Audio Sync Settings
        lbl_sync = QLabel("<b>Audio Sync (Seconds)</b>")
        layout.addWidget(lbl_sync)
        
        form = QFormLayout()
        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10, 10)
        self.spin_offset.setSingleStep(0.1)
        self.spin_pad = QDoubleSpinBox()
        self.spin_pad.setRange(0, 5)
        self.spin_pad.setSingleStep(0.1)
        self.spin_snap = QDoubleSpinBox()
        self.spin_snap.setRange(0, 5)
        self.spin_snap.setSingleStep(0.1)
        
        form.addRow("Offset (s):", self.spin_offset)
        form.addRow("Padding (s):", self.spin_pad)
        form.addRow("Snap Max (s):", self.spin_snap)
        layout.addLayout(form)
        
        # Advanced View Options
        self.chk_show_inaudible = QCheckBox("Show inaudible fragments")
        self.chk_mark_inaudible = QCheckBox("Mark inaudible fragments with brown")
        layout.addWidget(self.chk_show_inaudible)
        layout.addWidget(self.chk_mark_inaudible)
        
        # Save Button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_ok = QPushButton("Save")
        btn_ok.setFixedSize(80, 30)
        btn_ok.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; border-radius: 4px;")
        btn_ok.clicked.connect(self.accept)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)


# ==========================================
# CLASS 3: MAIN APPLICATION WINDOW
# ==========================================

class BadWordsGUI(QMainWindow):
    """
    Stage 3 — QMainWindow implementing the "VS Code" unified workspace:
      - Opens maximized on the monitor under the cursor
      - NO top toolbar; left and right vertical activity bars instead
      - QStackedWidget as the central widget (3 pages)
        Page 0: Welcome / Config   (flat, borderless — default view)
        Page 1: Processing         (progress placeholder)
        Page 2: Editor             (editor placeholder)
      - Right dock starts hidden; revealed when analysis begins
    """

    def __init__(self, engine, resolve_handler, parent=None):
        super().__init__(parent)

        self.engine              = engine
        self.resolve_handler     = resolve_handler
        # This callback is injected by AppController in main.py
        self.closeEvent_callback = None
        self.shared_tooltip = IDETooltip()
        
        # Declare panel containers early for Pyre inference
        self._sidebar_left: SidebarFrame = None
        self._sidebar_right: SidebarFrame = None
        self._panel_left: QSplitter = None
        self._panel_right: QSplitter = None
        
        self._open_left = []
        self._open_right = []

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

        # --- Global QSS ---
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {config.BG_COLOR};
            }}
            .QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10px;
            }}
            /* ---- Scrollbars (global) ---- */
            QScrollBar:vertical {{
                background: {config.SCROLL_BG};
                width: 8px;
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
        """)

        # --- Build UI ---
        self._build_sidebars()         # left + right activity frames
        self._build_central_workspace() # QStackedWidget central area + panels

        # --- Maximize on the monitor the cursor is on ---
        self._maximize_on_active_screen()

        # --- Telemetry check fires 500 ms after first paint ---
        QTimer.singleShot(500, self.check_telemetry)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def closeEvent(self, event):
        """Native PySide6 close event override."""
        if self.closeEvent_callback:
            self.closeEvent_callback(event)
        else:
            event.accept()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_sidebars(self):
        """
        Left and right vertical activity frames overlaying the main window.
        """
        self._sidebar_left = SidebarFrame(self)
        self._sidebar_left.setFixedWidth(50)
        self._sidebar_left.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        left_layout = QVBoxLayout(self._sidebar_left)
        left_layout.setContentsMargins(5, 6, 5, 6)
        left_layout.setSpacing(6)
        
        btn_script = SidebarButton("\U0001f4dd", "Script", "script", tooltip_widget=self.shared_tooltip)
        btn_script.clicked.connect(lambda: self._toggle_activity("script"))
        left_layout.addWidget(btn_script)
        
        btn_analysis = SidebarButton("\U0001f4ca", "Analysis", "analyze", tooltip_widget=self.shared_tooltip)
        btn_analysis.clicked.connect(lambda: self._toggle_activity("analyze"))
        left_layout.addWidget(btn_analysis)
        
        left_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        btn_settings = SidebarButton("\u2699", "Settings", "settings", tooltip_widget=self.shared_tooltip)
        btn_settings.clicked.connect(self._on_settings)
        left_layout.addWidget(btn_settings)
        
        self._sidebar_left.show()

        self._sidebar_right = SidebarFrame(self)
        self._sidebar_right.setFixedWidth(50)
        self._sidebar_right.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        right_layout = QVBoxLayout(self._sidebar_right)
        right_layout.setContentsMargins(5, 6, 5, 6)
        right_layout.setSpacing(6)
        
        btn_markers = SidebarButton("\u2702", "Markers", "toolbox", tooltip_widget=self.shared_tooltip, is_right_side=True)
        btn_markers.clicked.connect(lambda: self._toggle_activity("toolbox"))
        right_layout.addWidget(btn_markers)
        
        btn_automation = SidebarButton("\U0001f5e8", "Automation", "automation", tooltip_widget=self.shared_tooltip, is_right_side=True)
        btn_automation.clicked.connect(lambda: self._toggle_activity("automation"))
        right_layout.addWidget(btn_automation)
        
        right_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

    def _build_central_workspace(self):
        """
        Main container incorporating sidebars, panels, and central stack using QHBoxLayout.
        """
        main_container = QWidget()
        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Build Panels
        self._panel_left = QSplitter(Qt.Vertical)
        self._panel_left.setFixedWidth(280)
        self._panel_left.setObjectName("leftPanel")
        self._panel_left.setStyleSheet("QSplitter { background: transparent; } QSplitter::handle { background: transparent; height: 6px; }")
        self._panel_left.hide()

        self._stack = QStackedWidget()
        self._stack.setObjectName("stack")
        self._stack.setStyleSheet(f"QStackedWidget#stack {{ background-color: {config.BG_COLOR}; }}")
        self._stack.addWidget(self._build_welcome_screen())   # index 0
        self._stack.addWidget(self._build_page_processing())  # index 1
        self._stack.addWidget(self._build_page_editor())      # index 2
        self._stack.setCurrentIndex(0)

        self._panel_right = QSplitter(Qt.Vertical)
        self._panel_right.setFixedWidth(280)
        self._panel_right.setObjectName("rightPanel")
        self._panel_right.setStyleSheet("QSplitter { background: transparent; } QSplitter::handle { background: transparent; height: 6px; }")
        self._panel_right.hide()
        
        self.activities = {}
        self.active_activity = None
        self._build_activities()

        # Splitter layout for panels and stack
        self._main_h_splitter = QSplitter(Qt.Horizontal)
        self._main_h_splitter.addWidget(self._panel_left)
        self._main_h_splitter.addWidget(self._stack)
        self._main_h_splitter.addWidget(self._panel_right)
        self._main_h_splitter.setHandleWidth(1)
        self._main_h_splitter.setStyleSheet("QSplitter::handle { background-color: #1a1a1a; }")

        # Add everything to main layout in exact order
        main_layout.addWidget(self._sidebar_left)
        main_layout.addWidget(self._main_h_splitter)
        main_layout.addWidget(self._sidebar_right)

        self.setCentralWidget(main_container)

    def _toggle_activity(self, activity_id: str):
        target_btn = None
        target_splitter = None
        
        for i in range(self._sidebar_left.layout().count()):
            widget = self._sidebar_left.layout().itemAt(i).widget()
            if isinstance(widget, SidebarButton) and widget.activity_id == activity_id:
                target_btn = widget
                target_splitter = self._panel_left
                break
                
        if not target_btn:
            for i in range(self._sidebar_right.layout().count()):
                widget = self._sidebar_right.layout().itemAt(i).widget()
                if isinstance(widget, SidebarButton) and widget.activity_id == activity_id:
                    target_btn = widget
                    target_splitter = self._panel_right
                    break
                    
        if not target_btn or not target_splitter:
            return  # Activity button not found in sidebars

        assert target_btn is not None
        assert target_splitter is not None

        activity_widget = self.activities[activity_id]
        
        # Check if the widget is currently inside a visible splitter
        is_open = activity_widget.parent() in (self._panel_left, self._panel_right) and activity_widget.isVisible()
        
        if is_open:
            activity_widget.setParent(None)
            activity_widget.hide()
            target_btn.set_active(False)
            if target_splitter.count() == 0:
                target_splitter.hide()
                
            if target_splitter == self._panel_left and activity_id in self._open_left:
                self._open_left.remove(activity_id)
            elif target_splitter == self._panel_right and activity_id in self._open_right:
                self._open_right.remove(activity_id)
        else:
            if activity_widget.parent():
                activity_widget.setParent(None)
                
            target_splitter.addWidget(activity_widget)
            activity_widget.show()
            target_btn.set_active(True)
            target_splitter.show()
            self._main_h_splitter.setSizes([280, 2000, 280])
            
            active_list = self._open_left if target_splitter == self._panel_left else self._open_right
            active_list.append(activity_id)
            
            if len(active_list) > 3:
                oldest_id = active_list.pop(0)
                oldest_widget = self.activities[oldest_id]
                oldest_widget.setParent(None)
                oldest_widget.hide()
                
                sidebar = self._sidebar_left if target_splitter == self._panel_left else self._sidebar_right
                for i in range(sidebar.layout().count()):
                    btn = sidebar.layout().itemAt(i).widget()
                    if isinstance(btn, SidebarButton) and getattr(btn, "activity_id", None) == oldest_id:
                        btn.set_active(False)
                        break

    def _build_activities(self):
        def _wrap_activity(widget: QWidget) -> QFrame:
            container = QFrame()
            container.setObjectName("ActivityPanel")
            container.setAttribute(Qt.WA_StyledBackground, True)

            container.setStyleSheet("""
                QFrame#ActivityPanel {
                    background-color: #212121;
                    border-radius: 6px;
                    margin: 2px;
                }
                /* Force all generic children to be transparent so the grey shows through */
                QFrame#ActivityPanel QWidget {
                    background-color: transparent;
                }
                /* Restore specific background for input fields so they don't blend in */
                QFrame#ActivityPanel QTextEdit,
                QFrame#ActivityPanel QDoubleSpinBox,
                QFrame#ActivityPanel QLineEdit {
                    background-color: #1e1e1e;
                    border: 1px solid #3a3a3a;
                    color: #ffffff;
                }
            """)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget)
            return container

        # Activity 1: Script
        p_script = QWidget()
        l_script = QVBoxLayout(p_script)
        text_edit = QTextEdit()
        text_edit.setStyleSheet("QTextEdit { background-color: #1e1e1e; border: 1px solid #3a3a3a; border-radius: 3px; padding: 5px; color: #ffffff; }")
        text_edit.setPlaceholderText("Paste script here...")
        text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        l_script.addWidget(text_edit)
        
        btn_row = QHBoxLayout()
        btn_import = QPushButton("Import Script")
        btn_import.setStyleSheet(f"background-color: #1e1e1e; color: #d4d4d4; padding: 4px; border: 1px solid #3a3a3a;")
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet(f"background-color: #1e1e1e; color: #d4d4d4; padding: 4px; border: 1px solid #3a3a3a;")
        btn_row.addWidget(btn_import)
        btn_row.addWidget(btn_clear)
        l_script.addLayout(btn_row)
        self.activities["script"] = _wrap_activity(p_script)
        
        # Activity 2: Analyze
        p_analyze = QWidget()
        l_analyze = QVBoxLayout(p_analyze)
        l_analyze.addStretch(1)
        l_analyze.setSpacing(15)
        
        btn_analyze = QPushButton("ANALYZE")
        btn_analyze.setMinimumHeight(40)
        btn_analyze.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; font-weight: bold; font-size: 14px; border: none; border-radius: 4px;")
        l_analyze.addWidget(btn_analyze)
        
        btn_replace = QPushButton("Replace typos in transcript\nwith text from script")
        btn_replace.setStyleSheet(f"background-color: #1e1e1e; color: #d4d4d4; padding: 4px; border: 1px solid #3a3a3a;")
        l_analyze.addWidget(btn_replace)
        
        btn_undo = QPushButton("Undo Replace")
        btn_undo.setStyleSheet(f"background-color: #444444; color: #aaaaaa; padding: 2px; border: none;")
        l_analyze.addWidget(btn_undo)
        
        btn_clear_transcript = QPushButton("Clear Transcript")
        btn_clear_transcript.setStyleSheet(f"background-color: #1e1e1e; color: #e74c3c; padding: 4px; border: 1px solid #3a3a3a;")
        l_analyze.addWidget(btn_clear_transcript)
        
        l_analyze.addStretch(1)
        self.activities["analyze"] = _wrap_activity(p_analyze)
        
        # Activity 3: Toolbox
        p_toolbox = QWidget()
        l_toolbox = QVBoxLayout(p_toolbox)
        l_toolbox.addStretch(1)
        l_toolbox.setSpacing(15)
        
        l_toolbox.addWidget(QRadioButton("RED - Cut/Filler"))
        l_toolbox.addWidget(QRadioButton("BLUE - Retake"))
        l_toolbox.addWidget(QRadioButton("GREEN - Typo"))
        l_toolbox.addWidget(QRadioButton("ERASER - Clear"))
        
        lbl_dummy = QLabel("add custom marker...")
        lbl_dummy.setStyleSheet(f"color: #888888; text-decoration: underline;")
        l_toolbox.addWidget(lbl_dummy)
        
        l_toolbox.addWidget(QCheckBox("Delete red clips automatically"))
        
        l_toolbox.addStretch(1)
        self.activities["toolbox"] = _wrap_activity(p_toolbox)
        
        # Activity 4: Automation
        p_automation = QWidget()
        l_automation = QVBoxLayout(p_automation)
        l_automation.addStretch(1)
        l_automation.setSpacing(15)
        
        fillers_edit = QTextEdit()
        fillers_edit.setStyleSheet("QTextEdit { background-color: #1e1e1e; border: 1px solid #3a3a3a; border-radius: 3px; padding: 5px; color: #ffffff; }")
        fillers_edit.setMaximumHeight(60)
        l_automation.addWidget(QLabel("Filler Words:"))
        l_automation.addWidget(fillers_edit)
        l_automation.addWidget(QCheckBox("Mark filler words automatically"))
        
        form = QFormLayout()
        spin_threshold = QDoubleSpinBox()
        spin_threshold.setRange(-100, 0)
        spin_threshold.setStyleSheet("QDoubleSpinBox { background-color: #1e1e1e; color: #ffffff; border: 1px solid #3a3a3a; padding: 3px; }")
        spin_padding = QDoubleSpinBox()
        spin_padding.setRange(0, 10)
        spin_padding.setStyleSheet("QDoubleSpinBox { background-color: #1e1e1e; color: #ffffff; border: 1px solid #3a3a3a; padding: 3px; }")
        form.addRow("Threshold (dB):", spin_threshold)
        form.addRow("Padding (s):", spin_padding)
        l_automation.addLayout(form)
        
        l_automation.addWidget(QCheckBox("Detect and cut silence"))
        l_automation.addWidget(QCheckBox("Detect and mark silence"))
        
        l_automation.addStretch(1)
        self.activities["automation"] = _wrap_activity(p_automation)

    # Removed deprecated _on_nav_script and _on_nav_analysis


    def _build_welcome_screen(self) -> QWidget:
        """
        Page 0: flat Welcome / Config screen.
        - 36px / weight 900 title
        - Vertical form: label ABOVE each input
        - Native QComboBox (editable=True, maxVisibleItems=4) with an event
          filter on its lineEdit() that calls showPopup() on click, giving
          perfect searchable combo-box behaviour
        """
        page = QWidget()
        page.setObjectName("page_welcome")
        page.setStyleSheet(f"QWidget#page_welcome {{ background-color: {config.BG_COLOR}; }}")

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        inner = QWidget()
        inner.setObjectName("welcome_inner")
        inner.setFixedWidth(320)
        inner.setStyleSheet("QWidget#welcome_inner { background: transparent; }")

        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
            """Label directly above the input."""
            row = QVBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {config.NOTE_COL}; font-size: 9px;"
                f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
            )
            row.addWidget(lbl)
            row.addWidget(widget)
            return row

        # ── Title ────────────────────────────────────────────────────────
        lbl_title = QLabel("BadWords", inner)
        lbl_title.setObjectName("welcome_title")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"""
            QLabel#welcome_title {{
                color: #ffffff;
                font-size: 36px;
                font-weight: 900;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
                letter-spacing: -2px;
            }}
        """)
        inner_layout.addWidget(lbl_title)

        lbl_sub = QLabel("Transcription workspace", inner)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 10px;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        inner_layout.addWidget(lbl_sub)
        inner_layout.addSpacing(28)

        # ── Language — editable SearchableDropdown ────────────────────────────
        lang_items = list(config.SUPPORTED_LANGUAGES.values())
        self._combo_lang = SearchableDropdown(lang_items)
        prefs = self.engine.load_preferences() or {}
        if "lang" in prefs and prefs["lang"] in lang_items:
            self._combo_lang.setText(prefs["lang"])
        else:
            self._combo_lang.setText("Auto")
        self._combo_lang.valueChanged.connect(lambda v: self.engine.save_preferences({"gui_lang": v}))
        inner_layout.addLayout(_row(self.txt("lbl_lang"), self._combo_lang))
        inner_layout.addSpacing(10)

        # ── Model — non-editable CustomDropdown ───────────────────────────
        model_items = [
            "Tiny  (Fast, <1 GB)",
            "Base  (Balanced, 1 GB)",
            "Small  (Good, 2 GB)",
            "Medium  (5 GB)",
            "Large Turbo  (Fast & Precise, 6 GB)",
            "Large  (Accurate, 10 GB)",
        ]
        self._combo_model = CustomDropdown(model_items)
        if "model" in prefs and prefs["model"] in model_items:
            self._combo_model.setText(prefs["model"])
        else:
            self._combo_model.setText(model_items[4])
        self._combo_model.valueChanged.connect(lambda v: self.engine.save_preferences({"model": v}))
        inner_layout.addLayout(_row(self.txt("lbl_model"), self._combo_model))
        inner_layout.addSpacing(10)

        # ── Device — non-editable CustomDropdown ──────────────────────────
        device_items = ["Auto", "CPU", "GPU (CUDA)"]
        self._combo_device = CustomDropdown(device_items)
        if "device" in prefs and prefs["device"] in device_items:
            self._combo_device.setText(prefs["device"])
        else:
            self._combo_device.setText("Auto")
        self._combo_device.valueChanged.connect(lambda v: self.engine.save_preferences({"device": v}))
        inner_layout.addLayout(_row(self.txt("lbl_device"), self._combo_device))
        inner_layout.addSpacing(24)

        # ── Buttons ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        btn_import = QPushButton(self.txt("btn_import_proj"))
        btn_import.setObjectName("btn_ghost")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.setFixedHeight(30)
        btn_import.setStyleSheet(f"""
            QPushButton#btn_ghost {{
                background-color: #1e1e1e;
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10px;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 0 12px;
            }}
            QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
            QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
        """)
        btn_import.clicked.connect(self._on_import_project)
        btn_row.addWidget(btn_import)

        btn_analyze = QPushButton("\u25b6  " + self.txt("btn_analyze"))
        btn_analyze.setObjectName("btn_primary")
        btn_analyze.setCursor(Qt.PointingHandCursor)
        btn_analyze.setFixedHeight(30)
        btn_analyze.setStyleSheet(f"""
            QPushButton#btn_primary {{
                background-color: {config.BTN_BG};
                color: #ffffff;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10px;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 0 18px;
            }}
            QPushButton#btn_primary:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_primary:pressed {{ background-color: #3b44a8; }}
        """)
        btn_analyze.clicked.connect(self._on_start_analysis)
        btn_row.addWidget(btn_analyze)

        inner_layout.addLayout(btn_row)

        # ── Centre horizontally ──────────────────────────────────────────
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch()
        h.addWidget(inner)
        h.addStretch()
        outer.addLayout(h)

        outer.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        return page

    def _build_page_processing(self) -> QWidget:
        """Page 1: Processing / progress placeholder."""
        page = QWidget()
        page.setObjectName("page_processing")
        page.setStyleSheet(
            f"QWidget#page_processing {{ background-color: {config.BG_COLOR}; }}"
        )
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel("Processing...", page)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 16px;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        layout.addWidget(lbl)
        return page

    def _build_page_editor(self) -> QWidget:
        """Page 2: Editor area placeholder."""
        page = QWidget()
        page.setObjectName("page_editor")
        page.setStyleSheet(
            f"QWidget#page_editor {{ background-color: {config.BG_COLOR}; }}"
        )
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        lbl = QLabel("Editor Area", page)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 16px;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        layout.addWidget(lbl)
        return page

    # ------------------------------------------------------------------
    # Sidebar navigation stubs
    # ------------------------------------------------------------------

    def _on_nav_script(self):
        """Navigate to the Script / Welcome page."""
        self.go_to_page(0)

    def _on_nav_analysis(self):
        """Navigate to the Analysis / Processing page."""
        self.go_to_page(1)

    def _on_nav_markers(self):
        """Toggle the right panel (placeholder)."""
        print("[BadWordsGUI] Tools toggled (Stage 4 TODO)")

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def _maximize_on_active_screen(self):
        """
        Move the window to the monitor that currently has the cursor,
        set its geometry to that screen's available geometry, then maximize.
        This is the standard multi-monitor pattern for PySide6.
        """
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            self.showMaximized()
            return
        self.setGeometry(screen.availableGeometry())
        self.showMaximized()

    # ------------------------------------------------------------------
    # Action handlers (stubs — logic added in later stages)
    # ------------------------------------------------------------------

    def _on_settings(self):
        """Open settings panel."""
        dlg = SettingsDialog(self.engine, self)
        dlg.exec()

    def _on_import_project(self):
        """Placeholder: import project (Stage 4+)."""
        print("[BadWordsGUI] Import Project triggered (Stage 4 TODO)")

    def _on_start_analysis(self):
        """Placeholder: begin analysis flow, switch to processing page."""
        print("[BadWordsGUI] Start Analysis triggered (Stage 4 TODO)")
        self.go_to_page(1)  # Jump to Processing page

    # ------------------------------------------------------------------
    # Page navigation
    # ------------------------------------------------------------------

    def go_to_page(self, index: int):
        """
        Switch the central QStackedWidget to *index*.
        """
        self._stack.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    def check_telemetry(self):
        """Show TelemetryPopup if consent has never been recorded."""
        opt_in = self.engine.os_doc.get_telemetry_pref("telemetry_opt_in")
        if opt_in is None:
            popup = TelemetryPopup(self.engine, parent=self)
            popup.exec()  # ApplicationModal — blocks until user responds
        elif opt_in is True:
            self.engine.send_telemetry_ping("app_started")

    # ------------------------------------------------------------------
    # Translation helper
    # ------------------------------------------------------------------

    def txt(self, key: str, **kwargs) -> str:
        return _txt(self.lang, key, **kwargs)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        if self.closeEvent_callback:
            self.closeEvent_callback()
        super().closeEvent(event)