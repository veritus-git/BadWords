#!/usr/bin/env python3
"""
StoryCraft brand builder: writes the SVG mark, wordmark and lockup, the favicon and every app
icon variant from one definition. Run with the app's venv python (needs PySide6):

    python tools/brand/build_brand.py

Outputs: assets/brand/*.svg, assets/brand/favicon.ico, assets/brand/png/*, and
assets/icons/icon_{default,monochrome,white,whiteb}{.png,_nobg.png,.ico,.icns}.
"""
import os
import struct
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BRAND = os.path.join(ROOT, "assets", "brand")
ICONS = os.path.join(ROOT, "assets", "icons")
FONT = os.path.join(ROOT, "assets", "fonts", "Outfit-Variable.ttf")

CYAN, VIOLET, INK = "#22d3ee", "#a855f7", "#0b0b14"

# The S: one continuous stroke, a story arc that doubles as a monogram (512 x 512 grid)
S_PATH = ("M 344 148 C 322 116 288 102 252 102 C 198 102 164 134 164 178 C 164 226 204 242 256 256 "
          "C 308 270 348 288 348 336 C 348 382 312 410 260 410 C 218 410 186 394 166 362")
# Timeline clips laid over the S, staggered like an edit, and the playhead
BARS = [(190, 210, 150, "bar"), (128, 246, 196, "hot"), (204, 282, 150, "bar")]  # x, y, width, kind
BAR_H = 17
PLAYHEAD_X = 292


def mark_svg(variant="default", tile=True, size=512, small=False):
    """variant: default (gradient on ink), monochrome (greys on ink), white (ink on white), whiteb (white on ink).
    small: the 16-32 px version (favicon): the S and one clip, no playhead."""
    tile_fill = {"default": "url(#tile)", "monochrome": "url(#tile)", "white": "#ffffff", "whiteb": "url(#tile)"}[variant]
    s_stroke = {"default": "url(#arc)", "monochrome": "#d4d4d8", "white": INK, "whiteb": "#ffffff"}[variant]
    bar = {"default": "#d9dbee", "monochrome": "#8b8b95", "white": "#9a9db4", "whiteb": "#c4c6dc"}[variant]
    hot = {"default": "url(#hot)", "monochrome": "#e4e4e7", "white": "#4b4f6b", "whiteb": "#ffffff"}[variant]
    head = {"default": "#ffffff", "monochrome": "#ffffff", "white": INK, "whiteb": "#ffffff"}[variant]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 512 512">',
             "<title>StoryCraft</title>",
             "<defs>",
             f'<linearGradient id="arc" x1="164" y1="102" x2="348" y2="410" gradientUnits="userSpaceOnUse">'
             f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
             f'<linearGradient id="hot" x1="112" y1="0" x2="348" y2="0" gradientUnits="userSpaceOnUse">'
             f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
             '<linearGradient id="tile" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">'
             '<stop offset="0" stop-color="#1a1b2e"/><stop offset="1" stop-color="#0b0b14"/></linearGradient>',
             '<linearGradient id="rim" x1="0" y1="0" x2="512" y2="512" gradientUnits="userSpaceOnUse">'
             f'<stop offset="0" stop-color="{CYAN}" stop-opacity="0.55"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0.55"/></linearGradient>',
             "</defs>"]
    if tile:
        parts.append(f'<rect x="8" y="8" width="496" height="496" rx="116" fill="{tile_fill}"/>')
        if variant != "white":
            parts.append('<rect x="9.5" y="9.5" width="493" height="493" rx="114.5" fill="none" stroke="url(#rim)" stroke-width="3"/>')
        else:
            parts.append('<rect x="9.5" y="9.5" width="493" height="493" rx="114.5" fill="none" stroke="#e4e4e7" stroke-width="3"/>')
    parts.append(f'<path d="{S_PATH}" fill="none" stroke="{s_stroke}" stroke-width="54" stroke-linecap="round" stroke-linejoin="round"/>')
    # Clips sit on top of the S with a thin tile-coloured gap, so the S reads as "cut"
    gap = None if not tile else ("#ffffff" if variant == "white" else "#11121f")
    bars = [(128, 240, 256, "hot")] if small else BARS
    bar_h = 32 if small else BAR_H
    for x, y, w, kind in bars:
        if gap:
            parts.append(f'<rect x="{x - 5}" y="{y - 5}" width="{w + 10}" height="{bar_h + 10}" rx="{(bar_h + 10) / 2}" fill="{gap}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{bar_h}" rx="{bar_h / 2}" fill="{hot if kind == "hot" else bar}"/>')
    if not small:
        if gap:
            parts.append(f'<rect x="{PLAYHEAD_X - 5}" y="176" width="10" height="150" rx="5" fill="{gap}"/>')
        parts.append(f'<rect x="{PLAYHEAD_X - 3}" y="180" width="6" height="142" rx="3" fill="{head}"/>')
        ring = f' stroke="{gap}" stroke-width="5"' if gap else ""
        parts.append(f'<circle cx="{PLAYHEAD_X}" cy="174" r="11" fill="{head}"{ring}/>')
    parts.append("</svg>")
    return "\n".join(parts)


