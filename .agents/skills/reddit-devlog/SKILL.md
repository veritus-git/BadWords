---
name: reddit-devlog
description: >-
  Draft natural, editor-friendly English Reddit posts for r/BadWordsApp after code changes
  or releases, saving ready-to-post Markdown drafts (plus real English-UI app screenshots
  only when UI/visual changes occurred) into gitignored devlogs/.
---

# Reddit Devlog Workflow (`r/BadWordsApp`)

Use this skill after **every** code change or release in BadWords (unless the Product Owner explicitly asks to skip it).

## Output Location

Save every draft into a gitignored folder:
`devlogs/YYYY-MM-DD_<short-slug>/post.md`

Only if visual/UI changes were made, capture PNG screenshots into the **same** folder (`screenshot_1.png`, ...). Link `post.md` and any screenshots in your final response.

## Critical Framing: Released vs Unreleased

Always check whether the change is **actually released** in a downloadable tag (`git describe --tags --exact-match HEAD` or `HEAD` vs latest tag):
- **If released (tagged release like `v4.1.1`)**: Write as an available update users can grab right now (can be slightly longer with clean `-` bullet points).
- **If NOT released yet (dev commits ahead of the latest tag)**: **Explicitly say up front** that these fixes/features are **coming in the next update** / **upcoming patch** and are not out to download yet. Never imply users can already see or download unreleased dev changes.

## Tone, Length & Discoverability Rules

1. **Always English & Keep It Short**:
   - Both `post.md` and screenshots (`gui_lang="en"`) must be in English.
   - Regular change devlogs must be **short and punchy** (~70-160 words: quick intro + 2-5 concise one-line bullets). Never dump walls of text.
   - Only full version releases (`vX.Y.Z`) should be slightly longer with grouped `-` bullets.
2. **Real Human Voice (Zero Cringe / Zero Corporate Slop)**:
   - Write casually and naturally, like an indie dev updating fellow video editors.
   - **NEVER** force repeated self-labels or sign-offs like `"Still an 18yo solo dev..."` or `"I'm an 18-year-old developer..."`.
   - **NEVER** use corporate hype (`"We are thrilled to announce"`, `"game-changing"`, `"seamless"`).
   - **NEVER** fabricate features or improvements you did not verify.
3. **For Video Editors, Zero Technical Clutter**:
   - Describe what changes in actual editing (fewer crashes, smoother timeline scrub, cleaner popups, faster search).
   - **NEVER** mention internal symbols, function/file names, Qt/Win32/Cocoa internals, debouncing/caching mechanics, SHA fingerprints, or raw tracebacks.
   - Use ASCII `-` only (never `\u2014` or `\u2013`).
4. **Natural Search Optimization (SEO)**:
   - Naturally weave in terms editors search on Reddit/Google when relevant: `BadWords`, `DaVinci Resolve` (Free / Studio), `rough cut`, `silence removal`, `filler words`, `retakes`, `AI transcription`, `FCPXML` / `XML`, `Premiere Pro`, `Final Cut Pro`, `Windows` / `macOS` / `Linux`. Never keyword-stuff.

## Screenshots Rule (Visual Changes Only)

- **Skip screenshots completely** if the change has no visible UI difference (bugfixes under the hood, stability, Bridge/IPC, backend, performance). Never attach old unrelated dialogs just to fill space.
- **Capture real English-UI screenshots** only when the UI/visuals changed:
  1. Run [capture_ui.py](./scripts/capture_ui.py) with `QT_QPA_PLATFORM=offscreen` targeting the specific view that changed:
     ```bash
     _BW_AUTO_HEAL_ATTEMPTED=1 BADWORDS_DEV=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen \
       python3 .agents/skills/reddit-devlog/scripts/capture_ui.py \
       --out devlogs/YYYY-MM-DD_<slug> --views <view1> <view2>
     ```
  2. Inspect **every** generated PNG with `read_file` to verify crisp English text and zero clipping.
