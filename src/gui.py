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
import ctypes
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QDialog, QLabel, QPushButton, QCheckBox,
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QSizePolicy, QAbstractItemView, QFrame, QScrollArea,
    QDockWidget, QToolBar, QStackedWidget, QFormLayout, QComboBox,
    QSpacerItem, QCompleter, QLineEdit, QWidgetAction, QToolTip,
    QTextEdit, QRadioButton, QDoubleSpinBox, QSplitter, QSplitterHandle,
    QTabWidget, QSpinBox
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize, QObject, QEvent, QRect, QPoint,
    QVariantAnimation, QEasingCurve, QAbstractAnimation,
    QPropertyAnimation, Property
)
from PySide6.QtGui import (
    QFont, QFontDatabase, QIcon, QPixmap, QColor, QAction, QGuiApplication, 
    QCursor, QDrag, QPainter, QPen, QFontMetrics, QLinearGradient
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
        
        w = self.width() # Expected to be 10
        h = self.height()
        half_w = w // 2  # Exactly 5
        
        # BULLETPROOF CHECK: handle(1) is always between LeftPanel and Stack.
        # If self is handle(1), it's the left sidebar grip. Else, it's the right one.
        is_left_handle = (self == self.splitter().handle(1))
        
        # 1. 50/50 Seamless Background Split
        if is_left_handle:
            painter.fillRect(0, 0, half_w, h, QColor("#212121")) # Left half touches panel
            painter.fillRect(half_w, 0, w - half_w, h, QColor("#1c1c1c")) # Right half touches workspace
        else:
            painter.fillRect(0, 0, half_w, h, QColor("#1c1c1c")) # Left half touches workspace
            painter.fillRect(half_w, 0, w - half_w, h, QColor("#212121")) # Right half touches panel
            
        # 2. Draw the Grip Pill (Centered, perfectly bisected by the background split)
        pill_width = 6
        pill_height = 36
        x = (w - pill_width) // 2
        y = (h - pill_height) // 2
        
        painter.setBrush(QColor("#555555"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(x, y, pill_width, pill_height, 3, 3)
        
        # 3. Draw 3 Centered Dots
        painter.setBrush(QColor("#aaaaaa"))
        dot_size = 2
        dot_x = x + (pill_width - dot_size) // 2
        
        painter.drawEllipse(dot_x, y + 8, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 17, dot_size, dot_size)
        painter.drawEllipse(dot_x, y + 26, dot_size, dot_size)

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


def apply_dark_title_bar(window: QWidget):
    """Forces the native Windows title bar to dark mode."""
    if platform.system() == "Windows":
        try:
            import ctypes
            # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE in Windows 10/11
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

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


def _qwidget_txt(self, key: str, **kwargs) -> str:
    w = self.window()
    if hasattr(w, 'txt') and w != self:
        return w.txt(key, **kwargs)
    return _txt("en", key, **kwargs)

QWidget.txt = _qwidget_txt


# ==========================================
# PHASE 7 CLASSES: WORKER, PROGRESS BAR, CANVAS
# ==========================================


class WorkerSignals(QObject):
    progress = Signal(int)
    status = Signal(str)
    finished = Signal(object, object)
    error = Signal(str)

class LiquidProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._indet_offset = 0.0
        self._indeterminate = False
        self.setFixedHeight(8)
        
        self._anim = QPropertyAnimation(self, b"value")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self._loop_anim = QPropertyAnimation(self, b"indet_offset")
        self._loop_anim.setDuration(1500)
        self._loop_anim.setStartValue(0.0)
        self._loop_anim.setEndValue(1.0)
        self._loop_anim.setLoopCount(-1)

    @Property(float)
    def value(self): return self._value

    @value.setter
    def value(self, val):
        self._value = val
        self.update()
        
    @Property(float)
    def indet_offset(self): return self._indet_offset

    @indet_offset.setter
    def indet_offset(self, val):
        self._indet_offset = val
        self.update()

    def set_value(self, val):
        if val < 0:
            if not self._indeterminate:
                self._indeterminate = True
                self._anim.stop()
                self._loop_anim.start()
        else:
            if self._indeterminate:
                self._indeterminate = False
                self._loop_anim.stop()
            self._anim.stop()
            self._anim.setEndValue(float(val))
            self._anim.start()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QLinearGradient
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2b2b2b"))
        p.drawRoundedRect(rect, 4, 4)
        
        if self._indeterminate:
            pill_width = rect.width() * 0.25
            x_pos = self._indet_offset * (rect.width() + pill_width) - pill_width
            
            grad = QLinearGradient(x_pos, 0, x_pos + pill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.setClipRect(rect)
            p.drawRoundedRect(QRectF(x_pos, 0, pill_width, rect.height()), 4, 4)
        elif self._value > 0:
            fill_width = (self._value / 100.0) * rect.width()
            fill_rect = QRectF(0, 0, fill_width, rect.height())
            
            grad = QLinearGradient(0, 0, fill_width, 0)
            grad.setColorAt(0.0, QColor("#1a7a3e"))
            grad.setColorAt(1.0, QColor("#b8d035"))
            
            p.setBrush(grad)
            p.drawRoundedRect(fill_rect, 4, 4)


class TranscriptionCanvas(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.words_data = []
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        self._last_dragged_id = -1

    def load_data(self, words_data):
        self.words_data = words_data
        self._calculate_layout()
        self.update()

    def _get_visible_words(self):
        """Returns a filtered list of only the words that should physically render.
        STAGE 9: Consecutive inaudible tokens are deduplicated in the view layer —
        only the first (...) of a run is shown; data remains intact in memory.
        """
        if not self.words_data: return []
        
        vis = []
        previous_was_inaudible = False

        for w in self.words_data:
            if w.get('type') == 'silence':
                continue
                
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'

            if is_inaudible:
                # Hide if the user toggled inaudible off
                if hasattr(self.main_window, 'tgl_show_inaudible') and not self.main_window.tgl_show_inaudible.isChecked():
                    previous_was_inaudible = True
                    continue
                # STAGE 9: Skip consecutive (...) clutter — show only the first of a run
                if previous_was_inaudible:
                    continue
                previous_was_inaudible = True
            else:
                previous_was_inaudible = False

            vis.append(w)
        return vis


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._calculate_layout()

    def _calculate_layout(self):
        if not self.words_data: return
        from PySide6.QtGui import QFontMetrics, QFont
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        pref_lh = prefs.get('editor_line_height', 8)
        view_mode = prefs.get('view_mode', 'continuous')
        
        active_font = QFont(pref_family, pref_size)
        metrics = QFontMetrics(active_font)
        ts_font = QFont(config.UI_FONT_NAME, max(8, pref_size - 2))
        ts_metrics = QFontMetrics(ts_font)
        
        space_w = metrics.horizontalAdvance(" ") + 2
        line_height = metrics.height() + pref_lh
        
        x, y = 20, 20
        max_w = self.width() - 40
        
        visible_words = self._get_visible_words()
        
        for w in visible_words:
            # Clean previous iteration markers
            w.pop('_ts_rect', None)
            w.pop('_ts_text', None)
            w.pop('_separator_y', None)
            
            # Paragraph formatting based on Engine's Chunking
            if view_mode == 'segmented' and w.get('is_segment_start'):
                if x > 20: 
                    y += line_height
                if y > 20: 
                    w['_separator_y'] = y + 10 # Store Y coordinate for the line
                    y += 20 # Gap between paragraphs
                x = 20
                
                # Generate Timestamp
                secs = w.get('start', 0)
                m = int(secs // 60)
                s = int(secs % 60)
                ms = int((secs - int(secs)) * 1000)
                ts_text = f"[{m:02d}:{s:02d}.{ms:03d}]"
                
                ts_w = ts_metrics.horizontalAdvance(ts_text)
                w['_ts_text'] = ts_text
                w['_ts_rect'] = QRect(x, y, ts_w, metrics.height() + 4)
                x += ts_w + space_w + 5
            
            # Standard word layout
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            text = "(...)" if is_inaudible else w.get('text', '')
            w['_display_text'] = text  # Store visual text
            
            word_w = metrics.horizontalAdvance(text)
            
            if x + word_w > max_w and x > 20:
                x = 20
                y += line_height
                
            w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
            x += word_w + space_w
            
        self.setMinimumHeight(y + line_height + 40)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QFont
        from PySide6.QtCore import QRectF
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        active_font = QFont(pref_family, pref_size)
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        
        color_map = {
            'bad': (QColor(config.WORD_BAD_BG), QColor(config.WORD_BAD_FG)),
            'repeat': (QColor(config.WORD_REPEAT_BG), QColor(config.WORD_REPEAT_FG)),
            'typo': (QColor(config.WORD_TYPO_BG), QColor(config.WORD_TYPO_FG)),
            'inaudible': (QColor(config.WORD_INAUDIBLE_BG), QColor(config.WORD_INAUDIBLE_FG))
        }
        
        def get_status(w):
            s = w.get('status')
            if s == 'inaudible' and hasattr(self.main_window, 'tgl_mark_inaudible') and not self.main_window.tgl_mark_inaudible.isChecked():
                if w.get('manual_status') != 'inaudible' or w.get('is_auto', False):
                    return None
            if s == 'typo' and hasattr(self.main_window, 'tgl_show_typos') and not self.main_window.tgl_show_typos.isChecked():
                # Keep 'typo' visible if it was manually marked by the user
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    return None
            return s

        p.setPen(Qt.NoPen)
        visible_words = self._get_visible_words()
        
        # PASS 0: Horizontal Separator Lines
        p.setPen(QPen(QColor("#333333"), 1))
        for w in visible_words:
            if '_separator_y' in w:
                sep_y = w['_separator_y']
                p.drawLine(20, sep_y, self.width() - 20, sep_y)
        
        p.setPen(Qt.NoPen) # Reset pen for Pass 1
        
        # PASS 1: Base Backgrounds
        for w in visible_words:
            if '_rect' not in w: continue
            status = get_status(w)
            if status in color_map:
                p.setBrush(color_map[status][0])
                p.drawRoundedRect(w['_rect'].adjusted(-3, -1, 3, 1), 5, 5)
                
        # PASS 2: Sharp Bridges
        for i in range(len(visible_words) - 1):
            w1 = visible_words[i]
            w2 = visible_words[i+1]
            
            if '_rect' not in w1 or '_rect' not in w2: continue
            if w1['_rect'].y() != w2['_rect'].y(): continue 
            
            s1 = get_status(w1)
            s2 = get_status(w2)
            
            if s1 in color_map and s2 in color_map:
                r1 = w1['_rect'].adjusted(-3, -1, 3, 1)
                r2 = w2['_rect'].adjusted(-3, -1, 3, 1)
                c1 = color_map[s1][0]
                c2 = color_map[s2][0]
                
                if s1 == s2:
                    p.setBrush(c1)
                    bridge_rect = QRectF(r1.right() - 5, r1.y(), r2.left() - r1.right() + 10, r1.height())
                    p.drawRect(bridge_rect)
                else:
                    p.setRenderHint(QPainter.Antialiasing, False)
                    gap_mid = int(r1.right() + (r2.left() - r1.right()) / 2.0)
                    p.setBrush(c1)
                    p.drawRect(QRectF(r1.right() - 5, r1.y(), gap_mid - r1.right() + 6, r1.height()))
                    p.setBrush(c2)
                    p.drawRect(QRectF(gap_mid, r2.y(), r2.left() - gap_mid + 5, r2.height()))
                    p.setRenderHint(QPainter.Antialiasing, True)
                
        # PASS 3: Timestamps & Text
        ts_font = QFont(config.UI_FONT_NAME, 10)
        ts_color = QColor("#666666")
        
        for w in visible_words:
            # Draw Timestamp if exists
            if '_ts_rect' in w:
                p.setFont(ts_font)
                p.setPen(ts_color)
                p.drawText(w['_ts_rect'], Qt.AlignLeft | Qt.AlignVCenter, w.get('_ts_text', ''))
                
            # Draw Word Text
            if '_rect' not in w: continue
            p.setFont(active_font)
            status = get_status(w)
            fg_color = color_map[status][1] if status in color_map else QColor(config.WORD_NORMAL_FG)
            p.setPen(fg_color)
            p.drawText(w['_rect'], Qt.AlignCenter, w.get('_display_text', w.get('text', '')))

    def _handle_mouse(self, pos):
        visible_words = self._get_visible_words()
        for w in visible_words:
            if '_rect' in w and w['_rect'].adjusted(-3, -1, 3, 1).contains(pos):
                if w['id'] != self._last_dragged_id:
                    self._last_dragged_id = w['id']
                    status = None
                    if self.main_window.rb_red.isChecked():   status = 'bad'
                    elif self.main_window.rb_blue.isChecked(): status = 'repeat'
                    elif self.main_window.rb_green.isChecked(): status = 'typo'
                    # rb_eraser → status stays None → propagate_status_change clears

                    import algorythms
                    updates = algorythms.propagate_status_change(self.words_data, w['id'], status)

                    if updates:
                        # Build a fast O(1) lookup: id → word_obj
                        id_map = {wo['id']: wo for wo in self.words_data}

                        layer_engine = getattr(self.main_window, '_calculate_visual_layer', None)
                        for wid, _raw in updates:
                            word_obj = id_map.get(wid)
                            if word_obj is None:
                                continue
                            # Stamp overlay_suppressed so the algo overlay sinks
                            # below the user's manual paint until the next reload.
                            word_obj['overlay_suppressed'] = True
                            # Route through the Layer Engine — this is what actually
                            # writes word_obj['status'] to the correct final value.
                            if layer_engine:
                                layer_engine(word_obj)

                        self.update()
                break


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._last_dragged_id = -1
            self._handle_mouse(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._handle_mouse(event.pos())

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
        apply_dark_title_bar(self)

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
                font-size: 18pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#loading {{
                color: {config.NOTE_COL};
                font-size: 12pt;
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

        self._lbl_loading = QLabel(self.txt("lbl_loading"), self)
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
                font-size: 11pt;
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
        apply_dark_title_bar(self)

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
                font-size: 14pt;
                font-weight: bold;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QLabel#lbl_msg {{
                color: {config.FG_COLOR};
                font-size: 11pt;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
            }}
            QPushButton#btn_lang {{
                color: {config.GEAR_COLOR};
                font-family: "{config.UI_FONT_NAME}";
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
                font-family: "{config.UI_FONT_NAME}";
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
                font-family: "{config.UI_FONT_NAME}";
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
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
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
                font-size: 10pt;
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
    def __init__(self, icon_text: str, label_text: str, activity_id: str, tooltip_widget=None, is_right_side: bool = False, is_draggable: bool = True, parent=None):
        super().__init__()
        if parent:
            self.setParent(parent)
        self.setText(icon_text)
        self.activity_id = activity_id
        self.setFixedSize(40, 40)
        self.setCursor(Qt.PointingHandCursor)
        self.custom_tooltip_text = label_text
        self.is_right_side = is_right_side
        self.is_draggable = is_draggable
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
                    font-size: 18pt; 
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
                    font-size: 18pt; 
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
        if not self.is_draggable: return
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
        
        self._drag_was_active = self.is_active
        
        was_active = self.is_active
        if was_active:
            self.set_active(False)  # Temporarily remove active CSS (green border)
            self.style().polish(self) # Force CSS update
        
        btn_pixmap = self.grab() # Take the perfect 40x40 photo without border
        
        if was_active:
            self.set_active(True) # Restore state
            self.style().polish(self)
        
        if self.is_active:
            panel_widget = self.window().activities.get(self.activity_id)
            if panel_widget:
                panel_pixmap = panel_widget.grab()
                scaled_panel = panel_pixmap.scaledToWidth(160, Qt.SmoothTransformation)
                composite = QPixmap(scaled_panel.size())
                composite.fill(Qt.transparent)
                p = QPainter(composite)
                p.setOpacity(0.6)
                p.drawPixmap(0, 0, scaled_panel)
                p.setOpacity(1.0)
                p.drawPixmap(0, 0, btn_pixmap)
                p.end()
                drag.setPixmap(composite)
                drag.setHotSpot(event.position().toPoint())
            else:
                drag.setPixmap(btn_pixmap)
                drag.setHotSpot(event.position().toPoint())
        else:
            # Snapshot the button for the drag icon
            drag.setPixmap(btn_pixmap)
            drag.setHotSpot(event.position().toPoint())
        
        # Execute drag
        if self._drag_was_active and self.window() and hasattr(self.window(), "_toggle_activity"):
            self.window()._toggle_activity(self.activity_id)
            
        self.hide()
        drag.exec(Qt.MoveAction)
        self.show()


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


class CustomDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText(self.txt("txt_select"))
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

class MultiSelectDropdown(QPushButton):
    valueChanged = Signal(list)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.selected_items = set()
        self.setText(self.txt("txt_select_tracks"))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #1e1e1e; color: #d4d4d4; text-align: left;
                padding: 4px 8px; border: 1px solid #3a3a3a; border-radius: 3px; min-height: 20px;
            }}
            QPushButton:hover {{ border-color: {config.BTN_BG}; }}
        """)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("QFrame { background-color: #1e1e1e; border: 1px solid #444; border-radius: 3px; padding: 0px; margin: 0px; }")

        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setStyleSheet("""
            QListWidget { border: none; outline: none; background: transparent; }
            QListWidget::item { border-bottom: 1px solid #2a2a2a; }
            QListWidget::item:hover { background-color: #2a2d2e; }
        """)

        from PySide6.QtCore import QSize
        for opt in self.options_list:
            item = QListWidgetItem(list_widget)
            item.setSizeHint(QSize(0, 28))  # TWARDE WYMUSZENIE 28px
            widget = QCheckBox(opt)
            widget.setCursor(Qt.PointingHandCursor)
            widget.setChecked(opt in self.selected_items)
            widget.setStyleSheet("""
                QCheckBox { color: #d4d4d4; padding: 0px 8px; margin: 0px; font-size: 10pt; background: transparent; }
                QCheckBox::indicator {
                    width: 14px; height: 14px; border-radius: 7px; background-color: #111111; border: 1px solid #333;
                }
                QCheckBox::indicator:checked {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.4, fx:0.5, fy:0.5, stop:0 #1a7a3e, stop:0.8 #1a7a3e, stop:1 transparent);
                    border: 1px solid #1a7a3e;
                }
            """)
            widget.toggled.connect(lambda checked, text=opt: self._on_toggled(text, checked))
            list_widget.setItemWidget(item, widget)

        layout.addWidget(list_widget)

        # PERFEKCYJNA MATEMATYKA WYSOKOŚCI
        display_count = min(5, len(self.options_list))
        list_height = display_count * 28
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)

        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        popup.move(global_pos)
        popup.setFixedWidth(self.width())
        popup.show()

    def _on_toggled(self, text, checked):
        if checked: self.selected_items.add(text)
        else: self.selected_items.discard(text)

        if not self.selected_items: self.setText(self.txt("txt_select_tracks"))
        else: self.setText(", ".join(sorted(self.selected_items)))
        self.valueChanged.emit(list(self.selected_items))


class SearchableDropdown(QPushButton):
    valueChanged = Signal(str)
    def __init__(self, options_list, parent=None):
        super().__init__(parent=parent)
        self.options_list = list(options_list)
        self.setText(self.txt("txt_select"))
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
        self.line_edit.setPlaceholderText(self.txt("ph_search"))
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


class CustomMsgBox(QDialog):
    def __init__(self, parent, title: str, message: str, btn_yes_text: str, btn_no_text: str = None):
        super().__init__(parent)
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        apply_dark_title_bar(self)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: {config.BG_COLOR}; border: 1px solid #111; }}
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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget(self)
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(20, 25, 20, 20)
        v_layout.setSpacing(15)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("lbl_title")
        v_layout.addWidget(lbl_title)
        
        lbl_msg = QLabel(message)
        lbl_msg.setObjectName("lbl_msg")
        lbl_msg.setWordWrap(True)
        lbl_msg.setFixedWidth(380)
        lbl_msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        v_layout.addWidget(lbl_msg)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        if btn_no_text:
            btn_no = QPushButton(btn_no_text)
            btn_no.clicked.connect(self.reject)
            btn_layout.addWidget(btn_no)
            btn_layout.addSpacing(10)
            
        btn_yes = QPushButton(btn_yes_text)
        btn_yes.setObjectName("btn_yes")
        btn_yes.clicked.connect(self.accept)
        btn_layout.addWidget(btn_yes)
        
        v_layout.addLayout(btn_layout)
        layout.addWidget(container)
        
        self.adjustSize()
        _center_on_screen(self, self.width(), self.height())


class SettingsDialog(QDialog):
    """Settings Dialog — left category menu + right stacked pages.
    All I/O goes through engine.load_preferences / engine.save_preferences
    which delegate to osdoc's smart router.
    """

    # Fallback defaults (for revert buttons)
    DEFAULTS = {
        'view_mode':          'continuous',
        'offset':             -0.05,
        'pad':                0.05,
        'snap_max':           0.25,
        'editor_font_family': config.UI_FONT_NAME,
        'editor_font_size':   12,
        'editor_line_height': 12,
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
        self.setWindowFlags(Qt.Dialog)
        self.setMinimumSize(680, 520)
        self.resize(720, 550)
        apply_dark_title_bar(self)

        prefs = self.engine.load_preferences() or {}

        # ── Global stylesheet ─────────────────────────────────────────────
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {config.BG_COLOR};
            }}
            QPushButton {{
                padding: 4px 12px;
            }}
            QLabel {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
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
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 10px 16px;
                border-radius: 0px;
            }}
            QListWidget::item:selected {{
                background-color: #2a2d2e;
                color: {config.FG_COLOR};
                border-left: 2px solid {config.BTN_BG};
            }}
            QListWidget::item:hover:!selected {{
                background-color: #222222;
                color: {config.FG_COLOR};
            }}
            QStackedWidget {{
                background-color: {config.BG_COLOR};
            }}
            QDoubleSpinBox, QSpinBox, QComboBox {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                padding: 4px 8px;
                border-radius: 3px;
                min-height: 26px;
            }}
            QCheckBox {{
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
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
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 0 18px;
            }}
            QPushButton#btn_apply:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_secondary {{
                background-color: transparent;
                color: #d4d4d4;
                border: 1px solid #555;
                border-radius: 4px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
                padding: 0 12px;
            }}
            QPushButton#btn_secondary:hover {{ background-color: #2a2d2e; border-color: #888; }}
            QPushButton#btn_ghost_sm {{
                background-color: transparent;
                color: #888;
                border: 1px solid #444;
                border-radius: 4px;
                font-family: "{config.UI_FONT_NAME}";
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
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: Category list ───────────────────────────────────────────
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(155)
        self.category_list.setFocusPolicy(Qt.NoFocus)
        self.category_list.addItem(self.txt("tab_general"))
        self.category_list.addItem(self.txt("tab_audio_sync"))
        self.category_list.addItem(self.txt("tab_transcript"))
        self.category_list.addItem(self.txt("tab_ai_engine"))
        self.category_list.addItem(self.txt("tab_interface"))
        self.category_list.setCurrentRow(0)
        root.addWidget(self.category_list)

        # ── RIGHT: stacked pages + bottom bar ────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        root.addLayout(right_layout)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        # Connect list → stack
        self.category_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        # ── Revert helper ─────────────────────────────────────────────────
        self.revert_funcs = []

        def _add_row(form, label_text, widget, default_val, setter_func):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(widget)
            btn_rev = QPushButton("↺")
            btn_rev.setFixedSize(26, 26)
            btn_rev.setCursor(Qt.PointingHandCursor)
            btn_rev.setObjectName("btn_ghost_sm")
            btn_rev.setToolTip(self.txt("tt_revert_to_default"))
            btn_rev.clicked.connect(lambda checked=False, d=default_val, s=setter_func: s(d))
            row.addWidget(btn_rev)
            lbl = QLabel(label_text)
            lbl.setWordWrap(True)
            lbl.setMinimumWidth(200)
            form.addRow(lbl, row)
            self.revert_funcs.append(lambda d=default_val, s=setter_func: s(d))

        # ─────────────────────────────────────────────────────────────────
        # PAGE 0 — GENERAL
        # ─────────────────────────────────────────────────────────────────
        page_gen = QWidget()
        page_gen.setStyleSheet("background: transparent;")
        l_gen = QVBoxLayout(page_gen)
        l_gen.setContentsMargins(24, 20, 24, 16)
        l_gen.setSpacing(0)
        form_gen = QFormLayout()
        form_gen.setSpacing(14)
        form_gen.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Language
        self.dropdown_lang = CustomDropdown(list(config.SUPPORTED_LANGS.values()))
        current_lang_code = prefs.get('gui_lang', 'en')
        self.dropdown_lang.setText(config.SUPPORTED_LANGS.get(current_lang_code, 'English'))

        def _on_lang_changed(val):
            code = next((k for k, v in config.SUPPORTED_LANGS.items() if v == val), 'en')
            self.engine.save_preferences({'gui_lang': code})
            target = config.TRANS.get(code, config.TRANS['en'])
            title   = target.get('msg_title_language_changed', 'Language Changed')
            message = target.get('msg_restart_lang', 'Language changed. Please restart BadWords.')
            ok_text = target.get('btn_ok', 'OK')
            self.accept()
            CustomMsgBox(self.parent(), title, message, ok_text).exec()

        self.dropdown_lang.valueChanged.connect(_on_lang_changed)
        _add_row(form_gen, self.txt("lbl_language"), self.dropdown_lang,
                 'English', self.dropdown_lang.setText)

        # Theme
        self.combo_theme = QComboBox()
        self.combo_theme.addItems([self.txt("opt_dark"), self.txt("opt_light")])
        current_theme = prefs.get('theme', 'dark')
        self.combo_theme.setCurrentIndex(0 if current_theme == 'dark' else 1)
        _add_row(form_gen, self.txt("lbl_theme"), self.combo_theme,
                 0, self.combo_theme.setCurrentIndex)

        l_gen.addLayout(form_gen)

        # ── Import / Export (inside General tab) ──────────────────────────
        sep_io = QFrame()
        sep_io.setFrameShape(QFrame.Shape.HLine)
        sep_io.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
        l_gen.addSpacing(12)
        l_gen.addWidget(sep_io)
        l_gen.addSpacing(10)

        io_row = QHBoxLayout()
        io_row.setContentsMargins(0, 0, 0, 0)
        io_row.setSpacing(8)

        btn_import_s = QPushButton(self.txt("btn_import_settings"))
        btn_import_s.setObjectName("btn_ghost_sm")
        btn_import_s.setFixedHeight(28)
        btn_import_s.setCursor(Qt.PointingHandCursor)
        btn_import_s.clicked.connect(self._on_import_settings)
        io_row.addWidget(btn_import_s)

        btn_export_s = QPushButton(self.txt("btn_export_settings"))
        btn_export_s.setObjectName("btn_ghost_sm")
        btn_export_s.setFixedHeight(28)
        btn_export_s.setCursor(Qt.PointingHandCursor)
        btn_export_s.clicked.connect(self._on_export_settings)
        io_row.addWidget(btn_export_s)

        io_row.addStretch()
        l_gen.addLayout(io_row)

        l_gen.addStretch()
        self.stack.addWidget(page_gen)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 1 — AUDIO SYNC
        # ─────────────────────────────────────────────────────────────────
        page_sync = QWidget()
        page_sync.setStyleSheet("background: transparent;")
        l_sync = QVBoxLayout(page_sync)
        l_sync.setContentsMargins(24, 20, 24, 16)
        l_sync.setSpacing(0)
        form_sync = QFormLayout()
        form_sync.setSpacing(14)
        form_sync.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.spin_offset = QDoubleSpinBox()
        self.spin_offset.setRange(-10, 10)
        self.spin_offset.setSingleStep(0.1)
        self.spin_offset.setValue(float(prefs.get('offset', self.DEFAULTS['offset'])))

        self.spin_pad = QDoubleSpinBox()
        self.spin_pad.setRange(0, 5)
        self.spin_pad.setSingleStep(0.1)
        self.spin_pad.setValue(float(prefs.get('pad', self.DEFAULTS['pad'])))

        self.spin_snap = QDoubleSpinBox()
        self.spin_snap.setRange(0, 5)
        self.spin_snap.setSingleStep(0.1)
        self.spin_snap.setValue(float(prefs.get('snap_max', prefs.get('snap_margin', self.DEFAULTS['snap_max']))))

        _add_row(form_sync, self.txt("lbl_offset_s"),   self.spin_offset, self.DEFAULTS['offset'],   self.spin_offset.setValue)
        _add_row(form_sync, self.txt("lbl_padding_s"),  self.spin_pad,    self.DEFAULTS['pad'],       self.spin_pad.setValue)
        _add_row(form_sync, self.txt("lbl_snap_max_s"), self.spin_snap,   self.DEFAULTS['snap_max'],  self.spin_snap.setValue)

        l_sync.addLayout(form_sync)
        l_sync.addStretch()
        self.stack.addWidget(page_sync)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 2 — TRANSCRIPT
        # ─────────────────────────────────────────────────────────────────
        page_transcript = QWidget()
        page_transcript.setStyleSheet("background: transparent;")
        l_transcript = QVBoxLayout(page_transcript)
        l_transcript.setContentsMargins(24, 20, 24, 16)
        l_transcript.setSpacing(0)
        form_transcript = QFormLayout()
        form_transcript.setSpacing(14)
        form_transcript.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Display Mode (moved from General)
        self.combo_view = QComboBox()
        self.combo_view.addItems([self.txt("opt_continuous_flow"), self.txt("opt_segmented_blocks")])
        is_seg = prefs.get('view_mode', 'segmented') == 'segmented'
        self.combo_view.setCurrentIndex(1 if is_seg else 0)
        _add_row(form_transcript, self.txt("lbl_display_mode"), self.combo_view,
                 1, self.combo_view.setCurrentIndex)

        # Font family, size, line height
        from PySide6.QtGui import QFontDatabase
        self.combo_font = QComboBox()
        self.combo_font.addItems(QFontDatabase.families())
        self.combo_font.setCurrentText(prefs.get('editor_font_family', self.DEFAULTS['editor_font_family']))

        self.spin_fsize = QSpinBox()
        self.spin_fsize.setRange(8, 48)
        self.spin_fsize.setValue(int(prefs.get('editor_font_size', self.DEFAULTS['editor_font_size'])))

        self.spin_lheight = QSpinBox()
        self.spin_lheight.setRange(0, 40)
        self.spin_lheight.setValue(int(prefs.get('editor_line_height', self.DEFAULTS['editor_line_height'])))

        _add_row(form_transcript, self.txt("lbl_transcript_font"), self.combo_font,
                 self.DEFAULTS['editor_font_family'], self.combo_font.setCurrentText)
        _add_row(form_transcript, self.txt("lbl_font_size_pt"),    self.spin_fsize,
                 self.DEFAULTS['editor_font_size'],   self.spin_fsize.setValue)
        _add_row(form_transcript, self.txt("lbl_line_spacing_px"), self.spin_lheight,
                 self.DEFAULTS['editor_line_height'], self.spin_lheight.setValue)
        l_transcript.addLayout(form_transcript)

        # Font preview
        self.lbl_preview = QLabel(self.txt("lbl_font_preview"))
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumHeight(60)
        self.lbl_preview.setStyleSheet(f"background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px; color: {config.FG_COLOR};")
        l_transcript.addSpacing(10)
        l_transcript.addWidget(self.lbl_preview)

        # Separator before chunking settings
        sep_chunk = QFrame()
        sep_chunk.setFrameShape(QFrame.Shape.HLine)
        sep_chunk.setStyleSheet("background-color: #3a3a3a; max-height: 1px; border: none;")
        l_transcript.addSpacing(12)
        l_transcript.addWidget(sep_chunk)
        l_transcript.addSpacing(10)

        # Chunking spinboxes
        form_chunk = QFormLayout()
        form_chunk.setSpacing(14)
        form_chunk.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.spin_chunk_max = QSpinBox()
        self.spin_chunk_max.setRange(5, 200)
        self.spin_chunk_max.setValue(int(prefs.get('chunk_max_words', 30)))
        _add_row(form_chunk, self.txt("lbl_chunk_max_words"), self.spin_chunk_max, 30, self.spin_chunk_max.setValue)

        self.spin_chunk_look = QSpinBox()
        self.spin_chunk_look.setRange(0, 20)
        self.spin_chunk_look.setValue(int(prefs.get('chunk_lookahead', 3)))
        _add_row(form_chunk, self.txt("lbl_chunk_lookahead"), self.spin_chunk_look, 3, self.spin_chunk_look.setValue)

        self.spin_chunk_min = QSpinBox()
        self.spin_chunk_min.setRange(1, 50)
        self.spin_chunk_min.setValue(int(prefs.get('chunk_min_chars', 7)))
        _add_row(form_chunk, self.txt("lbl_chunk_min_chars"), self.spin_chunk_min, 7, self.spin_chunk_min.setValue)

        l_transcript.addLayout(form_chunk)
        l_transcript.addStretch()

        # Enable/disable chunk spinboxes based on view mode
        def _update_chunk_state(idx):
            enabled = (idx == 1)  # 1 = Segmented
            self.spin_chunk_max.setEnabled(enabled)
            self.spin_chunk_look.setEnabled(enabled)
            self.spin_chunk_min.setEnabled(enabled)
        self.combo_view.currentIndexChanged.connect(_update_chunk_state)
        _update_chunk_state(self.combo_view.currentIndex())

        self.combo_font.currentTextChanged.connect(self._update_preview)
        self.spin_fsize.valueChanged.connect(self._update_preview)
        self.spin_lheight.valueChanged.connect(self._update_preview)
        self._update_preview()
        self.stack.addWidget(page_transcript)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 3 — AI ENGINE
        # ─────────────────────────────────────────────────────────────────
        page_ai = QWidget()
        page_ai.setStyleSheet("background: transparent;")
        l_ai = QVBoxLayout(page_ai)
        l_ai.setContentsMargins(24, 20, 24, 16)
        l_ai.setSpacing(0)
        form_ai = QFormLayout()
        form_ai.setSpacing(14)
        form_ai.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Device
        _device_items = ["Auto", "CPU", "GPU"]
        self.dropdown_device = CustomDropdown(_device_items)
        self.dropdown_device.setFixedHeight(30)
        saved_device = prefs.get('device', 'auto').capitalize()
        if saved_device.upper() == 'AUTO': saved_device = 'Auto'
        self.dropdown_device.setText(saved_device if saved_device in _device_items else 'Auto')
        _add_row(form_ai, self.txt("lbl_device"), self.dropdown_device, 'Auto', self.dropdown_device.setText)

        # Compute type
        _compute_items = ["float16", "int8", "float32"]
        self.dropdown_compute = CustomDropdown(_compute_items)
        self.dropdown_compute.setFixedHeight(30)
        saved_compute = prefs.get('ai_compute_type', 'float16')
        self.dropdown_compute.setText(saved_compute if saved_compute in _compute_items else 'float16')
        _add_row(form_ai, self.txt("lbl_compute_type"), self.dropdown_compute, 'float16', self.dropdown_compute.setText)

        l_ai.addLayout(form_ai)
        l_ai.addSpacing(14)

        # Initial prompt label + QTextEdit
        lbl_prompt = QLabel(self.txt("lbl_initial_prompt"))
        lbl_prompt.setStyleSheet(f"color: {config.NOTE_COL}; font-size: 9pt; background: transparent;")
        l_ai.addWidget(lbl_prompt)
        l_ai.addSpacing(4)

        self.textedit_prompt = QTextEdit()
        self.textedit_prompt.setMaximumHeight(80)
        self.textedit_prompt.setPlaceholderText("e.g. Transcribe film dialogue with punctuation.")
        self.textedit_prompt.setPlainText(prefs.get('ai_initial_prompt', config.DEFAULT_WHISPER_PROMPT))
        self.textedit_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3a3a3a;
                border-radius: 3px;
                padding: 6px 8px;
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
            }}
        """)
        l_ai.addWidget(self.textedit_prompt)
        l_ai.addStretch()
        self.stack.addWidget(page_ai)

        # ─────────────────────────────────────────────────────────────────
        # PAGE 3 — INTERFACE
        # ─────────────────────────────────────────────────────────────────
        page_iface = QWidget()
        page_iface.setStyleSheet("background: transparent;")
        l_iface = QVBoxLayout(page_iface)
        l_iface.setContentsMargins(24, 20, 24, 16)
        l_iface.setSpacing(0)
        form_iface = QFormLayout()
        form_iface.setSpacing(14)
        form_iface.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Always on top
        self.chk_ontop = QCheckBox()
        self.chk_ontop.setChecked(bool(prefs.get('always_on_top', True)))
        _add_row(form_iface, self.txt("lbl_always_on_top"), self.chk_ontop,
                 False, self.chk_ontop.setChecked)

        # Hidden panels (multi-select)
        _panel_options = ["Script Analysis", "Silence", "Filler Words", "Assembly"]
        self.dropdown_hidden = MultiSelectDropdown(_panel_options)
        self.dropdown_hidden.setFixedHeight(30)
        saved_hidden = prefs.get('hidden_panels', [])
        if isinstance(saved_hidden, list) and saved_hidden:
            self.dropdown_hidden.selected_items = set(saved_hidden)
            self.dropdown_hidden.setText(", ".join(sorted(saved_hidden)))
        else:
            self.dropdown_hidden.setText(self.txt("txt_select"))
        _add_row(form_iface, self.txt("lbl_hidden_panels"), self.dropdown_hidden,
                 [], lambda v: None)  # revert placeholder — clear handled by Restore Defaults

        l_iface.addLayout(form_iface)
        l_iface.addStretch()
        self.stack.addWidget(page_iface)

        # ─────────────────────────────────────────────────────────────────
        # BOTTOM BUTTON BAR (separator + row)
        # ─────────────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {config.SEPARATOR_COL}; max-height: 1px; border: none;")
        right_layout.addWidget(sep)

        btn_bar = QHBoxLayout()
        btn_bar.setContentsMargins(16, 10, 16, 12)
        btn_bar.setSpacing(8)

        btn_bar.addStretch()

        # Right: Restore / Close / Apply
        btn_restore = QPushButton(self.txt("btn_restore_defaults"))
        btn_restore.setObjectName("btn_secondary")
        btn_restore.setFixedHeight(30)
        btn_restore.setCursor(Qt.PointingHandCursor)
        btn_restore.clicked.connect(self._restore_all_defaults)
        btn_bar.addWidget(btn_restore)

        btn_close = QPushButton(self.txt("btn_close"))
        btn_close.setObjectName("btn_secondary")
        btn_close.setFixedWidth(80)
        btn_close.setFixedHeight(30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_bar.addWidget(btn_close)

        btn_apply = QPushButton(self.txt("btn_apply"))
        btn_apply.setObjectName("btn_apply")
        btn_apply.setFixedWidth(90)
        btn_apply.setFixedHeight(30)
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.clicked.connect(self._apply_settings)
        btn_bar.addWidget(btn_apply)

        right_layout.addLayout(btn_bar)

    # ── Helpers ───────────────────────────────────────────────────────────

    def _restore_all_defaults(self):
        msg_box = CustomMsgBox(self, self.txt("msg_restore_title"), self.txt("msg_restore_desc"),
                               self.txt("btn_yes"), self.txt("btn_no"))
        if msg_box.exec() == QDialog.Accepted:
            for f in self.revert_funcs:
                f()

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
        """)
        px_size = int(fs * 1.33)
        total_lh = px_size + lh
        self.lbl_preview.setText(
            f'<div style="line-height: {total_lh}px; text-align: center;">Aa<br>Bb</div>'
        )

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

    def _apply_settings(self):
        old_prefs = self.engine.load_preferences() or {}

        # Gather current UI state
        theme_val    = 'dark' if self.combo_theme.currentIndex() == 0 else 'light'
        view_val     = 'segmented' if self.combo_view.currentIndex() == 1 else 'continuous'
        hidden_items = sorted(self.dropdown_hidden.selected_items)
        device_val   = self.dropdown_device.text().lower()
        compute_val  = self.dropdown_compute.text()

        new_prefs = {
            'theme':              theme_val,
            'view_mode':          view_val,
            'offset':             self.spin_offset.value(),
            'pad':                self.spin_pad.value(),
            'snap_max':           self.spin_snap.value(),
            'editor_font_family': self.combo_font.currentText(),
            'editor_font_size':   self.spin_fsize.value(),
            'editor_line_height': self.spin_lheight.value(),
            'chunk_max_words':    self.spin_chunk_max.value(),
            'chunk_lookahead':    self.spin_chunk_look.value(),
            'chunk_min_chars':    self.spin_chunk_min.value(),
            'device':             device_val,
            'ai_compute_type':    compute_val,
            'compute_type':       compute_val,  # keep legacy alias in sync
            'ai_initial_prompt':  self.textedit_prompt.toPlainText(),
            'always_on_top':      self.chk_ontop.isChecked(),
            'hidden_panels':      hidden_items,
        }

        # Detect which restart-required keys actually changed
        restart_needed = any(
            new_prefs.get(k) != old_prefs.get(k)
            for k in config.RESTART_REQUIRED_KEYS
            if k in new_prefs
        )

        self.engine.save_preferences(new_prefs)

        # Real-time canvas update
        main_win = self.parent()
        if hasattr(main_win, 'text_canvas'):
            main_win.text_canvas._calculate_layout()
            main_win.text_canvas.update()

        # Always-on-top: apply immediately
        aot_changed = new_prefs['always_on_top'] != bool(old_prefs.get('always_on_top', False))
        if aot_changed and main_win:
            flags = main_win.windowFlags()
            if new_prefs['always_on_top']:
                main_win.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            else:
                main_win.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            main_win.show()

        # Restart notification
        if restart_needed:
            lang = old_prefs.get('gui_lang', 'en')
            target = config.TRANS.get(lang, config.TRANS['en'])
            CustomMsgBox(
                self,
                target.get('msg_title_language_changed', 'Restart Required'),
                target.get('msg_restart_lang', 'Some changes require a restart to take full effect.'),
                target.get('btn_ok', 'OK')
            ).exec()



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
        self.engine.os_doc.force_dark_titlebar(int(self.winId()))

        # --- Global QSS ---
        self.setStyleSheet(f"""
            * {{ outline: none; }}
            QMainWindow {{
                background-color: {config.BG_COLOR};
            }}
            QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}";
                font-size: 10pt;
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
        
        self._bind_prefs()

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
            if 'ui_spin_thresh' in prefs:
                self.spin_thresh.setValue(prefs['ui_spin_thresh'])
            self.spin_thresh.valueChanged.connect(lambda v: self._save_single_pref('ui_spin_thresh', v))
            
        if hasattr(self, 'spin_pad'):
            if 'ui_spin_pad' in prefs:
                self.spin_pad.setValue(prefs['ui_spin_pad'])
            self.spin_pad.valueChanged.connect(lambda v: self._save_single_pref('ui_spin_pad', v))
        
        # Restore pinned favorites
        for fav_id in prefs.get('favorites', []):
            if fav_id in self._pin_buttons:
                self._pin_buttons[fav_id].setStyleSheet("QPushButton { background: transparent; border: none; color: #eebb00; font-size: 11pt; padding: 0; } QPushButton:hover { color: #ffcc00; }")
                self._pin_buttons[fav_id].click()

    def resizeEvent(self, event):
        super().resizeEvent(event)

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
        
        self.btn_nav_quit = SidebarButton("\u2716", self.txt("tool_quit"), "quit", tooltip_widget=self.shared_tooltip, is_draggable=False)
        self.btn_nav_quit.clicked.connect(self.close)
        left_layout.addWidget(self.btn_nav_quit)
        
        self.btn_nav_settings = SidebarButton("\u2699", self.txt("tool_settings"), "settings", tooltip_widget=self.shared_tooltip, is_draggable=False)
        self.btn_nav_settings.clicked.connect(self._on_settings)
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
        self._main_h_splitter.setStretchFactor(0, 0)
        self._main_h_splitter.setStretchFactor(1, 1)
        self._main_h_splitter.setStretchFactor(2, 0)
        self._main_h_splitter.setHandleWidth(10)
        self._main_h_splitter.setStyleSheet("QSplitter { border: none; background: transparent; }")

        # Add everything to main layout in exact order
        main_layout.addWidget(self._sidebar_left)
        main_layout.addWidget(self._main_h_splitter)
        main_layout.addWidget(self._sidebar_right)

        self.setCentralWidget(main_container)

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
                target_w = 280
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
        def _wrap_activity(widget: QWidget) -> QFrame:
            container = QFrame()
            container.setObjectName("ActivityPanel")
            container.setAttribute(Qt.WA_StyledBackground, True)

            container.setStyleSheet("""
                QFrame#ActivityPanel {
                    background-color: #212121;
                    border-radius: 0px;
                    margin: 0px;
                    border: none;
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
        self.text_script.setAcceptRichText(False)
        self.text_script.setPlaceholderText(self.txt("ph_paste_script_here"))
        l_script_analysis.addWidget(self.text_script)
        
        btn_row_script = QHBoxLayout()
        self.btn_import_script = QPushButton(self.txt("btn_import_script"))
        self.btn_import_script.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_script = QPushButton(self.txt("btn_clear"))
        self.btn_clear_script.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_row_script.addWidget(self.btn_import_script)
        btn_row_script.addWidget(self.btn_clear_script)
        l_script_analysis.addLayout(btn_row_script)
        
        self.btn_analyze_compare = QPushButton(self.txt("btn_analyze_compare"))
        self.btn_analyze_compare.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze_compare.setFixedHeight(35)
        self.btn_analyze_compare.setStyleSheet(f"background-color: {config.BTN_BG}; color: white; font-weight: bold; font-size: 12pt; border: none; border-radius: 4px; padding: 10px;")
        l_script_analysis.addWidget(self.btn_analyze_compare)
        
        self._analyze_color_anim = QVariantAnimation(self)
        self._analyze_color_anim.setDuration(250)

        def update_btn_style(color):
            self.btn_analyze_compare.setStyleSheet(f"QPushButton {{ background-color: {color.name()}; border: 1px solid #111; border-radius: 4px; color: #fff; font-weight: bold; padding: 8px; }}")
        self._analyze_color_anim.valueChanged.connect(update_btn_style)
        
        self.btn_analyze_standalone = QPushButton(self.txt("btn_analyze_standalone"))
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
        form_silence.addRow(self.txt("lbl_threshold_db"), self.spin_thresh)
        form_silence.addRow(self.txt("lbl_padding_s"), self.spin_pad)
        l_silence.addLayout(form_silence)
        
        row_silence_cut = QHBoxLayout()
        lbl_cut = QLabel(self.txt("lbl_detect_and_cut_silence"))
        lbl_cut.setWordWrap(True)
        row_silence_cut.addWidget(lbl_cut)
        row_silence_cut.addStretch()
        self.tgl_silence_cut = ToggleSwitch()
        row_silence_cut.addWidget(self.tgl_silence_cut)
        l_silence.addLayout(row_silence_cut)
        
        row_silence_mark = QHBoxLayout()
        lbl_mark = QLabel(self.txt("lbl_detect_and_mark_silence"))
        lbl_mark.setWordWrap(True)
        row_silence_mark.addWidget(lbl_mark)
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
        # Inline Filler Words Editor
        prefs = self.engine.load_preferences() or {}
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        
        self.txt_fillers = QTextEdit()
        self.txt_fillers.setAcceptRichText(False)
        self.txt_fillers.setStyleSheet(f"background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3a3a3a; border-radius: 4px; padding: 4px;")
        self.txt_fillers.setText(", ".join(fillers))
        l_fillers.addWidget(self.txt_fillers)
        
        # Bottom tools for fillers (Counter, Reset, Save)
        filler_tools_layout = QHBoxLayout()
        filler_tools_layout.setContentsMargins(0, 2, 0, 0)
        
        self.lbl_filler_count = QLabel(self.txt("lbl_words"))
        self.lbl_filler_count.setStyleSheet("color: #888888; font-size: 9pt;")
        filler_tools_layout.addWidget(self.lbl_filler_count)
        
        filler_tools_layout.addStretch()
        
        self.btn_reset_fillers = QPushButton("↺")
        self.btn_reset_fillers.setFixedSize(24, 24)
        self.btn_reset_fillers.setCursor(Qt.PointingHandCursor)
        self.btn_reset_fillers.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 3px; color: #888;")
        self.btn_reset_fillers.clicked.connect(self._on_reset_inline_fillers)
        filler_tools_layout.addWidget(self.btn_reset_fillers)
        
        self.btn_save_fillers = QPushButton(self.txt("btn_save"))
        self.btn_save_fillers.setCursor(Qt.PointingHandCursor)
        self.btn_save_fillers.setStyleSheet(f"background-color: {config.BTN_GHOST_BG}; color: {config.FG_COLOR}; border-radius: 4px; font-weight: bold; padding: 4px 10px;")
        self.btn_save_fillers.clicked.connect(self._on_save_inline_fillers)
        filler_tools_layout.addWidget(self.btn_save_fillers)
        l_fillers.addLayout(filler_tools_layout)
        
        # Connect text changed signal for auto-resize and counting
        self.txt_fillers.textChanged.connect(self._on_fillers_text_changed)
        
        # Force initial calculation
        self._on_fillers_text_changed()
        
        row_auto_filler = QHBoxLayout()
        row_auto_filler.addWidget(QLabel(self.txt("lbl_mark_filler_words_automat")))
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
        row_marking_title.addWidget(QLabel(self.txt("lbl_marking_mode")))
        row_marking_title.addStretch()
        self.btn_clear_transcript = QPushButton("🧹")
        self.btn_clear_transcript.setFixedSize(26, 26)
        self.btn_clear_transcript.setToolTip("") # Force remove native tooltip
        self.btn_clear_transcript.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_transcript.setStyleSheet("background: transparent; border: none; font-size: 12pt; padding: 2px;")
        self.btn_clear_transcript.clicked.connect(self._on_clear_transcript)
        row_marking_title.addWidget(self.btn_clear_transcript)
        l_main.addLayout(row_marking_title)
        
        self.rb_red = QRadioButton(self.txt("rad_red_cut_filler"))
        self.rb_red.setChecked(True)
        self.rb_red.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_red, config.WORD_BAD_BG)
        l_main.addWidget(self.rb_red)
        
        self.rb_blue = QRadioButton(self.txt("rad_blue_retake"))
        self.rb_blue.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_blue, config.WORD_REPEAT_BG)
        l_main.addWidget(self.rb_blue)
        
        self.rb_green = QRadioButton(self.txt("rad_green_typo"))
        self.rb_green.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_green, config.WORD_TYPO_BG)
        l_main.addWidget(self.rb_green)
        
        self.rb_eraser = QRadioButton(self.txt("rad_eraser_clear"))
        self.rb_eraser.setCursor(Qt.CursorShape.PointingHandCursor)
        style_rb(self.rb_eraser, "#ffffff")
        l_main.addWidget(self.rb_eraser)
        
        lbl_dummy = QLabel(self.txt("lbl_add_custom_marker"))
        lbl_dummy.setStyleSheet("color: #808080; font-size: 9pt; text-decoration: underline;")
        l_main.addWidget(lbl_dummy)
        
        # Middle
        l_main.addStretch(1)
        
        # Favorites section
        lbl_favs = QLabel(self.txt("lbl_pinned_favorites"))
        lbl_favs.setStyleSheet("color: #888888; font-size: 8pt; font-weight: bold; text-transform: uppercase;")
        l_main.addWidget(lbl_favs)
        
        self.layout_favorites = QVBoxLayout()
        self.layout_favorites.setSpacing(10)
        l_main.addLayout(self.layout_favorites)
        
        # Bottom Section removed!
        
        row_proj = QHBoxLayout()
        self.btn_import_proj = QPushButton(self.txt("btn_import_project"))
        self.btn_import_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_proj = QPushButton(self.txt("btn_export_project"))
        self.btn_export_proj.setCursor(Qt.CursorShape.PointingHandCursor)
        row_proj.addWidget(self.btn_import_proj)
        row_proj.addWidget(self.btn_export_proj)
        l_main.addLayout(row_proj)
        
        self.btn_assemble = QPushButton(self.txt("btn_assemble"))
        self.btn_assemble.setFixedHeight(35)
        self.btn_assemble.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_assemble.setStyleSheet("QPushButton { background-color: #11703c; color: white; font-weight: bold; border-radius: 4px; border: 1px solid #0a4d28; } QPushButton:hover { background-color: #168f4d; } QPushButton:pressed { background-color: #0d5c31; }")
        l_main.addWidget(self.btn_assemble)
        
        self.activities["main_panel"] = _wrap_activity(p_main)
        
        self._favorite_proxies = {}
        self._pin_buttons = {}
        
        # E. assembly
        p_assembly = QWidget()
        l_assembly = QVBoxLayout(p_assembly)
        l_assembly.setContentsMargins(15, 15, 15, 15)
        l_assembly.setSpacing(15)
        
        def _pin_btn(fav_id: str):
            btn = QPushButton("★")
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #555555; font-size: 11pt; padding: 0; } QPushButton:hover { color: #aaaaaa; }")
            self._pin_buttons[fav_id] = btn
            return btn
        
        row_show_inaudible = QHBoxLayout()
        lbl_show_inaud = QLabel(self.txt("lbl_show_inaudible_fragments"))
        lbl_show_inaud.setWordWrap(True)
        row_show_inaudible.addWidget(lbl_show_inaud)
        row_show_inaudible.addStretch()
        self.tgl_show_inaudible = ToggleSwitch()
        self.tgl_show_inaudible.setChecked(True)
        self.tgl_show_inaudible.toggled.connect(self._on_inaudible_toggled)
        row_show_inaudible.addWidget(self.tgl_show_inaudible)
        pin_show_inaud = _pin_btn('show_inaudible')
        row_show_inaudible.addWidget(pin_show_inaud)
        l_assembly.addLayout(row_show_inaudible)
        pin_show_inaud.clicked.connect(lambda: self._toggle_favorite('show_inaudible', self.tgl_show_inaudible, self.txt("tool_show_inaudible"), pin_show_inaud))
        
        row_mark_inaudible = QHBoxLayout()
        lbl_mark_inaud = QLabel(self.txt("lbl_mark_inaudible_fragments"))
        lbl_mark_inaud.setWordWrap(True)
        row_mark_inaudible.addWidget(lbl_mark_inaud)
        row_mark_inaudible.addStretch()
        self.tgl_mark_inaudible = ToggleSwitch()
        self.tgl_mark_inaudible.toggled.connect(self._on_mark_inaudible_toggled)
        row_mark_inaudible.addWidget(self.tgl_mark_inaudible)
        pin_mark_inaud = _pin_btn('mark_inaudible')
        row_mark_inaudible.addWidget(pin_mark_inaud)
        l_assembly.addLayout(row_mark_inaudible)
        pin_mark_inaud.clicked.connect(lambda: self._toggle_favorite('mark_inaudible', self.tgl_mark_inaudible, self.txt("tool_mark_inaudible"), pin_mark_inaud))
        
        row_show_typos = QHBoxLayout()
        lbl_show_typos = QLabel(self.txt("lbl_show_detected_typos"))
        lbl_show_typos.setWordWrap(True)
        row_show_typos.addWidget(lbl_show_typos)
        row_show_typos.addStretch()
        self.tgl_show_typos = ToggleSwitch()
        self.tgl_show_typos.setChecked(True)
        self.tgl_show_typos.toggled.connect(self._on_typos_toggled)
        row_show_typos.addWidget(self.tgl_show_typos)
        pin_show_typos = _pin_btn('show_typos')
        row_show_typos.addWidget(pin_show_typos)
        l_assembly.addLayout(row_show_typos)
        pin_show_typos.clicked.connect(lambda: self._toggle_favorite('show_typos', self.tgl_show_typos, self.txt("tool_show_typos"), pin_show_typos))
        
        row_ripple_delete = QHBoxLayout()
        lbl_ripple = QLabel(self.txt("lbl_ripple_delete_red_clips"))
        lbl_ripple.setWordWrap(True)
        row_ripple_delete.addWidget(lbl_ripple)
        row_ripple_delete.addStretch()
        self.tgl_ripple_delete = ToggleSwitch()
        row_ripple_delete.addWidget(self.tgl_ripple_delete)
        pin_ripple = _pin_btn('ripple_delete')
        row_ripple_delete.addWidget(pin_ripple)
        l_assembly.addLayout(row_ripple_delete)
        pin_ripple.clicked.connect(lambda: self._toggle_favorite('ripple_delete', self.tgl_ripple_delete, self.txt("tool_ripple_delete"), pin_ripple))
        
        l_assembly.addStretch(1)
        self.activities["assembly"] = _wrap_activity(p_assembly)
        
        self.btn_analyze_standalone.installEventFilter(self)
        self.btn_clear_transcript.installEventFilter(self)

        # Signal Connections
        self.btn_import_script.clicked.connect(self._on_import_script)
        self.btn_clear_script.clicked.connect(self._on_clear_script)
        self.btn_analyze_compare.clicked.connect(self._on_analyze_compare)
        self.btn_analyze_standalone.clicked.connect(self._on_analyze_standalone)
        self.tgl_auto_filler.toggled.connect(self._on_auto_filler_toggled)
        
        # Right Panel Signals
        self.btn_assemble.clicked.connect(self._on_assemble)
        self.btn_import_proj.clicked.connect(self._on_import_project)
        self.btn_export_proj.clicked.connect(self._on_export_project)
        
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            if watched == getattr(self, 'btn_analyze_standalone', None):
                self.shared_tooltip.show_at(watched, self.txt("tooltip_dev"), is_right_side=False)
            elif watched == getattr(self, 'btn_clear_transcript', None):
                # CRITICAL: is_right_side=True forces it to render to the left of the button!
                self.shared_tooltip.show_at(watched, self.txt("tooltip_clear_all_markings"), is_right_side=True)
        elif event.type() == QEvent.Type.Leave:
            if watched in (getattr(self, 'btn_analyze_standalone', None), getattr(self, 'btn_clear_transcript', None)):
                self.shared_tooltip.hide()
                
        return super().eventFilter(watched, event)


    # Removed deprecated _on_nav_script and _on_nav_analysis

    # ------------------------------------------------------------------
    # UI Logic Methods
    # ------------------------------------------------------------------

    def _on_import_script(self):
        from PySide6.QtWidgets import QFileDialog
        import algorythms
        
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
            if hasattr(algorythms, 'read_docx_text'):
                content = algorythms.read_docx_text(file_path)
        elif ext == 'pdf':
            if hasattr(algorythms, 'read_pdf_text'):
                content = algorythms.read_pdf_text(file_path)
            
        self.text_script.setText(content)

    def _on_clear_script(self):
        self.text_script.clear()

    def _on_analyze_compare(self):
        from PySide6.QtWidgets import QMessageBox
        script_text = self.text_script.toPlainText().strip()
        if not script_text:
            QMessageBox.warning(self, self.txt("msg_warning"), self.txt("msg_please_import_or_paste_a"))
            return
            
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            QMessageBox.warning(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"))
            return
            
        # Run comparison via engine and overwrite canvas data
        updated_words = self.engine.run_comparison_analysis(script_text, self.text_canvas.words_data)
        self.text_canvas.load_data(updated_words)

    def _on_analyze_standalone(self):
        from PySide6.QtWidgets import QMessageBox
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            QMessageBox.warning(self, self.txt("msg_warning"), self.txt("msg_no_active_transcription_t"))
            return
            
        prefs = self.engine.load_preferences() or {}
        show_inaudible = prefs.get('show_inaudible', True)
        
        # Standalone analysis returns a tuple: (processed_words, count)
        updated_words, _ = self.engine.run_standalone_analysis(self.text_canvas.words_data, show_inaudible)
        self.text_canvas.load_data(updated_words)

    def _on_auto_filler_toggled(self, is_checked):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        import algorythms
        prefs = self.engine.load_preferences() or {}
        fillers = prefs.get('filler_words', config.DEFAULT_BAD_WORDS)
        
        # Apply filler logic directly to the current state
        if hasattr(algorythms, 'apply_auto_filler_logic'):
            updated_words = algorythms.apply_auto_filler_logic(self.text_canvas.words_data, fillers, is_checked)
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
            import algorythms
            if hasattr(algorythms, 'apply_auto_filler_logic'):
                updated_words = algorythms.apply_auto_filler_logic(self.text_canvas.words_data, new_fillers, True)
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

    def _on_export_project(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        from PySide6.QtWidgets import QFileDialog
        import time, os
        
        saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
        os.makedirs(saves_dir, exist_ok=True)
        
        # SMART TIMELINE NAMING
        timeline_name = "Project"
        try:
            if hasattr(self, 'resolve_handler') and self.resolve_handler:
                project = self.resolve_handler.project_manager.GetCurrentProject()
                if project:
                    timeline_name = project.GetName()
                    tl = project.GetCurrentTimeline()
                    if tl:
                        timeline_name = tl.GetName()
        except Exception:
            pass
        safe_name = "".join([c for c in timeline_name if c.isalpha() or c.isdigit() or c in ' -_']).rstrip()
        default_filename = f"BadWords_{safe_name}.json"
        
        path, _ = QFileDialog.getSaveFileName(self, "Export Project", os.path.join(saves_dir, default_filename), "JSON Files (*.json)")
        if not path: return
        
        prefs = self.engine.load_preferences() or {}

        # GATHER ACTIVE PANELS (Using correct attribute names)
        active_panels = []
        nav_btns = [
            getattr(self, 'btn_nav_script',   None), getattr(self, 'btn_nav_silence', None),
            getattr(self, 'btn_nav_fillers',  None), getattr(self, 'btn_nav_main',    None),
            getattr(self, 'btn_nav_assembly', None)
        ]
        for btn in nav_btns:
            if btn and getattr(btn, 'is_active', False):
                active_panels.append(btn.activity_id)

        # SMUGGLE LAYOUT DATA INTO PREFS TO BYPASS ENGINE RESTRICTIONS
        prefs['ui_active_panels']  = active_panels
        prefs['ui_splitter_sizes'] = self._main_h_splitter.sizes() if hasattr(self, '_main_h_splitter') else []

        clean_words = self._get_clean_words_data()

        data_packet = {
            "lang_code":      prefs.get('lang', 'Auto'),
            "settings":       prefs,
            "filler_words":   prefs.get('filler_words', config.DEFAULT_BAD_WORDS),
            "words_data":     clean_words,
            "script_content": getattr(self, 'text_script', None).toPlainText() if hasattr(self, 'text_script') else ""
        }
        # Note: layout state is inside 'settings', not at the root level
        self.engine.save_project_state(path, data_packet)

    def _on_import_project(self):
        try:
            from PySide6.QtWidgets import QFileDialog, QApplication
            import os
            
            saves_dir = os.path.join(self.engine.os_doc.install_dir, "saves")
            os.makedirs(saves_dir, exist_ok=True)
            
            path, _ = QFileDialog.getOpenFileName(self, "Import Project", saves_dir, "JSON Files (*.json)")
            if not path: return
            
            state, _ = self.engine.load_project_state(path)

            from PySide6.QtCore import QTimer

            # --- 1. SYNC UI PREFERENCES ---
            imported_prefs = state.get('settings', {})
            if imported_prefs:
                self.engine.save_preferences(imported_prefs)

                # Update Toggle Switches
                toggles = [
                    ('ui_tgl_silence_cut',    getattr(self, 'tgl_silence_cut',    None)),
                    ('ui_tgl_silence_mark',   getattr(self, 'tgl_silence_mark',   None)),
                    ('ui_tgl_show_inaudible', getattr(self, 'tgl_show_inaudible', None)),
                    ('ui_tgl_mark_inaudible', getattr(self, 'tgl_mark_inaudible', None)),
                    ('ui_tgl_show_typos',     getattr(self, 'tgl_show_typos',     None)),
                    ('ui_tgl_ripple_delete',  getattr(self, 'tgl_ripple_delete',  None)),
                    ('ui_tgl_auto_filler',    getattr(self, 'tgl_auto_filler',    None)),
                ]
                for key, widget in toggles:
                    if widget and key in imported_prefs:
                        widget.setChecked(imported_prefs[key], animated=False)

                # Update SpinBoxes
                if hasattr(self, 'spin_thresh') and 'ui_spin_thresh' in imported_prefs:
                    self.spin_thresh.setValue(imported_prefs['ui_spin_thresh'])
                if hasattr(self, 'spin_pad') and 'ui_spin_pad' in imported_prefs:
                    self.spin_pad.setValue(imported_prefs['ui_spin_pad'])

                # Restore pinned favorites visually
                for fav_id in imported_prefs.get('favorites', []):
                    if hasattr(self, '_pin_buttons') and fav_id in self._pin_buttons:
                        if not hasattr(self, '_favorite_proxies') or fav_id not in self._favorite_proxies:
                            self._pin_buttons[fav_id].click()

            # Restore Script
            if hasattr(self, 'text_script') and 'script_content' in state:
                self.text_script.setText(state['script_content'])

            # --- 2. SWITCH TO EDITOR CONTEXT ---
            if hasattr(self, 'go_to_page'):
                self.go_to_page(2)

            # EXTRACT SMUGGLED UI STATE FROM PREFS
            saved_panels = imported_prefs.get('ui_active_panels', [])
            saved_sizes  = imported_prefs.get('ui_splitter_sizes', [])

            # --- 3. BULLETPROOF PANEL RESTORATION ---
            if hasattr(self, '_panel_left'):  self._panel_left.hide()
            if hasattr(self, '_panel_right'): self._panel_right.hide()

            # STRICT MAPPING: exact activity_id string -> actual button instance
            nav_map = {
                'script_analysis': getattr(self, 'btn_nav_script',   None),
                'silence':         getattr(self, 'btn_nav_silence',  None),
                'fillers':         getattr(self, 'btn_nav_fillers',  None),
                'main_panel':      getattr(self, 'btn_nav_main',     None),
                'assembly':        getattr(self, 'btn_nav_assembly', None),
            }

            # Force all buttons off safely
            for act_id, btn in nav_map.items():
                if btn:
                    btn.is_active = False
                    btn.style().unpolish(btn)
                    btn.style().polish(btn)

            QApplication.processEvents()

            # Forcefully trigger saved panels
            for act_id in saved_panels:
                if act_id in nav_map and nav_map[act_id] is not None:
                    self._toggle_activity(act_id)

            QApplication.processEvents()

            # Load Words Data
            if hasattr(self, 'text_canvas'):
                self.text_canvas.load_data(state.get('words_data', []))

            # Apply splitter sizes
            if saved_sizes and hasattr(self, '_main_h_splitter'):
                QTimer.singleShot(150, lambda: self._main_h_splitter.setSizes(saved_sizes))
        except Exception as e:
            from osdoc import log_error
            log_error(f"Failed to load project: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to load project: {e}")

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
            
        # Update settings for the core
        settings = {'threshold_db': thresh_val, 'padding_s': pad_val}

        self._worker_signals = WorkerSignals()
        self._worker_signals.progress.connect(self._on_analysis_progress)
        self._worker_signals.status.connect(self._on_analysis_status)
        # Route to fast-silence-specific finished handler
        self._worker_signals.finished.connect(self._on_fs_finished)
        self._worker_signals.error.connect(self._on_analysis_error)

        def worker_func():
            try:
                words_data, segments_data = self.engine.run_fast_silence_pipeline(
                    settings,
                    callback_status=self._worker_signals.status.emit,
                    callback_progress=self._worker_signals.progress.emit
                )
                self._worker_signals.finished.emit(words_data, segments_data)
            except Exception as e:
                self._worker_signals.error.emit(str(e))

        self._analysis_thread = threading.Thread(target=worker_func, daemon=True)
        self._analysis_thread.start()

    def _on_fs_finished(self, words_data, segments_data):
        """Called when run_fast_silence_pipeline completes. Directly assembles the timeline."""
        from PySide6.QtWidgets import QApplication, QMessageBox

        if not words_data:
            QMessageBox.critical(self, self.txt("msg_fast_silence"), self.txt("msg_no_silence_segments_detec"))
            self.go_to_page(0)
            if hasattr(self, 'welcome_stack'): self.welcome_stack.setCurrentIndex(0)
            return

        self.lbl_processing_status.setText(self.txt("txt_assembling_timeline"))
        QApplication.processEvents()

        fs_prefs = self.engine.load_preferences() or {}
        fs_prefs['silence_cut']  = getattr(self, 'tgl_fs_cut',  None) and self.tgl_fs_cut.isChecked()
        fs_prefs['silence_mark'] = getattr(self, 'tgl_fs_mark', None) and self.tgl_fs_mark.isChecked()

        success, err = self.engine.assemble_timeline(
            words_data, fs_prefs,
            callback_status=self.lbl_processing_status.setText,
            callback_progress=self.bar_processing.set_value
        )

        if success:
            QMessageBox.information(self, self.txt("msg_fast_silence"), self.txt("msg_fast_silence_processing_c"))
        else:
            QMessageBox.critical(self, "Fast Silence Error", f"Assembly failed: {err}")

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
            try: source_toggle.toggled.disconnect(entry['src_conn'])
            except: pass
            try: entry['proxy'].toggled.disconnect(entry['prx_conn'])
            except: pass
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
        else:
            # --- ADD favorite ---
            from PySide6.QtWidgets import QWidget as _QWidget
            row_widget = _QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            row_layout.addWidget(QLabel(label_text))
            row_layout.addStretch()

            proxy_toggle = ToggleSwitch()
            pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #eebb00; font-size: 11pt; padding: 0; } QPushButton:hover { color: #ffcc00; }")
            proxy_toggle.setChecked(source_toggle.isChecked(), animated=False)
            row_layout.addWidget(proxy_toggle)

            self.layout_favorites.addWidget(row_widget)

            # Two-way binding (loop-safe)
            def prx_to_src(v, src=source_toggle, prx=proxy_toggle):
                if src.isChecked() != v: src.setChecked(v)
            def src_to_prx(v, src=source_toggle, prx=proxy_toggle):
                if prx.isChecked() != v: prx.setChecked(v)

            prx_conn = proxy_toggle.toggled.connect(prx_to_src)
            src_conn = source_toggle.toggled.connect(src_to_prx)

            self._favorite_proxies[target_id] = {
                'row_widget': row_widget,
                'proxy': proxy_toggle,
                'prx_conn': prx_conn,
                'src_conn': src_conn,
            }
            pin_btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #f0b429; font-size: 11pt; padding: 0; } QPushButton:hover { color: #f5c842; }")
            # Persist addition
            prefs = self.engine.load_preferences() or {}
            favs = prefs.get('favorites', [])
            if target_id not in favs: favs.append(target_id)
            prefs['favorites'] = favs
            self.engine.save_preferences(prefs)

    def _on_assemble(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data: return
        
        from PySide6.QtWidgets import QApplication
        import copy
        
        prefs = self.engine.load_preferences() or {}
        
        # GATHER UI STATES
        if hasattr(self, 'tgl_silence_cut'): prefs['silence_cut'] = self.tgl_silence_cut.isChecked()
        if hasattr(self, 'tgl_silence_mark'): prefs['silence_mark'] = self.tgl_silence_mark.isChecked()
        if hasattr(self, 'tgl_reviewer'): prefs['enable_reviewer'] = self.tgl_reviewer.isChecked()
        if hasattr(self, 'tgl_ripple_delete'): prefs['auto_del'] = self.tgl_ripple_delete.isChecked()
        if hasattr(self, 'tgl_show_typos'): prefs['show_typos'] = self.tgl_show_typos.isChecked()
        if hasattr(self, 'tgl_mark_inaudible'): prefs['mark_inaudible'] = self.tgl_mark_inaudible.isChecked()
        if hasattr(self, 'tgl_show_inaudible'): prefs['show_inaudible'] = self.tgl_show_inaudible.isChecked()
        
        prefs['mark_tool'] = 'bad'
        if hasattr(self, 'rb_red') and self.rb_red.isChecked(): prefs['mark_tool'] = 'bad'
        elif hasattr(self, 'rb_blue') and self.rb_blue.isChecked(): prefs['mark_tool'] = 'repeat'
        elif hasattr(self, 'rb_green') and self.rb_green.isChecked(): prefs['mark_tool'] = 'typo'
        
        self.engine.save_preferences(prefs)
        
        # UI Prep
        self._panel_left.hide()
        self._panel_right.hide()
        self.go_to_page(1)
        self.lbl_processing_status.setText(self.txt("txt_initializing_assembly"))
        self.bar_processing.set_value(0)
        
        # Force UI update immediately before the heavy processing begins
        QApplication.processEvents()
        
        # SANITIZE EXPORT DATA (Prevents C++ QRect deepcopy memory leaks)
        export_data = self._get_clean_words_data()
        show_typos = prefs.get('show_typos', True)
        mark_inaudible = prefs.get('mark_inaudible', True)
        
        for w in export_data:
            if w.get('status') == 'typo' and not show_typos:
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    w['status'] = None
            if w.get('status') == 'inaudible' and not mark_inaudible:
                w['status'] = None

        from PySide6.QtCore import QEventLoop
        
        # EVENT-PUMP CALLBACKS: Keep UI fluid but block rogue clicks
        def pump_status(msg):
            self.lbl_processing_status.setText(msg)
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

        def pump_progress(val):
            self.bar_processing.set_value(val)
            QApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
            
        # EXECUTE TRULY SYNCHRONOUSLY ON MAIN THREAD
        # We bypass the threaded wrapper and call the core method directly
        success, warning = self.engine.assemble_timeline(
            export_data, 
            prefs, 
            callback_status=pump_status, 
            callback_progress=pump_progress
        )
        
        # AGGRESSIVE RAM CLEANUP: Free memory immediately after assembly finishes
        try:
            del export_data
            import gc
            gc.collect()
        except:
            pass
            
        # HANDLE RESULTS SEQUENTIALLY
        if success:
            self.bar_processing.set_value(100)
            self.lbl_processing_status.setText(self.txt("txt_finishing"))
            QApplication.processEvents()
            self._on_assembly_success()
        else:
            self._on_assembly_error("Assembly failed. Check logs.")

    def _on_assembly_success(self):
        from PySide6.QtWidgets import QMessageBox
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        if hasattr(self, '_panel_left'): self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        QMessageBox.information(self, self.txt("msg_success"), self.txt("msg_timeline_assembled_succes"))

    def _on_assembly_error(self, err_msg):
        from PySide6.QtWidgets import QMessageBox
        if hasattr(self, 'go_to_page'): self.go_to_page(2)
        if hasattr(self, '_panel_left'): self._panel_left.show()
        if hasattr(self, '_panel_right'): self._panel_right.show()
        QMessageBox.critical(self, "Error", err_msg)

    def _build_welcome_screen(self) -> QWidget:
        """
        Page 0 of the main stack: Welcome / Config screen.
        Contains a local QStackedWidget (self.welcome_stack):
          - sub-page 0: Transcription workflow (existing dropdowns + Analyze button)
          - sub-page 1: Fast Silence settings + Run button
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
        inner_layout.setAlignment(Qt.AlignTop)

        # ── Shared Title ─────────────────────────────────────────────────
        lbl_title = QLabel("BadWords", inner)
        lbl_title.setObjectName("welcome_title")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(f"""
            QLabel#welcome_title {{
                color: #ffffff;
                font-size: 34pt;
                font-weight: 900;
                font-family: "{config.UI_FONT_NAME}";
                background: transparent;
                letter-spacing: -2px;
            }}
        """)
        inner_layout.addWidget(lbl_title)
        inner_layout.addSpacing(10)

        # ── Local stacked widget ──────────────────────────────────────────
        self.welcome_stack = QStackedWidget()
        self.welcome_stack.setStyleSheet("background: transparent;")
        inner_layout.addWidget(self.welcome_stack)

        prefs = self.engine.load_preferences() or {}

        def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
            """Label directly above the input."""
            row = QVBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(3)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                f"color: {config.NOTE_COL}; font-size: 9pt;"
                f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
            )
            row.addWidget(lbl)
            row.addWidget(widget)
            return row

        p_transcription = QWidget()
        p_transcription.setStyleSheet("background: transparent;")
        l_trans = QVBoxLayout(p_transcription)
        l_trans.setContentsMargins(0, 0, 0, 0)
        l_trans.setSpacing(0)
        l_trans.setAlignment(Qt.AlignTop)

        lbl_sub = QLabel(self.txt("lbl_transcription_workspace"))
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setFixedHeight(20)
        lbl_sub.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 10pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        l_trans.addWidget(lbl_sub)
        l_trans.addSpacing(20)

        self.combo_tl_0 = CustomDropdown(["Timeline 1", "Timeline 2", "No timelines detected"])
        self.combo_tl_0.setFixedHeight(30)
        l_trans.addLayout(_row(self.txt("lbl_timeline_selection"), self.combo_tl_0))
        l_trans.addSpacing(10)

        self.combo_tr_0 = MultiSelectDropdown(["Audio 1", "Audio 2", "Audio 3", "No audio detected"])
        self.combo_tr_0.setFixedHeight(30)
        l_trans.addLayout(_row(self.txt("lbl_tracks_selection"), self.combo_tr_0))
        l_trans.addSpacing(10)

        # ── Language
        lang_items = list(config.SUPPORTED_LANGUAGES.values())
        self._combo_lang = SearchableDropdown(lang_items)
        self._combo_lang.setFixedHeight(30)
        saved_lang = prefs.get('lang', 'Auto')
        display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
        self._combo_lang.setText(display_name if (display_name in lang_items or display_name == 'Auto') else "Auto")
        self._combo_lang.valueChanged.connect(lambda v: self.engine.save_preferences({"lang": v}))
        l_trans.addLayout(_row(self.txt("lbl_lang"), self._combo_lang))
        l_trans.addSpacing(10)

        # ── Model
        model_items = [
            "Tiny  (Fast, <1 GB)",
            "Base  (Balanced, 1 GB)",
            "Small  (Good, 2 GB)",
            "Medium  (5 GB)",
            "Large Turbo  (Fast & Precise, 6 GB)",
            "Large  (Accurate, 10 GB)",
        ]
        self._combo_model = CustomDropdown(model_items)
        self._combo_model.setFixedHeight(30)
        self._combo_model.setText(prefs["model"] if "model" in prefs and prefs["model"] in model_items else model_items[4])
        self._combo_model.valueChanged.connect(lambda v: self.engine.save_preferences({"model": v}))
        l_trans.addLayout(_row(self.txt("lbl_model"), self._combo_model))
        l_trans.addSpacing(10)

        # ── Device
        device_items = ["Auto", "CPU", "GPU (CUDA)"]
        self._combo_device = CustomDropdown(device_items)
        self._combo_device.setFixedHeight(30)
        self._combo_device.setText(prefs["device"] if "device" in prefs and prefs["device"] in device_items else "Auto")
        self._combo_device.valueChanged.connect(lambda v: self.engine.save_preferences({"device": v}))
        l_trans.addLayout(_row(self.txt("lbl_device"), self._combo_device))
        l_trans.addSpacing(24)

        # ── Action buttons
        btn_row_t = QHBoxLayout()
        btn_row_t.setSpacing(8)

        btn_import = QPushButton(self.txt("btn_import_project"))
        btn_import.setObjectName("btn_ghost")
        btn_import.setCursor(Qt.PointingHandCursor)
        btn_import.setFixedHeight(30)
        btn_import.setStyleSheet(f"""
            QPushButton#btn_ghost {{
                background-color: #1e1e1e; color: {config.FG_COLOR};
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt;
                border: 1px solid #3a3a3a; border-radius: 3px; padding: 0 12px;
            }}
            QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
            QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
        """)
        btn_import.clicked.connect(self._on_import_project)
        btn_row_t.addWidget(btn_import)

        btn_analyze = QPushButton("▶ " + self.txt("btn_analyze"))
        btn_analyze.setObjectName("btn_primary")
        btn_analyze.setCursor(Qt.PointingHandCursor)
        btn_analyze.setFixedHeight(30)
        btn_analyze.setStyleSheet(f"""
            QPushButton#btn_primary {{
                background-color: {config.BTN_BG}; color: #ffffff;
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt; font-weight: bold;
                border: none; border-radius: 3px; padding: 0 18px;
            }}
            QPushButton#btn_primary:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton#btn_primary:pressed {{ background-color: #176e38; }}
        """)
        btn_analyze.clicked.connect(self._on_start_analysis)
        btn_row_t.addWidget(btn_analyze)
        l_trans.addLayout(btn_row_t)
        l_trans.addSpacing(14)

        # ── Link to fast silence sub-page
        btn_switch_fast = QPushButton(self.txt("btn_fast_silence_detection"))
        btn_switch_fast.setCursor(Qt.PointingHandCursor)
        btn_switch_fast.setStyleSheet(
            f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
            " font-size: 9pt; text-decoration: underline; border: none; padding: 0;"
        )
        btn_switch_fast.clicked.connect(lambda: self.welcome_stack.setCurrentIndex(1))
        l_trans.addWidget(btn_switch_fast, 0, Qt.AlignCenter)

        self.welcome_stack.addWidget(p_transcription)  # index 0

        # ═══════════════════════════════════════════════════════════════
        # SUB-PAGE 1: FAST SILENCE (clean layout, mirrors main page)
        # ═══════════════════════════════════════════════════════════════
        p_fast = QWidget()
        p_fast.setStyleSheet("background: transparent;")
        l_fast = QVBoxLayout(p_fast)
        l_fast.setContentsMargins(0, 0, 0, 0)
        l_fast.setSpacing(0)
        l_fast.setAlignment(Qt.AlignTop)

        # TITLE
        lbl_fs_title = QLabel(self.txt("lbl_fast_silence_workspace"))
        lbl_fs_title.setAlignment(Qt.AlignCenter)
        lbl_fs_title.setFixedHeight(20)
        lbl_fs_title.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 10pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        l_fast.addWidget(lbl_fs_title)
        l_fast.addSpacing(20)

        self.combo_tl_1 = CustomDropdown(["Timeline 1", "Timeline 2", "No timelines detected"])
        self.combo_tl_1.setFixedHeight(30)
        l_fast.addLayout(_row(self.txt("lbl_timeline_selection"), self.combo_tl_1))
        l_fast.addSpacing(10)

        self.combo_tr_1 = MultiSelectDropdown(["Audio 1", "Audio 2", "Audio 3", "No audio detected"])
        self.combo_tr_1.setFixedHeight(30)
        l_fast.addLayout(_row(self.txt("lbl_tracks_selection"), self.combo_tr_1))
        l_fast.addSpacing(10)

        # SETTINGS ROWS
        input_style = '''
            QLineEdit {
                background-color: #1e1e1e; color: #d4d4d4; 
                border: 1px solid #3a3a3a; border-radius: 3px; 
                padding: 4px 8px;
            }
            QLineEdit:focus { border: 1px solid #1a7a3e; }
        '''

        self.input_fs_thresh = QLineEdit()
        self.input_fs_thresh.setText(str(prefs.get('ui_spin_thresh', -42.0)))
        self.input_fs_thresh.setStyleSheet(input_style)
        self.input_fs_thresh.setFixedHeight(30)
        l_fast.addLayout(_row(self.txt("lbl_silence_threshold_db"), self.input_fs_thresh))
        l_fast.addSpacing(10)

        self.input_fs_pad = QLineEdit()
        self.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.05)))
        self.input_fs_pad.setStyleSheet(input_style)
        self.input_fs_pad.setFixedHeight(30)
        l_fast.addLayout(_row(self.txt("lbl_padding_s"), self.input_fs_pad))
        l_fast.addSpacing(16)

        # MODE TOGGLES (Mutually Exclusive)
        row_fs_cut = QHBoxLayout()
        lbl_fs_cut = QLabel(self.txt("lbl_cut_silence_directly"))
        lbl_fs_cut.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
        row_fs_cut.addWidget(lbl_fs_cut)
        row_fs_cut.addStretch()
        self.tgl_fs_cut = ToggleSwitch()
        self.tgl_fs_cut.setChecked(prefs.get('fs_cut_mode', True), animated=False)
        row_fs_cut.addWidget(self.tgl_fs_cut)
        l_fast.addLayout(row_fs_cut)
        l_fast.addSpacing(10)

        row_fs_mark = QHBoxLayout()
        lbl_fs_mark = QLabel(self.txt("lbl_mark_silence_with_color"))
        lbl_fs_mark.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: 10pt; background: transparent;")
        row_fs_mark.addWidget(lbl_fs_mark)
        row_fs_mark.addStretch()
        self.tgl_fs_mark = ToggleSwitch()
        self.tgl_fs_mark.setChecked(prefs.get('fs_mark_mode', False), animated=False)
        row_fs_mark.addWidget(self.tgl_fs_mark)
        l_fast.addLayout(row_fs_mark)
        l_fast.addSpacing(24)

        # Connect mutual exclusion & auto-saving
        self.tgl_fs_cut.toggled.connect(lambda c: self.tgl_fs_mark.setChecked(False) if c else None)
        self.tgl_fs_mark.toggled.connect(lambda c: self.tgl_fs_cut.setChecked(False) if c else None)
        self.tgl_fs_cut.toggled.connect(lambda v: self._save_single_pref('fs_cut_mode', v))
        self.tgl_fs_mark.toggled.connect(lambda v: self._save_single_pref('fs_mark_mode', v))

        # RUN BUTTON
        btn_row_fs = QHBoxLayout()
        btn_row_fs.addStretch()
        self.btn_run_fs = QPushButton(self.txt("btn_run_fast_silence"))
        self.btn_run_fs.setCursor(Qt.PointingHandCursor)
        self.btn_run_fs.setFixedHeight(30)
        self.btn_run_fs.setStyleSheet(f'''
            QPushButton {{
                background-color: {config.BTN_BG}; color: #ffffff;
                font-family: "{config.UI_FONT_NAME}"; font-size: 10pt; font-weight: bold;
                border: none; border-radius: 3px; padding: 0 18px;
            }}
            QPushButton:hover {{ background-color: {config.BTN_ACTIVE}; }}
            QPushButton:pressed {{ background-color: #176e38; }}
        ''')
        self.btn_run_fs.clicked.connect(self._on_fast_silence)
        btn_row_fs.addWidget(self.btn_run_fs)
        l_fast.addLayout(btn_row_fs)

        l_fast.addSpacing(20)

        # BACK BUTTON
        btn_back = QPushButton(f"← {self.txt('btn_back_to_transcription')}")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet(
            f"background: transparent; color: #888888; font-family: '{config.UI_FONT_NAME}';"
            " font-size: 9pt; text-decoration: underline; border: none; padding: 0; text-align: left;"
        )
        btn_back.clicked.connect(lambda: self.welcome_stack.setCurrentIndex(0))
        l_fast.addWidget(btn_back)

        l_fast.addStretch()

        self.welcome_stack.addWidget(p_fast)   # index 1

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
        page = QWidget()
        page.setObjectName("page_processing")
        page.setStyleSheet(f"QWidget#page_processing {{ background-color: {config.BG_COLOR}; }}")
        
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        
        self.lbl_processing_status = QLabel(self.txt("lbl_initializing"), page)
        self.lbl_processing_status.setAlignment(Qt.AlignCenter)
        self.lbl_processing_status.setStyleSheet(
            f"color: {config.NOTE_COL}; font-size: 13pt;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        layout.addWidget(self.lbl_processing_status)
        layout.addSpacing(15)
        
        self.bar_processing = LiquidProgressBar(page)
        self.bar_processing.setFixedWidth(400)
        layout.addWidget(self.bar_processing, 0, Qt.AlignCenter)
        return page

    def _update_processing_progress(self, val: int):
        if hasattr(self, 'bar_processing'):
            self.bar_processing.set_value(val)

    def _build_page_editor(self) -> QWidget:
        page = QWidget()
        page.setObjectName("page_editor")
        page.setStyleSheet(f"QWidget#page_editor {{ background-color: {config.BG_COLOR}; }}")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.scroll_area = QScrollArea(page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {config.BG_COLOR}; border: none; }}")
        
        self.text_canvas = TranscriptionCanvas(main_window=self)
        self.scroll_area.setWidget(self.text_canvas)
        layout.addWidget(self.scroll_area)
        
        return page

    def _populate_editor(self, words_data, segments_data):
        if hasattr(self, 'text_canvas'):
            self.text_canvas.load_data(words_data)

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
        
        settings = {
            "lang": lang_code,
            "model": model,
            "device": "Auto",
            "filler_words": config.DEFAULT_BAD_WORDS
        }
        
        # 4. Start thread targeting self.engine.run_analysis_pipeline()
        self._worker_signals = WorkerSignals()
        self._worker_signals.progress.connect(self._on_analysis_progress)
        self._worker_signals.status.connect(self._on_analysis_status)
        self._worker_signals.finished.connect(self._on_analysis_finished)
        self._worker_signals.error.connect(self._on_analysis_error)
        
        def worker_func():
            try:
                words_data, segments_data = self.engine.run_analysis_pipeline(
                    settings, 
                    callback_status=self._worker_signals.status.emit, 
                    callback_progress=self._worker_signals.progress.emit
                )
                self._worker_signals.finished.emit(words_data, segments_data)
            except Exception as e:
                self._worker_signals.error.emit(str(e))
                
        self._analysis_thread = threading.Thread(target=worker_func, daemon=True)
        self._analysis_thread.start()

    def _on_analysis_progress(self, val):
        self._update_processing_progress(val)

    def _on_analysis_status(self, msg):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(msg)

    def _on_analysis_error(self, err):
        if hasattr(self, 'lbl_processing_status'):
            self.lbl_processing_status.setText(f"Error: {err}")

    def _on_analysis_finished(self, words_data, segments_data):
        if not words_data:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, self.txt("msg_analysis_failed"), self.txt("msg_the_transcription_process"))
            
            # Reset UI to Page 0 and show panels again
            self.go_to_page(0)
            self._panel_left.show()
            self._panel_right.show()
            return
            
        self.go_to_page(2)
        
        self._toggle_activity("script_analysis")
        self._toggle_activity("main_panel")
        
        self._populate_editor(words_data, segments_data)

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

    def _on_clear_transcript(self):
        if not hasattr(self, 'text_canvas') or not self.text_canvas.words_data:
            return
            
        msg_box = CustomMsgBox(self, self.txt("msg_clear_title"), self.txt("msg_clear_desc"), self.txt("btn_yes"), self.txt("btn_no"))
        if msg_box.exec() == QDialog.Accepted:
            for w in self.text_canvas.words_data:
                w['status'] = None
                w['manual_status'] = None
                w['algo_status'] = None
                w['is_auto'] = False
                w['selected'] = False
            self.text_canvas.update()

    def _on_settings(self):
        """Open settings panel."""
        dlg = SettingsDialog(self.engine, self)
        dlg.exec()




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
            self.engine.os_doc.force_dark_titlebar(int(popup.winId()))
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
        msg_box = CustomMsgBox(self, self.txt('msg_quit_title'), self.txt('msg_quit_desc'), self.txt('btn_yes'), self.txt('btn_no'))
        if msg_box.exec() == QDialog.Accepted:
            event.accept()
            if self.closeEvent_callback:
                self.closeEvent_callback()
        else:
            event.ignore()
