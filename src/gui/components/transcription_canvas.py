#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: transcription_canvas.py
ROLE: Module
DESCRIPTION:
Provides core functionality for this component.
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
from .mixins import FramelessWindowMixin, _BaseDialog
from ..utils import _app_icon, _txt

class TranscriptionCanvas(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.words_data = []
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        self._last_dragged_id = -1
        # --- VIEWPORT CULLING: cache visible_words so paintEvent never recomputes it ---
        self._cached_visible_words = []

    def load_data(self, words_data):
        self.words_data = words_data
        self._calculate_layout()
        self.update()

    def _get_visible_words(self):
        """Returns a filtered list of only the words that should physically render.
        STAGE 9: Consecutive inaudible tokens are deduplicated in the view layer —
        only the first (...) of a run is shown; data remains intact in memory.
        Result is cached in self._cached_visible_words — do NOT call this inside paintEvent.
        """
        if not self.words_data: return []
        
        vis = []
        previous_was_inaudible = False
        force_segment_start = False

        for w in self.words_data:
            if w.get('type') == 'silence':
                continue
                
            if w.get('is_hidden_start') and not getattr(self.main_window, 'show_hidden_start', False):
                if w.get('is_segment_start'):
                    force_segment_start = True
                continue
                
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'

            if is_inaudible:
                # Hide if the user toggled inaudible off
                if hasattr(self.main_window, 'tgl_show_inaudible') and not self.main_window.tgl_show_inaudible.isChecked():
                    if w.get('is_segment_start'):
                        force_segment_start = True
                    previous_was_inaudible = True
                    continue
                # STAGE 9: Skip consecutive (...) clutter — show only the first of a run
                if previous_was_inaudible:
                    continue
                previous_was_inaudible = True
            else:
                previous_was_inaudible = False

            if force_segment_start:
                w_copy = w.copy()
                w_copy['is_segment_start'] = True
                vis.append(w_copy)
                force_segment_start = False
            else:
                vis.append(w)
        return vis

    def _get_clip_rect(self):
        """Returns the QRect of the currently visible viewport area in canvas coordinates,
        expanded by a generous vertical buffer so words near the edge are never clipped.
        Falls back to the full canvas rect when no parent scroll area is found."""
        try:
            scroll = getattr(self.main_window, 'scroll_area', None)
            if scroll is not None:
                vbar = scroll.verticalScrollBar()
                hbar = scroll.horizontalScrollBar()
                y_off = vbar.value()
                x_off = hbar.value()
                vp = scroll.viewport()
                vp_h = vp.height()
                vp_w = vp.width()
                # 400px vertical buffer — ensures words on partially-visible lines render correctly
                BUFFER = 400
                return QRect(x_off, max(0, y_off - BUFFER), vp_w, vp_h + BUFFER * 2)
        except Exception:
            pass
        return self.rect()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Prevent infinite layout loops: only recalculate when width changes
        if not event.oldSize().isValid() or event.oldSize().width() != event.size().width():
            self._calculate_layout()

    def _calculate_layout(self):
        if not hasattr(self, 'words_data') or not self.words_data:
            self._cached_visible_words = []
            return
            
        # Clean up leftover artifacts from previous layout passes
        words_to_clean = []
        if hasattr(self, 'words_data') and self.words_data:
            words_to_clean.extend(self.words_data)
        if hasattr(self, '_cached_visible_words') and self._cached_visible_words:
            # We don't use set() since dicts are unhashable, just iterate all.
            words_to_clean.extend(self._cached_visible_words)
            
        for w in words_to_clean:
            w.pop('_ts_rect', None)
            w.pop('_ts_text', None)
            w.pop('_separator_y', None)

        from PySide6.QtGui import QFontMetrics, QFont, QTextOption, QTextBlockFormat, QTextCursor
        from PySide6.QtCore import Qt, QRect
        from PySide6.QtWidgets import QFrame, QTextEdit
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        import platform
        if platform.system() == "Darwin": pref_size = int(pref_size * 1.333)
        pref_lh = prefs.get('editor_line_height', 7)
        view_mode = prefs.get('view_mode', 'continuous')
        
        is_rtl = False
        lang_pref = prefs.get('lang', 'Auto')
        
        rtl_codes = getattr(config, 'RTL_LANGUAGES', {'ar', 'he', 'fa', 'ur', 'yi', 'ps', 'sd'})
        rtl_english_names = {'arabic', 'hebrew', 'persian', 'urdu', 'yiddish', 'pashto', 'sindhi'}
        rtl_native_names = {config.SUPPORTED_LANGUAGES.get(code, code) for code in rtl_codes}
        
        if isinstance(lang_pref, str) and lang_pref.lower() != 'auto':
            if lang_pref in rtl_native_names or lang_pref.lower() in rtl_codes or lang_pref.lower() in rtl_english_names:
                is_rtl = True
        elif self.words_data:
            meta_lang = self.words_data[0].get('meta_language')
            if isinstance(meta_lang, str) and (meta_lang.lower() in rtl_codes or meta_lang.lower() in rtl_english_names):
                is_rtl = True
                
        active_font = QFont(pref_family, pref_size)
        metrics = QFontMetrics(active_font)
        ts_font = QFont(config.UI_FONT_NAME, max(8, pref_size - 2))
        ts_metrics = QFontMetrics(ts_font)
        
        space_w = metrics.horizontalAdvance(" ") + 2
        line_height = metrics.height() + pref_lh
        
        max_w = self.width() - 40
        x = max_w if is_rtl else 20
        y = 20
        
        is_sbs = getattr(self, 'is_sbs_mode', False)
        
        if is_sbs and hasattr(self, 'sbs_rows'):
            # 0. CLEANUP (usuwamy śmieci z normalnego widoku, które powodowały problemy z separatorami)
            for w in self.words_data:
                for key in ['_rect', '_ts_rect', '_display_text', '_ts_text', '_separator_y']:
                    w.pop(key, None)
                    
            visible_words = []
            right_start_x = self.width() // 2 + 10
            max_w = self.width() - 20
            
            # Estimate timestamp width for consistent left-column alignment
            sample_ts = "[00:00]"
            ts_base_w = ts_metrics.horizontalAdvance(sample_ts)
            default_script_start_x = 20 + ts_base_w + 10
            default_script_w = (self.width() // 2 - 20) - default_script_start_x
            
            show_inaudible = True
            if hasattr(self.main_window, 'tgl_show_inaudible'):
                show_inaudible = self.main_window.tgl_show_inaudible.isChecked()

            for idx, row in enumerate(self.sbs_rows):
                script_text = row.get("script_text", "")
                
                trans_toks = row.get("transcript_tokens", [])
                
                if not show_inaudible:
                    filtered_toks = []
                    for tok in trans_toks:
                        w = tok.get("original_word", {})
                        if not (w.get('is_inaudible') or w.get('type') == 'inaudible'):
                            filtered_toks.append(tok)
                    trans_toks = filtered_toks
                    row["transcript_tokens"] = trans_toks # Update the row itself for rendering
                    
                if not script_text.strip() and not trans_toks:
                    continue
                
                is_interruption = row.get("_is_interruption", False)
                
                # Separator line between rows
                if y > 20:
                    if is_interruption:
                        y += 10
                    else:
                        y += 20
                        # Store separator on a virtual dictionary to avoid tainting real words
                        sep_marker = {'_separator_y': y - 10}
                        visible_words.append(sep_marker)
                            
                row_start_y = y
                x = max_w if is_rtl else right_start_x
                
                # Script editor position defaults
                script_start_x = default_script_start_x
                script_w = default_script_w
                
                if trans_toks:
                    secs = trans_toks[0].get('start', 0)
                    if prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']):
                        m = int(secs // 60)
                        s = int(secs % 60)
                        ms = int((secs - int(secs)) * 1000)
                        ts_text = f"[{m:02d}:{s:02d}.{ms:03d}]"
                    else:
                        total_s = int(round(secs))
                        m = total_s // 60
                        s = total_s % 60
                        ts_text = f"[{m:02d}:{s:02d}]"
                        
                    w_ts = trans_toks[0].get("original_word")
                    if w_ts:
                        w_ts['_ts_text'] = f"\u202A\u2068{ts_text}\u2069\u202C" if is_rtl else ts_text
                        ts_w = ts_metrics.horizontalAdvance(w_ts['_ts_text'])
                        
                        # Timestamp on the far left
                        w_ts['_ts_rect'] = QRect(20, y, ts_w, metrics.height() + 4)
                        script_start_x = 20 + ts_w + 10
                        script_w = (self.width() // 2 - 20) - script_start_x

                prev_status = None
                force_newline = False
                
                for tok in trans_toks:
                    w = tok.get("original_word")
                    if not w: continue
                    
                    curr_status = w.get("status")
                    
                    # Smart line break for repeat runs
                    is_line_started = (x < max_w) if is_rtl else (x > right_start_x)
                    if curr_status == "repeat" and prev_status != "repeat" and is_line_started:
                        x = max_w if is_rtl else right_start_x
                        y += line_height
                    elif prev_status == "repeat" and curr_status != "repeat" and is_line_started:
                        x = max_w if is_rtl else right_start_x
                        y += line_height
                    elif prev_status == "repeat" and curr_status == "repeat" and force_newline and is_line_started:
                        x = max_w if is_rtl else right_start_x
                        y += line_height
                    
                    is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
                    raw_text = "(...)" if is_inaudible else w.get('text', '')
                    display_text = f"\u202B\u2068{raw_text}\u2069\u202C" if is_rtl else raw_text
                    w['_display_text'] = display_text
                    word_w = metrics.horizontalAdvance(display_text)
                    
                    if is_rtl:
                        if x - word_w < right_start_x and x < max_w:
                            x = max_w
                            y += line_height
                        x -= word_w
                        w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                        x -= space_w
                    else:
                        if x + word_w > max_w and x > right_start_x:
                            x = right_start_x
                            y += line_height
                        w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                        x += word_w + space_w
                        
                    visible_words.append(w)
                    
                    if curr_status == "repeat" and raw_text.endswith((".", "?", "!", "...")):
                        force_newline = True
                    else:
                        force_newline = False
                        
                    prev_status = curr_status
                    
                # Transcript content height
                transcript_h = (y + line_height) - row_start_y
                
                script_kind = row.get("script_kind")
                script_y = row_start_y
                sx = script_start_x
                
                script_words = script_text.split()
                for w_text in script_words:
                    w_w = metrics.horizontalAdvance(w_text)
                    if sx + w_w > script_start_x + default_script_w and sx > script_start_x:
                        sx = script_start_x
                        script_y += line_height
                        
                    visible_words.append({
                        'text': w_text,
                        '_display_text': w_text,
                        '_rect': QRect(sx, script_y, w_w, metrics.height() + 4),
                        'is_script_word': True,
                        'script_kind': script_kind
                    })
                    sx += w_w + space_w
                    
                if script_words:
                    script_y += line_height
                
                script_h = script_y - row_start_y
                row_h = max(transcript_h, script_h, line_height)
                
                if script_kind in ("missing", "improv_gap"):
                    bg_rect = QRect(script_start_x - 10, row_start_y, default_script_w + 20, row_h)
                    visible_words.insert(0, {
                        'is_script_bg': True,
                        'script_kind': script_kind,
                        '_rect': bg_rect
                    })
                    
                    if script_kind == "missing":
                        placeholder = self.main_window.txt("sbs_skipped")
                        pw = metrics.horizontalAdvance(placeholder)
                        rx = right_start_x
                        if is_rtl: rx = max_w - pw
                        visible_words.append({
                            'text': placeholder,
                            '_display_text': placeholder,
                            '_rect': QRect(rx, row_start_y + (row_h - metrics.height()) // 2, pw, metrics.height() + 4),
                            'is_script_placeholder': True,
                            'script_kind': "improv_gap"  # use same styling as improv gap (italic, gray)
                        })
                
                y = row_start_y + row_h # No extra padding here, handled by next row's y += 20

            self._cached_visible_words = visible_words
            self.setMinimumHeight(y + line_height + 40)
            return
            
        # Hide editors if returning to normal view
        if hasattr(self, 'sbs_editors'):
            for ed in self.sbs_editors:
                ed.hide()
        
        # Rebuild the cached list once — paintEvent reads it directly, never recomputes
        visible_words = self._get_visible_words()
        self._cached_visible_words = visible_words
        
        for w in visible_words:
            # Clean previous iteration markers
            w.pop('_ts_rect', None)
            w.pop('_ts_text', None)
            w.pop('_separator_y', None)
            
            # Paragraph formatting based on Engine's Chunking
            if view_mode == 'segmented' and w.get('is_segment_start'):
                has_advanced = (x < max_w) if is_rtl else (x > 20)
                if has_advanced: 
                    y += line_height
                if y > 20: 
                    w['_separator_y'] = y + 10 # Store Y coordinate for the line
                    y += 20 # Gap between paragraphs
                x = max_w if is_rtl else 20
                
                # Generate Timestamp — format depends on 'timestamp_precise' setting
                secs = w.get('start', 0)
                if prefs.get('timestamp_precise', config.DEFAULT_SETTINGS['timestamp_precise']):
                    m = int(secs // 60)
                    s = int(secs % 60)
                    ms = int((secs - int(secs)) * 1000)
                    ts_text = f"[{m:02d}:{s:02d}.{ms:03d}]"
                else:
                    total_s = int(round(secs))
                    m = total_s // 60
                    s = total_s % 60
                    ts_text = f"[{m:02d}:{s:02d}]"
                
                # Ensure timestamps stay isolated as LTR natively, using LTR Embedding, if in RTL mode.
                w['_ts_text'] = f"\u202A\u2068{ts_text}\u2069\u202C" if is_rtl else ts_text
                ts_w = ts_metrics.horizontalAdvance(w['_ts_text'])
                
                if is_rtl:
                    x -= ts_w
                    w['_ts_rect'] = QRect(x, y, ts_w, metrics.height() + 4)
                    x -= (space_w + 5)
                else:
                    w['_ts_rect'] = QRect(x, y, ts_w, metrics.height() + 4)
                    x += ts_w + space_w + 5
            
            # Standard word layout
            is_inaudible = w.get('is_inaudible') or w.get('type') == 'inaudible'
            raw_text = "(...)" if is_inaudible else w.get('text', '')
            
            # Use BiDirectional formatting to perfectly resolve neutral chars (e.g. dots, numbers) in RTL.
            # \u202B (RLE) sets the base direction to RTL.
            # \u2068 (FSI) isolates the word so LTR chunks like "[x34]" keep their brackets unmirrored.
            display_text = f"\u202B\u2068{raw_text}\u2069\u202C" if is_rtl else raw_text
            
            w['_display_text'] = display_text  # Store visual text
            
            word_w = metrics.horizontalAdvance(display_text)
            
            if is_rtl:
                if x - word_w < 20 and x < max_w:
                    x = max_w
                    y += line_height
                x -= word_w
                w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                x -= space_w
            else:
                if x + word_w > max_w and x > 20:
                    x = 20
                    y += line_height
                w['_rect'] = QRect(x, y, word_w, metrics.height() + 4)
                x += word_w + space_w
            
        self.setMinimumHeight(y + line_height + 40)



    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor, QFont, QPen, QLinearGradient
        from PySide6.QtCore import QRectF, Qt
        
        prefs = self.main_window.engine.load_preferences() or {}
        pref_family = prefs.get('editor_font_family', config.UI_FONT_NAME)
        pref_size = prefs.get('editor_font_size', 12)
        import platform
        if platform.system() == "Darwin": pref_size = int(pref_size * 1.333)
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
                if w.get('manual_status') != 'typo' or w.get('is_auto', False):
                    return None
            return s

        def get_color_tuple(status_val):
            if status_val in color_map: return color_map[status_val]
            if status_val and str(status_val).startswith("custom_"):
                c_name = status_val.split("_")[1]
                return (QColor(config.RESOLVE_COLORS_HEX.get(c_name, "#ffffff")), QColor("#ffffff"))
            return None
            
        def get_base_bg_fg(w):
            status = get_status(w)
            c_res = get_color_tuple(status)
            if c_res:
                bg, fg = c_res[0], c_res[1]
                if w.get('is_assembled_cut'):
                    # Interpolate sharply towards dark gray background to dim seamlessly
                    r = int(bg.red() * 0.2 + 30 * 0.8)
                    g = int(bg.green() * 0.2 + 30 * 0.8)
                    b = int(bg.blue() * 0.2 + 30 * 0.8)
                    bg = QColor(r, g, b, 255)
                return bg, fg, False
            return None, QColor(config.WORD_NORMAL_FG), True

        p.setPen(Qt.NoPen)

        # ── VIEWPORT CULLING ─────────────────────────────────────────────────────
        # Use the pre-computed cached list — never call _get_visible_words() here.
        # Build a smaller list of only those words whose _rect overlaps the visible
        # viewport region. All rendering passes below use this culled list.
        # The full cached list is kept so bridge-detection can peek at neighbours.
        all_visible = self._cached_visible_words
        clip = self._get_clip_rect()
        visible_words = [w for w in all_visible if '_rect' not in w or clip.intersects(w['_rect'])]
        # ────────────────────────────────────────────────────────────────────────

        # Oś Y separatorów (only in visible range)
        p.setPen(QPen(QColor("#333333"), 1))
        is_sbs = getattr(self, 'is_sbs_mode', False)
        for w in visible_words:
            if '_separator_y' in w:
                sep_y = w['_separator_y']
                if is_sbs:
                    mid = self.width() // 2
                    p.drawLine(20, sep_y, mid - 20, sep_y)
                    p.drawLine(mid + 20, sep_y, self.width() - 20, sep_y)
                else:
                    p.drawLine(20, sep_y, self.width() - 20, sep_y)
            
        p.setPen(Qt.NoPen)
        
        # 1. CZYSZCZENIE ŚMIECI PO POPRZEDNICH ITERACJACH
        # Only clear per-frame keys on the culled (visible) set — no reason to touch off-screen words
        for w in visible_words:
            for key in ['_search_brush', '_search_fg', '_is_bold']:
                w.pop(key, None)
            
        groups = []
        curr_group = []
        curr_state = None # Teraz będzie przechowywać tuple: (search_state, bg_color)
        
        for w in visible_words:
            if '_rect' not in w: continue
            if w.get('is_script_word') or w.get('is_script_bg') or w.get('is_script_placeholder'): continue
            
            # Pobieramy stan wyszukiwania i kolor tła dla danego słowa
            search_state = 'active' if w.get('_search_active') else ('match' if w.get('_search_match') else None)
            bg_color, _, _ = get_base_bg_fg(w)
            
            # Nasz nowy klucz grupowania to kombinacja stanu i koloru
            state = (search_state, bg_color) if search_state else None
            
            if state:
                # Grupujemy tylko jeśli: ten sam stan, ten sam kolor i ta sama linia Y
                if curr_state == state and curr_group and w['_rect'].y() == curr_group[-1]['_rect'].y():
                    curr_group.append(w)
                else:
                    if curr_group: groups.append((curr_group, curr_state[0])) # Zapisujemy tylko search_state do grup
                    curr_group = [w]
                    curr_state = state
            else:
                if curr_group: groups.append((curr_group, curr_state[0]))
                curr_group = []
                curr_state = None
        if curr_group: groups.append((curr_group, curr_state[0]))

        # Uproszczone wygaszanie kolorów
        def get_dimmed_center(color):
            h, s, v, a = color.getHsv()
            if h == -1: h = 0
            return QColor.fromHsv(h, s, max(0, int(v * 0.90)), a)

        def get_dimmed_edge(color):
            h, s, v, a = color.getHsv()
            if h == -1: h = 0
            return QColor.fromHsv(h, s, max(0, int(v * 0.70)), a) 

        from PySide6.QtGui import QRadialGradient, QBrush, QTransform
        
        active_underlines = []
        active_line_rect = None
        active_line_color = None

        for grp_words, state in groups:
            is_active = (state == 'active')
            bg, fg, is_neutral = get_base_bg_fg(grp_words[0])
            
            min_x = min(w['_rect'].left() for w in grp_words)
            max_x = max(w['_rect'].right() for w in grp_words)
            r0 = grp_words[0]['_rect']
            
            if is_active:
                # Obliczamy prostokąt obejmujący płótno (teraz zawsze na pełną szerokość, również w SBS)
                active_line_rect = QRectF(0, r0.top() - 4, self.width(), r0.height() + 8)
                    
                # Dynamiczny kolor linii
                if is_neutral:
                    active_line_color = QColor(255, 200, 50, 15) # Domyślny, delikatny żółty
                else:
                    active_line_color = QColor(bg.red(), bg.green(), bg.blue(), 18) # 7% przezroczystości natywnego koloru markera
            
            if is_neutral:
                # KLON VS CODE: Jeden zbiorczy prostokąt dla całej frazy (Brak Alpha Stacking!)
                p.setBrush(QColor(255, 140, 0, 120) if is_active else QColor(255, 200, 50, 60))
                p.drawRoundedRect(QRectF(min_x - 2, r0.top() - 1, (max_x - min_x) + 4, r0.height() + 2), 3, 3)
                for w in grp_words:
                    w['_search_fg'] = fg 
                    w['_is_bold'] = False
            else:
                # KOLOROWE TAGI: Wygaszony gradient
                center_x = (min_x + max_x) / 2.0
                center_y = r0.center().y()
                half_w = max(1.0, (max_x - min_x) / 2.0 + 6)
                half_h = max(1.0, r0.height() / 2.0 + 1)
                
                grad = QRadialGradient(0, 0, 1.0)
                h, s, v, a = bg.getHsv()
                if h == -1: h = 0
                grad.setColorAt(0.0, get_dimmed_center(bg))
                grad.setColorAt(1.0, get_dimmed_edge(bg))
                    
                brush = QBrush(grad)
                brush.setTransform(QTransform().translate(center_x, center_y).scale(half_w, half_h))
                
                for w in grp_words:
                    w['_search_brush'] = brush
                    w['_search_fg'] = QColor("#ffffff") if is_active else fg
                    w['_is_bold'] = is_active
                    
                if is_active:
                    active_underlines.append(QRectF(min_x, r0.bottom() - 3, max_x - min_x, 2))

        # PASS 0: Podświetlenie aktywnej linii
        if active_line_rect and active_line_color:
            p.setPen(Qt.NoPen)
            p.setBrush(active_line_color)
            p.drawRect(active_line_rect)

        # PASS -1: Script Backgrounds
        for w in visible_words:
            if w.get('is_script_bg'):
                script_kind = w.get('script_kind')
                rect = w.get('_rect')
                if rect:
                    if script_kind == "improv_gap":
                        bg = QColor(config.RESOLVE_COLORS_HEX.get('Red', "#ff0000"))
                        p.setBrush(QColor(bg.red(), bg.green(), bg.blue(), 25))
                    elif script_kind == "missing":
                        p.setBrush(QColor(255, 200, 50, 20))
                    else:
                        continue
                    p.drawRect(QRectF(0, rect.top() - 5, self.width(), rect.height() + 10))

        p.setPen(Qt.NoPen)
        # PASS 1: Base Backgrounds
        for w in visible_words:
            if '_rect' not in w or w.get('is_script_word') or w.get('is_script_bg'): continue
            bg, _, _ = get_base_bg_fg(w)
            brush = w.get('_search_brush', bg)
            if brush:
                p.setBrush(brush)
                expand = 6 if '_search_brush' in w else 3
                p.drawRoundedRect(w['_rect'].adjusted(-expand, -1, expand, 1), 5, 5)

        # PASS 2: Sharp Bridges
        # Iterate over the FULL cached list so bridges between an off-screen word and
        # an on-screen word are never orphaned. We skip pairs where neither is in the
        # visible set (fast path via a set of ids).
        p.setPen(Qt.NoPen)
        visible_ids = {id(w) for w in visible_words}
        for i in range(len(all_visible) - 1):
            w1 = all_visible[i]
            w2 = all_visible[i+1]
            # Skip pairs where neither word is on screen
            if id(w1) not in visible_ids and id(w2) not in visible_ids:
                continue
            
            if '_rect' not in w1 or '_rect' not in w2: continue
            if w1['_rect'].y() != w2['_rect'].y(): continue 
            
            bg1, _, _ = get_base_bg_fg(w1)
            bg2, _, _ = get_base_bg_fg(w2)
            
            brush1 = w1.get('_search_brush', bg1)
            brush2 = w2.get('_search_brush', bg2)
            
            if brush1 and brush2:
                expand1 = 6 if '_search_brush' in w1 else 3
                expand2 = 6 if '_search_brush' in w2 else 3
                
                r1 = w1['_rect'].adjusted(-expand1, -1, expand1, 1)
                r2 = w2['_rect'].adjusted(-expand2, -1, expand2, 1)
                
                left_rect = r1 if r1.left() <= r2.left() else r2
                right_rect = r2 if r1.left() <= r2.left() else r1
                brush_left = brush1 if r1.left() <= r2.left() else brush2
                brush_right = brush2 if r1.left() <= r2.left() else brush1
                
                if brush1 == brush2:
                    p.setBrush(brush1)
                    bridge_rect = QRectF(left_rect.right() - 5, left_rect.y(), right_rect.left() - left_rect.right() + 10, left_rect.height())
                    if bridge_rect.width() > 0:
                        p.drawRect(bridge_rect)
                else:
                    p.setRenderHint(QPainter.Antialiasing, False)
                    gap_mid = int(left_rect.right() + (right_rect.left() - left_rect.right()) / 2.0)
                    
                    if right_rect.left() - left_rect.right() > 0:
                        p.setBrush(brush_left)
                        p.drawRect(QRectF(left_rect.right() - 5, left_rect.y(), gap_mid - left_rect.right() + 6, left_rect.height()))
                        p.setBrush(brush_right)
                        p.drawRect(QRectF(gap_mid, right_rect.y(), right_rect.left() - gap_mid + 5, right_rect.height()))
                        
                    p.setRenderHint(QPainter.Antialiasing, True)
                    
        # PASS 3: Timestamps & Text
        ts_font = QFont(config.UI_FONT_NAME, 10)
        ts_color = QColor("#666666")
        
        for w in visible_words:
            if w.get('is_script_bg'): continue
            
            if '_ts_rect' in w:
                p.setFont(ts_font)
                p.setPen(ts_color)
                p.drawText(w['_ts_rect'], Qt.AlignLeft | Qt.AlignVCenter, w.get('_ts_text', ''))
                
            if '_rect' not in w: continue
            
            if w.get('is_script_word') or w.get('is_script_placeholder'):
                font = QFont(active_font)
                p.setFont(font)
                
                script_kind = w.get('script_kind')
                if script_kind == "improv_gap":
                    p.setPen(QColor("#9a9a9a"))
                    font.setItalic(True)
                    p.setFont(font)
                elif script_kind == "missing":
                    p.setPen(QColor(config.FG_COLOR))
                else:
                    p.setPen(QColor(config.FG_COLOR))
                    
                p.drawText(w['_rect'], Qt.AlignCenter, w.get('_display_text', w.get('text', '')))
                continue
            
            _, fg, _ = get_base_bg_fg(w)
            final_fg = w.get('_search_fg', fg)
            
            font = QFont(active_font)
            if w.get('_is_bold') or w.get('_audio_active'):
                font.setBold(True)
                
            if w.get('_audio_active'):
                p.setBrush(QColor("#ffffff"))
                p.setPen(Qt.NoPen)
                active_rect = w['_rect'].adjusted(-8, -2, 8, 2)
                p.drawRoundedRect(active_rect, 6, 6)
                final_fg = QColor("#222222")
                
            if w.get('is_assembled_cut'):
                final_fg = QColor("#5a5a5a")
                
            p.setFont(font)
            p.setPen(final_fg)
            draw_rect = w['_rect'].adjusted(-20, 0, 20, 0) if w.get('_audio_active') else w['_rect']
            p.drawText(draw_rect, Qt.AlignCenter, w.get('_display_text', w.get('text', '')))
            
            if w.get('is_assembled_cut'):
                p.setPen(QPen(final_fg, 1.5))
                mid_y = int(w['_rect'].center().y()) + 1
                p.drawLine(int(w['_rect'].left()) + 4, mid_y, int(w['_rect'].right()) - 4, mid_y)
            
        # PASS 4: Active Underlines
        if active_underlines:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#ffffff"))
            for rect in active_underlines:
                p.drawRoundedRect(rect, 1, 1)

    def _handle_mouse(self, pos):
        visible_words = self._cached_visible_words
        for w in visible_words:
            if w.get('is_script_word') or w.get('is_script_bg') or w.get('is_script_placeholder'):
                continue
                
            if '_rect' in w and w['_rect'].adjusted(-3, -1, 3, 1).contains(pos):
                if w['id'] != self._last_dragged_id:
                    self._last_dragged_id = w['id']
                    checked_btn = self.main_window.marker_btn_group.checkedButton()
                    status = checked_btn.property('status_id') if checked_btn else None
                    if status == 'eraser': status = None
                    # rb_eraser → status stays None → propagate_status_change clears

                    # UNDO SUPPORT: Save old state before algorithms modifies words_data
                    if getattr(self, '_current_undo_action', None) is not None:
                        ids_to_save = [w['id']]
                        if w.get('is_inaudible'):
                            start = w['id']
                            while start > 0 and (self.words_data[start-1].get('is_inaudible') or self.words_data[start-1].get('type') == 'silence'): start -= 1
                            end = w['id']
                            while end < len(self.words_data)-1 and (self.words_data[end+1].get('is_inaudible') or self.words_data[end+1].get('type') == 'silence'): end += 1
                            ids_to_save = range(start, end + 1)
                        
                        changes = self._current_undo_action['changes']
                        for wid in ids_to_save:
                            if wid not in changes: # Save only the first state observed during this drag session
                                old_w = self.words_data[wid]
                                changes[wid] = {
                                    'status': old_w.get('status'),
                                    'manual_status': old_w.get('manual_status'),
                                    'algo_status': old_w.get('algo_status'),
                                    'is_auto': old_w.get('is_auto'),
                                    'selected': old_w.get('selected')
                                }

                    import algorithms
                    updates = algorithms.propagate_status_change(self.words_data, w['id'], status)

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
                            word_obj.pop('is_assembled_cut', None)
                            # Route through the Layer Engine — this is what actually
                            # writes word_obj['status'] to the correct final value.
                            if layer_engine:
                                layer_engine(word_obj)

                        self.update()
                break


    def mousePressEvent(self, event):
        from PySide6.QtGui import QGuiApplication
        prefs = getattr(self.main_window.engine, 'load_preferences', lambda: {})() or {}
        shortcuts = prefs.get('shortcuts', getattr(config, 'DEFAULT_SETTINGS', {}).get('shortcuts', {}))
        jump_opt = shortcuts.get('jump_to_word', 'opt_ctrl_rmb')
        
        expected_btn = Qt.RightButton if 'rmb' in jump_opt else Qt.LeftButton
        
        if 'ctrl' in jump_opt: expected_mod = Qt.KeyboardModifier.ControlModifier
        elif 'alt' in jump_opt: expected_mod = Qt.KeyboardModifier.AltModifier
        elif 'shift' in jump_opt: expected_mod = Qt.KeyboardModifier.ShiftModifier
        else: expected_mod = Qt.KeyboardModifier.ControlModifier
        
        # Querying global keyboard state prevents Qt's stuck modifier bug (especially after Alt-Tab)
        global_mods = QGuiApplication.queryKeyboardModifiers()
        active_mods = global_mods & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier)
        
        if event.button() == expected_btn:
            if active_mods == expected_mod:
                for w in self._cached_visible_words:
                    if w.get('is_script_word') or w.get('is_script_bg') or w.get('is_script_placeholder'):
                        continue
                    if '_rect' in w and w['_rect'].adjusted(-10, -5, 10, 5).contains(event.pos()):
                        start_time = w.get('start', 0.0)
                        
                        audio_ts = start_time
                        
                        is_assembled = False
                        if hasattr(self.main_window, '_current_chapter_idx') and self.main_window._current_chapter_idx > 0:
                            is_assembled = True
                            
                        # Use the engine's pre-calculated anchor point if available
                        audio_ts = start_time
                        if 'anchor_start' in w:
                            audio_ts = w['anchor_start']
                        else:
                            # Fallback if anchor_start is missing
                            prefs = {}
                            fps = 24.0
                            if hasattr(self.main_window, 'engine') and self.main_window.engine:
                                prefs = self.main_window.engine.load_preferences() or {}
                                if getattr(self.main_window.engine, 'resolve_handler', None):
                                    fps = getattr(self.main_window.engine.resolve_handler, 'fps', 24.0)
                                    
                            offset_s = prefs.get('offset', 0.133)
                            snap_max = prefs.get('snap_max', 0.25)
                            
                            offset_f = int(round(offset_s * fps))
                            snap_f = int(round(snap_max * fps))
                            
                            def t2f(t): return int(round(t * fps))
                            
                            w_start_f = t2f(start_time) + offset_f
                            
                            if hasattr(self, 'words_data'):
                                for dw in self.words_data:
                                    if dw.get('type') == 'silence':
                                        s_start_f = t2f(dw.get('start', 0.0))
                                        s_end_f = t2f(dw.get('end', 0.0))
                                        if abs(w_start_f - s_start_f) <= snap_f:
                                            w_start_f = s_start_f
                                            break
                                        if abs(w_start_f - s_end_f) <= snap_f:
                                            w_start_f = s_end_f
                                            break
                                            
                            audio_ts = max(0.0, w_start_f / fps)
                            
                        idx = -1
                        try:
                            idx = self.words_data.index(w)
                        except Exception:
                            pass

                        if is_assembled and hasattr(self.main_window, 'audio_preview'):
                            # When on an assembled timeline, map the padded anchor point to the assembled coordinate space.
                            # This ensures we hit the exact frame boundary DaVinci cut at.
                            audio_ts = self.main_window.audio_preview._original_to_audio_time(audio_ts)
                            self.main_window.audio_preview.set_position_ms(int(audio_ts * 1000), force_word_idx=idx)
                        elif hasattr(self.main_window, 'audio_preview') and self.main_window.audio_preview.is_preview_active():
                            # When on marking mode but audio preview is running
                            self.main_window.audio_preview.set_position_ms(int(audio_ts * 1000), force_word_idx=idx)
                            
                        if hasattr(self.main_window, '_jump_playhead'):
                            from PySide6.QtCore import QTimer
                            QTimer.singleShot(0, lambda t=audio_ts: self.main_window._jump_playhead(t))
                        break
                return  # Block painting if jump shortcut was used

        if event.button() == Qt.LeftButton:
            self._is_painting = True
            self._last_dragged_id = -1
            self._current_undo_action = {"type": "paint", "changes": {}}
            self._handle_mouse(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and getattr(self, '_is_painting', False):
            self._handle_mouse(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_painting = False
            action = getattr(self, '_current_undo_action', None)
            if action and action.get('changes'):
                if hasattr(self.main_window, 'undo_manager'):
                    self.main_window.undo_manager.push(action)
            self._current_undo_action = None

# ==========================================
