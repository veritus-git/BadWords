#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: welcome_view.py
ROLE: GUI View
DESCRIPTION:
Welcome screen with unified shared Timeline/Track controls in the upper block,
smooth cubic Bezier vertical gliding, and optimized wave cross-fade on the lower dynamic section.
"""

import os
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QVariantAnimation, QRectF
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QLineEdit, QTextEdit, QSpacerItem, QSizePolicy, QGraphicsOpacityEffect, QLayout
)
from PySide6.QtGui import QPixmap, QCursor, QFont, QPainter, QColor, QPen, QLinearGradient
from PySide6.QtSvg import QSvgRenderer

import config
from gui.utils import get_play_icon, get_layout_icon_path
from gui.widgets.buttons import CustomDropdown, SearchableDropdown, MultiSelectDropdown, ToggleSwitch, ReloadButton


class WelcomeBrandingWidget(QWidget):
    """
    Renders the authentic vector 'BadWords' branding logo in Helvetica Neue
    consistently across all platforms from badwords-welcome-branding.svg.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("welcome_title")
        svg_path = get_layout_icon_path("badwords-welcome-branding.svg")
        self.renderer = QSvgRenderer(svg_path, self)
        s = self.renderer.defaultSize()
        self.aspect = float(s.width()) / float(max(1, s.height())) if not s.isEmpty() else 6.046
        target_h = config.S(36)
        target_w = int(target_h * self.aspect)
        self.setFixedSize(target_w, target_h)

    def sizeHint(self) -> QSize:
        h = config.S(36)
        return QSize(int(h * self.aspect), h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.renderer.isValid():
            self.renderer.render(p, self.rect())


class AnimatedUnderlineGlowModeSwitch(QWidget):
    """
    Mode switcher with continuous gray baseline, active green segment,
    upward soft flame gradient, and smooth cubic bezier animation.
    Aligned flush with inputs below.
    """
    def __init__(self, tab1_text: str, tab2_text: str, parent=None):
        super().__init__(parent)
        self.active_idx = 0
        self._anim_pos = 0.0
        self.on_change = None
        self._anim = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.btn1 = QPushButton(tab1_text)
        self.btn2 = QPushButton(tab2_text)
        for btn in (self.btn1, self.btn2):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(config.S(30))

        self.btn1.clicked.connect(lambda: self.set_index(0, trigger_callback=True))
        self.btn2.clicked.connect(lambda: self.set_index(1, trigger_callback=True))

        lay.addWidget(self.btn1, 1)
        lay.addWidget(self.btn2, 1)
        self.update_styles()

    def set_index(self, idx: int, trigger_callback: bool = False):
        if self.active_idx == idx and not trigger_callback:
            return
        self.active_idx = idx
        self.update_styles()

        if trigger_callback and self.on_change:
            self.on_change(idx)

    def animate_indicator(self, idx: int, duration: int = 280):
        target_pos = float(idx)
        if self._anim is not None:
            self._anim.stop()

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(self._anim_pos)
        anim.setEndValue(target_pos)
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        def _on_val(v):
            self._anim_pos = v
            self.update()

        anim.valueChanged.connect(_on_val)
        self._anim = anim
        anim.start()

    def update_styles(self):
        self.btn1.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {"#ffffff" if self.active_idx == 0 else "#777777"};
                font-family: "{config.UI_FONT_NAME}";
                font-weight: {"bold" if self.active_idx == 0 else "normal"};
                font-size: {config.FS(9.5)}pt;
                padding-bottom: {config.S(4)}px;
            }}
            QPushButton:hover {{
                color: {"#ffffff" if self.active_idx == 0 else "#bbbbbb"};
            }}
        """)
        self.btn2.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {"#ffffff" if self.active_idx == 1 else "#777777"};
                font-family: "{config.UI_FONT_NAME}";
                font-weight: {"bold" if self.active_idx == 1 else "normal"};
                font-size: {config.FS(9.5)}pt;
                padding-bottom: {config.S(4)}px;
            }}
            QPushButton:hover {{
                color: {"#ffffff" if self.active_idx == 1 else "#bbbbbb"};
            }}
        """)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        half_w = w / 2.0

        # Continuous gray baseline
        p.setPen(QPen(QColor("#333333"), 1.0))
        p.drawLine(0, int(h - 1), int(w), int(h - 1))

        # Bezier-interpolated active tab geometry
        cur_left = self._anim_pos * half_w
        active_rect = QRectF(cur_left, 0, half_w, h - 1)

        # Soft upward flame glow gradient
        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, QColor(26, 122, 62, 75))
        grad.setColorAt(0.45, QColor(26, 122, 62, 20))
        grad.setColorAt(1.0, QColor(26, 122, 62, 0))
        p.fillRect(active_rect, grad)

        # Green accent indicator line
        p.setPen(QPen(QColor("#1a7a3e"), 2.0))
        p.drawLine(int(active_rect.left()), int(h - 1), int(active_rect.right()), int(h - 1))


