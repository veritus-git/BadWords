# BadWords Development State & Task Tracking

> **Status**: Active  
> **Last Updated**: 2026-11-23  
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
| `tests/test_settings_and_version.py` | Settings dialog refactor, lazy tab construction, real-time search filtering, basic vs advanced visibility, DaVinci XML vs DRT assembly mode toggling and animated option dimming, DaVinci Free 21.1+ DRT rejection, dynamic UI scaling (75%-150%), version detection (`git describe --tags`), and telemetry popup drop shadow. | **PASS** |
| `tests/test_host_env_fixes.py` | Regression suite for school PC environment crashes: DaVinci Resolve wrapper generation syntax (`_host_ver`), Kepler/legacy GPU rejection (`driver < 525`), `nvidia-smi` query error parsing resilience, CPU mode CUDA preinit suppression, Windows 8.3 short path fallback, CUDA functionality probing, GitHub issue #19 (`cublas64_12.dll` missing probe detection), and silent Resolve decoupling when Resolve is not installed. | **PASS** |
| `tests/test_visual_progress_bar.py` | Visual regression test for `LiquidProgressBar`: renders screenshots into `tests/artifacts/`, verifies all 4 rounded corners and anti-aliasing clipping across determinate (50%, 100%) and 3-phase indeterminate states (entering, centered, exiting) to prevent squared-off corner regressions (`setClipRect`). | **PASS** |
| `tests/test_timeline_cuts.py` | Multi-framerate calculation across standard & drop rates (23.976, 29.97, 47.952, 59.94, 60.0, 25.0 fps), exact rational drop-frame timebases (24000/1001, 30000/1001), silence cut ripple deletion, color cut extraction, timeline end capping. | **PASS** |
| `tests/test_algorithms.py` | Heuristic repetition/retake detection, 2-layer visual priority (`manual_status` > `algo_status` across both repeat and auto-filler passes), fuzzy string comparison. | **PASS** |
| `tests/test_assembler_xml.py` | Final Cut Pro 7 XML generation (`<xmeml version="5">`), XML schema and frame accuracy validation. | **PASS** |
| `tests/test_data_contracts.py` | Invariant preservation of `words_data[0]` metadata (`meta_global_silence`, session tags, custom metadata), required word keys, empty dataset safety. | **PASS** |
| `tests/test_startup_guard.py` | Startup pipeline: Python 3.10–3.12 gate, Python 3.8 grammar compatibility for `src/startup/`, foreign `sys.path` pruning, consent-only self-heal, Resolve process safety, Discord multipart crash report + opt-out, unified Resolve wrapper isolation, DEV Resolve sync protection, lazy `gui` / instant `BootSplash` visual render. | **PASS** |

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
   - 33 comprehensive unit & visual regression tests implemented and passing.
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
5. **Standalone vs DaVinci Decoupling & GitHub Issue #19 Fix (2026-11-17)**:
   - **GitHub Issue #19 Fix (`Library cublas64_12.dll is not found or cannot be loaded`)**:
     * Expanded `_get_cuda_preinit_code` search paths to include `safe_libs_dir`, `torch/lib`, `bin`, and all `sys.path` entries.
     * Hardened `is_cuda_functional()` probe script by injecting dynamic preinit DLL paths and checking loadability of `cublas64_12.dll` / `cublas64_11.dll` (Windows) and `libcublas.so.12` / `libcublas.so.11` (Linux) prior to execution.
     * If cuBLAS is missing, `is_cuda_functional()` gracefully rejects GPU mode and Auto Mode defaults cleanly to CPU without crashing.
     * In runner failure, `run_whisper` catches exit code 1 / runtime errors and automatically re-executes transcription in CPU mode.
   - **Standalone Mode Clean Decoupling from DaVinci Resolve**:
     * Guarded `sync_resolve_scripts()`: returns immediately without touching filesystem or logging warnings when DaVinci Resolve is not installed.
     * Guarded `ResolveHandler.__init__()`: initializes silently on boot (`silent=True`); early return in `_connect()` and `_load_resolve_script_module()` if Resolve is not installed; no spurious `Could not import DaVinciResolveScript` errors or `sys.path` pollution.
     * Fixed `get_resolve_api_path()` to return `""` when candidate paths do not exist.
     * In `welcome_view.py`: if DaVinci Resolve is not installed, the source selector dropdown offers only "Plik lokalny" (Local file), preventing user confusion.
     * In `main_window.py`: skipped `_populate_timeline_track_combos()` on boot in file mode, deferring it until the user actually switches to Resolve mode.
     * In `track_options_drawer.py`: skipped querying Resolve tracks when in file mode.
     * `_jump_playhead()` no-ops cleanly in standalone file mode.
6. **AI Codex & Rules Update**:
   - Updated `.agents/rules/architecture.md` with 3-Zone architecture, empirical verification rule, progressive task tracking, token budget efficiency, mandatory MIT license header, GitHub CLI (`gh`) authentication note, and smooth dimming UI animation conventions.
   - Maintained strict 100% English convention across codex, code comments, and terminal output.
