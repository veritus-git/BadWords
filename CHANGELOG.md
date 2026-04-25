# Changelog

All notable changes to the **BadWords** project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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