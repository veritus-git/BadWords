#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: titlebar.py
ROLE: GUI Component
DESCRIPTION:
Custom window titlebar with window control buttons.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QListWidget
)
from PySide6.QtCore import Qt, QSize, QVariantAnimation, QEasingCurve, Signal, QPoint
from PySide6.QtGui import QIcon, QPixmap, QColor
import config
from ..widgets.buttons import TitleDropdown
from ..utils import _app_icon

class AnimatedTitleButton(QPushButton):
    """
    Title-bar control button with a 150ms QVariantAnimation colour transition
    on hover. The close button uses a red hover (#c42b1c) to match Discord/
    Spotify conventions; all other buttons use HOVER from config.
    """

    def __init__(self, icon_path: str, tooltip_key: str, lang: str, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBarBtn")
        self._bg    = config.COLOR_TITLEBAR_BG
        self._hover = config.COLOR_TITLEBAR_HOVER
        self._press = "#3a3a3d"
        self._cur   = self._bg

        self.setFixedSize(32, 32)
        from ..utils import _txt
        self.setToolTip(_txt(lang, tooltip_key))
        self.setCursor(Qt.ArrowCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAutoFillBackground(False)
        self.setFlat(True)

        pix = QPixmap(icon_path)
        if not pix.isNull():
            self.setIcon(QIcon(pix))
            self.setIconSize(QSize(12, 12))

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self._on_color_changed)
        self._icon_path = icon_path

        self._update_style()

    def change_base_icon(self, new_icon_path):
        self._icon_path = new_icon_path
        self.setIcon(QIcon(new_icon_path))
        self.update()

    # ── internal ─────────────────────────────────────────────────────────────
    def _on_color_changed(self, color):
        self._cur = color.name() if hasattr(color, 'name') else str(color)
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton#TitleBarBtn {{
                background-color: {self._cur}; border: none; border-radius: 0px;
                min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px;
                margin: 0px; padding: 0px;
            }}
            QPushButton#TitleBarBtn:pressed {{ background-color: {self._press}; }}
        """)

    # ── events ────────────────────────────────────────────────────────────────
    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._hover))
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(QColor(self._cur))
        self._anim.setEndValue(QColor(self._bg))
        self._anim.start()
        super().leaveEvent(event)


class CustomTitleBar(QWidget):
    """
    Cross-platform custom title bar.

    macOS / Linux
    -------------
    • Dragging  → QWindow.startSystemMove()  (native OS behaviour)
    • Dbl-click → toggle maximized             (native OS behaviour)

    Windows (with qframelesswindow library)
    ----------------------------------------
    • Dragging  → win32gui.ReleaseCapture + WM_SYSCOMMAND SC_MOVE|HTCAPTION
                  (full Aero Snap, drag-detach from maximized, snap layouts)
    • Dbl-click → toggle maximized via WM_SYSCOMMAND SC_MAXIMIZE/SC_RESTORE
    • Resize    → handled by library's nativeEvent (WM_NCHITTEST border edges)
    """

    # ── Shared titlebar menu button style ────────────────────────────────────
    _MENU_BTN_QSS = """
        QPushButton {{
            background: transparent;
            color: {fg};
            font-family: "{font}";
            font-size: 9pt;
            border: none;
            padding: 2px 8px;
            border-radius: 3px;
        }}
        QPushButton:hover {{ background: #2b2b2b; color: #ffffff; }}
        QPushButton:pressed {{ background: #333333; color: #ffffff; }}
    """

    # Signal emitted when the user picks an action from a menu dropdown
    projectExportRequested = Signal()
    projectImportRequested = Signal()
    transcriptExportTxtRequested = Signal()
    transcriptCopyRequested = Signal()

    def __init__(self, window: QWidget, lang: str, parent=None):
        super().__init__(parent)
        self._win  = window
        self._lang = lang
        self._transcription_active = False  # True after first transcription
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(32)
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#CustomTitleBar {{ background-color: {config.COLOR_TITLEBAR_BG}; }}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(0)

        # Small app-icon
        icon_lbl = QLabel()
        icon_pix = _app_icon().pixmap(QSize(14, 14))
        if not icon_pix.isNull():
            icon_lbl.setPixmap(icon_pix)
        icon_lbl.setFixedSize(18, 32)
        icon_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(icon_lbl)
        lay.addSpacing(6)

        # ── DEFAULT title label (shown before transcription) ──
        self._lbl_title = QLabel(config.APP_NAME)
        self._full_title = config.APP_NAME
        self._lbl_title.setTextFormat(Qt.RichText)
        self._lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._lbl_title.setStyleSheet(
            f"color: #999999; font-family: \"{config.UI_FONT_NAME}\"; "
            f"font-size: 9pt; background: transparent;"
        )
        lay.addWidget(self._lbl_title)

        # ── POST-TRANSCRIPTION menu buttons container ──
        self._menu_container = QWidget(self)
        self._menu_container.setStyleSheet("background: transparent;")
        menu_lay = QHBoxLayout(self._menu_container)
        menu_lay.setContentsMargins(0, 0, 0, 0)
        menu_lay.setSpacing(2)

        _btn_qss = self._MENU_BTN_QSS.format(fg="#888888", font=config.UI_FONT_NAME)

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

        # Edit dropdown — always visible after transcription with at least "Original"
        self.btn_menu_edit = QPushButton(_t("titlebar_edit"))
        self.btn_menu_edit.setStyleSheet(_btn_qss)
        self.btn_menu_edit.setCursor(Qt.PointingHandCursor)
        self.btn_menu_edit.clicked.connect(self._show_edit_menu)
        menu_lay.addWidget(self.btn_menu_edit)

        self._menu_container.hide()  # hidden until transcription

        lay.addWidget(self._menu_container)

        lay.addStretch()

        # ── CENTERED source info label (replaces old left-aligned title after transcription) ──
        self._lbl_source_info = QLabel(self)
        self._lbl_source_info.setTextFormat(Qt.RichText)
        self._lbl_source_info.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._lbl_source_info.setStyleSheet(
            f"color: #777777; font-family: \"{config.UI_FONT_NAME}\"; "
            f"font-size: 9pt; background: transparent;"
        )
        self._lbl_source_info.hide()
        self._full_source_info = ""
        # Absolutely positioned — updated in resizeEvent

        # Chapter Dropdown — kept for backwards compat but now internal to Edit menu
        _orig_label = config.get_trans("titlebar_original", lang)
        self.chapter_dropdown = TitleDropdown([_orig_label], parent=self)
        self.chapter_dropdown.setFixedHeight(24)
        self.chapter_dropdown.setMinimumWidth(100)
        self.chapter_dropdown.hide()  # Always hidden — Edit menu now owns this
        
        # Resolve icon directory relative to gui/components/titlebar.py -> src/assets/layout
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        _prod_assets_dir = os.path.join(_src_dir, "layout")
        _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
        _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir

        self.btn_min = AnimatedTitleButton(
            os.path.join(_assets_dir, "minimize.png"),
            "btn_minimize", lang, parent=self)
        self.btn_max = AnimatedTitleButton(
            os.path.join(_assets_dir, "maximize.png"),
            "btn_maximize", lang, parent=self)
        self.btn_close    = AnimatedTitleButton(
            os.path.join(_assets_dir, "exit.png"),
            "btn_close",    lang, parent=self)

        self.btn_min.clicked.connect(self._minimize_window)
        self.btn_max.clicked.connect(self._toggle_maximize)
        self.btn_close.clicked.connect(self._close_window)

        for btn in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(btn)

    # ── Titlebar menu dropdowns ───────────────────────────────────────────────
    def _show_titlebar_popup(self, anchor_btn, items):
        """Generic popup for titlebar menus. items = [(label, callback), ...]"""
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 4px 0;
            }
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(0)

        for label, callback in items:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #b0b0b0;
                    font-family: "{config.UI_FONT_NAME}";
                    font-size: 9pt;
                    text-align: left;
                    padding: 5px 14px;
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
        popup.move(global_pos)
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
        """Shows the edit/chapter selection popup (same as old chapter_dropdown)."""
        popup = QFrame(self, Qt.Popup | Qt.FramelessWindowHint)
        popup.setAttribute(Qt.WA_DeleteOnClose)
        popup.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 6px;
                padding: 0px;
                margin: 0px;
            }
        """)
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        list_widget = QListWidget()
        list_widget.setFrameShape(QFrame.Shape.NoFrame)
        list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget.addItems(self.chapter_dropdown.options_list)
        list_widget.setStyleSheet("""
            QListWidget {
                border: none; padding: 0px; margin: 0px; outline: none;
                background: transparent; color: #b0b0b0; font-size: 9pt;
            }
            QListWidget::item { height: 26px; padding: 0px 8px; border: none; }
            QListWidget::item:selected { background-color: #171717; color: #1ed760; font-weight: bold; }
            QListWidget::item:focus { border: none; outline: none; }
            QListWidget::item:hover { background-color: #222222; color: #ffffff; }
            QListWidget::item:selected:hover { background-color: #171717; color: #1ed760; }
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

        row_h = 26
        display_count = list_widget.count()
        list_height = display_count * row_h
        list_widget.setFixedHeight(list_height)
        popup.setFixedHeight(list_height + 2)

        global_pos = self.btn_menu_edit.mapToGlobal(QPoint(0, self.btn_menu_edit.height() + 2))
        popup.move(global_pos)
        popup.setFixedWidth(max(self.btn_menu_edit.width(), 140))
        popup.show()

    # ── Activate post-transcription mode ──────────────────────────────────────
    def activate_transcription_mode(self):
        """Switch from simple 'BadWords' title to [Project] [Transcript] [Edit] menus."""
        self._transcription_active = True
        self._lbl_title.hide()
        self._menu_container.show()
        self._lbl_source_info.show()

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
            text = f"Source: <i>{tl_name}</i> — Tracks: <i>{tracks_str}</i>"
        self._full_source_info = text
        self._lbl_source_info.setText(text)
        self._update_source_info_placement()

    def set_title(self, text):
        """Legacy title setter — for backward compat. Now also updates source info if in transcription mode."""
        self._full_title = text
        if not self._transcription_active:
            self._lbl_title.setText(text)
            self.update_elision()

    def update_elision(self):
        from PySide6.QtGui import QFontMetrics, QTextDocument
        if self._transcription_active:
            self._update_source_info_placement()
            return

        btn_area = self.btn_min.width() * 3 + 4
        max_w = max(10, self.width() - self._lbl_title.x() - btn_area - 4)

        # Measure using plain text (HTML tags would inflate the pixel width)
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
        """Centers the source info label between menu buttons and window controls."""
        if not self._lbl_source_info.isVisible():
            return
        from PySide6.QtGui import QFontMetrics, QTextDocument
        doc = QTextDocument()
        doc.setHtml(self._full_source_info)
        plain = doc.toPlainText()
        fm = QFontMetrics(self._lbl_source_info.font())
        text_w = min(fm.horizontalAdvance(plain) + 10, self.width() // 2)

        # Center in the title bar
        lbl_x = (self.width() - text_w) // 2
        self._lbl_source_info.setGeometry(lbl_x, 0, text_w, self.height())

        # Elide if needed
        avail = text_w - 4
        if fm.horizontalAdvance(plain) > avail:
            self._lbl_source_info.setText(fm.elidedText(plain, Qt.ElideRight, avail))
        else:
            self._lbl_source_info.setText(self._full_source_info)

    def update_dropdown_placement(self):
        # Chapter dropdown is now hidden — Edit menu owns this
        self._update_source_info_placement()
        if not self._transcription_active:
            self.update_elision()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_dropdown_placement()

    def update_maximize_icon(self, is_maximized):
        icon_name = 'windowed.png' if is_maximized else 'maximize.png'
        _src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        _prod_assets_dir = os.path.join(_src_dir, "layout")
        _dev_assets_dir = os.path.join(os.path.dirname(_src_dir), "assets", "layout")
        _assets_dir = _prod_assets_dir if os.path.exists(_prod_assets_dir) else _dev_assets_dir
        icon_path = os.path.join(_assets_dir, icon_name)

        # Używamy nowej metody, która zabezpiecza ikonę przed resetem przez animację hover!
        self.btn_max.change_base_icon(icon_path)
        self.btn_max.setIconSize(QSize(14, 14))

    # ── helpers ───────────────────────────────────────────────────────────────
    def _minimize_window(self):
        win = self.window()
        if getattr(win, '_is_win', False):
            try:
                import ctypes
                ctypes.windll.user32.PostMessageW(int(win.winId()), 0x0112, 0xF020, 0) # SC_MINIMIZE
                return
            except Exception:
                pass
        win.showMinimized()

    def _close_window(self):
        win = self.window()
        if getattr(win, '_is_win', False):
            try:
                import ctypes
                ctypes.windll.user32.PostMessageW(int(win.winId()), 0x0112, 0xF060, 0) # SC_CLOSE
                return
            except Exception:
                pass
        win.close()

    def _toggle_maximize(self):
        # Zapis/odczyt stanu przed maksymalizacją, aby przycisk "windowed"
        # przywracał dokładny poprzedni rozmiar i położenie.
        win = self.window()
        if not getattr(win, '_is_root', False):
            return

        if getattr(win, '_is_win', False):
            try:
                import ctypes
                hwnd = int(win.winId())
                if win.isMaximized():
                    ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF120, 0) # SC_RESTORE
                else:
                    win._pre_max_geometry = win.geometry()
                    ctypes.windll.user32.PostMessageW(hwnd, 0x0112, 0xF030, 0) # SC_MAXIMIZE
                return
            except Exception:
                pass

        if win.isMaximized():
            win.showNormal()
            saved_geo = getattr(win, '_pre_max_geometry', None)
            if saved_geo and saved_geo.isValid():
                win.setGeometry(saved_geo)
        else:
            win._pre_max_geometry = win.geometry()  # zapamiętaj przed max
            if getattr(win, '_is_mac', False):
                win.showFullScreen()
            else:
                win.showMaximized()

    def mousePressEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._click_pos = event.position().toPoint()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return
        if not getattr(self, '_is_dragging', False):
            super().mouseMoveEvent(event)
            return

        win = self.window()
        self._is_dragging = False
        
        # Native window dragging
        # Modern Window Managers (DWM, Mutter, KWin, Wayland) natively un-maximize 
        # the window if startSystemMove is called while maximized, providing seamless 
        # cursor proportional attachment and edge-snapping (Aero Snap) out of the box.
        if hasattr(win, 'windowHandle') and win.windowHandle():
            try:
                win.windowHandle().startSystemMove()
            except Exception as e:
                import osdoc
                osdoc.log_info(f"startSystemMove error: {e}")

        event.accept()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if not getattr(self, 'movable', True):
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self._toggle_maximize()
        super().mouseDoubleClickEvent(event)
