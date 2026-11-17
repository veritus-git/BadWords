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
| `tests/test_host_env_fixes.py` | Regression suite for school PC environment crashes: DaVinci Resolve wrapper generation syntax (`_host_ver`), Kepler/legacy GPU rejection (`driver < 525`), `nvidia-smi` query error parsing resilience, CPU mode CUDA preinit suppression, Windows 8.3 short path fallback, and CUDA functionality probing. | **PASS** |
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
   - 27 comprehensive unit & visual regression tests implemented and passing.
4. **School PC Crash & Environment Fixes (2026-11-17)**:
   - **DaVinci Resolve Script Sync (`_host_ver` undefined & ctypes.CDLL cleanup)**: Fixed f-string interpolation bug in `generate_davinci_wrapper_content()` in `src/osdoc.py`, and removed remaining unsafe `ctypes.CDLL` preload loop in generated wrapper.
   - **Feedback / Bug Report Form Crash (`No module named 'requests'`)**: Replaced `requests.post()` in `src/gui/dialogs/settings_dialog.py` with zero-dependency standard library `urllib.request` multipart/form-data POST.
   - **Update Check Failure (`No module named 'certifi'`)**: Added graceful fallback to `ssl.create_default_context()` across `src/main.py`, `src/gui/dialogs/update_dialog.py`, `src/gui/dialogs/settings_dialog.py`, `src/engine/preferences.py`, and `src/gui/main_window.py`.
   - **Kepler / Legacy GPU Incompatibility (CUDA 12 vs Driver < 525)**: Updated `has_nvidia_support()` in `src/osdoc.py` to check driver major version and reject driver < 525 (with fallback Windows search paths); implemented `is_cuda_functional()` probe in `TranscriptionMixin`; added regex protection in `_get_optimal_compute_type()` against unexpected `nvidia-smi` error strings.
   - **Windows CPU Return Code 3221225477 (0xC0000005) Access Violation & Unicode Paths**:
     * Suppressed CUDA preinit injection when `fw_device == 'cpu'`.
     * Removed unsafe blind `ctypes.CDLL` preload loop in `setup_cuda_dll_paths()` and DaVinci wrapper.
     * Fixed critical `NameError: name 'log_warn' is not defined` in `src/engine/transcription.py` that broke fallback paths.
     * Enabled `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `KMP_DUPLICATE_LIB_OK=TRUE`, and `OMP_WAIT_POLICY=PASSIVE` across all child subprocesses.
     * Implemented 8.3 short path conversion via `get_short_path()` with parent folder fallback for non-existent target files.
     * Applied safe short paths to `audio_path`, `models_dir`, `libs_dir`, `bin_dir`, `json_output_path`, and `python_exec` in both chunked and single-file runners and model downloader.
     * Added automatic graceful fallback to CPU mode upon runner failure.
5. **AI Codex & Rules Update**:
   - Updated `.agents/rules/architecture.md` with 3-Zone architecture, empirical verification rule, progressive task tracking, and token budget efficiency.
   - Established persistent task state tracking via `docs/DEV_STATE.md`.

---

## 5. Next Steps for Incoming Reviewer / Developer

1. Run `python3 run_tests.py` to verify all 27 tests pass.
2. Run `python3 -m compileall src` to ensure bytecode consistency.
3. Check `tests/artifacts/` for visual progress bar screenshots.
4. Synchronize modified files to `/mnt/dump/BadWords FILES/` as per rule 7.

