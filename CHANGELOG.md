# Changelog

All notable changes to the **BadWords** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [4.1.2] - 2026-11-26
### Fixed
- **macOS Windows, Fullscreen, Settings & Popups (`main_window.py`, `settings_dialog.py`, `titlebar.py`, `mixins.py`, `telemetry_popup.py`, `crash_report_dialog.py`, `export_dialog.py`, `osdoc.py`, `settings_defaults.py`, `welcome_view.py`)**:
  - Defaulted first-launch macOS main window to native desktop maximize (`mac_window_maximized=True` via `showMaximized()`, without forcing a Fullscreen Space) while persisting Fullscreen Space, Maximized, and custom window geometry across restarts.
  - Fixed Settings closing on macOS (both bottom `Close` button and native red `X` from fullscreen, maximized, desktop, or Stage Manager) using native Cocoa `[nsWindow close]` + clean dialog recreation, eliminating empty gray window ghosts and stranded black Fullscreen Spaces.
  - Prevented macOS Fullscreen Space exit / black flash when changing UI scale in Settings by deferring off-Space `MainWindow` rebuilds until Settings closes, removing orphan `setParent(None)` detaches on widgets containing `QVideoWidget`, and skipping `setMinimumSize()` mutations while fullscreen.
  - Switched popups and consent dialogs from `Qt.WindowModal` (Cocoa Sheets) to `Qt.ApplicationModal`, fixed Retina DPR vector icon centering in `_FadeIconLabel`, fixed wrapped label card expansion, and replaced `startSystemMove()` with clamped manual `win.move()` for `_is_popup` windows on macOS so dragging popups never stretches them or triggers Sequoia tiling.
  - Restored `NSWindowCollectionBehaviorFullScreenPrimary` (`1 << 7`) when disabling Always on Top on macOS.
- **DaVinci Resolve Bridge Stability & `.bws` Import (`BadWords Bridge.lua`, `resolve_bridge.py`, `resolve_handler.py`, `welcome_view.py`, `main_window.py`, `main.py`)**:
  - Added read-only `find_timeline_by_name()` in Lua so timeline/track/structure/export queries never switch `SetCurrentTimeline()`, and sent `bridge_ack(req.id)` immediately before executing handlers.
  - Normalized Bridge `GetTimelineStructure` tracks to match Native SHA-256 fingerprints 1:1 (fixing false timeline-changed prompts on identical timelines), fixed `has_complex_timeline_video` callable checks (`'NoneType' object is not callable`), raised Bridge timeouts (`0.75s` alive / `6.0s` info & tracks / `15.0s` structure), debounced `welcome_view` mailbox file watcher (`1500ms` cooldown ignoring `request.lua`), bundled FCPXML inside `.bws` whenever Resolve is connected (preferring XML on import under Bridge/Free 21.1+), and deferred `app.quit()` via `QTimer.singleShot(0, app.quit)` to avoid macOS shutdown segfaults.
- **Chunked Transcription Manual Marks (`transcription_canvas.py`, `main_window.py`)**: Added `merge_manual_marks_into_words()` and protected user-touched tail words from streaming rewinds so manual markings survive chunk finalization across editor, `chapters[0]`, and waveform timeline.
- **Debounced Search Performance (`settings_widgets.py`, `settings_dialog.py`, `search_overlay.py`, `buttons.py`)**: Added folded-entry & chevron pixmap caching + batched `setUpdatesEnabled` in Settings search, precompiled regex + per-word cache + instant clear/Enter flush in transcript `Ctrl+F`, and `160ms` debouncing with Enter/Up/Down flush in `SearchableDropdown`.
- **Updater, Crash Reports & Open Bug Fixes (`src/gui/__init__.py`, `main_window.py`, `setupfiles/updater.py`, `crash_report.py`, `update_dialog.py`)**: Exported `UpdateNotifyDialog` in `gui.__init__._LAZY` (fixing Settings Update `ImportError`, closed crash reports `001` & `002`), imported missing `QFont` in `main_window.py` (closed `003`), fixed `updater.py` `detect_installed_version()` ignoring dynamic `_detect_version()` calls, scoped crash dedup fingerprints by `app_version`, and wired opt-in auto-reports for updater and active Resolve Bridge technical failures.

