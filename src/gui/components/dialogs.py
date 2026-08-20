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
from .mixins import FramelessWindowMixin, _BaseDialog, _HAS_QFRAMELESS
from .titlebar import CustomTitleBar
from ..utils import _app_icon, _txt, _center_on_screen, apply_dark_title_bar, _qwidget_txt
from ..widgets.delegates import MarqueeItemDelegate

from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtCore import QModelIndex

# ==========================================
# CLASS 1: SPLASH SCREEN
# ==========================================

class SplashScreen(FramelessWindowMixin, _BaseDialog):
    """
    Frameless, dark loading window displayed while engine/api are initializing.
    Shows an animated "loading…" label (0-3 cycling dots at 400 ms).
    Closed by main.py once InitThread emits `loaded`.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        W, H = 300, 150
        self.setFixedSize(W + 30, H + 30)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        self.inner_frame = QFrame()
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        layout = QVBoxLayout(self.inner_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        content_layout = QVBoxLayout()
        layout.addLayout(content_layout)

        # --- QSS styling ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
            }}
            QLabel#title {{
                color: #ffffff;
                font-size: 18pt;
                font-weight: bold;
                font-family: {config.UI_FONT_NAME};
                background: transparent;
            }}
            QLabel#loading {{
                color: {config.NOTE_COL};
                font-size: 12pt;
                font-family: {config.UI_FONT_NAME};
                background: transparent;
            }}
        """)

        # --- Layout ---
        content_layout.setContentsMargins(20, 30, 20, 20)
        content_layout.setSpacing(8)
        content_layout.setAlignment(Qt.AlignCenter)

        lbl_title = QLabel("BadWords", self.inner_frame)
        lbl_title.setObjectName("title")
        lbl_title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(lbl_title)

        self._lbl_loading = QLabel(self.txt("lbl_loading"), self.inner_frame)
        self._lbl_loading.setObjectName("loading")
        self._lbl_loading.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(self._lbl_loading)

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

    def set_status(self, text: str):
        """Display a custom status text (stops the dot animation)."""
        self._timer.stop()
        self._lbl_loading.setText(text)
        QApplication.processEvents()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


# ==========================================
# CLASS 2: TELEMETRY POPUP
# ==========================================



class TelemetryPopup(FramelessWindowMixin, _BaseDialog):
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
        self.frameless_init(is_popup=True)
        # WindowModal blocks only the parent — avoids ApplicationModal event-queue
        # pileup where pending main-window signals fire all at once after exec() returns.
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowIcon(_app_icon())

        # --- Root QSS (window is transparent; styling lives on inner_frame) ---
        self.setStyleSheet(f"""
            QDialog, TelemetryPopup {{ background-color: transparent; }}
            QFrame#MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #000000;
                border-radius: 8px;
            }}
            QLabel#lbl_title {{
                color: #ffffff;
                font-size: 14pt;
                font-weight: bold;
                font-family: {config.UI_FONT_NAME};
                background: transparent;
            }}
            QLabel#lbl_msg {{
                color: {config.FG_COLOR};
                font-size: 11pt;
                font-family: {config.UI_FONT_NAME};
                background: transparent;
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: {config.UI_FONT_NAME};
                font-size: 11pt;
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
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
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
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
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
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 14px;
        """)

        # --- Outer wrapper ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Custom title bar ---
        self._tb = CustomTitleBar(self, self._lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(self._t("title_telemetry"))
        root_layout.addWidget(self._tb)

        # --- Content area ---
        container = QWidget(self.inner_frame)
        container.setObjectName("container")
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(20, 15, 20, 20)
        content_layout.setSpacing(0)
        root_layout.addWidget(container)

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

        content_layout.addLayout(header)
        content_layout.addSpacing(15)

        # Message label
        self._lbl_msg = QLabel("", container)
        self._lbl_msg.setObjectName("lbl_msg")
        self._lbl_msg.setWordWrap(True)
        self._lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(self._lbl_msg)
        content_layout.addSpacing(10)

        # Geo Toggle
        geo_layout = QHBoxLayout()
        geo_layout.setContentsMargins(0, 0, 0, 0)
        
        self._chk_geo = ToggleSwitch(container)
        self._chk_geo.setChecked(True, animated=False)
        
        self._lbl_geo = QLabel("", container)
        self._lbl_geo.setStyleSheet(f"color: {config.FG_COLOR}; font-family: {config.UI_FONT_NAME}; font-size: 11pt; background: transparent;")
        
        geo_layout.addWidget(self._chk_geo)
        geo_layout.addSpacing(10)
        geo_layout.addWidget(self._lbl_geo)
        geo_layout.addStretch()
        content_layout.addLayout(geo_layout)
        content_layout.addSpacing(20)

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

        content_layout.addLayout(btn_row)

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
        self._lbl_geo.setText(self._t("chk_telemetry_geo"))
        # Keep title bar in sync when language changes
        if hasattr(self, '_tb') and hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(self._t("title_telemetry"))

        # ── Size calculation ──────────────────────────────────────────────
        # The dialog uses a shadow outer wrapper (15px each side) and a content
        # area with 20px horizontal padding each side. Total horizontal overhead:
        # 15 + 15 + 20 + 20 = 70px.  We must tell the word-wrapped label its
        # exact available width BEFORE calling adjustSize(), otherwise Qt
        # computes height without accounting for wrapping and the bottom text
        # gets clipped.
        DIALOG_W      = 580
        HORIZ_MARGINS = 15 + 15 + 20 + 20   # shadow margins + content margins
        self._lbl_msg.setMaximumWidth(DIALOG_W - HORIZ_MARGINS)

        # Now constrain the dialog width and let height grow freely
        self.setFixedWidth(DIALOG_W)
        self.adjustSize()    # height is now computed correctly with wrapped text
        h = max(self.sizeHint().height(), self.height())
        _center_on_screen(self, DIALOG_W, h)


    def _show_lang_picker(self):
        """Open a floating language picker anchored below the lang button."""
        try:
            if self._lang_picker and self._lang_picker.isVisible():
                self._lang_picker.close()
                return
        except RuntimeError:
            self._lang_picker = None # Object was deleted by Qt

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
        self._engine.os_doc.set_telemetry_pref("telemetry_allow_geo", False)
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


class GlobalAppFilter(QObject):
    """Intercepts native QEvent.ToolTip globally and handles global input focus management."""
    def __init__(self, shared_tooltip):
        super().__init__()
        self.shared_tooltip = shared_tooltip
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._do_show)
        self.current_text = ""
        self.current_pos = None
        self.active_widget = None

    def eventFilter(self, obj, event):
        try:
            etype = event.type()
            # 1. Global Focus Management: clear focus from QLineEdit on click anywhere outside
            if etype == QEvent.Type.MouseButtonPress:
                focused = QApplication.focusWidget()
                if isinstance(focused, QLineEdit):
                    global_pos = QCursor.pos()
                    focused_global_rect = QRect(focused.mapToGlobal(QPoint(0, 0)), focused.size())
                    if not focused_global_rect.contains(global_pos):
                        focused.clearFocus()

            # 2. Enter/Return removes focus from QLineEdit
            if etype == QEvent.Type.KeyPress and isinstance(obj, QLineEdit) and obj.hasFocus():
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    obj.clearFocus()

            # 3. Tooltip handling via Enter/Leave for better reliability
            if etype == QEvent.Type.Enter:
                if isinstance(obj, QWidget):
                    text = obj.toolTip()
                    if text:
                        self.current_text = text
                        self.current_pos = QCursor.pos()
                        # Start timer on Enter
                        self.active_widget = obj
                        self.tooltip_timer.start(750)  # 750ms hover to show
            elif etype == QEvent.Type.MouseMove and self.active_widget == obj:
                # Update position as they move the mouse
                self.current_pos = QCursor.pos()
            elif etype in (QEvent.Type.Leave, QEvent.Type.Hide,
                           QEvent.Type.MouseButtonPress, QEvent.Type.WindowDeactivate):
                if obj == self.active_widget or self.active_widget is None:
                    self.tooltip_timer.stop()
                    if hasattr(self, 'shared_tooltip'):
                        self.shared_tooltip.hide()
                    self.active_widget = None
                    self.current_text = ""
            elif etype == QEvent.Type.ToolTip and self.active_widget == obj:
                # Suppress the native ToolTip event
                return True
        except RuntimeError:
            pass
        return False



    def _do_show(self):
        if self.current_text and self.active_widget:
            self.shared_tooltip.show_global(self.current_text, self.current_pos)



class SidebarDragZone(QFrame):
    """
    A drop-zone container for SidebarButtons
    """
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(6)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText():
            return
            
        layout = self.layout()
        source_btn = event.source()
        
        target_idx = layout.count()
        last_vis_widget = None
        drop_y = 0
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_btn:
                continue
            
            last_vis_widget = w
            
            # Hit-test: if mouse is above the vertical center of this widget, insert BEFORE it.
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            # If the loop completes without breaking, we are dropping at the VERY BOTTOM.
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
            else:
                layout_margins = self.layout().contentsMargins()
                drop_y = layout_margins.top() if layout_margins else 0
                
        self._drop_line_y = drop_y
        self.update()
            
        event.accept()

    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        
        activity_id = event.mimeData().text()
        source_btn = event.source()
        if isinstance(source_btn, SidebarButton) and source_btn.activity_id == activity_id:
            layout = self.layout()
            
            target_idx = layout.count()
            last_vis_widget = None
            drop_y = 0
            
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if not w or w.isHidden() or w == source_btn:
                    continue
                
                last_vis_widget = w
                
                # Hit-test: if mouse is above the vertical center of this widget, insert BEFORE it.
                if event.position().y() < w.geometry().center().y():
                    target_idx = i
                    drop_y = w.geometry().top()
                    break
            else:
                # If the loop completes without breaking, we are dropping at the VERY BOTTOM.
                if last_vis_widget:
                    drop_y = last_vis_widget.geometry().bottom()
                else:
                    layout_margins = self.layout().contentsMargins()
                    drop_y = layout_margins.top() if layout_margins else 0
                        
            layout.insertWidget(target_idx, source_btn)
            event.acceptProposedAction()
            
            main_window = self.window()
            is_right = (hasattr(main_window, "_sidebar_right") and self == main_window._drag_zone_right)
            source_btn.is_right_side = is_right
            source_btn.set_active(False)
            
            self._drop_line_y = -1
            self.update()

            main_window = self.window()
            if hasattr(main_window, '_save_sidebar_layout'):
                main_window._save_sidebar_layout()

            if getattr(source_btn, '_drag_was_active', False):
                source_btn.window()._toggle_activity(source_btn.activity_id)
                source_btn._drag_was_active = False


class MarkerDragZone(QFrame):
    """
    A drop-zone container for Custom Markers in the settings panel.
    """
    def __init__(self, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._drop_line_y = -1
        self.setLayout(QVBoxLayout())
        self.layout().setAlignment(Qt.AlignTop)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_line_y >= 0:
            p = QPainter(self)
            p.setPen(QPen(QColor("#11703c"), 3))
            p.drawLine(0, self._drop_line_y, self.width(), self._drop_line_y)
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text() == "m_drag":
            event.acceptProposedAction()
            
    def dragMoveEvent(self, event):
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        layout = self.layout()
        source_widget = event.source()
        
        target_idx = layout.count() - 1 
        drop_y = 0
        last_vis_widget = None
        
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            
            if w.objectName() == "stretch_placeholder":
                continue
                
            last_vis_widget = w
            
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                drop_y = w.geometry().top()
                break
        else:
            if last_vis_widget:
                drop_y = last_vis_widget.geometry().bottom()
                
        if drop_y != self._drop_line_y:
            self._drop_line_y = drop_y
            self.update()
            
        event.acceptProposedAction()
        
    def dragLeaveEvent(self, event):
        self._drop_line_y = -1
        self.update()

    def dropEvent(self, event):
        self._drop_line_y = -1
        self.update()
        
        if not event.mimeData().hasText() or event.mimeData().text() != "m_drag":
            return
            
        source_widget = event.source()
        layout = self.layout()
        
        target_idx = layout.count() - 1
        for i in range(layout.count()):
            w = layout.itemAt(i).widget()
            if not w or w.isHidden() or w == source_widget:
                continue
            if w.objectName() == "stretch_placeholder":
                continue
            if event.position().y() < w.geometry().center().y():
                target_idx = i
                break
                
        if hasattr(self.window(), "_on_markers_reordered"):
            self.window()._on_markers_reordered(source_widget.original_idx, target_idx)
            
        event.acceptProposedAction()


class MarkerRowWidget(QWidget):
    """
    Draggable marker row.
    """
    def __init__(self, marker_data, original_idx, parent=None):
        super().__init__(parent)
        self.marker_data = marker_data
        self.original_idx = original_idx
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not self.drag_start_pos:
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        from PySide6.QtGui import QDrag
        from PySide6.QtCore import QMimeData
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText("m_drag")
        drag.setMimeData(mime)
        
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.MoveAction)







class AnimatedDimOverlay(QWidget):
    def __init__(self, parent_gui, opacity_target=0.55, duration=200):
        parent = getattr(parent_gui, 'centralWidget', lambda: None)() or parent_gui
        super().__init__(parent)
        self.opacity_target = opacity_target
        self.current_alpha = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        from PySide6.QtCore import QVariantAnimation, QEasingCurve
        self.anim_in = QVariantAnimation(self)
        self.anim_in.setDuration(duration)
        self.anim_in.setStartValue(0)
        self.anim_in.setEndValue(int(255 * opacity_target))
        self.anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_in.valueChanged.connect(self._on_alpha_changed)

    def _on_alpha_changed(self, val):
        self.current_alpha = val
        self.update()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.current_alpha))

    def fade_in(self):
        p = self.parentWidget()
        if p:
            self.setGeometry(0, 0, p.width(), p.height())
        self.show()
        self.raise_()
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        self.anim_in.start()

    def fade_out(self):
        from PySide6.QtCore import QVariantAnimation, QEasingCurve
        self.anim_out = QVariantAnimation(self)
        self.anim_out.setDuration(160)
        self.anim_out.setStartValue(self.current_alpha)
        self.anim_out.setEndValue(0)
        self.anim_out.setEasingCurve(QEasingCurve.InCubic)
        self.anim_out.valueChanged.connect(self._on_alpha_changed)
        self.anim_out.finished.connect(self.deleteLater)
        self.anim_out.start()


class CustomMsgBox(FramelessWindowMixin, _BaseDialog):
    def __init__(self, parent, title: str, message: str, btn_yes_text: str, btn_no_text: str = None, btn_cancel_text: str = None):
        super().__init__(parent)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; }}
            QLabel {{ color: {config.FG_COLOR}; }}
            QLabel#lbl_title {{ font-size: 14pt; font-weight: bold; }}
            QLabel#lbl_msg {{ font-size: 11pt; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_yes {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_yes:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tb = CustomTitleBar(self, "en", parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(15)
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("lbl_msg")
        lbl_msg.setWordWrap(True)
        lbl_msg.setFixedWidth(380)
        lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        content_layout.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if btn_cancel_text:
            btn_cancel = QPushButton(btn_cancel_text)
            btn_cancel.clicked.connect(lambda: self.done(2))
            btn_layout.addWidget(btn_cancel)
            btn_layout.addSpacing(10)
            
        if btn_no_text:
            btn_no = QPushButton(btn_no_text)
            btn_no.clicked.connect(self.reject)
            btn_layout.addWidget(btn_no)
            btn_layout.addSpacing(10)
            
        btn_yes = QPushButton(btn_yes_text)
        btn_yes.setObjectName("btn_yes")
        btn_yes.clicked.connect(self.accept)
        btn_layout.addWidget(btn_yes)
        
        content_layout.addLayout(btn_layout)
        
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())


# ---------------------------------------------------------------------------
# AUTO-UPDATE: background thread + notification dialog
# ---------------------------------------------------------------------------

