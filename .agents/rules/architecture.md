---
trigger: always_on
description: Core architecture layers, non-negotiable engineering workarounds, coding commandments, and verification protocols for BadWords.
---

# BadWords Architecture & Engineering Rules

## 1. Project Overview & Architecture Layers
**BadWords** is a high-performance desktop editor tool for DaVinci Resolve timelines. It analyzes audio/video to detect silence, repetitions, filler words, and off-script lines using local Whisper AI (CTranslate2/CUDA/Apple Silicon) and heuristic algorithms, producing ripple-cut edits or markers via DRT/XML and socket IPC bridges.

### Strict Architectural Boundaries
- **Presentation (`src/gui/`)**: Pure UI rendering (PySide6). Strictly decoupled into `views/` (stacked pages), `panels/` (sidebar activities), `dialogs/` (modals), `components/` (composite editors/preview), and `widgets/` (atomic primitives). **NEVER run heavy I/O, network, or AI computations on the GUI thread.**
- **Handlers (`src/handlers/`)**: Async background task orchestrators (`QThread`). Communicates with GUI solely via Qt Signals (`Signal`).
- **Engine & API (`src/engine/`, `src/api/`)**: Pure computational workers and DaVinci Resolve socket/COM bridges. GUI-agnostic; inputs and outputs are plain data dicts/primitives.
- **Localization (`src/i18n/`)**: All user-facing strings must use `_txt(lang, key)` or `self.txt(key)`. Translations reside in `src/i18n/*.json` (11 supported languages) with fallback strictly to English (`en`).
- **Configuration (`src/config/`)**: Constants, themes, defaults (`settings_defaults.py`), and release notes (`release_notes.json`).

---

## 2. Protected Engineering Workarounds (DO NOT REMOVE)
These battle-tested patterns solve cross-platform and DaVinci Resolve environment constraints. AI agents must preserve them:
1. **Python < 3.9 PySide6 Typings Hotfix (`src/main.py`)**: Fixes `TypeError: unsupported operand type(s) for |` in embedded Python 3.8/3.9.
2. **`ResolveStreamProxy` Console Buffering (`src/osdoc.py`)**: Intercepts unbuffered stdout/stderr writes to prevent DaVinci Resolve embedded console crashes.
3. **CUDA / cuDNN DLL Dynamic Injection (`src/engine/transcription.py`, `src/engine/audio_engine.py`)**: Dynamically resolves and injects virtual environment cuBLAS/cuDNN paths into `PATH` and `sys.path` before Whisper initialization.
4. **Cross-Platform Frameless Window (`src/gui/components/mixins.py`)**: Uses `qframelesswindow` on Windows for native DWM drop shadow/Aero Snap; falls back cleanly on Linux/macOS.
5. **Global Event Filter & Hover Debounce (`src/gui/dialogs/overlay.py`)**: `GlobalAppFilter` clears focus on outside clicks and debounces tooltips (750ms) to prevent event queue pileup.

---

## 3. Mandatory AI Coding Commandments
1. **No Monoliths**: Never dump functionality into `main_window.py` or create massive single-file classes. Keep modules focused and placed in their proper subpackages.
2. **Never Block GUI Event Loop**: Any task exceeding 15ms MUST run in a `QThread` or worker handler.
3. **English Only in Code & Logs**: Variable names, comments, docstrings, terminal logs, and commit messages MUST be in English. (Translations belong solely in `src/i18n/*.json`).
4. **No Runtime Trash in Git**: Never stage or commit `settings.json`, `user.json`, `*.log`, `saves/`, `temp/`, `models/`, `venv/`, `__pycache__/`, or the scratch directory `raport/`.
5. **Self-Verification Protocol**:
   - Always run `python3 -m compileall src` after making changes.
   - Verify headless GUI imports with `QT_QPA_PLATFORM=offscreen python3 -c "import main"`.
   - If modifying Rust installer, run `cargo check` and `cargo test` before release builds.
6. **Sync Installation Folder**:
   - After any modification in `src/`, `installer/`, or `setupfiles/`, always synchronize files to `/mnt/dump/BadWords FILES/` (excluding runtime user data like `settings.json`, `user.json`, `temp/`, `models/`, `saves/`, `venv/`).
7. **Curated Release Notes on Releases**:
   - When preparing an official application **Release** (not every regular commit or internal tag), update `src/config/release_notes.json` with the critical user-facing highlights in the `"changes"` array.
8. **Automated Commit & Push**:
   - When completing a milestone, commit with conventional commit messages and push to all configured remotes (`git push all <branch>`).
