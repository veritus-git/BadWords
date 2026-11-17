---
trigger: always_on
description: Core architecture layers, 3-zone boundaries, protected workarounds, test protocols, and task tracking rules for BadWords.
---

# BadWords Architecture & Engineering Rules

## 1. 3-Zone Architecture & Responsibilities
- **Red Zone (System Plumbing & Bridge - LOCKED)**: `src/osdoc.py`, `src/gui/components/mixins.py`, `src/api/resolve_bridge.py`.
  * Handles OS path resolution, headless console buffering, subprocess window suppression, and DaVinci Resolve socket IPC.
  * Changes require extreme scrutiny; do not refactor without explicit justification.
- **Yellow Zone (Algorithms & Data Contracts - STRICT)**: `src/algorithms.py`, `src/engine/audio_engine.py`, `src/assembler.py`.
  * Invariant: `words_data[0]` must preserve all metadata (`meta_global_silence`, session tags).
  * Invariant: Two-layer status priority (`manual_status` set by user always overrides `algo_status` and is never overwritten by repeat or filler passes).
  * Exact frame-rate math (e.g. 23.976 -> 24000/1001, 29.97 -> 30000/1001).
- **Green Zone (Presentation & UI - DECOUPLED)**: `src/gui/` (`views/`, `panels/`, `dialogs/`, `components/`, `widgets/`), `src/handlers/`.
  * Pure PySide6 rendering. Never run tasks >15ms on the GUI thread; offload to `QThread`.

---

## 2. Environment Isolation: DEV vs INSTALLED
- **Dev Mode (`.git` detected or `BADWORDS_DEV=1`)**:
  * All runtime data (`settings.json`, `user.json`, `saves/`, `temp/`, `badwords_debug.log`) MUST route to `.dev_workspace/` in repo root.
  * Running tests or `main.py` directly from source must NEVER litter `src/`.
- **Installed Mode (Portable / End-User)**:
  * Runtime data lives locally inside/next to the installation directory.

---

## 3. Protected Engineering Workarounds (DO NOT REMOVE)
1. **Python < 3.9 PySide6 Typings Hotfix (`src/main.py`)**: Fixes `TypeError: unsupported operand type(s) for |` in embedded 3.8/3.9.
2. **`ResolveStreamProxy` Console Buffering (`src/osdoc.py`)**: Intercepts unbuffered stdout/stderr to prevent Resolve console crashes.
3. **CUDA / cuDNN Dynamic Injection (`src/engine/transcription.py`, `src/engine/audio_engine.py`)**: Injects venv cuBLAS/cuDNN paths before Whisper init.
4. **Cross-Platform Frameless Window (`src/gui/components/mixins.py`)**: Uses `qframelesswindow` on Windows; clean fallback on Linux/macOS.
5. **Global Event Filter & Hover Debounce (`src/gui/dialogs/overlay.py`)**: `GlobalAppFilter` clears focus on outside clicks; 750ms tooltip debounce.

---

## 4. Mandatory AI Coding Commandments
1. **No Monoliths**: Keep modules focused in their proper subpackages. Do not bloat `main_window.py`.
2. **English Only**: Code, variable names, comments, terminal logs, and git commits must be in English. Translations go in `src/i18n/*.json`.
3. **Continuous State Tracking (`docs/DEV_STATE.md`)**:
   * Record task progress, changes made, and pending steps in `docs/DEV_STATE.md` progressively (not just at session end) so multi-turn context is never lost.
4. **Empirical Verification (No Guesswork)**:
   * Never guess APIs or behavior ("co mi się wydaje"). Verify against official docs, codebase inspection, or minimal reproduction scripts before committing.
5. **No Runtime Trash in Git**: Never commit `.dev_workspace/`, `settings.json`, `user.json`, `*.log`, `saves/`, `temp/`, `models/`, `venv/`, `__pycache__/`, or `raport/`.
6. **Mandatory Verification Protocol**:
   * Run automated tests: `python3 run_tests.py` (ALL tests must pass).
   * Run bytecode compilation: `python3 -m compileall src`.
   * Verify headless GUI import: `_BW_AUTO_HEAL_ATTEMPTED=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -c "import gui; print('GUI OK')"`.
   * If modifying Rust installer: `cargo check` and `cargo test`.
7. **Sync Installation Folder**:
   * After any change in `src/`, `installer/`, or `setupfiles/`, synchronize to `/mnt/dump/BadWords FILES/` (excluding runtime user data).
8. **Curated Release Notes on Releases**:
   * When preparing an official Release, update `src/config/release_notes.json`.
9. **Automated Commit & Push**:
   * Commit with conventional commit messages and push to all configured remotes (`git push all <branch>`).
