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
from .mixins import FramelessWindowMixin, _BaseDialog
from ..utils import _app_icon, _txt

# ==========================================



class SearchOverlayWidget(QFrame):
    def __init__(self, parent_widget, main_window):
        super().__init__(parent_widget)
        self.main_window = main_window
        from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QLabel, QPushButton, QGraphicsDropShadowEffect, QWidget, QFrame, QGraphicsOpacityEffect
        from PySide6.QtCore import Qt, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QRect, QSize
        from PySide6.QtGui import QColor, QAction, QIcon, QPixmap
        import os
        
        self.setObjectName("SearchOverlay")
        self.setProperty("expanded", False)
        self.setFixedHeight(36)
        
        self.setStyleSheet("""
            QFrame#SearchOverlay {
                background-color: transparent;
                border: none;
            }
            QFrame#SearchContainer {
                background-color: #252525;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
            }
            QLineEdit, QLabel, QPushButton {
                background: transparent;
                border: none;
                color: #dddddd;
            }
            QLineEdit {
                padding: 4px;
            }
            QLabel {
                padding-right: 8px;
            }
            QPushButton {
                font-weight: bold;
                padding: 4px;
            }
            QPushButton:hover {
                color: #ffffff;
                background-color: #333333;
                border-radius: 4px;
            }
            QPushButton#BtnOpenSearch {
                border-radius: 6px;
                background-color: transparent;
            }
            QPushButton#BtnOpenSearch:hover {
                background-color: #333333;
            }
        """)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        _prod_assets_dir = os.path.join(_src_dir, "layout")
        _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
        _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
        
        _icon_path = os.path.join(_assets_dir, "search.png")
        self.btn_open_search = QPushButton()
        self.btn_open_search.setObjectName("BtnOpenSearch")
        self.btn_open_search.setFixedSize(36, 36)
        
        pix = QPixmap(_icon_path)
        if not pix.isNull():
            self.btn_open_search.setIcon(QIcon(pix))
            self.btn_open_search.setIconSize(QSize(18, 18))
        else:
            self.btn_open_search.setText("🔍")
            
        self.btn_open_search.setToolTip(self.main_window.txt("search_placeholder"))
        self.btn_open_search.clicked.connect(self.toggle_search)
        
        self.search_container = QFrame()
        self.search_container.setObjectName("SearchContainer")
        self.search_container.setFixedSize(300, 36)
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(8, 6, 8, 6)
        search_layout.setSpacing(4)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(self.main_window.txt("search_placeholder"))
        
        self.counter_label = QLabel(self.main_window.txt("search_results_counter_empty"))
        
        self.btn_prev = QPushButton("▲")
        self.btn_prev.setToolTip(self.main_window.txt("search_tooltip_prev"))
        self.btn_prev.setFixedSize(24, 24)
        
        self.btn_next = QPushButton("▼")
        self.btn_next.setToolTip(self.main_window.txt("search_tooltip_next"))
        self.btn_next.setFixedSize(24, 24)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip(self.main_window.txt("search_tooltip_close"))
        self.btn_close.setFixedSize(24, 24)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.counter_label)
        search_layout.addWidget(self.btn_prev)
        search_layout.addWidget(self.btn_next)
        search_layout.addWidget(self.btn_close)
        
        from PySide6.QtWidgets import QScrollArea
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.search_container)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_area.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.btn_open_search)
        
        self.scroll_area.hide()
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self._perform_search)
        
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.returnPressed.connect(self._on_enter_pressed)
        self.search_input.installEventFilter(self)
        
        self.btn_prev.clicked.connect(self.prev_match)
        self.btn_next.clicked.connect(self.next_match)
        self.btn_close.clicked.connect(self.close_search)
        
        self.matches = []
        self.current_index = -1
        self._anim = None
        
        if parent_widget:
            parent_widget.installEventFilter(self)
            
        self.show()
        QTimer.singleShot(0, self._reposition)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent, Qt
        if obj == self.parentWidget() and event.type() == QEvent.Resize:
            self._reposition()
        elif obj == self.search_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:
                self.prev_match()
                return True
            elif event.key() == Qt.Key_Down:
                self.next_match()
                return True
        return super().eventFilter(obj, event)

    def _on_text_changed(self, text):
        self.search_timer.start()

    def _on_enter_pressed(self):
        from PySide6.QtGui import QGuiApplication
        mods = QGuiApplication.keyboardModifiers()
        from PySide6.QtCore import Qt
        if mods & Qt.ShiftModifier:
            self.prev_match()
        else:
            self.next_match()

    def _perform_search(self):
        query = self.search_input.text().strip()
        self.matches.clear()
        self.current_index = -1
        
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or getattr(canvas, 'words_data', None) is None:
            self._update_counter()
            return
            
        # Clean flags
        for w in canvas.words_data:
            w.pop('_search_match', None)
            w.pop('_search_active', None)
            
        if not query:
            canvas.update()
            self._update_counter()
            return
            
        import re
        q_lower = query.lower()
        # Break query into words removing special chars for matching
        q_words = [re.sub(r'[^\w\s]', '', q) for q in q_lower.split() if q]
        if not q_words:
            # If all were special chars, just use the raw query tokens
            q_words = [q for q in q_lower.split() if q]
            if not q_words:
                canvas.update()
                self._update_counter()
                return
        
        # Build searchable list
        searchable = []
        for idx, w in enumerate(canvas.words_data):
            if w.get('type') == 'silence' or w.get('_hidden'):
                continue
            d_text = w.get('_display_text', w.get('text', ''))
            if not d_text.strip():
                continue
            clean_text = re.sub(r'[^\w\s]', '', d_text).lower()
            raw_text = d_text.lower()
            searchable.append((idx, clean_text, raw_text))
            
        # Sliding window
        q_len = len(q_words)
        for i in range(len(searchable) - q_len + 1):
            match = True
            matched_indices = []
            
            for j in range(q_len):
                idx, clean_text, raw_text = searchable[i + j]
                q_word = q_words[j]
                
                # Full match required for all except the last word
                if j < q_len - 1:
                    # check exact match on clean text or raw text
                    if q_word != clean_text and q_word != raw_text:
                        match = False
                        break
                else:
                    # Last word can be a partial (contains) match
                    if q_word not in clean_text and q_word not in raw_text:
                        match = False
                        break
                        
                matched_indices.append(idx)
                
            if match:
                self.matches.append(matched_indices)
                for idx in matched_indices:
                    canvas.words_data[idx]['_search_match'] = True

        if self.matches:
            self.current_index = 0
            self._apply_active_highlight()
            
        self._update_counter()
        canvas.update()

    def _apply_active_highlight(self):
        canvas = getattr(self.main_window, 'text_canvas', None)
        if not canvas or not getattr(canvas, 'words_data', None): return
        
        for matched_indices in self.matches:
            for idx in matched_indices:
                canvas.words_data[idx].pop('_search_active', None)
            
        if 0 <= self.current_index < len(self.matches):
            active_indices = self.matches[self.current_index]
            for idx in active_indices:
                canvas.words_data[idx]['_search_active'] = True
            
            w = canvas.words_data[active_indices[0]]
            if '_rect' in w:
                rect = w['_rect']
                if hasattr(self.main_window, 'scroll_area'):
                    scroll_area = self.main_window.scroll_area
                    # Podstawowe przesunięcie X jeśli schowane
                    scroll_area.ensureVisible(rect.x(), rect.y(), 50, 50)
                    
                    # Wymuszenie idealnego wyśrodkowania w pionie
                    vp_h = scroll_area.viewport().height()
                    vbar = scroll_area.verticalScrollBar()
                    target_y = rect.center().y()
                    new_val = int(target_y - vp_h / 2)
                    vbar.setValue(max(vbar.minimum(), min(new_val, vbar.maximum())))
                
        canvas.update()

    def _update_counter(self):
        if not self.matches:
            self.counter_label.setText(self.main_window.txt("search_results_counter_empty"))
        else:
            self.counter_label.setText(f"{self.current_index + 1}/{len(self.matches)}")

    def next_match(self):
        if not self.matches: return
        self.current_index = (self.current_index + 1) % len(self.matches)
        self._apply_active_highlight()
        self._update_counter()

    def prev_match(self):
        if not self.matches: return
        self.current_index = (self.current_index - 1) % len(self.matches)
        self._apply_active_highlight()
        self._update_counter()

    def toggle_search(self):
        if self.property("expanded"):
            self.close_search()
        else:
            self.open_search()

    def close_search(self):
        if not self.property("expanded"): return
        self.search_input.clear()
        
        canvas = getattr(self.main_window, 'text_canvas', None)
        if canvas and canvas.words_data:
            for w in canvas.words_data:
                w.pop('_search_match', None)
                w.pop('_search_active', None)
            canvas.update()
            
        self.setProperty("expanded", False)
        
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        start_geom = self.geometry()
        self._anim.setStartValue(start_geom)
        
        parent_w = self.parentWidget().width()
        target_w = 36
        target_x = parent_w - target_w - 8
        self._anim.setEndValue(QRect(target_x, start_geom.y(), target_w, 36))
        
        def on_finished():
            self.scroll_area.hide()
            self.btn_open_search.show()
            self._reposition()
            
        self._anim.finished.connect(on_finished)
        self._anim.start()

    def open_search(self):
        if self.property("expanded"):
            self.search_input.setFocus()
            self.search_input.selectAll()
            return
            
        self.show()
        self.raise_()
            
        self.btn_open_search.hide()
        self.scroll_area.show()
        
        self.setProperty("expanded", True)
        
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.OutBack)
        
        start_geom = self.geometry()
        self._anim.setStartValue(start_geom)
        
        parent_w = self.parentWidget().width()
        target_w = 300
        target_x = parent_w - target_w - 8
        
        self._anim.setEndValue(QRect(target_x, start_geom.y(), target_w, 36))
        
        def on_finished():
            self.search_input.setFocus()
            self.search_input.selectAll()
            
        self._anim.finished.connect(on_finished)
        self._anim.start()

    def _reposition(self):
        try:
            if not self.parentWidget(): return
            parent_w = self.parentWidget().width()
            if self.property("expanded"):
                target_w = self.sizeHint().width()
                if target_w < 300: target_w = 300
                self.setGeometry(parent_w - target_w - 8, 8, target_w, 36)
            else:
                self.setGeometry(parent_w - 36 - 8, 8, 36, 36)
        except Exception as e:
            import osdoc
            osdoc.log_error(f"Search positioning error: {str(e)}")


from PySide6.QtWidgets import QPushButton, QSlider
