---
trigger: always_on
description: Architecture zones, cementing rules, UI quality, crash-report workflow, devlogs, and Product Owner rules.
---

# BadWords Architecture & Rules

## 0. Product Owner, Learning & Audit Workflow
- **Language & Scenarios**: Reply in plain **Polish** using `-` only; code/comments/logs/docs/commits in **English** (`src/i18n/*.json` for UI). User is **Product Owner**, not a coder-explain via **real user-side scenarios** (clicks, screen symptoms), never dry slogans, code, or tracebacks unless asked.
- **Audit-First**: Inspect **read-only** first. Never silently delete workarounds-explain failures they prevent and ask numbered decisions first.
- **Self-Learning**: Capture PO expectations in `.agents/rules/lessons_and_standards.md` + `docs/PO_STANDARDS.md`.
- **Crash Reports (`raport/open/`)**: On every code change (unless PO opts out), check `raport/open/` (never edit `resolved/`; warn if unmounted), resolve relevant bugs (`report.json` + move to `resolved/`), and include a Polish section explaining open errors' symptoms, cause, and fix.
- **Reddit Devlogs (`r/badwordsapp`)**: After every change (unless PO opts out), use `.agents/skills/reddit-devlog/SKILL.md` -> English post in `devlogs/YYYY-MM-DD_<slug>/post.md` (EN UI PNGs ONLY when visuals changed).
- **Cementing**: Decouple modules. On closure: `# INVARIANT:`, tests, `docs/CEMENTED.md`, `[x]` in `ROADMAP_CEMENTING.md`, 3-4 word bullet in Sec. 3 (`<4,000` chars).

## 1. 3-Zone Architecture
- **Red (LOCKED)**: `src/osdoc.py`, `src/gui/components/mixins.py`, `src/api/resolve_bridge.py` - OS paths, stream buffering, hidden subprocesses, Resolve IPC.
- **Yellow (STRICT)**: `src/algorithms.py`, `src/engine/audio_engine.py`, `src/assembler.py` - `words_data[0]` metadata; `manual_status` > `algo_status`; exact frames (`24000/1001`, `30000/1001`).
- **Green (DECOUPLED)**: `src/gui/`, `src/handlers/` - Pure PySide6; never block GUI >15ms (`QThread`).

## 2. Environment Isolation
- **Dev (`.git` or `BADWORDS_DEV=1`)**: Route `settings.json`, `user.json`, `saves/`, `temp/`, `*.log` to `.dev_workspace/`; never pollute `src/`.
- **Installed**: Runtime data stays inside/next to install dir.

## 3. Cemented Modules Index (Details: `docs/CEMENTED.md`)
1. Startup & runtime guard
2. Resolve stream proxy
3. CUDA/CPU isolation
4. Frameless windows & VSync
5. Global filter debounce
6. Auto crash reporting
7. Runtime data & isolation
8. Unified UI scaling
9. i18n, vector UI & theme
10. macOS UX, Bridge & search

## 4. Coding & Verification Rules
1. **No Monoliths**: Keep subpackages focused; do not bloat `main_window.py`.
2. **License Header**: New `.py`, `.rs`, `.cpp`, `.sh` start with `#Copyright (c) 2026 Szymon Wolarz` + MIT license line.
3. **GitHub CLI**: `gh` is authenticated for issues, PRs, releases.
4. **UI & Animation**: App QSS/themes; **ZERO system emojis** (SVG/Qt icons only); dim disabled controls (`200-250ms`, `1.0 <-> 0.35`, `Qt.WA_TransparentForMouseEvents`).
5. **State & Releases**: Read `docs/DEV_STATE.md` at start; update after changes; update `src/config/release_notes.json` on releases.
6. **Empirical, Resolve & Git**: Test live. Check Resolve 21.1+ limits (`davinci-resolve-current`). Never commit `.dev_workspace/`, `settings.json`, `user.json`, `*.log`, `saves/`, `temp/`, `models/`, `venv/`, `__pycache__/`, `raport/`, `devlogs/`.
7. **Checks**: Run `python3 run_tests.py`, `python3 -m compileall src`, `_BW_AUTO_HEAL_ATTEMPTED=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -c "import gui; print('GUI OK')"`, and `cd installer && cargo check && cargo test`.
8. **Proactive UX**: Render PNGs (`tests/artifacts/`), inspect every PNG, polish UI first.
9. **VM Verification**: Verify Win11/clean-Linux changes in KVM VMs (`badwords-win11`, `badwords-linux-kde`), then give PO a short Polish checklist.
10. **Sync & Push**: Sync `src/`, `installer/`, `setupfiles/` to `/mnt/dump/BadWords FILES/`, conventional commit, `git push all <branch>`.
