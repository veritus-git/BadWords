<!--
Copyright (c) 2026 Szymon Wolarz
Licensed under the MIT License. See LICENSE file in the project root for full license information.
-->

# BadWords Cemented Modules Ledger

> **Purpose:** Authoritative technical reference for all **protected workarounds** and **cemented modules** in BadWords.
> Whenever a roadmap item is audited, fixed, verified, and approved by the Product Owner:
> 1. Add full technical documentation below (exact paths, behavior, `# INVARIANT:` contracts, OS quirks, protecting tests, and "DO NOT CHANGE" rules).
> 2. Add **only a 3–4 word index bullet** pointing to this file in `.agents/rules/architecture.md` Section 3 (to keep `architecture.md` strictly under 4,000 characters).

---

## Documentation Template (Copy for New Entries)

```markdown
### N. <Short Module Title>
- **Status:** Cemented (<YYYY-MM-DD>)
- **Files:** `src/...`, `tests/...`
- **How It Works:** Concise technical summary of the architecture and flow.
- **OS-Specific Behavior:** Windows / Linux / macOS differences and required workarounds.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` ...
- **Regression Tests:** `tests/test_...` (`python3 run_tests.py`)
- **Do Not Change Without Product Owner Approval:** Explicit boundaries.
```

---

## Baseline Protected Workarounds (Pre-Roadmap)

### 1. Python < 3.9 PySide6 Typings Hotfix
- **Status:** Removed (replaced by Section 6 on 2026-11-23)
- **Why Removed:** BadWords 4.x requires Python 3.10–3.12 (enforced at startup before any third-party import). The obsolete runtime patch on `PySide6/__init__.py` was removed in Point 1 cementing.

### 2. Resolve Headless Console Stream Buffering (`ResolveStreamProxy`)
- **Status:** Protected Workaround (Pending full Stage 1 audit in Point 2)
- **Files:** `src/osdoc.py` (lines 67–104)
- **How It Works:** Wraps `stdout`/`stderr` streams, accumulates partial writes in `self._buffer` until `\n`, strips redundant `[INFO]`/`[ERROR]`/`[STDOUT/ERR]` prefixes, forwards complete lines to the logger, and swallows stream write/flush errors intentionally.
- **Why It Exists:** Prevents crashes or dropped tracebacks when running inside DaVinci Resolve's embedded Python console or headless launchers.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must implement `write`, `flush`, and `__getattr__` delegation so callers expecting standard file-like stream attributes keep working.
- **Regression Tests:** Covered in Stage 1 Point 2 cementing.

### 3. CUDA / cuDNN Dynamic DLL Injection & CPU Isolation
- **Status:** Protected Workaround & Tested (`tests/test_host_env_fixes.py`; pending full Stage 2 audit in Point 6)
- **Files:** `src/engine/transcription.py` (lines 620–680), `src/osdoc.py` (`has_nvidia_support`, `setup_cuda_dll_paths`, `get_short_path`), `tests/test_host_env_fixes.py`
- **How It Works:** Before initializing Faster-Whisper in GPU mode (`fw_device == "cuda"`), injects venv/libs `nvidia/{cublas,cudnn,cuda_nvrtc,cuda_runtime}/bin`, `torch/lib`, and `bin` paths into `PATH` and `os.add_dll_directory` (Windows) or `LD_LIBRARY_PATH` (Linux). Rejects NVIDIA drivers `< 525` and probes loadability of `cublas64_12.dll`/`cublas64_11.dll` (Windows) or `libcublas.so.12`/`11` (Linux) via `is_cuda_functional()`.
- **OS-Specific Behavior:**
  - Windows: Uses `os.add_dll_directory` + `PATH` + 8.3 short paths (`get_short_path`) for Unicode paths; never runs blind `ctypes.CDLL` preloading loops.
  - Linux: Walks `nvidia/*/lib` and prepends to `LD_LIBRARY_PATH`.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` When `fw_device != "cuda"` (e.g. CPU mode), `_get_cuda_preinit_code()` **must return `""`** so CUDA DLLs are never injected or loaded (prevents Windows `0xC0000005` access violation crashes).
  - `# INVARIANT:` Missing `cublas` or driver `< 525` must gracefully fall back to CPU without crashing.
- **Regression Tests:** `tests/test_host_env_fixes.py`

### 4. Cross-Platform Frameless Window Mixin (`FramelessWindowMixin`)
- **Status:** Protected Workaround (Pending full Stage 1 audit in Point 3)
- **Files:** `src/gui/components/mixins.py`
- **How It Works:** Provides unified frameless window initialization (`frameless_init`), smart corners, and edge resizing across OSes (`_HAS_QFRAMELESS` is currently `False`, using pure Qt + native OS calls).
- **OS-Specific Behavior:**
  - Windows: Root window uses `Qt.Window | Qt.FramelessWindowHint` + Win32 `SetWindowLong` (`WS_THICKFRAME | WS_CAPTION`), DWM attributes (`DwmExtendFrameIntoClientArea`, cloaking, corner/border attributes), and `WM_NCHITTEST` hit-testing; popups use translucent dialogs.
  - macOS: Root window uses native title bar with traffic lights and fullscreen button (`Qt.WindowFullscreenButtonHint`); popups use frameless translucent dialogs.
  - Linux: Root window stays `Qt.Window | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint` with custom `ResizeGrip` edges (never `Qt.Dialog`, preserving WM maximize/fullscreen).
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Linux root window must never use `Qt.Dialog`; Windows root window relies on `WM_NCHITTEST` for Aero Snap and border resize.
- **Regression Tests:** Covered in Stage 1 Point 3 cementing.

### 5. Global Input Focus Clear & Tooltip Debounce (`GlobalAppFilter`)
- **Status:** Protected Workaround (Pending full Stage 3 audit in Point 12A)
- **Files:** `src/gui/dialogs/overlay.py` (lines 21–86)
- **How It Works:** Installed globally on the Qt application to clear focus from active input widgets on outside mouse clicks or `Return`/`Enter`, and replaces native tooltips with a shared debounced custom tooltip (`750ms` single-shot `QTimer` triggered on `Enter`/`Leave`).
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must ignore transient `RuntimeError` on deleted Qt objects and cancel/hide tooltip timers on `Leave`, `Hide`, `MouseButtonPress`, and `WindowDeactivate`.
- **Regression Tests:** Covered in Stage 3 Point 12A cementing.

---

## Cemented Roadmap Modules

### 6. Startup Pipeline, Runtime Isolation & Consent-Based Self-Heal
- **Status:** Cemented (2026-11-23)
- **Files:** `src/main.py`, `src/startup/` (`__init__.py`, `env_guard.py`, `runtime_mode.py`, `i18n_lite.py`, `native_dialogs.py`, `crash_report.py`, `fatal_dialog.py`, `legacy_cleanup.py`, `qt_env.py`, `self_heal.py`, `boot_splash.py`), `src/gui/__init__.py`, `src/gui/dialogs/splash_screen.py`, `src/gui/views/welcome_view.py`, `src/osdoc.py`, `setupfiles/resolve_wrapper_template.py`, `setupfiles/windows/launcher.c`, `setupfiles/linux/launcher.c`, `setupfiles/macos/launcher.c`, `setupfiles/setup.py`, `setupfiles/updater.py`, `setupfiles/pe_patcher.py`, `installer/src/engine.rs`, `installer/src/os/windows.rs`, `tests/test_startup_guard.py`
- **How It Works:**
  1. **Early Guard (`src/startup/`)**: Executes stdlib-only checks before third-party imports. Strips foreign Python/Conda `sys.path` entries tagged with a different minor version (`env_guard.prune_mismatched_version_paths`), enforces Python `3.10 <= ver < 3.13` (`check_python_version`) without auto-opening a browser, relies on `osdoc`'s single idempotent Windows hidden-subprocess hook, cleans legacy v3 files (`legacy_cleanup`), isolates Linux Qt6 (`qt_env`), and verifies core packages (`self_heal.ensure_components`).
  2. **Consent-Based Self-Heal & Crash Reporting**: Missing packages (`HARD_REQUIRED`: `PySide6`, `numpy`; `SOFT_REQUIRED`: `faster_whisper`, `av`, `pypdf`) prompt explicit user consent before running `pip` strictly inside BadWords' own venv (never touching system Python). Fatal startup errors display a localized Qt or native OS dialog (`MessageBoxW` / `osascript` / `zenity` / `kdialog`) with real cause, log path, and an optional consent-gated crash report upload to `SUPPORT_WEBHOOK_URL` (`crash_report.send_report`).
  3. **Instant BootSplash & Deferred Backend**: `src/gui/__init__.py` uses PEP 562 lazy loading so `BootSplash` displays immediately after `QApplication` setup, before `OSDoctor.__init__`, `api`, `engine`, or `gui.main_window` are loaded. `AppController.start()` imports `api` and `engine`, runs `InitThread` (`log_hardware_info`, `sync_resolve_scripts`, `ResolveHandler`, `AudioEngine`), and pre-imports `gui.main_window` while `BootSplash` remains responsive.
  4. **Unified DaVinci Resolve Wrapper**: `setupfiles/resolve_wrapper_template.py` is the single template consumed by `osdoc.py`, `installer/src/engine.rs`, `setupfiles/setup.py`, and `setupfiles/updater.py`. When host Python matches venv Python, it executes in-process (preserving native connection in Resolve Free < 21.1); on version mismatch or failure, it spawns BadWords in an isolated external process stripped of host/Conda env vars (`PYTHONNOUSERSITE=1`, no `PYTHONHOME`/foreign `PYTHONPATH`, never falling back to host/system Python).
- **OS-Specific Behavior:**
  - **Windows:** `launcher.c` reads `pyvenv.cfg` and loads only the exact matching `pythonXYY.dll` (otherwise falls back to `CreateProcessW`), clears `PYTHONHOME` and foreign `PYTHONPATH`, sets `PYTHONNOUSERSITE=1`, and skips `MessageBoxW` when Python exits with `EXIT_FATAL_REPORTED` (`3`). `osdoc.get_venv_python_path` no longer copies `BadWords.exe` into `venv/Scripts`; `installer/src/os/windows.rs` and `setupfiles/setup.py` refresh root `BadWords.exe` when size or mtime differs.
  - **Linux:** `launcher.c` discovers only the exact `libpythonX.Y.so*` matching `pyvenv.cfg` and strips foreign Python env vars. `qt_env.isolate_linux_qt_env` runs before `PySide6` import. Native dialogs fall back to `zenity` → `kdialog` → `notify-send`.
  - **macOS:** `launcher.c` discovers only the exact `ver_short` framework/dylib. Resolve external fallback launches `BadWords.app` (`open -n ... --args --embedded`) when installed. Standalone identity check ignores `RESOLVE_SCRIPT_API` and uses `startup.runtime_mode.is_embedded_in_resolve()`.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` `src/startup/` and the guard section at the top of `src/main.py` must remain parseable by Python 3.8 grammar.
  - `# INVARIANT:` Version gate must run before any third-party import; never auto-open a browser on startup errors.
  - `# INVARIANT:` Exit code `3` (`EXIT_FATAL_REPORTED`) means Python already presented a fatal dialog; native launchers must not display a duplicate dialog.
  - `# INVARIANT:` `BootSplash` and `import gui` must never eagerly import `gui.main_window`.
  - `# INVARIANT:` `OSDoctor.__init__` must not run GPU/CPU probing subprocesses (`log_hardware_info()` runs inside `InitThread`).
  - `# INVARIANT:` `self_heal` must never run without explicit user consent, never target system Python, and never `os.execve` inside a host DaVinci Resolve process.
  - `# INVARIANT:` `sync_resolve_scripts` never deletes `BadWords.py` based on Resolve edition and never writes to real Resolve script directories in DEV mode.
- **Regression Tests:** `tests/test_startup_guard.py`, `tests/test_host_env_fixes.py`, `installer/src/engine.rs` (`test_generate_davinci_wrapper_template_and_isolation`)
- **Do Not Change Without Product Owner Approval:** Supported Python range (3.10–3.12), consent-only self-heal & crash reporting policy, in-process wrapper priority for Resolve Free < 21.1, `EXIT_FATAL_REPORTED = 3` contract.
