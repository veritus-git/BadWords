# StoryCraft brand

StoryCraft is a fork of [BadWords](https://github.com/veritus-git/BadWords) by Szymon Wolarz (MIT). The original copyright notices and licence stay in place; this identity only covers the fork's name and look.

## Mark
An **S** drawn as one continuous stroke (a story arc), cut across by three timeline clips with a playhead: the interview becomes a story through editing. It sits on a dark rounded tile with a thin cyan→violet rim.

| File | Use |
|---|---|
| `assets/brand/storycraft-mark.svg` | App mark, colour, on its tile |
| `assets/brand/storycraft-mark-mono.svg` | Greyscale |
| `assets/brand/storycraft-mark-light.svg` | Dark S on a white tile |
| `assets/brand/storycraft-mark-white.svg` | White S on the dark tile |
| `assets/brand/storycraft-glyph.svg` | The S alone, no tile, on transparent |
| `assets/brand/favicon.svg`, `favicon.ico` | 16–48 px: the S with one clip, no playhead |
| `assets/brand/png/` | Web icons (180, 192, 512 px) |
| `assets/icons/icon_*.{png,ico,icns}` | App icons; same names the app already uses (default, monochrome, white, whiteb) |

Keep clear space of at least a quarter of the tile's width around the mark. Don't recolour the S outside the four variants, and don't add effects.

## Wordmark
**Story** in white (or ink on light backgrounds), **Craft** in the brand gradient, set in **Outfit SemiBold**, as one word with no space. The SVGs are outlined, so they don't depend on the font being installed.

- `storycraft-wordmark.svg` / `storycraft-wordmark-light.svg`
- Lockup with the mark and "FOR DAVINCI RESOLVE" (Outfit Medium, wide tracking): `storycraft-lockup.svg` / `storycraft-lockup-light.svg`

## Colours
| | Hex | Use |
|---|---|---|
| Cyan | `#22d3ee` | Gradient start, the story arc's beginning |
| Violet | `#a855f7` | Gradient end |
| Ink | `#0b0b14` | Tile and splash background |
| Muted | `#a1a3bd` | Taglines on dark |

The gradient always runs cyan → violet, left to right or top-left to bottom-right. The brand colours stay fixed; the app's colour themes (Classic, Graphite, Midnight, Studio) only change the working interface.

## Type
- **Outfit**: wordmark and brand moments.
- Interface: the theme's font (Inter, Geist or Manrope; Ubuntu Sans in Classic).

All fonts are under the SIL Open Font License (`assets/fonts/OFL-*.txt`).

## Rebuilding
Everything above is generated from one definition:

```
python tools/brand/build_brand.py
```

Run it with the app's venv Python on a normal desktop session; Qt's offscreen mode can't load the font.
