# StoryCraft website

The StoryCraft website: plain HTML, CSS and JavaScript, no build step, no libraries, no tracking, no third-party requests (fonts and images are in `assets/`).

- Preview: `python3 -m http.server 8765 --bind 127.0.0.1` in this folder, then open http://127.0.0.1:8765
- Publish: every push to `fork` that touches `website/` runs `.github/workflows/pages.yml`, which publishes this folder (without this README) to GitHub Pages. The site uses relative paths only, so any static host works too.
- Link to one workflow step: `?step=1` to `?step=4`.
- After changing `styles.css` or `app.js`, raise the `?v=` number on their links in `index.html` so browsers fetch the new files.
- Fonts: Outfit and Inter, SIL Open Font License (`assets/fonts/OFL-*.txt`). Brand files come from `assets/brand` in this repo (see BRAND.md).
- Screenshots: `assets/shots/*.jpg` are what the site shows (1920 x 1080 web versions; Settings 1400 x 889), captures of the real app with an invented interview. After replacing a file in `assets/shots`, raise `SHOTS_V` in `app.js` (and the `?v=` on the first image in `index.html`), or browsers keep showing the old picture.
