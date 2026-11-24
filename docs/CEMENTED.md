<!--
Copyright (c) 2026 Szymon Wolarz
Licensed under the MIT License. See LICENSE file in the project root for full license information.
-->

# BadWords Cemented Modules Ledger

> **Purpose:** Authoritative technical reference for all **protected workarounds** and **cemented modules** in BadWords.
> Whenever a roadmap item is audited, fixed, verified, and approved by the Product Owner:
> 1. Add full technical documentation below (exact paths, behavior, `# INVARIANT:` contracts, OS quirks, protecting tests, and "DO NOT CHANGE" rules).
> 2. Add **only a 3-4 word index bullet** pointing to this file in `.agents/rules/architecture.md` Section 3 (to keep `architecture.md` strictly under 4,000 characters).

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
- **Why Removed:** BadWords 4.x requires Python 3.10-3.12 (enforced at startup before any third-party import). The obsolete runtime patch on `PySide6/__init__.py` was removed in Point 1 cementing.

### 2. Resolve Headless Console Stream Buffering (`ResolveStreamProxy`)
- **Status:** Cemented (2026-11-23 - see Section 8 for full Point 2 documentation)
- **Files:** `src/osdoc.py` (`ResolveStreamProxy`, `log_info`, `log_warn`, `log_warning`, `log_error`), `src/config/runtime_data.py` (`is_stream_redirected_to_file`, `trim_log_file_if_needed`)
- **How It Works:** Wraps `stdout`/`stderr` streams, accumulates partial writes in `self._buffer` until `\n`, strips redundant `[INFO]`/`[WARN]`/`[ERROR]`/`[STDOUT/ERR]` prefixes, forwards complete lines to the logger, and suppresses raw stream echoing (`suppress_stream_echo=True`) whenever `sys.__stdout__` or `sys.__stderr__` already points to `badwords_debug.log` via native C launcher `dup2`.
- **Why It Exists:** Prevents crashes or dropped tracebacks when running inside DaVinci Resolve's embedded Python console or headless launchers while eliminating duplicate log lines when launched from desktop binaries.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must implement `write`, `flush`, and `__getattr__` delegation so callers expecting standard file-like stream attributes keep working.
  - `# INVARIANT:` When `stdout`/`stderr` is redirected to `badwords_debug.log`, `log_info`/`log_warn`/`log_error` and `ResolveStreamProxy` must not echo a second raw copy to the redirected descriptor.
- **Regression Tests:** `tests/test_runtime_data_and_isolation.py` (`test_live_launcher_redirected_logging_writes_each_line_once`, `test_5mb_log_trimming_on_startup`)

### 3. CUDA / cuDNN Dynamic DLL Injection & CPU Isolation
- **Status:** Protected Workaround & Tested (`tests/test_host_env_fixes.py`; pending full Stage 2 audit in Point 6)
- **Files:** `src/engine/transcription.py` (lines 620-680), `src/osdoc.py` (`has_nvidia_support`, `setup_cuda_dll_paths`, `get_short_path`), `tests/test_host_env_fixes.py`
- **How It Works:** Before initializing Faster-Whisper in GPU mode (`fw_device == "cuda"`), injects venv/libs `nvidia/{cublas,cudnn,cuda_nvrtc,cuda_runtime}/bin`, `torch/lib`, and `bin` paths into `PATH` and `os.add_dll_directory` (Windows) or `LD_LIBRARY_PATH` (Linux). Rejects NVIDIA drivers `< 525` and probes loadability of `cublas64_12.dll`/`cublas64_11.dll` (Windows) or `libcublas.so.12`/`11` (Linux) via `is_cuda_functional()`.
- **OS-Specific Behavior:**
  - Windows: Uses `os.add_dll_directory` + `PATH` + 8.3 short paths (`get_short_path`) for Unicode paths; never runs blind `ctypes.CDLL` preloading loops.
  - Linux: Walks `nvidia/*/lib` and prepends to `LD_LIBRARY_PATH`.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` When `fw_device != "cuda"` (e.g. CPU mode), `_get_cuda_preinit_code()` **must return `""`** so CUDA DLLs are never injected or loaded (prevents Windows `0xC0000005` access violation crashes).
  - `# INVARIANT:` Missing `cublas` or driver `< 525` must gracefully fall back to CPU without crashing.
- **Regression Tests:** `tests/test_host_env_fixes.py`

