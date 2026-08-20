import os
import platform
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QIcon
import config

def _app_icon() -> QIcon:
    try:
        import json
        # install_dir should be the project root. gui/utils.py -> root
        install_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        is_win = platform.system() == "Windows"
        ext = ".ico" if is_win else ".png"

        icon_name = "default"
        settings_file = os.path.join(install_dir, "settings.json")
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                icon_name = data.get('app_icon', 'default')

        # Prod layout (icons/ folder directly in install_dir), Dev layout (assets/icons/)
        prod_icon_path = os.path.join(install_dir, "icons", f"icon_{icon_name}{ext}")
        dev_icon_path = os.path.join(install_dir, "assets", "icons", f"icon_{icon_name}{ext}")
        
        icon_path = prod_icon_path if os.path.exists(prod_icon_path) else dev_icon_path
        
        if not os.path.exists(icon_path):
            icon_path = os.path.join(install_dir, "icon" + ext)

        if os.path.exists(icon_path):
            return QIcon(icon_path)
    except Exception:
        pass
    return QIcon()


def apply_dark_title_bar(window: QWidget):
    """Forces the native Windows title bar to dark mode."""
    if platform.system() == "Windows":
        try:
            import ctypes
            # 20 is DWMWA_USE_IMMERSIVE_DARK_MODE in Windows 10/11
            ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, ctypes.byref(ctypes.c_int(1)), 4)
        except Exception:
            pass

def _center_on_screen(widget: QWidget, w: int, h: int):
    """Center *widget* on the primary screen (or active monitor if detectable)."""
    screen = QApplication.primaryScreen()
    if screen:
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width()  - w) // 2
        y = geo.y() + (geo.height() - h) // 2
        widget.setGeometry(x, y, w, h)


def _txt(lang: str, key: str, **kwargs) -> str:
    """Return translation string for *key* in *lang*, falling back to 'en'."""
    text = config.TRANS.get(lang, config.TRANS["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def _qwidget_txt(self, key: str, **kwargs) -> str:
    w = self.window()
    if hasattr(w, 'txt') and w != self:
        return w.txt(key, **kwargs)
    return _txt("en", key, **kwargs)

QWidget.txt = _qwidget_txt