## [4.1.1] - 2026-11-25
### Changed
- **Windows 11 Taskbar Preview & Window Surfaces (`mixins.py`, `boot_splash.py`, `update_dialog.py`)**: Replaced `DWMWA_COLOR_NONE` (`0xFFFFFFFE`) with exact dark `DWMWA_BORDER_COLOR` (`0x00101010` / `0x002e2e2e`), stopped `nativeEvent` from swallowing `WM_NCPAINT` (`0x0085`) and `WM_NCACTIVATE` (`0x0086`) so DWM composes the hidden 8px maximized non-client frame cleanly (`DWMWA_EXTENDED_FRAME_BOUNDS` matching `rcWork` instead of leaving an unpainted white ring), applied dark Win32 `GCLP_HBRBACKGROUND` class brushes and opaque dark `QPalette`/`paintEvent` fills, and extended paint-synchronized DWM cloaking across every transition - eliminating the Dark Mode taskbar preview white outline, maximized startup bottom white bar, and white unmaximize/close outlines.
- **Localized Model Download Guidance (`src/i18n/*.json`)**: Updated `msg_model_download_failed` across all 11 languages to remove macOS-only `Little Snitch` references and point Windows/Linux/macOS users to internet, firewall/antivirus, folder write permissions, and disk space checks.

### Fixed
- **Windows Startup Diagnostics & GPU-less PC Resilience (`launcher.c`, `main.py`, `osdoc.py`, `runtime_data.py`, `resolve_bridge.py`, `resolve_handler.py`, `audio_preview.py`, `video_preview.py`)**: Fixed `/SUBSYSTEM:WINDOWS` launcher log output via `_wfsopen` + `SetStdHandle`, added Win32 `SetUnhandledExceptionFilter` + MSVC SEH wrapper and automatic one-time `BADWORDS_SAFE_BOOT=1` software RHI/OpenGL relaunch, enabled `faulthandler(..., all_threads=True)`, added full 64-bit ctypes `argtypes`/`restype` across all Win32 handles, deferred `DaVinciResolveScript`/`fusionscript.dll` loading until Resolve is actually running (after an isolated child probe), and guarded `QMediaPlayer`/`QVideoWidget` initialization cleanly.
- **Settings Maximize Reopen & Always-On-Top Z-Order (`settings_dialog.py`, `main_window.py`, `mixins.py`, `osdoc.py`)**: Tracked maximized state on close so reopening restores genuine OS maximize (removing Win11 16px client shrink and Linux Wayland/X11 edge gaps and updating the top-right exit-maximize icon), fixed 64-bit `SetWindowPos` + `WS_EX_TOPMOST` verification, and stopped stale Qt flags from sticking Settings always-on-top when disabled.
- **Windows Whisper Model Symlink Error (`WinError 1314`) & Worker Crash Reporting (`transcription.py`, `audio_engine.py`, `analysis_worker.py`)**: Forced `huggingface_hub.file_download.are_symlinks_supported` to `False` on Windows to avoid unprivileged symlink failures, validated `model.bin`/`config.json` in `check_model_exists()` so partial downloads cannot falsely pass, and wired opt-in auto-crash-reporting for unexpected technical errors in `AnalysisWorker`.
- **Transactional Installer Updates & `certifi` (`installer/src/engine.rs`, `setupfiles/setup.py`)**: Moved obsolete code cleanup (`clean_wipe_target_dir`) inside deployment helpers so existing files are wiped only after a valid package is downloaded and extracted, and explicitly installed/verified `certifi` alongside `faster-whisper`, `av<19`, and `pypdf`.

