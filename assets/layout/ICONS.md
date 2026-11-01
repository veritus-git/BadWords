# UI icons

**Style:** line icons in the Lucide style. They sit on a 24-unit grid and use round caps and joins. The stroke is 2, or 1.75 for the 24 px sidebar icons. Glyphs drawn at 12-13 px use a stroke of 2.25-2.5. Play and pause are filled because they sit on the white play circle. `star-checked` is filled with the accent colour.

**Two sets with the same file names and sizes:**

- `assets/layout/` is for the dark theme. Strokes are light (`#e6e6ee`), muted (`#8b8b9e`) or hover (`#fafaff`).
- `assets/layout-light/` is for the light theme. Strokes are dark (`#2a2a3a`), muted (`#6b6b7d`) or hover (`#0b0b14`).
- Both sets use the accent `#a855f7` (violet) for `auto-marked` and `star-checked`.
- The window controls keep their blue, green and red roles. Set `NEUTRAL_WINDOW_CONTROLS` in the script to draw them in the neutral stroke colour.

**Licence:** most of the path data comes from [Lucide](https://lucide.dev) (ISC licence, © Lucide contributors; Feather parts are MIT). That covers file-pen-line, volume-off, message-square-x, house, clapperboard, settings, rewind/fast-forward, volume-*, search, copy, scissors, brush-cleaning, info, rotate-ccw, star and x. The auto-mark "A", the pause bars and the window-control glyphs were drawn for this project.

**How they are made:** every icon is defined once in `tools/brand/build_icons.py`. Run it with the app's venv python to rebuild both folders:

    python tools/brand/build_icons.py [--sheet contact.png --old <dir with previous icons>]

The script renders each PNG from SVG with QSvgRenderer into a transparent, antialiased QImage. Each PNG keeps the pixel size of the file it replaced, because the code scales them down. The `.svg` icons are written out as plain SVG with explicit colours.

The script does not touch `splashscreen.png` or `badwords-welcome-branding.svg`.
