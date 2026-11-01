#!/usr/bin/env python3
"""
UI line-icon builder: writes every interface icon in assets/layout/ (dark theme, light strokes)
and assets/layout-light/ (light theme, dark strokes) from one definition. Run with the app's
venv python (needs PySide6):

    python tools/brand/build_icons.py                      # rebuild both folders
    python tools/brand/build_icons.py --sheet OUT.png [--old DIR]   # also write a contact sheet

Style: Lucide-like line icons on a 24-unit grid, round caps and joins, stroke 2 (1.75 for the
24 px sidebar icons). Most glyphs reuse Lucide path data (ISC licence, https://lucide.dev);
the "A" auto-mark and the window-control glyphs are drawn here.

Every PNG is rendered at the pixel size of the file it replaces (the code scales them down),
centred in a transparent canvas. SVG icons are written as plain SVG with explicit colours.
splashscreen.png and badwords-welcome-branding.svg are not touched.
"""
import argparse
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QByteArray, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT_DIRS = {
    "dark": os.path.join(ROOT, "assets", "layout"),         # dark UI -> light strokes
    "light": os.path.join(ROOT, "assets", "layout-light"),  # light UI -> dark strokes
}

# Set True to draw the titlebar window controls in the neutral stroke colour instead of
# their blue/green/red roles.
NEUTRAL_WINDOW_CONTROLS = False

ACCENT = "#a855f7"
# Colour roles per theme set.
ROLES = {
    "dark": {
        "normal": "#e6e6ee", "muted": "#8b8b9e", "hover": "#fafaff",
        "dim": "#6a6a80", "dimhover": "#a6a6b8", "accent": ACCENT,
        "onwhite": "#15151f",  # play/pause sit on the player's white circle
        "win_min": "#60a5fa", "win_max": "#4ade80", "win_close": "#f87171",
    },
    "light": {
        "normal": "#2a2a3a", "muted": "#6b6b7d", "hover": "#0b0b14",
        "dim": "#a4a4b6", "dimhover": "#6b6b7d", "accent": ACCENT,
        "onwhite": "#ffffff",  # the light theme turns the player's white circle ink: the glyph goes white
        "win_min": "#2563eb", "win_max": "#16a34a", "win_close": "#dc2626",
    },
}

# --- glyphs (24-unit grid) -------------------------------------------------------------------
SPEAKER = ('<path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3'
           'a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384'
           'A.705.705 0 0 0 11 19.298z"/>')
STAR = '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
X_GLYPH = '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'
RELOAD = '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>'
AUTO_A = '<circle cx="12" cy="12" r="10"/><path d="m8.5 16.5 3.5-9 3.5 9"/><path d="M9.8 13.3h4.4"/>'

GLYPHS = {
    # sidebar activities (24 px)
    "script": '<path d="m18 5-2.414-2.414A2 2 0 0 0 14.172 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2"/>'
              '<path d="M21.378 12.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87'
              'a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z"/><path d="M8 18h1"/>'
              '<path d="M8 10h6"/><path d="M8 14h3"/>',
    "silence": '<path d="M16 9a5 5 0 0 1 .95 2.293"/><path d="M19.364 5.636a9 9 0 0 1 1.889 9.96"/>'
               '<path d="m2 2 20 20"/><path d="m7 7-.587.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6'
               'a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298V11"/>'
               '<path d="M9.828 4.172A.686.686 0 0 1 11 4.657v.686"/>',
    "fillers": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
               '<path d="m14.5 7.5-5 5"/><path d="m9.5 7.5 5 5"/>',
    "main": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
            '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9'
            'a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "assembly": '<path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3Z"/>'
                '<path d="m6.2 5.3 3.1 3.9"/><path d="m12.4 3.4 3.1 4"/>'
                '<path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08'
                'a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74'
                'l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73'
                'V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08'
                'a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74'
                'l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25'
                'a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    # player (14-18 px)
    "player-backward": '<polygon points="11 19 2 12 11 5 11 19"/><polygon points="22 19 13 12 22 5 22 19"/>',
    "player-forward": '<polygon points="13 19 22 12 13 5 13 19"/><polygon points="2 19 11 12 2 5 2 19"/>',
    "player-play": '<polygon points="7 4 20 12 7 20 7 4"/>',
    "player-stop": '<rect x="5.5" y="4" width="4.5" height="16" rx="1"/><rect x="14" y="4" width="4.5" height="16" rx="1"/>',
    "volume-max": SPEAKER + '<path d="M16 9a5 5 0 0 1 0 6"/><path d="M19.364 18.364a9 9 0 0 0 0-12.728"/>',
    "volume-mid": SPEAKER + '<path d="M16 9a5 5 0 0 1 0 6"/>',
    "volume-min": SPEAKER,
    # actions (16-20 px)
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>'
            '<path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "cut": '<circle cx="6" cy="6" r="3"/><path d="M8.12 8.12 12 12"/><path d="M20 4 8.12 15.88"/>'
           '<circle cx="6" cy="18" r="3"/><path d="M14.8 14.8 20 20"/>',
    "clean": '<path d="m16 22-1-4"/><path d="M19 13.99a1 1 0 0 0 1-1V12a2 2 0 0 0-2-2h-3a1 1 0 0 1-1-1V4'
             'a2 2 0 0 0-4 0v5a1 1 0 0 1-1 1H6a2 2 0 0 0-2 2v.99a1 1 0 0 0 1 1"/>'
             '<path d="M5 14h14l1.973 6.767A1 1 0 0 1 20 22H4a1 1 0 0 1-.973-1.233z"/><path d="m8 22 1-4"/>',
    "information": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "auto-marked": AUTO_A,
    "auto-unmarked": AUTO_A,
    # titlebar window controls (12 px): tighter than Lucide's padding so they read at 12 px
    "minimize": '<path d="M3.5 12h17"/>',
    "maximize": '<rect x="3.5" y="3.5" width="17" height="17" rx="2.5"/>',
    "windowed": '<rect x="3" y="8" width="13" height="13" rx="2"/>'
                '<path d="M8 8V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-3"/>',
    "exit": '<path d="M19.5 4.5 4.5 19.5"/><path d="m4.5 4.5 15 15"/>',
    # small SVG buttons (~12-13 px)
    "reload": RELOAD, "reload-hover": RELOAD,
    "star-empty": STAR, "star-hover": STAR, "star-checked": STAR,
    "x": X_GLYPH, "x-hover": X_GLYPH,
}