## [4.1.0] - 2026-11-25
### Added
- **Startup Guard & Consent-Based Self-Heal**: Instant startup splash (`BootSplash`), isolated Python 3.10-3.12 runtime guard, foreign `sys.path` pruning, and consent-gated automatic dependency repair.
- **Automatic Crash Reporting**: Independent opt-in/opt-out error reporting consent (`TelemetryPopup` and `CrashReportConsentDialog`) with automatic privacy scrubbing and rate-limited diagnostics.
- **Zero-Sudo Portable Python 3.12 (Linux/macOS)**: Automatic relocatable CPython 3.12 setup requiring no root password, plus Wayland clipboard fallback in the installer.
- **Redesigned 9-Tab Settings Window**: Live debounced search across tabs, streamlined Custom Markers with optional shortcut binding, hardened Export/Import/Reset All Defaults, and an improved Support & Feedback form with screenshot thumbnails and scrubbed log bundles.
- **Unified Cross-Platform UI Scaling (75%-200%)**: True Auto OS DPI detection without double-scaling across Windows 11, Linux (Wayland/X11), and macOS Retina, with Apply-triggered live UI rebuild.

### Changed
- **Windows 11 & Cross-OS Frameless Windows**: Sharp 90-degree corners (`DWMWCP_DONOTROUND`), exact half-screen Aero Snap restore, proportional cursor drag-rip from maximize, zero startup flashes, opaque solid borders without custom shadows, and cross-OS VSync refresh rate tracking.
- **11-Language Parity & Vector UI**: Synced all 11 translations identically to 631 keys per language, replaced remaining emojis with crisp vector SVG icons, enforced global `Fusion` dark palette immunity against OS Light themes, and rounded progress bar ends cleanly.
- **Static-CRT Windows Binaries & Fast Setup**: Eliminated `VCRUNTIME140.dll` missing errors on clean Windows 11 PCs and replaced slow PowerShell spawns at 96% with pure Win32 COM shortcuts and native NTFS ADS unblocking.

### Fixed
- **Playback End Boundary & Resolve Proxy Audio**: Stopped preview playback cleanly at trimmed DaVinci Resolve clip/timeline boundaries (including trailing `skip_cuts` and `skip_forward`), prevented raw untrimmed playback on head-trimmed clips, and muxed selected-track WAV audio into rendered 360p Resolve video proxies.
- **Safe In-Place Updates (Option 1 & Auto-Updater)**: Replaced blacklist folder wipes with a strict BadWords code whitelist preserving user files, launchers, `temp/`, `models/`, `saves/`, and `venv/`; added real ABI import probes (`PySide6.QtCore`, `faster_whisper`, `av<19`, `pypdf`), `.version` stamping, `4.x` Windows DLL-lock protection, bare + `v`-prefixed release URLs, and clean Linux POSIX wrappers when no C compiler is present.
- **Standalone & Hardware Resilience**: Decoupled standalone mode cleanly when DaVinci Resolve is absent, fixed Kepler/legacy NVIDIA GPU detection (`driver < 525`), and handled missing `cublas64_12.dll` / `requests` / `certifi` gracefully.

## [4.0.1] - 2026-11-11
### Fixed
- **NTSC Timeline Sync**: Fixed 23.976 fps timeline XML synchronization and sub-frame ripple cuts.
- **Text Selection & Installer Polish**: Set continuous Notepad-style text selection as default LMB, added hardware-tier disk space estimation, smart install path detection, keyboard auto-scroll, and legacy v3 cleanup.

