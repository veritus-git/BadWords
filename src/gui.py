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
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter, QSplitterHandle
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation, Property
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter, QPen
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

class GripHandle(QSplitterHandle):
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # Fill entirely with workspace background first
        painter.fillRect(self.rect(), QColor("#1c1c1c"))
        
        is_left_handle = self.geometry().x() < (self.parent().width() / 2)
        
        pill_width = 8
        pill_height = 42
        y = (h - pill_height) // 2
        
        # Extend panel color and anchor the pill
        if is_left_handle:
            # Panel is on the left.
            painter.fillRect(0, 0, w // 2 + 2, h, QColor("#212121"))
            x = (w // 2 + 2) - pill_width # Anchor pill to the right edge of the panel color
        else:
            # Panel is on the right.
            painter.fillRect(w // 2 - 2, 0, w - (w // 2 - 2), h, QColor("#212121"))
            x = w // 2 - 2 # Anchor pill to the left edge of the panel color
            
        # Draw Grip Pill
        painter.setBrush(QColor("#444444"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, pill_width, pill_height, 3, 3)
        
        # Draw 3 Dots
        painter.setBrush(QColor("#999999"))
        dot_size = 2
        dot_x = x + (pill_width - dot_size) // 2
        
        painter.drawEllipse(dot_x, y + 8, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 20, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 32, dot_size, dot_size)

class GripSplitter(QSplitter):
    def createHandle(self):
        handle = GripHandle(self.orientation(), self)
        handle.setCursor(Qt.CursorShape.SplitHCursor)
        return handle

class ToggleSwitch(QWidget):
    """
    iOS-style animated toggle switch inheriting from QWidget.
    """
    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_checked = False

        # Internal animation states
        self._thumb_x = 2
        self._bg_color = QColor("#555555")
        
        # Animators
        self._anim_group = QPropertyAnimation(self, b"thumb_x")
        self._anim_group.setDuration(150)
        
        self._color_anim = QPropertyAnimation(self, b"bg_color")
        self._color_anim.setDuration(150)

    @Property(float)
    def thumb_x(self):
        return self._thumb_x

    @thumb_x.setter
    def thumb_x(self, value):
        self._thumb_x = value
        self.update()
        
    @Property(QColor)
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = value
        self.update()

    def isChecked(self) -> bool:
        return self._is_checked

    def setChecked(self, checked: bool, animated: bool = True):
        if self._is_checked == checked:
            return
        self._is_checked = checked

        if animated:
            self._update_animation()
        else:
            self._bg_color = QColor(config.BTN_BG) if checked else QColor("#555555")
            self._thumb_x = self.width() - 20 if checked else 4
            self.update()
        
        self.toggled.emit(self._is_checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_checked = not self._is_checked
            self._update_animation()
            self.toggled.emit(self._is_checked)
        super().mouseReleaseEvent(event)

    def _update_animation(self):
        self._anim_group.stop()
        self._color_anim.stop()
        
        end_x = 18 if self._is_checked else 2
        end_color = QColor(config.BTN_BG) if self._is_checked else QColor("#555555")
        
        self._anim_group.setEndValue(float(end_x))
        self._color_anim.setEndValue(end_color)
        
        self._anim_group.start()
        self._color_anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Draw background capsule
        p.setPen(Qt.NoPen)
        p.setBrush(self._bg_color)
        rect = QRect(0, 0, self.width(), self.height())
        p.drawRoundedRect(rect, 10, 10)
        
        # Draw white thumb
        p.setBrush(QColor("white"))
        thumb_rect = QRect(int(self._thumb_x), 2, 16, 16)
        p.drawEllipse(thumb_rect)


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
        self.shared_tooltip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.shared_tooltip.setWindowFlag(Qt.WindowTransparentForInput, True)
        
        # Declare panel containers early for Pyre inference
        self._sidebar_right: SidebarFrame = None
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
        
        self.btn_nav_script = SidebarButton("\U0001f4dd", "Script & Analysis", "script_analysis", tooltip_widget=self.shared_tooltip)
        self.btn_nav_script.clicked.connect(lambda: self._toggle_activity("script_analysis"))
        left_layout.addWidget(self.btn_nav_script)
        
        self.btn_nav_silence = SidebarButton("\U0001f507", "Silence", "silence", tooltip_widget=self.shared_tooltip)
        self.btn_nav_silence.clicked.connect(lambda: self._toggle_activity("silence"))
        left_layout.addWidget(self.btn_nav_silence)

        self.btn_nav_fillers = SidebarButton("\U0001f4ac", "Filler Words", "fillers", tooltip_widget=self.shared_tooltip)
        self.btn_nav_fillers.clicked.connect(lambda: self._toggle_activity("fillers"))
        left_layout.addWidget(self.btn_nav_fillers)
        
        left_layout.addSpacerItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.btn_nav_quit = SidebarButton("\U0001f6aa", "Quit", "quit", tooltip_widget=self.shared_tooltip)
        self.btn_nav_quit.clicked.connect(self.close)
        left_layout.addWidget(self.btn_nav_quit)
        
        self.btn_nav_settings = SidebarButton("\u2699", "Settings", "settings", tooltip_widget=self.shared_tooltip)
        self.btn_nav_settings.clicked.connect(self._on_settings)
        left_layout.addWidget(self.btn_nav_settings)
        
        self._sidebar_left.show()

        self._sidebar_right = SidebarFrame(self)
        self._sidebar_right.setFixedWidth(50)
        self._sidebar_right.setStyleSheet(f"QFrame {{ background-color: {config.SIDEBAR_BG}; border: none; }}")
        right_layout = QVBoxLayout(self._sidebar_right)
        right_layout.setContentsMargins(5, 6, 5, 6)
        right_layout.setSpacing(6)
        
        self.btn_nav_main = SidebarButton("\U0001f6e0\ufe0f", "Main Panel", "main_panel", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_main.clicked.connect(lambda: self._toggle_activity("main_panel"))
        right_layout.addWidget(self.btn_nav_main)
        
        self.btn_nav_assembly = SidebarButton("\u2699\ufe0f", "Assembly", "assembly", tooltip_widget=self.shared_tooltip, is_right_side=True)
        self.btn_nav_assembly.clicked.connect(lambda: self._toggle_activity("assembly"))
        right_layout.addWidget(self.btn_nav_assembly)
        
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
        self._panel_left = QFrame()
        self._panel_left.setMinimumWidth(150)
        self._panel_left.setObjectName("leftPanel")
        self._panel_left.setStyleSheet("QFrame#leftPanel { background: transparent; } QFrame#ActivityPanel { background-color: #212121; border-radius: 6px; }")
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
        self._panel_right.setStyleSheet("QFrame#rightPanel { background: transparent; } QFrame#ActivityPanel { background-color: #212121; border-radius: 6px; }")
        QVBoxLayout(self._panel_right).setContentsMargins(0, 0, 0, 0)
        self._panel_right.hide()
        
        self.activities = {}
        self.active_activity = None
        self._build_activities()

        # Splitter layout for panels and stack
        self._main_h_splitter = GripSplitter(Qt.Horizontal)
        self._main_h_splitter.setChildrenCollapsible(False)
        self._main_h_splitter.addWidget(self._panel_left)
        self._main_h_splitter.addWidget(self._stack)
        self._main_h_splitter.addWidget(self._panel_right)
        self._main_h_splitter.setHandleWidth(12)
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
        sidebar = self._sidebar_left if not target_btn.is_right_side else self._sidebar_right
        
        is_already_active = target_btn.is_active
        
        if is_already_active:
            target_splitter.hide()
            target_btn.set_active(False)
        else:
            for i in range(sidebar.layout().count()):
                btn = sidebar.layout().itemAt(i).widget()
                if isinstance(btn, SidebarButton):
                    btn.set_active(False)
                    
            target_btn.set_active(True)
            layout = target_splitter.layout()
            
            # Clear existing items safely
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    
            layout.addWidget(activity_widget)
            activity_widget.show()
            target_splitter.show()
            self._main_h_splitter.setSizes([480, 2000, 480])

    def _build_activities(self):
        def _wrap_activity(widget: QWidget) -> QFrame:
            container = QFrame()
            container.setObjectName("ActivityPanel")
            container.setAttribute(Qt.WA_StyledBackground, True)

            container.setStyleSheet("""
                QFrame#ActivityPanel {
                    background-color: #212121;
                    border-radius: 0px;
                    margin: 0px;
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
                QFrame#ActivityPanel QPushButton {
                    background-color: #333333;
                    border: 1px solid #454545;
                    border-radius: 4px;
                    padding: 5px;
                    color: #d9d9d9;
                }
                QFrame#ActivityPanel QPushButton:hover { background-color: #404040; border-color: #555555; }
                QFrame#ActivityPanel QPushButton:disabled { background-color: #2a2a2a; border-color: #222; color: #555555; }
            """)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget)
            return container

        def style_rb(rb, color):
            rb.setStyleSheet(f"""
                QRadioButton {{ color: {color}; font-weight: bold; }}
                QRadioButton::indicator {{
                    width: 12px; height: 12px;
                    border-radius: 7px;
                    border: 2px solid #555555;
                    background: transparent;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #555555;
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.45, fx:0.5, fy:0.5, stop:0 {color}, stop:0.8 {color}, stop:1 transparent);
                }}
            """)

        # A. script_analysis
        p_script_analysis = QWidget()
        l_script_analysis = QVBoxLayout(p_script_analysis)
        l_script_analysis.setContentsMargins(15, 15, 15, 15)
        l_script_analysis.setSpacing(10)
        
        self.text_script = QTextEdit()
        self.text_script.setPlaceholderText("Paste script here...")
        l_script_analysis.addWidget(self.text_script)
        
        btn_row_script = QHBoxLayout()
        self.btn_import_script = QPushButton("Import Script")
        self.btn_import_script.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_script = QPushButton("Clear")
        self.btn_clear_script.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row_script.addWidget(self.btn_import_script)
        btn_row_script.addWidget(self.btn_clear_script)
        l_script_analysis.addLayout(btn_row_script)
        
        self.btn_analyze_compare = QPushButton("ANALYZE (Compare)")
        self.btn_analyze_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_compare.setFixedHeight(35)
        self.btn_analyze_compare.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; font-weight: bold; font-size: 14px; border: none; border-radius: 4px; padding: 10px;")
        l_script_analysis.addWidget(self.btn_analyze_compare)
        
        self._analyze_color_anim = QVariantAnimation(self)
        self._analyze_color_anim.setDuration(250)

        def update_btn_style(color):
            self.btn_analyze_compare.setStyleSheet(f"QPushButton {{ background-color: {color.name()}; border: 1px solid #111; border-radius: 4px; color: #fff; font-weight: bold; padding: 8px; }}")
        self._analyze_color_anim.valueChanged.connect(update_btn_style)
        
        self.btn_analyze_standalone = QPushButton("ANALYZE (Standalone)")
        self.btn_analyze_standalone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_standalone.setFixedHeight(35)
        self.btn_analyze_standalone.setEnabled(False)
        l_script_analysis.addWidget(self.btn_analyze_standalone)
        
        self.activities["script_analysis"] = _wrap_activity(p_script_analysis)
        
        # Connect text change logic
        def update_compare_btn():
            has_text = bool(self.text_script.toPlainText().strip())
            
            # Check if state actually changed to prevent animation loop on every keystroke
            if getattr(self, '_analyze_last_state', None) == has_text:
                return 
            self._analyze_last_state = has_text
            
            self.btn_analyze_compare.setEnabled(has_text)
            
            start_color = QColor("#2a2a2a") if has_text else QColor(config.BTN_BG)
            end_color = QColor(config.BTN_BG) if has_text else QColor("#2a2a2a")

            self._analyze_color_anim.stop()
            self._analyze_color_anim.setStartValue(start_color)
            self._analyze_color_anim.setEndValue(end_color)
            self._analyze_color_anim.start()
            
        self.text_script.textChanged.connect(update_compare_btn)
        update_compare_btn()

        # B. silence
        p_silence = QWidget()
        l_silence = QVBoxLayout(p_silence)
        l_silence.setContentsMargins(15, 15, 15, 15)
        l_silence.setSpacing(10)
        
        form_silence = QFormLayout()
        self.spin_thresh = QDoubleSpinBox()
        self.spin_thresh.setRange(-100, 0)
        self.spin_thresh.setValue(-42.0)
        self.spin_pad = QDoubleSpinBox()
        self.spin_pad.setRange(0, 5)
        self.spin_pad.setSingleStep(0.05)
        self.spin_pad.setValue(0.05)
        form_silence.addRow("Threshold (dB):", self.spin_thresh)
        form_silence.addRow("Padding (s):", self.spin_pad)
        l_silence.addLayout(form_silence)
        
        row_silence_cut = QHBoxLayout()
        row_silence_cut.addWidget(QLabel("Detect and cut silence"))
        row_silence_cut.addStretch()
        self.tgl_silence_cut = ToggleSwitch()
        row_silence_cut.addWidget(self.tgl_silence_cut)
        l_silence.addLayout(row_silence_cut)
        
        row_silence_mark = QHBoxLayout()
        row_silence_mark.addWidget(QLabel("Detect and mark silence"))
        row_silence_mark.addStretch()
        self.tgl_silence_mark = ToggleSwitch()
        row_silence_mark.addWidget(self.tgl_silence_mark)
        l_silence.addLayout(row_silence_mark)
        
        l_silence.addStretch(1)
        self.activities["silence"] = _wrap_activity(p_silence)
        
        self.tgl_silence_cut.toggled.connect(lambda checked: self.tgl_silence_mark.setChecked(False) if checked else None)
        self.tgl_silence_mark.toggled.connect(lambda checked: self.tgl_silence_cut.setChecked(False) if checked else None)

        # C. fillers
        p_fillers = QWidget()
        l_fillers = QVBoxLayout(p_fillers)
        l_fillers.setContentsMargins(15, 15, 15, 15)
        l_fillers.setSpacing(10)
        
        l_fillers.addWidget(QLabel("Filler Words (comma separated):"))
        self.text_fillers = QTextEdit()
        self.text_fillers.setFixedHeight(80)
        l_fillers.addWidget(self.text_fillers)
        
        self.btn_save_fillers = QPushButton("Save")
        self.btn_save_fillers.setCursor(Qt.CursorShape.PointingHandCursor)
        l_fillers.addWidget(self.btn_save_fillers)
        
        row_auto_filler = QHBoxLayout()
        row_auto_filler.addWidget(QLabel("Mark filler words automatically"))
        row_auto_filler.addStretch()
        self.tgl_auto_filler = ToggleSwitch()
        self.tgl_auto_filler.setChecked(True)
        row_auto_filler.addWidget(self.tgl_auto_filler)
        l_fillers.addLayout(row_auto_filler)
        
        l_fillers.addStretch(1)
        self.activities["fillers"] = _wrap_activity(p_fillers)

        # D. main_panel
        p_main = QWidget()
        l_main = QVBoxLayout(p_main)
        l_main.setContentsMargins(15, 15, 15, 15)
        l_main.setSpacing(10)
        
        # Top Section (Markers)
        row_marking_title = QHBoxLayout()
        row_marking_title.addWidget(QLabel("Marking Mode:"))
        row_marking_title.addStretch()
        self.btn_clear_transcript = QPushButton("🧹")
        self.btn_clear_transcript.setFixedSize(26, 26)
        self.btn_clear_transcript.setToolTip("") # Force remove native tooltip
        self.btn_clear_transcript.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_transcript.setStyleSheet("background: transparent; border: none; font-size: 14px; padding: 2px;")
        row_marking_title.addWidget(self.btn_clear_transcript)
        l_main.addLayout(row_marking_title)
        
        self.rb_red = QRadioButton("RED (Cut/Filler)")
        self.rb_red.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_red, config.WORD_BAD_BG)
        l_main.addWidget(self.rb_red)
        
        self.rb_blue = QRadioButton("BLUE (Retake)")
        self.rb_blue.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_blue, config.WORD_REPEAT_BG)
        l_main.addWidget(self.rb_blue)
        
        self.rb_green = QRadioButton("GREEN (Typo)")
        self.rb_green.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_green, config.WORD_TYPO_BG)
        l_main.addWidget(self.rb_green)
        
        self.rb_eraser = QRadioButton("ERASER (Clear)")
        self.rb_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_eraser, "#ffffff")
        l_main.addWidget(self.rb_eraser)
        
        lbl_dummy = QLabel("+ add custom marker...")
        lbl_dummy.setStyleSheet("color: #808080; font-size: 9px; text-decoration: underline;")
        l_main.addWidget(lbl_dummy)
        
        # Middle
        l_main.addStretch(1)
        
        # Bottom Section
        self.lbl_progress = QLabel("Ready.")
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        self.lbl_progress.setStyleSheet("font-size: 9px;")
        l_main.addWidget(self.lbl_progress)
        
        from PySide6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {config.PROGRESS_FILL_COLOR}; }}")
        l_main.addWidget(self.progress_bar)
        
        row_proj = QHBoxLayout()
        self.btn_import_proj = QPushButton("Import Project")
        self.btn_import_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_proj = QPushButton("Export Project")
        self.btn_export_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        row_proj.addWidget(self.btn_import_proj)
        row_proj.addWidget(self.btn_export_proj)
        l_main.addLayout(row_proj)
        
        self.btn_assemble = QPushButton("ASSEMBLE")
        self.btn_assemble.setFixedHeight(35)
        self.btn_assemble.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_assemble.setStyleSheet("QPushButton { background-color: #11703c; color: white; font-weight: bold; border-radius: 4px; border: 1px solid #0a4d28; } QPushButton:hover { background-color: #168f4d; } QPushButton:pressed { background-color: #0d5c31; }")
        l_main.addWidget(self.btn_assemble)
        
        self.activities["main_panel"] = _wrap_activity(p_main)
        
        # E. assembly
        p_assembly = QWidget()
        l_assembly = QVBoxLayout(p_assembly)
        l_assembly.setContentsMargins(15, 15, 15, 15)
        l_assembly.setSpacing(15)
        
        row_show_inaudible = QHBoxLayout()
        row_show_inaudible.addWidget(QLabel("Show inaudible fragments"))
        row_show_inaudible.addStretch()
        self.tgl_show_inaudible = ToggleSwitch()
        self.tgl_show_inaudible.setChecked(True)
        row_show_inaudible.addWidget(self.tgl_show_inaudible)
        l_assembly.addLayout(row_show_inaudible)
        
        row_mark_inaudible = QHBoxLayout()
        row_mark_inaudible.addWidget(QLabel("Mark inaudible fragments with brown"))
        row_mark_inaudible.addStretch()
        self.tgl_mark_inaudible = ToggleSwitch()
        row_mark_inaudible.addWidget(self.tgl_mark_inaudible)
        l_assembly.addLayout(row_mark_inaudible)
        
        row_show_typos = QHBoxLayout()
        row_show_typos.addWidget(QLabel("Show detected typos"))
        row_show_typos.addStretch()
        self.tgl_show_typos = ToggleSwitch()
        self.tgl_show_typos.setChecked(True)
        row_show_typos.addWidget(self.tgl_show_typos)
        l_assembly.addLayout(row_show_typos)
        
        l_assembly.addStretch(1)
        self.activities["assembly"] = _wrap_activity(p_assembly)
        
        self.btn_analyze_standalone.installEventFilter(self)
        self.btn_clear_transcript.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            if watched == getattr(self, 'btn_analyze_standalone', None):
                self.shared_tooltip.show_at(watched, self.txt("tooltip_dev"), is_right_side=False)
            elif watched == getattr(self, 'btn_clear_transcript', None):
                # CRITICAL: is_right_side=True forces it to render to the left of the button!
                self.shared_tooltip.show_at(watched, "Clear all markings", is_right_side=True)
        elif event.type() == QEvent.Type.Leave:
            if watched in (getattr(self, 'btn_analyze_standalone', None), getattr(self, 'btn_clear_transcript', None)):
                self.shared_tooltip.hide()
                
        return super().eventFilter(watched, event)


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
            QPushButton#btn_primary:pressed {{ background-color: #176e38; }}
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

    def _on_start_analysis(self):
        print("[BadWordsGUI] Start Analysis triggered (Stage 4 TODO)")
        # Auto-open panels if they aren't already open
        if hasattr(self, 'btn_nav_script') and not getattr(self.btn_nav_script, 'is_active', False):
            self._toggle_activity("script_analysis")
        if hasattr(self, 'btn_nav_main') and not getattr(self.btn_nav_main, 'is_active', False):
            self._toggle_activity("main_panel")
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