class DynamicLowerStack(QStackedWidget):
    """
    Stacked widget for the variable lower section of the Welcome Screen.
    Contains Object 0 (Transcription controls) and Object 1 (Silence controls).
    Drives smooth Bezier height morphing and clean wave cross-fade at 60 FPS without lag.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.H0 = config.S(238)
        self.H1 = config.S(348)
        self.setFixedSize(config.S(360), self.H0)
        self._animating = False
        self.mode_switch = None
        self._master_anim = None
        self._eff = None

    def morph_to_index(self, target_idx: int, duration: int = 280):
        if self._animating or target_idx == self.currentIndex() or target_idx >= self.count():
            return
        self._animating = True

        start_h = self.H0 if self.currentIndex() == 0 else self.H1
        target_h = self.H1 if target_idx == 1 else self.H0

        if self.mode_switch is not None:
            self.mode_switch.animate_indicator(target_idx, duration=duration)

        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._eff.setOpacity(1.0)

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        curve = QEasingCurve(QEasingCurve.InOutCubic)
        half = 0.5
        swapped = [False]

        def _on_step(p: float):
            eased = curve.valueForProgress(p)
            cur_h = int(start_h + (target_h - start_h) * eased)
            self.setFixedHeight(cur_h)

            if self._eff is not None:
                if p < half:
                    # Fade out outgoing lower section: 1.0 -> 0.0
                    p_out = p / half
                    self._eff.setOpacity(1.0 - p_out)
                else:
                    if not swapped[0]:
                        swapped[0] = True
                        self.setCurrentIndex(target_idx)
                    # Fade in incoming lower section: 0.0 -> 1.0
                    p_in = (p - half) / (1.0 - half)
                    self._eff.setOpacity(p_in)

        def _on_finished():
            if not swapped[0]:
                self.setCurrentIndex(target_idx)
            self.setFixedHeight(target_h)
            self.setGraphicsEffect(None)
            self._eff = None
            self._animating = False
            self._master_anim = None

        anim.valueChanged.connect(_on_step)
        anim.finished.connect(_on_finished)
        self._master_anim = anim
        anim.start()



def build_welcome_view(win) -> QWidget:
    """Build Page 0 of the main stack: Welcome / Configuration screen."""
    prefs = win.engine.load_preferences() or {}
    is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))
    page = QWidget()
    page.setObjectName("page_welcome")
    page.setStyleSheet(f"QWidget#page_welcome {{ background-color: {config.BG_COLOR}; }}")

    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    outer.setAlignment(Qt.AlignCenter)

    inner = QWidget()
    inner.setObjectName("welcome_inner")
    inner.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    inner.setStyleSheet("QWidget#welcome_inner { background: transparent; }")

    inner_layout = QVBoxLayout(inner)
    inner_layout.setSizeConstraint(QLayout.SetFixedSize)
    inner_layout.setContentsMargins(0, 0, 0, 0)
    inner_layout.setSpacing(0)
    inner_layout.setAlignment(Qt.AlignTop)

    # ── 1. Shared Title (Restored Vector Logo with 20% reduced spacing: 32px) ──
    win.welcome_title = WelcomeBrandingWidget(inner)
    inner_layout.addWidget(win.welcome_title, 0, Qt.AlignCenter)
    inner_layout.addSpacing(config.S(32))

    # ── 2. Underline Glow Mode Switcher (Aligned flush with inputs) ────────────
    win.welcome_mode_switch = AnimatedUnderlineGlowModeSwitch(
        win.txt("titlebar_transcript"),
        win.txt("msg_standalone_silence"),
        inner
    )
    win.welcome_mode_switch.setFixedWidth(config.S(360))
    inner_layout.addWidget(win.welcome_mode_switch, 0, Qt.AlignCenter)
    inner_layout.addSpacing(config.S(16))

    def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
        row = QVBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(config.S(4))
        lbl = QLabel(label_text)
        lbl.setFixedHeight(config.S(18))
        lbl.setStyleSheet(
            f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
        )
        row.addWidget(lbl)
        row.addWidget(widget)
        return row

    # ── 3. SHARED UPPER CONTROLS: Timeline & Track Selection ─────────────────
    # Shared Timeline Selection
    win.combo_tl_0 = CustomDropdown([])
    win.combo_tl_0.setFixedHeight(config.S(30))
    win.combo_tl_0.valueChanged.connect(
        lambda tl: win._on_timeline_selected(tl, win.combo_tr_0, None)
    )
    # Alias combo_tl_1 to combo_tl_0 for full backwards compatibility
    win.combo_tl_1 = win.combo_tl_0

    _vbox_tl0 = QVBoxLayout()
    _vbox_tl0.setContentsMargins(0, 0, 0, 0)
    _vbox_tl0.setSpacing(config.S(4))
    _lbl_tl0 = QLabel(win.txt("lbl_timeline_selection"))
    _lbl_tl0.setFixedHeight(config.S(18))
    _lbl_tl0.setStyleSheet(
        f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    _hbox_tl0 = QHBoxLayout()
    _hbox_tl0.setContentsMargins(0, 0, 0, 0)
    _hbox_tl0.setSpacing(config.S(4))
    _hbox_tl0.setAlignment(Qt.AlignVCenter)
    _hbox_tl0.addWidget(win.combo_tl_0, 1)

    win.btn_ref_tl0 = ReloadButton(size=30)
    win.btn_ref_tl0.setToolTip(win.txt("tt_refresh_timelines"))
    win.btn_ref_tl0.clicked.connect(win._populate_timeline_track_combos)
    win.btn_ref_tl1 = win.btn_ref_tl0
    _hbox_tl0.addWidget(win.btn_ref_tl0)

    _vbox_tl0.addWidget(_lbl_tl0)
    _vbox_tl0.addLayout(_hbox_tl0)
    
    tl_container = QWidget()
    tl_container.setFixedWidth(config.S(360))
    tl_container_lay = QVBoxLayout(tl_container)
    tl_container_lay.setContentsMargins(0, 0, 0, 0)
    tl_container_lay.setSpacing(0)
    tl_container_lay.addLayout(_vbox_tl0)
    inner_layout.addWidget(tl_container, 0, Qt.AlignCenter)
    inner_layout.addSpacing(config.S(16))

    # Shared Tracks Selection
    win.combo_tr_0 = MultiSelectDropdown([])
    win.combo_tr_0.setFixedHeight(config.S(30))
    win.combo_tr_1 = win.combo_tr_0

    tr_container = QWidget()
    tr_container.setFixedWidth(config.S(360))
    tr_container_lay = QVBoxLayout(tr_container)
    tr_container_lay.setContentsMargins(0, 0, 0, 0)
    tr_container_lay.setSpacing(0)
    tr_container_lay.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_0))
    inner_layout.addWidget(tr_container, 0, Qt.AlignCenter)
    inner_layout.addSpacing(config.S(16))

    # ── 4. DYNAMIC LOWER SECTION STACK ───────────────────────────────────────
    win.welcome_stack = DynamicLowerStack(inner)
    win.welcome_stack.setStyleSheet("background: transparent;")
    win.welcome_stack.mode_switch = win.welcome_mode_switch
    inner_layout.addWidget(win.welcome_stack, 0, Qt.AlignCenter)

    win.welcome_mode_switch.on_change = lambda idx: win.welcome_stack.morph_to_index(idx)
    win.welcome_stack.currentChanged.connect(lambda idx: win.welcome_mode_switch.set_index(idx, trigger_callback=False))

    # ═══════════════════════════════════════════════════════════════
    # OBJECT 0: TRANSCRIPTION LOWER CONTROLS
    # ═══════════════════════════════════════════════════════════════
    low_trans = QWidget()
    low_trans.setStyleSheet("background: transparent;")
    l_trans = QVBoxLayout(low_trans)
    l_trans.setContentsMargins(0, 0, 0, 0)
    l_trans.setSpacing(0)
    l_trans.setAlignment(Qt.AlignTop)

    win.slider_widget = QWidget()
    win.slider_widget.setStyleSheet("background: transparent;")
    win.slider_widget.setFixedWidth(config.S(360) + (config.S(360) if is_more_accurate else 0))
    win.slider_layout = QHBoxLayout(win.slider_widget)
    win.slider_layout.setContentsMargins(0, 0, 0, 0)
    win.slider_layout.setSpacing(0)
    win.slider_layout.setAlignment(Qt.AlignTop)
    
    win.settings_container = QWidget()
    win.settings_container.setFixedWidth(config.S(360))
    win.settings_container.setStyleSheet("background: transparent;")
    win.settings_layout = QVBoxLayout(win.settings_container)
    win.settings_layout.setContentsMargins(0, 0, 0, 0)
    win.settings_layout.setSpacing(0)
    win.settings_layout.setAlignment(Qt.AlignTop)
    win.slider_layout.addWidget(win.settings_container)

    # Language
    lang_items = list(config.SUPPORTED_LANGUAGES.values())
    win._combo_lang = SearchableDropdown(lang_items)
    win._combo_lang.setFixedHeight(config.S(30))
    saved_lang = prefs.get('lang', '')
    display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
    placeholder = win.txt("lbl_choose_recording_language") if hasattr(win, 'txt') else "Choose recording language"
    win._combo_lang.setText(display_name if display_name in lang_items else placeholder)
    win._combo_lang.valueChanged.connect(lambda v: win.engine.save_preferences({"lang": v}))
    win.settings_layout.addLayout(_row(win.txt("lbl_lang"), win._combo_lang))
    win.settings_layout.addSpacing(config.S(16))

    # Model
    model_items = [
        "Tiny (I wouldn't, ~0.3GB)",
        "Base (Dogsh!t, ~0.5GB)",
        "Small (Bearable, ~1.0GB)",
        "Medium (Okayish, ~2.5GB)",
        "Large Turbo (Best Balance, ~2.5GB)",
        "Large (Recommended, ~3.5GB)",
    ]
    win._combo_model = CustomDropdown(model_items)
    win._combo_model.max_visible_items = 6
    win._combo_model.setFixedHeight(config.S(30))
    
    saved_model = prefs.get("model", "")
    if saved_model in model_items:
        win._combo_model.setText(saved_model)
    else:
        win._combo_model.setText(model_items[4])
        win.engine.save_preferences({"model": model_items[4]})
        
    win._combo_model.valueChanged.connect(lambda v: win.engine.save_preferences({"model": v}))
    
    info_model = QLabel()
    info_icon_path = get_layout_icon_path("information.png")
    if os.path.exists(info_icon_path):
        pix = QPixmap(info_icon_path)
        dpr = win.devicePixelRatioF() if hasattr(win, 'devicePixelRatioF') else 1.0
        s = config.S(18)
        scaled_pix = pix.scaled(int(s * dpr), int(s * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_pix.setDevicePixelRatio(dpr)
        info_model.setPixmap(scaled_pix)
    else:
        info_model.setText("i")
        info_model.setStyleSheet(f"color: #888888; font-size: {config.FS(10)}pt; font-weight: bold;")
        
    info_model.custom_tooltip_text = f"<div style='max-width: {config.S(320)}px; white-space: pre-wrap;'>{win.txt('tt_model_size_info')}</div>"
    info_model.setCursor(Qt.WhatsThisCursor)
    
    def instant_tooltip_model(event):
        if hasattr(win, 'shared_tooltip'):
            win.shared_tooltip.show_global(info_model.custom_tooltip_text, QCursor.pos())
    info_model.enterEvent = instant_tooltip_model
    info_model.leaveEvent = lambda e: win.shared_tooltip.hide() if hasattr(win, 'shared_tooltip') else None
    info_model.installEventFilter(win)
    
    row_model_lbl = QHBoxLayout()
    row_model_lbl.setContentsMargins(0, 0, 0, 0)
    row_model_lbl.setSpacing(config.S(5))
    lbl_model = QLabel(win.txt("lbl_model"))
    lbl_model.setFixedHeight(config.S(18))
    lbl_model.setStyleSheet(
        f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    row_model_lbl.addWidget(lbl_model)
    row_model_lbl.addWidget(info_model)
    row_model_lbl.addStretch()
    
    vbox_model = QVBoxLayout()
    vbox_model.setContentsMargins(0, 0, 0, 0)
    vbox_model.setSpacing(config.S(4))
    vbox_model.addLayout(row_model_lbl)
    vbox_model.addWidget(win._combo_model)
    
    win.settings_layout.addLayout(vbox_model)
    win.settings_layout.addSpacing(config.S(20))

    # More Accurate Mode
    win.tgl_more_accurate = ToggleSwitch()
    is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))
    win.tgl_more_accurate.setChecked(is_more_accurate)
    win.tgl_more_accurate.toggled.connect(win._on_more_accurate_toggled)
    
    lbl_acc = QLabel(win.txt("lbl_more_accurate"))
    lbl_acc.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(10)}pt;")
    
    info_acc = QLabel()
    if os.path.exists(info_icon_path):
        pix = QPixmap(info_icon_path)
        dpr = win.devicePixelRatioF() if hasattr(win, 'devicePixelRatioF') else 1.0
        s = config.S(18)
        scaled_pix = pix.scaled(int(s * dpr), int(s * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled_pix.setDevicePixelRatio(dpr)
        info_acc.setPixmap(scaled_pix)
    else:
        info_acc.setText("i")
        info_acc.setStyleSheet(f"color: #888888; font-size: {config.FS(10)}pt; font-weight: bold;")
    tt_acc_text = win.txt("tt_more_accurate")
    info_acc.custom_tooltip_text = f"<div style='max-width: {config.S(350)}px; white-space: pre-wrap;'>{tt_acc_text}</div>"
    info_acc.setCursor(Qt.WhatsThisCursor)
    
    def instant_tooltip_acc(event):
        if hasattr(win, 'shared_tooltip'):
            win.shared_tooltip.show_global(info_acc.custom_tooltip_text, QCursor.pos())
    info_acc.enterEvent = instant_tooltip_acc
    info_acc.leaveEvent = lambda e: win.shared_tooltip.hide() if hasattr(win, 'shared_tooltip') else None
    
    row_acc = QHBoxLayout()
    row_acc.setSpacing(0)
    row_acc.addWidget(lbl_acc)
    row_acc.addStretch()
    row_acc.addWidget(info_acc)
    row_acc.addSpacing(config.S(6))
    row_acc.addWidget(win.tgl_more_accurate)
    
    win.settings_layout.addLayout(row_acc)
    win.settings_layout.addSpacing(config.S(28))

    # Script Container
    win.script_container = QWidget()
    win.script_container.setFixedWidth(config.S(360) if is_more_accurate else 0)
    win.script_container.setVisible(bool(is_more_accurate))
    win.script_container.setStyleSheet("background: transparent;")
    
    win.script_container_layout = QHBoxLayout(win.script_container)
    win.script_container_layout.setContentsMargins(config.S(10), 0, 0, 0)
    win.script_container_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)
    
    win.script_content_widget = QWidget()
    win.script_content_widget.setFixedWidth(config.S(350))
    win.script_layout = QVBoxLayout(win.script_content_widget)
    win.script_layout.setContentsMargins(0, 0, 0, 0)
    win.script_layout.setSpacing(0)
    win.script_layout.setAlignment(Qt.AlignTop)
    
    _lbl_script = QLabel(win.txt("lbl_script"))
    _lbl_script.setFixedHeight(config.S(18))
    _lbl_script.setStyleSheet(
        f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    win.script_layout.addWidget(_lbl_script)
    win.script_layout.addSpacing(config.S(4))
    
    win.welcome_script_edit = QTextEdit()
    win.welcome_script_edit.setFixedHeight(config.S(255))
    win.welcome_script_edit.setAcceptRichText(False)
    win.welcome_script_edit.setStyleSheet(f"""
        QTextEdit {{
            background-color: #1e1e1e; color: #d4d4d4; 
            border: 1px solid #3a3a3a; border-radius: {config.S(4)}px; 
            padding: {config.S(6)}px {config.S(10)}px; outline: none; font-family: '{config.UI_FONT_NAME}';
            font-size: {config.FS(9.5)}pt;
        }}
        QTextEdit:focus {{ border: 1px solid #1a7a3e; }}
    """)
    win.script_layout.addWidget(win.welcome_script_edit)
    
    win.btn_import_welcome_script = QPushButton(win.txt("btn_import_script"))
    win.btn_import_welcome_script.setObjectName("btn_ghost")
    win.btn_import_welcome_script.setCursor(Qt.PointingHandCursor)
    win.btn_import_welcome_script.setFixedHeight(config.S(30))
    win.btn_import_welcome_script.setStyleSheet(f"""
        QPushButton#btn_ghost {{
            background-color: #1e1e1e; color: {config.FG_COLOR};
            font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt;
            border: 1px solid #3a3a3a; border-radius: {config.S(4)}px; padding: 0 {config.S(12)}px;
        }}
        QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
        QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
    """)
    win.btn_import_welcome_script.clicked.connect(win._on_import_script)
    win.script_container_layout.addWidget(win.script_content_widget)
    
    win.slider_layout.addWidget(win.script_container)
    
    h_slider = QHBoxLayout()
    h_slider.setContentsMargins(0, 0, 0, 0)
    h_slider.addStretch()
    h_slider.addWidget(win.slider_widget)
    h_slider.addStretch()
    l_trans.addLayout(h_slider)
    
    win.settings_container.raise_()

    # Action buttons
    btn_row_t = QHBoxLayout()
    btn_row_t.setContentsMargins(0, 0, 0, 0)
    btn_row_t.setSpacing(0)

    btn_import = QPushButton(win.txt("btn_import_project"))
    btn_import.setObjectName("btn_ghost")
    btn_import.setCursor(Qt.PointingHandCursor)
    btn_import.setFixedHeight(config.S(30))
    btn_import.setStyleSheet(f"""
        QPushButton#btn_ghost {{
            background-color: #1e1e1e; color: {config.FG_COLOR};
            font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt;
            border: 1px solid #3a3a3a; border-radius: {config.S(4)}px; padding: 0 {config.S(14)}px;
        }}
        QPushButton#btn_ghost:hover {{ background-color: #2a2d2e; }}
        QPushButton#btn_ghost:pressed {{ background-color: #3a3d3e; }}
    """)
    btn_import.clicked.connect(win._on_import_project)
    btn_row_t.addWidget(btn_import)

    btn_analyze = QPushButton(win.txt("btn_analyze"))
    btn_analyze.setObjectName("btn_primary")
    btn_analyze.setIcon(get_play_icon(config.S(12), "#ffffff", 1.5))
    btn_analyze.setIconSize(QSize(config.S(12), config.S(12)))
    btn_analyze.setCursor(Qt.PointingHandCursor)
    btn_analyze.setFixedHeight(config.S(30))
    btn_analyze.setStyleSheet(f"""
        QPushButton#btn_primary {{
            background-color: {config.BTN_BG}; color: #ffffff;
            font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt; font-weight: bold;
            border: none; border-radius: {config.S(4)}px; padding: 0 {config.S(18)}px;
        }}
        QPushButton#btn_primary:hover {{ background-color: {config.BTN_ACTIVE}; }}
        QPushButton#btn_primary:pressed {{ background-color: #176e38; }}
    """)
    btn_analyze.clicked.connect(win._on_start_analysis)
    btn_row_t.addSpacing(config.S(8))
    btn_row_t.addWidget(btn_analyze)
    
    win.btn_import_wrapper = QWidget()
    wrapper_l = QHBoxLayout(win.btn_import_wrapper)
    wrapper_l.setContentsMargins(config.S(8), 0, 0, 0)
    wrapper_l.setSpacing(0)
    wrapper_l.addWidget(win.btn_import_welcome_script)
    btn_row_t.addWidget(win.btn_import_wrapper)
    
    win.btn_import_wrapper.setVisible(prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False)))
    
    btn_row_t_centered = QHBoxLayout()
    btn_row_t_centered.setContentsMargins(0, 0, 0, 0)
    btn_row_t_centered.addStretch()
    btn_row_t_centered.addLayout(btn_row_t)
    btn_row_t_centered.addStretch()
    
    l_trans.addLayout(btn_row_t_centered)
    l_trans.addSpacing(config.S(16))
    l_trans.addStretch()

    win.welcome_stack.addWidget(low_trans)

    # ═══════════════════════════════════════════════════════════════
    # OBJECT 1: FAST SILENCE LOWER CONTROLS
    # ═══════════════════════════════════════════════════════════════
    low_fast = QWidget()
    low_fast.setStyleSheet("background: transparent;")
    l_fast = QVBoxLayout(low_fast)
    l_fast.setContentsMargins(0, 0, 0, 0)
    l_fast.setSpacing(0)
    l_fast.setAlignment(Qt.AlignTop)

    input_style = f"""
        QLineEdit {{
            background-color: #1e1e1e; color: #d4d4d4; 
            border: 1px solid #3a3a3a; border-radius: {config.S(4)}px; 
            padding: {config.S(4)}px {config.S(8)}px;
            outline: none;
            font-family: '{config.UI_FONT_NAME}';
            font-size: {config.FS(9.5)}pt;
        }}
        QLineEdit:focus {{ border: 1px solid #1a7a3e; outline: none; }}
    """

    def _row_rst(label_text, widget, reset_val_str):
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(config.S(4))
        lbl = QLabel(label_text)
        lbl.setFixedHeight(config.S(18))
        lbl.setStyleSheet(
            f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent;"
        )
        vbox.addWidget(lbl)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(config.S(4))
        hbox.setAlignment(Qt.AlignVCenter)
        hbox.addWidget(widget, 1)

        rst = ReloadButton(size=30)
        rst.setToolTip(win.txt("tt_reset_to_default"))
        rst.clicked.connect(lambda: widget.setText(reset_val_str))
        hbox.addWidget(rst)
        vbox.addLayout(hbox)
        return vbox

    win.input_fs_thresh = QLineEdit()
    win.input_fs_thresh.setText(str(prefs.get('silence_threshold_db', prefs.get('ui_spin_thresh', -42.0))))
    win.input_fs_thresh.setStyleSheet(input_style)
    win.input_fs_thresh.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_silence_threshold_db"), win.input_fs_thresh, "-42.0"))
    l_fast.addSpacing(config.S(16))

    win.input_fs_pad = QLineEdit()
    win.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.1)))
    win.input_fs_pad.setStyleSheet(input_style)
    win.input_fs_pad.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_padding_s"), win.input_fs_pad, "0.1"))
    l_fast.addSpacing(config.S(16))

    win.input_fs_min_dur = QLineEdit()
    win.input_fs_min_dur.setText(str(prefs.get('silence_min_dur', 0.2)))
    win.input_fs_min_dur.setStyleSheet(input_style)
    win.input_fs_min_dur.setFixedHeight(config.S(30))
    win.input_fs_min_dur.setToolTip(
        "Minimum gap duration (s) to classify as silence. "
        "Lower = more gaps detected. Shared with post-transcript mode."
    )
    l_fast.addLayout(_row_rst(win.txt("lbl_min_silence_dur"), win.input_fs_min_dur, "0.2"))
    l_fast.addSpacing(config.S(20))

    # MODE TOGGLES
    row_fs_cut = QHBoxLayout()
    lbl_fs_cut = QLabel(win.txt("lbl_cut_silence_directly"))
    lbl_fs_cut.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(10)}pt; background: transparent;")
    row_fs_cut.addWidget(lbl_fs_cut)
    row_fs_cut.addStretch()
    info_fs_cut = win._create_info_icon("tt_cut_silence_directly")
    row_fs_cut.addWidget(info_fs_cut)
    row_fs_cut.addSpacing(config.S(6))
    win.tgl_fs_cut = ToggleSwitch()
    win.tgl_fs_cut.setChecked(prefs.get('fs_cut_mode', True), animated=False)
    row_fs_cut.addWidget(win.tgl_fs_cut)
    l_fast.addLayout(row_fs_cut)
    l_fast.addSpacing(config.S(14))

    row_fs_mark = QHBoxLayout()
    lbl_fs_mark = QLabel(win.txt("lbl_mark_silence_with_color"))
    lbl_fs_mark.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(10)}pt; background: transparent;")
    row_fs_mark.addWidget(lbl_fs_mark)
    row_fs_mark.addStretch()
    info_fs_mark = win._create_info_icon("tt_mark_silence_with_color")
    row_fs_mark.addWidget(info_fs_mark)
    row_fs_mark.addSpacing(config.S(6))
    win.tgl_fs_mark = ToggleSwitch()
    win.tgl_fs_mark.setChecked(prefs.get('fs_mark_mode', False), animated=False)
    row_fs_mark.addWidget(win.tgl_fs_mark)
    l_fast.addLayout(row_fs_mark)
    l_fast.addSpacing(config.S(28))

    win.tgl_fs_cut.toggled.connect(lambda c: win.tgl_fs_mark.setChecked(False) if c else None)
    win.tgl_fs_mark.toggled.connect(lambda c: win.tgl_fs_cut.setChecked(False) if c else None)
    win.tgl_fs_cut.toggled.connect(lambda v: win._save_single_pref('fs_cut_mode', v))
    win.tgl_fs_mark.toggled.connect(lambda v: win._save_single_pref('fs_mark_mode', v))

    btn_row_fs = QHBoxLayout()
    btn_row_fs.setContentsMargins(0, 0, 0, 0)
    btn_row_fs.addStretch()

    win.btn_run_fs = QPushButton(win.txt("btn_run_standalone_silence"))
    win.btn_run_fs.setCursor(Qt.PointingHandCursor)
    win.btn_run_fs.setFixedHeight(config.S(30))
    win.btn_run_fs.setStyleSheet(f"""
        QPushButton {{
            background-color: {config.BTN_BG}; color: #ffffff;
            font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt; font-weight: bold;
            border: none; border-radius: {config.S(4)}px; padding: 0 {config.S(24)}px;
        }}
        QPushButton:hover {{ background-color: {config.BTN_ACTIVE}; }}
        QPushButton:pressed {{ background-color: #176e38; }}
    """)
    win.btn_run_fs.clicked.connect(win._on_fast_silence)
    btn_row_fs.addWidget(win.btn_run_fs)
    btn_row_fs.addStretch()
    
    l_fast.addLayout(btn_row_fs)
    l_fast.addSpacing(config.S(16))
    l_fast.addStretch()

    win.welcome_stack.addWidget(low_fast)

    outer.addWidget(inner, 0, Qt.AlignCenter)
    return page