## [4.0.0] - 2026-11-06
### Added
- **Standalone Rough Cut Workstation**: Complete independence from DaVinci Resolve — open video or audio files directly from disk with a multi-file queue and drop zone.
- **Multi-Format Timeline Export**: Direct sequence export into Final Cut Pro 7 XML (`.xml`), Final Cut Pro XML (`.fcpxml`), OpenTimelineIO (`.otio`), and CMX 3600 EDL (`.edl`).
- **Background Video Preview Proxies**: Lightweight 360p video proxy generation in background for ultra-smooth scrub and playback of heavy 4K/8K media.
- **Marquee Box Selection**: Desktop-style click-and-drag rectangular text selection in the transcript canvas to highlight and mark dialogue in bulk.
- **Dual Mouse Marking Modes**: Toggle between Marquee Box Selection and Brush Painting, with freely configurable Left and Right mouse button bindings.
- **Live Cut Strikethrough Preview**: Continuous visual strikethrough in transcript text showing exactly what will be removed upon assembly.
- **Advanced Silence Tuning**: Dedicated Silence Detection panel with independent Cut vs. Mark toggles, decibel threshold (-60 dB to 0 dB), pauses to remove (%), min silence duration, min clip duration, and customizable keep-pause padding (default 0.10s) to prevent clipping syllables.
- **Sub-5ms In-RAM Silence Recalculation**: Live recalculation of silence blocks directly from RAM waveform peaks, updating pause statistics and markers instantly without FFmpeg passes.
- **Interactive Timeline Waveform Preview**: Bottom audio/video player with synchronized waveform rendering, progressive cut hatching, rounded clip notches, and playhead clamping.
- **Real-Time Cut Skipping**: Dynamic audio skipping over cut/silence intervals during playback, enabling full acoustic preview of the rough cut before rendering.
- **Apple Silicon Metal Acceleration**: Native GPU transcription via `mlx-whisper` on Apple Silicon Macs (M1-M5), achieving up to ~11x faster transcription than CPU.
- **Chunked Live-Streaming Transcription**: Real-time token streaming with TopStatusIsland indicator and LLM-style token reveal.
- **Dedicated Colors Sidebar Panel**: Active color palette legend with marker counts and one-click bulk removal.
- **Modern Rust GUI Installer**: Sleek egui-based installer with dual animated progress bars, live pip output streaming, system registry integration, and fallback terminal setup.
- **Native Standalone Launchers**: Single-binary executables for Windows (`BadWords.exe`), Linux (ELF), and macOS (Mach-O).
- **Simplified Chinese (`zh`) UI Localization**: Expanded multi-language support to 11 fully localized languages.

### Changed
- **Default Timeline Assembly to FCP7 XML**: Shifted default assembly pipeline from `.drt` to FCP7 XML to permanently resolve DaVinci Resolve's clip unlinking bug and restore full compatibility with DaVinci Resolve Free 21.1+.
- **DRT Assembly Preservation Option**: Maintained native `.drt` pipeline in Settings for DaVinci Resolve Studio (and Free < 21.1) users who require 100% preservation of Color grades, Fusion node graphs, and Fairlight FX.
- **Modular Codebase Architecture**: Complete architectural split into clean packages (`gui/panels`, `gui/views`, `gui/dialogs`, `gui/widgets`, `handlers`, `engine`, `api`).
- **Clustering & Timestamp Heuristics**: Refined Whisper clustering window to 22s and tuned inaudible token detection threshold to 0.67s.

### Fixed
- **PyAV 19 Breaking Change**: Resolved fatal `TypeError: open() got an unexpected keyword argument 'metadata_errors'` on fresh faster-whisper installs by injecting runtime compatibility shims and pinning `av<19`.
- **Broadcast Wave (BWF) Timecode**: Conformed timecode offsets and sequence alignment across XML, EDL, and FCPXML exports.
- **Audio Routing & Multi-Track**: Fixed media offline issues for discrete audio channels, preserved multi-track audio assignments, and corrected stereo pan routing.
- **UI Responsiveness**: Implemented O(1) incremental layout streaming and dirty-rect painting to eliminate UI lag during multi-hour transcript handling.

## [3.2.4] - 2026-07-31
### Fixed
- **Version Metadata**: Hotfixed application version metadata inconsistency in `config.py`.

## [3.2.3] - 2026-07-31
### Fixed
- **Audio Cutting Engine**: Corrected positive offset handling for temporal speech boundary alignment and resolved silence overlap slicing.
- **Audio Preview Word Synchronization**: Fixed word selection drift and added forced word highlight retention during audio preview seeking.
- **WAV Assembly Resilience**: Clamped frame ranges in `WavAssemblyThread` and introduced safe PCM decoding via FFmpeg to prevent `wave.Error` crashes during assembly.

## [3.2.2] - 2026-07-30
### Added
- **Advanced Color Assembly**: Extended the Assembly page logic, enabling users to dynamically select and cut any specific marker color.

