# BadWords Development State & Task Tracking

> **Status**: Active  
> **Last Updated**: 2026-11-17  
> **Active Environment**: Development Workspace (`.dev_workspace/`)  

---

## 1. Architectural Zones Status

| Zone | Path | Responsibility | Status |
| :--- | :--- | :--- | :--- |
| **Red Zone** | `src/osdoc.py`, `src/gui/components/mixins.py`, `src/api/resolve_bridge.py` | System plumbing, OS paths, stream buffering, DaVinci IPC | **Locked & Protected** |
| **Yellow Zone** | `src/algorithms.py`, `src/engine/audio_engine.py`, `src/assembler.py` | Repeat/retake detection, cut calculations, FCP7 XML assembly | **Tested & Validated** |
| **Green Zone** | `src/gui/` (`views/`, `panels/`, `widgets/`, `components/`, `dialogs/`) | PySide6 presentation layer | **Decoupled & Non-blocking** |

---

## 2. Environment Isolation

- **Development Mode**:
  - Automatically detected via `.git` folder in workspace root or `BADWORDS_DEV=1`.
  - All runtime outputs (`settings.json`, `user.json`, `saves/`, `temp/`, `badwords_debug.log`) are isolated into `.dev_workspace/`.
  - Running `main.py` directly from source never pollutes `src/`.
- **Installed Mode**:
  - End-user / portable deployment.
  - Runtime files reside locally within the installation directory (`BadWords FILES/`).

---

## 3. Automated Test Suite (`python3 run_tests.py`)

Test Runner: `run_tests.py` using Python `unittest`.

| Test Module | Coverage | Status |
| :--- | :--- | :--- |
| `tests/test_visual_progress_bar.py` | Visual regression test for `LiquidProgressBar`: renders screenshots into `tests/artifacts/`, verifies all 4 rounded corners and anti-aliasing clipping across determinate (50%, 100%) and 3-phase indeterminate states (entering, centered, exiting) to prevent squared-off corner regressions (`setClipRect`). | **PASS** |
| `tests/test_timeline_cuts.py` | Multi-framerate calculation across standard & drop rates (23.976, 29.97, 47.952, 59.94, 60.0, 25.0 fps), exact rational drop-frame timebases (24000/1001, 30000/1001), silence cut ripple deletion, color cut extraction, timeline end capping. | **PASS** |
| `tests/test_algorithms.py` | Heuristic repetition/retake detection, 2-layer visual priority (`manual_status` > `algo_status` across both repeat and auto-filler passes), fuzzy string comparison. | **PASS** |
| `tests/test_assembler_xml.py` | Final Cut Pro 7 XML generation (`<xmeml version="5">`), XML schema and frame accuracy validation. | **PASS** |
| `tests/test_data_contracts.py` | Invariant preservation of `words_data[0]` metadata (`meta_global_silence`, session tags, custom metadata), required word keys, empty dataset safety. | **PASS** |

---

## 4. Completed Milestone Record

1. **Repository Cleanup**:
   - Removed stale runtime files from `src/` (`src/settings.json`, `src/user.json`, `src/saves/`, `src/temp/`).
   - Removed rogue directory `"` inadvertently created by misquoted script commands.
   - Removed stale empty `src/models/` and added dev-mode routing in `AudioEngine` to prevent recreating it in `src/`.
   - Updated `.gitignore` to ignore `.dev_workspace/`, `workspace_data/`, and `tests/artifacts/`.
2. **DEV vs INSTALLED Separation**:
   - Implemented `_detect_dev_mode()` in `src/osdoc.py`.
   - Configured runtime data isolation into `.dev_workspace/` when in development mode.
   - Updated `src/main.py`, `src/gui/main_window.py`, `src/gui/utils.py`, `src/gui/dialogs/settings_dialog.py`, and `src/engine/audio_engine.py` to route through `os_doc.settings_file`, `os_doc.saves_dir`, and `os_doc.log_file`.
   - Implemented automatic migration of legacy config, saves, and temp from `src/` to `.dev_workspace/`.
3. **Automated Test Suite**:
   - Created test framework in `tests/` and test runner `run_tests.py`.
   - 17 comprehensive unit & visual regression tests implemented and passing.
4. **AI Codex & Rules Update**:
   - Updated `.agents/rules/architecture.md` with 3-Zone architecture, empirical verification rule, progressive task tracking, and token budget efficiency.
   - Established persistent task state tracking via `docs/DEV_STATE.md`.

---

## 5. Next Steps for Incoming Reviewer / Developer

1. Run `python3 run_tests.py` to verify all 17 tests pass.
2. Run `python3 -m compileall src` to ensure bytecode consistency.
3. Check `tests/artifacts/` for visual progress bar screenshots.
4. Synchronize modified files to `/mnt/dump/BadWords FILES/` as per rule 6.

