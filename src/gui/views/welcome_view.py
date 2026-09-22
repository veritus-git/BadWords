#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2026 Szymon Wolarz
# Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: welcome_view.py
ROLE: GUI View
DESCRIPTION:
Welcome screen with smooth Y-axis vertical centering of both workspaces,
hardware-accelerated sequential fade transition, rock-solid horizontal centering,
and adaptive support for both Standalone (file import / DaVinci switch) and
Embedded DaVinci Resolve modes.
Adheres strictly to the BadWords design system: dark aesthetics, zero emojis,
vector SVG icons, and embedded Ubuntu font consistency across all platforms.
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
from gui.widgets.file_drop_zone import FileDropZone


def is_embedded_in_resolve() -> bool:
    """Returns True if BadWords was launched from inside DaVinci Resolve (Workspace -> Scripts)."""
    import sys
    for mod_name in ('__main__', 'builtins'):
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        obj_res = getattr(mod, 'resolve', None)
        if obj_res is not None:
            type_name = type(obj_res).__name__
            if type_name != 'ResolveHandler' and hasattr(obj_res, 'GetProjectManager'):
                return True
        obj_bmd = getattr(mod, 'bmd', None)
        if obj_bmd is not None and hasattr(obj_bmd, 'scriptapp'):
            return True

    if 'fscript' in sys.executable.lower():
        return True
    return False


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

        painter.fillRect(self.rect(), QColor(config.BG_COLOR))

        p = self.progress
        w = self.width()

        if self.pix_from and p < 0.65:
            alpha_from = max(0.0, min(1.0, (0.65 - p) / 0.65))
            painter.setOpacity(alpha_from)
            dpr_from = self.pix_from.devicePixelRatio() if hasattr(self.pix_from, 'devicePixelRatio') and self.pix_from.devicePixelRatio() > 0 else 1.0
            log_w_from = self.pix_from.width() / dpr_from
            x_from = int(round((w - log_w_from) / 2.0))
            painter.drawPixmap(x_from, 0, self.pix_from)

        if self.pix_to and p > 0.35:
            alpha_to = max(0.0, min(1.0, (p - 0.35) / 0.65))
            painter.setOpacity(alpha_to)
            dpr_to = self.pix_to.devicePixelRatio() if hasattr(self.pix_to, 'devicePixelRatio') and self.pix_to.devicePixelRatio() > 0 else 1.0
            log_w_to = self.pix_to.width() / dpr_to
            x_to = int(round((w - log_w_to) / 2.0))
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

    def animate_indicator(self, idx: int, duration: int = 280):
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

        p.setPen(QPen(QColor("#333333"), 1.0))
        p.drawLine(0, int(h - 1), int(w), int(h - 1))

        cur_left = self._anim_pos * half_w
        active_rect = QRectF(cur_left, 0, half_w, h - 1)

        grad = QLinearGradient(0, h, 0, 0)
        grad.setColorAt(0.0, QColor(26, 122, 62, 75))
        grad.setColorAt(0.45, QColor(26, 122, 62, 20))
        grad.setColorAt(1.0, QColor(26, 122, 62, 0))
        p.fillRect(active_rect, grad)

        p.setPen(QPen(QColor("#1a7a3e"), 2.0))
        p.drawLine(int(active_rect.left()), int(h - 1), int(active_rect.right()), int(h - 1))