### 4. Cross-Platform Frameless Windows, Custom Title Bar, Always on Top & VSync (`FramelessWindowMixin`)
- **Status:** Cemented (2026-11-24 - Point 3 complete & verified)
- **Files:** `src/gui/components/mixins.py`, `src/gui/components/titlebar.py`, `src/gui/vsync.py`, `src/gui/utils.py`, `src/osdoc.py`, `src/main.py`, `src/startup/boot_splash.py`, `src/gui/main_window.py`, `src/gui/dialogs/settings_dialog.py`, `src/gui/panels/script_panel.py`, `src/gui/widgets/{labels,buttons,language_selector,delegates}.py`, `src/gui/components/{audio_preview,top_status_island,video_preview}.py`, `src/gui/dialogs/{msgbox,unsaved_changes_dialog,marker_dialog,update_dialog,export_dialog,telemetry_popup,v4_migration_dialog}.py`, `installer/src/main.rs`, `installer/src/os/windows.rs`, `src/config/settings_defaults.py`, `src/i18n/*.json`, `tests/test_window_titlebar_vsync.py`
- **How It Works:**
  1. **Frameless Root Windows & 8-Edge Hit-Testing (`mixins.py`, `titlebar.py`)**: Both `BadWordsGUI` and `SettingsDialog` inherit `_BaseMainWindow` (`QMainWindow`, zero `QDialog` X11 dialog shadows) and share identical framing, titlebar (`CustomTitleBar`), and native Win32/Unix handling. On Windows: `nativeEvent` ALWAYS uses `msg.hWnd` (NEVER `self.winId()`, preventing re-entrant `QWidget::create` stack overflow `0xC00000FD` during `ShowWindow`/`CreateWindowEx`), uses 64-bit typed Win32 ctypes signatures via `_get_win32_apis()`, wraps startup `_finish_startup()` in `on_error` + `faulthandler.enable()` checkpoints (`src/main.py`), and uses a cached dark HBRUSH without mutating shared `WNDCLASS`. `WM_NCCALCSIZE` queries live Win32 `IsZoomed(hwnd)` via `compute_win_nccalcsize_rect()`, `WM_NCPAINT=0`, `WM_NCACTIVATE=1` (unless minimized), `WM_NCHITTEST` uses `ScreenToClient` + `GetClientRect` + `compute_win_nchittest()` (`HTMAXBUTTON` Snap Layouts, disabled all 8 resize edges when maximized for Fitts's Law corner `X` & top-edge rip). On Windows 11, root window styles strip `WS_POPUP` (`~0x80000000`) while setting `WS_THICKFRAME | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX`, and `_enforce_win_dwm_attributes()` calls `SetWindowRgn(hwnd, None, True)` (eliminating the Win32 `uxtheme` 4-rect `(4,2,1,0)` top-corner rounding GDI region on `WS_POPUP | WS_CAPTION`), enforces sharp 90-degree corners (`DWMWCP_DONOTROUND`, attribute `33 = 1`), `DWMWA_COLOR_NONE` (`34 = 0xFFFFFFFE`), dark mode (`20 -> 19`), and `DwmExtendFrameIntoClientArea(0,0,0,1)` consistently across `showEvent`, `_dwm_uncloak`, `changeEvent` (`WindowStateChange` / `WinIdChange` / style repair), and `nativeEvent` (`WM_STYLECHANGED` `0x007D` / `WM_DWMCOMPOSITIONCHANGED` `0x031E`). For button restore, `_record_normal_geometry()` captures real `GetWindowRect(hwnd)` (converted to Win32 workspace coords rather than frozen `rcNormalPosition`, preserving Aero-snapped half-screen positions) and `_verify_win_button_restore()` safeguards exact pre-maximize restoration. On Linux: all 8 `ResizeGrip` widgets and the `1px #101010` mouse-transparent `_WindowBorderOverlay` are hidden whenever `_is_effectively_maximized()` is True.
  2. **Zero Custom Shadows, Opaque Solid Borders & Clean Native OS Shadows**: 100% of software `QGraphicsDropShadowEffect`, outer shadow margins, `WA_TranslucentBackground`, and `NoDropShadowWindowHint` are removed across all windows, dialogs, splash screens, popups, tooltips, and the Rust installer (`installer/src/main.rs` Linux window is now opaque `650x550` with zero 28px shadow margin). Windowed root windows render a `1px #101010` border overlay (hidden when maximized); dialogs, splash, popups, and installer use opaque `1px #2e2e2e` solid borders (`#3c3c3c` tooltips). Native OS drop shadows work automatically without margins on Windows 11 (DWM), macOS (`NSWindow`), and Linux X11 (border-only on Wayland).
  3. **Distinct Unmaximize Size Semantics & Proportional Cursor Ripping (`mixins.py`, `titlebar.py`, `settings_dialog.py`)**:
     - **Main Window (`BadWordsGUI`)**: Clicking `btn_max` (`via_button=True`) restores the exact pre-maximize size and position (`_pre_maximize_geometry` / raw Win32 `_pre_maximize_win_rect`). Ripping or double-clicking (`via_button=False`) ALWAYS restores **70% x 70%** of the active screen.
     - **Settings Window (`SettingsDialog`)**: Manually resizable by all 8 edges, **but** exiting maximize (BOTH `btn_max` and ripping/double-clicking) ALWAYS restores its original small default size (`config.SETTINGS_WINDOW_W` x `config.SETTINGS_WINDOW_H`), never 70% or a previous resized size.
     - **Proportional Horizontal Cursor Anchoring**: `compute_proportional_rip_rect()` calculates the exact unclamped cursor ratio (`0.0..1.0`) along the maximized titlebar and clamps cleanly within active screen work area. On Wayland, `CustomTitleBar` calls `showNormal(); resize(); startSystemMove()`; on Linux X11, it positions cleanly under the cursor and settles unmaximize (`25ms` timer) before `startSystemMove()` so the window never jumps left.
  4. **Zero Startup Micro-Window Flashes & Fast Windows Installer Registration**: `create_panel_header()` never calls `setVisible(True)` before layout attachment; `SettingsDialog` never calls `winId()` in `__init__()` or `Qt.Tool | Qt.Dialog`. `installer/src/os/windows.rs` replaces slow PowerShell `Unblock-File` scans over `venv/` with pure-Rust `<5ms` NTFS ADS deletion (`Zone.Identifier`) and replaces the PowerShell `WScript.Shell` COM spawn at `96%` with pure Win32 COM (`IShellLinkW` + `IPersistFile` + `SHGetFolderPathW` + `SendMessageTimeoutW`), eliminating the 96% stall during shortcuts/registration.
  5. **Independent Settings Window, Unsaved-Close Guard, Always on Top, App Icons & VSync**: Non-modal top-level `QMainWindow` with dynamically widened sidebar (`165px+`), centered content (`_CenteredPageHost` max `660px`), zero clipping at 0.85 scale, main-window close guard (`UnsavedChangesDialog`), live zero-restart `always_on_top` (Wayland hint + dynamic popup inheritance) and `apply_app_icon_everywhere()`, macOS `showMaximized()` + localized menus, and 120Hz ProMotion / dynamic monitor `vsync.py`.
- **OS-Specific Behavior:**
  - **Windows:** Live `IsZoomed` `WM_NCCALCSIZE` (`rcWork`), `msg.hWnd` + 64-bit ctypes APIs in `nativeEvent`, `WM_NCPAINT=0`, `WM_NCACTIVATE=1`, cached dark `WM_ERASEBKGND`, `ScreenToClient` `WM_NCHITTEST`, initial `DWMWA_CLOAK`, `DwmExtendFrameIntoClientArea(0, 0, 0, 1)`, `DWMWCP_DONOTROUND (33)`, `DWMWA_BORDER_COLOR (34)`, pure-Rust ADS unblock in installer (`96%` step `<1s`).
  - **macOS:** Root windows start maximized (`showMaximized()`), native NSWindow drop shadow, traffic lights, native localized menu bar (`Cmd+,`/`Cmd+M`), background Dock/bundle icon updates.
  - **Linux:** Opaque `QMainWindow` root windows with `1px #101010` border overlay when windowed (`#2e2e2e` on popups/installer, zero outer shadow margins), 8 `ResizeGrip` widgets, `setDesktopFileName("badwords")`, X11 `libX11`/`wmctrl` `_NET_WM_STATE_ABOVE`, Wayland toggle note.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Never call `self.winId()` inside `nativeEvent` on Windows (always use `msg.hWnd` + typed 64-bit `_get_win32_apis()` signatures); keep `_finish_startup` wrapped with `on_error`.
  - `# INVARIANT:` Close button (`btn_close`) hover background must stay neutral `COLOR_TITLEBAR_HOVER` (NEVER red).
  - `# INVARIANT:` Both `BadWordsGUI` and `SettingsDialog` must inherit `QMainWindow` (`_BaseMainWindow`, never `QDialog` or `Qt.Tool`); zero custom `QGraphicsDropShadowEffect` or `WA_TranslucentBackground` outer margins on any window/dialog/popup/splash/installer.
  - `# INVARIANT:` Main window unmaximize keeps `btn_max` -> pre-max rect and rip -> 70% x 70%; `SettingsDialog` ALWAYS restores its small default size on BOTH `btn_max` and rip; ripping preserves exact proportional horizontal cursor offset via `compute_proportional_rip_rect()`.
  - `# INVARIANT:` Closing `BadWordsGUI` while `SettingsDialog` has unsaved changes must show `UnsavedChangesDialog` and prevent closing either window until the user decides.
- **Regression Tests:** `tests/test_window_titlebar_vsync.py` (14 tests + 8 visual PNG renders in `tests/artifacts/point3_*.png`)
- **Do Not Change Without Product Owner Approval:** Main window `btn_max` vs 70% rip split, `SettingsDialog` always-small unmaximize rule, zero custom shadows + solid `1px` borders (`#101010` root / `#2e2e2e` dialogs/installer), neutral `btn_close` hover color, and proportional cursor rip anchoring.

### 5. Global Input Focus Clear & Tooltip Debounce (`GlobalAppFilter`)
- **Status:** Protected Workaround (Pending full Stage 3 audit in Point 12A)
- **Files:** `src/gui/dialogs/overlay.py` (lines 21-86)
- **How It Works:** Installed globally on the Qt application to clear focus from active input widgets on outside mouse clicks or `Return`/`Enter`, and replaces native tooltips with a shared debounced custom tooltip (`750ms` single-shot `QTimer` triggered on `Enter`/`Leave`).
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Must ignore transient `RuntimeError` on deleted Qt objects and cancel/hide tooltip timers on `Leave`, `Hide`, `MouseButtonPress`, and `WindowDeactivate`.
- **Regression Tests:** Covered in Stage 3 Point 12A cementing.

---

## Cemented Roadmap Modules

### 6. Startup Pipeline, Runtime Isolation & Consent-Based Self-Heal
- **Status:** Cemented (2026-11-23)
- **Files:** `src/main.py`, `src/startup/` (`__init__.py`, `env_guard.py`, `runtime_mode.py`, `i18n_lite.py`, `native_dialogs.py`, `crash_report.py`, `fatal_dialog.py`, `legacy_cleanup.py`, `qt_env.py`, `self_heal.py`, `boot_splash.py`), `src/gui/__init__.py`, `src/gui/dialogs/splash_screen.py`, `src/gui/dialogs/settings_dialog.py`, `src/gui/views/welcome_view.py`, `src/osdoc.py`, `setupfiles/resolve_wrapper_template.py`, `setupfiles/windows/launcher.c`, `setupfiles/linux/launcher.c`, `setupfiles/macos/launcher.c`, `setupfiles/setup.py`, `setupfiles/updater.py`, `setupfiles/pe_patcher.py`, `installer/src/engine.rs`, `installer/src/os/windows.rs`, `tests/test_startup_guard.py`
- **How It Works:**
  1. **Early Guard (`src/startup/`)**: Executes stdlib-only checks before third-party imports. Strips foreign Python/Conda `sys.path` entries tagged with a different minor version (`env_guard.prune_mismatched_version_paths`), enforces Python `3.10 <= ver < 3.13` (`check_python_version`) without auto-opening a browser, relies on `osdoc`'s single idempotent Windows hidden-subprocess hook, cleans legacy v3 files (`legacy_cleanup`), isolates Linux Qt6 (`qt_env`), and verifies core packages (`self_heal.ensure_components`).
  2. **Consent-Based Self-Heal & Crash Reporting**: Missing packages (`HARD_REQUIRED`: `PySide6`, `numpy`; `SOFT_REQUIRED`: `faster_whisper`, `av`, `pypdf`) prompt explicit user consent before running `pip` strictly inside BadWords' own venv (never touching system Python). Fatal startup errors display a styled dark Qt (or native OS fallback) dialog with real cause, expandable traceback, log path, and an optional consent-gated crash report upload via shared `crash_report.post_support_report`, which is also reused by `SettingsDialog` (Contact tab) so both paths share the exact relay validation contract (`Wersja:`, `Tytuł:`, `Treść:`, `User-Agent: BadWords/<ver>`, 1900-char cap).
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
  - `# INVARIANT:` All Discord relay uploads (`crash_report.post_support_report` and `SettingsDialog` Support tab) must use Polish content markers (`Wersja:`, `Tytuł:`, `Treść:`), `<= 1900` chars content truncation, and `User-Agent: BadWords/<ver>`.
- **Regression Tests:** `tests/test_startup_guard.py`, `tests/test_host_env_fixes.py`, `installer/src/engine.rs` (`test_generate_davinci_wrapper_template_and_isolation`)
- **Do Not Change Without Product Owner Approval:** Supported Python range (3.10-3.12), consent-only self-heal & crash reporting policy, in-process wrapper priority for Resolve Free < 21.1, `EXIT_FATAL_REPORTED = 3` contract.

### 7. Automatic Crash Reporting & Dual Consent Flow
- **Status:** Cemented (2026-11-23)
- **Files:** `src/startup/crash_report.py`, `src/startup/fatal_dialog.py`, `src/startup/i18n_lite.py`, `src/main.py`, `src/config/settings_defaults.py`, `src/osdoc.py`, `src/gui/dialogs/telemetry_popup.py`, `src/gui/dialogs/crash_report_dialog.py`, `src/gui/dialogs/__init__.py`, `src/gui/components/dialogs.py`, `src/gui/dialogs/settings_dialog.py`, `src/gui/widgets/buttons.py`, `src/gui/main_window.py`, `src/i18n/*.json`, `tests/test_startup_guard.py`, `tests/test_settings_and_version.py`
- **How It Works:**
  1. **Independent Consent Keys (`user.json`)**: `DEFAULT_USER_DATA` stores `auto_crash_report` (`None | bool`) completely independently from `telemetry_opt_in` (`None | bool`) and `telemetry_geo`. `OSDoctor.load_settings()` strips any lingering `auto_crash_report` key from `settings.json` so all consent state lives exclusively in `user.json`.
  2. **New-User vs Existing-User Consent Routing (`MainWindow.check_telemetry`)**:
     - Brand-new user (`telemetry_opt_in is None`): opens `TelemetryPopup` with two separate cards - Anonymous Telemetry (with geo checkbox that smoothly dims to `0.35` when off) and Automatic Error Reports (**default ON**) - plus `Save & Continue` / `Disable All`.
     - Existing user (`telemetry_opt_in is not None` and `auto_crash_report is None`): opens `CrashReportConsentDialog` **regardless** of whether `telemetry_opt_in` was `True` or `False`, offering one-click `Enable Error Reports` / `Not Now` (closing/Esc persists `False`).
     - Settings Page 8 (`About & Privacy`) exposes `chk_auto_crash_report` (`ToggleSwitch`) alongside telemetry toggles with `(i)` tooltip and search indexing.
  3. **Runtime & Startup Capture + Privacy + Anti-Spam (`src/startup/crash_report.py`)**:
     - `install_runtime_crash_hooks()` installs idempotent `sys.excepthook` and `threading.excepthook` in `src/main.py` before Qt event loop startup (catching main-thread, Qt-slot, `QThread`, and `threading.Thread` uncaught exceptions).
     - `sanitize_crash_text()` strips user home paths, OS usernames/hostnames, private media/script filenames (preserving extension as `<MEDIA_FILE>.<ext>`), email addresses, and webhook URLs across both report bodies and `logs.zip` diagnostic log tails (`_MAX_LOG_BYTES = 256 KB`). Automatic reports never attach `user.json` or `settings.json`.
     - `_CrashRateLimiter` enforces in-session fingerprint deduplication, per-session cap (`3`), permanent per-fingerprint deduplication (`500` newest fingerprints stored in `crash_guard_state.json`, so an identical error is never sent twice), hourly cap (`5/hour`) for distinct errors, recursion guard, and DEV-mode suppression (`BADWORDS_FORCE_CRASH_SEND=1` to override).
     - `fatal_dialog.show_fatal()` checks `get_auto_crash_report_pref()`: if `True`, starts non-blocking background upload via shared `post_support_report()` Discord relay contract and notifies user; if `False` or `None`, shows manual consent prompt.
- **OS-Specific Behavior:**
  - **Windows / Linux / macOS:** Scrubs `C:\Users\<name>\...`, `Documents and Settings`, `/home/<name>`, `/Users/<name>`, and active env/OS user tokens uniformly. Zero system emojis across dialogs and all 11 `src/i18n/*.json` files (vector SVG icons only); `TrackSquareCheckbox` updates minimum dimensions on `setText()` and `_PrivacyConsentDialogBase` disables `QGraphicsOpacityEffect` when opacity is `1.0` to prevent Qt offscreen caching invisibility.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` `auto_crash_report` must remain completely independent of `telemetry_opt_in`; existing users (`telemetry_opt_in is not None`, `auto_crash_report is None`) must always see `CrashReportConsentDialog` once even if they opted out of telemetry.
  - `# INVARIANT:` `src/startup/crash_report.py` must stay stdlib-only and Python 3.8 parseable; automatic runtime sending is suppressed in DEV checkouts unless explicitly overridden.
  - `# INVARIANT:` All automatic crash reports must pass through `sanitize_crash_text()`, `_CrashRateLimiter`, and `post_support_report()` (matching Settings -> Support webhook format).
- **Regression Tests:** `tests/test_startup_guard.py` (`test_privacy_scrubbing_rate_limit_and_live_http_relay`), `tests/test_settings_and_version.py` (`test_telemetry_popup_drop_shadow_and_defaults`, `test_existing_user_crash_report_consent_dialog`, `test_settings_about_page_crash_toggle_and_render`, `test_check_telemetry_routing_new_vs_existing_users`).
- **Do Not Change Without Product Owner Approval:** New-user default ON state for `auto_crash_report`, existing-user telemetry independence, anti-spam rate-limit caps, and Discord relay payload compatibility.

### 8. DEV vs Installed Workspace Isolation, Atomic Config, Single-Write Logging & Session Temp Manager
- **Status:** Cemented (2026-11-23)
- **Files:** `src/config/runtime_data.py`, `src/osdoc.py`, `src/engine/audio_engine.py`, `src/engine/audio_extraction.py`, `src/engine/preferences.py`, `src/api/resolve_bridge.py`, `src/gui/main_window.py`, `src/main.py`, `src/startup/crash_report.py`, `setupfiles/BadWords Bridge.lua`, `setupfiles/windows/launcher.c`, `setupfiles/linux/launcher.c`, `setupfiles/macos/launcher.c`, `tests/test_runtime_data_and_isolation.py`
- **How It Works:**
  1. **Decoupled Data & Path Layer (`src/config/runtime_data.py`)**: Extracted DEV/Installed detection (`detect_dev_mode`), one-time stray `src/` file cleanup (`migrate_stray_src_files_to_dev_workspace`), dynamic sibling `BadWords FILES` discovery (`discover_sibling_installed_dir`), empirical directory write probing (`is_dir_writable`), persistent OS user-profile fallback (`get_user_profile_data_dir`), atomic JSON persistence (`atomic_write_json`), corruption backup & key salvage (`load_json_with_recovery`), startup log trimming (`trim_log_file_if_needed`), stream redirection detection (`is_stream_redirected_to_file`), session-protected temp management (`SessionTempManager`), and Mac App Store container discovery (`get_macos_app_store_resolve_dirs`) out of `src/osdoc.py`.
  2. **Persistent User-Profile Fallback on Read-Only Install Dirs**: When `install_dir` is read-only in Installed mode (e.g., `C:\Program Files\BadWords` tested via empirical file probe `is_dir_writable`, avoiding Windows `os.access` NTFS ACL false positives), `OSDoctor` routes `app_data_dir` to the persistent per-user OS profile (`%LOCALAPPDATA%\BadWords` on Windows, `~/Library/Application Support/BadWords` on macOS, `$XDG_DATA_HOME/BadWords` or `~/.local/share/BadWords` on Linux) before falling back to `Temp/BadWords_Fallback`. Log filename is uniformly `badwords_debug.log`.
  3. **Atomic JSON Config Writes, `.bak` Backup & One-Time Calibration Migration**:
     - All `user.json` and `settings.json` writes go through `atomic_write_json()` (re-entrant lock -> sibling `.tmp` file -> `flush` + `os.fsync` -> `os.replace`).
     - If `user.json` or `settings.json` is corrupted on startup, `load_json_with_recovery()` copies the damaged file to `<file>.bak` and salvages readable primitive key-value pairs via regex before merging with defaults.
     - Legacy `< 4.0.0` configs migrate internal calibration constants (`offset=0.133`, `pad=0.0`, `snap_max=0.25`) once in `OSDoctor.load_settings()`; the per-startup forced disk overwrite in `AudioEngine.__init__()` was removed.
  4. **Single-Write Logging & 5 MB Startup Trimming**:
     - Native C launchers (`windows/launcher.c`, `linux/launcher.c`, `macos/launcher.c`) set `BADWORDS_STDIO_REDIRECTED=1` upon `dup2` redirection to `badwords_debug.log`, and `is_stream_redirected_to_file()` also verifies descriptor identity via `os.path.sameopenfile`.
     - When `sys.__stdout__` / `sys.__stderr__` points to `badwords_debug.log`, `log_info`, `log_warn` (plus alias `log_warning`), `log_error`, and `ResolveStreamProxy` suppress secondary console echoing so every log line and traceback is written **exactly once**.
     - On startup, `trim_log_file_if_needed()` checks if `badwords_debug.log` exceeds `5 MB`; if so, it atomically retains the newest `2.5 MB` aligned to a line boundary.
  5. **Session-Protected Temp Directory & 24h Stale Cleanup (`SessionTempManager`)**:
     - `OSDoctor` registers active project temp files/folders (`wav_path`, `_direct_wav`, `bws_import_*`, background `BW_proxy_*.mp4`) via `register_active_temp_path()` and persists `.bw_session_<pid>.json`.
     - `cleanup_temp(max_age_seconds=86400, close_session=...)` runs on startup (`close_session=False`) and shutdown (`close_session=True`): it never deletes files belonging to any live PID's active session, deletes unreferenced temp files older than **24 hours** (`86400s`), and immediately deletes one-shot helper scripts (`fw_downloader.py`, `bw_runner_*.py`, `bw_drt_probe_*.drt`, concat lists) and the session lock when closing.
  6. **Mac App Store Resolve Sandbox & Windows 8.3 Bridge Paths**:
     - On macOS, `get_macos_app_store_resolve_dirs()` discovers existing `~/Library/Containers/<bundle-id>/Data/Library/Application Support/Blackmagic Design/DaVinci Resolve` directories across Free (`DaVinciResolveLite`) and Studio (`DaVinciResolveAppStore`) MAS containers, adding their `Fusion/Scripts/Utility` and `Fusion/Profiles/*/Fusion.prefs` to `OSDoctor` and `ResolveBridgeClient`.
     - On Windows, `sync_resolve_scripts()` injects both `__BADWORDS_INSTALL_DIR__` and 8.3 `__BADWORDS_SHORT_INSTALL_DIR__` into `BadWords Bridge.lua` so Lua 5.1 `loadfile()` succeeds even when the Windows username contains Polish/Unicode characters.
- **OS-Specific Behavior:**
  - **Windows:** Empirical write probe detects NTFS ACL read-only dirs (`C:\Program Files`); 8.3 short path (`get_short_path`) injected into `BadWords Bridge.lua`; `_is_pid_alive` uses Win32 `OpenProcess` + `GetExitCodeProcess`.
  - **Linux:** Installed mode uses `~/Videos/BadWords_Temp` when `~/Videos` exists so sandboxed/containerized DaVinci Resolve can read exported XML/audio files; DEV mode always isolates temp inside `.dev_workspace/temp`.
  - **macOS:** Supports both standard Blackmagic installer paths and Mac App Store sandbox container paths (`~/Library/Containers/...`) for script deployment, in-container mailbox, and `Fusion.prefs` polling.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` DEV mode must never leave `settings.json`, `user.json`, `saves/`, `temp/`, or `badwords_debug.log` inside `src/`.
  - `# INVARIANT:` All `user.json` and `settings.json` writes must use `atomic_write_json()`, and corrupt files must be backed up to `.bak` with key salvage before healing.
  - `# INVARIANT:` Never echo duplicate `[INFO]`/`[WARN]`/`[ERROR]` lines to `stdout`/`stderr` when redirected to `badwords_debug.log`.
  - `# INVARIANT:` `cleanup_temp()` must never delete files registered to an active session (`register_active_temp_path`), and default stale retention is 24 hours (`86400s`).
  - `# INVARIANT:` `osdoc` must expose both `log_warn` and `log_warning`, as well as module-level `load_preferences()`.
- **Regression Tests:** `tests/test_runtime_data_and_isolation.py` (8 comprehensive live empirical tests).
- **Do Not Change Without Product Owner Approval:** 24-hour temp retention threshold, 5 MB log cap, persistent user-profile fallback priority, and internal calibration constants (`offset=0.133`, `pad=0.0`, `snap_max=0.25`).

### 9. Unified Cross-Platform UI Scaling (Auto OS DPI & Live Rebuild)
- **Status:** Cemented (2026-11-24)
- **Files:** `src/config/app_constants.py`, `src/config/settings_defaults.py`, `src/config/runtime_data.py`, `src/config/__init__.py`, `src/osdoc.py`, `src/main.py`, `setupfiles/windows/badwords.manifest`, `setupfiles/windows/launcher.rc`, `src/i18n/*.json`, `src/gui/dialogs/settings_dialog.py`, `src/gui/main_window.py`, `src/gui/views/welcome_view.py`, `src/gui/panels/script_panel.py`, `src/gui/components/audio_preview.py`, `src/gui/components/transcription_canvas.py`, `src/gui/widgets/sliders.py`, plus `FS_PX()` typography unification across `src/startup/` and `src/gui/` (`dialogs/`, `panels/`, `components/`, `views/`, `widgets/`), `tests/test_ui_scaling.py`, `tests/test_settings_and_version.py`
- **How It Works:**
  1. **Zero Double-Multiplication Formula (`src/config/app_constants.py`)**:
     - `detect_os_scale_pct(screen)` measures true OS display scaling across platforms: native `devicePixelRatio * 100` on Windows and Linux Wayland, normalized `logicalDotsPerInch / 96.0 * 100` on Linux X11 (`Xft.dpi`), and Retina-normalized baseline `logicalDotsPerInch / 72.0 * 100` (`100%`) on macOS (eliminating the legacy hidden `0.85` macOS shrink).
     - `get_qt_base_scale_pct(screen)` separates what Qt already multiplies natively (`dpr * 100`, or `100%` on macOS Retina where `pt` maps `1:1` to `px`) from `OS_SCALE_PERCENT`.
     - In `auto` mode (`ui_scale_mode == "auto"`), `SCALE_FACTOR = OS_SCALE_PERCENT / QT_BASE_SCALE_PERCENT` (`1.0` when Qt already scales natively at `125%`/`150%`, avoiding `125% * 125% = 156%` double-scaling; `1.25` on X11 when `dpr=1.0` and `Xft.dpi=120`). In `manual` mode (`75%-200%`, step `5%`), `SCALE_FACTOR = clamped_pct / QT_BASE_SCALE_PERCENT` so user target percentages produce identical physical size across monitors and platforms.
  2. **Pixel-Locked Typography (`FS_PX` vs `pt`)**:
     - Every Qt stylesheet font rule across `src/gui/` and `src/startup/` uses `config.FS_PX(pt)` (`px` sized cleanly via `SCALE_FACTOR`, avoiding extra OS `Xft.dpi` / `pt` multiplication on top of `SCALE_FACTOR`).
     - `DEFAULT_FONT_SIZE`, widget geometry helpers (`S()`), `TranscriptionCanvas` typography/layout, `AudioPreviewWidget` dynamic `QFontMetrics` timecode width, `WelcomePageView` vertical scroll area, and `wrap_activity_panel` scroll wrapper scale uniformly from `75%` through `200%`.
  3. **Auto Mode, Legacy Migration & Settings UI (`src/osdoc.py`, `src/gui/dialogs/settings_dialog.py`)**:
     - `DEFAULT_SETTINGS["ui_scale_mode"] = "auto"`. `OSDoctor.load_settings()` runs a one-time migration on legacy configs missing `ui_scale_mode` so existing installs automatically adopt native OS scaling without keeping stale hardcoded values, while explicit `"manual"` preferences remain preserved.
     - `SettingsDialog` displays `<N>% (System)` in Auto mode, places the `(i)` tooltip icon directly beside the right-hand slider control (`info_on_right=True`), dynamically sizes `lbl_ui_scale_val` from localized `QFontMetrics`, supports `75%-200%` (5% snaps via `JumpSlider`), switches to `"manual"` upon user drag/click, and returns to `"auto"` on reset.
  4. **Resolve-Safe Live UI Rebuild & Mixed-DPI Monitor Tracking**:
     - Changing UI Scale in Settings triggers live in-process UI reconstruction (`BadWordsGUI.rebuild_ui_for_scale()` and `SettingsDialog.rebuild_ui_for_scale()`), safely tearing down media outputs (`QMediaPlayer`) and child widgets while preserving the active `ResolveHandler` / Lua bridge connection, loaded `words_data`, waveform peaks, timeline selections, and active panels without restarting the process.
     - Connecting `windowHandle().screenChanged` automatically updates the `"System"` scale readout in Auto mode and recalculates `SCALE_FACTOR` in Manual mode when dragging across mixed-DPI displays.
  5. **Aspect-Ratio Sidebar Adaptation (`compute_sidebar_panel_width`)**:
     - Side panels adapt dynamically to screen aspect ratio (`16:9` vs narrower `16:10` / `3:2` displays), narrowing sidebars proportionally (`<= 29%` width at `200%` zoom on laptops) to protect the central transcription canvas instead of shrinking overall UI scale blindly.
- **OS-Specific Behavior:**
  - **Windows 11:** Embedded PerMonitorV2 manifest (`setupfiles/windows/badwords.manifest` linked in `launcher.rc`) ensures native per-monitor DPI crispness alongside `QT_ENABLE_HIGHDPI_SCALING=1` and `PassThrough` rounding.
  - **Linux (X11 / Wayland):** Handles both Wayland fractional DPR (`1.0x` extra scale factor in Auto) and X11 `Xft.dpi` (`SCALE_FACTOR = Xft.dpi / 96` in Auto) uniformly without double font scaling.
  - **macOS (Retina):** Normalizes `72` logical DPI Retina to `100%` OS baseline and maps `FS_PX` consistently with Windows/Linux.
- **Invariants (DO NOT BREAK):**
  - `# INVARIANT:` Never multiply OS DPR twice (`SCALE_FACTOR * QT_BASE_SCALE_PERCENT` in Auto mode must match `OS_SCALE_PERCENT`).
  - `# INVARIANT:` All QSS font rules must use `FS_PX()` (never raw OS-multiplied `pt`) so X11 `Xft.dpi`, Wayland DPR, Windows DPI, and macOS Retina render identically.
  - `# INVARIANT:` `rebuild_ui_for_scale()` must never disconnect or reinitialize `resolve_handler` or discard loaded `words_data` / waveform peaks.
- **Regression Tests:** `tests/test_ui_scaling.py` (8 tests), `tests/test_settings_and_version.py`, plus offscreen PNG renders verified across `75%`, `100%`, `125%`, `150%`, `200%`, and `16:10` aspect ratio in `tests/artifacts/`.
- **Do Not Change Without Product Owner Approval:** Auto OS default mode, `75%-200%` slider range, right-aligned `(i)` placement, Resolve-preserving live rebuild, and aspect-ratio sidebar adaptation.
