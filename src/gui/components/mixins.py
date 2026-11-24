#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: mixins.py
ROLE: GUI Component (Red Zone)
DESCRIPTION:
Cross-platform frameless window mixin providing 1:1 root window behavior across
BadWordsGUI and SettingsDialog:
- Windows: zero-artifact WM_NCCALCSIZE (live IsZoomed -> exact rcWork), WM_NCPAINT
  suppression, dark WM_ERASEBKGND brush, ScreenToClient WM_NCHITTEST (8 edges when
  windowed, 100% disabled when maximized for Fitts's Law corner X & top-edge rip),
  Windows 11 Snap Layouts (HTMAXBUTTON), and Win32 WINDOWPLACEMENT restore/rip.
- Linux / macOS: 8 ResizeGrips (strictly hidden when maximized), 1px mouse-transparent
  window border overlay (hidden when maximized, zero shadow margin), and pre-unmaximize
  70% x 70% rip geometry before startSystemMove() so WMs never revert to stale sizes.
"""

from PySide6.QtWidgets import QWidget, QMainWindow, QDialog, QAbstractButton, QLineEdit
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QTimer, QEvent
from PySide6.QtGui import QGuiApplication, QCursor, QColor, QPainter, QPen

_HAS_QFRAMELESS = False
_BaseMainWindow = QMainWindow
_BaseDialog = QDialog

# Win32 Hit-Test Constants
HTCLIENT = 1
HTCAPTION = 2
HTMAXBUTTON = 9
HTLEFT = 10
HTRIGHT = 11
HTTOP = 12
HTTOPLEFT = 13
HTTOPRIGHT = 14
HTBOTTOM = 15
HTBOTTOMLEFT = 16
HTBOTTOMRIGHT = 17

# Subtle 1px outer frame border for windowed root windows (slightly darker than #191919 / #1c1c1c UI)
_WINDOW_BORDER_COLOR = "#101010"

_WIN32_APIS = None
_DARK_BG_BRUSH = None


def _get_win32_apis():
    """Lazily initializes and caches properly typed 64-bit Win32/DWM/GDI ctypes bindings."""
    global _WIN32_APIS
    if _WIN32_APIS is not None:
        return _WIN32_APIS
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    dwmapi = ctypes.windll.dwmapi

    HMONITOR = getattr(wintypes, "HMONITOR", ctypes.c_void_p)
    HGDIOBJ = getattr(wintypes, "HGDIOBJ", ctypes.c_void_p)
    HRESULT = getattr(wintypes, "HRESULT", ctypes.c_long)

    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.IsZoomed.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = HMONITOR
    user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user32.MonitorFromPoint.restype = HMONITOR
    user32.GetMonitorInfoW.argtypes = [HMONITOR, ctypes.c_void_p]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClientRect.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.ScreenToClient.restype = wintypes.BOOL
    user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
    user32.FillRect.restype = ctypes.c_int
    user32.GetWindowPlacement.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.GetWindowPlacement.restype = wintypes.BOOL
    user32.SetWindowPlacement.argtypes = [wintypes.HWND, ctypes.c_void_p]
    user32.SetWindowPlacement.restype = wintypes.BOOL
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = wintypes.LONG
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.SetWindowLongW.restype = wintypes.LONG
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    if hasattr(user32, "GetDpiForWindow"):
        user32.GetDpiForWindow.argtypes = [wintypes.HWND]
        user32.GetDpiForWindow.restype = wintypes.UINT
    if hasattr(user32, "GetSystemMetricsForDpi"):
        user32.GetSystemMetricsForDpi.argtypes = [ctypes.c_int, wintypes.UINT]
        user32.GetSystemMetricsForDpi.restype = ctypes.c_int
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetSystemMenu.argtypes = [wintypes.HWND, wintypes.BOOL]
    user32.GetSystemMenu.restype = wintypes.HMENU
    user32.EnableMenuItem.argtypes = [wintypes.HMENU, wintypes.UINT, wintypes.UINT]
    user32.EnableMenuItem.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        wintypes.HMENU, wintypes.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, ctypes.c_void_p
    ]
    user32.TrackPopupMenu.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL

    gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
    gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
    gdi32.DeleteObject.argtypes = [HGDIOBJ]
    gdi32.DeleteObject.restype = wintypes.BOOL

    dwmapi.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmSetWindowAttribute.restype = HRESULT
    dwmapi.DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.c_void_p]
    dwmapi.DwmExtendFrameIntoClientArea.restype = HRESULT

    _WIN32_APIS = (user32, gdi32, dwmapi)
    return _WIN32_APIS


def _get_dark_bg_brush():
    """Returns a cached Win32 HBRUSH matching config.BG_COLOR (#1c1c1c) for WM_ERASEBKGND."""
    global _DARK_BG_BRUSH
    if _DARK_BG_BRUSH is None:
        _, gdi32, _ = _get_win32_apis()
        import config as _cfg
        col = QColor(_cfg.BG_COLOR)
        colorref = (col.blue() << 16) | (col.green() << 8) | col.red()
        _DARK_BG_BRUSH = gdi32.CreateSolidBrush(colorref)
    return _DARK_BG_BRUSH


def compute_win_nccalcsize_rect(
    rect: tuple[int, int, int, int],
    is_zoomed: bool,
    is_fullscreen: bool,
    work_rect: tuple[int, int, int, int] | None = None,
    monitor_rect: tuple[int, int, int, int] | None = None,
    fallback_bx: int = 8,
    fallback_by: int = 8,
) -> tuple[int, int, int, int]:
    """
    Pure Win32 WM_NCCALCSIZE client-rect calculator.
    # INVARIANT:
    # - When NOT maximized (is_zoomed=False) or fullscreen: leave rect 100% untouched
    #   (0px non-client area -> zero black bar, zero native caption buttons, zero clipping).
    # - When maximized (live Win32 IsZoomed=True, never stale Qt isMaximized()): snap client
    #   rect directly to the active monitor's rcWork (minus 1px bottom only for auto-hide taskbar).
    """
    left, top, right, bottom = rect
    if is_fullscreen or not is_zoomed:
        return (left, top, right, bottom)

    if work_rect is not None:
        wl, wt, wr, wb = work_rect
        if wr > wl and wb > wt:
            if monitor_rect is not None and work_rect == monitor_rect:
                # Auto-hide taskbar edge safeguard (1px) so mouse at bottom edge still raises taskbar
                wb = max(wt + 1, wb - 1)
            return (wl, wt, wr, wb)

    # Fallback if GetMonitorInfoW is unavailable
    bx = max(0, int(fallback_bx))
    by = max(0, int(fallback_by))
    return (left + bx, top + by, right - bx, bottom - by)


def compute_win_nchittest(
    rel_x: int,
    rel_y: int,
    win_w: int,
    win_h: int,
    border_px: int,
    is_maximized: bool,
    is_fullscreen: bool,
    titlebar_height: int,
    is_on_max_btn: bool = False,
    is_on_interactive_child: bool = False,
    top_border_px: int = 4,
) -> int:
    """
    Pure cross-platform hit-test classifier returning Win32 HT* constants.
    # INVARIANT:
    # - When maximized or fullscreen: ALL 8 resize edges/corners are 100% disabled so
    #   top-right corner (win_w-1, 0) hits close button (HTCLIENT) and top edge (y=0)
    #   hits HTCAPTION for effortless drag-detach ('ripping').
    # - When windowed: supports all 8 resize edges/corners with a thin top strip (4px,
    #   3px over titlebar buttons) so top/corner resizing never blocks clicking buttons.
    """
    if not is_maximized and not is_fullscreen and win_w > 0 and win_h > 0:
        b = max(2, int(border_px))
        bt = max(2, int(top_border_px))
        if is_on_interactive_child or is_on_max_btn:
            bt = min(bt, 3)

        lx = rel_x < b
        rx = rel_x >= win_w - b
        ty = rel_y < bt
        by = rel_y >= win_h - b

        if ty and lx:
            return HTTOPLEFT
        if ty and rx:
            return HTTOPRIGHT
        if by and lx:
            return HTBOTTOMLEFT
        if by and rx:
            return HTBOTTOMRIGHT
        if lx:
            return HTLEFT
        if rx:
            return HTRIGHT
        if ty:
            return HTTOP
        if by:
            return HTBOTTOM

    if 0 <= rel_y < max(0, int(titlebar_height)):
        if is_on_max_btn:
            return HTMAXBUTTON
        if is_on_interactive_child:
            return HTCLIENT
        return HTCAPTION

    return HTCLIENT


def compute_default_normal_geometry(
    screen_geo: QRect,
    ratio: float = 0.70,
    min_w: int = 640,
    min_h: int = 460,
) -> QRect:
    """
    Computes centered normal (non-maximized) geometry inside *screen_geo*
    at *ratio* (default 70% width x 70% height), clamped cleanly to screen bounds.
    """
    if not screen_geo or not screen_geo.isValid():
        return QRect(100, 100, max(min_w, 960), max(min_h, 640))

    avail_w = max(1, screen_geo.width())
    avail_h = max(1, screen_geo.height())
    eff_min_w = min(min_w, avail_w)
    eff_min_h = min(min_h, avail_h)

    w = max(eff_min_w, min(avail_w, int(round(avail_w * ratio))))
    h = max(eff_min_h, min(avail_h, int(round(avail_h * ratio))))
    x = screen_geo.x() + (avail_w - w) // 2
    y = screen_geo.y() + (avail_h - h) // 2
    return QRect(x, y, w, h)


def compute_proportional_rip_rect(
    cursor_x: int,
    cursor_y: int,
    click_x: int,
    click_y: int,
    maximized_w: int,
    target_w: int,
    target_h: int,
    screen_geo: QRect | None,
) -> QRect:
    """
    Computes target window geometry when ripping out of maximized state so the cursor
    remains at the exact same proportional horizontal fraction (0.0..1.0) on the
    restored titlebar, clamped safely inside *screen_geo*.
    """
    tw = max(1, int(target_w))
    th = max(1, int(target_h))
    ratio_x = max(0.0, min(1.0, float(click_x) / float(max(1, int(maximized_w)))))
    nx = int(round(cursor_x - tw * ratio_x))
    ny = int(round(cursor_y - click_y))

    if screen_geo and screen_geo.isValid():
        avail_w = max(1, screen_geo.width())
        avail_h = max(1, screen_geo.height())
        tw = min(tw, avail_w)
        th = min(th, avail_h)
        nx = max(screen_geo.left(), min(nx, screen_geo.left() + avail_w - tw))
        ny = max(screen_geo.top(), min(ny, screen_geo.top() + avail_h - th))

    return QRect(nx, ny, tw, th)


class _WindowBorderOverlay(QWidget):
    """
    1px mouse-transparent outer border drawn on top of windowed root windows
    (hidden when maximized/fullscreen) so overlapping windows separate cleanly
    without shrinking layout margins or blocking Fitts's Law corner clicks.
    """

    def __init__(self, parent, color: str = _WINDOW_BORDER_COLOR):
        super().__init__(parent)
        self._border_color = QColor(color)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.hide()

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(self._border_color, 1))
        painter.drawRect(0, 0, w - 1, h - 1)


class ResizeGrip(QWidget):
    """Transparent edge/corner hit zone triggering native window resizing on Unix."""

    def __init__(self, parent, edge):
        super().__init__(parent)
        self.edge = edge
        self.setStyleSheet("background: transparent;")

        if self.edge in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        elif self.edge in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif self.edge in (Qt.TopEdge | Qt.LeftEdge, Qt.BottomEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.edge in (Qt.TopEdge | Qt.RightEdge, Qt.BottomEdge | Qt.LeftEdge):
            self.setCursor(Qt.SizeBDiagCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            win = self.window()
            if hasattr(win, '_is_effectively_maximized') and win._is_effectively_maximized():
                event.ignore()
                return
            if hasattr(win, 'windowHandle') and win.windowHandle():
                try:
                    win.windowHandle().startSystemResize(self.edge)
                except Exception as e:
                    import osdoc
                    osdoc.log_info(f"startSystemResize error: {e}")
            event.accept()


class FramelessWindowMixin:
    """
    Mixin that turns any root QMainWindow (BadWordsGUI, SettingsDialog) or popup QDialog
    into a clean cross-platform frameless window with identical titlebar & restore rules.
    """

    _RESIZE_BORDER = 5      # px - left/right/bottom resize hit zone
    _TOP_RESIZE_BORDER = 4  # px - thin top resize strip (3px over buttons)

    def frameless_init(self, is_popup: bool = False, use_linux_csd_shadow: bool = False):
        """Call once, right after super().__init__()."""
        import platform
        self._is_win = platform.system() == "Windows"
        self._is_mac = platform.system() == "Darwin"
        self._is_wayland = QGuiApplication.platformName() == "wayland"
        self._is_popup = bool(is_popup)
        self._is_root = not self._is_popup
        # Root windows use clean opaque framing + 1px border overlay (no custom software shadow padding)
        self._use_linux_csd_shadow = False
        self._normal_ratio = 0.70
        self._normal_min_w = 640
        self._normal_min_h = 460
        self._default_normal_size = None
        self._always_restore_default_size = False
        self._last_normal_geo = None
        self._pre_maximize_geometry = None
        self._last_normal_win_rect = None
        self._pre_maximize_win_rect = None
        self._restore_via_button = False
        self._restoring_from_max = False
        self._was_maximized = False
        self._dark_brush = None
        self._border_overlay = None

        if self._is_win:
            if self._is_root:
                # Root window: FramelessWindowHint removes native NC chrome; native DWM shadow,
                # animations, Snap Layouts, and 8-edge resize are wired in showEvent + nativeEvent.
                self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            else:
                # Opaque frameless popup/dialog: solid 1px border + native DWM shadow in showEvent.
                self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)
        elif self._is_mac and self._is_root:
            # macOS root window: native titlebar with traffic lights, native shadow, and fullscreen button.
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinMaxButtonsHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowFullscreenButtonHint
            )
        elif self._is_root:
            # INVARIANT: Linux root windows must be opaque Qt.Window (never Qt.Dialog / Qt.Tool)
            # with zero custom shadow padding so maximize, Aero Snap, Alt+Tab, and native X11 shadows work 1:1.
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        else:
            # Linux and macOS popups/dialogs: opaque frameless dialogs (zero custom shadow padding)
            self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog)

        if self._is_popup:
            self._sync_popup_always_on_top()

        if self._is_root and not self._is_mac:
            self._border_overlay = _WindowBorderOverlay(self, _WINDOW_BORDER_COLOR)

        if self._is_root and not self._is_win and not self._is_mac:
            self._setup_grips()

    def _get_root_frame(self):
        """Return the topmost styled QFrame."""
        return getattr(self, 'inner_frame', getattr(self, '_root_frame', None))

    def _get_reference_main_window(self):
        """Returns parent or stored main window reference, or active BadWordsGUI."""
        ref = getattr(self, '_main_window', None) or self.parent()
        if ref is not None:
            return ref
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for w in app.topLevelWidgets():
                if w is not self and w.__class__.__name__ == "BadWordsGUI":
                    return w
        return None

    def _sync_popup_always_on_top(self):
        """Inherits Always on Top from the main/parent window without hardcoding it ON."""
        ref = self._get_reference_main_window()
        is_top = False
        if ref is not None:
            is_top = bool(
                getattr(ref, '_always_on_top_active', False)
                or (ref.windowFlags() & Qt.WindowStaysOnTopHint)
            )
        cur = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        if cur != is_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, is_top)

    def _is_effectively_maximized(self) -> bool:
        """
        True whenever the window is maximized, fullscreen, or filling the screen work area.
        # INVARIANT: Top/corner resize grips, border overlay, and Win32 edge hit-testing MUST
        # be completely disabled whenever maximized so Fitts's Law corner X & top-edge rip work.
        """
        if self.isMaximized() or self.isFullScreen():
            return True
        if getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
            try:
                user32, _, _ = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd and user32.IsZoomed(hwnd):
                    return True
            except Exception:
                pass
        elif getattr(self, '_is_root', False) and not getattr(self, '_is_mac', False) and self.isVisible():
            try:
                geo = self.frameGeometry()
                scr = QGuiApplication.screenAt(geo.center()) or self.screen() or QGuiApplication.primaryScreen()
                if scr is not None:
                    avail = scr.availableGeometry()
                    if (
                        avail.isValid()
                        and avail.width() > 0
                        and avail.height() > 0
                        and geo.width() >= avail.width() - 2
                        and geo.height() >= avail.height() - 2
                        and abs(geo.left() - avail.left()) <= 2
                        and abs(geo.top() - avail.top()) <= 2
                    ):
                        return True
            except Exception:
                pass
        return False

    def init_normal_geometry(
        self,
        saved_w: int = None,
        saved_h: int = None,
        screen=None,
        ratio: float = 0.70,
        min_w: int = 640,
        min_h: int = 460,
        apply_geometry: bool = True,
        always_restore_default: bool = False,
    ) -> QRect:
        """
        Initializes normal (non-maximized) geometry on *screen*.
        - Main window (always_restore_default=False): default 70% x 70%; ripping ALWAYS uses
          70% x 70%, while btn_max restores exact pre-maximize geometry.
        - Settings window (always_restore_default=True): user may resize manually by edges,
          but exiting maximize (both btn_max AND ripping) ALWAYS returns to saved_w x saved_h.
        """
        self._normal_ratio = float(ratio)
        self._normal_min_w = int(min_w)
        self._normal_min_h = int(min_h)
        self._always_restore_default_size = bool(always_restore_default)
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        sg = screen.availableGeometry() if screen else QRect(100, 100, 1280, 720)
        if (
            isinstance(saved_w, (int, float))
            and isinstance(saved_h, (int, float))
            and saved_w >= min_w
            and saved_h >= min_h
        ):
            w = max(min(min_w, sg.width()), min(int(saved_w), sg.width()))
            h = max(min(min_h, sg.height()), min(int(saved_h), sg.height()))
            x = sg.x() + (sg.width() - w) // 2
            y = sg.y() + (sg.height() - h) // 2
            geo = QRect(x, y, w, h)
        else:
            geo = compute_default_normal_geometry(sg, ratio=ratio, min_w=min_w, min_h=min_h)

        self._default_normal_size = QSize(geo.width(), geo.height())

        if apply_geometry:
            self.setGeometry(geo)
        return geo

    def _compute_rip_geometry(self, screen=None) -> QRect:
        """Returns 70% x 70% for MainWindow, or original small default size for SettingsDialog."""
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or self.screen() or QGuiApplication.primaryScreen()
        sg = screen.availableGeometry() if screen else QRect(100, 100, 1280, 720)
        if getattr(self, '_always_restore_default_size', False):
            def_sz = getattr(self, '_default_normal_size', None)
            if def_sz and def_sz.isValid() and def_sz.width() > 0 and def_sz.height() > 0:
                w = max(1, min(def_sz.width(), sg.width()))
                h = max(1, min(def_sz.height(), sg.height()))
                x = sg.x() + (sg.width() - w) // 2
                y = sg.y() + (sg.height() - h) // 2
                return QRect(x, y, w, h)
        return compute_default_normal_geometry(
            sg,
            ratio=getattr(self, '_normal_ratio', 0.70),
            min_w=getattr(self, '_normal_min_w', 640),
            min_h=getattr(self, '_normal_min_h', 460),
        )

    def _compute_restore_target_geometry(self, via_button: bool = False) -> QRect:
        """
        Computes exact target geometry when leaving maximized state:
        - Settings (always_restore_default=True): ALWAYS returns to original small default size.
        - MainWindow + Restore button (via_button=True): restores EXACT pre-maximize geometry
          (_pre_maximize_geometry), clamped to screen (falls back to 70% x 70% if never windowed).
        - MainWindow + Rip / double-click (via_button=False): ALWAYS 70% x 70%.
        """
        scr = self.screen() or QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        sg = scr.availableGeometry() if scr else QRect(100, 100, 1280, 720)

        if getattr(self, '_always_restore_default_size', False):
            return self._compute_rip_geometry(screen=scr)

        if via_button:
            pre_geo = getattr(self, '_pre_maximize_geometry', None)
            if pre_geo and pre_geo.isValid() and pre_geo.width() > 0 and pre_geo.height() > 0:
                target_scr = QGuiApplication.screenAt(pre_geo.center()) or scr
                tsg = target_scr.availableGeometry() if target_scr else sg
                w = min(pre_geo.width(), tsg.width())
                h = min(pre_geo.height(), tsg.height())
                x = max(tsg.left(), min(pre_geo.x(), tsg.right() - w + 1))
                y = max(tsg.top(), min(pre_geo.y(), tsg.bottom() - h + 1))
                return QRect(x, y, w, h)

        return self._compute_rip_geometry(screen=scr)

    def _snapshot_pre_maximize_geometry(self):
        """Captures the exact normal geometry right before entering maximized state."""
        if not getattr(self, '_is_root', False):
            return
        if getattr(self, '_last_normal_geo', None) is not None:
            self._pre_maximize_geometry = QRect(self._last_normal_geo)
        if getattr(self, '_is_win', False) and getattr(self, '_last_normal_win_rect', None) is not None:
            self._pre_maximize_win_rect = tuple(self._last_normal_win_rect)

    def _get_win32_primary_work_offset(self, user32) -> tuple[int, int]:
        """Returns primary monitor work-area origin (rcWork.left, rcWork.top) for WINDOWPLACEMENT workspace conversion."""
        try:
            import ctypes
            from ctypes import wintypes

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD),
                ]

            hprim = user32.MonitorFromPoint(wintypes.POINT(0, 0), 1)  # MONITOR_DEFAULTTOPRIMARY
            if hprim:
                pmi = MONITORINFO()
                pmi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(hprim, ctypes.byref(pmi)):
                    return (int(pmi.rcWork.left), int(pmi.rcWork.top))
        except Exception:
            pass
        return (0, 0)

    def _record_normal_geometry(self):
        """Tracks the window's latest non-maximized geometry (including Aero-snapped half-screen) for btn_max restore."""
        if (
            not getattr(self, '_is_root', False)
            or not self.isVisible()
            or self.isMinimized()
            or self._is_effectively_maximized()
            or getattr(self, '_restoring_from_max', False)
        ):
            return
        geo = QRect(self.geometry())
        if not geo.isValid() or geo.width() <= 0 or geo.height() <= 0:
            return
        scr = QGuiApplication.screenAt(geo.center()) or self.screen() or QGuiApplication.primaryScreen()
        sg = scr.availableGeometry() if scr else None
        if sg and geo.width() >= int(sg.width() * 0.98) and geo.height() >= int(sg.height() * 0.98):
            return
        self._last_normal_geo = geo

        if getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
            try:
                import ctypes
                from ctypes import wintypes
                user32, _, _ = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd and not user32.IsIconic(hwnd) and not user32.IsZoomed(hwnd):
                    # Always read GetWindowRect (NOT rcNormalPosition, which Windows leaves frozen
                    # at the old pre-snap rect when Aero-snapping to left/right half of the screen).
                    rc = wintypes.RECT()
                    if user32.GetWindowRect(hwnd, ctypes.byref(rc)) and rc.right > rc.left and rc.bottom > rc.top:
                        prim_off_x, prim_off_y = self._get_win32_primary_work_offset(user32)
                        self._last_normal_win_rect = (
                            int(rc.left) - prim_off_x,
                            int(rc.top) - prim_off_y,
                            int(rc.right) - prim_off_x,
                            int(rc.bottom) - prim_off_y,
                        )
            except Exception:
                pass

    def _sync_win_normal_placement(self, use_button_restore: bool = False):
        """
        Updates Win32 WINDOWPLACEMENT.rcNormalPosition ONLY while maximized (IsZoomed=True),
        so calling SetWindowPlacement NEVER causes a normal window to jump before maximizing.
        - Main window: use_button_restore=False sets 70% x 70% (Aero drag-detach);
          use_button_restore=True restores exact _pre_maximize_win_rect.
        - Settings window (_always_restore_default_size=True): ALWAYS sets small default size.
        """
        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False):
            return
        if not self.testAttribute(Qt.WA_WState_Created):
            return
        try:
            import ctypes
            from ctypes import wintypes

            user32, _, _ = _get_win32_apis()
            hwnd = int(self.winId())
            if not hwnd or not user32.IsZoomed(hwnd):
                return

            class WINDOWPLACEMENT(ctypes.Structure):
                _fields_ = [
                    ('length', wintypes.UINT),
                    ('flags', wintypes.UINT),
                    ('showCmd', wintypes.UINT),
                    ('ptMinPosition', wintypes.POINT),
                    ('ptMaxPosition', wintypes.POINT),
                    ('rcNormalPosition', wintypes.RECT),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD),
                ]

            wp = WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(WINDOWPLACEMENT)
            if not user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
                return

            always_default = bool(getattr(self, '_always_restore_default_size', False))
            if (
                not always_default
                and use_button_restore
                and getattr(self, '_pre_maximize_win_rect', None) is not None
            ):
                l, t, r, b = self._pre_maximize_win_rect
                wp.rcNormalPosition.left = l
                wp.rcNormalPosition.top = t
                wp.rcNormalPosition.right = r
                wp.rcNormalPosition.bottom = b
                user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
                return

            # Compute target size in native Win32 workspace coordinates (zero DPI drift!)
            hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            if not hmon:
                return
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                return

            prim_off_x, prim_off_y = self._get_win32_primary_work_offset(user32)

            work = mi.rcWork
            avail_w = max(1, work.right - work.left)
            avail_h = max(1, work.bottom - work.top)
            def_sz = getattr(self, '_default_normal_size', None)
            if always_default and def_sz and def_sz.isValid() and def_sz.width() > 0 and def_sz.height() > 0:
                try:
                    dpi = user32.GetDpiForWindow(hwnd) if hasattr(user32, "GetDpiForWindow") else 0
                    scale = (float(dpi) / 96.0) if dpi else max(1.0, float(self.devicePixelRatioF()))
                except Exception:
                    scale = max(1.0, float(self.devicePixelRatioF()))
                phys_w = max(1, min(avail_w, int(round(def_sz.width() * scale))))
                phys_h = max(1, min(avail_h, int(round(def_sz.height() * scale))))
            else:
                ratio = getattr(self, '_normal_ratio', 0.70)
                phys_w = max(1, int(round(avail_w * ratio)))
                phys_h = max(1, int(round(avail_h * ratio)))
            left = (work.left - prim_off_x) + (avail_w - phys_w) // 2
            top = (work.top - prim_off_y) + (avail_h - phys_h) // 2

            wp.rcNormalPosition.left = left
            wp.rcNormalPosition.top = top
            wp.rcNormalPosition.right = left + phys_w
            wp.rcNormalPosition.bottom = top + phys_h
            user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
        except Exception:
            pass

    def _restore_after_unmaximize(self, via_button: bool = False):
        """Enforces exact post-maximize geometry on Unix (btn_max -> pre-max rect; otherwise -> 70% x 70%)."""
        if not getattr(self, '_is_root', False):
            return
        if self._is_effectively_maximized():
            return

        target_geo = self._compute_restore_target_geometry(via_button=via_button)
        if not target_geo or not target_geo.isValid():
            return

        self._restoring_from_max = True
        try:
            if via_button:
                self.setGeometry(target_geo)
                # Re-assert after WM async settle on X11/Wayland
                def _reassert():
                    if not self._is_effectively_maximized():
                        self.setGeometry(target_geo)
                    self._restoring_from_max = False
                QTimer.singleShot(35, _reassert)
            else:
                self.resize(target_geo.width(), target_geo.height())
                scr = self.screen() or QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
                sg = scr.availableGeometry() if scr else None
                if sg and sg.isValid():
                    cur_x, cur_y = self.x(), self.y()
                    near_origin = abs(cur_x - sg.x()) <= 8 and abs(cur_y - sg.y()) <= 8
                    if near_origin:
                        self.move(target_geo.x(), target_geo.y())
                    else:
                        x = max(sg.left(), min(cur_x, sg.right() - target_geo.width() + 1))
                        y = max(sg.top(), min(cur_y, sg.bottom() - target_geo.height() + 1))
                        self.move(x, y)
                QTimer.singleShot(60, lambda: setattr(self, '_restoring_from_max', False))
        except Exception:
            self._restoring_from_max = False
        finally:
            self._restore_via_button = False

    def _update_border_overlay(self):
        """Shows crisp 1px outer border when visible & windowed; hides it when maximized/fullscreen."""
        overlay = getattr(self, '_border_overlay', None)
        if overlay is None:
            return
        if not self.isVisible() or self._is_effectively_maximized():
            if not overlay.isHidden():
                overlay.hide()
            return
        overlay.setGeometry(0, 0, self.width(), self.height())
        if overlay.isHidden():
            overlay.show()
        overlay.raise_()

    def _enforce_win_dwm_attributes(self, hwnd: int, include_extend: bool = True):
        """
        Enforces sharp 90-degree corners (DWMWCP_DONOTROUND), dark DWM theme, and
        native OS drop shadow without light Win11 border across state/style changes.
        """
        if not hwnd or not getattr(self, '_is_win', False):
            return
        try:
            import ctypes
            _, _, dwmapi = _get_win32_apis()

            dark_val = ctypes.c_int(1)
            if dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_val), 4) != 0:
                dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_val), 4)

            if include_extend:
                nc_policy = ctypes.c_int(2)
                dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(nc_policy), 4)

                class MARGINS(ctypes.Structure):
                    _fields_ = [
                        ('left', ctypes.c_int),
                        ('right', ctypes.c_int),
                        ('top', ctypes.c_int),
                        ('bottom', ctypes.c_int),
                    ]
                margins = MARGINS(0, 0, 0, 1)
                dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

            # INVARIANT: Sharp 90-degree corners ALWAYS on Windows 11 (DWMWCP_DONOTROUND = 1)
            # and suppress Win11 default light/gray DWM outline (DWMWA_COLOR_NONE = 0xFFFFFFFE).
            corner_pref = ctypes.c_uint(1)
            dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), 4)
            border_color = ctypes.c_uint(0xFFFFFFFE)
            dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), 4)
        except Exception:
            pass

    def _verify_win_button_restore(self):
        """Ensures btn_max unmaximize on Windows lands on exact _pre_maximize_win_rect (e.g. half-screen)."""
        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False):
            return
        if getattr(self, '_always_restore_default_size', False):
            return
        if self.isMinimized() or self.isFullScreen() or self._is_effectively_maximized():
            return
        pre = getattr(self, '_pre_maximize_win_rect', None)
        if not pre or not self.testAttribute(Qt.WA_WState_Created):
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32, _, _ = _get_win32_apis()
            hwnd = int(self.winId())
            if not hwnd or user32.IsZoomed(hwnd) or user32.IsIconic(hwnd):
                return
            prim_off_x, prim_off_y = self._get_win32_primary_work_offset(user32)
            l, t, r, b = pre
            tl = int(l) + prim_off_x
            tt = int(t) + prim_off_y
            tw = max(1, int(r) - int(l))
            th = max(1, int(b) - int(t))

            rc = wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                cw = int(rc.right) - int(rc.left)
                ch = int(rc.bottom) - int(rc.top)
                if (
                    abs(int(rc.left) - tl) <= 2
                    and abs(int(rc.top) - tt) <= 2
                    and abs(cw - tw) <= 2
                    and abs(ch - th) <= 2
                ):
                    return
            user32.SetWindowPos(hwnd, None, tl, tt, tw, th, 0x0004 | 0x0010)  # SWP_NOZORDER | SWP_NOACTIVATE
        except Exception:
            pass

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                super().changeEvent(event)
                return

            was_max = getattr(self, '_was_maximized', False)
            now_max = self.isMaximized()

            if not was_max and now_max:
                self._snapshot_pre_maximize_geometry()

            if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
                # Repair styles ONLY if missing; never cloak/SWP_FRAMECHANGED on normal restore (no white flash)
                try:
                    user32, _, _ = _get_win32_apis()
                    hwnd = int(self.winId()) if self.testAttribute(Qt.WA_WState_Created) else 0
                    if hwnd:
                        GWL_STYLE = -16
                        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                        wanted = style | 0x00040000 | 0x00C00000 | 0x00080000 | 0x00020000 | 0x00010000
                        if wanted != style:
                            user32.SetWindowLongW(hwnd, GWL_STYLE, wanted)
                            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)  # NOSIZE|NOMOVE|NOZORDER|NOACTIVATE|FRAMECHANGED
                        self._enforce_win_dwm_attributes(hwnd, include_extend=True)
                except Exception:
                    pass

            self._was_maximized = now_max
            self._update_border_overlay()
            self._update_grips()
            self._refresh_max_state()

            if now_max and getattr(self, '_is_win', False):
                # Now that IsZoomed(hwnd) is True, set rcNormalPosition to 70% x 70% for smooth Aero ripping
                self._sync_win_normal_placement(use_button_restore=False)

            if was_max and not now_max and not self.isFullScreen():
                via_btn = bool(getattr(self, '_restore_via_button', False))
                self._restore_via_button = False
                if getattr(self, '_is_win', False):
                    if via_btn and not getattr(self, '_always_restore_default_size', False):
                        QTimer.singleShot(0, self._verify_win_button_restore)
                elif not getattr(self, '_restoring_from_max', False):
                    # Unix enforces exact geometry after WM async settle
                    QTimer.singleShot(0, lambda vb=via_btn: self._restore_after_unmaximize(via_button=vb))
        elif event.type() == QEvent.Type.WinIdChange:
            if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
                try:
                    hwnd = int(self.winId())
                    if hwnd:
                        self._enforce_win_dwm_attributes(hwnd, include_extend=True)
                except Exception:
                    pass
        elif event.type() == QEvent.Type.ActivationChange:
            if hasattr(self, '_update_shortcut_enabled_states'):
                self._update_shortcut_enabled_states()
        super().changeEvent(event)

    def _apply_dark_class_brush(self, hwnd: int):
        """Caches the dark Win32 HBRUSH matching BG_COLOR (#1c1c1c) for WM_ERASEBKGND without mutating shared WNDCLASS."""
        try:
            self._dark_brush = _get_dark_bg_brush()
        except Exception:
            pass

    def _dwm_uncloak(self):
        try:
            import ctypes
            if self.testAttribute(Qt.WA_WState_Created):
                _, _, dwmapi = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd:
                    self._enforce_win_dwm_attributes(hwnd, include_extend=True)
                    val = ctypes.c_int(0)
                    dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)
                    self._enforce_win_dwm_attributes(hwnd, include_extend=False)
        except Exception:
            pass

    def showEvent(self, event):
        if self._is_popup:
            self._sync_popup_always_on_top()

        # Cloak during initial window mapping on Windows to eliminate DWM standard NC white flash
        if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
            try:
                import ctypes
                _, _, dwmapi = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd and not getattr(self, '_shown_once', False):
                    self._shown_once = True
                    val = ctypes.c_int(1)
                    dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)
                    self._enforce_win_dwm_attributes(hwnd, include_extend=False)
            except Exception:
                pass

        super().showEvent(event)

        if not _HAS_QFRAMELESS and getattr(self, '_is_win', False):
            try:
                user32, _, _ = _get_win32_apis()
                hwnd = int(self.winId())
                if hwnd and getattr(self, '_is_root', False):
                    GWL_STYLE = -16
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    style |= 0x00040000  # WS_THICKFRAME
                    style |= 0x00C00000  # WS_CAPTION
                    style |= 0x00080000  # WS_SYSMENU
                    style |= 0x00020000  # WS_MINIMIZEBOX
                    style |= 0x00010000  # WS_MAXIMIZEBOX
                    user32.SetWindowLongW(hwnd, GWL_STYLE, style)

                    self._apply_dark_class_brush(hwnd)
                    self._enforce_win_dwm_attributes(hwnd, include_extend=True)

                    user32.SetWindowPos(
                        hwnd, None, 0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020
                    )

                    # Re-apply sharp corners & border color AFTER SWP_FRAMECHANGED
                    self._enforce_win_dwm_attributes(hwnd, include_extend=True)

                    if user32.IsZoomed(hwnd):
                        self._was_maximized = True
                        self._sync_win_normal_placement(use_button_restore=False)

                    QTimer.singleShot(35, self._dwm_uncloak)
                    QTimer.singleShot(150, self._dwm_uncloak)
                elif hwnd:
                    self._enforce_win_dwm_attributes(hwnd, include_extend=True)
            except Exception:
                self._dwm_uncloak()

        self._update_border_overlay()
        self._update_grips()
        self._refresh_max_state()
        self._record_normal_geometry()

    def _refresh_max_state(self):
        is_max = self.isMaximized()
        title_bar = getattr(self, '_title_bar', getattr(self, '_tb', None))
        if title_bar and hasattr(title_bar, 'update_maximize_icon'):
            title_bar.update_maximize_icon(is_max)

    def _setup_grips(self):
        self._grips = []
        edges = [
            Qt.TopEdge,
            Qt.BottomEdge,
            Qt.LeftEdge,
            Qt.RightEdge,
            Qt.TopEdge | Qt.LeftEdge,
            Qt.TopEdge | Qt.RightEdge,
            Qt.BottomEdge | Qt.LeftEdge,
            Qt.BottomEdge | Qt.RightEdge,
        ]
        for edge in edges:
            grip = ResizeGrip(self, edge)
            self._grips.append(grip)

    def moveEvent(self, event):
        super().moveEvent(event)
        self._update_border_overlay()
        self._update_grips()
        self._record_normal_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_border_overlay()
        self._update_grips()
        self._record_normal_geometry()

    def _update_grips(self):
        if not hasattr(self, '_grips'):
            return

        is_full = self._is_effectively_maximized()
        b = 6
        b_top = 3       # Thin top resize strip so titlebar drag & buttons remain unobstructed
        b_corner = 5    # Compact top corner hit zones when windowed

        fw, fh = self.width(), self.height()

        for grip in self._grips:
            if is_full:
                if not grip.isHidden():
                    grip.hide()
                continue
            elif grip.isHidden():
                grip.show()

            if grip.edge == Qt.TopEdge:
                grip.setGeometry(b_corner, 0, max(1, fw - 2 * b_corner), b_top)
            elif grip.edge == Qt.BottomEdge:
                grip.setGeometry(b, fh - b, max(1, fw - 2 * b), b)
            elif grip.edge == Qt.LeftEdge:
                grip.setGeometry(0, b_corner, b, max(1, fh - b_corner - b))
            elif grip.edge == Qt.RightEdge:
                grip.setGeometry(fw - b, b_corner, b, max(1, fh - b_corner - b))
            elif grip.edge == (Qt.TopEdge | Qt.LeftEdge):
                grip.setGeometry(0, 0, b_corner, b_corner)
            elif grip.edge == (Qt.TopEdge | Qt.RightEdge):
                grip.setGeometry(fw - b_corner, 0, b_corner, b_corner)
            elif grip.edge == (Qt.BottomEdge | Qt.LeftEdge):
                grip.setGeometry(0, fh - b, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.RightEdge):
                grip.setGeometry(fw - b, fh - b, b, b)
            grip.raise_()

    # ── Windows Native Event Handling ────────────────────────────────────────
    def _show_win_system_menu(self, hwnd: int, screen_x: int, screen_y: int):
        try:
            user32, _, _ = _get_win32_apis()
            hmenu = user32.GetSystemMenu(hwnd, False)
            if not hmenu:
                return
            SC_RESTORE = 0xF120
            SC_MOVE = 0xF010
            SC_SIZE = 0xF000
            SC_MINIMIZE = 0xF020
            SC_MAXIMIZE = 0xF030
            MF_ENABLED = 0x0000
            MF_GRAYED = 0x0001
            is_max = bool(user32.IsZoomed(hwnd))
            user32.EnableMenuItem(hmenu, SC_RESTORE, MF_ENABLED if is_max else MF_GRAYED)
            user32.EnableMenuItem(hmenu, SC_MOVE, MF_GRAYED if is_max else MF_ENABLED)
            user32.EnableMenuItem(hmenu, SC_SIZE, MF_GRAYED if is_max else MF_ENABLED)
            user32.EnableMenuItem(hmenu, SC_MINIMIZE, MF_ENABLED)
            user32.EnableMenuItem(hmenu, SC_MAXIMIZE, MF_GRAYED if is_max else MF_ENABLED)

            TPM_RETURNCMD = 0x0100
            TPM_RIGHTBUTTON = 0x0002
            cmd = user32.TrackPopupMenu(
                hmenu, TPM_RETURNCMD | TPM_RIGHTBUTTON, screen_x, screen_y, 0, hwnd, None
            )
            if cmd:
                user32.PostMessageW(hwnd, 0x0112, cmd, 0)
        except Exception:
            pass

    def nativeEvent(self, eventType, message):
        if _HAS_QFRAMELESS and getattr(self, '_is_win', False):
            return super().nativeEvent(eventType, message)

        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False) or eventType != b"windows_generic_MSG":
            return super().nativeEvent(eventType, message)

        import ctypes
        from ctypes import wintypes
        msg = wintypes.MSG.from_address(int(message))
        # INVARIANT: Never call self.winId() inside nativeEvent (causes re-entrant QWidget::create
        # stack overflow 0xC00000FD on Windows 11 during ShowWindow/CreateWindowEx). Always use msg.hWnd.
        hwnd = int(msg.hWnd or 0)
        if not hwnd:
            return super().nativeEvent(eventType, message)

        user32, _, _ = _get_win32_apis()

        # ── WM_NCCALCSIZE (0x0083) ────────────────────────────────────────────
        # INVARIANT: Query live Win32 IsZoomed(hwnd), NEVER stale Qt isMaximized(),
        # and NEVER pair this with a custom WM_GETMINMAXINFO that shrinks ptMaxSize.
        if msg.message == 0x0083:
            if not msg.wParam:
                return True, 0
            try:
                is_zoomed = bool(user32.IsZoomed(hwnd))
                params = ctypes.cast(msg.lParam, ctypes.POINTER(wintypes.RECT))
                r0 = params[0]

                work_tuple = None
                mon_tuple = None
                bx, by = 8, 8
                if is_zoomed:
                    class MONITORINFO(ctypes.Structure):
                        _fields_ = [
                            ('cbSize', wintypes.DWORD),
                            ('rcMonitor', wintypes.RECT),
                            ('rcWork', wintypes.RECT),
                            ('dwFlags', wintypes.DWORD),
                        ]
                    hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
                    if hmon:
                        mi = MONITORINFO()
                        mi.cbSize = ctypes.sizeof(MONITORINFO)
                        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                            work_tuple = (mi.rcWork.left, mi.rcWork.top, mi.rcWork.right, mi.rcWork.bottom)
                            mon_tuple = (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom)
                    if work_tuple is None:
                        try:
                            dpi = user32.GetDpiForWindow(hwnd) or 96
                            pad = user32.GetSystemMetricsForDpi(92, dpi)
                            bx = user32.GetSystemMetricsForDpi(32, dpi) + pad
                            by = user32.GetSystemMetricsForDpi(33, dpi) + pad
                        except Exception:
                            pad = user32.GetSystemMetrics(92)
                            bx = user32.GetSystemMetrics(32) + pad
                            by = user32.GetSystemMetrics(33) + pad

                nl, nt, nr, nb = compute_win_nccalcsize_rect(
                    (r0.left, r0.top, r0.right, r0.bottom),
                    is_zoomed=is_zoomed,
                    is_fullscreen=self.isFullScreen(),
                    work_rect=work_tuple,
                    monitor_rect=mon_tuple,
                    fallback_bx=bx,
                    fallback_by=by,
                )
                r0.left, r0.top, r0.right, r0.bottom = nl, nt, nr, nb
            except Exception:
                pass
            return True, 0

        # ── WM_NCPAINT (0x0085) ───────────────────────────────────────────────
        # Suppress native non-client border & caption button painting completely.
        if msg.message == 0x0085:
            return True, 0

        # ── WM_ERASEBKGND (0x0014) ────────────────────────────────────────────
        # Fill exposed client area with dark app background so resize/rip never flashes white.
        if msg.message == 0x0014:
            try:
                if msg.wParam:
                    brush = getattr(self, '_dark_brush', None) or _get_dark_bg_brush()
                    if brush:
                        rc = wintypes.RECT()
                        if user32.GetClientRect(hwnd, ctypes.byref(rc)):
                            user32.FillRect(
                                wintypes.HDC(msg.wParam),
                                ctypes.byref(rc),
                                wintypes.HBRUSH(brush),
                            )
                            return True, 1
            except Exception:
                pass

        # ── WM_NCACTIVATE (0x0086) ────────────────────────────────────────────
        # Return TRUE without calling DefWindowProcW (unless minimized) so Windows
        # allows activation changes without ever painting native NC chrome/buttons.
        if msg.message == 0x0086:
            try:
                if not user32.IsIconic(hwnd):
                    return True, 1
            except Exception:
                return True, 1
            return super().nativeEvent(eventType, message)

        # ── WM_MOUSEACTIVATE (0x0021) ─────────────────────────────────────────
        if msg.message == 0x0021:
            return True, 1  # MA_ACTIVATE

        # ── WM_NCHITTEST (0x0084) ─────────────────────────────────────────────
        # Uses ScreenToClient + GetClientRect so coordinates match Qt client pixels 1:1
        # even when maximized (overhanging -8px frame) or across mixed-DPI monitors.
        if msg.message == 0x0084:
            sx = msg.lParam & 0xFFFF
            if sx & 0x8000:
                sx -= 0x10000
            sy = (msg.lParam >> 16) & 0xFFFF
            if sy & 0x8000:
                sy -= 0x10000

            w = max(1, self.width())
            h = max(1, self.height())
            pt = wintypes.POINT(sx, sy)
            crc = wintypes.RECT()
            if user32.ScreenToClient(hwnd, ctypes.byref(pt)) and user32.GetClientRect(hwnd, ctypes.byref(crc)) and crc.right > 0 and crc.bottom > 0:
                rel_x = int(pt.x * w // crc.right) if pt.x >= 0 else -1
                rel_y = int(pt.y * h // crc.bottom) if pt.y >= 0 else -1
            else:
                ratio = max(1.0, float(self.devicePixelRatioF()))
                pos_pt = self.mapFromGlobal(QPoint(int(round(sx / ratio)), int(round(sy / ratio))))
                rel_x, rel_y = pos_pt.x(), pos_pt.y()

            is_max = self._is_effectively_maximized()
            if is_max:
                # Clamp extreme top/corner edge hits cleanly inside [0..w-1, 0..h-1] for Fitts's Law
                rel_x = max(0, min(rel_x, w - 1))
                rel_y = max(0, min(rel_y, h - 1))

            _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
            tb_height = (_tb.height() if (_tb and _tb.isVisible()) else 0)

            is_on_max_btn = False
            is_on_interactive = False
            if 0 <= rel_y < tb_height and 0 <= rel_x < w:
                child = self.childAt(QPoint(rel_x, rel_y))
                btn_max = getattr(_tb, 'btn_max', None) if _tb else None
                cur = child
                while cur is not None and cur is not _tb and cur is not self:
                    if btn_max is not None and cur is btn_max and btn_max.isVisible():
                        is_on_max_btn = True
                        break
                    if isinstance(cur, (QAbstractButton, QLineEdit)) or cur.__class__.__name__ == "TitleDropdown":
                        is_on_interactive = True
                        break
                    cur = cur.parentWidget()

            hit = compute_win_nchittest(
                rel_x=rel_x,
                rel_y=rel_y,
                win_w=w,
                win_h=h,
                border_px=self._RESIZE_BORDER,
                is_maximized=is_max,
                is_fullscreen=self.isFullScreen(),
                titlebar_height=tb_height,
                is_on_max_btn=is_on_max_btn,
                is_on_interactive_child=is_on_interactive,
                top_border_px=self._TOP_RESIZE_BORDER,
            )

            _tb_btn_max = getattr(_tb, 'btn_max', None) if _tb else None
            if _tb_btn_max and hit != HTMAXBUTTON and hasattr(_tb_btn_max, 'set_native_hover'):
                _tb_btn_max.set_native_hover(False)

            return True, hit

        # ── Snap Layouts / HTMAXBUTTON non-client hover & click forwarding ────
        _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
        btn_max = getattr(_tb, 'btn_max', None) if _tb else None

        if msg.message == 0x00A0:  # WM_NCMOUSEMOVE
            if btn_max and hasattr(btn_max, 'set_native_hover'):
                btn_max.set_native_hover(msg.wParam == HTMAXBUTTON)
            return False, 0  # Let Windows 11 receive HTMAXBUTTON hover for Snap Layouts

        if msg.message == 0x02A2:  # WM_NCMOUSELEAVE
            if btn_max and hasattr(btn_max, 'set_native_hover'):
                btn_max.set_native_hover(False)
                btn_max.set_native_pressed(False)
            return False, 0

        if msg.message == 0x00A1 and msg.wParam == HTMAXBUTTON:  # WM_NCLBUTTONDOWN
            if btn_max and hasattr(btn_max, 'set_native_pressed'):
                btn_max.set_native_pressed(True)
            return True, 0

        if msg.message == 0x00A2 and msg.wParam == HTMAXBUTTON:  # WM_NCLBUTTONUP
            if btn_max and hasattr(btn_max, 'set_native_pressed'):
                btn_max.set_native_pressed(False)
            if _tb and hasattr(_tb, '_toggle_maximize'):
                _tb._toggle_maximize(via_button=True)
            return True, 0

        # ── WM_NCRBUTTONUP (0x00A5) on HTCAPTION ─────────────────────────────
        if msg.message == 0x00A5 and msg.wParam == HTCAPTION:
            sx = msg.lParam & 0xFFFF
            if sx & 0x8000:
                sx -= 0x10000
            sy = (msg.lParam >> 16) & 0xFFFF
            if sy & 0x8000:
                sy -= 0x10000
            self._show_win_system_menu(hwnd, sx, sy)
            return True, 0

        # ── WM_NCLBUTTONDBLCLK (0x00A3) ───────────────────────────────────────
        # Double-clicking titlebar un-maximizes to 70% x 70% (ONLY btn_max restores pre-max rect)
        if msg.message == 0x00A3:
            if _tb and hasattr(_tb, '_toggle_maximize') and msg.wParam == HTCAPTION:
                _tb._toggle_maximize(via_button=False)
            return True, 0

        # ── WM_STYLECHANGED (0x007D) / WM_DWMCOMPOSITIONCHANGED (0x031E) ─────
        # Keep sharp 90-degree corners & dark DWM framing if Qt/Windows resets styles.
        if msg.message in (0x007D, 0x031E):
            self._enforce_win_dwm_attributes(hwnd, include_extend=(msg.message == 0x031E))

        return super().nativeEvent(eventType, message)