def _text_path(text, family, weight, px, x=0.0, y=0.0):
    """Outline text with Qt (so the SVG doesn't depend on installed fonts). Returns (svg d, advance)."""
    from PySide6.QtGui import QFont, QPainterPath, QFontMetricsF
    f = QFont(family)
    f.setPixelSize(px)
    f.setWeight(QFont.Weight(weight))
    path = QPainterPath()
    path.addText(x, y, f, text)
    d, i, n = [], 0, path.elementCount()
    while i < n:
        e = path.elementAt(i)
        if e.type == QPainterPath.ElementType.MoveToElement:
            d.append(f"M{e.x:.2f} {e.y:.2f}"); i += 1
        elif e.type == QPainterPath.ElementType.LineToElement:
            d.append(f"L{e.x:.2f} {e.y:.2f}"); i += 1
        else:  # cubic: CurveTo + 2 CurveToData
            c1, c2 = path.elementAt(i + 1), path.elementAt(i + 2)
            d.append(f"C{e.x:.2f} {e.y:.2f} {c1.x:.2f} {c1.y:.2f} {c2.x:.2f} {c2.y:.2f}"); i += 3
    return " ".join(d) + " Z", QFontMetricsF(f).horizontalAdvance(text)


def wordmark_parts(on_dark=True, px=120, x0=0.0, baseline=0.0):
    """'Story' solid + 'Craft' in the gradient. Returns (svg elements, width)."""
    story_d, story_w = _text_path("Story", "Outfit", 600, px, x0, baseline)
    craft_d, craft_w = _text_path("Craft", "Outfit", 600, px, x0 + story_w, baseline)
    solid = "#ffffff" if on_dark else INK
    els = [f'<linearGradient id="craft" x1="{x0 + story_w:.1f}" y1="0" x2="{x0 + story_w + craft_w:.1f}" y2="0" gradientUnits="userSpaceOnUse">'
           f'<stop offset="0" stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
           f'<path d="{story_d}" fill="{solid}"/>', f'<path d="{craft_d}" fill="url(#craft)"/>']
    return els, story_w + craft_w


def wordmark_svg(on_dark=True):
    px = 120
    els, w = wordmark_parts(on_dark, px, 0, px * 0.86)
    h = px * 1.1
    defs = [e for e in els if e.startswith("<linearGradient")]
    body = [e for e in els if not e.startswith("<linearGradient")]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 0 {w + 8:.0f} {h:.0f}" width="{w + 8:.0f}" height="{h:.0f}">'
            f'<title>StoryCraft</title><defs>{"".join(defs)}</defs>{"".join(body)}</svg>')


def lockup_svg(on_dark=True):
    """Mark + wordmark + 'FOR DAVINCI RESOLVE'."""
    mark = mark_svg("default" if on_dark else "white").split("</defs>", 1)
    mark_defs = mark[0].split("<defs>", 1)[1]
    mark_body = mark[1].replace("</svg>", "")
    px = 120
    els, w = wordmark_parts(on_dark, px, 300, 170)
    tag_d, tag_w = _text_path("F O R   D A V I N C I   R E S O L V E", "Outfit", 500, 30, 304, 226)
    defs = mark_defs + "".join(e for e in els if e.startswith("<linearGradient"))
    body = "".join(e for e in els if not e.startswith("<linearGradient"))
    width = 300 + max(w, tag_w) + 12
    muted = "#a1a3bd" if on_dark else "#5b5e78"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} 256" width="{width:.0f}" height="256">'
            f'<title>StoryCraft for DaVinci Resolve</title><defs>{defs}</defs>'
            f'<g transform="scale(0.5)">{mark_body}</g>{body}<path d="{tag_d}" fill="{muted}"/></svg>')