class UpdateCheckThread(QThread):
    """
    Stdlib-only background worker that checks GitHub (with GitLab fallback)
    for a newer release of BadWords.

    Signals
    -------
    update_available(str, str, str)
        Emitted when a newer version is detected.
        Args: (latest_version, github_release_url, gitlab_release_url)

    Class-level cache
    -----------------
    _cached_result is set after the first successful check so that subsequent
    thread starts (e.g. every time the settings dialog opens) do NOT fire new
    HTTP requests and cannot hit the GitHub rate limit.
    """
    update_available = Signal(str, str, str)

    # GitHub unauthenticated limit = 60 req/h — cache result for the session
    _cached_result: tuple | None = None   # (latest_display, gh_page, gl_page) | None
    _checked: bool = False                # True once a check completed (even if up-to-date)
    _lock = None                          # threading.Lock — lazy init (import at use time)


    # ── API endpoints ─────────────────────────────────────────────────────
    _GH_API  = "https://api.github.com/repos/veritus-git/BadWords/releases/latest"
    # GitLab project: badwords/BadWords (ID 78101072)
    # /releases returns a JSON list sorted newest-first; we take [0].tag_name
    _GL_API  = "https://gitlab.com/api/v4/projects/78101072/releases"
    _GH_PAGE = "https://github.com/veritus-git/BadWords/releases/latest"
    _GL_PAGE = "https://gitlab.com/badwords/BadWords/-/releases"

    # ── Update script URLs ────────────────────────────────────────────────
    _UPDATE_SCRIPT_LINUX    = 'https://raw.githubusercontent.com/veritus-git/BadWords/main/updaters/update-linux.sh'
    _UPDATE_SCRIPT_MAC      = 'https://raw.githubusercontent.com/veritus-git/BadWords/main/updaters/update-mac.sh'
    _UPDATE_SCRIPT_WIN      = 'https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/legacy/update-windows.bat'
    _UPDATE_SCRIPT_LINUX_GL = 'https://gitlab.com/badwords/BadWords/-/raw/main/updaters/update-linux.sh'
    _UPDATE_SCRIPT_MAC_GL   = 'https://gitlab.com/badwords/BadWords/-/raw/main/updaters/update-mac.sh'
    _UPDATE_SCRIPT_WIN_GL   = 'https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/legacy/update-windows.bat'

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self._current = current_version

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_version(tag: str):
        """Convert '3.0', 'v2.0.3', '2.0.3' → tuple of ints for comparison."""
        tag = tag.strip().lstrip('v').lstrip('V')
        try:
            return tuple(int(x) for x in tag.split('.'))
        except ValueError:
            return (0,)

    @staticmethod
    def _fetch_json(url: str, timeout: int = 8):
        import urllib.request, json, ssl
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        req = urllib.request.Request(url, headers={"User-Agent": "BadWords-UpdateCheck/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode('utf-8'))

    # ------------------------------------------------------------------
    # main
    # ------------------------------------------------------------------

    def run(self):
        import threading
        from osdoc import log_info, log_error

        # Lazy init of class-level lock (safe: done under GIL before threads diverge)
        if UpdateCheckThread._lock is None:
            UpdateCheckThread._lock = threading.Lock()

        current_tuple = self._parse_version(self._current)

        # ── Replay cached result if already checked this session ──────────
        # Quick path without the lock — avoids blocking when _checked is set
        if UpdateCheckThread._checked:
            cached = UpdateCheckThread._cached_result
            if cached:
                latest_display, gh_page, gl_page = cached
                if self._parse_version(latest_display) > current_tuple:
                    log_info(f"[UpdateCheck] (cached) New version available: {latest_display}")
                    self.update_available.emit(latest_display, gh_page, gl_page)
                else:
                    log_info(f"[UpdateCheck] (cached) Already up-to-date ({self._current}).")
            else:
                log_info("[UpdateCheck] (cached) No version info available.")
            return

        # ── First check — hold lock so only ONE thread does the HTTP work ─
        with UpdateCheckThread._lock:
            # Re-check inside lock (another thread may have finished while we waited)
            if UpdateCheckThread._checked:
                cached = UpdateCheckThread._cached_result
                if cached:
                    latest_display, gh_page, gl_page = cached
                    if self._parse_version(latest_display) > current_tuple:
                        log_info(f"[UpdateCheck] (cached/lock) New version available: {latest_display}")
                        self.update_available.emit(latest_display, gh_page, gl_page)
                    else:
                        log_info(f"[UpdateCheck] (cached/lock) Already up-to-date ({self._current}).")
                return

            latest_tag = None

            # 1. Try GitHub
            try:
                data = self._fetch_json(self._GH_API)
                latest_tag = data.get("tag_name", "").strip()
                log_info(f"[UpdateCheck] GitHub latest tag: {latest_tag!r}")
            except Exception as e:
                log_error(f"[UpdateCheck] GitHub API failed: {e}")

            # 2. Fallback: GitLab — /releases returns a JSON list; take first entry
            if not latest_tag:
                try:
                    data = self._fetch_json(self._GL_API)
                    if isinstance(data, list) and data:
                        latest_tag = data[0].get("tag_name", "").strip()
                    elif isinstance(data, dict):
                        latest_tag = data.get("tag_name", "").strip()
                    if latest_tag:
                        log_info(f"[UpdateCheck] GitLab latest tag: {latest_tag!r}")
                except Exception as e:
                    log_error(f"[UpdateCheck] GitLab API failed: {e}")

            # Mark as checked (even on failure) — prevents hammering APIs
            UpdateCheckThread._checked = True

            if not latest_tag:
                log_error("[UpdateCheck] Could not retrieve latest version from any source.")
                UpdateCheckThread._cached_result = None
                return

            latest_tuple   = self._parse_version(latest_tag)
            latest_display = latest_tag.lstrip('vV')

            if latest_tuple > current_tuple:
                log_info(f"[UpdateCheck] New version available: {latest_display} (current: {self._current})")
                UpdateCheckThread._cached_result = (latest_display, self._GH_PAGE, self._GL_PAGE)
                self.update_available.emit(latest_display, self._GH_PAGE, self._GL_PAGE)
            else:
                log_info(f"[UpdateCheck] Already up-to-date ({self._current}).")
                UpdateCheckThread._cached_result = None




class UpdateNotifyDialog(FramelessWindowMixin, _BaseDialog):
    """
    Custom frameless update-notification dialog.

    Windows  → 'Download from GitHub' button (opens browser).
    macOS    → 'Update Now' runs the macOS setup script silently in background.
    Linux    → 'Update Now' runs the Linux setup script silently in background.

    Layout: clean version badge (current → latest), no terminal command shown.
    """

    # URLs for the dedicated cross-platform python update script
    _UPDATE_SCRIPT    = 'https://raw.githubusercontent.com/veritus-git/BadWords/main/setupfiles/updater.py'
    _UPDATE_SCRIPT_GL = 'https://gitlab.com/badwords/BadWords/-/raw/main/setupfiles/updater.py'

    # Class-level signal so Qt registers it properly
    _update_done = Signal(bool, str)   # (success, error_message)

    def __init__(self, parent, lang: str, current_ver: str, latest_ver: str,
                 gh_url: str, gl_url: str, is_win: bool, is_mac: bool,
                 install_dir: str):
        super().__init__(parent)
        self._lang    = lang
        self._engine  = getattr(parent, 'engine', None)
        self._is_mac  = is_mac
        self._is_win  = is_win
        self._gh_url  = gh_url
        self._install_dir = install_dir

        # Wire update result back to GUI thread
        self._update_done.connect(self._on_update_done)

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #111;
                border-radius: 8px;
            }}
            QLabel {{ color: {config.FG_COLOR}; background: transparent; }}
            QLabel#lbl_title  {{ font-size: 15pt; font-weight: bold; }}
            QLabel#lbl_sub    {{ font-size: 10pt; color: #999; }}
            QLabel#lbl_status {{ font-size: 10pt; color: #888; font-style: italic; }}
            #ver_frame {{
                background-color: #101010;
                border: 1px solid #1e1e1e;
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 7px 20px;
                border-radius: 5px;
                min-width: 90px;
                font-weight: bold;
                font-size: 10pt;
            }}
            QPushButton:hover    {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton:disabled {{ color: #444; background-color: #181818; }}
            QPushButton#btn_primary           {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_primary:hover     {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_primary:disabled  {{ background-color: #1a2e1a; color: #3a5a3a; }}
        """)

        # ── Outer layout with drop shadow ──────────────────────────────────
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        outer.addWidget(self.inner_frame)

        # ── Inner structure ────────────────────────────────────────────────
        root = QVBoxLayout(self.inner_frame)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root.addWidget(self._tb)

        body = QVBoxLayout()
        body.setContentsMargins(28, 20, 28, 24)
        body.setSpacing(12)
        root.addLayout(body)

        # ── Headline ───────────────────────────────────────────────────────
        lbl_title = QLabel(_txt(lang, 'update_notify_title'))
        lbl_title.setObjectName("lbl_title")
        body.addWidget(lbl_title)

        lbl_sub = QLabel(_txt(lang, 'update_notify_sub'))
        lbl_sub.setObjectName("lbl_sub")
        body.addWidget(lbl_sub)

        body.addSpacing(6)

        # ── Version comparison card ────────────────────────────────────────
        ver_frame = QFrame()
        ver_frame.setObjectName("ver_frame")
        ver_layout = QHBoxLayout(ver_frame)
        ver_layout.setContentsMargins(24, 16, 24, 16)
        ver_layout.setSpacing(0)

        def _ver_col(label_txt, ver_txt, ver_color):
            col = QVBoxLayout()
            col.setSpacing(3)
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color: #555; font-size: 9pt; letter-spacing: 1px;")
            val = QLabel(ver_txt)
            val.setStyleSheet(f"color: {ver_color}; font-size: 20pt; font-weight: bold;")
            col.addWidget(lbl)
            col.addWidget(val)
            return col

        body.addWidget(ver_frame)
        ver_layout.addLayout(_ver_col(
            _txt(lang, 'update_notify_lbl_current'), current_ver, "#555"
        ))

        lbl_arrow = QLabel("→")
        lbl_arrow.setStyleSheet("color: #333; font-size: 24pt; padding: 0 24px 0 20px;")
        lbl_arrow.setAlignment(Qt.AlignCenter)
        ver_layout.addWidget(lbl_arrow)

        ver_layout.addLayout(_ver_col(
            _txt(lang, 'update_notify_lbl_latest'), latest_ver, "#39ff7a"
        ))
        ver_layout.addStretch()

        # ── Status label (shown during / after update) ─────────────────────
        self._lbl_status = QLabel("")
        self._lbl_status.setObjectName("lbl_status")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.hide()
        body.addWidget(self._lbl_status)

        body.addSpacing(4)

        # ── Button row ─────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._btn_dismiss = QPushButton(_txt(lang, 'update_notify_btn_dismiss'))
        self._btn_dismiss.setCursor(Qt.PointingHandCursor)
        self._btn_dismiss.clicked.connect(self._on_dismiss)
        btn_row.addWidget(self._btn_dismiss)

        btn_row.addSpacing(8)

        self._btn_primary = QPushButton(_txt(lang, 'update_notify_btn_update'))
        self._btn_primary.setObjectName("btn_primary")
        self._btn_primary.setCursor(Qt.PointingHandCursor)
        self._btn_primary.clicked.connect(self._on_update_now)

        btn_row.addWidget(self._btn_primary)
        body.addLayout(btn_row)

        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    # ------------------------------------------------------------------
    # Update logic
    # ------------------------------------------------------------------

    def _on_update_now(self):
        """
        Download the dedicated non-interactive update script from the repo and
        run it with bash in a daemon thread.  The script (update-linux.sh /
        update-mac.sh) handles GitHub→GitLab fallback, file sync, and pip
        upgrades entirely on its own — no interactive prompts.
        """
        import threading, subprocess, tempfile, os

        self._btn_primary.setEnabled(False)
        self._btn_primary.setText(_txt(self._lang, 'update_notify_updating'))
        self._btn_dismiss.setEnabled(False)
        self._lbl_status.setText(_txt(self._lang, 'update_notify_wait'))
        self._lbl_status.setStyleSheet("color: #888; font-style: italic; font-size: 10pt;")
        self._lbl_status.show()
        self.adjustSize()

        url_primary  = self._UPDATE_SCRIPT
        url_fallback = self._UPDATE_SCRIPT_GL

        def _worker():
            tmp_script = None
            try:
                import urllib.request, ssl, sys, os
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())

                # Try primary (GitHub raw), then GitLab fallback
                script_content = None
                for url in (url_primary, url_fallback):
                    try:
                        with urllib.request.urlopen(url, timeout=20, context=ctx) as resp:
                            script_content = resp.read()
                        break
                    except Exception:
                        continue

                if not script_content:
                    self._update_done.emit(False, "Could not download update script from GitHub or GitLab.")
                    return

                # Write to a temp file and execute
                fd, tmp_script = tempfile.mkstemp(suffix='.py', prefix='bw_update_')
                with os.fdopen(fd, 'wb') as f:
                    f.write(script_content)

                cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0

                if self._is_win:
                    venv_py = os.path.join(self._install_dir, 'venv', 'Scripts', 'python.exe')
                else:
                    venv_py = os.path.join(self._install_dir, 'venv', 'bin', 'python3')

                # Fallback just in case
                if not os.path.isfile(venv_py):
                    venv_py = sys.executable

                result = subprocess.run(
                    [venv_py, tmp_script, '--install-dir', self._install_dir],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    encoding='utf-8', errors='replace',
                    timeout=600,
                    creationflags=cf,
                )

                # Log full output for diagnostics
                from osdoc import log_info, log_error
                for line in (result.stdout or '').splitlines():
                    log_info(f'[Updater] {line}')

                if result.returncode == 0:
                    self._update_done.emit(True, "")
                else:
                    self._update_done.emit(False, f"Exit code {result.returncode}")

            except subprocess.TimeoutExpired:
                self._update_done.emit(False, "Timeout (>10 min) — update may still be running.")
            except Exception as e:
                self._update_done.emit(False, str(e))
            finally:
                if tmp_script and os.path.exists(tmp_script):
                    try: os.remove(tmp_script)
                    except Exception: pass

        threading.Thread(target=_worker, daemon=True).start()

    def _on_update_done(self, success: bool, error_msg: str):
        """Called on the main thread when the background update finishes."""
        from osdoc import log_info, log_error
        if success:
            log_info("[UpdateCheck] Auto-update completed successfully.")
            self._lbl_status.setText(_txt(self._lang, 'update_notify_success'))
            self._lbl_status.setStyleSheet("color: #39ff7a; font-size: 10pt; font-style: normal;")
            self._btn_primary.hide()
            self._btn_dismiss.setText(_txt(self._lang, 'btn_close'))
            self._btn_dismiss.clicked.disconnect()
            self._btn_dismiss.clicked.connect(self.accept)
            self._btn_dismiss.setEnabled(True)
        else:
            log_error(f"[UpdateCheck] Auto-update failed: {error_msg}")
            self._lbl_status.setText(_txt(self._lang, 'update_notify_failed'))
            self._lbl_status.setStyleSheet("color: #ed4245; font-size: 10pt; font-style: normal;")
            # Change primary button to open GitHub releases page
            self._btn_primary.setText(_txt(self._lang, 'update_notify_win_btn'))
            self._btn_primary.clicked.disconnect()
            self._btn_primary.clicked.connect(lambda: self._open_url(self._gh_url))
            self._btn_primary.setEnabled(True)
            self._btn_dismiss.setEnabled(True)
        self.adjustSize()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _on_dismiss(self):
        """Close without modifying auto-check setting."""
        self.reject()

    def closeEvent(self, event):
        """X button = 'Remind me later': just close, keep auto_check_updates enabled."""
        event.accept()  # do NOT touch auto_check_updates

    @staticmethod
    def _open_url(url: str):
        import webbrowser
        webbrowser.open(url)



class MarkerDialog(FramelessWindowMixin, _BaseDialog):

    """
    Custom frameless dialog for adding or editing a custom marker.
    Usage:
        dlg = MarkerDialog(parent, lang, title_key, prefill_name='', prefill_color='Blue')
        if dlg.exec() == QDialog.Accepted:
            name, color = dlg.result_name, dlg.result_color
    """
    def __init__(self, parent, lang: str, title_key: str,
                 prefill_name: str = '', prefill_color: str = ''):
        super().__init__(parent)
        self._lang = lang
        self.result_name = ''
        self.result_color = ''

        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowModality(Qt.ApplicationModal)

        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; border: 1px solid #111; border-radius: 6px; }}
            QLabel {{ color: {config.FG_COLOR}; font-family: {config.UI_FONT_NAME}; }}
            QLabel#lbl_title {{ font-size: 13pt; font-weight: bold; color: #ffffff; }}
            QLineEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 5px 8px;
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
            }}
            QLineEdit:focus {{ border-color: {config.BTN_BG}; }}
            QPushButton {{
                background-color: {config.BTN_GHOST_BG};
                color: {config.BTN_FG};
                padding: 6px 16px;
                border-radius: 4px;
                min-width: 80px;
                font-weight: bold;
                font-family: {config.UI_FONT_NAME};
            }}
            QPushButton:hover {{ background-color: {config.BTN_GHOST_ACTIVE}; }}
            QPushButton#btn_ok {{ background-color: {config.BTN_BG}; }}
            QPushButton#btn_ok:hover {{ background-color: {config.BTN_ACTIVE}; }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.inner_frame.setGraphicsEffect(shadow)
        main_layout.addWidget(self.inner_frame)

        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._tb = CustomTitleBar(self, lang, parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        title_text = _txt(lang, title_key)
        if hasattr(self._tb, '_lbl_title'):
            self._tb._lbl_title.setText(title_text)
        root_layout.addWidget(self._tb)

        content = QWidget(self.inner_frame)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(14)
        root_layout.addWidget(content)

        lbl_title = QLabel(title_text, content)
        lbl_title.setObjectName("lbl_title")
        content_layout.addWidget(lbl_title)

        # Name row
        name_row = QHBoxLayout()
        name_lbl = QLabel(_txt(lang, "lbl_marker_name"), content)
        name_lbl.setFixedWidth(100)
        self._name_edit = QLineEdit(content)
        self._name_edit.setText(prefill_name)
        self._name_edit.setPlaceholderText(_txt(lang, "placeholder_marker_name"))
        name_row.addWidget(name_lbl)
        name_row.addWidget(self._name_edit)
        content_layout.addLayout(name_row)

        # Color row — translated display names with a reverse map to English keys
        color_row = QHBoxLayout()
        color_lbl = QLabel(_txt(lang, "lbl_marker_color"), content)
        color_lbl.setFixedWidth(100)
        _blocked = getattr(config, 'RESOLVE_COLORS_BLOCKED', {"Olive", "Violet", "Chocolate", "Navy", "Tan"})
        # Build [(translated_label, english_key), ...]
        self._color_key_map: dict[str, str] = {}  # translated → english
        translated_options: list[str] = []
        for c in config.RESOLVE_COLORS:
            if c in _blocked:
                continue
            t = _txt(lang, f"resolve_color_{c.lower()}")
            self._color_key_map[t] = c
            translated_options.append(t)
        self._color_combo = CustomDropdown(translated_options)
        # CustomDropdown defaults to self.txt("txt_select") which resolves to English
        # at creation time (no parent window yet). Override with the correct lang immediately.
        if not (prefill_color and prefill_color in config.RESOLVE_COLORS):
            self._color_combo.setText(_txt(lang, "txt_select"))
        # Set prefill value — find its translated equivalent
        if prefill_color and prefill_color in config.RESOLVE_COLORS:
            prefill_t = _txt(lang, f"resolve_color_{prefill_color.lower()}")
            self._color_combo.setText(prefill_t)
        color_row.addWidget(color_lbl)
        color_row.addWidget(self._color_combo)
        content_layout.addLayout(color_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(_txt(lang, "btn_close"), content)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton(_txt(lang, "btn_apply"), content)
        btn_ok.setObjectName("btn_ok")
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addSpacing(8)
        btn_row.addWidget(btn_ok)
        content_layout.addLayout(btn_row)

        self.adjustSize()
        self.setFixedWidth(380)
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())

    def _on_ok(self):
        name = self._name_edit.text().strip()
        translated = self._color_combo.currentText()
        color_key = self._color_key_map.get(translated, "")
        # Both name and a valid color must be provided
        if name and color_key:
            self.result_name = name
            self.result_color = color_key
            self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self._on_ok()
        elif event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)



class UnsavedChangesDialog(FramelessWindowMixin, _BaseDialog):

    def __init__(self, parent, diff_dict, key_name_map):
        super().__init__(parent)
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
        self.setStyleSheet(parent.styleSheet() + f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{ background-color: {config.BG_COLOR}; }}
            QScrollArea {{ border: 1px solid #333; background-color: #1c1c1c; border-radius: 4px; }}
            QFrame#item_row {{ border-bottom: 1px solid #333; padding-bottom: 5px; }}
        """)
        
        self.decisions = {}
        self.diff_dict = diff_dict
        self.rows = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.inner_frame = QFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        root_layout = QVBoxLayout(self.inner_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        self._tb = CustomTitleBar(self, "en", parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        root_layout.addWidget(self._tb)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 25, 20, 20)
        content_layout.setSpacing(15)
        root_layout.addLayout(content_layout)
        
        lbl_title = QLabel(parent.txt('msg_unsaved_title'))
        lbl_title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        content_layout.addWidget(lbl_title)
        content_layout.addWidget(QLabel(parent.txt('msg_unsaved_desc')))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.vbox = QVBoxLayout(scroll_content)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.vbox.setSpacing(10)
        
        for k, (old_v, new_v) in diff_dict.items():
            row = QFrame()
            row.setObjectName("item_row")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            
            fname = key_name_map.get(k, k.replace('_', ' ').title())
            lbl_name = QLabel(f"{fname}:")
            
            if isinstance(new_v, bool):
                display_val = parent.txt('btn_yes') if new_v else parent.txt('btn_no')
            elif isinstance(new_v, list):
                t_list = []
                for item in new_v:
                    t = parent.txt(str(item))
                    t_list.append(t if t != str(item) else str(item).replace('_', ' ').title())
                display_val = ", ".join(t_list) if t_list else "—"
            elif isinstance(new_v, str):
                t = parent.txt(new_v)
                display_val = t if t != new_v else new_v
            else:
                display_val = str(new_v)
                
            lbl_val = QLabel(f"<b>{display_val}</b>")
            lbl_val.setStyleSheet("color: #aaa;")
            
            btn_save = QPushButton(parent.txt('btn_save'))
            btn_save.setObjectName("btn_apply")
            btn_save.setCursor(Qt.PointingHandCursor)
            btn_save.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'save'))
            
            btn_discard = QPushButton(parent.txt('btn_discard'))
            btn_discard.setObjectName("btn_secondary")
            btn_discard.setCursor(Qt.PointingHandCursor)
            btn_discard.clicked.connect(lambda checked=False, key=k: self._make_decision(key, 'discard'))
            
            rl.addWidget(lbl_name)
            rl.addWidget(lbl_val)
            rl.addStretch()
            rl.addWidget(btn_discard)
            rl.addWidget(btn_save)
            
            self.vbox.addWidget(row)
            self.rows[k] = row
        
        self.vbox.addStretch()
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)
        
        bot_layout = QHBoxLayout()
        btn_cancel = QPushButton(parent.txt('btn_cancel'))
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        
        btn_discard_all = QPushButton(parent.txt('btn_discard_all'))
        btn_discard_all.setObjectName("btn_secondary")
        btn_discard_all.setCursor(Qt.PointingHandCursor)
        btn_discard_all.clicked.connect(self._discard_all)
        
        btn_save_all = QPushButton(parent.txt('btn_save_all'))
        btn_save_all.setObjectName("btn_apply")
        btn_save_all.setCursor(Qt.PointingHandCursor)
        btn_save_all.clicked.connect(self._save_all)
        
        bot_layout.addWidget(btn_cancel)
        bot_layout.addStretch()
        bot_layout.addWidget(btn_discard_all)
        bot_layout.addWidget(btn_save_all)
        content_layout.addLayout(bot_layout)
        
        self.resize(630, 480)
        _center_on_screen(self, 630, 480)
        
    def _make_decision(self, key, decision):
        self.decisions[key] = decision
        self.rows[key].hide()
        if len(self.decisions) == len(self.diff_dict):
            self.accept()
            
    def _save_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'save'
        self.accept()
        
    def _discard_all(self):
        for k in self.diff_dict:
            if k not in self.decisions:
                self.decisions[k] = 'discard'
        self.accept()


