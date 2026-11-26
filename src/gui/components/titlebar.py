#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: titlebar.py
ROLE: GUI Component
DESCRIPTION:
Custom window titlebar with window control buttons, menu dropdowns,
centered source label with overlap protection, and cross-OS window actions.
"""

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QListWidget
)
from PySide6.QtCore import Qt, QSize, QVariantAnimation, QEasingCurve, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QGuiApplication
import config
from ..widgets.buttons import TitleDropdown
from ..utils import _app_icon, _titlebar_icon


class AnimatedTitleButton(QPushButton):
    """
    Title-bar control button with a 150ms QVariantAnimation colour transition on hover.
    # INVARIANT: Never change the close button hover color to red; keep neutral
    # COLOR_TITLEBAR_HOVER across minimize, maximize, and close buttons.
    """

    def __init__(self, icon_path: str, tooltip_key: str, lang: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBarBtn")
        self._bg = config.COLOR_TITLEBAR_BG
        self._hover = config.COLOR_TITLEBAR_HOVER
        self._press = "#3a3a3d"
        self._cur = self._bg
        self._native_hovered = False
        self._native_pressed = False

        s_sz = config.S(32)
        self.setFixedSize(s_sz, s_sz)
        from ..utils import _txt
        self.setToolTip(_txt(lang, tooltip_key))
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAutoFillBackground(False)
        self.setFlat(True)

        pix = QPixmap(icon_path)
        if not pix.isNull():
            self.setIcon(QIcon(pix))
            self.setIconSize(QSize(config.S(12), config.S(12)))

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.OutQuad)
        self._anim.valueChanged.connect(self._on_color_changed)
        self._icon_path = icon_path

        self.setStyleSheet(f"""
            QPushButton#TitleBarBtn {{
                border: none; border-radius: 0px;
                min-width: {s_sz}px; max-width: {s_sz}px; min-height: {s_sz}px; max-height: {s_sz}px;
                margin: 0px; padding: 0px;
                background: transparent;
            }}
        """)

    def change_base_icon(self, new_icon_path: str):
        self._icon_path = new_icon_path
        self.setIcon(QIcon(new_icon_path))
        self.update()

    def set_native_hover(self, hovered: bool):
        hovered = bool(hovered)
        if hovered == self._native_hovered:
            return
        self._native_hovered = hovered
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._hover if hovered else self._bg))
        self._anim.start()

    def set_native_pressed(self, pressed: bool):
        pressed = bool(pressed)
        if pressed == self._native_pressed:
            return
        self._native_pressed = pressed
        self.update()

    def _on_color_changed(self, color):
        self._cur = color.name() if hasattr(color, 'name') else str(color)
        self.update()

    def reset_state(self):
        self._anim.stop()
        self._native_hovered = False
        self._native_pressed = False
        self._cur = self._bg
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        bg = QColor(self._press if (self.isDown() or self._native_pressed) else self._cur)
        painter.fillRect(self.rect(), bg)
        icon = self.icon()
        if not icon.isNull():
            sz = self.iconSize()
            x = (self.width() - sz.width()) // 2
            y = (self.height() - sz.height()) // 2
            icon.paint(painter, x, y, sz.width(), sz.height())

    def hideEvent(self, event):
        self.reset_state()
        super().hideEvent(event)

    def showEvent(self, event):
        self.reset_state()
        super().showEvent(event)

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._hover))
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._native_hovered = False
        self._native_pressed = False
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._bg))
        self._anim.start()
        super().leaveEvent(event)


class CustomTitleBar(QWidget):
    """
    Cross-platform custom title bar.
    """

    _MENU_BTN_QSS = """
        QPushButton {{
            background: transparent;
            color: {fg};
            font-family: "{font}";
            font-size: {font_size}px;
            border: none;
            padding: {pad_y}px {pad_x}px;
            border-radius: {radius}px;
        }}
        QPushButton:hover {{ background: #2b2b2b; color: #ffffff; }}
        QPushButton:pressed {{ background: #333333; color: #ffffff; }}
    """

    projectExportRequested = Signal()
    projectImportRequested = Signal()
    transcriptExportTxtRequested = Signal()
    transcriptCopyRequested = Signal()

    def __init__(self, window: QWidget, lang: str, parent=None):
        super().__init__(parent)
        self._win = window
        self._lang = lang
        self._transcription_active = False
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(config.S(32))
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#CustomTitleBar {{ background-color: {config.COLOR_TITLEBAR_BG}; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(config.S(12), 0, 0, 0)
        lay.setSpacing(0)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFixedSize(config.S(18), config.S(32))
        self._icon_lbl.setStyleSheet("background: transparent;")
        self._icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.update_titlebar_icon()
        lay.addWidget(self._icon_lbl)
        lay.addSpacing(config.S(6))

        self._lbl_title = QLabel(config.APP_NAME)
        self._full_title = config.APP_NAME
        self._lbl_title.setTextFormat(Qt.RichText)
        self._lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._lbl_title.setStyleSheet(
            f"color: #999999; font-family: \"{config.UI_FONT_NAME}\"; "
            f"font-size: {config.FS_PX(9)}px; background: transparent;"
        )
        lay.addWidget(self._lbl_title)

        self._menu_container = QWidget(self)
        self._menu_container.setStyleSheet("background: transparent;")
        menu_lay = QHBoxLayout(self._menu_container)
        menu_lay.setContentsMargins(0, 0, 0, 0)
        menu_lay.setSpacing(config.S(2))

        _btn_qss = self._MENU_BTN_QSS.format(
            fg="#888888",
            font=config.UI_FONT_NAME,
            font_size=config.FS_PX(9),
            pad_y=config.S(2),
            pad_x=config.S(8),
            radius=config.S(3),
        )

        def _t(key):
            return config.get_trans(key, lang)

        self.btn_menu_project = QPushButton(_t("titlebar_project"))
        self.btn_menu_project.setStyleSheet(_btn_qss)
        self.btn_menu_project.setCursor(Qt.PointingHandCursor)
        self.btn_menu_project.clicked.connect(self._show_project_menu)
        menu_lay.addWidget(self.btn_menu_project)

        self.btn_menu_transcript = QPushButton(_t("titlebar_transcript"))
        self.btn_menu_transcript.setStyleSheet(_btn_qss)
        self.btn_menu_transcript.setCursor(Qt.PointingHandCursor)
        self.btn_menu_transcript.clicked.connect(self._show_transcript_menu)
        menu_lay.addWidget(self.btn_menu_transcript)

        self.btn_menu_edit = QPushButton(_t("titlebar_edit"))
        self.btn_menu_edit.setStyleSheet(_btn_qss)
        self.btn_menu_edit.setCursor(Qt.PointingHandCursor)
        self.btn_menu_edit.clicked.connect(self._show_edit_menu)
        menu_lay.addWidget(self.btn_menu_edit)

        self._menu_container.hide()
        lay.addWidget(self._menu_container)
        lay.addStretch()

        self._lbl_source_info = QLabel(self)
        self._lbl_source_info.setTextFormat(Qt.RichText)
        self._lbl_source_info.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._lbl_source_info.setStyleSheet(
            f"color: #777777; font-family: \"{config.UI_FONT_NAME}\"; "
            f"font-size: {config.FS_PX(9)}px; background: transparent;"
        )
        self._lbl_source_info.hide()
        self._full_source_info = ""

        _orig_label = config.get_trans("titlebar_original", lang)
        self.chapter_dropdown = TitleDropdown([_orig_label], parent=self)
        self.chapter_dropdown.setFixedHeight(config.S(24))
        self.chapter_dropdown.setMinimumWidth(config.S(100))
        self.chapter_dropdown.hide()

        from ..utils import get_layout_icon_path
        self.btn_min = AnimatedTitleButton(
            get_layout_icon_path("minimize.png"),
            "btn_minimize", lang, parent=self
        )
        self.btn_max = AnimatedTitleButton(
            get_layout_icon_path("maximize.png"),
            "btn_maximize", lang, parent=self
        )
        self.btn_close = AnimatedTitleButton(
            get_layout_icon_path("exit.png"),
            "btn_close", lang, parent=self
        )

        self.btn_min.clicked.connect(self._minimize_window)
        self.btn_max.clicked.connect(lambda: self._toggle_maximize(via_button=True))
        self.btn_close.clicked.connect(self._close_window)

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(btn)

    def update_titlebar_icon(self, icon_name: str = None):
        if hasattr(self, '_icon_lbl'):
            pix = _titlebar_icon(icon_name).pixmap(QSize(config.S(14), config.S(14)))
            if not pix.isNull():
                self._icon_lbl.setPixmap(pix)

    def _popup_flags_for_window(self):
        flags = Qt.Popup | Qt.FramelessWindowHint
        win = self.window()
        if win is not None and (
            getattr(win, '_always_on_top_active', False) or bool(win.windowFlags() & Qt.WindowStaysOnTopHint)
        ):
            flags |= Qt.WindowStaysOnTopHint
        return flags

    def _position_popup_on_screen(self, popup: QWidget, global_pos: QPoint):
        win = self.window()
        scr = (
            QGuiApplication.screenAt(global_pos)
            or (win.screen() if win else None)
            or QGuiApplication.primaryScreen()
        )
        x, y = global_pos.x(), global_pos.y()
        if scr is not None:
            sg = scr.availableGeometry()
            pw = max(popup.width(), popup.sizeHint().width())
            ph = max(popup.height(), popup.sizeHint().height())
            x = max(sg.left() + 4, min(x, sg.right() - pw - 4))
            if y + ph > sg.bottom() - 4:
                y = max(sg.top() + 4, global_pos.y() - ph - self.height() - 4)
            y = max(sg.top() + 4, min(y, sg.bottom() - ph - 4))
        popup.move(x, y)

    def _show_titlebar_popup(self, anchor_btn, items):
        """Generic popup for titlebar menus. items = [(label, callback), ...]"""
        popup = QFrame(self, self._popup_flags_for_window())
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 1px solid #2e2e2e;
                border-radius: 0px;
                padding: {config.S(4)}px 0;
            }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, config.S(4), 0, config.S(4))
        layout.setSpacing(0)

        for label, callback in items:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #b0b0b0;
                    font-family: "{config.UI_FONT_NAME}";
                    font-size: {config.FS_PX(9)}px;
                    text-align: left;
                    padding: {config.S(5)}px {config.S(14)}px;
                    border: none;
                    border-radius: 0px;
                }}
                QPushButton:hover {{ background: #222222; color: #ffffff; }}
            """)
            btn.clicked.connect(lambda checked, cb=callback, p=popup: (p.close(), cb()))
            layout.addWidget(btn)

        global_pos = anchor_btn.mapToGlobal(QPoint(0, anchor_btn.height() + 2))
        popup.adjustSize()
        popup.setMinimumWidth(max(anchor_btn.width(), popup.sizeHint().width()))
        popup.adjustSize()
        self._position_popup_on_screen(popup, global_pos)
        popup.show()

    def _show_project_menu(self):
        def _t(key):
            return config.get_trans(key, self._lang)
        self._show_titlebar_popup(self.btn_menu_project, [
            (_t("titlebar_export_project"), lambda: self.projectExportRequested.emit()),
            (_t("titlebar_import_project"), lambda: self.projectImportRequested.emit()),
        ])

    def _show_transcript_menu(self):
        def _t(key):
            return config.get_trans(key, self._lang)
        self._show_titlebar_popup(self.btn_menu_transcript, [
            (_t("titlebar_export_txt"), lambda: self.transcriptExportTxtRequested.emit()),
            (_t("titlebar_copy_clipboard"), lambda: self.transcriptCopyRequested.emit()),
        ])

    def _show_edit_menu(self):
        """Shows the edit/chapter selection popup."""
        popup = QFrame(self, self._popup_flags_for_window())
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border: 1px solid #2e2e2e;
                border-radius: 0px;
                padding: 0px;
                margin: 0px;
            }}
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.addItems(self.chapter_dropdown.options_list)
        list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none; padding: 0px; margin: 0px; outline: none;
                background: transparent; color: #b0b0b0; font-size: {config.FS_PX(9)}px;
            }}
            QListWidget::item {{ height: {config.S(26)}px; padding: 0px {config.S(8)}px; border: none; }}
            QListWidget::item:selected {{ background-color: #171717; color: #1ed760; font-weight: bold; }}
            QListWidget::item:focus {{ border: none; outline: none; }}
            QListWidget::item:hover {{ background-color: #222222; color: #ffffff; }}
            QListWidget::item:selected:hover {{ background-color: #171717; color: #1ed760; }}
        """)

        cur = self.chapter_dropdown.currentText()
        for row in range(list_widget.count()):
            if list_widget.item(row).text() == cur:
                list_widget.setCurrentRow(row)
                break

        def _on_item(item):
            self.chapter_dropdown._on_item_clicked(item, popup)

        list_widget.itemClicked.connect(_on_item)
        layout.addWidget(list_widget)

        row_h = config.S(26)
        display_count = list_widget.count()
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)
        popup.setFixedWidth(max(self.btn_menu_edit.width(), config.S(140)))

        global_pos = self.btn_menu_edit.mapToGlobal(QPoint(0, self.btn_menu_edit.height() + 2))
        self._position_popup_on_screen(popup, global_pos)
        popup.show()

    def activate_transcription_mode(self):
        """Switch from simple 'BadWords' title to [Project] [Transcript] [Edit] menus."""
        self._transcription_active = True
        self._lbl_title.hide()
        self._menu_container.show()
        self._lbl_source_info.show()
        self._update_source_info_placement()

    def deactivate_transcription_mode(self):
        """Switch back to simple 'BadWords' title."""
        self._transcription_active = False
        self._lbl_title.show()
        self._lbl_title.setText(config.APP_NAME)
        self._full_title = config.APP_NAME
        self._menu_container.hide()
        self._lbl_source_info.hide()

    def set_source_info(self, tl_name, tracks_str):
        """Update the centered source info label."""
        def _t(key):
            return config.get_trans(key, self._lang)
        msg = _t("titlebar_source_info")
        if "{tl}" in msg:
            text = msg.replace("{tl}", tl_name).replace("{tr}", tracks_str)
        else:
            text = f"Source: <i>{tl_name}</i> - Tracks: <i>{tracks_str}</i>"
        self._full_source_info = text
        self._lbl_source_info.setText(text)
        self._update_source_info_placement()

    def set_title(self, text):
        """Legacy title setter."""
        self._full_title = text
        if not self._transcription_active:
            self._lbl_title.setText(text)
            self.update_elision()

    def _right_controls_left_edge(self) -> int:
        visible_xs = [
            btn.x()
            for btn in (self.btn_min, self.btn_max, self.btn_close)
            if not btn.isHidden() and btn.x() > 0
        ]
        if visible_xs:
            return min(visible_xs)
        visible_count = sum(1 for btn in (self.btn_min, self.btn_max, self.btn_close) if not btn.isHidden())
        return max(0, self.width() - visible_count * self.btn_close.width())

    def update_elision(self):
        from PySide6.QtGui import QFontMetrics, QTextDocument
        if self._transcription_active:
            self._update_source_info_placement()
            return

        right_bound = self._right_controls_left_edge() - config.S(8)
        left_x = max(config.S(36), self._lbl_title.x())
        max_w = max(10, right_bound - left_x)

        doc = QTextDocument()
        doc.setHtml(self._full_title)
        plain = doc.toPlainText()

        fm = QFontMetrics(self._lbl_title.font())
        if fm.horizontalAdvance(plain) <= max_w:
            self._lbl_title.setText(self._full_title)
        else:
            elided = fm.elidedText(plain, Qt.ElideRight, max_w)
            self._lbl_title.setText(elided)

    def _update_source_info_placement(self):
        """Centers the source info label cleanly without ever overlapping menu or control buttons."""
        if not self._transcription_active:
            return
        from PySide6.QtGui import QFontMetrics, QTextDocument

        pad = config.S(12)
        if not self._menu_container.isHidden():
            menu_hint_w = max(self._menu_container.width(), self._menu_container.sizeHint().width())
            menu_x = self._menu_container.x() if self._menu_container.x() > 0 else config.S(36)
            left_bound = menu_x + menu_hint_w + pad
        else:
            left_bound = self._icon_lbl.x() + self._icon_lbl.width() + pad

        right_bound = self._right_controls_left_edge() - pad
        avail_space = right_bound - left_bound
        if avail_space < config.S(40):
            self._lbl_source_info.hide()
            return

        self._lbl_source_info.show()
        doc = QTextDocument()
        doc.setHtml(self._full_source_info)
        plain = doc.toPlainText()
        fm = QFontMetrics(self._lbl_source_info.font())

        desired_w = fm.horizontalAdvance(plain) + config.S(8)
        text_w = min(desired_w, avail_space)

        # Ideal centered X, then clamped strictly into [left_bound, right_bound - text_w]
        centered_x = (self.width() - text_w) // 2
        lbl_x = max(left_bound, min(centered_x, right_bound - text_w))
        self._lbl_source_info.setGeometry(lbl_x, 0, text_w, self.height())

        avail = max(4, text_w - config.S(4))
        if fm.horizontalAdvance(plain) > avail:
            self._lbl_source_info.setText(fm.elidedText(plain, Qt.ElideRight, avail))
        else:
            self._lbl_source_info.setText(self._full_source_info)

    def update_dropdown_placement(self):
        self._update_source_info_placement()
        if not self._transcription_active:
            self.update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dropdown_placement()

    def update_maximize_icon(self, is_maximized):
        icon_name = 'windowed.png' if is_maximized else 'maximize.png'
        from ..utils import get_layout_icon_path
        icon_path = get_layout_icon_path(icon_name)
        self.btn_max.change_base_icon(icon_path)
        self.btn_max.setIconSize(QSize(config.S(12), config.S(12)))

    def _minimize_window(self):
        win = self.window()
        if getattr(win, '_is_win', False):
            try:
                from .mixins import _get_win32_apis
                user32, _, _ = _get_win32_apis()
                user32.PostMessageW(int(win.winId()), 0x0112, 0xF020, 0)  # SC_MINIMIZE
                return
            except Exception:
                pass
        win.showMinimized()

    def _close_window(self):
        win = self.window()
        if getattr(win, '_is_win', False) and getattr(win, '_is_root', False):
            try:
                from .mixins import _get_win32_apis
                user32, _, _ = _get_win32_apis()
                user32.PostMessageW(int(win.winId()), 0x0112, 0xF060, 0)  # SC_CLOSE
                return
            except Exception:
                pass
        win.close()

    def _toggle_maximize(self, via_button: bool = True):
        win = self.window()
        if not getattr(win, '_is_root', False):
            return

        if getattr(win, '_is_win', False):
            try:
                from .mixins import _get_win32_apis
                user32, _, _ = _get_win32_apis()
                hwnd = int(win.winId())
                is_max = bool(win._is_effectively_maximized()) if hasattr(win, '_is_effectively_maximized') else win.isMaximized()
                if is_max:
                    win._restore_via_button = bool(via_button)
                    if hasattr(win, '_sync_win_normal_placement'):
                        win._sync_win_normal_placement(use_button_restore=bool(via_button))
                    user32.PostMessageW(hwnd, 0x0112, 0xF120, 0)  # SC_RESTORE
                else:
                    if hasattr(win, '_snapshot_pre_maximize_geometry'):
                        win._snapshot_pre_maximize_geometry()
                    user32.PostMessageW(hwnd, 0x0112, 0xF030, 0)  # SC_MAXIMIZE
                return
            except Exception:
                pass

        is_max = bool(win._is_effectively_maximized()) if hasattr(win, '_is_effectively_maximized') else win.isMaximized()
        if is_max:
            win._restore_via_button = bool(via_button)
            win.showNormal()
            if hasattr(win, '_restore_after_unmaximize'):
                win._restore_after_unmaximize(via_button=bool(via_button))
        else:
            if hasattr(win, '_snapshot_pre_maximize_geometry'):
                win._snapshot_pre_maximize_geometry()
            win.showMaximized()

    def mousePressEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._manual_drag_active = False
            self._manual_drag_offset = None
            self._rip_pending_system_move = False
            self._rip_drag_offset = None
            self._rip_target_size = None
            self._click_pos = event.position().toPoint()
            self._press_global_pos = event.globalPosition().toPoint()
            win = self.window()
            if getattr(win, '_is_mac', False) and getattr(win, '_is_popup', False):
                self._manual_drag_offset = self._press_global_pos - win.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def _begin_rip_system_move(self, win, tw: int, th: int):
        if not getattr(self, '_rip_pending_system_move', False):
            return
        self._rip_pending_system_move = False
        offset = getattr(self, '_rip_drag_offset', None)
        from PySide6.QtWidgets import QApplication
        if not (QApplication.mouseButtons() & Qt.LeftButton):
            return
        try:
            if offset is not None:
                cur = QGuiApplication.primaryScreen()
                cur_pos = win.mapToGlobal(self.mapTo(win, QPoint(0, 0)))
                from PySide6.QtGui import QCursor
                gpos = QCursor.pos()
                scr = QGuiApplication.screenAt(gpos) or win.screen() or cur
                sg = scr.availableGeometry() if scr else None
                nx = gpos.x() - offset.x()
                ny = gpos.y() - offset.y()
                if sg and sg.isValid():
                    nx = max(sg.left(), min(nx, sg.left() + sg.width() - tw))
                    ny = max(sg.top(), min(ny, sg.top() + sg.height() - th))
                win.setGeometry(nx, ny, tw, th)
                if hasattr(win, 'windowHandle') and win.windowHandle():
                    win.windowHandle().setGeometry(nx, ny, tw, th)
            QGuiApplication.sync()
            if hasattr(win, 'windowHandle') and win.windowHandle():
                win.windowHandle().startSystemMove()
        except Exception as e:
            from osdoc import log_info
            log_info(f"startSystemMove error: {e}")

    def mouseMoveEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return

        cur_global = event.globalPosition().toPoint()

        # While X11 WM settles un-maximize before startSystemMove, keep window locked under cursor
        if getattr(self, '_rip_pending_system_move', False):
            win = self.window()
            offset = getattr(self, '_rip_drag_offset', None)
            tsize = getattr(self, '_rip_target_size', None)
            if offset is not None and tsize is not None:
                scr = QGuiApplication.screenAt(cur_global) or win.screen() or QGuiApplication.primaryScreen()
                sg = scr.availableGeometry() if scr else None
                tw, th = tsize
                nx = cur_global.x() - offset.x()
                ny = cur_global.y() - offset.y()
                if sg and sg.isValid():
                    nx = max(sg.left(), min(nx, sg.left() + sg.width() - tw))
                    ny = max(sg.top(), min(ny, sg.top() + sg.height() - th))
                win.setGeometry(nx, ny, tw, th)
                if hasattr(win, 'windowHandle') and win.windowHandle():
                    win.windowHandle().setGeometry(nx, ny, tw, th)
            event.accept()
            return

        if not getattr(self, '_is_dragging', False):
            super().mouseMoveEvent(event)
            return

        press_global = getattr(self, '_press_global_pos', cur_global)
        if not getattr(self, '_manual_drag_active', False) and (cur_global - press_global).manhattanLength() < 4:
            event.accept()
            return

        win = self.window()

        # On macOS, dragging fixed/frameless popups via startSystemMove() can distort Cocoa bounds;
        # move manually clamped inside the active screen's availableGeometry instead.
        if getattr(self, '_manual_drag_offset', None) is not None and getattr(win, '_is_mac', False) and getattr(win, '_is_popup', False):
            self._manual_drag_active = True
            nx = cur_global.x() - self._manual_drag_offset.x()
            ny = cur_global.y() - self._manual_drag_offset.y()
            scr = QGuiApplication.screenAt(cur_global) or win.screen() or QGuiApplication.primaryScreen()
            sg = scr.availableGeometry() if scr else None
            if sg and sg.isValid():
                nx = max(sg.left() - win.width() + 60, min(nx, sg.right() - 60))
                ny = max(sg.top(), min(ny, sg.bottom() - 40))
            win.move(nx, ny)
            event.accept()
            return

        self._is_dragging = False

        # INVARIANT: On Linux/macOS, ripping out of maximized MUST un-maximize & resize to target
        # size (70% x 70% MainWindow; small default Settings) with exact proportional horizontal
        # cursor placement BEFORE startSystemMove() so WMs never jump left or revert size.
        is_max = bool(win._is_effectively_maximized()) if hasattr(win, '_is_effectively_maximized') else win.isMaximized()
        if is_max and not getattr(win, '_is_win', False):
            win._restore_via_button = False
            win._restoring_from_max = True
            from PySide6.QtCore import QTimer
            try:
                from .mixins import compute_proportional_rip_rect
                scr = QGuiApplication.screenAt(cur_global) or win.screen() or QGuiApplication.primaryScreen()
                sg = scr.availableGeometry() if scr else None
                rip_geo = win._compute_rip_geometry(screen=scr) if hasattr(win, '_compute_rip_geometry') else None
                if rip_geo and rip_geo.isValid():
                    tw, th = rip_geo.width(), rip_geo.height()
                    click_pt = getattr(self, '_click_pos', QPoint(win.width() // 2, 16))
                    max_w = max(1, win.width())
                    target_rect = compute_proportional_rip_rect(
                        cursor_x=cur_global.x(),
                        cursor_y=cur_global.y(),
                        click_x=click_pt.x(),
                        click_y=click_pt.y(),
                        maximized_w=max_w,
                        target_w=tw,
                        target_h=th,
                        screen_geo=sg,
                    )
                    if getattr(win, '_is_wayland', False):
                        win.showNormal()
                        win.resize(target_rect.width(), target_rect.height())
                        if hasattr(win, 'windowHandle') and win.windowHandle():
                            win.windowHandle().startSystemMove()
                    else:
                        self._rip_drag_offset = QPoint(
                            cur_global.x() - target_rect.x(),
                            cur_global.y() - target_rect.y(),
                        )
                        self._rip_target_size = (target_rect.width(), target_rect.height())
                        self._rip_pending_system_move = True
                        win.showNormal()
                        win.setGeometry(target_rect)
                        if hasattr(win, 'windowHandle') and win.windowHandle():
                            win.windowHandle().setGeometry(target_rect)
                        QGuiApplication.sync()
                        # Wait ~25ms for X11 WM (Muffin/KWin/Mutter) to process _NET_WM_STATE
                        # unmaximize & ConfigureNotify at target_rect BEFORE starting system move grab.
                        QTimer.singleShot(
                            25,
                            lambda w=win, rw=target_rect.width(), rh=target_rect.height(): self._begin_rip_system_move(w, rw, rh),
                        )
                    QTimer.singleShot(160, lambda w=win: setattr(w, '_restoring_from_max', False))
                    event.accept()
                    return
            except Exception:
                QTimer.singleShot(120, lambda w=win: setattr(w, '_restoring_from_max', False))

        if hasattr(win, 'windowHandle') and win.windowHandle():
            try:
                win.windowHandle().startSystemMove()
            except Exception as e:
                from osdoc import log_info
                log_info(f"startSystemMove error: {e}")

        event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        self._manual_drag_active = False
        self._manual_drag_offset = None
        self._rip_pending_system_move = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._toggle_maximize(via_button=False)
        super().mouseDoubleClickEvent(event)
