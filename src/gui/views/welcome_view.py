#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: welcome_view.py
ROLE: GUI View
DESCRIPTION:
Welcome screen with smooth Y-axis vertical centering of both workspaces,
hardware-accelerated sequential fade transition (zero flash / double-blending),
and rock-solid horizontal centering without jitter during scenario expansion.
"""

import os
from PySide6.QtCore import Qt, QSize, QEasingCurve, QVariantAnimation, QRectF, QRect
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QStackedWidget,
    QLineEdit, QTextEdit, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QLinearGradient
from PySide6.QtSvg import QSvgRenderer

import config
from gui.utils import get_play_icon, get_layout_icon_path
from gui.widgets.buttons import CustomDropdown, SearchableDropdown, MultiSelectDropdown, ToggleSwitch, ReloadButton


class _WorkspaceFadeCanvas(QWidget):
    """
    Renders a hardware-accelerated sequential Fade Out -> Fade In transition.
    Renders on a solid background matching config.BG_COLOR to completely eliminate
    double alpha-blending, brightness flashes, and color glitches.
    Phase 1 (0.0 -> 0.45): Pure fade OUT of outgoing workspace (1.0 -> 0.0).
    Phase 2 (0.45 -> 0.55): Clean darkness buffer with zero overlapping controls.
    Phase 3 (0.55 -> 1.0): Pure fade IN of incoming workspace (0.0 -> 1.0).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.pix_from = None
        self.pix_to = None
        self.progress = 0.0
        self.hide()

    def set_transition(self, pix_from: QPixmap, pix_to: QPixmap):
        self.pix_from = pix_from
        self.pix_to = pix_to
        self.progress = 0.0
        self.show()
        self.raise_()

    def set_progress(self, p: float):
        self.progress = p
        self.update()

    def finish(self):
        self.pix_from = None
        self.pix_to = None
        self.progress = 0.0
        self.hide()

    def paintEvent(self, event):
        if not self.pix_from and not self.pix_to:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Solid background ensures underlying live widgets or parent widgets cannot bleed through
        painter.fillRect(self.rect(), QColor(config.BG_COLOR))

        p = self.progress
        w = self.width()

        # Seamless overlapping cross-fade without dead black frames
        if self.pix_from and p < 0.65:
            alpha_from = max(0.0, min(1.0, (0.65 - p) / 0.65))
            painter.setOpacity(alpha_from)
            x_from = (w - self.pix_from.width()) // 2
            painter.drawPixmap(x_from, 0, self.pix_from)

        if self.pix_to and p > 0.35:
            alpha_to = max(0.0, min(1.0, (p - 0.35) / 0.65))
            painter.setOpacity(alpha_to)
            x_to = (w - self.pix_to.width()) // 2
            painter.drawPixmap(x_to, 0, self.pix_to)

        painter.end()


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

    def animate_indicator(self, idx: int, duration: int = 240):
        target_pos = float(idx)
        if self._anim is not None:
            self._anim.stop()

        if duration <= 0:
            self._anim_pos = target_pos
            self.update()
            return

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(self._anim_pos)
        anim.setEndValue(target_pos)
        anim.setEasingCurve(QEasingCurve.OutCubic)

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