class SettingsDialog(FramelessWindowMixin, _BaseDialog):
    """Settings Dialog — left category menu + right stacked pages.
    All I/O goes through engine.load_preferences / engine.save_preferences
    which delegate to osdoc's smart router.
    """

    # Fallback defaults (for revert buttons)
    DEFAULTS = {
        'view_mode':          'continuous',
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

    def txt(self, key: str, **kwargs) -> str:
        prefs = self.engine.load_preferences() or {}
        lang = prefs.get("gui_lang", "en")
        text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
        if kwargs: return text.format(**kwargs)
        return text

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle(self.txt("tool_settings"))
        self.frameless_init(is_popup=True)
        self.setWindowFlags(self.windowFlags() | Qt.Tool | Qt.Dialog)
        self.setFixedSize(750, 580)

        prefs = self.engine.load_preferences() or {}

        # ── Global stylesheet ─────────────────────────────────────────────
        self.setStyleSheet(f"""
            QDialog {{ background-color: transparent; }}
            #MainInnerFrame {{
                background-color: {config.BG_COLOR};
                border: 1px solid #1a1a1a;
            }}
            QPushButton {{
                padding: 6px 16px;
                outline: none;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                background: transparent;
            }}
            QListWidget {{
                background-color: {config.SIDEBAR_BG};
                border: none;
                border-right: 1px solid {config.SEPARATOR_COL};
                outline: none;
                padding: 6px 0;
            }}
            QListWidget::item {{
                color: {config.NOTE_COL};
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                padding: 10px 16px;
                border-radius: 0px;
            }}
            QListWidget::item:selected,
            QListWidget::item:selected:active,
            QListWidget::item:selected:!active {{
                background-color: #2a2d2e;
                color: #ffffff;
                border-left: 2px solid {config.BTN_BG};
            }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover:!selected {{
                background-color: #222222;
                color: {config.FG_COLOR};
            }}
            QStackedWidget {{
                background-color: {config.BG_COLOR};
            }}
            QLineEdit, QTextEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
                background-color: {config.INPUT_BG};
                color: {config.INPUT_FG};
                border: 1px solid #3a3a3a;
                padding: 4px 8px;
                border-radius: 3px;
                outline: none;
            }}
            QLineEdit:focus, QTextEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
                border: 1px solid {config.BTN_BG};
                outline: none;
            }}
            QCheckBox {{
                color: {config.FG_COLOR};
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {config.BTN_BG};
                border-color: {config.BTN_BG};
            }}
            QPushButton#btn_apply {{
                background-color: {config.BTN_BG};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                padding: 0 18px;
            }}
            QPushButton#btn_apply:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_apply:pressed {{ background-color: #125c2f; }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                padding: 0 12px;
            }}
            QPushButton#btn_secondary:hover {{ background-color: #2a2d2e; border-color: #888; }}
            QPushButton#btn_ghost_sm {{
                background-color: transparent;
                color: #888;
                border: 1px solid #444;
                border-radius: 4px;
                font-family: {config.UI_FONT_NAME};
                font-size: 9pt;
                padding: 0px;
                text-align: center;
            }}
            QPushButton#btn_ghost_sm:hover {{ background-color: #222; color: #bbb; border-color: #666; }}
            QPushButton[class="revert-btn"] {{
                padding: 0px;
                text-align: center;
                background: transparent;
                border: 1px solid #444;
                border-radius: 3px;
                color: #888;
                font-size: 12pt;
                font-weight: bold;
            }}
        """)

        # ─────────────────────────────────────────────────────────────────
        # Root layout: [LEFT menu | RIGHT content]
        # ─────────────────────────────────────────────────────────────────
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        class SolidFrame(QFrame):
            def paintEvent(self, e):
                from PySide6.QtGui import QPainter, QColor
                p = QPainter(self)
                p.fillRect(self.rect(), QColor(config.BG_COLOR))
                super().paintEvent(e)
                
        self.inner_frame = SolidFrame(self)
        self.inner_frame.setObjectName("MainInnerFrame")
        
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 0)
        self.inner_frame.setGraphicsEffect(shadow)
        
        main_layout.addWidget(self.inner_frame)
        
        outer_layout = QVBoxLayout(self.inner_frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        self._tb = CustomTitleBar(self, prefs.get("gui_lang", "en"), parent=self.inner_frame)
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False) and hasattr(self, 'setTitleBar'):
            self.setTitleBar(self._tb)
        # Manually force the title into toolbars that normally get theirs from windowTitle()
        if hasattr(self._tb, "_lbl_title"):
            self._tb._lbl_title.setText(self.txt("tool_settings"))
        self._tb.btn_min.hide()
        self._tb.btn_max.hide()
        outer_layout.addWidget(self._tb)
        
        root = QHBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer_layout.addLayout(root)

        # ── LEFT: Category list ───────────────────────────────────────────
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(155)
        self.category_list.setFocusPolicy(Qt.NoFocus)
        # Disable horizontal scrollbar — marquee handles overflow instead
        self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._marquee_delegate = MarqueeItemDelegate(self.category_list)
        self.category_list.setItemDelegate(self._marquee_delegate)
        root.addWidget(self.category_list)

        # ── RIGHT: stacked pages + bottom bar ────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        root.addLayout(right_layout)


        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        self.w_footer = QWidget()
        l_footer = QVBoxLayout(self.w_footer)
        l_footer.setContentsMargins(0, 0, 0, 0)
        l_footer.setSpacing(0)
        
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {config.SEPARATOR_COL}; max-height: 1px; border: none;")
        l_footer.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(16, 10, 16, 12)
        btn_bar.setSpacing(8)

        btn_bar.addStretch()

        # Right: Restore / Close / Apply
        self.btn_restore = QPushButton(self.txt("btn_restore_defaults"))
        self.btn_restore.setObjectName("btn_secondary")
        self.btn_restore.setMinimumWidth(120)
        self.btn_restore.setFixedHeight(30)
        self.btn_restore.setCursor(Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self._restore_all_defaults)
        btn_bar.addWidget(self.btn_restore)

        self.btn_close = QPushButton(self.txt("btn_close"))
        self.btn_close.setObjectName("btn_secondary")
        self.btn_close.setMinimumWidth(120)
        self.btn_close.setFixedHeight(30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.reject)
        btn_bar.addWidget(self.btn_close)

        self.btn_apply = QPushButton(self.txt("btn_apply"))
        self.btn_apply.setObjectName("btn_apply")
        self.btn_apply.setMinimumWidth(120)
        self.btn_apply.setFixedHeight(30)
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.clicked.connect(self._apply_settings)
        btn_bar.addWidget(self.btn_apply)

        l_footer.addLayout(btn_bar)
        right_layout.addWidget(self.w_footer)

        self._build_ui()

    # ── Helpers ───────────────────────────────────────────────────────────


    def _set_view_mode(self, mode):
        self.engine.save_preferences({'settings_view_mode': mode})
        if hasattr(self, '_initial_state'):
            self._initial_state['settings_view_mode'] = mode
            
        self._is_basic_mode = (mode == 'basic')
        
        item = self.category_list.item(4) # AI Engine
        if item:
            item.setHidden(self._is_basic_mode)
            
        if self._is_basic_mode and self.category_list.currentRow() == 4:
            self.category_list.setCurrentRow(0)
            
    def _build_ui(self):
        self._advanced_widgets = []
        self.category_list.clear()
        while self.stack.count() > 0:
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        prefs = self.engine.load_preferences() or {}
        view_mode = prefs.get('settings_view_mode', 'basic')
        self._is_basic_mode = (view_mode == 'basic')

        self.category_list.addItem(self.txt("tab_general"))
        self.category_list.addItem(self.txt("tab_transcript"))
        self.category_list.addItem(self.txt("tab_shortcuts"))
        self.category_list.addItem(self.txt("tab_custom_markers"))
        self.category_list.addItem(self.txt("tab_ai_engine"))
        self.category_list.addItem(self.txt("tab_telemetry"))
        self.category_list.addItem(self.txt("tab_support"))

        if self._is_basic_mode:
            item = self.category_list.item(4)
            if item:
                item.setHidden(True)

        self.revert_funcs = []
        
        self._page_built = [False] * self.category_list.count()
        for _ in range(self.category_list.count()):
            scroll = QScrollArea()
            scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
            self.stack.addWidget(scroll)

        def _on_tab_changed(idx):
            self.stack.setCurrentIndex(idx)
            item = self.category_list.item(idx)
            if item and item.text() == self.txt("tab_support"):
                self.w_footer.hide()
            else:
                self.w_footer.show()
                
            if not self._page_built[idx]:
                self._build_page(idx)
                
        self.category_list.currentRowChanged.connect(_on_tab_changed)
        self.category_list.setCurrentRow(0)
        self._build_page(0)

    def _add_row(self, form, label_text, widget, default_val, setter_func):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        row.addWidget(widget)
        btn_rev = QPushButton("↺")
        btn_rev.setFixedSize(26, 26)
        btn_rev.setCursor(Qt.PointingHandCursor)
        btn_rev.setObjectName("btn_ghost_sm")
        btn_rev.setToolTip(self.txt("tt_revert_to_default"))
        def create_reset_handler(s_func, d_val):
            return lambda checked=False: s_func(d_val)
        btn_rev.clicked.connect(create_reset_handler(setter_func, default_val))
        row.addWidget(btn_rev)
        lbl = QLabel(label_text)
        lbl.setWordWrap(True)
        lbl.setMinimumWidth(200)
        form.addRow(lbl, container)
        self.revert_funcs.append(lambda d=default_val, s=setter_func: s(d))
        return lbl, container

    def _build_page(self, idx):
        scroll = self.stack.widget(idx)
        prefs = self.engine.load_preferences() or {}
        
        mapping = {0: 'general', 1: 'transcript', 2: 'shortcuts', 3: 'custom_markers', 4: 'ai_engine', 5: 'telemetry', 6: 'support'}
            
        page_name = mapping.get(idx)
        if not page_name:
            return
            
        method = getattr(self, f"_build_page_{page_name}", None)
        if method:
            page_widget = method(prefs)
            if page_widget:
                scroll.setWidget(page_widget)
            self._page_built[idx] = True

    def _build_page_general(self, prefs):
        # PAGE 0 — GENERAL
        # ─────────────────────────────────────────────────────────────────
        page_gen = QWidget()
        page_gen.setStyleSheet("background: transparent;")
        l_gen = QVBoxLayout(page_gen)
        l_gen.setContentsMargins(24, 20, 24, 16)

        # Basic/Advanced view switch

        view_btn_row = QHBoxLayout()
        view_btn_row.setContentsMargins(0, 0, 0, 16)
        view_btn_row.setSpacing(10)
        
        btn_view_basic = QPushButton(self.txt("btn_view_basic"))
        btn_view_basic.setFixedHeight(30)
        btn_view_basic.setCursor(Qt.PointingHandCursor)
        active_btn_style = "background-color: #1b8745; color: white; border: 1px solid #125c2f; border-radius: 4px; font-weight: bold;"
        inactive_btn_style = "background-color: #1a1a1a; color: #777777; border-top: 1px solid #0d0d0d; border-bottom: 1px solid #2e2e2e; border-left: 1px solid #141414; border-right: 1px solid #141414; border-radius: 4px; font-weight: normal;"
        
        if self._is_basic_mode:
            btn_view_basic.setStyleSheet(active_btn_style)
        else:
            btn_view_basic.setStyleSheet(inactive_btn_style)
        btn_view_basic.clicked.connect(lambda: self._set_view_mode('basic'))
        
        btn_view_advanced = QPushButton(self.txt("btn_view_advanced"))
        btn_view_advanced.setFixedHeight(30)
        btn_view_advanced.setCursor(Qt.PointingHandCursor)
        
        if prefs.get('settings_view_mode', 'basic') == 'advanced':
            btn_view_advanced.setStyleSheet(active_btn_style)
        else:
            btn_view_advanced.setStyleSheet(inactive_btn_style)
            
        btn_view_advanced.clicked.connect(lambda: self._set_view_mode('advanced'))

        view_btn_row.addWidget(btn_view_basic)
        view_btn_row.addWidget(btn_view_advanced)
        l_gen.addLayout(view_btn_row)

        # ── Version / Update card (at the top) ────────────────────────────
        ver_card = QFrame()
        ver_card.setStyleSheet(
            "QFrame { background-color: #111; border: 1px solid #242424; border-radius: 8px; }"
        )
        ver_card_lay = QVBoxLayout(ver_card)
        ver_card_lay.setContentsMargins(16, 12, 16, 12)
        ver_card_lay.setSpacing(10)

        # Row 1: version + status + Update Now
        ver_row = QHBoxLayout()
        ver_row.setSpacing(6)
        lbl_ver_key = QLabel(self.txt("lbl_ver_installed") + ":")
        lbl_ver_key.setStyleSheet("color: #666; font-size: 9pt; background: transparent; border: none;")
        lbl_ver_val = QLabel(config.VERSION)
        lbl_ver_val.setStyleSheet(f"color: {config.FG_COLOR}; font-size: 11pt; font-weight: bold; background: transparent; border: none;")
        self._lbl_ver_status = QLabel("…")
        self._lbl_ver_status.setStyleSheet("color: #555; font-size: 9pt; background: transparent; border: none;")
        self._btn_ver_update = QPushButton(self.txt("btn_settings_update_now"))
        self._btn_ver_update.setObjectName("btn_ghost_sm")
        self._btn_ver_update.setStyleSheet("padding: 3px 10px; font-size: 9pt;")
        self._btn_ver_update.setCursor(Qt.PointingHandCursor)
        self._btn_ver_update.hide()
        ver_row.addWidget(lbl_ver_key)
        ver_row.addWidget(lbl_ver_val)
        ver_row.addSpacing(12)
        ver_row.addWidget(self._lbl_ver_status)
        ver_row.addStretch()
        ver_row.addWidget(self._btn_ver_update)
        ver_card_lay.addLayout(ver_row)

        # Thin divider inside card
        card_sep = QFrame()
        card_sep.setFrameShape(QFrame.Shape.HLine)
        card_sep.setStyleSheet("background-color: #222; max-height: 1px; border: none;")
        ver_card_lay.addWidget(card_sep)

        # Row 2: Notify toggle
        tgl_notify_row = QHBoxLayout()
        tgl_notify_row.setSpacing(10)
        self.tgl_auto_check_updates = ToggleSwitch()
        self.tgl_auto_check_updates.setChecked(
            bool(prefs.get('auto_check_updates', True)), animated=False
        )
        self.tgl_auto_check_updates.setToolTip(self.txt("tt_auto_check_updates"))
        lbl_notify = QLabel(self.txt("lbl_auto_check_updates"))
        lbl_notify.setStyleSheet(f"color: {config.FG_COLOR}; font-size: 10pt; background: transparent; border: none;")
        lbl_notify.setToolTip(self.txt("tt_auto_check_updates"))
        tgl_notify_row.addWidget(self.tgl_auto_check_updates)
        tgl_notify_row.addWidget(lbl_notify)
        tgl_notify_row.addStretch()
        ver_card_lay.addLayout(tgl_notify_row)

        # Row 3: Auto-update toggle
        tgl_autoupd_row = QHBoxLayout()
        tgl_autoupd_row.setSpacing(10)
        self.tgl_auto_update_on_start = ToggleSwitch()
        self.tgl_auto_update_on_start.setChecked(
            bool(prefs.get('auto_update_on_start', False)), animated=False
        )
        self.tgl_auto_update_on_start.setToolTip(self.txt("tt_auto_update_on_start"))
        lbl_autoupd = QLabel(self.txt("lbl_auto_update_on_start"))
        lbl_autoupd.setStyleSheet(f"color: {config.FG_COLOR}; font-size: 10pt; background: transparent; border: none;")
        lbl_autoupd.setToolTip(self.txt("tt_auto_update_on_start"))
        tgl_autoupd_row.addWidget(self.tgl_auto_update_on_start)
        tgl_autoupd_row.addWidget(lbl_autoupd)
        tgl_autoupd_row.addStretch()
        ver_card_lay.addLayout(tgl_autoupd_row)

        l_gen.addWidget(ver_card)
        l_gen.addSpacing(12)

        # ── Async: populate version status + wire Update Now button ───────
        # Use engine reference captured now; derive lang at call time from prefs
        _card_engine = self.engine

        def _card_lang():
            p = _card_engine.load_preferences() or {}
            return p.get('gui_lang', 'en')

        def _on_update_known_for_card(latest_ver, gh_url, gl_url):
            # If auto-update already ran silently this session, just show restart notice
            main_win = self.parent()
            pending = getattr(main_win, '_pending_update_ver', None)
            if pending and pending == latest_ver:
                self._lbl_ver_status.setText(self.txt('lbl_ver_pending_restart'))
                self._lbl_ver_status.setStyleSheet(
                    "color: #f4a641; font-size: 9pt; font-weight: bold; background: transparent; border: none;"
                )
                self._btn_ver_update.hide()
                return

            # Normal: update available, show Update Now button
            self._lbl_ver_status.setText(
                f"{self.txt('lbl_ver_update_avail')} {latest_ver}"
            )
            self._lbl_ver_status.setStyleSheet(
                "color: #f4a641; font-size: 9pt; background: transparent; border: none;"
            )
            self._btn_ver_update.show()

            def _do_inline_update():
                import threading, subprocess, tempfile, os, urllib.request, ssl
                from osdoc import log_info, log_error

                is_win  = _card_engine.os_doc.is_win
                from gui import UpdateNotifyDialog as _UND
                urls = [_UND._UPDATE_SCRIPT, _UND._UPDATE_SCRIPT_GL]

                # Disable button + show "Updating…"
                self._btn_ver_update.setEnabled(False)
                self._btn_ver_update.setText(_txt(_card_lang(), 'update_notify_updating'))
                self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_wait'))
                self._lbl_ver_status.setStyleSheet(
                    "color: #888; font-size: 9pt; font-style: italic; background: transparent; border: none;"
                )

                # Signal bridge: safe cross-thread UI update
                class _Bridge(QObject):
                    done = Signal(bool, str)
                _bridge = _Bridge(self)

                def _on_done(success, err):
                    if success:
                        log_info("[Updater] Card update succeeded.")
                        self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_success'))
                        self._lbl_ver_status.setStyleSheet(
                            "color: #39ff7a; font-size: 9pt; background: transparent; border: none;"
                        )
                        self._btn_ver_update.hide()
                    else:
                        log_error(f"[Updater] Card update failed: {err}")
                        self._lbl_ver_status.setText(_txt(_card_lang(), 'update_notify_failed'))
                        self._lbl_ver_status.setStyleSheet(
                            "color: #ed4245; font-size: 9pt; background: transparent; border: none;"
                        )
                        self._btn_ver_update.setText(_txt(_card_lang(), 'update_notify_win_btn'))
                        self._btn_ver_update.setEnabled(True)
                        try:
                            self._btn_ver_update.clicked.disconnect()
                        except Exception:
                            pass
                        from gui import UpdateNotifyDialog as _UND2
                        self._btn_ver_update.clicked.connect(
                            lambda: _UND2._open_url(gh_url)
                        )
                        self._btn_ver_update.show()

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
                        fd, tmp = tempfile.mkstemp(suffix='.py', prefix='bw_upd_')
                        with os.fdopen(fd, 'wb') as fh:
                            fh.write(content)
                        cf = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                        
                        install_dir = getattr(_card_engine.os_doc, 'install_dir', '')
                        
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

            # Disconnect any previous connections, then wire up.
            # PySide6 emits RuntimeWarning (not RuntimeError) when no connections
            # exist — catch_warnings suppresses it cleanly without hiding real bugs.
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    self._btn_ver_update.clicked.disconnect()
                except Exception:
                    pass
            self._btn_ver_update.clicked.connect(_do_inline_update)

        def _on_check_done_for_card():
            if self._lbl_ver_status.text() == "…":
                self._lbl_ver_status.setText(self.txt("lbl_ver_up_to_date"))
                self._lbl_ver_status.setStyleSheet(
                    "color: #39ff7a; font-size: 9pt; background: transparent; border: none;"
                )

        _thr = UpdateCheckThread(config.VERSION, parent=self)
        _thr.update_available.connect(_on_update_known_for_card)
        _thr.finished.connect(_on_check_done_for_card)
        _thr.start()
        self._settings_ver_thread = _thr

        # ── Language + App Icon ────────────────────────────────────────────
        form_gen = QFormLayout()
        form_gen.setSpacing(14)
        form_gen.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Language dropdown
        self.dropdown_lang = CustomDropdown(list(config.SUPPORTED_LANGS.values()))
        current_lang_code = prefs.get('gui_lang', 'en')
        self.dropdown_lang.setText(config.SUPPORTED_LANGS.get(current_lang_code, 'English'))

        def _on_lang_changed(val):
            code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), 'en')
            prefs = self.engine.load_preferences() or {}
            if code == prefs.get('gui_lang'):
                return

            current_state = self._get_current_state_dict()
            current_state['gui_lang'] = code
            
            prefs['gui_lang'] = code
            self.engine.save_preferences(prefs)

            self._build_ui()
            self._restore_state_dict(current_state)

            target = config.TRANS.get(code, config.TRANS['en'])
            title   = target.get('msg_title_language_changed', 'Language Changed')
            message = target.get('msg_restart_lang_pending', 'Language changed. Full changes will apply on restart.')
            ok_text = target.get('btn_ok', 'OK')
            
            CustomMsgBox(self, title, message, ok_text).exec()
            
            self.btn_apply.setText(self.txt("btn_apply"))
            self.btn_close.setText(self.txt("btn_close"))
            self.btn_restore.setText(self.txt("btn_restore_defaults"))

        self.dropdown_lang.valueChanged.connect(_on_lang_changed)
        def _reset_lang(val):
            self.dropdown_lang.setText(val)
            _on_lang_changed(val)
        self._add_row(form_gen, self.txt("lbl_language"), self.dropdown_lang, 'English', _reset_lang)

        # App Icon (Visual Selector)
        icon_row = QHBoxLayout()
        icon_row.setSpacing(10)
        self.icon_group = QButtonGroup(self)
        self.icon_group.setExclusive(True)
        
        icon_names = ["default", "monochrome", "whiteb", "white"]
        saved_icon = prefs.get('app_icon', 'default')
        
        from PySide6.QtGui import QIcon
        from PySide6.QtCore import QSize
        import os
        
        for i, name in enumerate(icon_names):
            btn = QPushButton()
            ext = ".ico" if self.engine.os_doc.is_win else ".png"
            icon_path = os.path.join(self.engine.os_doc.install_dir, "icons", f"icon_{name}{ext}")
            
            if os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(QSize(48, 48))
            btn.setCheckable(True)
            if name == saved_icon:
                btn.setChecked(True)
                
            btn.setProperty("icon_name", name)
            
            btn.setStyleSheet("""
                QPushButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px; }
                QPushButton:checked { background: #262626; border: 1px solid #404040; }
                QPushButton:hover { background: #333333; }
            """)
            self.icon_group.addButton(btn, i)
            icon_row.addWidget(btn)
            
        icon_row.addStretch()
        
        icon_container = QWidget()
        icon_container.setLayout(icon_row)
        icon_container.layout().setContentsMargins(0, 0, 0, 0)
        
        lbl_icon, container_icon = self._add_row(form_gen, self.txt("lbl_app_icon"), icon_container, 'default', lambda: None)
        btn_rev_icon = container_icon.findChild(QPushButton, "btn_ghost_sm")
        if btn_rev_icon:
            btn_rev_icon.clicked.disconnect()
            def set_icon_default(val="default"):
                for btn in self.icon_group.buttons():
                    if btn.property("icon_name") == val:
                        btn.setChecked(True)
                        break
            btn_rev_icon.clicked.connect(lambda *args: set_icon_default("default"))

        l_gen.addLayout(form_gen)
        l_gen.addSpacing(8)
        l_gen.addStretch()


        # ── Import / Export settings (bottom) ─────────────────────────────
        io_row = QHBoxLayout()
        io_row.setContentsMargins(0, 0, 0, 8)
        io_row.setSpacing(8)

        btn_import_s = QPushButton(self.txt("btn_import_settings"))
        btn_import_s.setObjectName("btn_ghost_sm")
        btn_import_s.setStyleSheet("padding: 4px 12px;")
        btn_import_s.setCursor(Qt.PointingHandCursor)
        btn_import_s.clicked.connect(self._on_import_settings)
        io_row.addWidget(btn_import_s)

        btn_export_s = QPushButton(self.txt("btn_export_settings"))
        btn_export_s.setObjectName("btn_ghost_sm")
        btn_export_s.setStyleSheet("padding: 4px 12px;")
        btn_export_s.setCursor(Qt.PointingHandCursor)
        btn_export_s.clicked.connect(self._on_export_settings)
        io_row.addWidget(btn_export_s)
        io_row.addStretch()
        l_gen.addLayout(io_row)

        # ─────────────────────────────────────────────────────────────────

        return page_gen

    def _build_page_shortcuts(self, prefs):
        # PAGE 1 — SHORTCUTS


        # ─────────────────────────────────────────────────────────────────
        page_shorts = QWidget()
        page_shorts.setStyleSheet("background: transparent;")
        l_shorts = QVBoxLayout(page_shorts)
        l_shorts.setContentsMargins(24, 20, 24, 16)
        l_shorts.setSpacing(0)


        default_shortcuts = getattr(config, 'DEFAULT_SETTINGS', {}).get('shortcuts', {})
        # Merge defaults with saved prefs, keeping only keys present in DEFAULT_SETTINGS
        saved_shortcuts = prefs.get('shortcuts', {})
        current_shortcuts = {k: saved_shortcuts.get(k, v) for k, v in default_shortcuts.items()}

        self.shortcut_inputs = {}

        def _check_shortcut_conflicts():
            """Scan all capturable inputs; set red border on any with a duplicate sequence."""
            # Gather sequences from capturable inputs only (built-in + custom marker)
            all_inputs = dict(self.shortcut_inputs)
            all_inputs.update(getattr(self, 'custom_marker_shortcut_inputs', {}))
            seq_to_keys = {}
            for k, w in all_inputs.items():
                if w.display_only:
                    continue
                seq = w.get_sequence()
                if seq:
                    seq_to_keys.setdefault(seq, []).append(k)
            # Apply conflict styling
            for k, w in all_inputs.items():
                if w.display_only:
                    continue
                seq = w.get_sequence()
                is_conflict = seq and len(seq_to_keys.get(seq, [])) > 1
                w.set_conflict(bool(is_conflict))


        # Builds label + field container for one shortcut row (used for addRow and insertRow)
        def _make_shortcut_widgets(label_text, widget, default_val, setter_func, is_display=False, info_key=None):
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(widget)

            if not is_display:
                btn_clear = QPushButton("✕")
                btn_clear.setFixedSize(26, 26)
                btn_clear.setCursor(Qt.PointingHandCursor)
                btn_clear.setObjectName("btn_ghost_sm")
                btn_clear.setToolTip(self.txt("tt_clear_shortcut") if self.txt("tt_clear_shortcut") != "tt_clear_shortcut" else "Clear shortcut")
                btn_clear.clicked.connect(lambda: setter_func(""))
                row.addWidget(btn_clear)

            btn_rev = QPushButton("↺")
            btn_rev.setFixedSize(26, 26)
            btn_rev.setCursor(Qt.PointingHandCursor)
            btn_rev.setObjectName("btn_ghost_sm")
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            def create_reset_handler(s_func, d_val):
                return lambda checked=False: s_func(d_val)
            btn_rev.clicked.connect(create_reset_handler(setter_func, default_val))
            row.addWidget(btn_rev)

            lbl = QLabel(label_text)
            lbl.setWordWrap(True)
            
            if info_key:
                lbl_container = QWidget()
                lbl_container.setMinimumWidth(200)
                lbl_layout = QHBoxLayout(lbl_container)
                lbl_layout.setContentsMargins(0, 0, 0, 0)
                lbl_layout.setSpacing(6)
                info_icon = self.parent()._create_info_icon(info_key)
                lbl_layout.addWidget(lbl)
                lbl_layout.addWidget(info_icon)
                lbl_layout.addStretch()
                return lbl_container, container

            lbl.setMinimumWidth(200)
            return lbl, container

        def _add_shortcut_row(form, label_text, widget, default_val, setter_func, is_display=False):
            lbl, container = _make_shortcut_widgets(label_text, widget, default_val, setter_func, is_display)
            form.addRow(lbl, container)

        # Keys and their ordering in the final form
        MARKER_KEYS  = {'mark_red', 'mark_blue', 'mark_green', 'mark_eraser'}
        NAV_KEYS     = {'search', 'open_settings', 'jump_to_word', 'play_stop', 'skip_backward', 'skip_forward'}
        DISPLAY_ONLY = set()
        KEY_ORDER    = ['mark_red', 'mark_blue', 'mark_green', 'mark_eraser',
                        'search', 'open_settings', 'jump_to_word', 'play_stop', 'skip_backward', 'skip_forward']

        def make_setter(w, check_fn):
            def _setter(v):
                w.set_sequence(str(v))
                check_fn()
            return _setter

        # ── ONE unified QFormLayout ───────────────────────────────────────────
        # Custom markers inserted via insertRow() at _custom_sc_insert_pos so
        # spacing is always identical (14px) between EVERY row.
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Marker shortcuts (red … eraser)
        for key in KEY_ORDER:
            if key not in MARKER_KEYS or key not in current_shortcuts:
                continue
            is_disp = key in DISPLAY_ONLY
            if self._is_basic_mode and is_disp:
                continue
            value      = current_shortcuts[key]
            i18n_key   = f'shortcut_{key}'
            label_text = self.txt(i18n_key) if self.txt(i18n_key) != i18n_key else key.replace('_', ' ').title()
            
            if key == 'jump_to_word':
                opts_keys = ['opt_ctrl_lmb', 'opt_ctrl_rmb', 'opt_alt_lmb', 'opt_alt_rmb', 'opt_shift_lmb', 'opt_shift_rmb']
                key_map = {k: self.txt(k) for k in opts_keys}
                widget = MouseShortcutCaptureButton(str(value), key_map, display_only=is_disp)
                widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
                lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, 'opt_ctrl_lmb'),
                                                         make_setter(widget, _check_shortcut_conflicts),
                                                         is_display=is_disp, info_key='tt_jump_to_word_info')
            else:
                widget = ShortcutCaptureButton(str(value), display_only=is_disp)
                widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
                lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, ''),
                                                         make_setter(widget, _check_shortcut_conflicts),
                                                         is_display=is_disp)
            form.addRow(lbl, container)
            self.shortcut_inputs[key] = widget

        # Position where custom marker rows will be inserted (after last marker row)
        self._custom_sc_insert_pos       = form.rowCount()
        self._custom_sc_unified          = form
        self._make_shortcut_widgets_fn   = _make_shortcut_widgets
        self._check_shortcut_conflicts_fn = _check_shortcut_conflicts
        self._add_shortcut_row_fn         = _add_shortcut_row
        self.custom_marker_shortcut_inputs = {}

        # Nav shortcuts (search, open_settings, jump_to_word)
        for key in KEY_ORDER:
            if key not in NAV_KEYS or key not in current_shortcuts:
                continue
            is_disp = key in DISPLAY_ONLY
            if self._is_basic_mode and is_disp:
                continue
            value      = current_shortcuts[key]
            i18n_key   = f'shortcut_{key}'
            label_text = self.txt(i18n_key) if self.txt(i18n_key) != i18n_key else key.replace('_', ' ').title()
            
            if key == 'jump_to_word':
                opts_keys = ['opt_ctrl_lmb', 'opt_ctrl_rmb', 'opt_alt_lmb', 'opt_alt_rmb', 'opt_shift_lmb', 'opt_shift_rmb']
                key_map = {k: self.txt(k) for k in opts_keys}
                widget = MouseShortcutCaptureButton(str(value), key_map, display_only=is_disp)
                widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
                lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, 'opt_ctrl_lmb'),
                                                         make_setter(widget, _check_shortcut_conflicts),
                                                         is_display=is_disp, info_key='tt_jump_to_word_info')
            else:
                widget = ShortcutCaptureButton(str(value), display_only=is_disp)
                widget.sequence_changed.connect(lambda _seq, _w=widget: _check_shortcut_conflicts())
                lbl, container = _make_shortcut_widgets(label_text, widget, default_shortcuts.get(key, ''),
                                                         make_setter(widget, _check_shortcut_conflicts),
                                                         is_display=is_disp)
            form.addRow(lbl, container)
            self.shortcut_inputs[key] = widget

        l_shorts.addLayout(form)
        l_shorts.addStretch()

        _check_shortcut_conflicts()


        # ─────────────────────────────────────────────────────────────────

        return page_shorts

    def _build_page_custom_markers(self, prefs):
        # PAGE 2 — CUSTOM MARKERS
        # ─────────────────────────────────────────────────────────────────
        page_markers = QWidget()
        page_markers.setStyleSheet("background: transparent;")
        l_markers = QVBoxLayout(page_markers)
        l_markers.setContentsMargins(24, 20, 24, 16)
        l_markers.setSpacing(10)

        self.current_custom_markers = list(prefs.get('custom_markers', []))

        # Scroll area to hold the dynamic marker rows
        markers_scroll = QScrollArea()
        markers_scroll.setWidgetResizable(True)
        markers_scroll.setFrameShape(QFrame.NoFrame)
        markers_scroll.setMinimumHeight(120)
        markers_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
            }}
            QWidget#markers_inner {{
                background-color: #1e1e1e;
            }}
        """)
        self._markers_inner = MarkerDragZone()
        self._markers_inner.setObjectName("markers_inner")
        self._markers_layout = self._markers_inner.layout()
        self._markers_layout.setContentsMargins(4, 4, 4, 4)
        self._markers_layout.setSpacing(2)
        self._markers_layout.addStretch()
        markers_scroll.setWidget(self._markers_inner)
        self._refresh_markers_list()
        # Also refresh Shortcuts tab now that current_custom_markers is populated
        self._refresh_custom_marker_shortcuts()
        l_markers.addWidget(markers_scroll)


        marker_btn_row = QHBoxLayout()
        marker_btn_row.setSpacing(8)
        btn_add_m = QPushButton(self.txt("btn_add_marker"))
        btn_add_m.setObjectName("btn_secondary")
        btn_add_m.setFixedHeight(30)
        btn_add_m.setCursor(Qt.PointingHandCursor)
        btn_add_m.clicked.connect(self._on_add_marker)
        marker_btn_row.addWidget(btn_add_m)

        btn_export_m = QPushButton(self.txt("btn_export_markers"))
        btn_export_m.setObjectName("btn_ghost_sm")
        btn_export_m.setStyleSheet("padding: 0 14px;")
        btn_export_m.setFixedHeight(30)
        btn_export_m.setCursor(Qt.PointingHandCursor)
        btn_export_m.clicked.connect(self._on_export_markers)
        marker_btn_row.addWidget(btn_export_m)

        btn_import_m = QPushButton(self.txt("btn_import_markers"))
        btn_import_m.setObjectName("btn_ghost_sm")
        btn_import_m.setStyleSheet("padding: 0 14px;")
        btn_import_m.setFixedHeight(30)
        btn_import_m.setCursor(Qt.PointingHandCursor)
        btn_import_m.clicked.connect(self._on_import_markers)
        marker_btn_row.addWidget(btn_import_m)

        marker_btn_row.addStretch()
        l_markers.addLayout(marker_btn_row)



        # ─────────────────────────────────────────────────────────────────

        return page_markers

    def _build_page_transcript(self, prefs):
        # PAGE 3 — TRANSCRIPT
        # ─────────────────────────────────────────────────────────────────
        page_transcript = QWidget()
        page_transcript.setStyleSheet("background: transparent;")
        l_transcript = QVBoxLayout(page_transcript)
        l_transcript.setContentsMargins(24, 20, 24, 16)
        l_transcript.setSpacing(0)

        if not self._is_basic_mode:
            form_ontop = QFormLayout()
            form_ontop.setSpacing(14)
            form_ontop.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
            self.chk_ontop = ToggleSwitch()
            self.chk_ontop.setChecked(bool(prefs.get('always_on_top', False)), animated=False)
            w_ontop = QWidget()
            l_ontop = QHBoxLayout(w_ontop)
            l_ontop.setContentsMargins(0, 0, 0, 0)
            l_ontop.addStretch()
            l_ontop.addWidget(self.parent()._create_info_icon("tt_always_on_top"))
            l_ontop.addSpacing(6)
            l_ontop.addWidget(self.chk_ontop)
            
            self._add_row(form_ontop, self.txt("lbl_always_on_top"), w_ontop,
                     False, lambda v: self.chk_ontop.setChecked(v, animated=False))
            l_transcript.addLayout(form_ontop)
            
            l_transcript.addSpacing(14)

        form_transcript = QFormLayout()
        form_transcript.setSpacing(14)
        form_transcript.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Display Mode (moved from General)
        view_items = [self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")]
        self.combo_view = CustomDropdown(view_items)
        is_seg = prefs.get('view_mode', 'segmented') == 'segmented'
        self.combo_view.setText(self.txt("opt_segmented_blocks") if is_seg else self.txt("opt_continuous_flow"))
        self._add_row(form_transcript, self.txt("lbl_display_mode"), self.combo_view,
                 self.txt("opt_segmented_blocks"), self.combo_view.setValue)

        self._chunk_widgets = []
        if not self._is_basic_mode:
            def _add_chunk_row(form, label_text, widget, default_val, setter_func, info_key):
                container = QWidget()
                row = QHBoxLayout(container)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(6)
                widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                row.addWidget(widget)
                
                btn_rev = QPushButton("↺")
                btn_rev.setFixedSize(26, 26)
                btn_rev.setCursor(Qt.PointingHandCursor)
                btn_rev.setObjectName("btn_ghost_sm")
                btn_rev.setToolTip(self.txt("tt_revert_to_default"))
                def create_reset_handler(s_func, d_val):
                    return lambda checked=False: s_func(d_val)
                btn_rev.clicked.connect(create_reset_handler(setter_func, default_val))
                row.addWidget(btn_rev)
                
                lbl_container = QWidget()
                lbl_container.setMinimumWidth(200)
                lbl_layout = QHBoxLayout(lbl_container)
                lbl_layout.setContentsMargins(0, 0, 0, 0)
                lbl_layout.setSpacing(6)
                lbl = QLabel(label_text)
                lbl.setWordWrap(True)
                lbl_layout.addWidget(lbl)
                lbl_layout.addWidget(self.parent()._create_info_icon(info_key))
                lbl_layout.addStretch()
                
                form.addRow(lbl_container, container)
                self.revert_funcs.append(lambda d=default_val, s=setter_func: s(d))
                return lbl_container, container

            self.spin_chunk_max = QSpinBox()
            self.spin_chunk_max.setRange(5, 200)
            self.spin_chunk_max.setValue(int(prefs.get('chunk_max_words', 30)))
            lbl_max, cnt_max = _add_chunk_row(form_transcript, self.txt("lbl_chunk_max_words"), self.spin_chunk_max, 30, self.spin_chunk_max.setValue, "tt_chunk_max_words")
            self._chunk_widgets.extend([lbl_max, cnt_max])

            self.spin_chunk_look = QSpinBox()
            self.spin_chunk_look.setRange(0, 20)
            self.spin_chunk_look.setValue(int(prefs.get('chunk_lookahead', 3)))
            lbl_look, cnt_look = _add_chunk_row(form_transcript, self.txt("lbl_chunk_lookahead"), self.spin_chunk_look, 3, self.spin_chunk_look.setValue, "tt_chunk_lookahead")
            self._chunk_widgets.extend([lbl_look, cnt_look])

            self.spin_chunk_min = QSpinBox()
            self.spin_chunk_min.setRange(1, 50)
            self.spin_chunk_min.setValue(int(prefs.get('chunk_min_chars', 7)))
            lbl_min, cnt_min = _add_chunk_row(form_transcript, self.txt("lbl_chunk_min_chars"), self.spin_chunk_min, 7, self.spin_chunk_min.setValue, "tt_chunk_min_chars")
            self._chunk_widgets.extend([lbl_min, cnt_min])



            def _update_chunk_state(idx):
                visible = (idx == 1)
                for w in self._chunk_widgets:
                    w.setVisible(visible)
            
            self.combo_view.valueChanged.connect(lambda v: _update_chunk_state(1 if v == self.txt("opt_segmented_blocks") else 0))
            _update_chunk_state(1 if self.combo_view.currentText() == self.txt("opt_segmented_blocks") else 0)

        # Font family, size, line height
        from PySide6.QtGui import QFontDatabase
        self.combo_font = SearchableDropdown(QFontDatabase.families())
        self.combo_font.setText(prefs.get('editor_font_family', self.DEFAULTS['editor_font_family']))

        self.spin_fsize = QSpinBox()
        self.spin_fsize.setRange(8, 48)
        self.spin_fsize.setValue(int(prefs.get('editor_font_size', self.DEFAULTS['editor_font_size'])))

        self.spin_lheight = QSpinBox()
        self.spin_lheight.setRange(0, 40)
        self.spin_lheight.setValue(int(prefs.get('editor_line_height', self.DEFAULTS['editor_line_height'])))

        self._add_row(form_transcript, self.txt("lbl_transcript_font"), self.combo_font,
                 self.DEFAULTS['editor_font_family'], self.combo_font.setValue)
        self._add_row(form_transcript, self.txt("lbl_font_size_pt"),    self.spin_fsize,
                 self.DEFAULTS['editor_font_size'],   self.spin_fsize.setValue)
        self._add_row(form_transcript, self.txt("lbl_line_spacing_px"), self.spin_lheight,
                 self.DEFAULTS['editor_line_height'], self.spin_lheight.setValue)
        l_transcript.addLayout(form_transcript)

        # Font preview
        from PySide6.QtWidgets import QTextEdit
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
                lh = self.spin_lheight.value()
                # Document size includes lh added to the bottom of the last line.
                # We subtract lh to get the actual visual height, then add 24px padding.
                new_h = int(self.lbl_preview.document().size().height()) - lh + 24
                # Ensure height doesn't become too small due to calculation artifacts
                new_h = max(30, new_h)
                if self.lbl_preview.height() != new_h:
                    self.lbl_preview.setFixedHeight(new_h)
            except: pass
            
        self.lbl_preview.document().documentLayout().documentSizeChanged.connect(_update_preview_height)
        self.lbl_preview.setStyleSheet(f"background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px; color: {config.FG_COLOR}; padding: 12px 14px;")
        l_transcript.addSpacing(10)
        l_transcript.addWidget(self.lbl_preview)


        # Removed sep_chunk
        # ── Sync DaVinci timeline on chapter switch ─ BOTTOM of Transcript tab
        # (below font preview and chunking settings, applies to both basic/advanced)
        l_transcript.addSpacing(14)

        form_bottom = QFormLayout()
        form_bottom.setSpacing(14)
        form_bottom.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.chk_sync_davinci = ToggleSwitch()
        self.chk_sync_davinci.setChecked(bool(prefs.get('sync_davinci_chapter', True)), animated=False)
        w_sync = QWidget()
        l_sync = QHBoxLayout(w_sync)
        l_sync.setContentsMargins(0, 0, 0, 0)
        l_sync.addStretch()
        l_sync.addWidget(self.parent()._create_info_icon("tt_sync_davinci_chapter"))
        l_sync.addSpacing(6)
        l_sync.addWidget(self.chk_sync_davinci)
        self._add_row(form_bottom, self.txt("chk_sync_davinci"), w_sync,
                 True, lambda v: self.chk_sync_davinci.setChecked(v, animated=False))

        # Track order toggle — directly below sync davinci
        import config as _cfg_bot
        _bot_prefs = self.engine.load_preferences() or {}
        self.tgl_xml_preserve_track_order = ToggleSwitch()
        self.tgl_xml_preserve_track_order.setChecked(
            bool(_bot_prefs.get("xml_preserve_track_order",
                                _cfg_bot.DEFAULT_SETTINGS["xml_preserve_track_order"])),
            animated=False
        )
        self.tgl_xml_preserve_track_order.toggled.connect(
            lambda checked: self.engine.save_preferences({"xml_preserve_track_order": checked})
        )
        w_xml_track = QWidget()
        l_xml_track = QHBoxLayout(w_xml_track)
        l_xml_track.setContentsMargins(0, 0, 0, 0)
        l_xml_track.addStretch()
        l_xml_track.addWidget(self.parent()._create_info_icon("tt_xml_preserve_track_order"))
        l_xml_track.addSpacing(6)
        l_xml_track.addWidget(self.tgl_xml_preserve_track_order)
        self._add_row(form_bottom, self.txt("lbl_xml_preserve_track_order"), w_xml_track,
                 False, lambda v: self.tgl_xml_preserve_track_order.setChecked(v, animated=False))

        # ── Precise timestamps toggle — bottom of Transcript tab (basic + advanced) ──
        self.tgl_timestamp_precise = ToggleSwitch()
        self.tgl_timestamp_precise.setChecked(
            bool(prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise'])),
            animated=False
        )
        w_ts_precise = QWidget()
        l_ts_precise = QHBoxLayout(w_ts_precise)
        l_ts_precise.setContentsMargins(0, 0, 0, 0)
        l_ts_precise.addStretch()
        l_ts_precise.addWidget(self.parent()._create_info_icon("tt_timestamp_precise"))
        l_ts_precise.addSpacing(6)
        l_ts_precise.addWidget(self.tgl_timestamp_precise)
        self._add_row(form_bottom, self.txt("lbl_timestamp_precise"), w_ts_precise,
                 False, lambda v: self.tgl_timestamp_precise.setChecked(v, animated=False))

        l_transcript.addLayout(form_bottom)
        l_transcript.addSpacing(14)

        self.combo_font.valueChanged.connect(self._update_preview)
        self.spin_fsize.valueChanged.connect(self._update_preview)
        self.spin_lheight.valueChanged.connect(self._update_preview)
        self._update_preview()
        l_transcript.addStretch()

        # ─────────────────────────────────────────────────────────────────

        return page_transcript

    def _build_page_ai_engine(self, prefs):
        # PAGE 5 — AI ENGINE
        # ─────────────────────────────────────────────────────────────────
        page_ai = QWidget()
        page_ai.setStyleSheet("background: transparent;")
        l_ai = QVBoxLayout(page_ai)
        l_ai.setContentsMargins(24, 20, 24, 16)
        l_ai.setSpacing(0)
        form_ai = QFormLayout()
        form_ai.setSpacing(14)
        form_ai.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        l_ai.addLayout(form_ai)

        # Device
        _device_items = ["Auto", "CPU", "GPU"]
        self.dropdown_device = CustomDropdown(_device_items, parent=page_ai)
        self.dropdown_device.setFixedHeight(30)
        saved_device = prefs.get('device', 'auto').upper()
        if saved_device == 'AUTO': saved_device = 'Auto'
        self.dropdown_device.setText(saved_device if saved_device in _device_items else 'Auto')
        self._add_row(form_ai, self.txt("lbl_device"), self.dropdown_device, 'Auto', self.dropdown_device.setValue)

        # Compute type
        _compute_items = ["Auto", "float16", "int8", "float32", "int8_float16", "int8_float32"]
        self.dropdown_compute = CustomDropdown(_compute_items, parent=page_ai)
        self.dropdown_compute.setFixedHeight(30)
        saved_compute = prefs.get('ai_compute_type', 'Auto')
        self.dropdown_compute.setText(saved_compute if saved_compute in _compute_items else 'Auto')
        self._add_row(form_ai, self.txt("lbl_compute_type"), self.dropdown_compute, 'Auto', self.dropdown_compute.setValue)

        l_ai.addSpacing(14)

        # Initial prompt label + QTextEdit
        lbl_prompt = QLabel(self.txt("lbl_initial_prompt"))
        lbl_prompt.setStyleSheet(f"color: {config.NOTE_COL}; font-size: 9pt; background: transparent;")
        l_ai.addWidget(lbl_prompt)
        l_ai.addSpacing(4)

        self.textedit_prompt = WrappingPlaceholderTextEdit()
        self.textedit_prompt.setMaximumHeight(80)
        saved_prompt = prefs.get('ai_initial_prompt', '').strip()
        
        # Resolve ISO code from display name in prefs
        current_lang_display = prefs.get('lang', 'Auto')
        current_lang_iso = "Auto"
        for iso, display in config.SUPPORTED_LANGUAGES.items():
            if display == current_lang_display:
                current_lang_iso = iso
                break
        
        auto_prompt = config.get_whisper_prompt_for_lang(current_lang_iso)
        self.textedit_prompt.setPlaceholderText(auto_prompt)
        
        if saved_prompt:
            self.textedit_prompt.setPlainText(saved_prompt)
        else:
            self.textedit_prompt.setPlainText("")
        self.textedit_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 6px 8px;
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
            }}
        """)
        l_ai.addWidget(self.textedit_prompt)

        # ── Advanced Whisper Parameters ─────────────────────────
        sep_whisper = QFrame()
        sep_whisper.setFrameShape(QFrame.Shape.HLine)
        sep_whisper.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
        l_ai.addSpacing(14)
        l_ai.addWidget(sep_whisper)
        l_ai.addSpacing(10)
        self._advanced_widgets.append(sep_whisper)

        form_whisper = QFormLayout()
        form_whisper.setSpacing(14)
        form_whisper.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        l_ai.addLayout(form_whisper)

        self.chk_vad_filter = ToggleSwitch(parent=page_ai)
        self.chk_vad_filter.setChecked(bool(prefs.get('ai_vad_filter', False)), animated=False)
        w_vad = QWidget(page_ai); l_vad = QHBoxLayout(w_vad); l_vad.setContentsMargins(0, 0, 0, 0); l_vad.addStretch(); l_vad.addWidget(self.chk_vad_filter)
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_vad_filter"), w_vad, False, lambda v: self.chk_vad_filter.setChecked(v, animated=False)))

        self.chk_condition_prev = ToggleSwitch(parent=page_ai)
        self.chk_condition_prev.setChecked(bool(prefs.get('ai_condition_on_prev', False)), animated=False)
        w_cond = QWidget(page_ai); l_cond = QHBoxLayout(w_cond); l_cond.setContentsMargins(0, 0, 0, 0); l_cond.addStretch(); l_cond.addWidget(self.chk_condition_prev)
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_condition_prev"), w_cond, False, lambda v: self.chk_condition_prev.setChecked(v, animated=False)))

        self.spin_beam_size = QSpinBox(page_ai)
        self.spin_beam_size.setRange(1, 10)
        def_beam = config.DEFAULT_SETTINGS.get('ai_beam_size', 1)
        self.spin_beam_size.setValue(int(prefs.get('ai_beam_size', def_beam)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_beam_size"), self.spin_beam_size, def_beam, self.spin_beam_size.setValue))

        self.spin_temperature = QDoubleSpinBox(page_ai)
        self.spin_temperature.setRange(0.0, 1.0)
        self.spin_temperature.setSingleStep(0.1)
        self.spin_temperature.setDecimals(2)
        def_temp = config.DEFAULT_SETTINGS.get('ai_temperature', 0.0)
        self.spin_temperature.setValue(float(prefs.get('ai_temperature', def_temp)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_temperature"), self.spin_temperature, def_temp, self.spin_temperature.setValue))

        self.spin_logprob = QDoubleSpinBox(page_ai)
        self.spin_logprob.setRange(-3.0, 0.0)
        self.spin_logprob.setSingleStep(0.1)
        self.spin_logprob.setDecimals(2)
        def_logprob = config.DEFAULT_SETTINGS.get('ai_logprob_threshold', -0.8)
        self.spin_logprob.setValue(float(prefs.get('ai_logprob_threshold', def_logprob)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_logprob"), self.spin_logprob, def_logprob, self.spin_logprob.setValue))

        self.spin_no_speech = QDoubleSpinBox(page_ai)
        self.spin_no_speech.setRange(0.0, 1.0)
        self.spin_no_speech.setSingleStep(0.1)
        self.spin_no_speech.setDecimals(2)
        def_nospeech = config.DEFAULT_SETTINGS.get('ai_no_speech_threshold', 0.7)
        self.spin_no_speech.setValue(float(prefs.get('ai_no_speech_threshold', def_nospeech)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_no_speech"), self.spin_no_speech, def_nospeech, self.spin_no_speech.setValue))

        self.spin_patience = QDoubleSpinBox(page_ai)
        self.spin_patience.setRange(0.0, 10.0)
        self.spin_patience.setSingleStep(0.1)
        self.spin_patience.setDecimals(2)
        def_patience = config.DEFAULT_SETTINGS.get('ai_patience', 1.0)
        self.spin_patience.setValue(float(prefs.get('ai_patience', def_patience)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_patience"), self.spin_patience, def_patience, self.spin_patience.setValue))

        self.spin_compression = QDoubleSpinBox(page_ai)
        self.spin_compression.setRange(0.0, 100.0)
        self.spin_compression.setSingleStep(0.1)
        self.spin_compression.setDecimals(2)
        def_comp = config.DEFAULT_SETTINGS.get('ai_compression_ratio_threshold', 2.4)
        self.spin_compression.setValue(float(prefs.get('ai_compression_ratio_threshold', def_comp)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_compression_ratio"), self.spin_compression, def_comp, self.spin_compression.setValue))

        self.spin_no_repeat = QSpinBox(page_ai)
        self.spin_no_repeat.setRange(0, 100)
        def_no_rep = config.DEFAULT_SETTINGS.get('ai_no_repeat_ngram_size', 0)
        self.spin_no_repeat.setValue(int(prefs.get('ai_no_repeat_ngram_size', def_no_rep)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_no_repeat_ngram"), self.spin_no_repeat, def_no_rep, self.spin_no_repeat.setValue))



        
        self.spin_length_penalty = QDoubleSpinBox(page_ai)
        self.spin_length_penalty.setRange(0.0, 10.0)
        self.spin_length_penalty.setSingleStep(0.1)
        self.spin_length_penalty.setDecimals(2)
        self.spin_length_penalty.setValue(float(prefs.get('ai_length_penalty', 1.0)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_length_penalty") if self.txt("lbl_length_penalty") != "lbl_length_penalty" else "Length Penalty", self.spin_length_penalty, 1.0, self.spin_length_penalty.setValue))

        self.spin_repetition_penalty = QDoubleSpinBox(page_ai)
        self.spin_repetition_penalty.setRange(1.0, 10.0)
        self.spin_repetition_penalty.setSingleStep(0.1)
        self.spin_repetition_penalty.setDecimals(2)
        self.spin_repetition_penalty.setValue(float(prefs.get('ai_repetition_penalty', 1.0)))
        self._advanced_widgets.extend(self._add_row(form_whisper, self.txt("lbl_repetition_penalty") if self.txt("lbl_repetition_penalty") != "lbl_repetition_penalty" else "Repetition Penalty", self.spin_repetition_penalty, 1.0, self.spin_repetition_penalty.setValue))
        
        l_ai.addStretch()




        # ─────────────────────────────────────────────────────────────────
        # ─────────────────────────────────────────────────────────────────

        # ─────────────────────────────────────────────────────────────────

        return page_ai

    def _build_page_telemetry(self, prefs):
        # PAGE 8 — TELEMETRY
        # ─────────────────────────────────────────────────────────────────
        page_telem = QWidget()
        page_telem.setStyleSheet("background: transparent;")
        l_telem = QVBoxLayout(page_telem)
        l_telem.setContentsMargins(24, 20, 24, 16)
        l_telem.setSpacing(12)

        # Info label
        lbl_telem_info = QLabel(self.txt("msg_telemetry_settings"))
        lbl_telem_info.setWordWrap(True)
        lbl_telem_info.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        l_telem.addWidget(lbl_telem_info)

        form_telem = QFormLayout()
        form_telem.setSpacing(14)
        form_telem.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        user_data = getattr(self.engine.os_doc, 'user_data', {})

        self.chk_telemetry_opt_in = ToggleSwitch()
        self.chk_telemetry_opt_in.setChecked(bool(user_data.get('telemetry_opt_in', False)), animated=False)
        w1 = QWidget()
        l1 = QHBoxLayout(w1)
        l1.setContentsMargins(0, 0, 0, 0)
        l1.addStretch()
        l1.addWidget(self.chk_telemetry_opt_in)
        self._add_row(form_telem, self.txt("chk_telemetry_opt_in"), w1,
                 False, lambda v: self.chk_telemetry_opt_in.setChecked(v, animated=False))

        self.chk_telemetry_geo = ToggleSwitch()
        self.chk_telemetry_geo.setChecked(bool(user_data.get('telemetry_geo', True)), animated=False)
        w2 = QWidget()
        l2 = QHBoxLayout(w2)
        l2.setContentsMargins(0, 0, 0, 0)
        l2.addStretch()
        l2.addWidget(self.chk_telemetry_geo)
        self._add_row(form_telem, self.txt("chk_telemetry_geo"), w2,
                 True, lambda v: self.chk_telemetry_geo.setChecked(v, animated=False))

        l_telem.addLayout(form_telem)
        l_telem.addStretch()

        # ── Project links — pinned at the bottom ───────────────────────────
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        _BTN_LINK_SS = """
            QPushButton {
                color: #1a7a45;
                background: transparent;
                border: none;
                text-align: left;
                padding: 0px;
                font-size: 9pt;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #2dcc70;
            }
        """

        # Buy Me a Coffee link — description above, URL as button
        lbl_coffee_desc = QLabel(self.txt("link_coffee_desc"))
        lbl_coffee_desc.setStyleSheet("color: #888888; font-size: 10pt; background: transparent;")
        l_telem.addWidget(lbl_coffee_desc)

        btn_coffee = QPushButton("buymeacoffee.com/badwords")
        btn_coffee.setFlat(True)
        btn_coffee.setCursor(Qt.PointingHandCursor)
        btn_coffee.setStyleSheet(_BTN_LINK_SS)
        btn_coffee.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://buymeacoffee.com/badwords")))
        l_telem.addWidget(btn_coffee)

        l_telem.addSpacing(10)

        # GitHub repo link — description above, URL as button
        lbl_repo_desc = QLabel(self.txt("link_repo_desc"))
        lbl_repo_desc.setStyleSheet("color: #888888; font-size: 10pt; background: transparent;")
        l_telem.addWidget(lbl_repo_desc)

        btn_repo = QPushButton("github.com/veritus-git/BadWords")
        btn_repo.setFlat(True)
        btn_repo.setCursor(Qt.PointingHandCursor)
        btn_repo.setStyleSheet(_BTN_LINK_SS)
        btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/veritus-git/BadWords")))
        l_telem.addWidget(btn_repo)

        l_telem.addSpacing(12)



        # ─────────────────────────────────────────────────────────────────

        return page_telem

    def _build_page_support(self, prefs):
        # PAGE 9 — SUPPORT
        # ─────────────────────────────────────────────────────────────────
        page_support = QWidget()
        page_support.setStyleSheet("background: transparent;")
        l_support = QVBoxLayout(page_support)
        l_support.setContentsMargins(24, 20, 24, 16)
        l_support.setSpacing(12)

        lbl_support_info = QLabel(self.txt("msg_support_info"))
        lbl_support_info.setWordWrap(True)
        lbl_support_info.setStyleSheet("color: #AAAAAA; font-size: 9pt;")
        l_support.addWidget(lbl_support_info)

        # Logs location
        import os
        log_file_path = getattr(self.engine.os_doc, 'log_file', '')
        if not log_file_path:
            log_file_path = os.path.join(getattr(self.engine.os_doc, 'install_dir', ''), 'badwords_debug.log')
        log_dir = os.path.dirname(log_file_path) if log_file_path else ''
            
        w_logs = QWidget()
        l_logs = QHBoxLayout(w_logs)
        l_logs.setContentsMargins(0, 0, 0, 0)
        l_logs.setSpacing(8)
        lbl_logs = QLabel(self.txt("lbl_logs_path"))
        lbl_logs.setStyleSheet("color: #CCCCCC; font-size: 10pt;")
        
        w_path = QWidget()
        w_path.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333; border-radius: 3px;")
        l_path = QHBoxLayout(w_path)
        l_path.setContentsMargins(4, 0, 0, 0)
        l_path.setSpacing(2)
        
        val_logs = QLineEdit(str(log_file_path))
        val_logs.setReadOnly(True)
        val_logs.setStyleSheet("color: #AAAAAA; font-family: monospace; background: transparent; border: none;")
        val_logs.setCursorPosition(0)
        
        btn_copy_logs = QPushButton("")
        import PySide6.QtGui as qg
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        btn_copy_logs.setIcon(qg.QIcon(os.path.join(_src_dir, "layout", "copy.png")))
        btn_copy_logs.setToolTip(self.txt("btn_copy_path"))
        btn_copy_logs.setStyleSheet("background: transparent; border: none; padding: 4px;")
        btn_copy_logs.setCursor(Qt.PointingHandCursor)
        def _copy_path():
            import PySide6.QtGui as qg
            qg.QGuiApplication.clipboard().setText(str(log_file_path))
        btn_copy_logs.clicked.connect(_copy_path)
        
        l_path.addWidget(val_logs, stretch=1)
        l_path.addWidget(btn_copy_logs)
        
        btn_logs = QPushButton(self.txt("btn_open_logs_dir"))
        btn_logs.setObjectName("btn_ghost_sm")
        btn_logs.setStyleSheet("padding: 4px 12px;")
        btn_logs.setCursor(Qt.PointingHandCursor)
        def _open_logs():
            import os
            try:
                if self.engine.os_doc.is_win:
                    os.startfile(log_dir)
                elif getattr(self.engine.os_doc, 'is_mac', False):
                    import subprocess
                    subprocess.Popen(['open', log_dir])
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', log_dir])
            except: pass
        btn_logs.clicked.connect(_open_logs)
        l_logs.addWidget(lbl_logs)
        l_logs.addWidget(w_path, stretch=1)
        l_logs.addWidget(btn_logs)
        l_support.addWidget(w_logs)

        # Separator
        sep_supp = QFrame()
        sep_supp.setFrameShape(QFrame.HLine)
        sep_supp.setStyleSheet("background-color: #222; max-height: 1px; border: none;")
        l_support.addWidget(sep_supp)
        l_support.addSpacing(6)

        l_inputs = QVBoxLayout()
        l_inputs.setSpacing(14)
        
        self.input_support_email = QLineEdit()
        self.input_support_email.setPlaceholderText(self.txt("ph_support_email"))
        l_inputs.addWidget(self.input_support_email)
        
        self.input_support_title = QLineEdit()
        self.input_support_title.setPlaceholderText(self.txt("lbl_support_title"))
        l_inputs.addWidget(self.input_support_title)

        from PySide6.QtWidgets import QTextEdit
        self.input_support_body = QTextEdit()
        self.input_support_body.setPlaceholderText(self.txt("lbl_support_body"))
        self.input_support_body.setMinimumHeight(150)
        l_inputs.addWidget(self.input_support_body)

        # Attachments list (above the bottom buttons)
        self.w_attachments_list = QWidget()
        self.l_attachments_list = QVBoxLayout(self.w_attachments_list)
        self.l_attachments_list.setContentsMargins(0, 0, 0, 0)
        self.l_attachments_list.setSpacing(4)
        l_inputs.addWidget(self.w_attachments_list)

        self.w_attachments_list.hide()

        self.support_attachments = []
        def _render_attachments():
            while self.l_attachments_list.count():
                child = self.l_attachments_list.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                    
            if not self.support_attachments:
                self.w_attachments_list.hide()
            else:
                self.w_attachments_list.show()
                for p in self.support_attachments:
                    w_row = QWidget()
                    w_row.setStyleSheet("background: #1a1a1a; border: 1px solid #333; border-radius: 3px;")
                    l_row = QHBoxLayout(w_row)
                    l_row.setContentsMargins(6, 2, 2, 2)
                    
                    lbl_name = QLabel(p)
                    lbl_name.setStyleSheet("color: #aaa; border: none; font-size: 9pt;")
                    
                    btn_del = QPushButton("✕")
                    btn_del.setObjectName("btn_ghost_sm")
                    btn_del.setStyleSheet("color: #e74c3c; border: none; font-weight: bold; font-size: 11pt; padding: 2px;")
                    btn_del.setCursor(Qt.PointingHandCursor)
                    btn_del.setFixedSize(24, 24)
                    
                    def _del(checked=False, path=p):
                        if path in self.support_attachments:
                            self.support_attachments.remove(path)
                            _render_attachments()
                    btn_del.clicked.connect(_del)
                    
                    l_row.addWidget(lbl_name, stretch=1)
                    l_row.addWidget(btn_del)
                    self.l_attachments_list.addWidget(w_row)

        l_support.addLayout(l_inputs)

        # Bottom row: Attach | Stretch | Send
        w_send = QWidget()
        l_send = QHBoxLayout(w_send)
        l_send.setContentsMargins(0, 0, 0, 0)
        
        btn_attach = QPushButton(self.txt("btn_attach_screenshots"))
        btn_attach.setCursor(Qt.PointingHandCursor)
        btn_attach.setStyleSheet(f"background-color: #2b2b2b; color: #ddd; padding: 6px 14px; border: 1px solid #444; border-radius: 4px;")
        
        def _attach():
            from PySide6.QtWidgets import QFileDialog
            files, _ = QFileDialog.getOpenFileNames(self, self.txt("btn_attach_screenshots"), "", "Images (*.png *.jpg *.jpeg)")
            if files:
                btn_attach.setText("Attached!")
                btn_attach.setStyleSheet("background-color: #3b3b3b; color: #fff; padding: 6px 14px; border: 1px solid #555; border-radius: 4px;")
                import PySide6.QtCore as qc
                qc.QTimer.singleShot(1500, lambda: btn_attach.setText(self.txt("btn_attach_screenshots")))
                qc.QTimer.singleShot(1500, lambda: btn_attach.setStyleSheet("background-color: #2b2b2b; color: #ddd; padding: 6px 14px; border: 1px solid #444; border-radius: 4px;"))
                
                for f in files:
                    if f not in self.support_attachments:
                        self.support_attachments.append(f)
                _render_attachments()
        btn_attach.clicked.connect(_attach)
        l_send.addWidget(btn_attach)
        
        l_send.addStretch()
        
        btn_send = QPushButton(self.txt("btn_send_report"))
        btn_send.setCursor(Qt.PointingHandCursor)
        btn_send.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; padding: 6px 16px; border: none; border-radius: 4px; font-weight: bold;")
        
        def _send_report():
            title = self.input_support_title.text().strip()
            body = self.input_support_body.toPlainText().strip()
            email = self.input_support_email.text().strip()
            if not title or not body:
                return

            btn_send.setEnabled(False)
            btn_send.setText("...")

            attachments = list(self.support_attachments)

            class SendSignals(QObject):
                finished = Signal(bool, str)
            signals = SendSignals(self)

            def _worker():
                import os, zipfile, tempfile, requests
                from osdoc import log_info, log_error
                tmp_logs = ""
                opened_files = []
                try:
                    fd, tmp_logs = tempfile.mkstemp(suffix='.zip', prefix='bw_logs_')
                    os.close(fd)
                    with zipfile.ZipFile(tmp_logs, 'w', zipfile.ZIP_DEFLATED) as zf:
                        l_file = getattr(self.engine.os_doc, 'log_file', '')
                        if l_file and os.path.exists(l_file):
                            zf.write(l_file, os.path.basename(l_file))
                        inst_dir = getattr(self.engine.os_doc, 'install_dir', '')
                        if inst_dir:
                            for cfile in ['user.json', 'settings.json', 'pref.json']:
                                p = os.path.join(inst_dir, cfile)
                                if os.path.exists(p):
                                    zf.write(p, cfile)
                        from PySide6.QtGui import QImage
                        for i, p in enumerate(attachments):
                            if os.path.exists(p):
                                img = QImage(p)
                                if not img.isNull():
                                    if img.width() > 1920 or img.height() > 1080:
                                        img = img.scaled(1920, 1080, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                    fd_img, tmp_img = tempfile.mkstemp(suffix='.jpg')
                                    os.close(fd_img)
                                    img.save(tmp_img, "JPG", 70)
                                    zf.write(tmp_img, f"screenshot_{i+1}.jpg")
                                    try:
                                        os.remove(tmp_img)
                                    except:
                                        pass
                                else:
                                    zf.write(p, f"screenshot_{i+1}{os.path.splitext(p)[1]}")
                    
                    files_payload = []
                    import builtins
                    f_logs = builtins.open(tmp_logs, 'rb')
                    opened_files.append(f_logs)
                    files_payload.append(('file', ('logs.zip', f_logs, 'application/zip')))

                    data_payload = {
                        'title': title,
                        'body': body,
                        'email': email,
                        'version': getattr(config, 'VERSION', 'Unknown'),
                        'content': f"@here\n>>> **Wersja:** {getattr(config, 'VERSION', 'Unknown')}\n**Email:** {email if email else 'Brak'}\n**Tytuł:** {title}\n\n**Treść:**\n{body}"
                    }

                    webhook_url = getattr(config, 'SUPPORT_WEBHOOK_URL', '')
                    if not webhook_url:
                        import time
                        time.sleep(1)
                        log_info("Webhook URL not defined in config.py, skipping actual HTTP POST.")
                        return True, ""

                    resp = requests.post(webhook_url, data=data_payload, files=files_payload, timeout=30)
                    success = resp.status_code in (200, 201, 202, 204)
                    if not success:
                        log_error(f"Support report send failed: {resp.status_code} {resp.text}")
                    return success, resp.text
                except Exception as e:
                    from osdoc import log_error
                    log_error(f"Support report exception: {e}")
                    return False, str(e)
                finally:
                    for f in opened_files:
                        try: f.close()
                        except: pass
                    if tmp_logs and os.path.exists(tmp_logs):
                        try: os.remove(tmp_logs)
                        except: pass

            def _thread_target():
                success, msg = _worker()
                signals.finished.emit(success, msg)

            def _on_finished(success, msg):
                btn_send.setEnabled(True)
                if success:
                    btn_send.setText(self.txt("msg_success"))
                    btn_send.setStyleSheet(f"background-color: #1a7a3e; color: white; padding: 6px 16px; border: none; border-radius: 4px; font-weight: bold;")
                    import PySide6.QtCore as qc
                    qc.QTimer.singleShot(2000, lambda: btn_send.setText(self.txt("btn_send_report")))
                    qc.QTimer.singleShot(2000, lambda: btn_send.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; padding: 6px 16px; border: none; border-radius: 4px; font-weight: bold;"))
                    
                    self.input_support_title.clear()
                    self.input_support_body.clear()
                    self.input_support_email.clear()
                    self.support_attachments.clear()
                    _render_attachments()
                else:
                    btn_send.setText(self.txt("btn_send_report"))
                    CustomMsgBox(self, self.txt("tab_support"), f"Error sending report: {msg[:100]}", self.txt("btn_ok")).exec()

            signals.finished.connect(_on_finished)
            import threading
            threading.Thread(target=_thread_target, daemon=True).start()

        btn_send.clicked.connect(_send_report)
        l_send.addWidget(btn_send)
        l_support.addWidget(w_send)

        l_support.addStretch()

        # FIX: Capture the exact UI state right after full construction
        # This prevents false-positive unsaved changes warnings when disk JSON
        # lacks keys that are correctly populated with defaults by the UI.
        self._initial_state = self._get_current_state_dict()


        return page_support

    def _restore_all_defaults(self):
        msg_box = CustomMsgBox(
            self, 
            self.txt('msg_restore_title'), 
            self.txt('msg_restore_desc'), 
            self.txt('btn_yes'), 
            self.txt('btn_no')
        )
        if msg_box.exec() == QDialog.Accepted:
            import config
            old_prefs = self.engine.load_preferences() or {}
            # Build a full default state — start with DEFAULT_SETTINGS then keep
            # lang and settings_view_mode so the UI doesn't switch language/mode.
            default_state = config.DEFAULT_SETTINGS.copy()
            default_state['gui_lang'] = old_prefs.get('gui_lang', 'en')
            default_state['settings_view_mode'] = old_prefs.get('settings_view_mode', 'basic')
            # Save to disk first so subsequent load_preferences() returns defaults
            self.engine.save_preferences(default_state)
            self.initial_prefs = self.engine.load_preferences() or {}
            # Reset all visible widgets to their default values
            self._restore_state_dict(default_state)
            # Clear custom markers
            self.current_custom_markers = []
            CustomMsgBox(self, self.txt('msg_title_settings'), self.txt('msg_restart_required'), self.txt('btn_ok')).exec()
            try:
                self._refresh_markers_list()
            except Exception:
                pass

    # ── Custom Markers helpers ─────────────────────────────────────────────

    def _refresh_markers_list(self):
        """Rebuild the custom marker list widget with inline Edit/Delete buttons."""
        # Clear existing rows (keep the trailing stretch)
        layout = self._markers_layout
        while layout.count() > 1:  # keep the stretch at the end
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_ss = f"""
            QWidget#marker_row {{
                background-color: #1e1e1e;
                border-bottom: 1px solid #2a2a2a;
            }}
            QWidget#marker_row:hover {{
                background-color: #252525;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: {config.UI_FONT_NAME};
                font-size: 10pt;
                background: transparent;
            }}
            QPushButton {{
                background-color: #2d2d2d;
                color: #aaaaaa;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 9pt;
                min-height: 22px;
            }}
            QPushButton:hover {{
                background-color: #383838;
                color: #ffffff;
            }}
            QPushButton#btn_del:hover {{
                background-color: #7a2020;
                border-color: #ed4245;
                color: #ed4245;
            }}
        """

        for idx, m in enumerate(self.current_custom_markers):
            name  = m.get('name', '?')
            color = m.get('color', '')
            hex_col = config.RESOLVE_COLORS_HEX.get(color, '#FFFFFF')

            row_widget = MarkerRowWidget(m, idx)
            row_widget.setObjectName("marker_row")
            row_widget.setStyleSheet(row_ss)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)
            row_layout.setSpacing(8)

            # Color dot indicator
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {hex_col}; font-size: 14pt; background: transparent;")
            dot.setFixedWidth(20)
            row_layout.addWidget(dot)

            # Name + color label
            lbl_name = QLabel(f"{name}")
            lbl_name.setStyleSheet(f"color: {hex_col}; font-weight: bold; background: transparent;")
            row_layout.addWidget(lbl_name, 1)

            lbl_color = QLabel(f"[{self.txt(f'resolve_color_{color.lower()}')}]")
            lbl_color.setStyleSheet(f"color: #666666; font-size: 9pt; background: transparent;")
            row_layout.addWidget(lbl_color)

            # Edit button
            def make_edit(i):
                return lambda checked=False: self._on_edit_marker(i)
            btn_edit = QPushButton(self.txt("btn_edit_marker"))
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(make_edit(idx))
            if color.lower() in ["green", "blue"]:
                btn_edit.setEnabled(False)
                btn_edit.setToolTip(self.txt("tooltip_disabled_davinci_colors"))
                lbl_name.setStyleSheet("color: #666666; font-weight: bold; background: transparent;")
                dot.setStyleSheet("color: #666666; font-size: 14pt; background: transparent;")
            row_layout.addWidget(btn_edit)

            # Delete button
            def make_del(i):
                return lambda checked=False: self._on_remove_marker_inline(i)
            btn_del = QPushButton("✕")
            btn_del.setObjectName("btn_del")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.setFixedWidth(28)
            btn_del.clicked.connect(make_del(idx))
            row_layout.addWidget(btn_del)

            # Insert before stretch
            layout.insertWidget(layout.count() - 1, row_widget)

    def _on_markers_reordered(self, source_idx, target_idx):
        if source_idx == target_idx:
            return
        m = self.current_custom_markers.pop(source_idx)
        # if source_idx < target_idx, target_idx shifted down by 1 due to pop
        if source_idx < target_idx:
            target_idx -= 1
        self.current_custom_markers.insert(target_idx, m)
        self._refresh_markers_list()
        self._save_markers_and_refresh_main()

    def _save_markers_and_refresh_main(self):
        """
        Persist custom_markers immediately (bypassing the Apply button),
        then rebuild the main window's marker sidebar and dynamic shortcuts.
        Markers work like a live database, not a pending settings value.
        """
        prefs = self.engine.load_preferences() or {}
        prefs['custom_markers'] = list(self.current_custom_markers)
        self.engine.save_preferences(prefs)

        # Walk the widget parent hierarchy to find BadWordsGUI
        # (self.parent() alone is not reliable when SettingsDialog is modal)
        w = self
        main_win = None
        while w is not None:
            try:
                if hasattr(w, '_build_marker_radio_buttons') \
                        and hasattr(w, '_apply_dynamic_shortcuts'):
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
        lang = self.engine.load_preferences().get('gui_lang', 'en')
        dlg = MarkerDialog(self, lang, "btn_add_marker")
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            self.current_custom_markers.append({
                "name":  dlg.result_name,
                "color": dlg.result_color,
            })
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()

    def _on_edit_marker(self, idx: int):
        if not (0 <= idx < len(self.current_custom_markers)):
            return
        m = self.current_custom_markers[idx]
        lang = self.engine.load_preferences().get('gui_lang', 'en')
        dlg = MarkerDialog(self, lang, "btn_edit_marker",
                           prefill_name=m.get('name', ''),
                           prefill_color=m.get('color', ''))
        if dlg.exec() == QDialog.Accepted and dlg.result_name:
            self.current_custom_markers[idx] = {
                "name":  dlg.result_name,
                "color": dlg.result_color,
            }
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()

    def _on_remove_marker_inline(self, idx: int):
        if 0 <= idx < len(self.current_custom_markers):
            self.current_custom_markers.pop(idx)
            self._refresh_markers_list()
            self._refresh_custom_marker_shortcuts()
            self._save_markers_and_refresh_main()


    def _on_remove_marker(self):
        """Legacy method — kept for safety but no longer wired to any button."""
        pass

    def _on_export_markers(self):
        """Export custom markers to a JSON file."""
        from PySide6.QtWidgets import QFileDialog
        import json, os

        if not self.current_custom_markers:
            lang = self.engine.load_preferences().get('gui_lang', 'en')
            CustomMsgBox(
                self,
                _txt(lang, 'btn_export_markers'),
                _txt(lang, 'msg_no_markers_to_export'),
                _txt(lang, 'btn_ok'),
            ).exec()
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.txt('btn_export_markers'),
            os.path.expanduser('~/badwords_markers.json'),
            'JSON Files (*.json)',
        )
        if not path:
            return

        data = {
            'version': 1,
            'app': 'BadWords',
            'custom_markers': list(self.current_custom_markers),
        }
        try:
            with open(path, 'w', encoding='utf-8') as f:
                import json
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            lang = self.engine.load_preferences().get('gui_lang', 'en')
            CustomMsgBox(self, 'Error', str(e), _txt(lang, 'btn_ok')).exec()

    def _on_import_markers(self):
        """Import custom markers from a JSON file (replaces current list)."""
        from PySide6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getOpenFileName(
            self,
            self.txt('btn_import_markers'),
            '',
            'JSON Files (*.json)',
        )
        if not path:
            return

        lang = self.engine.load_preferences().get('gui_lang', 'en')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            CustomMsgBox(self, 'Error', str(e), _txt(lang, 'btn_ok')).exec()
            return

        # Accept both {"custom_markers": [...]} and plain lists
        if isinstance(data, list):
            imported = data
        elif isinstance(data, dict):
            imported = data.get('custom_markers', [])
        else:
            CustomMsgBox(
                self, 'Error', _txt(lang, 'msg_import_invalid_format'), _txt(lang, 'btn_ok')
            ).exec()
            return

        # Validate: each entry must have at least a non-empty 'name'
        valid = []
        for entry in imported:
            if isinstance(entry, dict) and entry.get('name', '').strip():
                valid.append({
                    'name':  entry['name'].strip(),
                    'color': entry.get('color', 'Blue'),
                })

        if not valid:
            CustomMsgBox(
                self, 'Error', _txt(lang, 'msg_import_no_valid_markers'), _txt(lang, 'btn_ok')
            ).exec()
            return

        self.current_custom_markers = valid
        self._refresh_markers_list()
        self._refresh_custom_marker_shortcuts()
        self._save_markers_and_refresh_main()


    def _refresh_custom_marker_shortcuts(self):
        """
        Rebuilds the custom-marker shortcut rows in the unified Shortcuts form.
        Uses insertRow(pos) / removeRow(pos) on the single QFormLayout so all
        rows always have identical 14px spacing — no separate widget needed.
        """
        form       = getattr(self, '_custom_sc_unified', None)
        make_fn    = getattr(self, '_make_shortcut_widgets_fn', None)
        check_fn   = getattr(self, '_check_shortcut_conflicts_fn', None)
        insert_pos = getattr(self, '_custom_sc_insert_pos', None)

        if form is None or make_fn is None or check_fn is None or insert_pos is None:
            return

        # ── Remove previous custom rows ─────────────────────────────────────
        old_count = len(getattr(self, 'custom_marker_shortcut_inputs', {}))
        for _ in range(old_count):
            # Always remove at the same index; rows shift up after each removal
            try:
                form.removeRow(insert_pos)
            except Exception:
                break

        self.custom_marker_shortcut_inputs = {}

        # ── Insert new custom rows at insert_pos ────────────────────────────
        prefs = self.engine.load_preferences() or {}
        saved_shortcuts = prefs.get('shortcuts', {})
        markers = getattr(self, 'current_custom_markers', [])

        for i, m in enumerate(markers):
            name = m.get('name', '')
            if not name:
                continue
            s_key = f'custom_marker_{name}'

            fmt = self.txt('shortcut_custom_marker_fmt')
            label_text = fmt.format(name=name) if fmt != 'shortcut_custom_marker_fmt' \
                         else f'Switch to "{name}" Marker'

            current_seq = saved_shortcuts.get(s_key, '')
            widget = ShortcutCaptureButton(str(current_seq), display_only=False)
            widget.sequence_changed.connect(lambda _seq, _w=widget: check_fn())

            def make_setter(w, check):
                def _setter(v):
                    w.set_sequence(str(v))
                    check()
                return _setter

            lbl, container = make_fn(label_text, widget, '',
                                     make_setter(widget, check_fn),
                                     is_display=False)
            form.insertRow(insert_pos + i, lbl, container)
            self.custom_marker_shortcut_inputs[s_key] = widget

        check_fn()


    def _update_preview(self):

        ff = self.combo_font.currentText()
        fs = self.spin_fsize.value()
        lh = self.spin_lheight.value()
        self.lbl_preview.setStyleSheet(f"""
            background-color: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: {config.FG_COLOR};
            font-family: "{ff}";
            font-size: {fs}pt;
            padding: 12px 14px;
        """)
        preview_text = self.txt("lbl_font_preview")
        self.lbl_preview.setPlainText(preview_text)
        from PySide6.QtGui import QTextCursor, QTextBlockFormat
        cursor = self.lbl_preview.textCursor()
        cursor.select(QTextCursor.Document)
        fmt = QTextBlockFormat()
        fmt.setLineHeight(float(lh), 4)
        cursor.setBlockFormat(fmt)
        cursor.setPosition(0)
        self.lbl_preview.setTextCursor(cursor)
        self.lbl_preview.verticalScrollBar().setValue(0)

    # ── Export / Import ───────────────────────────────────────────────────

    def _on_export_settings(self):
        import shutil
        from PySide6.QtWidgets import QFileDialog
        dest, _ = QFileDialog.getSaveFileName(
            self, self.txt("btn_export_settings"), "badwords_settings.json",
            "JSON files (*.json)"
        )
        if dest:
            try:
                shutil.copy2(self.engine.os_doc.settings_file, dest)
            except Exception as e:
                from osdoc import log_error
                log_error(f"Export settings failed: {e}")

    def _on_import_settings(self):
        import shutil
        from PySide6.QtWidgets import QFileDialog
        src, _ = QFileDialog.getOpenFileName(
            self, self.txt("btn_import_settings"), "",
            "JSON files (*.json)"
        )
        if not src:
            return
        try:
            shutil.copy2(src, self.engine.os_doc.settings_file)
            self.engine.os_doc.settings = self.engine.os_doc.load_settings()
        except Exception as e:
            from osdoc import log_error
            log_error(f"Import settings failed: {e}")
            return

        target = config.TRANS.get('en', config.TRANS['en'])
        CustomMsgBox(
            self,
            target.get('msg_title_language_changed', 'Restart Required'),
            target.get('msg_restart_lang', 'Settings imported. Please restart BadWords to apply all changes.'),
            target.get('btn_ok', 'OK')
        ).exec()
        self.reject()


    # ── Smart Apply ───────────────────────────────────────────────────────

    def _safe_get(self, attr_name, default_val, method_name="value"):
        """Safely extracts a value from a widget, avoiding PySide6 dead C++ object errors."""
        try:
            widget = getattr(self, attr_name)
            return getattr(widget, method_name)()
        except (RuntimeError, AttributeError):
            return default_val

    def _get_current_state_dict(self):
        old_prefs = self.engine.load_preferences() or {}
        is_basic = old_prefs.get('settings_view_mode', 'basic') == 'basic'
        
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
        view_mode = 'segmented' if view_mode_val == self.txt("opt_segmented_blocks") else ('continuous' if view_mode_val else old_prefs.get('view_mode', 'segmented'))

        try:
            shortcuts_dict = {k: v.get_sequence() for k, v in self.shortcut_inputs.items()}
            # Merge in custom marker shortcuts
            for k, v in getattr(self, 'custom_marker_shortcut_inputs', {}).items():
                shortcuts_dict[k] = v.get_sequence()
        except (RuntimeError, AttributeError):
            shortcuts_dict = old_prefs.get('shortcuts', {})

        state = {
            'gui_lang':           lang_code,
            'settings_view_mode': old_prefs.get('settings_view_mode', 'basic'),
            'app_icon':           icon_val,
            'shortcuts':          shortcuts_dict,
            'custom_markers':     getattr(self, 'current_custom_markers', old_prefs.get('custom_markers', [])),
            'telemetry_opt_in':   (self._safe_get('chk_telemetry_opt_in', old_prefs.get('telemetry_opt_in'), 'isChecked') if old_prefs.get('telemetry_opt_in') is not None or self._safe_get('chk_telemetry_opt_in', False, 'isChecked') else None),
            'telemetry_geo':      self._safe_get('chk_telemetry_geo', old_prefs.get('telemetry_geo', True), 'isChecked'),
            'view_mode':          view_mode,
            'editor_font_family': self._safe_get('combo_font', old_prefs.get('editor_font_family', 'Segoe UI'), 'currentText'),
            'editor_font_size':   self._safe_get('spin_fsize', old_prefs.get('editor_font_size', 12), 'value'),
            'editor_line_height': self._safe_get('spin_lheight', old_prefs.get('editor_line_height', 7), 'value'),
            'sync_davinci_chapter': self._safe_get('chk_sync_davinci', old_prefs.get('sync_davinci_chapter', True), 'isChecked'),
            'timestamp_precise':    self._safe_get('tgl_timestamp_precise', old_prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'isChecked'),
            'auto_check_updates':      self._safe_get('tgl_auto_check_updates', old_prefs.get('auto_check_updates', True), 'isChecked'),
            'auto_update_on_start':   self._safe_get('tgl_auto_update_on_start', old_prefs.get('auto_update_on_start', False), 'isChecked'),
        }
        
        if not is_basic:
            state.update({
                'always_on_top':      self._safe_get('chk_ontop', old_prefs.get('always_on_top', False), 'isChecked'),
                'device':             self._safe_get('dropdown_device', old_prefs.get('device', 'auto'), 'currentText').lower(),
                'ai_compute_type':    self._safe_get('dropdown_compute', old_prefs.get('ai_compute_type', 'Auto'), 'currentText'),
                'ai_initial_prompt':  self._safe_get('textedit_prompt', old_prefs.get('ai_initial_prompt', ''), 'toPlainText'),
                'chunk_max_words':    self._safe_get('spin_chunk_max', old_prefs.get('chunk_max_words', 30), 'value'),
                'chunk_lookahead':    self._safe_get('spin_chunk_look', old_prefs.get('chunk_lookahead', 3), 'value'),
                'chunk_min_chars':    self._safe_get('spin_chunk_min', old_prefs.get('chunk_min_chars', 7), 'value'),
                'algo_fuzzy_threshold':  self._safe_get('spin_fuzzy', old_prefs.get('algo_fuzzy_threshold', 80), 'value'),
                'algo_retake_lookahead': self._safe_get('spin_lookahead', old_prefs.get('algo_retake_lookahead', 80), 'value'),
                'algo_distance_penalty': self._safe_get('spin_penalty', old_prefs.get('algo_distance_penalty', 2.0), 'value'),
                'algo_anchor_depth':     self._safe_get('spin_anchor', old_prefs.get('algo_anchor_depth', 3), 'value'),
                'ai_vad_filter':            self._safe_get('chk_vad_filter', old_prefs.get('ai_vad_filter', False), 'isChecked'),
                'ai_beam_size':             self._safe_get('spin_beam_size', old_prefs.get('ai_beam_size', 1), 'value'),
                'ai_temperature':           self._safe_get('spin_temperature', old_prefs.get('ai_temperature', 0.0), 'value'),
                'ai_condition_on_prev':     self._safe_get('chk_condition_prev', old_prefs.get('ai_condition_on_prev', False), 'isChecked'),
                'ai_logprob_threshold':     self._safe_get('spin_logprob', old_prefs.get('ai_logprob_threshold', -1.0), 'value'),
                'ai_no_speech_threshold':   self._safe_get('spin_no_speech', old_prefs.get('ai_no_speech_threshold', 0.6), 'value'),
                'ai_patience':              self._safe_get('spin_patience', old_prefs.get('ai_patience', 1.0), 'value'),
                'ai_compression_ratio_threshold': self._safe_get('spin_compression', old_prefs.get('ai_compression_ratio_threshold', 2.4), 'value'),
                'ai_no_repeat_ngram_size':  self._safe_get('spin_no_repeat', old_prefs.get('ai_no_repeat_ngram_size', 0), 'value'),
                'ai_length_penalty':        self._safe_get('spin_length_penalty', old_prefs.get('ai_length_penalty', 1.0), 'value'),
                'ai_repetition_penalty':    self._safe_get('spin_repetition_penalty', old_prefs.get('ai_repetition_penalty', 1.0), 'value'),
            })
        else:
            advanced_keys = ["always_on_top", "device", "ai_compute_type", "ai_initial_prompt", "chunk_max_words", "chunk_lookahead", "chunk_min_chars", "algo_fuzzy_threshold", "algo_retake_lookahead", "algo_distance_penalty", "algo_anchor_depth", "ai_vad_filter", "ai_beam_size", "ai_temperature", "ai_condition_on_prev", "ai_logprob_threshold", "ai_no_speech_threshold", "ai_patience", "ai_compression_ratio_threshold", "ai_no_repeat_ngram_size", "ai_length_penalty", "ai_repetition_penalty"]
            for key in advanced_keys:
                if key in old_prefs:
                    state[key] = old_prefs[key]
        return state

    def _safe_set(self, attr_name, value, method_name="setValue"):
        """Safely sets a value on a widget, avoiding dead objects or missing attributes."""
        try:
            if hasattr(self, attr_name):
                widget = getattr(self, attr_name)
                getattr(widget, method_name)(value)
        except (RuntimeError, AttributeError):
            pass

    def _restore_state_dict(self, state):
        is_basic = state.get('settings_view_mode', 'basic') == 'basic'
        self._safe_set('chk_telemetry_opt_in', state.get('telemetry_opt_in', False), 'setChecked')
        self._safe_set('chk_telemetry_geo', state.get('telemetry_geo', False), 'setChecked')
        
        try:
            if hasattr(self, 'icon_group'):
                icon_name = state.get('app_icon', 'default')
                for btn in self.icon_group.buttons():
                    if btn.property("icon_name") == icon_name:
                        btn.setChecked(True)
                        break
        except RuntimeError:
            pass
                
        try:
            lang_code = state.get('gui_lang', 'en')
            self._safe_set('dropdown_lang', config.SUPPORTED_LANGS.get(lang_code, 'English'), 'setText')
        except Exception:
            pass
        
        view_mode = state.get('view_mode', 'segmented')
        self._safe_set('combo_view', self.txt("opt_segmented_blocks") if view_mode == 'segmented' else self.txt("opt_continuous_flow"), 'setText')
        self._safe_set('combo_font', state.get('editor_font_family', 'Segoe UI'), 'setText')
        self._safe_set('spin_fsize', state.get('editor_font_size', 12), 'setValue')
        self._safe_set('spin_lheight', state.get('editor_line_height', 7), 'setValue')
        
        self.current_custom_markers = state.get('custom_markers', [])
        try:
            if hasattr(self, '_refresh_markers_list'):
                self._refresh_markers_list()
        except RuntimeError:
            pass
        
        try:
            from PySide6.QtGui import QKeySequence
            if hasattr(self, 'shortcut_inputs'):
                for k, v in state.get('shortcuts', {}).items():
                    if k in self.shortcut_inputs:
                        self.shortcut_inputs[k].set_sequence(v)
        except RuntimeError:
            pass
                
        self._safe_set('chk_sync_davinci', state.get('sync_davinci_chapter', True), 'setChecked')
        self._safe_set('tgl_timestamp_precise', state.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']), 'setChecked')
        self._safe_set('tgl_auto_check_updates', state.get('auto_check_updates', True), 'setChecked')
        self._safe_set('tgl_auto_update_on_start', state.get('auto_update_on_start', False), 'setChecked')
        
        if not is_basic:
            self._safe_set('chk_ontop', state.get('always_on_top', False), 'setChecked')
            
            dev_val = state.get('device', 'Auto').upper()
            if dev_val == 'AUTO': dev_val = 'Auto'
            self._safe_set('dropdown_device', dev_val, 'setText')
            self._safe_set('dropdown_compute', state.get('ai_compute_type', 'Auto'), 'setText')
            self._safe_set('textedit_prompt', state.get('ai_initial_prompt', ''), 'setPlainText')
            self._safe_set('spin_chunk_max', state.get('chunk_max_words', 30), 'setValue')
            self._safe_set('spin_chunk_look', state.get('chunk_lookahead', 3), 'setValue')
            self._safe_set('spin_chunk_min', state.get('chunk_min_chars', 7), 'setValue')
            self._safe_set('chk_vad_filter', state.get('ai_vad_filter', False), 'setChecked')
            self._safe_set('spin_beam_size', state.get('ai_beam_size', 1), 'setValue')
            self._safe_set('spin_temperature', state.get('ai_temperature', 0.0), 'setValue')
            self._safe_set('chk_condition_prev', state.get('ai_condition_on_prev', False), 'setChecked')
            self._safe_set('spin_logprob', state.get('ai_logprob_threshold', -1.0), 'setValue')
            self._safe_set('spin_no_speech', state.get('ai_no_speech_threshold', 0.6), 'setValue')
            self._safe_set('spin_patience', state.get('ai_patience', 1.0), 'setValue')
            self._safe_set('spin_compression', state.get('ai_compression_ratio_threshold', 2.4), 'setValue')
            self._safe_set('spin_no_repeat', state.get('ai_no_repeat_ngram_size', 0), 'setValue')

            self._safe_set('spin_length_penalty', state.get('ai_length_penalty', 1.0), 'setValue')
            self._safe_set('spin_repetition_penalty', state.get('ai_repetition_penalty', 1.0), 'setValue')
            self._safe_set('spin_fuzzy', state.get('algo_fuzzy_threshold', 80), 'setValue')
            self._safe_set('spin_lookahead', state.get('algo_retake_lookahead', 80), 'setValue')
            self._safe_set('spin_penalty', state.get('algo_distance_penalty', 2.0), 'setValue')
            self._safe_set('spin_anchor', state.get('algo_anchor_depth', 3), 'setValue')

    def _apply_settings(self):
        old_prefs = self.engine.load_preferences() or {}
        new_prefs = self._get_current_state_dict()
        
        selected_device  = new_prefs.get('device', 'auto')
        selected_compute = new_prefs.get('ai_compute_type', 'Auto')
        old_compute      = old_prefs.get('ai_compute_type', 'Auto')
        old_device       = old_prefs.get('device', 'auto')

        compute_changed = (selected_compute != old_compute) or (selected_device != old_device)
        if selected_compute.lower() != 'auto' and compute_changed:
            from PySide6.QtWidgets import QApplication
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                is_supported = self.engine.verify_hardware_compute(selected_device, selected_compute)
            finally:
                QApplication.restoreOverrideCursor()

            if not is_supported:
                CustomMsgBox(self, self.txt('msg_compute_fail_title'), self.txt('msg_compute_fail_desc'), self.txt('btn_close')).exec()
                return

        restart_needed = any(
            new_prefs.get(k) != old_prefs.get(k)
            for k in config.RESTART_REQUIRED_KEYS
            if k in new_prefs
        )

        self.engine.save_preferences(new_prefs)
        self.initial_prefs = self.engine.load_preferences() or {}
        self._initial_state = self._get_current_state_dict()
        self.btn_apply.setText(self.txt("txt_saved"))
        self.btn_apply.setStyleSheet(f"background-color: #1a7a3e; color: white;")
        from PySide6.QtCore import QTimer
        def restore_btn():
            self.btn_apply.setText(self.txt("btn_apply"))
            self.btn_apply.setStyleSheet("") # Przywraca domyślny arkusz CSS
        QTimer.singleShot(1500, restore_btn)

        main_win = self.parent()
        if hasattr(main_win, 'text_canvas'):
            main_win.text_canvas._calculate_layout()
            main_win.text_canvas.update()

        aot_changed = new_prefs.get('always_on_top', False) != bool(old_prefs.get('always_on_top', False))
        if aot_changed and main_win:
            is_top = bool(new_prefs.get('always_on_top'))
            if hasattr(main_win, '_apply_always_on_top'):
                main_win._apply_always_on_top(is_top)
            else:
                main_win.setWindowFlag(Qt.WindowStaysOnTopHint, is_top)
                main_win.show()

        if restart_needed:
            lang = old_prefs.get('gui_lang', 'en')
            target = config.TRANS.get(lang, config.TRANS['en'])
            CustomMsgBox(
                self,
                target.get('tool_settings', 'Settings'),
                target.get('msg_restart_required', 'Changes applied. Full effect will be visible on next launch.'),
                target.get('btn_ok', 'OK')
            ).exec()

    def reject(self):
        # FIX: Validate against the exact snapshot of how the UI was built
        # rather than the raw preferences file which may be missing keys.
        old_prefs = getattr(self, '_initial_state', self.engine.load_preferences() or {})
        new_prefs = self._get_current_state_dict()
        diff = {}
        for k, new_val in new_prefs.items():
            old_val = old_prefs.get(k)
            if old_val is None:
                if k == 'app_icon': old_val = 'default'
                elif k == 'gui_lang': old_val = 'en'
                elif k == 'hidden_panels': old_val = []
                elif k == 'custom_markers': old_val = []
            
            if k == 'shortcuts':
                old_dict = old_val if old_val is not None else {}
                for sub_k, sub_new in new_val.items():
                    sub_old = old_dict.get(sub_k, '')
                    if sub_old != sub_new:
                        diff[f"shortcuts.{sub_k}"] = (sub_old, sub_new)
            else:
                if str(new_val) != str(old_val) and new_val != old_val:
                    diff[k] = (old_val, new_val)
                
        if diff:
            key_name_map = {
                'shortcuts': f"{self.txt('tab_shortcuts')}",
                'gui_lang': f"{self.txt('tab_general')}: {self.txt('lbl_language')}",
                'app_icon': f"{self.txt('tab_general')}: {self.txt('lbl_app_icon')}",
                'view_mode': f"{self.txt('tab_transcript')}: {self.txt('lbl_display_mode')}",
                'editor_font_family': f"{self.txt('tab_transcript')}: {self.txt('lbl_transcript_font')}",
                'editor_font_size': f"{self.txt('tab_transcript')}: {self.txt('lbl_font_size_pt')}",
                'editor_line_height': f"{self.txt('tab_transcript')}: {self.txt('lbl_line_spacing_px')}",
                'chunk_max_words': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_max_words')}",
                'chunk_lookahead': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_lookahead')}",
                'chunk_min_chars': f"{self.txt('tab_transcript')}: {self.txt('lbl_chunk_min_chars')}",
                'always_on_top': f"{self.txt('tab_transcript')}: {self.txt('lbl_always_on_top')}",
                'sync_davinci_chapter': f"{self.txt('tab_transcript')}: {self.txt('chk_sync_davinci')}",
                'timestamp_precise':    f"{self.txt('tab_transcript')}: {self.txt('lbl_timestamp_precise')}",
                'device': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_device')}",
                'ai_compute_type': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_compute_type')}",
                'ai_initial_prompt': f"{self.txt('tab_ai_engine')}: {self.txt('lbl_initial_prompt')}",
                'ai_length_penalty': f"{self.txt('tab_ai_engine')}: Length Penalty",
                'ai_repetition_penalty': f"{self.txt('tab_ai_engine')}: Repetition Penalty",

                'telemetry_opt_in': f"{self.txt('tab_telemetry')}: {self.txt('chk_telemetry_opt_in')}",
                'telemetry_geo': f"{self.txt('tab_telemetry')}: {self.txt('chk_telemetry_geo')}",
                'auto_check_updates': f"{self.txt('tab_general')}: {self.txt('lbl_auto_check_updates')}",
                'custom_markers': self.txt('tab_custom_markers')
            }
            
            # Map dynamic shortcut composite keys
            for diff_k in diff.keys():
                if diff_k.startswith('shortcuts.'):
                    sub_k = diff_k.split('.', 1)[1]
                    sub_name = self.txt(f"shortcut_{sub_k}")
                    if sub_name == f"shortcut_{sub_k}": # Fallback if not translated
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
                        else:
                            new_prefs[k] = diff[k][0] 
                    else:
                        save_needed = True
                
                self._restore_state_dict(new_prefs)
                
                if save_needed:
                    self._apply_settings()
                super().reject()
            else:
                return 
        else:
            super().reject()


