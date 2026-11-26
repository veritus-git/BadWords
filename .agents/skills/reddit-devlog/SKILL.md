---
name: reddit-devlog
description: >-
  Draft natural, editor-friendly English Reddit posts for r/badwordsapp after code changes
  or releases, saving ready-to-post Markdown drafts (plus real English-UI app screenshots
  only when UI/visual changes occurred) into gitignored devlogs/.
---

# Reddit Devlog Workflow (`r/badwordsapp`)

Use this skill after **every** code change or release in BadWords (unless the Product Owner explicitly asks to skip it).

## Output Location

Save every draft into a gitignored folder:
`devlogs/YYYY-MM-DD_<short-slug>/post.md`

If visual/UI changes were made, capture PNG screenshots into the **same** folder (`screenshot_1.png`, `screenshot_2.png`, ...) so the PO can copy-paste `post.md` and drag-and-drop the images straight into Reddit. Link `post.md` and any screenshots in your final response.

## Language, Tone & Discoverability Rules

1. **Always English**: Both the Reddit post (`post.md`) and any captured app screenshots (`gui_lang="en"`) must be in English.
2. **Real Human Voice (No Forced Persona / No Corporate Slop)**:
   - Write naturally, relaxed, and straight to the point - like an indie developer casually updating fellow video editors.
   - **NEVER** force cringey self-labels or repeated sign-offs like `"Still an 18yo solo dev..."` or `"I'm an 18-year-old developer..."`.
   - **NEVER** use corporate hype (`"We are thrilled to announce"`, `"game-changing paradigm"`, `"seamless synergy"`).
   - **NEVER** fabricate features, timings, or fixes you did not directly verify.
3. **For Editors, Not Logs**:
   - Explain what actually changes when editing videos (fewer crashes on startup, smoother timeline playback, cleaner settings, faster transcription, etc.).
   - **NEVER** paste raw tracebacks, internal symbol names, file paths (`src/...`), Win32 API calls, or commit hashes.
   - Use ASCII `-` only (never `\u2014` or `\u2013`).
4. **Format by Change Size**:
   - **Regular change / fix / single feature**: Short, punchy title + 1-3 short casual paragraphs (or 2-4 quick bullets) covering what changed and why it helps.
   - **Version release (`vX.Y.Z`)**: Slightly longer summary post with a short intro and clean `-` bullet points grouping new features, improvements, and bugfixes clearly.
5. **Natural Search Optimization (SEO)**:
   - Naturally include terms video editors actually search on Reddit/Google when relevant to the change: `BadWords`, `DaVinci Resolve` (Free / Studio), `rough cut`, `auto silence removal`, `retake / filler word detection`, `AI transcription`, `FCPXML` / `XML`, `Premiere Pro`, `Final Cut Pro`, `Windows` / `macOS` / `Linux`.
   - Keep phrasing organic - never stuff unrelated keywords.

## Screenshots Rule (Visual Changes Only)

- **Skip screenshots completely** if the change is purely internal, CLI/installer-under-the-hood, or has no visible UI difference.
- **Capture real English-UI screenshots** whenever the UI, dialogs, layout, themes, progress indicators, or visible workflows changed:
  1. Run [capture_ui.py](./scripts/capture_ui.py) with `QT_QPA_PLATFORM=offscreen` targeting the specific window/tab/dialog that changed:
     ```bash
     _BW_AUTO_HEAL_ATTEMPTED=1 BADWORDS_DEV=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen \
       python3 .agents/skills/reddit-devlog/scripts/capture_ui.py \
       --out devlogs/YYYY-MM-DD_<slug> --views <view1> <view2>
     ```
  2. For brand-new custom dialogs or states not yet wired as a named preset in `capture_ui.py`, capture the real widget via `grab().save(...)` in English (`gui_lang="en"`) with realistic non-empty sample content.
  3. Inspect **every** generated PNG with `read_file` before linking it to confirm zero clipped text, zero missing icons, and English UI labels.