### Changed
- **Engine Architecture**: Removed the `stable-ts` (and underlying PyTorch) dependency entirely. The engine now relies purely on `faster-whisper` for native word-level timestamps, drastically reducing the installation footprint.
- **Cutting Precision**: Purged outdated legacy hardcoded values and introduced a global temporal offset. While sub-50ms precision remains elusive, these optimizations push verbatim cutting accuracy to the absolute edge of what is currently possible with open-source models.
- **CPU Performance**: Optimized the chunking and decoding pipeline, pushing CPU transcription speeds to roughly 1.7x real-time on Large models (up from 1.0x).
- **Default Precision**: Set `Ultra precise (chunking)` as the default processing mode to ensure maximum verbatim accuracy out of the box.
- **Installer Cleanup**: Updated the installer and updater scripts to reflect the new lightweight dependency tree and purged legacy installation files.

### Fixed
- **Temporal Drift**: Fixed an issue causing audio preview drift and synchronization inaccuracies with the DaVinci Resolve "Jump to Word" feature.
- **UI & Models**: Fixed an initialization bug with the `Turbo Large` model, adjusted the smooth marquee hover animation logic, and squashed various minor GUI bugs.

## [3.2.0] - 2026-07-27
### Added
- **Audio Preview**: Integrated a built-in audio player with volume and playback controls to preview specific words directly inside the transcript. Features strict source timeline validation.
- **Custom Project Format**: Introduced the `.bws` file extension for robust saving and exporting of BadWords projects.
- **AutoSave System**: Implemented a background AutoSave feature with crash recovery, prompting users to restore their exact session upon a fresh restart.
- **Track Selection Drawer**: Added a responsive, self-expanding grid menu within a sliding drawer to select specific audio/video tracks for assembly.

### Changed
- **Native Assembly (.drt)**: Replaced legacy FCP7 XML timeline assembly with direct manipulation of DaVinci Resolve `.drt` files, ensuring compatibility with complex timelines, adjustment clips, and proxies.
- **Media Cleanup**: Added a post-import cleanup mechanism to automatically remove duplicate media from the Media Pool after timeline creation.
- **Silence Detection Accuracy**: Decoupled duration calculations from timeline metadata to direct WAV file analysis, fixing unmarked silence 'islands' across all framerates.

### Fixed
- **macOS OpenGL Rendering**: Resolved severe transparency glitches and artifacts on macOS by switching the GUI rendering engine to OpenGL and locking UI scaling logic.
- **UI Animation Optimization**: Fixed laggy UI expansion by caching size hints, making drawer animations and window resizing buttery-smooth.
- **Missing Translations**: Added all missing localization keys for the 9 supported languages.

## [3.1.1] - 2026-06-24
### Added
- **Technical Hotwords**: Implemented an experimental feature to scrape technical terms from the original script and feed them into Whisper for more consistent technical transcription.
- **Broom Icon**: Added a quick-clear button to wipe all color marks from the transcript.

### Changed
- **Compare Algorithm (DP)**: Completely rewrote the "Compare to Script" engine using Dynamic Programming with advanced penalties and retake heuristics. This dramatically improves matching precision.
- **Algorithm Performance**: Fixed UI freezing during analysis by moving the compare algorithm to an external subprocess.
- **Side-By-Side Polish**: Enhanced the side-by-side view, correctly centering the focused word when using "Jump to Word".
- **Contact Tab**: Renamed the "Support" tab to "Contact" and changed the webhook to prevent spam.

### Fixed
- **Mac M4 Initialization**: Patched a critical issue with newer Apple Silicon CPUs (M4) getting stuck on initialization.
- **Project Serialization**: Fixed exporting and importing projects so they only hold project data, preventing crashes related to layout/settings data.
- **Taskbar Icon**: Fixed the issue where the app icon randomly vanished on Windows.

## [3.1.0] - 2026-06-21
### Added
- **Standalone Analysis**: Added the ability to scan raw audio for stutters, false starts, and retakes without needing a base script.
- **Side-By-Side View (BETA)**: Introduced the first iteration of a split-screen view mode for comparing script and transcript, complete with a "Jump to Word" sync feature in DaVinci Resolve.
- **Advanced Settings**: Unlocked the "Advanced View" to tweak AI thresholds, chunking settings, and file paths.
- **Auto Python Installation**: Added automatic Python installation for all operating systems if missing.

