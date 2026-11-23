#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Copyright (c) 2026 Szymon Wolarz
#Licensed under the MIT License. See LICENSE file in the project root for full license information.

"""
MODULE: mixins.py
ROLE: GUI Component (Red Zone)
DESCRIPTION:
Cross-platform frameless window mixin providing CSD titlebar integration,
8-edge/corner resize hit-testing, Windows DWM shadow/Snap Layouts, Linux CSD
shadow management, user normal-size restoration, and popup Always-on-Top inheritance.
"""

from PySide6.QtWidgets import QWidget, QMainWindow, QDialog, QAbstractButton, QLineEdit
from PySide6.QtCore import Qt, QPoint, QRect, QSize, QTimer, QEvent
from PySide6.QtGui import QGuiApplication, QCursor

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
) -> int:
    """
    Pure cross-platform hit-test classifier returning Win32 HT* constants.
    # INVARIANT: Supports all 8 resize edges/corners when not maximized/fullscreen,
    # HTMAXBUTTON (9) on the maximize button (Windows 11 Snap Layouts), and
    # HTCAPTION (2) on empty titlebar area (Aero Snap + drag-detach).
    """
    if not is_maximized and not is_fullscreen and win_w > 0 and win_h > 0:
        b = max(2, int(border_px))
        lx = rel_x < b
        rx = rel_x >= win_w - b
        ty = rel_y < b
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
    Mixin that turns any QMainWindow / QDialog into a frameless, CSD window.
    """

    _RESIZE_BORDER = 5   # px - hit-test sensitivity at window edges

    def frameless_init(self, is_popup: bool = False, use_linux_csd_shadow: bool = False):
        """Call once, right after super().__init__()."""
        import platform
        self._is_win = platform.system() == "Windows"
        self._is_mac = platform.system() == "Darwin"
        self._is_wayland = QGuiApplication.platformName() == "wayland"
        self._is_popup = bool(is_popup)
        self._is_root = not self._is_popup
        self._use_linux_csd_shadow = bool(
            use_linux_csd_shadow and self._is_root and not self._is_win and not self._is_mac
        )
        self._default_normal_size = None
        self._session_user_geometry = None
        self._always_restore_default_size = False
        self._restore_via_button = False
        self._normal_ratio = 0.70
        self._normal_min_w = 640
        self._normal_min_h = 460
        self._restoring_from_max = False
        self._last_restored_geo = None
        self._csd_shadow_margin = 14
        self._csd_shadow_collapsed = None

        if self._is_win:
            if self._is_root:
                # Root window: FramelessWindowHint removes native NC chrome; DWM shadow,
                # animations, Snap Layouts, and 8-edge resize are restored in showEvent + nativeEvent.
                self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
            else:
                self.setWindowFlags(
                    self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog | Qt.NoDropShadowWindowHint
                )
                self.setAttribute(Qt.WA_TranslucentBackground, True)
        elif self._is_mac and self._is_root:
            # macOS root window: native titlebar with traffic lights, native shadow, and fullscreen button.
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinMaxButtonsHint
                | Qt.WindowCloseButtonHint
                | Qt.WindowFullscreenButtonHint
            )
        elif self._is_root:
            # INVARIANT: Linux root windows must remain Qt.Window (never Qt.Dialog)
            # to preserve maximize, minimize, Alt+Tab, and window manager actions.
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
            if self._use_linux_csd_shadow:
                self.setAttribute(Qt.WA_TranslucentBackground, True)
        else:
            # Linux and macOS popups/dialogs: frameless translucent dialogs
            self.setWindowFlags(
                self.windowFlags() | Qt.FramelessWindowHint | Qt.Dialog | Qt.NoDropShadowWindowHint
            )
            self.setAttribute(Qt.WA_TranslucentBackground, True)

        if self._is_popup:
            self._sync_popup_always_on_top()

        if self._is_root and not self._is_win and not self._is_mac:
            self._setup_grips()

    def _get_root_frame(self):
        """Return the topmost styled QFrame to apply border-radius or shadow to."""
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
        True whenever the window is maximized or fullscreen.
        # INVARIANT: Top/corner resize grips and WM_NCHITTEST edges MUST be
        # completely disabled when maximized so top-right close clicks and
        # top-edge drag-detach ('ripping') never trigger resize.
        """
        if self.isMaximized() or self.isFullScreen():
            return True
        if getattr(self, '_is_win', False) and self.testAttribute(Qt.WA_WState_Created):
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd and ctypes.windll.user32.IsZoomed(hwnd):
                    return True
            except Exception:
                pass
        return False

    def _is_snapped_or_tiled(self) -> bool:
        """
        Returns True when a Linux CSD window is maximized, fullscreen, or snapped/tiled
        against screen edges (left/right/top/bottom half or quarter Aero Snap), so the
        outer translucent drop-shadow padding collapses to 0px and the window sits flush.
        """
        if self._is_effectively_maximized():
            return True
        if not getattr(self, '_use_linux_csd_shadow', False):
            return False
        if not self.isVisible():
            return False
        geo = self.frameGeometry()
        if not geo.isValid() or geo.width() <= 0 or geo.height() <= 0:
            return False
        scr = (
            QGuiApplication.screenAt(geo.center())
            or self.screen()
            or QGuiApplication.primaryScreen()
        )
        if not scr:
            return False
        avail = scr.availableGeometry()
        if not avail.isValid() or avail.width() <= 0 or avail.height() <= 0:
            return False

        tol = 4
        touch_left = abs(geo.left() - avail.left()) <= tol
        touch_right = abs(geo.right() - avail.right()) <= tol
        touch_top = abs(geo.top() - avail.top()) <= tol
        touch_bottom = abs(geo.bottom() - avail.bottom()) <= tol

        # Left/right half-screen snap or vertical maximize (touches both top and bottom)
        if touch_top and touch_bottom:
            return True
        # Top/bottom half-screen snap or horizontal maximize (touches both left and right)
        if touch_left and touch_right:
            return True
        # Quarter-screen snap (touches corner + matches ~half width & ~half height)
        if (touch_left or touch_right) and (touch_top or touch_bottom):
            half_w = avail.width() // 2
            half_h = avail.height() // 2
            if abs(geo.width() - half_w) <= 36 and abs(geo.height() - half_h) <= 36:
                return True
        # Pseudo-maximized (fills available work area without Qt.WindowMaximized flag)
        if geo.width() >= avail.width() - tol and geo.height() >= avail.height() - tol:
            return True
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
        Initializes default normal (non-maximized) geometry.
        - Main window (always_restore_default=False): default is 70% x 70% of active screen;
          ripping out of maximized ALWAYS uses 70% x 70%, while Restore button uses the
          user's last in-session geometry if they manually resized/snapped it.
        - Settings window (always_restore_default=True): exiting maximize ALWAYS returns
          to the small default size (saved_w x saved_h).
        """
        self._normal_ratio = float(ratio)
        self._normal_min_w = int(min_w)
        self._normal_min_h = int(min_h)
        self._always_restore_default_size = bool(always_restore_default)
        if screen is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        sg = screen.availableGeometry() if screen else QRect(100, 100, 1280, 720)
        default_geo = compute_default_normal_geometry(sg, ratio=ratio, min_w=min_w, min_h=min_h)

        if isinstance(saved_w, (int, float)) and isinstance(saved_h, (int, float)) and saved_w >= min_w and saved_h >= min_h:
            w = max(min(min_w, sg.width()), min(int(saved_w), sg.width()))
            h = max(min(min_h, sg.height()), min(int(saved_h), sg.height()))
            x = sg.x() + (sg.width() - w) // 2
            y = sg.y() + (sg.height() - h) // 2
            geo = QRect(x, y, w, h)
        else:
            geo = default_geo

        self._default_normal_size = QSize(geo.width(), geo.height())
        self._session_user_geometry = None
        if apply_geometry:
            self.setGeometry(geo)
        return geo

    def get_session_user_geometry(self) -> QRect | None:
        return getattr(self, '_session_user_geometry', None)

    def _compute_restore_target_geometry(self, via_button: bool = False) -> QRect:
        """
        Computes exact target geometry when leaving maximized state:
        - Settings window (_always_restore_default_size=True): ALWAYS small default size.
        - Main window ripped by titlebar (via_button=False): ALWAYS 70% x 70% of active screen.
        - Main window Restore button (via_button=True): last in-session user geometry if set
          (e.g. half-screen Aero Snap or manual resize), otherwise 70% x 70% centered.
        """
        scr = self.screen() or QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        sg = scr.availableGeometry() if scr else QRect(100, 100, 1280, 720)

        if getattr(self, '_always_restore_default_size', False):
            def_sz = getattr(self, '_default_normal_size', None)
            if def_sz and def_sz.isValid():
                w = min(def_sz.width(), sg.width())
                h = min(def_sz.height(), sg.height())
                x = sg.x() + (sg.width() - w) // 2
                y = sg.y() + (sg.height() - h) // 2
                return QRect(x, y, w, h)

        if via_button:
            user_geo = getattr(self, '_session_user_geometry', None)
            if user_geo and user_geo.isValid() and user_geo.width() > 0 and user_geo.height() > 0:
                w = min(user_geo.width(), sg.width())
                h = min(user_geo.height(), sg.height())
                x = max(sg.left(), min(user_geo.x(), sg.right() - w + 1))
                y = max(sg.top(), min(user_geo.y(), sg.bottom() - h + 1))
                return QRect(x, y, w, h)

        return compute_default_normal_geometry(
            sg,
            ratio=getattr(self, '_normal_ratio', 0.70),
            min_w=getattr(self, '_normal_min_w', 640),
            min_h=getattr(self, '_normal_min_h', 460),
        )

    def _sync_win_normal_placement(self, use_button_restore: bool = False):
        """
        Updates Win32 WINDOWPLACEMENT.rcNormalPosition:
        - use_button_restore=False (default while maximized): sets rcNormalPosition to 70% x 70%
          (or small default for Settings) so Windows Aero drag-detach ('ripping') ALWAYS detaches
          at that exact size.
        - use_button_restore=True (right before SC_RESTORE button click): sets rcNormalPosition to
          the in-session user geometry (if any) or 70% x 70% / default size.
        """
        if not getattr(self, '_is_win', False) or not getattr(self, '_is_root', False):
            return
        if not self.testAttribute(Qt.WA_WState_Created):
            return
        target_geo = self._compute_restore_target_geometry(via_button=use_button_restore)
        if not target_geo or not target_geo.isValid():
            return
        try:
            import ctypes
            from ctypes import wintypes

            class WINDOWPLACEMENT(ctypes.Structure):
                _fields_ = [
                    ('length', wintypes.UINT),
                    ('flags', wintypes.UINT),
                    ('showCmd', wintypes.UINT),
                    ('ptMinPosition', wintypes.POINT),
                    ('ptMaxPosition', wintypes.POINT),
                    ('rcNormalPosition', wintypes.RECT),
                ]

            hwnd = int(self.winId())
            if not hwnd:
                return
            wp = WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(WINDOWPLACEMENT)
            if not ctypes.windll.user32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
                return

            dpr = max(1.0, float(self.devicePixelRatioF()))
            phys_x = int(round(target_geo.x() * dpr))
            phys_y = int(round(target_geo.y() * dpr))
            phys_w = int(round(target_geo.width() * dpr))
            phys_h = int(round(target_geo.height() * dpr))

            wp.rcNormalPosition.left = phys_x
            wp.rcNormalPosition.top = phys_y
            wp.rcNormalPosition.right = phys_x + phys_w
            wp.rcNormalPosition.bottom = phys_y + phys_h
            ctypes.windll.user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
        except Exception:
            pass

    def _sync_csd_shadow_state(self):
        """On Linux CSD windows with drop shadow, collapse outer shadow margin when maximized, fullscreen, or snapped/tiled."""
        if not getattr(self, '_use_linux_csd_shadow', False):
            return
        collapse = self._is_snapped_or_tiled()
        if collapse == getattr(self, '_csd_shadow_collapsed', None):
            return
        self._csd_shadow_collapsed = collapse
        lay = self.layout()
        if lay is not None:
            m = 0 if collapse else getattr(self, '_csd_shadow_margin', 14)
            lay.setContentsMargins(m, m, m, m)
        frame = self._get_root_frame()
        if frame is not None and frame.graphicsEffect() is not None:
            frame.graphicsEffect().setEnabled(not collapse)
        self._update_grips()

    def _restore_after_unmaximize(self, via_button: bool = False):
        """Enforces exact post-maximize geometry (button restore vs titlebar rip vs Settings default)."""
        if not getattr(self, '_is_root', False):
            return
        if self._is_effectively_maximized():
            return

        target_geo = self._compute_restore_target_geometry(via_button=via_button)
        if not target_geo or not target_geo.isValid():
            return

        self._restoring_from_max = True
        try:
            if via_button or getattr(self, '_always_restore_default_size', False):
                self.setGeometry(target_geo)
            else:
                # Ripping out of maximized: always enforce exact 70% x 70% size while keeping window under cursor/on screen
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
            self._last_restored_geo = QRect(self.geometry())
        finally:
            self._restore_via_button = False
            QTimer.singleShot(80, lambda: setattr(self, '_restoring_from_max', False))

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                super().changeEvent(event)
                return

            was_max = getattr(self, '_was_maximized', False)
            now_max = self.isMaximized()

            if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
                try:
                    import ctypes
                    hwnd = int(self.winId())
                    if hwnd:
                        user32 = ctypes.windll.user32
                        GWL_STYLE = -16
                        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                        style |= 0x00040000  # WS_THICKFRAME
                        style |= 0x00C00000  # WS_CAPTION
                        style |= 0x00080000  # WS_SYSMENU
                        style |= 0x00020000  # WS_MINIMIZEBOX
                        style |= 0x00010000  # WS_MAXIMIZEBOX
                        user32.SetWindowLongW(hwnd, GWL_STYLE, style)

                        if was_max and not now_max:
                            val = ctypes.c_int(1)
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)

                        user32.SetWindowPos(
                            hwnd, None, 0, 0, 0, 0,
                            0x0001 | 0x0002 | 0x0004 | 0x0020
                        )

                        if was_max and not now_max:
                            QTimer.singleShot(30, self._dwm_uncloak)
                except Exception:
                    pass

            self._was_maximized = now_max
            self._sync_csd_shadow_state()
            self._update_grips()
            self._refresh_max_state()

            if now_max and getattr(self, '_is_win', False):
                # Keep Win32 rcNormalPosition at rip size (70% or Settings default) while maximized
                self._sync_win_normal_placement(use_button_restore=False)

            if was_max and not now_max and not self.isFullScreen():
                via_btn = bool(getattr(self, '_restore_via_button', False))
                QTimer.singleShot(0, lambda vb=via_btn: self._restore_after_unmaximize(via_button=vb))
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
        if self._is_popup:
            self._sync_popup_always_on_top()

        # Cloak during initial window mapping on Windows to eliminate DWM standard NC white flash
        if not _HAS_QFRAMELESS and getattr(self, '_is_win', False) and getattr(self, '_is_root', False):
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd and not getattr(self, '_shown_once', False):
                    self._shown_once = True
                    val = ctypes.c_int(1)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 13, ctypes.byref(val), 4)
            except Exception:
                pass

        super().showEvent(event)
        self._sync_csd_shadow_state()
        self._update_grips()

        if not _HAS_QFRAMELESS and getattr(self, '_is_win', False):
            try:
                import ctypes
                hwnd = int(self.winId())
                if hwnd and getattr(self, '_is_root', False):
                    user32 = ctypes.windll.user32
                    dwmapi = ctypes.windll.dwmapi

                    GWL_STYLE = -16
                    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
                    style |= 0x00040000  # WS_THICKFRAME
                    style |= 0x00C00000  # WS_CAPTION
                    style |= 0x00080000  # WS_SYSMENU (system context menu on titlebar right-click)
                    style |= 0x00020000  # WS_MINIMIZEBOX
                    style |= 0x00010000  # WS_MAXIMIZEBOX
                    user32.SetWindowLongW(hwnd, GWL_STYLE, style)

                    # Force dark DWM attribute for Windows 10/11 (20 -> 19 fallback, value=1)
                    dark_val = ctypes.c_int(1)
                    if dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_val), 4) != 0:
                        dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_val), 4)

                    # Force DWM NC rendering enabled (shadow)
                    nc_policy = ctypes.c_int(2)
                    dwmapi.DwmSetWindowAttribute(hwnd, 2, ctypes.byref(nc_policy), 4)

                    # 1px top DWM frame strip for Aero Snap preview and shadow anchoring
                    class MARGINS(ctypes.Structure):
                        _fields_ = [
                            ('left', ctypes.c_int),
                            ('right', ctypes.c_int),
                            ('top', ctypes.c_int),
                            ('bottom', ctypes.c_int),
                        ]
                    margins = MARGINS(0, 0, 1, 0)
                    dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

                    self._sync_win_normal_placement()

                    user32.SetWindowPos(
                        hwnd, None, 0, 0, 0, 0,
                        0x0001 | 0x0002 | 0x0004 | 0x0020
                    )

                    QTimer.singleShot(35, self._dwm_uncloak)
                elif hwnd:
                    dark_val = ctypes.c_int(1)
                    if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_val), 4) != 0:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(dark_val), 4)

                if hwnd:
                    # All windows: DWMWCP_DONOTROUND (33) & remove Win11 1px border (34)
                    corner_pref = ctypes.c_int(1)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), 4)
                    border_color = ctypes.c_uint(0xFFFFFFFE)
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border_color), 4)
            except Exception:
                pass

        # Refresh grips after Win32/WM show so hidden grips are never raised over maximized titlebar
        self._update_grips()

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

    def _record_session_user_geometry_if_applicable(self):
        """Records in-session manual geometry (e.g., manual resize or Aero Snap) for Main Window Restore button."""
        if (
            not getattr(self, '_is_root', False)
            or getattr(self, '_always_restore_default_size', False)
            or not self.isVisible()
            or self._is_effectively_maximized()
            or getattr(self, '_restoring_from_max', False)
        ):
            return
        geo = QRect(self.geometry())
        if not geo.isValid() or geo.width() <= 0 or geo.height() <= 0:
            return
        scr = self.screen() or QGuiApplication.primaryScreen()
        sg = scr.availableGeometry() if scr else None
        if sg and geo.width() >= int(sg.width() * 0.96) and geo.height() >= int(sg.height() * 0.96):
            return
        # Ignore exact echo of programmatic restore geometry
        last_rest = getattr(self, '_last_restored_geo', None)
        if last_rest is not None and abs(geo.width() - last_rest.width()) <= 2 and abs(geo.height() - last_rest.height()) <= 2 and abs(geo.x() - last_rest.x()) <= 2 and abs(geo.y() - last_rest.y()) <= 2:
            return
        self._session_user_geometry = geo

    def moveEvent(self, event):
        super().moveEvent(event)
        self._sync_csd_shadow_state()
        self._update_grips()
        self._record_session_user_geometry_if_applicable()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_csd_shadow_state()
        self._update_grips()
        self._record_session_user_geometry_if_applicable()

    def _update_grips(self):
        if not hasattr(self, '_grips'):
            return

        is_full = self._is_effectively_maximized()
        b = 6
        b_top = 4  # Thin top border strip so titlebar close/min/max buttons remain unobstructed

        # When CSD shadow padding is active on Linux, place grips tightly around inner_frame
        frame = self._get_root_frame() if getattr(self, '_use_linux_csd_shadow', False) else None
        if frame is not None and frame.width() > 0 and frame.height() > 0:
            fx, fy, fw, fh = frame.x(), frame.y(), frame.width(), frame.height()
        else:
            fx, fy, fw, fh = 0, 0, self.width(), self.height()

        for grip in self._grips:
            if is_full:
                if not grip.isHidden():
                    grip.hide()
                continue
            elif grip.isHidden():
                grip.show()

            if grip.edge == Qt.TopEdge:
                grip.setGeometry(fx + b, fy, max(1, fw - 2 * b), b_top)
            elif grip.edge == Qt.BottomEdge:
                grip.setGeometry(fx + b, fy + fh - b, max(1, fw - 2 * b), b)
            elif grip.edge == Qt.LeftEdge:
                grip.setGeometry(fx, fy + b, b, max(1, fh - 2 * b))
            elif grip.edge == Qt.RightEdge:
                grip.setGeometry(fx + fw - b, fy + b, b, max(1, fh - 2 * b))
            elif grip.edge == (Qt.TopEdge | Qt.LeftEdge):
                grip.setGeometry(fx, fy, b, b)
            elif grip.edge == (Qt.TopEdge | Qt.RightEdge):
                grip.setGeometry(fx + fw - b, fy, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.LeftEdge):
                grip.setGeometry(fx, fy + fh - b, b, b)
            elif grip.edge == (Qt.BottomEdge | Qt.RightEdge):
                grip.setGeometry(fx + fw - b, fy + fh - b, b, b)
            grip.raise_()

    # ── Windows Native Event Handling ────────────────────────────────────────
    def _show_win_system_menu(self, hwnd: int, screen_x: int, screen_y: int):
        try:
            import ctypes
            user32 = ctypes.windll.user32
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
            is_max = self.isMaximized()
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

        # ── WM_GETMINMAXINFO (0x0024) ─────────────────────────────────────────
        # Constrains maximized geometry to the active monitor's rcWork area.
        if msg.message == 0x0024:
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32

                class MINMAXINFO(ctypes.Structure):
                    _fields_ = [
                        ('ptReserved', wintypes.POINT),
                        ('ptMaxSize', wintypes.POINT),
                        ('ptMaxPosition', wintypes.POINT),
                        ('ptMinTrackSize', wintypes.POINT),
                        ('ptMaxTrackSize', wintypes.POINT),
                    ]

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
                        mmi = ctypes.cast(msg.lParam, ctypes.POINTER(MINMAXINFO))
                        work = mi.rcWork
                        mon = mi.rcMonitor
                        mmi[0].ptMaxPosition.x = work.left - mon.left
                        mmi[0].ptMaxPosition.y = work.top - mon.top
                        mmi[0].ptMaxSize.x = work.right - work.left
                        mmi[0].ptMaxSize.y = work.bottom - work.top
                        if (
                            work.left == mon.left
                            and work.top == mon.top
                            and work.right == mon.right
                            and work.bottom == mon.bottom
                        ):
                            # Auto-hide taskbar edge safeguard (1px)
                            mmi[0].ptMaxSize.y = max(1, mmi[0].ptMaxSize.y - 1)
                        return True, 0
            except Exception:
                pass

        # ── WM_NCCALCSIZE (0x0083) ────────────────────────────────────────────
        if msg.message == 0x0083:
            if msg.wParam and self.isMaximized():
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                try:
                    dpi = user32.GetDpiForWindow(hwnd) or 96
                    pad = user32.GetSystemMetricsForDpi(92, dpi)  # SM_CXPADDEDBORDER
                    bx = user32.GetSystemMetricsForDpi(32, dpi) + pad  # SM_CXSIZEFRAME
                    by = user32.GetSystemMetricsForDpi(33, dpi) + pad  # SM_CYSIZEFRAME
                except Exception:
                    pad = user32.GetSystemMetrics(92)
                    bx = user32.GetSystemMetrics(32) + pad
                    by = user32.GetSystemMetrics(33) + pad
                params = ctypes.cast(msg.lParam, ctypes.POINTER(wintypes.RECT))
                params[0].left += bx
                params[0].top += by
                params[0].right -= bx
                params[0].bottom -= by
            return True, (0x0300 if msg.wParam else 0)  # WVR_REDRAW

        # ── WM_ENTERSIZEMOVE (0x0231) ─────────────────────────────────────────
        if msg.message == 0x0231:
            hwnd = int(self.winId())
            if hwnd:
                ctypes.windll.user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0027)
            return super().nativeEvent(eventType, message)

        # ── WM_NCACTIVATE (0x0086) ────────────────────────────────────────────
        if msg.message == 0x0086:
            hwnd = int(self.winId())
            ctypes.windll.user32.DefWindowProcW(
                hwnd, 0x0086, msg.wParam, ctypes.c_long(-1)
            )
            return True, 1

        # ── WM_MOUSEACTIVATE (0x0021) ─────────────────────────────────────────
        if msg.message == 0x0021:
            return True, 1  # MA_ACTIVATE

        # ── WM_NCHITTEST (0x0084) ─────────────────────────────────────────────
        if msg.message == 0x0084:
            x = msg.lParam & 0xFFFF
            if x & 0x8000:
                x -= 0x10000
            y = (msg.lParam >> 16) & 0xFFFF
            if y & 0x8000:
                y -= 0x10000

            hwnd = int(self.winId())
            rc = wintypes.RECT()
            user32 = ctypes.windll.user32
            if hwnd and user32.GetWindowRect(hwnd, ctypes.byref(rc)):
                ratio = max(1.0, float(self.devicePixelRatioF()))
                rel_x = int(round((x - rc.left) / ratio))
                rel_y = int(round((y - rc.top) / ratio))
                w = max(1, int(round((rc.right - rc.left) / ratio)))
                h = max(1, int(round((rc.bottom - rc.top) / ratio)))
            else:
                ratio = max(1.0, float(self.devicePixelRatioF()))
                pos_pt = self.mapFromGlobal(QPoint(int(round(x / ratio)), int(round(y / ratio))))
                rel_x, rel_y = pos_pt.x(), pos_pt.y()
                w, h = self.width(), self.height()

            _tb = getattr(self, '_title_bar', getattr(self, '_tb', None))
            tb_height = (_tb.height() if (_tb and _tb.isVisible()) else 0)

            is_on_max_btn = False
            is_on_interactive = False
            if 0 <= rel_y < tb_height:
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
                is_maximized=self._is_effectively_maximized(),
                is_fullscreen=self.isFullScreen(),
                titlebar_height=tb_height,
                is_on_max_btn=is_on_max_btn,
                is_on_interactive_child=is_on_interactive,
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
                _tb._toggle_maximize()
            return True, 0

        # ── WM_NCRBUTTONUP (0x00A5) on HTCAPTION ─────────────────────────────
        if msg.message == 0x00A5 and msg.wParam == HTCAPTION:
            x = msg.lParam & 0xFFFF
            if x & 0x8000:
                x -= 0x10000
            y = (msg.lParam >> 16) & 0xFFFF
            if y & 0x8000:
                y -= 0x10000
            self._show_win_system_menu(int(self.winId()), x, y)
            return True, 0

        # ── WM_NCLBUTTONDBLCLK (0x00A3) ───────────────────────────────────────
        if msg.message == 0x00A3:
            if _tb and hasattr(_tb, '_toggle_maximize') and msg.wParam == HTCAPTION:
                _tb._toggle_maximize()
            return True, 0

        return super().nativeEvent(eventType, message)