class _StatusDotWidget(QWidget):
    """Paints a soft anti-aliased status circle (green for connected, red for disconnected)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self.setFixedSize(config.S(8), config.S(8))

    def set_connected(self, conn: bool):
        self._connected = conn
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QColor("#38c172") if self._connected else QColor("#e05555")
        p.setBrush(c)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, config.S(8), config.S(8))
        p.end()


class SourceHeaderWidget(QWidget):
    """
    Header label above the Source dropdown:
    - Left: 'Source' / 'Źródło'
    - Right: Soft status dot + 'Connected: ProjectName' (or 'Disconnected')
      Only shown when DaVinci Resolve is selected.
    """
    def __init__(self, win, parent=None):
        super().__init__(parent)
        self.win = win
        self.setFixedHeight(config.S(18))
        self.setStyleSheet("background: transparent;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(config.S(4))

        self.lbl_title = QLabel(win.txt("src_source") if hasattr(win, 'txt') else "Źródło")
        self.lbl_title.setFixedHeight(config.S(18))
        self.lbl_title.setStyleSheet(
            f"color: #9e9e9e; font-size: {config.FS(9.5)}pt; font-weight: 500;"
            f" font-family: '{config.UI_FONT_NAME}'; background: transparent; padding: 0;"
        )
        lay.addWidget(self.lbl_title)
        lay.addStretch()

        self.status_container = QWidget()
        self.status_container.setFixedHeight(config.S(18))
        self.status_container.setStyleSheet("background: transparent;")
        stat_lay = QHBoxLayout(self.status_container)
        stat_lay.setContentsMargins(0, 0, 0, 0)
        stat_lay.setSpacing(config.S(4))

        self.dot = _StatusDotWidget()
        stat_lay.addWidget(self.dot)

        self.lbl_status = QLabel()
        self.lbl_status.setStyleSheet(
            f"font-size: {config.FS(8.0)}pt; font-family: '{config.UI_FONT_NAME}';"
            f" background: transparent; padding: 0;"
        )
        stat_lay.addWidget(self.lbl_status)

        self.info_icon = self.win._create_info_icon("") if hasattr(self.win, '_create_info_icon') else QLabel()
        stat_lay.addWidget(self.info_icon)
        lay.addWidget(self.status_container)

        if getattr(win, 'current_source_type', 'file') == "resolve":
            self.status_container.show()
        else:
            self.status_container.hide()
        self.update_status()

    def set_source_mode(self, mode: str):
        self.update_status()
        if mode == "resolve":
            self.status_container.show()
        else:
            self.status_container.hide()

    def update_status(self):
        rh = getattr(self.win.engine, 'resolve_handler', None)
        is_conn = rh.is_connected() if rh else False
        project_name = rh.get_current_project_name() if rh else ""
        is_bridge = rh.is_bridge_connected() if rh else False

        self.dot.set_connected(is_conn)
        if is_conn:
            disp_project = project_name or "Aktywny"
            if is_bridge:
                txt_tpl = self.win.txt("status_resolve_bridge_connected") if hasattr(self.win, 'txt') else "Połączono (Bridge): {project}"
            else:
                txt_tpl = self.win.txt("status_resolve_connected") if hasattr(self.win, 'txt') else "Połączono: {project}"
            self.lbl_status.setText(txt_tpl.replace("{project}", disp_project))
            self.lbl_status.setStyleSheet(
                f"color: #70c080; font-size: {config.FS(8.0)}pt; font-family: '{config.UI_FONT_NAME}';"
                f" background: transparent; padding: 0;"
            )
            if hasattr(self, 'info_icon') and self.info_icon:
                self.info_icon.hide()
            self.setToolTip(f"Połączono z projektem DaVinci Resolve: {disp_project}")
        else:
            self.lbl_status.setText(self.win.txt("status_resolve_not_connected") if hasattr(self.win, 'txt') else "Brak połączenia")
            self.lbl_status.setStyleSheet(
                f"color: #e05555; font-size: {config.FS(8.0)}pt; font-family: '{config.UI_FONT_NAME}';"
                f" background: transparent; padding: 0;"
            )
            is_installed = False
            is_studio = False
            if rh:
                ed_info = rh.get_resolve_edition_info() if hasattr(rh, 'get_resolve_edition_info') else {}
                is_installed = bool(ed_info.get("installed", False))
                if is_installed:
                    if ed_info.get("edition") == "Studio":
                        is_studio = True
                    elif ed_info.get("edition") != "Free":
                        if hasattr(rh, 'os_doc') and rh.os_doc:
                            util_dirs = rh.os_doc.get_resolve_script_utility_dirs()
                            has_py = any(os.path.isfile(os.path.join(d, "BadWords.py")) for d in util_dirs if os.path.isdir(d))
                            has_lua = any(os.path.isfile(os.path.join(d, "BadWords Bridge.lua")) for d in util_dirs if os.path.isdir(d))
                            if has_py and not has_lua:
                                is_studio = True

            if not is_installed:
                tip = self.win.txt("tt_resolve_not_installed") if hasattr(self.win, 'txt') else "Nie znaleziono programu DaVinci Resolve. Dla pełni funkcji BadWords zalecane jest pobranie DaVinci Resolve."
            elif is_studio:
                tip = self.win.txt("tt_resolve_connection_studio") if hasattr(self.win, 'txt') else "Ensure Preferences > System > General > 'External scripting using' is set to 'Local'."
            else:
                tip = self.win.txt("tt_resolve_connection_free") if hasattr(self.win, 'txt') else "Open DaVinci Resolve and run Workspace → Scripts → BadWords Bridge."

            if hasattr(self, 'info_icon') and self.info_icon:
                self.info_icon.show()
                formatted_tip = tip.replace('\n', '<br>')
                self.info_icon.custom_tooltip_text = f"<div style='max-width: {config.S(360)}px; line-height: 135%;'>{formatted_tip}</div>"
            self.setToolTip("")

        # Update stop bridge buttons visibility
        is_resolve_mode = (getattr(self.win, 'current_source_type', 'file') == 'resolve')
        for stop_btn in (getattr(self.win, 'btn_stop_bridge_0', None), getattr(self.win, 'btn_stop_bridge_1', None)):
            if stop_btn:
                stop_btn.setVisible(is_resolve_mode and is_bridge)


class DavinciSourceBox(QWidget):
    """
    Groups DaVinci Resolve timeline selector and track selector.
    """
    def __init__(self, vbox_tl: QVBoxLayout, vbox_tr: QVBoxLayout, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addLayout(vbox_tl)
        lay.addSpacing(config.S(8))
        lay.addLayout(vbox_tr)
        self.setFixedHeight(config.S(112))


class SourceAreaWidget(QWidget):
    """
    Container for source inputs (File Drop Zone vs DaVinci Resolve controls).
    Cleanly switches between File state (90px) and DaVinci state (112px) with zero jitter.
    """
    def __init__(self, drop_zone: QWidget, davinci_box: QWidget, initial_mode: str = "file", parent=None):
        super().__init__(parent)
        self.drop_zone = drop_zone
        self.davinci_box = davinci_box

        self.H_FILE = config.S(90)
        self.H_RESOLVE = config.S(112)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.drop_zone)
        lay.addWidget(self.davinci_box)

        self.set_mode(initial_mode)

    def set_mode(self, mode: str):
        if mode == "file":
            self.davinci_box.hide()
            self.drop_zone.show()
            self.setFixedHeight(self.H_FILE)
        else:
            self.drop_zone.hide()
            self.davinci_box.show()
            self.setFixedHeight(self.H_RESOLVE)



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

        self.H_HEADER = config.S(110)
        self.H_MAX_CONTENT = config.S(540)

        self.welcome_root = QWidget(self)
        self.welcome_root.setObjectName("welcome_root")
        self.welcome_root.setStyleSheet("QWidget#welcome_root { background: transparent; }")

        self.root_layout = QVBoxLayout(self.welcome_root)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        self.root_layout.setAlignment(Qt.AlignTop)

        # ── 1. Branding Logo (BadWords) ───────────────────────────────────────
        win.welcome_title = WelcomeBrandingWidget(self.welcome_root)
        h_title = QHBoxLayout()
        h_title.setContentsMargins(0, 0, 0, 0)
        h_title.setSpacing(0)
        h_title.addStretch()
        h_title.addWidget(win.welcome_title)
        h_title.addStretch()
        self.root_layout.addLayout(h_title)
        self.root_layout.addSpacing(config.S(24))

        # ── 2. Mode Switcher (Transcript | Silence Detection) ─────────────────
        win.welcome_mode_switch = AnimatedUnderlineGlowModeSwitch(
            win.txt("titlebar_transcript"),
            win.txt("msg_standalone_silence"),
            self.welcome_root
        )
        win.welcome_mode_switch.setFixedWidth(config.S(325))
        h_mode = QHBoxLayout()
        h_mode.setContentsMargins(0, 0, 0, 0)
        h_mode.setSpacing(0)
        h_mode.addStretch()
        h_mode.addWidget(win.welcome_mode_switch)
        h_mode.addStretch()
        self.root_layout.addLayout(h_mode)
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

        orig_set_current_index = win.welcome_stack.setCurrentIndex
        def _on_stack_set_index(idx: int):
            orig_set_current_index(idx)
            if self._current_idx != idx and not self._is_animating:
                self.switch_workspace_instant(idx)
        win.welcome_stack.setCurrentIndex = _on_stack_set_index

    def preload(self, target_w: int = 0, target_h: int = 0):
        if target_w <= 0 or target_h <= 0:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                avail = screen.availableGeometry()
                sb_w = getattr(config, 'SIDEBAR_WIDTH', config.S(50))
                target_w = max(config.S(600), avail.width() - 2 * sb_w)
                target_h = max(config.S(400), avail.height() - config.S(36))
            else:
                target_w = config.S(1280)
                target_h = config.S(800)
        self.resize(target_w, target_h)
        self.resizeEvent(None)
        self.ensurePolished()
        self.welcome_root.ensurePolished()
        for child in self.welcome_root.findChildren(QWidget):
            child.ensurePolished()

    def get_visual_height(self, idx: int, source_type: str = None) -> int:
        is_standalone = getattr(self.win, 'is_standalone', True)
        if source_type is None:
            source_type = getattr(self.win, 'current_source_type', 'file')

        if not is_standalone:
            content_h = config.S(322) if idx == 0 else config.S(404)
        else:
            if idx == 0:
                content_h = config.S(366) if source_type == 'file' else config.S(388)
            else:
                content_h = config.S(408) if source_type == 'file' else config.S(458)

        return self.H_HEADER + content_h

    def _target_y(self, idx: int, source_type: str = None) -> int:
        vis_h = self.get_visual_height(idx, source_type)
        avail_h = self.height()
        if avail_h <= 0:
            avail_h = config.S(800)
        return max(config.S(16), (avail_h - vis_h) // 2)

    def animate_y_step(self):
        if not self._is_animating:
            cur_y = self._target_y(self._current_idx)
            self.welcome_root.move(0, cur_y)

    def animate_y_to_content(self, duration: int = 240):
        if self._y_anim and self._y_anim.state() == QVariantAnimation.Running:
            self._y_anim.stop()
        start_y = self.welcome_root.y()
        end_y = self._target_y(self._current_idx)
        if start_y == end_y or duration <= 0:
            self.welcome_root.move(0, end_y)
            return

        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(start_y)
        anim.setEndValue(end_y)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.valueChanged.connect(lambda y: self.welcome_root.move(0, int(y)))
        self._y_anim = anim
        anim.start()

    def resizeEvent(self, event):
        if event is not None:
            super().resizeEvent(event)
        w = self.width()
        if w <= 0:
            return
        root_h = self.H_HEADER + self.H_MAX_CONTENT
        self.welcome_root.setFixedWidth(w)
        self.welcome_root.setFixedHeight(root_h)
        self.workspace_container.setFixedWidth(w)
        if hasattr(self.win, 'welcome_stack') and self.win.welcome_stack:
            self.win.welcome_stack.setFixedSize(w, self.H_MAX_CONTENT)
            for i in range(self.win.welcome_stack.count()):
                widget = self.win.welcome_stack.widget(i)
                if widget:
                    widget.resize(w, self.H_MAX_CONTENT)
                    if widget.layout():
                        widget.layout().activate()
        self.fade_canvas.setGeometry(0, 0, w, self.H_MAX_CONTENT)
        if not self._is_animating:
            cur_y = self._target_y(self._current_idx)
            self.welcome_root.move(0, cur_y)
        self.root_layout.activate()

    def switch_workspace_animated(self, target_idx: int):
        if self._current_idx == target_idx and not self._is_animating:
            return

        if self._y_anim and self._y_anim.state() == QVariantAnimation.Running:
            self._y_anim.stop()
            self.fade_canvas.finish()

        duration = 350
        self.win.welcome_mode_switch.animate_indicator(target_idx, duration=280)

        current_w = self.win.welcome_stack.widget(self._current_idx)
        target_w = self.win.welcome_stack.widget(target_idx)

        if current_w is None or target_w is None:
            self.switch_workspace_instant(target_idx)
            return

        w = self.width()
        self.welcome_root.setFixedWidth(w)
        self.workspace_container.setFixedWidth(w)
        self.win.welcome_stack.setFixedSize(w, self.H_MAX_CONTENT)
        self.fade_canvas.setGeometry(0, 0, w, self.H_MAX_CONTENT)

        pix_from = current_w.grab()

        target_w.resize(w, self.H_MAX_CONTENT)
        if target_w.layout():
            target_w.layout().activate()
        pix_to = target_w.grab()

        self.fade_canvas.set_transition(pix_from, pix_to)
        current_w.hide()

        start_y = self.welcome_root.y()
        end_y = self._target_y(target_idx)

        self._is_animating = True
        anim = QVariantAnimation(self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)

        def _step(v: float):
            cur_y = int(start_y + (end_y - start_y) * v)
            self.welcome_root.move(0, cur_y)
            self.fade_canvas.set_progress(v)

        def _done():
            self.welcome_root.move(0, end_y)
            self._current_idx = target_idx
            self.win.welcome_stack.setCurrentIndex(target_idx)
            self.fade_canvas.finish()
            cur_w = self.width()
            self.win.welcome_stack.setFixedSize(cur_w, self.H_MAX_CONTENT)
            target_w.resize(cur_w, self.H_MAX_CONTENT)
            if target_w.layout():
                target_w.layout().activate()
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
        w = self.width()
        self.welcome_root.setFixedWidth(w)
        self.workspace_container.setFixedWidth(w)
        if hasattr(self.win, 'welcome_stack') and self.win.welcome_stack:
            self.win.welcome_stack.setFixedSize(w, self.H_MAX_CONTENT)
            target_w = self.win.welcome_stack.widget(target_idx)
            if target_w:
                target_w.resize(w, self.H_MAX_CONTENT)
                if target_w.layout():
                    target_w.layout().activate()
                target_w.show()
                target_w.raise_()
        self.win.welcome_mode_switch.set_index(target_idx, trigger_callback=False)
        self.win.welcome_mode_switch.animate_indicator(target_idx, duration=0)
        y = self._target_y(target_idx)
        self.welcome_root.move(0, y)
        self._is_animating = False


def build_welcome_view(win) -> QWidget:
    """Build Page 0 of the main stack: Welcome / Configuration screen."""
    prefs = win.engine.load_preferences() or {}
    is_more_accurate = prefs.get('ai_more_accurate', config.DEFAULT_SETTINGS.get('ai_more_accurate', False))

    is_standalone = not is_embedded_in_resolve()
    win.is_standalone = is_standalone
    rh = getattr(win.engine, 'resolve_handler', None)
    if is_standalone and rh and rh.is_connected():
        win.current_source_type = "resolve"
    else:
        win.current_source_type = "file" if is_standalone else "resolve"

    # Non-blocking auto-reconnect worker for standalone mode when Resolve is selected
    if is_standalone and not hasattr(win, '_resolve_auto_reconnect_timer'):
        from PySide6.QtCore import QTimer, QThread, Signal

        class _ResolveReconnectWorker(QThread):
            connected = Signal()

            def __init__(self, engine, parent=None):
                super().__init__(parent)
                self.engine = engine

            def run(self):
                handler = getattr(self.engine, 'resolve_handler', None)
                if handler and not handler.is_connected():
                    handler.refresh_context(silent=True)
                    if handler.is_connected():
                        self.connected.emit()

        win._reconnect_worker = None

        def _on_reconnect_detected():
            opt_dr = win.txt("src_davinci_resolve") if hasattr(win, 'txt') else "DaVinci Resolve"
            win.current_source_type = "resolve"
            if hasattr(win, 'combo_source_0'):
                win.combo_source_0.blockSignals(True)
                win.combo_source_0.setText(opt_dr)
                win.combo_source_0.blockSignals(False)
            if hasattr(win, 'combo_source_1'):
                win.combo_source_1.blockSignals(True)
                win.combo_source_1.setText(opt_dr)
                win.combo_source_1.blockSignals(False)

            if hasattr(win, 'source_area_0'):
                win.source_area_0.set_mode("resolve")
            if hasattr(win, 'source_area_1'):
                win.source_area_1.set_mode("resolve")

            if hasattr(win, 'header_source_0') and win.header_source_0:
                win.header_source_0.set_source_mode("resolve")
            if hasattr(win, 'header_source_1') and win.header_source_1:
                win.header_source_1.set_source_mode("resolve")

            if hasattr(win, 'btn_ref_source_0'):
                win.btn_ref_source_0.setVisible(True)
            if hasattr(win, 'btn_ref_source_1'):
                win.btn_ref_source_1.setVisible(True)

            if hasattr(win, 'w_fs_resolve_group'):
                win.w_fs_resolve_group.show()
            if hasattr(win, 'w_fs_hidden_info'):
                win.w_fs_hidden_info.hide()

            win._populate_timeline_track_combos()

        def _check_auto_reconnect():
            if getattr(win, 'current_source_type', 'file') == 'resolve':
                handler = getattr(win.engine, 'resolve_handler', None)
                if handler and not handler.is_connected():
                    if win._reconnect_worker is None or not win._reconnect_worker.isRunning():
                        win._reconnect_worker = _ResolveReconnectWorker(win.engine, win)
                        win._reconnect_worker.connected.connect(_on_reconnect_detected)
                        win._reconnect_worker.start()

        win._resolve_auto_reconnect_timer = QTimer(win)
        win._resolve_auto_reconnect_timer.timeout.connect(_check_auto_reconnect)
        win._resolve_auto_reconnect_timer.start(2500)

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

    # ── 1. Source Selection & Controls ────────────────────────────────────────
    # Shared Timeline / Track dropdowns for Resolve branch
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

    win.combo_tr_0 = MultiSelectDropdown([])
    win.combo_tr_0.setFixedHeight(config.S(30))

    if is_standalone:
        opt_file = win.txt("src_local_file") if hasattr(win, 'txt') else "Plik lokalny"
        opt_dr = win.txt("src_davinci_resolve") if hasattr(win, 'txt') else "DaVinci Resolve"
        win.combo_source_0 = CustomDropdown([opt_file, opt_dr])
        win.combo_source_0.setText(opt_file if win.current_source_type == "file" else opt_dr)
        win.combo_source_0.setFixedHeight(config.S(30))

        win.header_source_0 = SourceHeaderWidget(win)
        win.settings_layout.addWidget(win.header_source_0)
        win.settings_layout.addSpacing(config.S(4))

        _hbox_source_0 = QHBoxLayout()
        _hbox_source_0.setContentsMargins(0, 0, 0, 0)
        _hbox_source_0.setSpacing(config.S(4))
        _hbox_source_0.addWidget(win.combo_source_0, 1)

        def _on_stop_bridge():
            win.engine.resolve_handler.stop_bridge()
            if hasattr(win, 'header_source_0'):
                win.header_source_0.update_status()
            if hasattr(win, 'header_source_1'):
                win.header_source_1.update_status()
            if hasattr(win, '_populate_timeline_track_combos'):
                win._populate_timeline_track_combos()

        win.btn_stop_bridge_0 = QPushButton(win.txt("btn_stop_bridge") if hasattr(win, 'txt') else "Stop Bridge")
        win.btn_stop_bridge_0.setFixedHeight(config.S(30))
        win.btn_stop_bridge_0.setMinimumWidth(config.S(85))
        win.btn_stop_bridge_0.setMaximumWidth(config.S(125))
        win.btn_stop_bridge_0.setCursor(Qt.PointingHandCursor)
        win.btn_stop_bridge_0.setToolTip(win.txt("tt_stop_bridge") if hasattr(win, 'txt') else "Zatrzymaj działanie skryptu BadWords Bridge w DaVinci Resolve")
        win.btn_stop_bridge_0.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #d4d4d4; font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(8.5)}pt; border: 1px solid #3c3c3c; border-radius: {config.S(4)}px;
                padding: 0 {config.S(6)}px;
            }}
            QPushButton:hover {{ background-color: #383838; color: #ffffff; border-color: #505050; }}
            QPushButton:pressed {{ background-color: #702525; color: #ffffff; border-color: #903030; }}
        """)
        win.btn_stop_bridge_0.clicked.connect(_on_stop_bridge)
        _hbox_source_0.addWidget(win.btn_stop_bridge_0)
        win.btn_stop_bridge_0.setVisible(win.current_source_type == "resolve" and (rh.is_bridge_connected() if rh else False))

        win.btn_ref_source_0 = ReloadButton(size=30)
        win.btn_ref_source_0.setToolTip(win.txt("btn_reconnect_resolve") if hasattr(win, 'txt') else "Połącz ponownie")
        win.btn_ref_source_0.clicked.connect(lambda: (win._refresh_davinci_connection(), win._populate_timeline_track_combos()))
        _hbox_source_0.addWidget(win.btn_ref_source_0)
        win.btn_ref_source_0.setVisible(win.current_source_type == "resolve")

        win.settings_layout.addLayout(_hbox_source_0)
        win.settings_layout.addSpacing(config.S(4))

        win.drop_zone_0 = FileDropZone()
        win.davinci_box_0 = DavinciSourceBox(
            _vbox_tl0,
            _row(win.txt("lbl_tracks_selection"), win.combo_tr_0)
        )
        win.source_area_0 = SourceAreaWidget(win.drop_zone_0, win.davinci_box_0, initial_mode=win.current_source_type)
        win.source_area_0.set_mode(win.current_source_type)
        win.settings_layout.addWidget(win.source_area_0)
        win.settings_layout.addSpacing(config.S(10))

    else:
        # Embedded DaVinci Resolve mode: exact original layout
        win.settings_layout.addLayout(_vbox_tl0)
        win.settings_layout.addSpacing(config.S(10))
        win.settings_layout.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_0))
        win.settings_layout.addSpacing(config.S(10))

    # ── 2. Language Selection ─────────────────────────────────────────────────
    lang_items = list(config.SUPPORTED_LANGUAGES.values())
    win._combo_lang = SearchableDropdown(lang_items)
    win._combo_lang.setFixedHeight(config.S(30))
    saved_lang = prefs.get('lang', '')
    display_name = config.SUPPORTED_LANGUAGES.get(saved_lang, saved_lang)
    placeholder = win.txt("lbl_choose_recording_language") if hasattr(win, 'txt') else "Wybierz język nagrania"
    win._combo_lang.setText(display_name if display_name in lang_items else placeholder)
    win._combo_lang.valueChanged.connect(lambda v: win.engine.save_preferences({"lang": v}))
    win.settings_layout.addLayout(_row(win.txt("lbl_lang"), win._combo_lang))
    win.settings_layout.addSpacing(config.S(10))

    # ── 3. Model Selection ────────────────────────────────────────────────────
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
    win.settings_layout.addSpacing(config.S(14))

    # ── 4. More Accurate Mode Toggle ──────────────────────────────────────────
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

    win.w_row_acc = w_row_acc
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

    # ── Action Buttons ────────────────────────────────────────────────────────
    l_trans.addSpacing(config.S(18))

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

    # ── 1. Source Selection & Controls (Fast Silence) ─────────────────────────
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

    win.combo_tr_1 = MultiSelectDropdown([])
    win.combo_tr_1.setFixedHeight(config.S(30))

    if is_standalone:
        opt_file = win.txt("src_local_file") if hasattr(win, 'txt') else "Plik lokalny"
        opt_dr = win.txt("src_davinci_resolve") if hasattr(win, 'txt') else "DaVinci Resolve"
        win.combo_source_1 = CustomDropdown([opt_file, opt_dr])
        win.combo_source_1.setText(opt_file if win.current_source_type == "file" else opt_dr)
        win.combo_source_1.setFixedHeight(config.S(30))

        win.header_source_1 = SourceHeaderWidget(win)
        l_fast.addWidget(win.header_source_1)
        l_fast.addSpacing(config.S(4))

        _hbox_source_1 = QHBoxLayout()
        _hbox_source_1.setContentsMargins(0, 0, 0, 0)
        _hbox_source_1.setSpacing(config.S(4))
        _hbox_source_1.addWidget(win.combo_source_1, 1)

        win.btn_stop_bridge_1 = QPushButton(win.txt("btn_stop_bridge") if hasattr(win, 'txt') else "Stop Bridge")
        win.btn_stop_bridge_1.setFixedHeight(config.S(30))
        win.btn_stop_bridge_1.setMinimumWidth(config.S(85))
        win.btn_stop_bridge_1.setMaximumWidth(config.S(125))
        win.btn_stop_bridge_1.setCursor(Qt.PointingHandCursor)
        win.btn_stop_bridge_1.setToolTip(win.txt("tt_stop_bridge") if hasattr(win, 'txt') else "Zatrzymaj działanie skryptu BadWords Bridge w DaVinci Resolve")
        win.btn_stop_bridge_1.setStyleSheet(f"""
            QPushButton {{
                background-color: #242424; color: #d4d4d4; font-family: "{config.UI_FONT_NAME}";
                font-size: {config.FS(8.5)}pt; border: 1px solid #3c3c3c; border-radius: {config.S(4)}px;
                padding: 0 {config.S(6)}px;
            }}
            QPushButton:hover {{ background-color: #383838; color: #ffffff; border-color: #505050; }}
            QPushButton:pressed {{ background-color: #702525; color: #ffffff; border-color: #903030; }}
        """)
        win.btn_stop_bridge_1.clicked.connect(_on_stop_bridge)
        _hbox_source_1.addWidget(win.btn_stop_bridge_1)
        win.btn_stop_bridge_1.setVisible(win.current_source_type == "resolve" and (rh.is_bridge_connected() if rh else False))

        win.btn_ref_source_1 = ReloadButton(size=30)
        win.btn_ref_source_1.setToolTip(win.txt("btn_reconnect_resolve") if hasattr(win, 'txt') else "Połącz ponownie")
        win.btn_ref_source_1.clicked.connect(lambda: (win._refresh_davinci_connection(), win._populate_timeline_track_combos()))
        _hbox_source_1.addWidget(win.btn_ref_source_1)
        win.btn_ref_source_1.setVisible(win.current_source_type == "resolve")

        l_fast.addLayout(_hbox_source_1)
        l_fast.addSpacing(config.S(4))

        win.drop_zone_1 = FileDropZone()
        win.davinci_box_1 = DavinciSourceBox(
            _vbox_tl1,
            _row(win.txt("lbl_tracks_selection"), win.combo_tr_1)
        )
        win.source_area_1 = SourceAreaWidget(win.drop_zone_1, win.davinci_box_1, initial_mode=win.current_source_type)
        win.source_area_1.set_mode(win.current_source_type)
        l_fast.addWidget(win.source_area_1)
        l_fast.addSpacing(config.S(10))

    else:
        # Embedded DaVinci Resolve mode: exact original layout
        l_fast.addLayout(_vbox_tl1)
        l_fast.addSpacing(config.S(10))
        l_fast.addLayout(_row(win.txt("lbl_tracks_selection"), win.combo_tr_1))
        l_fast.addSpacing(config.S(10))

    # ── 2. Silence Threshold Inputs ───────────────────────────────────────────
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

    win.input_fs_thresh = QLineEdit()
    win.input_fs_thresh.setText(str(prefs.get('silence_threshold_db', prefs.get('ui_spin_thresh', -42.0))))
    win.input_fs_thresh.setStyleSheet(input_style)
    win.input_fs_thresh.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_silence_threshold_db"), win.input_fs_thresh, "-42.0"))
    l_fast.addSpacing(config.S(10))

    win.input_fs_pad = QLineEdit()
    win.input_fs_pad.setText(str(prefs.get('ui_spin_pad', 0.1)))
    win.input_fs_pad.setStyleSheet(input_style)
    win.input_fs_pad.setFixedHeight(config.S(30))
    l_fast.addLayout(_row_rst(win.txt("lbl_padding_s"), win.input_fs_pad, "0.1"))
    l_fast.addSpacing(config.S(10))

    win.input_fs_min_dur = QLineEdit()
    win.input_fs_min_dur.setText(str(prefs.get('silence_min_dur', 0.2)))
    win.input_fs_min_dur.setStyleSheet(input_style)
    win.input_fs_min_dur.setFixedHeight(config.S(30))
    win.input_fs_min_dur.setToolTip(
        "Threshold duration: gaps longer than this are considered silence.\n"
        "Lower = more gaps detected. Shared with post-transcript mode."
    )
    l_fast.addLayout(_row_rst(win.txt("lbl_min_silence_dur"), win.input_fs_min_dur, "0.2"))
    l_fast.addSpacing(config.S(6))

    # ── 3. Mode Toggles & Standalone Info ─────────────────────────────────────
    win.w_fs_cut = QWidget()
    win.w_fs_cut.setFixedHeight(config.S(22))
    row_fs_cut = QHBoxLayout(win.w_fs_cut)
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

    win.w_fs_mark = QWidget()
    win.w_fs_mark.setFixedHeight(config.S(22))
    row_fs_mark = QHBoxLayout(win.w_fs_mark)
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

    win.w_fs_resolve_group = QWidget()
    win.w_fs_resolve_group.setStyleSheet("background: transparent;")
    lay_fs_resolve = QVBoxLayout(win.w_fs_resolve_group)
    lay_fs_resolve.setContentsMargins(0, 0, 0, 0)
    lay_fs_resolve.setSpacing(config.S(8))
    lay_fs_resolve.addWidget(win.w_fs_cut)
    lay_fs_resolve.addWidget(win.w_fs_mark)
    l_fast.addWidget(win.w_fs_resolve_group)

    # Info row when in Local File mode (toggles are hidden)
    win.w_fs_hidden_info = QWidget()
    win.w_fs_hidden_info.setFixedHeight(config.S(24))
    row_fs_hidden = QHBoxLayout(win.w_fs_hidden_info)
    row_fs_hidden.setContentsMargins(0, 0, 0, 0)
    row_fs_hidden.setSpacing(config.S(6))
    lbl_why_hidden = QLabel(win.txt("lbl_why_options_hidden") if hasattr(win, 'txt') else "Dlaczego niektóre opcje są ukryte?")
    lbl_why_hidden.setStyleSheet(
        f"color: #9e9e9e; font-family: '{config.UI_FONT_NAME}'; "
        f"font-size: {config.FS(9.0)}pt; font-style: italic; background: transparent; padding: 0;"
    )
    row_fs_hidden.addWidget(lbl_why_hidden)
    info_why = win._create_info_icon("tt_why_silence_options_hidden")
    row_fs_hidden.addWidget(info_why)
    row_fs_hidden.addStretch()
    l_fast.addWidget(win.w_fs_hidden_info)

    if is_standalone and win.current_source_type == "file":
        win.w_fs_resolve_group.hide()
        win.w_fs_hidden_info.show()
    else:
        win.w_fs_resolve_group.show()
        win.w_fs_hidden_info.hide()

    l_fast.addSpacing(config.S(16))

    win.tgl_fs_cut.toggled.connect(lambda c: win.tgl_fs_mark.setChecked(False) if c else None)
    win.tgl_fs_mark.toggled.connect(lambda c: win.tgl_fs_cut.setChecked(False) if c else None)
    win.tgl_fs_cut.toggled.connect(lambda v: win._save_single_pref('fs_cut_mode', v))
    win.tgl_fs_mark.toggled.connect(lambda v: win._save_single_pref('fs_mark_mode', v))

    # ── 4. Run Detection Button ───────────────────────────────────────────────
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

    # ── 5. Standalone Synchronization ─────────────────────────────────────────
    if is_standalone:
        p_txt = win.txt("lbl_drop_file_prompt") if hasattr(win, 'txt') else "Przeciągnij plik wideo lub audio tutaj"
        sub_txt = win.txt("lbl_drop_file_subprompt") if hasattr(win, 'txt') else "lub kliknij, aby wybrać z dysku"
        win.drop_zone_0.set_texts(p_txt, sub_txt)
        win.drop_zone_1.set_texts(p_txt, sub_txt)

        def _sync_source(idx: int):
            mode = "file" if idx == 0 else "resolve"
            win.current_source_type = mode

            win.combo_source_0.blockSignals(True)
            win.combo_source_1.blockSignals(True)
            win.combo_source_0.setText(opt_file if idx == 0 else opt_dr)
            win.combo_source_1.setText(opt_file if idx == 0 else opt_dr)
            win.combo_source_0.blockSignals(False)
            win.combo_source_1.blockSignals(False)

            if hasattr(win, 'header_source_0'):
                win.header_source_0.set_source_mode(mode)
            if hasattr(win, 'header_source_1'):
                win.header_source_1.set_source_mode(mode)

            if hasattr(win, 'btn_ref_source_0'):
                win.btn_ref_source_0.setVisible(mode == "resolve")
            if hasattr(win, 'btn_ref_source_1'):
                win.btn_ref_source_1.setVisible(mode == "resolve")

            rh = getattr(win.engine, 'resolve_handler', None) if hasattr(win, 'engine') else None
            is_bridge = rh.is_bridge_connected() if rh else False
            if hasattr(win, 'btn_stop_bridge_0'):
                win.btn_stop_bridge_0.setVisible(mode == "resolve" and is_bridge)
            if hasattr(win, 'btn_stop_bridge_1'):
                win.btn_stop_bridge_1.setVisible(mode == "resolve" and is_bridge)

            if hasattr(win, 'source_area_0'):
                win.source_area_0.set_mode(mode)
            if hasattr(win, 'source_area_1'):
                win.source_area_1.set_mode(mode)

            if mode == "file":
                if hasattr(win, 'w_fs_resolve_group'):
                    win.w_fs_resolve_group.hide()
                win.w_fs_hidden_info.show()
            else:
                if hasattr(win, 'w_fs_resolve_group'):
                    win.w_fs_resolve_group.show()
                win.w_fs_hidden_info.hide()

            page.animate_y_to_content(200)
            if hasattr(win, '_sync_script_edit_height'):
                win._sync_script_edit_height()

        win.combo_source_0.valueChanged.connect(lambda val: _sync_source(0 if val == opt_file else 1))
        win.combo_source_1.valueChanged.connect(lambda val: _sync_source(0 if val == opt_file else 1))

        def _sync_file_0(fp: str):
            if hasattr(win, 'drop_zone_1') and win.drop_zone_1.get_file() != fp:
                if fp:
                    win.drop_zone_1.set_file(fp)
                else:
                    win.drop_zone_1.clear_file()

        def _sync_file_1(fp: str):
            if hasattr(win, 'drop_zone_0') and win.drop_zone_0.get_file() != fp:
                if fp:
                    win.drop_zone_0.set_file(fp)
                else:
                    win.drop_zone_0.clear_file()

        win.drop_zone_0.file_selected.connect(_sync_file_0)
        win.drop_zone_1.file_selected.connect(_sync_file_1)

    if hasattr(win, '_sync_script_edit_height'):
        QTimer.singleShot(0, win._sync_script_edit_height)

    return page