# name -> (file name, (width, height) of the original, colour role, filled, stroke, real UI size px)
WIN = (lambda r: "normal" if NEUTRAL_WINDOW_CONTROLS else r)
ICONS = {
    "script": ("script.png", (493, 512), "normal", False, 1.75, 24),
    "silence": ("silence.png", (493, 512), "normal", False, 1.75, 24),
    "fillers": ("fillers.png", (493, 512), "normal", False, 1.75, 24),
    "main": ("main.png", (493, 512), "normal", False, 1.75, 24),
    "assembly": ("assembly.png", (493, 512), "normal", False, 1.75, 24),
    "settings": ("settings.png", (493, 512), "normal", False, 1.75, 24),
    "player-backward": ("player-backward.png", (512, 512), "normal", False, 2.25, 14),
    "player-forward": ("player-forward.png", (512, 512), "normal", False, 2.25, 14),
    "player-play": ("player-play.png", (512, 512), "onwhite", True, 2, 16),
    "player-stop": ("player-stop.png", (512, 512), "onwhite", True, 1, 16),
    "volume-max": ("volume-max.png", (512, 512), "normal", False, 2, 18),
    "volume-mid": ("volume-mid.png", (512, 512), "normal", False, 2, 18),
    "volume-min": ("volume-min.png", (512, 512), "normal", False, 2, 18),
    "search": ("search.png", (220, 220), "normal", False, 2, 18),
    "copy": ("copy.png", (512, 512), "normal", False, 2, 16),
    "cut": ("cut.png", (512, 512), "normal", False, 2, 20),
    "clean": ("clean.png", (512, 512), "normal", False, 2, 18),
    "information": ("information.png", (1000, 1000), "muted", False, 2, 16),
    "auto-marked": ("auto-marked.png", (512, 512), "accent", False, 2.25, 20),
    "auto-unmarked": ("auto-unmarked.png", (512, 512), "normal", False, 2, 20),
    "minimize": ("minimize.png", (220, 220), WIN("win_min"), False, 2.5, 12),
    "maximize": ("maximize.png", (220, 220), WIN("win_max"), False, 2.5, 12),
    "windowed": ("windowed.png", (274, 274), WIN("win_max"), False, 2.5, 12),
    "exit": ("exit.png", (220, 220), WIN("win_close"), False, 2.5, 12),
    "reload": ("reload.svg", (144, 148), "muted", False, 2.25, 13),
    "reload-hover": ("reload-hover.svg", (144, 148), "hover", False, 2.25, 13),
    "star-empty": ("star-empty.svg", (123, 118), "dim", False, 2, 12),
    "star-hover": ("star-hover.svg", (123, 118), "dimhover", False, 2, 12),
    "star-checked": ("star-checked.svg", (122.88, 117.1), "accent", True, 2, 12),
    "x": ("x.svg", (123, 123), "muted", False, 2.25, 13),
    "x-hover": ("x-hover.svg", (123, 123), "hover", False, 2.25, 13),
}