### Changed
- **Prompt Structure**: Updated all Whisper prompts to use the "GOLDEN stutter structure" for better baseline transcription.

### Fixed
- **PySide6 Compatibility**: Fixed compatibility issues with Python 3.9 and older versions.
- **macOS Hardware Detection**: Fixed the computing type selection on macOS based on available hardware.
- **Performance**: Improved UI performance and reduced input delay.

## [3.0.5] - 2026-06-09
### Changed
- **Terminology**: Renamed "Standalone Silence" to "Simple Silence" for clarity.
- **Localization**: Refined interface language libraries for a more intuitive user experience.
### Fixed
- **Window Management**: Fixed numerous visual and drag behavior issues with the custom titlebar on Windows 11 and Linux X11 environments.
- **Python Detection**: Implemented advanced local Python detection to prevent missing `venv` dependency errors in embedded environments.

## [3.0.4] - 2026-05-15
### Added
- **Documentation**: Added instructions to the README on properly utilizing the local installer for Windows.
### Fixed
- **Windows Assembly**: Deployed a critical hotfix for timeline assembly issues specific to Windows.

## [3.0.3] - 2026-05-15
### Changed
- **Assembly Fallback**: Enhanced the `AppendToTimeline` fallback logic to handle edge-cases when the primary method fails.
### Fixed
- **Audio-Only Timelines**: Fixed an issue where timelines containing only audio clips would cause the assembly process to fail.
- **Windows 11 UI**: Patched final display issues and visual glitches on Windows 11.

## [3.0.2] - 2026-05-06
### Fixed
- **macOS Setup**: Resolved a setup issue on macOS exposed by Python 3.14.
- **Installation Issues**: Fixed an issue causing errors when pasting installation commands in the terminal.

## [3.0.1] - 2026-05-05
### Added
- **Support Links**: Added direct links to the GitHub repository and Buy Me A Coffee page in the Telemetry settings tab.
### Changed
- **UI Tweaks**: Small visual refinements across the application and updated tooltip texts for better clarity.

## [3.0.0] - 2026-05-03
### Added
- **New PySide6 GUI**: Completely migrated the graphical interface from `tkinter` to `PySide6`, bringing a massive visual overhaul and modern architecture.
- **Search Widget**: Added a "Find" widget (`Ctrl+F` shortcut) for searching keywords within the transcript.
- **Multi-language UI**: Added full internationalization (i18n) support with 10 built-in interface languages.
- **Settings System**: Introduced a dedicated JSON-based settings window (`settings.json`) separate from the legacy config, featuring tabs for General, Transcript, and AI Engine.
- **Drag & Drop**: Added drag and drop functionality to side panels
- **Custom Titlebar**: Implemented a cross-platform custom titlebar with system behavior for Windows and Linux.

### Changed
- **Panel Architecture**: Replaced fixed windows with dynamic, resizable panels that have edge holders to indicate resizability.
- **Silence Detection Workflow**: Remade the fast silence page mechanism for better UX and stability.
- **Progress Tracking**: Refined the transcription progress bar stages for a more intuitive user experience.

### Fixed
- **Auto-Installer Python Detection**: Improved the installer to automatically detect and handle missing Python environments (`venv`) on Windows, macOS, and Linux.

## [2.0.3] - 2026-02-28
### Added
- **Transcription Progress**: Replaced the infinite loading loop with a precise, visible percentage progress bar for transcription stage
- **Privacy Controls**: Added an option to send telemetry data without sharing geolocation (country/city) information.
- **Linux Installer**: Added the ability to choose a custom installation path.
- **Uninstallation**: Introduced proper, clean uninstallation routines for both Windows (scorched earth removal of all files and registry orphans) and Linux.

### Changed
- **Installer Polish**: Refined the overall behavior and flow of both Windows and Linux installers for a smoother setup.
- **Linux Updates**: The update option on Linux now smartly skips asking for the hardware acceleration type if an existing environment is detected.
- **Windows Downloads**: Optimized the dependency downloading process in the Windows installer.

