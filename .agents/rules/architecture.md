---
name: BadWords Architecture & Rules
description: Guidelines and architectural mapping for modifying the BadWords codebase. AI Agents MUST follow this when modifying the project.
---

# BadWords Architecture & Rules

## Project Overview
BadWords is an application for analyzing audio/video transcripts and finding bad words/segments (using `algorithms.py`), rendering audio waveforms (`audio_preview.py`), and managing project workspaces (`osdoc.py`). It integrates heavily with DaVinci Resolve via an API handler.

## Core Architectural Principle
The project has recently undergone **Phase 1 of Structural Refactoring**. The codebase is strictly layered. 
**NEVER INTRODUCE MONOLITHIC CLASSES.** Keep the GUI strictly separated from Business Logic.

## Directory Structure & Responsibilities

### 1. `src/gui/` - Presentation Layer (Strictly UI)
This layer contains ONLY visual elements and PySide6 UI logic. It must **not** perform heavy processing, file I/O, or blocking tasks.
- `main_window.py`: The entry point for the GUI. Acts as a composer/director. It wires signals and slots between components but delegates heavy logic to `handlers/`.
- `components/`: Large, autonomous UI modules (e.g., `dialogs.py` for settings, `audio_preview.py`, `transcription_canvas.py`).
- `widgets/`: Small, reusable, stateless UI primitives (e.g., custom `buttons.py`, `sliders.py`, `text_edits.py`).
- `utils.py`: Purely visual utilities (icon loading, color manipulation, UI fonts).

### 2. `src/handlers/` - Business Logic Layer
This layer handles background threads, complex state management, and file saving.
- `analysis_worker.py`: QThread that runs the transcription and AI models in the background to prevent GUI freezing.
- `autosave_manager.py`: Manages the debounced autosaving of workspace recovery files (`recovery.bws`).
- `undo_manager.py`: Manages the history stack (Undo/Redo up to 50 states).

### 3. `src/engine/` - AI & Audio Processing
- `audio_engine.py` / `audio_extraction.py`: FFmpeg integrations and audio processing.
- `transcription.py`: Communication with external transcription AI models.

### 4. `src/config/` - Configuration & Constants
- Global parameters, palette configs, default settings, and supported languages. **Do not hardcode constants in the GUI logic.** Always map them to `config/`.

### 5. Root Modules (`src/`)
- `algorithms.py`: Contains complex text alignment, fuzzy matching, and transcript sanitation logic.
- `osdoc.py`: Project file management, zipping/unzipping workspaces.
- `main.py`: The main entry point. Sets up exception handling, loads config, and initializes the `BadWordsGUI`.

## Coding Rules for AI Agents
1. **No Logic in `__init__.py`**: Python `__init__.py` files should strictly be used for exporting (`from .xyz import ABC`) and package declarations. Do not write business logic or classes inside them.
2. **DRY (Don't Repeat Yourself)**: If you notice duplicate UI components or event filters, extract them into `mixins.py` or `utils.py`.
3. **Event Loop Safety**: Never block the Qt Event Loop. Use QTimer or QThread (`handlers/analysis_worker.py`) for I/O operations or algorithmic computations.
4. **Localization (i18n)**: Do not hardcode user-facing strings. Always use `get_trans(key)` from `i18n.__init__`.
5. **English Only Descriptions**: All python module docstrings MUST be written in English. Do NOT inject Polish instructions in codebase comments or docstrings.
6. **Self-Updating Documentation**: You MUST update this `architecture.md` file whenever you introduce new files, refactor architecture, or create major functions. Ensure this map is always up-to-date with reality.
7. **Commit & Push Protocol**: You MUST commit your changes and always push them to all remotes (e.g., `git push all <branch>`) when completing a task or milestone.
8. **Testing Etiquette (No Trash)**: Do not run `main.py` directly in the repository unless absolutely necessary. Running `main.py` generates the following runtime files and folders that must NEVER be committed:
   - `src/settings.json` (user settings, auto-generated)
   - `src/user.json` (user UUID/telemetry data, auto-generated)
   - `src/badwords_debug.log` (debug log, auto-generated)
   - `src/saves/` (autosave workspace history)
   - `src/temp/` (temporary processing files)
   - `src/models/` (downloaded AI models)
   - `__pycache__/` directories (Python bytecode cache)
   - `.fuse_hidden*` files (zombie process artifacts)
   If you must run `main.py`, clean up ALL of the above afterwards (`find src -type d -name "__pycache__" -exec rm -rf {} +`) and verify with `git status` that none of these appear in staged changes.
