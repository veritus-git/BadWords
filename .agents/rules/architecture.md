---
trigger: always_on
description: Architecture zones, cementing rules, UI quality, verification, and Product Owner workflow.
---

# BadWords Architecture & Rules

## 0. Product Owner & Audit Workflow
- **Language**: Reply in **Polish**; code, names, comments, logs, docs, commits in **English** (`src/i18n/*.json` for UI).
- **Zero-Jargon**: User is **Product Owner**, not a coder. Explain via user-visible behavior in plain Polish. **Never show code, class/function names, or tracebacks** unless asked.
- **Audit-First**: Inspect targets **read-only** first. Never silently delete workarounds—explain why they exist and ask numbered decisions before editing.
- **Cementing**: Decouple modules for future features. Once approved: add `# INVARIANT:` comments, regression tests, full docs in `docs/CEMENTED.md`, and **only a 3–4 word bullet** in Sec. 3 below (keep this file **<4,000 chars**).

## 1. 3-Zone Architecture
- **Red (LOCKED)**: `src/osdoc.py`, `src/gui/components/mixins.py`, `src/api/resolve_bridge.py` — OS paths, stream buffering, hidden subprocesses, Resolve IPC.
- **Yellow (STRICT)**: `src/algorithms.py`, `src/engine/audio_engine.py`, `src/assembler.py` — `words_data[0]` holds metadata; `manual_status` > `algo_status`; exact frame math (`24000/1001`, `30000/1001`).
- **Green (DECOUPLED)**: `src/gui/`, `src/handlers/` — Pure PySide6; never block GUI >15ms (`QThread`).

## 2. Environment Isolation
- **Dev (`.git` or `BADWORDS_DEV=1`)**: Route `settings.json`, `user.json`, `saves/`, `temp/`, `*.log` to `.dev_workspace/`; never pollute `src/`.
- **Installed**: Runtime data stays inside/next to install dir.

## 3. Cemented Modules Index (Details: `docs/CEMENTED.md`)
1. Python <3.9 typings
2. Resolve stream proxy
3. CUDA/CPU isolation
4. Frameless window mixin
5. Global filter debounce

## 4. Coding & Verification Rules
1. **No Monoliths**: Keep subpackages focused; do not bloat `main_window.py`.
2. **License Header**: New `.py`, `.rs`, `.cpp`, `.sh` (and requested docs) start with `#Copyright (c) 2026 Szymon Wolarz` + MIT license line.
3. **GitHub CLI**: `gh` is authenticated for issues, PRs, releases.
4. **UI & Animation**: App QSS/themes; **ZERO system emojis** (SVG/Qt icons only); dim disabled controls (`200–250ms`, `1.0 <-> 0.35`, `Qt.WA_TransparentForMouseEvents`).
5. **State & Releases**: Log progress in `docs/DEV_STATE.md`; update `src/config/release_notes.json` on releases.
6. **Empirical & Git**: Verify empirically. Never commit `.dev_workspace/`, `settings.json`, `user.json`, `*.log`, `saves/`, `temp/`, `models/`, `venv/`, `__pycache__/`, `raport/`.
7. **Checks**: Run `python3 run_tests.py`, `python3 -m compileall src`, `_BW_AUTO_HEAL_ATTEMPTED=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -c "import gui; print('GUI OK')"`, and in `installer/`: `cargo check && cargo test`.
8. **Visual Check**: GUI changes MUST render PNGs (`tests/artifacts/` or `raport/screenshots/`); inspect every PNG yourself before reporting.
9. **Sync & Push**: Sync `src/`, `installer/`, `setupfiles/` to `/mnt/dump/BadWords FILES/`, conventional commit, `git push all <branch>`.