### Fixed
- **Linux Subprocesses**: Fixed critical issues with subprocess execution, ensuring the Whisper runner works reliably.
- **Telemetry & Pinging**: Resolved issues with telemetry pings and implemented secure, hash-based UUID generation.
- **Windows Wrapper**: Fixed the DaVinci Resolve wrapper script generation issues during the Windows installation.

## [2.0.2] - 2026-02-25
### Added
- **Compute Type Selection**: Added automatic/manual selection for optimal compute types (float16, float32, int8) to improve performance on new GPUs and compatibility on older hardware.
- **Lazy-Assemble**: Implemented a non-blocking assembly process so the application no longer appears frozen during timeline creation.
- **Windows Status Updates**: Added a dedicated "checking/downloading" stage for better feedback during the initial setup on Windows.
- **Branding**: Official project icon added for the taskbar and system interface.
- **Telemetry**: Added optional, anonymous statistics ping in the installer (OS, version, and country only).
- **Easter Egg**: Secret code added. Try typing $RGB in the script window and click "Analyze".

### Changed
- **Precise Timestamps**: Integrated `stable-ts` for word-level precision, significantly reducing instances of words being cut in half.
- **Auto-Sourcing**: Replaced the manual "Compound Clip Fix Mode" with an intelligent background "Auto-Sourcing" algorithm for smarter timeline assembly.
- **Installer Improvements**: Updated installers to support "Update", "Clean Install", and "Full Wipe" modes.
- **Verbatim Optimization**: Tweaked the transcription logic for better repetition detection.

### Fixed
- **Whisper Hallucinations**: Repetitive AI output (e.g., "mhm mhm...") is now detected and compressed in the GUI (e.g., [x100]).
- **UI Scaling**: Fixed the "non-script-reviewer" window behavior and improved text display.
- **Windows UI**: Fixed the issue where a white title bar would appear on Windows systems.
- **Logic Fixes**: Corrected the behavior of "typos" and "inaudible" fragments when visibility is toggled off.

## [2.0.1] - 2026-02-10
### Added
- **Multi-language Support**: Added all supported Whisper languages, including RTL (Right-to-Left) support.
- **Editor Features**: Added "Show detected typos", "Clear transcript", and "Import project" options.
- **User Preferences**: The app now saves user settings between sessions.

### Changed
- **Silence Detection**: Updated the silence detection algorithm for better accuracy.
- **Window Flexibility**: Changed the fixed editor window resolution to be resizable.

### Fixed
- Fixed the yellow marking of missing parts in script comparison mode.

## [2.0.0] - 2026-02-01
### Added
- **Windows Support**: First official Windows Installer release.
- **Cross-Platform**: Achieved full cross-platform compatibility.

### Changed
- **Engine Rewrite**: Migrated from `openai-whisper` to `faster-whisper` for faster transcription and lower RAM usage.
- **Architecture**: App is now "compact," with all necessary files contained within a single directory.
- **Linux Update**: Rewrote the Linux installer to support the new `faster-whisper` engine.

### Removed
- Removed the manual option for downloading Whisper models on Linux (now automatic).

## [1.0.3] - 2026-01-20
### Added
- Added Russian language support.
- Added a "Marquee Progress Bar" for transcription activity.

### Changed
- **Refactoring**: Decoupled logical functions from `gui.py` into `algorithms.py` and `engine.py`.
- **Terminology**: Renamed "Generate" function to "Assemble".
- **UI Design**: Implemented dynamic window heights for a cleaner look.
- **Installer Safety**: Updated Linux installer to work without the `--break-system-packages` flag.
- **Compound Clips**: Completely remade the "Compound Clip Fix" option.

### Fixed
- Fixed timeline assembly crashes on audio-only timelines.
- Corrected "Compare" option issues (reduced excessive blue/yellow marks).
- Fixed script importing from PDF and DOCX files.
- Improved Whisper verbatim transcript precision.

## [1.0.0] - [1.0.2] - 2026-01-05
- Early local development and proof-of-concept.