7. **Settings Architecture Refactor & Setup UX Enhancement (2026-11-17)**:
   - **Terminal Auto-Closure on Linux & macOS**:
     * Updated `setupfiles/linux-setup.sh` and `setupfiles/mac-setup.sh` to launch native installer executable detached (`nohup "$EXE" "$@" >/dev/null 2>&1 &` / `setsid`) and exit 0 immediately so terminal closes.
   - **Settings Dialog Overhaul (`SettingsDialog`)**:
     * Split overcrowded Interface tab into "Appearance & Scaling" (Theme, UI Scaling slider 75%–150%, Font selector) and "Editor & Canvas" (Segmented/Continuous flow, line height, text select mode, marquee).
     * Added dedicated "DaVinci Resolve" tab featuring `AssemblyModeSelector` (`[ XML ]` vs `[ DRT ]` clickable segment blocks).
     * Integrated DaVinci Free 21.1+ check (`is_free_21_1_or_newer`): DRT is locked/disabled with informative tooltip on Free 21.1+, while older Free (< 21.1) and Studio retain DRT support.
     * Implemented animated smooth dimming (0.35 opacity) and interaction blocking on XML-dependent settings (`xml_preserve_track_order`, `link_av_clips`, `link_all_cut_tracks`) when DRT is active, matching silence panel UX.
     * Decoupled Feedback/Bug Report into dedicated "Support & Feedback" tab and moved telemetry toggles/project info to "About & Privacy" tab.
     * Added real-time search bar on the left sidebar above category list to filter options and controls across tabs dynamically.
     * Implemented lazy page construction (`_ensure_page_built`) for instant dialog opening and dark DWM initialization to eliminate white flash on Windows.
     * Fixed DaVinci DRT dimming bug when running standalone/file mode and kept primary XML linking options visible in basic mode.
     * Persisted `timeline_assembly_method` in `_collect_preferences()` and added support across `audio_engine.py` and `track_options_drawer.py`.
   - **Telemetry Consent Popup Styling**:
     * Removed hard border on inner frame and added soft drop shadow (`QGraphicsDropShadowEffect(blurRadius=config.S(30), offset=(0,0))`) matching `SettingsDialog`.
   - **Dynamic Version Detection & Fallback**:
     * Restored `_DEFAULT_VERSION = "4.0.1"` fallback in `src/config/app_constants.py` while ensuring `_detect_version()` auto-detects git tags via `git describe --tags --exact-match` and `--abbrev=0`.
   - **Visual Verification Artifacts & Mandatory Rule 12**:
     * Added Rule 12 to `.agents/rules/architecture.md` mandating visual verification PNG screenshots for all GUI changes.
     * Rendered all 5 required verification screenshots into `tests/artifacts/` (`settings_dialog_general.png`, `settings_dialog_appearance.png`, `settings_dialog_davinci_xml.png`, `settings_dialog_davinci_drt.png`, `telemetry_popup.png`).
8. **Point 1 Cementing: Startup Pipeline, Runtime Isolation & Consent-Based Self-Heal (2026-11-23)**:
   - Created `src/startup/` package (Python 3.8-parseable, stdlib-only guards, unified `runtime_mode`, `i18n_lite`, cross-platform `native_dialogs`, consent-gated `crash_report` + `fatal_dialog`, `legacy_cleanup`, Linux `qt_env`, consent-based `self_heal`, and instant `BootSplash`).
   - Made `src/gui/__init__.py` lazy (PEP 562) and refactored `src/main.py` so `BootSplash` displays immediately before `OSDoctor`, `api`, `engine`, or `gui.main_window` load; removed dead `<3.9` PySide6 hotfix and dead blocking auto-updater.
   - Deferred `OSDoctor` GPU/CPU probing to `log_hardware_info()` inside `InitThread`; removed hardcoded paths and runtime `venv/Scripts/BadWords.exe` copying/patching (`pe_patcher.ensure_badwords_exe`); guarded `sync_resolve_scripts` in DEV mode and stopped deleting `BadWords.py` on Free 21.1+.
   - Unified all 4 Resolve wrapper generators (`osdoc.py`, `installer/src/engine.rs`, `setupfiles/setup.py`, `setupfiles/updater.py`) onto `setupfiles/resolve_wrapper_template.py` with full foreign Python/Conda isolation and macOS `.app` external fallback.
   - Hardened `windows/launcher.c`, `linux/launcher.c`, and `macos/launcher.c` to load only the exact matching Python library version, strip `PYTHONHOME`/foreign `PYTHONPATH`, set `PYTHONNOUSERSITE=1`, and respect `EXIT_FATAL_REPORTED = 3`.
   - Added 11-language startup/self-heal i18n keys, `tests/test_startup_guard.py`, and documented invariants in `docs/CEMENTED.md` (Section 6).

---

## 5. Next Steps for Incoming Reviewer / Developer

1. Run `python3 run_tests.py` to verify all 60 tests pass.
2. Run `python3 -m compileall src` to ensure bytecode consistency.
3. Verify headless GUI import: `_BW_AUTO_HEAL_ATTEMPTED=1 PYTHONPATH=src QT_QPA_PLATFORM=offscreen python3 -c "import gui; print('GUI OK')"`.
4. Ensure files are synchronized with `/mnt/dump/BadWords FILES/`.