class WelcomePageView(QWidget):
    """
    Welcome / Configuration screen (Page 0 of the main stack).
    Manages smooth Y-axis vertical centering of both workspaces,
    zero-jitter horizontal positioning during scenario expansion,
    and glitch-free sequential fade transitions.
    """
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.setObjectName("page_welcome")
        self.setStyleSheet(f"QWidget#page_welcome {{ background-color: {config.BG_COLOR}; }}")
        self._current_idx = 0
        self._is_animating = False
        self._y_anim = None

        # Content height metrics:
        # Header = Logo (36) + Spacing (24) + Switch (30) + Spacing (20) = 110px
        # Transcript visual height = 328px (total = 438px)
        # Silence visual height = 398px (total = 508px)
        self.H_HEADER = config.S(110)
        self.H_TRANS_VISUAL = config.S(444)
        self.H_SILENCE_VISUAL = config.S(508)
        self.H_MAX_CONTENT = config.S(398)

        # Full-width root container ensuring 100% stable horizontal centering
        self.welcome_root = QWidget(self)
        self.welcome_root.setObjectName("welcome_root")
        self.welcome_root.setStyleSheet("QWidget#welcome_root { background: transparent; }")

        self.root_layout = QVBoxLayout(self.welcome_root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.root_layout.setAlignment(Qt.AlignTop)

        # ── 1. Branding Logo (BadWords) ───────────────────────────────────────
        win.welcome_title = WelcomeBrandingWidget(self.welcome_root)
        self.root_layout.addWidget(win.welcome_title, 0, Qt.AlignCenter)
        self.root_layout.addSpacing(config.S(24))

        # ── 2. Mode Switcher (Transcript | Silence Detection) ─────────────────
        win.welcome_mode_switch = AnimatedUnderlineGlowModeSwitch(
            win.txt("titlebar_transcript"),
            win.txt("msg_standalone_silence"),
            self.welcome_root
        )
        win.welcome_mode_switch.setFixedWidth(config.S(325))
        self.root_layout.addWidget(win.welcome_mode_switch, 0, Qt.AlignCenter)
        self.root_layout.addSpacing(config.S(20))

        # ── 3. Workspace Stack Area ───────────────────────────────────────────
        self.workspace_container = QWidget(self.welcome_root)
        self.workspace_container.setFixedHeight(self.H_MAX_CONTENT)
        self.workspace_container.setStyleSheet("background: transparent;")

        ws_layout = QVBoxLayout(self.workspace_container)
        ws_layout.setContentsMargins(0, 0, 0, 0)
        ws_layout.setSpacing(0)

        win.welcome_stack = QStackedWidget(self.workspace_container)
        win.welcome_stack.setStyleSheet("background: transparent;")
        win.welcome_stack.setFixedHeight(self.H_MAX_CONTENT)
        ws_layout.addWidget(win.welcome_stack)

        self.fade_canvas = _WorkspaceFadeCanvas(self.workspace_container)
        self.fade_canvas.setGeometry(0, 0, self.width(), self.H_MAX_CONTENT)

        self.root_layout.addWidget(self.workspace_container)

        win.welcome_mode_switch.on_change = self.switch_workspace_animated

        # Hook setCurrentIndex on welcome_stack for external programmatic calls
        orig_set_current_index = win.welcome_stack.setCurrentIndex
        def _on_stack_set_index(idx: int):
            orig_set_current_index(idx)
            if self._current_idx != idx and not self._is_animating:
                self.switch_workspace_instant(idx)
        win.welcome_stack.setCurrentIndex = _on_stack_set_index

    def _target_y(self, idx: int) -> int:
        h_visual = self.H_TRANS_VISUAL if idx == 0 else self.H_SILENCE_VISUAL
        avail_h = self.height()
        if avail_h <= 0:
            avail_h = config.S(600)
        return max(config.S(10), (avail_h - h_visual) // 2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        root_h = self.H_HEADER + self.H_MAX_CONTENT
        self.welcome_root.setFixedWidth(w)
        self.workspace_container.setFixedWidth(w)
        self.fade_canvas.setGeometry(0, 0, w, self.H_MAX_CONTENT)
        if not self._is_animating:
            cur_y = self._target_y(self._current_idx)
            self.welcome_root.move(0, cur_y)

    def switch_workspace_animated(self, target_idx: int):
        if self._current_idx == target_idx and not self._is_animating:
            return

        if self._y_anim and self._y_anim.state() == QVariantAnimation.Running:
            self._y_anim.stop()
            self.fade_canvas.finish()

        duration = 280
        self.win.welcome_mode_switch.animate_indicator(target_idx, duration=duration)

        current_w = self.win.welcome_stack.widget(self._current_idx)
        target_w = self.win.welcome_stack.widget(target_idx)

        if current_w is None or target_w is None:
            self.switch_workspace_instant(target_idx)
            return

        w = self.width()
        self.welcome_root.setFixedWidth(w)
        self.workspace_container.setFixedWidth(w)
        self.fade_canvas.setGeometry(0, 0, w, self.H_MAX_CONTENT)

        # 1. Grab snapshot of current outgoing workspace
        pix_from = current_w.grab()

        # 2. Prepare target incoming workspace and grab snapshot
        target_w.resize(self.win.welcome_stack.size())
        pix_to = target_w.grab()

        # 3. Setup canvas & hide live widgets to prevent double-render/flash
        self.fade_canvas.set_transition(pix_from, pix_to)
        current_w.hide()

        start_y = self.welcome_root.y()
        end_y = self._target_y(target_idx)

        self._is_animating = True
        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _step(v: float):
            cur_y = int(start_y + (end_y - start_y) * v)
            self.welcome_root.move(0, cur_y)
            self.fade_canvas.set_progress(v)

        def _done():
            self.welcome_root.move(0, end_y)
            self._current_idx = target_idx
            self.win.welcome_stack.setCurrentIndex(target_idx)
            self.fade_canvas.finish()
            target_w.show()
            target_w.raise_()
            self._is_animating = False

        anim.valueChanged.connect(_step)
        anim.finished.connect(_done)
        self._y_anim = anim
        anim.start()

    def switch_workspace_instant(self, target_idx: int):
        if self._y_anim and self._y_anim.state() == QVariantAnimation.Running:
            self._y_anim.stop()
        self.fade_canvas.finish()
        self._current_idx = target_idx
        self.win.welcome_stack.setCurrentIndex(target_idx)
        w = self.win.welcome_stack.widget(target_idx)
        if w:
            w.show()
            w.raise_()
        self.win.welcome_mode_switch.set_index(target_idx, trigger_callback=False)
        self.win.welcome_mode_switch.animate_indicator(target_idx, duration=0)
        y = self._target_y(target_idx)
        self.welcome_root.move(0, y)
        self._is_animating = False


def build_welcome_view(win) -> QWidget:
    """Build Page 0 of the main stack: Welcome / Configuration screen."""
    prefs = win.engine.load_preferences() or {}
    is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))
    
    page = WelcomePageView(win)

    def _row(label_text: str, widget: QWidget) -> QVBoxLayout:
        row_l = QVBoxLayout()
        row_l.setContentsMargins(0, 0, 0, 0)
        row_l.setSpacing(config.S(4))
        lbl = QLabel(label_text)
        lbl.setFixedHeight(config.S(18))
        lbl.setStyleSheet(
            f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
        )
        row_l.addWidget(lbl)
        row_l.addWidget(widget)
        return row_l

    # ═══════════════════════════════════════════════════════════════
    # PAGE 0: TRANSCRIPTION WORKSPACE
    # ═══════════════════════════════════════════════════════════════
    p_transcription = QWidget()
    p_transcription.setStyleSheet("background: transparent;")
    l_trans = QVBoxLayout(p_transcription)
    l_trans.setContentsMargins(0, 0, 0, 0)
    l_trans.setSpacing(0)
    l_trans.setAlignment(Qt.AlignTop)

    win.slider_widget = QWidget()
    win.slider_widget.setStyleSheet("background: transparent;")
    win.slider_layout = QHBoxLayout(win.slider_widget)
    win.slider_layout.setContentsMargins(0, 0, 0, 0)
    win.slider_layout.setSpacing(0)
    win.slider_layout.setAlignment(Qt.AlignTop)

    # ── Left Column: Settings Container (325px + shake padding) ──────────────
    pad = config.S(10)
    win.settings_container = QWidget()
    win.settings_container.setFixedWidth(config.S(325) + 2 * pad)
    win.settings_container.setStyleSheet("background: transparent;")
    win.settings_layout = QVBoxLayout(win.settings_container)
    win.settings_layout.setContentsMargins(pad, 0, pad, 0)
    win.settings_layout.setSpacing(0)
    win.settings_layout.setAlignment(Qt.AlignTop)
    win.slider_layout.addWidget(win.settings_container)

    # 1. Timeline Selection
    win.combo_tl_0 = CustomDropdown([])
    win.combo_tl_0.setFixedHeight(config.S(30))
    win.combo_tl_0.valueChanged.connect(
        lambda tl: win._on_timeline_selected(tl, win.combo_tr_0, getattr(win, 'combo_tl_1', None))
    )
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
    _hbox_tl0.addWidget(win.btn_ref_tl0)

    _vbox_tl0.addWidget(_lbl_tl0)
    _vbox_tl0.addLayout(_hbox_tl0)
    win.settings_layout.addLayout(_vbox_tl0)
    win.settings_layout.addSpacing(config.S(10))

    # 2. Tracks Selection
    win.combo_tr_0 = MultiSelectDropdown([])
    win.combo_tr_0.setFixedHeight(config.S(30))
    win.settings_layout.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_0))
    win.settings_layout.addSpacing(config.S(10))

    # 3. Language Selection
    lang_items = list(config.SUPPORTED_LANGUAGES.values())
    win._combo_lang = SearchableDropdown(lang_items)
    win._combo_lang.setFixedHeight(config.S(30))
    saved_lang = prefs.get('lang', '')
    display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
    placeholder = win.txt("lbl_choose_recording_language") if hasattr(win, 'txt') else "Choose recording language"
    win._combo_lang.setText(display_name if display_name in lang_items else placeholder)
    win._combo_lang.valueChanged.connect(lambda v: win.engine.save_preferences({"lang": v}))
    win.settings_layout.addLayout(_row(win.txt("lbl_lang"), win._combo_lang))
    win.settings_layout.addSpacing(config.S(10))

    # 4. Model Selection
    model_items = [
        "Tiny (I wouldn't, ~0.3GB)",
        "Base (Dogsh!t, ~0.5GB)",
        "Small (Bearable, ~1.0GB)",
        "Medium (Okayish, ~1.5GB)",
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

    info_model = win._create_info_icon("tt_model_size_info")

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
    win.settings_layout.addSpacing(config.S(16))

    # 5. More Accurate Mode Toggle
    win.tgl_more_accurate = ToggleSwitch()
    win.tgl_more_accurate.setChecked(is_more_accurate)
    win.tgl_more_accurate.toggled.connect(win._on_more_accurate_toggled)

    lbl_acc = QLabel(win.txt("lbl_more_accurate"))
    lbl_acc.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt;")

    info_acc = win._create_info_icon("tt_more_accurate")

    w_row_acc = QWidget()
    w_row_acc.setFixedHeight(config.S(30))
    row_acc = QHBoxLayout(w_row_acc)
    row_acc.setContentsMargins(0, 0, 0, 0)
    row_acc.setSpacing(0)
    row_acc.addWidget(lbl_acc)
    row_acc.addStretch()
    row_acc.addWidget(info_acc)
    row_acc.addSpacing(config.S(6))
    row_acc.addWidget(win.tgl_more_accurate)

    win.settings_layout.addWidget(w_row_acc)

    # ── Right Column: Full-Height Script Container (325px + shake padding) ───
    target_script_w = config.S(16) + config.S(325) + pad
    win.script_container = QWidget()
    win.script_container.setFixedWidth(target_script_w if is_more_accurate else 0)
    win.script_container.setVisible(bool(is_more_accurate))
    win.script_container.setStyleSheet("background: transparent;")

    win.script_container_layout = QHBoxLayout(win.script_container)
    win.script_container_layout.setContentsMargins(config.S(16), 0, pad, 0)
    win.script_container_layout.setAlignment(Qt.AlignRight | Qt.AlignTop)

    win.script_content_widget = QWidget()
    win.script_content_widget.setFixedWidth(config.S(325))
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
    # Matches top of Timeline flush with bottom of More Accurate toggle: 256px.
    win.welcome_script_edit.setFixedHeight(config.S(256))
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
    win.script_container_layout.addWidget(win.script_content_widget)
    win.slider_layout.addWidget(win.script_container)

    w_settings = config.S(325) + 2 * pad
    w_initial_slider = (w_settings + target_script_w) if is_more_accurate else w_settings
    win.slider_widget.setFixedWidth(w_initial_slider)

    h_slider = QHBoxLayout()
    h_slider.setContentsMargins(0, 0, 0, 0)
    h_slider.addStretch()
    h_slider.addWidget(win.slider_widget)
    h_slider.addStretch()
    l_trans.addLayout(h_slider)

    # ── Action Buttons (STATIONARY IN THE CENTER BELOW SLIDER) ────────────────
    l_trans.addSpacing(config.S(20))

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

    win.btn_import_wrapper = QWidget()
    win.btn_import_wrapper.setStyleSheet("background: transparent;")
    wrapper_l = QHBoxLayout(win.btn_import_wrapper)
    wrapper_l.setContentsMargins(config.S(8), 0, 0, 0)
    wrapper_l.setSpacing(0)
    wrapper_l.addWidget(win.btn_import_welcome_script)
    btn_row_t.addWidget(win.btn_import_wrapper)
    win.btn_import_wrapper.setVisible(bool(is_more_accurate))

    btn_row_t_centered = QHBoxLayout()
    btn_row_t_centered.setContentsMargins(0, 0, 0, 0)
    btn_row_t_centered.addStretch()
    btn_row_t_centered.addLayout(btn_row_t)
    btn_row_t_centered.addStretch()

    l_trans.addLayout(btn_row_t_centered)
    l_trans.addStretch()

    win.welcome_stack.addWidget(p_transcription)

    # ═══════════════════════════════════════════════════════════════
    # PAGE 1: FAST SILENCE WORKSPACE (325px)
    # ═══════════════════════════════════════════════════════════════
    p_silence_outer = QWidget()
    p_silence_outer.setStyleSheet("background: transparent;")
    p_silence_outer_layout = QHBoxLayout(p_silence_outer)
    p_silence_outer_layout.setContentsMargins(0, 0, 0, 0)
    p_silence_outer_layout.setSpacing(0)

    p_silence = QWidget()
    p_silence.setFixedWidth(config.S(325) + 2 * pad)
    p_silence.setStyleSheet("background: transparent;")
    l_fast = QVBoxLayout(p_silence)
    l_fast.setContentsMargins(pad, 0, pad, 0)
    l_fast.setSpacing(0)
    l_fast.setAlignment(Qt.AlignTop)

    p_silence_outer_layout.addStretch()
    p_silence_outer_layout.addWidget(p_silence)
    p_silence_outer_layout.addStretch()

    # 1. Timeline Selection
    win.combo_tl_1 = CustomDropdown([])
    win.combo_tl_1.setFixedHeight(config.S(30))
    win.combo_tl_1.valueChanged.connect(
        lambda tl: win._on_timeline_selected(tl, win.combo_tr_1, win.combo_tl_0)
    )
    _vbox_tl1 = QVBoxLayout()
    _vbox_tl1.setContentsMargins(0, 0, 0, 0)
    _vbox_tl1.setSpacing(config.S(4))
    _lbl_tl1 = QLabel(win.txt("lbl_timeline_selection"))
    _lbl_tl1.setFixedHeight(config.S(18))
    _lbl_tl1.setStyleSheet(
        f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
        f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
    )
    _hbox_tl1 = QHBoxLayout()
    _hbox_tl1.setContentsMargins(0, 0, 0, 0)
    _hbox_tl1.setSpacing(config.S(4))
    _hbox_tl1.setAlignment(Qt.AlignVCenter)
    _hbox_tl1.addWidget(win.combo_tl_1, 1)

    win.btn_ref_tl1 = ReloadButton(size=30)
    win.btn_ref_tl1.setToolTip(win.txt("tt_refresh_timelines"))
    win.btn_ref_tl1.clicked.connect(win._populate_timeline_track_combos)
    _hbox_tl1.addWidget(win.btn_ref_tl1)

    _vbox_tl1.addWidget(_lbl_tl1)
    _vbox_tl1.addLayout(_hbox_tl1)
    l_fast.addLayout(_vbox_tl1)
    l_fast.addSpacing(config.S(10))

    # 2. Tracks Selection
    win.combo_tr_1 = MultiSelectDropdown([])
    win.combo_tr_1.setFixedHeight(config.S(30))
    l_fast.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_1))
    l_fast.addSpacing(config.S(10))

    # Input style for silence detection
    h_in = config.S(30) - 2
    input_style = f"""
        QLineEdit {{
            background-color: #1e1e1e; color: #d4d4d4; 
            border: 1px solid #3a3a3a; border-radius: {config.S(4)}px; 
            padding: 0px {config.S(8)}px;
            min-height: {h_in}px;
            max-height: {h_in}px;
            height: {h_in}px;
            outline: none;
            font-family: '{config.UI_FONT_NAME}';
            font-size: {config.FS(9.5)}pt;
        }}
        QLineEdit:focus {{ border: 1px solid #1a7a3e; }}
    """

    def _row_rst(lbl_text, line_edit, default_val):
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(config.S(4))
        lbl = QLabel(lbl_text)
        lbl.setFixedHeight(config.S(18))
        lbl.setStyleSheet(f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500; font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;")
        vbox.addWidget(lbl)
        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(config.S(4))
        hbox.addWidget(line_edit, 1)
        rst = ReloadButton(size=30)
        rst.setToolTip(win.txt("tt_reset_to_default"))
        rst.clicked.connect(lambda: line_edit.setText(default_val))
        hbox.addWidget(rst)
        vbox.addLayout(hbox)
        return vbox

    # 3. Silence threshold
    win.input_fs_thresh = QLineEdit()
    win.input_fs_thresh.setText(str(prefs.get('silence_threshold_db', prefs.get('ui_spin_thresh', -42.0))))
    win.input_fs_thresh.setStyleSheet(input_style)
    win.input_fs_thresh.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_silence_threshold_db"), win.input_fs_thresh, "-42.0"))
    l_fast.addSpacing(config.S(10))

    # 4. Padding
    win.input_fs_pad = QLineEdit()
    win.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.1)))
    win.input_fs_pad.setStyleSheet(input_style)
    win.input_fs_pad.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_padding_s"), win.input_fs_pad, "0.1"))
    l_fast.addSpacing(config.S(10))

    # 5. Min silence duration
    win.input_fs_min_dur = QLineEdit()
    win.input_fs_min_dur.setText(str(prefs.get('silence_min_dur', 0.2)))
    win.input_fs_min_dur.setStyleSheet(input_style)
    win.input_fs_min_dur.setFixedHeight(config.S(30))
    win.input_fs_min_dur.setToolTip(
        "Threshold duration: gaps longer than this are considered silence.\n"
        "Lower = more gaps detected. Shared with post-transcript mode."
    )
    l_fast.addLayout(_row_rst(win.txt("lbl_min_silence_dur"), win.input_fs_min_dur, "0.2"))
    l_fast.addSpacing(config.S(16))

    # 6. Mode Toggles
    w_fs_cut = QWidget()
    w_fs_cut.setFixedHeight(config.S(22))
    row_fs_cut = QHBoxLayout(w_fs_cut)
    row_fs_cut.setContentsMargins(0, 0, 0, 0)
    lbl_fs_cut = QLabel(win.txt("lbl_cut_silence_directly"))
    lbl_fs_cut.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; background: transparent;")
    row_fs_cut.addWidget(lbl_fs_cut)
    row_fs_cut.addStretch()
    info_fs_cut = win._create_info_icon("tt_cut_silence_directly")
    row_fs_cut.addWidget(info_fs_cut)
    row_fs_cut.addSpacing(config.S(6))
    win.tgl_fs_cut = ToggleSwitch()
    win.tgl_fs_cut.setChecked(prefs.get('fs_cut_mode', True), animated=False)
    row_fs_cut.addWidget(win.tgl_fs_cut)
    l_fast.addWidget(w_fs_cut)
    l_fast.addSpacing(config.S(8))

    w_fs_mark = QWidget()
    w_fs_mark.setFixedHeight(config.S(22))
    row_fs_mark = QHBoxLayout(w_fs_mark)
    row_fs_mark.setContentsMargins(0, 0, 0, 0)
    lbl_fs_mark = QLabel(win.txt("lbl_mark_silence_with_color"))
    lbl_fs_mark.setStyleSheet(f"color: {config.FG_COLOR}; font-family: '{config.UI_FONT_NAME}'; font-size: {config.FS(9.5)}pt; background: transparent;")
    row_fs_mark.addWidget(lbl_fs_mark)
    row_fs_mark.addStretch()
    info_fs_mark = win._create_info_icon("tt_mark_silence_with_color")
    row_fs_mark.addWidget(info_fs_mark)
    row_fs_mark.addSpacing(config.S(6))
    win.tgl_fs_mark = ToggleSwitch()
    win.tgl_fs_mark.setChecked(prefs.get('fs_mark_mode', False), animated=False)
    row_fs_mark.addWidget(win.tgl_fs_mark)
    l_fast.addWidget(w_fs_mark)
    l_fast.addSpacing(config.S(18))

    win.tgl_fs_cut.toggled.connect(lambda c: win.tgl_fs_mark.setChecked(False) if c else None)
    win.tgl_fs_mark.toggled.connect(lambda c: win.tgl_fs_cut.setChecked(False) if c else None)
    win.tgl_fs_cut.toggled.connect(lambda v: win._save_single_pref('fs_cut_mode', v))
    win.tgl_fs_mark.toggled.connect(lambda v: win._save_single_pref('fs_mark_mode', v))

    # 7. Run Detection button
    btn_row_fs = QHBoxLayout()
    btn_row_fs.setContentsMargins(0, 0, 0, 0)
    btn_row_fs.addStretch()

    win.btn_run_fs = QPushButton(win.txt("btn_run_standalone_silence"))
    win.btn_run_fs.setCursor(Qt.PointingHandCursor)
    win.btn_run_fs.setFixedHeight(config.S(30))
    win.btn_run_fs.setMinimumWidth(config.S(110))
    win.btn_run_fs.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
    win.btn_run_fs.setStyleSheet(f"""
        QPushButton {{
            background-color: {config.BTN_BG}; color: #ffffff;
            font-family: "{config.UI_FONT_NAME}"; font-size: {config.FS(9.5)}pt; font-weight: bold;
            border: none; border-radius: {config.S(4)}px; padding: 0 {config.S(14)}px;
        }}
        QPushButton:hover {{ background-color: {config.BTN_ACTIVE}; }}
        QPushButton:pressed {{ background-color: #176e38; }}
    """)
    win.btn_run_fs.clicked.connect(win._on_fast_silence)
    btn_row_fs.addWidget(win.btn_run_fs)
    btn_row_fs.addStretch()

    l_fast.addLayout(btn_row_fs)
    l_fast.addStretch()

    win.welcome_stack.addWidget(p_silence_outer)

    return page
