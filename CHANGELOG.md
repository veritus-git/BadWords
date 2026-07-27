# Changelog

All notable changes to the **BadWords** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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