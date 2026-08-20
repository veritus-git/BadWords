#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: mixins.py
ROLE: GUI Component
DESCRIPTION:
Helper mixin classes providing additional behaviors to GUI widgets.
"""

from PySide6.QtWidgets import QWidget, QMainWindow, QDialog
from PySide6.QtCore import Qt

_HAS_QFRAMELESS = False
_BaseMainWindow = QMainWindow
_BaseDialog = QDialog

class ResizeGrip(QWidget):
    def __init__(self, parent, edge):
        super().__init__(parent)
        self.edge = edge
        self.setStyleSheet("background: transparent;")
        
        if self.edge == Qt.TopEdge or self.edge == Qt.BottomEdge: 
            self.setCursor(Qt.SizeVerCursor)
        elif self.edge == Qt.LeftEdge or self.edge == Qt.RightEdge: 
            self.setCursor(Qt.SizeHorCursor)
        elif self.edge == (Qt.TopEdge | Qt.LeftEdge) or self.edge == (Qt.BottomEdge | Qt.RightEdge): 
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edge == (Qt.TopEdge | Qt.RightEdge) or self.edge == (Qt.BottomEdge | Qt.LeftEdge): 
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if hasattr(win, 'windowHandle') and win.windowHandle():
                try:
                    win.windowHandle().startSystemResize(self.edge)
                except Exception as e:
                    import osdoc
                    osdoc.log_info(f"startSystemResize error: {e}")
            event.accept()

class FramelessWindowMixin:
    """
    Mixin that turns any QMainWindow / QDialog into a frameless, CSD window.

    Usage
    -----
        class MyWindow(FramelessWindowMixin, _BaseMainWindow):
            def __init__(self):
                super().__init__()
                self.frameless_init(is_popup=False)

    Provides
    --------
    • frameless_init()      — sets flags, creates shadow for popups
    • moveEvent / resizeEvent — Smart Corners (per-corner border-radius)
    • nativeEvent           — WM_NCHITTEST map (Windows only):
          resize borders → HT* constants
          title bar area → HTCAPTION  (enables Aero Snap, system animations)
          close/min/max buttons → HTCLIENT
          rest of window → HTCLIENT
    """

    _RESIZE_BORDER = 5   # px — hit-test sensitivity at window edges

    # ── public API ────────────────────────────────────────────────────────────
    def frameless_init(self, is_popup: bool = False):
        """Call once, right after super().__init__()."""
        import platform
        from PySide6.QtGui import QGuiApplication
        self._is_win = platform.system() == "Windows"
        self._is_mac = platform.system() == "Darwin"
        self._is_wayland = QGuiApplication.platformName() == 'wayland'
        # Sprawdzamy, czy to jest główne okno (root)
        self._is_root = self.__class__.__name__ == "BadWordsGUI"

        if self._is_win:
            if self._is_root:
                # Root window: FramelessWindowHint eliminuje CAŁĄ NC area — DWM nie
                # rysuje żadnych system buttonów (koniec z "Win98 button" artefaktem).
                # Shadow i animacje odzyskujemy przez SetWindowLong(WS_THICKFRAME|WS_CAPTION)
                # w showEvent + DwmExtendFrameIntoClientArea.
                self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            else:
                # Popups are genuinely frameless — translucency is safe here.
                self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog | Qt.NoDropShadowWindowHint)
                self.setAttribute(Qt.WA_TranslucentBackground, True)
        elif self._is_mac and self._is_root:
            # macOS root window: use native title bar with traffic lights.
            # This gives us the green fullscreen button which hides Dock + Menu Bar.
            # The custom CSD title bar widget is hidden in BadWordsGUI.__init__.
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinMaxButtonsHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowFullscreenButtonHint
            )
        else:
            # Linux and macOS popups: fully frameless + translucent (rounded corners via QSS).
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._is_popup = is_popup

        if not self._is_win and not (self._is_mac and self._is_root):
            self._setup_grips()

    def _get_root_frame(self):
        """Return the topmost styled QFrame to apply border-radius to."""
        return getattr(self, 'inner_frame', getattr(self, '_root_frame', None))

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.WindowStateChange:
            was_max = getattr(self, '_was_maximized', False)
            now_max = self.isMaximized()

            if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
                try:
                    import ctypes
                    hwnd = int(self.winId())
                    if hwnd:
                        # Reaplikacja stylów! Qt czasem resetuje natywne style podczas
                        # zmian stanu (szczególnie max -> drag restore -> max na Win10).
                        user32 = ctypes.windll.user32
                        GWL_STYLE = -16
                        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                        style |= 0x00040000  # WS_THICKFRAME
                        style |= 0x00C00000  # WS_CAPTION
                        style |= 0x00020000  # WS_MINIMIZEBOX
                        style |= 0x00010000  # WS_MAXIMIZEBOX
                        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

                        if was_max and not now_max:
                            # max→normal: DWM ma stary bufor (full-size) i renderuje go
                            # w mniejszym oknie → biały flash. DWMWA_CLOAK(13) ukrywa
                            # okno w DWM na czas przejścia.
                            val = ctypes.c_int(1)
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)
                        
                        ctypes.windll.user32.SetWindowPos(
                            hwnd, None, 0, 0, 0, 0, 
                            0x0001 | 0x0002 | 0x0004 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|FRAMECHANGED
                        )
                        
                        if was_max and not now_max:
                            from PySide6.QtCore import QTimer
                            QTimer.singleShot(30, self._dwm_uncloak)
                except Exception:
                    pass

            self._was_maximized = now_max
            self._refresh_max_state()
        elif event.type() == QEvent.Type.ActivationChange:
            if hasattr(self, '_update_shortcut_enabled_states'):
                self._update_shortcut_enabled_states()
        super().changeEvent(event)

    def _dwm_uncloak(self):
        try:
            import ctypes
            hwnd = int(self.winId())
            if hwnd:
                val = ctypes.c_int(0)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        if not _HAS_QFRAMELESS and getattr(self, '_is_win', False):
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd and getattr(self, '_is_root', False):
                    user32 = ctypes.windll.user32
                    dwmapi = ctypes.windll.dwmapi

                    # 1. Przywróć style okna które FramelessWindowHint usunął:
                    #    WS_THICKFRAME → DWM shadow + resize
                    #    WS_CAPTION    → DWM animacje (minimize/restore)
                    #    WS_MIN/MAXIMIZEBOX → systemowe min/max zachowanie
                    #    WM_NCCALCSIZE=0 gwarantuje że NC area ma 0px —
                    #    style mówią DWM "to okno MA frame" ale NCCALCSIZE
                    #    mówi "frame ma 0 pikseli" → shadow bez artefaktów.
                    GWL_STYLE = -16
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    style |= 0x00040000  # WS_THICKFRAME
                    style |= 0x00C00000  # WS_CAPTION
                    style |= 0x00020000  # WS_MINIMIZEBOX
                    style |= 0x00010000  # WS_MAXIMIZEBOX
                # 2. Wymuszenie renderowania NC przez DWM (shadow)
                    # DWMWA_NCRENDERING_POLICY=2, DWMNCRP_ENABLED=2
                    nc_policy = ctypes.c_int(2)
                    dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(nc_policy), 4)

                    # 3. DwmExtendFrameIntoClientArea: 1px top — DWM frame strip
                    #    dla Aero Snap preview i systemowego shadow anchoring.
                    class MARGINS(ctypes.Structure):
                        _fields_ = [('left', ctypes.c_int), ('right', ctypes.c_int),
                                     ('top',  ctypes.c_int), ('bottom', ctypes.c_int)]
                    margins = MARGINS(0, 0, 1, 0)
                    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

                    # 4. Flush — DWM musi przetworzyć nowe style
                    user32.SetWindowPos(
                        hwnd, None, 0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0004 | 0x0020  # NOSIZE|NOMOVE|NOZORDER|FRAMECHANGED
                    )
                if hwnd:
                    # ALL windows (root & popups): DWMWCP_DONOTROUND
                    # Removes Windows 11 rounded corners
                    corner_pref = ctypes.c_int(1)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), 4)

                    # Remove Windows 11 1px accent border completely (DWMWA_BORDER_COLOR = 34, DWMWA_COLOR_NONE = 0xFFFFFFFE)
                    border_color = ctypes.c_uint(0xFFFFFFFE)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), 4)
            except Exception:
                pass
        if hasattr(self, '_grips'):
            for grip in self._grips:
                grip.raise_()

    def _refresh_max_state(self):
        is_max = self.isMaximized()

        # Szukamy paska pod obiema nazwami (główne okno: _title_bar, dialogi: _tb)
        title_bar = getattr(self, '_title_bar', getattr(self, '_tb', None))
        if title_bar and hasattr(title_bar, 'update_maximize_icon'):
            title_bar.update_maximize_icon(is_max)



    def _setup_grips(self):
        self._grips = []
        edges = [
            Qt.BottomEdge, Qt.LeftEdge, Qt.RightEdge, 
            Qt.BottomEdge | Qt.LeftEdge, 
            Qt.BottomEdge | Qt.RightEdge
        ]
        for edge in edges:
            grip = ResizeGrip(self, edge)
            self._grips.append(grip)
            grip.raise_() # <-- ZMIANA: Podnosimy Z-index tylko raz przy tworzeniu

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_grips()

    def _update_grips(self):
        if not hasattr(self, '_grips'): return

        is_max = self.isMaximized()

        b = 6 
        w, h = self.width(), self.height()

        for grip in self._grips:
            if is_max:
                if not grip.isHidden(): grip.hide()
                continue
            else:
                if grip.isHidden(): grip.show()

            if grip.edge == Qt.BottomEdge: grip.setGeometry(b, h - b, w - 2*b, b)
            elif grip.edge == Qt.LeftEdge: grip.setGeometry(0, 0, b, h - b)
            elif grip.edge == Qt.RightEdge: grip.setGeometry(w - b, 0, b, h - b)
            elif grip.edge == (Qt.BottomEdge | Qt.LeftEdge): grip.setGeometry(0, h - b, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.RightEdge): grip.setGeometry(w - b, h - b, b, b)

    # ── Windows WM_NCHITTEST ──────────────────────────────────────────────────
    def nativeEvent(self, eventType, message):
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False):
            return super().nativeEvent(eventType, message)

        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False) or eventType != b"windows_generic_MSG":
            return super().nativeEvent(eventType, message)

        import ctypes
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))

        # ── WM_NCCALCSIZE (0x0083) ────────────────────────────────────────────
        # Returning 0 with wParam=True removes the entire native NC area so
        # Windows draws nothing there — our custom title bar owns that space.
        # When maximized, Windows adds a hidden "maximized border" (SM_CXFRAME +
        # SM_CXPADDEDBORDER) that would otherwise push the client area inward.
        # We compensate by shrinking the rect on all four sides. Left/right/bottom
        # corrections prevent edge clipping on multi-monitor setups.
        if msg.message == 0x0083:  # WM_NCCALCSIZE
            if msg.wParam and self.isMaximized():
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                try:
                    dpi = user32.GetDpiForWindow(hwnd) or 96
                    border = (user32.GetSystemMetricsForDpi(32, dpi) +
                              user32.GetSystemMetricsForDpi(92, dpi))
                except Exception:
                    border = user32.GetSystemMetrics(32) + user32.GetSystemMetrics(92)
                params = ctypes.cast(msg.lParam, ctypes.POINTER(wintypes.RECT))
                params[0].left   += border
                params[0].top    += border
                params[0].right  -= border
                params[0].bottom -= border
            return True, (0x0300 if msg.wParam else 0)  # WVR_REDRAW

        # ── WM_ENTERSIZEMOVE (0x0231) ─────────────────────────────────────────
        # Fires at the start of every drag or resize. Forces DWM to flush our
        # WM_NCCALCSIZE=0 result before NC repaint — eliminates white flash.
        if msg.message == 0x0231:  # WM_ENTERSIZEMOVE
            hwnd = int(self.winId())
            if hwnd:
                # SWP_FRAMECHANGED(0x20)|SWP_NOZORDER(0x04)|SWP_NOMOVE(0x02)|SWP_NOSIZE(0x01)
                ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0027)
            return super().nativeEvent(eventType, message)  # don't consume

        # ── WM_NCACTIVATE (0x0086) ────────────────────────────────────────────
        # The default handler repaints the NC area on activate/deactivate,
        # which produces a white flash at the top of the window.
        # Passing wParam=True and lParam=-1 tells Windows to suppress NC
        # repainting entirely and keeps our custom title bar pixel-perfect.
        if msg.message == 0x0086:  # WM_NCACTIVATE
            hwnd = int(self.winId())
            ctypes.windll.user32.DefWindowProcW(
                hwnd,
                0x0086,          # WM_NCACTIVATE
                msg.wParam,      # keep active/inactive state
                ctypes.c_long(-1)  # lParam = -1 → skip NC repaint
            )
            return True, 1

        # ── WM_MOUSEACTIVATE (0x0021) ─────────────────────────────────────────
        # When the window is clicked to regain focus, Windows sends WM_MOUSEACTIVATE
        # before WM_NCHITTEST. Returning MA_ACTIVATE (1) lets Windows correctly
        # re-register the HTCAPTION tracking state, fixing drag loss after focus-out.
        if msg.message == 0x0021:  # WM_MOUSEACTIVATE
            return True, 1  # MA_ACTIVATE — activate and pass click through normally

        # ── WM_NCHITTEST (0x0084) ─────────────────────────────────────────────
        if msg.message == 0x0084:  # WM_NCHITTEST
            x = msg.lParam & 0xFFFF
            if x & 0x8000: x -= 0x10000
            y = (msg.lParam >> 16) & 0xFFFF
            if y & 0x8000: y -= 0x10000

            # HighDPI FIX: x and y from WM_NCHITTEST are physical pixels!
            # mapFromGlobal expects logical pixels in PySide6.
            ratio = self.devicePixelRatioF()
            logical_x = x / ratio
            logical_y = y / ratio

            from PySide6.QtCore import QPointF
            pos = self.mapFromGlobal(QPointF(logical_x, logical_y).toPoint())
            w, h = self.width(), self.height()
            b = self._RESIZE_BORDER

            if not self.isMaximized():
                lx, rx = pos.x() < b, pos.x() > w - b
                by = pos.y() > h - b
                if by and lx: return True, 16  # HTBOTTOMLEFT
                if by and rx: return True, 17  # HTBOTTOMRIGHT
                if lx:        return True, 10  # HTLEFT
                if rx:        return True, 11  # HTRIGHT
                if by:        return True, 15  # HTBOTTOM

            _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
            tb_height = (_tb.height() if _tb else 32)
            if 0 <= pos.y() < tb_height:
                child = self.childAt(pos)

                if not child or not child.inherits("QPushButton"):
                    return True, 1  # HTCLIENT

            return True, 1  # HTCLIENT

        # ── WM_NCLBUTTONDBLCLK (0x00A3) ───────────────────────────────────────
        # Double-click na HTCAPTION: delegujemy do _toggle_maximize().
        if msg.message == 0x00A3:  # WM_NCLBUTTONDBLCLK
            _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
            if _tb and hasattr(_tb, '_toggle_maximize'):
                _tb._toggle_maximize()
            return True, 0

        return super().nativeEvent(eventType, message)