def _render(svg_text, size, path):
    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtGui import QImage, QPainter, QColor
    from PySide6.QtSvg import QSvgRenderer
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(QColor(0, 0, 0, 0))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    QSvgRenderer(QByteArray(svg_text.encode())).render(p, QRectF(0, 0, size, size))
    p.end()
    img.save(path)


def _write_ico(pngs, path):
    """ICO with PNG-compressed entries (Windows Vista and later)."""
    blobs = [open(p, "rb").read() for _, p in pngs]
    header = struct.pack("<HHH", 0, 1, len(blobs))
    offset = 6 + 16 * len(blobs)
    entries = b""
    for (size, _), blob in zip(pngs, blobs):
        s = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", s, s, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    with open(path, "wb") as f:
        f.write(header + entries + b"".join(blobs))


def build():
    from PySide6.QtGui import QGuiApplication, QFontDatabase
    app = QGuiApplication.instance() or QGuiApplication([])
    if QFontDatabase.addApplicationFont(FONT) < 0:
        sys.exit("Outfit font could not be loaded (needs a real Qt platform, not offscreen)")
    os.makedirs(os.path.join(BRAND, "png"), exist_ok=True)
    files = {
        "storycraft-mark.svg": mark_svg("default"),
        "storycraft-mark-mono.svg": mark_svg("monochrome"),
        "storycraft-mark-light.svg": mark_svg("white"),
        "storycraft-mark-white.svg": mark_svg("whiteb"),
        "storycraft-glyph.svg": mark_svg("default", tile=False),
        "favicon.svg": mark_svg("default", small=True),
        "storycraft-wordmark.svg": wordmark_svg(True),
        "storycraft-wordmark-light.svg": wordmark_svg(False),
        "storycraft-lockup.svg": lockup_svg(True),
        "storycraft-lockup-light.svg": lockup_svg(False),
    }
    for name, svg in files.items():
        with open(os.path.join(BRAND, name), "w", encoding="utf-8") as f:
            f.write(svg + "\n")
    # Favicon + web icons
    tmp = tempfile.mkdtemp()
    fav = []
    for s in (16, 32, 48):
        p = os.path.join(tmp, f"fav{s}.png")
        _render(mark_svg("default", small=s <= 32), s, p)
        fav.append((s, p))
    _write_ico(fav, os.path.join(BRAND, "favicon.ico"))
    for s, name in ((180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")):
        _render(mark_svg("default"), s, os.path.join(BRAND, "png", name))
    # App icons, same file names the app already looks for
    for v in ("default", "monochrome", "white", "whiteb"):
        _render(mark_svg(v), 1024, os.path.join(ICONS, f"icon_{v}.png"))
        _render(mark_svg(v, tile=False), 2048, os.path.join(ICONS, f"icon_{v}_nobg.png"))
        ico = []
        for s in (16, 24, 32, 48, 64, 128, 256):
            p = os.path.join(tmp, f"{v}_{s}.png")
            _render(mark_svg(v, small=s <= 32), s, p)
            ico.append((s, p))
        _write_ico(ico, os.path.join(ICONS, f"icon_{v}.ico"))
        iconset = os.path.join(tmp, f"{v}.iconset")
        os.makedirs(iconset)
        for s in (16, 32, 128, 256, 512):
            _render(mark_svg(v, small=s <= 16), s, os.path.join(iconset, f"icon_{s}x{s}.png"))
            _render(mark_svg(v, small=s * 2 <= 32), s * 2, os.path.join(iconset, f"icon_{s}x{s}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", iconset, "-o", os.path.join(ICONS, f"icon_{v}.icns")], check=True)
    print("brand written:", sorted(os.listdir(BRAND)))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--drafts":
        out = sys.argv[2]
        for v in ("default", "monochrome", "white", "whiteb"):
            open(os.path.join(out, f"draft_{v}.svg"), "w").write(mark_svg(v))
        open(os.path.join(out, "draft_small.svg"), "w").write(mark_svg("default", small=True))
    else:
        build()