def svg_text(name, theme):
    _file, (w, h), role, filled, stroke, _real = ICONS[name]
    colour = ROLES[theme][role]
    fill = colour if filled else "none"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 24 24" '
            f'fill="{fill}" stroke="{colour}" stroke-width="{stroke}" stroke-linecap="round" '
            f'stroke-linejoin="round">{GLYPHS[name]}</svg>\n')


def render_png(svg, w, h, path):
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    img = QImage(int(w), int(h), QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    side = min(w, h)
    renderer.render(p, QRectF((w - side) / 2, (h - side) / 2, side, side))
    p.end()
    if not img.save(path, "PNG"):
        raise RuntimeError(f"could not write {path}")


def build():
    written = []
    for theme, out in OUT_DIRS.items():
        os.makedirs(out, exist_ok=True)
        for name, (fname, (w, h), *_rest) in ICONS.items():
            svg = svg_text(name, theme)
            path = os.path.join(out, fname)
            if fname.endswith(".svg"):
                with open(path, "w", encoding="utf-8") as f:
                    f.write(svg)
            else:
                render_png(svg, w, h, path)
            written.append(path)
    return written


def _draw_icon(p, path, x, y, size, on_white=False):
    if on_white:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#ffffff"))
        pad = size * (0.56 if size <= 32 else 0.15)  # real size: 34 px circle round a 16 px glyph
        p.drawEllipse(QRectF(x - pad, y - pad, size + 2 * pad, size + 2 * pad))
    if path.endswith(".png"):
        pix = QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        p.drawPixmap(int(x + (size - pix.width()) / 2), int(y + (size - pix.height()) / 2), pix)
    else:
        QIcon(path).paint(p, QRect(int(x), int(y), size, size))


def contact_sheet(out_png, old_dir):
    """Rows: icon. Columns: (old | new dark set) on #0b0b14, (old | new light set) on #f7f7fb,
    each at 48 px and at the real UI size (1x and 2x)."""
    names = list(ICONS)
    row_h, label_w = 64, 150
    block = [("old", "#0b0b14"), ("dark", "#0b0b14"), ("old", "#f7f7fb"), ("light", "#f7f7fb")]
    col_w = 48 + 16 + 30 + 52 + 16
    W, H = label_w + col_w * len(block), 28 + row_h * len(names)
    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    img.fill(QColor("#20202a"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    f = QFont()
    f.setPixelSize(11)
    p.setFont(f)
    for bi, (src, bg) in enumerate(block):
        x0 = label_w + bi * col_w
        p.fillRect(x0, 0, col_w, H, QColor(bg))
        p.setPen(QColor("#888899"))
        title = {"old": "old", "dark": "new (layout/)", "light": "new (layout-light/)"}[src]
        p.drawText(QRect(x0, 4, col_w, 20), Qt.AlignCenter, f"{title} on {bg}")
    for ri, name in enumerate(names):
        fname, _wh, role, _f, _s, real = ICONS[name]
        y0 = 28 + ri * row_h
        p.setPen(QColor("#ccccd6"))
        p.drawText(QRect(6, y0, label_w - 8, row_h), Qt.AlignVCenter | Qt.AlignLeft, f"{fname}\n{real}px")
        for bi, (src, bg) in enumerate(block):
            d = old_dir if src == "old" else OUT_DIRS[src]
            path = os.path.join(d, fname)
            if not os.path.exists(path):
                continue
            x0 = label_w + bi * col_w + 8
            on_white = role == "onwhite"
            _draw_icon(p, path, x0, y0 + 8, 48, on_white)
            _draw_icon(p, path, x0 + 48 + 18, y0 + (row_h - real) / 2, real, on_white)
            _draw_icon(p, path, x0 + 48 + 18 + 30, y0 + (row_h - 2 * real) / 2, 2 * real, on_white)
    p.end()
    img.save(out_png)
    return out_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", help="also write a contact sheet PNG here")
    ap.add_argument("--old", help="folder with the previous icons for the contact sheet")
    ap.add_argument("--sheet-only", action="store_true", help="do not rebuild, only draw the sheet")
    a = ap.parse_args()
    _app = QGuiApplication(sys.argv)
    if not a.sheet_only:
        files = build()
        print(f"wrote {len(files)} files into {', '.join(OUT_DIRS.values())}")
    if a.sheet:
        print("contact sheet:", contact_sheet(a.sheet, a.old or OUT_DIRS["dark"]))


if __name__ == "__main__":
    main()
